"""
API routes for SuiteMind blueprint.
Handles all API endpoints for chatbot functionality.
"""

from flask import request, jsonify, g
from flask_login import login_required
from corposostenibile.extensions import csrf, db
from langchain_community.utilities import SQLDatabase

from ..services import get_postgres_suitemind_service
from ..services.casi_pazienti_service import get_casi_pazienti_service

def register_api_routes(bp):
    """Registra le route API del blueprint."""
    
    @bp.route('/api/postgres-chat', methods=['POST'])
    @csrf.exempt
    def postgres_chat_api():
        """API endpoint per le query del chatbot con PostgreSQL diretto."""
        try:
            data = request.get_json()
            user_query = data.get('query', '').strip()
            session_id = data.get('session_id', None)
            context = data.get('context', {})

            # Aggiungi session_id al context se fornito
            if session_id:
                context['session_id'] = session_id
            else:
                # Genera un session_id basato sull'utente o sulla sessione Flask
                from flask import session
                if hasattr(g, 'user') and g.user:
                    context['session_id'] = f"user_{g.user.id}"
                else:
                    # Usa l'ID di sessione Flask
                    context['session_id'] = session.get('_id', 'anonymous')

            if not user_query:
                return jsonify({
                    'success': False,
                    'error': 'Query vuota'
                }), 400

            # Accesso completo al database - tutte le tabelle disponibili
            sql_db = SQLDatabase(
                engine=db.engine,
                # Rimosso include_tables per accedere a TUTTO il database
                sample_rows_in_table_info=2,  # Mostra 2 righe di esempio per capire la struttura
                include_tables=None  # None = tutte le tabelle
            )

            service = get_postgres_suitemind_service(sql_db=sql_db)
            result = service.process_query(user_query, context)
            return jsonify(result)
        except Exception as e:
            return jsonify({
                'success': False, 
                'error': 'Internal Server Error '
            }), 500

    @bp.route('/api/postgres-chat/clear-session', methods=['POST'])
    @csrf.exempt
    def clear_session_api():
        """API endpoint per pulire la memoria della sessione."""
        try:
            data = request.get_json()
            session_id = data.get('session_id', None)

            if not session_id:
                # Genera session_id come sopra
                from flask import session
                if hasattr(g, 'user') and g.user:
                    session_id = f"user_{g.user.id}"
                else:
                    session_id = session.get('_id', 'anonymous')

            # Inizializza con accesso completo al database
            sql_db = SQLDatabase(
                engine=db.engine,
                include_tables=None,
                sample_rows_in_table_info=0
            )
            service = get_postgres_suitemind_service(sql_db=sql_db)
            service.clear_session_memory(session_id)

            return jsonify({
                'success': True,
                'message': 'Memoria della sessione pulita con successo',
                'session_id': session_id
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Internal Server Error'
            }), 500

    @bp.route('/api/postgres-info', methods=['GET'])
    @csrf.exempt
    def postgres_info_api():
        """API endpoint per ottenere informazioni sul servizio PostgreSQL."""
        try:
            # Inizializza con accesso completo al database
            sql_db = SQLDatabase(
                engine=db.engine,
                include_tables=None,  # Tutte le tabelle
                sample_rows_in_table_info=0
            )
            service = get_postgres_suitemind_service(sql_db=sql_db)
            result = service.get_service_info()
            return jsonify({
                'success': True,
                'data': result
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Internal Server Error'
            }), 500
    @bp.route('/api/casi-pazienti', methods=['POST'])
    @csrf.exempt
    def casi_pazienti_api():
        """
        API endpoint dedicato per analizzare casi di successo dei pazienti.

        Usa un servizio SQL Agent SEPARATO da SuiteMind chat generale,
        ottimizzato per analisi rigorose anti-allucinazione.
        """
        try:
            from flask_login import current_user
            from corposostenibile.models import WeeklyCheck, WeeklyCheckResponse

            # Verifica admin
            if not current_user.is_authenticated or not current_user.is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Accesso non autorizzato'
                }), 403

            data = request.get_json()
            user_query = data.get('query', '').strip()

            if not user_query:
                return jsonify({
                    'success': False,
                    'error': 'Query vuota'
                }), 400

            # ═══════════════════════════════════════════════════════════════════
            # Configura SQL Database SOLO per tabelle pazienti/check
            # (separato da SuiteMind che ha accesso a TUTTO il database)
            # ═══════════════════════════════════════════════════════════════════
            sql_db = SQLDatabase(
                engine=db.engine,
                include_tables=[
                    'clienti',                  # Anagrafica pazienti
                    'weekly_checks',            # Assignment Weekly Check
                    'weekly_check_responses',   # Compilazioni Weekly Check
                    'dca_checks',               # Assignment DCA Check
                    'dca_check_responses',      # Compilazioni DCA Check
                    'typeform_responses'        # Check legacy TypeForm
                ],
                sample_rows_in_table_info=3
            )

            # ═══════════════════════════════════════════════════════════════════
            # USA SERVIZIO DEDICATO "CasiPazientiService"
            # (Separato da SuiteMind chat - NO memoria conversazionale)
            # ═══════════════════════════════════════════════════════════════════

            service = get_casi_pazienti_service(sql_db=sql_db)

            # Analizza casi di successo con timeout protection
            # (il servizio ha già timeout interno di 60s, questo è un safety net)
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("Analisi casi pazienti timeout dopo 90 secondi")

            # Imposta timeout solo su Linux/Unix (non Windows)
            try:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(90)  # Timeout totale 90s
            except (AttributeError, ValueError):
                pass  # Windows non supporta SIGALRM, skip

            try:
                agent_result = service.analyze_success_cases(user_query)
            finally:
                try:
                    signal.alarm(0)  # Disabilita timeout
                except (AttributeError, ValueError):
                    pass

            # Verifica successo analisi
            if not agent_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': agent_result.get('error', 'Errore sconosciuto'),
                    'cases': [],
                    'summary': agent_result.get('summary', '')
                }), 500

            cases = agent_result.get('cases', [])

            # ═══════════════════════════════════════════════════════════════════
            # ARRICCHISCI ogni caso con foto evoluzione settimanale
            # ═══════════════════════════════════════════════════════════════════
            for case in cases:
                cliente_id = case.get('cliente_id')
                if cliente_id:
                    # Trova tutti i weekly check del cliente (ordinati cronologicamente)
                    weekly_checks = db.session.query(WeeklyCheckResponse).join(
                        WeeklyCheck
                    ).filter(
                        WeeklyCheck.cliente_id == cliente_id
                    ).order_by(
                        WeeklyCheckResponse.submit_date.asc()
                    ).all()

                    # Crea array di foto per settimana
                    weekly_photos = []
                    for idx, check in enumerate(weekly_checks, 1):
                        if check.photo_front or check.photo_side or check.photo_back:
                            photos = {
                                'week_number': idx,
                                'submit_date': check.submit_date.strftime('%d/%m/%Y') if check.submit_date else None,
                                'weight': check.weight,
                                'photo_front': check.photo_front,
                                'photo_side': check.photo_side,
                                'photo_back': check.photo_back
                            }
                            weekly_photos.append(photos)

                    case['weekly_photos'] = weekly_photos
                else:
                    case['weekly_photos'] = []

            # Ritorna risultati finali
            return jsonify({
                'success': True,
                'cases': cases,
                'summary': agent_result.get('summary', '')
            })

        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()

            # Log completo nel backend
            print("=" * 80)
            print("ERRORE API CASI PAZIENTI:")
            print("=" * 80)
            print(error_traceback)
            print("=" * 80)

            # Ritorna errore dettagliato al frontend (solo in dev)
            return jsonify({
                'success': False,
                'error': f'Errore interno: {str(e)}',
                'error_type': type(e).__name__,
                'error_traceback': error_traceback  # Mostra traceback completo in console F12
            }), 500

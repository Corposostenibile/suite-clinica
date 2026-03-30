"""
calendar.routes
===============

Route per l'integrazione Google Calendar.

Endpoint:
- /calendar/connect - Connessione OAuth Google
- /calendar/sync - Sincronizzazione eventi
- /calendar/meetings/<cliente_id> - Meeting per cliente
- /calendar/api/events - API per gestire eventi
"""

from datetime import datetime, timedelta
import requests
from flask import (
    Blueprint, request, jsonify,
    redirect, flash, current_app
)
from flask_login import login_required, current_user
from flask_dance.contrib.google import google

from corposostenibile.extensions import db
from corposostenibile.models import User, GoogleAuth, Meeting, Cliente
from .services import GoogleCalendarService, MeetingService, GoogleTokenRefreshService, refresh_google_token_http
from .tasks import refresh_google_tokens_task, cleanup_expired_tokens_task, monitor_token_health

# Import del blueprint dal modulo __init__
from . import calendar_bp


def _ensure_valid_token() -> bool:
    """
    Verifica che il token dell'utente corrente sia valido.
    Se scaduto, tenta il refresh automatico.

    Returns:
        True se il token è valido/refreshato, False altrimenti
    """
    if not current_user.google_auth:
        return False

    google_auth = current_user.google_auth

    # Token ancora valido
    if not google_auth.is_expiring_soon(minutes=5):
        return True

    # Token scaduto o in scadenza, proviamo il refresh
    if not google_auth.can_auto_refresh():
        current_app.logger.warning(f"Token scaduto e nessun refresh_token per user {current_user.id}")
        return False

    current_app.logger.info(f"🔄 Refresh token in corso per user {current_user.id}")
    refresh_token = google_auth.get_refresh_token()

    new_token_data = refresh_google_token_http(refresh_token)
    if new_token_data:
        google_auth.update_tokens(new_token_data)
        db.session.commit()
        current_app.logger.info(f"✅ Token refreshato con successo per user {current_user.id}")
        return True

    current_app.logger.error(f"❌ Refresh fallito per user {current_user.id}")
    return False


@calendar_bp.route('/connect')
@login_required
def calendar_connect():
    """Gestisce il callback OAuth dopo l'autorizzazione Google."""
    # Questo è il callback dopo che l'utente ha autorizzato
    # Flask-Dance ha già salvato il token nella sessione

    frontend_url = current_app.config.get('FRONTEND_URL', '')
    calendar_redirect = f"{frontend_url}/calendar"

    try:
        # Verifica se abbiamo il token da Flask-Dance
        if not google.authorized:
            current_app.logger.warning("❌ Token non autorizzato dopo OAuth callback")
            flash('Errore: autorizzazione Google non completata', 'error')
            return redirect(calendar_redirect)

        # Recupera il token PRIMA di fare chiamate API
        token = google.token
        if not token:
            current_app.logger.error("❌ google.authorized è True ma token è None")
            flash('Errore: token non disponibile', 'error')
            return redirect(calendar_redirect)

        # Log dettagliato del token ricevuto
        current_app.logger.info(f"✅ Token OAuth ricevuto:")
        current_app.logger.info(f"   - Has access_token: {bool(token.get('access_token'))}")
        current_app.logger.info(f"   - Has refresh_token: {bool(token.get('refresh_token'))}")
        current_app.logger.info(f"   - Scopes: {token.get('scope', 'N/A')}")

        if token.get('expires_at'):
            import time
            expires_in = int(token['expires_at'] - time.time())
            current_app.logger.info(f"   - Expires in: {expires_in} secondi ({expires_in//60} minuti)")

        # IMPORTANTE: Verifica che abbiamo il refresh_token
        if not token.get('refresh_token'):
            current_app.logger.warning("⚠️ Nessun refresh_token ricevuto! Il token scadrà dopo 1 ora.")
            current_app.logger.warning("   Verifica che l'app sia in 'Production' mode su Google Cloud Console")

        # Prepara i dati del token per salvarli nel database
        token_data = {
            'access_token': token.get('access_token'),
            'refresh_token': token.get('refresh_token'),
            'token_uri': token.get('token_uri', 'https://oauth2.googleapis.com/token'),
            'client_id': token.get('client_id', current_app.config.get('GOOGLE_CLIENT_ID')),
            'client_secret': token.get('client_secret', current_app.config.get('GOOGLE_CLIENT_SECRET')),
            'scopes': token.get('scope', '').split() if isinstance(token.get('scope'), str) else token.get('scope', []),
        }

        # Calcola expires_at dalla risposta reale di Google
        expires_at = datetime.utcnow() + timedelta(hours=1)  # Default
        if token.get('expires_at'):
            try:
                # expires_at potrebbe essere un timestamp Unix
                expires_at = datetime.fromtimestamp(token['expires_at'])
            except (TypeError, ValueError, OSError):
                current_app.logger.warning(f"⚠️ Impossibile parsare expires_at: {token.get('expires_at')}")
        elif token.get('expires_in'):
            expires_at = datetime.utcnow() + timedelta(seconds=int(token['expires_in']))

        # Aggiungi expires_in al token_data per update_tokens
        if token.get('expires_in'):
            token_data['expires_in'] = token['expires_in']
        if token.get('expires_at'):
            token_data['expires_at'] = token['expires_at']

        # Salva o aggiorna GoogleAuth usando il metodo update_tokens
        google_auth = GoogleAuth.query.filter_by(user_id=current_user.id).first()
        if not google_auth:
            google_auth = GoogleAuth(
                user_id=current_user.id,
                token_json=token_data,
                expires_at=expires_at
            )
            db.session.add(google_auth)
            current_app.logger.info(f"✅ Creato nuovo GoogleAuth per user {current_user.id}")
        else:
            current_app.logger.info(f"✅ Aggiornato GoogleAuth per user {current_user.id}")

        # Usa update_tokens per gestire tutti i campi inclusi refresh_token
        google_auth.update_tokens(token_data)
        db.session.commit()

        current_app.logger.info(f"✅ Token salvato con successo. Scadenza: {expires_at}")
        current_app.logger.info(f"   - Has refresh_token in DB: {google_auth.has_refresh_token()}")

        flash('Google Calendar connesso con successo!', 'success')

    except Exception as e:
        current_app.logger.error(f"❌ Errore in calendar_connect: {str(e)}", exc_info=True)
        flash(f'Errore durante la connessione: {str(e)}', 'error')

    return redirect(calendar_redirect)


@calendar_bp.route('/sync')
@login_required
def sync_events():
    """Sincronizza gli eventi da Google Calendar."""
    if not current_user.google_auth:
        return jsonify({'error': 'Devi prima connetterti a Google Calendar'}), 400

    # Verifica e refresha il token se necessario
    if not _ensure_valid_token():
        return jsonify({'error': 'Token Google scaduto o non valido. Riconnetti il tuo account.'}), 401

    try:
        # Ottieni il token aggiornato dal database
        token_data = current_user.google_auth.token_json
        access_token = token_data.get('access_token')

        if not access_token:
            return jsonify({'error': 'Token di accesso non disponibile. Riconnetti il tuo account.'}), 401

        # Recupera eventi da Google Calendar usando il token dal DB
        params = {
            'timeMin': (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z',
            'timeMax': (datetime.utcnow() + timedelta(days=90)).isoformat() + 'Z',
            'singleEvents': True,
            'orderBy': 'startTime',
            'maxResults': 100
        }

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        resp = requests.get(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events',
            headers=headers,
            params=params,
            timeout=30
        )

        if not resp.ok:
            current_app.logger.error(f"Errore API Google: {resp.status_code} - {resp.text}")
            # Se 401, prova a refreshare e riprovare
            if resp.status_code == 401:
                current_app.logger.info("🔄 Ricevuto 401, tentativo refresh...")
                if _ensure_valid_token():
                    # Riprova con il nuovo token
                    access_token = current_user.google_auth.token_json.get('access_token')
                    headers['Authorization'] = f'Bearer {access_token}'
                    resp = requests.get(
                        'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                        headers=headers,
                        params=params,
                        timeout=30
                    )
                    if not resp.ok:
                        return jsonify({'error': 'Errore nel recupero eventi da Google Calendar'}), 502
                else:
                    return jsonify({'error': 'Token scaduto. Riconnetti il tuo account Google.'}), 401
            else:
                return jsonify({'error': 'Errore nel recupero eventi da Google Calendar'}), 502

        google_events = resp.json().get('items', [])
        synced_count = 0
        updated_count = 0

        for g_event in google_events:
            try:
                # Estrai dati evento
                google_event_id = g_event.get('id')
                if not google_event_id:
                    continue

                # Controlla se l'evento esiste già
                existing_meeting = Meeting.query.filter_by(google_event_id=google_event_id).first()

                # Prepara dati evento
                title = g_event.get('summary', 'Evento senza titolo')
                description = g_event.get('description', '')

                # Estrai il link del meeting (Google Meet, Zoom, etc.)
                meeting_link = None

                # DEBUG: Log dei dati dell'evento
                current_app.logger.info(f"Evento {title}: conferenceData={g_event.get('conferenceData')}, hangoutLink={g_event.get('hangoutLink')}")

                # 1. Controlla conferenceData per Google Meet
                if 'conferenceData' in g_event and 'entryPoints' in g_event['conferenceData']:
                    for entry_point in g_event['conferenceData']['entryPoints']:
                        if entry_point.get('entryPointType') == 'video':
                            meeting_link = entry_point.get('uri')
                            current_app.logger.info(f"Found meeting link from conferenceData: {meeting_link}")
                            break

                # 2. Controlla hangoutLink per Google Meet legacy
                if not meeting_link and 'hangoutLink' in g_event:
                    meeting_link = g_event['hangoutLink']
                    current_app.logger.info(f"Found meeting link from hangoutLink: {meeting_link}")

                # 3. Cerca link nella descrizione (per Zoom, Teams, etc.)
                if not meeting_link and description:
                    import re
                    # Pattern per trovare URL di meeting
                    patterns = [
                        r'(https?://meet\.google\.com/[a-z0-9\-]+)',
                        r'(https?://.*?zoom\.us/[^\s]+)',
                        r'(https?://teams\.microsoft\.com/[^\s]+)',
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, description)
                        if match:
                            meeting_link = match.group(1)
                            current_app.logger.info(f"Found meeting link from description: {meeting_link}")
                            break

                if not meeting_link:
                    current_app.logger.warning(f"No meeting link found for event: {title}")

                # Gestisci date
                start_data = g_event.get('start', {})
                end_data = g_event.get('end', {})

                start_time = None
                end_time = None

                if 'dateTime' in start_data:
                    start_time = datetime.fromisoformat(start_data['dateTime'].replace('Z', '+00:00'))
                elif 'date' in start_data:
                    start_time = datetime.fromisoformat(start_data['date'] + 'T00:00:00+00:00')

                if 'dateTime' in end_data:
                    end_time = datetime.fromisoformat(end_data['dateTime'].replace('Z', '+00:00'))
                elif 'date' in end_data:
                    end_time = datetime.fromisoformat(end_data['date'] + 'T23:59:59+00:00')

                if not start_time:
                    continue

                if existing_meeting:
                    # Aggiorna meeting esistente
                    existing_meeting.title = title
                    existing_meeting.description = description
                    existing_meeting.start_time = start_time
                    existing_meeting.end_time = end_time or start_time
                    existing_meeting.meeting_link = meeting_link  # Aggiorna link meeting
                    updated_count += 1
                else:
                    # Crea nuovo meeting con user loggato ma senza cliente
                    new_meeting = Meeting(
                        google_event_id=google_event_id,
                        title=title,
                        description=description,
                        start_time=start_time,
                        end_time=end_time or start_time,
                        meeting_link=meeting_link,  # Salva link meeting
                        user_id=current_user.id,  # Associa automaticamente all'user loggato
                        cliente_id=None,  # Cliente da associare manualmente
                        status='scheduled'
                    )
                    db.session.add(new_meeting)
                    synced_count += 1

            except Exception as e:
                current_app.logger.error(f"Errore sincronizzazione evento {g_event.get('id')}: {e}")
                continue

        db.session.commit()

        message = f'Sincronizzazione completata: {synced_count} nuovi eventi, {updated_count} aggiornati'
        current_app.logger.info(message)

        return jsonify({
            'success': True,
            'message': message,
            'synced': synced_count,
            'updated': updated_count
        })

    except Exception as e:
        current_app.logger.error(f"Errore sincronizzazione: {e}", exc_info=True)
        return jsonify({'error': f'Errore nella sincronizzazione: {str(e)}'}), 500


# API Routes
@calendar_bp.route('/api/events', methods=['POST'])
@login_required
def api_create_event():
    """API per creare un nuovo evento."""
    if not current_user.google_auth:
        return jsonify({'error': 'Google Calendar non connesso'}), 400

    try:
        data = request.get_json()

        # Crea l'evento in Google Calendar
        service = GoogleCalendarService(current_user.id)

        # Per supportare conferenceData, usiamo conferenceDataVersion=1
        google_event = service.create_event(data, use_conference_data=True)

        # Sincronizza l'evento nel DB locale (associato all'utente + eventuale cliente)
        cliente_id = data.get('cliente_id', None)
        event_category = data.get('event_category', None)
        meeting = MeetingService.sync_google_event_to_meeting(
            google_event,
            cliente_id=cliente_id,
            user_id=current_user.id,
            event_category=event_category
        )

        # Ritorna i dati del meeting creato
        return jsonify({
            'success': True,
            'meeting': {
                'id': meeting.id,
                'google_event_id': meeting.google_event_id,
                'title': meeting.title,
                'start': meeting.start_time.isoformat() if meeting.start_time else None,
                'end': meeting.end_time.isoformat() if meeting.end_time else None,
                'cliente_id': meeting.cliente_id,
                'user_id': meeting.user_id
            },
            'google_event': google_event
        })

    except Exception as e:
        current_app.logger.error(f"Errore creazione evento: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/meetings/<int:cliente_id>')
@login_required
def api_cliente_meetings(cliente_id):
    """API per recuperare i meeting di un cliente (solo quelli dell'utente corrente)."""
    # Ogni utente vede solo i PROPRI meeting con questo cliente
    # Admin può vedere quelli di altri se passa user_id
    requested_user_id = request.args.get('user_id')

    if requested_user_id and current_user.is_admin:
        # Admin può filtrare per altri utenti
        meetings = Meeting.query.filter_by(
            cliente_id=cliente_id,
            user_id=requested_user_id
        ).order_by(Meeting.start_time.desc()).all()
    else:
        # Default: solo i propri meeting (anche per admin)
        meetings = Meeting.query.filter_by(
            cliente_id=cliente_id,
            user_id=current_user.id
        ).order_by(Meeting.start_time.desc()).all()
    return jsonify([meeting.to_dict() for meeting in meetings])


@calendar_bp.route('/api/meeting/<int:meeting_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_meeting_details(meeting_id):
    """API per recuperare, aggiornare o eliminare un meeting."""
    # Recupera il meeting
    meeting = Meeting.query.get_or_404(meeting_id)

    # SICUREZZA: Verifica ownership - solo il proprietario o admin può accedere
    if not current_user.is_admin and meeting.user_id != current_user.id:
        return jsonify({'error': 'Non autorizzato - questo meeting non ti appartiene'}), 403

    if request.method == 'GET':
        # Recupera i dettagli del meeting
        return jsonify({
            'id': meeting.id,
            'google_event_id': meeting.google_event_id,
            'title': meeting.title,
            'description': meeting.description,
            'start': meeting.start_time.isoformat() if meeting.start_time else None,
            'end': meeting.end_time.isoformat() if meeting.end_time else None,
            'location': meeting.location,
            'meeting_link': meeting.meeting_link,
            'cliente_id': meeting.cliente_id,
            'cliente_name': meeting.cliente.nome_cognome if meeting.cliente else None,
            'user_id': meeting.user_id,
            'user_name': meeting.user.full_name if meeting.user else None,
            'user_department': meeting.user.department.name if meeting.user and meeting.user.department else None,
            'event_category': meeting.event_category,
            'status': meeting.status,
            'meeting_outcome': meeting.meeting_outcome,
            'meeting_notes': meeting.meeting_notes,
            'loom_link': meeting.loom_link
        })

    if request.method == 'PUT':
        # PUT - Aggiorna il meeting
        try:
            data = request.get_json()

            # Aggiorna tutti i campi forniti (meeting già recuperato sopra)
            if 'user_id' in data:
                meeting.user_id = data['user_id'] if data['user_id'] else None
            if 'cliente_id' in data:
                meeting.cliente_id = data['cliente_id'] if data['cliente_id'] else None
            if 'event_category' in data:
                meeting.event_category = data['event_category'] if data['event_category'] else None
            if 'status' in data:
                meeting.status = data['status']
            if 'meeting_outcome' in data:
                meeting.meeting_outcome = data['meeting_outcome']
            if 'meeting_notes' in data:
                meeting.meeting_notes = data['meeting_notes']
            if 'loom_link' in data:
                meeting.loom_link = data['loom_link']

            db.session.commit()

            # Prepara la risposta con i dati aggiornati
            response_data = {
                'id': meeting.id,
                'google_event_id': meeting.google_event_id,
                'title': meeting.title,
                'user_id': meeting.user_id,
                'user_name': meeting.user.full_name if meeting.user else None,
                'cliente_id': meeting.cliente_id,
                'cliente_name': meeting.cliente.nome_cognome if meeting.cliente else None,
                'status': meeting.status,
                'meeting_outcome': meeting.meeting_outcome,
                'meeting_notes': meeting.meeting_notes,
                'loom_link': meeting.loom_link,
                'meeting_link': meeting.meeting_link
            }

            return jsonify(response_data)

        except Exception as e:
            current_app.logger.error(f"Errore aggiornamento meeting: {e}")
            return jsonify({'error': str(e)}), 500

    if request.method == 'DELETE':
        # DELETE - Elimina il meeting da Google Calendar e DB locale
        try:
            # meeting già recuperato sopra
            google_event_id = meeting.google_event_id

            # Elimina da Google Calendar se l'utente è autenticato
            if current_user.google_auth:
                try:
                    service = GoogleCalendarService(current_user.id)
                    service.delete_event(google_event_id)
                    current_app.logger.info(f"Evento {google_event_id} eliminato da Google Calendar")
                except Exception as google_error:
                    current_app.logger.warning(f"Errore eliminazione da Google Calendar (continuo comunque): {google_error}")
                    # Continua comunque con l'eliminazione dal DB locale

            # Elimina dal database locale
            db.session.delete(meeting)
            db.session.commit()

            current_app.logger.info(f"Meeting {meeting_id} eliminato dal database")

            return jsonify({
                'success': True,
                'message': 'Evento eliminato con successo',
                'deleted_meeting_id': meeting_id,
                'deleted_google_event_id': google_event_id
            })

        except Exception as e:
            current_app.logger.error(f"Errore eliminazione meeting: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/event/<string:google_event_id>', methods=['DELETE'])
@login_required
def api_delete_event_by_google_id(google_event_id):
    """API per eliminare un evento tramite google_event_id (per eventi senza meeting_id nel DB)."""
    if not current_user.google_auth:
        return jsonify({'error': 'Google Calendar non connesso'}), 400

    try:
        # SICUREZZA: Verifica ownership del meeting nel DB se esiste
        meeting = Meeting.query.filter_by(google_event_id=google_event_id).first()
        if meeting and not current_user.is_admin and meeting.user_id != current_user.id:
            return jsonify({'error': 'Non autorizzato - questo evento non ti appartiene'}), 403

        # Elimina da Google Calendar (usa il calendario dell'utente corrente)
        service = GoogleCalendarService(current_user.id)
        service.delete_event(google_event_id)

        current_app.logger.info(f"Evento {google_event_id} eliminato da Google Calendar")

        # Elimina dal DB locale se esiste
        if meeting:
            db.session.delete(meeting)
            db.session.commit()
            current_app.logger.info(f"Meeting {meeting.id} eliminato anche dal database")

        return jsonify({
            'success': True,
            'message': 'Evento eliminato con successo',
            'deleted_google_event_id': google_event_id,
            'deleted_from_db': meeting is not None
        })

    except Exception as e:
        current_app.logger.error(f"Errore eliminazione evento: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/sync-single-event', methods=['POST'])
@login_required
def api_sync_single_event():
    """API per sincronizzare un singolo evento da Google e salvarlo nel DB."""
    try:
        data = request.get_json()

        # Controlla se il meeting esiste già
        google_event_id = data.get('google_event_id')
        existing_meeting = Meeting.query.filter_by(google_event_id=google_event_id).first()

        if existing_meeting:
            # SICUREZZA: Verifica ownership - solo il proprietario o admin può modificare
            if not current_user.is_admin and existing_meeting.user_id != current_user.id:
                return jsonify({'error': 'Non autorizzato - questo meeting non ti appartiene'}), 403

            # Aggiorna il meeting esistente
            if 'user_id' in data:
                existing_meeting.user_id = data['user_id'] if data['user_id'] else None
            if 'cliente_id' in data:
                existing_meeting.cliente_id = data['cliente_id'] if data['cliente_id'] else None
            if 'event_category' in data:
                existing_meeting.event_category = data['event_category'] if data['event_category'] else None
            if 'status' in data:
                existing_meeting.status = data['status']
            if 'meeting_outcome' in data:
                existing_meeting.meeting_outcome = data['meeting_outcome']
            if 'meeting_notes' in data:
                existing_meeting.meeting_notes = data['meeting_notes']
            if 'loom_link' in data:
                existing_meeting.loom_link = data['loom_link']

            db.session.commit()
            meeting = existing_meeting
        else:
            # Crea un nuovo meeting
            # Parse date con gestione errori
            try:
                start_time_str = data.get('start_time')
                end_time_str = data.get('end_time')

                if not start_time_str:
                    raise ValueError("start_time è obbligatorio")

                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))

                # Se end_time non è fornito, usa start_time + 1 ora
                if end_time_str:
                    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                else:
                    end_time = start_time + timedelta(hours=1)

            except (ValueError, AttributeError) as date_error:
                raise ValueError(f"Formato date non valido: {date_error}")

            # SICUREZZA: Il nuovo meeting appartiene SEMPRE all'utente corrente
            # Admin può assegnare a un altro utente se specificato
            if current_user.is_admin and data.get('user_id'):
                assigned_user_id = data.get('user_id')
            else:
                assigned_user_id = current_user.id

            meeting = Meeting(
                google_event_id=google_event_id,
                title=data.get('title', 'Meeting'),
                description=data.get('description', ''),
                start_time=start_time,
                end_time=end_time,
                user_id=assigned_user_id,
                cliente_id=data.get('cliente_id') if data.get('cliente_id') else None,
                event_category=data.get('event_category') if data.get('event_category') else None,
                status=data.get('status', 'scheduled'),
                meeting_outcome=data.get('meeting_outcome'),
                meeting_notes=data.get('meeting_notes'),
                loom_link=data.get('loom_link')
            )
            db.session.add(meeting)
            db.session.commit()

        # Prepara la risposta
        response_data = {
            'id': meeting.id,
            'google_event_id': meeting.google_event_id,
            'title': meeting.title,
            'user_id': meeting.user_id,
            'user_name': meeting.user.full_name if meeting.user else None,
            'cliente_id': meeting.cliente_id,
            'cliente_name': meeting.cliente.nome_cognome if meeting.cliente else None,
            'event_category': meeting.event_category,
            'status': meeting.status,
            'meeting_outcome': meeting.meeting_outcome,
            'meeting_notes': meeting.meeting_notes,
            'loom_link': meeting.loom_link,
            'meeting_link': meeting.meeting_link
        }

        current_app.logger.info(f"Meeting sincronizzato: {meeting.id} - {meeting.title}")
        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Errore sincronizzazione singolo evento: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/connection-status')
@login_required
def api_connection_status():
    """
    API per verificare lo stato della connessione Google Calendar.

    Returns:
        JSON con:
        - is_connected: bool
        - connect_url: URL per iniziare OAuth
        - user_email: email dell'utente (se connesso)
        - expires_at: scadenza token (se connesso)
    """
    is_connected = False
    expires_at = None
    can_refresh = False

    if current_user.google_auth:
        google_auth = current_user.google_auth

        if not google_auth.is_token_expired():
            is_connected = True
            expires_at = google_auth.expires_at.isoformat() if google_auth.expires_at else None
        elif google_auth.can_auto_refresh():
            is_connected = True
            can_refresh = True
            expires_at = google_auth.expires_at.isoformat() if google_auth.expires_at else None

    return jsonify({
        'success': True,
        'is_connected': is_connected,
        'connect_url': '/oauth/google',  # URL per iniziare OAuth Flask-Dance
        'disconnect_url': '/calendar/disconnect',
        'can_auto_refresh': can_refresh,
        'expires_at': expires_at,
        'user_id': current_user.id,
        'user_email': current_user.email
    })


@calendar_bp.route('/disconnect')
@login_required
def calendar_disconnect():
    """Disconnette l'utente da Google Calendar."""
    if current_user.google_auth:
        db.session.delete(current_user.google_auth)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Google Calendar disconnesso con successo.'})
    else:
        return jsonify({'success': True, 'message': 'Non eri connesso a Google Calendar.'})


@calendar_bp.route('/api/events')
@login_required
def api_get_events():
    """
    API per recuperare eventi per FullCalendar.

    LOGICA: Google Calendar è la FONTE PRIMARIA.
    - Mostra SOLO eventi presenti su Google Calendar
    - Il DB (tabella Meeting) serve solo per ARRICCHIRE i dati (cliente, note, loom, categoria)
    - Se un evento non è su Google → NON viene mostrato
    """
    try:
        events = []

        # DEBUG: Log stato autenticazione
        current_app.logger.info(f"=== API EVENTS DEBUG ===")
        current_app.logger.info(f"User ID: {current_user.id}")
        current_app.logger.info(f"google_auth exists: {current_user.google_auth is not None}")
        current_app.logger.info(f"google.authorized: {google.authorized}")

        if current_user.google_auth:
            current_app.logger.info(f"Token expires_at: {current_user.google_auth.expires_at}")
            current_app.logger.info(f"Has refresh_token: {current_user.google_auth.has_refresh_token()}")

        # Verifica autenticazione Google
        if not current_user.google_auth:
            current_app.logger.warning(f"Utente {current_user.id} - google_auth NON ESISTE")
            return jsonify({'error': 'Google Calendar non connesso - nessun token salvato', 'events': []}), 200

        if not google.authorized:
            current_app.logger.warning(f"Utente {current_user.id} - google.authorized è FALSE")
            # Proviamo a usare direttamente il token dal DB invece di Flask-Dance
            current_app.logger.info("Tento chiamata diretta con token dal DB...")

        # Parametri temporali dal frontend (FullCalendar passa start/end)
        time_min = request.args.get('start')
        time_max = request.args.get('end')

        # Se non specificati, usa default ragionevoli
        if not time_min:
            time_min = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
        else:
            # Normalizza formato data (il frontend potrebbe passare solo YYYY-MM-DD)
            if 'T' not in time_min:
                time_min = time_min + 'T00:00:00Z'
            elif not time_min.endswith('Z') and '+' not in time_min:
                time_min = time_min + 'Z'

        if not time_max:
            time_max = (datetime.utcnow() + timedelta(days=180)).isoformat() + 'Z'
        else:
            # Normalizza formato data
            if 'T' not in time_max:
                time_max = time_max + 'T23:59:59Z'
            elif not time_max.endswith('Z') and '+' not in time_max:
                time_max = time_max + 'Z'

        # Parametri per API Google Calendar
        params = {
            'timeMin': time_min,
            'timeMax': time_max,
            'singleEvents': True,
            'orderBy': 'startTime',
            'maxResults': 2500  # Massimo eventi per richiesta
        }

        current_app.logger.info(f"Richiesta Google Calendar: {time_min} -> {time_max}")

        # Usa token dal DB direttamente (più affidabile di Flask-Dance)
        token_data = current_user.google_auth.token_json
        access_token = token_data.get('access_token')

        if not access_token:
            current_app.logger.error("Nessun access_token nel DB!")
            return jsonify({'error': 'Token non valido', 'events': []}), 200

        current_app.logger.info(f"Access token trovato: {access_token[:20]}...")

        # Chiama Google Calendar API direttamente con requests
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        resp = requests.get(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events',
            headers=headers,
            params=params,
            timeout=30
        )

        current_app.logger.info(f"Risposta Google: status={resp.status_code}")

        if not resp.ok:
            current_app.logger.error(f"Errore API Google Calendar: {resp.status_code} - {resp.text}")
            # Se 401, proviamo refresh token
            if resp.status_code == 401:
                current_app.logger.info("Token scaduto, tento refresh...")
                new_token = refresh_google_token_http(current_user.google_auth.get_refresh_token())
                if new_token:
                    current_user.google_auth.update_tokens(new_token)
                    db.session.commit()
                    # Riprova con nuovo token
                    headers['Authorization'] = f'Bearer {new_token.get("access_token")}'
                    resp = requests.get(
                        'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                        headers=headers,
                        params=params,
                        timeout=30
                    )
                    if not resp.ok:
                        return jsonify({'error': 'Errore dopo refresh token', 'events': []}), 200
                else:
                    return jsonify({'error': 'Impossibile rinnovare token', 'events': []}), 200
            else:
                return jsonify({'error': 'Errore comunicazione Google Calendar', 'events': []}), 200

        google_events = resp.json().get('items', [])
        current_app.logger.info(f"Recuperati {len(google_events)} eventi da Google Calendar")

        # Processa ogni evento Google
        for g_event in google_events:
            google_event_id = g_event.get('id')
            if not google_event_id:
                continue

            # Cerca dati arricchiti nel DB (cliente, note, loom, etc.)
            meeting = Meeting.query.filter_by(google_event_id=google_event_id).first()

            # Estrai meeting_link da Google
            meeting_link = None

            # 1. conferenceData (Google Meet)
            if 'conferenceData' in g_event and 'entryPoints' in g_event['conferenceData']:
                for entry_point in g_event['conferenceData']['entryPoints']:
                    if entry_point.get('entryPointType') == 'video':
                        meeting_link = entry_point.get('uri')
                        break

            # 2. hangoutLink (legacy)
            if not meeting_link and 'hangoutLink' in g_event:
                meeting_link = g_event['hangoutLink']

            # 3. Fallback dal DB se salvato
            if not meeting_link and meeting and meeting.meeting_link:
                meeting_link = meeting.meeting_link

            # Determina colore in base allo status del meeting nel DB
            color = '#667eea'  # Viola default
            if meeting:
                if meeting.status == 'completed':
                    color = '#11998e'  # Verde
                elif meeting.status == 'cancelled':
                    color = '#4b6cb7'  # Blu scuro
                elif meeting.status == 'no_show':
                    color = '#eb3349'  # Rosso

            # Costruisci evento per FullCalendar
            event = {
                'id': google_event_id,
                'title': g_event.get('summary', 'Evento senza titolo'),
                'description': g_event.get('description', ''),
                'color': color,
                'extendedProps': {
                    'google_event_id': google_event_id,
                    'location': g_event.get('location', ''),
                    'google_status': g_event.get('status', 'confirmed'),
                    'meeting_link': meeting_link,
                    # Dati arricchiti dal DB (se esistono)
                    'meeting_id': meeting.id if meeting else None,
                    'user_id': meeting.user_id if meeting else current_user.id,
                    'user_name': meeting.user.full_name if meeting and meeting.user else current_user.full_name,
                    'cliente_id': meeting.cliente_id if meeting else None,
                    'cliente_name': meeting.cliente.nome_cognome if meeting and meeting.cliente else None,
                    'event_category': meeting.event_category if meeting else None,
                    'status': meeting.status if meeting else 'scheduled',
                    'meeting_outcome': meeting.meeting_outcome if meeting else None,
                    'meeting_notes': meeting.meeting_notes if meeting else None,
                    'loom_link': meeting.loom_link if meeting else None
                }
            }

            # Gestisci date/time
            start_data = g_event.get('start', {})
            end_data = g_event.get('end', {})

            if 'dateTime' in start_data:
                event['start'] = start_data['dateTime']
            elif 'date' in start_data:
                event['start'] = start_data['date']
                event['allDay'] = True

            if 'dateTime' in end_data:
                event['end'] = end_data['dateTime']
            elif 'date' in end_data:
                event['end'] = end_data['date']

            events.append(event)

        current_app.logger.info(f"Totale eventi restituiti: {len(events)}")
        return jsonify(events)

    except Exception as e:
        current_app.logger.error(f"Errore recupero eventi: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# Additional API Routes for Users and Customers
@calendar_bp.route('/api/team/users')
@login_required
def api_team_users():
    """API per recuperare la lista dei team members."""
    try:
        users = User.query.filter_by(is_active=True).all()
        users_data = []

        for user in users:
            try:
                # Gestisci department in modo sicuro
                department_name = None
                if hasattr(user, 'department') and user.department:
                    if hasattr(user.department, 'name'):
                        department_name = user.department.name
                    elif hasattr(user.department, 'nome'):
                        department_name = user.department.nome
                    else:
                        department_name = str(user.department)

                user_data = {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'department': department_name
                }
                users_data.append(user_data)
            except Exception as user_error:
                current_app.logger.warning(f"Errore elaborazione utente {user.id}: {user_error}")
                # Aggiungi comunque l'utente senza department
                users_data.append({
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'department': None
                })

        current_app.logger.info(f"Trovati {len(users_data)} utenti")
        return jsonify({'users': users_data})
    except Exception as e:
        current_app.logger.error(f"Errore recupero team users: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/customers/search')
@login_required
def api_customers_search():
    """API per la ricerca live dei clienti."""
    from sqlalchemy import or_

    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 20)), 50)  # Max 50 risultati

    if len(query) < 3:
        return jsonify({'customers': []})

    # Ricerca per nome (case-insensitive)
    search_filter = Cliente.nome_cognome.ilike(f'%{query}%')

    # Query con filtri per trial users se necessario
    customers_query = Cliente.query.filter(search_filter)

    # Se l'utente è trial stage 2, filtra solo clienti assegnati
    if current_user.is_trial and current_user.trial_stage == 2:
        assigned_ids = [c.cliente_id for c in current_user.trial_assigned_clients]
        if assigned_ids:
            customers_query = customers_query.filter(Cliente.cliente_id.in_(assigned_ids))
        else:
            return jsonify({'customers': []})

    # Ordina per nome e limita risultati
    customers = customers_query.order_by(Cliente.nome_cognome).limit(limit).all()

    return jsonify({
        'customers': [{
            'cliente_id': c.cliente_id,
            'nome_cognome': c.nome_cognome,
            'programma_attuale': c.programma_attuale,
            'stato_cliente': c.stato_cliente.value if c.stato_cliente else None
        } for c in customers]
    })


@calendar_bp.route('/api/customers/<int:cliente_id>/minimal')
@login_required
def api_customer_minimal(cliente_id):
    """API per recuperare info minime di un cliente per ID."""
    cliente = Cliente.query.get(cliente_id)

    if not cliente:
        return jsonify({'error': 'Cliente non trovato'}), 404

    # Verifica permessi per trial users
    if current_user.is_trial and current_user.trial_stage == 2:
        assigned_ids = [c.cliente_id for c in current_user.trial_assigned_clients]
        if cliente_id not in assigned_ids:
            return jsonify({'error': 'Non autorizzato'}), 403

    return jsonify({
        'cliente_id': cliente.cliente_id,
        'nome_cognome': cliente.nome_cognome,
        'programma_attuale': cliente.programma_attuale,
        'stato_cliente': cliente.stato_cliente.value if cliente.stato_cliente else None
    })


@calendar_bp.route('/api/customers/list')
@login_required
def api_customers_list():
    """API per recuperare la lista dei clienti."""
    try:
        # Cliente model non ha is_active, prendiamo tutti i clienti attivi
        customers = Cliente.query.all()  # Rimuovo filter_by(is_active=True)
        customers_data = [{
            'cliente_id': customer.cliente_id,
            'nome_cognome': customer.nome_cognome,
            'email': getattr(customer, 'email', None)
        } for customer in customers]

        current_app.logger.info(f"Trovati {len(customers_data)} clienti")
        return jsonify({'customers': customers_data})
    except Exception as e:
        current_app.logger.error(f"Errore recupero clienti: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ADMIN API ENDPOINTS - Token Management & Monitoring
# ============================================================================

@calendar_bp.route('/api/admin/tokens/status')
@login_required
def api_admin_tokens_status():
    """
    API Admin per recuperare lo stato di tutti i token OAuth.

    Requires: Admin privileges
    """
    # Verifica permessi admin
    if not current_user.is_admin:
        return jsonify({'error': 'Accesso negato - solo admin'}), 403

    try:
        status_list = GoogleTokenRefreshService.get_token_expiry_status()
        metrics = monitor_token_health()

        return jsonify({
            'tokens': status_list,
            'metrics': metrics,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f"Errore recupero status token: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/admin/tokens/refresh', methods=['POST'])
@login_required
def api_admin_force_refresh():
    """
    API Admin per forzare il refresh di tutti i token in scadenza.

    Requires: Admin privileges
    """
    # Verifica permessi admin
    if not current_user.is_admin:
        return jsonify({'error': 'Accesso negato - solo admin'}), 403

    try:
        current_app.logger.info(f"Admin {current_user.full_name} ha forzato refresh token")
        stats = refresh_google_tokens_task()

        return jsonify({
            'success': True,
            'stats': stats,
            'message': f"Refresh completato: {stats['refreshed']} token aggiornati, {stats['failed']} falliti"
        })
    except Exception as e:
        current_app.logger.error(f"Errore refresh forzato: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/admin/tokens/cleanup', methods=['POST'])
@login_required
def api_admin_cleanup_tokens():
    """
    API Admin per eliminare token scaduti da più di 7 giorni.

    Requires: Admin privileges
    """
    # Verifica permessi admin
    if not current_user.is_admin:
        return jsonify({'error': 'Accesso negato - solo admin'}), 403

    try:
        current_app.logger.info(f"Admin {current_user.full_name} ha avviato cleanup token")
        count = cleanup_expired_tokens_task()

        return jsonify({
            'success': True,
            'cleaned': count,
            'message': f"{count} token scaduti eliminati"
        })
    except Exception as e:
        current_app.logger.error(f"Errore cleanup token: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/admin/tokens/<int:user_id>/refresh', methods=['POST'])
@login_required
def api_admin_refresh_user_token(user_id):
    """
    API Admin per forzare il refresh del token di un utente specifico.

    Requires: Admin privileges
    """
    # Verifica permessi admin
    if not current_user.is_admin:
        return jsonify({'error': 'Accesso negato - solo admin'}), 403

    try:
        google_auth = GoogleAuth.query.filter_by(user_id=user_id).first()

        if not google_auth:
            return jsonify({'error': f'Nessun token trovato per user {user_id}'}), 404

        current_app.logger.info(f"Admin {current_user.full_name} forza refresh token per user {user_id}")

        success = GoogleTokenRefreshService._refresh_token(google_auth)

        if success:
            return jsonify({
                'success': True,
                'message': f'Token refreshato con successo per user {user_id}',
                'new_expiry': google_auth.expires_at.isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Refresh fallito - controlla i log'
            }), 500

    except Exception as e:
        current_app.logger.error(f"Errore refresh token user {user_id}: {e}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/admin/scheduler/status')
@login_required
def api_admin_scheduler_status():
    """
    API Admin per verificare lo stato dello scheduler.

    Requires: Admin privileges
    """
    # Verifica permessi admin
    if not current_user.is_admin:
        return jsonify({'error': 'Accesso negato - solo admin'}), 403

    try:
        from .scheduler import get_scheduler_status
        status = get_scheduler_status()

        return jsonify(status)
    except Exception as e:
        current_app.logger.error(f"Errore recupero status scheduler: {e}")
        return jsonify({'error': str(e)}), 500


"""
API Routes per Rimborsi clienti.
Solo admin possono accedere.
"""

from datetime import datetime, date
from functools import wraps

from flask import jsonify, request, abort
from flask_login import login_required, current_user

from corposostenibile.blueprints.rimborsi import bp
from corposostenibile.models import Rimborso, Cliente
from corposostenibile.extensions import db, csrf


def admin_required(f):
    """Decorator per verificare che l'utente sia admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/list', methods=['GET'])
@login_required
@admin_required
def list_rimborsi():
    """
    GET /rimborsi/api/list
    Lista tutti i rimborsi con paginazione e filtri.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    tipologia = request.args.get('tipologia', '').strip()

    query = Rimborso.query.join(Cliente, Rimborso.cliente_id == Cliente.cliente_id)

    if search:
        query = query.filter(Cliente.nome_cognome.ilike(f'%{search}%'))

    if tipologia:
        query = query.filter(Rimborso.tipologia == tipologia)

    query = query.order_by(Rimborso.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'rimborsi': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': pagination.page,
    })


@bp.route('/create', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def create_rimborso():
    """
    POST /rimborsi/api/create
    Crea un nuovo rimborso.
    """
    data = request.get_json() or {}

    cliente_id = data.get('cliente_id')
    if not cliente_id:
        return jsonify({'success': False, 'error': 'Cliente obbligatorio'}), 400

    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), 404

    tipologia = data.get('tipologia')
    if tipologia not in ('entro_14_giorni', 'dopo_14_giorni'):
        return jsonify({'success': False, 'error': 'Tipologia non valida'}), 400

    motivato = data.get('motivato')
    if motivato is None:
        return jsonify({'success': False, 'error': 'Indicare se motivato o immotivato'}), 400

    motivazione = data.get('motivazione', '').strip()
    if motivato and not motivazione:
        return jsonify({'success': False, 'error': 'La motivazione è obbligatoria per rimborsi motivati'}), 400

    data_fine_percorso_str = data.get('data_fine_percorso')
    if not data_fine_percorso_str:
        return jsonify({'success': False, 'error': 'Data fine percorso obbligatoria'}), 400

    try:
        data_fine_percorso = date.fromisoformat(data_fine_percorso_str)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'error': 'Formato data non valido (YYYY-MM-DD)'}), 400

    # Snapshot professionisti assegnati al momento del rimborso
    # I professionisti sono direttamente sul modello Cliente
    professionisti = []
    for ruolo, rel_attr in [('nutrizionista', 'nutrizionista_user'), ('coach', 'coach_user'), ('psicologa', 'psicologa_user')]:
        user = getattr(cliente, rel_attr, None)
        if user:
            professionisti.append({
                'id': user.id,
                'nome': user.full_name,
                'ruolo': ruolo,
            })

    try:
        rimborso = Rimborso(
            cliente_id=cliente_id,
            tipologia=tipologia,
            motivato=motivato,
            motivazione=motivazione if motivato else None,
            data_fine_percorso=data_fine_percorso,
            professionisti_snapshot=professionisti,
            created_by_id=current_user.id,
        )

        # Aggiorna la data fine percorso sul cliente
        cliente.data_fine_percorso = data_fine_percorso

        db.session.add(rimborso)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Rimborso registrato con successo',
            'rimborso': rimborso.to_dict(),
        }), 201
    except Exception:
        db.session.rollback()
        bp.logger.exception("Errore creazione rimborso")
        return jsonify({
            'success': False,
            'error': 'Errore interno durante la creazione del rimborso',
        }), 500


@bp.route('/<int:rimborso_id>', methods=['GET'])
@login_required
@admin_required
def get_rimborso(rimborso_id):
    """GET /rimborsi/api/<id>"""
    rimborso = Rimborso.query.get(rimborso_id)
    if not rimborso:
        return jsonify({'success': False, 'error': 'Rimborso non trovato'}), 404

    return jsonify({'success': True, 'rimborso': rimborso.to_dict()})


@bp.route('/<int:rimborso_id>', methods=['DELETE'])
@csrf.exempt
@login_required
@admin_required
def delete_rimborso(rimborso_id):
    """DELETE /rimborsi/api/<id>"""
    rimborso = Rimborso.query.get(rimborso_id)
    if not rimborso:
        return jsonify({'success': False, 'error': 'Rimborso non trovato'}), 404

    db.session.delete(rimborso)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Rimborso eliminato con successo'})


@bp.route('/search-clienti', methods=['GET'])
@login_required
@admin_required
def search_clienti():
    """
    GET /rimborsi/api/search-clienti?q=nome
    Ricerca clienti per nome/cognome (autocomplete).
    """
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'success': True, 'clienti': []})

    clienti = Cliente.query.filter(
        Cliente.nome_cognome.ilike(f'%{q}%')
    ).order_by(Cliente.nome_cognome).limit(10).all()

    return jsonify({
        'success': True,
        'clienti': [{
            'cliente_id': c.cliente_id,
            'nome_cognome': c.nome_cognome,
            'programma_attuale': c.programma_attuale,
        } for c in clienti],
    })

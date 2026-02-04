from flask import jsonify, request
from sqlalchemy import or_

from corposostenibile.models import Cliente
from corposostenibile.blueprints.search import bp

@bp.route('/global', methods=['GET'])
def global_search():
    """
    Search endpoint for global search.
    Query params:
        q: search query string
    """
    q = request.args.get('q', '').strip()
    
    if not q or len(q) < 2:
        return jsonify([])
        
    results = []
    
    # --- SEARCH CLIENTI ---
    # Search in nome_cognome, mail, numero_telefono
    # Limit to top 10 for now
    clienti_query = Cliente.query.filter(
        or_(
            Cliente.nome_cognome.ilike(f'%{q}%'),
            Cliente.mail.ilike(f'%{q}%'),
            Cliente.numero_telefono.ilike(f'%{q}%')
        )
    ).limit(10).all()
    
    for c in clienti_query:
        # Determine avatar or initials (logic similar to frontend if needed, 
        # but here we just return data)
        results.append({
            'type': 'paziente',
            'id': c.cliente_id,
            'title': c.nome_cognome,
            'subtitle': c.mail or 'No email',
            'avatar': None, # Placeholder for now
            'link': f'/clienti-dettaglio/{c.cliente_id}' # Frontend route
        })
        
    return jsonify(results)

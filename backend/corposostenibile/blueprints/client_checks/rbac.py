"""
RBAC helpers for client_checks: filter data by role (admin / team_leader / professionista).
Used by api_azienda_stats and api_admin_dashboard_stats.
"""
from flask_login import current_user
from sqlalchemy import or_

from corposostenibile.extensions import db
from corposostenibile.models import Cliente, User, Team


def get_accessible_clients_query():
    """
    Restituisce una subquery di Cliente.cliente_id accessibili all'utente corrente.
    - Admin: None (accesso a tutti i clienti)
    - Team Leader: clienti assegnati ai membri dei team gestiti
    - Professionista: solo i propri clienti
    """
    if not current_user.is_authenticated:
        return None
    # Admin: vede tutto
    if getattr(current_user, 'is_admin', False) or getattr(current_user, 'role', None) == 'admin':
        return None
    # Team Leader: clienti dei membri dei team che guida
    if current_user.teams_led:
        managed_team_ids = [t.id for t in current_user.teams_led]
        team_members_query = (
            db.session.query(User.id)
            .join(User.teams)
            .filter(Team.id.in_(managed_team_ids))
        )
        return (
            db.session.query(Cliente.cliente_id)
            .filter(
                or_(
                    Cliente.nutrizionista_id.in_(team_members_query),
                    Cliente.coach_id.in_(team_members_query),
                    Cliente.psicologa_id.in_(team_members_query),
                )
            )
        )
    # Professionista: solo i propri clienti
    return (
        db.session.query(Cliente.cliente_id)
        .filter(
            or_(
                Cliente.nutrizionista_id == current_user.id,
                Cliente.coach_id == current_user.id,
                Cliente.psicologa_id == current_user.id,
                Cliente.nutrizionisti_multipli.any(User.id == current_user.id),
                Cliente.coaches_multipli.any(User.id == current_user.id),
                Cliente.psicologi_multipli.any(User.id == current_user.id),
            )
        )
    )

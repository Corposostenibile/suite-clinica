"""
RBAC helpers for client_checks: filter data by role (admin / team_leader / professionista).
Used by api_azienda_stats and api_admin_dashboard_stats.
"""
from flask_login import current_user
from sqlalchemy import or_

from corposostenibile.extensions import db
from corposostenibile.models import (
    CallBonus,
    CallBonusStatusEnum,
    Cliente,
    ClienteProfessionistaHistory,
    User,
    Team,
)


def _call_bonus_client_ids_for_user(user_id: int):
    """Subquery: cliente_id di CallBonus attive assegnate all'utente."""
    return (
        db.session.query(CallBonus.cliente_id)
        .filter(
            CallBonus.professionista_id == user_id,
            CallBonus.status == CallBonusStatusEnum.accettata,
        )
    )


def get_accessible_clients_query():
    """
    Restituisce una subquery di Cliente.cliente_id accessibili all'utente corrente.
    - Admin: None (accesso a tutti i clienti)
    - Team Leader: clienti assegnati ai membri dei team gestiti
    - Professionista: solo i propri clienti + clienti con call bonus attive
    """
    if not current_user.is_authenticated:
        return None
    # Admin: vede tutto
    if getattr(current_user, 'is_admin', False) or getattr(current_user, 'role', None) == 'admin':
        return None
    # Team Leader: clienti dei membri dei team che guida (incluso sé stesso)
    if current_user.teams_led:
        managed_team_ids = [t.id for t in current_user.teams_led]
        team_members_query = (
            db.session.query(User.id)
            .join(User.teams)
            .filter(Team.id.in_(managed_team_ids))
        )
        # Include the team leader themselves in the visible member IDs
        team_member_ids_with_leader = team_members_query.union(
            db.session.query(db.literal(current_user.id))
        )
        return (
            db.session.query(Cliente.cliente_id)
            .filter(
                or_(
                    Cliente.nutrizionista_id.in_(team_member_ids_with_leader),
                    Cliente.coach_id.in_(team_member_ids_with_leader),
                    Cliente.psicologa_id.in_(team_member_ids_with_leader),
                    Cliente.consulente_alimentare_id.in_(team_member_ids_with_leader),
                    Cliente.health_manager_id.in_(team_member_ids_with_leader),
                    Cliente.nutrizionisti_multipli.any(User.id.in_(team_member_ids_with_leader)),
                    Cliente.coaches_multipli.any(User.id.in_(team_member_ids_with_leader)),
                    Cliente.psicologi_multipli.any(User.id.in_(team_member_ids_with_leader)),
                    Cliente.consulenti_multipli.any(User.id.in_(team_member_ids_with_leader)),
                )
            )
        )
    # Professionista: propri clienti + history attiva + clienti con call bonus attive assegnate
    cb_client_ids = _call_bonus_client_ids_for_user(current_user.id)
    return (
        db.session.query(Cliente.cliente_id)
        .filter(
            or_(
                Cliente.nutrizionista_id == current_user.id,
                Cliente.coach_id == current_user.id,
                Cliente.psicologa_id == current_user.id,
                Cliente.consulente_alimentare_id == current_user.id,
                Cliente.health_manager_id == current_user.id,
                Cliente.nutrizionisti_multipli.any(User.id == current_user.id),
                Cliente.coaches_multipli.any(User.id == current_user.id),
                Cliente.psicologi_multipli.any(User.id == current_user.id),
                Cliente.consulenti_multipli.any(User.id == current_user.id),
                Cliente.cliente_id.in_(cb_client_ids),
                db.session.query(ClienteProfessionistaHistory.cliente_id)
                .filter(
                    ClienteProfessionistaHistory.cliente_id == Cliente.cliente_id,
                    ClienteProfessionistaHistory.user_id == current_user.id,
                    ClienteProfessionistaHistory.is_active == True,
                )
                .exists(),
            )
        )
    )

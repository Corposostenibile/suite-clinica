"""
blueprints/department/team_routes.py
=====================================

Route per la gestione dei Team all'interno dei dipartimenti.

Features:
- CRUD completo per team
- Assegnazione membri a team
- Gestione team leader
- API AJAX per operazioni rapide
"""

from __future__ import annotations

from http import HTTPStatus

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from corposostenibile.extensions import db
from corposostenibile.models import Department, Team, User
from . import dept_bp
from .forms import TeamForm


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ ACL Helpers                                                            ║
# ╚════════════════════════════════════════════════════════════════════════╝
def _require_admin() -> None:
    """Consente l'accesso solo agli admin, altrimenti 403."""
    if not (current_user.is_authenticated and current_user.is_admin):
        abort(HTTPStatus.FORBIDDEN)


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ TEAM LIST                                                              ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/<int:dept_id>/teams", methods=["GET"])
@login_required
def teams_list(dept_id: int):
    """
    Lista team del dipartimento con statistiche.

    Mostra:
    - Tutti i team del dipartimento
    - Numero membri per team
    - Team leader
    - Membri senza team assegnato
    """
    dept = Department.query.get_or_404(dept_id)

    # Statistiche
    stats = {
        "total_members": len(dept.all_members),
        "members_with_team": sum(1 for m in dept.all_members if m.team_id is not None),
        "members_without_team": len(dept.get_members_without_team()),
        "total_teams": dept.team_count,
    }

    return render_template(
        "department/teams/list.html",
        dept=dept,
        teams=dept.teams,
        members_without_team=dept.get_members_without_team(),
        stats=stats,
        can_manage=current_user.is_admin,
    )


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ TEAM CREATE                                                            ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/<int:dept_id>/teams/new", methods=["GET", "POST"])
@login_required
def team_create(dept_id: int):
    """Crea nuovo team nel dipartimento."""
    _require_admin()

    dept = Department.query.get_or_404(dept_id)
    form = TeamForm(department=dept)

    if form.validate_on_submit():
        # Verifica unicità nome team nel dipartimento
        existing = dept.get_team_by_name(form.name.data)
        if existing:
            flash(
                f"Esiste già un team con nome '{form.name.data}' "
                f"nel dipartimento {dept.name}.",
                "warning",
            )
            return render_template(
                "department/teams/form.html",
                form=form,
                dept=dept,
                mode="create",
            )

        # Crea team
        team = Team(
            name=form.name.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            department_id=dept.id,
            head_id=form.head_id.data if form.head_id.data != 0 else None,
            head_2_id=form.head_2_id.data if form.head_2_id.data != 0 else None,
        )

        try:
            db.session.add(team)
            db.session.commit()

            flash(
                f"Team '{team.name}' creato con successo nel dipartimento {dept.name}.",
                "success",
            )
            current_app.logger.info(
                f"[team] Team {team.id} '{team.name}' creato da user {current_user.id}"
            )

            return redirect(url_for("department.teams_list", dept_id=dept.id))

        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"[team] IntegrityError creating team: {e}")
            flash(
                "Errore: un team con questo nome esiste già nel dipartimento.",
                "danger",
            )

    return render_template(
        "department/teams/form.html", form=form, dept=dept, mode="create"
    )


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ TEAM EDIT                                                              ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/teams/<int:team_id>/edit", methods=["GET", "POST"])
@login_required
def team_edit(team_id: int):
    """Modifica team esistente."""
    _require_admin()

    team = Team.query.get_or_404(team_id)
    form = TeamForm(obj=team, department=team.department)

    if form.validate_on_submit():
        # Verifica unicità nome (se cambiato)
        if form.name.data.strip().lower() != team.name.lower():
            existing = team.department.get_team_by_name(form.name.data)
            if existing and existing.id != team.id:
                flash(
                    f"Esiste già un team con nome '{form.name.data}' "
                    f"nel dipartimento {team.department.name}.",
                    "warning",
                )
                return render_template(
                    "department/teams/form.html",
                    form=form,
                    dept=team.department,
                    team=team,
                    mode="edit",
                )

        # Aggiorna team
        team.name = form.name.data.strip()
        team.description = form.description.data.strip() if form.description.data else None
        team.head_id = form.head_id.data if form.head_id.data != 0 else None
        team.head_2_id = form.head_2_id.data if form.head_2_id.data != 0 else None

        try:
            db.session.commit()

            flash(f"Team '{team.name}' aggiornato con successo.", "success")
            current_app.logger.info(
                f"[team] Team {team.id} '{team.name}' aggiornato da user {current_user.id}"
            )

            return redirect(
                url_for("department.teams_list", dept_id=team.department_id)
            )

        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"[team] IntegrityError updating team: {e}")
            flash("Errore durante l'aggiornamento del team.", "danger")

    return render_template(
        "department/teams/form.html", form=form, dept=team.department, team=team, mode="edit"
    )


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ TEAM DELETE                                                            ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/teams/<int:team_id>/delete", methods=["POST"])
@login_required
def team_delete(team_id: int):
    """
    Elimina team (gli utenti rimangono nel dipartimento).

    IMPORTANT: Rimuove team_id da tutti i membri ma NON elimina gli utenti.
    Gli utenti rimangono nel dipartimento con department_id intatto.
    """
    _require_admin()

    team = Team.query.get_or_404(team_id)
    dept_id = team.department_id
    team_name = team.name
    member_count = team.member_count

    # Rimuovi team_id da tutti i membri (rimangono nel dipartimento)
    if member_count > 0:
        User.query.filter_by(team_id=team.id).update({"team_id": None})

    # Elimina il team
    db.session.delete(team)
    db.session.commit()

    flash(
        f"Team '{team_name}' eliminato. "
        f"{member_count} membri rimangono nel dipartimento senza team assegnato.",
        "info",
    )
    current_app.logger.info(
        f"[team] Team {team_id} '{team_name}' eliminato da user {current_user.id}"
    )

    return redirect(url_for("department.teams_list", dept_id=dept_id))


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ TEAM DETAIL                                                            ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/teams/<int:team_id>", methods=["GET"])
@login_required
def team_detail(team_id: int):
    """Dettaglio team con lista membri e statistiche."""
    team = Team.query.get_or_404(team_id)

    # Statistiche
    stats = {
        "member_count": team.member_count,
        "has_leader": team.head is not None,
        "created_at": team.created_at,
    }

    return render_template(
        "department/teams/detail.html",
        team=team,
        stats=stats,
        can_manage=current_user.is_admin,
    )


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ API: ASSIGN MEMBER TO TEAM                                            ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/teams/<int:team_id>/assign-member", methods=["POST"])
@login_required
def team_assign_member(team_id: int):
    """
    Assegna utente a team (via AJAX).

    Request JSON:
        {
            "user_id": int
        }

    Response JSON:
        {
            "success": true,
            "message": "User assigned successfully",
            "user": {
                "id": int,
                "full_name": str,
                "team_id": int
            }
        }
    """
    _require_admin()

    team = Team.query.get_or_404(team_id)
    data = request.get_json()

    if not data or "user_id" not in data:
        return jsonify({"error": "user_id mancante"}), HTTPStatus.BAD_REQUEST

    user_id = data.get("user_id")
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Utente non trovato"}), HTTPStatus.NOT_FOUND

    # Verifica che l'utente appartenga al dipartimento
    if user.department_id != team.department_id:
        return (
            jsonify(
                {
                    "error": f"L'utente non appartiene al dipartimento {team.department.name}"
                }
            ),
            HTTPStatus.BAD_REQUEST,
        )

    # Assegna team
    user.team_id = team.id
    db.session.commit()

    current_app.logger.info(
        f"[team] User {user.id} assegnato a team {team.id} da user {current_user.id}"
    )

    return jsonify(
        {
            "success": True,
            "message": f"{user.full_name} assegnato al team {team.name}",
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "team_id": user.team_id,
            },
        }
    )


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ API: REMOVE MEMBER FROM TEAM                                          ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/teams/<int:team_id>/remove-member/<int:user_id>", methods=["POST"])
@login_required
def team_remove_member(team_id: int, user_id: int):
    """
    Rimuove utente da team (rimane nel dipartimento).

    IMPORTANT: Rimuove solo team_id, department_id rimane intatto.

    Response JSON:
        {
            "success": true,
            "message": "User removed from team (remains in department)"
        }
    """
    _require_admin()

    team = Team.query.get_or_404(team_id)
    user = User.query.get_or_404(user_id)

    if user.team_id != team.id:
        return (
            jsonify({"error": "L'utente non è in questo team"}),
            HTTPStatus.BAD_REQUEST,
        )

    # Rimuovi da team (rimane nel dipartimento)
    user.team_id = None
    db.session.commit()

    current_app.logger.info(
        f"[team] User {user.id} rimosso da team {team.id} da user {current_user.id}"
    )

    return jsonify(
        {
            "success": True,
            "message": f"{user.full_name} rimosso dal team (rimane in {user.department.name})",
        }
    )


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ API: GET AVAILABLE MEMBERS (for team assignment)                      ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/teams/<int:team_id>/available-members", methods=["GET"])
@login_required
def team_available_members(team_id: int):
    """
    Ritorna lista membri del dipartimento che NON sono già in questo team.

    Used by: AJAX autocomplete per assegnare membri a team.

    Query params:
        - q: query string per filtrare per nome (optional)

    Response JSON:
        [
            {
                "id": int,
                "full_name": str,
                "current_team": str | null
            },
            ...
        ]
    """
    team = Team.query.get_or_404(team_id)
    query = request.args.get("q", "").strip()

    # DEBUG: Log info
    current_app.logger.info(f"[team] Getting available members for team {team.id} (dept {team.department_id})")

    # Prima prendi TUTTI i membri del dipartimento
    all_dept_members = User.query.filter(
        User.department_id == team.department_id,
        User.is_active == True
    ).all()

    current_app.logger.info(f"[team] Total active members in department: {len(all_dept_members)}")

    # Filtra quelli NON in questo team
    available_members = [
        user for user in all_dept_members
        if user.team_id != team.id
    ]

    current_app.logger.info(f"[team] Available members (not in this team): {len(available_members)}")

    # Filtra per nome se query fornita
    if query:
        available_members = [
            user for user in available_members
            if query.lower() in user.first_name.lower() or query.lower() in user.last_name.lower()
        ]

    # Ordina per nome
    available_members = sorted(available_members, key=lambda u: (u.first_name, u.last_name))

    results = [
        {
            "id": user.id,
            "full_name": user.full_name,
            "current_team": user.team.name if user.team else None,
        }
        for user in available_members
    ]

    current_app.logger.info(f"[team] Returning {len(results)} available members")

    return jsonify({"members": results})

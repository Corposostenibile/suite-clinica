from datetime import datetime, timedelta

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from corposostenibile.extensions import csrf, db
from corposostenibile.models import Cliente, Meeting, User

from . import loom_bp


@loom_bp.get("/health")
def health():
    """Health endpoint del blueprint Loom."""
    return jsonify({"success": True, "service": "loom", "status": "ok"})


@loom_bp.route("/api/meeting/loom", methods=["POST"])
@csrf.exempt
@login_required
def save_meeting_loom():
    """
    Salva link Loom per un evento GHL.
    Crea o aggiorna record Meeting locale associato all'evento GHL.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "message": "Dati non forniti"}), 400

        ghl_event_id = data.get("ghl_event_id")
        loom_link = data.get("loom_link")

        if not ghl_event_id:
            return jsonify({"success": False, "message": "ghl_event_id richiesto"}), 400

        if not loom_link:
            return jsonify({"success": False, "message": "loom_link richiesto"}), 400

        title = data.get("title", "Meeting GHL")
        start_time_str = data.get("start_time")
        end_time_str = data.get("end_time")
        cliente_id = data.get("cliente_id")

        meeting = Meeting.query.filter_by(ghl_event_id=ghl_event_id).first()

        if meeting:
            meeting.loom_link = loom_link
            current_app.logger.info(f"[Loom] Updated loom_link for meeting {meeting.id}")
        else:
            start_time = _parse_datetime_or_default(start_time_str, datetime.utcnow())
            end_time = _parse_datetime_or_default(
                end_time_str, start_time + timedelta(minutes=30)
            )

            meeting = Meeting(
                ghl_event_id=ghl_event_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                cliente_id=cliente_id if cliente_id else None,
                user_id=current_user.id,
                loom_link=loom_link,
                status="completed",
            )
            db.session.add(meeting)
            current_app.logger.info(f"[Loom] Created meeting for GHL event {ghl_event_id}")

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "meeting_id": meeting.id,
                "message": "Link Loom salvato con successo",
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[Loom] Error saving loom link: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@loom_bp.route("/api/meeting/loom/<ghl_event_id>", methods=["GET"])
@login_required
def get_meeting_loom(ghl_event_id):
    """Ottiene il link Loom per un evento GHL."""
    meeting = Meeting.query.filter_by(ghl_event_id=ghl_event_id).first()

    if meeting:
        return jsonify(
            {
                "success": True,
                "meeting_id": meeting.id,
                "loom_link": meeting.loom_link,
                "has_loom": bool(meeting.loom_link),
            }
        )

    return jsonify(
        {
            "success": True,
            "meeting_id": None,
            "loom_link": None,
            "has_loom": False,
        }
    )


@loom_bp.route("/api/meeting/<int:meeting_id>/loom", methods=["GET", "PUT"])
@login_required
def meeting_loom_by_meeting_id(meeting_id):
    """
    Recupera o aggiorna il campo loom_link di un meeting esistente.
    """
    meeting = Meeting.query.get_or_404(meeting_id)

    if not current_user.is_admin and meeting.user_id != current_user.id:
        return jsonify({"success": False, "message": "Non autorizzato"}), 403

    if request.method == "GET":
        return jsonify(
            {
                "success": True,
                "meeting_id": meeting.id,
                "loom_link": meeting.loom_link,
                "has_loom": bool(meeting.loom_link),
            }
        )

    try:
        data = request.get_json() or {}
        meeting.loom_link = data.get("loom_link")
        db.session.commit()
        return jsonify(
            {
                "success": True,
                "meeting_id": meeting.id,
                "loom_link": meeting.loom_link,
                "has_loom": bool(meeting.loom_link),
                "message": "Loom link aggiornato",
            }
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[Loom] Error updating meeting loom link: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@loom_bp.route("/api/library", methods=["GET"])
@login_required
def api_loom_library():
    """
    Libreria Loom in formato JSON.
    Replica la logica filtri della pagina calendar/loom-library.
    """
    query = Meeting.query.filter(Meeting.loom_link.isnot(None), Meeting.loom_link != "")

    if not current_user.is_admin:
        query = query.filter(Meeting.user_id == current_user.id)
    else:
        user_id_filter = request.args.get("user_id", type=int)
        if user_id_filter:
            query = query.filter(Meeting.user_id == user_id_filter)

    cliente_filter = request.args.get("cliente", "").strip()
    if cliente_filter:
        query = query.join(Cliente, Meeting.cliente_id == Cliente.cliente_id, isouter=True)
        query = query.filter(Cliente.nome_cognome.ilike(f"%{cliente_filter}%"))

    categoria_filter = request.args.get("categoria", "").strip()
    if categoria_filter:
        query = query.filter(Meeting.event_category == categoria_filter)

    date_from = request.args.get("date_from")
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Meeting.start_time >= from_date)
        except ValueError:
            pass

    date_to = request.args.get("date_to")
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Meeting.start_time < to_date)
        except ValueError:
            pass

    meetings = query.order_by(Meeting.start_time.desc()).all()

    payload = []
    for meeting in meetings:
        payload.append(
            {
                "id": meeting.id,
                "title": meeting.title,
                "loom_link": meeting.loom_link,
                "google_event_id": meeting.google_event_id,
                "ghl_event_id": meeting.ghl_event_id,
                "start_time": meeting.start_time.isoformat() if meeting.start_time else None,
                "end_time": meeting.end_time.isoformat() if meeting.end_time else None,
                "event_category": meeting.event_category,
                "status": meeting.status,
                "cliente_id": meeting.cliente_id,
                "cliente_name": meeting.cliente.nome_cognome if meeting.cliente else None,
                "user_id": meeting.user_id,
                "user_name": meeting.user.full_name if meeting.user else None,
            }
        )

    now = datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month_count = sum(
        1 for meeting in meetings if meeting.start_time and meeting.start_time >= first_of_month
    )

    users = []
    if current_user.is_admin:
        users = [
            {"id": u.id, "full_name": u.full_name}
            for u in User.query.filter(User.is_active == True)
            .order_by(User.first_name, User.last_name)
            .all()
        ]

    return jsonify(
        {
            "success": True,
            "count": len(payload),
            "this_month_count": this_month_count,
            "meetings": payload,
            "users": users,
        }
    )


def _parse_datetime_or_default(value, default_dt):
    if not value:
        return default_dt
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return default_dt

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_required

from corposostenibile.extensions import db, csrf
from corposostenibile.models import AppointmentSettingMessage, AppointmentSettingContact, AppointmentSettingFunnel

appointment_setting_api_bp = Blueprint(
    "appointment_setting_api",
    __name__,
    url_prefix="/api/appointment-setting",
)

csrf.exempt(appointment_setting_api_bp)


@appointment_setting_api_bp.route("/messages", methods=["GET"])
@login_required
def get_messages():
    """Return all stored monthly message stats."""
    records = AppointmentSettingMessage.query.order_by(
        AppointmentSettingMessage.anno,
        AppointmentSettingMessage.mese,
    ).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in records]})


@appointment_setting_api_bp.route("/messages", methods=["POST"])
@login_required
def save_messages():
    """
    Save CSV data for a given month/year.
    Expects JSON: { mese: str, anno: int, utenti: [{utente: str, messaggi_inviati: int}] }
    Upserts: if a record for the same utente+mese+anno exists, it gets updated.
    """
    data = request.get_json(force=True)
    mese = data.get("mese")
    anno = data.get("anno")
    utenti = data.get("utenti", [])

    if not mese or not anno or not utenti:
        return jsonify({"success": False, "error": "mese, anno e utenti sono obbligatori"}), 400

    saved = 0
    for entry in utenti:
        utente = entry.get("utente", "").strip()
        if not utente:
            continue

        messaggi = entry.get("messaggi_inviati", 0)
        contatti = entry.get("contatti_unici_chiusi", 0)
        conv_assegnate = entry.get("conversazioni_assegnate", 0)
        conv_chiuse = entry.get("conversazioni_chiuse", 0)

        existing = AppointmentSettingMessage.query.filter_by(
            utente=utente, mese=mese, anno=anno
        ).first()

        if existing:
            existing.messaggi_inviati = messaggi
            existing.contatti_unici_chiusi = contatti
            existing.conversazioni_assegnate = conv_assegnate
            existing.conversazioni_chiuse = conv_chiuse
        else:
            record = AppointmentSettingMessage(
                utente=utente,
                mese=mese,
                anno=anno,
                messaggi_inviati=messaggi,
                contatti_unici_chiusi=contatti,
                conversazioni_assegnate=conv_assegnate,
                conversazioni_chiuse=conv_chiuse,
            )
            db.session.add(record)
        saved += 1

    db.session.commit()
    return jsonify({"success": True, "saved": saved})


@appointment_setting_api_bp.route("/messages/<int:anno>/<string:mese>", methods=["DELETE"])
@login_required
def delete_month(anno, mese):
    """Delete all records for a given month/year."""
    deleted = AppointmentSettingMessage.query.filter_by(mese=mese, anno=anno).delete()
    db.session.commit()
    return jsonify({"success": True, "deleted": deleted})


# ─── Contacts endpoints ─────────────────────────────────────────────────────

@appointment_setting_api_bp.route("/contacts", methods=["GET"])
@login_required
def get_contacts():
    """Return all stored daily contact stats."""
    records = AppointmentSettingContact.query.order_by(
        AppointmentSettingContact.anno,
        AppointmentSettingContact.mese,
        AppointmentSettingContact.giorno,
    ).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in records]})


@appointment_setting_api_bp.route("/contacts", methods=["POST"])
@login_required
def save_contacts():
    """
    Save daily contacts CSV data.
    Expects JSON: { mese: str, anno: int, rows: [{giorno: int, utenti: {name: count, ...}}] }
    """
    data = request.get_json(force=True)
    mese = data.get("mese")
    anno = data.get("anno")
    rows = data.get("rows", [])

    if not mese or not anno or not rows:
        return jsonify({"success": False, "error": "mese, anno e rows sono obbligatori"}), 400

    saved = 0
    for row in rows:
        giorno = row.get("giorno")
        utenti = row.get("utenti", {})
        if not giorno:
            continue

        for utente, contatti in utenti.items():
            utente = utente.strip()
            if not utente:
                continue

            existing = AppointmentSettingContact.query.filter_by(
                utente=utente, giorno=giorno, mese=mese, anno=anno
            ).first()

            if existing:
                existing.contatti = contatti
            else:
                record = AppointmentSettingContact(
                    utente=utente,
                    giorno=giorno,
                    mese=mese,
                    anno=anno,
                    contatti=contatti,
                )
                db.session.add(record)
            saved += 1

    db.session.commit()
    return jsonify({"success": True, "saved": saved})


@appointment_setting_api_bp.route("/contacts/<int:anno>/<string:mese>", methods=["DELETE"])
@login_required
def delete_contacts_month(anno, mese):
    """Delete all contact records for a given month/year."""
    deleted = AppointmentSettingContact.query.filter_by(mese=mese, anno=anno).delete()
    db.session.commit()
    return jsonify({"success": True, "deleted": deleted})


# ─── Funnel endpoints ────────────────────────────────────────────────────────

@appointment_setting_api_bp.route("/funnel", methods=["GET"])
@login_required
def get_funnel():
    """Return all stored funnel data."""
    records = AppointmentSettingFunnel.query.order_by(
        AppointmentSettingFunnel.anno,
        AppointmentSettingFunnel.mese,
    ).all()
    return jsonify({"success": True, "data": [r.to_dict() for r in records]})


@appointment_setting_api_bp.route("/funnel", methods=["POST"])
@login_required
def save_funnel():
    """
    Save lifecycle journey breakdown CSV data.
    Expects JSON: { mese: str, anno: int, rows: [{fase, tasso_conversione, tempo_medio_fase, tasso_abbandono, cold, non_in_target, prenotato_non_in_target, under}] }
    """
    data = request.get_json(force=True)
    mese = data.get("mese")
    anno = data.get("anno")
    rows = data.get("rows", [])

    if not mese or not anno or not rows:
        return jsonify({"success": False, "error": "mese, anno e rows sono obbligatori"}), 400

    saved = 0
    for row in rows:
        fase = row.get("fase", "").strip()
        if not fase:
            continue

        existing = AppointmentSettingFunnel.query.filter_by(
            fase=fase, mese=mese, anno=anno
        ).first()

        values = {
            "tasso_conversione": row.get("tasso_conversione", 0),
            "tempo_medio_fase": row.get("tempo_medio_fase", 0),
            "tasso_abbandono": row.get("tasso_abbandono", 0),
            "cold": row.get("cold", 0),
            "non_in_target": row.get("non_in_target", 0),
            "prenotato_non_in_target": row.get("prenotato_non_in_target", 0),
            "under": row.get("under", 0),
        }

        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
        else:
            record = AppointmentSettingFunnel(
                fase=fase, mese=mese, anno=anno, **values
            )
            db.session.add(record)
        saved += 1

    db.session.commit()
    return jsonify({"success": True, "saved": saved})


@appointment_setting_api_bp.route("/funnel/<int:anno>/<string:mese>", methods=["DELETE"])
@login_required
def delete_funnel_month(anno, mese):
    """Delete all funnel records for a given month/year."""
    deleted = AppointmentSettingFunnel.query.filter_by(mese=mese, anno=anno).delete()
    db.session.commit()
    return jsonify({"success": True, "deleted": deleted})

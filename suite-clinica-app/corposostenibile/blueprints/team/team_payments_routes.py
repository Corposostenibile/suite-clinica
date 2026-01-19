"""
Routes per la gestione dei Pagamenti Team
==========================================

Gestione fatture collaboratori con approvazione.
"""
from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from pathlib import Path
import os
import mimetypes

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    send_file,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from corposostenibile.extensions import db, csrf
from corposostenibile.models import User, TeamPayment, TeamPaymentStatusEnum
from . import team_bp


# ════════════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════════════

def _require_admin():
    """Verifica che l'utente sia admin."""
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(HTTPStatus.FORBIDDEN)


def _get_upload_base_path() -> Path:
    """Ritorna il path base per gli upload."""
    base_upload = Path(current_app.config.get("UPLOAD_FOLDER", "uploads"))
    if not base_upload.is_absolute():
        base_upload = Path(current_app.root_path).parent / base_upload
    base_upload.mkdir(parents=True, exist_ok=True)
    return base_upload


def _upload_dir(sub: str) -> Path:
    """Return absolute upload dir, creating it if missing."""
    base_upload = _get_upload_base_path()
    folder = base_upload / sub
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _save_fattura(file, user_id: int) -> tuple[str, str] | tuple[None, None]:
    """Salva il PDF della fattura e ritorna (path, filename)."""
    if not file or not file.filename:
        return None, None

    # Verifica estensione
    ext = os.path.splitext(file.filename)[1].lower()
    if ext != '.pdf':
        flash("La fattura deve essere un file PDF", "warning")
        return None, None

    try:
        # Nome file univoco
        filename = secure_filename(file.filename)
        timestamp = int(datetime.utcnow().timestamp())
        unique_filename = f"fattura_user{user_id}_{timestamp}{ext}"

        # Salva
        fatture_dir = _upload_dir("team_fatture")
        dst = fatture_dir / unique_filename
        file.save(str(dst))

        # Path relativo
        base_upload = _get_upload_base_path()
        relative_path = dst.relative_to(base_upload)

        return str(relative_path), filename

    except Exception as e:
        current_app.logger.error(f"Errore salvataggio fattura: {e}")
        return None, None


# ════════════════════════════════════════════════════════════════════════
#  Pannello Approvazione Pagamenti Team
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/pagamenti-team", methods=["GET"])
@login_required
def pagamenti_team_approvazione():
    """Pagina di gestione approvazione pagamenti team."""
    _require_admin()

    # Query tutti i pagamenti
    pagamenti = TeamPayment.query.order_by(
        TeamPayment.data_emissione.desc()
    ).all()

    # Lista utenti per il form di inserimento
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()

    return render_template(
        "team/pagamenti_team_approvazione.html",
        pagamenti=pagamenti,
        users=users,
        TeamPaymentStatusEnum=TeamPaymentStatusEnum,
    )


# ════════════════════════════════════════════════════════════════════════
#  CRUD Pagamenti Team
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/pagamenti-team/nuovo", methods=["POST"])
@login_required
def pagamenti_team_nuovo():
    """Crea nuovo pagamento team."""
    _require_admin()

    try:
        user_id = request.form.get("user_id", type=int)
        data_emissione = request.form.get("data_emissione")
        totale_fisso = request.form.get("totale_fisso", type=float, default=0)
        totale_bonus = request.form.get("totale_bonus", type=float, default=0)
        numero_fattura = request.form.get("numero_fattura", "").strip()
        note = request.form.get("note", "").strip()

        if not user_id or not data_emissione:
            flash("Membro team e data emissione sono obbligatori", "warning")
            return redirect(url_for("team.pagamenti_team_approvazione"))

        # Verifica user esiste
        user = User.query.get(user_id)
        if not user:
            flash("Membro team non trovato", "danger")
            return redirect(url_for("team.pagamenti_team_approvazione"))

        # Parse data
        try:
            data_emissione_parsed = datetime.strptime(data_emissione, "%Y-%m-%d").date()
        except ValueError:
            flash("Formato data non valido", "warning")
            return redirect(url_for("team.pagamenti_team_approvazione"))

        # Salva fattura PDF se presente
        fattura_path = None
        fattura_filename = None
        if "fattura_pdf" in request.files:
            fattura_file = request.files["fattura_pdf"]
            if fattura_file and fattura_file.filename:
                fattura_path, fattura_filename = _save_fattura(fattura_file, user_id)

        # Crea pagamento
        pagamento = TeamPayment(
            user_id=user_id,
            data_emissione=data_emissione_parsed,
            totale_fisso=totale_fisso,
            totale_bonus=totale_bonus,
            numero_fattura=numero_fattura or None,
            note=note or None,
            fattura_path=fattura_path,
            fattura_filename=fattura_filename,
            stato=TeamPaymentStatusEnum.da_valutare,
            created_by_id=current_user.id,
        )

        db.session.add(pagamento)
        db.session.commit()

        flash(f"Pagamento per {user.full_name} creato con successo!", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore creazione pagamento team: {e}")
        flash(f"Errore nella creazione: {str(e)}", "danger")

    return redirect(url_for("team.pagamenti_team_approvazione"))


@team_bp.route("/pagamenti-team/<int:pagamento_id>/modifica", methods=["POST"])
@login_required
def pagamenti_team_modifica(pagamento_id: int):
    """Modifica pagamento team esistente."""
    _require_admin()

    pagamento = TeamPayment.query.get_or_404(pagamento_id)

    # Non permettere modifica se già approvato/rifiutato
    if pagamento.stato != TeamPaymentStatusEnum.da_valutare:
        flash("Non puoi modificare un pagamento già processato", "warning")
        return redirect(url_for("team.pagamenti_team_approvazione"))

    try:
        pagamento.totale_fisso = request.form.get("totale_fisso", type=float, default=0)
        pagamento.totale_bonus = request.form.get("totale_bonus", type=float, default=0)
        pagamento.numero_fattura = request.form.get("numero_fattura", "").strip() or None
        pagamento.note = request.form.get("note", "").strip() or None

        # Data emissione
        data_emissione = request.form.get("data_emissione")
        if data_emissione:
            pagamento.data_emissione = datetime.strptime(data_emissione, "%Y-%m-%d").date()

        # Nuova fattura PDF se caricata
        if "fattura_pdf" in request.files:
            fattura_file = request.files["fattura_pdf"]
            if fattura_file and fattura_file.filename:
                fattura_path, fattura_filename = _save_fattura(fattura_file, pagamento.user_id)
                if fattura_path:
                    pagamento.fattura_path = fattura_path
                    pagamento.fattura_filename = fattura_filename

        db.session.commit()
        flash("Pagamento aggiornato con successo!", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore modifica pagamento team: {e}")
        flash(f"Errore nella modifica: {str(e)}", "danger")

    return redirect(url_for("team.pagamenti_team_approvazione"))


@team_bp.route("/pagamenti-team/<int:pagamento_id>/elimina", methods=["POST"])
@login_required
@csrf.exempt
def pagamenti_team_elimina(pagamento_id: int):
    """Elimina pagamento team."""
    _require_admin()

    pagamento = TeamPayment.query.get_or_404(pagamento_id)

    try:
        # Elimina file fattura se esiste
        if pagamento.fattura_path:
            try:
                base_upload = _get_upload_base_path()
                file_path = base_upload / pagamento.fattura_path
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                current_app.logger.warning(f"Errore eliminazione file fattura: {e}")

        db.session.delete(pagamento)
        db.session.commit()

        return jsonify({"success": True, "message": "Pagamento eliminato"})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore eliminazione pagamento team: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ════════════════════════════════════════════════════════════════════════
#  API Approvazione/Rifiuto
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/api/pagamenti-team/<int:pagamento_id>/approva", methods=["POST"])
@login_required
@csrf.exempt
def api_pagamenti_team_approva(pagamento_id: int):
    """Approva un pagamento team."""
    _require_admin()

    pagamento = TeamPayment.query.get_or_404(pagamento_id)

    if pagamento.stato != TeamPaymentStatusEnum.da_valutare:
        return jsonify({
            "success": False,
            "message": "Pagamento già processato"
        }), 400

    try:
        data = request.get_json() or {}

        pagamento.stato = TeamPaymentStatusEnum.approvato
        pagamento.approvato_da_id = current_user.id
        pagamento.data_approvazione = datetime.utcnow()
        pagamento.note_approvazione = data.get("note", "")

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Pagamento approvato"
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore approvazione pagamento team: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@team_bp.route("/api/pagamenti-team/<int:pagamento_id>/rifiuta", methods=["POST"])
@login_required
@csrf.exempt
def api_pagamenti_team_rifiuta(pagamento_id: int):
    """Rifiuta un pagamento team."""
    _require_admin()

    pagamento = TeamPayment.query.get_or_404(pagamento_id)

    if pagamento.stato != TeamPaymentStatusEnum.da_valutare:
        return jsonify({
            "success": False,
            "message": "Pagamento già processato"
        }), 400

    try:
        data = request.get_json() or {}

        pagamento.stato = TeamPaymentStatusEnum.rifiutato
        pagamento.approvato_da_id = current_user.id
        pagamento.data_approvazione = datetime.utcnow()
        pagamento.note_approvazione = data.get("note", "")

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Pagamento rifiutato"
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore rifiuto pagamento team: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ════════════════════════════════════════════════════════════════════════
#  Download Fattura
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/pagamenti-team/<int:pagamento_id>/fattura")
@login_required
def pagamenti_team_download_fattura(pagamento_id: int):
    """Download del PDF fattura."""
    _require_admin()

    pagamento = TeamPayment.query.get_or_404(pagamento_id)

    if not pagamento.fattura_path:
        abort(HTTPStatus.NOT_FOUND)

    try:
        base_upload = _get_upload_base_path()
        file_path = base_upload / pagamento.fattura_path

        if not file_path.exists():
            abort(HTTPStatus.NOT_FOUND)

        return send_file(
            file_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=pagamento.fattura_filename or f"fattura_{pagamento_id}.pdf"
        )

    except Exception as e:
        current_app.logger.error(f"Errore download fattura: {e}")
        abort(HTTPStatus.NOT_FOUND)

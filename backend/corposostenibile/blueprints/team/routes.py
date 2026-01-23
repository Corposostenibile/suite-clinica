"""
team.routes
===========

CRUD completo + dettaglio degli utenti interni
con upload di contratto (PDF) e certificazioni (PDF / immagini).

- elenco paginato
- dettaglio read-only
- create / edit con caricamento file
- toggle attivo / disattivo
- gestione nuovi campi (lingue, HR notes, orario, PDP, data nascita, account)
"""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Any, List
import os
import json
import mimetypes

from flask import (
    abort,
    current_app,
    flash,
    send_file,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    send_from_directory,
    send_file,
)
from flask_login import current_user, login_required
from corposostenibile.extensions import csrf
from sqlalchemy import select, func, text, and_, or_, extract, distinct
from werkzeug.datastructures import FileStorage
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, time, date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal


from corposostenibile.extensions import db
from corposostenibile.models import (
    Certification, User, Department, Team,
    LeaveRequest, LeavePolicy, ItalianHoliday,
    LeaveTypeEnum, LeaveStatusEnum,
    Cliente, StatoClienteEnum
)
from . import team_bp
from .forms import (
    ALLOWED_CERT_MIMETYPES,
    ALLOWED_CONTRACT_MIMETYPES,
    ALLOWED_AVATAR_MIMETYPES,
    UserForm,
    LeavePolicyForm,
    LeaveRequestForm,
    HolidayForm,
)
from .leave_service import LeaveService
from .leave_notifications import LeaveNotificationService

# ════════════════════════════════════════════════════════════════════════
#  ACL helper
# ════════════════════════════════════════════════════════════════════════

def _require_admin() -> None:
    is_hr = current_user.department and current_user.department.id == 17
    if not (current_user.is_authenticated and (current_user.is_admin or is_hr)):
        abort(HTTPStatus.FORBIDDEN)


def _require_assignment_permission() -> None:
    """
    Verifica permessi per gestione assegnazioni AI.
    Permette: Admin, CCO, Head dipartimento Coach/Psicologia, Head e Team Leader dipartimento Nutrizione,
    Utente ID 35 per Psicologia
    """
    if not current_user.is_authenticated:
        abort(HTTPStatus.FORBIDDEN)

    if current_user.is_admin:
        return

    # Utente specifico con accesso gestione Psicologia (ID 35)
    if current_user.id == 35:
        return

    if current_user.department:
        # CCO ha accesso completo
        if current_user.department.name == 'CCO':
            return

        # Head dei dipartimenti Coach, Psicologia
        if current_user.department.name in ['Coach', 'Psicologia']:
            if current_user.department.head_id == current_user.id:
                return

        # Per Nutrizione: Head dipartimento + Team Leader
        if current_user.department.name in ['Nutrizione', 'Nutrizione 2']:
            # Head dipartimento
            if current_user.department.head_id == current_user.id:
                return
            # Team Leader (head di un team nel dipartimento Nutrizione)
            from corposostenibile.models import Team
            is_team_leader = Team.query.filter_by(head_id=current_user.id).first() is not None
            if is_team_leader:
                return

    abort(HTTPStatus.FORBIDDEN)


# ════════════════════════════════════════════════════════════════════════
#  Upload utility - VERSIONE FUNZIONANTE
# ════════════════════════════════════════════════════════════════════════

def _get_upload_base_path() -> Path:
    """Ritorna il path base per gli upload, creandolo se necessario."""
    base_upload = Path(current_app.config.get("UPLOAD_FOLDER", "uploads"))
    
    if not base_upload.is_absolute():
        # IMPORTANTE: current_app.root_path punta a /home/devops/corposostenibile-suite/corposostenibile
        # Dobbiamo salire di un livello con .parent per arrivare a /home/devops/corposostenibile-suite
        base_upload = Path(current_app.root_path).parent / base_upload
    
    # Crea la directory se non esiste
    base_upload.mkdir(parents=True, exist_ok=True)
    
    return base_upload

def _upload_dir(sub: str) -> Path:
    """Return absolute upload dir, creating it if missing."""
    base_upload = _get_upload_base_path()
    folder = base_upload / sub
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _unique_path(folder: Path, filename: str) -> Path:
    """Genera un path univoco per evitare sovrascritture."""
    filename = secure_filename(filename)
    if not filename:
        filename = f"file_{datetime.utcnow().timestamp()}.bin"
    
    # Preserva l'estensione originale
    name, ext = os.path.splitext(filename)
    if not name:
        name = "file"
    
    dst = folder / filename
    idx = 1
    while dst.exists():
        dst = folder / f"{name}-{idx}{ext}"
        idx += 1
    return dst


def _validate_file(fs: FileStorage, allowed_types: set[str], file_type: str) -> bool:
    """Valida il file upload."""
    if not fs or not fs.filename:
        current_app.logger.warning(f"File vuoto o senza nome per {file_type}")
        return False
    
    # Verifica estensione
    ext = os.path.splitext(fs.filename)[1].lower()
    
    # Log per debug
    current_app.logger.info(f"Validating {file_type}: filename={fs.filename}, mimetype={fs.mimetype}, ext={ext}")
    
    # Per PDF, verifica sia mimetype che estensione
    if file_type == "contract":
        if ext != '.pdf':
            flash("Il contratto deve essere un file PDF", "warning")
            return False
        # Accetta vari mimetype per PDF dato che i browser possono inviarli diversamente
        valid_pdf_mimetypes = {
            'application/pdf', 
            'application/x-pdf', 
            'application/acrobat',
            'applications/vnd.pdf',
            'text/pdf',
            'text/x-pdf'
        }
        if fs.mimetype and fs.mimetype not in valid_pdf_mimetypes and fs.mimetype != 'application/octet-stream':
            current_app.logger.warning(f"Mimetype PDF non standard: {fs.mimetype}")
    
    if file_type == "certification":
        if ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
            flash("Le certificazioni devono essere PDF o immagini (JPG/PNG)", "warning")
            return False
    
    if file_type == "avatar":
        if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
            flash("L'avatar deve essere un'immagine (JPG/PNG/WebP)", "warning")
            return False
    
    # Verifica dimensione file
    fs.seek(0, 2)  # Vai alla fine del file
    file_size = fs.tell()
    fs.seek(0)  # Torna all'inizio
    
    max_size = current_app.config.get('UPLOAD_SIZE_LIMITS', {}).get(file_type, 10 * 1024 * 1024)
    if file_size > max_size:
        flash(f"Il file è troppo grande. Massimo {max_size // (1024*1024)}MB", "warning")
        return False
    
    return True


def _save_cert_file(fs: FileStorage) -> Certification | None:
    """Salva un file di certificazione e crea il record nel DB."""
    if not _validate_file(fs, ALLOWED_CERT_MIMETYPES, "certification"):
        return None
    
    try:
        # Salva il file
        dst = _unique_path(_upload_dir("certifications"), fs.filename)
        fs.save(str(dst))
        
        current_app.logger.info(f"Certificazione salvata: {dst}")
        
        # Path relativo dalla cartella uploads
        base_upload = _get_upload_base_path()
        relative_path = dst.relative_to(base_upload)
        
        # Determina il content type corretto
        content_type = fs.mimetype or mimetypes.guess_type(str(dst))[0] or 'application/octet-stream'
        
        # Crea record certificazione
        cert = Certification(
            title=dst.stem,
            file_path=str(relative_path),
            content_type=content_type,
        )
        db.session.add(cert)
        
        return cert
        
    except Exception as e:
        current_app.logger.error(f"Errore salvataggio certificazione: {e}")
        flash("Errore durante il salvataggio della certificazione", "danger")
        return None


def _save_contract(fs: FileStorage) -> str | None:
    """Salva un contratto e ritorna il path relativo."""
    if not _validate_file(fs, ALLOWED_CONTRACT_MIMETYPES, "contract"):
        return None
    
    try:
        # Salva il file
        dst = _unique_path(_upload_dir("contracts"), fs.filename)
        fs.save(str(dst))
        
        current_app.logger.info(f"Contratto salvato: {dst}")
        
        # Path relativo dalla cartella uploads
        base_upload = _get_upload_base_path()
        relative_path = dst.relative_to(base_upload)
        
        return str(relative_path)
        
    except Exception as e:
        current_app.logger.error(f"Errore salvataggio contratto: {e}")
        flash("Errore durante il salvataggio del contratto", "danger")
        return None


def _save_avatar(fs: FileStorage, user_id: int) -> str | None:
    """Salva l'avatar dell'utente e ritorna il path relativo."""
    if not _validate_file(fs, ALLOWED_AVATAR_MIMETYPES, "avatar"):
        return None
    
    try:
        # Nome file univoco basato su user_id
        ext = Path(fs.filename).suffix.lower()
        filename = f"user_{user_id}_{int(datetime.utcnow().timestamp())}{ext}"
        
        # Directory avatars
        avatar_dir = _upload_dir("avatars")
        dst = avatar_dir / filename
        
        # Log dettagliato
        current_app.logger.info(f"Saving avatar to: {dst}")
        current_app.logger.info(f"Directory exists: {avatar_dir.exists()}")
        current_app.logger.info(f"Directory writable: {os.access(avatar_dir, os.W_OK)}")
        
        # Salva il file
        fs.save(str(dst))
        
        # Verifica che il file sia stato salvato
        if not dst.exists():
            current_app.logger.error(f"File not saved at {dst}")
            return None
        
        current_app.logger.info(f"Avatar saved successfully: {dst}")
        current_app.logger.info(f"File size: {dst.stat().st_size} bytes")
        
        # Path relativo dalla cartella uploads
        base_upload = _get_upload_base_path()
        relative_path = dst.relative_to(base_upload)
        
        current_app.logger.info(f"Relative path: {relative_path}")
        
        return str(relative_path)
        
    except Exception as e:
        current_app.logger.error(f"Errore salvataggio avatar: {e}", exc_info=True)
        flash("Errore durante il salvataggio dell'avatar", "danger")
        return None


def _delete_old_avatar(user: User) -> None:
    """Elimina il vecchio avatar se esiste."""
    if user.avatar_path:
        try:
            base_upload = _get_upload_base_path()
            old_path = base_upload / user.avatar_path
            if old_path.exists():
                old_path.unlink()
                current_app.logger.info(f"Avatar eliminato: {old_path}")
        except Exception as e:
            current_app.logger.warning(f"Errore eliminazione avatar: {e}")


# ════════════════════════════════════════════════════════════════════════
#  API Routes for Profile Management
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/<int:user_id>/update", methods=["POST"])
@login_required
@csrf.exempt
def user_update(user_id: int):
    """Update user profile data via AJAX."""
    user = db.session.get(User, user_id) or abort(404)
    
    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_finance = current_user.department and current_user.department.name == "Finance"
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_finance or is_self
    
    if not can_edit:
        return jsonify({"success": False, "message": "Permesso negato"}), 403
    
    try:
        data = request.get_json()
        form_id = data.get('form_id')
        form_data = data.get('data', {})
        
        # Update based on form
        if form_id == 'form-anagrafica':
            user.first_name = form_data.get('first_name', user.first_name)
            user.last_name = form_data.get('last_name', user.last_name)
            user.email = form_data.get('email', user.email)
            
            # Convert empty strings to None for optional fields
            mobile = form_data.get('mobile', '').strip()
            user.mobile = mobile if mobile else None

            job_title = form_data.get('job_title', '').strip()
            user.job_title = job_title if job_title else None

            citta = form_data.get('citta', '').strip()
            user.citta = citta if citta else None

            indirizzo = form_data.get('indirizzo', '').strip()
            user.indirizzo = indirizzo if indirizzo else None
            
            # Parse birth date
            if form_data.get('birth_date'):
                try:
                    user.birth_date = datetime.strptime(form_data['birth_date'], '%Y-%m-%d').date()
                except:
                    pass
            
            # Documents - Convert empty strings to None for unique fields
            codice_fiscale = form_data.get('codice_fiscale', '').strip()
            user.codice_fiscale = codice_fiscale if codice_fiscale else None
            
            partita_iva = form_data.get('partita_iva', '').strip()
            user.partita_iva = partita_iva if partita_iva else None
            
            documento_tipo = form_data.get('documento_tipo', '').strip()
            user.documento_tipo = documento_tipo if documento_tipo else None
            
            documento_numero = form_data.get('documento_numero', '').strip()
            user.documento_numero = documento_numero if documento_numero else None
            
            # Parse document expiry
            if form_data.get('documento_scadenza'):
                try:
                    user.documento_scadenza = datetime.strptime(form_data['documento_scadenza'], '%Y-%m-%d').date()
                except:
                    pass
            
            # Handle department_id (only admin can change)
            if current_user.is_admin and 'department_id' in form_data:
                dept_id = form_data.get('department_id')
                user.department_id = int(dept_id) if dept_id else None
            
            # Handle languages array
            if 'languages' in form_data:
                import json
                try:
                    languages = json.loads(form_data['languages']) if isinstance(form_data['languages'], str) else form_data['languages']
                    user.languages = languages if isinstance(languages, list) else []
                except:
                    user.languages = []
        
        elif form_id == 'form-formazione':
            # Education updates
            user.education_high_school = {
                'type': form_data.get('education_high_school_type'),
                'institute': form_data.get('education_high_school_institute'),
                'year': form_data.get('education_high_school_year'),
                'grade': form_data.get('education_high_school_grade')
            }
        
        elif form_id == 'form-contratto':
            # Tipo contratto sempre forzato a partita_iva
            user.contract_type = 'partita_iva'
            if form_data.get('hired_at'):
                try:
                    user.hired_at = datetime.strptime(form_data['hired_at'], '%Y-%m-%d')
                except:
                    pass
            
            # Department
            if form_data.get('department_id'):
                user.department_id = int(form_data['department_id'])
            
            # Work schedule - orario e giorni lavorativi
            if not user.work_schedule:
                user.work_schedule = {}
            
            # Tipo orario (solo full-time o part-time)
            if form_data.get('work_schedule_type'):
                user.work_schedule['type'] = form_data['work_schedule_type']
            
            # Orari
            if form_data.get('work_schedule_from'):
                user.work_schedule['hours_from'] = form_data['work_schedule_from']
            if form_data.get('work_schedule_to'):
                user.work_schedule['hours_to'] = form_data['work_schedule_to']
            
            # Giorni lavorativi (array di giorni selezionati)
            if 'workdays' in form_data:
                workdays = form_data.get('workdays', [])
                user.work_schedule['workdays'] = workdays if isinstance(workdays, list) else []
            
            # Mark field as modified for SQLAlchemy
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(user, 'work_schedule')
        
        elif form_id == 'form-retribuzione' and (current_user.is_admin or is_hr or is_finance):
            # Salary updates (restricted)
            if form_data.get('stipendio_mensile_lordo'):
                user.stipendio_mensile_lordo = Decimal(form_data['stipendio_mensile_lordo'])
            if form_data.get('ral_annua'):
                user.ral_annua = Decimal(form_data['ral_annua'])
        
        elif form_id == 'form-credenziali' and (current_user.is_admin or is_self):
            # Password update (admin or self only)
            if form_data.get('new_password'):
                user.set_password(form_data['new_password'])

        elif form_id == 'form-ordine':
            # Ordine professionale updates
            current_app.logger.info(f"[ORDINE] Ricevuto form_data: {form_data}")

            ordine_name = form_data.get('ordine_name', '').strip()
            user.ordine_name = ordine_name if ordine_name else None
            current_app.logger.info(f"[ORDINE] Impostato ordine_name: {user.ordine_name}")

            ordine_provincia = form_data.get('ordine_provincia', '').strip()
            user.ordine_provincia = ordine_provincia if ordine_provincia else None
            current_app.logger.info(f"[ORDINE] Impostato ordine_provincia: {user.ordine_provincia}")

            ordine_numero_iscrizione = form_data.get('ordine_numero_iscrizione', '').strip()
            user.ordine_numero_iscrizione = ordine_numero_iscrizione if ordine_numero_iscrizione else None
            current_app.logger.info(f"[ORDINE] Impostato ordine_numero_iscrizione: {user.ordine_numero_iscrizione}")

            # Parse iscrizione date
            if form_data.get('ordine_iscrizione_date'):
                try:
                    user.ordine_iscrizione_date = datetime.strptime(form_data['ordine_iscrizione_date'], '%Y-%m-%d').date()
                    current_app.logger.info(f"[ORDINE] Impostato ordine_iscrizione_date: {user.ordine_iscrizione_date}")
                except Exception as e:
                    current_app.logger.error(f"[ORDINE] Errore parsing data: {e}")
                    user.ordine_iscrizione_date = None
            else:
                user.ordine_iscrizione_date = None

            current_app.logger.info(f"[ORDINE] User {user.id} - Dati ordine aggiornati prima del commit")

        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Dati aggiornati con successo"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user {user_id}: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@team_bp.route("/<int:user_id>/education", methods=["POST"])
@login_required
@csrf.exempt
def user_update_education(user_id: int):
    """Update education data (degrees, masters, courses, certifications)."""
    user = db.session.get(User, user_id) or abort(404)
    
    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_self
    
    if not can_edit:
        return jsonify({"success": False, "message": "Permesso negato"}), 403
    
    try:
        data = request.get_json()
        field_type = data.get('type')
        action = data.get('action')
        item_data = data.get('data')
        
        # Map field types to User model attributes
        field_map = {
            'high_school': 'education_high_school',
            'degrees': 'education_degrees',
            'masters': 'education_masters',
            'courses': 'education_courses',
            'certifications': 'education_certifications',
            'phd': 'education_phd'
        }
        
        if field_type not in field_map:
            return jsonify({"success": False, "message": "Tipo non valido"}), 400
        
        field_name = field_map[field_type]
        
        # Handle mark_not_owned action for all types
        if action == 'mark_not_owned':
            if field_type in ['high_school', 'phd']:
                setattr(user, field_name, {'not_owned': True})
            else:
                setattr(user, field_name, [{'not_owned': True}])
        # Handle different field types - some are lists, some are single objects
        elif field_type in ['high_school', 'phd']:
            # Single object fields
            if action == 'add' or action == 'edit':
                setattr(user, field_name, item_data)
            elif action == 'remove':
                setattr(user, field_name, {})
        else:
            # List fields
            current_list = getattr(user, field_name) or []

            if action == 'add':
                current_list.append(item_data)
            elif action == 'edit':
                # Check if item_data is a dictionary with 'index' and 'data' keys
                if isinstance(item_data, dict) and 'index' in item_data and 'data' in item_data:
                    # This is an edit with index (for list items)
                    index = item_data.get('index')
                    new_data = item_data.get('data')
                    if isinstance(index, int) and 0 <= index < len(current_list):
                        current_list[index] = new_data
                else:
                    # This shouldn't happen for list fields in edit mode
                    # but handle it just in case
                    pass
            elif action == 'remove':
                if isinstance(item_data, int) and 0 <= item_data < len(current_list):
                    current_list.pop(item_data)

            setattr(user, field_name, current_list)
        
        # Mark the field as modified for SQLAlchemy to track the change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, field_name)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Formazione aggiornata con successo"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating education for user {user_id}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@team_bp.route("/<int:user_id>/experience", methods=["POST"])
@login_required
def user_update_experience(user_id: int):
    """Update experience data (work experiences, referees)."""
    user = db.session.get(User, user_id) or abort(404)
    
    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_self
    
    if not can_edit:
        return jsonify({"success": False, "message": "Permesso negato"}), 403
    
    try:
        data = request.get_json()
        field_type = data.get('type')
        action = data.get('action')
        item_data = data.get('data')
        
        # Map field types to User model attributes
        field_map = {
            'experiences': 'work_experiences',
            'referees': 'referee_contacts'
        }
        
        if field_type not in field_map:
            return jsonify({"success": False, "message": "Tipo non valido"}), 400
        
        field_name = field_map[field_type]
        current_list = getattr(user, field_name) or []
        
        if action == 'add':
            current_list.append(item_data)
        elif action == 'edit':
            # For edit, item_data should contain index and data
            if isinstance(item_data, dict) and 'index' in item_data and 'data' in item_data:
                index = item_data['index']
                if isinstance(index, int) and 0 <= index < len(current_list):
                    current_list[index] = item_data['data']
        elif action == 'remove':
            if isinstance(item_data, int) and 0 <= item_data < len(current_list):
                current_list.pop(item_data)
        
        setattr(user, field_name, current_list)
        
        # Mark the field as modified for SQLAlchemy to track the change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(user, field_name)
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Esperienza aggiornata con successo"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating experience for user {user_id}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@team_bp.route("/<int:user_id>/update-field", methods=["POST"])
@login_required
def user_update_field(user_id: int):
    """Update single field via inline editing."""
    user = db.session.get(User, user_id) or abort(404)

    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_finance = current_user.department and current_user.department.name == "Finance"
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_finance or is_self

    if not can_edit:
        return jsonify({"success": False, "message": "Permesso negato"}), 403

    try:
        data = request.get_json()
        field = data.get('field')
        value = data.get('value')

        # Special permission check for AI assignment notes (admin only)
        if field == 'assignment_ai_notes' and not current_user.is_admin:
            return jsonify({"success": False, "message": "Solo gli amministratori possono modificare le note AI"}), 403

        # Handle assignment_ai_notes: parse JSON string if needed
        if field == 'assignment_ai_notes' and isinstance(value, str):
            try:
                import json as json_lib
                value = json_lib.loads(value)
            except (json_lib.JSONDecodeError, TypeError):
                # If not valid JSON, keep as dict with specializzazione field
                value = {"specializzazione": value} if value else {}

        field_data = data.get('data')  # For complex fields with multiple values
        
        # Handle special research fields
        if field in ['clinical_research', 'scientific_publications', 'teaching_experience']:
            if field == 'clinical_research':
                user.has_clinical_research = field_data.get('has_clinical_research', False)
                user.clinical_research_details = field_data.get('clinical_research_details', '')
            elif field == 'scientific_publications':
                user.has_scientific_publications = field_data.get('has_scientific_publications', False)
                user.scientific_publications_details = field_data.get('scientific_publications_details', '')
            elif field == 'teaching_experience':
                user.has_teaching_experience = field_data.get('has_teaching_experience', False)
                user.teaching_experience_details = field_data.get('teaching_experience_details', '')
            
            db.session.commit()
            return jsonify({"success": True, "message": "Campo aggiornato con successo"})
        
        # Handle nested fields
        elif '.' in field:
            parts = field.split('.')
            if parts[0] == 'education_high_school':
                if not user.education_high_school:
                    user.education_high_school = {}
                user.education_high_school[parts[1]] = value
            elif parts[0] == 'work_schedule':
                if not user.work_schedule:
                    user.work_schedule = {}
                user.work_schedule[parts[1]] = value
            elif parts[0] == 'development_plan':
                if not user.development_plan:
                    user.development_plan = {}
                user.development_plan[parts[1]] = value
        else:
            # Simple field update
            if hasattr(user, field):
                # Type conversion for specific fields
                if field in ['birth_date', 'documento_scadenza', 'hired_at', 'ordine_iscrizione_date']:
                    if value:
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    else:
                        value = None
                elif field in ['stipendio_mensile_lordo', 'ral_annua']:
                    if value:
                        value = Decimal(value)
                    else:
                        value = None
                elif field in ['department_id']:
                    if value:
                        value = int(value)
                    else:
                        value = None
                elif field in ['languages', 'skills']:
                    # These fields are JSON arrays
                    if not isinstance(value, list):
                        value = []
                
                setattr(user, field, value)
        
        db.session.commit()
        
        # Format display value
        display_value = value
        if isinstance(value, date):
            display_value = value.strftime('%d/%m/%Y')
        elif isinstance(value, Decimal):
            display_value = f"€ {value:,.2f}"
        elif value is None or value == '':
            display_value = '—'
        
        return jsonify({
            "success": True,
            "display_value": display_value
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating field for user {user_id}: {e}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@team_bp.route("/<int:user_id>/upload-avatar", methods=["POST"])
@login_required
def user_upload_avatar(user_id: int):
    """Upload new avatar for user."""
    user = db.session.get(User, user_id) or abort(404)
    
    # Check permissions
    is_self = current_user.id == user.id
    is_hr = current_user.department and current_user.department.id == 17
    can_edit = current_user.is_admin or is_hr or is_self
    
    if not can_edit:
        return jsonify({"success": False, "message": "Permesso negato"}), 403
    
    try:
        avatar_file = request.files.get('avatar')
        if not avatar_file:
            return jsonify({"success": False, "message": "Nessun file selezionato"}), 400
        
        # Delete old avatar
        _delete_old_avatar(user)
        
        # Save new avatar
        avatar_path = _save_avatar(avatar_file, user_id)
        if avatar_path:
            user.avatar_path = avatar_path
            db.session.commit()
            
            return jsonify({
                "success": True,
                "avatar_url": url_for('team.serve_avatar', user_id=user_id)
            })
        else:
            return jsonify({"success": False, "message": "Errore nel salvataggio"}), 500
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading avatar: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ════════════════════════════════════════════════════════════════════════
#  Routes per servire i file - VERSIONE FUNZIONANTE
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/files/<path:subpath>/<path:filename>")
@login_required
def serve_file(subpath: str, filename: str):
    """Serve file da upload directory con controllo accessi."""
    try:
        # Solo admin possono accedere ai file del team
        if not current_user.is_admin:
            abort(HTTPStatus.FORBIDDEN)
        
        # Determina la directory base
        base_upload = _get_upload_base_path()
        
        # Costruisci il path sicuro
        file_path = base_upload / subpath / secure_filename(filename)
        
        # Log per debug
        current_app.logger.info(f"Serving file: {file_path}")
        
        # Verifica che il file esista e sia dentro la directory consentita
        if not file_path.exists() or not file_path.is_file():
            current_app.logger.warning(f"File non trovato: {file_path}")
            abort(HTTPStatus.NOT_FOUND)
        
        # Verifica che il path sia dentro la directory uploads
        file_path = file_path.resolve()
        base_upload = base_upload.resolve()
        if not str(file_path).startswith(str(base_upload)):
            current_app.logger.warning(f"Tentativo di accesso fuori directory: {file_path}")
            abort(HTTPStatus.FORBIDDEN)
        
        # Determina il mimetype
        mimetype = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
        
        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=filename
        )
    except Exception as e:
        current_app.logger.error(f"Errore serving file {subpath}/{filename}: {e}")
        abort(HTTPStatus.NOT_FOUND)


@team_bp.route("/avatar/<int:user_id>")
def serve_avatar(user_id: int):
    """Serve avatar files with proper access control."""
    try:
        user = User.query.get_or_404(user_id)
        
        current_app.logger.info(f"Serving avatar for user {user_id}")
        current_app.logger.info(f"User avatar_path: {user.avatar_path}")
        
        if not user.avatar_path:
            # Ritorna avatar di default
            default_avatar = Path(current_app.static_folder) / "assets" / "immagini" / "logo_user.png"
            current_app.logger.info(f"No avatar path, using default: {default_avatar}")
            if default_avatar.exists():
                return send_file(default_avatar, mimetype='image/png')
            abort(HTTPStatus.NOT_FOUND)
        
        # Costruisci il path dell'avatar
        base_upload = _get_upload_base_path()
        avatar_path = base_upload / user.avatar_path
        
        current_app.logger.info(f"Full avatar path: {avatar_path}")
        current_app.logger.info(f"Avatar exists: {avatar_path.exists()}")
        
        if not avatar_path.exists():
            current_app.logger.error(f"Avatar file not found at {avatar_path}")
            # Fallback all'avatar di default
            default_avatar = Path(current_app.static_folder) / "assets" / "immagini" / "logo_user.png"
            if default_avatar.exists():
                return send_file(default_avatar, mimetype='image/png')
            abort(HTTPStatus.NOT_FOUND)
        
        # Determina il mimetype
        mimetype = mimetypes.guess_type(str(avatar_path))[0] or 'image/png'
        
        return send_file(
            avatar_path,
            mimetype=mimetype,
            as_attachment=False
        )
    except Exception as e:
        current_app.logger.error(f"Errore serving avatar per user {user_id}: {e}", exc_info=True)
        abort(HTTPStatus.NOT_FOUND)

# ════════════════════════════════════════════════════════════════════════
#  1) Lista utenti con ricerca + filtri + reset
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/", methods=["GET"])
@login_required
def user_list() -> str:
    """Elenco paginato con ricerca full-text, filtri e tasto reset."""
    # Accessibile a tutti gli utenti autenticati, non solo admin

    # ── Parametri di paging e filtri GET ─────────────────────────
    page     = request.args.get("page",     1,  type=int)
    per_page = request.args.get("per_page", 25, type=int)

    q          = request.args.get("q",      "", type=str).strip()
    dept_param = request.args.get("dept",   "")
    dept       = int(dept_param) if dept_param.isdigit() else None
    admin      = request.args.get("admin")   # "1" | "0" | None
    active     = request.args.get("active")  # "1" | "0" | None

    # ── Costruzione dinamica dei filtri ──────────────────────────
    filters: list = []
    
    # Mostra solo utenti attivi per default (a meno che non sia specificato diversamente)
    if active is None:
        filters.append(User.is_active.is_(True))
    elif active in {"1", "0"}:
        filters.append(User.is_active.is_(active == "1"))
    
    if dept is not None:
        filters.append(User.department_id == dept)
    if admin in {"1", "0"}:
        filters.append(User.is_admin.is_(admin == "1"))

    if q:
        # sanitizzo eventuali '%' e divido in termini
        safe_q = q.replace("%", "").strip()
        terms  = safe_q.split()

        # 1) full-text search con COALESCE su vettore
        fts = func.coalesce(User.search_vector, "") \
                  .op("@@")(func.plainto_tsquery("italian", safe_q))

        # 2) fallback ILIKE: ogni termine deve comparire in almeno un campo
        term_filters = []
        for term in terms:
            pat = f"%{term}%"
            term_filters.append(
                User.email.ilike(pat)
                | User.first_name.ilike(pat)
                | User.last_name.ilike(pat)
            )
        txt_fallback = and_(*term_filters)

        # 3) OR tra full-text e fallback testuale
        filters.append(fts | txt_fallback)

    # ── Query base con ordinamento alfabetico per cognome e nome ─────
    stmt = select(User).order_by(User.last_name.asc(), User.first_name.asc())
    if filters:
        stmt = stmt.where(*filters)

    # ── Paginazione ─────────────────────────────────────────────
    pagination = db.paginate(
        stmt,
        page=page,
        per_page=per_page,
        error_out=False,
    )

    # ── Reparti per dropdown filtro ─────────────────────────────
    departments = Department.query.order_by(Department.name).all()

    # ── Render template ─────────────────────────────────────────
    return render_template(
        "team/list.html",
        pagination=pagination,
        q=q,
        dept=dept,
        admin=admin,
        active=active,
        departments=departments,
        reset_url=url_for("team.user_list"),
    )


# ════════════════════════════════════════════════════════════════════════
#  2) Dettaglio
# ════════════════════════════════════════════════════════════════════════

def user_detail_v2(user_id: int) -> str:
    """Versione 2 del dettaglio utente con UI/UX migliorata."""
    user = User.query.get_or_404(user_id)
    
    # Carica i dipartimenti per il dropdown
    departments = Department.query.order_by(Department.name).all()
    
    # Carica dati assenze per l'anno corrente
    current_year = datetime.now().year
    leave_balance = LeaveService.get_user_leave_balance(user_id, current_year)
    
    # Carica richieste assenze dell'anno
    leave_requests = LeaveRequest.query.filter_by(
        user_id=user_id
    ).filter(
        extract('year', LeaveRequest.start_date) == current_year
    ).order_by(LeaveRequest.start_date.desc()).all()
    
    # Carica l'ultimo weekly report dell'utente
    try:
        from corposostenibile.models import WeeklyReport
        latest_report = WeeklyReport.query.filter_by(
            user_id=user_id
        ).order_by(WeeklyReport.submission_date.desc()).first()
        
        # Calcola weekly report compliance
        total_reports = WeeklyReport.query.filter_by(user_id=user_id).count()
        expected_reports = 52  # Assumendo 52 settimane l'anno
        weekly_report_compliance = int((total_reports / expected_reports) * 100) if expected_reports > 0 else 0
        
        # Check if user can submit report
        can_submit_report = WeeklyReport.can_submit_report(user_id)
        
        # Get recent weekly reports
        weekly_reports = WeeklyReport.query.filter_by(user_id=user_id).order_by(
            WeeklyReport.submission_date.desc()
        ).limit(10).all()
    except:
        # Se il modello non esiste ancora
        latest_report = None
        weekly_report_compliance = 0
        can_submit_report = False
        weekly_reports = []
        total_reports = 0
    
    # Calcola statistiche ferie
    if leave_balance:
        leave_days_available = leave_balance.get('leave_days_available', 0)
        leave_days_total = leave_balance.get('leave_days_total', 26)
        permission_hours_available = leave_balance.get('permission_hours_available', 0)
        permission_hours_total = leave_balance.get('permission_hours_total', 104)
    else:
        leave_days_available = 0
        leave_days_total = 26
        permission_hours_available = 0
        permission_hours_total = 104
    
    return render_template(
        "team/detail_wowdash.html",
        user=user,
        departments=departments,
        current_year=current_year,
        leave_balance={
            'leave_days_available': leave_days_available,
            'leave_days_total': leave_days_total,
            'permission_hours_available': permission_hours_available,
            'permission_hours_total': permission_hours_total
        },
        leave_requests=leave_requests,
        latest_report=latest_report,
        weekly_report_compliance=weekly_report_compliance,
        total_reports=total_reports,
        can_submit_report=can_submit_report,
        weekly_reports=weekly_reports
    )

@team_bp.route("/<int:user_id>", methods=["GET"])
def user_detail(user_id: int) -> str:
    _require_admin()
    user = (
        User.query.options(db.lazyload(User.clienti))  # nessuna join pesante
        .get_or_404(user_id)
    )
    
    # Usa il nuovo template se il parametro v2 è presente nell'URL
    if request.args.get('v2'):
        return user_detail_v2(user_id)
    
    # Altrimenti usa il template originale
    
    # Carica i dipartimenti per il dropdown di editing inline
    departments = Department.query.order_by(Department.name).all()

    # Carica richieste ferie (tutte, non solo anno corrente)
    leave_requests = LeaveRequest.query.filter_by(
        user_id=user_id
    ).order_by(LeaveRequest.start_date.desc()).all()
    
    # Carica l'ultimo weekly report dell'utente
    from .models.weekly_report import WeeklyReport
    latest_report = WeeklyReport.query.filter_by(
        user_id=user_id
    ).order_by(WeeklyReport.submission_date.desc()).first()
    
    # Calcola weekly report compliance
    total_reports = WeeklyReport.query.filter_by(user_id=user_id).count()
    expected_reports = 52  # Assumendo 52 settimane l'anno
    weekly_report_compliance = int((total_reports / expected_reports) * 100) if expected_reports > 0 else 0
    
    # Check if user can submit report
    can_submit_report = WeeklyReport.can_submit_report(user_id)
    
    # Get recent weekly reports
    weekly_reports = WeeklyReport.query.filter_by(user_id=user_id).order_by(
        WeeklyReport.submission_date.desc()
    ).limit(10).all()
    
    # Determina i permessi per le varie sezioni
    is_hr = current_user.department and current_user.department.id == 17
    is_finance = current_user.department and current_user.department.name == "Finance"
    is_admin = current_user.is_admin
    is_self = current_user.id == user_id
    
    # Permessi per le varie sezioni
    can_edit = is_admin or is_hr or is_self
    can_view_salary = is_admin or is_hr or is_finance or is_self
    can_edit_competences = is_admin or is_hr
    can_view_hr_notes = is_admin or is_hr or is_finance
    readonly = not (is_admin or is_hr)
    
    # Carica le note HR se l'utente ha i permessi
    hr_notes = []
    if can_view_hr_notes:
        from corposostenibile.models import HRNote
        hr_notes = HRNote.query.filter_by(user_id=user_id).order_by(HRNote.created_at.desc()).all()
    
    return render_template(
        "team/detail_editable.html",
        user=user,
        departments=departments,
        # Ferie
        user_leave_requests=leave_requests,
        latest_report=latest_report,
        weekly_reports=weekly_reports,
        weekly_report_compliance=weekly_report_compliance,
        total_reports=total_reports,
        can_submit_report=can_submit_report,
        today=date.today(),
        now=datetime.now(),
        # Permessi
        can_edit=can_edit,
        can_view_salary=can_view_salary,
        can_edit_competences=can_edit_competences,
        can_view_hr_notes=can_view_hr_notes,
        readonly=readonly,
        hr_notes=hr_notes,
        is_hr=is_hr,
        is_finance=is_finance,
        is_admin=is_admin,
        is_self=is_self
    )


# ════════════════════════════════════════════════════════════════════════
#  3) Create - VERSIONE FUNZIONANTE
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/new", methods=["GET", "POST"])
def user_create() -> str | Any:
    _require_admin()
    form = UserForm(db_session=db.session)

    if request.method == "POST":
        current_app.logger.info("POST ricevuta per creazione utente")
        
        if form.validate_on_submit():
            current_app.logger.info("Form validato con successo")
            
            # Verifica email duplicata
            if User.query.filter_by(email=form.email.data.lower()).first():
                flash("Esiste già un account con questa email.", "warning")
                return render_template("team/form.html", form=form, mode="create")
            
            try:
                # Crea l'utente con tutti i dati del form
                user = User(
                    # credenziali
                    email=form.email.data.lower(),
                    password_hash=(
                        generate_password_hash(form.password.data)
                        if form.password.data
                        else generate_password_hash("changeme123")  # Password default
                    ),
                    # profilo base
                    first_name=form.first_name.data.strip(),
                    last_name=form.last_name.data.strip(),
                    job_title=form.job_title.data.strip() if form.job_title.data else None,
                    mobile=form.mobile.data.strip() if form.mobile.data else None,
                    citta=form.citta.data.strip() if form.citta.data else None,
                    indirizzo=form.indirizzo.data.strip() if form.indirizzo.data else None,
                    department_id=(
                        form.department_id.data if form.department_id.data and form.department_id.data != 0 else None
                    ),
                    # HR fields
                    contract_type='partita_iva',  # Sempre Partita IVA di default
                    hired_at=form.hired_at.data,
                    birth_date=form.birth_date.data,
                    languages=form.languages.data or [],
                    hr_notes=form.hr_notes.data.strip() if form.hr_notes.data else None,
                    # Dati fiscali
                    codice_fiscale=form.codice_fiscale.data.strip().upper() if form.codice_fiscale.data else None,
                    partita_iva=form.partita_iva.data.strip() if form.partita_iva.data else None,
                    documento_tipo=form.documento_tipo.data if form.documento_tipo.data else None,
                    documento_numero=form.documento_numero.data.strip().upper() if form.documento_numero.data else None,
                    documento_scadenza=form.documento_scadenza.data,
                    # ACL
                    is_admin=form.is_admin.data,
                    is_active=form.is_active.data,
                    # Timestamp di sicurezza
                    last_password_change_at=datetime.utcnow(),
                )

                # Gestione orario di lavoro
                if form.work_schedule.data:
                    schedule_data = form.work_schedule.data
                    work_schedule = {}
                    
                    # Tipo di orario
                    work_schedule['type'] = schedule_data.get('schedule_type', 'full-time')
                    
                    # Orari (converti time objects in stringhe)
                    if schedule_data.get('hours_from'):
                        work_schedule['hours_from'] = schedule_data['hours_from'].strftime('%H:%M')
                    else:
                        work_schedule['hours_from'] = None
                        
                    if schedule_data.get('hours_to'):
                        work_schedule['hours_to'] = schedule_data['hours_to'].strftime('%H:%M')
                    else:
                        work_schedule['hours_to'] = None
                    
                    # Giorni lavorativi
                    work_schedule['days'] = schedule_data.get('work_days', [])
                    
                    user.work_schedule = work_schedule
                    current_app.logger.info(f"Orario di lavoro impostato: {work_schedule}")

                # Gestione piano di sviluppo
                if form.development_plan.data:
                    plan_data = form.development_plan.data
                    development_plan = {}
                    
                    # Obiettivi
                    if plan_data.get('goals'):
                        development_plan['goals'] = plan_data['goals'].strip()
                    else:
                        development_plan['goals'] = ''
                    
                    # Competenze da sviluppare
                    if plan_data.get('skills_to_develop'):
                        development_plan['skills_to_develop'] = plan_data['skills_to_develop'].strip()
                    else:
                        development_plan['skills_to_develop'] = ''
                    
                    # Timeline
                    if plan_data.get('timeline'):
                        development_plan['timeline'] = plan_data['timeline'].strip()
                    else:
                        development_plan['timeline'] = ''
                    
                    # Assegna solo se c'è almeno un campo valorizzato
                    if any(development_plan.values()):
                        user.development_plan = development_plan
                        current_app.logger.info(f"Piano di sviluppo impostato: {development_plan}")

                # Gestione account aziendali
                accounts = {}
                
                # Google
                if form.accounts_google.data:
                    accounts['google'] = form.accounts_google.data.strip()
                
                # Slack
                if form.accounts_slack.data:
                    accounts['slack'] = form.accounts_slack.data.strip()
                
                # GitHub
                if form.accounts_github.data:
                    accounts['github'] = form.accounts_github.data.strip()
                
                # Altri account da textarea (formato: "servizio: account" per riga)
                if form.accounts_other.data:
                    other_accounts_text = form.accounts_other.data.strip()
                    for line in other_accounts_text.split('\n'):
                        line = line.strip()
                        if line and ':' in line:
                            parts = line.split(':', 1)
                            if len(parts) == 2:
                                service = parts[0].strip().lower()
                                account = parts[1].strip()
                                if service and account:
                                    accounts[service] = account
                
                if accounts:
                    user.accounts = accounts
                    current_app.logger.info(f"Account aziendali: {list(accounts.keys())}")
                
                # Gestione campi retributivi
                if form.ral_annua.data:
                    try:
                        user.ral_annua = float(form.ral_annua.data.replace(',', '.'))
                    except ValueError:
                        pass
                
                if form.stipendio_mensile_lordo.data:
                    try:
                        user.stipendio_mensile_lordo = float(form.stipendio_mensile_lordo.data.replace(',', '.'))
                    except ValueError:
                        pass

                # Salva l'utente per ottenere l'ID
                db.session.add(user)
                db.session.flush()  # Ottiene l'ID senza fare commit completo
                
                current_app.logger.info(f"Utente creato con ID: {user.id}")
                
                # ===== GESTIONE AVATAR =====
                if form.avatar_file.data:
                    current_app.logger.info("Rilevato file avatar, inizio caricamento...")
                    
                    try:
                        avatar_path = _save_avatar(form.avatar_file.data, user.id)
                        
                        if avatar_path:
                            user.avatar_path = avatar_path
                            current_app.logger.info(f"Avatar path salvato nel model: {avatar_path}")
                            
                            # Flush aggiuntivo per assicurarsi che avatar_path sia salvato
                            db.session.flush()
                            
                            # Verifica che sia stato salvato
                            current_app.logger.info(f"Verifica avatar_path dopo flush: {user.avatar_path}")
                        else:
                            current_app.logger.warning("_save_avatar ha ritornato None")
                            flash("L'avatar non è stato salvato correttamente", "warning")
                            
                    except Exception as avatar_error:
                        current_app.logger.error(f"Errore durante il salvataggio avatar: {avatar_error}", exc_info=True)
                        flash("Errore durante il caricamento dell'avatar", "warning")

                # ===== GESTIONE CONTRATTO =====
                if form.contract_file.data:
                    current_app.logger.info("Rilevato file contratto, inizio caricamento...")
                    
                    try:
                        contract_path = _save_contract(form.contract_file.data)
                        
                        if contract_path:
                            user.contract_file = contract_path
                            current_app.logger.info(f"Contratto salvato: {contract_path}")
                        else:
                            current_app.logger.warning("_save_contract ha ritornato None")
                            flash("Il contratto non è stato salvato correttamente", "warning")
                            
                    except Exception as contract_error:
                        current_app.logger.error(f"Errore durante il salvataggio contratto: {contract_error}", exc_info=True)
                        flash("Errore durante il caricamento del contratto", "warning")

                # ===== GESTIONE CERTIFICAZIONI =====
                cert_files = request.files.getlist('new_cert_files')
                if cert_files:
                    current_app.logger.info(f"Trovati {len(cert_files)} file certificazioni")
                    
                    cert_count = 0
                    for idx, fs in enumerate(cert_files):
                        if fs and fs.filename:  # Verifica che il file sia valido
                            current_app.logger.info(f"Elaborazione certificazione {idx+1}: {fs.filename}")
                            
                            try:
                                cert = _save_cert_file(fs)
                                
                                if cert:
                                    user.certifications.append(cert)
                                    cert_count += 1
                                    current_app.logger.info(f"Certificazione {idx+1} aggiunta con successo")
                                else:
                                    current_app.logger.warning(f"Certificazione {idx+1} non salvata")
                                    
                            except Exception as cert_error:
                                current_app.logger.error(f"Errore certificazione {idx+1}: {cert_error}", exc_info=True)
                    
                    if cert_count > 0:
                        current_app.logger.info(f"Aggiunte {cert_count} certificazioni")
                        if cert_count < len(cert_files):
                            flash(f"Caricate {cert_count} certificazioni su {len(cert_files)}", "warning")

                # ===== COMMIT FINALE =====
                # Log dello stato prima del commit
                current_app.logger.info(f"Prima del commit finale:")
                current_app.logger.info(f"  - email: {user.email}")
                current_app.logger.info(f"  - avatar_path: {user.avatar_path}")
                current_app.logger.info(f"  - contract_file: {user.contract_file}")
                current_app.logger.info(f"  - certificazioni: {len(user.certifications)}")
                
                db.session.commit()
                
                # Verifica post-commit
                db.session.refresh(user)
                current_app.logger.info(f"Dopo il commit:")
                current_app.logger.info(f"  - ID: {user.id}")
                current_app.logger.info(f"  - avatar_path salvato: {user.avatar_path}")
                
                flash("Utente creato con successo.", "success")
                return redirect(url_for("team.user_detail", user_id=user.id))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Errore creazione utente: {str(e)}", exc_info=True)
                flash(f"Errore durante la creazione dell'utente: {str(e)}", "danger")
                
        else:
            # Form non validato - log degli errori
            current_app.logger.warning(f"Form non validato. Errori: {form.errors}")
            
            # Mostra gli errori specifici per campo
            for field_name, errors in form.errors.items():
                for error in errors:
                    current_app.logger.warning(f"Errore campo {field_name}: {error}")
                    
                    # Messaggi user-friendly per errori comuni
                    if field_name == 'email' and 'Invalid email address' in error:
                        flash("Inserisci un indirizzo email valido", "warning")
                    elif field_name == 'password' and 'Field must be at least' in error:
                        flash("La password deve essere di almeno 6 caratteri", "warning")
                    elif field_name == 'confirm' and 'Passwords must match' in error:
                        flash("Le password non corrispondono", "warning")
                    else:
                        flash(f"Errore nel campo {field_name}: {error}", "warning")

    # GET request o form non valido
    return render_template("team/form.html", form=form, mode="create")

# ════════════════════════════════════════════════════════════════════════
#  4) Edit - VERSIONE FUNZIONANTE
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id: int) -> str | Any:
    _require_admin()
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user, db_session=db.session)

    # Prepopola i campi complessi per GET
    if request.method == 'GET':
        # Orario di lavoro
        if user.work_schedule:
            form.work_schedule.schedule_type.data = user.work_schedule.get('type', 'full-time')
            if user.work_schedule.get('hours_from'):
                try:
                    form.work_schedule.hours_from.data = time.fromisoformat(user.work_schedule['hours_from'])
                except:
                    pass
            if user.work_schedule.get('hours_to'):
                try:
                    form.work_schedule.hours_to.data = time.fromisoformat(user.work_schedule['hours_to'])
                except:
                    pass
            form.work_schedule.work_days.data = user.work_schedule.get('days', [])
        
        # Piano di sviluppo
        if user.development_plan:
            form.development_plan.goals.data = user.development_plan.get('goals', '')
            form.development_plan.skills_to_develop.data = user.development_plan.get('skills_to_develop', '')
            form.development_plan.timeline.data = user.development_plan.get('timeline', '')
        
        # Account
        if user.accounts:
            form.accounts_google.data = user.accounts.get('google', '')
            form.accounts_slack.data = user.accounts.get('slack', '')
            form.accounts_github.data = user.accounts.get('github', '')
            
            # Altri account
            other_accounts = []
            for service, account in user.accounts.items():
                if service not in ['google', 'slack', 'github']:
                    other_accounts.append(f"{service}: {account}")
            form.accounts_other.data = '\n'.join(other_accounts)

    if request.method == "POST":
        current_app.logger.info(f"POST ricevuta per modifica utente {user_id}")
        
        if form.validate_on_submit():
            current_app.logger.info("Form validato con successo")
            
            # email duplicata?
            other = User.query.filter(
                User.email == form.email.data.lower(), 
                User.id != user.id
            ).first()
            
            if other:
                flash("Email già utilizzata da un altro account.", "warning")
                return render_template("team/form.html", form=form, mode="edit", user=user)
            
            try:
                # credenziali
                user.email = form.email.data.lower()
                if form.password.data:
                    user.password_hash = generate_password_hash(form.password.data)

                # profilo
                user.first_name = form.first_name.data.strip()
                user.last_name = form.last_name.data.strip()
                user.job_title = form.job_title.data.strip() if form.job_title.data else None
                user.mobile = form.mobile.data.strip() if form.mobile.data else None
                user.citta = form.citta.data.strip() if form.citta.data else None
                user.indirizzo = form.indirizzo.data.strip() if form.indirizzo.data else None
                user.department_id = (
                    form.department_id.data if form.department_id.data and form.department_id.data != 0 else None
                )

                # HR
                user.contract_type = 'partita_iva'  # Sempre Partita IVA
                user.hired_at = form.hired_at.data

                # ACL
                user.is_admin = form.is_admin.data
                user.is_active = form.is_active.data

                # NUOVI CAMPI
                user.birth_date = form.birth_date.data
                user.languages = form.languages.data or []
                user.hr_notes = form.hr_notes.data.strip() if form.hr_notes.data else None
                
                # Dati fiscali
                user.codice_fiscale = form.codice_fiscale.data.strip().upper() if form.codice_fiscale.data else None
                user.partita_iva = form.partita_iva.data.strip() if form.partita_iva.data else None
                user.documento_tipo = form.documento_tipo.data if form.documento_tipo.data else None
                user.documento_numero = form.documento_numero.data.strip().upper() if form.documento_numero.data else None
                user.documento_scadenza = form.documento_scadenza.data

                # Gestione orario di lavoro
                if form.work_schedule.data:
                    schedule_data = form.work_schedule.data
                    user.work_schedule = {
                        'type': schedule_data.get('schedule_type', 'full-time'),
                        'hours_from': schedule_data.get('hours_from').strftime('%H:%M') if schedule_data.get('hours_from') else None,
                        'hours_to': schedule_data.get('hours_to').strftime('%H:%M') if schedule_data.get('hours_to') else None,
                        'days': schedule_data.get('work_days', [])
                    }

                # Gestione piano di sviluppo
                if form.development_plan.data:
                    plan_data = form.development_plan.data
                    user.development_plan = {
                        'goals': plan_data.get('goals', '').strip() if plan_data.get('goals') else '',
                        'skills_to_develop': plan_data.get('skills_to_develop', '').strip() if plan_data.get('skills_to_develop') else '',
                        'timeline': plan_data.get('timeline', '').strip() if plan_data.get('timeline') else ''
                    }

                # Gestione account
                accounts = {}
                if form.accounts_google.data:
                    accounts['google'] = form.accounts_google.data.strip()
                if form.accounts_slack.data:
                    accounts['slack'] = form.accounts_slack.data.strip()
                if form.accounts_github.data:
                    accounts['github'] = form.accounts_github.data.strip()
                
                # Altri account da textarea
                if form.accounts_other.data:
                    for line in form.accounts_other.data.strip().split('\n'):
                        if ':' in line:
                            service, account = line.split(':', 1)
                            accounts[service.strip().lower()] = account.strip()
                
                user.accounts = accounts
                
                # Gestione campi retributivi
                if form.ral_annua.data:
                    try:
                        user.ral_annua = float(form.ral_annua.data.replace(',', '.'))
                    except ValueError:
                        user.ral_annua = None
                else:
                    user.ral_annua = None
                
                if form.stipendio_mensile_lordo.data:
                    try:
                        user.stipendio_mensile_lordo = float(form.stipendio_mensile_lordo.data.replace(',', '.'))
                    except ValueError:
                        user.stipendio_mensile_lordo = None
                else:
                    user.stipendio_mensile_lordo = None

                # Avatar upload
                if form.avatar_file.data:
                    current_app.logger.info("Caricamento nuovo avatar...")
                    # Elimina vecchio avatar
                    _delete_old_avatar(user)
                    
                    # Salva nuovo avatar
                    avatar_path = _save_avatar(form.avatar_file.data, user.id)
                    if avatar_path:
                        user.avatar_path = avatar_path
                        current_app.logger.info(f"Nuovo avatar salvato: {avatar_path}")

                # sostituzione contratto
                if form.contract_file.data:
                    current_app.logger.info("Caricamento nuovo contratto...")
                    new_contract = _save_contract(form.contract_file.data)
                    if new_contract:
                        # Elimina vecchio contratto
                        if user.contract_file:
                            try:
                                base_upload = _get_upload_base_path()
                                old_path = base_upload / user.contract_file
                                if old_path.exists():
                                    old_path.unlink()
                                    current_app.logger.info(f"Vecchio contratto eliminato: {old_path}")
                            except Exception as e:
                                current_app.logger.warning(f"Errore eliminazione vecchio contratto: {e}")
                        user.contract_file = new_contract
                        current_app.logger.info(f"Nuovo contratto salvato: {new_contract}")

                # nuove certificazioni
                cert_files = request.files.getlist('new_cert_files')
                if cert_files:
                    current_app.logger.info(f"Trovati {len(cert_files)} file certificazioni")
                    for idx, fs in enumerate(cert_files):
                        if fs and fs.filename:  # Verifica che il file sia valido
                            current_app.logger.info(f"Certificazione {idx+1}: {fs.filename}")
                            cert = _save_cert_file(fs)
                            if cert:
                                user.certifications.append(cert)
                                current_app.logger.info(f"Certificazione {idx+1} salvata")

                db.session.commit()
                flash("Profilo aggiornato.", "success")
                return redirect(url_for("team.user_detail", user_id=user.id))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Errore modifica utente: {str(e)}", exc_info=True)
                flash(f"Errore durante l'aggiornamento del profilo: {str(e)}", "danger")
        else:
            # Log errori di validazione
            current_app.logger.warning(f"Form non validato. Errori: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    current_app.logger.warning(f"Errore {field}: {error}")

    return render_template(
        "team/form.html", form=form, mode="edit", user=user
    )


# ════════════════════════════════════════════════════════════════════════
#  5) Toggle attivo / disattivo
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/<int:user_id>/toggle", methods=["POST"])
def user_toggle(user_id: int):
    _require_admin()
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()

    stato = "attivo" if user.is_active else "disattivato"
    flash(f"L'utente '{user.email}' è ora {stato}.", "info")
    return redirect(url_for("team.user_list"))


# ════════════════════════════════════════════════════════════════════════
#  6) Upload certificazioni add-on (detail page)
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/<int:user_id>/add-cert", methods=["POST"])
def user_add_cert(user_id: int):
    _require_admin()
    user = User.query.get_or_404(user_id)

    added: List[Certification] = []
    for fs in request.files.getlist("cert_files"):
        cert = _save_cert_file(fs)
        if cert:
            user.certifications.append(cert)
            added.append(cert)

    if added:
        db.session.commit()
        flash(f"Caricate {len(added)} certificazioni.", "success")
    else:
        flash("Nessun file valido caricato.", "warning")

    return redirect(url_for("team.user_detail", user_id=user.id))


# ════════════════════════════════════════════════════════════════════════
#  7) Upload / sostituzione contratto (detail page)
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/<int:user_id>/add-contract", methods=["POST"])
def user_add_contract(user_id: int):
    _require_admin()
    user = User.query.get_or_404(user_id)

    fs = request.files.get("contract_file")
    new_path = _save_contract(fs)
    if not new_path:
        return redirect(url_for("team.user_detail", user_id=user.id))

    # Elimina vecchio contratto
    if user.contract_file:
        try:
            base_upload = _get_upload_base_path()
            old_path = base_upload / user.contract_file
            if old_path.exists():
                old_path.unlink()
        except Exception:
            pass

    user.contract_file = new_path
    db.session.commit()
    flash("Contratto caricato correttamente.", "success")
    return redirect(url_for("team.user_detail", user_id=user.id))


@team_bp.route("/<int:user_id>/upload-contract", methods=["POST"])
@login_required
def upload_contract(user_id: int):
    """Upload contract PDF file."""
    user = db.session.get(User, user_id) or abort(404)
    
    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_self
    
    if not can_edit:
        return jsonify({"success": False, "message": "Permesso negato"}), 403
    
    try:
        file = request.files.get('file')
        
        if not file:
            return jsonify({"success": False, "message": "File mancante"}), 400
        
        # Validate file
        if file.filename == '':
            return jsonify({"success": False, "message": "Nessun file selezionato"}), 400
        
        # Check file type - only PDF
        if not (file.filename.lower().endswith('.pdf')):
            return jsonify({"success": False, "message": "Solo file PDF sono accettati"}), 400
        
        # Check file size (10MB max)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 10 * 1024 * 1024:
            return jsonify({"success": False, "message": "File troppo grande (max 10MB)"}), 400
        
        # Create contracts directory if not exists
        upload_dir = os.path.join(current_app.root_path, 'uploads', 'contracts')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"contract_{user_id}_{timestamp}.pdf"
        filepath = os.path.join(upload_dir, filename)
        
        # Remove old contract file if exists
        if user.contract_file:
            old_path = os.path.join(current_app.root_path, user.contract_file.lstrip('/'))
            if os.path.exists(old_path):
                os.remove(old_path)
        
        # Save new file
        file.save(filepath)
        
        # Update user record
        user.contract_file = f'/uploads/contracts/{filename}'
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Contratto caricato con successo",
            "filename": filename
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@team_bp.route("/<int:user_id>/remove-contract", methods=["POST"])
@login_required
def remove_contract(user_id: int):
    """Remove contract PDF file."""
    user = db.session.get(User, user_id) or abort(404)
    
    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_self
    
    if not can_edit:
        return jsonify({"success": False, "message": "Permesso negato"}), 403
    
    try:
        if user.contract_file:
            # Remove file from filesystem
            filepath = os.path.join(current_app.root_path, user.contract_file.lstrip('/'))
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # Update user record
            user.contract_file = None
            db.session.commit()
            
            return jsonify({"success": True, "message": "Contratto rimosso con successo"})
        else:
            return jsonify({"success": False, "message": "Nessun contratto da rimuovere"}), 400
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@team_bp.route("/<int:user_id>/download-contract")
@login_required
def download_contract(user_id: int):
    """Download contract PDF file."""
    user = db.session.get(User, user_id) or abort(404)
    
    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    is_finance = current_user.department and current_user.department.name == "Finance"
    can_view = current_user.is_admin or is_hr or is_finance or is_self
    
    if not can_view:
        abort(403)
    
    if not user.contract_file:
        abort(404)
    
    filepath = os.path.join(current_app.root_path, user.contract_file.lstrip('/'))
    if not os.path.exists(filepath):
        abort(404)
    
    return send_file(filepath, as_attachment=True, download_name=f"contratto_{user.first_name}_{user.last_name}.pdf")


# ═══════════════════════════════════════════════════════════════════════════════
#  CV UPLOAD / DELETE
# ═══════════════════════════════════════════════════════════════════════════════

@team_bp.route("/<int:user_id>/upload-cv", methods=["POST"])
@login_required
def upload_cv(user_id: int):
    """Upload CV file (PDF, DOC, DOCX)."""
    user = db.session.get(User, user_id) or abort(404)

    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_self

    if not can_edit:
        return jsonify({"success": False, "error": "Permesso negato"}), 403

    try:
        file = request.files.get('cv_file')

        if not file:
            return jsonify({"success": False, "error": "File mancante"}), 400

        if file.filename == '':
            return jsonify({"success": False, "error": "Nessun file selezionato"}), 400

        # Check file type - PDF, DOC, DOCX
        allowed_extensions = ['.pdf', '.doc', '.docx']
        ext = os.path.splitext(file.filename.lower())[1]
        if ext not in allowed_extensions:
            return jsonify({"success": False, "error": "Formato non valido. Usa PDF, DOC o DOCX."}), 400

        # Check file size (10MB max)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > 50 * 1024 * 1024:
            return jsonify({"success": False, "error": "File troppo grande (max 50MB)"}), 400

        # Create cv directory if not exists
        upload_dir = os.path.join(current_app.root_path, 'uploads', 'cv')
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = secure_filename(f"{user.first_name}_{user.last_name}")
        filename = f"cv_{user_id}_{safe_name}_{timestamp}{ext}"
        filepath = os.path.join(upload_dir, filename)

        # Remove old CV file if exists
        if user.cv_file:
            old_path = os.path.join(current_app.root_path, 'uploads', user.cv_file)
            if os.path.exists(old_path):
                os.remove(old_path)

        # Save new file
        file.save(filepath)

        # Update user record
        user.cv_file = f'cv/{filename}'
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "CV caricato con successo",
            "filename": filename
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading CV for user {user_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@team_bp.route("/<int:user_id>/delete-cv", methods=["POST"])
@login_required
def delete_cv(user_id: int):
    """Delete CV file."""
    user = db.session.get(User, user_id) or abort(404)

    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_self

    if not can_edit:
        return jsonify({"success": False, "error": "Permesso negato"}), 403

    try:
        if user.cv_file:
            # Remove file from filesystem
            filepath = os.path.join(current_app.root_path, 'uploads', user.cv_file)
            if os.path.exists(filepath):
                os.remove(filepath)

            # Update user record
            user.cv_file = None
            db.session.commit()

            return jsonify({"success": True, "message": "CV eliminato con successo"})
        else:
            return jsonify({"success": False, "error": "Nessun CV da eliminare"}), 400

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting CV for user {user_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@team_bp.route("/<int:user_id>/cv")
@login_required
def serve_cv(user_id: int):
    """Serve CV file with access control."""
    user = db.session.get(User, user_id) or abort(404)

    # Check permissions - self, admin, HR can view
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    can_view = current_user.is_admin or is_hr or is_self

    if not can_view:
        abort(403)

    if not user.cv_file:
        abort(404)

    filepath = os.path.join(current_app.root_path, 'uploads', user.cv_file)
    if not os.path.exists(filepath):
        abort(404)

    # Determina il mimetype
    mimetype = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'

    return send_file(
        filepath,
        mimetype=mimetype,
        as_attachment=False,
        download_name=os.path.basename(user.cv_file)
    )


@team_bp.route("/<int:user_id>/upload-document", methods=["POST"])
@login_required
@csrf.exempt
def upload_document(user_id: int):
    """Upload document front or back side."""
    user = db.session.get(User, user_id) or abort(404)
    
    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_self
    
    if not can_edit:
        return jsonify({"success": False, "message": "Permesso negato"}), 403
    
    try:
        file = request.files.get('file')
        side = request.form.get('side')  # 'fronte' or 'retro'
        
        if not file or not side:
            return jsonify({"success": False, "message": "File o lato mancante"}), 400
        
        # Validate file
        if file.filename == '':
            return jsonify({"success": False, "message": "Nessun file selezionato"}), 400
        
        # Check file type
        allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({"success": False, "message": "Formato file non supportato"}), 400
        
        # Check file size (5MB max)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        if file_size > 5 * 1024 * 1024:
            return jsonify({"success": False, "message": "File troppo grande (max 5MB)"}), 400
        
        # Generate filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"doc_{user_id}_{side}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        
        # Save file
        upload_dir = _upload_dir("documents")
        filepath = upload_dir / filename
        file.save(str(filepath))
        
        # Remove old file if exists
        if side == 'fronte' and user.documento_fronte_path:
            try:
                old_file = upload_dir / user.documento_fronte_path.split('/')[-1]
                if old_file.exists():
                    old_file.unlink()
            except:
                pass
        elif side == 'retro' and user.documento_retro_path:
            try:
                old_file = upload_dir / user.documento_retro_path.split('/')[-1]
                if old_file.exists():
                    old_file.unlink()
            except:
                pass
        
        # Update user record
        if side == 'fronte':
            user.documento_fronte_path = f"documents/{filename}"
        else:
            user.documento_retro_path = f"documents/{filename}"
        
        db.session.commit()
        
        return jsonify({"success": True, "message": f"Documento {side} caricato con successo"})
        
    except Exception as e:
        current_app.logger.error(f"Error uploading document: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@team_bp.route("/<int:user_id>/remove-document", methods=["POST"])
@login_required
@csrf.exempt
def remove_document(user_id: int):
    """Remove document front or back side."""
    user = db.session.get(User, user_id) or abort(404)
    
    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_self
    
    if not can_edit:
        return jsonify({"success": False, "message": "Permesso negato"}), 403
    
    try:
        data = request.get_json()
        side = data.get('side')  # 'fronte' or 'retro'
        
        if not side:
            return jsonify({"success": False, "message": "Lato mancante"}), 400
        
        # Remove file
        upload_dir = _upload_dir("documents")
        
        if side == 'fronte' and user.documento_fronte_path:
            try:
                filepath = upload_dir / user.documento_fronte_path.split('/')[-1]
                if filepath.exists():
                    filepath.unlink()
            except:
                pass
            user.documento_fronte_path = None
            
        elif side == 'retro' and user.documento_retro_path:
            try:
                filepath = upload_dir / user.documento_retro_path.split('/')[-1]
                if filepath.exists():
                    filepath.unlink()
            except:
                pass
            user.documento_retro_path = None
        
        db.session.commit()
        
        return jsonify({"success": True, "message": f"Documento {side} rimosso"})
        
    except Exception as e:
        current_app.logger.error(f"Error removing document: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@team_bp.route("/<int:user_id>/view-document/<doc_type>")
@login_required
def view_user_document(user_id: int, doc_type: str):
    """View user document (contract, documento_fronte, documento_retro)."""
    user = db.session.get(User, user_id) or abort(404)

    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    is_finance = current_user.department and current_user.department.name == "Finance"
    can_view = current_user.is_admin or is_hr or is_finance or is_self

    if not can_view:
        abort(403)

    # Get file path based on doc_type
    if doc_type == 'contract':
        file_path = user.contract_file
    elif doc_type == 'documento_fronte':
        file_path = user.documento_fronte_path
    elif doc_type == 'documento_retro':
        file_path = user.documento_retro_path
    else:
        abort(404)

    if not file_path:
        abort(404)

    # Build absolute path
    base_upload = _get_upload_base_path()
    full_path = base_upload / file_path

    if not full_path.exists():
        # Try alternative path structure
        full_path = Path(current_app.root_path) / file_path.lstrip('/')
        if not full_path.exists():
            current_app.logger.warning(f"Document not found: {file_path}")
            abort(404)

    # Determine mimetype
    mimetype = mimetypes.guess_type(str(full_path))[0] or 'application/octet-stream'

    return send_file(
        full_path,
        mimetype=mimetype,
        as_attachment=False,
        download_name=full_path.name
    )


@team_bp.route("/<int:user_id>/upload-education-attachment", methods=["POST"])
@login_required
@csrf.exempt
def upload_education_attachment(user_id: int):
    """Upload attachment for education items."""
    user = db.session.get(User, user_id) or abort(404)
    
    # Check permissions
    is_hr = current_user.department and current_user.department.id == 17
    is_self = current_user.id == user.id
    can_edit = current_user.is_admin or is_hr or is_self
    
    if not can_edit:
        return jsonify({"success": False, "message": "Permesso negato"}), 403
    
    try:
        file = request.files.get('file')
        edu_type = request.form.get('type')  # 'high_school', 'degree', 'master', 'phd', 'course', 'certification'
        index = request.form.get('index')  # For list items (degrees, masters, courses, certifications)
        
        if not file or not edu_type:
            return jsonify({"success": False, "message": "File o tipo mancante"}), 400
        
        # Validate file
        if file.filename == '':
            return jsonify({"success": False, "message": "Nessun file selezionato"}), 400
        
        # Check file type
        allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({"success": False, "message": "Formato file non supportato"}), 400
        
        # Check file size (10MB max for education attachments)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        if file_size > 10 * 1024 * 1024:
            return jsonify({"success": False, "message": "File troppo grande (max 10MB)"}), 400
        
        # Generate filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"edu_{user_id}_{edu_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        
        # Save file
        upload_dir = _upload_dir("education")
        filepath = upload_dir / filename
        file.save(str(filepath))
        
        # Update user education data with attachment
        attachment_info = {
            'filename': filename,
            'name': file.filename,
            'uploaded_at': datetime.now().isoformat()
        }
        
        # Add attachment to appropriate education field
        if edu_type == 'high_school':
            if not user.education_high_school:
                user.education_high_school = {}
            if 'attachments' not in user.education_high_school:
                user.education_high_school['attachments'] = []
            user.education_high_school['attachments'].append(attachment_info)
            
        elif edu_type == 'degree' and index is not None:
            idx = int(index)
            if user.education_degrees and idx < len(user.education_degrees):
                if 'attachments' not in user.education_degrees[idx]:
                    user.education_degrees[idx]['attachments'] = []
                user.education_degrees[idx]['attachments'].append(attachment_info)
                
        elif edu_type == 'master' and index is not None:
            idx = int(index)
            if user.education_masters and idx < len(user.education_masters):
                if 'attachments' not in user.education_masters[idx]:
                    user.education_masters[idx]['attachments'] = []
                user.education_masters[idx]['attachments'].append(attachment_info)
                
        elif edu_type == 'phd':
            if not user.education_phd:
                user.education_phd = {}
            if 'attachments' not in user.education_phd:
                user.education_phd['attachments'] = []
            user.education_phd['attachments'].append(attachment_info)
            
        elif edu_type == 'course' and index is not None:
            idx = int(index)
            if user.education_courses and idx < len(user.education_courses):
                if 'attachments' not in user.education_courses[idx]:
                    user.education_courses[idx]['attachments'] = []
                user.education_courses[idx]['attachments'].append(attachment_info)
                
        elif edu_type == 'certification' and index is not None:
            idx = int(index)
            if user.education_certifications and idx < len(user.education_certifications):
                if 'attachments' not in user.education_certifications[idx]:
                    user.education_certifications[idx]['attachments'] = []
                user.education_certifications[idx]['attachments'].append(attachment_info)
        
        # Mark fields as modified for SQLAlchemy to detect changes
        from sqlalchemy.orm.attributes import flag_modified
        if edu_type == 'high_school':
            flag_modified(user, 'education_high_school')
        elif edu_type == 'degree':
            flag_modified(user, 'education_degrees')
        elif edu_type == 'master':
            flag_modified(user, 'education_masters')
        elif edu_type == 'phd':
            flag_modified(user, 'education_phd')
        elif edu_type == 'course':
            flag_modified(user, 'education_courses')
        elif edu_type == 'certification':
            flag_modified(user, 'education_certifications')
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Allegato caricato con successo"})
        
    except Exception as e:
        current_app.logger.error(f"Error uploading education attachment: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# --------------------------------------------------------------------------- #
#  Dashboard Team – KPI snapshot
# --------------------------------------------------------------------------- #

@team_bp.route("/dashboard", methods=["GET"])
@team_bp.route("/dashboard/", methods=["GET"])
def team_dashboard() -> str:
    """
    Dashboard Team con metriche HR e OKR.
    """
    _require_admin()

    from corposostenibile.models import Objective, OKRStatusEnum
    from datetime import date
    from sqlalchemy import case

    # ─────────────────── 1) HERO KPI ──────────────────────────
    total_users: int = db.session.query(func.count(User.id)).scalar() or 0

    avg_tenure_days = (
        db.session.query(
            func.avg(func.date_part("day", func.now() - User.hired_at))
        )
        .filter(User.hired_at.isnot(None))
        .scalar()
    )
    avg_tenure_years: float = round((avg_tenure_days or 0) / 365, 1)

    hero_kpi: dict[str, Any] = {
        "total_users": total_users,
        "avg_tenure_years": avg_tenure_years,
    }

    # ───────────────── 2) PEOPLE COMPOSITION ──────────────────
    # 2.a utenti per reparto
    dept_counts = (
        db.session.query(Department.name, func.count(User.id))
        .outerjoin(User, User.department_id == Department.id)
        .group_by(Department.name)
        .order_by(func.count(User.id).desc())
        .all()
    )
    dept_breakdown = [
        {"department": d or "Senza reparto", "count": c} 
        for d, c in dept_counts if c > 0
    ]

    # 2.b contract-type
    contract_counts = (
        db.session.query(User.contract_type, func.count(User.id))
        .group_by(User.contract_type)
        .order_by(func.count(User.id).desc())
        .all()
    )
    contract_breakdown = [
        {"contract_type": ct or "Non specificato", "count": c} 
        for ct, c in contract_counts
    ]

    # ─────────────────── 3) OKR METRICS ──────────────────────────
    current_year = date.today().year
    
    # 3.a OKR Achievement Rate (% obiettivi completati)
    total_objectives = db.session.query(func.count(Objective.id)).scalar() or 0
    
    completed_objectives = db.session.query(func.count(Objective.id)).filter(
        Objective.status == OKRStatusEnum.completed
    ).scalar() or 0
    
    achievement_rate = int((completed_objectives / total_objectives * 100) if total_objectives > 0 else 0)
    
    # 3.b Average OKR Progress - Non più disponibile senza campo progress
    avg_progress = 0
    
    okr_stats = {
        "total": total_objectives,
        "completed": completed_objectives,
        "achievement_rate": achievement_rate,
        "avg_progress": int(avg_progress),
    }
    
    # 3.c OKR Progress per dipartimento
    okr_by_dept_query = (
        db.session.query(
            Department.name,
            func.count(Objective.id).label('total_okrs'),
            func.sum(
                case(
                    (Objective.status == OKRStatusEnum.completed, 1),
                    else_=0
                )
            ).label('completed_okrs')
        )
        .join(User, User.department_id == Department.id)
        .join(Objective, Objective.user_id == User.id)
        .filter(
            Objective.status.in_([OKRStatusEnum.active, OKRStatusEnum.completed])
        )
        .group_by(Department.name)
        .order_by(func.count(Objective.id).desc())
        .all()
    )
    
    okr_by_department = [
        {
            "department": dept_name,
            "progress": int((completed_okrs / total * 100) if total > 0 else 0),
            "count": total
        }
        for dept_name, total, completed_okrs in okr_by_dept_query
    ]
    
    # 3.d Top Performers - Query semplificata per evitare problemi di GROUP BY
    top_performers_subquery = (
        db.session.query(
            User.id.label('user_id'),
            User.first_name,
            User.last_name,
            User.job_title,
            User.avatar_path,
            User.department_id,
            func.count(Objective.id).label('total_okrs'),
            func.sum(
                case(
                    (Objective.status == OKRStatusEnum.completed, 1),
                    else_=0
                )
            ).label('completed_count')
        )
        .join(Objective, Objective.user_id == User.id)
        .filter(
            User.is_active == True
        )
        .group_by(
            User.id, 
            User.first_name, 
            User.last_name, 
            User.job_title, 
            User.avatar_path,
            User.department_id
        )
        .order_by(func.sum(
            case(
                (Objective.status == OKRStatusEnum.completed, 1),
                else_=0
            )
        ).desc())
        .limit(5)
        .all()
    )
    
    # Recupera i dipartimenti separatamente per evitare problemi di join
    dept_dict = {d.id: d.name for d in Department.query.all()}
    
    top_performers = []
    for row in top_performers_subquery:
        top_performers.append({
            "id": row.user_id,
            "full_name": f"{row.first_name} {row.last_name}".strip(),
            "initials": f"{row.first_name[0] if row.first_name else ''}{row.last_name[0] if row.last_name else ''}".upper(),
            "avatar_path": row.avatar_path,
            "job_title": row.job_title,
            "department": {"name": dept_dict.get(row.department_id, "—")} if row.department_id else None,
            "okr_score": int((row.completed_count / row.total_okrs * 100) if row.total_okrs > 0 else 0),
            "completed_okrs": int(row.completed_count or 0)
        })
    
    # 3.e OKR Progress trend - Non più disponibile senza campo progress
    okr_progress_trend = [0] * 12  # Array di zeri per mantenere la struttura
    
    # ─────────────────── RENDERING ─────────────────────────────
    return render_template(
        "team/dashboard.html",
        hero_kpi=hero_kpi,
        dept_breakdown=dept_breakdown,
        contract_breakdown=contract_breakdown,
        okr_stats=okr_stats,
        okr_by_department=okr_by_department,
        top_performers=top_performers,
        okr_progress_trend=okr_progress_trend,
        current_year=current_year,
    )


# --------------------------------------------------------------------------- #
#  Profilo personale (read-only)
# --------------------------------------------------------------------------- #

@team_bp.route("/profile", methods=["GET"])
@login_required
def my_profile() -> str:
    """Pagina profilo dell'utente corrente (read-only)."""
    # Carica dati assenze per l'anno corrente
    current_year = datetime.now().year
    leave_balance = LeaveService.get_user_leave_balance(current_user.id, current_year)
    
    # Carica richieste assenze dell'anno
    leave_requests = LeaveRequest.query.filter_by(
        user_id=current_user.id
    ).filter(
        extract('year', LeaveRequest.start_date) == current_year
    ).order_by(LeaveRequest.start_date.desc()).all()
    
    # Carica l'ultimo weekly report dell'utente
    from .models.weekly_report import WeeklyReport
    latest_report = WeeklyReport.query.filter_by(
        user_id=current_user.id
    ).order_by(WeeklyReport.submission_date.desc()).first()
    
    return render_template(
        "team/detail_editable.html",
        user=current_user,
        can_edit=True,  # User can edit their own profile
        can_view_hr_notes=False,  # Regular users can't see HR notes
        self_view=True,
        current_year=current_year,
        leave_balance=leave_balance,
        leave_requests=leave_requests,
        latest_report=latest_report
    )


# ════════════════════════════════════════════════════════════════════════════ #
#  SISTEMA FERIE E PERMESSI
# ════════════════════════════════════════════════════════════════════════════ #

# --------------------------------------------------------------------------- #
#  Configurazione Policy (solo admin)
# --------------------------------------------------------------------------- #

@team_bp.route("/leaves/settings", methods=["GET", "POST"])
@login_required
def leave_settings():
    """Configurazione policy ferie/permessi annuale."""
    _require_admin()
    
    # Anno corrente di default
    from datetime import datetime
    current_year = datetime.now().year
    
    # Carica policy esistente o crea nuova
    selected_year = request.args.get('year', current_year, type=int)
    policy = LeavePolicy.query.filter_by(year=selected_year).first()
    
    form = LeavePolicyForm(obj=policy)
    
    if request.method == "POST" and form.validate_on_submit():
        year = form.year.data
        
        # Verifica se esiste già una policy per l'anno
        existing = LeavePolicy.query.filter_by(year=year).first()
        if existing and (not policy or existing.id != policy.id):
            flash(f"Esiste già una policy per l'anno {year}", "warning")
            return render_template("team/leaves/settings.html", form=form, current_year=current_year)
        
        if policy:
            # Aggiorna esistente
            policy.annual_leave_days = int(form.annual_leave_days.data)
            policy.annual_permission_hours = int(form.annual_permission_hours.data)
            policy.min_consecutive_days = int(form.min_consecutive_days.data)
            policy.max_consecutive_days = int(form.max_consecutive_days.data)
            policy.notes = form.notes.data
        else:
            # Crea nuova
            policy = LeavePolicy(
                year=year,
                annual_leave_days=int(form.annual_leave_days.data),
                annual_permission_hours=int(form.annual_permission_hours.data),
                min_consecutive_days=int(form.min_consecutive_days.data),
                max_consecutive_days=int(form.max_consecutive_days.data),
                notes=form.notes.data,
                created_by_id=current_user.id
            )
            db.session.add(policy)
        
        db.session.commit()
        
        # Popola festività italiane per l'anno se non esistono
        LeaveService.populate_italian_holidays(year)
        
        flash(f"Policy per l'anno {year} salvata con successo", "success")
        return redirect(url_for("team.leave_settings", year=year))
    
    # Carica festività per l'anno selezionato
    holidays = ItalianHoliday.query.filter_by(year=selected_year).order_by(ItalianHoliday.date).all()
    
    # Carica tutte le policy esistenti per il dropdown anni
    all_policies = LeavePolicy.query.order_by(LeavePolicy.year.desc()).all()
    
    return render_template(
        "team/leaves/settings.html",
        form=form,
        policy=policy,
        holidays=holidays,
        selected_year=selected_year,
        current_year=current_year,
        all_policies=all_policies,
        HolidayForm=HolidayForm
    )


@team_bp.route("/leaves/holidays/add", methods=["POST"])
@login_required
def add_holiday():
    """Aggiunge una festività/ponte aziendale."""
    _require_admin()
    
    form = HolidayForm()
    if form.validate_on_submit():
        # Verifica che non esista già
        existing = ItalianHoliday.query.filter_by(date=form.date.data).first()
        if existing:
            flash("Esiste già una festività per questa data", "warning")
        else:
            holiday = ItalianHoliday(
                date=form.date.data,
                name=form.name.data,
                is_company_bridge=form.is_company_bridge.data,
                year=form.date.data.year
            )
            db.session.add(holiday)
            db.session.commit()
            flash("Festività aggiunta con successo", "success")
    
    return redirect(url_for("team.leave_settings", year=form.date.data.year))


@team_bp.route("/leaves/holidays/<int:holiday_id>/delete", methods=["POST"])
@login_required
def delete_holiday(holiday_id: int):
    """Elimina una festività (solo ponti aziendali)."""
    _require_admin()
    
    holiday = ItalianHoliday.query.get_or_404(holiday_id)
    
    if not holiday.is_company_bridge:
        flash("Non puoi eliminare le festività nazionali", "warning")
    else:
        year = holiday.year
        db.session.delete(holiday)
        db.session.commit()
        flash("Festività eliminata", "info")
        return redirect(url_for("team.leave_settings", year=year))
    
    return redirect(url_for("team.leave_settings"))


# --------------------------------------------------------------------------- #
#  Richiesta Ferie/Permessi
# --------------------------------------------------------------------------- #

@team_bp.route("/leaves/request", methods=["GET", "POST"])
@login_required
def leave_request():
    """Form per richiesta ferie."""
    form = LeaveRequestForm()

    if request.method == "POST" and form.validate_on_submit():
        # Forza il tipo a "ferie" (ignorando il form)
        leave_type = LeaveTypeEnum.ferie

        # Validazione base date
        if form.start_date.data > form.end_date.data:
            flash("La data di inizio deve essere prima della data di fine", "warning")
            return render_template("team/leaves/request.html", form=form)

        if form.start_date.data < date.today():
            flash("Non puoi richiedere ferie per date passate", "warning")
            return render_template("team/leaves/request.html", form=form)

        # Calcola giorni totali effettivi (inclusi weekend)
        total_days = (form.end_date.data - form.start_date.data).days + 1

        # Determina stato iniziale e primo approvatore in base alla logica aziendale
        initial_status, first_approver_id, approver_desc = LeaveRequest.determine_initial_status_and_approver(current_user)

        # Crea richiesta (sempre di tipo "ferie")
        leave_req = LeaveRequest(
            user_id=current_user.id,
            leave_type=leave_type,
            status=initial_status,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            hours=None,  # Non usato per ferie
            working_days=total_days,  # Giorni totali effettivi
            notes=None,  # Rimosso campo note
            first_approver_id=first_approver_id
        )

        db.session.add(leave_req)
        db.session.commit()

        # Invia notifica appropriata
        LeaveNotificationService.send_request_notification(leave_req)

        flash(f"Richiesta ferie inviata. In attesa di approvazione da: {approver_desc}", "success")
        return redirect(url_for("team.my_leaves"))

    return render_template(
        "team/leaves/request.html",
        form=form
    )


@team_bp.route("/leaves/my-requests")
@login_required
def my_leaves():
    """Le mie richieste ferie."""
    year = request.args.get('year', datetime.now().year, type=int)

    # Le mie richieste
    requests = LeaveRequest.query.filter_by(
        user_id=current_user.id
    ).filter(
        extract('year', LeaveRequest.start_date) == year
    ).order_by(LeaveRequest.created_at.desc()).all()

    return render_template(
        "team/leaves/my_requests.html",
        requests=requests,
        selected_year=year
    )


# --------------------------------------------------------------------------- #
#  Dashboard Approvazioni (role-based)
# --------------------------------------------------------------------------- #

def _is_hr_user(user: User) -> bool:
    """Verifica se l'utente fa parte del dipartimento HR."""
    return user.department and user.department.name == 'HR'


def _can_approve_first_tier(leave_req: LeaveRequest) -> bool:
    """
    Verifica se l'utente corrente può approvare la prima fase.
    Può approvare se:
    - È admin globale
    - È il first_approver designato per questa richiesta
    """
    if current_user.is_admin:
        return True
    if leave_req.first_approver_id == current_user.id:
        return True
    return False


def _can_approve_hr_tier(leave_req: LeaveRequest) -> bool:
    """
    Verifica se l'utente corrente può approvare la fase HR.
    Può approvare se:
    - È admin globale
    - È membro del dipartimento HR
    """
    if current_user.is_admin:
        return True
    if _is_hr_user(current_user):
        return True
    return False


def _is_potential_approver(user: User) -> bool:
    """
    Verifica se l'utente è un potenziale approvatore di ferie.
    Ritorna True se l'utente è:
    - Team Leader (head di un team)
    - Responsabile Dipartimento (head di un dipartimento)
    - CCO o CEO (possono approvare per i rispettivi responsabili)
    """
    from corposostenibile.models import Team

    # È head di un team?
    is_team_leader = Team.query.filter_by(head_id=user.id).first() is not None

    # È head di un dipartimento?
    is_dept_head = Department.query.filter_by(head_id=user.id).first() is not None

    # È CCO o CEO?
    is_cco_ceo = user.department and user.department.name in ('CCO', 'CEO')

    return is_team_leader or is_dept_head or is_cco_ceo


@team_bp.route("/leaves/approvals")
@login_required
def leave_approvals():
    """Dashboard approvazioni richieste (role-based filtering)."""
    # Determina ruolo utente
    is_admin = current_user.is_admin
    is_hr = _is_hr_user(current_user)

    # Verifica se l'utente è un potenziale approvatore (Team Leader, Resp. Dip., CCO, CEO)
    is_potential_approver = _is_potential_approver(current_user)

    # Verifica se ha richieste pending assegnate a lui
    has_pending_requests = LeaveRequest.query.filter(
        LeaveRequest.first_approver_id == current_user.id,
        LeaveRequest.status == LeaveStatusEnum.pending_first_approval
    ).first() is not None

    # Verifica autorizzazione: può accedere se è admin, HR, o potenziale approvatore
    if not (is_admin or is_hr or is_potential_approver):
        flash("Non hai i permessi per accedere a questa pagina", "warning")
        return redirect(url_for("team.team_dashboard"))

    # Filtri
    status_filter = request.args.get('status', 'pending')
    dept_filter = request.args.get('dept', type=int)

    # Query base
    query = LeaveRequest.query.join(User, LeaveRequest.user_id == User.id)

    # Applica scope basato sul ruolo
    # Admin e HR vedono TUTTE le richieste (nessun filtro)
    # Gli altri vedono solo richieste dove sono first_approver
    if not is_admin and not is_hr:
        query = query.filter(LeaveRequest.first_approver_id == current_user.id)

    # Applica filtri stato
    if status_filter == 'pending':
        # Tutti vedono entrambe le fasi pending (ma filtrate per scope sopra)
        query = query.filter(LeaveRequest.status.in_([
            LeaveStatusEnum.pending_first_approval,
            LeaveStatusEnum.pending_hr,
            LeaveStatusEnum.richiesta  # Legacy
        ]))
    elif status_filter and status_filter != 'all':
        query = query.filter(LeaveRequest.status == status_filter)

    if dept_filter:
        query = query.filter(User.department_id == dept_filter)

    # Paginazione
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(LeaveRequest.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    # Dipartimenti per filtro
    departments = Department.query.order_by(Department.name).all()

    return render_template(
        "team/leaves/approvals.html",
        pagination=pagination,
        departments=departments,
        status_filter=status_filter,
        dept_filter=dept_filter,
        LeaveStatusEnum=LeaveStatusEnum,
        is_admin=is_admin,
        is_hr=is_hr,
        is_first_approver=is_potential_approver,
        has_pending_requests=has_pending_requests
    )


@team_bp.route("/leaves/<int:request_id>/approve", methods=["POST"])
@login_required
def approve_leave(request_id: int):
    """Approva una richiesta (single-tier workflow)."""
    leave_req = LeaveRequest.query.get_or_404(request_id)

    # Approvazione diretta (Team Leader / Resp. Dip. / CCO / CEO / Admin)
    if leave_req.status == LeaveStatusEnum.pending_first_approval:
        if not _can_approve_first_tier(leave_req):
            flash("Non hai i permessi per approvare questa richiesta", "warning")
            return redirect(url_for("team.leave_approvals"))

        # Approvazione definitiva
        leave_req.first_approved_at = datetime.utcnow()
        leave_req.approved_by_id = current_user.id
        leave_req.approved_at = datetime.utcnow()
        leave_req.status = LeaveStatusEnum.approvata

        db.session.commit()

        # Notifica dipendente
        LeaveNotificationService.send_approval_notification(leave_req)

        flash(f"Richiesta di {leave_req.user.full_name} approvata", "success")

    # LEGACY: Richieste vecchie pending_hr - permettiamo a admin/HR di approvarle
    elif leave_req.status == LeaveStatusEnum.pending_hr:
        if not _can_approve_hr_tier(leave_req):
            flash("Non hai i permessi per approvare questa richiesta", "warning")
            return redirect(url_for("team.leave_approvals"))

        leave_req.approved_by_id = current_user.id
        leave_req.approved_at = datetime.utcnow()
        leave_req.status = LeaveStatusEnum.approvata

        db.session.commit()
        LeaveNotificationService.send_approval_notification(leave_req)

        flash(f"Richiesta di {leave_req.user.full_name} approvata", "success")

    # LEGACY: Approvazione single-tier vecchio sistema
    elif leave_req.status == LeaveStatusEnum.richiesta:
        if not _can_approve_hr_tier(leave_req):
            flash("Non hai i permessi per approvare questa richiesta", "warning")
            return redirect(url_for("team.leave_approvals"))

        leave_req.status = LeaveStatusEnum.approvata
        leave_req.approved_by_id = current_user.id
        leave_req.approved_at = datetime.utcnow()

        db.session.commit()
        LeaveNotificationService.send_approval_notification(leave_req)

        flash(f"Richiesta di {leave_req.user.full_name} approvata", "success")

    else:
        flash("Questa richiesta è già stata processata", "warning")

    return redirect(url_for("team.leave_approvals"))


@team_bp.route("/leaves/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_leave(request_id: int):
    """Rifiuta una richiesta (two-tier workflow)."""
    leave_req = LeaveRequest.query.get_or_404(request_id)

    # Verifica stato
    if leave_req.status not in [
        LeaveStatusEnum.pending_first_approval,
        LeaveStatusEnum.pending_hr,
        LeaveStatusEnum.richiesta  # Legacy
    ]:
        flash("Questa richiesta è già stata processata", "warning")
        return redirect(url_for("team.leave_approvals"))

    # Verifica autorizzazione
    if leave_req.status == LeaveStatusEnum.pending_first_approval:
        if not _can_approve_first_tier(leave_req):
            flash("Non hai i permessi per rifiutare questa richiesta", "warning")
            return redirect(url_for("team.leave_approvals"))
    elif leave_req.status in [LeaveStatusEnum.pending_hr, LeaveStatusEnum.richiesta]:
        if not _can_approve_hr_tier(leave_req):
            flash("Non hai i permessi per rifiutare questa richiesta", "warning")
            return redirect(url_for("team.leave_approvals"))

    # Motivazione obbligatoria
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash("Devi specificare una motivazione per il rifiuto", "warning")
        return redirect(url_for("team.leave_approvals"))

    # Rifiuta la richiesta
    leave_req.status = LeaveStatusEnum.rifiutata
    leave_req.rejection_reason = reason
    leave_req.approved_by_id = current_user.id
    leave_req.approved_at = datetime.utcnow()

    db.session.commit()

    # Notifica dipendente
    LeaveNotificationService.send_rejection_notification(leave_req)

    flash(f"Richiesta di {leave_req.user.full_name} rifiutata", "info")
    return redirect(url_for("team.leave_approvals"))


# --------------------------------------------------------------------------- #
#  Report Assenze
# --------------------------------------------------------------------------- #

@team_bp.route("/leaves/report")
@login_required
def leave_report():
    """Report assenze per dipartimento."""
    _require_admin()

    # Parametri
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    dept_id = request.args.get('dept', type=int)

    # Dati calendario
    calendar_data = LeaveService.get_team_calendar_data(month, year, dept_id)

    # Statistiche per dipartimento
    dept_stats = db.session.query(
        Department.name,
        func.count(LeaveRequest.id).label('total_requests'),
        func.sum(LeaveRequest.working_days).label('total_days')
    ).join(
        User, User.department_id == Department.id
    ).join(
        LeaveRequest, LeaveRequest.user_id == User.id
    ).filter(
        LeaveRequest.status == LeaveStatusEnum.approvata,
        extract('year', LeaveRequest.start_date) == year
    ).group_by(Department.name).all()

    # Dipartimenti per filtro
    departments = Department.query.order_by(Department.name).all()

    return render_template(
        "team/leaves/report.html",
        calendar_data=calendar_data,
        dept_stats=dept_stats,
        departments=departments,
        selected_year=year,
        selected_month=month,
        selected_dept=dept_id
    )


@team_bp.route("/leaves/calendar")
@login_required
def leaves_calendar():
    """Calendario ferie team con filtro dipartimento (role-based)."""
    from corposostenibile.models import Team
    import calendar
    from collections import defaultdict

    # Determina ruolo utente
    is_admin = current_user.is_admin
    is_hr = _is_hr_user(current_user)
    is_potential_approver = _is_potential_approver(current_user)

    # Verifica autorizzazione
    if not (is_admin or is_hr or is_potential_approver):
        flash("Non hai i permessi per accedere a questa pagina", "warning")
        return redirect(url_for("team.team_dashboard"))

    # Parametri
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    dept_id = request.args.get('dept', type=int)

    # Dipartimenti per filtro (solo per admin/HR)
    if is_admin or is_hr:
        departments = Department.query.order_by(Department.name).all()
    else:
        # Non-admin vedono solo il proprio dipartimento
        departments = [current_user.department] if current_user.department else []

    # Calcola primo e ultimo giorno del mese
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    # Query ferie approvate per il mese
    query = db.session.query(LeaveRequest).join(User, LeaveRequest.user_id == User.id).filter(
        LeaveRequest.status == LeaveStatusEnum.approvata,
        or_(
            and_(
                extract('month', LeaveRequest.start_date) == month,
                extract('year', LeaveRequest.start_date) == year
            ),
            and_(
                extract('month', LeaveRequest.end_date) == month,
                extract('year', LeaveRequest.end_date) == year
            ),
            and_(
                LeaveRequest.start_date < first_day,
                LeaveRequest.end_date >= first_day
            )
        )
    )

    # Applica scope basato sul ruolo
    if not is_admin and not is_hr:
        # Determina quali utenti può vedere questo approvatore
        user_dept = current_user.department

        if user_dept and user_dept.name in ('Nutrizione', 'Nutrizione 2'):
            # Team Leader Nutrizione: vede solo membri del suo team
            team_led = Team.query.filter_by(head_id=current_user.id).first()
            if team_led:
                query = query.filter(User.team_id == team_led.id)
            else:
                # Responsabile Dipartimento Nutrizione: vede tutto il dipartimento
                query = query.filter(User.department_id == user_dept.id)
        else:
            # Responsabile altri dipartimenti: vede tutto il suo dipartimento
            if user_dept:
                query = query.filter(User.department_id == user_dept.id)

    # Filtro dipartimento manuale (solo per admin/HR)
    if dept_id and (is_admin or is_hr):
        query = query.filter(User.department_id == dept_id)

    leave_requests = query.all()

    # Organizza ferie per giorno
    leaves_by_day = defaultdict(list)
    for req in leave_requests:
        # Calcola range di date per questa richiesta
        start = max(req.start_date, first_day)
        end = min(req.end_date, last_day)

        current = start
        while current <= end:
            leaves_by_day[current.day].append({
                'user': req.user,
                'start_date': req.start_date,
                'end_date': req.end_date,
                'working_days': req.working_days,
                'leave_type': req.leave_type
            })
            current += timedelta(days=1)

    # Calcola giorni del mese
    days_in_month = calendar.monthrange(year, month)[1]
    first_weekday = calendar.monthrange(year, month)[0]  # 0 = Monday

    # Mese precedente e successivo
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    # Nome mese
    month_names = ['', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
                   'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
    month_name = month_names[month]

    # Statistiche
    total_people_off = len(set(req.user_id for req in leave_requests))
    total_days_off = sum(req.working_days or 0 for req in leave_requests)

    # Giorno corrente
    today = date.today()
    current_day = today.day if today.year == year and today.month == month else None

    return render_template(
        "team/leaves/calendar.html",
        leave_requests=leave_requests,
        leaves_by_day=dict(leaves_by_day),
        departments=departments,
        selected_year=year,
        selected_month=month,
        selected_dept=dept_id,
        year=year,
        month=month,
        month_name=month_name,
        days_in_month=days_in_month,
        first_weekday=first_weekday,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        total_people_off=total_people_off,
        total_days_off=total_days_off,
        current_day=current_day,
        now=datetime.now(),
        LeaveTypeEnum=LeaveTypeEnum,
        is_admin=is_admin,
        is_hr=is_hr
    )


# --------------------------------------------------------------------------- #
#  API Endpoints
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
#  Dashboard Team Analytics Avanzata
# --------------------------------------------------------------------------- #

@team_bp.route("/analytics", methods=["GET"])
@team_bp.route("/analytics-dashboard", methods=["GET"])
@login_required
def team_analytics_dashboard() -> str:
    """
    Dashboard Team Analytics con filtri avanzati e visualizzazioni interattive.
    """
    _require_admin()

    from corposostenibile.models import (
        Objective, KeyResult, OKRStatusEnum,
        LeaveRequest, LeaveStatusEnum, LeaveTypeEnum,
        Certification, HRNote
    )
    from datetime import date, timedelta, datetime
    from sqlalchemy import case, distinct, cast, Float, or_
    from decimal import Decimal
    import json

    # ─────────────────── FILTRI ──────────────────────────
    # Periodo
    period_filter = request.args.get('period', '30')  # 30, 90, 365, ytd, all
    dept_filter = request.args.getlist('dept')  # Multi-select departments
    contract_filter = request.args.get('contract')
    active_filter = request.args.get('active', '1')  # Default: only active

    # Calcola date range
    today = date.today()
    if period_filter == 'ytd':
        start_date = date(today.year, 1, 1)
        end_date = today
    elif period_filter == 'all':
        start_date = date(2020, 1, 1)
        end_date = today
    else:
        days = int(period_filter)
        start_date = today - timedelta(days=days)
        end_date = today

    # ─────────────────── 1) WORKFORCE METRICS ──────────────────────────

    # Total headcount con filtri
    users_query = User.query
    if active_filter == '1':
        users_query = users_query.filter(User.is_active == True)
    if dept_filter:
        users_query = users_query.filter(User.department_id.in_(dept_filter))
    if contract_filter:
        users_query = users_query.filter(User.contract_type == contract_filter)

    # Sottrai 2 utenti di test dal conteggio
    total_users = max(0, users_query.count() - 2)  # Assicura che non sia negativo
    active_users = max(0, users_query.filter(User.is_active == True).count() - 2)

    # Growth metrics
    new_hires = users_query.filter(
        User.hired_at >= start_date,
        User.hired_at <= end_date
    ).count()

    # Turnover
    inactive_users = User.query.filter(
        User.is_active == False,
        User.updated_at >= start_date
    ).count()

    # Usa il totale reale (prima della sottrazione) per il calcolo del turnover
    total_users_real = users_query.count()
    turnover_rate = round((inactive_users / total_users_real * 100) if total_users_real > 0 else 0, 1)

    # Average tenure - calcola correttamente i giorni totali
    avg_tenure_days = db.session.query(
        func.avg(
            func.extract('epoch', func.now() - User.hired_at) / 86400  # converte secondi in giorni
        )
    ).filter(User.hired_at.isnot(None)).scalar() or 0
    avg_tenure_years = round(avg_tenure_days / 365, 1)

    # Compensation metrics
    total_cost = db.session.query(
        func.sum(User.ral_annua)
    ).filter(
        User.ral_annua.isnot(None),
        User.is_active == True
    ).scalar() or 0

    avg_salary = db.session.query(
        func.avg(User.ral_annua)
    ).filter(
        User.ral_annua.isnot(None),
        User.is_active == True
    ).scalar() or 0

    # ─────────────────── 2) DEPARTMENT BREAKDOWN ──────────────────────────

    # Escludi dipartimenti CEO, Co-Founder e Test
    excluded_departments = ['CEO', 'Co-Founder', 'Test']

    dept_stats = db.session.query(
        Department.id,
        Department.name,
        func.count(User.id).label('headcount'),
        func.count(User.id).filter(User.is_active == True).label('active_count'),
        func.avg(User.ral_annua).label('avg_salary'),
        func.sum(User.ral_annua).label('total_cost')
    ).outerjoin(
        User, User.department_id == Department.id
    ).filter(
        ~Department.name.in_(excluded_departments)  # Escludi i dipartimenti non desiderati
    ).group_by(
        Department.id, Department.name
    ).order_by(func.count(User.id).desc()).all()

    # ─────────────────── 3) SKILLS & COMPETENCIES ──────────────────────────

    # Languages distribution
    language_stats = {}
    all_languages = db.session.query(User.languages).filter(
        User.languages.isnot(None),
        User.is_active == True
    ).all()

    for user_langs in all_languages:
        if user_langs[0]:
            for lang in user_langs[0]:
                language_stats[lang] = language_stats.get(lang, 0) + 1

    # Certifications status
    cert_stats = db.session.query(
        func.count(distinct(Certification.id)).label('total_certs'),
        func.count(distinct(User.id)).label('users_with_certs')
    ).select_from(Certification).join(
        Certification.users
    ).filter(User.is_active == True).first()

    # Education levels
    education_stats = db.session.query(
        func.count(User.id).filter(User.education_degrees.isnot(None)).label('with_degree'),
        func.count(User.id).filter(User.education_masters.isnot(None)).label('with_master'),
        func.count(User.id).filter(User.education_phd.isnot(None)).label('with_phd')
    ).filter(User.is_active == True).first()

    # ─────────────────── 4) PERFORMANCE METRICS ──────────────────────────

    # OKR Achievement
    okr_stats = db.session.query(
        func.count(Objective.id).label('total'),
        func.count(Objective.id).filter(
            Objective.status == OKRStatusEnum.completed
        ).label('completed'),
        func.count(Objective.id).filter(
            Objective.status == OKRStatusEnum.active
        ).label('active')
    ).first()

    okr_achievement_rate = round(
        (okr_stats.completed / okr_stats.total * 100) if okr_stats.total > 0 else 0, 1
    )

    # Weekly Reports Compliance
    from corposostenibile.blueprints.team.models.weekly_report import WeeklyReport

    # Find the first report date to calculate compliance from that point
    first_report_date = db.session.query(func.min(WeeklyReport.submission_date)).scalar()

    if first_report_date:
        # Calculate weeks since first report
        weeks_since_start = max(1, (datetime.now() - first_report_date).days // 7)
        total_expected_reports = total_users * weeks_since_start
        total_submitted_reports = WeeklyReport.query.count()

        report_compliance_rate = round(
            (total_submitted_reports / total_expected_reports * 100)
            if total_expected_reports > 0 else 0, 1
        )
    else:
        report_compliance_rate = 0
        weeks_since_start = 0

    # Calculate compliance per department
    dept_compliance = db.session.query(
        Department.id,
        Department.name,
        func.count(distinct(User.id)).label('total_users'),
        func.count(WeeklyReport.id).label('submitted_reports')
    ).outerjoin(User, Department.id == User.department_id)\
     .outerjoin(WeeklyReport, User.id == WeeklyReport.user_id)\
     .filter(
        Department.name.notin_(['CEO', 'Co-Founder', 'Test']),
        or_(User.is_active == True, User.is_active == None)
     ).group_by(Department.id, Department.name)\
     .having(func.count(distinct(User.id)) > 0).all()

    # Calculate compliance percentage per department
    dept_compliance_stats = []
    for dept in dept_compliance:
        if first_report_date and weeks_since_start > 0:
            expected_reports = dept.total_users * weeks_since_start
            compliance_pct = round(
                (dept.submitted_reports / expected_reports * 100)
                if expected_reports > 0 else 0, 1
            )
        else:
            compliance_pct = 0

        dept_compliance_stats.append({
            'id': dept.id,
            'name': dept.name,
            'total_users': dept.total_users,
            'submitted_reports': dept.submitted_reports,
            'compliance_pct': compliance_pct
        })

    # ─────────────────── 5) TIME & ATTENDANCE ──────────────────────────

    # Leave statistics
    leave_stats = db.session.query(
        func.count(LeaveRequest.id).label('total_requests'),
        func.sum(LeaveRequest.working_days).filter(
            LeaveRequest.leave_type == LeaveTypeEnum.ferie
        ).label('vacation_days'),
        func.sum(LeaveRequest.hours).filter(
            LeaveRequest.leave_type == LeaveTypeEnum.permesso
        ).label('permission_hours'),
        func.count(distinct(LeaveRequest.user_id)).label('users_on_leave')
    ).filter(
        LeaveRequest.status == LeaveStatusEnum.approvata,
        LeaveRequest.start_date >= start_date,
        LeaveRequest.end_date <= end_date
    ).first()

    # Current absences
    current_absences = LeaveRequest.query.filter(
        LeaveRequest.status == LeaveStatusEnum.approvata,
        LeaveRequest.start_date <= today,
        LeaveRequest.end_date >= today
    ).count()

    # ─────────────────── 6) DEMOGRAPHICS ──────────────────────────

    # Age distribution
    age_ranges = db.session.query(
        func.count(User.id).filter(
            func.date_part('year', func.age(User.birth_date)) < 25
        ).label('under_25'),
        func.count(User.id).filter(
            func.date_part('year', func.age(User.birth_date)).between(25, 34)
        ).label('25_34'),
        func.count(User.id).filter(
            func.date_part('year', func.age(User.birth_date)).between(35, 44)
        ).label('35_44'),
        func.count(User.id).filter(
            func.date_part('year', func.age(User.birth_date)).between(45, 54)
        ).label('45_54'),
        func.count(User.id).filter(
            func.date_part('year', func.age(User.birth_date)) >= 55
        ).label('over_55')
    ).filter(
        User.birth_date.isnot(None),
        User.is_active == True
    ).first()

    # Contract types distribution
    contract_distribution = db.session.query(
        User.contract_type,
        func.count(User.id).label('count')
    ).filter(
        User.is_active == True
    ).group_by(User.contract_type).all()

    # ─────────────────── 7) TOP PERFORMERS ──────────────────────────

    # Based on OKR completion and weekly reports
    top_performers = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        User.job_title,
        User.avatar_path,
        Department.name.label('dept_name'),
        func.count(distinct(Objective.id)).filter(
            Objective.status == OKRStatusEnum.completed
        ).label('completed_okrs'),
        func.count(distinct(WeeklyReport.id)).label('reports_submitted')
    ).outerjoin(
        Department, User.department_id == Department.id
    ).outerjoin(
        Objective, Objective.user_id == User.id
    ).outerjoin(
        WeeklyReport, WeeklyReport.user_id == User.id
    ).filter(
        User.is_active == True
    ).group_by(
        User.id, User.first_name, User.last_name,
        User.job_title, User.avatar_path, Department.name
    ).order_by(
        func.count(distinct(Objective.id)).filter(
            Objective.status == OKRStatusEnum.completed
        ).desc()
    ).limit(10).all()

    # ─────────────────── 8) TRENDS DATA ──────────────────────────

    # Monthly headcount trend (last 12 months)
    headcount_trend = []
    for i in range(11, -1, -1):
        month_date = today - timedelta(days=i*30)
        month_count = User.query.filter(
            User.hired_at <= month_date,
            or_(User.is_active == True, User.updated_at > month_date)
        ).count()
        headcount_trend.append({
            'month': month_date.strftime('%b'),
            'count': month_count
        })

    # OKR progress trend
    okr_trend = []
    for i in range(11, -1, -1):
        month_date = today - timedelta(days=i*30)
        month_okrs = Objective.query.filter(
            Objective.created_at <= month_date
        ).count()
        completed_okrs = Objective.query.filter(
            Objective.created_at <= month_date,
            Objective.status == OKRStatusEnum.completed
        ).count()
        okr_trend.append({
            'month': month_date.strftime('%b'),
            'total': month_okrs,
            'completed': completed_okrs
        })

    # ─────────────────── 9) PREPARE DATA FOR TEMPLATE ──────────────────────────

    # All departments for filters
    all_departments = Department.query.order_by(Department.name).all()

    # Prepare context
    context = {
        # Filters
        'period_filter': period_filter,
        'dept_filter': dept_filter,
        'contract_filter': contract_filter,
        'active_filter': active_filter,
        'all_departments': all_departments,

        # Workforce metrics
        'total_users': total_users,
        'active_users': active_users,
        'new_hires': new_hires,
        'turnover_rate': turnover_rate,
        'avg_tenure_years': avg_tenure_years,
        'total_cost': float(total_cost) if total_cost else 0,
        'avg_salary': float(avg_salary) if avg_salary else 0,

        # Department stats
        'dept_stats': dept_stats,

        # Skills & Competencies
        'language_stats': language_stats,
        'cert_stats': cert_stats,
        'education_stats': education_stats,

        # Performance
        'okr_stats': okr_stats,
        'okr_achievement_rate': okr_achievement_rate,
        'report_compliance_rate': report_compliance_rate,
        'dept_compliance_stats': dept_compliance_stats,

        # Time & Attendance
        'leave_stats': leave_stats,
        'current_absences': current_absences,

        # Demographics
        'age_ranges': age_ranges,
        'contract_distribution': contract_distribution,

        # Top performers
        'top_performers': top_performers,

        # Trends (JSON for charts)
        'headcount_trend_json': json.dumps(headcount_trend),
        'okr_trend_json': json.dumps(okr_trend),

        # Dates
        'start_date': start_date,
        'end_date': end_date,
        'today': today
    }

    return render_template("team/analytics_dashboard.html", **context)


@team_bp.route("/scientific-dashboard")
@login_required
def scientific_dashboard():
    """
    Dashboard scientifica per i dipartimenti Coach, Nutrizione e Psicologia.
    Mostra competenze accademiche, certificazioni, pubblicazioni e ricerca.
    Accessibile a: Admin e membri del dipartimento CCO (id=23).
    """
    # Verifica permessi: admin o membro del dipartimento CCO (id=23)
    if not (current_user.is_admin or (current_user.department_id == 23)):
        abort(HTTPStatus.FORBIDDEN)

    # Filter per dipartimento
    dept_filter = request.args.get('department', 'all')

    # Dipartimenti target
    target_departments = ['Coach', 'Nutrizione', 'Psicologia']

    # Base query per utenti dei dipartimenti scientifici
    users_query = User.query.join(Department, User.department_id == Department.id).filter(
        Department.name.in_(target_departments),
        User.is_active == True
    )

    # Applica filtro dipartimento se specificato
    if dept_filter != 'all' and dept_filter in target_departments:
        users_query = users_query.filter(Department.name == dept_filter)

    users = users_query.all()

    # ─────────────────── 1) TITOLI ACCADEMICI ──────────────────────────

    # Conteggio titoli per dipartimento
    academic_stats = {}
    degree_details = {}
    master_details = {}
    phd_details = {}

    for dept_name in target_departments:
        dept_users = [u for u in users if u.department and u.department.name == dept_name]

        # Conteggi base
        total_users = len(dept_users)
        users_with_degree = sum(1 for u in dept_users if u.education_degrees)
        users_with_master = sum(1 for u in dept_users if u.education_masters)
        users_with_phd = sum(1 for u in dept_users if u.education_phd)

        academic_stats[dept_name] = {
            'total_users': total_users,
            'degrees': users_with_degree,
            'masters': users_with_master,
            'phds': users_with_phd,
            'master_rate': round((users_with_master / total_users * 100) if total_users > 0 else 0, 1),
            'phd_rate': round((users_with_phd / total_users * 100) if total_users > 0 else 0, 1)
        }

        # Dettagli lauree
        degrees = {}
        for user in dept_users:
            if user.education_degrees:
                try:
                    if isinstance(user.education_degrees, list):
                        for degree in user.education_degrees:
                            if isinstance(degree, dict):
                                degree_name = degree.get('degree') or degree.get('name') or degree.get('title', 'Laurea')
                                degrees[degree_name] = degrees.get(degree_name, 0) + 1
                except:
                    pass
        degree_details[dept_name] = sorted(degrees.items(), key=lambda x: x[1], reverse=True)

        # Dettagli master
        masters = {}
        for user in dept_users:
            if user.education_masters:
                try:
                    if isinstance(user.education_masters, list):
                        for master in user.education_masters:
                            if isinstance(master, dict):
                                master_name = master.get('master') or master.get('name') or master.get('title', 'Master')
                                masters[master_name] = masters.get(master_name, 0) + 1
                except:
                    pass
        master_details[dept_name] = sorted(masters.items(), key=lambda x: x[1], reverse=True)

        # Dettagli PhD
        phds = {}
        for user in dept_users:
            if user.education_phd:
                try:
                    if isinstance(user.education_phd, list):
                        for phd in user.education_phd:
                            if isinstance(phd, dict):
                                phd_name = phd.get('phd') or phd.get('name') or phd.get('title', 'PhD')
                                phds[phd_name] = phds.get(phd_name, 0) + 1
                except:
                    pass
        phd_details[dept_name] = sorted(phds.items(), key=lambda x: x[1], reverse=True)

    # ─────────────────── 2) CERTIFICAZIONI E CORSI ──────────────────────────

    # Certificazioni e Corsi per dipartimento
    cert_stats = {}
    cert_details = {}
    course_stats = {}
    course_details = {}

    for dept_name in target_departments:
        dept_users = [u for u in users if u.department and u.department.name == dept_name]

        # Conta certificazioni dal campo JSON education_certifications
        certifications = {}
        total_certs = 0
        users_with_certs = 0

        for user in dept_users:
            if user.education_certifications:
                try:
                    if isinstance(user.education_certifications, list) and user.education_certifications:
                        users_with_certs += 1
                        for cert in user.education_certifications:
                            if isinstance(cert, dict):
                                cert_name = cert.get('name') or cert.get('title') or 'Certificazione'
                                certifications[cert_name] = certifications.get(cert_name, 0) + 1
                                total_certs += 1
                except:
                    pass

        cert_stats[dept_name] = {
            'total_certifications': total_certs,
            'users_with_certs': users_with_certs,
            'total_people_with_certifications': users_with_certs,  # Per compatibilità con il grafico
            'cert_rate': round((users_with_certs / len(dept_users) * 100) if dept_users else 0, 1)
        }
        cert_details[dept_name] = sorted(certifications.items(), key=lambda x: x[1], reverse=True)

        # Conta corsi di formazione dal campo JSON education_courses
        courses = {}
        total_courses = 0
        users_with_courses = 0

        for user in dept_users:
            if user.education_courses:
                try:
                    if isinstance(user.education_courses, list) and user.education_courses:
                        users_with_courses += 1
                        for course in user.education_courses:
                            if isinstance(course, dict):
                                course_name = course.get('name') or course.get('title') or 'Corso'
                                courses[course_name] = courses.get(course_name, 0) + 1
                                total_courses += 1
                except:
                    pass

        course_stats[dept_name] = {
            'total_courses': total_courses,
            'users_with_courses': users_with_courses,
            'course_rate': round((users_with_courses / len(dept_users) * 100) if dept_users else 0, 1)
        }
        course_details[dept_name] = sorted(courses.items(), key=lambda x: x[1], reverse=True)

    # ─────────────────── 3) RICERCA & PUBBLICAZIONI ──────────────────────────

    research_stats = {}
    for dept_name in target_departments:
        dept_users = [u for u in users if u.department and u.department.name == dept_name]

        # Conteggi ricerca e pubblicazioni
        clinical_research = sum(1 for u in dept_users if getattr(u, 'has_clinical_research', False))
        publications = sum(1 for u in dept_users if getattr(u, 'has_scientific_publications', False))
        training_exp = sum(1 for u in dept_users if getattr(u, 'has_teaching_experience', False))

        research_stats[dept_name] = {
            'total_users': len(dept_users),
            'clinical_research': clinical_research,
            'publications': publications,
            'training_experience': training_exp,
            'research_rate': round((clinical_research / len(dept_users) * 100) if dept_users else 0, 1),
            'publication_rate': round((publications / len(dept_users) * 100) if dept_users else 0, 1),
            'training_rate': round((training_exp / len(dept_users) * 100) if dept_users else 0, 1)
        }

    # ─────────────────── 4) TREND TEMPORALE BASATO SU DATA ASSUNZIONE ──────────────────────────

    from datetime import datetime, timedelta
    import calendar

    # Calcola trend ultimi 12 mesi basato su data assunzione PER DIPARTIMENTO
    trend_data = []
    trend_data_by_dept = {}  # Trend separato per dipartimento
    today = datetime.now()

    for i in range(11, -1, -1):  # Ultimi 12 mesi
        # Calcola la data di riferimento (fine del mese)
        month_date = today - timedelta(days=i*30)
        month_end = datetime(month_date.year, month_date.month,
                            calendar.monthrange(month_date.year, month_date.month)[1])

        # Filtra utenti dei 3 dipartimenti scientifici assunti prima di questa data
        active_users = [u for u in users if u.hired_at and u.hired_at <= month_end]

        # Statistiche aggregate per tutti i dipartimenti - COERENTI: contano PERSONE
        month_stats = {
            'date': month_end.strftime('%Y-%m'),
            'month_name': month_end.strftime('%b'),
            'phds': sum(1 for u in active_users if u.education_phd),
            'masters': sum(1 for u in active_users if u.education_masters),
            'degrees': sum(1 for u in active_users if u.education_degrees),
            # CORREZIONE: Conta PERSONE certificate, non totale certificazioni
            'certifications': sum(1 for u in active_users if u.education_certifications and len(u.education_certifications) > 0),
            'courses': sum(1 for u in active_users if u.education_courses and len(u.education_courses) > 0),
            'total_users': len(active_users)
        }

        # Calcola persone con almeno una qualifica (più sensato del totale)
        qualified_users = [u for u in active_users if
                          u.education_phd or u.education_masters or u.education_degrees or
                          (u.education_certifications and len(u.education_certifications) > 0) or
                          (u.education_courses and len(u.education_courses) > 0)]
        month_stats['total'] = len(qualified_users)

        trend_data.append(month_stats)

        # Calcola anche per singolo dipartimento
        for dept_name in target_departments:
            if dept_name not in trend_data_by_dept:
                trend_data_by_dept[dept_name] = []

            dept_active_users = [u for u in active_users if u.department and u.department.name == dept_name]

            dept_month_stats = {
                'date': month_end.strftime('%Y-%m'),
                'month_name': month_end.strftime('%b'),
                'phds': sum(1 for u in dept_active_users if u.education_phd),
                'masters': sum(1 for u in dept_active_users if u.education_masters),
                'degrees': sum(1 for u in dept_active_users if u.education_degrees),
                # CORREZIONE: Conta PERSONE certificate per dipartimento
                'certifications': sum(1 for u in dept_active_users if u.education_certifications and len(u.education_certifications) > 0),
                'courses': sum(1 for u in dept_active_users if u.education_courses and len(u.education_courses) > 0),
                'total_users': len(dept_active_users)
            }

            # Calcola persone qualificate nel dipartimento
            dept_qualified_users = [u for u in dept_active_users if
                                   u.education_phd or u.education_masters or u.education_degrees or
                                   (u.education_certifications and len(u.education_certifications) > 0) or
                                   (u.education_courses and len(u.education_courses) > 0)]
            dept_month_stats['total'] = len(dept_qualified_users)

            trend_data_by_dept[dept_name].append(dept_month_stats)

    # ─────────────────── 5) TOTALI GENERALI ──────────────────────────

    total_users = len(users)
    total_phd = sum(stats['phds'] for stats in academic_stats.values())
    total_masters = sum(stats['masters'] for stats in academic_stats.values())
    total_certs = sum(stats['total_certifications'] for stats in cert_stats.values())
    total_courses = sum(stats['total_courses'] for stats in course_stats.values())
    total_publications = sum(stats['publications'] for stats in research_stats.values())
    total_research = sum(stats['clinical_research'] for stats in research_stats.values())

    # ─────────────────── 5) TEAM MEMBERS DETTAGLIO ──────────────────────────

    # Calcola punteggio scientifico per ogni membro
    team_members = []
    for user in users:
        score = 0

        # FORMAZIONE ACCADEMICA (max 50 punti - solo il più alto conta)
        if user.education_phd:
            score += 50  # PhD vale 50 punti
        elif user.education_masters:
            score += 30  # Master vale 30 punti (solo se non ha PhD)
        elif user.education_degrees:
            score += 20  # Laurea vale 20 punti (solo se non ha Master/PhD)

        # CERTIFICAZIONI (3 punti ciascuna, max 15 punti totali)
        user_certs = 0
        if user.education_certifications:
            try:
                if isinstance(user.education_certifications, list):
                    user_certs = len(user.education_certifications)
            except:
                pass
        score += min(user_certs * 3, 15)  # Max 15 punti per certificazioni

        # CORSI DI FORMAZIONE (1 punto per corso, max 5 punti totali)
        user_courses = 0
        if user.education_courses:
            try:
                if isinstance(user.education_courses, list):
                    user_courses = len(user.education_courses)
            except:
                pass
        score += min(user_courses * 1, 5)  # Max 5 punti per corsi

        # RICERCA & PUBBLICAZIONI (10 punti ciascuno)
        if getattr(user, 'has_clinical_research', False): score += 10
        if getattr(user, 'has_scientific_publications', False): score += 10
        if getattr(user, 'has_teaching_experience', False): score += 10

        team_members.append({
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'department': user.department.name if user.department else '',
            'job_title': user.job_title,
            'has_degree': bool(user.education_degrees),
            'has_master': bool(user.education_masters),
            'has_phd': bool(user.education_phd),
            'certifications_count': user_certs,
            'has_research': getattr(user, 'has_clinical_research', False),
            'has_publications': getattr(user, 'has_scientific_publications', False),
            'has_training': getattr(user, 'has_teaching_experience', False),
            'scientific_score': min(score, 100)  # Cap a 100
        })

    # Ordina per punteggio
    team_members.sort(key=lambda x: x['scientific_score'], reverse=True)

    # ─────────────────── 7) PREPARE CONTEXT ──────────────────────────

    # Calcola statistiche trend
    if trend_data:
        current_month = trend_data[-1]
        previous_month = trend_data[-2] if len(trend_data) > 1 else trend_data[-1]

        trend_growth = current_month['total'] - previous_month['total']
        trend_growth_pct = round((trend_growth / previous_month['total'] * 100) if previous_month['total'] > 0 else 0, 1)
        trend_total_current = current_month['total']
    else:
        trend_growth = 0
        trend_growth_pct = 0
        trend_total_current = 0

    context = {
        # Filtri
        'dept_filter': dept_filter,
        'target_departments': target_departments,

        # Statistiche generali
        'total_users': total_users,
        'total_phd': total_phd,
        'total_masters': total_masters,
        'total_certifications': total_certs,
        'total_courses': total_courses,
        'total_publications': total_publications,
        'total_research': total_research,

        # Tassi generali
        'phd_rate': round((total_phd / total_users * 100) if total_users > 0 else 0, 1),
        'cert_rate': round((sum(stats['users_with_certs'] for stats in cert_stats.values()) / total_users * 100) if total_users > 0 else 0, 1),
        'course_rate': round((sum(stats['users_with_courses'] for stats in course_stats.values()) / total_users * 100) if total_users > 0 else 0, 1),
        'publication_rate': round((total_publications / total_users * 100) if total_users > 0 else 0, 1),
        'research_rate': round((total_research / total_users * 100) if total_users > 0 else 0, 1),

        # Dati per dipartimento
        'academic_stats': academic_stats,
        'cert_stats': cert_stats,
        'course_stats': course_stats,
        'research_stats': research_stats,

        # Dettagli competenze
        'degree_details': degree_details,
        'master_details': master_details,
        'phd_details': phd_details,
        'cert_details': cert_details,
        'course_details': course_details,

        # Dati trend
        'trend_data': trend_data,
        'trend_data_by_dept': trend_data_by_dept,
        'trend_growth': trend_growth,
        'trend_growth_pct': trend_growth_pct,
        'trend_total_current': trend_total_current,

        # Team members
        'team_members': team_members[:20],  # Top 20

        # Dati per grafici (JSON)
        'academic_stats_json': json.dumps(academic_stats),
        'cert_stats_json': json.dumps(cert_stats),
        'course_stats_json': json.dumps(course_stats),
        'research_stats_json': json.dumps(research_stats),
        'trend_data_json': json.dumps(trend_data),
        'trend_data_by_dept_json': json.dumps(trend_data_by_dept)
    }

    return render_template("team/scientific_dashboard.html", **context)


@team_bp.route("/api/member/<int:user_id>/scientific-profile")
@login_required
def get_member_scientific_profile(user_id: int) -> dict:
    """
    API endpoint per recuperare il profilo scientifico dettagliato di un membro.
    Accessibile a: Admin e membri del dipartimento CCO (id=23).
    """
    # Verifica permessi: admin o membro del dipartimento CCO (id=23)
    if not (current_user.is_admin or (current_user.department_id == 23)):
        abort(HTTPStatus.FORBIDDEN)

    # Recupera l'utente
    user = User.query.get_or_404(user_id)

    # ─────────────────── FORMAZIONE ACCADEMICA ──────────────────────────

    # Lauree
    degrees = []
    if user.education_degrees:
        try:
            if isinstance(user.education_degrees, list):
                for degree in user.education_degrees:
                    if isinstance(degree, dict):
                        degrees.append({
                            'type': degree.get('type', 'Laurea'),
                            'university': degree.get('university', ''),
                            'course': degree.get('course', ''),
                            'year': degree.get('year', '')
                        })
        except:
            pass

    # Master
    masters = []
    if user.education_masters:
        try:
            if isinstance(user.education_masters, list):
                for master in user.education_masters:
                    if isinstance(master, dict):
                        masters.append({
                            'name': master.get('name', 'Master'),
                            'institute': master.get('institute', ''),
                            'year': master.get('year', '')
                        })
        except:
            pass

    # PhD
    phd = {}
    if user.education_phd:
        try:
            if isinstance(user.education_phd, dict):
                phd = {
                    'title': user.education_phd.get('title', ''),
                    'university': user.education_phd.get('university', ''),
                    'year': user.education_phd.get('year', '')
                }
        except:
            pass

    # Certificazioni
    certifications = []
    if user.education_certifications:
        try:
            if isinstance(user.education_certifications, list):
                for cert in user.education_certifications:
                    if isinstance(cert, dict):
                        certifications.append({
                            'name': cert.get('name', 'Certificazione'),
                            'issuer': cert.get('issuer', ''),
                            'date': cert.get('date', ''),
                            'expiry': cert.get('expiry', '')
                        })
        except:
            pass

    # ─────────────────── RICERCA & PUBBLICAZIONI ──────────────────────────

    # Ricerca clinica
    clinical_research = {
        'has_experience': getattr(user, 'has_clinical_research', False),
        'details': getattr(user, 'clinical_research_details', '')
    }

    # Pubblicazioni scientifiche
    publications = {
        'has_publications': getattr(user, 'has_scientific_publications', False),
        'details': getattr(user, 'scientific_publications_details', '')
    }

    # Esperienza formazione
    teaching = {
        'has_experience': getattr(user, 'has_teaching_experience', False),
        'details': getattr(user, 'teaching_experience_details', '')
    }

    # ─────────────────── ESPERIENZA LAVORATIVA ──────────────────────────

    work_experiences = []
    if user.work_experiences:
        try:
            if isinstance(user.work_experiences, list):
                for exp in user.work_experiences:
                    if isinstance(exp, dict):
                        work_experiences.append({
                            'company': exp.get('company', ''),
                            'role': exp.get('role', ''),
                            'start_date': exp.get('start_date', ''),
                            'end_date': exp.get('end_date', ''),
                            'description': exp.get('description', '')
                        })
        except:
            pass

    # ─────────────────── CALCOLO PUNTEGGIO (NUOVO SISTEMA) ──────────────────────────

    # Conta corsi per il calcolo punteggio
    courses_count = 0
    if user.education_courses:
        try:
            if isinstance(user.education_courses, list):
                courses_count = len(user.education_courses)
        except:
            pass

    # Solo il titolo più alto conta per la formazione accademica
    academic_score = 0
    if phd and phd.get('title'):
        academic_score = 50  # PhD vale 50 punti
    elif masters:
        academic_score = 30  # Master vale 30 punti
    elif degrees:
        academic_score = 20  # Laurea vale 20 punti

    score_breakdown = {
        'academic': academic_score,  # Max 50 (solo il più alto)
        'certifications': min(len(certifications) * 3, 15),  # 3 pt/cad, max 15
        'courses': min(courses_count * 1, 5),  # 1 pt/cad, max 5
        'clinical_research': 10 if clinical_research['has_experience'] else 0,
        'publications': 10 if publications['has_publications'] else 0,
        'teaching': 10 if teaching['has_experience'] else 0
    }

    total_score = sum(score_breakdown.values())

    return jsonify({
        'user': {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'job_title': user.job_title,
            'department': user.department.name if user.department else '',
            'email': user.email
        },
        'academic': {
            'degrees': degrees,
            'masters': masters,
            'phd': phd,
            'certifications': certifications
        },
        'research': {
            'clinical_research': clinical_research,
            'publications': publications,
            'teaching': teaching
        },
        'work_experiences': work_experiences,
        'score': {
            'breakdown': score_breakdown,
            'total': min(total_score, 100),
            'level': 'Eccellente' if total_score >= 70 else
                    'Buono' if total_score >= 45 else
                    'Medio' if total_score >= 25 else 'Base'
        }
    })


@team_bp.route("/api/department/<int:dept_id>/members")
@login_required
def get_department_members(dept_id: int) -> dict:
    """
    API endpoint per recuperare i membri di un dipartimento.
    """
    _require_admin()

    # Recupera i membri del dipartimento
    members = User.query.filter(
        User.department_id == dept_id,
        User.is_active == True
    ).order_by(User.last_name, User.first_name).all()

    # Calcola statistiche
    total_count = len(members)
    total_cost = sum(m.ral_annua for m in members if m.ral_annua) or 0
    avg_salary = (total_cost / total_count) if total_count > 0 else 0

    # Prepara i dati dei membri
    members_data = []
    for member in members:
        members_data.append({
            'id': member.id,
            'first_name': member.first_name,
            'last_name': member.last_name,
            'job_title': member.job_title,
            'ral_annua': float(member.ral_annua) if member.ral_annua else 0,
            'is_active': member.is_active
        })

    return jsonify({
        'members': members_data,
        'stats': {
            'total': total_count,
            'avg_salary': avg_salary,
            'total_cost': total_cost
        }
    })


@team_bp.route("/api/department/<int:dept_id>/education")
@login_required
def get_department_education(dept_id: int) -> dict:
    """
    API endpoint per recuperare i dati di istruzione di un dipartimento.
    """
    _require_admin()

    # Recupera i membri del dipartimento con i loro dati di istruzione
    members = User.query.filter(
        User.department_id == dept_id,
        User.is_active == True
    ).order_by(User.last_name, User.first_name).all()

    # Calcola statistiche
    with_degree = sum(1 for m in members if m.education_degrees)
    with_master = sum(1 for m in members if m.education_masters)
    with_phd = sum(1 for m in members if m.education_phd)

    # Conta le certificazioni
    from corposostenibile.models import Certification
    total_certs = 0
    members_data = []

    for member in members:
        # Recupera certificazioni per questo membro
        user_certs = []
        if member.certifications:
            user_certs = [cert.name for cert in member.certifications]
            total_certs += len(user_certs)

        # Processa i campi education (sono array JSON)
        degrees_text = "-"
        if member.education_degrees:
            try:
                if isinstance(member.education_degrees, list):
                    # Estrai i nomi delle università/titoli
                    degree_items = []
                    for degree in member.education_degrees:
                        if isinstance(degree, dict):
                            # Prova diversi campi possibili
                            text = degree.get('degree') or degree.get('name') or degree.get('university') or degree.get('title', '')
                            if text:
                                degree_items.append(str(text))
                    degrees_text = ", ".join(degree_items) if degree_items else "-"
                elif isinstance(member.education_degrees, str):
                    degrees_text = member.education_degrees
                else:
                    degrees_text = str(member.education_degrees)
            except Exception as e:
                current_app.logger.error(f"Error processing degrees for {member.first_name} {member.last_name}: {e}")
                degrees_text = "-"

        masters_text = "-"
        if member.education_masters:
            try:
                if isinstance(member.education_masters, list):
                    master_items = []
                    for master in member.education_masters:
                        if isinstance(master, dict):
                            text = master.get('master') or master.get('name') or master.get('university') or master.get('title', '')
                            if text:
                                master_items.append(str(text))
                    masters_text = ", ".join(master_items) if master_items else "-"
                elif isinstance(member.education_masters, str):
                    masters_text = member.education_masters
                else:
                    masters_text = str(member.education_masters)
            except Exception as e:
                current_app.logger.error(f"Error processing masters for {member.first_name} {member.last_name}: {e}")
                masters_text = "-"

        phd_text = "-"
        if member.education_phd:
            try:
                if isinstance(member.education_phd, list):
                    phd_items = []
                    for phd in member.education_phd:
                        if isinstance(phd, dict):
                            text = phd.get('phd') or phd.get('name') or phd.get('university') or phd.get('title', '')
                            if text:
                                phd_items.append(str(text))
                    phd_text = ", ".join(phd_items) if phd_items else "-"
                elif isinstance(member.education_phd, str):
                    phd_text = member.education_phd
                else:
                    phd_text = str(member.education_phd)
            except Exception as e:
                current_app.logger.error(f"Error processing phd for {member.first_name} {member.last_name}: {e}")
                phd_text = "-"

        members_data.append({
            'id': member.id,
            'first_name': member.first_name,
            'last_name': member.last_name,
            'education_degrees': degrees_text,
            'education_masters': masters_text,
            'education_phd': phd_text,
            'certifications': user_certs
        })

    return jsonify({
        'members': members_data,
        'stats': {
            'with_degree': with_degree,
            'with_master': with_master,
            'with_phd': with_phd,
            'total_certifications': total_certs
        }
    })


@team_bp.route("/api/department/<int:dept_id>/compliance")
@login_required
def get_department_compliance(dept_id: int) -> dict:
    """
    API endpoint per recuperare i dati di conformità report di un dipartimento.
    """
    _require_admin()

    from corposostenibile.blueprints.team.models.weekly_report import WeeklyReport

    # Get department
    department = Department.query.get_or_404(dept_id)

    # Get first report date to calculate compliance from that point
    first_report_date = db.session.query(func.min(WeeklyReport.submission_date)).scalar()

    if not first_report_date:
        return jsonify({
            'members': [],
            'stats': {
                'total_members': 0,
                'total_reports': 0,
                'compliance_rate': 0,
                'weeks_since_start': 0
            }
        })

    # Calculate weeks since first report
    weeks_since_start = max(1, (datetime.now() - first_report_date).days // 7)

    # Get department members
    members = User.query.filter(
        User.department_id == dept_id,
        User.is_active == True
    ).order_by(User.last_name, User.first_name).all()

    # Get reports for each member
    members_data = []
    total_reports = 0
    expected_reports_per_user = weeks_since_start

    for member in members:
        user_reports = WeeklyReport.query.filter(
            WeeklyReport.user_id == member.id
        ).count()

        total_reports += user_reports
        compliance_pct = round(
            (user_reports / expected_reports_per_user * 100)
            if expected_reports_per_user > 0 else 0, 1
        )

        members_data.append({
            'id': member.id,
            'first_name': member.first_name,
            'last_name': member.last_name,
            'job_title': member.job_title,
            'submitted_reports': user_reports,
            'expected_reports': expected_reports_per_user,
            'compliance_pct': compliance_pct
        })

    # Calculate department stats
    total_members = len(members)
    total_expected = total_members * expected_reports_per_user
    dept_compliance_rate = round(
        (total_reports / total_expected * 100)
        if total_expected > 0 else 0, 1
    )

    return jsonify({
        'department_name': department.name,
        'members': members_data,
        'stats': {
            'total_members': total_members,
            'total_reports': total_reports,
            'expected_reports': total_expected,
            'compliance_rate': dept_compliance_rate,
            'weeks_since_start': weeks_since_start,
            'first_report_date': first_report_date.strftime('%Y-%m-%d') if first_report_date else None
        }
    })


@team_bp.route("/api/leaves/<int:user_id>/calendar")
@login_required
def user_leave_calendar(user_id: int):
    """API endpoint per calendario assenze utente."""
    # Verifica permessi
    if not current_user.is_admin and current_user.id != user_id:
        abort(HTTPStatus.FORBIDDEN)
    
    year = request.args.get('year', datetime.now().year, type=int)
    
    # Richieste dell'utente
    requests = LeaveRequest.query.filter(
        LeaveRequest.user_id == user_id,
        LeaveRequest.status.in_([LeaveStatusEnum.approvata, LeaveStatusEnum.richiesta]),
        extract('year', LeaveRequest.start_date) == year
    ).all()
    
    # Formatta per JSON
    events = []
    for req in requests:
        color = {
            LeaveTypeEnum.ferie: '#28a745',
            LeaveTypeEnum.permesso: '#ffc107',
            LeaveTypeEnum.malattia: '#dc3545'
        }.get(req.leave_type, '#6c757d')
        
        events.append({
            'id': req.id,
            'title': req.leave_type.value.capitalize(),
            'start': req.start_date.isoformat(),
            'end': (req.end_date + timedelta(days=1)).isoformat(),  # FullCalendar vuole end esclusivo
            'color': color,
            'status': req.status.value,
            'working_days': req.working_days,
            'hours': req.hours
        })
    
    return {'events': events}


# --------------------------------------------------------------------------- #
#  Birthdays
# --------------------------------------------------------------------------- #

@team_bp.route("/birthdays")
@login_required
def birthdays():
    """Mostra il calendario dei compleanni del team."""
    # Check permissions - only admin and HR can access
    is_hr = current_user.department and current_user.department.id == 17
    if not (current_user.is_admin or is_hr):
        flash("Non hai i permessi per accedere a questa pagina", "warning")
        return redirect(url_for("team.user_list"))
    
    from calendar import monthrange, month_name
    from datetime import date
    
    # Get month and year from query params or use current
    now = datetime.now()
    month = request.args.get('month', now.month, type=int)
    year = request.args.get('year', now.year, type=int)
    
    # Validate month and year
    if month < 1 or month > 12:
        month = now.month
    if year < 1900 or year > 2100:
        year = now.year
    
    # Get all active users with birthdays in the selected month
    users_with_birthdays = User.query.filter(
        User.is_active == True,
        User.birth_date != None,
        extract('month', User.birth_date) == month
    ).order_by(
        extract('day', User.birth_date)
    ).all()
    
    # Create a dictionary of birthdays by day
    birthdays_by_day = {}
    for user in users_with_birthdays:
        day = user.birth_date.day
        if day not in birthdays_by_day:
            birthdays_by_day[day] = []
        
        # Calculate age if birth year is available
        age = None
        if user.birth_date.year:
            age = year - user.birth_date.year
            # Adjust if birthday hasn't occurred this year yet
            if (month, day) < (now.month, now.day):
                age += 1
        
        birthdays_by_day[day].append({
            'user': user,
            'age': age,
            'is_today': (day == now.day and month == now.month and year == now.year)
        })
    
    # Get upcoming birthdays (next 30 days)
    today = date.today()
    end_date = today + timedelta(days=30)
    
    upcoming_birthdays = []
    all_users = User.query.filter(
        User.is_active == True,
        User.birth_date != None
    ).all()
    
    for user in all_users:
        # Create birthday date for current year
        try:
            birthday_this_year = date(today.year, user.birth_date.month, user.birth_date.day)
        except ValueError:
            # Handle February 29 for non-leap years
            birthday_this_year = date(today.year, user.birth_date.month, 28)
        
        # Check next year if birthday already passed
        if birthday_this_year < today:
            try:
                birthday_this_year = date(today.year + 1, user.birth_date.month, user.birth_date.day)
            except ValueError:
                birthday_this_year = date(today.year + 1, user.birth_date.month, 28)
        
        # Check if birthday is within next 30 days
        if today <= birthday_this_year <= end_date:
            days_until = (birthday_this_year - today).days
            age = birthday_this_year.year - user.birth_date.year if user.birth_date.year else None
            
            upcoming_birthdays.append({
                'user': user,
                'date': birthday_this_year,
                'days_until': days_until,
                'age': age
            })
    
    # Sort upcoming birthdays by date
    upcoming_birthdays.sort(key=lambda x: x['date'])
    
    # Calendar data
    first_weekday, days_in_month = monthrange(year, month)
    
    # Calculate previous and next month
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year = year - 1
    
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year = year + 1
    
    return render_template(
        "team/birthdays.html",
        birthdays_by_day=birthdays_by_day,
        upcoming_birthdays=upcoming_birthdays[:5],  # Show only next 5
        month=month,
        year=year,
        month_name=month_name[month],
        days_in_month=days_in_month,
        first_weekday=first_weekday,
        current_day=now.day if month == now.month and year == now.year else None,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year,
        now=now  # Pass now to template
    )

# =============================================================================
# DOCUMENTATION ROUTES
# =============================================================================

@team_bp.route("/codice-condotta")
@login_required
def codice_condotta():
    """
    Visualizza la pagina del Codice di Condotta.
    Controlla se l'utente ha già confermato la lettura.
    """
    from corposostenibile.models import DocumentAcknowledgment, DocumentTypeEnum

    # Verifica se l'utente ha già confermato
    acknowledgment = DocumentAcknowledgment.query.filter_by(
        user_id=current_user.id,
        document_type=DocumentTypeEnum.codice_condotta
    ).first()

    return render_template(
        "team/codice_condotta.html",
        has_acknowledged=acknowledgment is not None,
        acknowledgment=acknowledgment
    )


@team_bp.route("/regolamento-remoto")
@login_required
def regolamento_remoto():
    """
    Visualizza la pagina del Regolamento per il lavoro da Remoto.
    Controlla se l'utente ha già confermato la lettura.
    """
    from corposostenibile.models import DocumentAcknowledgment, DocumentTypeEnum

    # Verifica se l'utente ha già confermato
    acknowledgment = DocumentAcknowledgment.query.filter_by(
        user_id=current_user.id,
        document_type=DocumentTypeEnum.regolamento_remoto
    ).first()

    return render_template(
        "team/regolamento_remoto.html",
        has_acknowledged=acknowledgment is not None,
        acknowledgment=acknowledgment
    )


# =============================================================================
# DOCUMENT ACKNOWLEDGMENT ROUTES
# =============================================================================

@team_bp.route("/acknowledge-document", methods=["POST"])
@login_required
def acknowledge_document():
    """
    API endpoint per confermare la lettura di un documento.
    Registra IP e User-Agent per audit trail.
    """
    from corposostenibile.models import DocumentAcknowledgment, DocumentTypeEnum

    data = request.get_json()
    document_type = data.get("document_type")

    if not document_type:
        return jsonify({"success": False, "message": "Tipo documento mancante"}), 400

    # Valida il tipo di documento
    try:
        doc_type_enum = DocumentTypeEnum(document_type)
    except ValueError:
        return jsonify({"success": False, "message": "Tipo documento non valido"}), 400

    # Verifica se l'utente ha già confermato
    existing = DocumentAcknowledgment.query.filter_by(
        user_id=current_user.id,
        document_type=doc_type_enum
    ).first()

    if existing:
        return jsonify({
            "success": False,
            "message": "Hai già confermato la lettura di questo documento",
            "acknowledged_at": existing.acknowledged_at.isoformat()
        }), 400

    # Crea la conferma
    acknowledgment = DocumentAcknowledgment(
        user_id=current_user.id,
        document_type=doc_type_enum,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:500]
    )

    db.session.add(acknowledgment)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Conferma di lettura registrata con successo",
        "acknowledged_at": acknowledgment.acknowledged_at.isoformat()
    })


@team_bp.route("/admin/document-acknowledgments")
@login_required
def admin_document_acknowledgments():
    """
    Dashboard admin per visualizzare le conferme di lettura.
    Filtri: dipartimento, documento, stato conferma.
    """
    _require_admin()

    from corposostenibile.models import DocumentAcknowledgment, DocumentTypeEnum, Department

    # Parametri filtro
    dept_filter = request.args.get("dept", type=int)
    doc_filter = request.args.get("doc")
    status_filter = request.args.get("status")  # "confirmed", "pending", "all"

    # Query base: tutti gli utenti attivi
    users_query = User.query.filter_by(is_active=True)

    # Filtro dipartimento
    if dept_filter:
        users_query = users_query.filter_by(department_id=dept_filter)

    users = users_query.order_by(User.department_id, User.last_name, User.first_name).all()

    # Determina quali documenti analizzare
    if doc_filter and doc_filter in ["codice_condotta", "regolamento_remoto"]:
        document_types = [DocumentTypeEnum(doc_filter)]
    else:
        document_types = [DocumentTypeEnum.codice_condotta, DocumentTypeEnum.regolamento_remoto]

    # Costruisci i dati per ogni utente
    user_data = []
    for user in users:
        user_info = {
            "user": user,
            "acknowledgments": {}
        }

        for doc_type in document_types:
            ack = DocumentAcknowledgment.query.filter_by(
                user_id=user.id,
                document_type=doc_type
            ).first()

            user_info["acknowledgments"][doc_type.value] = ack

        # Filtro stato
        if status_filter == "confirmed":
            # Solo utenti che hanno confermato TUTTI i documenti
            if all(user_info["acknowledgments"].values()):
                user_data.append(user_info)
        elif status_filter == "pending":
            # Solo utenti che mancano almeno una conferma
            if not all(user_info["acknowledgments"].values()):
                user_data.append(user_info)
        else:
            # Tutti
            user_data.append(user_info)

    # Statistiche
    total_users = len(users)
    stats = {}

    for doc_type in document_types:
        confirmed_count = DocumentAcknowledgment.query.join(User).filter(
            User.is_active == True,
            DocumentAcknowledgment.document_type == doc_type
        ).count()

        if dept_filter:
            confirmed_count = DocumentAcknowledgment.query.join(User).filter(
                User.is_active == True,
                User.department_id == dept_filter,
                DocumentAcknowledgment.document_type == doc_type
            ).count()

        stats[doc_type.value] = {
            "confirmed": confirmed_count,
            "pending": total_users - confirmed_count,
            "percentage": round((confirmed_count / total_users * 100) if total_users > 0 else 0, 1)
        }

    # Dipartimenti per filtro
    departments = Department.query.order_by(Department.name).all()

    return render_template(
        "team/admin_document_acknowledgments.html",
        user_data=user_data,
        stats=stats,
        departments=departments,
        dept_filter=dept_filter,
        doc_filter=doc_filter,
        status_filter=status_filter,
        DocumentTypeEnum=DocumentTypeEnum,
        total_users=total_users
    )


# ════════════════════════════════════════════════════════════════════════════ #
#  PAGINA ASSEGNAZIONI AI - Professionisti Nutrizione, Coach, Psicologia
# ════════════════════════════════════════════════════════════════════════════ #

@team_bp.route("/assegnazioni", methods=["GET"])
@login_required
def assignments_dashboard():
    """
    Dashboard Assegnazioni AI.
    Mostra tutti i professionisti di Nutrizione, Coach e Psicologia
    con le loro impostazioni di assegnazione AI.
    """
    _require_admin()

    # ID dipartimenti: Nutrizione=2, Nutrizione 2=24, Coach=3, Psicologia=4
    DEPT_NUTRIZIONE = [2, 24]  # Nutrizione e Nutrizione 2
    DEPT_COACH = [3]
    DEPT_PSICOLOGIA = [4]

    # Query professionisti attivi per dipartimento (esclusi utenti in prova)
    nutrizionisti = User.query.filter(
        User.department_id.in_(DEPT_NUTRIZIONE),
        User.is_active == True,
        User.is_trial == False
    ).order_by(User.first_name, User.last_name).all()

    coaches = User.query.filter(
        User.department_id.in_(DEPT_COACH),
        User.is_active == True,
        User.is_trial == False
    ).order_by(User.first_name, User.last_name).all()

    psicologi = User.query.filter(
        User.department_id.in_(DEPT_PSICOLOGIA),
        User.is_active == True,
        User.is_trial == False
    ).order_by(User.first_name, User.last_name).all()

    # Statistiche
    def count_available(users):
        """Conta quanti professionisti sono disponibili per assegnazioni."""
        count = 0
        for u in users:
            if u.assignment_ai_notes and isinstance(u.assignment_ai_notes, dict):
                # Se il campo non è definito o è True, conta come disponibile
                if u.assignment_ai_notes.get('disponibile_assegnazioni', True):
                    count += 1
            else:
                # Se non ha note AI, conta come disponibile (default)
                count += 1
        return count

    def count_configured(users):
        """Conta quanti hanno le note AI configurate."""
        return sum(1 for u in users if u.assignment_ai_notes and isinstance(u.assignment_ai_notes, dict) and u.assignment_ai_notes.get('specializzazione'))

    stats = {
        'nutrizione': {
            'total': len(nutrizionisti),
            'available': count_available(nutrizionisti),
            'configured': count_configured(nutrizionisti)
        },
        'coach': {
            'total': len(coaches),
            'available': count_available(coaches),
            'configured': count_configured(coaches)
        },
        'psicologia': {
            'total': len(psicologi),
            'available': count_available(psicologi),
            'configured': count_configured(psicologi)
        }
    }

    return render_template(
        "team/assignments_dashboard.html",
        nutrizionisti=nutrizionisti,
        coaches=coaches,
        psicologi=psicologi,
        stats=stats
    )


@team_bp.route("/api/assegnazioni/<int:user_id>", methods=["GET"])
@login_required
def api_get_assignment_notes(user_id: int):
    """API per ottenere le note di assegnazione AI di un utente."""
    _require_assignment_permission()

    user = User.query.get_or_404(user_id)

    ai_notes = user.assignment_ai_notes or {}
    if isinstance(ai_notes, str):
        try:
            ai_notes = json.loads(ai_notes)
        except json.JSONDecodeError:
            ai_notes = {}

    return jsonify({
        'success': True,
        'user_id': user_id,
        'full_name': user.full_name,
        'department': user.department.name if user.department else None,
        'assignment_ai_notes': {
            'disponibile_assegnazioni': ai_notes.get('disponibile_assegnazioni', True),
            'specializzazione': ai_notes.get('specializzazione', ''),
            'target_ideale': ai_notes.get('target_ideale', ''),
            'problematiche_efficaci': ai_notes.get('problematiche_efficaci', ''),
            'target_non_ideale': ai_notes.get('target_non_ideale', ''),
            'link_calendario': ai_notes.get('link_calendario', ''),
            'note_aggiuntive': ai_notes.get('note_aggiuntive', '')
        }
    })


@team_bp.route("/api/assegnazioni/<int:user_id>", methods=["POST"])
@login_required
@csrf.exempt
def api_update_assignment_notes(user_id: int):
    """API per aggiornare le note di assegnazione AI di un utente."""
    _require_assignment_permission()

    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Dati non validi'}), 400

    # Recupera note esistenti o inizializza
    ai_notes = user.assignment_ai_notes or {}
    if isinstance(ai_notes, str):
        try:
            ai_notes = json.loads(ai_notes)
        except json.JSONDecodeError:
            ai_notes = {}

    # Aggiorna i campi
    if 'disponibile_assegnazioni' in data:
        ai_notes['disponibile_assegnazioni'] = bool(data['disponibile_assegnazioni'])
    if 'specializzazione' in data:
        ai_notes['specializzazione'] = data['specializzazione'].strip() if data['specializzazione'] else ''
    if 'target_ideale' in data:
        ai_notes['target_ideale'] = data['target_ideale'].strip() if data['target_ideale'] else ''
    if 'problematiche_efficaci' in data:
        ai_notes['problematiche_efficaci'] = data['problematiche_efficaci'].strip() if data['problematiche_efficaci'] else ''
    if 'target_non_ideale' in data:
        ai_notes['target_non_ideale'] = data['target_non_ideale'].strip() if data['target_non_ideale'] else ''
    if 'link_calendario' in data:
        ai_notes['link_calendario'] = data['link_calendario'].strip() if data['link_calendario'] else ''
    if 'note_aggiuntive' in data:
        ai_notes['note_aggiuntive'] = data['note_aggiuntive'].strip() if data['note_aggiuntive'] else ''

    # Salva
    user.assignment_ai_notes = ai_notes

    # Flag modified per SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, 'assignment_ai_notes')

    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Impostazioni assegnazione per {user.full_name} aggiornate'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore aggiornamento assignment_ai_notes: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@team_bp.route("/api/assegnazioni/<int:user_id>/toggle-disponibile", methods=["POST"])
@login_required
@csrf.exempt
def api_toggle_assignment_available(user_id: int):
    """API per toggle rapido disponibilità assegnazioni."""
    _require_assignment_permission()

    user = User.query.get_or_404(user_id)

    # Recupera note esistenti o inizializza
    ai_notes = user.assignment_ai_notes or {}
    if isinstance(ai_notes, str):
        try:
            ai_notes = json.loads(ai_notes)
        except json.JSONDecodeError:
            ai_notes = {}

    # Toggle disponibilità (default True se non definito)
    current_value = ai_notes.get('disponibile_assegnazioni', True)
    ai_notes['disponibile_assegnazioni'] = not current_value

    user.assignment_ai_notes = ai_notes

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, 'assignment_ai_notes')

    try:
        db.session.commit()
        new_status = "disponibile" if ai_notes['disponibile_assegnazioni'] else "non disponibile"
        return jsonify({
            'success': True,
            'disponibile': ai_notes['disponibile_assegnazioni'],
            'message': f'{user.full_name} ora è {new_status} per nuove assegnazioni'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore toggle disponibilità: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ════════════════════════════════════════════════════════════════════════════ #
#  ASSEGNAZIONI AI - NUTRIZIONE (con tab per team)
# ════════════════════════════════════════════════════════════════════════════ #

@team_bp.route("/assegnazioni/nutrizione", methods=["GET"])
@login_required
def assignments_nutrizione():
    """
    Dashboard Assegnazioni AI per Nutrizione.
    Mostra i nutrizionisti suddivisi per team.

    Permessi:
    - Admin: accesso completo
    - CCO: accesso completo
    - Head dipartimento Nutrizione: accesso completo
    - Team leader Nutrizione: accesso completo (tutti i team)
    """
    # Verifica permessi
    is_admin = current_user.is_admin
    is_cco = current_user.department and current_user.department.name == 'CCO'
    is_nutri_head = (
        current_user.department and
        current_user.department.name in ['Nutrizione', 'Nutrizione 2'] and
        current_user.department.head_id == current_user.id
    )
    is_nutri_team_leader = (
        current_user.department and
        current_user.department.name in ['Nutrizione', 'Nutrizione 2'] and
        len(current_user.teams_led) > 0
    )

    if not (is_admin or is_cco or is_nutri_head or is_nutri_team_leader):
        flash("Non hai i permessi per accedere a questa pagina.", "danger")
        return redirect(url_for("main.index"))

    # Recupera i team del dipartimento Nutrizione
    DEPT_NUTRIZIONE = [2, 24]  # Nutrizione e Nutrizione 2

    teams = Team.query.filter(Team.department_id.in_(DEPT_NUTRIZIONE)).order_by(Team.name).all()

    # Per ogni team, recupera i membri attivi (non trial)
    for team in teams:
        team.members = [m for m in team.members if m.is_active and not m.is_trial]

    # Statistiche generali
    all_users = []
    for team in teams:
        all_users.extend(team.members)

    # Recupera tutti gli ID degli utenti per la query KPI
    all_user_ids = [u.id for u in all_users]

    # Query aggregata per KPI clienti per stato_nutrizione per ogni nutrizionista
    # Usa la tabella M2M cliente_nutrizionisti per le assegnazioni multiple
    from sqlalchemy import case
    from corposostenibile.models import cliente_nutrizionisti

    user_kpi = {}
    if all_user_ids:
        # Query per contare clienti per stato_nutrizione per ogni nutrizionista
        kpi_query = (
            db.session.query(
                cliente_nutrizionisti.c.user_id,
                func.count(case((Cliente.stato_nutrizione == StatoClienteEnum.attivo, 1))).label('attivo'),
                func.count(case((Cliente.stato_nutrizione == StatoClienteEnum.ghost, 1))).label('ghost'),
                func.count(case((Cliente.stato_nutrizione == StatoClienteEnum.pausa, 1))).label('pausa'),
                func.count(case((Cliente.stato_nutrizione == StatoClienteEnum.stop, 1))).label('stop'),
            )
            .join(Cliente, Cliente.cliente_id == cliente_nutrizionisti.c.cliente_id)
            .filter(cliente_nutrizionisti.c.user_id.in_(all_user_ids))
            .group_by(cliente_nutrizionisti.c.user_id)
            .all()
        )

        for row in kpi_query:
            user_kpi[row.user_id] = {
                'attivo': row.attivo,
                'ghost': row.ghost,
                'pausa': row.pausa,
                'stop': row.stop,
                'totale': row.attivo + row.ghost + row.pausa + row.stop
            }

    # Assegna KPI a ogni membro
    for team in teams:
        for member in team.members:
            member.cliente_kpi = user_kpi.get(member.id, {
                'attivo': 0,
                'ghost': 0,
                'pausa': 0,
                'stop': 0,
                'totale': 0
            })

    def count_available(users):
        count = 0
        for u in users:
            if u.assignment_ai_notes and isinstance(u.assignment_ai_notes, dict):
                if u.assignment_ai_notes.get('disponibile_assegnazioni', True):
                    count += 1
            else:
                count += 1
        return count

    def count_configured(users):
        return sum(1 for u in users if u.assignment_ai_notes and isinstance(u.assignment_ai_notes, dict) and u.assignment_ai_notes.get('specializzazione'))

    stats = {
        'total': len(all_users),
        'available': count_available(all_users),
        'configured': count_configured(all_users)
    }

    return render_template(
        "team/assignments_nutrizione.html",
        teams=teams,
        stats=stats
    )


# ════════════════════════════════════════════════════════════════════════════ #
#  ASSEGNAZIONI AI - COACH
# ════════════════════════════════════════════════════════════════════════════ #

@team_bp.route("/assegnazioni/coach", methods=["GET"])
@login_required
def assignments_coach():
    """
    Dashboard Assegnazioni AI per Coach.

    Permessi:
    - Admin: accesso completo
    - CCO: accesso completo
    - Head dipartimento Coach: accesso completo
    """
    # Verifica permessi
    is_admin = current_user.is_admin
    is_cco = current_user.department and current_user.department.name == 'CCO'
    is_coach_head = (
        current_user.department and
        current_user.department.name == 'Coach' and
        current_user.department.head_id == current_user.id
    )

    if not (is_admin or is_cco or is_coach_head):
        flash("Non hai i permessi per accedere a questa pagina.", "danger")
        return redirect(url_for("main.index"))

    DEPT_COACH = [3]

    coaches = User.query.filter(
        User.department_id.in_(DEPT_COACH),
        User.is_active == True,
        User.is_trial == False
    ).order_by(User.first_name, User.last_name).all()

    # Recupera tutti gli ID degli coach per la query KPI
    all_coach_ids = [u.id for u in coaches]

    # Query aggregata per KPI clienti per stato_coach per ogni coach
    from sqlalchemy import case
    from corposostenibile.models import cliente_coaches

    user_kpi = {}
    if all_coach_ids:
        kpi_query = (
            db.session.query(
                cliente_coaches.c.user_id,
                func.count(case((Cliente.stato_coach == StatoClienteEnum.attivo, 1))).label('attivo'),
                func.count(case((Cliente.stato_coach == StatoClienteEnum.ghost, 1))).label('ghost'),
                func.count(case((Cliente.stato_coach == StatoClienteEnum.pausa, 1))).label('pausa'),
                func.count(case((Cliente.stato_coach == StatoClienteEnum.stop, 1))).label('stop'),
            )
            .join(Cliente, Cliente.cliente_id == cliente_coaches.c.cliente_id)
            .filter(cliente_coaches.c.user_id.in_(all_coach_ids))
            .group_by(cliente_coaches.c.user_id)
            .all()
        )

        for row in kpi_query:
            user_kpi[row.user_id] = {
                'attivo': row.attivo,
                'ghost': row.ghost,
                'pausa': row.pausa,
                'stop': row.stop,
                'totale': row.attivo + row.ghost + row.pausa + row.stop
            }

    # Assegna KPI a ogni coach
    for coach in coaches:
        coach.cliente_kpi = user_kpi.get(coach.id, {
            'attivo': 0,
            'ghost': 0,
            'pausa': 0,
            'stop': 0,
            'totale': 0
        })

    def count_available(users):
        count = 0
        for u in users:
            if u.assignment_ai_notes and isinstance(u.assignment_ai_notes, dict):
                if u.assignment_ai_notes.get('disponibile_assegnazioni', True):
                    count += 1
            else:
                count += 1
        return count

    def count_configured(users):
        return sum(1 for u in users if u.assignment_ai_notes and isinstance(u.assignment_ai_notes, dict) and u.assignment_ai_notes.get('specializzazione'))

    stats = {
        'total': len(coaches),
        'available': count_available(coaches),
        'configured': count_configured(coaches)
    }

    return render_template(
        "team/assignments_coach.html",
        coaches=coaches,
        stats=stats
    )


# ════════════════════════════════════════════════════════════════════════════ #
#  ASSEGNAZIONI AI - PSICOLOGIA
# ════════════════════════════════════════════════════════════════════════════ #

@team_bp.route("/assegnazioni/psicologia", methods=["GET"])
@login_required
def assignments_psicologia():
    """
    Dashboard Assegnazioni AI per Psicologia.

    Permessi:
    - Admin: accesso completo
    - CCO: accesso completo
    - Head dipartimento Psicologia: accesso completo
    - Utente ID 35: accesso completo gestione Psicologia
    """
    # Verifica permessi
    is_admin = current_user.is_admin
    is_cco = current_user.department and current_user.department.name == 'CCO'
    is_psico_head = (
        current_user.department and
        current_user.department.name == 'Psicologia' and
        current_user.department.head_id == current_user.id
    )
    # Utente specifico con accesso gestione Psicologia (ID 35)
    is_psico_manager = current_user.id == 35

    if not (is_admin or is_cco or is_psico_head or is_psico_manager):
        flash("Non hai i permessi per accedere a questa pagina.", "danger")
        return redirect(url_for("main.index"))

    DEPT_PSICOLOGIA = [4]

    psicologi = User.query.filter(
        User.department_id.in_(DEPT_PSICOLOGIA),
        User.is_active == True,
        User.is_trial == False
    ).order_by(User.first_name, User.last_name).all()

    # Recupera tutti gli ID degli psicologi per la query KPI
    all_psico_ids = [u.id for u in psicologi]

    # Query aggregata per KPI clienti per stato_psicologia per ogni psicologo
    from sqlalchemy import case
    from corposostenibile.models import cliente_psicologi

    user_kpi = {}
    if all_psico_ids:
        kpi_query = (
            db.session.query(
                cliente_psicologi.c.user_id,
                func.count(case((Cliente.stato_psicologia == StatoClienteEnum.attivo, 1))).label('attivo'),
                func.count(case((Cliente.stato_psicologia == StatoClienteEnum.ghost, 1))).label('ghost'),
                func.count(case((Cliente.stato_psicologia == StatoClienteEnum.pausa, 1))).label('pausa'),
                func.count(case((Cliente.stato_psicologia == StatoClienteEnum.stop, 1))).label('stop'),
            )
            .join(Cliente, Cliente.cliente_id == cliente_psicologi.c.cliente_id)
            .filter(cliente_psicologi.c.user_id.in_(all_psico_ids))
            .group_by(cliente_psicologi.c.user_id)
            .all()
        )

        for row in kpi_query:
            user_kpi[row.user_id] = {
                'attivo': row.attivo,
                'ghost': row.ghost,
                'pausa': row.pausa,
                'stop': row.stop,
                'totale': row.attivo + row.ghost + row.pausa + row.stop
            }

    # Assegna KPI a ogni psicologo
    for psicologo in psicologi:
        psicologo.cliente_kpi = user_kpi.get(psicologo.id, {
            'attivo': 0,
            'ghost': 0,
            'pausa': 0,
            'stop': 0,
            'totale': 0
        })

    def count_available(users):
        count = 0
        for u in users:
            if u.assignment_ai_notes and isinstance(u.assignment_ai_notes, dict):
                if u.assignment_ai_notes.get('disponibile_assegnazioni', True):
                    count += 1
            else:
                count += 1
        return count

    def count_configured(users):
        return sum(1 for u in users if u.assignment_ai_notes and isinstance(u.assignment_ai_notes, dict) and u.assignment_ai_notes.get('specializzazione'))

    stats = {
        'total': len(psicologi),
        'available': count_available(psicologi),
        'configured': count_configured(psicologi)
    }

    return render_template(
        "team/assignments_psicologia.html",
        psicologi=psicologi,
        stats=stats
    )


# ════════════════════════════════════════════════════════════════════════
#  Vista HR - Panoramica documentazione team
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/vista-hr")
@login_required
def vista_hr():
    """
    Vista HR per monitorare la documentazione completa dei membri del team.
    Mostra tutti i campi richiesti con indicatori verde/rosso per la completezza.
    """
    # Controllo accesso: solo Admin, HR
    is_hr = current_user.department and current_user.department.id == 17
    if not (current_user.is_admin or is_hr):
        flash("Non hai i permessi per accedere a questa pagina.", "danger")
        return redirect(url_for("main.index"))

    # Parametri di ricerca/filtro
    q = request.args.get("q", "").strip()
    department_id = request.args.get("department_id", type=int)
    completeness_filter = request.args.get("completeness", "")  # all, complete, incomplete
    page = request.args.get("page", 1, type=int)
    per_page = 50

    # Query base
    query = User.query.filter(User.is_active == True)

    # Filtro ricerca nome/cognome
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                func.concat(User.first_name, ' ', User.last_name).ilike(search_term)
            )
        )

    # Filtro dipartimento
    if department_id:
        query = query.filter(User.department_id == department_id)

    # Ordinamento
    query = query.order_by(User.first_name, User.last_name)

    # Paginazione
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    members = pagination.items

    # Helper per verificare completezza dati
    def check_field(value):
        """Ritorna True se il campo ha un valore valido."""
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, (list, dict)):
            # Per education fields, controlla se non vuoto e non solo 'not_owned'
            if isinstance(value, dict):
                if value.get('not_owned'):
                    return True  # 'Non posseduto' è considerato completo
                return bool(value)
            if isinstance(value, list):
                if len(value) > 0 and isinstance(value[0], dict) and value[0].get('not_owned'):
                    return True  # 'Non posseduto' è considerato completo
                return len(value) > 0
        return True

    # Prepara dati per il template
    hr_data = []
    for m in members:
        member_data = {
            'user': m,
            'fields': {
                'birth_date': check_field(m.birth_date),
                'codice_fiscale': check_field(m.codice_fiscale),
                'hired_at': check_field(m.hired_at),
                'contract_file': check_field(m.contract_file),
                'mobile': check_field(m.mobile),
                'citta': check_field(m.citta),
                'indirizzo': check_field(m.indirizzo),
                'documento_numero': check_field(m.documento_numero),
                'documento_fronte': check_field(m.documento_fronte_path),
                'documento_retro': check_field(m.documento_retro_path),
                'diploma': check_field(m.education_high_school),
                'lauree': check_field(m.education_degrees),
                'master': check_field(m.education_masters),
                'phd': check_field(m.education_phd),
                'corsi': check_field(m.education_courses),
                'certificazioni': check_field(m.education_certifications),
                'cv': check_field(m.cv_file),
            }
        }
        # Calcola completezza totale
        total_fields = len(member_data['fields'])
        complete_fields = sum(1 for v in member_data['fields'].values() if v)
        member_data['completeness'] = int((complete_fields / total_fields) * 100) if total_fields > 0 else 0
        hr_data.append(member_data)

    # Filtro per completezza (dopo aver calcolato i dati)
    if completeness_filter == "complete":
        hr_data = [d for d in hr_data if d['completeness'] == 100]
    elif completeness_filter == "incomplete":
        hr_data = [d for d in hr_data if d['completeness'] < 100]

    # KPI
    all_members_query = User.query.filter(User.is_active == True)
    if department_id:
        all_members_query = all_members_query.filter(User.department_id == department_id)
    all_members = all_members_query.all()

    kpi = {
        'total': len(all_members),
        'complete': 0,
        'incomplete': 0,
        'missing_documents': 0,
        'missing_education': 0,
    }

    for m in all_members:
        # Conta documenti mancanti
        docs_complete = all([
            check_field(m.birth_date),
            check_field(m.codice_fiscale),
            check_field(m.hired_at),
            check_field(m.contract_file),
            check_field(m.mobile),
            check_field(m.documento_numero),
            check_field(m.documento_fronte_path),
            check_field(m.documento_retro_path),
        ])

        # Conta formazione mancante
        edu_complete = all([
            check_field(m.education_high_school),
            check_field(m.education_degrees),
            check_field(m.education_masters),
            check_field(m.education_phd),
            check_field(m.education_courses),
            check_field(m.education_certifications),
        ])

        if docs_complete and edu_complete:
            kpi['complete'] += 1
        else:
            kpi['incomplete'] += 1
            if not docs_complete:
                kpi['missing_documents'] += 1
            if not edu_complete:
                kpi['missing_education'] += 1

    # Lista dipartimenti per filtro
    departments = Department.query.order_by(Department.name).all()

    return render_template(
        "team/list_hr.html",
        hr_data=hr_data,
        pagination=pagination,
        kpi=kpi,
        departments=departments,
        current_department_id=department_id,
        search_query=q,
        completeness_filter=completeness_filter,
    )

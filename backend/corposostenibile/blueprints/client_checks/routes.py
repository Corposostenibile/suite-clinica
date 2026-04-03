"""
client_checks.routes
===================

Route per il sistema di gestione check clienti:

**Route Admin (autenticazione richiesta):**
1. **Dashboard**           – GET       → /client-checks/
2. **Gestione Form**       – GET/POST  → /client-checks/forms/
3. **Crea Form**           – GET/POST  → /client-checks/forms/create
4. **Modifica Form**       – GET/POST  → /client-checks/forms/<id>/edit
5. **Elimina Form**        – POST      → /client-checks/forms/<id>/delete
6. **Assegna Form**        – GET/POST  → /client-checks/assign
7. **Gestione Assignment** – GET       → /client-checks/assignments/
8. **Risposte**            – GET       → /client-checks/responses/
9. **Dettaglio Risposta**  – GET       → /client-checks/responses/<id>

**Route Pubbliche (senza autenticazione):**
10. **Compilazione Form**  – GET/POST  → /client-checks/public/<token>
11. **Conferma Invio**     – GET       → /client-checks/public/<token>/success
"""
from __future__ import annotations

from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Dict, Any
from urllib.parse import urlparse

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    abort,
)
from flask_login import current_user, login_required
from sqlalchemy import desc, and_, exists, select, text, union_all, literal
from sqlalchemy.orm import joinedload, defer
from werkzeug.exceptions import HTTPException

from corposostenibile.extensions import db, csrf
from corposostenibile.models import (
    Cliente,
    ClienteProfessionistaHistory,
    User,
    Department,
    CheckForm,
    CheckFormField,
    ClientCheckAssignment,
    ClientCheckResponse,
    CheckFormTypeEnum,
    CheckFormFieldTypeEnum,
    WeeklyCheck,
    WeeklyCheckResponse,
    WeeklyCheckLinkAssignment,
    DCACheck,
    DCACheckResponse,
    StatoClienteEnum,
    MinorCheck,
    MinorCheckResponse,
    UserRoleEnum,
)
from .forms import (
    CheckFormForm,
    CheckFormFieldForm,
    ClientCheckAssignmentForm,
    ClientCheckResponseForm,
    AssignmentFilterForm,
    BulkAssignmentForm,
    DynamicCheckForm,
)
from .services import (
    CheckFormService,
    ClientCheckService,
    NotificationService,
)
from .helpers import (
    validate_form_data,
    format_response_data,
    get_client_ip,
    get_user_agent,
)
from .rbac import get_accessible_clients_query


def _fix_sequence(table_name: str) -> None:
    """Reset a PostgreSQL sequence to MAX(id) after a UniqueViolation."""
    seq_name = f"{table_name}_id_seq"
    max_id = db.session.execute(text(f"SELECT MAX(id) FROM {table_name}")).scalar() or 0
    db.session.execute(
        text("SELECT setval(:seq, GREATEST(:max_id, 1), true)"),
        {"seq": seq_name, "max_id": max_id},
    )
    db.session.commit()
    current_app.logger.warning(f"[SEQ_FIX] Reset {seq_name} to {max(max_id, 1)}")


def _photo_path_to_url(path: str | None) -> str | None:
    """Converte un path filesystem di foto check in URL web servibile.

    Il campo DB potrebbe contenere:
    - Path con prefisso ``/static/uploads/...`` (vecchio formato) → normalizzato a ``/uploads/...``
    - URL http/https esterno → restituisce così com'è
    - Path assoluto del filesystem: ``/var/.../uploads/weekly_checks/...``
    - Path relativo: ``uploads/weekly_checks/...``
    Tutti vengono normalizzati a ``/uploads/...`` servito dalla route ``uploaded_file``
    definita in ``__init__.py``.
    """
    if not path:
        return None
    path = path.strip()
    # URL http/https esterno
    if path.startswith('http'):
        return path
    # Vecchio formato /static/uploads/... → normalizza a /uploads/...
    # I file risiedono nel PVC servito dalla route /uploads/, non in Flask static
    if path.startswith('/static/uploads/'):
        return path.replace('/static/uploads/', '/uploads/', 1)
    # Già un URL relativo /uploads/...
    if path.startswith('/uploads/'):
        return path
    # Path assoluto del filesystem → estrai la parte dopo "uploads/"
    import os
    idx = path.find('/uploads/')
    if idx != -1:
        return path[idx:]
    # Parte dopo la cartella configurata UPLOAD_FOLDER
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '')
    if upload_folder and path.startswith(upload_folder):
        rel = path[len(upload_folder):].lstrip(os.sep)
        return f'/uploads/{rel}'
    # Path relativo tipo "uploads/weekly_checks/..."
    if path.startswith('uploads/'):
        return f'/{path}'
    # Fallback: wrappa in /uploads/
    return f'/uploads/{path}'


def _can_access_cliente_checks(cliente_id: int) -> bool:
    accessible_query = get_accessible_clients_query()
    if accessible_query is None:
        return True
    return db.session.query(accessible_query.filter(Cliente.cliente_id == cliente_id).exists()).scalar()


def _abort_if_no_cliente_checks_access(cliente_id: int) -> None:
    if not _can_access_cliente_checks(cliente_id):
        abort(HTTPStatus.FORBIDDEN, description="Non autorizzato a visualizzare i check di questo paziente.")


def _frontend_base_url() -> str:
    """
    Calcola il base URL del frontend pubblico per i link dei check.
    Priorita:
    1) Config applicativa esplicita
    2) Header Origin della richiesta browser
    3) Header Referer
    4) Header forwardati dal proxy
    5) Host della richiesta corrente
    """
    configured = (
        current_app.config.get("FRONTEND_BASE_URL")
        or current_app.config.get("FRONTEND_URL")
        or ""
    ).strip()
    if configured:
        return configured.rstrip("/")

    origin = (request.headers.get("Origin") or "").strip()
    if origin:
        parsed = urlparse(origin)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"

    referer = (request.headers.get("Referer") or "").strip()
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"

    forwarded_host = (request.headers.get("X-Forwarded-Host") or "").split(",")[0].strip()
    if forwarded_host:
        forwarded_proto = (request.headers.get("X-Forwarded-Proto") or request.scheme).split(",")[0].strip()
        scheme = forwarded_proto if forwarded_proto else request.scheme
        return f"{scheme}://{forwarded_host}"

    return request.host_url.rstrip("/")


def _get_weekly_professional_snapshot(cliente: Cliente | None) -> Dict[str, int | None]:
    """
    Restituisce gli ID professionisti da salvare nel WeeklyCheckResponse
    come snapshot storico al momento della compilazione.
    """
    if not cliente:
        return {
            "nutritionist_user_id": None,
            "psychologist_user_id": None,
            "coach_user_id": None,
        }

    nutritionist_id = cliente.nutrizionista_id
    if not nutritionist_id and cliente.nutrizionisti_multipli:
        nutritionist_id = cliente.nutrizionisti_multipli[0].id

    psychologist_id = cliente.psicologa_id
    if not psychologist_id and cliente.psicologi_multipli:
        psychologist_id = cliente.psicologi_multipli[0].id

    coach_id = cliente.coach_id
    if not coach_id and cliente.coaches_multipli:
        coach_id = cliente.coaches_multipli[0].id

    return {
        "nutritionist_user_id": nutritionist_id,
        "psychologist_user_id": psychologist_id,
        "coach_user_id": coach_id,
    }

# --------------------------------------------------------------------------- #
#  Blueprint setup                                                            #
# --------------------------------------------------------------------------- #

# Importa il blueprint già definito in __init__.py
# Importa il blueprint già definito in __init__.py
from . import client_checks_bp

# API Blueprint (Standard Pattern)
api_bp = Blueprint(
    'client_checks_api',
    __name__,
    url_prefix='/api/client-checks'
)
csrf.exempt(api_bp)  # Exclude API from CSRF since it uses Tokens/Session with different mechanism if needed or just standard API rules


# --------------------------------------------------------------------------- #
#  Route Admin - Dashboard                                                    #
# --------------------------------------------------------------------------- #

@client_checks_bp.route("/")
@login_required
def dashboard():
    """Dashboard principale con statistiche generali."""
    try:
        # Statistiche generali
        total_forms = CheckForm.query.filter_by(is_active=True).count()
        total_assignments = ClientCheckAssignment.query.filter_by(is_active=True).count()
        total_responses = ClientCheckResponse.query.count()
        
        # Form recenti
        recent_forms = (
            CheckForm.query
            .filter_by(is_active=True)
            .order_by(desc(CheckForm.created_at))
            .limit(5)
            .all()
        )
        
        # Risposte recenti
        recent_responses = (
            ClientCheckResponse.query
            .options(
                joinedload(ClientCheckResponse.assignment)
                .joinedload(ClientCheckAssignment.cliente),
                joinedload(ClientCheckResponse.assignment)
                .joinedload(ClientCheckAssignment.form)
            )
            .order_by(desc(ClientCheckResponse.created_at))
            .limit(10)
            .all()
        )
        
        return render_template(
            "client_checks/dashboard_modern.html",
            total_forms=total_forms,
            total_assignments=total_assignments,
            total_responses=total_responses,
            recent_forms=recent_forms,
            recent_responses=recent_responses,
        )
    except HTTPException:
        raise
    except Exception as e:
        current_app.logger.error(f"Errore dashboard client_checks: {e}")
        flash("Errore nel caricamento della dashboard", "error")
        return redirect(url_for("welcome.index"))


# --------------------------------------------------------------------------- #
#  Route Professionisti - Check da Leggere                                   #
# --------------------------------------------------------------------------- #

@client_checks_bp.route("/da-leggere")
@login_required
def da_leggere():
    """
    Pagina per professionisti: mostra tutti i check WeeklyCheck e DCACheck
    dei loro clienti che devono ancora leggere (da oggi in poi).
    """
    from datetime import date
    from corposostenibile.models import (
        ClientCheckReadConfirmation,
        WeeklyCheck,
        WeeklyCheckResponse,
        DCACheck,
        DCACheckResponse
    )

    # Ottieni i clienti visibili in base al ruolo
    query = db.session.query(Cliente)
    
    # 1. Admin: vede tutto (ma qui filtriamo solo chi ha check non letti dopo)
    if current_user.role == UserRoleEnum.admin:
        # Recupera TUTTI i clienti che hanno check
        # In questo contesto "da_leggere" per admin potrebbe mostrare tutto, 
        # ma per coerenza con la logica "Inbox" manteniamo il focus.
        # Tuttavia, se l'admin vuole vedere tutto, non applichiamo filtri qui
        # e lasciamo che la join successiva trovi i check non letti.
        pass

    # 2. Team Leader: vede i clienti assegnati ai membri del proprio team
    elif current_user.role == UserRoleEnum.team_leader:
        team_member_ids = set()
        # Includi se stesso
        team_member_ids.add(current_user.id)
        # Includi membri dei team guidati
        for team in (current_user.teams_led or []):
            for member in (team.members or []):
                team_member_ids.add(member.id)
        
        member_ids_list = list(team_member_ids)
        
        query = query.filter(
            db.or_(
                # Relazioni singole (foreign keys) - controlla se assegnato a QUALSIASI membro del team
                Cliente.nutrizionista_id.in_(member_ids_list),
                Cliente.coach_id.in_(member_ids_list),
                Cliente.psicologa_id.in_(member_ids_list),
                Cliente.consulente_alimentare_id.in_(member_ids_list),
                # Relazioni multiple - controlla se QUALSIASI membro del team è nelle liste
                Cliente.nutrizionisti_multipli.any(User.id.in_(member_ids_list)),
                Cliente.coaches_multipli.any(User.id.in_(member_ids_list)),
                Cliente.psicologi_multipli.any(User.id.in_(member_ids_list)),
                Cliente.consulenti_multipli.any(User.id.in_(member_ids_list)),
                # Assegnazione tramite history (es. Medico nel team)
                exists(
                    select(ClienteProfessionistaHistory.cliente_id).where(
                        ClienteProfessionistaHistory.cliente_id == Cliente.cliente_id,
                        ClienteProfessionistaHistory.user_id.in_(member_ids_list),
                        ClienteProfessionistaHistory.is_active == True,
                    )
                ),
            )
        )

    # 3. Professionista: vede solo i propri clienti (inclusi assegnazioni da history, es. Medico)
    else:
        query = query.filter(
            db.or_(
                # Relazioni singole (foreign keys)
                Cliente.nutrizionista_id == current_user.id,
                Cliente.coach_id == current_user.id,
                Cliente.psicologa_id == current_user.id,
                Cliente.consulente_alimentare_id == current_user.id,
                # Relazioni multiple (many-to-many)
                Cliente.nutrizionisti_multipli.any(User.id == current_user.id),
                Cliente.coaches_multipli.any(User.id == current_user.id),
                Cliente.psicologi_multipli.any(User.id == current_user.id),
                Cliente.consulenti_multipli.any(User.id == current_user.id),
                # Assegnazione tramite ClienteProfessionistaHistory (es. Medico)
                exists(
                    select(ClienteProfessionistaHistory.cliente_id).where(
                        ClienteProfessionistaHistory.cliente_id == Cliente.cliente_id,
                        ClienteProfessionistaHistory.user_id == current_user.id,
                        ClienteProfessionistaHistory.is_active == True,
                    )
                ),
            )
        )

    my_clienti = query.all()
    my_clienti_ids = [c.cliente_id for c in my_clienti]

    if not my_clienti_ids:
        return render_template(
            "client_checks/da_leggere.html",
            responses_to_read=[],
            total_to_read=0
        )

    all_responses = []

    # 1. WeeklyCheckResponse non ancora letti
    weekly_responses = (
        WeeklyCheckResponse.query
        .join(WeeklyCheck)
        .join(Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id)
        .outerjoin(
            ClientCheckReadConfirmation,
            and_(
                ClientCheckReadConfirmation.response_type == 'weekly_check',
                ClientCheckReadConfirmation.response_id == WeeklyCheckResponse.id,
                ClientCheckReadConfirmation.user_id == current_user.id
            )
        )
        .filter(
            Cliente.cliente_id.in_(my_clienti_ids),
            ClientCheckReadConfirmation.id.is_(None)
        )
        .options(
            joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente)
        )
        .all()
    )
    for resp in weekly_responses:
        resp.check_type = 'Weekly'
        resp.response_type = 'weekly_check'
    all_responses.extend(weekly_responses)

    # 2. DCACheckResponse non ancora letti
    dca_responses = (
        DCACheckResponse.query
        .join(DCACheck)
        .join(Cliente, DCACheck.cliente_id == Cliente.cliente_id)
        .outerjoin(
            ClientCheckReadConfirmation,
            and_(
                ClientCheckReadConfirmation.response_type == 'dca_check',
                ClientCheckReadConfirmation.response_id == DCACheckResponse.id,
                ClientCheckReadConfirmation.user_id == current_user.id
            )
        )
        .filter(
            Cliente.cliente_id.in_(my_clienti_ids),
            ClientCheckReadConfirmation.id.is_(None)
        )
        .options(
            joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente)
        )
        .all()
    )
    for resp in dca_responses:
        resp.check_type = 'DCA'
        resp.response_type = 'dca_check'
    all_responses.extend(dca_responses)

    # Ordina per data più recente
    from datetime import datetime
    all_responses.sort(key=lambda x: x.submit_date if x.submit_date else datetime.min, reverse=True)

    return render_template(
        "client_checks/da_leggere.html",
        responses_to_read=all_responses,
        total_to_read=len(all_responses)
    )


@client_checks_bp.route("/conferma-lettura/<string:response_type>/<int:response_id>", methods=["POST"])
@login_required
def conferma_lettura(response_type, response_id):
    """
    Conferma la lettura di un check (WeeklyCheck o DCACheck) da parte del professionista.
    """
    from corposostenibile.models import (
        ClientCheckReadConfirmation,
        WeeklyCheck,
        WeeklyCheckResponse,
        DCACheck,
        DCACheckResponse
    )
    from datetime import datetime

    try:
        # Validate response_type
        if response_type not in ['weekly_check', 'dca_check']:
            flash("Tipo di check non valido", "error")
            return redirect(url_for("client_checks.da_leggere"))

        # Get the response based on type
        if response_type == 'weekly_check':
            response = WeeklyCheckResponse.query.get_or_404(response_id)
            cliente = response.assignment.cliente if response.assignment else None
        else:  # dca_check
            response = DCACheckResponse.query.get_or_404(response_id)
            cliente = response.assignment.cliente if response.assignment else None

        if not cliente:
            flash("Cliente non trovato per questo check", "error")
            return redirect(url_for("client_checks.da_leggere"))

        # Verify professional is assigned
        is_assigned = (
            cliente.nutrizionista_id == current_user.id or
            cliente.coach_id == current_user.id or
            cliente.psicologa_id == current_user.id or
            cliente.consulente_alimentare_id == current_user.id or
            current_user in cliente.nutrizionisti_multipli or
            current_user in cliente.coaches_multipli or
            current_user in cliente.psicologi_multipli or
            current_user in cliente.consulenti_multipli
        )

        if not is_assigned and not current_user.is_admin and current_user.id != 95:
            flash("Non sei autorizzato a confermare la lettura di questo check", "error")
            return redirect(url_for("client_checks.da_leggere"))

        # Check if already confirmed
        existing = ClientCheckReadConfirmation.query.filter_by(
            response_type=response_type,
            response_id=response_id,
            user_id=current_user.id
        ).first()

        if existing:
            flash("Hai già confermato la lettura di questo check", "warning")
        else:
            confirmation = ClientCheckReadConfirmation(
                response_type=response_type,
                response_id=response_id,
                user_id=current_user.id,
                read_at=datetime.utcnow()
            )
            db.session.add(confirmation)
            db.session.commit()
            flash("Lettura confermata con successo", "success")

        return redirect(url_for("client_checks.da_leggere"))

    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore conferma lettura: {e}")
        flash("Errore durante la conferma di lettura", "error")
        return redirect(url_for("client_checks.da_leggere"))


# --------------------------------------------------------------------------- #
#  Route Admin - Gestione Form                                               #
# --------------------------------------------------------------------------- #

@client_checks_bp.route("/forms/")
@login_required
def forms_list():
    """Lista di tutti i form check."""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = 20
        
        # Filtri
        form_type = request.args.get("type")
        search = request.args.get("search", "").strip()
        
        query = CheckForm.query
        
        if form_type and form_type in [e.value for e in CheckFormTypeEnum]:
            query = query.filter(CheckForm.form_type == form_type)
        
        if search:
            query = query.filter(CheckForm.name.ilike(f"%{search}%"))
        
        forms = (
            query
            .order_by(desc(CheckForm.created_at))
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        )
        
        return render_template(
            "client_checks/form_list_modern.html",
            forms=forms,
            form_types=CheckFormTypeEnum,
            current_type=form_type,
            current_search=search,
        )
    except HTTPException:
        raise
    except Exception as e:
        current_app.logger.error(f"Errore lista form: {e}")
        flash("Errore nel caricamento dei form", "error")
        return redirect(url_for("client_checks.dashboard"))


@client_checks_bp.route("/forms/create", methods=["GET", "POST"])
@login_required
def create_form():
    """Crea un nuovo form check."""
    if request.method == "POST":
        # Gestisci richieste JSON dal frontend
        if request.is_json:
            try:
                data = request.get_json()
                
                # Validazione base
                if not data.get('name'):
                    return jsonify({"success": False, "message": "Nome form richiesto"}), 400
                
                if not data.get('fields') or len(data.get('fields', [])) == 0:
                    return jsonify({"success": False, "message": "Almeno un campo è richiesto"}), 400
                
                # Crea il form
                check_form = CheckFormService.create_form(
                    name=data['name'],
                    description=data.get('description', ''),
                    form_type=data.get('form_type', 'standard'),
                    created_by_id=current_user.id,
                    department_id=current_user.department_id,  # Usa il dipartimento dell'utente corrente
                    fields_data=data['fields'],
                )
                
                return jsonify({
                    "success": True, 
                    "message": f"Form '{check_form.name}' creato con successo!",
                    "redirect": url_for("client_checks.edit_form", id=check_form.id)
                })
                
            except Exception as e:
                current_app.logger.error(f"Errore creazione form: {e}")
                return jsonify({"success": False, "message": "Errore nella creazione del form"}), 500
        
        # Gestisci form HTML tradizionale (fallback)
        else:
            form = CheckFormForm()
            if form.validate_on_submit():
                try:
                    check_form = CheckFormService.create_form(
                        name=form.name.data,
                        description=form.description.data,
                        form_type=form.form_type.data,
                        created_by_id=current_user.id,
                        department_id=form.department_id.data,
                        fields_data=form.fields.data,
                    )
                    
                    flash(f"Form '{check_form.name}' creato con successo!", "success")
                    return redirect(url_for("client_checks.edit_form", id=check_form.id))
                    
                except Exception as e:
                    current_app.logger.error(f"Errore creazione form: {e}")
                    flash("Errore nella creazione del form", "error")
    
    # GET request - mostra il form builder
    form = CheckFormForm()
    return render_template("client_checks/form_builder.html", form=form)


@client_checks_bp.route("/forms/<int:id>/preview")
@login_required
def preview_form(id: int):
    """Visualizza l'anteprima di un form check."""
    try:
        form = CheckForm.query.options(
            joinedload(CheckForm.fields)
        ).filter_by(id=id).first()
        
        if not form:
            flash("Form non trovato", "error")
            return redirect(url_for("client_checks.forms_list"))
        
        return render_template(
            "client_checks/form_preview.html",
            form=form
        )
    except HTTPException:
        raise
    except Exception as e:
        current_app.logger.error(f"Errore anteprima form {id}: {e}")
        flash("Errore nel caricamento dell'anteprima", "error")
        return redirect(url_for("client_checks.forms_list"))


@client_checks_bp.route("/forms/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_form(id: int):
    """Modifica un form esistente."""
    check_form = CheckForm.query.get_or_404(id)
    form = CheckFormForm(obj=check_form)
    
    if request.method == "POST":
        # Gestisce richieste JSON dal JavaScript
        if request.is_json:
            try:
                data = request.get_json()
                updated_form = CheckFormService.update_form(
                    form_id=id,
                    name=data.get('name'),
                    description=data.get('description'),
                    form_type=data.get('form_type'),
                    department_id=data.get('department_id'),
                    fields_data=data.get('fields', []),
                )
                
                return jsonify({
                    'success': True,
                    'message': f"Form '{updated_form.name}' aggiornato con successo!",
                    'redirect': url_for("client_checks.forms_list")
                })
                
            except Exception as e:
                current_app.logger.error(f"Errore aggiornamento form: {e}")
                return jsonify({
                    'success': False,
                    'message': f'Errore nell\'aggiornamento del form: {str(e)}'
                }), 400
        
        # Gestisce form submission tradizionale
        elif form.validate_on_submit():
            try:
                updated_form = CheckFormService.update_form(
                    form_id=id,
                    name=form.name.data,
                    description=form.description.data,
                    form_type=form.form_type.data,
                    department_id=form.department_id.data,
                    fields_data=form.fields.data,
                )
                
                flash(f"Form '{updated_form.name}' aggiornato con successo!", "success")
                return redirect(url_for("client_checks.forms_list"))
                
            except Exception as e:
                current_app.logger.error(f"Errore aggiornamento form: {e}")
                flash("Errore nell'aggiornamento del form", "error")
    
    # Prepara i dati dei campi esistenti per il JavaScript
    fields_json = []
    if check_form.fields:
        for field in check_form.fields:
            field_data = {
                'id': field.id,
                'label': field.label,
                'field_type': field.field_type.value,
                'is_required': field.is_required,
                'position': field.position,
            }
            if field.options:
                field_data['options'] = field.options
            if field.placeholder:
                field_data['placeholder'] = field.placeholder
            if field.help_text:
                field_data['help_text'] = field.help_text
            fields_json.append(field_data)
    
    return render_template("client_checks/form_builder.html", form=form, check_form=check_form, fields_json=fields_json)


@client_checks_bp.route("/forms/<int:id>/delete", methods=["POST"])
@login_required
def delete_form(id: int):
    """Elimina un form (soft delete)."""
    try:
        CheckFormService.delete_form(id)
        flash("Form eliminato con successo!", "success")
    except HTTPException:
        raise
    except Exception as e:
        current_app.logger.error(f"Errore eliminazione form: {e}")
        flash("Errore nell'eliminazione del form", "error")
    
    return redirect(url_for("client_checks.forms_list"))


@client_checks_bp.route("/forms/<int:id>", methods=["POST"])
@login_required
def delete_form_api(id: int):
    """Elimina un form via API (soft delete)."""
    try:
        CheckFormService.delete_form(id)
        return jsonify({"success": True, "message": "Form eliminato con successo!"})
    except HTTPException:
        raise
    except Exception as e:
        current_app.logger.error(f"Errore eliminazione form: {e}")
        return jsonify({"success": False, "error": "Errore nell'eliminazione del form"}), 500


# --------------------------------------------------------------------------- #
#  Route Admin - Assegnazioni                                                #
# --------------------------------------------------------------------------- #

@client_checks_bp.route("/assign", methods=["GET", "POST"])
@login_required
def assign_form():
    """Assegna un form a uno o più clienti."""
    form = ClientCheckAssignmentForm()

    # Populate form choices
    form.check_form_id.choices = [(0, '-- Seleziona un form --')] + [
        (f.id, f.name)
        for f in CheckForm.query.filter_by(is_active=True).order_by(CheckForm.name).all()
    ]

    if form.validate_on_submit():
        try:
            assignments = ClientCheckService.assign_form_to_clients(
                form_id=form.check_form_id.data,
                client_ids=form.client_ids.data,
                assigned_by_id=current_user.id,
                send_notifications=form.send_notification.data,
            )

            current_app.logger.info(f"--------------------------------------------Form assegnato a {len(assignments)} clienti!")
            flash(f"Form assegnato a {len(assignments)} clienti!", "success")
            return redirect(url_for("client_checks.assignments_list"))

        except Exception as e:
            current_app.logger.error(f"------------------------------------------Errore assegnazione form: {e}")
            flash("Errore nell'assegnazione del form", "error")

    # Get available clients for the template
    page = request.args.get("page", 1, type=int)
    # Filter active clients only
    clients = Cliente.query.filter(
        Cliente.stato_cliente.in_([StatoClienteEnum.attivo, StatoClienteEnum.pausa])
    ).order_by(Cliente.nome_cognome).paginate(page=page, per_page=50)

    # Packages list empty for now (no direct package field in Cliente)
    packages = []

    return render_template("client_checks/assign_form_modern.html",
                         form=form,
                         clients=clients,
                         packages=packages)


@client_checks_bp.route("/assign/<int:client_id>", methods=["POST"])
@login_required
def assign_to_single_client(client_id: int):
    """Assegna un form a un singolo cliente (chiamata dai modal del dettaglio cliente)."""
    try:
        # Verifica che il cliente esista
        cliente = Cliente.query.get_or_404(client_id)

        # Estrai dati dal form
        form_id = request.form.get('form_id', type=int)
        if not form_id:
            flash("Seleziona un form da assegnare", "error")
            return redirect(url_for("customers.detail_view", cliente_id=client_id))

        # Verifica che il form esista
        check_form = CheckForm.query.get_or_404(form_id)

        # Assegna il form al cliente
        assignment = ClientCheckService.assign_form_to_client(
            form_id=form_id,
            client_id=client_id,
            assigned_by_id=current_user.id,
            send_notification=True
        )

        if assignment:
            flash(f"Check '{check_form.name}' assegnato con successo a {cliente.nome_cognome}!", "success")
        else:
            flash("Questo check è già stato assegnato a questo cliente", "warning")

        return redirect(url_for("customers.detail_view", cliente_id=client_id))

    except HTTPException:
        raise
    except Exception as e:
        current_app.logger.error(f"Errore assegnazione check a cliente {client_id}: {e}")
        flash("Errore nell'assegnazione del check", "error")
        return redirect(url_for("customers.detail_view", cliente_id=client_id))


@client_checks_bp.route("/assignments/")
@login_required
def assignments_list():
    """Lista delle assegnazioni form-cliente."""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = 20
        
        # Filtri
        form_id = request.args.get("form_id", type=int)
        client_search = request.args.get("client_search", "").strip()
        status = request.args.get("status")  # active, completed, pending
        
        query = (
            ClientCheckAssignment.query
            .options(
                joinedload(ClientCheckAssignment.cliente),
                joinedload(ClientCheckAssignment.form),
                joinedload(ClientCheckAssignment.assigned_by)
            )
        )
        
        if form_id:
            query = query.filter(ClientCheckAssignment.form_id == form_id)
        
        if client_search:
            query = query.join(Cliente).filter(
                Cliente.nome.ilike(f"%{client_search}%") |
                Cliente.cognome.ilike(f"%{client_search}%")
            )
        
        if status == "completed":
            query = query.filter(ClientCheckAssignment.response_count > 0)
        elif status == "pending":
            query = query.filter(ClientCheckAssignment.response_count == 0)
        elif status == "active":
            query = query.filter(ClientCheckAssignment.is_active == True)
        
        assignments = (
            query
            .order_by(desc(ClientCheckAssignment.created_at))
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        )
        
        # Form disponibili per filtro
        available_forms = CheckForm.query.filter_by(is_active=True).all()
        
        return render_template(
            "client_checks/assignments_list.html",
            assignments=assignments,
            available_forms=available_forms,
            current_form_id=form_id,
            current_client_search=client_search,
            current_status=status,
        )
    except Exception as e:
        current_app.logger.error(f"Errore lista assegnazioni: {e}")
        flash("Errore nel caricamento delle assegnazioni", "error")
        return redirect(url_for("client_checks.dashboard"))


# --------------------------------------------------------------------------- #
#  Route Admin - Risposte                                                    #
# --------------------------------------------------------------------------- #

@client_checks_bp.route("/responses/")
@login_required
def responses_list():
    """Lista delle risposte ricevute."""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = 20
        
        # Filtri
        form_id = request.args.get("form_id", type=int)
        client_search = request.args.get("client_search", "").strip()
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        
        query = (
            ClientCheckResponse.query
            .options(
                joinedload(ClientCheckResponse.assignment)
                .joinedload(ClientCheckAssignment.cliente),
                joinedload(ClientCheckResponse.assignment)
                .joinedload(ClientCheckAssignment.form)
            )
        )
        
        if form_id:
            query = query.join(ClientCheckAssignment).filter(
                ClientCheckAssignment.form_id == form_id
            )
        
        if client_search:
            query = query.join(ClientCheckAssignment).join(Cliente).filter(
                Cliente.nome.ilike(f"%{client_search}%") |
                Cliente.cognome.ilike(f"%{client_search}%")
            )
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(ClientCheckResponse.created_at >= date_from_obj)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
                query = query.filter(ClientCheckResponse.created_at <= date_to_obj)
            except ValueError:
                pass
        
        responses = (
            query
            .order_by(desc(ClientCheckResponse.created_at))
            .paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
        )
        
        # Form disponibili per filtro
        available_forms = CheckForm.query.filter_by(is_active=True).all()
        
        return render_template(
            "client_checks/responses_view.html",
            responses=responses,
            available_forms=available_forms,
            current_form_id=form_id,
            current_client_search=client_search,
            current_date_from=date_from,
            current_date_to=date_to,
        )
    except Exception as e:
        current_app.logger.error(f"Errore lista risposte: {e}")
        flash("Errore nel caricamento delle risposte", "error")
        return redirect(url_for("client_checks.dashboard"))


@client_checks_bp.route("/responses/<int:id>")
@login_required
def response_detail(id: int):
    """Dettaglio di una risposta specifica."""
    try:
        response = (
            ClientCheckResponse.query
            .options(
                joinedload(ClientCheckResponse.assignment)
                .joinedload(ClientCheckAssignment.cliente),
                joinedload(ClientCheckResponse.assignment)
                .joinedload(ClientCheckAssignment.form)
                .joinedload(CheckForm.fields)
            )
            .get_or_404(id)
        )

        # Formatta le risposte per la visualizzazione
        formatted_responses = format_response_data(response)

        return render_template(
            "client_checks/response_detail.html",
            response=response,
            formatted_responses=formatted_responses,
        )
    except Exception as e:
        current_app.logger.error(f"Errore dettaglio risposta: {e}")
        flash("Errore nel caricamento della risposta", "error")
        return redirect(url_for("client_checks.responses_list"))


@client_checks_bp.route("/responses/<int:id>/data")
@login_required
def response_data(id: int):
    """Restituisce i dati della risposta in formato JSON per il modal."""
    try:
        response = (
            ClientCheckResponse.query
            .options(
                joinedload(ClientCheckResponse.assignment)
                .joinedload(ClientCheckAssignment.form)
                .joinedload(CheckForm.fields)
            )
            .get_or_404(id)
        )

        # Prepara i dati delle risposte
        responses_data = []
        for field in sorted(response.assignment.form.fields, key=lambda f: f.position):
            field_value = response.get_response_value(field.id)
            responses_data.append({
                'label': field.label,
                'field_type': field.field_type.value if hasattr(field.field_type, 'value') else str(field.field_type),
                'is_required': field.is_required,
                'value': field_value,
                'options': field.options if field.options else {}
            })

        # Prepara la risposta JSON
        data = {
            'form_name': response.assignment.form.name,
            'form_description': response.assignment.form.description,
            'created_at': response.created_at.strftime('%d/%m/%Y %H:%M') if response.created_at else None,
            'ip_address': response.ip_address,
            'user_agent': response.user_agent,
            'responses': responses_data
        }

        return jsonify(data)

    except Exception as e:
        current_app.logger.error(f"Errore nel recupero dati risposta: {e}")
        return jsonify({'error': f'Errore nel caricamento dei dati: {e}'}), 500


# --------------------------------------------------------------------------- #
#  Route Pubbliche - Compilazione Form                                       #
# --------------------------------------------------------------------------- #

@client_checks_bp.route("/public/<token>", methods=["GET", "POST"])
@csrf.exempt
def public_form(token: str):
    """Compilazione pubblica di un form tramite token."""
    current_app.logger.info(f"[PUBLIC_FORM] Richiesta ricevuta per token: {token}")
    try:
        # Trova l'assignment tramite token
        current_app.logger.debug(f"[PUBLIC_FORM] Query database per token: {token}")
        assignment = (
            ClientCheckAssignment.query
            .options(
                joinedload(ClientCheckAssignment.cliente),
                joinedload(ClientCheckAssignment.form)
                .joinedload(CheckForm.fields)
            )
            .filter_by(token=token, is_active=True)
            .first_or_404()
        )
        current_app.logger.info(f"[PUBLIC_FORM] Assignment trovato: ID={assignment.id}")
        
        # Verifica che il form sia attivo
        if not assignment.form.is_active:
            abort(404)
        
        # Crea form dinamico basato sui campi
        form_class = DynamicCheckForm.create_form_class(assignment.form.fields)
        form = form_class()
        
        if request.method == "POST" and form.validate_on_submit():
            try:
                # Evita compilazioni multiple dello stesso check
                if assignment.response_count > 0:
                    flash("Questo check e' gia' stato compilato.", "info")
                    return redirect(url_for("client_checks.public_success", token=token))

                # Salva la risposta
                response = ClientCheckService.save_response(
                    assignment_id=assignment.id,
                    form_data=form.data,
                    ip_address=get_client_ip(),
                    user_agent=get_user_agent(),
                )
                
                # Invia notifiche se configurate
                if assignment.form.department:
                    NotificationService.send_response_notifications(response)
                
                flash("Grazie! La tua risposta è stata salvata con successo.", "success")
                return redirect(url_for("client_checks.public_success", token=token))
                
            except Exception as e:
                current_app.logger.error(f"Errore salvataggio risposta: {e}")
                flash("Errore nel salvataggio. Riprova più tardi.", "error")
        
        return render_template(
            "client_checks/public_form.html",
            form=form,
            assignment=assignment,
            token=token,
        )
        
    except Exception as e:
        current_app.logger.error(f"[PUBLIC_FORM] Errore form pubblico: {e}", exc_info=True)
        abort(404)


@client_checks_bp.route("/public/<token>/success")
@csrf.exempt
def public_success(token: str):
    """Pagina di conferma dopo invio form."""
    try:
        assignment = (
            ClientCheckAssignment.query
            .options(
                joinedload(ClientCheckAssignment.cliente),
                joinedload(ClientCheckAssignment.form)
            )
            .filter_by(token=token, is_active=True)
            .first_or_404()
        )
        
        return render_template(
            "client_checks/public_success.html",
            assignment=assignment,
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore pagina successo: {e}")
        abort(404)


# --------------------------------------------------------------------------- #
#  API Routes                                                                 #
# --------------------------------------------------------------------------- #

@client_checks_bp.route("/api/clients/search")
@login_required
def api_clients_search():
    """API per ricerca clienti (per autocomplete)."""
    try:
        query = request.args.get("q", "").strip()
        if len(query) < 2:
            return jsonify([])
        
        clients = (
            Cliente.query
            .filter(
                Cliente.nome.ilike(f"%{query}%") |
                Cliente.cognome.ilike(f"%{query}%")
            )
            .limit(20)
            .all()
        )
        
        results = [
            {
                "id": client.cliente_id,
                "text": f"{client.nome} {client.cognome}",
                "email": client.email,
            }
            for client in clients
        ]
        
        return jsonify(results)
        
    except Exception as e:
        current_app.logger.error(f"Errore ricerca clienti: {e}")
        return jsonify([]), 500


@client_checks_bp.route("/api/forms/<int:form_id>/preview")
@login_required
def api_form_preview(form_id: int):
    """API per anteprima form."""
    try:
        form = (
            CheckForm.query
            .options(joinedload(CheckForm.fields))
            .get_or_404(form_id)
        )
        
        fields_data = [
            {
                "id": field.id,
                "label": field.label,
                "type": field.field_type.value,
                "required": field.is_required,
                "options": field.options,
                "placeholder": field.placeholder,
                "help_text": field.help_text,
            }
            for field in form.fields
        ]
        
        return jsonify({
            "id": form.id,
            "name": form.name,
            "description": form.description,
            "type": form.form_type.value,
            "fields": fields_data,
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore anteprima form: {e}")
        return jsonify({"error": "Form non trovato"}), 404


# --------------------------------------------------------------------------- #
#  Weekly Check 2.0 Routes                                                    #
# --------------------------------------------------------------------------- #

@client_checks_bp.route("/weekly/<token>", methods=["GET", "POST"])
@csrf.exempt
def weekly_check_public(token: str):
    """
    Route pubblica per compilazione Check Settimanale 2.0 tramite token PERMANENTE.

    Il cliente accede tramite link univoco del tipo:
    https://suite.corposostenibile.com/client-checks/weekly/<TOKEN>

    LINK PERMANENTE: il cliente può compilare più volte usando lo stesso link.
    Ogni compilazione crea un nuovo record WeeklyCheckResponse.
    """
    from werkzeug.utils import secure_filename
    from corposostenibile.models import WeeklyCheck, WeeklyCheckResponse
    from .forms import WeeklyCheckForm
    import secrets
    import os

    current_app.logger.info(f"[WEEKLY_CHECK] Richiesta ricevuta per token: {token}")

    try:
        # Trova l'assignment PERMANENTE tramite token
        weekly_check = (
            WeeklyCheck.query
            .options(joinedload(WeeklyCheck.cliente))
            .filter_by(token=token, is_active=True)
            .first()
        )

        if not weekly_check:
            current_app.logger.warning(f"[WEEKLY_CHECK] Token non valido o assignment disattivato: {token}")
            abort(404, "Link non valido o disattivato.")

        form = WeeklyCheckForm()

        if request.method == "POST" and form.validate_on_submit():
            try:
                current_app.logger.info(
                    f"[WEEKLY_CHECK] Inizio salvataggio compilazione per cliente_id={weekly_check.cliente_id} "
                    f"(compilazione #{weekly_check.response_count + 1})"
                )

                # ─── CREA NUOVA RISPOSTA ────────────────────────────────────
                response = WeeklyCheckResponse(
                    weekly_check_id=weekly_check.id,
                    submit_date=datetime.utcnow(),
                    ip_address=get_client_ip(),
                    user_agent=get_user_agent(),
                )
                snapshot = _get_weekly_professional_snapshot(weekly_check.cliente)
                response.nutritionist_user_id = snapshot["nutritionist_user_id"]
                response.psychologist_user_id = snapshot["psychologist_user_id"]
                response.coach_user_id = snapshot["coach_user_id"]

                # ─── UPLOAD FOTO ────────────────────────────────────────────
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                photos_folder = os.path.join(upload_folder, 'weekly_checks', str(weekly_check.cliente_id))
                os.makedirs(photos_folder, exist_ok=True)

                # Foto frontale
                if form.photo_front.data:
                    file = form.photo_front.data
                    filename = secure_filename(f"wc{weekly_check.id}_resp_front_{secrets.token_hex(8)}{os.path.splitext(file.filename)[1]}")
                    filepath = os.path.join(photos_folder, filename)
                    file.save(filepath)
                    response.photo_front = filepath
                    current_app.logger.debug(f"[WEEKLY_CHECK] Foto frontale salvata: {filepath}")

                # Foto laterale
                if form.photo_side.data:
                    file = form.photo_side.data
                    filename = secure_filename(f"wc{weekly_check.id}_resp_side_{secrets.token_hex(8)}{os.path.splitext(file.filename)[1]}")
                    filepath = os.path.join(photos_folder, filename)
                    file.save(filepath)
                    response.photo_side = filepath
                    current_app.logger.debug(f"[WEEKLY_CHECK] Foto laterale salvata: {filepath}")

                # Foto posteriore
                if form.photo_back.data:
                    file = form.photo_back.data
                    filename = secure_filename(f"wc{weekly_check.id}_resp_back_{secrets.token_hex(8)}{os.path.splitext(file.filename)[1]}")
                    filepath = os.path.join(photos_folder, filename)
                    file.save(filepath)
                    response.photo_back = filepath
                    current_app.logger.debug(f"[WEEKLY_CHECK] Foto posteriore salvata: {filepath}")

                # ─── SALVA TUTTI I CAMPI NELLA RESPONSE ────────────────────
                # Riflessioni settimanali
                response.what_worked = form.what_worked.data
                response.what_didnt_work = form.what_didnt_work.data
                response.what_learned = form.what_learned.data
                response.what_focus_next = form.what_focus_next.data
                response.injuries_notes = form.injuries_notes.data

                # Valutazioni benessere (0-10)
                response.digestion_rating = form.digestion_rating.data
                response.energy_rating = form.energy_rating.data
                response.strength_rating = form.strength_rating.data
                response.hunger_rating = form.hunger_rating.data
                response.sleep_rating = form.sleep_rating.data
                response.mood_rating = form.mood_rating.data
                response.motivation_rating = form.motivation_rating.data

                # Peso
                response.weight = form.weight.data

                # Aderenza ai programmi
                response.nutrition_program_adherence = form.nutrition_program_adherence.data
                response.training_program_adherence = form.training_program_adherence.data
                response.exercise_modifications = form.exercise_modifications.data
                response.daily_steps = form.daily_steps.data
                response.completed_training_weeks = form.completed_training_weeks.data
                response.planned_training_days = form.planned_training_days.data
                response.live_session_topics = form.live_session_topics.data

                # Valutazioni professionisti (1-10)
                response.nutritionist_rating = form.nutritionist_rating.data
                response.nutritionist_feedback = form.nutritionist_feedback.data
                response.psychologist_rating = form.psychologist_rating.data
                response.psychologist_feedback = form.psychologist_feedback.data
                response.coach_rating = form.coach_rating.data
                response.coach_feedback = form.coach_feedback.data

                # Progresso e referral
                response.progress_rating = form.progress_rating.data
                response.referral = form.referral.data
                response.extra_comments = form.extra_comments.data

                db.session.add(response)
                try:
                    db.session.commit()
                except Exception as commit_err:
                    db.session.rollback()
                    if "unique" in str(commit_err).lower():
                        _fix_sequence("weekly_check_responses")
                        db.session.add(response)
                        db.session.commit()
                    else:
                        raise

                current_app.logger.info(
                    f"[WEEKLY_CHECK] Response salvata con successo: "
                    f"response_id={response.id}, check_id={weekly_check.id}, "
                    f"totale_compilazioni={weekly_check.response_count}"
                )

                # Invia notifiche ai professionisti associati
                try:
                    NotificationService.send_check_notification_to_professionals(
                        cliente=weekly_check.cliente,
                        check_type='weekly',
                        check_id=response.id
                    )
                except Exception as e:
                    current_app.logger.error(f"[WEEKLY_CHECK] Errore invio notifiche: {e}")
                    # Non bloccare il flusso se l'invio email fallisce

                try:
                    NotificationService.send_weekly_check_summary_to_patient(
                        cliente=weekly_check.cliente,
                        weekly_response=response,
                    )
                except Exception as e:
                    current_app.logger.error(f"[WEEKLY_CHECK] Errore invio riepilogo paziente: {e}")
                    # Non bloccare il flusso se l'invio email fallisce

                flash("Grazie! Il tuo check settimanale è stato salvato con successo.", "success")
                return redirect(url_for("client_checks.weekly_check_success", token=token))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"[WEEKLY_CHECK] Errore nel salvataggio: {e}", exc_info=True)
                flash("Errore nel salvataggio. Riprova più tardi.", "error")

        # Mostra il form con info sulle compilazioni precedenti
        previous_responses_count = weekly_check.response_count
        last_response_date = weekly_check.last_response_date

        return render_template(
            "client_checks/weekly_check_form.html",
            form=form,
            cliente=weekly_check.cliente,
            token=token,
            previous_responses_count=previous_responses_count,
            last_response_date=last_response_date,
        )

    except Exception as e:
        current_app.logger.error(f"[WEEKLY_CHECK] Errore form pubblico: {e}", exc_info=True)
        abort(404)


@client_checks_bp.route("/weekly/<token>/success")
@csrf.exempt
def weekly_check_success(token: str):
    """Pagina di conferma dopo invio check settimanale."""
    from corposostenibile.models import WeeklyCheck

    try:
        weekly_check = (
            WeeklyCheck.query
            .options(joinedload(WeeklyCheck.cliente))
            .filter_by(token=token)
            .first_or_404()
        )

        return render_template(
            "client_checks/weekly_check_success.html",
            cliente=weekly_check.cliente,
        )

    except Exception as e:
        current_app.logger.error(f"[WEEKLY_CHECK] Errore pagina successo: {e}")
        abort(404)


@client_checks_bp.route("/weekly/generate/<int:cliente_id>", methods=["POST"])
@login_required
def generate_weekly_check_link(cliente_id: int):
    """
    Genera o recupera il link PERMANENTE per il check settimanale di un cliente.

    LINK PERMANENTE: il cliente usa sempre lo stesso link per compilare più volte.
    Se esiste già un assignment attivo, ritorna quello esistente.

    Permessi: utenti con accesso al paziente (RBAC su cliente).
    """
    from corposostenibile.models import WeeklyCheck
    import secrets

    try:
        cliente = Cliente.query.get_or_404(cliente_id)
        _abort_if_no_cliente_checks_access(cliente_id)

        # Cerca assignment ATTIVO esistente
        existing_check = (
            WeeklyCheck.query
            .filter_by(cliente_id=cliente_id, is_active=True)
            .first()
        )

        if existing_check:
            # Assignment già esistente - riutilizza lo stesso link!
            token = existing_check.token
            # URL React frontend
            # Use React frontend port in development
            base_url = _frontend_base_url()
            check_url = f"{base_url}/check/weekly/{token}"

            current_app.logger.info(
                f"[WEEKLY_CHECK] Link PERMANENTE già esistente per {cliente.nome_cognome}: {check_url} "
                f"(compilazioni: {existing_check.response_count})"
            )

            flash(f"Link permanente già attivo per {cliente.nome_cognome}! Compilazioni ricevute: {existing_check.response_count}", "info")

            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    "success": True,
                    "url": check_url,
                    "token": token,
                    "check_id": existing_check.id,
                    "is_new": False,
                    "response_count": existing_check.response_count
                })

            return redirect(url_for("customers.detail_view", cliente_id=cliente_id))

        # Nessun assignment attivo - crea nuovo assignment PERMANENTE
        token = secrets.token_urlsafe(32)

        for attempt in range(2):
            try:
                weekly_check = WeeklyCheck(
                    cliente_id=cliente_id,
                    token=token,
                    is_active=True,
                    assigned_by_id=current_user.id,
                    assigned_at=datetime.utcnow(),
                )
                db.session.add(weekly_check)
                db.session.commit()
                break
            except Exception as seq_err:
                db.session.rollback()
                if attempt == 0 and "unique" in str(seq_err).lower():
                    _fix_sequence("weekly_checks")
                    continue
                raise

        # URL React frontend
        # Use React frontend port in development
        base_url = _frontend_base_url()
        check_url = f"{base_url}/check/weekly/{token}"

        current_app.logger.info(f"[WEEKLY_CHECK] Nuovo link PERMANENTE per {cliente.nome_cognome}: {check_url}")

        flash(f"Link permanente check settimanale generato per {cliente.nome_cognome}!", "success")

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": True,
                "url": check_url,
                "token": token,
                "check_id": weekly_check.id,
                "is_new": True,
                "response_count": 0
            })

        return redirect(url_for("customers.detail_view", cliente_id=cliente_id))

    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[WEEKLY_CHECK] Errore generazione link: {e}", exc_info=True)
        flash("Errore nella generazione del link", "error")

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": str(e)}), 500

        return redirect(url_for("customers.detail_view", cliente_id=cliente_id))


@client_checks_bp.route("/weekly/<int:check_id>/deactivate", methods=["POST"])
@login_required
def deactivate_weekly_check(check_id: int):
    """
    Disattiva un link permanente di check settimanale.

    Il link non sarà più utilizzabile dal cliente, ma le risposte già ricevute
    rimangono salvate.
    """
    from corposostenibile.models import WeeklyCheck

    try:
        weekly_check = WeeklyCheck.query.get_or_404(check_id)

        _abort_if_no_cliente_checks_access(weekly_check.cliente_id)

        # Disattiva il check
        weekly_check.is_active = False
        weekly_check.deactivated_at = datetime.utcnow()
        weekly_check.deactivated_by_id = current_user.id

        db.session.commit()

        current_app.logger.info(
            f"[WEEKLY_CHECK] Link disattivato: check_id={check_id}, "
            f"by={current_user.nome_cognome}, compilazioni={weekly_check.response_count}"
        )

        return jsonify({
            "success": True,
            "message": "Link disattivato con successo",
            "response_count": weekly_check.response_count
        })

    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[WEEKLY_CHECK] Errore disattivazione: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@client_checks_bp.route("/weekly/response/<int:response_id>")
@login_required
def weekly_check_response_view(response_id: int):
    """
    Visualizza il dettaglio di una singola compilazione (WeeklyCheckResponse).
    """
    from corposostenibile.models import WeeklyCheckResponse

    try:
        response = (
            WeeklyCheckResponse.query
            .options(joinedload(WeeklyCheckResponse.assignment))
            .get_or_404(response_id)
        )

        # Verifica permessi (solo admin, user 95, o professionisti del cliente)
        cliente = response.assignment.cliente
        if not current_user.is_admin and current_user.id != 95 and current_user not in [
            cliente.nutrizionista_user,
            cliente.coach_user,
            cliente.psicologo_user
        ]:
            abort(403)

        # Ritorna JSON se richiesto via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": True,
                "response": {
                    "id": response.id,
                    "submit_date": response.submit_date.strftime('%d/%m/%Y %H:%M') if response.submit_date else None,
                    "completion_percentage": response.completion_percentage,

                    # Foto (convertiti da path filesystem a URL web)
                    "photo_front": _photo_path_to_url(response.photo_front),
                    "photo_side": _photo_path_to_url(response.photo_side),
                    "photo_back": _photo_path_to_url(response.photo_back),

                    # Riflessioni
                    "what_worked": response.what_worked,
                    "what_didnt_work": response.what_didnt_work,
                    "what_learned": response.what_learned,
                    "what_focus_next": response.what_focus_next,
                    "injuries_notes": response.injuries_notes,

                    # Valutazioni benessere
                    "digestion_rating": response.digestion_rating,
                    "energy_rating": response.energy_rating,
                    "strength_rating": response.strength_rating,
                    "hunger_rating": response.hunger_rating,
                    "sleep_rating": response.sleep_rating,
                    "mood_rating": response.mood_rating,
                    "motivation_rating": response.motivation_rating,

                    # Peso
                    "weight": response.weight,

                    # Aderenza programmi
                    "nutrition_program_adherence": response.nutrition_program_adherence,
                    "training_program_adherence": response.training_program_adherence,
                    "exercise_modifications": response.exercise_modifications,
                    "daily_steps": response.daily_steps,
                    "completed_training_weeks": response.completed_training_weeks,
                    "planned_training_days": response.planned_training_days,
                    "live_session_topics": response.live_session_topics,

                    # Valutazioni professionisti
                    "nutritionist_rating": response.nutritionist_rating,
                    "nutritionist_feedback": response.nutritionist_feedback,
                    "psychologist_rating": response.psychologist_rating,
                    "psychologist_feedback": response.psychologist_feedback,
                    "coach_rating": response.coach_rating,
                    "coach_feedback": response.coach_feedback,

                    # Progresso
                    "progress_rating": response.progress_rating,
                    "referral": response.referral,
                    "extra_comments": response.extra_comments,
                }
            })

        # Altrimenti mostra template
        return render_template(
            "client_checks/weekly_check_response_detail.html",
            response=response,
            cliente=cliente,
        )

    except Exception as e:
        current_app.logger.error(f"[WEEKLY_CHECK] Errore visualizzazione response: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": str(e)}), 500
        abort(404)


# ═══════════════════════════════════════════════════════════════════════════
#  DCA CHECK ROUTES (Permanent Links)
# ═══════════════════════════════════════════════════════════════════════════

@client_checks_bp.route("/dca/generate/<int:cliente_id>", methods=["POST"])
@login_required
def generate_dca_check_link(cliente_id: int):
    """
    Genera o recupera il link PERMANENTE per il check DCA di un cliente.

    LINK PERMANENTE: il cliente usa sempre lo stesso link per compilare più volte.
    Se esiste già un assignment attivo, ritorna quello esistente.

    Permessi: utenti con accesso al paziente (RBAC su cliente).
    """
    from corposostenibile.models import DCACheck
    import secrets

    try:
        cliente = Cliente.query.get_or_404(cliente_id)
        _abort_if_no_cliente_checks_access(cliente_id)

        # Cerca assignment ATTIVO esistente
        existing_check = (
            DCACheck.query
            .filter_by(cliente_id=cliente_id, is_active=True)
            .first()
        )

        if existing_check:
            # Assignment già esistente - riutilizza lo stesso link!
            token = existing_check.token
            # URL React frontend
            # Use React frontend port in development
            base_url = _frontend_base_url()
            check_url = f"{base_url}/check/dca/{token}"

            current_app.logger.info(
                f"[DCA_CHECK] Link PERMANENTE già esistente per {cliente.nome_cognome}: {check_url} "
                f"(compilazioni: {existing_check.response_count})"
            )

            flash(f"Link DCA permanente già attivo per {cliente.nome_cognome}! Compilazioni ricevute: {existing_check.response_count}", "info")

            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    "success": True,
                    "url": check_url,
                    "token": token,
                    "check_id": existing_check.id,
                    "is_new": False,
                    "response_count": existing_check.response_count
                })

            return redirect(url_for("customers.detail_view", cliente_id=cliente_id))

        # Nessun assignment attivo - crea nuovo assignment PERMANENTE
        token = secrets.token_urlsafe(32)

        for attempt in range(2):
            try:
                dca_check = DCACheck(
                    cliente_id=cliente_id,
                    token=token,
                    is_active=True,
                    assigned_by_id=current_user.id,
                    assigned_at=datetime.utcnow(),
                )
                db.session.add(dca_check)
                db.session.commit()
                break
            except Exception as seq_err:
                db.session.rollback()
                if attempt == 0 and "unique" in str(seq_err).lower():
                    _fix_sequence("dca_checks")
                    continue
                raise

        # URL React frontend
        # Use React frontend port in development
        base_url = _frontend_base_url()
        check_url = f"{base_url}/check/dca/{token}"

        current_app.logger.info(f"[DCA_CHECK] Nuovo link PERMANENTE per {cliente.nome_cognome}: {check_url}")

        flash(f"Link permanente check DCA generato per {cliente.nome_cognome}!", "success")

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": True,
                "url": check_url,
                "token": token,
                "check_id": dca_check.id,
                "is_new": True,
                "response_count": 0
            })

        return redirect(url_for("customers.detail_view", cliente_id=cliente_id))

    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[DCA_CHECK] Errore generazione link: {e}", exc_info=True)
        flash("Errore nella generazione del link DCA", "error")

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": str(e)}), 500

        return redirect(url_for("customers.detail_view", cliente_id=cliente_id))


@client_checks_bp.route("/dca/<token>", methods=["GET", "POST"])
@csrf.exempt
def dca_check_public(token: str):
    """
    Route pubblica per compilazione Check DCA tramite token PERMANENTE.

    LINK PERMANENTE: il cliente può compilare più volte usando lo stesso link.
    Ogni compilazione crea un nuovo record DCACheckResponse.
    """
    from corposostenibile.models import DCACheck, DCACheckResponse
    from .forms import DCACheckForm

    current_app.logger.info(f"[DCA_CHECK] Richiesta ricevuta per token: {token}")

    try:
        # Trova l'assignment PERMANENTE tramite token
        dca_check = (
            DCACheck.query
            .options(joinedload(DCACheck.cliente))
            .filter_by(token=token, is_active=True)
            .first()
        )

        if not dca_check:
            current_app.logger.warning(f"[DCA_CHECK] Token non valido o assignment disattivato: {token}")
            abort(404, "Link non valido o disattivato.")

        form = DCACheckForm()

        if request.method == "POST" and form.validate_on_submit():
            try:
                current_app.logger.info(
                    f"[DCA_CHECK] Inizio salvataggio compilazione per cliente_id={dca_check.cliente_id} "
                    f"(compilazione #{dca_check.response_count + 1})"
                )

                # ─── CREA NUOVA RISPOSTA ────────────────────────────────────
                response = DCACheckResponse(
                    dca_check_id=dca_check.id,
                    submit_date=datetime.utcnow(),
                    ip_address=get_client_ip(),
                    user_agent=get_user_agent(),
                )

                # ─── SALVA TUTTI I CAMPI NELLA RESPONSE ────────────────────
                # Benessere emotivo (1-5)
                response.mood_balance_rating = form.mood_balance_rating.data
                response.food_plan_serenity = form.food_plan_serenity.data
                response.food_weight_worry = form.food_weight_worry.data
                response.emotional_eating = form.emotional_eating.data
                response.body_comfort = form.body_comfort.data
                response.body_respect = form.body_respect.data

                # Allenamento (1-5)
                response.exercise_wellness = form.exercise_wellness.data
                response.exercise_guilt = form.exercise_guilt.data

                # Riposo e relazioni (1-5)
                response.sleep_satisfaction = form.sleep_satisfaction.data
                response.relationship_time = form.relationship_time.data
                response.personal_time = form.personal_time.data

                # Interferenze e gestione (1-5)
                response.life_interference = form.life_interference.data
                response.unexpected_management = form.unexpected_management.data
                response.self_compassion = form.self_compassion.data
                response.inner_dialogue = form.inner_dialogue.data

                # Sostenibilità e motivazione (1-5)
                response.long_term_sustainability = form.long_term_sustainability.data
                response.values_alignment = form.values_alignment.data
                response.motivation_level = form.motivation_level.data

                # Organizzazione pasti (1-5)
                response.meal_organization = form.meal_organization.data
                response.meal_stress = form.meal_stress.data
                response.shopping_awareness = form.shopping_awareness.data
                response.shopping_impact = form.shopping_impact.data
                response.meal_clarity = form.meal_clarity.data

                # Parametri fisici (1-10)
                response.digestion_rating = form.digestion_rating.data
                response.energy_rating = form.energy_rating.data
                response.strength_rating = form.strength_rating.data
                response.hunger_rating = form.hunger_rating.data
                response.sleep_rating = form.sleep_rating.data
                response.mood_rating = form.mood_rating.data
                response.motivation_rating = form.motivation_rating.data

                # Referral e commenti
                response.referral = form.referral.data
                response.extra_comments = form.extra_comments.data

                db.session.add(response)
                db.session.commit()

                current_app.logger.info(
                    f"[DCA_CHECK] Response salvata con successo: "
                    f"response_id={response.id}, check_id={dca_check.id}, "
                    f"totale_compilazioni={dca_check.response_count}"
                )

                # Invia notifiche ai professionisti associati
                try:
                    NotificationService.send_check_notification_to_professionals(
                        cliente=dca_check.cliente,
                        check_type='dca',
                        check_id=response.id
                    )
                except Exception as e:
                    current_app.logger.error(f"[DCA_CHECK] Errore invio notifiche: {e}")
                    # Non bloccare il flusso se l'invio email fallisce

                flash("Grazie! Il tuo check è stato salvato con successo.", "success")
                return redirect(url_for("client_checks.dca_check_success", token=token))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"[DCA_CHECK] Errore nel salvataggio: {e}", exc_info=True)
                flash("Errore nel salvataggio. Riprova più tardi.", "error")

        # Mostra il form con info sulle compilazioni precedenti
        previous_responses_count = dca_check.response_count
        last_response_date = dca_check.last_response_date

        return render_template(
            "client_checks/dca_check_form.html",
            form=form,
            cliente=dca_check.cliente,
            token=token,
            previous_responses_count=previous_responses_count,
            last_response_date=last_response_date,
        )

    except Exception as e:
        current_app.logger.error(f"[DCA_CHECK] Errore form pubblico: {e}", exc_info=True)
        abort(404)


@client_checks_bp.route("/dca/<token>/success")
@csrf.exempt
def dca_check_success(token: str):
    """Pagina di conferma dopo compilazione DCA check."""
    from corposostenibile.models import DCACheck

    try:
        dca_check = (
            DCACheck.query
            .options(joinedload(DCACheck.cliente))
            .filter_by(token=token, is_active=True)
            .first_or_404()
        )

        return render_template(
            "client_checks/dca_check_success.html",
            cliente=dca_check.cliente,
        )
    except Exception as e:
        current_app.logger.error(f"[DCA_CHECK] Errore pagina successo: {e}")
        abort(404)


@client_checks_bp.route("/dca/<int:check_id>/deactivate", methods=["POST"])
@login_required
def deactivate_dca_check(check_id: int):
    """
    Disattiva un link permanente di check DCA.
    """
    from corposostenibile.models import DCACheck

    try:
        dca_check = DCACheck.query.get_or_404(check_id)

        _abort_if_no_cliente_checks_access(dca_check.cliente_id)

        # Disattiva il check
        dca_check.is_active = False
        dca_check.deactivated_at = datetime.utcnow()
        dca_check.deactivated_by_id = current_user.id

        db.session.commit()

        current_app.logger.info(
            f"[DCA_CHECK] Link disattivato: check_id={check_id}, "
            f"by={current_user.nome_cognome}, compilazioni={dca_check.response_count}"
        )

        return jsonify({
            "success": True,
            "message": "Link DCA disattivato con successo",
            "response_count": dca_check.response_count
        })

    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[DCA_CHECK] Errore disattivazione: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@client_checks_bp.route("/dca/response/<int:response_id>")
@login_required
def dca_check_response_view(response_id: int):
    """
    Visualizza il dettaglio di una singola compilazione DCA (DCACheckResponse).
    """
    from corposostenibile.models import DCACheckResponse

    try:
        response = (
            DCACheckResponse.query
            .options(joinedload(DCACheckResponse.assignment))
            .get_or_404(response_id)
        )

        # Verifica permessi
        cliente = response.assignment.cliente
        if not current_user.is_admin and current_user.id != 95 and current_user not in [
            cliente.nutrizionista_user,
            cliente.coach_user,
            cliente.psicologo_user
        ]:
            abort(403)

        # Ritorna JSON se richiesto via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": True,
                "response": {
                    "id": response.id,
                    "submit_date": response.submit_date.strftime('%d/%m/%Y %H:%M'),
                    "completion_percentage": response.completion_percentage,

                    # Benessere emotivo
                    "mood_balance_rating": response.mood_balance_rating,
                    "food_plan_serenity": response.food_plan_serenity,
                    "food_weight_worry": response.food_weight_worry,
                    "emotional_eating": response.emotional_eating,
                    "body_comfort": response.body_comfort,
                    "body_respect": response.body_respect,

                    # Allenamento
                    "exercise_wellness": response.exercise_wellness,
                    "exercise_guilt": response.exercise_guilt,

                    # Riposo e relazioni
                    "sleep_satisfaction": response.sleep_satisfaction,
                    "relationship_time": response.relationship_time,
                    "personal_time": response.personal_time,

                    # Interferenze
                    "life_interference": response.life_interference,
                    "unexpected_management": response.unexpected_management,
                    "self_compassion": response.self_compassion,
                    "inner_dialogue": response.inner_dialogue,

                    # Sostenibilità
                    "long_term_sustainability": response.long_term_sustainability,
                    "values_alignment": response.values_alignment,
                    "motivation_level": response.motivation_level,

                    # Organizzazione pasti
                    "meal_organization": response.meal_organization,
                    "meal_stress": response.meal_stress,
                    "shopping_awareness": response.shopping_awareness,
                    "shopping_impact": response.shopping_impact,
                    "meal_clarity": response.meal_clarity,

                    # Parametri fisici
                    "digestion_rating": response.digestion_rating,
                    "energy_rating": response.energy_rating,
                    "strength_rating": response.strength_rating,
                    "hunger_rating": response.hunger_rating,
                    "sleep_rating": response.sleep_rating,
                    "mood_rating": response.mood_rating,
                    "motivation_rating": response.motivation_rating,

                    # Referral e commenti
                    "referral": response.referral,
                    "extra_comments": response.extra_comments,
                }
            })

        # Altrimenti mostra template
        return render_template(
            "client_checks/dca_check_response_detail.html",
            response=response,
            cliente=cliente,
        )

    except Exception as e:
        current_app.logger.error(f"[DCA_CHECK] Errore visualizzazione response: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": str(e)}), 500
        abort(404)


@client_checks_bp.route("/weekly/list/<int:cliente_id>")
@login_required
def weekly_checks_list(cliente_id: int):
    """
    Lista di tutti i check settimanali di un cliente (per visualizzazione nel dettaglio cliente).
    """
    from corposostenibile.models import WeeklyCheck

    try:
        cliente = Cliente.query.get_or_404(cliente_id)

        # Recupera tutti i check del cliente, ordinati per data (più recenti prima)
        checks = (
            WeeklyCheck.query
            .filter_by(cliente_id=cliente_id)
            .order_by(desc(WeeklyCheck.submit_date))
            .all()
        )

        # Se richiesta AJAX, ritorna JSON
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": True,
                "checks": [
                    {
                        "id": check.id,
                        "submit_date": check.submit_date.strftime('%d/%m/%Y %H:%M') if check.submit_date else None,
                        "is_completed": check.is_completed,
                        "completion_percentage": check.completion_percentage,
                        "weight": check.weight,
                        "progress_rating": check.progress_rating,
                    }
                    for check in checks
                ]
            })

        # Altrimenti template HTML
        return render_template(
            "client_checks/weekly_checks_list.html",
            cliente=cliente,
            checks=checks,
        )

    except Exception as e:
        current_app.logger.error(f"[WEEKLY_CHECK] Errore lista check: {e}")
        flash("Errore nel caricamento dei check", "error")

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": str(e)}), 500

        return redirect(url_for("customers.detail_view", cliente_id=cliente_id))


@client_checks_bp.route("/weekly/view/<int:check_id>")
@login_required
def weekly_check_view(check_id: int):
    """
    Visualizza dettaglio di un check settimanale completato.
    """
    from corposostenibile.models import WeeklyCheck

    try:
        weekly_check = (
            WeeklyCheck.query
            .options(joinedload(WeeklyCheck.cliente))
            .get_or_404(check_id)
        )

        # Se richiesta AJAX, ritorna JSON
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": True,
                "check": {
                    "id": weekly_check.id,
                    "cliente_nome": weekly_check.cliente.nome_cognome if weekly_check.cliente else None,
                    "submit_date": weekly_check.submit_date.strftime('%d/%m/%Y %H:%M') if weekly_check.submit_date else None,
                    "is_completed": weekly_check.is_completed,
                    "completion_percentage": weekly_check.completion_percentage,
                    # Foto (convertiti da path filesystem a URL web)
                    "photo_front": _photo_path_to_url(weekly_check.photo_front),
                    "photo_side": _photo_path_to_url(weekly_check.photo_side),
                    "photo_back": _photo_path_to_url(weekly_check.photo_back),
                    # Riflessioni
                    "what_worked": weekly_check.what_worked,
                    "what_didnt_work": weekly_check.what_didnt_work,
                    "what_learned": weekly_check.what_learned,
                    "what_focus_next": weekly_check.what_focus_next,
                    "injuries_notes": weekly_check.injuries_notes,
                    # Rating benessere
                    "digestion_rating": weekly_check.digestion_rating,
                    "energy_rating": weekly_check.energy_rating,
                    "strength_rating": weekly_check.strength_rating,
                    "hunger_rating": weekly_check.hunger_rating,
                    "sleep_rating": weekly_check.sleep_rating,
                    "mood_rating": weekly_check.mood_rating,
                    "motivation_rating": weekly_check.motivation_rating,
                    # Peso
                    "weight": weekly_check.weight,
                    # Aderenza
                    "nutrition_program_adherence": weekly_check.nutrition_program_adherence,
                    "training_program_adherence": weekly_check.training_program_adherence,
                    "exercise_modifications": weekly_check.exercise_modifications,
                    "daily_steps": weekly_check.daily_steps,
                    "completed_training_weeks": weekly_check.completed_training_weeks,
                    "planned_training_days": weekly_check.planned_training_days,
                    "live_session_topics": weekly_check.live_session_topics,
                    # Rating professionisti
                    "nutritionist_rating": weekly_check.nutritionist_rating,
                    "nutritionist_feedback": weekly_check.nutritionist_feedback,
                    "psychologist_rating": weekly_check.psychologist_rating,
                    "psychologist_feedback": weekly_check.psychologist_feedback,
                    "coach_rating": weekly_check.coach_rating,
                    "coach_feedback": weekly_check.coach_feedback,
                    # Progresso
                    "progress_rating": weekly_check.progress_rating,
                    "referral": weekly_check.referral,
                    "extra_comments": weekly_check.extra_comments,
                }
            })

        # Template HTML completo
        return render_template(
            "client_checks/weekly_check_detail.html",
            check=weekly_check,
        )

    except Exception as e:
        current_app.logger.error(f"[WEEKLY_CHECK] Errore visualizzazione check: {e}")
        flash("Errore nel caricamento del check", "error")

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": str(e)}), 500

        return redirect(url_for("client_checks.dashboard"))


# ═══════════════════════════════════════════════════════════════════════════
#  MINOR CHECK ROUTES (Check Minori) - Permanent Links
# ═══════════════════════════════════════════════════════════════════════════

@client_checks_bp.route("/minor/generate/<int:cliente_id>", methods=["POST"])
@login_required
def generate_minor_check_link(cliente_id: int):
    """
    Genera o recupera il link PERMANENTE per il Check Minori di un cliente.

    LINK PERMANENTE: il cliente usa sempre lo stesso link per compilare più volte.
    Se esiste già un assignment attivo, ritorna quello esistente.

    Permessi: utenti con accesso al paziente (RBAC su cliente).
    """
    import secrets

    try:
        cliente = Cliente.query.get_or_404(cliente_id)
        _abort_if_no_cliente_checks_access(cliente_id)

        # Cerca assignment ATTIVO esistente
        existing_check = (
            MinorCheck.query
            .filter_by(cliente_id=cliente_id, is_active=True)
            .first()
        )

        if existing_check:
            # Assignment già esistente - riutilizza lo stesso link!
            token = existing_check.token
            # URL React frontend
            # Use React frontend port in development
            base_url = _frontend_base_url()
            check_url = f"{base_url}/check/minor/{token}"

            current_app.logger.info(
                f"[MINOR_CHECK] Link PERMANENTE già esistente per {cliente.nome_cognome}: {check_url} "
                f"(compilazioni: {existing_check.response_count})"
            )

            flash(f"Link Check Minori permanente già attivo per {cliente.nome_cognome}! Compilazioni ricevute: {existing_check.response_count}", "info")

            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    "success": True,
                    "url": check_url,
                    "token": token,
                    "check_id": existing_check.id,
                    "is_new": False,
                    "response_count": existing_check.response_count
                })

            return redirect(url_for("customers.detail_view", cliente_id=cliente_id))

        # Nessun assignment attivo - crea nuovo assignment PERMANENTE
        token = secrets.token_urlsafe(32)

        for attempt in range(2):
            try:
                minor_check = MinorCheck(
                    cliente_id=cliente_id,
                    token=token,
                    is_active=True,
                    assigned_by_id=current_user.id,
                    assigned_at=datetime.utcnow(),
                )
                db.session.add(minor_check)
                db.session.commit()
                break
            except Exception as seq_err:
                db.session.rollback()
                if attempt == 0 and "unique" in str(seq_err).lower():
                    _fix_sequence("minor_checks")
                    continue
                raise

        # URL React frontend
        # Use React frontend port in development
        base_url = _frontend_base_url()
        check_url = f"{base_url}/check/minor/{token}"

        current_app.logger.info(f"[MINOR_CHECK] Nuovo link PERMANENTE per {cliente.nome_cognome}: {check_url}")

        flash(f"Link permanente Check Minori generato per {cliente.nome_cognome}!", "success")

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": True,
                "url": check_url,
                "token": token,
                "check_id": minor_check.id,
                "is_new": True,
                "response_count": 0
            })

        return redirect(url_for("customers.detail_view", cliente_id=cliente_id))

    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[MINOR_CHECK] Errore generazione link: {e}", exc_info=True)
        flash("Errore nella generazione del link Check Minori", "error")

        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": str(e)}), 500

        return redirect(url_for("customers.detail_view", cliente_id=cliente_id))


@client_checks_bp.route("/minor/<token>", methods=["GET", "POST"])
@csrf.exempt
def minor_check_public(token: str):
    """
    Route pubblica per compilazione Check Minori tramite token PERMANENTE.

    LINK PERMANENTE: il cliente può compilare più volte usando lo stesso link.
    Ogni compilazione crea un nuovo record MinorCheckResponse.
    """
    current_app.logger.info(f"[MINOR_CHECK] Richiesta ricevuta per token: {token}")

    try:
        # Trova l'assignment PERMANENTE tramite token
        minor_check = (
            MinorCheck.query
            .options(joinedload(MinorCheck.cliente))
            .filter_by(token=token, is_active=True)
            .first()
        )

        if not minor_check:
            current_app.logger.warning(f"[MINOR_CHECK] Token non valido o assignment disattivato: {token}")
            abort(404, "Link non valido o disattivato.")

        if request.method == "POST":
            try:
                current_app.logger.info(
                    f"[MINOR_CHECK] Inizio salvataggio compilazione per cliente_id={minor_check.cliente_id} "
                    f"(compilazione #{minor_check.response_count + 1})"
                )

                # ─── CREA NUOVA RISPOSTA ────────────────────────────────────
                response = MinorCheckResponse(
                    minor_check_id=minor_check.id,
                    submit_date=datetime.utcnow(),
                    ip_address=get_client_ip(),
                    user_agent=get_user_agent(),
                )

                # ─── ESTRAI DATI DAL FORM ────────────────────────────────────
                # Peso e altezza
                peso = request.form.get('peso_attuale', type=float)
                altezza = request.form.get('altezza', type=float)

                response.peso_attuale = peso
                response.altezza = altezza

                # Raccogli tutte le risposte in formato JSON
                responses_data = {}
                for i in range(1, 29):  # 28 domande
                    key = f'q{i}'
                    value = request.form.get(key)
                    if value is not None and value != '':
                        try:
                            responses_data[key] = int(value)
                        except ValueError:
                            responses_data[key] = value

                response.responses_data = responses_data

                # Calcola i punteggi delle sottoscale
                response.calculate_scores()

                db.session.add(response)
                db.session.commit()

                current_app.logger.info(
                    f"[MINOR_CHECK] Response salvata con successo: "
                    f"response_id={response.id}, check_id={minor_check.id}, "
                    f"totale_compilazioni={minor_check.response_count}, "
                    f"score_global={response.score_global}"
                )

                # Invia notifiche ai professionisti associati
                try:
                    NotificationService.send_check_notification_to_professionals(
                        cliente=minor_check.cliente,
                        check_type='minor',
                        check_id=response.id
                    )
                except Exception as e:
                    current_app.logger.error(f"[MINOR_CHECK] Errore invio notifiche: {e}")
                    # Non bloccare il flusso se l'invio email fallisce

                flash("Grazie! Il questionario è stato salvato con successo.", "success")
                return redirect(url_for("client_checks.minor_check_success", token=token))

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"[MINOR_CHECK] Errore nel salvataggio: {e}", exc_info=True)
                flash("Errore nel salvataggio. Riprova più tardi.", "error")

        # Mostra il form con info sulle compilazioni precedenti
        previous_responses_count = minor_check.response_count
        last_response_date = minor_check.last_response_date

        return render_template(
            "client_checks/public_minor_check.html",
            cliente=minor_check.cliente,
            token=token,
            previous_responses_count=previous_responses_count,
            last_response_date=last_response_date,
        )

    except Exception as e:
        current_app.logger.error(f"[MINOR_CHECK] Errore form pubblico: {e}", exc_info=True)
        abort(404)


@client_checks_bp.route("/minor/<token>/success")
@csrf.exempt
def minor_check_success(token: str):
    """Pagina di conferma dopo compilazione Check Minori."""
    try:
        minor_check = (
            MinorCheck.query
            .options(joinedload(MinorCheck.cliente))
            .filter_by(token=token)
            .first_or_404()
        )

        return render_template(
            "client_checks/minor_check_success.html",
            cliente=minor_check.cliente,
        )
    except Exception as e:
        current_app.logger.error(f"[MINOR_CHECK] Errore pagina successo: {e}")
        abort(404)


@client_checks_bp.route("/minor/<int:check_id>/deactivate", methods=["POST"])
@login_required
def deactivate_minor_check(check_id: int):
    """
    Disattiva un link permanente di Check Minori.
    """
    try:
        minor_check = MinorCheck.query.get_or_404(check_id)

        _abort_if_no_cliente_checks_access(minor_check.cliente_id)

        # Disattiva il check
        minor_check.is_active = False
        minor_check.deactivated_at = datetime.utcnow()
        minor_check.deactivated_by_id = current_user.id

        db.session.commit()

        current_app.logger.info(
            f"[MINOR_CHECK] Link disattivato: check_id={check_id}, "
            f"by={current_user.nome_cognome}, compilazioni={minor_check.response_count}"
        )

        return jsonify({
            "success": True,
            "message": "Link Check Minori disattivato con successo",
            "response_count": minor_check.response_count
        })

    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[MINOR_CHECK] Errore disattivazione: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@client_checks_bp.route("/minor/response/<int:response_id>")
@login_required
def minor_check_response_view(response_id: int):
    """
    Visualizza il dettaglio di una singola compilazione Check Minori (MinorCheckResponse).
    """
    try:
        response = (
            MinorCheckResponse.query
            .options(joinedload(MinorCheckResponse.assignment))
            .get_or_404(response_id)
        )

        # Verifica permessi
        cliente = response.assignment.cliente
        if not current_user.is_admin and current_user.id != 95 and current_user not in [
            cliente.nutrizionista_user,
            cliente.coach_user,
            cliente.psicologo_user
        ]:
            abort(403)

        # Ritorna JSON se richiesto via AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "success": True,
                "response": {
                    "id": response.id,
                    "submit_date": response.submit_date.strftime('%d/%m/%Y %H:%M') if response.submit_date else None,
                    "completion_percentage": response.completion_percentage,

                    # Peso e altezza
                    "peso_attuale": response.peso_attuale,
                    "altezza": response.altezza,

                    # Punteggi calcolati
                    "score_restraint": round(response.score_restraint, 2) if response.score_restraint else None,
                    "score_eating_concern": round(response.score_eating_concern, 2) if response.score_eating_concern else None,
                    "score_shape_concern": round(response.score_shape_concern, 2) if response.score_shape_concern else None,
                    "score_weight_concern": round(response.score_weight_concern, 2) if response.score_weight_concern else None,
                    "score_global": round(response.score_global, 2) if response.score_global else None,

                    # Risposte raw
                    "responses_data": response.responses_data,
                }
            })

        # Altrimenti mostra template
        return render_template(
            "client_checks/minor_check_response_detail.html",
            response=response,
            cliente=cliente,
        )

    except Exception as e:
        current_app.logger.error(f"[MINOR_CHECK] Errore visualizzazione response: {e}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": str(e)}), 500
        abort(404)


# ═══════════════════════════════════════════════════════════════════════════ #
#  WEEKLY CHECK LINK ASSIGNMENTS - Dashboard e gestione invii                 #
# ═══════════════════════════════════════════════════════════════════════════ #

@client_checks_bp.route("/link-assignments")
@login_required
def link_assignments_dashboard():
    """
    Dashboard per professionisti: mostra i clienti a cui devono inviare il link WeeklyCheck.
    Include filtro per stato invio e statistiche.
    """
    try:
        # Filtro per stato invio
        status_filter = request.args.get('status', 'pending')

        # Determina quale user_id usare per il filtro
        if current_user.is_admin or current_user.id == 95 or current_user.id == 2:
            professional_id = request.args.get('professional_id', type=int)
            # Se admin, user 95 o user 2 non specifica un professionista, mostra tutti
            filter_user_id = professional_id if professional_id else None

            # Lista professionisti per filtro
            professionals = User.query.join(
                WeeklyCheckLinkAssignment,
                User.id == WeeklyCheckLinkAssignment.assigned_to_user_id
            ).distinct(User.id).all()
        else:
            # Utente normale: vede solo i suoi assignment
            filter_user_id = current_user.id
            professional_id = None
            professionals = []

        # Base query per assignments
        assignments_query = WeeklyCheckLinkAssignment.query

        # Applica filtro user se specificato
        if filter_user_id:
            assignments_query = assignments_query.filter_by(assigned_to_user_id=filter_user_id)

        # Applica options per eager loading
        assignments_query = assignments_query.options(
            joinedload(WeeklyCheckLinkAssignment.cliente),
            joinedload(WeeklyCheckLinkAssignment.weekly_check)
        )

        # Se admin, user 95 o user 2 visualizza tutti o un singolo prof, carica anche assigned_to
        if current_user.is_admin or current_user.id == 95 or current_user.id == 2:
            assignments_query = assignments_query.options(
                joinedload(WeeklyCheckLinkAssignment.assigned_to)
            )

        # Applica filtro per stato
        if status_filter == 'pending':
            assignments_query = assignments_query.filter_by(sent_confirmed=False)
        elif status_filter == 'sent':
            assignments_query = assignments_query.filter_by(sent_confirmed=True)

        assignments = assignments_query.order_by(
            WeeklyCheckLinkAssignment.created_at.desc()
        ).all()

        # Statistiche basate sullo stesso filtro
        stats_query = WeeklyCheckLinkAssignment.query
        if filter_user_id:
            stats_query = stats_query.filter_by(assigned_to_user_id=filter_user_id)

        total_assignments = stats_query.count()
        sent_count = stats_query.filter_by(sent_confirmed=True).count()
        pending_count = total_assignments - sent_count

        return render_template(
            "client_checks/link_assignments_dashboard.html",
            assignments=assignments,
            total_assignments=total_assignments,
            sent_count=sent_count,
            pending_count=pending_count,
            status_filter=status_filter,
            professionals=professionals,
            professional_id=professional_id
        )

    except Exception as e:
        current_app.logger.error(f"[LINK_ASSIGNMENTS] Errore dashboard: {e}")
        flash("Errore nel caricamento della dashboard", "error")
        return redirect(url_for("welcome.index"))


@client_checks_bp.route("/link-assignments/<int:assignment_id>/confirm", methods=["POST"])
@login_required
def confirm_link_sent(assignment_id):
    """
    Conferma che il professionista ha inviato il link al cliente.
    """
    try:
        assignment = WeeklyCheckLinkAssignment.query.get_or_404(assignment_id)

        # Verifica che sia il professionista assegnato, un admin, user 95 o user 2
        if assignment.assigned_to_user_id != current_user.id and not current_user.is_admin and current_user.id != 95 and current_user.id != 2:
            flash("Non sei autorizzato a confermare questo invio", "error")
            return redirect(url_for("client_checks.link_assignments_dashboard"))

        # Conferma invio
        assignment.sent_confirmed = True
        assignment.sent_at = datetime.utcnow()

        # Note opzionali
        notes = request.form.get('notes', '').strip()
        if notes:
            assignment.notes = notes

        db.session.commit()

        flash(f"✅ Invio confermato per {assignment.cliente.nome_cognome}", "success")

        # Redirect con filtro stato
        status_filter = request.args.get('status', 'pending')
        return redirect(url_for("client_checks.link_assignments_dashboard", status=status_filter))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[LINK_ASSIGNMENTS] Errore conferma invio: {e}")
        flash("Errore nella conferma dell'invio", "error")
        return redirect(url_for("client_checks.link_assignments_dashboard"))


@client_checks_bp.route("/link-assignments/<int:assignment_id>/undo", methods=["POST"])
@login_required
def undo_link_sent(assignment_id):
    """
    Annulla la conferma di invio (solo per admin o in caso di errore immediato).
    """
    try:
        assignment = WeeklyCheckLinkAssignment.query.get_or_404(assignment_id)

        # Verifica che sia il professionista assegnato, un admin, user 95 o user 2
        if assignment.assigned_to_user_id != current_user.id and not current_user.is_admin and current_user.id != 95 and current_user.id != 2:
            flash("Non sei autorizzato a modificare questo assignment", "error")
            return redirect(url_for("client_checks.link_assignments_dashboard"))

        # Annulla conferma
        assignment.sent_confirmed = False
        assignment.sent_at = None

        db.session.commit()

        flash(f"Conferma invio annullata per {assignment.cliente.nome_cognome}", "info")

        # Redirect con filtro stato
        status_filter = request.args.get('status', 'sent')
        return redirect(url_for("client_checks.link_assignments_dashboard", status=status_filter))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[LINK_ASSIGNMENTS] Errore annullamento conferma: {e}")
        flash("Errore nell'annullamento della conferma", "error")
        return redirect(url_for("client_checks.link_assignments_dashboard"))


# --------------------------------------------------------------------------- #
#  API JSON per React Frontend                                                 #
# --------------------------------------------------------------------------- #

@api_bp.route("/cliente/<int:cliente_id>/checks")
@login_required
def api_cliente_checks(cliente_id: int):
    """
    API JSON: Ritorna tutti i check (Weekly, DCA, Minor) e relative risposte per un cliente.
    """
    from corposostenibile.models import (
        WeeklyCheck, WeeklyCheckResponse,
        DCACheck, DCACheckResponse,
        MinorCheck, MinorCheckResponse,
        ClientCheckReadConfirmation,
        TypeFormResponse,
    )

    try:
        cliente = Cliente.query.get_or_404(cliente_id)
        _abort_if_no_cliente_checks_access(cliente_id)

        base_url = _frontend_base_url()

        result = {
            "success": True,
            "cliente_id": cliente_id,
            "cliente_nome": cliente.nome_cognome,
            "checks": {
                "weekly": None,
                "dca": None,
                "minor": None
            },
            "responses": []
        }

        # Weekly Check
        weekly_check = WeeklyCheck.query.filter_by(cliente_id=cliente_id, is_active=True).first()
        if weekly_check:
            result["checks"]["weekly"] = {
                "id": weekly_check.id,
                "token": weekly_check.token,
                "url": f"{base_url}/check/weekly/{weekly_check.token}",
                "is_active": weekly_check.is_active,
                "response_count": weekly_check.response_count,
                "assigned_at": weekly_check.assigned_at.strftime('%d/%m/%Y %H:%M') if weekly_check.assigned_at else None
            }
            # Get responses
            for resp in weekly_check.responses.order_by(WeeklyCheckResponse.submit_date.desc()).all():
                # Check if read by current user
                read_confirmation = ClientCheckReadConfirmation.query.filter_by(
                    response_type='weekly_check',
                    response_id=resp.id,
                    user_id=current_user.id
                ).first()
                result["responses"].append({
                    "id": resp.id,
                    "type": "weekly",
                    "submit_date": resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                    "submit_date_iso": resp.submit_date.isoformat() if resp.submit_date else None,
                    "completion_percentage": resp.completion_percentage,
                    "weight": resp.weight,
                    "progress_rating": resp.progress_rating,
                    "nutritionist_rating": resp.nutritionist_rating,
                    "psychologist_rating": resp.psychologist_rating,
                    "coach_rating": resp.coach_rating,
                    "nutritionist_user_id": resp.nutritionist_user_id,
                    "nutritionist_name": (resp.nutritionist_user.full_name or resp.nutritionist_user.email) if resp.nutritionist_user else None,
                    "psychologist_user_id": resp.psychologist_user_id,
                    "psychologist_name": (resp.psychologist_user.full_name or resp.psychologist_user.email) if resp.psychologist_user else None,
                    "coach_user_id": resp.coach_user_id,
                    "coach_name": (resp.coach_user.full_name or resp.coach_user.email) if resp.coach_user else None,
                    "digestion_rating": resp.digestion_rating,
                    "energy_rating": resp.energy_rating,
                    "strength_rating": resp.strength_rating,
                    "hunger_rating": resp.hunger_rating,
                    "sleep_rating": resp.sleep_rating,
                    "mood_rating": resp.mood_rating,
                    "motivation_rating": resp.motivation_rating,
                    "photo_front": _photo_path_to_url(resp.photo_front),
                    "photo_side": _photo_path_to_url(resp.photo_side),
                    "photo_back": _photo_path_to_url(resp.photo_back),
                    "is_read": read_confirmation is not None,
                    "read_at": read_confirmation.read_at.strftime('%d/%m/%Y %H:%M') if read_confirmation else None
                })

        # DCA Check
        dca_check = DCACheck.query.filter_by(cliente_id=cliente_id, is_active=True).first()
        if dca_check:
            result["checks"]["dca"] = {
                "id": dca_check.id,
                "token": dca_check.token,
                "url": f"{base_url}/check/dca/{dca_check.token}",
                "is_active": dca_check.is_active,
                "response_count": dca_check.response_count,
                "assigned_at": dca_check.assigned_at.strftime('%d/%m/%Y %H:%M') if dca_check.assigned_at else None
            }
            for resp in dca_check.responses.order_by(DCACheckResponse.submit_date.desc()).all():
                read_confirmation = ClientCheckReadConfirmation.query.filter_by(
                    response_type='dca_check',
                    response_id=resp.id,
                    user_id=current_user.id
                ).first()
                result["responses"].append({
                    "id": resp.id,
                    "type": "dca",
                    "submit_date": resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                    "submit_date_iso": resp.submit_date.isoformat() if resp.submit_date else None,
                    "completion_percentage": resp.completion_percentage,
                    "mood_balance_rating": resp.mood_balance_rating,
                    "food_weight_worry": resp.food_weight_worry,
                    "food_plan_serenity": resp.food_plan_serenity,
                    "emotional_eating": resp.emotional_eating,
                    "body_comfort": resp.body_comfort,
                    "sleep_satisfaction": resp.sleep_satisfaction,
                    "motivation_level": resp.motivation_level,
                    "self_compassion": resp.self_compassion,
                    "long_term_sustainability": resp.long_term_sustainability,
                    "digestion_rating": resp.digestion_rating,
                    "energy_rating": resp.energy_rating,
                    "sleep_rating": resp.sleep_rating,
                    "mood_rating": resp.mood_rating,
                    "motivation_rating": resp.motivation_rating,
                    "is_read": read_confirmation is not None,
                    "read_at": read_confirmation.read_at.strftime('%d/%m/%Y %H:%M') if read_confirmation else None
                })

        # Minor Check
        minor_check = MinorCheck.query.filter_by(cliente_id=cliente_id, is_active=True).first()
        if minor_check:
            result["checks"]["minor"] = {
                "id": minor_check.id,
                "token": minor_check.token,
                "url": f"{base_url}/check/minor/{minor_check.token}",
                "is_active": minor_check.is_active,
                "response_count": minor_check.response_count,
                "assigned_at": minor_check.assigned_at.strftime('%d/%m/%Y %H:%M') if minor_check.assigned_at else None
            }
            for resp in minor_check.responses.order_by(MinorCheckResponse.submit_date.desc()).all():
                result["responses"].append({
                    "id": resp.id,
                    "type": "minor",
                    "submit_date": resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                    "submit_date_iso": resp.submit_date.isoformat() if resp.submit_date else None,
                    "peso": resp.peso_attuale,
                    "score_global": resp.score_global,
                    "is_read": True  # Minor checks don't track read status
                })

        # TypeForm Responses (old check system) — show as "weekly" sub-type "typeform"
        typeform_responses = (
            TypeFormResponse.query
            .filter_by(cliente_id=cliente_id)
            .order_by(TypeFormResponse.submit_date.desc())
            .all()
        )
        for resp in typeform_responses:
            result["responses"].append({
                "id": resp.id,
                "type": "weekly",
                "source": "typeform",
                "submit_date": resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                "submit_date_iso": resp.submit_date.isoformat() if resp.submit_date else None,
                "completion_percentage": None,
                "weight": resp.weight,
                "progress_rating": resp.progress_rating,
                "nutritionist_rating": resp.nutritionist_rating,
                "psychologist_rating": resp.psychologist_rating,
                "coach_rating": resp.coach_rating,
                "nutritionist_user_id": resp.nutritionist_user_id,
                "nutritionist_name": (resp.nutritionist_user.full_name or resp.nutritionist_user.email) if resp.nutritionist_user else None,
                "psychologist_user_id": resp.psychologist_user_id,
                "psychologist_name": (resp.psychologist_user.full_name or resp.psychologist_user.email) if resp.psychologist_user else None,
                "coach_user_id": resp.coach_user_id,
                "coach_name": (resp.coach_user.full_name or resp.coach_user.email) if resp.coach_user else None,
                "digestion_rating": resp.digestion_rating,
                "energy_rating": resp.energy_rating,
                "strength_rating": resp.strength_rating,
                "hunger_rating": resp.hunger_rating,
                "sleep_rating": resp.sleep_rating,
                "mood_rating": resp.mood_rating,
                "motivation_rating": resp.motivation_rating,
                "photo_front": resp.photo_front or None,
                "photo_side": resp.photo_side or None,
                "photo_back": resp.photo_back or None,
                "is_read": True,
                "read_at": None,
            })

        # Sort all responses by date
        result["responses"].sort(key=lambda x: x["submit_date_iso"] or "", reverse=True)

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"[API] Errore get cliente checks: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@csrf.exempt
@api_bp.route("/generate/<check_type>/<int:cliente_id>", methods=["POST"])
@login_required
def api_generate_check_link(check_type: str, cliente_id: int):
    """
    API JSON: Genera o recupera link permanente per check (weekly, dca, minor).
    """
    from corposostenibile.models import WeeklyCheck, DCACheck, MinorCheck
    import secrets

    if check_type not in ['weekly', 'dca', 'minor']:
        return jsonify({"success": False, "error": "Tipo check non valido"}), 400

    try:
        cliente = Cliente.query.get_or_404(cliente_id)
        if not _can_access_cliente_checks(cliente_id):
            return jsonify({"success": False, "error": "Non autorizzato"}), 403

        # Select correct model
        if check_type == 'weekly':
            Model = WeeklyCheck
        elif check_type == 'dca':
            Model = DCACheck
        else:  # minor
            Model = MinorCheck

        base_url = _frontend_base_url()

        # Check for existing active assignment
        existing = Model.query.filter_by(cliente_id=cliente_id, is_active=True).first()

        if existing:
            check_url = f"{base_url}/check/{check_type}/{existing.token}"
            return jsonify({
                "success": True,
                "is_new": False,
                "check_id": existing.id,
                "token": existing.token,
                "url": check_url,
                "response_count": existing.response_count
            })

        # Create new assignment (with sequence auto-fix on UniqueViolation)
        token = secrets.token_urlsafe(32)
        for attempt in range(2):
            try:
                new_check = Model(
                    cliente_id=cliente_id,
                    token=token,
                    is_active=True,
                    assigned_by_id=current_user.id,
                    assigned_at=datetime.utcnow()
                )
                db.session.add(new_check)
                db.session.commit()
                break
            except Exception as seq_err:
                db.session.rollback()
                if attempt == 0 and "UniqueViolation" in str(type(seq_err).__mro__) or "unique" in str(seq_err).lower():
                    _fix_sequence(Model.__tablename__)
                    continue
                raise

        check_url = f"{base_url}/check/{check_type}/{token}"

        return jsonify({
            "success": True,
            "is_new": True,
            "check_id": new_check.id,
            "token": token,
            "url": check_url,
            "response_count": 0
        })

    except HTTPException:
        raise
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[API] Errore generazione link {check_type}: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/da-leggere")
@login_required
def api_da_leggere():
    """
    API JSON: Ritorna tutti i check non letti per il professionista corrente.
    OTTIMIZZATO: usa subquery per i clienti, evita caricamento preventivo.
    """
    from corposostenibile.models import (
        ClientCheckReadConfirmation,
        WeeklyCheck, WeeklyCheckResponse,
        DCACheck, DCACheckResponse,
        Team
    )

    try:
        # RBAC Logic for Client Access
        my_clienti_query = None
        
        # 1. Admin: vede tutto (my_clienti_query resta None)
        if current_user.is_admin or current_user.role == 'admin':
            pass
            
        # 2. Team Leader
        elif current_user.teams_led:
            managed_team_ids = [t.id for t in current_user.teams_led]
            team_members_query = (
                db.session.query(User.id)
                .join(User.teams)
                .filter(Team.id.in_(managed_team_ids))
            ).union(
                db.session.query(db.literal(current_user.id))  # Includi il TL stesso
            )
            my_clienti_query = (
                db.session.query(Cliente.cliente_id)
                .filter(
                    db.or_(
                        Cliente.nutrizionista_id.in_(team_members_query),
                        Cliente.coach_id.in_(team_members_query),
                        Cliente.psicologa_id.in_(team_members_query),
                        Cliente.consulente_alimentare_id.in_(team_members_query),
                    )
                )
            )
            
        # 3. Professional (default)
        else:
            my_clienti_query = (
                db.session.query(Cliente.cliente_id)
                .filter(
                    db.or_(
                        Cliente.nutrizionista_id == current_user.id,
                        Cliente.coach_id == current_user.id,
                        Cliente.psicologa_id == current_user.id,
                        Cliente.consulente_alimentare_id == current_user.id,
                        Cliente.nutrizionisti_multipli.any(User.id == current_user.id),
                        Cliente.coaches_multipli.any(User.id == current_user.id),
                        Cliente.psicologi_multipli.any(User.id == current_user.id),
                        Cliente.consulenti_multipli.any(User.id == current_user.id),
                    )
                )
            )

        unread_checks = []

        # Weekly checks not read - with eager loading
        # Weekly checks query building
        weekly_query = (
            WeeklyCheckResponse.query
            .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
            .join(Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id)
            .outerjoin(
                ClientCheckReadConfirmation,
                and_(
                    ClientCheckReadConfirmation.response_type == 'weekly_check',
                    ClientCheckReadConfirmation.response_id == WeeklyCheckResponse.id,
                    ClientCheckReadConfirmation.user_id == current_user.id
                )
            )
            .filter(ClientCheckReadConfirmation.id.is_(None))
        )
        
        if my_clienti_query is not None:
             weekly_query = weekly_query.filter(Cliente.cliente_id.in_(my_clienti_query))
             
        weekly_responses = (
            weekly_query
            .options(
                joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente)
            )
            .order_by(WeeklyCheckResponse.submit_date.desc())
            .limit(100)  # Limit for performance
            .all()
        )

        for resp in weekly_responses:
            cliente = resp.assignment.cliente if resp.assignment else None
            unread_checks.append({
                "id": resp.id,
                "type": "weekly",
                "response_type": "weekly_check",
                "cliente_id": cliente.cliente_id if cliente else None,
                "cliente_nome": cliente.nome_cognome if cliente else "Sconosciuto",
                "submit_date": resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                "submit_date_iso": resp.submit_date.isoformat() if resp.submit_date else None,
                "progress_rating": resp.progress_rating,
                "nutritionist_rating": resp.nutritionist_rating,
                "psychologist_rating": resp.psychologist_rating,
                "coach_rating": resp.coach_rating
            })

        # DCA checks not read - with eager loading
        # DCA checks query building
        dca_query = (
            DCACheckResponse.query
            .join(DCACheck, DCACheckResponse.dca_check_id == DCACheck.id)
            .join(Cliente, DCACheck.cliente_id == Cliente.cliente_id)
            .outerjoin(
                ClientCheckReadConfirmation,
                and_(
                    ClientCheckReadConfirmation.response_type == 'dca_check',
                    ClientCheckReadConfirmation.response_id == DCACheckResponse.id,
                    ClientCheckReadConfirmation.user_id == current_user.id
                )
            )
            .filter(ClientCheckReadConfirmation.id.is_(None))
        )

        if my_clienti_query is not None:
             dca_query = dca_query.filter(Cliente.cliente_id.in_(my_clienti_query))

        dca_responses = (
            dca_query
            .options(
                joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente)
            )
            .order_by(DCACheckResponse.submit_date.desc())
            .limit(100)  # Limit for performance
            .all()
        )

        for resp in dca_responses:
            cliente = resp.assignment.cliente if resp.assignment else None
            unread_checks.append({
                "id": resp.id,
                "type": "dca",
                "response_type": "dca_check",
                "cliente_id": cliente.cliente_id if cliente else None,
                "cliente_nome": cliente.nome_cognome if cliente else "Sconosciuto",
                "submit_date": resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                "submit_date_iso": resp.submit_date.isoformat() if resp.submit_date else None
            })

        # Sort by date
        unread_checks.sort(key=lambda x: x["submit_date_iso"] or "", reverse=True)

        return jsonify({
            "success": True,
            "unread_checks": unread_checks,
            "total": len(unread_checks)
        })

    except Exception as e:
        current_app.logger.error(f"[API] Errore get da-leggere: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@csrf.exempt
@api_bp.route("/conferma-lettura/<string:response_type>/<int:response_id>", methods=["POST"])
@login_required
def api_conferma_lettura(response_type: str, response_id: int):
    """
    API JSON: Conferma lettura di un check.
    """
    from corposostenibile.models import ClientCheckReadConfirmation

    if response_type not in ['weekly_check', 'dca_check']:
        return jsonify({"success": False, "error": "Tipo check non valido"}), 400

    try:
        # Check if already confirmed
        existing = ClientCheckReadConfirmation.query.filter_by(
            response_type=response_type,
            response_id=response_id,
            user_id=current_user.id
        ).first()

        if existing:
            return jsonify({
                "success": True,
                "message": "Già confermato",
                "read_at": existing.read_at.strftime('%d/%m/%Y %H:%M')
            })

        # Create confirmation
        confirmation = ClientCheckReadConfirmation(
            response_type=response_type,
            response_id=response_id,
            user_id=current_user.id,
            read_at=datetime.utcnow()
        )
        db.session.add(confirmation)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Lettura confermata",
            "read_at": confirmation.read_at.strftime('%d/%m/%Y %H:%M')
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[API] Errore conferma lettura: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/response/<string:response_type>/<int:response_id>")
@login_required
def api_get_response_detail(response_type: str, response_id: int):
    """
    API JSON: Ritorna i dettagli completi di una risposta.
    """
    from corposostenibile.models import (
        WeeklyCheckResponse, DCACheckResponse, MinorCheckResponse,
        ClientCheckReadConfirmation, TypeFormResponse,
    )

    try:
        if response_type == 'weekly':
            resp = WeeklyCheckResponse.query.get_or_404(response_id)
            cliente = resp.assignment.cliente if resp.assignment else None
            if cliente and not _can_access_cliente_checks(cliente.cliente_id):
                abort(HTTPStatus.FORBIDDEN, description="Non autorizzato")

            # Check read status
            read_conf = ClientCheckReadConfirmation.query.filter_by(
                response_type='weekly_check',
                response_id=response_id,
                user_id=current_user.id
            ).first()

            data = {
                "id": resp.id,
                "type": "weekly",
                "cliente_id": cliente.cliente_id if cliente else None,
                "cliente_nome": cliente.nome_cognome if cliente else None,
                "submit_date": resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                "completion_percentage": resp.completion_percentage,
                "is_read": read_conf is not None,
                # Wellness ratings
                "digestion_rating": resp.digestion_rating,
                "energy_rating": resp.energy_rating,
                "strength_rating": resp.strength_rating,
                "hunger_rating": resp.hunger_rating,
                "sleep_rating": resp.sleep_rating,
                "mood_rating": resp.mood_rating,
                "motivation_rating": resp.motivation_rating,
                # Professional ratings
                "nutritionist_rating": resp.nutritionist_rating,
                "nutritionist_feedback": resp.nutritionist_feedback,
                "nutritionist_user_id": resp.nutritionist_user_id,
                "nutritionist_name": (resp.nutritionist_user.full_name or resp.nutritionist_user.email) if resp.nutritionist_user else None,
                "psychologist_rating": resp.psychologist_rating,
                "psychologist_feedback": resp.psychologist_feedback,
                "psychologist_user_id": resp.psychologist_user_id,
                "psychologist_name": (resp.psychologist_user.full_name or resp.psychologist_user.email) if resp.psychologist_user else None,
                "coach_rating": resp.coach_rating,
                "coach_feedback": resp.coach_feedback,
                "coach_user_id": resp.coach_user_id,
                "coach_name": (resp.coach_user.full_name or resp.coach_user.email) if resp.coach_user else None,
                # Progress
                "progress_rating": resp.progress_rating,
                "coordinator_rating": resp.coordinator_rating,
                "coordinator_notes": resp.coordinator_notes,
                # Physical
                "weight": resp.weight,
                # Text fields
                "what_worked": resp.what_worked,
                "what_didnt_work": resp.what_didnt_work,
                "what_learned": resp.what_learned,
                "what_focus_next": resp.what_focus_next,
                "injuries_notes": resp.injuries_notes,
                "nutrition_program_adherence": resp.nutrition_program_adherence,
                "training_program_adherence": resp.training_program_adherence,
                "exercise_modifications": resp.exercise_modifications,
                "daily_steps": resp.daily_steps,
                "completed_training_weeks": resp.completed_training_weeks,
                "planned_training_days": resp.planned_training_days,
                "live_session_topics": resp.live_session_topics,
                "extra_comments": resp.extra_comments,
                "referral": resp.referral,
                # Photos (convertiti da path filesystem a URL web)
                "photo_front": _photo_path_to_url(resp.photo_front),
                "photo_side": _photo_path_to_url(resp.photo_side),
                "photo_back": _photo_path_to_url(resp.photo_back),
            }

        elif response_type == 'typeform':
            resp = TypeFormResponse.query.get_or_404(response_id)
            if resp.cliente_id and not _can_access_cliente_checks(resp.cliente_id):
                abort(HTTPStatus.FORBIDDEN, description="Non autorizzato")

            data = {
                "id": resp.id,
                "type": "weekly",
                "source": "typeform",
                "cliente_id": resp.cliente_id,
                "cliente_nome": resp.cliente.nome_cognome if resp.cliente else f"{resp.first_name} {resp.last_name}",
                "submit_date": resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                "completion_percentage": None,
                "is_read": True,
                # Wellness ratings
                "digestion_rating": resp.digestion_rating,
                "energy_rating": resp.energy_rating,
                "strength_rating": resp.strength_rating,
                "hunger_rating": resp.hunger_rating,
                "sleep_rating": resp.sleep_rating,
                "mood_rating": resp.mood_rating,
                "motivation_rating": resp.motivation_rating,
                # Professional ratings
                "nutritionist_rating": resp.nutritionist_rating,
                "nutritionist_feedback": resp.nutritionist_feedback,
                "nutritionist_user_id": resp.nutritionist_user_id,
                "nutritionist_name": (resp.nutritionist_user.full_name or resp.nutritionist_user.email) if resp.nutritionist_user else None,
                "psychologist_rating": resp.psychologist_rating,
                "psychologist_feedback": resp.psychologist_feedback,
                "psychologist_user_id": resp.psychologist_user_id,
                "psychologist_name": (resp.psychologist_user.full_name or resp.psychologist_user.email) if resp.psychologist_user else None,
                "coach_rating": resp.coach_rating,
                "coach_feedback": resp.coach_feedback,
                "coach_user_id": resp.coach_user_id,
                "coach_name": (resp.coach_user.full_name or resp.coach_user.email) if resp.coach_user else None,
                # Progress
                "progress_rating": resp.progress_rating,
                "coordinator_rating": resp.coordinator_rating,
                "coordinator_notes": resp.coordinator_notes,
                # Physical
                "weight": resp.weight,
                # Text fields
                "what_worked": resp.what_worked,
                "what_didnt_work": resp.what_didnt_work,
                "what_learned": resp.what_learned,
                "what_focus_next": resp.what_focus_next,
                "injuries_notes": resp.injuries_notes,
                "nutrition_program_adherence": resp.nutrition_program_adherence,
                "training_program_adherence": resp.training_program_adherence,
                "exercise_modifications": resp.exercise_modifications,
                "daily_steps": resp.daily_steps,
                "completed_training_weeks": resp.completed_training_weeks,
                "planned_training_days": resp.planned_training_days,
                "live_session_topics": resp.live_session_topics,
                "extra_comments": resp.extra_comments,
                "referral": resp.referral,
                # Photos (TypeForm may store external URLs or local paths)
                "photo_front": _photo_path_to_url(resp.photo_front),
                "photo_side": _photo_path_to_url(resp.photo_side),
                "photo_back": _photo_path_to_url(resp.photo_back),
            }

        elif response_type == 'dca':
            resp = DCACheckResponse.query.get_or_404(response_id)
            cliente = resp.assignment.cliente if resp.assignment else None
            if cliente and not _can_access_cliente_checks(cliente.cliente_id):
                abort(HTTPStatus.FORBIDDEN, description="Non autorizzato")

            read_conf = ClientCheckReadConfirmation.query.filter_by(
                response_type='dca_check',
                response_id=response_id,
                user_id=current_user.id
            ).first()

            data = {
                "id": resp.id,
                "type": "dca",
                "cliente_id": cliente.cliente_id if cliente else None,
                "cliente_nome": cliente.nome_cognome if cliente else None,
                "submit_date": resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                "completion_percentage": resp.completion_percentage,
                "is_read": read_conf is not None,
                # Emotional wellbeing
                "mood_balance_rating": resp.mood_balance_rating,
                "food_plan_serenity": resp.food_plan_serenity,
                "food_weight_worry": resp.food_weight_worry,
                "emotional_eating": resp.emotional_eating,
                "body_comfort": resp.body_comfort,
                "body_respect": resp.body_respect,
                # Exercise
                "exercise_wellness": resp.exercise_wellness,
                "exercise_guilt": resp.exercise_guilt,
                # Rest & relationships
                "sleep_satisfaction": resp.sleep_satisfaction,
                "relationship_time": resp.relationship_time,
                "personal_time": resp.personal_time,
                # Interference & management
                "life_interference": resp.life_interference,
                "unexpected_management": resp.unexpected_management,
                "self_compassion": resp.self_compassion,
                "inner_dialogue": resp.inner_dialogue,
                # Sustainability
                "long_term_sustainability": resp.long_term_sustainability,
                "values_alignment": resp.values_alignment,
                "motivation_level": resp.motivation_level,
                # Meal organization
                "meal_organization": resp.meal_organization,
                "meal_stress": resp.meal_stress,
                "shopping_awareness": resp.shopping_awareness,
                "shopping_impact": resp.shopping_impact,
                "meal_clarity": resp.meal_clarity,
                # Physical parameters
                "digestion_rating": resp.digestion_rating,
                "energy_rating": resp.energy_rating,
                "strength_rating": resp.strength_rating,
                "hunger_rating": resp.hunger_rating,
                "sleep_rating": resp.sleep_rating,
                "mood_rating": resp.mood_rating,
                "motivation_rating": resp.motivation_rating,
                # Extra
                "referral": resp.referral,
                "extra_comments": resp.extra_comments,
            }

        elif response_type == 'minor':
            resp = MinorCheckResponse.query.get_or_404(response_id)
            cliente = resp.assignment.cliente if resp.assignment else None
            if cliente and not _can_access_cliente_checks(cliente.cliente_id):
                abort(HTTPStatus.FORBIDDEN, description="Non autorizzato")

            data = {
                "id": resp.id,
                "type": "minor",
                "cliente_id": cliente.cliente_id if cliente else None,
                "cliente_nome": cliente.nome_cognome if cliente else None,
                "submit_date": resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                "peso_attuale": resp.peso_attuale,
                "altezza": resp.altezza,
                "responses_data": resp.responses_data,
                "score_restraint": resp.score_restraint,
                "score_eating_concern": resp.score_eating_concern,
                "score_shape_concern": resp.score_shape_concern,
                "score_weight_concern": resp.score_weight_concern,
                "score_global": resp.score_global,
            }
        else:
            return jsonify({"success": False, "error": "Tipo non valido"}), 400

        return jsonify({"success": True, "response": data})

    except Exception as e:
        current_app.logger.error(f"[API] Errore get response detail: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/azienda/stats")
@login_required
def api_azienda_stats():
    """
    API JSON: Statistiche aziendali sui check (per Check Azienda).
    OTTIMIZZATO: paginazione server-side, eager loading, batch queries.
    Dati filtrati per ruolo (admin=all, TL=team clients, professionista=own).
    Supporta check_type: 'all', 'weekly', 'dca', 'minor' (default: 'all').
    """
    from corposostenibile.models import (
        ClientCheckReadConfirmation,
        WeeklyCheck, WeeklyCheckResponse,
        DCACheck, DCACheckResponse,
        MinorCheck, MinorCheckResponse,
        TypeFormResponse,
        Team
    )

    try:
        # Paginazione server-side & Filtri
        period = request.args.get('period', 'month')
        custom_start = request.args.get('start_date')
        custom_end = request.args.get('end_date')
        prof_type = request.args.get('prof_type')  # 'nutrizione', 'coach', 'psicologia'
        prof_id = request.args.get('prof_id', type=int)  # Specific professional ID
        check_type = request.args.get('check_type', 'all')  # 'all', 'weekly', 'dca', 'minor'
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)

        # Calculate date range
        now = datetime.utcnow()
        end_date = now

        if period == 'custom' and custom_start and custom_end:
            start_date = datetime.strptime(custom_start, '%Y-%m-%d')
            end_date = datetime.strptime(custom_end, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        elif period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        elif period == 'trimester':
            start_date = now - timedelta(days=90)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=30)

        # --- RBAC ---
        accessible_query = get_accessible_clients_query()

        # --- Helper: apply prof filters to a query that already has Cliente joined ---
        def _apply_prof_filters(q):
            if prof_type and prof_id:
                if prof_type == 'nutrizione':
                    q = q.filter(db.or_(Cliente.nutrizionista_id == prof_id, Cliente.nutrizionisti_multipli.any(User.id == prof_id)))
                elif prof_type == 'coach':
                    q = q.filter(db.or_(Cliente.coach_id == prof_id, Cliente.coaches_multipli.any(User.id == prof_id)))
                elif prof_type == 'psicologia':
                    q = q.filter(db.or_(Cliente.psicologa_id == prof_id, Cliente.psicologi_multipli.any(User.id == prof_id)))
            elif prof_type:
                if prof_type == 'nutrizione':
                    q = q.filter(db.or_(Cliente.nutrizionista_id.isnot(None), Cliente.nutrizionisti_multipli.any()))
                elif prof_type == 'coach':
                    q = q.filter(db.or_(Cliente.coach_id.isnot(None), Cliente.coaches_multipli.any()))
                elif prof_type == 'psicologia':
                    q = q.filter(db.or_(Cliente.psicologa_id.isnot(None), Cliente.psicologi_multipli.any()))
            return q

        include_weekly = check_type in ('all', 'weekly')
        include_dca = check_type in ('all', 'dca')
        include_minor = check_type in ('all', 'minor')

        # ============================================================
        # 1) WEEKLY — count + paginated fetch
        # ============================================================
        weekly_count = 0
        weekly_responses = []
        if include_weekly:
            weekly_base = (
                WeeklyCheckResponse.query
                .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
                .join(Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id)
                .filter(WeeklyCheckResponse.submit_date >= start_date)
            )
            if period == 'custom':
                weekly_base = weekly_base.filter(WeeklyCheckResponse.submit_date <= end_date)
            if accessible_query is not None:
                weekly_base = weekly_base.filter(Cliente.cliente_id.in_(accessible_query))
            weekly_base = _apply_prof_filters(weekly_base)
            weekly_count = weekly_base.count()

        # TypeForm responses (old weekly system) — counted together with weekly
        typeform_count = 0
        if include_weekly:
            tf_base = (
                TypeFormResponse.query
                .join(Cliente, TypeFormResponse.cliente_id == Cliente.cliente_id)
                .filter(TypeFormResponse.submit_date >= start_date)
            )
            if period == 'custom':
                tf_base = tf_base.filter(TypeFormResponse.submit_date <= end_date)
            if accessible_query is not None:
                tf_base = tf_base.filter(Cliente.cliente_id.in_(accessible_query))
            tf_base = _apply_prof_filters(tf_base)
            typeform_count = tf_base.count()

        dca_count = 0
        dca_responses_raw = []
        if include_dca:
            dca_base = (
                DCACheckResponse.query
                .join(DCACheck, DCACheckResponse.dca_check_id == DCACheck.id)
                .join(Cliente, DCACheck.cliente_id == Cliente.cliente_id)
                .filter(DCACheckResponse.submit_date >= start_date)
            )
            if period == 'custom':
                dca_base = dca_base.filter(DCACheckResponse.submit_date <= end_date)
            if accessible_query is not None:
                dca_base = dca_base.filter(Cliente.cliente_id.in_(accessible_query))
            dca_base = _apply_prof_filters(dca_base)
            dca_count = dca_base.count()

        minor_count = 0
        minor_responses_raw = []
        if include_minor:
            minor_base = (
                MinorCheckResponse.query
                .join(MinorCheck, MinorCheckResponse.minor_check_id == MinorCheck.id)
                .join(Cliente, MinorCheck.cliente_id == Cliente.cliente_id)
                .filter(MinorCheckResponse.submit_date >= start_date)
            )
            if period == 'custom':
                minor_base = minor_base.filter(MinorCheckResponse.submit_date <= end_date)
            if accessible_query is not None:
                minor_base = minor_base.filter(Cliente.cliente_id.in_(accessible_query))
            minor_base = _apply_prof_filters(minor_base)
            minor_count = minor_base.count()

        total_count = weekly_count + typeform_count + dca_count + minor_count

        # ============================================================
        # 2) STATS — from weekly + typeform (types with ratings)
        # ============================================================
        stats_query = (
            db.session.query(
                db.func.avg(WeeklyCheckResponse.nutritionist_rating).label('avg_nutrizionista'),
                db.func.avg(WeeklyCheckResponse.psychologist_rating).label('avg_psicologo'),
                db.func.avg(WeeklyCheckResponse.coach_rating).label('avg_coach'),
                db.func.avg(WeeklyCheckResponse.progress_rating).label('avg_progresso')
            )
            .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
            .join(Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id)
            .filter(WeeklyCheckResponse.submit_date >= start_date)
        )
        if period == 'custom':
            stats_query = stats_query.filter(WeeklyCheckResponse.submit_date <= end_date)
        stats_query = _apply_prof_filters(stats_query)
        if accessible_query is not None:
            stats_query = stats_query.filter(Cliente.cliente_id.in_(accessible_query))
        stats_result = stats_query.first()

        # TypeForm stats (same rating fields)
        tf_stats_query = (
            db.session.query(
                db.func.avg(TypeFormResponse.nutritionist_rating).label('avg_nutrizionista'),
                db.func.avg(TypeFormResponse.psychologist_rating).label('avg_psicologo'),
                db.func.avg(TypeFormResponse.coach_rating).label('avg_coach'),
                db.func.avg(TypeFormResponse.progress_rating).label('avg_progresso')
            )
            .join(Cliente, TypeFormResponse.cliente_id == Cliente.cliente_id)
            .filter(TypeFormResponse.submit_date >= start_date)
        )
        if period == 'custom':
            tf_stats_query = tf_stats_query.filter(TypeFormResponse.submit_date <= end_date)
        tf_stats_query = _apply_prof_filters(tf_stats_query)
        if accessible_query is not None:
            tf_stats_query = tf_stats_query.filter(Cliente.cliente_id.in_(accessible_query))
        tf_stats_result = tf_stats_query.first()

        # Combine averages (weighted by count)
        def _combined_avg(wc_avg, tf_avg, wc_n, tf_n):
            if wc_avg and tf_avg and (wc_n + tf_n) > 0:
                return round((float(wc_avg) * wc_n + float(tf_avg) * tf_n) / (wc_n + tf_n), 1)
            if wc_avg:
                return round(float(wc_avg), 1)
            if tf_avg:
                return round(float(tf_avg), 1)
            return None

        avg_nutrizionista = _combined_avg(stats_result.avg_nutrizionista, tf_stats_result.avg_nutrizionista, weekly_count, typeform_count)
        avg_psicologo = _combined_avg(stats_result.avg_psicologo, tf_stats_result.avg_psicologo, weekly_count, typeform_count)
        avg_coach = _combined_avg(stats_result.avg_coach, tf_stats_result.avg_coach, weekly_count, typeform_count)
        avg_progresso = _combined_avg(stats_result.avg_progresso, tf_stats_result.avg_progresso, weekly_count, typeform_count)
        all_avgs = [x for x in [avg_nutrizionista, avg_psicologo, avg_coach, avg_progresso] if x is not None]
        avg_quality = round(sum(all_avgs) / len(all_avgs), 1) if all_avgs else None

        # ============================================================
        # 3) UNIFIED PAGINATION — UNION ALL SQL
        # ============================================================
        # Ogni tipo di check contribuisce un SELECT (id, submit_date, tipo).
        # Postgres ordina e pagina internamente: restituisce solo `per_page`
        # righe invece di caricare tutti gli ID in memoria Python.
        #
        # _apply_prof_filters usa l'API ORM (query.filter) e resta invariata
        # per le query di conteggio/stats. Qui serve la condizione grezza per
        # poterla passare a select().where().
        def _prof_filter_cond():
            if prof_type and prof_id:
                if prof_type == 'nutrizione':
                    return db.or_(Cliente.nutrizionista_id == prof_id, Cliente.nutrizionisti_multipli.any(User.id == prof_id))
                elif prof_type == 'coach':
                    return db.or_(Cliente.coach_id == prof_id, Cliente.coaches_multipli.any(User.id == prof_id))
                elif prof_type == 'psicologia':
                    return db.or_(Cliente.psicologa_id == prof_id, Cliente.psicologi_multipli.any(User.id == prof_id))
            elif prof_type:
                if prof_type == 'nutrizione':
                    return db.or_(Cliente.nutrizionista_id.isnot(None), Cliente.nutrizionisti_multipli.any())
                elif prof_type == 'coach':
                    return db.or_(Cliente.coach_id.isnot(None), Cliente.coaches_multipli.any())
                elif prof_type == 'psicologia':
                    return db.or_(Cliente.psicologa_id.isnot(None), Cliente.psicologi_multipli.any())
            return None

        offset = (page - 1) * per_page
        prof_cond = _prof_filter_cond()

        union_parts = []

        if include_weekly:
            w_sel = (
                select(
                    WeeklyCheckResponse.id.label("id"),
                    WeeklyCheckResponse.submit_date.label("submit_date"),
                    literal("weekly").label("check_type"),
                )
                .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
                .join(Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id)
                .where(WeeklyCheckResponse.submit_date >= start_date)
            )
            if period == 'custom':
                w_sel = w_sel.where(WeeklyCheckResponse.submit_date <= end_date)
            if accessible_query is not None:
                w_sel = w_sel.where(Cliente.cliente_id.in_(accessible_query))
            if prof_cond is not None:
                w_sel = w_sel.where(prof_cond)
            union_parts.append(w_sel)

            tf_sel = (
                select(
                    TypeFormResponse.id.label("id"),
                    TypeFormResponse.submit_date.label("submit_date"),
                    literal("typeform").label("check_type"),
                )
                .join(Cliente, TypeFormResponse.cliente_id == Cliente.cliente_id)
                .where(TypeFormResponse.submit_date >= start_date)
            )
            if period == 'custom':
                tf_sel = tf_sel.where(TypeFormResponse.submit_date <= end_date)
            if accessible_query is not None:
                tf_sel = tf_sel.where(Cliente.cliente_id.in_(accessible_query))
            if prof_cond is not None:
                tf_sel = tf_sel.where(prof_cond)
            union_parts.append(tf_sel)

        if include_dca:
            d_sel = (
                select(
                    DCACheckResponse.id.label("id"),
                    DCACheckResponse.submit_date.label("submit_date"),
                    literal("dca").label("check_type"),
                )
                .join(DCACheck, DCACheckResponse.dca_check_id == DCACheck.id)
                .join(Cliente, DCACheck.cliente_id == Cliente.cliente_id)
                .where(DCACheckResponse.submit_date >= start_date)
            )
            if period == 'custom':
                d_sel = d_sel.where(DCACheckResponse.submit_date <= end_date)
            if accessible_query is not None:
                d_sel = d_sel.where(Cliente.cliente_id.in_(accessible_query))
            if prof_cond is not None:
                d_sel = d_sel.where(prof_cond)
            union_parts.append(d_sel)

        if include_minor:
            m_sel = (
                select(
                    MinorCheckResponse.id.label("id"),
                    MinorCheckResponse.submit_date.label("submit_date"),
                    literal("minor").label("check_type"),
                )
                .join(MinorCheck, MinorCheckResponse.minor_check_id == MinorCheck.id)
                .join(Cliente, MinorCheck.cliente_id == Cliente.cliente_id)
                .where(MinorCheckResponse.submit_date >= start_date)
            )
            if period == 'custom':
                m_sel = m_sel.where(MinorCheckResponse.submit_date <= end_date)
            if accessible_query is not None:
                m_sel = m_sel.where(Cliente.cliente_id.in_(accessible_query))
            if prof_cond is not None:
                m_sel = m_sel.where(prof_cond)
            union_parts.append(m_sel)

        if union_parts:
            combined = union_all(*union_parts).subquery("combined")
            page_rows = db.session.execute(
                select(combined.c.id, combined.c.submit_date, combined.c.check_type)
                .order_by(combined.c.submit_date.desc().nullslast(), combined.c.id.desc())
                .limit(per_page)
                .offset(offset)
            ).fetchall()
            page_items = [(row.submit_date, row.check_type, row.id) for row in page_rows]
        else:
            page_items = []

        # Group IDs by type for batch loading
        weekly_ids_page = [item[2] for item in page_items if item[1] == 'weekly']
        typeform_ids_page = [item[2] for item in page_items if item[1] == 'typeform']
        dca_ids_page = [item[2] for item in page_items if item[1] == 'dca']
        minor_ids_page = [item[2] for item in page_items if item[1] == 'minor']

        # ── Batch load weekly ──
        weekly_by_id = {}
        if weekly_ids_page:
            weekly_loaded = (
                WeeklyCheckResponse.query
                .filter(WeeklyCheckResponse.id.in_(weekly_ids_page))
                .options(
                    joinedload(WeeklyCheckResponse.assignment)
                    .joinedload(WeeklyCheck.cliente)
                    .defer(Cliente.check_saltati),
                    joinedload(WeeklyCheckResponse.assignment)
                    .joinedload(WeeklyCheck.cliente)
                    .selectinload(Cliente.nutrizionisti_multipli),
                    joinedload(WeeklyCheckResponse.assignment)
                    .joinedload(WeeklyCheck.cliente)
                    .selectinload(Cliente.coaches_multipli),
                    joinedload(WeeklyCheckResponse.assignment)
                    .joinedload(WeeklyCheck.cliente)
                    .selectinload(Cliente.psicologi_multipli),
                    joinedload(WeeklyCheckResponse.assignment)
                    .joinedload(WeeklyCheck.cliente)
                    .joinedload(Cliente.nutrizionista_user),
                    joinedload(WeeklyCheckResponse.assignment)
                    .joinedload(WeeklyCheck.cliente)
                    .joinedload(Cliente.coach_user),
                    joinedload(WeeklyCheckResponse.assignment)
                    .joinedload(WeeklyCheck.cliente)
                    .joinedload(Cliente.psicologa_user),
                )
                .all()
            )
            weekly_by_id = {r.id: r for r in weekly_loaded}

        # ── Batch load TypeForm ──
        typeform_by_id = {}
        if typeform_ids_page:
            tf_loaded = (
                TypeFormResponse.query
                .filter(TypeFormResponse.id.in_(typeform_ids_page))
                .options(
                    joinedload(TypeFormResponse.cliente)
                    .defer(Cliente.check_saltati),
                    joinedload(TypeFormResponse.cliente)
                    .selectinload(Cliente.nutrizionisti_multipli),
                    joinedload(TypeFormResponse.cliente)
                    .selectinload(Cliente.coaches_multipli),
                    joinedload(TypeFormResponse.cliente)
                    .selectinload(Cliente.psicologi_multipli),
                    joinedload(TypeFormResponse.cliente)
                    .joinedload(Cliente.nutrizionista_user),
                    joinedload(TypeFormResponse.cliente)
                    .joinedload(Cliente.coach_user),
                    joinedload(TypeFormResponse.cliente)
                    .joinedload(Cliente.psicologa_user),
                )
                .all()
            )
            typeform_by_id = {r.id: r for r in tf_loaded}

        # ── Batch load DCA ──
        dca_by_id = {}
        if dca_ids_page:
            dca_loaded = (
                DCACheckResponse.query
                .filter(DCACheckResponse.id.in_(dca_ids_page))
                .options(
                    joinedload(DCACheckResponse.assignment)
                    .joinedload(DCACheck.cliente)
                    .defer(Cliente.check_saltati),
                    joinedload(DCACheckResponse.assignment)
                    .joinedload(DCACheck.cliente)
                    .selectinload(Cliente.nutrizionisti_multipli),
                    joinedload(DCACheckResponse.assignment)
                    .joinedload(DCACheck.cliente)
                    .selectinload(Cliente.coaches_multipli),
                    joinedload(DCACheckResponse.assignment)
                    .joinedload(DCACheck.cliente)
                    .selectinload(Cliente.psicologi_multipli),
                    joinedload(DCACheckResponse.assignment)
                    .joinedload(DCACheck.cliente)
                    .joinedload(Cliente.nutrizionista_user),
                    joinedload(DCACheckResponse.assignment)
                    .joinedload(DCACheck.cliente)
                    .joinedload(Cliente.coach_user),
                    joinedload(DCACheckResponse.assignment)
                    .joinedload(DCACheck.cliente)
                    .joinedload(Cliente.psicologa_user),
                )
                .all()
            )
            dca_by_id = {r.id: r for r in dca_loaded}

        # ── Batch load Minor ──
        minor_by_id = {}
        if minor_ids_page:
            minor_loaded = (
                MinorCheckResponse.query
                .filter(MinorCheckResponse.id.in_(minor_ids_page))
                .options(
                    joinedload(MinorCheckResponse.assignment)
                    .joinedload(MinorCheck.cliente)
                    .defer(Cliente.check_saltati),
                    joinedload(MinorCheckResponse.assignment)
                    .joinedload(MinorCheck.cliente)
                    .selectinload(Cliente.nutrizionisti_multipli),
                    joinedload(MinorCheckResponse.assignment)
                    .joinedload(MinorCheck.cliente)
                    .selectinload(Cliente.coaches_multipli),
                    joinedload(MinorCheckResponse.assignment)
                    .joinedload(MinorCheck.cliente)
                    .selectinload(Cliente.psicologi_multipli),
                    joinedload(MinorCheckResponse.assignment)
                    .joinedload(MinorCheck.cliente)
                    .joinedload(Cliente.nutrizionista_user),
                    joinedload(MinorCheckResponse.assignment)
                    .joinedload(MinorCheck.cliente)
                    .joinedload(Cliente.coach_user),
                    joinedload(MinorCheckResponse.assignment)
                    .joinedload(MinorCheck.cliente)
                    .joinedload(Cliente.psicologa_user),
                )
                .all()
            )
            minor_by_id = {r.id: r for r in minor_loaded}

        # ── Batch load read confirmations for all 3 types ──
        all_confirmations = {}  # key: (type, response_id) → set of user_ids
        conf_filters = []
        if weekly_ids_page:
            conf_filters.append(db.and_(
                ClientCheckReadConfirmation.response_type == 'weekly_check',
                ClientCheckReadConfirmation.response_id.in_(weekly_ids_page)
            ))
        if dca_ids_page:
            conf_filters.append(db.and_(
                ClientCheckReadConfirmation.response_type == 'dca_check',
                ClientCheckReadConfirmation.response_id.in_(dca_ids_page)
            ))
        if minor_ids_page:
            conf_filters.append(db.and_(
                ClientCheckReadConfirmation.response_type == 'minor_check',
                ClientCheckReadConfirmation.response_id.in_(minor_ids_page)
            ))
        if conf_filters:
            confirmations = ClientCheckReadConfirmation.query.filter(db.or_(*conf_filters)).all()
            for conf in confirmations:
                key = (conf.response_type, conf.response_id)
                if key not in all_confirmations:
                    all_confirmations[key] = set()
                all_confirmations[key].add(conf.user_id)

        # ── Helper: format professional info ──
        def _format_prof(user, confirmed_ids):
            if not user:
                return None
            return {
                "id": user.id,
                "nome": user.full_name,
                "avatar_path": user.avatar_path,
                "has_read": user.id in confirmed_ids
            }

        def _get_profs(cliente, confirmed_user_ids):
            """Extract nutrizionisti, psicologi, coaches for a cliente."""
            nutrizionisti = []
            seen_ids = set()
            for n in (cliente.nutrizionisti_multipli or [])[:2]:
                if n.id not in seen_ids:
                    nutrizionisti.append(_format_prof(n, confirmed_user_ids))
                    seen_ids.add(n.id)
            if cliente.nutrizionista_user and cliente.nutrizionista_user.id not in seen_ids and len(nutrizionisti) < 2:
                nutrizionisti.append(_format_prof(cliente.nutrizionista_user, confirmed_user_ids))
            nutrizionisti = [n for n in nutrizionisti if n]

            psicologi = []
            seen_ids = set()
            for p in (cliente.psicologi_multipli or [])[:2]:
                if p.id not in seen_ids:
                    psicologi.append(_format_prof(p, confirmed_user_ids))
                    seen_ids.add(p.id)
            if cliente.psicologa_user and cliente.psicologa_user.id not in seen_ids and len(psicologi) < 2:
                psicologi.append(_format_prof(cliente.psicologa_user, confirmed_user_ids))
            psicologi = [p for p in psicologi if p]

            coaches = []
            seen_ids = set()
            for c in (cliente.coaches_multipli or [])[:2]:
                if c.id not in seen_ids:
                    coaches.append(_format_prof(c, confirmed_user_ids))
                    seen_ids.add(c.id)
            if cliente.coach_user and cliente.coach_user.id not in seen_ids and len(coaches) < 2:
                coaches.append(_format_prof(cliente.coach_user, confirmed_user_ids))
            coaches = [c for c in coaches if c]

            return nutrizionisti, psicologi, coaches

        # ============================================================
        # 4) SERIALIZE — iterate page_items in order
        # ============================================================
        responses_data = []
        for _, item_type, item_id in page_items:
            if item_type == 'weekly':
                resp = weekly_by_id.get(item_id)
                if not resp:
                    continue
                cliente = resp.assignment.cliente if resp.assignment else None
                if not cliente:
                    continue
                confirmed_user_ids = all_confirmations.get(('weekly_check', resp.id), set())
                nutrizionisti, psicologi, coaches = _get_profs(cliente, confirmed_user_ids)
                responses_data.append({
                    "id": resp.id,
                    "type": "weekly",
                    "cliente_id": cliente.cliente_id,
                    "cliente_nome": cliente.nome_cognome or "Sconosciuto",
                    "programma": cliente.tipologia_cliente.value if cliente.tipologia_cliente else None,
                    "submit_date": resp.submit_date.strftime('%d/%m/%Y') if resp.submit_date else None,
                    "submit_date_iso": resp.submit_date.isoformat() if resp.submit_date else None,
                    "nutritionist_rating": resp.nutritionist_rating,
                    "psychologist_rating": resp.psychologist_rating,
                    "coach_rating": resp.coach_rating,
                    "progress_rating": resp.progress_rating,
                    "nutrizionisti": nutrizionisti,
                    "psicologi": psicologi,
                    "coaches": coaches,
                })

            elif item_type == 'typeform':
                resp = typeform_by_id.get(item_id)
                if not resp:
                    continue
                cliente = resp.cliente
                if not cliente:
                    continue
                nutrizionisti, psicologi, coaches = _get_profs(cliente, set())
                responses_data.append({
                    "id": resp.id,
                    "type": "weekly",
                    "source": "typeform",
                    "cliente_id": cliente.cliente_id,
                    "cliente_nome": cliente.nome_cognome or "Sconosciuto",
                    "programma": cliente.tipologia_cliente.value if cliente.tipologia_cliente else None,
                    "submit_date": resp.submit_date.strftime('%d/%m/%Y') if resp.submit_date else None,
                    "submit_date_iso": resp.submit_date.isoformat() if resp.submit_date else None,
                    "nutritionist_rating": resp.nutritionist_rating,
                    "psychologist_rating": resp.psychologist_rating,
                    "coach_rating": resp.coach_rating,
                    "progress_rating": resp.progress_rating,
                    "nutrizionisti": nutrizionisti,
                    "psicologi": psicologi,
                    "coaches": coaches,
                })

            elif item_type == 'dca':
                resp = dca_by_id.get(item_id)
                if not resp:
                    continue
                cliente = resp.assignment.cliente if resp.assignment else None
                if not cliente:
                    continue
                confirmed_user_ids = all_confirmations.get(('dca_check', resp.id), set())
                nutrizionisti, psicologi, coaches = _get_profs(cliente, confirmed_user_ids)
                responses_data.append({
                    "id": resp.id,
                    "type": "dca",
                    "cliente_id": cliente.cliente_id,
                    "cliente_nome": cliente.nome_cognome or "Sconosciuto",
                    "programma": cliente.tipologia_cliente.value if cliente.tipologia_cliente else None,
                    "submit_date": resp.submit_date.strftime('%d/%m/%Y') if resp.submit_date else None,
                    "submit_date_iso": resp.submit_date.isoformat() if resp.submit_date else None,
                    "completion_percentage": resp.completion_percentage,
                    "nutrizionisti": nutrizionisti,
                    "psicologi": psicologi,
                    "coaches": coaches,
                })

            elif item_type == 'minor':
                resp = minor_by_id.get(item_id)
                if not resp:
                    continue
                cliente = resp.assignment.cliente if resp.assignment else None
                if not cliente:
                    continue
                confirmed_user_ids = all_confirmations.get(('minor_check', resp.id), set())
                nutrizionisti, psicologi, coaches = _get_profs(cliente, confirmed_user_ids)
                responses_data.append({
                    "id": resp.id,
                    "type": "minor",
                    "cliente_id": cliente.cliente_id,
                    "cliente_nome": cliente.nome_cognome or "Sconosciuto",
                    "programma": cliente.tipologia_cliente.value if cliente.tipologia_cliente else None,
                    "submit_date": resp.submit_date.strftime('%d/%m/%Y') if resp.submit_date else None,
                    "submit_date_iso": resp.submit_date.isoformat() if resp.submit_date else None,
                    "score_global": resp.score_global,
                    "completion_percentage": resp.completion_percentage,
                    "nutrizionisti": nutrizionisti,
                    "psicologi": psicologi,
                    "coaches": coaches,
                })

        return jsonify({
            "success": True,
            "period": period,
            "check_type": check_type,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_count,
                "pages": (total_count + per_page - 1) // per_page
            },
            "stats": {
                "total_responses": total_count,
                "weekly_count": weekly_count + typeform_count,
                "dca_count": dca_count,
                "minor_count": minor_count,
                "avg_nutrizionista": avg_nutrizionista,
                "avg_psicologo": avg_psicologo,
                "avg_coach": avg_coach,
                "avg_progresso": avg_progresso,
                "avg_quality": avg_quality
            },
            "responses": responses_data
        })

    except Exception as e:
        current_app.logger.error(f"[API] Errore azienda stats: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/professionisti/<prof_type>")
@login_required
def api_get_professionisti_by_type(prof_type: str):
    """
    API JSON: Ottiene la lista dei professionisti per tipo.
    prof_type: 'nutrizione', 'coach', 'psicologia'
    """
    from corposostenibile.models import User, Team

    try:
        # Map prof_type to specialty values (from UserSpecialtyEnum)
        specialty_map = {
            'nutrizione': ['nutrizione', 'nutrizionista'],
            'coach': ['coach'],
            'psicologia': ['psicologia', 'psicologo']
        }

        if prof_type not in specialty_map:
            return jsonify({"success": False, "error": "Tipo professionista non valido"}), 400

        specialties = specialty_map[prof_type]

        # Query users with matching specialty
        professionals_query = User.query.filter(
            User.specialty.in_(specialties),
            User.is_active == True
        )

        # Team leader: only professionals of own led team(s) and only own specialty family
        user_role = getattr(current_user, 'role', None)
        current_specialty = getattr(current_user, 'specialty', None)
        if hasattr(user_role, 'value'):
            user_role = user_role.value
        if hasattr(current_specialty, 'value'):
            current_specialty = current_specialty.value

        if str(user_role) == 'team_leader':
            tl_specialty_map = {
                'nutrizione': 'nutrizione',
                'nutrizionista': 'nutrizione',
                'coach': 'coach',
                'psicologia': 'psicologia',
                'psicologo': 'psicologia',
            }
            expected_prof_type = tl_specialty_map.get(str(current_specialty or '').lower())
            if expected_prof_type and prof_type != expected_prof_type:
                return jsonify({
                    "success": True,
                    "professionisti": []
                })

            led_team_ids = [t.id for t in (getattr(current_user, 'teams_led', None) or [])]
            if led_team_ids:
                # Includi sia i membri del team che il team leader stesso
                led_head_ids = [t.head_id for t in current_user.teams_led if t.head_id]
                professionals_query = professionals_query.filter(
                    db.or_(
                        User.teams.any(Team.id.in_(led_team_ids)),
                        User.id.in_(led_head_ids)
                    )
                )
            else:
                professionals_query = professionals_query.filter(User.id == -1)

        professionals = professionals_query.order_by(User.last_name, User.first_name).all()

        result = [{
            "id": p.id,
            "nome": p.full_name,
            "avatar_url": p.avatar_url
        } for p in professionals]

        return jsonify({
            "success": True,
            "professionisti": result
        })

    except Exception as e:
        current_app.logger.error(f"[API] Errore get professionisti: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/initial-assignments", methods=["GET"])
@login_required
def api_initial_assignments():
    """
    API JSON: lista lead con stato Check 1 / Check 2 iniziali.
    Filtri:
      - client_search: nome/cognome/email
      - status: all | completed_all | completed_any | pending
      - page, per_page
    """
    try:
        client_search = request.args.get("client_search", "").strip().lower()
        status = request.args.get("status", "all").strip().lower()
        page = max(request.args.get("page", 1, type=int), 1)
        per_page = min(max(request.args.get("per_page", 20, type=int), 1), 100)
        client_ids_raw = (request.args.get("client_ids") or "").strip()
        client_ids = {
            int(cid)
            for cid in client_ids_raw.split(",")
            if cid.strip().isdigit()
        } if client_ids_raw else set()

        check_1_form, check_2_form = _get_initial_check_forms()

        target_form_ids = [f.id for f in [check_1_form, check_2_form] if f]
        if not target_form_ids:
            return jsonify({
                "success": True,
                "items": [],
                "pagination": {"page": page, "per_page": per_page, "total": 0, "pages": 0},
                "meta": {"check_1_name": "Check 1", "check_2_name": "Check 2"},
            })

        query = (
            ClientCheckAssignment.query
            .options(
                joinedload(ClientCheckAssignment.cliente),
                joinedload(ClientCheckAssignment.form),
            )
            .filter(
                ClientCheckAssignment.is_active.is_(True),
                ClientCheckAssignment.form_id.in_(target_form_ids),
            )
            .order_by(desc(ClientCheckAssignment.created_at))
        )

        if client_ids:
            query = query.filter(ClientCheckAssignment.cliente_id.in_(client_ids))

        accessible_clients_query = get_accessible_clients_query()
        if accessible_clients_query is not None:
            query = query.filter(
                ClientCheckAssignment.cliente_id.in_(accessible_clients_query)
            )

        assignments = query.all()

        grouped: Dict[int, Dict[str, Any]] = {}
        for assignment in assignments:
            cliente = assignment.cliente
            if not cliente:
                continue

            if client_search:
                nome = (cliente.nome or "").lower()
                cognome = (cliente.cognome or "").lower()
                email = (cliente.mail or "").lower()
                full_name = f"{nome} {cognome}".strip()
                if (
                    client_search not in nome
                    and client_search not in cognome
                    and client_search not in email
                    and client_search not in full_name
                ):
                    continue

            row = grouped.setdefault(
                cliente.cliente_id,
                {
                    "lead_id": cliente.cliente_id,
                    "lead_name": cliente.nome_cognome,
                    "lead_email": cliente.mail,
                    "latest_activity_at": assignment.created_at,
                    "check_1": {"assigned": False, "completed": False, "response_count": 0},
                    "check_2": {"assigned": False, "completed": False, "response_count": 0},
                },
            )

            if assignment.created_at and assignment.created_at > row["latest_activity_at"]:
                row["latest_activity_at"] = assignment.created_at

            if check_1_form and assignment.form_id == check_1_form.id:
                row["check_1"] = {
                    "assigned": True,
                    "completed": assignment.response_count > 0,
                    "response_count": 1 if (assignment.response_count or 0) > 0 else 0,
                    "latest_response_id": assignment.latest_response.id if assignment.latest_response else None,
                    "token": assignment.token,
                }
            elif check_2_form and assignment.form_id == check_2_form.id:
                row["check_2"] = {
                    "assigned": True,
                    "completed": assignment.response_count > 0,
                    "response_count": 1 if (assignment.response_count or 0) > 0 else 0,
                    "latest_response_id": assignment.latest_response.id if assignment.latest_response else None,
                    "token": assignment.token,
                }

        items = list(grouped.values())

        def _match_status(item: Dict[str, Any]) -> bool:
            c1 = item["check_1"]["completed"]
            c2 = item["check_2"]["completed"]
            if status == "completed_all":
                return c1 and c2
            if status == "completed_any":
                return c1 or c2
            if status == "pending":
                return not (c1 or c2)
            return True

        items = [item for item in items if _match_status(item)]
        items.sort(key=lambda x: x["latest_activity_at"] or datetime.min, reverse=True)

        total = len(items)
        pages = (total + per_page - 1) // per_page if total else 0
        start = (page - 1) * per_page
        end = start + per_page
        page_items = items[start:end]

        return jsonify({
            "success": True,
            "items": page_items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": pages,
            },
            "meta": {
                "check_1_name": check_1_form.name if check_1_form else "Check 1",
                "check_2_name": check_2_form.name if check_2_form else "Check 2",
            },
        })
    except Exception as e:
        current_app.logger.error(f"[API] Errore initial assignments: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def _get_initial_check_forms():
    check_1_form = (
        CheckForm.query
        .filter(CheckForm.name.ilike("Check 1 - PRE-CHECK INIZIALE"))
        .first()
    )
    check_2_form = (
        CheckForm.query
        .filter(CheckForm.name.ilike("Check 2 - Mockup Follow-up Iniziale"))
        .first()
    )
    return check_1_form, check_2_form


@api_bp.route("/initial-assignments/<int:lead_id>/check/<int:check_number>/response", methods=["GET"])
@login_required
def api_initial_assignment_check_response(lead_id: int, check_number: int):
    """Restituisce il dettaglio della compilazione check iniziale per il modal React."""
    try:
        if check_number not in (1, 2):
            return jsonify({"success": False, "error": "check_number non valido"}), 400

        check_1_form, check_2_form = _get_initial_check_forms()
        target_form = check_1_form if check_number == 1 else check_2_form
        if not target_form:
            return jsonify({"success": False, "error": "Form check non trovato"}), 404

        query = ClientCheckAssignment.query.filter(
            ClientCheckAssignment.cliente_id == lead_id,
            ClientCheckAssignment.form_id == target_form.id,
            ClientCheckAssignment.is_active.is_(True),
        )
        accessible_clients_query = get_accessible_clients_query()
        if accessible_clients_query is not None:
            query = query.filter(
                ClientCheckAssignment.cliente_id.in_(accessible_clients_query)
            )

        assignment = (
            query
            .options(
                joinedload(ClientCheckAssignment.form).joinedload(CheckForm.fields),
                joinedload(ClientCheckAssignment.responses),
                joinedload(ClientCheckAssignment.cliente),
            )
            .order_by(desc(ClientCheckAssignment.created_at))
            .first()
        )

        if not assignment:
            return jsonify({"success": False, "error": "Assegnazione non trovata"}), 404
        if assignment.response_count <= 0 or not assignment.latest_response:
            return jsonify({"success": False, "error": "Check non ancora compilato"}), 404

        response = assignment.latest_response
        payload = []
        for field in sorted(assignment.form.fields, key=lambda f: f.position):
            payload.append({
                "field_id": field.id,
                "label": field.label,
                "field_type": field.field_type.value if hasattr(field.field_type, "value") else str(field.field_type),
                "value": response.get_response_value(field.id),
            })

        return jsonify({
            "success": True,
            "data": {
                "lead_id": lead_id,
                "lead_name": assignment.cliente.nome_cognome if assignment.cliente else None,
                "check_number": check_number,
                "form_name": assignment.form.name,
                "response_id": response.id,
                "submitted_at": response.created_at.isoformat() if response.created_at else None,
                "responses": payload,
            },
        })
    except Exception as e:
        current_app.logger.error(
            f"[API] Errore dettaglio check iniziale lead={lead_id} check={check_number}: {e}",
            exc_info=True,
        )
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# PUBLIC API ENDPOINTS (No authentication required - for React frontend)
# ============================================================================

@csrf.exempt
@api_bp.route("/public/<check_type>/<token>", methods=["GET"])
@client_checks_bp.route("/api/public/<check_type>/<token>", methods=["GET"])
def api_public_get_check_info(check_type: str, token: str):
    """
    API pubblica: Ottiene le info del check e del cliente per il form React.
    Non richiede autenticazione.
    """
    from corposostenibile.models import WeeklyCheck, DCACheck, MinorCheck

    if check_type not in ['weekly', 'dca', 'minor']:
        return jsonify({"success": False, "error": "Tipo check non valido"}), 400

    try:
        # Select correct model
        if check_type == 'weekly':
            Model = WeeklyCheck
        elif check_type == 'dca':
            Model = DCACheck
        else:
            Model = MinorCheck

        # Find check by token
        check = Model.query.filter_by(token=token, is_active=True).first()

        if not check:
            return jsonify({"success": False, "error": "Check non trovato o scaduto"}), 404

        # Get client info
        cliente = Cliente.query.get(check.cliente_id)
        if not cliente:
            return jsonify({"success": False, "error": "Cliente non trovato"}), 404

        # Get professionals info (supporta assegnazioni singole e multiple)
        professionisti = []
        seen_keys = set()

        def append_prof(user, ruolo, rating_field, feedback_field):
            if not user:
                return
            key = f"{ruolo}:{user.id}"
            if key in seen_keys:
                return
            seen_keys.add(key)
            professionisti.append({
                "id": user.id,
                "nome": user.full_name or user.email,
                "ruolo": ruolo,
                "rating_field": rating_field,
                "feedback_field": feedback_field,
            })

        append_prof(cliente.nutrizionista_user, "Nutrizionista", "nutritionist_rating", "nutritionist_feedback")
        for user in (cliente.nutrizionisti_multipli or []):
            append_prof(user, "Nutrizionista", "nutritionist_rating", "nutritionist_feedback")

        append_prof(cliente.psicologa_user, "Psicologo/a", "psychologist_rating", "psychologist_feedback")
        for user in (cliente.psicologi_multipli or []):
            append_prof(user, "Psicologo/a", "psychologist_rating", "psychologist_feedback")

        append_prof(cliente.coach_user, "Coach", "coach_rating", "coach_feedback")
        for user in (cliente.coaches_multipli or []):
            append_prof(user, "Coach", "coach_rating", "coach_feedback")

        response = jsonify({
            "success": True,
            "check": {
                "id": check.id,
                "type": check_type,
                "response_count": check.response_count
            },
            "cliente": {
                "id": cliente.cliente_id,
                "nome": cliente.nome_cognome.split()[0] if cliente.nome_cognome else "",
                "nome_cognome": cliente.nome_cognome
            },
            "professionisti": professionisti
        })
        # Prevent browser/proxy conditional caching (304) on this endpoint.
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        current_app.logger.error(f"[API_PUBLIC] Errore get check info: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Errore interno"}), 500


@csrf.exempt
@api_bp.route("/public/weekly/<token>", methods=["POST"])
@client_checks_bp.route("/api/public/weekly/<token>", methods=["POST"])
def api_public_submit_weekly(token: str):
    """
    API pubblica: Salva risposta check settimanale.
    Accetta sia form-data (con foto) che JSON.
    """
    from corposostenibile.models import WeeklyCheck, WeeklyCheckResponse

    try:
        check = WeeklyCheck.query.filter_by(token=token, is_active=True).first()
        if not check:
            return jsonify({"success": False, "error": "Check non trovato"}), 404

        # Handle both JSON and form-data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        # Create response with correct model field names
        snapshot = _get_weekly_professional_snapshot(check.cliente)
        response = WeeklyCheckResponse(
            weekly_check_id=check.id,
            submit_date=datetime.utcnow(),
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None,
            nutritionist_user_id=snapshot["nutritionist_user_id"],
            psychologist_user_id=snapshot["psychologist_user_id"],
            coach_user_id=snapshot["coach_user_id"],
            # Text fields
            what_worked=data.get('what_worked'),
            what_didnt_work=data.get('what_didnt_work'),
            what_learned=data.get('what_learned'),
            what_focus_next=data.get('what_focus_next'),
            injuries_notes=data.get('injuries_notes'),
            nutrition_program_adherence=data.get('nutrition_program_adherence'),
            training_program_adherence=data.get('training_program_adherence'),
            exercise_modifications=data.get('exercise_modifications'),
            daily_steps=data.get('daily_steps'),
            completed_training_weeks=data.get('completed_training_weeks'),
            planned_training_days=data.get('planned_training_days'),
            live_session_topics=data.get('live_session_topics'),
            extra_comments=data.get('extra_comments'),
            # Wellness ratings (0-10)
            digestion_rating=int(data.get('digestion_rating')) if data.get('digestion_rating') else None,
            energy_rating=int(data.get('energy_rating')) if data.get('energy_rating') else None,
            strength_rating=int(data.get('strength_rating')) if data.get('strength_rating') else None,
            hunger_rating=int(data.get('hunger_rating')) if data.get('hunger_rating') else None,
            sleep_rating=int(data.get('sleep_rating')) if data.get('sleep_rating') else None,
            mood_rating=int(data.get('mood_rating')) if data.get('mood_rating') else None,
            motivation_rating=int(data.get('motivation_rating')) if data.get('motivation_rating') else None,
            # Weight
            weight=float(data.get('weight')) if data.get('weight') else None,
            # Professional ratings
            nutritionist_rating=int(data.get('nutritionist_rating')) if data.get('nutritionist_rating') else None,
            psychologist_rating=int(data.get('psychologist_rating')) if data.get('psychologist_rating') else None,
            coach_rating=int(data.get('coach_rating')) if data.get('coach_rating') else None,
            progress_rating=int(data.get('progress_rating')) if data.get('progress_rating') else None,
        )

        # Handle photo uploads
        if not request.is_json and request.files:
            import os
            from werkzeug.utils import secure_filename
            photos_folder = os.path.join(
                current_app.config.get('UPLOAD_FOLDER', 'uploads'),
                'weekly_checks', str(check.cliente_id)
            )
            os.makedirs(photos_folder, exist_ok=True)

            photo_mapping = {'photo_front': 'front', 'photo_side': 'side', 'photo_back': 'back'}
            for field, suffix in photo_mapping.items():
                if field in request.files:
                    file = request.files[field]
                    if file and file.filename:
                        filename = secure_filename(f"{check.cliente_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{suffix}.jpg")
                        filepath = os.path.join(photos_folder, filename)
                        file.save(filepath)
                        setattr(response, field, filepath)

        db.session.add(response)
        try:
            db.session.commit()
        except Exception as commit_err:
            db.session.rollback()
            if "unique" in str(commit_err).lower():
                _fix_sequence("weekly_check_responses")
                db.session.add(response)
                db.session.commit()
            else:
                raise

        current_app.logger.info(f"[WEEKLY_CHECK] Risposta salvata per cliente {check.cliente_id}")

        return jsonify({"success": True, "message": "Check inviato con successo"})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[API_PUBLIC] Errore submit weekly: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Errore nel salvataggio"}), 500


@csrf.exempt
@api_bp.route("/public/dca/<token>", methods=["POST"])
@client_checks_bp.route("/api/public/dca/<token>", methods=["POST"])
def api_public_submit_dca(token: str):
    """
    API pubblica: Salva risposta check DCA (benessere).
    """
    from corposostenibile.models import DCACheck, DCACheckResponse

    try:
        check = DCACheck.query.filter_by(token=token, is_active=True).first()
        if not check:
            return jsonify({"success": False, "error": "Check non trovato"}), 404

        data = request.get_json() if request.is_json else request.form.to_dict()

        # Create response with correct model field names
        def safe_int(val):
            try:
                return int(val) if val else None
            except (ValueError, TypeError):
                return None

        response = DCACheckResponse(
            dca_check_id=check.id,
            submit_date=datetime.utcnow(),
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None,
            # Benessere emotivo e psicologico (1-5)
            mood_balance_rating=safe_int(data.get('mood_balance_rating')),
            food_plan_serenity=safe_int(data.get('food_plan_serenity')),
            food_weight_worry=safe_int(data.get('food_weight_worry')),
            emotional_eating=safe_int(data.get('emotional_eating')),
            body_comfort=safe_int(data.get('body_comfort')),
            body_respect=safe_int(data.get('body_respect')),
            # Allenamento (1-5)
            exercise_wellness=safe_int(data.get('exercise_wellness')),
            exercise_guilt=safe_int(data.get('exercise_guilt')),
            # Riposo e relazioni (1-5)
            sleep_satisfaction=safe_int(data.get('sleep_satisfaction')),
            relationship_time=safe_int(data.get('relationship_time')),
            personal_time=safe_int(data.get('personal_time')),
            # Gestione emozioni (1-5)
            life_interference=safe_int(data.get('life_interference')),
            unexpected_management=safe_int(data.get('unexpected_management')),
            self_compassion=safe_int(data.get('self_compassion')),
            # Physical params (0-10)
            digestion_rating=safe_int(data.get('digestion_rating')),
            energy_rating=safe_int(data.get('energy_rating')),
            strength_rating=safe_int(data.get('strength_rating')),
            hunger_rating=safe_int(data.get('hunger_rating')),
            sleep_rating=safe_int(data.get('sleep_rating')),
            mood_rating=safe_int(data.get('mood_rating')),
            motivation_rating=safe_int(data.get('motivation_rating')),
        )

        db.session.add(response)
        try:
            db.session.commit()
        except Exception as commit_err:
            db.session.rollback()
            if "unique" in str(commit_err).lower():
                _fix_sequence("dca_check_responses")
                db.session.add(response)
                db.session.commit()
            else:
                raise

        current_app.logger.info(f"[DCA_CHECK] Risposta salvata per cliente {check.cliente_id}")

        return jsonify({"success": True, "message": "Check inviato con successo"})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[API_PUBLIC] Errore submit DCA: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Errore nel salvataggio"}), 500


@csrf.exempt
@api_bp.route("/public/minor/<token>", methods=["POST"])
@client_checks_bp.route("/api/public/minor/<token>", methods=["POST"])
def api_public_submit_minor(token: str):
    """
    API pubblica: Salva risposta check minori (EDE-Q6).
    """
    from corposostenibile.models import MinorCheck, MinorCheckResponse

    try:
        check = MinorCheck.query.filter_by(token=token, is_active=True).first()
        if not check:
            return jsonify({"success": False, "error": "Check non trovato"}), 404

        data = request.get_json() if request.is_json else request.form.to_dict()

        # Build responses_data JSON from all q1-q28 questions
        responses_data = {}
        for i in range(1, 29):
            key = f'q{i}'
            if data.get(key) is not None:
                try:
                    responses_data[key] = int(data.get(key))
                except (ValueError, TypeError):
                    responses_data[key] = data.get(key)

        # Create response with correct model field names
        response = MinorCheckResponse(
            minor_check_id=check.id,
            submit_date=datetime.utcnow(),
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None,
            # Store all questions as JSON
            responses_data=responses_data,
            # Physical fields
            peso_attuale=float(data.get('peso_attuale')) if data.get('peso_attuale') else None,
            altezza=float(data.get('altezza')) if data.get('altezza') else None,
        )

        # Calculate scores after creation
        response.calculate_scores()

        db.session.add(response)
        try:
            db.session.commit()
        except Exception as commit_err:
            db.session.rollback()
            if "unique" in str(commit_err).lower():
                _fix_sequence("minor_check_responses")
                db.session.add(response)
                db.session.commit()
            else:
                raise

        current_app.logger.info(f"[MINOR_CHECK] Risposta salvata per cliente {check.cliente_id}")

        return jsonify({"success": True, "message": "Questionario inviato con successo"})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[API_PUBLIC] Errore submit minor: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Errore nel salvataggio"}), 500


# --------------------------------------------------------------------------- #
#  API Admin Dashboard Stats (for React Welcome dashboard)                     #
# --------------------------------------------------------------------------- #

def _apply_check_rbac_weekly(q):
    """Join WeeklyCheckResponse -> WeeklyCheck -> Cliente and apply RBAC if needed."""
    q = q.join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id).join(
        Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id
    )
    accessible = get_accessible_clients_query()
    if accessible is not None:
        q = q.filter(Cliente.cliente_id.in_(accessible))
    return q


def _apply_check_rbac_dca(q):
    """Join DCACheckResponse -> DCACheck -> Cliente and apply RBAC if needed."""
    q = q.join(DCACheck, DCACheckResponse.dca_check_id == DCACheck.id).join(
        Cliente, DCACheck.cliente_id == Cliente.cliente_id
    )
    accessible = get_accessible_clients_query()
    if accessible is not None:
        q = q.filter(Cliente.cliente_id.in_(accessible))
    return q


def _apply_check_rbac_minor(q):
    """Join MinorCheckResponse -> MinorCheck -> Cliente and apply RBAC if needed."""
    q = q.join(MinorCheck, MinorCheckResponse.minor_check_id == MinorCheck.id).join(
        Cliente, MinorCheck.cliente_id == Cliente.cliente_id
    )
    accessible = get_accessible_clients_query()
    if accessible is not None:
        q = q.filter(Cliente.cliente_id.in_(accessible))
    return q


@api_bp.route("/admin/dashboard-stats")
@login_required
def api_admin_dashboard_stats():
    """Check dashboard stats; data filtered by role (admin=all, TL=team clients, professionista=own)."""
    from corposostenibile.models import ClientCheckReadConfirmation
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta
    from sqlalchemy import func, case, and_

    try:
        now = datetime.utcnow()
        today = now.date()
        first_day_month = today.replace(day=1)
        prev_month_start = (first_day_month - relativedelta(months=1))
        prev_month_end = first_day_month - timedelta(days=1)
        accessible_query = get_accessible_clients_query()

        # ─── COUNTS BY TYPE ───────────────────────────────────────── #
        q_weekly = db.session.query(func.count(WeeklyCheckResponse.id))
        q_weekly = _apply_check_rbac_weekly(q_weekly)
        weekly_total = q_weekly.scalar() or 0

        q_dca = db.session.query(func.count(DCACheckResponse.id))
        q_dca = _apply_check_rbac_dca(q_dca)
        dca_total = q_dca.scalar() or 0

        q_minor = db.session.query(func.count(MinorCheckResponse.id))
        q_minor = _apply_check_rbac_minor(q_minor)
        minor_total = q_minor.scalar() or 0
        total_all = weekly_total + dca_total + minor_total

        # This month
        weekly_month = _apply_check_rbac_weekly(
            db.session.query(func.count(WeeklyCheckResponse.id)).filter(
                WeeklyCheckResponse.submit_date >= first_day_month
            )
        ).scalar() or 0
        dca_month = _apply_check_rbac_dca(
            db.session.query(func.count(DCACheckResponse.id)).filter(
                DCACheckResponse.submit_date >= first_day_month
            )
        ).scalar() or 0
        minor_month = _apply_check_rbac_minor(
            db.session.query(func.count(MinorCheckResponse.id)).filter(
                MinorCheckResponse.submit_date >= first_day_month
            )
        ).scalar() or 0
        total_month = weekly_month + dca_month + minor_month

        # Previous month
        weekly_prev = _apply_check_rbac_weekly(
            db.session.query(func.count(WeeklyCheckResponse.id)).filter(
                WeeklyCheckResponse.submit_date >= prev_month_start,
                WeeklyCheckResponse.submit_date <= datetime.combine(prev_month_end, datetime.max.time()),
            )
        ).scalar() or 0
        dca_prev = _apply_check_rbac_dca(
            db.session.query(func.count(DCACheckResponse.id)).filter(
                DCACheckResponse.submit_date >= prev_month_start,
                DCACheckResponse.submit_date <= datetime.combine(prev_month_end, datetime.max.time()),
            )
        ).scalar() or 0
        minor_prev = _apply_check_rbac_minor(
            db.session.query(func.count(MinorCheckResponse.id)).filter(
                MinorCheckResponse.submit_date >= prev_month_start,
                MinorCheckResponse.submit_date <= datetime.combine(prev_month_end, datetime.max.time()),
            )
        ).scalar() or 0
        total_prev = weekly_prev + dca_prev + minor_prev

        # ─── AVERAGE RATINGS (from weekly checks - last 30 days) ──── #
        thirty_days_ago = now - timedelta(days=30)
        avg_q = db.session.query(
            func.avg(WeeklyCheckResponse.nutritionist_rating).label('avg_nutrizionista'),
            func.avg(WeeklyCheckResponse.psychologist_rating).label('avg_psicologo'),
            func.avg(WeeklyCheckResponse.coach_rating).label('avg_coach'),
            func.avg(WeeklyCheckResponse.progress_rating).label('avg_progresso'),
        ).filter(WeeklyCheckResponse.submit_date >= thirty_days_ago)
        avg_q = _apply_check_rbac_weekly(avg_q)
        avg_result = avg_q.first()

        avg_nutrizionista = round(float(avg_result.avg_nutrizionista), 1) if avg_result.avg_nutrizionista else None
        avg_psicologo = round(float(avg_result.avg_psicologo), 1) if avg_result.avg_psicologo else None
        avg_coach = round(float(avg_result.avg_coach), 1) if avg_result.avg_coach else None
        avg_progresso = round(float(avg_result.avg_progresso), 1) if avg_result.avg_progresso else None
        all_avgs = [x for x in [avg_nutrizionista, avg_psicologo, avg_coach, avg_progresso] if x is not None]
        avg_quality = round(sum(all_avgs) / len(all_avgs), 1) if all_avgs else None

        # ─── RATINGS DISTRIBUTION (last 30 days) ─────────────────── #
        rating_cols = [
            WeeklyCheckResponse.nutritionist_rating,
            WeeklyCheckResponse.psychologist_rating,
            WeeklyCheckResponse.coach_rating,
            WeeklyCheckResponse.progress_rating,
        ]
        ratings_dist = {"low": 0, "medium": 0, "good": 0, "excellent": 0}
        for col in rating_cols:
            low = _apply_check_rbac_weekly(
                db.session.query(func.count(WeeklyCheckResponse.id)).filter(
                    WeeklyCheckResponse.submit_date >= thirty_days_ago,
                    col.isnot(None), col >= 1, col <= 4
                )
            ).scalar() or 0
            medium = _apply_check_rbac_weekly(
                db.session.query(func.count(WeeklyCheckResponse.id)).filter(
                    WeeklyCheckResponse.submit_date >= thirty_days_ago,
                    col.isnot(None), col >= 5, col <= 6
                )
            ).scalar() or 0
            good = _apply_check_rbac_weekly(
                db.session.query(func.count(WeeklyCheckResponse.id)).filter(
                    WeeklyCheckResponse.submit_date >= thirty_days_ago,
                    col.isnot(None), col >= 7, col <= 8
                )
            ).scalar() or 0
            excellent = _apply_check_rbac_weekly(
                db.session.query(func.count(WeeklyCheckResponse.id)).filter(
                    WeeklyCheckResponse.submit_date >= thirty_days_ago,
                    col.isnot(None), col >= 9
                )
            ).scalar() or 0
            ratings_dist["low"] += low
            ratings_dist["medium"] += medium
            ratings_dist["good"] += good
            ratings_dist["excellent"] += excellent

        # ─── MONTHLY TREND (last 6 months - weekly checks) ───────── #
        six_months_ago = (first_day_month - relativedelta(months=5)).replace(day=1)
        monthly_q = db.session.query(
            func.date_trunc("month", WeeklyCheckResponse.submit_date).label("month"),
            func.count(WeeklyCheckResponse.id).label("count"),
            func.avg(WeeklyCheckResponse.progress_rating).label("avg_progress"),
        ).filter(WeeklyCheckResponse.submit_date >= six_months_ago)
        monthly_q = _apply_check_rbac_weekly(monthly_q)
        monthly_rows = monthly_q.group_by("month").order_by("month").all()
        monthly_trend = [
            {
                "month": row.month.strftime("%Y-%m"),
                "count": row.count,
                "avgProgress": round(float(row.avg_progress), 1) if row.avg_progress else None,
            }
            for row in monthly_rows
        ]

        # ─── UNREAD CHECKS COUNT ─────────────────────────────────── #
        unread_count = 0
        try:
            read_ids = db.session.query(ClientCheckReadConfirmation.response_id).filter(
                ClientCheckReadConfirmation.user_id == current_user.id,
                ClientCheckReadConfirmation.response_type == 'weekly_check',
            ).subquery()
            unread_q = db.session.query(func.count(WeeklyCheckResponse.id)).filter(
                WeeklyCheckResponse.submit_date >= thirty_days_ago,
                ~WeeklyCheckResponse.id.in_(read_ids),
            )
            unread_count = _apply_check_rbac_weekly(unread_q).scalar() or 0
        except Exception:
            pass

        # ─── TOP PROFESSIONALS BY RATING ─────────────────────────── #
        top_nutrizionisti = []
        try:
            nutri_base = db.session.query(
                Cliente.nutrizionista_id,
                User.nome_cognome,
                func.avg(WeeklyCheckResponse.nutritionist_rating).label("avg_rating"),
                func.count(WeeklyCheckResponse.id).label("count"),
            ).join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id).join(
                Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id
            ).join(User, Cliente.nutrizionista_id == User.id).filter(
                WeeklyCheckResponse.submit_date >= thirty_days_ago,
                WeeklyCheckResponse.nutritionist_rating.isnot(None),
                Cliente.nutrizionista_id.isnot(None),
            )
            if accessible_query is not None:
                nutri_base = nutri_base.filter(Cliente.cliente_id.in_(accessible_query))
            nutri_rows = nutri_base.group_by(Cliente.nutrizionista_id, User.nome_cognome).having(
                func.count(WeeklyCheckResponse.id) >= 3
            ).order_by(func.avg(WeeklyCheckResponse.nutritionist_rating).desc()).limit(5).all()
            top_nutrizionisti = [
                {"name": r.nome_cognome, "avg": round(float(r.avg_rating), 1), "count": r.count}
                for r in nutri_rows
            ]
        except Exception:
            pass
        top_coaches = []
        try:
            coach_base = db.session.query(
                Cliente.coach_id,
                User.nome_cognome,
                func.avg(WeeklyCheckResponse.coach_rating).label("avg_rating"),
                func.count(WeeklyCheckResponse.id).label("count"),
            ).join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id).join(
                Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id
            ).join(User, Cliente.coach_id == User.id).filter(
                WeeklyCheckResponse.submit_date >= thirty_days_ago,
                WeeklyCheckResponse.coach_rating.isnot(None),
                Cliente.coach_id.isnot(None),
            )
            if accessible_query is not None:
                coach_base = coach_base.filter(Cliente.cliente_id.in_(accessible_query))
            coach_rows = coach_base.group_by(Cliente.coach_id, User.nome_cognome).having(
                func.count(WeeklyCheckResponse.id) >= 3
            ).order_by(func.avg(WeeklyCheckResponse.coach_rating).desc()).limit(5).all()
            top_coaches = [
                {"name": r.nome_cognome, "avg": round(float(r.avg_rating), 1), "count": r.count}
                for r in coach_rows
            ]
        except Exception:
            pass
        top_psicologi = []
        try:
            psico_base = db.session.query(
                Cliente.psicologa_id,
                User.nome_cognome,
                func.avg(WeeklyCheckResponse.psychologist_rating).label("avg_rating"),
                func.count(WeeklyCheckResponse.id).label("count"),
            ).join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id).join(
                Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id
            ).join(User, Cliente.psicologa_id == User.id).filter(
                WeeklyCheckResponse.submit_date >= thirty_days_ago,
                WeeklyCheckResponse.psychologist_rating.isnot(None),
                Cliente.psicologa_id.isnot(None),
            )
            if accessible_query is not None:
                psico_base = psico_base.filter(Cliente.cliente_id.in_(accessible_query))
            psico_rows = psico_base.group_by(Cliente.psicologa_id, User.nome_cognome).having(
                func.count(WeeklyCheckResponse.id) >= 3
            ).order_by(func.avg(WeeklyCheckResponse.psychologist_rating).desc()).limit(5).all()
            top_psicologi = [
                {"name": r.nome_cognome, "avg": round(float(r.avg_rating), 1), "count": r.count}
                for r in psico_rows
            ]
        except Exception:
            pass

        # ─── RECENT RESPONSES (last 10) ──────────────────────────── #
        recent_responses = []
        try:
            recent_q = db.session.query(
                WeeklyCheckResponse.id,
                WeeklyCheckResponse.submit_date,
                WeeklyCheckResponse.nutritionist_rating,
                WeeklyCheckResponse.coach_rating,
                WeeklyCheckResponse.psychologist_rating,
                WeeklyCheckResponse.progress_rating,
                Cliente.nome_cognome.label("cliente_nome"),
            ).join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id).join(
                Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id
            )
            if accessible_query is not None:
                recent_q = recent_q.filter(Cliente.cliente_id.in_(accessible_query))
            recent_rows = recent_q.order_by(WeeklyCheckResponse.submit_date.desc()).limit(15).all()
            for r in recent_rows:
                ratings = [x for x in [r.nutritionist_rating, r.coach_rating, r.psychologist_rating, r.progress_rating] if x is not None]
                avg = round(sum(ratings) / len(ratings), 1) if ratings else None
                recent_responses.append({
                    "id": r.id,
                    "cliente": r.cliente_nome,
                    "date": r.submit_date.strftime("%d/%m/%Y") if r.submit_date else None,
                    "dateIso": r.submit_date.isoformat() if r.submit_date else None,
                    "nutrizionista": r.nutritionist_rating,
                    "coach": r.coach_rating,
                    "psicologo": r.psychologist_rating,
                    "progresso": r.progress_rating,
                    "avg": avg,
                })
        except Exception:
            pass

        # ─── PHYSICAL METRICS AVERAGES (last 30 days) ────────────── #
        physical_avgs = {}
        try:
            phys_q = db.session.query(
                func.avg(WeeklyCheckResponse.digestion_rating).label('digestion'),
                func.avg(WeeklyCheckResponse.energy_rating).label('energy'),
                func.avg(WeeklyCheckResponse.strength_rating).label('strength'),
                func.avg(WeeklyCheckResponse.sleep_rating).label('sleep'),
                func.avg(WeeklyCheckResponse.mood_rating).label('mood'),
                func.avg(WeeklyCheckResponse.motivation_rating).label('motivation'),
            ).filter(WeeklyCheckResponse.submit_date >= thirty_days_ago)
            phys_q = _apply_check_rbac_weekly(phys_q)
            phys_result = phys_q.first()
            if phys_result:
                physical_avgs = {
                    "digestione": round(float(phys_result.digestion), 1) if phys_result.digestion else None,
                    "energia": round(float(phys_result.energy), 1) if phys_result.energy else None,
                    "forza": round(float(phys_result.strength), 1) if phys_result.strength else None,
                    "sonno": round(float(phys_result.sleep), 1) if phys_result.sleep else None,
                    "umore": round(float(phys_result.mood), 1) if phys_result.mood else None,
                    "motivazione": round(float(phys_result.motivation), 1) if phys_result.motivation else None,
                }
        except Exception:
            pass

        return jsonify({
            "kpi": {
                "totalAll": total_all,
                "totalMonth": total_month,
                "totalPrevMonth": total_prev,
                "avgQuality": avg_quality,
                "unreadCount": unread_count,
            },
            "ratings": {
                "nutrizionista": avg_nutrizionista,
                "coach": avg_coach,
                "psicologo": avg_psicologo,
                "progresso": avg_progresso,
            },
            "typeBreakdown": {
                "weekly": {"total": weekly_total, "month": weekly_month},
                "dca": {"total": dca_total, "month": dca_month},
                "minor": {"total": minor_total, "month": minor_month},
            },
            "ratingsDistribution": ratings_dist,
            "monthlyTrend": monthly_trend,
            "topProfessionals": {
                "nutrizionisti": top_nutrizionisti,
                "coaches": top_coaches,
                "psicologi": top_psicologi,
            },
            "recentResponses": recent_responses,
            "physicalMetrics": physical_avgs,
        })

    except Exception as e:
        current_app.logger.error(f"[CHECK_ADMIN_STATS] Error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

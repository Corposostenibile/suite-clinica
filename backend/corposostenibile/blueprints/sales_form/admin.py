"""
Admin views for Form Sales management
"""

from flask import redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user

from corposostenibile.extensions import db
from corposostenibile.models import (
    SalesFormConfig, SalesFormField, SalesFormLink,
    SalesLead, User, Department
)
from .decorators import admin_required
from . import sales_form_bp
from .services import FormConfigService, LinkService


@sales_form_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Dashboard admin per gestione Form Sales"""
    # Statistiche generali
    form = FormConfigService.get_system_form()
    stats = {
        'form_active': form.is_active,
        'total_fields': SalesFormField.query.filter_by(config_id=form.id).count(),
        'total_leads': SalesLead.query.count(),
        'converted_leads': SalesLead.query.filter_by(status='CONVERTED').count(),
        'total_links': SalesFormLink.query.count(),
        'active_links': SalesFormLink.query.filter_by(is_active=True).count()
    }

    # Top sales performers
    top_sales = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        db.func.count(SalesLead.id).label('lead_count'),
        db.func.sum(SalesLead.paid_amount).label('revenue')
    ).join(SalesLead, User.id == SalesLead.sales_user_id)\
     .group_by(User.id, User.first_name, User.last_name)\
     .order_by(db.func.sum(SalesLead.paid_amount).desc())\
     .limit(10).all()

    # Formatta i risultati con il nome completo
    top_sales = [
        {
            'name': f"{s.first_name} {s.last_name}",
            'lead_count': s.lead_count,
            'revenue': s.revenue
        }
        for s in top_sales
    ]

    abort(404)

@sales_form_bp.route('/admin/form')
@login_required
@admin_required
def admin_form_config():
    """Configurazione del form unico di sistema"""
    form = FormConfigService.get_system_form()
    fields = SalesFormField.query.filter_by(config_id=form.id)\
        .order_by(SalesFormField.position).all()

    abort(404)

@sales_form_bp.route('/admin/form/update', methods=['POST'])
@login_required
@admin_required
def admin_form_update():
    """Aggiorna configurazione del form unico"""
    data = {
        'description': request.form.get('description'),
        'is_active': request.form.get('is_active') == 'on',
        'success_message': request.form.get('success_message'),
        'redirect_url': request.form.get('redirect_url'),
        'notification_emails': request.form.getlist('notification_emails'),
        'primary_color': request.form.get('primary_color', '#007bff'),
        'logo_url': request.form.get('logo_url')
    }

    try:
        form = FormConfigService.update_form(data)
        flash('Configurazione form aggiornata con successo!', 'success')
    except Exception as e:
        flash(f'Errore nell\'aggiornamento: {str(e)}', 'error')

    return redirect(url_for('sales_form.admin_form_config'))


@sales_form_bp.route('/admin/form/builder')
@login_required
@admin_required
def admin_form_builder():
    """Form builder - interfaccia drag & drop per configurare campi"""
    form = FormConfigService.get_system_form()
    form_id = form.id
    fields_query = SalesFormField.query.filter_by(config_id=form_id)\
        .order_by(SalesFormField.position).all()

    # Converti i campi in dizionari per JSON serialization
    fields = [
        {
            'id': field.id,
            'field_name': field.field_name,
            'field_type': {'value': field.field_type.value if hasattr(field.field_type, 'value') else field.field_type},
            'field_label': field.field_label,
            'label': field.field_label,  # Alias per compatibilità template
            'name': field.field_name,  # Alias per compatibilità template
            'placeholder': field.placeholder or '',
            'help_text': field.help_text or '',
            'is_required': field.is_required,
            'required': field.is_required,  # Alias per compatibilità template
            'position': field.position,
            'validation_rules': field.validation_rules or {},
            'options': field.options or [],
            'section': field.section,
            'width': field.width or 12
        }
        for field in fields_query
    ]

    # Field types disponibili
    field_types = [
        {'value': 'text', 'label': 'Testo', 'icon': 'fas fa-font'},
        {'value': 'email', 'label': 'Email', 'icon': 'fas fa-envelope'},
        {'value': 'tel', 'label': 'Telefono', 'icon': 'fas fa-phone'},
        {'value': 'number', 'label': 'Numero', 'icon': 'fas fa-hashtag'},
        {'value': 'date', 'label': 'Data', 'icon': 'fas fa-calendar'},
        {'value': 'select', 'label': 'Select', 'icon': 'fas fa-list'},
        {'value': 'radio', 'label': 'Radio', 'icon': 'fas fa-dot-circle'},
        {'value': 'checkbox', 'label': 'Checkbox', 'icon': 'fas fa-check-square'},
        {'value': 'textarea', 'label': 'Testo lungo', 'icon': 'fas fa-align-left'},
        {'value': 'file', 'label': 'File upload', 'icon': 'fas fa-file-upload'},
        {'value': 'heading', 'label': 'Titolo', 'icon': 'fas fa-heading'},
        {'value': 'paragraph', 'label': 'Paragrafo', 'icon': 'fas fa-paragraph'},
        {'value': 'divider', 'label': 'Divisore', 'icon': 'fas fa-minus'}
    ]

    abort(404)

@sales_form_bp.route('/admin/form/preview')
@login_required
@admin_required
def admin_form_preview():
    """Anteprima del form unico"""
    form = FormConfigService.get_system_form()
    form_id = form.id
    fields = SalesFormField.query.filter_by(config_id=form_id)\
        .order_by(SalesFormField.position).all()

    # Simula un link per preview
    fake_link = type('obj', (object,), {
        'unique_code': 'PREVIEW',
        'user': current_user,
        'custom_message': 'Questo è un messaggio di esempio del sales'
    })

    # Organizza campi per sezioni
    sections = {}
    for field in fields:
        section_name = field.section or 'Informazioni'
        if section_name not in sections:
            sections[section_name] = {
                'name': section_name,
                'description': field.section_description,
                'fields': []
            }
        sections[section_name]['fields'].append(field)

    abort(404)

@sales_form_bp.route('/admin/links')
@login_required
@admin_required
def admin_links():
    """Gestione link univoci"""
    # Carica tutti i link con info utente
    links = db.session.query(
        SalesFormLink,
        User
    ).join(User, SalesFormLink.user_id == User.id)\
     .order_by(User.first_name, User.last_name).all()

    # Carica utenti sales (dipartimenti 5 e 18) senza link
    sales_users = User.query.join(Department, User.department_id == Department.id)\
        .filter(Department.id.in_([5, 18]))\
        .filter(User.is_active == True).all()

    # Trova chi non ha ancora un link
    users_with_links = set(link[0].user_id for link in links)  # link[0] è SalesFormLink
    users_without_links = [u for u in sales_users if u.id not in users_with_links]

    abort(404)

@sales_form_bp.route('/admin/links/generate', methods=['POST'])
@login_required
@admin_required
def admin_generate_link():
    """Genera link per utente"""
    user_id = request.form.get('user_id', type=int)

    if not user_id:
        flash('Seleziona un utente', 'error')
        return redirect(url_for('sales_form.admin_links'))

    try:
        link = LinkService.create_or_get_link(user_id)
        user = User.query.get(user_id)
        flash(f'Link generato per {user.first_name} {user.last_name}: {link.unique_code}', 'success')
    except Exception as e:
        flash(f'Errore: {str(e)}', 'error')

    return redirect(url_for('sales_form.admin_links'))


@sales_form_bp.route('/admin/links/bulk-generate', methods=['POST'])
@login_required
@admin_required
def admin_bulk_generate_links():
    """Genera link per tutti i sales senza link"""

    # Trova tutti i sales senza link
    sales_users = User.query.join(Department, User.department_id == Department.id)\
        .filter(Department.id.in_([5, 18]))\
        .filter(User.is_active == True).all()

    existing_links = SalesFormLink.query.all()
    users_with_links = set(link.user_id for link in existing_links)

    user_ids_without_links = [u.id for u in sales_users if u.id not in users_with_links]
    count = LinkService.bulk_create_links(user_ids_without_links)

    flash(f'{count} link generati con successo', 'success')
    return redirect(url_for('sales_form.admin_links'))


@sales_form_bp.route('/admin/leads')
@login_required
@admin_required
def admin_leads():
    """Vista admin di tutte le lead"""
    # Filtri
    status = request.args.get('status')
    sales_user_id = request.args.get('sales_user_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search = request.args.get('search')

    # Query base - ESCLUDI ARCHIVIATE (archiviazione = solo pulizia visiva)
    query = SalesLead.query.filter(SalesLead.archived_at.is_(None))

    # Applica filtri
    if status:
        query = query.filter_by(status=status)
    if sales_user_id:
        query = query.filter_by(sales_user_id=sales_user_id)
    if date_from:
        from datetime import datetime
        query = query.filter(SalesLead.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        from datetime import datetime
        query = query.filter(SalesLead.created_at <= datetime.strptime(date_to, '%Y-%m-%d'))
    if search:
        search_term = f'%{search}%'
        query = query.filter(db.or_(
            SalesLead.first_name.ilike(search_term),
            SalesLead.last_name.ilike(search_term),
            SalesLead.email.ilike(search_term),
            SalesLead.phone.ilike(search_term)
        ))

    # Paginazione
    page = request.args.get('page', 1, type=int)
    leads = query.order_by(SalesLead.created_at.desc())\
        .paginate(page=page, per_page=50, error_out=False)

    # Carica sales users per filtro
    sales_users = User.query.join(Department, User.department_id == Department.id)\
        .filter(Department.id.in_([5, 18])).all()

    abort(404)

@sales_form_bp.route('/admin/stats')
@login_required
@admin_required
def admin_stats():
    """Statistiche e report completi"""
    from datetime import datetime, timedelta

    # Periodo corrente
    today = datetime.now()
    month_start = today.replace(day=1)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Metriche generali
    total_leads = SalesLead.query.count()
    total_converted = SalesLead.query.filter_by(status='CONVERTED').count()
    total_revenue = db.session.query(db.func.sum(SalesLead.paid_amount)).scalar() or 0

    # Metriche del mese
    month_leads = SalesLead.query.filter(SalesLead.created_at >= month_start).count()
    month_converted = SalesLead.query.filter(
        SalesLead.created_at >= month_start,
        SalesLead.status == 'CONVERTED'
    ).count()
    month_revenue = db.session.query(db.func.sum(SalesLead.paid_amount))\
        .filter(SalesLead.created_at >= month_start).scalar() or 0

    # Confronto mese precedente
    prev_month_leads = SalesLead.query.filter(
        SalesLead.created_at >= prev_month_start,
        SalesLead.created_at < month_start
    ).count()

    # Performance per sales
    sales_performance = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        db.func.count(SalesLead.id).label('total_leads'),
        db.func.sum(db.case(
            [(SalesLead.status == 'CONVERTED', 1)],
            else_=0
        )).label('converted'),
        db.func.sum(SalesLead.paid_amount).label('revenue')
    ).join(SalesLead, User.id == SalesLead.sales_user_id)\
     .filter(SalesLead.created_at >= month_start)\
     .group_by(User.id, User.first_name, User.last_name)\
     .order_by(db.func.sum(SalesLead.paid_amount).desc()).all()

    # Formatta i risultati con il nome completo
    sales_performance = [
        {
            'id': s.id,
            'name': f"{s.first_name} {s.last_name}",
            'total_leads': s.total_leads,
            'converted': s.converted,
            'revenue': s.revenue
        }
        for s in sales_performance
    ]

    # Funnel conversion
    funnel = {
        'new': SalesLead.query.filter_by(status='NEW').count(),
        'contacted': SalesLead.query.filter_by(status='CONTACTED').count(),
        'qualified': SalesLead.query.filter_by(status='QUALIFIED').count(),
        'payment': SalesLead.query.filter(SalesLead.status.in_(['PARTIAL_PAYMENT', 'FULL_PAYMENT'])).count(),
        'converted': total_converted
    }

    abort(404)

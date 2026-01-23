"""
API endpoints per Form Sales system
"""

from datetime import datetime
from flask import jsonify, request, abort
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func

from corposostenibile.extensions import db
from corposostenibile.models import (
    SalesFormConfig, SalesFormField, SalesFormLink,
    SalesLead, LeadPayment, User, Package,
    LeadStatusEnum, FormFieldTypeEnum
)
from .decorators import admin_required, department_required
from . import sales_form_bp
from .services import FormConfigService, LinkService, LeadService


# ===================== ADMIN FORM BUILDER API =====================

@sales_form_bp.route('/api/admin/forms', methods=['GET'])
@login_required
@admin_required
def api_get_forms():
    """Lista tutti i form configurati"""
    forms = SalesFormConfig.query.all()
    return jsonify({
        'success': True,
        'data': [
            {
                'id': f.id,
                'name': f.name,
                'description': f.description,
                'is_active': f.is_active,
                'is_default': f.is_default,
                'field_count': f.field_count,
                'submission_count': f.submission_count,
                'created_at': f.created_at.isoformat() if f.created_at else None
            }
            for f in forms
        ]
    })


@sales_form_bp.route('/api/admin/forms', methods=['POST'])
@login_required
@admin_required
def api_create_form():
    """Crea un nuovo form"""
    data = request.get_json()

    if not data.get('name'):
        return jsonify({'success': False, 'error': 'Nome richiesto'}), 400

    try:
        form = FormConfigService.create_form(data, current_user.id)
        return jsonify({
            'success': True,
            'message': 'Form creato con successo',
            'form_id': form.id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@sales_form_bp.route('/api/admin/forms/<int:form_id>', methods=['PUT'])
@login_required
@admin_required
def api_update_form(form_id):
    """Modifica form esistente"""
    form = SalesFormConfig.query.get_or_404(form_id)
    data = request.get_json()

    # Aggiorna campi
    for key in ['name', 'description', 'is_active', 'is_default',
                'success_message', 'redirect_url', 'notification_emails',
                'primary_color', 'logo_url', 'custom_css']:
        if key in data:
            setattr(form, key, data[key])

    # Se è default, rimuovi default da altri
    if data.get('is_default'):
        SalesFormConfig.query.filter(
            SalesFormConfig.id != form_id
        ).update({'is_default': False})

    db.session.commit()

    return jsonify({'success': True, 'message': 'Form aggiornato'})


@sales_form_bp.route('/api/admin/forms/<int:form_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_form(form_id):
    """Elimina form (soft delete se ha submissions)"""
    form = SalesFormConfig.query.get_or_404(form_id)

    if form.submission_count > 0:
        # Soft delete
        form.is_active = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'Form disattivato (ha submissions)'})
    else:
        # Hard delete
        db.session.delete(form)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Form eliminato'})


@sales_form_bp.route('/api/admin/form/save', methods=['POST'])
@login_required
@admin_required
def api_save_system_form():
    """Salva il form unico di sistema"""
    data = request.get_json()

    # Ottieni il form unico di sistema
    form = FormConfigService.get_system_form()

    # Aggiorna configurazione
    if 'description' in data:
        form.description = data['description']
    if 'is_active' in data:
        form.is_active = data['is_active']

    db.session.commit()

    # Gestisci i campi se forniti
    if 'fields' in data:
        # Elimina campi esistenti
        SalesFormField.query.filter_by(config_id=form.id).delete()

        # Aggiungi nuovi campi
        for field_data in data['fields']:
            # Estrai il tipo di campo
            field_type = field_data.get('field_type')
            if isinstance(field_type, dict):
                field_type = field_type.get('value', 'text')
            elif not field_type:
                field_type = 'text'

            field = SalesFormField(
                config_id=form.id,
                field_name=field_data.get('field_name') or field_data.get('name', ''),
                field_type=field_type,
                field_label=field_data.get('field_label') or field_data.get('label', ''),
                placeholder=field_data.get('placeholder', ''),
                help_text=field_data.get('help_text', ''),
                is_required=field_data.get('is_required') or field_data.get('required', False),
                position=field_data.get('position', 0),
                width=field_data.get('width', 12),
                validation_rules=field_data.get('validation_rules', {}),
                options=field_data.get('options', [])
            )
            db.session.add(field)

        db.session.commit()

    return jsonify({'success': True, 'message': 'Form salvato con successo'})


# ===================== FIELD MANAGEMENT API =====================

@sales_form_bp.route('/api/admin/forms/<int:form_id>/fields', methods=['GET'])
@login_required
@admin_required
def api_get_fields(form_id):
    """Lista campi di un form"""
    form = SalesFormConfig.query.get_or_404(form_id)
    fields = SalesFormField.query.filter_by(config_id=form_id)\
        .order_by(SalesFormField.position).all()

    return jsonify({
        'success': True,
        'data': [
            {
                'id': f.id,
                'field_name': f.field_name,
                'field_type': f.field_type,
                'field_label': f.field_label,
                'placeholder': f.placeholder,
                'help_text': f.help_text,
                'is_required': f.is_required,
                'position': f.position,
                'section': f.section,
                'validation_rules': f.validation_rules,
                'options': f.options,
                'conditional_logic': f.conditional_logic
            }
            for f in fields
        ]
    })


@sales_form_bp.route('/api/admin/forms/<int:form_id>/fields', methods=['POST'])
@login_required
@admin_required
def api_add_field(form_id):
    """Aggiunge campo al form"""
    form = SalesFormConfig.query.get_or_404(form_id)
    data = request.get_json()

    # Validazione
    if not data.get('field_name') or not data.get('field_type') or not data.get('field_label'):
        return jsonify({'success': False, 'error': 'Dati campo mancanti'}), 400

    # Verifica tipo campo valido
    if data['field_type'] not in [e.value for e in FormFieldTypeEnum]:
        return jsonify({'success': False, 'error': 'Tipo campo non valido'}), 400

    try:
        field = FormConfigService.add_field(form_id, data)
        return jsonify({
            'success': True,
            'message': 'Campo aggiunto',
            'field_id': field.id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@sales_form_bp.route('/api/admin/fields/<int:field_id>', methods=['PUT'])
@login_required
@admin_required
def api_update_field(field_id):
    """Modifica campo esistente"""
    field = SalesFormField.query.get_or_404(field_id)
    data = request.get_json()

    # Aggiorna campi modificabili
    for key in ['field_label', 'placeholder', 'help_text', 'default_value',
                'is_required', 'validation_rules', 'options', 'width',
                'section', 'section_description', 'conditional_logic']:
        if key in data:
            setattr(field, key, data[key])

    db.session.commit()

    return jsonify({'success': True, 'message': 'Campo aggiornato'})


@sales_form_bp.route('/api/admin/fields/<int:field_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_field(field_id):
    """Elimina campo dal form"""
    field = SalesFormField.query.get_or_404(field_id)
    db.session.delete(field)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Campo eliminato'})


@sales_form_bp.route('/api/admin/fields/reorder', methods=['POST'])
@login_required
@admin_required
def api_reorder_fields():
    """Riordina campi"""
    data = request.get_json()
    field_order = data.get('field_order', [])

    if not field_order:
        return jsonify({'success': False, 'error': 'Ordine campi mancante'}), 400

    # Aggiorna posizioni
    for item in field_order:
        SalesFormField.query.filter_by(id=item['id'])\
            .update({'position': item['position']})

    db.session.commit()

    return jsonify({'success': True, 'message': 'Campi riordinati'})


# ===================== LINK MANAGEMENT API =====================

@sales_form_bp.route('/api/admin/links', methods=['GET'])
@login_required
@admin_required
def api_get_all_links():
    """Lista tutti i link generati"""
    links = db.session.query(
        SalesFormLink,
        User.name.label('user_name'),
        SalesFormConfig.name.label('form_name')
    ).join(User, SalesFormLink.user_id == User.id)\
     .outerjoin(SalesFormConfig, SalesFormLink.config_id == SalesFormConfig.id)\
     .all()

    return jsonify({
        'success': True,
        'data': [
            {
                'id': link.SalesFormLink.id,
                'user_id': link.SalesFormLink.user_id,
                'user_name': link.user_name,
                'form_id': link.SalesFormLink.config_id,
                'form_name': link.form_name,
                'unique_code': link.SalesFormLink.unique_code,
                'full_url': link.SalesFormLink.full_url,
                'is_active': link.SalesFormLink.is_active,
                'click_count': link.SalesFormLink.click_count,
                'submission_count': link.SalesFormLink.submission_count,
                'conversion_rate': (link.SalesFormLink.submission_count / link.SalesFormLink.click_count * 100)
                                  if link.SalesFormLink.click_count > 0 else 0,
                'created_at': link.SalesFormLink.created_at.isoformat() if link.SalesFormLink.created_at else None
            }
            for link in links
        ]
    })


@sales_form_bp.route('/api/admin/links/generate', methods=['POST'])
@login_required
@admin_required
def api_generate_links():
    """Genera link per uno o più utenti"""
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    form_id = data.get('form_id')

    if not user_ids:
        return jsonify({'success': False, 'error': 'Nessun utente selezionato'}), 400

    generated = []
    for user_id in user_ids:
        link = LinkService.create_or_update_link(user_id, form_id)
        generated.append({
            'user_id': user_id,
            'unique_code': link.unique_code,
            'url': link.full_url
        })

    return jsonify({
        'success': True,
        'message': f'{len(generated)} link generati',
        'links': generated
    })


@sales_form_bp.route('/api/admin/links/<int:link_id>/toggle', methods=['POST'])
@login_required
@admin_required
def api_toggle_link(link_id):
    """Attiva/disattiva un link"""
    link = SalesFormLink.query.get_or_404(link_id)
    link.is_active = not link.is_active
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Link {"attivato" if link.is_active else "disattivato"}',
        'is_active': link.is_active
    })


# ===================== SALES LEAD API =====================

@sales_form_bp.route('/api/leads/create-manual', methods=['POST'])
@login_required
@department_required([5, 18])
def api_create_lead_manual():
    """Crea lead manualmente (Sales)"""
    data = request.get_json()

    # Validazione base
    if not data.get('first_name') or not data.get('last_name') or not data.get('email'):
        return jsonify({
            'success': False,
            'error': 'Nome, cognome ed email sono obbligatori'
        }), 400

    # Per i sales, la lead viene assegnata automaticamente a loro
    lead_data = {
        'first_name': data['first_name'],
        'last_name': data['last_name'],
        'email': data['email'],
        'phone': data.get('phone'),
        'sales_user_id': current_user.id  # Auto-assegnazione
    }

    try:
        lead = LeadService.create_lead_manually(lead_data, current_user.id)
        return jsonify({
            'success': True,
            'message': f'Lead {lead.full_name} creata con successo',
            'lead': {
                'id': lead.id,
                'unique_code': lead.unique_code,
                'full_name': lead.full_name,
                'email': lead.email,
                'phone': lead.phone,
                'status': lead.status
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore durante la creazione: {str(e)}'
        }), 500


@sales_form_bp.route('/api/admin/leads/create-manual', methods=['POST'])
@login_required
@admin_required
def api_admin_create_lead_manual():
    """Crea lead manualmente con assegnazione custom (Admin)"""
    data = request.get_json()

    # Validazione base
    if not data.get('first_name') or not data.get('last_name') or not data.get('email'):
        return jsonify({
            'success': False,
            'error': 'Nome, cognome ed email sono obbligatori'
        }), 400

    # Admin può assegnare a qualsiasi sales (o nessuno)
    lead_data = {
        'first_name': data['first_name'],
        'last_name': data['last_name'],
        'email': data['email'],
        'phone': data.get('phone'),
        'sales_user_id': data.get('sales_user_id')  # Opzionale per admin
    }

    try:
        lead = LeadService.create_lead_manually(lead_data, current_user.id)

        sales_name = "Non assegnata"
        if lead.sales_user_id:
            sales_user = User.query.get(lead.sales_user_id)
            sales_name = f"{sales_user.first_name} {sales_user.last_name}" if sales_user else "Sconosciuto"

        return jsonify({
            'success': True,
            'message': f'Lead {lead.full_name} creata e assegnata a {sales_name}',
            'lead': {
                'id': lead.id,
                'unique_code': lead.unique_code,
                'full_name': lead.full_name,
                'email': lead.email,
                'phone': lead.phone,
                'status': lead.status,
                'sales_user_id': lead.sales_user_id,
                'sales_name': sales_name
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore durante la creazione: {str(e)}'
        }), 500


@sales_form_bp.route('/api/leads', methods=['GET'])
@login_required
@department_required([5, 18])
def api_get_leads():
    """API per ottenere le proprie lead con filtri"""
    # Parametri query
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    search = request.args.get('search')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Query base
    query = SalesLead.query.filter_by(sales_user_id=current_user.id)

    # Applica filtri
    if status:
        query = query.filter_by(status=status)

    if search:
        search_term = f'%{search}%'
        query = query.filter(or_(
            SalesLead.first_name.ilike(search_term),
            SalesLead.last_name.ilike(search_term),
            SalesLead.email.ilike(search_term)
        ))

    if date_from:
        query = query.filter(SalesLead.created_at >= datetime.fromisoformat(date_from))

    if date_to:
        query = query.filter(SalesLead.created_at <= datetime.fromisoformat(date_to))

    # Paginazione
    leads = query.order_by(SalesLead.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    # Statistiche
    stats = {
        'total': query.count(),
        'new': query.filter_by(status=LeadStatusEnum.NEW).count(),
        'qualified': query.filter_by(status=LeadStatusEnum.QUALIFIED).count(),
        'converted': query.filter_by(status=LeadStatusEnum.CONVERTED).count()
    }

    return jsonify({
        'success': True,
        'data': [
            {
                'id': lead.id,
                'unique_code': lead.unique_code,
                'full_name': lead.full_name,
                'email': lead.email,
                'phone': lead.phone,
                'status': lead.status,
                'package_name': lead.package.name if lead.package else None,
                'total_amount': float(lead.final_amount) if lead.final_amount else 0,
                'paid_amount': float(lead.paid_amount) if lead.paid_amount else 0,
                'payment_status': lead.payment_status,
                'lead_score': lead.lead_score,
                'priority': lead.priority,
                'created_at': lead.created_at.isoformat() if lead.created_at else None,
                'last_contact': lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
                'next_followup': lead.next_followup_at.isoformat() if lead.next_followup_at else None
            }
            for lead in leads.items
        ],
        'pagination': {
            'total': leads.total,
            'page': leads.page,
            'per_page': leads.per_page,
            'total_pages': leads.pages,
            'has_next': leads.has_next,
            'has_prev': leads.has_prev
        },
        'stats': stats
    })


@sales_form_bp.route('/api/leads/<int:lead_id>', methods=['GET'])
@login_required
@department_required([5, 18])
def api_get_lead_detail(lead_id):
    """Dettaglio completo di una lead"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        abort(403)

    # Carica relazioni
    payments = LeadPayment.query.filter_by(lead_id=lead_id)\
        .order_by(LeadPayment.payment_date.desc()).all()

    activities = lead.activity_logs.order_by('created_at desc').limit(20).all()

    return jsonify({
        'success': True,
        'data': {
            'id': lead.id,
            'basic_info': {
                'first_name': lead.first_name,
                'last_name': lead.last_name,
                'email': lead.email,
                'phone': lead.phone,
                'birth_date': lead.birth_date.isoformat() if lead.birth_date else None,
                'fiscal_code': lead.fiscal_code
            },
            'form_responses': lead.form_responses,
            'sales_info': {
                'status': lead.status,
                'client_story': lead.client_story,
                'package': {
                    'id': lead.package.id,
                    'name': lead.package.name,
                    'price': float(lead.package.price)
                } if lead.package else None,
                'pricing': {
                    'total_amount': float(lead.total_amount) if lead.total_amount else 0,
                    'discount_amount': float(lead.discount_amount) if lead.discount_amount else 0,
                    'final_amount': float(lead.final_amount) if lead.final_amount else 0,
                    'paid_amount': float(lead.paid_amount) if lead.paid_amount else 0,
                    'remaining': float(lead.remaining_amount)
                }
            },
            'payments': [
                {
                    'id': p.id,
                    'amount': float(p.amount),
                    'type': p.payment_type,
                    'method': p.payment_method,
                    'date': p.payment_date.isoformat(),
                    'verified': p.is_verified
                }
                for p in payments
            ],
            'activities': [
                {
                    'type': a.activity_type,
                    'description': a.description,
                    'date': a.created_at.isoformat() if a.created_at else None,
                    'user': a.user.name if a.user else 'Sistema'
                }
                for a in activities
            ]
        }
    })


@sales_form_bp.route('/api/leads/<int:lead_id>/generate-completion-link', methods=['POST'])
@login_required
@department_required([5, 18])
def api_generate_completion_link(lead_id):
    """Genera tutti e 3 i link di completamento form (check 1, 2, 3) per lead manuale"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Accesso negato'}), 403

    # Verifica che la lead sia stata inserita manualmente
    if not (lead.form_responses and lead.form_responses.get('_manual_entry')):
        return jsonify({
            'success': False,
            'error': 'Questa lead ha già compilato il form'
        }), 400

    try:
        # Crea tutti e 3 i link (o recupera quelli esistenti)
        links = LinkService.create_all_links_for_lead(
            lead_id=lead_id,
            sales_user_id=current_user.id
        )

        # Prepara dati per la risposta
        from flask import url_for
        links_data = []
        for link in links:
            form_url = url_for('welcome_form', unique_code=link.unique_code, _external=True)
            links_data.append({
                'check_number': link.check_number,
                'link_id': link.id,
                'unique_code': link.unique_code,
                'form_url': form_url,
                'custom_message': link.custom_message,
                'created_at': link.created_at.isoformat() if link.created_at else None,
                'click_count': link.click_count,
                'submission_count': link.submission_count
            })

        return jsonify({
            'success': True,
            'data': {
                'links': links_data,
                'total': len(links_data)
            }
        })

    except Exception as e:
        import traceback
        from flask import current_app
        current_app.logger.error(f"[COMPLETION-LINK-ERROR] {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Errore nella generazione del link'
        }), 500


@sales_form_bp.route('/api/my-link', methods=['GET'])
@login_required
@department_required([5, 18])
def api_get_my_link():
    """Ottiene il link personale del sales"""
    link = LinkService.create_or_update_link(current_user.id)

    return jsonify({
        'success': True,
        'data': {
            'unique_code': link.unique_code,
            'full_url': link.full_url,
            'short_url': link.short_url,
            'stats': {
                'clicks': link.click_count,
                'submissions': link.submission_count,
                'conversion_rate': (link.submission_count / link.click_count * 100)
                                  if link.click_count > 0 else 0
            }
        }
    })


@sales_form_bp.route('/api/stats/my-performance', methods=['GET'])
@login_required
@department_required([5, 18])
def api_my_performance():
    """Statistiche performance personale"""
    period = request.args.get('period', 'current_month')

    # Calcola date range
    if period == 'current_month':
        date_from = datetime.now().replace(day=1)
        date_to = None
    elif period == 'last_month':
        date_from = (datetime.now().replace(day=1) - timedelta(days=1)).replace(day=1)
        date_to = datetime.now().replace(day=1)
    else:
        date_from = None
        date_to = None

    # Query statistiche
    query = SalesLead.query.filter_by(sales_user_id=current_user.id)

    if date_from:
        query = query.filter(SalesLead.created_at >= date_from)
    if date_to:
        query = query.filter(SalesLead.created_at < date_to)

    # Calcola metriche
    total = query.count()
    qualified = query.filter_by(status=LeadStatusEnum.QUALIFIED).count()
    converted = query.filter_by(status=LeadStatusEnum.CONVERTED).count()
    lost = query.filter_by(status=LeadStatusEnum.LOST).count()

    revenue = db.session.query(func.sum(SalesLead.paid_amount))\
        .filter_by(sales_user_id=current_user.id).scalar() or 0

    return jsonify({
        'success': True,
        'data': {
            'period': period,
            'leads': {
                'total': total,
                'new': query.filter_by(status=LeadStatusEnum.NEW).count(),
                'qualified': qualified,
                'converted': converted,
                'lost': lost
            },
            'revenue': {
                'total': float(revenue),
                'average_deal': float(revenue / converted) if converted > 0 else 0
            },
            'conversion': {
                'lead_to_qualified': (qualified / total * 100) if total > 0 else 0,
                'qualified_to_converted': (converted / qualified * 100) if qualified > 0 else 0,
                'overall': (converted / total * 100) if total > 0 else 0
            }
        }
    })


@sales_form_bp.route('/api/lead/<int:lead_id>/details', methods=['GET'])
@login_required
def api_lead_details(lead_id):
    """Ottiene dettagli completi di una lead per modali"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Carica professionisti con i link calendario dalle note AI
    nutritionists = User.query.filter_by(department_id=2, is_active=True).order_by(User.first_name, User.last_name).all()
    coaches = User.query.filter_by(department_id=3, is_active=True).order_by(User.first_name, User.last_name).all()
    psychologists = User.query.filter_by(department_id=4, is_active=True).order_by(User.first_name, User.last_name).all()

    # Helper per estrarre il link calendario dalle note AI
    def get_calendar_link(user):
        if user.assignment_ai_notes and isinstance(user.assignment_ai_notes, dict):
            return user.assignment_ai_notes.get('link_calendario', '')
        return ''

    return jsonify({
        'success': True,
        'lead': {
            'id': lead.id,
            'full_name': f"{lead.first_name} {lead.last_name}",
            'email': lead.email,
            'phone': lead.phone,
            'package_name': lead.package.name if lead.package else None,
            'sales_user_name': f"{lead.sales_user.first_name} {lead.sales_user.last_name}" if lead.sales_user else None,
            'final_amount': float(lead.final_amount) if lead.final_amount else 0,
            'paid_amount': float(lead.paid_amount) if lead.paid_amount else 0,
            'client_story': lead.client_story,
            'payments': [
                {
                    'id': p.id,
                    'amount': float(p.amount),
                    'date': p.payment_date.strftime('%d/%m/%Y') if p.payment_date else '',
                    'method': p.payment_method,
                    'notes': p.notes,
                    'receipt_url': p.receipt_url
                }
                for p in lead.payments
            ] if hasattr(lead, 'payments') else []
        },
        'professionals': {
            'nutritionists': {
                str(n.id): {
                    'id': n.id,
                    'name': n.name,
                    'calendar_link': get_calendar_link(n)
                }
                for n in nutritionists
            },
            'coaches': {
                str(c.id): {
                    'id': c.id,
                    'name': c.name,
                    'calendar_link': get_calendar_link(c)
                }
                for c in coaches
            },
            'psychologists': {
                str(p.id): {
                    'id': p.id,
                    'name': p.name,
                    'calendar_link': get_calendar_link(p)
                }
                for p in psychologists
            }
        }
    })


@sales_form_bp.route('/api/lead/<int:lead_id>/story', methods=['GET'])
@login_required
def api_lead_story(lead_id):
    """Ottiene la storia cliente e le risposte del form di una lead"""
    lead = SalesLead.query.get_or_404(lead_id)

    return jsonify({
        'success': True,
        'lead': {
            'id': lead.id,
            'full_name': f"{lead.first_name} {lead.last_name}",
            'email': lead.email,
            'phone': lead.phone,
            'client_story': lead.client_story,
            'form_responses': lead.form_responses or {},
            'sales_user_name': f"{lead.sales_user.first_name} {lead.sales_user.last_name}" if lead.sales_user else None
        }
    })


# ===================== AI PROFESSIONAL MATCHING =====================

@sales_form_bp.route('/api/leads/<int:lead_id>/ai-suggest-professional', methods=['POST'])
@login_required
@department_required([13])  # Solo Health Manager
def ai_suggest_professional(lead_id):
    """
    Suggerimento AI per assegnazione professionista migliore

    Usa SuiteMind AI per analizzare:
    - Storia completa della lead
    - Note AI di tutti i professionisti del dipartimento
    - Fa matching intelligente e suggerisce il migliore

    POST data:
    {
        "department_id": 2,  # 2=Nutrizione, 3=Coach, 4=Psicologia
        "session_id": "user_123"  # opzionale
    }

    Response:
    {
        "success": true,
        "suggestion": {
            "professional_id": 45,
            "professional_name": "Dr. Mario Rossi",
            "score": 95,
            "reasoning": "Il professionista migliore perché..."
        }
    }
    """
    from .services import AIMatchingService

    lead = SalesLead.query.get_or_404(lead_id)

    # Check accesso
    has_access = (
        current_user.is_admin or
        current_user.department_id == 13  # Health Manager
    )

    if not has_access:
        return jsonify({
            'success': False,
            'error': 'Accesso negato'
        }), 403

    data = request.get_json()
    department_id = data.get('department_id')
    session_id = data.get('session_id', f'hm_{current_user.id}')

    # Validazione department_id
    ALLOWED_DEPARTMENTS = {
        2: 'Nutrizione',
        3: 'Coach',
        4: 'Psicologia',
        24: 'Nutrizione 2'
    }

    if not department_id or department_id not in ALLOWED_DEPARTMENTS:
        return jsonify({
            'success': False,
            'error': f'department_id deve essere uno tra: {list(ALLOWED_DEPARTMENTS.keys())}'
        }), 400

    try:
        # Chiama service per AI matching
        suggestion = AIMatchingService.suggest_professional(
            lead_id=lead_id,
            department_id=department_id,
            session_id=session_id
        )

        return jsonify({
            'success': True,
            'suggestion': suggestion,
            'department_name': ALLOWED_DEPARTMENTS[department_id]
        })

    except Exception as e:
        current_app.logger.error(f"[AI-SUGGEST] Errore: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
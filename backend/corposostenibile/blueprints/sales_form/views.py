"""
Views principali per Sales Form Blueprint
"""

from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func

from corposostenibile.extensions import db
from corposostenibile.models import (
    SalesLead, SalesFormLink, LeadPayment, LeadActivityLog,
    LeadStatusEnum, LeadOriginEnum, User, Package
)
from .decorators import department_required, admin_required, sales_required
from . import sales_form_bp
from .services import LeadService, LinkService, FinanceService, HealthManagerService


# ===================== DASHBOARD SALES =====================

@sales_form_bp.route('/')
@login_required
@sales_required  # Sales (dept 5, 18) o utenti con SalesFormLink attivo
def dashboard():
    """Dashboard principale sales con le proprie lead"""
    # Ottieni il link personale del sales (se esiste)
    my_link = SalesFormLink.query.filter_by(user_id=current_user.id).first()

    # Filtri dalla query string
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search = request.args.get('search')

    # Query lead del sales corrente - ESCLUDI ARCHIVIATE (solo per la lista)
    query = SalesLead.query.filter(
        SalesLead.sales_user_id == current_user.id,
        SalesLead.archived_at.is_(None)
    )

    if date_from:
        query = query.filter(SalesLead.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))

    if date_to:
        query = query.filter(SalesLead.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))

    if search:
        search_term = f'%{search}%'
        query = query.filter(or_(
            SalesLead.first_name.ilike(search_term),
            SalesLead.last_name.ilike(search_term),
            SalesLead.email.ilike(search_term),
            SalesLead.phone.ilike(search_term)
        ))

    # Paginazione
    page = request.args.get('page', 1, type=int)
    leads = query.order_by(SalesLead.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    # Statistiche KPI - INCLUDI TUTTE LE LEAD (anche archiviate)
    # L'archiviazione è solo per pulizia visiva, non per escludere dai KPI
    kpi_query = SalesLead.query.filter(
        SalesLead.sales_user_id == current_user.id
    )

    if date_from:
        kpi_query = kpi_query.filter(SalesLead.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))

    if date_to:
        kpi_query = kpi_query.filter(SalesLead.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))

    if search:
        search_term = f'%{search}%'
        kpi_query = kpi_query.filter(or_(
            SalesLead.first_name.ilike(search_term),
            SalesLead.last_name.ilike(search_term),
            SalesLead.email.ilike(search_term),
            SalesLead.phone.ilike(search_term)
        ))

    all_leads_for_kpi = kpi_query.all()

    stats = {
        'total_leads': len(all_leads_for_kpi),
        'expected_revenue': sum(lead.final_amount or 0 for lead in all_leads_for_kpi),
        'paid_amount': sum(lead.paid_amount or 0 for lead in all_leads_for_kpi),
        'approved_amount': sum(
            lead.paid_amount or 0 for lead in all_leads_for_kpi
            if lead.finance_approved == True
        )
    }

    # Conta per stato (sui dati KPI - tutte le lead)
    status_counts = {}
    for lead in all_leads_for_kpi:
        status_key = lead.status.value if hasattr(lead.status, 'value') else str(lead.status)
        status_counts[status_key] = status_counts.get(status_key, 0) + 1

    return render_template(
        'sales_form/dashboard.html',
        leads=leads,
        my_link=my_link,
        stats=stats,
        status_counts=status_counts,
        LeadStatusEnum=LeadStatusEnum
    )


@sales_form_bp.route('/lead/<int:lead_id>')
@login_required
@department_required([5, 18, 13])  # Sales (5), Finance (18), Health Manager (13)
def lead_detail(lead_id):
    """Dettaglio completo di una lead"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso:
    # - Admin: sempre
    # - Sales proprietario: sempre
    # - Health Manager: se assegnato O se lead in PENDING_ASSIGNMENT
    # - Finance: se proprietario
    has_access = (
        current_user.is_admin or
        lead.sales_user_id == current_user.id or
        lead.health_manager_id == current_user.id or
        (current_user.department_id == 13 and lead.status == LeadStatusEnum.PENDING_ASSIGNMENT)
    )

    if not has_access:
        flash('Non hai accesso a questa lead', 'error')
        # Redirect appropriato in base al ruolo
        if current_user.department_id == 13:  # Health Manager
            return redirect(url_for('sales_form.health_manager_panel'))
        else:
            return redirect(url_for('sales_form.dashboard'))

    # Carica pagamenti
    payments = LeadPayment.query.filter_by(lead_id=lead_id)\
        .order_by(LeadPayment.payment_date.desc()).all()

    # Carica activity log
    activities = LeadActivityLog.query.filter_by(lead_id=lead_id)\
        .order_by(LeadActivityLog.created_at.desc()).limit(20).all()

    # Carica pacchetti disponibili
    packages = Package.query.all()

    # Carica Health Manager disponibili (department_id = 13)
    health_managers = User.query.filter_by(
        department_id=13,
        is_active=True
    ).order_by(User.first_name, User.last_name).all()

    # Recupera TUTTI e 3 i link per i check (se esistono)
    check_links = {
        'check1': SalesFormLink.query.filter_by(lead_id=lead_id, check_number=1).first(),
        'check2': SalesFormLink.query.filter_by(lead_id=lead_id, check_number=2).first(),
        'check3': SalesFormLink.query.filter_by(lead_id=lead_id, check_number=3).first()
    }

    # Recupera le configurazioni dei form per i check (per mostrare le domande IN ORDINE)
    from corposostenibile.models import SalesFormConfig
    check_configs = {}
    check_fields_ordered = {}  # Lista ordinata di campi per ogni check

    for check_key, link in check_links.items():
        if link and link.config_id:
            config = SalesFormConfig.query.get(link.config_id)
            if config and config.fields:
                # Crea mapping field_name -> field_label (chiave risposta -> testo domanda)
                check_configs[check_key] = {
                    field.field_name: field.field_label
                    for field in config.fields
                }
                # NUOVO: Lista ordinata di campi per position
                check_fields_ordered[check_key] = sorted(config.fields, key=lambda f: f.position)
            else:
                check_configs[check_key] = {}
                check_fields_ordered[check_key] = []
        else:
            check_configs[check_key] = {}
            check_fields_ordered[check_key] = []

    # Verifica se la lead è manuale e deve ancora compilare i check
    needs_form_completion = (
        lead.form_responses and
        lead.form_responses.get('_manual_entry') == True
    )

    # Genera full URL per ogni check link in un dizionario separato
    from flask import url_for as flask_url_for
    check_urls = {}
    for check_key, link in check_links.items():
        if link:
            check_urls[check_key] = flask_url_for('welcome_form', unique_code=link.unique_code, _external=True)
        else:
            check_urls[check_key] = None

    return render_template(
        'sales_form/lead_detail.html',
        lead=lead,
        payments=payments,
        activities=activities,
        packages=packages,
        health_managers=health_managers,
        LeadStatusEnum=LeadStatusEnum,
        LeadOriginEnum=LeadOriginEnum,
        check_links=check_links,  # ← NUOVO: tutti e 3 i link
        check_urls=check_urls,  # ← NUOVO: URLs completi per i link
        check_configs=check_configs,  # ← Configurazioni form (dizionario field_name -> label)
        check_fields_ordered=check_fields_ordered,  # ← NUOVO: Lista ordinata di campi per mostrare TUTTE le domande
        needs_form_completion=needs_form_completion,
        today=datetime.now().date()  # Per calcolare età dalla birth_date
    )


@sales_form_bp.route('/lead/<int:lead_id>/story', methods=['GET', 'POST'])
@login_required
@department_required([5, 18, 13])  # Sales, Finance, Health Manager
def add_story(lead_id):
    """Aggiunge/modifica storia cliente"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    # Admin: può sempre
    # Sales: solo se è il proprietario
    # Health Manager: può modificare TUTTE le lead
    has_access = (
        current_user.is_admin or
        lead.sales_user_id == current_user.id or
        current_user.department_id == 13  # Tutti gli Health Manager
    )

    if not has_access:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.dashboard'))

    if request.method == 'POST':
        story = request.form.get('client_story')
        if story:
            LeadService.add_client_story(lead_id, story, current_user.id)
            flash('Storia cliente aggiunta con successo', 'success')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    return render_template('sales_form/add_story.html', lead=lead)


@sales_form_bp.route('/lead/<int:lead_id>/gender', methods=['POST'])
@login_required
@sales_required
def update_gender(lead_id):
    """Aggiorna il sesso della lead"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.dashboard'))

    gender = request.form.get('gender')

    # Valida il valore (deve essere 'M', 'F' o vuoto)
    if gender and gender not in ['M', 'F']:
        flash('Valore non valido per il sesso', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    # Aggiorna il campo
    lead.gender = gender if gender else None

    # Log attività
    if hasattr(lead, 'add_activity_log'):
        gender_text = 'Maschio' if gender == 'M' else 'Femmina' if gender == 'F' else 'Non specificato'
        lead.add_activity_log(
            'gender_updated',
            f'Sesso aggiornato: {gender_text}',
            user_id=current_user.id
        )

    db.session.commit()
    flash('Sesso aggiornato con successo', 'success')

    return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))


@sales_form_bp.route('/lead/<int:lead_id>/archive', methods=['POST'])
@login_required
@sales_required
def archive_lead(lead_id):
    """Archivia lead (1 click)"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.dashboard'))

    try:
        lead = LeadService.archive_lead(lead_id, current_user.id)
        flash(f'Lead {lead.full_name} archiviata', 'success')
    except ValueError as e:
        flash(f'Errore: {str(e)}', 'error')

    return redirect(url_for('sales_form.dashboard'))


@sales_form_bp.route('/lead/<int:lead_id>/restore', methods=['POST'])
@login_required
@sales_required
def restore_lead(lead_id):
    """Ripristina lead archiviata"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.archived_leads'))

    try:
        lead = LeadService.restore_lead(lead_id, current_user.id)
        flash(f'Lead {lead.full_name} ripristinata', 'success')
    except ValueError as e:
        flash(f'Errore: {str(e)}', 'error')
        return redirect(url_for('sales_form.archived_leads'))

    return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))


@sales_form_bp.route('/lead/<int:lead_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_lead(lead_id):
    """Elimina definitivamente una lead (SOLO ADMIN)"""
    # Non fare query qui per evitare conflitti di sessione
    # Il service farà la query e gestirà l'eliminazione

    try:
        LeadService.delete_lead(lead_id, current_user.id)
        flash(f'Lead eliminata definitivamente', 'success')
    except ValueError as e:
        flash(f'Errore: {str(e)}', 'error')
        return redirect(url_for('sales_form.dashboard'))
    except Exception as e:
        flash(f'Errore nell\'eliminazione: {str(e)}', 'error')
        return redirect(url_for('sales_form.dashboard'))

    # Redirect a dashboard, archivio o admin in base a dove era
    referer = request.referrer or ''
    if 'archived' in referer:
        return redirect(url_for('sales_form.archived_leads'))
    elif 'admin/leads' in referer:
        return redirect(url_for('sales_form.admin_leads'))
    else:
        return redirect(url_for('sales_form.dashboard'))


@sales_form_bp.route('/archived')
@login_required
@sales_required
def archived_leads():
    """Vista archivio lead"""
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    # Admin vede tutte, sales solo le proprie
    sales_user_id = None if current_user.is_admin else current_user.id

    archived_pagination = LeadService.get_archived_leads(
        sales_user_id=sales_user_id,
        search=search if search else None,
        page=page,
        per_page=20
    )

    return render_template(
        'sales_form/archived_leads.html',
        leads=archived_pagination,
        current_search=search
    )


@sales_form_bp.route('/lead/<int:lead_id>/origin', methods=['POST'])
@login_required
@sales_required
def update_origin(lead_id):
    """Aggiorna l'origine della lead"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.dashboard'))

    origin = request.form.get('origin')

    # Valida il valore (deve essere uno dei valori dell'ENUM o vuoto)
    if origin:
        valid_origins = [o.value for o in LeadOriginEnum]
        if origin not in valid_origins:
            flash('Origine non valida', 'error')
            return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    # Aggiorna il campo
    lead.origin = origin if origin else None

    # Log attività
    if hasattr(lead, 'add_activity_log'):
        origin_text = origin if origin else 'Non specificata'
        lead.add_activity_log(
            'origin_updated',
            f'Origine aggiornata: {origin_text}',
            user_id=current_user.id
        )

    db.session.commit()
    flash('Origine aggiornata con successo', 'success')

    return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))


@sales_form_bp.route('/lead/<int:lead_id>/anagrafica', methods=['POST'])
@login_required
@department_required([5, 18, 13])  # Sales e Health Manager
def update_anagrafica(lead_id):
    """Aggiorna i dati anagrafici della lead (nome, cognome, email, telefono)"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    # Admin: può sempre
    # Sales: deve essere il suo sales_user_id
    # Health Manager: può modificare TUTTE le lead (department_id = 13)
    has_access = (
        current_user.is_admin or
        lead.sales_user_id == current_user.id or
        current_user.department_id == 13  # Tutti gli Health Manager
    )

    if not has_access:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.dashboard'))

    # Recupera i dati dal form
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    indirizzo = request.form.get('indirizzo', '').strip()
    paese = request.form.get('paese', '').strip()

    # Validazione
    if not first_name or not last_name:
        flash('Nome e cognome sono obbligatori', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    if not email:
        flash('Email è obbligatoria', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    # Verifica che l'email non sia già usata da un'altra lead
    existing_lead = SalesLead.query.filter(
        SalesLead.email == email,
        SalesLead.id != lead_id
    ).first()

    if existing_lead:
        flash('Email già utilizzata da un\'altra lead', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    # Traccia le modifiche per il log
    changes = []
    if lead.first_name != first_name:
        changes.append(f'Nome: {lead.first_name} → {first_name}')
        lead.first_name = first_name

    if lead.last_name != last_name:
        changes.append(f'Cognome: {lead.last_name} → {last_name}')
        lead.last_name = last_name

    if lead.email != email:
        changes.append(f'Email: {lead.email} → {email}')
        lead.email = email

    if lead.phone != phone:
        old_phone = lead.phone or 'N/A'
        new_phone = phone or 'N/A'
        changes.append(f'Telefono: {old_phone} → {new_phone}')
        lead.phone = phone if phone else None

    if lead.indirizzo != indirizzo:
        old_indirizzo = lead.indirizzo or 'N/A'
        new_indirizzo = indirizzo or 'N/A'
        changes.append(f'Indirizzo: {old_indirizzo} → {new_indirizzo}')
        lead.indirizzo = indirizzo if indirizzo else None

    if lead.paese != paese:
        old_paese = lead.paese or 'N/A'
        new_paese = paese or 'N/A'
        changes.append(f'Paese: {old_paese} → {new_paese}')
        lead.paese = paese if paese else None

    # Se ci sono modifiche, salva e crea log
    if changes:
        # Log attività
        if hasattr(lead, 'add_activity_log'):
            changes_text = '\n'.join(changes)
            lead.add_activity_log(
                'anagrafica_updated',
                f'Dati anagrafici aggiornati:\n{changes_text}',
                user_id=current_user.id
            )

        db.session.commit()
        flash('Dati anagrafici aggiornati con successo', 'success')
    else:
        flash('Nessuna modifica rilevata', 'info')

    return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))


@sales_form_bp.route('/lead/<int:lead_id>/package', methods=['POST'])
@login_required
@sales_required
def select_package(lead_id):
    """Seleziona pacchetto per lead - usa sempre il prezzo dal database"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Accesso negato'}), 403

    data = request.get_json()
    package_id = data.get('package_id')

    if not package_id:
        return jsonify({'error': 'Pacchetto non selezionato'}), 400

    # Ottieni il pacchetto dal database per avere il prezzo corretto
    package = Package.query.get(package_id)
    if not package:
        return jsonify({'error': 'Pacchetto non trovato'}), 404

    # Usa sempre il prezzo dal database del pacchetto, ignora quello dal frontend
    pricing = {
        'total_amount': float(package.price),
        'discount_amount': 0,  # Nessuno sconto di default
        'discount_reason': None
    }

    lead = LeadService.select_package(lead_id, package_id, pricing, current_user.id)

    return jsonify({
        'success': True,
        'message': f'Pacchetto "{package.name}" associato con successo',
        'package_name': package.name,
        'final_amount': float(lead.final_amount)
    })


@sales_form_bp.route('/lead/<int:lead_id>/payment', methods=['GET', 'POST'])
@login_required
@sales_required
def add_payment(lead_id):
    """Aggiunge pagamento a lead"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.dashboard'))

    if request.method == 'POST':
        payment_data = {
            'amount': float(request.form.get('amount')),
            'payment_type': request.form.get('payment_type'),
            'payment_method': request.form.get('payment_method'),
            'payment_date': datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date(),
            'transaction_id': request.form.get('transaction_id'),
            'notes': request.form.get('notes')
        }

        # Gestione upload ricevuta bonifico
        receipt_file = request.files.get('receipt')
        receipt_path = None

        if receipt_file and receipt_file.filename:
            # Valida che sia un bonifico
            if payment_data['payment_method'] == 'bonifico':
                try:
                    # Valida estensione file
                    allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
                    file_ext = receipt_file.filename.rsplit('.', 1)[1].lower() if '.' in receipt_file.filename else ''

                    if file_ext not in allowed_extensions:
                        flash('Formato file non valido. Usa PDF, JPG o PNG', 'error')
                        return render_template('sales_form/add_payment.html', lead=lead)

                    # Valida dimensione (max 10MB)
                    receipt_file.seek(0, 2)  # Vai alla fine del file
                    file_size = receipt_file.tell()
                    receipt_file.seek(0)  # Torna all'inizio

                    if file_size > 10 * 1024 * 1024:
                        flash('File troppo grande (max 10MB)', 'error')
                        return render_template('sales_form/add_payment.html', lead=lead)

                    # Crea directory per ricevute
                    from flask import current_app
                    import os
                    upload_dir = os.path.join(current_app.root_path, 'uploads', 'payment_receipts')
                    os.makedirs(upload_dir, exist_ok=True)

                    # Genera nome file unico
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"receipt_lead{lead_id}_{timestamp}.{file_ext}"
                    filepath = os.path.join(upload_dir, filename)

                    # Salva file
                    receipt_file.save(filepath)

                    # Salva path relativo per il DB
                    receipt_path = f"payment_receipts/{filename}"

                except Exception as upload_error:
                    import traceback
                    print(f"[RECEIPT-UPLOAD-ERROR] {str(upload_error)}")
                    print(f"[RECEIPT-UPLOAD-TRACE] {traceback.format_exc()}")
                    flash(f'Errore nel caricamento della ricevuta: {str(upload_error)}', 'warning')
                    # Continua comunque con il salvataggio del pagamento

        # Aggiungi receipt_url ai dati del pagamento
        payment_data['receipt_url'] = receipt_path

        try:
            payment = LeadService.add_payment(lead_id, payment_data, current_user.id)

            success_msg = f'Pagamento di €{payment.amount} registrato con successo'
            if receipt_path:
                success_msg += ' (ricevuta allegata)'
            flash(success_msg, 'success')

            # Se pagamento completo, notifica
            if lead.paid_amount and lead.final_amount and lead.paid_amount >= lead.final_amount:
                flash('Pagamento completo! La lead è disponibile per verifica Finance', 'info')

        except Exception as e:
            import traceback
            print(f"[PAYMENT-ERROR] {str(e)}")
            print(f"[PAYMENT-ERROR-TRACE] {traceback.format_exc()}")
            flash(f'Errore nel registrare il pagamento: {str(e)}', 'error')

        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    return render_template('sales_form/add_payment.html', lead=lead)


@sales_form_bp.route('/lead/<int:lead_id>/payment/<int:payment_id>/edit', methods=['GET', 'POST'])
@login_required
@sales_required
def edit_payment(lead_id, payment_id):
    """Modifica un pagamento esistente"""
    from corposostenibile.models import LeadPayment

    lead = SalesLead.query.get_or_404(lead_id)
    payment = LeadPayment.query.get_or_404(payment_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.dashboard'))

    # Verifica che il pagamento appartenga alla lead
    if payment.lead_id != lead_id:
        flash('Pagamento non trovato per questa lead', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    if request.method == 'POST':
        try:
            # Aggiorna i dati del pagamento
            payment.amount = float(request.form.get('amount'))
            payment.payment_type = request.form.get('payment_type')
            payment.payment_method = request.form.get('payment_method')
            payment.payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date()
            payment.transaction_id = request.form.get('transaction_id')
            payment.notes = request.form.get('notes')

            db.session.commit()

            # Ricalcola paid_amount della lead
            lead.paid_amount = sum(p.amount for p in lead.payments)
            db.session.commit()

            # Log attività
            lead.add_activity_log(
                'payment_updated',
                f'Pagamento modificato: €{payment.amount} ({payment.payment_type})',
                user_id=current_user.id
            )

            flash(f'Pagamento aggiornato con successo', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nell\'aggiornamento del pagamento: {str(e)}', 'error')

        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    # GET - Mostra form di modifica
    return render_template('sales_form/edit_payment.html', lead=lead, payment=payment)


@sales_form_bp.route('/lead/<int:lead_id>/payment/<int:payment_id>/delete', methods=['POST'])
@login_required
@sales_required
def delete_payment(lead_id, payment_id):
    """Elimina un pagamento"""
    from corposostenibile.models import LeadPayment

    lead = SalesLead.query.get_or_404(lead_id)
    payment = LeadPayment.query.get_or_404(payment_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.dashboard'))

    # Verifica che il pagamento appartenga alla lead
    if payment.lead_id != lead_id:
        flash('Pagamento non trovato per questa lead', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    try:
        # Salva info per il log
        amount = payment.amount
        payment_type = payment.payment_type

        # Elimina il pagamento
        db.session.delete(payment)

        # Ricalcola paid_amount della lead
        lead.paid_amount = sum(p.amount for p in lead.payments if p.id != payment_id)

        db.session.commit()

        # Log attività
        lead.add_activity_log(
            'payment_deleted',
            f'Pagamento eliminato: €{amount} ({payment_type})',
            user_id=current_user.id
        )

        flash(f'Pagamento eliminato con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nell\'eliminazione del pagamento: {str(e)}', 'error')

    return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))


@sales_form_bp.route('/lead/<int:lead_id>/payment/<int:payment_id>/receipt')
@login_required
def download_receipt(lead_id, payment_id):
    """Scarica la ricevuta di un pagamento"""
    from corposostenibile.models import LeadPayment
    from flask import send_file, current_app, abort
    import os

    lead = SalesLead.query.get_or_404(lead_id)
    payment = LeadPayment.query.get_or_404(payment_id)

    # Verifica accesso: sales proprietario, health manager assegnato, finance o admin
    has_access = (
        lead.sales_user_id == current_user.id or
        lead.health_manager_id == current_user.id or
        current_user.department_id == 19 or  # Finance
        current_user.is_admin
    )

    if not has_access:
        flash('Non hai accesso a questa ricevuta', 'error')
        abort(403)

    # Verifica che il pagamento appartenga alla lead
    if payment.lead_id != lead_id:
        flash('Pagamento non trovato per questa lead', 'error')
        abort(404)

    # Verifica che esista la ricevuta
    if not payment.receipt_url:
        flash('Nessuna ricevuta disponibile per questo pagamento', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    # Costruisci il path completo del file
    receipt_path = os.path.join(current_app.root_path, 'uploads', payment.receipt_url)

    # Verifica che il file esista
    if not os.path.exists(receipt_path):
        flash('File ricevuta non trovato', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    # Invia il file
    try:
        return send_file(
            receipt_path,
            as_attachment=True,
            download_name=f"ricevuta_pagamento_{payment_id}.{payment.receipt_url.split('.')[-1]}"
        )
    except Exception as e:
        flash(f'Errore nel download della ricevuta: {str(e)}', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))


@sales_form_bp.route('/lead/<int:lead_id>/attachment/<path:filename>')
@login_required
def download_attachment(lead_id, filename):
    """Scarica un allegato (foto/file) dal form di una lead"""
    from flask import send_file, current_app, abort
    import os

    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso: sales proprietario, health manager assegnato, professionisti, finance o admin
    # Dipartimenti: 2=Nutrizione, 3=Coach, 4=Psicologia, 13=Customer Success/HM, 19=Finance, 24=Nutrizione 2
    has_access = (
        lead.sales_user_id == current_user.id or
        lead.health_manager_id == current_user.id or
        current_user.department_id in [2, 3, 4, 13, 19, 24] or  # Nutrizione, Coach, Psicologia, HM, Finance
        current_user.is_admin
    )

    if not has_access:
        flash('Non hai accesso a questo file', 'error')
        abort(403)

    # Costruisci il path completo del file
    file_path = os.path.join(current_app.root_path, 'uploads', 'lead_files', str(lead_id), filename)

    # Verifica che il file esista
    if not os.path.exists(file_path):
        flash('File non trovato', 'error')
        abort(404)

    # Verifica che il file appartenga davvero a questa lead (path traversal protection)
    try:
        real_path = os.path.realpath(file_path)
        expected_dir = os.path.realpath(os.path.join(current_app.root_path, 'uploads', 'lead_files', str(lead_id)))

        if not real_path.startswith(expected_dir):
            current_app.logger.warning(f"[SECURITY] Tentativo path traversal: {filename}")
            abort(403)
    except Exception as e:
        current_app.logger.error(f"[SECURITY] Error checking path: {str(e)}")
        abort(403)

    # Invia il file
    try:
        # Se è un'immagine, mostra inline nel browser invece di forzare download
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        is_image = file_ext in ['jpg', 'jpeg', 'png', 'gif', 'heic', 'heif']

        return send_file(
            file_path,
            as_attachment=not is_image,  # Se immagine: inline, altrimenti: download
            download_name=filename,
            mimetype=f'image/{file_ext}' if is_image else None
        )
    except Exception as e:
        flash(f'Errore nel download del file: {str(e)}', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))


@sales_form_bp.route('/lead/<int:lead_id>/assign-health-manager', methods=['POST'])
@login_required
@sales_required
def assign_health_manager(lead_id):
    """Assegna Health Manager e data onboarding a una lead"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    if lead.sales_user_id != current_user.id and not current_user.is_admin:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.dashboard'))

    health_manager_id = request.form.get('health_manager_id', type=int)
    onboarding_date_str = request.form.get('onboarding_date')
    onboarding_time_str = request.form.get('onboarding_time')

    # Validazione
    if not health_manager_id:
        flash('Devi selezionare un Health Manager', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    if not onboarding_date_str:
        flash('Devi inserire la data di onboarding', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    try:
        onboarding_date = datetime.strptime(onboarding_date_str, '%Y-%m-%d').date()
        onboarding_time = None
        if onboarding_time_str:
            onboarding_time = datetime.strptime(onboarding_time_str, '%H:%M').time()

        # Assegna Health Manager
        lead = LeadService.assign_health_manager(
            lead_id=lead_id,
            health_manager_id=health_manager_id,
            onboarding_date=onboarding_date,
            onboarding_time=onboarding_time,
            user_id=current_user.id
        )

        health_manager = User.query.get(health_manager_id)
        time_info = f' alle {onboarding_time.strftime("%H:%M")}' if onboarding_time else ''
        flash(
            f'Health Manager {health_manager.full_name} assegnato con successo! '
            f'Data onboarding: {onboarding_date.strftime("%d/%m/%Y")}{time_info}. '
            f'La lead è ora visibile nel pannello Health Manager.',
            'success'
        )

    except ValueError as e:
        flash(f'Errore: {str(e)}', 'error')
    except Exception as e:
        import traceback
        print(f"[ASSIGN-HM-ERROR] {str(e)}")
        print(f"[ASSIGN-HM-ERROR-TRACE] {traceback.format_exc()}")
        flash(f'Errore nell\'assegnazione: {str(e)}', 'error')

    return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))


@sales_form_bp.route('/lead/<int:lead_id>/update-health-manager', methods=['POST'])
@login_required
@department_required([5, 18, 13])  # Sales, Finance, Health Manager
def update_health_manager(lead_id):
    """Modifica Health Manager e/o data onboarding già assegnati"""
    lead = SalesLead.query.get_or_404(lead_id)

    # Verifica accesso
    # Admin: può sempre
    # Sales: solo se è il proprietario
    # Health Manager: può modificare TUTTE le lead
    has_access = (
        current_user.is_admin or
        lead.sales_user_id == current_user.id or
        current_user.department_id == 13  # Tutti gli Health Manager
    )

    if not has_access:
        flash('Non hai accesso a questa lead', 'error')
        return redirect(url_for('sales_form.dashboard'))

    # Verifica che l'HM sia già stato assegnato
    if not lead.health_manager_id:
        flash('Health Manager non ancora assegnato. Usa il form di assegnazione.', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    health_manager_id = request.form.get('health_manager_id', type=int)
    onboarding_date_str = request.form.get('onboarding_date')
    onboarding_time_str = request.form.get('onboarding_time')

    # Validazione
    if not health_manager_id:
        flash('Devi selezionare un Health Manager', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    if not onboarding_date_str:
        flash('Devi inserire la data di onboarding', 'error')
        return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))

    try:
        onboarding_date = datetime.strptime(onboarding_date_str, '%Y-%m-%d').date()
        onboarding_time = None
        if onboarding_time_str:
            onboarding_time = datetime.strptime(onboarding_time_str, '%H:%M').time()

        # Verifica che l'health manager esista e sia del dipartimento corretto
        health_manager = User.query.get(health_manager_id)
        if not health_manager:
            raise ValueError(f"Health Manager con ID {health_manager_id} non trovato")

        if health_manager.department_id != 13:
            raise ValueError(f"L'utente {health_manager.full_name} non è un Health Manager (dept 13)")

        # Salva i valori precedenti per il log
        old_hm_name = lead.health_manager.full_name if lead.health_manager else "N/A"
        old_onboarding_date = lead.onboarding_date.strftime('%d/%m/%Y') if lead.onboarding_date else "N/A"
        old_onboarding_time = lead.onboarding_time.strftime('%H:%M') if lead.onboarding_time else "N/A"

        # Aggiorna Health Manager, data e orario onboarding
        lead.health_manager_id = health_manager_id
        lead.onboarding_date = onboarding_date
        lead.onboarding_time = onboarding_time

        # Log attività
        changes = []
        if lead.health_manager_id != health_manager_id:
            changes.append(f"Health Manager: {old_hm_name} → {health_manager.full_name}")
        if lead.onboarding_date != onboarding_date:
            changes.append(f"Data Onboarding: {old_onboarding_date} → {onboarding_date.strftime('%d/%m/%Y')}")
        new_time_str = onboarding_time.strftime('%H:%M') if onboarding_time else "N/A"
        if old_onboarding_time != new_time_str:
            changes.append(f"Orario Call: {old_onboarding_time} → {new_time_str}")

        if changes:
            lead.add_activity_log(
                'health_manager_updated',
                f'Health Manager modificato: {", ".join(changes)}',
                user_id=current_user.id
            )

        db.session.commit()

        time_info = f' alle {onboarding_time.strftime("%H:%M")}' if onboarding_time else ''
        flash(
            f'Health Manager aggiornato: {health_manager.full_name}. '
            f'Data onboarding: {onboarding_date.strftime("%d/%m/%Y")}{time_info}.',
            'success'
        )

    except ValueError as e:
        flash(f'Errore: {str(e)}', 'error')
    except Exception as e:
        import traceback
        print(f"[UPDATE-HM-ERROR] {str(e)}")
        print(f"[UPDATE-HM-ERROR-TRACE] {traceback.format_exc()}")
        flash(f'Errore nella modifica: {str(e)}', 'error')

    return redirect(url_for('sales_form.lead_detail', lead_id=lead_id))


@sales_form_bp.route('/lead/<int:lead_id>/update-onboarding-date', methods=['POST'])
@login_required
@department_required([13])  # Health Manager
def update_onboarding_date(lead_id):
    """Aggiorna solo la data di onboarding (per Health Manager dal pannello)"""
    lead = SalesLead.query.get_or_404(lead_id)

    try:
        data = request.get_json()
        onboarding_date_str = data.get('onboarding_date')

        if not onboarding_date_str:
            return jsonify({
                'success': False,
                'message': 'Data di onboarding non fornita'
            }), 400

        # Parse e valida la data
        from datetime import datetime
        try:
            onboarding_date = datetime.strptime(onboarding_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato data non valido'
            }), 400

        # Salva il valore precedente per il log
        old_date = lead.onboarding_date.strftime('%d/%m/%Y') if lead.onboarding_date else "N/A"

        # Aggiorna la data
        lead.onboarding_date = onboarding_date

        # Log attività
        lead.add_activity_log(
            'onboarding_date_updated',
            f'Data Onboarding modificata: {old_date} → {onboarding_date.strftime("%d/%m/%Y")}',
            user_id=current_user.id
        )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Data di onboarding aggiornata con successo',
            'new_date': onboarding_date.strftime('%d/%m/%Y')
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"[UPDATE-ONBOARDING-DATE-ERROR] {str(e)}")
        print(f"[UPDATE-ONBOARDING-DATE-TRACE] {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), 500


@sales_form_bp.route('/lead/<int:lead_id>/update-onboarding-time', methods=['POST'])
@login_required
def update_onboarding_time(lead_id):
    """Aggiorna solo l'orario di onboarding (per Health Manager dal pannello) - API JSON"""
    # Check permessi: HM (dept 13) o Admin
    if not current_user.is_admin and current_user.department_id != 13:
        return jsonify({
            'success': False,
            'message': 'Non hai i permessi per questa operazione'
        }), 403

    lead = SalesLead.query.get(lead_id)
    if not lead:
        return jsonify({
            'success': False,
            'message': 'Lead non trovata'
        }), 404

    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            return jsonify({
                'success': False,
                'message': 'Dati non ricevuti'
            }), 400

        onboarding_time_str = data.get('onboarding_time')

        # Parse orario (può essere null per rimuoverlo)
        onboarding_time = None
        if onboarding_time_str:
            onboarding_time = datetime.strptime(onboarding_time_str, '%H:%M').time()

        # Salva il valore precedente per il log
        old_time = lead.onboarding_time.strftime('%H:%M') if lead.onboarding_time else "N/A"
        new_time = onboarding_time.strftime('%H:%M') if onboarding_time else "N/A"

        # Aggiorna l'orario
        lead.onboarding_time = onboarding_time

        # Log attività
        if old_time != new_time:
            lead.add_activity_log(
                'onboarding_time_updated',
                f'Orario Call Onboarding modificato: {old_time} → {new_time}',
                user_id=current_user.id
            )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Orario aggiornato: {new_time}' if onboarding_time else 'Orario rimosso',
            'new_time': new_time
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': 'Formato orario non valido'
        }), 400
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"[UPDATE-ONBOARDING-TIME-ERROR] {str(e)}")
        print(f"[UPDATE-ONBOARDING-TIME-TRACE] {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), 500


@sales_form_bp.route('/lead/<int:lead_id>/change-health-manager', methods=['POST'])
@login_required
def update_health_manager_inline(lead_id):
    """Aggiorna solo l'Health Manager assegnato (per Health Manager dal pannello) - API JSON"""
    from flask import current_app

    # Check permessi: HM (dept 13) o Admin
    if not current_user.is_admin and current_user.department_id != 13:
        return jsonify({
            'success': False,
            'message': 'Non hai i permessi per questa operazione'
        }), 403

    lead = SalesLead.query.get(lead_id)
    if not lead:
        return jsonify({
            'success': False,
            'message': 'Lead non trovata'
        }), 404

    try:
        data = request.get_json(force=True, silent=True)
        current_app.logger.info(f"[UPDATE-HM] Received data: {data}")

        if not data:
            return jsonify({
                'success': False,
                'message': 'Dati non ricevuti'
            }), 400

        new_health_manager_id = data.get('health_manager_id')
        if isinstance(new_health_manager_id, str):
            new_health_manager_id = int(new_health_manager_id) if new_health_manager_id else None

        if not new_health_manager_id:
            return jsonify({
                'success': False,
                'message': 'Health Manager non selezionato'
            }), 400

        # Verifica che l'health manager esista e sia del dipartimento corretto
        new_health_manager = User.query.get(new_health_manager_id)
        if not new_health_manager:
            return jsonify({
                'success': False,
                'message': f'Health Manager con ID {new_health_manager_id} non trovato'
            }), 404

        if new_health_manager.department_id != 13:
            return jsonify({
                'success': False,
                'message': f'{new_health_manager.full_name} non è un Health Manager'
            }), 400

        # Salva il valore precedente per il log
        old_hm_name = lead.health_manager.full_name if lead.health_manager else "Nessuno"

        # Aggiorna l'Health Manager
        lead.health_manager_id = new_health_manager_id

        # Log attività
        lead.add_activity_log(
            'health_manager_changed',
            f'Health Manager modificato: {old_hm_name} → {new_health_manager.full_name}',
            user_id=current_user.id
        )

        db.session.commit()

        current_app.logger.info(f"[UPDATE-HM] Success: Lead {lead_id} -> HM {new_health_manager_id}")

        return jsonify({
            'success': True,
            'message': f'Health Manager aggiornato a {new_health_manager.full_name}',
            'health_manager_name': new_health_manager.full_name,
            'health_manager_avatar': new_health_manager.avatar_url
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        current_app.logger.error(f"[UPDATE-HM-ERROR] {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), 500


# ===================== PANNELLO FINANCE =====================

@sales_form_bp.route('/finance')
@login_required
@department_required([19])  # Dipartimento Finance
def finance_panel():
    """Pannello Finance per approvazione pagamenti"""
    # Ottieni filtri dalla query string
    search = request.args.get('search', '').strip()
    sales_user_id = request.args.get('sales_user_id', type=int)

    # Carica lead con filtri
    pending_leads = FinanceService.get_pending_approvals(
        search=search if search else None,
        sales_user_id=sales_user_id
    )

    # Statistiche
    total_pending = len(pending_leads)
    total_amount = sum(lead.final_amount or 0 for lead in pending_leads)

    # Carica tutti gli utenti sales per il filtro
    sales_users = User.query.filter(
        User.department_id.in_([5, 18]),  # Dipartimenti sales
        User.is_active == True
    ).order_by(User.first_name, User.last_name).all()

    return render_template(
        'sales_form/finance_panel.html',
        pending_leads=pending_leads,
        total_pending=total_pending,
        total_amount=total_amount,
        sales_users=sales_users,
        current_search=search,
        current_sales_filter=sales_user_id
    )


@sales_form_bp.route('/finance/approve/<int:lead_id>', methods=['POST'])
@login_required
@department_required([19])  # Finance
def approve_payment(lead_id):
    """Approva pagamento - CHECK NON BLOCCANTE"""
    notes = request.form.get('notes')

    try:
        lead = FinanceService.approve_payment(lead_id, current_user.id, notes)

        # Se richiesta AJAX, restituisci JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({
                'success': True,
                'message': f'Pagamento approvato per {lead.first_name} {lead.last_name}. Verifica Finance completata.'
            })

        # Altrimenti redirect normale
        flash(
            f'Pagamento approvato per {lead.first_name} {lead.last_name}. '
            f'Verifica Finance completata.',
            'success'
        )
        return redirect(url_for('sales_form.finance_panel'))

    except Exception as e:
        import traceback
        print(f"[FINANCE-APPROVE-ERROR] {str(e)}")
        print(f"[FINANCE-APPROVE-ERROR-TRACE] {traceback.format_exc()}")

        # Se richiesta AJAX, restituisci JSON error
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400

        flash(f'Errore: {str(e)}', 'error')
        return redirect(url_for('sales_form.finance_panel'))


@sales_form_bp.route('/finance/reject/<int:lead_id>', methods=['POST'])
@login_required
@department_required([19])  # Finance
def reject_payment(lead_id):
    """Rifiuta pagamento"""
    reason = request.form.get('reason')

    if not reason:
        # Se richiesta AJAX, restituisci JSON error
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({
                'success': False,
                'message': 'Devi specificare una motivazione'
            }), 400

        flash('Devi specificare una motivazione', 'error')
        return redirect(url_for('sales_form.finance_panel'))

    try:
        lead = FinanceService.reject_payment(lead_id, current_user.id, reason)

        # Se richiesta AJAX, restituisci JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({
                'success': True,
                'message': f'Pagamento rifiutato per {lead.full_name}'
            })

        flash(f'Pagamento rifiutato per {lead.full_name}', 'warning')
        return redirect(url_for('sales_form.finance_panel'))

    except Exception as e:
        # Se richiesta AJAX, restituisci JSON error
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400

        flash(f'Errore: {str(e)}', 'error')
        return redirect(url_for('sales_form.finance_panel'))


@sales_form_bp.route('/finance/history')
@login_required
@department_required([19])  # Finance
def finance_history():
    """Storico pagamenti gestiti da Finance"""
    page = request.args.get('page', 1, type=int)
    sales_user_id = request.args.get('sales_user_id', type=int)
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')
    search = request.args.get('search', '').strip()

    # Converti date da stringa a datetime
    date_from = None
    date_to = None
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        except ValueError:
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
        except ValueError:
            pass

    # Ottieni lead filtrate
    leads_pagination = FinanceService.get_history(
        page=page,
        per_page=50,
        sales_user_id=sales_user_id,
        date_from=date_from,
        date_to=date_to,
        search=search if search else None
    )

    # Statistiche dello storico (totali, non filtrate)
    total_approved = SalesLead.query.filter_by(finance_approved=True).count()
    total_rejected = SalesLead.query.filter(
        SalesLead.finance_approved == False,
        SalesLead.finance_notes.isnot(None)
    ).count()

    # Carica tutti gli utenti sales per il filtro
    sales_users = User.query.filter(
        User.department_id.in_([5, 18]),  # Dipartimenti sales
        User.is_active == True
    ).order_by(User.first_name, User.last_name).all()

    return render_template(
        'sales_form/finance_history.html',
        leads=leads_pagination,
        total_approved=total_approved,
        total_rejected=total_rejected,
        sales_users=sales_users,
        current_sales_filter=sales_user_id,
        current_date_from=date_from_str,
        current_date_to=date_to_str,
        current_search=search
    )


# ===================== PANNELLO HEALTH MANAGER =====================

@sales_form_bp.route('/health-manager')
@login_required
@department_required([13])  # Health Manager department
def health_manager_panel():
    """Pannello Health Manager per assegnazione professionisti"""
    # Ottieni filtri dalla query string
    search = request.args.get('search', '').strip()
    health_manager_id = request.args.get('health_manager_id', type=int)
    onboarding_date_from_str = request.args.get('onboarding_date_from', '').strip()
    onboarding_date_to_str = request.args.get('onboarding_date_to', '').strip()
    missing_check1 = request.args.get('missing_check1') == '1'
    missing_check2 = request.args.get('missing_check2') == '1'
    missing_check3 = request.args.get('missing_check3') == '1'

    # Filtro messaggio presentazione: 'sent', 'not_sent', o None (tutti)
    presentation_filter = request.args.get('presentation_message_filter')
    presentation_message_sent = None
    if presentation_filter == 'sent':
        presentation_message_sent = True
    elif presentation_filter == 'not_sent':
        presentation_message_sent = False

    # Parse date range
    onboarding_date_from = None
    onboarding_date_to = None
    if onboarding_date_from_str:
        try:
            onboarding_date_from = datetime.strptime(onboarding_date_from_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if onboarding_date_to_str:
        try:
            onboarding_date_to = datetime.strptime(onboarding_date_to_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Carica lead con filtri
    pending_leads = HealthManagerService.get_pending_assignments(
        search=search if search else None,
        health_manager_id=health_manager_id,
        onboarding_date_from=onboarding_date_from,
        onboarding_date_to=onboarding_date_to,
        missing_check1=missing_check1,
        missing_check2=missing_check2,
        missing_check3=missing_check3,
        presentation_message_sent=presentation_message_sent
    )

    # Calcola professionisti necessari basandosi sui pacchetti delle lead
    professionals_needed = HealthManagerService.calculate_professionals_needed(pending_leads)

    # Carica professionisti disponibili
    nutritionists = User.query.filter_by(department_id=2, is_active=True).order_by(User.first_name, User.last_name).all()  # Nutrizione
    coaches = User.query.filter_by(department_id=3, is_active=True).order_by(User.first_name, User.last_name).all()  # Coach
    psychologists = User.query.filter_by(department_id=4, is_active=True).order_by(User.first_name, User.last_name).all()  # Psicologia

    # Carica tutti gli Health Manager per il filtro
    health_managers = User.query.filter_by(
        department_id=13,
        is_active=True
    ).order_by(User.first_name, User.last_name).all()

    return render_template(
        'sales_form/health_manager_panel.html',
        pending_leads=pending_leads,
        professionals_needed=professionals_needed,
        nutritionists=nutritionists,
        coaches=coaches,
        psychologists=psychologists,
        health_managers=health_managers,
        current_search=search,
        current_hm_filter=health_manager_id,
        onboarding_date_from=onboarding_date_from_str,
        onboarding_date_to=onboarding_date_to_str,
        current_presentation_filter=presentation_filter,
        now=datetime.now()
    )


@sales_form_bp.route('/health-manager/history')
@login_required
@department_required([13])  # Health Manager
def health_manager_history():
    """Storico assegnazioni Health Manager"""
    page = request.args.get('page', 1, type=int)
    health_manager_id = request.args.get('health_manager_id', type=int)
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')
    search = request.args.get('search', '').strip()

    # Converti date da stringa a datetime
    date_from = None
    date_to = None
    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        except ValueError:
            pass
    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
        except ValueError:
            pass

    # Ottieni lead filtrate
    leads_pagination = HealthManagerService.get_history(
        page=page,
        per_page=50,
        health_manager_id=health_manager_id,
        date_from=date_from,
        date_to=date_to,
        search=search if search else None
    )

    # Statistiche dello storico (tutte le lead con assegnazione effettuata)
    total_assigned = SalesLead.query.filter(SalesLead.assigned_at.isnot(None)).count()

    # Carica tutti gli Health Manager per il filtro
    health_managers = User.query.filter_by(
        department_id=13,
        is_active=True
    ).order_by(User.first_name, User.last_name).all()

    return render_template(
        'sales_form/health_manager_history.html',
        leads=leads_pagination,
        total_assigned=total_assigned,
        health_managers=health_managers,
        current_hm_filter=health_manager_id,
        current_date_from=date_from_str,
        current_date_to=date_to_str,
        current_search=search
    )


@sales_form_bp.route('/health-manager/toggle-presentation-message/<int:lead_id>', methods=['POST'])
@login_required
@department_required([13])  # Health Manager
def toggle_presentation_message(lead_id):
    """Toggle messaggio di presentazione inviato"""
    lead = SalesLead.query.get_or_404(lead_id)

    try:
        # Toggle del valore
        lead.presentation_message_sent = not lead.presentation_message_sent

        if lead.presentation_message_sent:
            # Segna come inviato
            lead.presentation_message_sent_at = datetime.now()
            lead.presentation_message_sent_by = current_user.id
            action = 'segnato come inviato'
        else:
            # Rimosso segno
            lead.presentation_message_sent_at = None
            lead.presentation_message_sent_by = None
            action = 'segnato come non inviato'

        # Log attività
        lead.add_activity_log(
            'presentation_message_toggled',
            f'Messaggio di presentazione {action}',
            user_id=current_user.id
        )

        db.session.commit()

        return jsonify({
            'success': True,
            'presentation_message_sent': lead.presentation_message_sent,
            'message': f'Messaggio di presentazione {action}'
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"[TOGGLE-PRESENTATION-ERROR] {str(e)}")
        print(f"[TOGGLE-PRESENTATION-TRACE] {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), 500


@sales_form_bp.route('/health-manager/assign/<int:lead_id>', methods=['POST'])
@login_required
@department_required([13])  # Health Manager
def assign_professionals(lead_id):
    """Assegna professionisti a lead"""
    # Data inizio abbonamento (obbligatoria)
    onboarding_date_str = request.form.get('onboarding_date')
    if not onboarding_date_str:
        return jsonify({
            'success': False,
            'message': 'La data di inizio abbonamento è obbligatoria'
        }), 400

    try:
        onboarding_date = datetime.strptime(onboarding_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Formato data non valido'
        }), 400

    # Parse date call iniziali (se presenti)
    data_call_iniziale_nutrizionista = None
    data_call_iniziale_coach = None
    data_call_iniziale_psicologia = None

    if request.form.get('data_call_iniziale_nutrizionista'):
        try:
            data_call_iniziale_nutrizionista = datetime.strptime(
                request.form.get('data_call_iniziale_nutrizionista'), '%Y-%m-%d'
            ).date()
        except ValueError:
            pass

    if request.form.get('data_call_iniziale_coach'):
        try:
            data_call_iniziale_coach = datetime.strptime(
                request.form.get('data_call_iniziale_coach'), '%Y-%m-%d'
            ).date()
        except ValueError:
            pass

    if request.form.get('data_call_iniziale_psicologia'):
        try:
            data_call_iniziale_psicologia = datetime.strptime(
                request.form.get('data_call_iniziale_psicologia'), '%Y-%m-%d'
            ).date()
        except ValueError:
            pass

    assignments = {
        'nutritionist_id': request.form.get('nutritionist_id', type=int),
        'coach_id': request.form.get('coach_id', type=int),
        'psychologist_id': request.form.get('psychologist_id', type=int),
        'notes': request.form.get('notes'),
        'note_onboarding': request.form.get('note_onboarding'),  # Note criticità iniziali
        'onboarding_date': onboarding_date,
        'data_call_iniziale_nutrizionista': data_call_iniziale_nutrizionista,
        'data_call_iniziale_coach': data_call_iniziale_coach,
        'data_call_iniziale_psicologia': data_call_iniziale_psicologia
    }

    # Almeno un professionista deve essere assegnato
    if not any([assignments['nutritionist_id'], assignments['coach_id'], assignments['psychologist_id']]):
        return jsonify({
            'success': False,
            'message': 'Devi assegnare almeno un professionista'
        }), 400

    # VALIDAZIONE DATE CALL OBBLIGATORIE
    # Se assegnato nutrizionista -> data obbligatoria
    if assignments['nutritionist_id'] and not assignments['data_call_iniziale_nutrizionista']:
        return jsonify({
            'success': False,
            'message': 'Data Call Iniziale Nutrizionista obbligatoria se il professionista è assegnato'
        }), 400

    # Se assegnato coach -> data obbligatoria
    if assignments['coach_id'] and not assignments['data_call_iniziale_coach']:
        return jsonify({
            'success': False,
            'message': 'Data Call Iniziale Coach obbligatoria se il professionista è assegnato'
        }), 400

    # Se assegnato psicologo -> data obbligatoria
    if assignments['psychologist_id'] and not assignments['data_call_iniziale_psicologia']:
        return jsonify({
            'success': False,
            'message': 'Data Call Iniziale Psicologo obbligatoria se il professionista è assegnato'
        }), 400

    try:
        lead = HealthManagerService.assign_professionals(lead_id, assignments, current_user.id)
        return jsonify({
            'success': True,
            'message': f'Professionisti assegnati a {lead.full_name}. Cliente creato con successo!'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ===================== STATISTICHE =====================

@sales_form_bp.route('/stats')
@login_required
@sales_required
def stats():
    """Statistiche performance sales"""
    # Periodo corrente
    today = datetime.now()
    month_start = today.replace(day=1)

    # Stats personali
    my_stats = LeadService.get_lead_stats(current_user.id, month_start.strftime('%Y-%m'))

    # Confronto con mese precedente
    prev_month = (month_start - timedelta(days=1)).replace(day=1)
    prev_stats = LeadService.get_lead_stats(current_user.id, prev_month.strftime('%Y-%m'))

    # Ranking team (se admin o manager)
    team_ranking = []
    if current_user.is_admin or current_user.role == 'manager':
        # Query per ranking team
        team_stats = db.session.query(
            User.id,
            User.first_name,
            User.last_name,
            func.count(SalesLead.id).label('total_leads'),
            func.sum(SalesLead.paid_amount).label('revenue')
        ).join(SalesLead, User.id == SalesLead.sales_user_id)\
         .filter(SalesLead.created_at >= month_start)\
         .group_by(User.id, User.first_name, User.last_name)\
         .order_by(func.sum(SalesLead.paid_amount).desc())\
         .all()

        team_ranking = [
            {
                'name': f"{stat.first_name} {stat.last_name}",
                'leads': stat.total_leads,
                'revenue': float(stat.revenue or 0)
            }
            for stat in team_stats
        ]

    return render_template(
        'sales_form/stats.html',
        my_stats=my_stats,
        prev_stats=prev_stats,
        team_ranking=team_ranking,
        month=month_start.strftime('%B %Y')
    )


# ===================== ANALYTICS DASHBOARD =====================

@sales_form_bp.route('/analytics')
@login_required
@department_required([5, 18, 19])  # Sales 1, Sales 2, Finance (per vedere analytics)
def analytics():
    """Dashboard Analytics con metriche aziendali e classifiche"""
    from .services import AnalyticsService
    from dateutil.relativedelta import relativedelta

    # Ottieni filtri dalla query string
    filter_type = request.args.get('filter_type', 'month')
    custom_start = request.args.get('start_date')
    custom_end = request.args.get('end_date')

    # Calcola date in base al filtro
    today = datetime.now()

    if filter_type == 'week':
        # Settimana corrente (lunedì - domenica)
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif filter_type == 'month':
        # Mese corrente
        start_date = today.replace(day=1)
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
    elif filter_type == 'quarter':
        # Trimestre corrente
        quarter = (today.month - 1) // 3
        start_date = datetime(today.year, quarter * 3 + 1, 1)
        end_date = (start_date + relativedelta(months=3)) - timedelta(days=1)
    elif filter_type == 'year':
        # Anno corrente
        start_date = datetime(today.year, 1, 1)
        end_date = datetime(today.year, 12, 31)
    elif filter_type == 'custom' and custom_start and custom_end:
        # Range personalizzato
        start_date = datetime.strptime(custom_start, '%Y-%m-%d')
        end_date = datetime.strptime(custom_end, '%Y-%m-%d')
    else:
        # Default: mese corrente
        start_date = today.replace(day=1)
        end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)

    # Imposta orari per includere tutta la giornata
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Calcola metriche filtrate
    company_metrics = AnalyticsService.get_company_metrics(start_date, end_date)

    # Trend ultimi 12 mesi (NON filtrabili)
    leads_trend = AnalyticsService.get_leads_trend_12_months()
    revenue_trend = AnalyticsService.get_revenue_trend_12_months()

    # Classifiche filtrate
    sales_ranking = AnalyticsService.get_sales_ranking(start_date, end_date, top_n=10)
    packages_ranking = AnalyticsService.get_packages_ranking(start_date, end_date, top_n=10)

    return render_template(
        'sales_form/analytics_dashboard.html',
        filter_type=filter_type,
        start_date=start_date,
        end_date=end_date,
        company_metrics=company_metrics,
        leads_trend=leads_trend,
        revenue_trend=revenue_trend,
        sales_ranking=sales_ranking,
        packages_ranking=packages_ranking
    )
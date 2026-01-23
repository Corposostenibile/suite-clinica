"""
Finance Dashboard for GHL Integration
======================================
Dashboard per il team finance per verificare e approvare pagamenti
"""

from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import and_, or_, func

from . import bp
from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    GHLOpportunity,
    ServiceClienteAssignment,
    ServiceClienteNote
)
# from corposostenibile.blueprints.finance.permissions import FinancePerm, has_permission


@bp.route('/dashboard/ghl')
@login_required
def ghl_dashboard():
    """Dashboard principale per verifiche pagamenti da GHL"""
    # Controllo permessi disabilitato temporaneamente
    # if not has_permission(current_user, FinancePerm.VIEW):
    #     flash('Non hai i permessi per accedere a questa sezione', 'danger')
    #     return redirect(url_for('welcome.dashboard'))

    # Filtri dalla query string
    status_filter = request.args.get('status', 'pending_finance')
    payment_type = request.args.get('payment_type', 'all')  # all, acconto, saldo
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Query base per assignments pendenti
    query = ServiceClienteAssignment.query.join(
        Cliente, ServiceClienteAssignment.cliente_id == Cliente.cliente_id
    ).outerjoin(
        GHLOpportunity, ServiceClienteAssignment.ghl_opportunity_id == GHLOpportunity.id
    )

    # Applica filtri
    if status_filter:
        if status_filter == 'pending_finance':
            # Mostra sia pending_finance che pending_finance_full
            query = query.filter(
                or_(
                    ServiceClienteAssignment.status == 'pending_finance',
                    ServiceClienteAssignment.status == 'pending_finance_full'
                )
            )
        else:
            query = query.filter(ServiceClienteAssignment.status == status_filter)

    if date_from:
        query = query.filter(ServiceClienteAssignment.created_at >= datetime.fromisoformat(date_from))

    if date_to:
        query = query.filter(ServiceClienteAssignment.created_at <= datetime.fromisoformat(date_to))

    # Esegui query
    assignments = query.order_by(ServiceClienteAssignment.created_at.desc()).all()

    # Statistiche
    stats = {
        'pending': ServiceClienteAssignment.query.filter_by(status='pending_finance').count(),
        'approved_today': ServiceClienteAssignment.query.filter(
            ServiceClienteAssignment.finance_approved == True,
            ServiceClienteAssignment.finance_approved_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count(),
        'total_pending_amount': db.session.query(
            func.sum(GHLOpportunity.importo_totale)
        ).join(
            ServiceClienteAssignment, ServiceClienteAssignment.ghl_opportunity_id == GHLOpportunity.id
        ).filter(
            ServiceClienteAssignment.status == 'pending_finance'
        ).scalar() or 0,
        'rejected_this_week': ServiceClienteAssignment.query.filter(
            ServiceClienteAssignment.status == 'finance_rejected',
            ServiceClienteAssignment.updated_at >= datetime.now() - timedelta(days=7)
        ).count()
    }

    return render_template(
        'finance/ghl_dashboard.html',
        assignments=assignments,
        stats=stats,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to
    )


@bp.route('/dashboard/verify/<int:assignment_id>')
@login_required
def verify_payment(assignment_id):
    """Pagina dettaglio per verifica pagamento"""
    if not has_permission(current_user, FinancePerm.APPROVE_PAYMENT):
        flash('Non hai i permessi per verificare pagamenti', 'danger')
        return redirect(url_for('finance.ghl_dashboard'))

    assignment = ServiceClienteAssignment.query.get_or_404(assignment_id)
    cliente = assignment.cliente
    opportunity = assignment.ghl_opportunity

    # Cerca transazioni esistenti per questo cliente
    existing_payments = PaymentTransaction.query.filter_by(
        cliente_id=cliente.cliente_id
    ).order_by(PaymentTransaction.payment_date.desc()).all()

    # Cerca note relative all'assignment
    notes = ServiceClienteNote.query.filter_by(
        assignment_id=assignment_id
    ).order_by(ServiceClienteNote.created_at.desc()).all()

    # Suggerimenti automatici basati su pattern
    suggestions = _get_payment_suggestions(cliente, opportunity)

    return render_template(
        'finance/verify_payment.html',
        assignment=assignment,
        cliente=cliente,
        opportunity=opportunity,
        existing_payments=existing_payments,
        notes=notes,
        suggestions=suggestions
    )


@bp.route('/dashboard/approve/<int:assignment_id>', methods=['POST'])
@login_required
def approve_payment(assignment_id):
    """Approva il pagamento verificato"""
    if not has_permission(current_user, FinancePerm.APPROVE_PAYMENT):
        return jsonify({'error': 'Permessi insufficienti'}), 403

    assignment = ServiceClienteAssignment.query.get_or_404(assignment_id)

    try:
        # Aggiorna assignment
        assignment.status = 'finance_approved'
        assignment.finance_approved = True
        assignment.finance_approved_by = current_user.id
        assignment.finance_approved_at = datetime.utcnow()
        assignment.finance_notes = request.form.get('notes', '')

        # Verifica importi
        acconto_verificato = request.form.get('acconto_verificato', type=float)
        totale_verificato = request.form.get('totale_verificato', type=float)

        if acconto_verificato:
            assignment.importo_verificato = Decimal(str(acconto_verificato))

        # Aggiorna stato cliente
        cliente = assignment.cliente
        cliente.payment_status = 'verified'
        cliente.payment_verified_at = datetime.utcnow()
        cliente.payment_verified_by = current_user.id
        cliente.service_status = 'ready_for_assignment'

        # Verifica se c'è discrepanza tra importi
        if assignment.ghl_opportunity:
            opp = assignment.ghl_opportunity
            if acconto_verificato and abs(float(opp.acconto_pagato or 0) - acconto_verificato) > 0.01:
                # Crea nota per discrepanza
                note = ServiceClienteNote(
                    assignment_id=assignment_id,
                    cliente_id=cliente.cliente_id,
                    note_text=f"ATTENZIONE: Discrepanza importo. GHL: €{opp.acconto_pagato}, Verificato: €{acconto_verificato}",
                    note_type='warning',
                    created_by=current_user.id,
                    visible_to_professionals=True
                )
                db.session.add(note)

        # Crea nota di approvazione
        approval_note = ServiceClienteNote(
            assignment_id=assignment_id,
            cliente_id=cliente.cliente_id,
            note_text=f"Pagamento verificato e approvato da {current_user.nome_cognome}. {request.form.get('notes', '')}",
            note_type='finance_approval',
            created_by=current_user.id,
            visible_to_professionals=True
        )
        db.session.add(approval_note)

        # Se richiesto, crea transazione di pagamento
        if request.form.get('create_transaction') == 'true':
            transaction = PaymentTransaction(
                cliente_id=cliente.cliente_id,
                amount=Decimal(str(totale_verificato or acconto_verificato or 0)),
                payment_type='acconto' if acconto_verificato else 'saldo',
                payment_date=datetime.utcnow(),
                payment_method=request.form.get('payment_method', 'bonifico'),
                reference=request.form.get('reference', ''),
                notes=request.form.get('transaction_notes', ''),
                created_by=current_user.id
            )
            db.session.add(transaction)

        db.session.commit()

        flash('Pagamento approvato con successo! Cliente pronto per assegnazione.', 'success')

        # TODO: Trigger notifica per servizio clienti
        # from corposostenibile.blueprints.ghl_integration.tasks import send_assignment_notification
        # send_assignment_notification.delay(cliente.cliente_id, assignment_id)

        return redirect(url_for('finance.ghl_dashboard'))

    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'approvazione: {str(e)}', 'danger')
        return redirect(url_for('finance.verify_payment', assignment_id=assignment_id))


@bp.route('/dashboard/reject/<int:assignment_id>', methods=['POST'])
@login_required
def reject_payment(assignment_id):
    """Rigetta il pagamento con motivazione"""
    if not has_permission(current_user, FinancePerm.APPROVE_PAYMENT):
        return jsonify({'error': 'Permessi insufficienti'}), 403

    assignment = ServiceClienteAssignment.query.get_or_404(assignment_id)

    try:
        # Aggiorna assignment
        assignment.status = 'finance_rejected'
        assignment.finance_approved = False
        assignment.finance_approved_by = current_user.id
        assignment.finance_approved_at = datetime.utcnow()
        assignment.finance_notes = request.form.get('rejection_reason', 'Motivo non specificato')

        # Aggiorna cliente
        cliente = assignment.cliente
        cliente.payment_status = 'rejected'
        cliente.service_status = 'blocked'

        # Crea nota di rigetto
        rejection_note = ServiceClienteNote(
            assignment_id=assignment_id,
            cliente_id=cliente.cliente_id,
            note_text=f"Pagamento RIGETTATO da {current_user.nome_cognome}. Motivo: {assignment.finance_notes}",
            note_type='finance_rejection',
            created_by=current_user.id,
            visible_to_professionals=True
        )
        db.session.add(rejection_note)

        db.session.commit()

        flash('Pagamento rigettato. Il cliente è stato bloccato.', 'warning')

        # TODO: Notifica sales per follow-up
        # send_sales_alert.delay(cliente.cliente_id, 'payment_rejected')

        return redirect(url_for('finance.ghl_dashboard'))

    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il rigetto: {str(e)}', 'danger')
        return redirect(url_for('finance.verify_payment', assignment_id=assignment_id))


@bp.route('/dashboard/bulk_actions', methods=['POST'])
@login_required
def bulk_actions():
    """Azioni bulk su più assignments"""
    if not has_permission(current_user, FinancePerm.APPROVE_PAYMENT):
        return jsonify({'error': 'Permessi insufficienti'}), 403

    action = request.form.get('action')
    assignment_ids = request.form.getlist('assignment_ids[]', type=int)

    if not assignment_ids:
        return jsonify({'error': 'Nessun elemento selezionato'}), 400

    try:
        if action == 'approve_all':
            for aid in assignment_ids:
                assignment = ServiceClienteAssignment.query.get(aid)
                if assignment and assignment.status == 'pending_finance':
                    assignment.status = 'finance_approved'
                    assignment.finance_approved = True
                    assignment.finance_approved_by = current_user.id
                    assignment.finance_approved_at = datetime.utcnow()

                    assignment.cliente.payment_status = 'verified'
                    assignment.cliente.service_status = 'ready_for_assignment'

            db.session.commit()
            return jsonify({'success': True, 'message': f'{len(assignment_ids)} pagamenti approvati'})

        elif action == 'export':
            # TODO: Implementare export Excel
            return jsonify({'success': False, 'message': 'Export non ancora implementato'})

        else:
            return jsonify({'error': 'Azione non valida'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def _get_payment_suggestions(cliente, opportunity):
    """Genera suggerimenti automatici per la verifica pagamento"""
    suggestions = []

    if opportunity:
        # Controlla se l'importo corrisponde a pacchetti standard
        standard_packages = FinancePackage.query.filter_by(is_active=True).all()
        for package in standard_packages:
            if package.price == opportunity.importo_totale:
                suggestions.append({
                    'type': 'package_match',
                    'message': f'Corrisponde al pacchetto standard: {package.name}',
                    'confidence': 'high'
                })

        # Controlla pattern di pagamento
        if opportunity.acconto_pagato and opportunity.importo_totale:
            ratio = float(opportunity.acconto_pagato) / float(opportunity.importo_totale)
            if abs(ratio - 0.333) < 0.01:
                suggestions.append({
                    'type': 'payment_pattern',
                    'message': 'Acconto standard 33% rilevato',
                    'confidence': 'high'
                })
            elif abs(ratio - 0.5) < 0.01:
                suggestions.append({
                    'type': 'payment_pattern',
                    'message': 'Acconto 50% rilevato',
                    'confidence': 'high'
                })

    # Controlla storico cliente (se esistente)
    if cliente.mail:
        similar_clients = Cliente.query.filter(
            Cliente.mail.like(f"%{cliente.mail.split('@')[0]}%"),
            Cliente.cliente_id != cliente.cliente_id
        ).limit(3).all()

        if similar_clients:
            suggestions.append({
                'type': 'similar_clients',
                'message': f'Trovati {len(similar_clients)} clienti simili nel database',
                'confidence': 'medium'
            })

    return suggestions
"""
Routes Feedback Global - FASE 1 + FASE 2

FASE 1:
- suggest_idea: Form globale suggerimento idee
- report_issue: Form globale segnalazione problemi

FASE 2:
- my_contributions: Dashboard personale contributi utente
- Admin actions: Approve/Reject/Pending con motivazioni obbligatorie
"""
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import desc
from datetime import datetime

from corposostenibile.extensions import db
from corposostenibile.models import (
    BlueprintRegistry, BlueprintIssue, BlueprintImprovement,
    ImprovementStatusEnum, IssueStatusEnum
)
from . import bp
from .notifications import (
    send_idea_notification,
    send_issue_notification,
    send_idea_status_email,
    send_issue_status_email
)


# ═══════════════════════════════════════════════════════════════════════════
#                           FASE 1 - FORM GLOBALI
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/suggest-idea', methods=['GET', 'POST'])
@login_required
def suggest_idea():
    """
    💡 Form globale per suggerire idee di miglioramento.

    FASE 1: Tutti gli utenti possono suggerire idee selezionando il modulo.
    """
    if request.method == 'POST':
        blueprint_code = request.form.get('blueprint_code')
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority', 'medium')
        expected_impact = request.form.get('expected_impact', '')

        # Validazione
        if not blueprint_code or not title:
            flash('Modulo e Titolo sono obbligatori', 'error')
            return redirect(url_for('feedback_global.suggest_idea'))

        # Trova blueprint
        blueprint = BlueprintRegistry.query.filter_by(code=blueprint_code).first()
        if not blueprint:
            flash('Modulo non trovato', 'error')
            return redirect(url_for('feedback_global.suggest_idea'))

        try:
            # Crea improvement
            improvement = BlueprintImprovement(
                blueprint_id=blueprint.id,
                title=title,
                description=description,
                priority=priority,
                expected_impact=expected_impact,
                proposed_by_id=current_user.id,
                status=ImprovementStatusEnum.proposed
            )

            db.session.add(improvement)
            db.session.commit()

            # 📧 Notifica owner del blueprint (se esiste)
            send_idea_notification(improvement, blueprint)

            flash(
                f'✨ Idea "{title}" inviata per il modulo {blueprint.name}! '
                f'Il team la valuterà e riceverai una notifica via email.',
                'success'
            )
            return redirect(url_for('feedback_global.my_contributions'))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'invio: {str(e)}', 'error')
            return redirect(url_for('feedback_global.suggest_idea'))

    # GET - Mostra form
    blueprints = BlueprintRegistry.query.filter(
        BlueprintRegistry.status.in_(['active', 'beta'])
    ).order_by(BlueprintRegistry.name).all()

    return render_template(
        'feedback_global/suggest_idea.html',
        blueprints=blueprints
    )


@bp.route('/report-issue', methods=['GET', 'POST'])
@login_required
def report_issue():
    """
    🐛 Form globale per segnalare problemi/bug.

    FASE 1: Tutti gli utenti possono segnalare issue selezionando il modulo.
    """
    if request.method == 'POST':
        blueprint_code = request.form.get('blueprint_code')
        title = request.form.get('title')
        description = request.form.get('description')
        severity = request.form.get('severity', 'minor')

        # Validazione
        if not blueprint_code or not title:
            flash('Modulo e Titolo sono obbligatori', 'error')
            return redirect(url_for('feedback_global.report_issue'))

        # Trova blueprint
        blueprint = BlueprintRegistry.query.filter_by(code=blueprint_code).first()
        if not blueprint:
            flash('Modulo non trovato', 'error')
            return redirect(url_for('feedback_global.report_issue'))

        try:
            # Crea issue
            issue = BlueprintIssue(
                blueprint_id=blueprint.id,
                title=title,
                description=description,
                severity=severity,
                reported_by_id=current_user.id,
                status=IssueStatusEnum.open
            )

            db.session.add(issue)
            db.session.commit()

            # 📧 Notifica team tecnico (owner blueprint + admin)
            send_issue_notification(issue, blueprint)

            # Flash message diverso per severity
            if severity in ['blocker', 'critical']:
                flash(
                    f'🚨 Issue critico "{title}" segnalato per {blueprint.name}! '
                    f'Il team tecnico è stato allertato.',
                    'warning'
                )
            else:
                flash(
                    f'🐛 Issue "{title}" segnalato per {blueprint.name}! '
                    f'Riceverai aggiornamenti via email.',
                    'success'
                )

            return redirect(url_for('feedback_global.my_contributions'))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la segnalazione: {str(e)}', 'error')
            return redirect(url_for('feedback_global.report_issue'))

    # GET - Mostra form
    blueprints = BlueprintRegistry.query.filter(
        BlueprintRegistry.status.in_(['active', 'beta'])
    ).order_by(BlueprintRegistry.name).all()

    return render_template(
        'feedback_global/report_issue.html',
        blueprints=blueprints
    )


# ═══════════════════════════════════════════════════════════════════════════
#                      FASE 2 - DASHBOARD CONTRIBUTI
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/my-contributions')
@login_required
def my_contributions():
    """
    📊 Dashboard personale contributi utente.

    FASE 2: Mostra tutte le idee e issue dell'utente con stato aggiornato.
    """
    # Idee proposte dall'utente
    my_ideas = BlueprintImprovement.query.filter_by(
        proposed_by_id=current_user.id
    ).order_by(desc(BlueprintImprovement.created_at)).all()

    # Issues segnalati dall'utente
    my_issues = BlueprintIssue.query.filter_by(
        reported_by_id=current_user.id
    ).order_by(desc(BlueprintIssue.created_at)).all()

    # Statistiche
    stats = {
        'total_ideas': len(my_ideas),
        'ideas_proposed': sum(1 for i in my_ideas if i.status == ImprovementStatusEnum.proposed),
        'ideas_approved': sum(1 for i in my_ideas if i.status == ImprovementStatusEnum.approved),
        'ideas_in_development': sum(1 for i in my_ideas if i.status == ImprovementStatusEnum.in_development),
        'ideas_implemented': sum(1 for i in my_ideas if i.status == ImprovementStatusEnum.completed),
        'ideas_rejected': sum(1 for i in my_ideas if i.status == ImprovementStatusEnum.rejected),

        'total_issues': len(my_issues),
        'issues_open': sum(1 for i in my_issues if i.status == IssueStatusEnum.open),
        'issues_in_progress': sum(1 for i in my_issues if i.status == IssueStatusEnum.in_progress),
        'issues_resolved': sum(1 for i in my_issues if i.status == IssueStatusEnum.resolved),
        'issues_wontfix': sum(1 for i in my_issues if i.status == IssueStatusEnum.wontfix),
    }

    return render_template(
        'feedback_global/my_contributions.html',
        my_ideas=my_ideas,
        my_issues=my_issues,
        stats=stats
    )


# ═══════════════════════════════════════════════════════════════════════════
#                    FASE 2 - ADMIN ACTIONS (CON MOTIVAZIONI)
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/admin/idea/<int:idea_id>/approve', methods=['POST'])
@login_required
def admin_approve_idea(idea_id):
    """
    ✅ Admin approva idea CON MOTIVAZIONE OBBLIGATORIA.

    FASE 2: Motivazione obbligatoria + email notification all'utente.
    """
    if not current_user.is_admin:
        flash('Solo gli admin possono approvare idee', 'error')
        abort(403)

    idea = BlueprintImprovement.query.get_or_404(idea_id)
    motivation = request.form.get('motivation', '').strip()

    # Validazione motivazione obbligatoria
    if not motivation:
        flash('La motivazione è obbligatoria per approvare un\'idea', 'error')
        return redirect(request.referrer or url_for('blueprint_registry.detail', code=idea.blueprint.code))

    try:
        idea.status = ImprovementStatusEnum.approved
        idea.approved_by_id = current_user.id
        idea.approved_at = datetime.utcnow()
        idea.approval_motivation = motivation
        idea.notified_at = datetime.utcnow()

        db.session.commit()

        # 📧 Invia email con motivazione
        send_idea_status_email(idea, 'approved', motivation)

        flash(
            f'✅ Idea "{idea.title}" approvata! '
            f'{idea.proposed_by.first_name} è stato notificato via email.',
            'success'
        )

        return redirect(request.referrer or url_for('blueprint_registry.detail', code=idea.blueprint.code))

    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'approvazione: {str(e)}', 'error')
        return redirect(request.referrer)


@bp.route('/admin/idea/<int:idea_id>/reject', methods=['POST'])
@login_required
def admin_reject_idea(idea_id):
    """
    ❌ Admin rigetta idea CON MOTIVAZIONE OBBLIGATORIA.

    FASE 2: Motivazione obbligatoria + email notification all'utente.
    """
    if not current_user.is_admin:
        flash('Solo gli admin possono rigettare idee', 'error')
        abort(403)

    idea = BlueprintImprovement.query.get_or_404(idea_id)
    motivation = request.form.get('motivation', '').strip()

    # Validazione motivazione obbligatoria
    if not motivation:
        flash('La motivazione è obbligatoria per rigettare un\'idea', 'error')
        return redirect(request.referrer or url_for('blueprint_registry.detail', code=idea.blueprint.code))

    try:
        idea.status = ImprovementStatusEnum.rejected
        idea.rejection_motivation = motivation
        idea.notified_at = datetime.utcnow()

        db.session.commit()

        # 📧 Invia email con motivazione
        send_idea_status_email(idea, 'rejected', motivation)

        flash(
            f'❌ Idea "{idea.title}" rigettata. '
            f'{idea.proposed_by.first_name} è stato notificato con la motivazione.',
            'info'
        )

        return redirect(request.referrer or url_for('blueprint_registry.detail', code=idea.blueprint.code))

    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante il rigetto: {str(e)}', 'error')
        return redirect(request.referrer)


@bp.route('/admin/idea/<int:idea_id>/set-pending', methods=['POST'])
@login_required
def admin_set_idea_pending(idea_id):
    """
    ⏸️ Admin mette idea IN SOSPESO CON MOTIVAZIONE.

    FASE 2: Spiega perché l'idea è in sospeso (es: "serve più info").
    """
    if not current_user.is_admin:
        flash('Solo gli admin possono gestire le idee', 'error')
        abort(403)

    idea = BlueprintImprovement.query.get_or_404(idea_id)
    motivation = request.form.get('motivation', '').strip()

    if not motivation:
        flash('La motivazione è obbligatoria per mettere in sospeso', 'error')
        return redirect(request.referrer or url_for('blueprint_registry.detail', code=idea.blueprint.code))

    try:
        idea.pending_motivation = motivation
        idea.notified_at = datetime.utcnow()

        db.session.commit()

        # 📧 Invia email
        send_idea_status_email(idea, 'pending', motivation)

        flash(
            f'⏸️ Idea "{idea.title}" messa in sospeso. '
            f'Utente notificato.',
            'info'
        )

        return redirect(request.referrer or url_for('blueprint_registry.detail', code=idea.blueprint.code))

    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'error')
        return redirect(request.referrer)


@bp.route('/admin/idea/<int:idea_id>/mark-implemented', methods=['POST'])
@login_required
def admin_mark_idea_implemented(idea_id):
    """
    🎉 Admin marca idea come IMPLEMENTATA con note completamento.

    FASE 2: Note implementazione + email celebrativa all'utente!
    """
    if not current_user.is_admin:
        flash('Solo gli admin possono marcare idee implementate', 'error')
        abort(403)

    idea = BlueprintImprovement.query.get_or_404(idea_id)
    completion_notes = request.form.get('completion_notes', '').strip()

    if not completion_notes:
        flash('Note di completamento obbligatorie', 'error')
        return redirect(request.referrer or url_for('blueprint_registry.detail', code=idea.blueprint.code))

    try:
        idea.status = ImprovementStatusEnum.completed
        idea.completed_at = datetime.utcnow()
        idea.completion_notes = completion_notes
        idea.notified_at = datetime.utcnow()

        db.session.commit()

        # 📧 Email celebrativa
        send_idea_status_email(idea, 'implemented', completion_notes)

        flash(
            f'🎉 Idea "{idea.title}" marcata come implementata! '
            f'{idea.proposed_by.first_name} riceverà email celebrativa.',
            'success'
        )

        return redirect(request.referrer or url_for('blueprint_registry.detail', code=idea.blueprint.code))

    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'error')
        return redirect(request.referrer)


# ───────────────────────────────────────────────────────────────────────────
# ADMIN ACTIONS - ISSUE
# ───────────────────────────────────────────────────────────────────────────

@bp.route('/admin/issue/<int:issue_id>/acknowledge', methods=['POST'])
@login_required
def admin_acknowledge_issue(issue_id):
    """
    👀 Admin prende in carico issue con messaggio.

    FASE 2: Messaggio acknowledgment + email utente.
    """
    if not current_user.is_admin:
        abort(403)

    issue = BlueprintIssue.query.get_or_404(issue_id)
    message = request.form.get('message', '').strip()

    if not message:
        flash('Messaggio obbligatorio per presa in carico', 'error')
        return redirect(request.referrer)

    try:
        issue.status = IssueStatusEnum.in_progress
        issue.acknowledgment_message = message
        issue.assigned_to_id = current_user.id
        issue.notified_at = datetime.utcnow()

        db.session.commit()

        # 📧 Email
        send_issue_status_email(issue, 'acknowledged', message)

        flash(f'👀 Issue "{issue.title}" preso in carico', 'success')
        return redirect(request.referrer)

    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'error')
        return redirect(request.referrer)


@bp.route('/admin/issue/<int:issue_id>/resolve', methods=['POST'])
@login_required
def admin_resolve_issue(issue_id):
    """
    ✅ Admin risolve issue CON MOTIVAZIONE.

    FASE 2: Spiega come è stato risolto + email utente.
    """
    if not current_user.is_admin:
        abort(403)

    issue = BlueprintIssue.query.get_or_404(issue_id)
    motivation = request.form.get('motivation', '').strip()

    if not motivation:
        flash('Motivazione risoluzione obbligatoria', 'error')
        return redirect(request.referrer)

    try:
        issue.status = IssueStatusEnum.resolved
        issue.resolved_at = datetime.utcnow()
        issue.resolution_motivation = motivation
        issue.notified_at = datetime.utcnow()

        db.session.commit()

        # 📧 Email
        send_issue_status_email(issue, 'resolved', motivation)

        flash(f'✅ Issue "{issue.title}" risolto', 'success')
        return redirect(request.referrer)

    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'error')
        return redirect(request.referrer)


@bp.route('/admin/issue/<int:issue_id>/wontfix', methods=['POST'])
@login_required
def admin_wontfix_issue(issue_id):
    """
    🚫 Admin marca issue come Won't Fix CON MOTIVAZIONE.

    FASE 2: Spiega perché non verrà fixato + email utente.
    """
    if not current_user.is_admin:
        abort(403)

    issue = BlueprintIssue.query.get_or_404(issue_id)
    motivation = request.form.get('motivation', '').strip()

    if not motivation:
        flash('Motivazione obbligatoria per Won\'t Fix', 'error')
        return redirect(request.referrer)

    try:
        issue.status = IssueStatusEnum.wontfix
        issue.wontfix_motivation = motivation
        issue.notified_at = datetime.utcnow()

        db.session.commit()

        # 📧 Email
        send_issue_status_email(issue, 'wontfix', motivation)

        flash(f'🚫 Issue "{issue.title}" marcato Won\'t Fix', 'info')
        return redirect(request.referrer)

    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'error')
        return redirect(request.referrer)

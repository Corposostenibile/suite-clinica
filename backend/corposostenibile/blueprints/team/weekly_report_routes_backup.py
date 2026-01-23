"""
Routes per i Report Settimanali
===============================

Gestione della compilazione e visualizzazione dei report settimanali.
"""
from __future__ import annotations

from datetime import datetime, date, timedelta
from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
    abort,
    jsonify,
    current_app
)
from flask_login import login_required, current_user
from sqlalchemy import and_, or_

from corposostenibile.extensions import db
from corposostenibile.models import User, Department, Objective, DepartmentObjective, OKRStatusEnum
from .models.weekly_report import WeeklyReport
from .weekly_report_forms import (
    WeeklyReportStep1Form,
    WeeklyReportStep2Form,
    WeeklyReportStep2UnifiedForm,
    WeeklyReportStep3Form,
    WeeklyReportStep4Form,
    WeeklyReportStep5Form,
    WeeklyReportStep6Form,
    WeeklyReportStep6IdeasForm,
    WeeklyReportStep7Form,
    WeeklyReportCompleteForm,
    SalesReportStep1Form,
    SalesReportStep2Form,
    SalesReportStep3Form
)

# Blueprint setup
weekly_report_bp = Blueprint(
    'weekly_report',
    __name__,
    url_prefix='/team/weekly-report'
)


def get_current_quarter():
    """Calcola il quarter corrente (Q1-Q4) e restituisce come enum OKRPeriodEnum."""
    from corposostenibile.models import OKRPeriodEnum
    month = date.today().month
    quarter_num = (month - 1) // 3 + 1
    quarter_map = {1: OKRPeriodEnum.q1, 2: OKRPeriodEnum.q2, 3: OKRPeriodEnum.q3, 4: OKRPeriodEnum.q4}
    return quarter_map[quarter_num]


@weekly_report_bp.route('/')
@login_required
def index():
    """Dashboard dei report settimanali."""
    # Determina la settimana da visualizzare
    week_offset = request.args.get('week', 0, type=int)
    today = date.today()
    
    # Calcola il lunedì della settimana richiesta
    current_monday = today - timedelta(days=today.weekday())
    target_monday = current_monday + timedelta(weeks=week_offset)
    target_sunday = target_monday + timedelta(days=6)
    
    # Recupera i report in base ai permessi
    current_app.logger.info(f"Checking permissions for user {current_user.id} - is_admin: {current_user.is_admin}")
    if current_user.department:
        current_app.logger.info(f"User department: {current_user.department.name} (id: {current_user.department_id})")
        current_app.logger.info(f"Department head_id: {current_user.department.head_id}")
        current_app.logger.info(f"Is user head? {current_user.department.head_id == current_user.id}")
    
    if current_user.is_admin:
        # Admin vede TUTTI i report
        reports = WeeklyReport.query.filter_by(week_start=target_monday).all()
        department_filter = request.args.get('department_id', type=int)
        if department_filter:
            reports = [r for r in reports if r.department_id == department_filter]
    elif current_user.department and current_user.department.head_id == current_user.id:
        # Head of department vede quelli del suo dipartimento + CEO
        current_app.logger.info(f"User {current_user.id} is head of department {current_user.department_id}")
        current_app.logger.info(f"Department name: {current_user.department.name}")
        
        ceo_dept = Department.query.filter_by(name="CEO").first()
        if ceo_dept:
            reports = WeeklyReport.query.filter(
                and_(
                    WeeklyReport.week_start == target_monday,
                    or_(
                        WeeklyReport.department_id == current_user.department_id,
                        WeeklyReport.department_id == ceo_dept.id
                    )
                )
            ).all()
            current_app.logger.info(f"Found {len(reports)} reports for head of {current_user.department.name}")
            for r in reports:
                current_app.logger.info(f"  - Report from {r.user.full_name} (dept: {r.department_id})")
        else:
            # Se non c'è il dipartimento CEO, vede solo quelli del suo dipartimento
            reports = WeeklyReport.query.filter_by(
                week_start=target_monday,
                department_id=current_user.department_id
            ).all()
    else:
        # Utente normale vede SOLO il suo report + quelli del dipartimento CEO
        ceo_dept = Department.query.filter_by(name="CEO").first()
        current_app.logger.info(f"CEO Department: {ceo_dept.id if ceo_dept else 'Not found'}")
        
        if ceo_dept:
            reports = WeeklyReport.query.filter(
                and_(
                    WeeklyReport.week_start == target_monday,
                    or_(
                        WeeklyReport.user_id == current_user.id,
                        WeeklyReport.department_id == ceo_dept.id
                    )
                )
            ).all()
            current_app.logger.info(f"Found {len(reports)} reports for user {current_user.id}")
        else:
            # Se non c'è il dipartimento CEO, vede solo i suoi
            reports = WeeklyReport.query.filter_by(
                week_start=target_monday,
                user_id=current_user.id
            ).all()
    
    # Statistiche
    total_reports = len(reports)
    departments = Department.query.all() if current_user.is_admin else []
    
    # Verifica se l'utente può/deve compilare il report
    can_submit = WeeklyReport.can_submit_report(current_user.id)
    has_submitted = WeeklyReport.user_has_report_this_period(current_user.id)
    is_sales = current_user.department and WeeklyReport.is_sales_department(current_user.department.name)
    
    # Calcola la prossima data di compilazione per i Sales
    next_compilation_date = None
    if is_sales:
        import calendar
        today = date.today()
        
        # Trova l'ultimo sabato del mese corrente
        last_day = calendar.monthrange(today.year, today.month)[1]
        last_date = date(today.year, today.month, last_day)
        
        # Trova l'ultimo sabato del mese
        while last_date.weekday() != 5:  # 5 = sabato
            last_date = last_date - timedelta(days=1)
        
        # Se siamo già passati l'ultimo sabato del mese, calcola il prossimo
        if today > last_date:
            # Vai al mese successivo
            if today.month == 12:
                next_month = 1
                next_year = today.year + 1
            else:
                next_month = today.month + 1
                next_year = today.year
            
            # Trova l'ultimo sabato del mese successivo
            last_day = calendar.monthrange(next_year, next_month)[1]
            last_date = date(next_year, next_month, last_day)
            
            while last_date.weekday() != 5:  # 5 = sabato
                last_date = last_date - timedelta(days=1)
        
        next_compilation_date = last_date
    
    return render_template(
        'team/weekly_report/index.html',
        reports=reports,
        week_start=target_monday,
        week_end=target_sunday,
        week_offset=week_offset,
        total_reports=total_reports,
        departments=departments,
        can_submit=can_submit,
        has_submitted=has_submitted,
        is_sales=is_sales,
        next_compilation_date=next_compilation_date,
        selected_department=request.args.get('department_id')
    )


@weekly_report_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_report():
    """Wizard multi-step per nuovo report."""
    # Determina se è un dipartimento Sales
    is_sales = current_user.department and WeeklyReport.is_sales_department(current_user.department.name)
    
    # Verifica se può compilare
    if not WeeklyReport.can_submit_report(current_user.id):
        if is_sales:
            flash("Puoi compilare il report mensile solo l'ultimo sabato del mese.", "warning")
        else:
            flash("Puoi compilare il report solo venerdì, sabato o domenica.", "warning")
        return redirect(url_for('weekly_report.index'))
    
    # Verifica se ha già compilato
    if WeeklyReport.user_has_report_this_period(current_user.id):
        if is_sales:
            flash("Hai già compilato il report mensile per questo mese.", "info")
        else:
            flash("Hai già compilato il report per questa settimana.", "info")
        return redirect(url_for('weekly_report.index'))
    
    # Gestione step
    step = request.args.get('step', 1, type=int)
    current_app.logger.info(f"GET request for step {step} - is_sales: {is_sales}")
    
    # Numero massimo di step differente per Sales vs normali
    max_steps = 4 if is_sales else 4  # Entrambi hanno 4 step ora (Welcome, Domande, Idee, Complete)
    if step < 1 or step > max_steps:
        return redirect(url_for('weekly_report.new_report', step=1))
    
    # Form differenti per Sales vs normali
    if is_sales:
        forms = {
            1: SalesReportStep1Form(),
            2: SalesReportStep2Form(),
            3: SalesReportStep3Form(),
        }
    else:
        forms = {
            1: WeeklyReportStep1Form(),
            2: WeeklyReportStep2Form(),  # OKR Dipartimento + Personali insieme
            3: WeeklyReportStep3Form(),  # Solo idee
        }
    
    form = forms.get(step)
    
    # Ripristina i dati dalla sessione se disponibili (per quando si torna indietro)
    if request.method == 'GET':
        if is_sales:
            # Sales workflow
            if step == 2:
                if 'main_obstacle' in session:
                    form.main_obstacle.data = session.get('main_obstacle')
                if 'obstacle_suggestions' in session:
                    form.obstacle_suggestions.data = session.get('obstacle_suggestions')
                if 'work_improvements' in session:
                    form.work_improvements.data = session.get('work_improvements')
            elif step == 3 and 'ideas' in session:
                form.ideas.data = session.get('ideas')
        else:
            # Normal workflow - Step 2 ha entrambi i campi OKR
            if step == 2:
                if 'department_reflection' in session:
                    form.department_reflection.data = session.get('department_reflection')
                if 'personal_reflection' in session:
                    form.personal_reflection.data = session.get('personal_reflection')
            elif step == 3 and 'ideas' in session:
                form.ideas.data = session.get('ideas')
    
    # Dati aggiuntivi per alcuni step
    context = {
        'form': form,
        'step': step,
        'total_steps': max_steps,
        'is_sales': is_sales,
        'department_name': current_user.department.name if current_user.department else "N/A"
    }
    
    # Per workflow normale - Step 2 mostra OKR Dipartimento e Personali
    if not is_sales and step == 2:
        quarter = get_current_quarter()
        
        # OKR Dipartimento
        dept_okrs = []
        if current_user.department:
            dept_okrs = DepartmentObjective.query.filter_by(
                department_id=current_user.department_id,
                status=OKRStatusEnum.active
            ).filter(
                DepartmentObjective.period.contains(quarter.value)
            ).all()
        
        # OKR Personali
        user_okrs = Objective.query.filter_by(
            user_id=current_user.id,
            period=quarter,
            status=OKRStatusEnum.active
        ).all()
        
        context['department_okrs'] = dept_okrs
        context['user_okrs'] = user_okrs
        context['quarter'] = quarter.value.upper()  # q1 -> Q1
    
    # Gestione POST
    if request.method == 'POST':
        current_app.logger.info(f"POST request for step {step} - is_sales: {is_sales}")
        action = request.form.get('action', 'next')
        
        # Salva sempre i dati in sessione (anche se il form non è valido o si va indietro)
        if is_sales:
            # Sales workflow
            if step == 2:
                session['main_obstacle'] = form.main_obstacle.data
                session['obstacle_suggestions'] = form.obstacle_suggestions.data
                session['work_improvements'] = form.work_improvements.data
            elif step == 3:
                session['ideas'] = form.ideas.data or ''
        else:
            # Normal workflow
            if step == 2:
                session['department_reflection'] = form.department_reflection.data
                session['personal_reflection'] = form.personal_reflection.data
            elif step == 3:
                session['ideas'] = form.ideas.data or ''
        
        # Se l'utente ha cliccato "Indietro", vai allo step precedente
        if action == 'back' and step > 1:
            return redirect(url_for('weekly_report.new_report', step=step - 1))
        
        # Altrimenti continua con la validazione normale
        if not form.validate_on_submit():
            current_app.logger.warning(f"Form validation failed for step {step}: {form.errors}")
            flash("Errore nella validazione del form. Controlla i campi.", "warning")
        else:
            # Se siamo all'ultimo step prima del completamento (step 3), salva il report
            if step == 3:
                # Determina i campi richiesti in base al tipo di report
                if is_sales:
                    required_fields = ['main_obstacle', 'obstacle_suggestions', 'work_improvements']
                else:
                    required_fields = ['department_reflection', 'personal_reflection']
                
                missing_fields = [field for field in required_fields if not session.get(field)]
                
                if missing_fields:
                    flash(f"Dati mancanti: {', '.join(missing_fields)}. Per favore ricompila il form dall'inizio.", "warning")
                    return redirect(url_for('weekly_report.new_report', step=1))
                
                # Salva il report completo
                monday, sunday = WeeklyReport.get_current_week_dates()
                
                # Crea il report con i dati appropriati
                if is_sales:
                    report = WeeklyReport(
                        user_id=current_user.id,
                        department_id=current_user.department_id,
                        week_start=monday,
                        week_end=sunday,
                        main_obstacle=session.get('main_obstacle'),
                        obstacle_suggestions=session.get('obstacle_suggestions'),
                        work_improvements=session.get('work_improvements'),
                        ideas=session.get('ideas', ''),
                        report_type='monthly'
                    )
                else:
                    report = WeeklyReport(
                        user_id=current_user.id,
                        department_id=current_user.department_id,
                        week_start=monday,
                        week_end=sunday,
                        department_reflection=session.get('department_reflection'),
                        personal_reflection=session.get('personal_reflection'),
                        ideas=session.get('ideas', ''),
                        report_type='weekly'
                    )
                
                try:
                    db.session.add(report)
                    db.session.commit()
                    
                    # Pulisci sessione - rimuovi tutti i campi possibili
                    session_keys = [
                        'department_reflection', 'personal_reflection', 
                        'weekly_victory', 'areas_to_improve', 
                        'main_obstacle', 'ideas',
                        'obstacle_suggestions', 'work_improvements'
                    ]
                    for key in session_keys:
                        session.pop(key, None)
                    
                    # Vai allo step finale
                    return redirect(url_for('weekly_report.new_report', step=4))
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Errore salvataggio report: {str(e)}")
                    flash(f"Errore nel salvataggio del report: {str(e)}", "danger")
                    return redirect(url_for('weekly_report.new_report', step=step))
            
            # Passa allo step successivo
            if step < 3:
                current_app.logger.info(f"Redirecting from step {step} to step {step + 1}")
                return redirect(url_for('weekly_report.new_report', step=step + 1))
    
    # Step 4: Ringraziamento finale
    if step == 4:
        return render_template('team/weekly_report/step4_complete.html', **context)
    
    # Render del template appropriato per ogni step
    if is_sales:
        # Template specifici per Sales
        if step == 1:
            return render_template('team/weekly_report/step1.html', **context)
        elif step == 2:
            return render_template('team/weekly_report/step2_sales.html', **context)
        elif step == 3:
            return render_template('team/weekly_report/step3_ideas.html', **context)
    else:
        # Template per workflow normale
        if step == 1:
            return render_template('team/weekly_report/step1.html', **context)
        elif step == 2:
            return render_template('team/weekly_report/step2_combined.html', **context)
        elif step == 3:
            return render_template('team/weekly_report/step3_ideas.html', **context)
    
    # Fallback (non dovrebbe mai arrivare qui)
    return render_template(f'team/weekly_report/step{step}.html', **context)


@weekly_report_bp.route('/<int:report_id>')
@login_required
def view_report(report_id):
    """Visualizza un singolo report."""
    report = WeeklyReport.query.get_or_404(report_id)
    
    # Verifica permessi
    if not current_user.is_admin:
        ceo_dept = Department.query.filter_by(name="CEO").first()
        ceo_dept_id = ceo_dept.id if ceo_dept else None
        
        # Head of department
        if hasattr(current_user, 'department') and current_user.department and \
           current_user.department.head_id == current_user.id:
            # Può vedere: suo dipartimento + CEO
            if report.department_id != current_user.department_id and \
               report.department_id != ceo_dept_id:
                abort(403)
        else:
            # Utente normale: può vedere solo il suo report + CEO
            if report.user_id != current_user.id and \
               report.department_id != ceo_dept_id:
                abort(403)
    
    # Carica OKR per contesto
    quarter = get_current_quarter()
    dept_okrs = []
    user_okrs = []
    
    if report.department:
        dept_okrs = DepartmentObjective.query.filter_by(
            department_id=report.department_id,
            status=OKRStatusEnum.active
        ).filter(
            DepartmentObjective.period.contains(quarter.value)
        ).all()
    
    user_okrs = Objective.query.filter_by(
        user_id=report.user_id,
        period=quarter,
        status=OKRStatusEnum.active
    ).all()
    
    return render_template(
        'team/weekly_report/view.html',
        report=report,
        department_okrs=dept_okrs,
        user_okrs=user_okrs,
        quarter=quarter.value.upper()  # q1 -> Q1
    )


@weekly_report_bp.route('/<int:report_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_report(report_id):
    """Modifica un report esistente (solo durante il weekend)."""
    report = WeeklyReport.query.get_or_404(report_id)
    
    # Verifica proprietà
    if report.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    # Verifica se può essere modificato
    if not report.can_be_edited and not current_user.is_admin:
        flash("Questo report non può più essere modificato.", "warning")
        return redirect(url_for('weekly_report.view_report', report_id=report_id))
    
    form = WeeklyReportCompleteForm(obj=report)
    
    if form.validate_on_submit():
        report.department_reflection = form.department_reflection.data
        report.personal_reflection = form.personal_reflection.data
        report.weekly_victory = form.weekly_victory.data
        report.areas_to_improve = form.areas_to_improve.data
        report.main_obstacle = form.main_obstacle.data
        report.ideas = form.ideas.data
        
        try:
            db.session.commit()
            flash("Report aggiornato con successo.", "success")
            return redirect(url_for('weekly_report.view_report', report_id=report_id))
        except Exception:
            db.session.rollback()
            flash("Errore nell'aggiornamento del report.", "danger")
    
    return render_template(
        'team/weekly_report/edit.html',
        form=form,
        report=report
    )


@weekly_report_bp.route('/<int:report_id>/delete', methods=['POST'])
@login_required
def delete_report(report_id):
    """Elimina un report (solo admin)."""
    if not current_user.is_admin:
        abort(403)
    
    report = WeeklyReport.query.get_or_404(report_id)
    
    try:
        db.session.delete(report)
        db.session.commit()
        flash("Report eliminato con successo.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Errore nell'eliminazione del report.", "danger")
        current_app.logger.error(f"Errore eliminazione report: {str(e)}")
    
    return redirect(url_for('weekly_report.index'))


@weekly_report_bp.route('/api/stats')
@login_required
def api_stats():
    """API per statistiche report (per grafici dashboard)."""
    if not current_user.is_admin:
        abort(403)
    
    # Statistiche ultime 12 settimane
    stats = []
    today = date.today()
    current_monday = today - timedelta(days=today.weekday())
    
    for i in range(12):
        week_start = current_monday - timedelta(weeks=i)
        week_reports = WeeklyReport.query.filter_by(week_start=week_start).all()
        
        stats.append({
            'week': week_start.strftime('%d/%m'),
            'total': len(week_reports),
            'by_department': {}
        })
        
        # Conta per dipartimento
        for report in week_reports:
            dept_name = report.department.name if report.department else 'N/A'
            if dept_name not in stats[-1]['by_department']:
                stats[-1]['by_department'][dept_name] = 0
            stats[-1]['by_department'][dept_name] += 1
    
    return jsonify(stats[::-1])  # Inverti per ordine cronologico
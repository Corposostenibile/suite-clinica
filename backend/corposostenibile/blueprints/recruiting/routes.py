"""
Routes principali per il modulo Recruiting
"""

from flask import render_template, redirect, url_for, flash, request, jsonify, abort, current_app, send_file
from flask_login import login_required, current_user
from corposostenibile.extensions import db
from sqlalchemy import func, and_
from corposostenibile.models import (
    JobOffer, JobQuestion, JobApplication, ApplicationAnswer,
    RecruitingKanban, KanbanStage, ApplicationStageHistory,
    JobOfferStatusEnum, ApplicationSourceEnum, ApplicationStatusEnum, KanbanStageTypeEnum
)
from .forms import JobOfferForm, ScreeningForm
from . import recruiting_bp
from .services.metrics_service import MetricsService, ANALYTICS_START_DATE
import json
import os
from datetime import datetime, timedelta


# ============================================================================
# DASHBOARD & OVERVIEW
# ============================================================================

@recruiting_bp.route("/")
@login_required
def index():
    """Dashboard principale recruiting."""
    # Statistiche
    stats = {
        'active_offers': JobOffer.query.filter_by(
            status=JobOfferStatusEnum.published
        ).count(),
        'total_applications': JobApplication.query.count(),
        'pending_review': JobApplication.query.filter_by(
            status='new'
        ).count(),
        'interviews_scheduled': JobApplication.query.filter_by(
            status='interview_scheduled'
        ).count(),
    }

    # Offerte recenti
    recent_offers = JobOffer.query.order_by(
        JobOffer.created_at.desc()
    ).limit(5).all()

    # Candidature recenti
    recent_applications = JobApplication.query.order_by(
        JobApplication.created_at.desc()
    ).limit(10).all()

    return render_template(
        "recruiting/index.html",
        stats=stats,
        recent_offers=recent_offers,
        recent_applications=recent_applications
    )


@recruiting_bp.route("/dashboard")
@login_required
def unified_dashboard():
    """Dashboard unificata con tab per metriche, offerte e pipeline."""
    from sqlalchemy.orm import joinedload
    from sqlalchemy import extract
    from dateutil.relativedelta import relativedelta

    # ========== FILTRI DATA ==========
    # Recupera parametri filtro data
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    filter_type = request.args.get('filter_type', 'month')  # month, quarter, year, custom

    # Calcola date in base al tipo di filtro
    today = datetime.now()

    if filter_type == 'month' and not start_date_str:
        # Inizio mese corrente
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif filter_type == 'quarter' and not start_date_str:
        # Inizio trimestre corrente
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif filter_type == 'year' and not start_date_str:
        # Inizio anno corrente
        start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif start_date_str and end_date_str:
        # Range custom
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    else:
        # Default: mese corrente
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)

    # ========== CALCOLO METRICHE GENERALI ==========

    # Query base per candidature nel periodo
    applications_query = JobApplication.query.filter(
        JobApplication.created_at >= start_date,
        JobApplication.created_at <= end_date
    )

    # 1. Numero candidature ricevute
    total_applications = applications_query.count()

    # 2. Assunzioni generate (status = hired)
    total_hires = applications_query.filter(
        JobApplication.status == ApplicationStatusEnum.hired
    ).count()

    # 3. Conversion Rate (candidature vs assunti)
    conversion_rate = round((total_hires / total_applications * 100), 2) if total_applications > 0 else 0

    # 4. Tempo medio assunzione (da ApplicationStageHistory)
    hired_apps = applications_query.filter(
        JobApplication.status == ApplicationStatusEnum.hired
    ).all()

    time_to_hire_days = 0
    if hired_apps:
        total_days = 0
        count = 0
        for app in hired_apps:
            # Cerca quando l'applicazione è entrata nello stage "hired" da ApplicationStageHistory
            hired_history = ApplicationStageHistory.query.filter_by(
                application_id=app.id
            ).join(
                KanbanStage,
                ApplicationStageHistory.stage_id == KanbanStage.id
            ).filter(
                KanbanStage.stage_type == KanbanStageTypeEnum.hired
            ).order_by(ApplicationStageHistory.entered_at.asc()).first()

            if hired_history and app.created_at:
                days = (hired_history.entered_at - app.created_at).days
                total_days += days
                count += 1
        time_to_hire_days = round(total_days / count, 1) if count > 0 else 0

    # 6. Score medio candidati
    applications_with_score = applications_query.filter(
        JobApplication.total_score.isnot(None)
    ).all()

    avg_score = 0
    if applications_with_score:
        total_score = sum(app.total_score for app in applications_with_score)
        avg_score = round(total_score / len(applications_with_score), 1)

    # ========== METRICHE PER PIATTAFORMA ==========
    from corposostenibile.models import JobOfferAdvertisingCost
    platform_metrics = []

    # Filtra solo le piattaforme principali (LinkedIn, Facebook, Instagram)
    main_platforms = [
        ApplicationSourceEnum.linkedin,
        ApplicationSourceEnum.facebook,
        ApplicationSourceEnum.instagram
    ]

    for source in main_platforms:
        # Candidature per fonte
        source_apps = applications_query.filter(JobApplication.source == source).all()
        apps_count = len(source_apps)

        # Assunti per fonte
        hires_count = len([app for app in source_apps if app.status == ApplicationStatusEnum.hired])

        # Conversion rate (candidature vs assunti)
        conv_rate = round((hires_count / apps_count * 100), 2) if apps_count > 0 else 0

        # Tempo medio assunzione
        hired_source_apps = [app for app in source_apps if app.status == ApplicationStatusEnum.hired]
        avg_time = 0
        if hired_source_apps:
            total_days = 0
            count = 0
            for app in hired_source_apps:
                # Cerca quando l'applicazione è entrata nello stage "hired" da ApplicationStageHistory
                hired_history = ApplicationStageHistory.query.filter_by(
                    application_id=app.id
                ).join(
                    KanbanStage,
                    ApplicationStageHistory.stage_id == KanbanStage.id
                ).filter(
                    KanbanStage.stage_type == KanbanStageTypeEnum.hired
                ).order_by(ApplicationStageHistory.entered_at.asc()).first()

                if hired_history and app.created_at:
                    days = (hired_history.entered_at - app.created_at).days
                    total_days += days
                    count += 1
            avg_time = round(total_days / count, 1) if count > 0 else 0

        # Score medio
        apps_with_score = [app for app in source_apps if app.total_score is not None]
        avg_source_score = 0
        if apps_with_score:
            avg_source_score = round(sum(app.total_score for app in apps_with_score) / len(apps_with_score), 1)

        # Costo totale per questa piattaforma (NUOVO SISTEMA)
        platform_cost = db.session.query(
            func.sum(JobOfferAdvertisingCost.amount)
        ).join(JobOffer).filter(
            JobOffer.status.in_([JobOfferStatusEnum.published, JobOfferStatusEnum.closed]),
            JobOfferAdvertisingCost.platform == source.value
        ).scalar() or 0

        # Costo per candidatura e per assunzione
        cost_per_app = round(platform_cost / apps_count, 2) if apps_count > 0 else 0
        cost_per_hire = round(platform_cost / hires_count, 2) if hires_count > 0 else 0

        platform_metrics.append({
            'source': source.value,
            'source_label': source.value.capitalize(),
            'applications': apps_count,
            'conversion_rate': conv_rate,
            'hires': hires_count,
            'avg_time_to_hire': avg_time,
            'avg_score': avg_source_score,
            'total_cost': round(platform_cost, 2),
            'cost_per_application': cost_per_app,
            'cost_per_hire': cost_per_hire
        })

    # ========== ANDAMENTO ULTIMI 12 MESI ==========
    monthly_trend = []

    for i in range(11, -1, -1):  # Ultimi 12 mesi
        month_date = today - relativedelta(months=i)
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Ultimo giorno del mese
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)

        # Conta candidature del mese
        month_apps = JobApplication.query.filter(
            JobApplication.created_at >= month_start,
            JobApplication.created_at <= month_end
        ).count()

        # Conta assunti del mese
        month_hires = JobApplication.query.filter(
            JobApplication.created_at >= month_start,
            JobApplication.created_at <= month_end,
            JobApplication.status == ApplicationStatusEnum.hired
        ).count()

        monthly_trend.append({
            'month': month_date.strftime('%b %Y'),
            'applications': month_apps,
            'hires': month_hires
        })

    # ========== METRICHE ECONOMICHE (NUOVO SISTEMA) ==========
    from corposostenibile.models import JobOfferAdvertisingCost

    # Calcola investimenti totali per piattaforma dalla tabella JobOfferAdvertisingCost
    # Query tutti i costi advertising per offerte pubblicate/chiuse
    total_investment_linkedin = db.session.query(
        func.sum(JobOfferAdvertisingCost.amount)
    ).join(JobOffer).filter(
        JobOffer.status.in_([JobOfferStatusEnum.published, JobOfferStatusEnum.closed]),
        JobOfferAdvertisingCost.platform == 'linkedin'
    ).scalar() or 0

    total_investment_facebook = db.session.query(
        func.sum(JobOfferAdvertisingCost.amount)
    ).join(JobOffer).filter(
        JobOffer.status.in_([JobOfferStatusEnum.published, JobOfferStatusEnum.closed]),
        JobOfferAdvertisingCost.platform == 'facebook'
    ).scalar() or 0

    total_investment_instagram = db.session.query(
        func.sum(JobOfferAdvertisingCost.amount)
    ).join(JobOffer).filter(
        JobOffer.status.in_([JobOfferStatusEnum.published, JobOfferStatusEnum.closed]),
        JobOfferAdvertisingCost.platform == 'instagram'
    ).scalar() or 0

    # Conteggio candidature e assunzioni per piattaforma (nel periodo filtrato)
    linkedin_apps = applications_query.filter(JobApplication.source == ApplicationSourceEnum.linkedin).count()
    facebook_apps = applications_query.filter(JobApplication.source == ApplicationSourceEnum.facebook).count()
    instagram_apps = applications_query.filter(JobApplication.source == ApplicationSourceEnum.instagram).count()

    linkedin_hires = applications_query.filter(
        JobApplication.source == ApplicationSourceEnum.linkedin,
        JobApplication.status == ApplicationStatusEnum.hired
    ).count()
    facebook_hires = applications_query.filter(
        JobApplication.source == ApplicationSourceEnum.facebook,
        JobApplication.status == ApplicationStatusEnum.hired
    ).count()
    instagram_hires = applications_query.filter(
        JobApplication.source == ApplicationSourceEnum.instagram,
        JobApplication.status == ApplicationStatusEnum.hired
    ).count()

    # Calcola costo per candidatura e costo per assunzione per piattaforma
    cost_per_application_linkedin = round(total_investment_linkedin / linkedin_apps, 2) if linkedin_apps > 0 else 0
    cost_per_application_facebook = round(total_investment_facebook / facebook_apps, 2) if facebook_apps > 0 else 0
    cost_per_application_instagram = round(total_investment_instagram / instagram_apps, 2) if instagram_apps > 0 else 0

    cost_per_hire_linkedin = round(total_investment_linkedin / linkedin_hires, 2) if linkedin_hires > 0 else 0
    cost_per_hire_facebook = round(total_investment_facebook / facebook_hires, 2) if facebook_hires > 0 else 0
    cost_per_hire_instagram = round(total_investment_instagram / instagram_hires, 2) if instagram_hires > 0 else 0

    # Metriche economiche aggregate
    economic_metrics = {
        'total_investment_linkedin': round(total_investment_linkedin, 2),
        'total_investment_facebook': round(total_investment_facebook, 2),
        'total_investment_instagram': round(total_investment_instagram, 2),
        'cost_per_application_linkedin': cost_per_application_linkedin,
        'cost_per_application_facebook': cost_per_application_facebook,
        'cost_per_application_instagram': cost_per_application_instagram,
        'cost_per_hire_linkedin': cost_per_hire_linkedin,
        'cost_per_hire_facebook': cost_per_hire_facebook,
        'cost_per_hire_instagram': cost_per_hire_instagram
    }

    # ========== ANDAMENTO ECONOMICO ULTIMI 12 MESI ==========
    economic_trend = []

    for i in range(11, -1, -1):  # Ultimi 12 mesi
        month_date = today - relativedelta(months=i)
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Ultimo giorno del mese
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)

        # Investimenti EFFETTIVI del mese corrente (dalla tabella JobOfferAdvertisingCost)
        # Filtra per year e month del mese corrente
        total_investment_month = db.session.query(
            func.sum(JobOfferAdvertisingCost.amount)
        ).join(JobOffer).filter(
            JobOffer.status.in_([JobOfferStatusEnum.published, JobOfferStatusEnum.closed]),
            JobOfferAdvertisingCost.year == month_date.year,
            JobOfferAdvertisingCost.month == month_date.month
        ).scalar() or 0

        # Candidature e assunzioni del mese
        month_apps = JobApplication.query.filter(
            JobApplication.created_at >= month_start,
            JobApplication.created_at <= month_end
        ).count()

        month_hires = JobApplication.query.filter(
            JobApplication.created_at >= month_start,
            JobApplication.created_at <= month_end,
            JobApplication.status == ApplicationStatusEnum.hired
        ).count()

        # Calcola costi medi
        cost_per_app_month = round(total_investment_month / month_apps, 2) if month_apps > 0 else 0
        cost_per_hire_month = round(total_investment_month / month_hires, 2) if month_hires > 0 else 0

        economic_trend.append({
            'month': month_date.strftime('%b %Y'),
            'total_investment': round(total_investment_month, 2),
            'cost_per_application': cost_per_app_month,
            'cost_per_hire': cost_per_hire_month
        })

    # ========== METRICHE ECONOMICHE AVANZATE (NUOVO SISTEMA) ==========

    # 1. BREAKDOWN PER PERIODO (decade del mese) - Ultimi 3 mesi
    period_breakdown = []
    for i in range(2, -1, -1):  # Ultimi 3 mesi
        month_date = today - relativedelta(months=i)

        # Query costi per ogni periodo (decade) di questo mese
        for period_value in ['1-10', '11-20', '21-30']:
            period_costs = db.session.query(
                JobOfferAdvertisingCost.platform,
                func.sum(JobOfferAdvertisingCost.amount).label('amount')
            ).join(JobOffer).filter(
                JobOffer.status.in_([JobOfferStatusEnum.published, JobOfferStatusEnum.closed]),
                JobOfferAdvertisingCost.year == month_date.year,
                JobOfferAdvertisingCost.month == month_date.month,
                JobOfferAdvertisingCost.period == period_value
            ).group_by(JobOfferAdvertisingCost.platform).all()

            # Crea dizionario con costi per piattaforma
            costs_by_platform = {cost.platform: float(cost.amount) for cost in period_costs}
            total_period = sum(costs_by_platform.values())

            period_breakdown.append({
                'year': month_date.year,
                'month': month_date.month,
                'month_name': month_date.strftime('%B %Y'),
                'period': period_value,
                'period_label': f"{period_value} {month_date.strftime('%b %Y')}",
                'linkedin': costs_by_platform.get('linkedin', 0),
                'facebook': costs_by_platform.get('facebook', 0),
                'instagram': costs_by_platform.get('instagram', 0),
                'total': total_period
            })

    # 2. ROI ANALYSIS per piattaforma
    roi_analysis = []
    for source in main_platforms:
        platform_name = source.value

        # Investimento totale
        investment = db.session.query(
            func.sum(JobOfferAdvertisingCost.amount)
        ).join(JobOffer).filter(
            JobOffer.status.in_([JobOfferStatusEnum.published, JobOfferStatusEnum.closed]),
            JobOfferAdvertisingCost.platform == platform_name
        ).scalar() or 0

        # Candidature e assunzioni
        apps_count = applications_query.filter(JobApplication.source == source).count()
        hires_count = applications_query.filter(
            JobApplication.source == source,
            JobApplication.status == ApplicationStatusEnum.hired
        ).count()

        # ROI metrics
        cost_per_app = round(investment / apps_count, 2) if apps_count > 0 else 0
        cost_per_hire = round(investment / hires_count, 2) if hires_count > 0 else 0
        roi_score = round((hires_count / investment * 1000), 2) if investment > 0 else 0  # Assunzioni per €1000

        roi_analysis.append({
            'platform': platform_name,
            'platform_label': platform_name.capitalize(),
            'investment': round(investment, 2),
            'applications': apps_count,
            'hires': hires_count,
            'cost_per_application': cost_per_app,
            'cost_per_hire': cost_per_hire,
            'roi_score': roi_score,
            'conversion_rate': round((hires_count / apps_count * 100), 2) if apps_count > 0 else 0
        })

    # Ordina per ROI score (migliore prima)
    roi_analysis_sorted = sorted(roi_analysis, key=lambda x: x['roi_score'], reverse=True)

    # 3. TOP 10 OFFERTE PER COSTO
    top_offers_by_cost = db.session.query(
        JobOffer.id,
        JobOffer.title,
        JobOffer.status,
        func.sum(JobOfferAdvertisingCost.amount).label('total_cost'),
        func.count(JobApplication.id).label('applications_count')
    ).join(
        JobOfferAdvertisingCost, JobOffer.id == JobOfferAdvertisingCost.job_offer_id
    ).outerjoin(
        JobApplication, JobOffer.id == JobApplication.job_offer_id
    ).group_by(
        JobOffer.id, JobOffer.title, JobOffer.status
    ).order_by(
        func.sum(JobOfferAdvertisingCost.amount).desc()
    ).limit(10).all()

    # 4. TOTALI GLOBALI
    total_investment_all = sum([r['investment'] for r in roi_analysis])
    total_apps_all = sum([r['applications'] for r in roi_analysis])
    total_hires_all = sum([r['hires'] for r in roi_analysis])
    avg_cost_per_app_all = round(total_investment_all / total_apps_all, 2) if total_apps_all > 0 else 0
    avg_cost_per_hire_all = round(total_investment_all / total_hires_all, 2) if total_hires_all > 0 else 0

    economic_metrics_advanced = {
        'period_breakdown': period_breakdown,
        'roi_analysis': roi_analysis_sorted,
        'top_offers_by_cost': top_offers_by_cost,
        'total_investment_all': round(total_investment_all, 2),
        'total_apps_all': total_apps_all,
        'total_hires_all': total_hires_all,
        'avg_cost_per_app_all': avg_cost_per_app_all,
        'avg_cost_per_hire_all': avg_cost_per_hire_all
    }

    # ========== DATI PER TAB OFFERTE E PIPELINE ==========

    # Recupera tutte le offerte ordinate dalla più recente
    all_offers = JobOffer.query.options(
        joinedload(JobOffer.department)
    ).order_by(JobOffer.created_at.desc()).all()

    # Pre-calcola i conteggi delle applications per ogni offerta (dynamic relationship)
    offers_applications_count = {}
    for offer in all_offers:
        offers_applications_count[offer.id] = offer.applications.count()

    # Recupera tutte le pipeline ordinate dalla più recente
    all_kanbans = RecruitingKanban.query.options(
        joinedload(RecruitingKanban.stages)
    ).order_by(RecruitingKanban.created_at.desc()).all()

    # Pre-calcola i conteggi per ogni kanban
    kanbans_data = {}
    for kanban in all_kanbans:
        # Verifica se è una query o una lista
        if hasattr(kanban.stages, 'all'):
            # È una query SQLAlchemy
            stages_list = kanban.stages.all()
            stages_count = len(stages_list)
        else:
            # È già una lista (joinedload)
            stages_list = list(kanban.stages)
            stages_count = len(stages_list)

        # Conta le applications totali per questo kanban
        total_apps = 0
        for stage in stages_list:
            # Verifica se stage.applications è una query o una lista
            if hasattr(stage.applications, 'all'):
                # È una query SQLAlchemy
                total_apps += stage.applications.count()
            else:
                # È già una lista
                total_apps += len(list(stage.applications))

        kanbans_data[kanban.id] = {
            'stages_count': stages_count,
            'applications_count': total_apps
        }

    return render_template(
        "recruiting/dashboard_unified.html",
        # Filtri
        start_date=start_date,
        end_date=end_date,
        filter_type=filter_type,
        # Metriche generali
        total_applications=total_applications,
        conversion_rate=conversion_rate,
        total_hires=total_hires,
        time_to_hire_days=time_to_hire_days,
        avg_score=avg_score,
        # Metriche piattaforme
        platform_metrics=platform_metrics,
        # Andamento
        monthly_trend=monthly_trend,
        # Metriche economiche
        economic_metrics=economic_metrics,
        economic_trend=economic_trend,
        economic_metrics_advanced=economic_metrics_advanced,
        # Tab offerte e pipeline
        all_offers=all_offers,
        all_kanbans=all_kanbans,
        offers_applications_count=offers_applications_count,
        kanbans_data=kanbans_data,
        total_offers_count=len(all_offers),
        total_kanbans_count=len(all_kanbans)
    )


# ============================================================================
# JOB OFFERS MANAGEMENT
# ============================================================================

@recruiting_bp.route("/offers")
@login_required
def offers_list():
    """Lista offerte di lavoro."""
    status = request.args.get('status', 'all')
    
    query = JobOffer.query
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    offers = query.order_by(JobOffer.created_at.desc()).all()
    
    return render_template(
        "recruiting/offers/list_modern.html",
        offers=offers,
        current_status=status
    )


@recruiting_bp.route("/offers/new", methods=["GET", "POST"])
@login_required
def offer_create():
    """Crea nuova offerta di lavoro."""
    form = JobOfferForm()
    
    if form.validate_on_submit():
        offer = JobOffer(
            title=form.title.data,
            description=form.description.data,
            requirements=form.requirements.data,
            benefits=form.benefits.data,
            salary_range=form.salary_range.data,
            location=form.location.data,
            employment_type=form.employment_type.data,
            department_id=form.department_id.data if form.department_id.data != 0 else None,
            what_we_search=form.what_we_search.data,
            form_weight=form.form_weight.data,
            cv_weight=form.cv_weight.data,
            kanban_id=form.kanban_id.data if form.kanban_id.data != 0 else None,
            # Costi separati per piattaforma
            costo_totale_speso_linkedin=form.costo_totale_speso_linkedin.data or 0.00,
            costo_totale_speso_facebook=form.costo_totale_speso_facebook.data or 0.00,
            costo_totale_speso_instagram=form.costo_totale_speso_instagram.data or 0.00,
            created_by_id=current_user.id,
            status=JobOfferStatusEnum.draft
        )

        # Genera link pubblici
        offer.generate_public_links()
        
        db.session.add(offer)
        db.session.commit()
        
        flash("Offerta di lavoro creata! Ora puoi aggiungere le domande.", "success")
        return redirect(url_for('recruiting.offer_questions', offer_id=offer.id))
    
    return render_template(
        "recruiting/offers/create_modern.html",
        form=form
    )


@recruiting_bp.route("/offers/<int:offer_id>")
@login_required
def offer_detail(offer_id):
    """Dettaglio offerta di lavoro."""
    offer = JobOffer.query.get_or_404(offer_id)
    
    # Statistiche candidature
    application_stats = {
        'total': offer.applications.count(),
        'by_source': {},
        'by_status': {},
        'avg_score': 0
    }
    
    # Conta per fonte
    for source in ApplicationSourceEnum:
        count = offer.applications.filter_by(source=source).count()
        if count > 0:
            application_stats['by_source'][source.value] = count
    
    # Media punteggi
    scores = [app.total_score for app in offer.applications if app.total_score]
    if scores:
        application_stats['avg_score'] = sum(scores) / len(scores)
    
    return render_template(
        "recruiting/offers/detail_modern.html",
        offer=offer,
        stats=application_stats
    )


@recruiting_bp.route("/offers/<int:offer_id>/edit", methods=["GET", "POST"])
@login_required
def offer_edit(offer_id):
    """Modifica offerta di lavoro."""
    offer = JobOffer.query.get_or_404(offer_id)
    
    form = JobOfferForm(obj=offer)
    
    if form.validate_on_submit():
        # Salva il kanban_id originale per confronto
        old_kanban_id = offer.kanban_id
        new_kanban_id = form.kanban_id.data  # Sempre richiesto ora

        form.populate_obj(offer)
        offer.kanban_id = new_kanban_id
        offer.updated_at = datetime.utcnow()
        
        # Se il kanban è cambiato, migra le candidature esistenti
        if old_kanban_id != new_kanban_id:
            migrated_count = _migrate_applications_to_new_kanban(offer_id, old_kanban_id, new_kanban_id)
            if migrated_count > 0:
                flash(f"Offerta aggiornata! {migrated_count} candidature migrate alla nuova pipeline.", "success")
            else:
                flash("Offerta aggiornata con successo!", "success")
        else:
            flash("Offerta aggiornata con successo!", "success")
        
        db.session.commit()
        return redirect(url_for('recruiting.offer_detail', offer_id=offer.id))
    
    return render_template(
        "recruiting/offers/edit_modern.html",
        form=form,
        offer=offer
    )


@recruiting_bp.route("/offers/<int:offer_id>/questions", methods=["GET", "POST"])
@login_required
def offer_questions(offer_id):
    """Gestione domande del form."""
    offer = JobOffer.query.get_or_404(offer_id)
    
    if request.method == "POST":
        try:
            # Riceve le domande come JSON
            questions_data = request.get_json()
            
            if not questions_data:
                return jsonify({'success': False, 'message': 'Nessuna domanda ricevuta'}), 400
            
            # Elimina domande esistenti
            JobQuestion.query.filter_by(job_offer_id=offer.id).delete()
            
            # Crea nuove domande
            for idx, q_data in enumerate(questions_data):
                question = JobQuestion(
                    job_offer_id=offer.id,
                    question_text=q_data.get('question_text', ''),
                    question_type=q_data.get('question_type', 'short_text'),
                    options=q_data.get('options', []),
                    expected_answer=q_data.get('expected_answer'),
                    expected_options=q_data.get('expected_options', []),
                    expected_min=q_data.get('expected_min'),
                    expected_max=q_data.get('expected_max'),
                    expected_match_type=q_data.get('expected_match_type', 'partial'),  # NUOVO!
                    is_required=q_data.get('is_required', True),
                    weight=q_data.get('weight', 0),
                    order=idx,
                    help_text=q_data.get('help_text'),
                    placeholder=q_data.get('placeholder'),
                    min_length=q_data.get('min_length'),
                    max_length=q_data.get('max_length')
                )
                db.session.add(question)
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Domande salvate con successo!'})
        
        except Exception as e:
            db.session.rollback()
            import traceback
            error_detail = traceback.format_exc()
            print(f"Error saving questions: {error_detail}")
            return jsonify({'success': False, 'message': f'Errore nel salvataggio: {str(e)}'}), 500
    
    # GET: mostra form builder
    # Converti le domande in dizionari per il template
    questions_data = []
    for q in offer.questions:
        questions_data.append({
            'id': q.id,
            'question_text': q.question_text,
            'question_type': q.question_type.value if q.question_type else 'text',
            'options': q.options if q.options else [],
            'is_required': q.is_required,
            'weight': q.weight,
            'help_text': q.help_text,
            'expected_answer': q.expected_answer,
            'expected_options': q.expected_options if q.expected_options else [],
            'expected_min': q.expected_min,
            'expected_max': q.expected_max,
            'expected_match_type': q.expected_match_type.value if q.expected_match_type else 'partial',  # NUOVO!
            'order': q.order
        })

    return render_template(
        "recruiting/offers/questions_perfect.html",  # ← NUOVO TEMPLATE PERFETTO!
        offer=offer,
        questions=questions_data,
        questions_objects=offer.questions
    )


@recruiting_bp.route("/offers/<int:offer_id>/questions/create", methods=["POST"])
@login_required
def question_create(offer_id):
    """Crea una singola nuova domanda."""
    offer = JobOffer.query.get_or_404(offer_id)

    try:
        data = request.get_json()
        print(f"[DEBUG] Received data: {data}")

        if not data:
            print("[ERROR] No data received")
            return jsonify({'success': False, 'message': 'Nessun dato ricevuto'}), 400

        # Validate required fields
        if not data.get('question_text'):
            print("[ERROR] Missing question_text")
            return jsonify({'success': False, 'message': 'Testo domanda obbligatorio'}), 400

        if not data.get('question_type'):
            print("[ERROR] Missing question_type")
            return jsonify({'success': False, 'message': 'Tipo domanda obbligatorio'}), 400

        # Get max order
        max_order = db.session.query(db.func.max(JobQuestion.order)).filter_by(job_offer_id=offer.id).scalar() or -1

        question = JobQuestion(
            job_offer_id=offer.id,
            question_text=data.get('question_text', ''),
            question_type=data.get('question_type', 'short_text'),
            options=data.get('options'),
            expected_answer=data.get('expected_answer'),
            expected_options=data.get('expected_options'),
            expected_min=data.get('expected_min'),
            expected_max=data.get('expected_max'),
            expected_match_type=data.get('expected_match_type', 'partial'),
            is_required=data.get('is_required', True),
            weight=data.get('weight', 0),
            order=max_order + 1
        )

        db.session.add(question)
        db.session.commit()

        print(f"[SUCCESS] Question created with ID: {question.id}")
        return jsonify({'success': True, 'message': 'Domanda creata con successo!', 'question_id': question.id})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] Error creating question: {error_detail}")
        return jsonify({'success': False, 'message': f'Errore nella creazione: {str(e)}'}), 500


@recruiting_bp.route("/offers/<int:offer_id>/questions/<int:question_id>", methods=["PUT"])
@login_required
def question_update(offer_id, question_id):
    """Modifica una singola domanda."""
    offer = JobOffer.query.get_or_404(offer_id)
    question = JobQuestion.query.get_or_404(question_id)

    # Verifica che la domanda appartenga all'offerta
    if question.job_offer_id != offer.id:
        return jsonify({'success': False, 'message': 'Domanda non trovata'}), 404

    try:
        data = request.get_json()

        # Aggiorna campi
        question.question_text = data.get('question_text', question.question_text)
        question.question_type = data.get('question_type', question.question_type)
        question.options = data.get('options', question.options)
        question.expected_answer = data.get('expected_answer')
        question.expected_options = data.get('expected_options', [])
        question.expected_min = data.get('expected_min')
        question.expected_max = data.get('expected_max')
        question.expected_match_type = data.get('expected_match_type', 'partial')
        question.is_required = data.get('is_required', question.is_required)
        question.weight = data.get('weight', question.weight)

        db.session.commit()

        return jsonify({'success': True, 'message': 'Domanda aggiornata con successo!'})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error updating question: {error_detail}")
        return jsonify({'success': False, 'message': f'Errore nell\'aggiornamento: {str(e)}'}), 500


@recruiting_bp.route("/offers/<int:offer_id>/questions/<int:question_id>", methods=["DELETE"])
@login_required
def question_delete(offer_id, question_id):
    """Elimina una singola domanda."""
    offer = JobOffer.query.get_or_404(offer_id)
    question = JobQuestion.query.get_or_404(question_id)

    # Verifica che la domanda appartenga all'offerta
    if question.job_offer_id != offer.id:
        return jsonify({'success': False, 'message': 'Domanda non trovata'}), 404

    try:
        db.session.delete(question)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Domanda eliminata con successo!'})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error deleting question: {error_detail}")
        return jsonify({'success': False, 'message': f'Errore nell\'eliminazione: {str(e)}'}), 500


@recruiting_bp.route("/offers/<int:offer_id>/questions/reorder", methods=["POST"])
@login_required
def questions_reorder(offer_id):
    """Riordina le domande."""
    offer = JobOffer.query.get_or_404(offer_id)

    try:
        data = request.get_json()
        order_data = data.get('order', [])

        for item in order_data:
            question_id = item.get('id')
            new_order = item.get('order')

            question = JobQuestion.query.get(question_id)
            if question and question.job_offer_id == offer.id:
                question.order = new_order

        db.session.commit()

        return jsonify({'success': True, 'message': 'Ordine aggiornato con successo!'})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error reordering questions: {error_detail}")
        return jsonify({'success': False, 'message': f'Errore nel riordino: {str(e)}'}), 500


@recruiting_bp.route("/offers/<int:offer_id>/publish", methods=["POST"])
@login_required
def offer_publish(offer_id):
    """Pubblica offerta di lavoro."""
    offer = JobOffer.query.get_or_404(offer_id)
    
    # Verifica che ci siano domande
    if not offer.questions:
        flash("Aggiungi almeno una domanda prima di pubblicare!", "warning")
        return redirect(url_for('recruiting.offer_questions', offer_id=offer.id))
    
    # Verifica che i pesi delle domande sommino a 100
    total_weight = offer.total_questions_weight
    if abs(total_weight - 100) > 0.01:  # Tolleranza per float
        flash(f"Il peso totale delle domande deve essere 100%, attualmente è {total_weight:.1f}%", "warning")
        return redirect(url_for('recruiting.offer_questions', offer_id=offer.id))
    
    offer.status = JobOfferStatusEnum.published
    offer.published_at = datetime.utcnow()
    
    db.session.commit()
    
    flash("Offerta pubblicata con successo!", "success")
    return redirect(url_for('recruiting.offer_detail', offer_id=offer.id))


@recruiting_bp.route("/offers/<int:offer_id>/close", methods=["POST"])
@login_required
def offer_close(offer_id):
    """Chiude offerta di lavoro."""
    offer = JobOffer.query.get_or_404(offer_id)
    
    offer.status = JobOfferStatusEnum.closed
    offer.closed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash("Offerta chiusa.", "info")
    return redirect(url_for('recruiting.offer_detail', offer_id=offer.id))


# ============================================================================
# PUBLIC APPLICATION FORM
# ============================================================================

@recruiting_bp.route("/apply/<link_code>", methods=["GET", "POST"])
def public_apply(link_code):
    """Form pubblico di candidatura."""
    # Trova l'offerta dal link code
    offer = JobOffer.query.filter(
        db.or_(
            JobOffer.linkedin_link == link_code,
            JobOffer.facebook_link == link_code,
            JobOffer.instagram_link == link_code
        )
    ).first_or_404()
    
    # Verifica che sia pubblicata
    if offer.status != JobOfferStatusEnum.published:
        abort(404)
    
    # Determina la fonte e incrementa contatori
    if offer.linkedin_link == link_code:
        source = ApplicationSourceEnum.linkedin
        offer.linkedin_views = (offer.linkedin_views or 0) + 1
    elif offer.facebook_link == link_code:
        source = ApplicationSourceEnum.facebook
        offer.facebook_views = (offer.facebook_views or 0) + 1
    else:
        source = ApplicationSourceEnum.instagram
        offer.instagram_views = (offer.instagram_views or 0) + 1
    
    # Incrementa view count totale
    offer.views_count += 1
    db.session.commit()
    
    if request.method == "POST":
        try:
            # Gestione form submission
            import os
            from werkzeug.utils import secure_filename
            from datetime import datetime

            # Crea nuova applicazione
            application = JobApplication()
            application.job_offer_id = offer.id
            application.source = source
            application.status = ApplicationStatusEnum.new

            # Dati personali
            application.first_name = request.form.get('first_name', '')
            application.last_name = request.form.get('last_name', '')
            application.email = request.form.get('email', '')
            application.phone = request.form.get('phone', '')
            application.linkedin_profile = request.form.get('linkedin_url', '')
            application.portfolio_url = request.form.get('portfolio_url', '')

            # Cover letter
            application.cover_letter = request.form.get('cover_letter', '')

            # ===== FUNNEL TRACKING: Salva timestamp inizio compilazione form =====
            form_started_at_str = request.form.get('form_started_at', '')
            if form_started_at_str:
                try:
                    # Parse ISO timestamp dal JavaScript
                    # Supporta sia formato con 'Z' che con timezone offset
                    if form_started_at_str.endswith('Z'):
                        form_started_at_str = form_started_at_str[:-1] + '+00:00'
                    application.form_started_at = datetime.fromisoformat(form_started_at_str)
                except (ValueError, AttributeError) as e:
                    current_app.logger.warning(f"Failed to parse form_started_at: {form_started_at_str} - {e}")
                    # Se il parsing fallisce, ignora e lascia NULL

            # Gestione file CV
            if 'cv' in request.files:
                cv_file = request.files['cv']
                if cv_file and cv_file.filename:
                    # Crea directory se non esiste
                    upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'applications', str(offer.id))
                    os.makedirs(upload_dir, exist_ok=True)

                    # Salva file con nome sicuro
                    filename = secure_filename(f"{application.first_name}_{application.last_name}_CV_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
                    filepath = os.path.join(upload_dir, filename)
                    cv_file.save(filepath)
                    # Salva solo il percorso relativo per evitare duplicazione
                    application.cv_file_path = os.path.join('applications', str(offer.id), filename)

            # Salva applicazione prima per ottenere l'ID
            db.session.add(application)
            db.session.flush()  # Ottieni l'ID senza commit

            # Salva risposte alle domande personalizzate
            for question in offer.questions:
                question_key = f"question_{question.id}"
                answer_text = None

                if question_key in request.form:
                    answer_text = request.form.get(question_key)
                elif f"{question_key}[]" in request.form:
                    # Per checkbox multipli, unisci in una stringa
                    responses = request.form.getlist(f"{question_key}[]")
                    answer_text = ", ".join(responses)

                if answer_text:
                    answer = ApplicationAnswer()
                    answer.application_id = application.id
                    answer.question_id = question.id
                    answer.answer_text = answer_text
                    db.session.add(answer)

            # Aggiungi alla pipeline se configurata
            if offer.kanban and offer.kanban.stages:
                # Trova la prima fase della pipeline (Applied)
                first_stage = None
                for stage in offer.kanban.stages:
                    if stage.stage_type == 'applied':
                        first_stage = stage
                        break

                # Se non c'è una fase "applied", prendi la prima fase
                if not first_stage and offer.kanban.stages:
                    first_stage = sorted(offer.kanban.stages, key=lambda s: s.order)[0]

                if first_stage:
                    application.kanban_stage_id = first_stage.id

                    # ===== TRACKING STORICO: Prima assegnazione stage =====
                    # Crea record in ApplicationStageHistory per la prima assegnazione
                    history_entry = ApplicationStageHistory(
                        application_id=application.id,
                        stage_id=first_stage.id,
                        previous_stage_id=None,  # Prima assegnazione
                        entered_at=datetime.utcnow(),
                        exited_at=None,  # Ancora attivo
                        duration_seconds=None,
                        changed_by_id=None,  # Auto-assegnazione da form pubblico
                        notes=f'Candidatura ricevuta da {source.value} - Auto-assegnata a "{first_stage.name}"'
                    )
                    db.session.add(history_entry)

            # Commit di tutto
            db.session.commit()

            # Incrementa contatore applicazioni
            offer.applications_count = (offer.applications_count or 0) + 1
            db.session.commit()

            # TODO: Invia email di conferma al candidato
            # TODO: Invia notifica al recruiter

            return jsonify({'success': True, 'message': 'Candidatura inviata con successo!'}), 200

        except Exception as e:
            db.session.rollback()
            import traceback
            error_msg = f"Errore invio candidatura: {str(e)}\n{traceback.format_exc()}"
            current_app.logger.error(error_msg)
            print(error_msg)  # Debug print
            return jsonify({'success': False, 'message': f'Errore: {str(e)}'}), 400
    
    return render_template(
        "recruiting/public/apply_modern.html",
        offer=offer,
        questions=offer.questions,
        source=source,
        link_code=link_code
    )


# ============================================================================
# APPLICATIONS MANAGEMENT
# ============================================================================

@recruiting_bp.route("/applications")
@login_required
def applications_list():
    """Lista tutte le candidature."""
    # Filtri
    offer_id = request.args.get('offer_id', type=int)
    status = request.args.get('status')
    source = request.args.get('source')
    
    query = JobApplication.query
    
    if offer_id:
        query = query.filter_by(job_offer_id=offer_id)
    if status:
        query = query.filter_by(status=status)
    if source:
        query = query.filter_by(source=source)
    
    applications = query.order_by(JobApplication.created_at.desc()).all()
    
    # Offerte per filtro
    offers = JobOffer.query.order_by(JobOffer.title).all()
    
    return render_template(
        "recruiting/applications/list.html",
        applications=applications,
        offers=offers,
        current_offer_id=offer_id,
        current_status=status,
        current_source=source
    )


@recruiting_bp.route("/applications/<int:application_id>")
@login_required
def application_detail(application_id):
    """Dettaglio candidatura."""
    application = JobApplication.query.get_or_404(application_id)
    
    # Carica risposte con domande
    answers_with_questions = []
    for answer in application.answers:
        answers_with_questions.append({
            'question': answer.question,
            'answer': answer,
            'score': answer.score
        })
    
    # Carica analisi AI se disponibile
    ai_analysis = None
    if hasattr(application, 'ats_analysis') and application.ats_analysis:
        try:
            ai_analysis = json.loads(application.ats_analysis) if isinstance(application.ats_analysis, str) else application.ats_analysis
        except (json.JSONDecodeError, TypeError):
            current_app.logger.warning(f"Failed to parse AI analysis for application {application_id}")
            ai_analysis = None
    current_app.logger.error(ai_analysis)
    
    return render_template(
        "recruiting/applications/detail_modern.html",
        application=application,
        answers=answers_with_questions,
        ai_analysis=ai_analysis
    )


@recruiting_bp.route("/offers/<int:offer_id>/applications")
@login_required
def offer_applications(offer_id):
    """Lista candidature per una specifica offerta."""
    offer = JobOffer.query.get_or_404(offer_id)
    
    # Opzioni di ordinamento
    sort_by = request.args.get('sort', 'score')
    
    query = offer.applications
    
    if sort_by == 'score':
        query = query.order_by(JobApplication.total_score.desc())
    elif sort_by == 'name':
        query = query.order_by(JobApplication.last_name, JobApplication.first_name)
    else:
        query = query.order_by(JobApplication.created_at.desc())
    
    applications = query.all()
    
    return render_template(
        "recruiting/offers/applications_modern.html",
        offer=offer,
        applications=applications,
        sort_by=sort_by
    )




@recruiting_bp.route("/offers/<int:offer_id>/screening", methods=["GET", "POST"])
@login_required
def offer_screening(offer_id):
    """Avvia screening ATS per le candidature."""
    offer = JobOffer.query.get_or_404(offer_id)
    form = ScreeningForm()
    
    if form.validate_on_submit():
        # Importa il modulo ATS
        from .ats import run_screening
        
        # Determina quali candidature analizzare
        if form.screen_all.data:
            applications = offer.applications.all()
        elif form.only_new.data:
            applications = offer.applications.filter_by(status='new').all()
        else:
            applications = offer.applications.all()
        
        # Esegui screening
        results = run_screening(
            applications,
            min_score=form.min_score.data
        )
        
        flash(f"Screening completato! Analizzate {len(results['processed'])} candidature.", "success")
        
        # Reindirizza al kanban se configurato
        if offer.kanban:
            return redirect(url_for('recruiting.kanban_view', kanban_id=offer.kanban.id))
        else:
            return redirect(url_for('recruiting.offer_applications', offer_id=offer.id))
    
    # Statistiche pre-screening
    stats = {
        'total': offer.applications.count(),
        'new': offer.applications.filter_by(status='new').count(),
        'screened': offer.applications.filter(JobApplication.screened_at.isnot(None)).count()
    }
    
    return render_template(
        "recruiting/offers/screening_modern.html",
        offer=offer,
        form=form,
        stats=stats
    )



# ============================================================================
# HR METRICS DASHBOARD
# ============================================================================

@recruiting_bp.route("/metrics")
@login_required
def metrics_dashboard():
    """Dashboard generale delle metriche HR."""
    
    # Recupera i parametri di data dalla richiesta o imposta i valori predefiniti
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    else:
        start_date = datetime.now().replace(day=1) # Inizio del mese corrente

    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        end_date = datetime.now() # Data odierna

    # Utilizza il servizio unificato per calcolare le metriche generali
    metrics_service = MetricsService()
    general_metrics = metrics_service.calculate_metrics(
        offer_id=None,  # None per metriche generali
        start_date=start_date,
        end_date=end_date
    )

    # ===== NUOVE METRICHE: Funnel Analysis e Source Effectiveness =====
    funnel_data = metrics_service.calculate_funnel_analysis(
        offer_id=None,
        start_date=start_date,
        end_date=end_date
    )

    source_effectiveness = metrics_service.calculate_source_effectiveness(
        offer_id=None,
        start_date=start_date,
        end_date=end_date
    )

    # Offerte recenti per mostrare un esempio
    recent_offers = JobOffer.query.order_by(JobOffer.created_at.desc()).limit(5).all()

    return render_template(
        "recruiting/metrics/dashboard.html",
        general_metrics=general_metrics,
        funnel_data=funnel_data,
        source_effectiveness=source_effectiveness,
        recent_offers=recent_offers,
        analytics_start_date=ANALYTICS_START_DATE
    )


@recruiting_bp.route("/offers/<int:offer_id>/metrics")
@login_required
def offer_metrics_dashboard(offer_id):
    """Dashboard delle metriche per una specifica offerta di lavoro con filtri temporali."""
    from dateutil.relativedelta import relativedelta

    # Recupera l'offerta
    offer = JobOffer.query.get_or_404(offer_id)

    # ========== FILTRI DATA (identici a unified_dashboard) ==========
    filter_type = request.args.get('filter_type', 'month')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    today = datetime.now()

    if filter_type == 'month' and not start_date_str:
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif filter_type == 'quarter' and not start_date_str:
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif filter_type == 'year' and not start_date_str:
        start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    else:
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)

    # ========== CALCOLO METRICHE PER SINGOLA OFFERTA ==========

    # Query base candidature per questa offerta nel periodo
    applications_query = JobApplication.query.filter(
        JobApplication.job_offer_id == offer_id,
        JobApplication.created_at >= start_date,
        JobApplication.created_at <= end_date
    )

    # ========== RIGA 1: METRICHE GENERALI ==========
    total_applications = applications_query.count()

    total_hires = applications_query.filter(
        JobApplication.status == ApplicationStatusEnum.hired
    ).count()

    conversion_rate = round((total_hires / total_applications * 100), 2) if total_applications > 0 else 0

    # Tempo medio assunzione
    hired_apps = applications_query.filter(
        JobApplication.status == ApplicationStatusEnum.hired
    ).all()

    time_to_hire_days = 0
    if hired_apps:
        total_days = 0
        count = 0
        for app in hired_apps:
            hired_history = ApplicationStageHistory.query.filter_by(
                application_id=app.id
            ).join(
                KanbanStage,
                ApplicationStageHistory.stage_id == KanbanStage.id
            ).filter(
                KanbanStage.stage_type == KanbanStageTypeEnum.hired
            ).order_by(ApplicationStageHistory.entered_at.asc()).first()

            if hired_history and app.created_at:
                days = (hired_history.entered_at - app.created_at).days
                total_days += days
                count += 1
        time_to_hire_days = round(total_days / count, 1) if count > 0 else 0

    # Score medio generale (escludi None e 0)
    applications_with_score = applications_query.filter(
        JobApplication.total_score.isnot(None),
        JobApplication.total_score > 0
    ).all()

    avg_score = 0
    if applications_with_score:
        total_score = sum(app.total_score for app in applications_with_score)
        avg_score = round(total_score / len(applications_with_score), 1)

    # ========== RIGHE 2-4: METRICHE PER PIATTAFORMA ==========

    # Costi totali per questa offerta (dai campi dell'offerta)
    linkedin_total_cost = offer.costo_totale_speso_linkedin or 0
    facebook_total_cost = offer.costo_totale_speso_facebook or 0
    instagram_total_cost = offer.costo_totale_speso_instagram or 0

    # LINKEDIN
    linkedin_apps = applications_query.filter(JobApplication.source == ApplicationSourceEnum.linkedin).all()
    linkedin_count = len(linkedin_apps)
    linkedin_hires = len([app for app in linkedin_apps if app.status == ApplicationStatusEnum.hired])
    linkedin_cost_per_app = round(linkedin_total_cost / linkedin_count, 2) if linkedin_count > 0 else 0
    linkedin_cost_per_hire = round(linkedin_total_cost / linkedin_hires, 2) if linkedin_hires > 0 else 0

    # Score medio LinkedIn (escludi None e 0)
    linkedin_scores = [app.total_score for app in linkedin_apps if app.total_score is not None and app.total_score > 0]
    linkedin_avg_score = round(sum(linkedin_scores) / len(linkedin_scores), 1) if linkedin_scores else 0

    # FACEBOOK
    facebook_apps = applications_query.filter(JobApplication.source == ApplicationSourceEnum.facebook).all()
    facebook_count = len(facebook_apps)
    facebook_hires = len([app for app in facebook_apps if app.status == ApplicationStatusEnum.hired])
    facebook_cost_per_app = round(facebook_total_cost / facebook_count, 2) if facebook_count > 0 else 0
    facebook_cost_per_hire = round(facebook_total_cost / facebook_hires, 2) if facebook_hires > 0 else 0

    # Score medio Facebook (escludi None e 0)
    facebook_scores = [app.total_score for app in facebook_apps if app.total_score is not None and app.total_score > 0]
    facebook_avg_score = round(sum(facebook_scores) / len(facebook_scores), 1) if facebook_scores else 0

    # INSTAGRAM
    instagram_apps = applications_query.filter(JobApplication.source == ApplicationSourceEnum.instagram).all()
    instagram_count = len(instagram_apps)
    instagram_hires = len([app for app in instagram_apps if app.status == ApplicationStatusEnum.hired])
    instagram_cost_per_app = round(instagram_total_cost / instagram_count, 2) if instagram_count > 0 else 0
    instagram_cost_per_hire = round(instagram_total_cost / instagram_hires, 2) if instagram_hires > 0 else 0

    # Score medio Instagram (escludi None e 0)
    instagram_scores = [app.total_score for app in instagram_apps if app.total_score is not None and app.total_score > 0]
    instagram_avg_score = round(sum(instagram_scores) / len(instagram_scores), 1) if instagram_scores else 0

    return render_template(
        "recruiting/metrics/offer_dashboard.html",
        offer=offer,
        # Filtri
        start_date=start_date,
        end_date=end_date,
        filter_type=filter_type,
        # Riga 1 - Metriche generali
        total_applications=total_applications,
        total_hires=total_hires,
        conversion_rate=conversion_rate,
        time_to_hire_days=time_to_hire_days,
        avg_score=avg_score,
        # Riga 2 - LinkedIn
        linkedin_total_cost=linkedin_total_cost,
        linkedin_count=linkedin_count,
        linkedin_cost_per_app=linkedin_cost_per_app,
        linkedin_cost_per_hire=linkedin_cost_per_hire,
        linkedin_avg_score=linkedin_avg_score,
        # Riga 3 - Instagram
        instagram_total_cost=instagram_total_cost,
        instagram_count=instagram_count,
        instagram_cost_per_app=instagram_cost_per_app,
        instagram_cost_per_hire=instagram_cost_per_hire,
        instagram_avg_score=instagram_avg_score,
        # Riga 4 - Facebook
        facebook_total_cost=facebook_total_cost,
        facebook_count=facebook_count,
        facebook_cost_per_app=facebook_cost_per_app,
        facebook_cost_per_hire=facebook_cost_per_hire,
        facebook_avg_score=facebook_avg_score,
        analytics_start_date=ANALYTICS_START_DATE
    )


def _migrate_applications_to_new_kanban(offer_id, old_kanban_id, new_kanban_id):
    """
    Migra le candidature di un'offerta da una pipeline kanban a un'altra.
    
    Args:
        offer_id: ID dell'offerta
        old_kanban_id: ID del kanban di origine
        new_kanban_id: ID del kanban di destinazione
        
    Returns:
        int: Numero di candidature migrate
    """
    if old_kanban_id == new_kanban_id:
        return 0
    
    # Ottieni gli stage dei due kanban
    old_stages = {stage.stage_type: stage for stage in KanbanStage.query.filter_by(kanban_id=old_kanban_id, is_active=True).all()}
    new_stages = {stage.stage_type: stage for stage in KanbanStage.query.filter_by(kanban_id=new_kanban_id, is_active=True).all()}
    
    # Mapping dei tipi di stage per la migrazione
    stage_mapping = {}
    for stage_type, old_stage in old_stages.items():
        if stage_type in new_stages:
            stage_mapping[old_stage.id] = new_stages[stage_type].id
    
    # Se non ci sono mapping, usa il primo stage del nuovo kanban come fallback
    if not stage_mapping:
        first_new_stage = KanbanStage.query.filter_by(kanban_id=new_kanban_id, is_active=True).order_by(KanbanStage.order).first()
        if first_new_stage:
            # Mappa tutti gli stage vecchi al primo stage nuovo
            for old_stage in old_stages.values():
                stage_mapping[old_stage.id] = first_new_stage.id
    
    # Ottieni le candidature da migrare
    applications = JobApplication.query.filter_by(job_offer_id=offer_id).all()
    migrated_count = 0

    for app in applications:
        if app.kanban_stage_id in stage_mapping:
            old_stage_id = app.kanban_stage_id
            new_stage_id = stage_mapping[app.kanban_stage_id]

            # Aggiorna lo stage
            app.kanban_stage_id = new_stage_id
            migrated_count += 1

            # ===== TRACKING STORICO: Migrazione kanban =====
            # Chiudi il record storico del vecchio stage
            old_history = ApplicationStageHistory.query.filter_by(
                application_id=app.id,
                stage_id=old_stage_id,
                exited_at=None
            ).first()

            if old_history:
                old_history.exited_at = datetime.utcnow()
                old_history.calculate_duration()

            # Crea nuovo record storico per il nuovo stage
            new_history = ApplicationStageHistory(
                application_id=app.id,
                stage_id=new_stage_id,
                previous_stage_id=old_stage_id,
                entered_at=datetime.utcnow(),
                exited_at=None,
                duration_seconds=None,
                changed_by_id=current_user.id if hasattr(current_user, 'id') else None,
                notes=f'Migrato da kanban {old_kanban_id} a kanban {new_kanban_id}'
            )
            db.session.add(new_history)

    return migrated_count


# ============================================================================
# CV DOWNLOAD
# ============================================================================

@recruiting_bp.route("/applications/<int:application_id>/view-cv")
@login_required
def view_cv(application_id):
    """Visualizza il CV inline nel browser."""
    application = JobApplication.query.get_or_404(application_id)

    if not application.cv_file_path:
        abort(404, "Nessun CV disponibile per questa candidatura.")

    # Costruisci il percorso completo del file
    upload_folder = current_app.config['UPLOAD_FOLDER']
    # Rimuovi "uploads/" dal path se presente per evitare duplicazione
    cv_file_path = application.cv_file_path
    if cv_file_path.startswith('uploads/'):
        cv_file_path = cv_file_path[8:]  # Rimuove "uploads/"
    # Risolvi il path assoluto per evitare duplicazioni
    cv_path = os.path.abspath(os.path.join(upload_folder, cv_file_path))

    # Verifica che il file esista
    if not os.path.exists(cv_path):
        current_app.logger.error(f"CV file not found: {cv_path}")
        abort(404, "File CV non trovato.")

    try:
        # Invia il file per visualizzazione inline (non download)
        return send_file(
            cv_path,
            as_attachment=False,
            mimetype='application/pdf'
        )

    except Exception as e:
        current_app.logger.error(f"Error viewing CV for application {application_id}: {str(e)}")
        abort(500, "Errore durante la visualizzazione del CV.")


@recruiting_bp.route("/applications/<int:application_id>/download-cv")
@login_required
def download_cv(application_id):
    """Scarica il CV di una candidatura."""
    application = JobApplication.query.get_or_404(application_id)

    if not application.cv_file_path:
        flash("Nessun CV disponibile per questa candidatura.", "warning")
        return redirect(request.referrer or url_for('recruiting.applications_list'))

    # Costruisci il percorso completo del file
    upload_folder = current_app.config['UPLOAD_FOLDER']
    # Rimuovi "uploads/" dal path se presente per evitare duplicazione
    cv_file_path = application.cv_file_path
    if cv_file_path.startswith('uploads/'):
        cv_file_path = cv_file_path[8:]  # Rimuove "uploads/"
    # Risolvi il path assoluto per evitare duplicazioni
    cv_path = os.path.abspath(os.path.join(upload_folder, cv_file_path))

    # Verifica che il file esista
    if not os.path.exists(cv_path):
        current_app.logger.error(f"CV file not found: {cv_path}")
        flash("File CV non trovato.", "error")
        return redirect(request.referrer or url_for('recruiting.applications_list'))

    try:
        # Estrai il nome del file originale dal percorso
        filename = os.path.basename(cv_path)

        # Se il nome del file non è descrittivo, crea un nome migliore
        if not filename or filename.startswith('cv_'):
            file_ext = os.path.splitext(cv_path)[1]
            filename = f"CV_{application.first_name}_{application.last_name}{file_ext}"

        return send_file(
            cv_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        current_app.logger.error(f"Error downloading CV for application {application_id}: {str(e)}")
        flash("Errore durante il download del CV.", "error")
        return redirect(request.referrer or url_for('recruiting.applications_list'))


# ============================================================================
# ADVERTISING COSTS ROUTES
# ============================================================================

@recruiting_bp.route("/offers/<int:offer_id>/advertising")
@login_required
def offer_advertising(offer_id):
    """
    Pagina gestione advertising costs per una specifica offerta.
    Mostra storico costi con filtri e form per aggiungere nuovi costi.
    """
    from corposostenibile.models import JobOfferAdvertisingCost, AdvertisingPlatformEnum, AdvertisingPeriodEnum

    offer = JobOffer.query.get_or_404(offer_id)

    # Filtri dalla query string
    platform_filter = request.args.get('platform')
    year_filter = request.args.get('year', type=int)
    month_filter = request.args.get('month', type=int)

    # Query base
    query = JobOfferAdvertisingCost.query.filter_by(job_offer_id=offer_id)

    # Applica filtri
    if platform_filter:
        try:
            query = query.filter_by(platform=AdvertisingPlatformEnum(platform_filter))
        except ValueError:
            pass

    if year_filter:
        query = query.filter_by(year=year_filter)

    if month_filter:
        query = query.filter_by(month=month_filter)

    # Ordina per data decrescente
    costs = query.order_by(
        JobOfferAdvertisingCost.year.desc(),
        JobOfferAdvertisingCost.month.desc(),
        JobOfferAdvertisingCost.period.desc()
    ).all()

    # Calcola totali per piattaforma
    totals_query = db.session.query(
        JobOfferAdvertisingCost.platform,
        func.sum(JobOfferAdvertisingCost.amount).label('total')
    ).filter_by(job_offer_id=offer_id)

    # Applica stessi filtri ai totali
    if year_filter:
        totals_query = totals_query.filter_by(year=year_filter)
    if month_filter:
        totals_query = totals_query.filter_by(month=month_filter)

    totals = totals_query.group_by(JobOfferAdvertisingCost.platform).all()

    totals_by_platform = {
        t.platform: float(t.total) for t in totals
    }

    grand_total = sum(totals_by_platform.values())

    # Anni disponibili per filtro (dal 2020 all'anno corrente + 1)
    current_year = datetime.now().year
    available_years = list(range(2020, current_year + 2))

    # Mesi (italiano)
    months_it = {
        1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
        5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
        9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
    }

    return render_template(
        "recruiting/offer_advertising.html",
        offer=offer,
        costs=costs,
        totals_by_platform=totals_by_platform,
        grand_total=grand_total,
        platforms=AdvertisingPlatformEnum,
        periods=AdvertisingPeriodEnum,
        available_years=available_years,
        months_it=months_it,
        # Filtri attivi
        platform_filter=platform_filter,
        year_filter=year_filter,
        month_filter=month_filter
    )


@recruiting_bp.route("/advertising")
@login_required
def advertising_global():
    """
    Pagina globale con tutti i costi advertising di tutte le offerte.
    Dashboard con KPI, filtri avanzati e tabella completa.
    """
    from corposostenibile.models import JobOfferAdvertisingCost, AdvertisingPlatformEnum, AdvertisingPeriodEnum

    # Filtri dalla query string
    offer_id_filter = request.args.get('offer_id', type=int)
    platform_filter = request.args.get('platform')
    year_filter = request.args.get('year', type=int)
    month_filter = request.args.get('month', type=int)

    # Paginazione
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    # Query base con join per nome offerta
    query = JobOfferAdvertisingCost.query.join(JobOffer)

    # Applica filtri
    if offer_id_filter:
        query = query.filter(JobOfferAdvertisingCost.job_offer_id == offer_id_filter)

    if platform_filter:
        try:
            query = query.filter(JobOfferAdvertisingCost.platform == AdvertisingPlatformEnum(platform_filter))
        except ValueError:
            pass

    if year_filter:
        query = query.filter(JobOfferAdvertisingCost.year == year_filter)

    if month_filter:
        query = query.filter(JobOfferAdvertisingCost.month == month_filter)

    # Ordina per data decrescente
    query = query.order_by(
        JobOfferAdvertisingCost.year.desc(),
        JobOfferAdvertisingCost.month.desc(),
        JobOfferAdvertisingCost.period.desc()
    )

    # Pagina risultati
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Calcola totali globali (senza filtri paginazione, ma con filtri piattaforma/anno/mese)
    totals_query = db.session.query(
        JobOfferAdvertisingCost.platform,
        func.sum(JobOfferAdvertisingCost.amount).label('total')
    )

    # Applica stessi filtri ai totali
    if offer_id_filter:
        totals_query = totals_query.filter_by(job_offer_id=offer_id_filter)
    if platform_filter:
        try:
            totals_query = totals_query.filter(JobOfferAdvertisingCost.platform == AdvertisingPlatformEnum(platform_filter))
        except ValueError:
            pass
    if year_filter:
        totals_query = totals_query.filter_by(year=year_filter)
    if month_filter:
        totals_query = totals_query.filter_by(month=month_filter)

    totals = totals_query.group_by(JobOfferAdvertisingCost.platform).all()

    totals_by_platform = {
        t.platform: float(t.total) for t in totals
    }

    grand_total = sum(totals_by_platform.values())

    # Top offerte per spesa
    top_offers_query = db.session.query(
        JobOffer.id,
        JobOffer.title,
        func.sum(JobOfferAdvertisingCost.amount).label('total_spent')
    ).join(JobOfferAdvertisingCost).group_by(JobOffer.id, JobOffer.title)

    # Applica filtri anno/mese anche a top offers
    if year_filter:
        top_offers_query = top_offers_query.filter(JobOfferAdvertisingCost.year == year_filter)
    if month_filter:
        top_offers_query = top_offers_query.filter(JobOfferAdvertisingCost.month == month_filter)

    top_offers = top_offers_query.order_by(func.sum(JobOfferAdvertisingCost.amount).desc()).limit(10).all()

    # Lista offerte per filtro dropdown
    all_offers = JobOffer.query.order_by(JobOffer.created_at.desc()).all()

    # Anni disponibili
    current_year = datetime.now().year
    available_years = list(range(2020, current_year + 2))

    # Mesi (italiano)
    months_it = {
        1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
        5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
        9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
    }

    return render_template(
        "recruiting/advertising_global.html",
        costs=pagination.items,
        pagination=pagination,
        totals_by_platform=totals_by_platform,
        grand_total=grand_total,
        top_offers=top_offers,
        all_offers=all_offers,
        platforms=AdvertisingPlatformEnum,
        available_years=available_years,
        months_it=months_it,
        # Filtri attivi
        offer_id_filter=offer_id_filter,
        platform_filter=platform_filter,
        year_filter=year_filter,
        month_filter=month_filter
    )
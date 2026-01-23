"""
Servizio per il calcolo delle metriche HR del recruiting.
Gestisce sia le metriche generali che quelle per singola offerta e le metriche Kanban.
"""

from datetime import datetime
from sqlalchemy import func
from corposostenibile.extensions import db
from corposostenibile.models import (
    JobOffer, JobApplication, ApplicationStatusEnum,
    RecruitingKanban, KanbanStage, KanbanStageTypeEnum,
    ApplicationStageHistory, JobOfferAdvertisingCost, AdvertisingPlatformEnum
)

# ===== DATA DI CUTOFF PER ANALYTICS =====
# Candidature create PRIMA di questa data vengono ESCLUSE dalle metriche
# (mantenute nel database ma non conteggiate nelle analytics)
ANALYTICS_START_DATE = datetime(2025, 10, 13, 0, 0, 0)  # 13 Ottobre 2025 (data implementazione)


# ===== HELPER FUNCTIONS =====

def get_advertising_costs_for_offer(offer_id, platform=None):
    """
    Calcola i costi advertising totali per un'offerta dalla tabella JobOfferAdvertisingCost.

    Args:
        offer_id: ID dell'offerta
        platform: (opzionale) Filtra per piattaforma specifica (AdvertisingPlatformEnum)

    Returns:
        float: Totale costi in EUR
    """
    query = db.session.query(
        func.sum(JobOfferAdvertisingCost.amount)
    ).filter_by(job_offer_id=offer_id)

    if platform:
        query = query.filter_by(platform=platform)

    result = query.scalar()
    return float(result or 0)


def get_advertising_costs_by_platform(offer_id):
    """
    Calcola i costi advertising per piattaforma per un'offerta.

    Args:
        offer_id: ID dell'offerta

    Returns:
        dict: {'linkedin': float, 'facebook': float, 'instagram': float}
    """
    return {
        'linkedin': get_advertising_costs_for_offer(offer_id, AdvertisingPlatformEnum.linkedin),
        'facebook': get_advertising_costs_for_offer(offer_id, AdvertisingPlatformEnum.facebook),
        'instagram': get_advertising_costs_for_offer(offer_id, AdvertisingPlatformEnum.instagram),
    }


class MetricsService:
    """Servizio per il calcolo unificato delle metriche HR e Kanban."""
    
    def __init__(self):
        self.cost_per_hire = 0  # Costo fisso per candidatura (configurabile)
    
    def calculate_metrics(self, offer_id=None, start_date=None, end_date=None):
        """
        Calcola le metriche HR in modo unificato.
        
        Args:
            offer_id (int, optional): ID dell'offerta specifica. Se None, calcola metriche generali.
            start_date (datetime, optional): Data di inizio per il filtro temporale.
            end_date (datetime, optional): Data di fine per il filtro temporale.
            
        Returns:
            dict: Dizionario con tutte le metriche calcolate.
        """
        # Imposta date predefinite se non fornite
        if not start_date:
            start_date = datetime.now().replace(day=1)  # Inizio del mese corrente
        if not end_date:
            end_date = datetime.now()  # Data odierna
        
        # Determina se stiamo calcolando metriche per una singola offerta o generali
        is_single_offer = offer_id is not None
        
        if is_single_offer:
            return self._calculate_single_offer_metrics(offer_id, start_date, end_date)
        else:
            return self._calculate_general_metrics(start_date, end_date)
    
    def calculate_kanban_analytics(self, kanban_id, bottleneck_threshold=35.0):
        """
        Calcola le metriche analytics per un Kanban specifico.
        
        Args:
            kanban_id (int): ID del kanban per cui calcolare le metriche.
            bottleneck_threshold (float): Soglia percentuale sopra la quale uno stage diventa bottleneck (default: 35.0).
            
        Returns:
            dict: Dizionario con tutte le metriche Kanban calcolate.
        """
        kanban = RecruitingKanban.query.get_or_404(kanban_id)
        
        # Ottieni tutti gli stage ordinati
        stages = KanbanStage.query.filter_by(
            kanban_id=kanban_id, 
            is_active=True
        ).order_by(KanbanStage.order).all()
        
        # Calcola metriche per ogni stage
        stage_metrics = []
        bottlenecks = []
        
        for i, stage in enumerate(stages):
            stage_data = self._calculate_stage_metrics(stage, stages, i, bottleneck_threshold)
            stage_metrics.append(stage_data)
            
            if stage_data['is_bottleneck']:
                bottlenecks.append(stage_data)
        
        # Calcola metriche generali
        general_metrics = self._calculate_kanban_general_metrics(kanban_id, stage_metrics)
        
        # Identifica stage più lento e più occupato
        slowest_stage = max(stage_metrics, key=lambda x: x['avg_time_days']) if stage_metrics else None
        busiest_stage = max(stage_metrics, key=lambda x: x['count']) if stage_metrics else None

        return {
            'total': general_metrics['total'],
            'hired': general_metrics['hired'],
            'rejected': general_metrics['rejected'],
            'in_progress': general_metrics['in_progress'],
            'hire_rate': general_metrics['hire_rate'],
            'total_stages': len(stages),
            'stages': stage_metrics,
            'bottlenecks': bottlenecks,
            'bottleneck_count': len(bottlenecks),
            'slowest_stage': slowest_stage,
            'busiest_stage': busiest_stage,
            'bottleneck_threshold': bottleneck_threshold,
            'avg_application_to_hire_time': general_metrics.get('avg_application_to_hire_time', 0.0),
            'contracts_offered': general_metrics.get('contracts_offered', 0),
            'contracts_signed': general_metrics.get('contracts_signed', 0),
            'contract_acceptance_rate': general_metrics.get('contract_acceptance_rate', 0.0)
        }
    
    def _calculate_stage_metrics(self, stage, all_stages, stage_index, bottleneck_threshold=35.0):
        """
        Calcola le metriche AVANZATE per un singolo stage del Kanban (VERSIONE 10/10).

        Args:
            stage: Lo stage per cui calcolare le metriche.
            all_stages: Lista di tutti gli stage del kanban.
            stage_index: Indice dello stage nella lista.
            bottleneck_threshold: Soglia percentuale per identificare i bottleneck.

        Returns:
            dict: Metriche complete dello stage con distribution, quality, conversion reale, drop-off.
        """
        # Candidati attualmente nello stage
        applications = JobApplication.query.filter_by(
            kanban_stage_id=stage.id
        ).all()

        # ===== TEMPO DI PERMANENZA: Calcola distribuzione completa =====
        times = []
        quality_scores = []  # Score ATS dei candidati in questo stage

        for app in applications:
            # Trova il record storico attivo per questo stage
            history = ApplicationStageHistory.query.filter_by(
                application_id=app.id,
                stage_id=stage.id
            ).order_by(ApplicationStageHistory.entered_at.desc()).first()

            if history:
                if history.duration_seconds is not None:
                    # Se la candidatura è già uscita, usa duration_seconds
                    times.append(history.duration_seconds / 86400.0)  # converti in giorni
                elif history.entered_at:
                    # Se è ancora nello stage, calcola tempo trascorso fino ad ora
                    delta = datetime.utcnow() - history.entered_at
                    times.append(delta.total_seconds() / 86400.0)  # giorni con decimali

            # Raccogli quality score (ATS)
            if app.total_score is not None:
                quality_scores.append(app.total_score)

        # Calcola distribuzione temporale (non solo media!)
        if times:
            times_sorted = sorted(times)
            avg_time = sum(times) / len(times)
            median_time = times_sorted[len(times_sorted) // 2]
            min_time = min(times)
            max_time = max(times)
            p90_time = times_sorted[int(len(times_sorted) * 0.90)] if len(times_sorted) > 10 else max_time
            p95_time = times_sorted[int(len(times_sorted) * 0.95)] if len(times_sorted) > 20 else max_time
        else:
            avg_time = median_time = min_time = max_time = p90_time = p95_time = 0

        # ===== CONVERSION RATE REALE (usando ApplicationStageHistory) =====
        # Quanti sono ENTRATI storicamente in questo stage?
        total_entered = ApplicationStageHistory.query.filter_by(
            stage_id=stage.id
        ).count()

        # Quanti sono PASSATI al prossimo stage?
        conversion_rate = 0
        drop_off_rate = 0
        moved_to_next = 0

        if stage_index < len(all_stages) - 1:
            next_stage = all_stages[stage_index + 1]

            # Conta quanti sono passati da THIS stage al NEXT stage
            moved_to_next = ApplicationStageHistory.query.filter_by(
                previous_stage_id=stage.id,
                stage_id=next_stage.id
            ).count()

            if total_entered > 0:
                conversion_rate = (moved_to_next / total_entered) * 100
                drop_off_rate = 100 - conversion_rate
        elif total_entered > 0:
            # Ultimo stage: calcola % che arrivano qui vs totale iniziale
            first_stage = all_stages[0] if all_stages else None
            if first_stage:
                total_started = ApplicationStageHistory.query.filter_by(
                    stage_id=first_stage.id
                ).count()
                if total_started > 0:
                    conversion_rate = (total_entered / total_started) * 100
                    drop_off_rate = 100 - conversion_rate

        # ===== QUALITY SCORE MEDIO =====
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        # ===== THROUGHPUT (velocità elaborazione) =====
        throughput = len(applications) / avg_time if avg_time > 0 else 0

        # ===== STAGE VELOCITY (velocità di spostamento) =====
        # Quanti candidati sono stati spostati FUORI da questo stage negli ultimi 7 giorni?
        from datetime import timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_exits = ApplicationStageHistory.query.filter(
            ApplicationStageHistory.previous_stage_id == stage.id,
            ApplicationStageHistory.entered_at >= seven_days_ago
        ).count()

        stage_velocity = recent_exits / 7.0  # candidati per giorno

        # ===== BOTTLENECK DETECTION AVANZATO (multi-criterio) =====
        is_bottleneck, bottleneck_reasons = self._identify_bottleneck_advanced(
            stage, applications, all_stages, avg_time, conversion_rate, bottleneck_threshold
        )

        return {
            'stage': stage,
            'count': len(applications),

            # Time distribution
            'avg_time_days': round(avg_time, 2),
            'median_time_days': round(median_time, 2),
            'min_time_days': round(min_time, 2),
            'max_time_days': round(max_time, 2),
            'p90_time_days': round(p90_time, 2),
            'p95_time_days': round(p95_time, 2),

            # Conversion & Drop-off
            'total_entered': total_entered,
            'moved_to_next': moved_to_next,
            'conversion_rate': round(conversion_rate, 2),
            'drop_off_rate': round(drop_off_rate, 2),

            # Quality & Velocity
            'avg_quality_score': round(avg_quality_score, 2),
            'throughput': round(throughput, 2),
            'stage_velocity': round(stage_velocity, 2),

            # Bottleneck
            'is_bottleneck': is_bottleneck,
            'bottleneck_reasons': bottleneck_reasons,

            'percentage': 0  # Sarà calcolato successivamente
        }
    
    def _identify_bottleneck(self, stage, applications, all_stages, bottleneck_threshold=35.0):
        """
        Identifica se uno stage è un collo di bottiglia (LEGACY - usa _identify_bottleneck_advanced).

        Args:
            stage: Lo stage da analizzare.
            applications: Lista delle applicazioni nello stage.
            all_stages: Lista di tutti gli stage del kanban.
            bottleneck_threshold: Soglia percentuale per identificare i bottleneck.

        Returns:
            tuple: (is_bottleneck, bottleneck_reasons)
        """
        is_bottleneck = False
        bottleneck_reasons = []

        # Calcola il totale delle applicazioni in processo
        total_applications_in_process = sum(
            len(JobApplication.query.filter_by(kanban_stage_id=s.id).all())
            for s in all_stages
            if s.stage_type not in ['hired', 'rejected']
        )

        if total_applications_in_process > 0:
            stage_percentage = (len(applications) / total_applications_in_process) * 100
            if stage_percentage >= bottleneck_threshold:
                is_bottleneck = True
                bottleneck_reasons.append("Accumulo di applicazioni")

        return is_bottleneck, bottleneck_reasons

    def _identify_bottleneck_advanced(self, stage, applications, all_stages, avg_time, conversion_rate, bottleneck_threshold=35.0):
        """
        Identifica bottleneck con ALGORITMO AVANZATO multi-criterio (VERSIONE 10/10).

        Un stage è bottleneck se soddisfa ALMENO 2 di questi criteri:
        1. Accumulo candidati (>35% del totale in process)
        2. Tempo medio elevato (>7 giorni)
        3. Basso tasso di conversione (<50%)
        4. Velocity in calo (pochi spostamenti negli ultimi 7gg)

        Args:
            stage: Lo stage da analizzare.
            applications: Lista delle applicazioni nello stage.
            all_stages: Lista di tutti gli stage del kanban.
            avg_time: Tempo medio di permanenza (giorni).
            conversion_rate: Tasso di conversione al prossimo stage (%).
            bottleneck_threshold: Soglia percentuale accumulo (default: 35%).

        Returns:
            tuple: (is_bottleneck, bottleneck_reasons)
        """
        criteria_met = 0
        bottleneck_reasons = []

        # CRITERIO 1: Accumulo di candidati
        total_applications_in_process = sum(
            len(JobApplication.query.filter_by(kanban_stage_id=s.id).all())
            for s in all_stages
            if s.stage_type not in [KanbanStageTypeEnum.hired, KanbanStageTypeEnum.rejected]
        )

        if total_applications_in_process > 0:
            stage_percentage = (len(applications) / total_applications_in_process) * 100
            if stage_percentage >= bottleneck_threshold:
                criteria_met += 1
                bottleneck_reasons.append(f"Accumulo eccessivo ({stage_percentage:.1f}% del totale)")

        # CRITERIO 2: Tempo medio elevato (>7 giorni è sospetto)
        if avg_time > 7.0:
            criteria_met += 1
            bottleneck_reasons.append(f"Tempo medio elevato ({avg_time:.1f} giorni)")

        # CRITERIO 3: Basso tasso di conversione (<50% è problematico)
        if conversion_rate < 50.0 and conversion_rate > 0:
            criteria_met += 1
            bottleneck_reasons.append(f"Basso tasso conversione ({conversion_rate:.1f}%)")

        # CRITERIO 4: Velocity bassa (pochi spostamenti recenti)
        from datetime import timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_exits = ApplicationStageHistory.query.filter(
            ApplicationStageHistory.previous_stage_id == stage.id,
            ApplicationStageHistory.entered_at >= seven_days_ago
        ).count()

        expected_exits = len(applications) / 7.0 if avg_time > 0 else 0  # spostamenti attesi
        if recent_exits < expected_exits * 0.5 and len(applications) > 5:  # meno della metà attesi
            criteria_met += 1
            bottleneck_reasons.append(f"Velocity in calo ({recent_exits} uscite vs {expected_exits:.1f} attese)")

        # È bottleneck se soddisfa ALMENO 2 criteri
        is_bottleneck = criteria_met >= 2

        return is_bottleneck, bottleneck_reasons
    
    def _calculate_kanban_general_metrics(self, kanban_id, stage_metrics):
        """
        Calcola le metriche generali per un Kanban.
        
        Args:
            kanban_id: ID del kanban.
            stage_metrics: Lista delle metriche per stage.
            
        Returns:
            dict: Metriche generali del kanban.
        """
        # Calcola totale applicazioni
        total_applications = sum(m['count'] for m in stage_metrics)
        
        # Calcola percentuali per ogni stage
        for stage_data in stage_metrics:
            if total_applications > 0:
                stage_data['percentage'] = round((stage_data['count'] / total_applications) * 100, 1)
            else:
                stage_data['percentage'] = 0
        
        # Hired vs Rejected
        hired_count = JobApplication.query.join(KanbanStage).filter(
            KanbanStage.kanban_id == kanban_id,
            KanbanStage.stage_type == KanbanStageTypeEnum.hired
        ).count()
        
        rejected_count = JobApplication.query.join(KanbanStage).filter(
            KanbanStage.kanban_id == kanban_id,
            KanbanStage.stage_type == KanbanStageTypeEnum.rejected
        ).count()
        
        # Calcola conversion rate complessivo
        if total_applications > 0:
            overall_conversion_rate = (hired_count / total_applications) * 100
        else:
            overall_conversion_rate = 0.0
        
        # Calcola tempo medio da candidatura ad assunzione
        avg_application_to_hire_time = self._calculate_avg_application_to_hire_time(kanban_id)
        
        # Calcola metriche contratti
        contract_metrics = self._calculate_contract_metrics(kanban_id)

        return {
            'total': total_applications,
            'hired': hired_count,
            'rejected': rejected_count,
            'in_progress': total_applications - hired_count - rejected_count,
            'hire_rate': round(overall_conversion_rate, 2) if overall_conversion_rate is not None else 0.0,
            'total_stages': len(stage_metrics),
            'avg_application_to_hire_time': avg_application_to_hire_time,
            'contracts_offered': contract_metrics['contracts_offered'],
            'contracts_signed': contract_metrics['contracts_signed'],
            'contract_acceptance_rate': contract_metrics['contract_acceptance_rate']
        }
    
    def _calculate_general_metrics(self, start_date, end_date):
        """Calcola le metriche generali per tutte le offerte."""

        # ===== FILTRO: Solo offerte create dal 13 Ottobre 2025 in poi =====
        # 1. Click totali (aperture delle offerte) - SOLO offerte create dopo ANALYTICS_START_DATE
        total_clicks = db.session.query(func.sum(JobOffer.views_count)).filter(
            JobOffer.created_at >= ANALYTICS_START_DATE
        ).scalar() or 0

        # ===== FILTRO: Solo candidature dal 13 Ottobre 2025 in poi =====
        # 2. Candidature totali (ESCLUSE quelle pre-implementazione)
        total_applications = JobApplication.query.filter(
            JobApplication.created_at >= ANALYTICS_START_DATE
        ).count()

        # 3. Conversion Rate (da click a candidatura)
        conversion_rate = (total_applications / total_clicks * 100) if total_clicks > 0 else 0

        # 4. Assunzioni totali nel periodo (con filtro analytics)
        total_hires = JobApplication.query.filter(
            JobApplication.created_at >= ANALYTICS_START_DATE,
            JobApplication.created_at >= start_date,
            JobApplication.created_at <= end_date,
            JobApplication.status == ApplicationStatusEnum.hired
        ).count()
        
        # 5. Tempo medio di assunzione (Time to hire)
        time_to_hire_days = self._calculate_time_to_hire(start_date, end_date)
        
        # 6. Tasso di accettazione delle offerte
        offer_acceptance_rate = self._calculate_offer_acceptance_rate(start_date, end_date, total_hires)
        
        # 7. Costi advertising totali
        advertising_costs = self._calculate_total_advertising_costs()
        
        # 8. Costo per candidatura reale (advertising ÷ candidature totali)
        real_cost_per_application = (advertising_costs['total_cost'] / total_applications) if total_applications > 0 else 0
        total_application_cost = real_cost_per_application * total_applications if total_applications > 0 else advertising_costs['total_cost']
        
        return {
            'total_clicks': total_clicks,
            'total_applications': total_applications,
            'conversion_rate': f"{conversion_rate:.2f}%",
            'total_hires': total_hires,
            'time_to_hire_days': f"{time_to_hire_days:.1f}",
            'offer_acceptance_rate': f"{offer_acceptance_rate:.2f}%",
            'cost_per_hire': f"€{real_cost_per_application:,.2f}",
            'total_hiring_cost': f"€{total_application_cost:,.2f}",
            'advertising_costs': advertising_costs
        }
    
    def _calculate_single_offer_metrics(self, offer_id, start_date, end_date):
        """Calcola le metriche per una singola offerta."""

        # Recupera l'offerta
        offer = JobOffer.query.get_or_404(offer_id)

        # ===== FILTRO: Solo offerte create dal 13 Ottobre 2025 in poi =====
        # 1. Click per questa offerta - SOLO se offerta creata dopo ANALYTICS_START_DATE
        if offer.created_at >= ANALYTICS_START_DATE:
            clicks = offer.views_count or 0
            linkedin_views = offer.linkedin_views or 0
            facebook_views = offer.facebook_views or 0
            instagram_views = offer.instagram_views or 0
        else:
            # Offerta pre-esistente: reset click a 0 per analytics
            clicks = 0
            linkedin_views = 0
            facebook_views = 0
            instagram_views = 0

        # ===== FILTRO: Solo candidature dal 13 Ottobre 2025 in poi =====
        # 2. Candidature per questa offerta (ESCLUSE quelle pre-implementazione)
        applications_received = offer.applications.filter(
            JobApplication.created_at >= ANALYTICS_START_DATE
        ).count()

        # 3. Conversion Rate per questa offerta
        conversion_rate = (applications_received / clicks * 100) if clicks > 0 else 0

        # 4. Assunzioni da questa offerta nel periodo (con filtro analytics)
        hires_from_offer = JobApplication.query.filter(
            JobApplication.job_offer_id == offer_id,
            JobApplication.created_at >= ANALYTICS_START_DATE,
            JobApplication.created_at >= start_date,
            JobApplication.created_at <= end_date,
            JobApplication.status == ApplicationStatusEnum.hired
        ).count()
        
        # 5. Tempo medio di assunzione per questa offerta
        time_to_hire_days = self._calculate_time_to_hire(start_date, end_date, offer_id)
        
        # 6. Tasso di accettazione delle offerte per questa offerta
        offer_acceptance_rate = self._calculate_offer_acceptance_rate(start_date, end_date, hires_from_offer, offer_id)
        
        # 7. Metriche sui contratti per questa offerta
        contract_metrics = self._calculate_single_offer_contract_metrics(offer_id)
        
        # 8. Costi advertising per questa offerta
        advertising_costs = self._calculate_offer_advertising_costs(offer)
        
        # 8. Costo per candidatura reale per questa offerta
        real_cost_per_application = (advertising_costs['total_cost'] / applications_received) if applications_received > 0 else advertising_costs['total_cost']
        total_application_cost = real_cost_per_application * applications_received if applications_received > 0 else advertising_costs['total_cost']
        
        return {
            'clicks': clicks,
            'linkedin_views': linkedin_views,
            'facebook_views': facebook_views,
            'instagram_views': instagram_views,
            'applications_received': applications_received,
            'conversion_rate': f"{conversion_rate:.2f}%",
            'hires_from_offer': hires_from_offer,
            'time_to_hire_days': f"{time_to_hire_days:.1f}",
            'offer_acceptance_rate': f"{offer_acceptance_rate:.2f}%",
            'cost_per_hire': f"€{real_cost_per_application:,.2f}",
            'total_hiring_cost': f"€{total_application_cost:,.2f}",
            'advertising_costs': advertising_costs,
            'contracts_offered': contract_metrics['contracts_offered'],
            'contracts_signed': contract_metrics['contracts_signed'],
            'contract_acceptance_rate': f"{contract_metrics['contract_acceptance_rate']:.2f}%",
            'offer': offer
        }
    
    def _calculate_time_to_hire(self, start_date, end_date, offer_id=None):
        """
        Calcola il tempo medio di assunzione usando ApplicationStageHistory.
        Somma i tempi trascorsi in TUTTI gli stage del processo di hiring.
        """

        # ===== FILTRO: Solo candidature dal 13 Ottobre 2025 in poi =====
        query = JobApplication.query.filter(
            JobApplication.created_at >= ANALYTICS_START_DATE,
            JobApplication.created_at >= start_date,
            JobApplication.created_at <= end_date,
            JobApplication.status == ApplicationStatusEnum.hired
        )

        if offer_id:
            query = query.filter(JobApplication.job_offer_id == offer_id)

        hired_applications = query.all()

        if not hired_applications:
            return 0

        # ===== FIX: Usa ApplicationStageHistory per calcolo accurato =====
        total_days = 0
        valid_applications = 0

        for app in hired_applications:
            # Ottieni TUTTI i record storici per questa candidatura
            history_records = ApplicationStageHistory.query.filter_by(
                application_id=app.id
            ).order_by(ApplicationStageHistory.entered_at).all()

            if history_records:
                # Somma tutti i tempi trascorsi in ogni stage
                app_total_seconds = 0
                for history in history_records:
                    if history.duration_seconds:
                        app_total_seconds += history.duration_seconds
                    elif history.entered_at and not history.exited_at:
                        # Stage attuale (ancora attivo)
                        delta = datetime.utcnow() - history.entered_at
                        app_total_seconds += delta.total_seconds()

                if app_total_seconds > 0:
                    total_days += app_total_seconds / 86400.0  # converti in giorni
                    valid_applications += 1

        return total_days / valid_applications if valid_applications > 0 else 0
    
    def _calculate_offer_acceptance_rate(self, start_date, end_date, total_hires, offer_id=None):
        """Calcola il tasso di accettazione delle offerte."""

        # ===== FILTRO: Solo candidature dal 13 Ottobre 2025 in poi =====
        query = JobApplication.query.filter(
            JobApplication.created_at >= ANALYTICS_START_DATE,
            JobApplication.created_at >= start_date,
            JobApplication.created_at <= end_date,
            JobApplication.status.in_([ApplicationStatusEnum.offer_sent, ApplicationStatusEnum.hired])
        )

        if offer_id:
            query = query.filter(JobApplication.job_offer_id == offer_id)

        offers_sent = query.count()
        
        return (total_hires / offers_sent * 100) if offers_sent > 0 else 0
    
    def _calculate_offer_advertising_costs(self, offer):
        """Calcola i costi advertising per una singola offerta dalla tabella JobOfferAdvertisingCost."""

        # ===== FILTRO: Solo offerte create dal 13 Ottobre 2025 in poi =====
        if offer.created_at >= ANALYTICS_START_DATE:
            # Costi separati per piattaforma dalla nuova tabella granulare
            costs = get_advertising_costs_by_platform(offer.id)
            linkedin_cost = costs['linkedin']
            facebook_cost = costs['facebook']
            instagram_cost = costs['instagram']
        else:
            # Offerta pre-esistente: reset costi a 0 per analytics
            linkedin_cost = 0
            facebook_cost = 0
            instagram_cost = 0

        # Costo totale speso per questa offerta
        total_cost = linkedin_cost + facebook_cost + instagram_cost

        # Calcola il numero totale di visualizzazioni e candidature (coerente con filtro)
        if offer.created_at >= ANALYTICS_START_DATE:
            total_views = (offer.linkedin_views or 0) + (offer.facebook_views or 0) + (offer.instagram_views or 0)
            applications = JobApplication.query.filter(
                JobApplication.created_at >= ANALYTICS_START_DATE,
                JobApplication.job_offer_id == offer.id
            ).count()
        else:
            # Offerta pre-esistente: reset anche views e applications per calcolo costi
            total_views = 0
            applications = 0
        
        # Calcola la spesa totale per click e per candidature in modo proporzionale
        total_events = total_views + applications
        
        if total_events > 0:
            proportional_cost_per_event = total_cost / total_events
            total_click_spend = proportional_cost_per_event * total_views
            total_application_spend = proportional_cost_per_event * applications
        else:
            total_click_spend = 0
            total_application_spend = 0

        return {
            'total_cost': total_cost,
            'total_cost_formatted': f"€{total_cost:,.2f}",
            'total_click_spend': f"€{total_click_spend:,.2f}",
            'total_application_spend': f"€{total_application_spend:,.2f}",
            'total_views': total_views,
            'total_applications': applications,
            'linkedin_cost_formatted': f"€{linkedin_cost:,.2f}",
            'facebook_cost_formatted': f"€{facebook_cost:,.2f}",
            'instagram_cost_formatted': f"€{instagram_cost:,.2f}",
        }
    
    def _calculate_total_advertising_costs(self):
        """Calcola i costi advertising totali per tutte le offerte basandosi sui costi separati per piattaforma."""

        # ===== FILTRO: Solo offerte create dal 13 Ottobre 2025 in poi =====
        offers = JobOffer.query.filter(
            JobOffer.created_at >= ANALYTICS_START_DATE
        ).all()
        total_cost = 0

        for offer in offers:
            # Calcola costi dalla nuova tabella granulare
            total_cost += get_advertising_costs_for_offer(offer.id)
        
        return {
            'total_cost': total_cost,
            'total_cost_formatted': f"€{total_cost:,.2f}",
            'total_budget': f"€{total_cost:,.2f}",  # Nel nuovo sistema, il budget è il costo speso
            'budget_utilization': "100.00%"  # Sempre 100% nel nuovo sistema
        }
    
    def get_metrics_config(self):
        """Restituisce la configurazione delle metriche."""
        return {
            'cost_per_hire': self.cost_per_hire,
            'supported_metrics': [
                'total_clicks', 'total_applications', 'conversion_rate', 'total_hires',
                'time_to_hire_days', 'offer_acceptance_rate', 'cost_per_hire', 'total_hiring_cost'
            ]
        }
    
    def _calculate_avg_application_to_hire_time(self, kanban_id):
        """
        Calcola il tempo medio da candidatura ad assunzione per un Kanban usando ApplicationStageHistory.
        Somma i tempi trascorsi in TUTTI gli stage del processo.

        Args:
            kanban_id: ID del kanban.

        Returns:
            float: Tempo medio in giorni da candidatura ad assunzione.
        """
        hired_applications = JobApplication.query.join(KanbanStage).filter(
            KanbanStage.kanban_id == kanban_id,
            KanbanStage.stage_type == KanbanStageTypeEnum.hired
        ).all()

        if not hired_applications:
            return 0.0

        # ===== FIX: Usa ApplicationStageHistory per calcolo accurato =====
        total_days = 0
        valid_applications = 0

        for app in hired_applications:
            # Ottieni TUTTI i record storici per questa candidatura
            history_records = ApplicationStageHistory.query.filter_by(
                application_id=app.id
            ).order_by(ApplicationStageHistory.entered_at).all()

            if history_records:
                # Somma tutti i tempi trascorsi in ogni stage
                app_total_seconds = 0
                for history in history_records:
                    if history.duration_seconds:
                        app_total_seconds += history.duration_seconds
                    elif history.entered_at and not history.exited_at:
                        # Stage attuale (ancora attivo)
                        delta = datetime.utcnow() - history.entered_at
                        app_total_seconds += delta.total_seconds()

                if app_total_seconds > 0:
                    total_days += app_total_seconds / 86400.0  # converti in giorni
                    valid_applications += 1

        if valid_applications == 0:
            return 0.0

        avg_days = total_days / valid_applications
        return round(avg_days, 2) if avg_days is not None else 0.0
    
    def _calculate_contract_metrics(self, kanban_id):
        """
        Calcola le metriche relative ai contratti per un Kanban.
        
        Args:
            kanban_id: ID del kanban.
            
        Returns:
            dict: Metriche sui contratti.
        """
        # Contratti offerti (applicazioni con status offer_sent o hired)
        contracts_offered = JobApplication.query.join(KanbanStage).filter(
            KanbanStage.kanban_id == kanban_id,
            JobApplication.status.in_([ApplicationStatusEnum.offer_sent, ApplicationStatusEnum.hired])
        ).count()
        
        # Contratti firmati (applicazioni hired)
        contracts_signed = JobApplication.query.join(KanbanStage).filter(
            KanbanStage.kanban_id == kanban_id,
            KanbanStage.stage_type == KanbanStageTypeEnum.hired
        ).count()
        
        # Tasso di accettazione contratti
        if contracts_offered > 0:
            contract_acceptance_rate = (contracts_signed / contracts_offered) * 100
            contract_acceptance_rate = round(contract_acceptance_rate, 2) if contract_acceptance_rate is not None else 0.0
        else:
            contract_acceptance_rate = 0.0
        
        return {
            'contracts_offered': contracts_offered,
            'contracts_signed': contracts_signed,
            'contract_acceptance_rate': contract_acceptance_rate
        }
    
    def _calculate_single_offer_contract_metrics(self, offer_id):
        """
        Calcola le metriche relative ai contratti per una singola offerta.

        Args:
            offer_id: ID dell'offerta.

        Returns:
            dict: Metriche sui contratti per l'offerta specifica.
        """
        # ===== FILTRO: Solo candidature dal 13 Ottobre 2025 in poi =====
        # Contratti offerti (applicazioni con status offer_sent o hired per questa offerta)
        contracts_offered = JobApplication.query.filter(
            JobApplication.created_at >= ANALYTICS_START_DATE,
            JobApplication.job_offer_id == offer_id,
            JobApplication.status.in_([ApplicationStatusEnum.offer_sent, ApplicationStatusEnum.hired])
        ).count()

        # Contratti firmati (applicazioni hired per questa offerta)
        contracts_signed = JobApplication.query.filter(
            JobApplication.created_at >= ANALYTICS_START_DATE,
            JobApplication.job_offer_id == offer_id,
            JobApplication.status == ApplicationStatusEnum.hired
        ).count()
        
        # Tasso di accettazione contratti
        if contracts_offered > 0:
            contract_acceptance_rate = (contracts_signed / contracts_offered) * 100
            contract_acceptance_rate = round(contract_acceptance_rate, 2) if contract_acceptance_rate is not None else 0.0
        else:
            contract_acceptance_rate = 0.0
        
        return {
            'contracts_offered': contracts_offered,
            'contracts_signed': contracts_signed,
            'contract_acceptance_rate': contract_acceptance_rate
        }
    
    def set_cost_per_hire(self, new_cost):
        """Aggiorna il costo per assunzione."""
        self.cost_per_hire = new_cost

    def calculate_funnel_analysis(self, offer_id=None, start_date=None, end_date=None):
        """
        Calcola la funnel analysis completa del recruiting.

        Funnel steps:
        1. Visitors: Totale visualizzazioni dell'offerta
        2. Form Started: Candidati che hanno iniziato a compilare il form (form_started_at)
        3. Form Completed: Candidati che hanno completato e inviato il form
        4. Hired: Candidati assunti

        Args:
            offer_id (int, optional): ID dell'offerta specifica. Se None, analizza tutte le offerte.
            start_date (datetime, optional): Data di inizio per il filtro temporale.
            end_date (datetime, optional): Data di fine per il filtro temporale.

        Returns:
            dict: Dizionario con metriche del funnel e drop-off rates.
        """
        # Imposta date predefinite se non fornite
        if not start_date:
            start_date = datetime.now().replace(day=1)  # Inizio del mese corrente
        if not end_date:
            end_date = datetime.now()  # Data odierna

        # ===== FILTRO: Solo offerte create dal 13 Ottobre 2025 in poi =====
        # 1. VISITORS: Totale visualizzazioni - SOLO offerte create dopo ANALYTICS_START_DATE
        if offer_id:
            offer = JobOffer.query.get(offer_id)
            # Per singola offerta, verifica se è stata creata dopo ANALYTICS_START_DATE
            if offer and offer.created_at >= ANALYTICS_START_DATE:
                visitors = offer.views_count
            else:
                visitors = 0
        else:
            visitors = db.session.query(func.sum(JobOffer.views_count)).filter(
                JobOffer.created_at >= ANALYTICS_START_DATE
            ).scalar() or 0

        # ===== FILTRO: Solo candidature dal 13 Ottobre 2025 in poi =====
        # 2. FORM STARTED: Candidati che hanno iniziato a compilare il form
        form_started_query = JobApplication.query.filter(
            JobApplication.created_at >= ANALYTICS_START_DATE,
            JobApplication.form_started_at.isnot(None),
            JobApplication.created_at >= start_date,
            JobApplication.created_at <= end_date
        )
        if offer_id:
            form_started_query = form_started_query.filter(JobApplication.job_offer_id == offer_id)
        form_started = form_started_query.count()

        # 3. FORM COMPLETED: Candidati che hanno completato e inviato il form
        form_completed_query = JobApplication.query.filter(
            JobApplication.created_at >= ANALYTICS_START_DATE,
            JobApplication.created_at >= start_date,
            JobApplication.created_at <= end_date
        )
        if offer_id:
            form_completed_query = form_completed_query.filter(JobApplication.job_offer_id == offer_id)
        form_completed = form_completed_query.count()

        # 4. HIRED: Candidati assunti
        hired_query = JobApplication.query.filter(
            JobApplication.created_at >= ANALYTICS_START_DATE,
            JobApplication.created_at >= start_date,
            JobApplication.created_at <= end_date,
            JobApplication.status == ApplicationStatusEnum.hired
        )
        if offer_id:
            hired_query = hired_query.filter(JobApplication.job_offer_id == offer_id)
        hired = hired_query.count()

        # ===== CALCOLO DROP-OFF RATES =====
        # Step 1 → 2: Visitors → Form Started
        if visitors > 0:
            visitor_to_start_rate = (form_started / visitors) * 100
            visitor_to_start_dropoff = 100 - visitor_to_start_rate
        else:
            visitor_to_start_rate = 0
            visitor_to_start_dropoff = 0

        # Step 2 → 3: Form Started → Form Completed
        if form_started > 0:
            start_to_complete_rate = (form_completed / form_started) * 100
            start_to_complete_dropoff = 100 - start_to_complete_rate
        else:
            start_to_complete_rate = 0
            start_to_complete_dropoff = 0

        # Step 3 → 4: Form Completed → Hired
        if form_completed > 0:
            complete_to_hire_rate = (hired / form_completed) * 100
            complete_to_hire_dropoff = 100 - complete_to_hire_rate
        else:
            complete_to_hire_rate = 0
            complete_to_hire_dropoff = 0

        # Overall: Visitors → Hired
        if visitors > 0:
            overall_conversion_rate = (hired / visitors) * 100
        else:
            overall_conversion_rate = 0

        return {
            'funnel_steps': {
                'visitors': {
                    'count': visitors,
                    'label': 'Visitors',
                    'description': 'Visualizzazioni totali dell\'offerta'
                },
                'form_started': {
                    'count': form_started,
                    'label': 'Form Started',
                    'description': 'Candidati che hanno iniziato a compilare il form',
                    'conversion_from_previous': round(visitor_to_start_rate, 2),
                    'dropoff_from_previous': round(visitor_to_start_dropoff, 2)
                },
                'form_completed': {
                    'count': form_completed,
                    'label': 'Form Completed',
                    'description': 'Candidati che hanno completato e inviato il form',
                    'conversion_from_previous': round(start_to_complete_rate, 2),
                    'dropoff_from_previous': round(start_to_complete_dropoff, 2)
                },
                'hired': {
                    'count': hired,
                    'label': 'Hired',
                    'description': 'Candidati assunti',
                    'conversion_from_previous': round(complete_to_hire_rate, 2),
                    'dropoff_from_previous': round(complete_to_hire_dropoff, 2)
                }
            },
            'overall_conversion_rate': round(overall_conversion_rate, 2),
            'total_dropoff': round(100 - overall_conversion_rate, 2),
            'start_date': start_date,
            'end_date': end_date,
            'offer_id': offer_id
        }

    def calculate_source_effectiveness(self, offer_id=None, start_date=None, end_date=None):
        """
        Calcola l'effectiveness di ogni source di recruiting.

        Per ogni source calcola:
        - Numero di candidature ricevute
        - Numero di assunzioni
        - Quality score (media ATS score)
        - Time-to-hire medio
        - Cost per source
        - ROI per source: (hired_count * avg_hire_value) / cost

        Args:
            offer_id (int, optional): ID dell'offerta specifica. Se None, analizza tutte le offerte.
            start_date (datetime, optional): Data di inizio per il filtro temporale.
            end_date (datetime, optional): Data di fine per il filtro temporale.

        Returns:
            dict: Dizionario con metriche per ogni source e ranking.
        """
        from corposostenibile.models import ApplicationSourceEnum

        # Imposta date predefinite se non fornite
        if not start_date:
            start_date = datetime.now().replace(day=1)  # Inizio del mese corrente
        if not end_date:
            end_date = datetime.now()  # Data odierna

        source_metrics = {}

        # Analizza ogni source
        for source in ApplicationSourceEnum:
            # ===== FILTRO: Solo candidature dal 13 Ottobre 2025 in poi =====
            # Query base per candidature da questo source (ESCLUSE pre-implementazione)
            applications_query = JobApplication.query.filter(
                JobApplication.created_at >= ANALYTICS_START_DATE,
                JobApplication.source == source,
                JobApplication.created_at >= start_date,
                JobApplication.created_at <= end_date
            )
            if offer_id:
                applications_query = applications_query.filter(JobApplication.job_offer_id == offer_id)

            applications = applications_query.all()
            applications_count = len(applications)

            if applications_count == 0:
                continue  # Skip sources con 0 candidature

            # 1. ASSUNZIONI da questo source
            hired_count = sum(1 for app in applications if app.status == ApplicationStatusEnum.hired)

            # 2. QUALITY SCORE: Media ATS score per questo source
            ats_scores = [app.total_score for app in applications if app.total_score is not None]
            avg_quality_score = (sum(ats_scores) / len(ats_scores)) if ats_scores else 0

            # 3. TIME-TO-HIRE medio per questo source
            hired_applications = [app for app in applications if app.status == ApplicationStatusEnum.hired]
            if hired_applications:
                total_time_days = 0
                valid_hires = 0

                for app in hired_applications:
                    # Usa ApplicationStageHistory per calcolare tempo totale
                    history_records = ApplicationStageHistory.query.filter_by(
                        application_id=app.id
                    ).order_by(ApplicationStageHistory.entered_at).all()

                    if history_records:
                        app_total_seconds = sum(
                            h.duration_seconds for h in history_records if h.duration_seconds
                        )
                        if app_total_seconds > 0:
                            total_time_days += app_total_seconds / 86400.0
                            valid_hires += 1

                avg_time_to_hire = (total_time_days / valid_hires) if valid_hires > 0 else 0
            else:
                avg_time_to_hire = 0

            # 4. COST per questo source
            if offer_id:
                offer = JobOffer.query.get(offer_id)
                # ===== FILTRO: Solo offerte create dal 13 Ottobre 2025 in poi =====
                if offer and offer.created_at >= ANALYTICS_START_DATE:
                    # Calcola costo dalla nuova tabella granulare per la piattaforma specifica
                    if source.value in ['linkedin', 'facebook', 'instagram']:
                        platform_enum = AdvertisingPlatformEnum(source.value)
                        source_cost = get_advertising_costs_for_offer(offer.id, platform_enum)
                    else:
                        source_cost = 0
                    # avg_hire_value per calcolo ROI
                    avg_hire_value = float(offer.avg_hire_value or 0)
                else:
                    # Offerta pre-esistente: reset costi a 0
                    source_cost = 0
                    avg_hire_value = 0
            else:
                # ===== FILTRO: Solo offerte create dal 13 Ottobre 2025 in poi =====
                # Somma costi di tutte le offerte per questo source
                offers = JobOffer.query.filter(
                    JobOffer.created_at >= ANALYTICS_START_DATE
                ).all()
                source_cost = 0
                total_avg_hire_value = 0
                offers_with_value = 0

                # Calcola costo dalla nuova tabella granulare
                for o in offers:
                    if source.value in ['linkedin', 'facebook', 'instagram']:
                        platform_enum = AdvertisingPlatformEnum(source.value)
                        source_cost += get_advertising_costs_for_offer(o.id, platform_enum)

                    if o.avg_hire_value:
                        total_avg_hire_value += float(o.avg_hire_value)
                        offers_with_value += 1

                avg_hire_value = (total_avg_hire_value / offers_with_value) if offers_with_value > 0 else 0

            # 5. ROI: (hired_count * avg_value) / cost
            if source_cost > 0 and hired_count > 0:
                roi = ((hired_count * avg_hire_value) / source_cost) * 100
            else:
                roi = 0

            # 6. COST PER HIRE
            cost_per_hire = (source_cost / hired_count) if hired_count > 0 else 0

            # 7. CONVERSION RATE: hired / applications
            conversion_rate = (hired_count / applications_count) * 100 if applications_count > 0 else 0

            source_metrics[source.value] = {
                'source': source.value,
                'source_label': source.value.replace('_', ' ').title(),
                'applications_count': applications_count,
                'hired_count': hired_count,
                'conversion_rate': round(conversion_rate, 2),
                'avg_quality_score': round(avg_quality_score, 2),
                'avg_time_to_hire_days': round(avg_time_to_hire, 2),
                'total_cost': round(source_cost, 2),
                'cost_per_hire': round(cost_per_hire, 2),
                'avg_hire_value': round(avg_hire_value, 2),
                'roi_percentage': round(roi, 2),
                'roi_label': f"{roi:.2f}%" if roi > 0 else "N/A"
            }

        # Ranking sources by ROI (best to worst)
        ranked_by_roi = sorted(
            source_metrics.values(),
            key=lambda x: x['roi_percentage'],
            reverse=True
        )

        # Ranking sources by quality score (best to worst)
        ranked_by_quality = sorted(
            source_metrics.values(),
            key=lambda x: x['avg_quality_score'],
            reverse=True
        )

        # Best source overall (considera ROI, quality e conversion rate)
        best_source = None
        if ranked_by_roi:
            # Calcola score composito per determinare miglior source
            for source_data in source_metrics.values():
                # Score composito: 40% ROI, 30% quality, 30% conversion
                composite_score = (
                    (source_data['roi_percentage'] * 0.4) +
                    (source_data['avg_quality_score'] * 0.3) +
                    (source_data['conversion_rate'] * 0.3)
                )
                source_data['composite_score'] = round(composite_score, 2)

            best_source = max(source_metrics.values(), key=lambda x: x['composite_score'])

        return {
            'source_metrics': source_metrics,
            'ranked_by_roi': ranked_by_roi,
            'ranked_by_quality': ranked_by_quality,
            'best_source_overall': best_source,
            'start_date': start_date,
            'end_date': end_date,
            'offer_id': offer_id
        }

    def get_kanban_calculation_explanations(self):
        """
        Restituisce le spiegazioni dei calcoli per le metriche Kanban.
        
        Returns:
            dict: Dizionario con le spiegazioni dei calcoli
        """
        return {
            'general_metrics': {
                'total': {
                    'title': 'Candidature Totali',
                    'explanation': 'Numero totale di candidature ricevute per tutte le offerte di lavoro associate al Kanban.',
                    'formula': 'COUNT(job_applications) WHERE kanban_id = X'
                },
                'hired': {
                    'title': 'Assunzioni',
                    'explanation': 'Numero di candidati che hanno raggiunto lo stage finale di tipo "HIRED" nel processo di selezione.',
                    'formula': 'COUNT(applications) WHERE current_stage.type = "HIRED"'
                },
                'rejected': {
                    'title': 'Rifiutati',
                    'explanation': 'Numero di candidati che hanno raggiunto uno stage di tipo "REJECTED" durante il processo.',
                    'formula': 'COUNT(applications) WHERE current_stage.type = "REJECTED"'
                },
                'in_progress': {
                    'title': 'In Corso',
                    'explanation': 'Numero di candidature attualmente in elaborazione, non ancora assunte o rifiutate.',
                    'formula': 'total - hired - rejected'
                },
                'hire_rate': {
                    'title': 'Tasso di Assunzione',
                    'explanation': 'Percentuale di candidature che si sono concluse con un\'assunzione rispetto al totale.',
                    'formula': '(hired / total) × 100'
                },
                'total_stages': {
                    'title': 'Numero Totale Stage',
                    'explanation': 'Numero totale di stage configurati nel processo di selezione Kanban.',
                    'formula': 'COUNT(stages) nel kanban'
                },
                'avg_application_to_hire_time': {
                    'title': 'Tempo Medio da Candidatura ad Assunzione',
                    'explanation': 'Tempo medio in giorni dal momento della candidatura fino all\'assunzione effettiva.',
                    'formula': 'AVERAGE(data_assunzione - data_candidatura) per tutte le assunzioni'
                }
            },
            'stage_metrics': {
                'count': {
                    'title': 'Numero Candidature',
                    'explanation': 'Numero totale di candidature che hanno raggiunto questo specifico stage.',
                    'formula': 'COUNT(applications) WHERE current_stage_id = stage_id'
                },
                'percentage': {
                    'title': 'Percentuale sul Totale',
                    'explanation': 'Percentuale di candidature in questo stage rispetto al totale delle candidature.',
                    'formula': '(candidature_stage / candidature_totali) × 100'
                },
                'avg_time': {
                    'title': 'Tempo Medio (giorni)',
                    'explanation': 'Tempo medio in giorni che le candidature trascorrono in questo stage prima di passare al successivo.',
                    'formula': 'AVERAGE(giorni_permanenza_stage) per tutte le candidature che hanno attraversato lo stage'
                },
                'conversion_rate': {
                    'title': 'Tasso di Conversione',
                    'explanation': 'Percentuale di candidature che passano da questo stage al successivo.',
                    'formula': '(candidature_stage_successivo / candidature_stage_corrente) × 100'
                },
                'throughput': {
                    'title': 'Throughput',
                    'explanation': 'Velocità di elaborazione delle candidature in questo stage, espressa come candidature processate per giorno.',
                    'formula': 'numero_candidature / tempo_medio_giorni'
                },
                'is_bottleneck': {
                    'title': 'Collo di Bottiglia',
                    'explanation': 'Indica se questo stage rappresenta un rallentamento nel processo. Uno stage è considerato bottleneck se il tempo medio supera la soglia configurata.',
                    'formula': 'avg_time_days > bottleneck_threshold (default: 35 giorni)'
                }
            },
            'bottleneck_detection': {
                'threshold': {
                    'title': 'Soglia Bottleneck',
                    'explanation': 'Valore percentuale configurabile che determina quando uno stage viene considerato un collo di bottiglia.',
                    'formula': 'Parametro configurabile (default: 35.0%)'
                },
                'detection': {
                    'title': 'Rilevamento Colli di Bottiglia',
                    'explanation': 'Sistema automatico che identifica gli stage che rallentano il processo di selezione basandosi sul tempo medio di permanenza.',
                    'formula': 'IF avg_time_days > bottleneck_threshold THEN is_bottleneck = true'
                },
                'title': 'Rilevamento Colli di Bottiglia',
                'explanation': 'Sistema automatico che identifica gli stage che rallentano il processo di selezione basandosi sul tempo medio di permanenza.',
                'criteria': [
                    'Tempo medio superiore alla soglia configurata (default: 35 giorni)',
                    'Accumulo significativo di candidature nello stage',
                    'Basso tasso di conversione verso lo stage successivo'
                ]
            },
            'contract_metrics': {
                'avg_application_to_hire_time': {
                    'title': 'Tempo Medio da Candidatura ad Assunzione',
                    'explanation': 'Tempo medio in giorni dal momento della candidatura fino all\'assunzione effettiva.',
                    'formula': 'AVERAGE(data_assunzione - data_candidatura) per tutte le assunzioni'
                },
                'contracts_offered': {
                    'title': 'Contratti Offerti',
                    'explanation': 'Numero totale di contratti proposti ai candidati che hanno superato il processo di selezione.',
                    'formula': 'COUNT(applications) WHERE reached_offer_stage = true'
                },
                'contracts_signed': {
                    'title': 'Contratti Firmati',
                    'explanation': 'Numero di contratti effettivamente accettati e firmati dai candidati.',
                    'formula': 'COUNT(applications) WHERE contract_signed = true'
                },
                'contract_acceptance_rate': {
                    'title': 'Tasso di Accettazione Contratti',
                    'explanation': 'Percentuale di contratti offerti che vengono effettivamente accettati dai candidati.',
                    'formula': '(contracts_signed / contracts_offered) × 100'
                }
            }
        }
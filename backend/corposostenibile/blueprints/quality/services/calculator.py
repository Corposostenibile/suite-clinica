"""
QualityScoreCalculator - Servizio principale per calcolo Quality Score.

Formula:
- Quality_cliente = (VProf + VRating) / 2 + BRec
  dove VRating = coordinator_rating se presente, altrimenti progress_rating
- Quality_settimana = Media(Quality_cliente) - Penalty
- Penalty (basato su miss_rate in fasce):
  0-5%   → 0 punti
  5-10%  → 0.5 punti
  10-20% → 1 punto
  20-30% → 2 punti
  30-40% → 3 punti
  40-50% → 4 punti
  >50%   → 5 punti
- Quality_mese = Media ultime 4 settimane
- Quality_trimestre = Media ultime 12 settimane
- Bonus band basato su Quality_trim (trimestrale):
  >= 9.0 → 100%
  >= 8.5 → 60%
  >= 8.0 → 30%
  < 8.0 → 0%
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func, desc
from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    User,
    UserSpecialtyEnum,
    QualityWeeklyScore,
    QualityClientScore,
    EleggibilitaSettimanale,
    WeeklyCheck,
    WeeklyCheckResponse,
    TypeFormResponse,
    DCACheckResponse,
    BonusBandEnum,
    CheckTypeEnum
)
from .reviews import ReviewService
from .eligibility import EligibilityService


class QualityScoreCalculator:
    """Servizio principale per calcolo Quality Score professionisti."""

    # Fasce penalty miss rate (soglia_max, penalty_punti)
    # miss_rate è espresso come decimale (0.05 = 5%)
    MISS_RATE_PENALTY_BANDS = [
        (0.05, 0.0),   # 0-5%   → 0 punti
        (0.10, 0.5),   # 5-10%  → 0.5 punti
        (0.20, 1.0),   # 10-20% → 1 punto
        (0.30, 2.0),   # 20-30% → 2 punti
        (0.40, 3.0),   # 30-40% → 3 punti
        (0.50, 4.0),   # 40-50% → 4 punti
        (1.00, 5.0),   # >50%   → 5 punti
    ]

    # Soglie bonus band (su score trimestrale) - QUALITY KPI2 (40% peso)
    # Usa direttamente le stringhe invece degli enum per evitare problemi di serializzazione
    BONUS_BANDS = [
        (9.0, '100%'),
        (8.5, '60%'),
        (8.0, '30%'),
        (0.0, '0%'),
    ]

    # Fasce bonus KPI2 Quality (per calcolo composito)
    QUALITY_BONUS_BANDS = [
        (9.0, 100),   # >= 9 → 100%
        (8.5, 60),    # 8.5-9 → 60%
        (8.0, 30),    # 8-8.5 → 30%
        (0.0, 0),     # < 8 → 0%
    ]

    # Fasce bonus KPI1 Rinnovo Adj (60% peso)
    RINNOVO_ADJ_BONUS_BANDS = [
        (80.0, 100),  # >= 80% → 100%
        (70.0, 60),   # 70-79% → 60%
        (60.0, 30),   # 60-69% → 30%
        (0.0, 0),     # < 60% → 0%
    ]

    # Pesi KPI per bonus composito
    KPI_WEIGHT_RINNOVO_ADJ = 0.60  # 60%
    KPI_WEIGHT_QUALITY = 0.40     # 40%

    @staticmethod
    def calculate_client_score(
        cliente_id: int,
        professionista_id: int,
        week_start: date,
        check_response_id: Optional[int] = None,
        check_response_type: Optional[str] = None
    ) -> Optional[QualityClientScore]:
        """
        Calcola Quality Score per singolo cliente in una settimana.

        Args:
            cliente_id: ID cliente
            professionista_id: ID professionista
            week_start: Data inizio settimana
            check_response_id: ID della response (WeeklyCheck/TypeForm/DCA)
            check_response_type: Tipo check ('weekly_check', 'typeform', 'dca_check')

        Returns:
            QualityClientScore creata/aggiornata, None se non ha fatto check
        """
        week_start, week_end = EligibilityService.get_week_bounds(week_start)

        # Verifica eleggibilità
        elig = db.session.query(EleggibilitaSettimanale).filter_by(
            cliente_id=cliente_id,
            professionista_id=professionista_id,
            week_start_date=week_start,
            eleggibile=True
        ).first()

        if not elig:
            return None  # Cliente non eleggibile

        # Trova check response
        voto_prof = None
        voto_percorso = None
        voto_coordinatore = None
        check_effettuato = False

        if check_response_type == 'weekly_check':
            check = db.session.get(WeeklyCheckResponse, check_response_id)
            if check:
                voto_prof = check.professional_rating
                voto_percorso = check.progress_rating
                voto_coordinatore = check.coordinator_rating  # Override se presente
                check_effettuato = True

        elif check_response_type == 'typeform':
            check = db.session.get(TypeFormResponse, check_response_id)
            if check:
                voto_prof = check.professional_rating
                voto_percorso = check.progress_rating
                voto_coordinatore = check.coordinator_rating
                check_effettuato = True

        elif check_response_type == 'dca_check':
            check = db.session.get(DCACheckResponse, check_response_id)
            if check:
                voto_prof = check.professional_rating
                voto_percorso = check.progress_rating
                voto_coordinatore = check.coordinator_rating
                check_effettuato = True

        if not check_effettuato:
            return None  # Nessun check fatto

        # Calcola VRating: usa coordinator_rating se presente, altrimenti progress_rating
        v_rating = voto_coordinatore if voto_coordinatore is not None else voto_percorso

        # Verifica che abbiamo entrambi i voti
        if voto_prof is None or v_rating is None:
            return None  # Dati incompleti

        # Calcola bonus recensione (BRec)
        brec_value = ReviewService.get_brec_for_professional(professionista_id, week_start)

        # Formula: Quality = (VProf + VRating) / 2 + BRec
        quality_score = ((voto_prof + v_rating) / 2.0) + brec_value

        # Crea o aggiorna QualityClientScore
        existing = db.session.query(QualityClientScore).filter_by(
            cliente_id=cliente_id,
            professionista_id=professionista_id,
            week_start_date=week_start
        ).first()

        if existing:
            existing.voto_professionista = voto_prof
            existing.voto_percorso = voto_percorso
            existing.voto_coordinatore = voto_coordinatore
            existing.brec_value = brec_value
            existing.quality_score = round(quality_score, 2)
            existing.check_response_id = check_response_id
            existing.check_response_type = check_response_type
            existing.check_effettuato = True
            client_score = existing
        else:
            client_score = QualityClientScore(
                cliente_id=cliente_id,
                professionista_id=professionista_id,
                week_start_date=week_start,
                voto_professionista=voto_prof,
                voto_percorso=voto_percorso,
                voto_coordinatore=voto_coordinatore,
                brec_value=brec_value,
                quality_score=round(quality_score, 2),
                check_response_id=check_response_id,
                check_response_type=check_response_type,
                check_effettuato=True
            )
            db.session.add(client_score)

        # Marca check come effettuato in eleggibilità
        if elig:
            elig.check_effettuato = True

        db.session.commit()

        return client_score

    @classmethod
    def process_check_responses_for_week(
        cls,
        week_start: date,
        professionista_id: Optional[int] = None,
        professionista_ids: Optional[List[int]] = None,
    ) -> Dict[str, int]:
        """
        Trova tutti i WeeklyCheckResponse nella settimana e crea QualityClientScore.

        Per ogni cliente eleggibile, cerca se ha compilato un check nella settimana.
        Se sì, estrae i voti per il professionista corretto e crea il QualityClientScore.

        Args:
            week_start: Data inizio settimana
            professionista_id: Filtra per professionista (opzionale)

        Returns:
            Dict con statistiche: processed, created, errors
        """
        week_start, week_end = EligibilityService.get_week_bounds(week_start)
        week_start_dt = datetime.combine(week_start, datetime.min.time())
        week_end_dt = datetime.combine(week_end, datetime.max.time())

        # Mapping specialty -> campo rating in WeeklyCheckResponse
        # Nutrizione specialties: nutritionist_rating
        # Coach specialties: coach_rating
        # Psicologia specialties: psychologist_rating
        SPECIALTY_RATING_MAP = {
            UserSpecialtyEnum.nutrizione: 'nutritionist_rating',
            UserSpecialtyEnum.nutrizionista: 'nutritionist_rating',
            UserSpecialtyEnum.coach: 'coach_rating',
            UserSpecialtyEnum.psicologia: 'psychologist_rating',
            UserSpecialtyEnum.psicologo: 'psychologist_rating',
        }

        stats = {'processed': 0, 'created': 0, 'updated': 0, 'skipped': 0}

        # 1. Ottieni tutte le eleggibilità della settimana
        elig_query = db.session.query(EleggibilitaSettimanale).filter_by(
            week_start_date=week_start,
            eleggibile=True
        )
        target_prof_ids = None
        if professionista_ids:
            target_prof_ids = list({int(pid) for pid in professionista_ids if pid is not None})
        elif professionista_id:
            target_prof_ids = [professionista_id]

        if professionista_id:
            elig_query = elig_query.filter_by(professionista_id=professionista_id)
        elif target_prof_ids:
            elig_query = elig_query.filter(EleggibilitaSettimanale.professionista_id.in_(target_prof_ids))

        eligibilities = elig_query.all()
        if not eligibilities:
            return stats

        # 2. Pre-carica professionisti per sapere la specialty
        prof_ids = list(set(e.professionista_id for e in eligibilities))
        profs = db.session.query(User).filter(User.id.in_(prof_ids)).all() if prof_ids else []
        prof_specialty_map = {p.id: p.specialty for p in profs}

        # 3. Pre-carica tutti i WeeklyCheck per i clienti eleggibili
        cliente_ids = list(set(e.cliente_id for e in eligibilities))
        weekly_checks = db.session.query(WeeklyCheck).filter(
            WeeklyCheck.cliente_id.in_(cliente_ids),
            WeeklyCheck.is_active == True
        ).all() if cliente_ids else []

        # Mappa cliente_id -> WeeklyCheck
        cliente_wc_map = {wc.cliente_id: wc for wc in weekly_checks}

        # 4. Pre-carica tutte le WeeklyCheckResponse della settimana per questi check
        wc_ids = [wc.id for wc in weekly_checks]
        responses = db.session.query(WeeklyCheckResponse).filter(
            WeeklyCheckResponse.weekly_check_id.in_(wc_ids),
            WeeklyCheckResponse.submit_date >= week_start_dt,
            WeeklyCheckResponse.submit_date <= week_end_dt
        ).all() if wc_ids else []

        # Mappa weekly_check_id -> ultima response della settimana
        wc_response_map = {}
        for r in responses:
            # Prendi l'ultima response per ogni weekly_check
            if r.weekly_check_id not in wc_response_map:
                wc_response_map[r.weekly_check_id] = r
            elif r.submit_date > wc_response_map[r.weekly_check_id].submit_date:
                wc_response_map[r.weekly_check_id] = r

        # 5. Pre-carica BRec per tutti i professionisti (batch)
        brec_map = ReviewService.get_brec_for_professionals(prof_ids, week_start)

        # 5b. Pre-carica QualityClientScore esistenti per evitare query nel loop (N+1)
        existing_scores = db.session.query(QualityClientScore).filter(
            QualityClientScore.week_start_date == week_start,
            QualityClientScore.professionista_id.in_(prof_ids),
            QualityClientScore.cliente_id.in_(cliente_ids)
        ).all() if prof_ids and cliente_ids else []
        existing_scores_map = {
            (s.cliente_id, s.professionista_id): s for s in existing_scores
        }

        # 6. Processa ogni eleggibilità
        for elig in eligibilities:
            stats['processed'] += 1

            cliente_id = elig.cliente_id
            prof_id = elig.professionista_id
            specialty = prof_specialty_map.get(prof_id)

            # Trova WeeklyCheck del cliente
            wc = cliente_wc_map.get(cliente_id)
            if not wc:
                stats['skipped'] += 1
                continue

            # Trova response della settimana
            response = wc_response_map.get(wc.id)
            if not response:
                stats['skipped'] += 1
                continue

            # Estrai voto professionista in base alla specialty
            rating_field = SPECIALTY_RATING_MAP.get(specialty)
            if not rating_field:
                stats['skipped'] += 1
                continue

            voto_prof = getattr(response, rating_field, None)
            voto_percorso = response.progress_rating
            voto_coordinatore = response.coordinator_rating

            # VRating: coordinator se presente, altrimenti progress
            v_rating = voto_coordinatore if voto_coordinatore is not None else voto_percorso

            # Skip se mancano voti essenziali
            if voto_prof is None or v_rating is None:
                stats['skipped'] += 1
                continue

            # Calcola quality score
            brec = brec_map.get(prof_id, 0.0)
            quality_score = ((voto_prof + v_rating) / 2.0) + brec

            # Crea o aggiorna QualityClientScore
            existing = existing_scores_map.get((cliente_id, prof_id))

            if existing:
                existing.voto_professionista = voto_prof
                existing.voto_percorso = voto_percorso
                existing.voto_coordinatore = voto_coordinatore
                existing.brec_value = brec
                existing.quality_score = round(quality_score, 2)
                existing.check_response_id = response.id
                existing.check_response_type = 'weekly_check'
                existing.check_effettuato = True
                stats['updated'] += 1
            else:
                client_score = QualityClientScore(
                    cliente_id=cliente_id,
                    professionista_id=prof_id,
                    week_start_date=week_start,
                    week_end_date=week_end,
                    voto_professionista=voto_prof,
                    voto_percorso=voto_percorso,
                    voto_coordinatore=voto_coordinatore,
                    brec_value=brec,
                    quality_score=round(quality_score, 2),
                    check_response_id=response.id,
                    check_response_type='weekly_check',
                    check_effettuato=True
                )
                db.session.add(client_score)
                existing_scores_map[(cliente_id, prof_id)] = client_score
                stats['created'] += 1

            # Marca eleggibilità come check effettuato
            elig.check_effettuato = True

        db.session.flush()
        return stats

    @classmethod
    def calculate_weekly_score(
        cls,
        professionista_id: int,
        week_start: date,
        calculated_by_user_id: Optional[int] = None
    ) -> QualityWeeklyScore:
        """
        Calcola Quality Score settimanale aggregato per un professionista.

        Args:
            professionista_id: ID professionista
            week_start: Data inizio settimana
            calculated_by_user_id: ID utente che richiede calcolo

        Returns:
            QualityWeeklyScore creato/aggiornato
        """
        week_start, week_end = EligibilityService.get_week_bounds(week_start)

        # 1. Ottieni dati eleggibilità
        elig_records = db.session.query(EleggibilitaSettimanale).filter_by(
            professionista_id=professionista_id,
            week_start_date=week_start,
            eleggibile=True
        ).all()

        n_clients_eligible = len(elig_records)
        n_checks_done = sum(1 for e in elig_records if e.check_effettuato)

        # Calcola miss rate
        miss_rate = 0.0
        if n_clients_eligible > 0:
            miss_rate = (n_clients_eligible - n_checks_done) / n_clients_eligible

        # 2. Ottieni score clienti
        client_scores = db.session.query(QualityClientScore).filter_by(
            professionista_id=professionista_id,
            week_start_date=week_start,
            check_effettuato=True
        ).all()

        # Calcola quality raw (media pura voti)
        quality_raw = None
        if client_scores:
            avg_score = sum(cs.quality_score for cs in client_scores) / len(client_scores)
            quality_raw = round(avg_score, 2)

        # 3. Calcola bonus recensioni medio
        avg_brec_week = 0.0
        if client_scores:
            total_brec = sum(cs.brec_value for cs in client_scores)
            avg_brec_week = round(total_brec / len(client_scores), 4)

        # 4. Calcola penalty miss rate con fasce
        # Il penalty è un valore positivo che verrà sottratto dallo score
        penalty_value = cls._get_miss_rate_penalty(miss_rate)
        penalty_week = -penalty_value  # Negativo per retrocompatibilità con il campo DB

        # 5. Calcola quality final
        quality_final = None
        if quality_raw is not None:
            quality_final = round(quality_raw - penalty_value, 2)

        # 6. Calcola trend vs settimana precedente
        prev_week_start = week_start - timedelta(days=7)
        prev_week_score = db.session.query(QualityWeeklyScore).filter_by(
            professionista_id=professionista_id,
            week_start_date=prev_week_start
        ).first()

        delta_vs_last_week = None
        trend_indicator = None
        if prev_week_score and prev_week_score.quality_final and quality_final:
            delta_vs_last_week = round(quality_final - prev_week_score.quality_final, 2)
            if delta_vs_last_week > 0.1:
                trend_indicator = 'up'
            elif delta_vs_last_week < -0.1:
                trend_indicator = 'down'
            else:
                trend_indicator = 'stable'

        # 7. Calcola aggregati rolling (mese = 4 settimane, trimestre = 12 settimane)
        quality_month = cls._calculate_rolling_avg(professionista_id, week_start, weeks=4)
        quality_trim = cls._calculate_rolling_avg(professionista_id, week_start, weeks=12)

        # 8. Determina bonus band (basato su quality_trim trimestrale)
        bonus_band = cls._get_bonus_band(quality_trim)

        # 9. Calcola settimana e trimestre
        week_number = week_start.isocalendar()[1]
        year = week_start.year
        quarter = ReviewService.get_quarter_string(week_start)

        # 10. Crea o aggiorna QualityWeeklyScore
        existing = db.session.query(QualityWeeklyScore).filter_by(
            professionista_id=professionista_id,
            week_start_date=week_start
        ).first()

        if existing:
            existing.n_clients_eligible = n_clients_eligible
            existing.n_checks_done = n_checks_done
            existing.miss_rate = round(miss_rate, 4)
            existing.quality_raw = quality_raw
            existing.avg_brec_week = avg_brec_week
            existing.penalty_week = penalty_week
            existing.quality_final = quality_final
            existing.delta_vs_last_week = delta_vs_last_week
            existing.trend_indicator = trend_indicator
            existing.quality_month = quality_month
            existing.quality_trim = quality_trim
            existing.bonus_band = bonus_band
            existing.calculated_at = datetime.utcnow()
            existing.calculated_by_user_id = calculated_by_user_id
            existing.calculation_status = 'completed'
            weekly_score = existing
        else:
            weekly_score = QualityWeeklyScore(
                professionista_id=professionista_id,
                week_start_date=week_start,
                week_end_date=week_end,
                week_number=week_number,
                year=year,
                quarter=quarter,
                n_clients_eligible=n_clients_eligible,
                n_checks_done=n_checks_done,
                miss_rate=round(miss_rate, 4),
                quality_raw=quality_raw,
                avg_brec_week=avg_brec_week,
                penalty_week=penalty_week,
                quality_final=quality_final,
                delta_vs_last_week=delta_vs_last_week,
                trend_indicator=trend_indicator,
                quality_month=quality_month,
                quality_trim=quality_trim,
                bonus_band=bonus_band,
                calculated_by_user_id=calculated_by_user_id,
                calculated_at=datetime.utcnow(),
                calculation_status='completed'
            )
            db.session.add(weekly_score)

        # 11. Aggiorna User con score correnti
        user = db.session.get(User, professionista_id)
        if user:
            user.quality_score_current_week = quality_final
            user.quality_score_current_month = quality_month
            user.quality_score_current_quarter = quality_trim
            # bonus_band è già una stringa ('100%', '60%', '30%', '0%')
            user.bonus_band_current = bonus_band
            user.quality_last_updated = datetime.utcnow()

        # NON fare commit qui - sarà fatto dal chiamante
        # db.session.commit()

        return weekly_score

    @staticmethod
    def _calculate_rolling_avg(
        professionista_id: int,
        week_start: date,
        weeks: int
    ) -> Optional[float]:
        """
        Calcola media rolling degli ultimi N settimane (inclusa quella corrente).

        Args:
            professionista_id: ID professionista
            week_start: Data inizio settimana corrente
            weeks: Numero settimane (4 per mese, 12 per trimestre)

        Returns:
            Media quality_final oppure None se dati insufficienti
        """
        # Trova ultime N settimane (inclusa quella corrente)
        scores = db.session.query(QualityWeeklyScore).filter(
            QualityWeeklyScore.professionista_id == professionista_id,
            QualityWeeklyScore.week_start_date <= week_start,
            QualityWeeklyScore.quality_final.isnot(None)
        ).order_by(desc(QualityWeeklyScore.week_start_date)).limit(weeks).all()

        if not scores:
            return None

        avg = sum(s.quality_final for s in scores) / len(scores)
        return round(avg, 2)

    @classmethod
    def _get_bonus_band(cls, quality_trim: Optional[float]) -> str:
        """
        Determina bonus band in base a score trimestrale.

        Args:
            quality_trim: Score trimestrale

        Returns:
            Stringa bonus band ('100%', '60%', '30%', '0%')
        """
        if quality_trim is None:
            return '0%'

        for threshold, band_str in cls.BONUS_BANDS:
            if quality_trim >= threshold:
                return band_str  # Restituisce direttamente la stringa

        return '0%'

    @classmethod
    def _get_miss_rate_penalty(cls, miss_rate: float) -> float:
        """
        Calcola il penalty in base al miss rate usando le fasce definite.

        Fasce:
        - 0-5%   → 0 punti
        - 5-10%  → 0.5 punti
        - 10-20% → 1 punto
        - 20-30% → 2 punti
        - 30-40% → 3 punti
        - 40-50% → 4 punti
        - >50%   → 5 punti

        Args:
            miss_rate: Tasso di check mancati (0.0 - 1.0)

        Returns:
            Penalty in punti (valore positivo, verrà sottratto dallo score)
        """
        if miss_rate <= 0:
            return 0.0

        for threshold, penalty in cls.MISS_RATE_PENALTY_BANDS:
            if miss_rate <= threshold:
                return penalty

        # Se supera tutte le soglie (>100%), applica penalty massima
        return 5.0

    @classmethod
    def calculate_full_week(
        cls,
        week_start: date,
        professionista_id: Optional[int] = None,
        calculated_by_user_id: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Calcola Quality Score completo per una settimana:
        1. Eleggibilità clienti
        2. Score clienti (da check responses esistenti)
        3. Score settimanali professionisti

        Args:
            week_start: Data inizio settimana
            professionista_id: ID professionista (None = tutti)
            calculated_by_user_id: ID utente che richiede calcolo

        Returns:
            Dict con statistiche complete
        """
        # 1. Calcola eleggibilità (già ottimizzato con bulk operations)
        elig_stats = EligibilityService.calculate_eligibility_for_week(
            week_start,
            professionista_id,
            calculated_by_user_id,
            auto_commit=False,
        )

        # 2. Processa check responses e crea QualityClientScore
        check_stats = cls.process_check_responses_for_week(week_start, professionista_id)

        # 3. OTTIMIZZAZIONE: Batch pre-fetch dati necessari per tutti i professionisti
        professionisti_ids = elig_stats['professionisti']

        # Pre-fetch tutti gli User che servono (bulk load)
        users_dict = {}
        if professionisti_ids:
            users = db.session.query(User).filter(
                User.id.in_(professionisti_ids)
            ).all()
            users_dict = {u.id: u for u in users}

        # 4. Calcola score settimanali
        weekly_scores = []

        for prof_id in professionisti_ids:
            # Calcola weekly score (no commit interno)
            weekly_score = cls.calculate_weekly_score(
                prof_id, week_start, calculated_by_user_id
            )
            weekly_scores.append({
                'professionista_id': prof_id,
                'quality_final': weekly_score.quality_final,
                'quality_month': weekly_score.quality_month,
                'quality_trim': weekly_score.quality_trim,
                'bonus_band': weekly_score.bonus_band  # Già una stringa
            })

        # 5. OTTIMIZZAZIONE: Single commit finale
        db.session.commit()

        return {
            'week_start': week_start,
            'week_end': elig_stats['week_end'],
            'eligibility': elig_stats,
            'check_processing': check_stats,
            'weekly_scores': weekly_scores,
            'calculated_at': datetime.utcnow(),
            'calculated_by_user_id': calculated_by_user_id
        }

    @classmethod
    def _get_bonus_from_bands(cls, value: float, bands: List[Tuple[float, int]]) -> int:
        """
        Determina il bonus percentage in base al valore e alle fasce.

        Args:
            value: Valore da valutare
            bands: Lista di tuple (soglia, bonus_percentage)

        Returns:
            Bonus percentage (0, 30, 60, 100)
        """
        for threshold, bonus in bands:
            if value >= threshold:
                return bonus
        return 0

    @classmethod
    def get_rinnovo_adj_percentage(
        cls,
        professionista_id: int,
        quarter: str
    ) -> Optional[float]:
        """
        Calcola % Rinnovo Adjustato per un professionista nel trimestre.

        Formula: clienti_rinnovati / clienti_con_contratto_scaduto × 100

        Args:
            professionista_id: ID professionista
            quarter: Trimestre (es. "2025-Q4")

        Returns:
            Percentuale rinnovo adj (0-100), None se dati insufficienti
        """
        from .super_malus import SuperMalusService

        start_date, end_date = SuperMalusService.get_quarter_dates(quarter)

        # Query per clienti del professionista con rinnovo/scadenza nel trimestre.
        # Nei modelli correnti la data utile è `Cliente.data_rinnovo`.
        from corposostenibile.models import SubscriptionContract, SubscriptionRenewal

        # Clienti del professionista
        professionista = db.session.get(User, professionista_id)
        if not professionista or not professionista.specialty:
            return None

        specialty = professionista.specialty.value.lower()

        # Determina il campo del cliente da usare
        if 'nutri' in specialty:
            cliente_field = Cliente.nutrizionista_id
        elif 'coach' in specialty:
            cliente_field = Cliente.coach_id
        elif 'psic' in specialty:
            cliente_field = Cliente.psicologa_id
        else:
            return None

        # Trova clienti assegnati al professionista con rinnovo previsto nel periodo
        clienti_scaduti = db.session.query(Cliente).filter(
            cliente_field == professionista_id,
            Cliente.data_rinnovo.isnot(None),
            Cliente.data_rinnovo >= start_date,
            Cliente.data_rinnovo <= end_date
        ).all()

        n_scaduti = len(clienti_scaduti)
        if n_scaduti == 0:
            return None  # Nessun cliente scaduto, non calcolabile

        # Conta quanti hanno rinnovato
        n_rinnovati = 0
        for cliente in clienti_scaduti:
            # Verifica se esiste almeno un rinnovo registrato per un contratto del cliente
            # a partire dalla data rinnovo prevista.
            rinnovo = db.session.query(SubscriptionRenewal).join(
                SubscriptionContract,
                SubscriptionRenewal.subscription_id == SubscriptionContract.subscription_id
            ).filter(
                SubscriptionContract.cliente_id == cliente.cliente_id,
                SubscriptionRenewal.renewal_payment_date.isnot(None),
                SubscriptionRenewal.renewal_payment_date >= cliente.data_rinnovo
            ).first()

            if rinnovo:
                n_rinnovati += 1

        # Calcola percentuale
        perc = (n_rinnovati / n_scaduti) * 100
        return round(perc, 2)

    @classmethod
    def _get_rinnovo_adj_percentages_bulk(
        cls,
        professionista_ids: List[int],
        quarter: str
    ) -> Dict[int, Optional[float]]:
        """
        Calcola Rinnovo Adj % per più professionisti con query aggregate.
        """
        from .super_malus import SuperMalusService
        from corposostenibile.models import SubscriptionContract, SubscriptionRenewal

        if not professionista_ids:
            return {}

        start_date, end_date = SuperMalusService.get_quarter_dates(quarter)
        users = db.session.query(User).filter(User.id.in_(professionista_ids)).all()
        users_by_id = {u.id: u for u in users}

        by_field = {
            'nutrizionista_id': [],
            'coach_id': [],
            'psicologa_id': [],
        }
        for pid in professionista_ids:
            user = users_by_id.get(pid)
            specialty = (user.specialty.value.lower() if user and user.specialty else '')
            if 'nutri' in specialty:
                by_field['nutrizionista_id'].append(pid)
            elif 'coach' in specialty:
                by_field['coach_id'].append(pid)
            elif 'psic' in specialty:
                by_field['psicologa_id'].append(pid)

        scaduti_count = {pid: 0 for pid in professionista_ids}
        rinnovati_count = {pid: 0 for pid in professionista_ids}

        for field_name, pids in by_field.items():
            if not pids:
                continue

            field_col = getattr(Cliente, field_name)
            clienti_scaduti = db.session.query(
                Cliente.cliente_id,
                field_col.label('professionista_id'),
                Cliente.data_rinnovo,
            ).filter(
                field_col.in_(pids),
                Cliente.data_rinnovo.isnot(None),
                Cliente.data_rinnovo >= start_date,
                Cliente.data_rinnovo <= end_date
            ).all()

            if not clienti_scaduti:
                continue

            cliente_rows = {row.cliente_id: row for row in clienti_scaduti}
            for row in clienti_scaduti:
                scaduti_count[row.professionista_id] += 1

            renewal_max_dates = db.session.query(
                SubscriptionContract.cliente_id,
                func.max(SubscriptionRenewal.renewal_payment_date).label('last_renewal_payment_date')
            ).join(
                SubscriptionRenewal,
                SubscriptionRenewal.subscription_id == SubscriptionContract.subscription_id
            ).filter(
                SubscriptionContract.cliente_id.in_(list(cliente_rows.keys())),
                SubscriptionRenewal.renewal_payment_date.isnot(None),
            ).group_by(SubscriptionContract.cliente_id).all()

            for renewal_row in renewal_max_dates:
                cliente_row = cliente_rows.get(renewal_row.cliente_id)
                if not cliente_row:
                    continue
                if renewal_row.last_renewal_payment_date and renewal_row.last_renewal_payment_date >= cliente_row.data_rinnovo:
                    rinnovati_count[cliente_row.professionista_id] += 1

        result = {}
        for pid in professionista_ids:
            n_scaduti = scaduti_count.get(pid, 0)
            if n_scaduti == 0:
                result[pid] = None
                continue
            result[pid] = round((rinnovati_count.get(pid, 0) / n_scaduti) * 100, 2)
        return result

    @classmethod
    def calculate_quarterly_composite_kpi(
        cls,
        weekly_score: 'QualityWeeklyScore',
        apply_super_malus: bool = True,
        rinnovo_adj_override: Optional[float] = None,
        use_rinnovo_adj_override: bool = False,
    ) -> None:
        """
        Calcola KPI composito trimestrale e applica Super Malus.

        Aggiorna i campi:
        - rinnovo_adj_percentage
        - rinnovo_adj_bonus_band
        - quality_bonus_band
        - final_bonus_percentage
        - (Super Malus fields via SuperMalusService)
        - final_bonus_after_malus

        Args:
            weekly_score: QualityWeeklyScore instance
            apply_super_malus: Se True, applica anche Super Malus
        """
        from .super_malus import SuperMalusService

        quarter = weekly_score.quarter
        professionista_id = weekly_score.professionista_id

        # 1. Calcola Rinnovo Adj %
        if use_rinnovo_adj_override:
            rinnovo_adj = rinnovo_adj_override
        else:
            rinnovo_adj = cls.get_rinnovo_adj_percentage(professionista_id, quarter)
        weekly_score.rinnovo_adj_percentage = rinnovo_adj

        # 2. Determina fasce bonus per entrambi i KPI
        if rinnovo_adj is not None:
            rinnovo_bonus = cls._get_bonus_from_bands(rinnovo_adj, cls.RINNOVO_ADJ_BONUS_BANDS)
            weekly_score.rinnovo_adj_bonus_band = f"{rinnovo_bonus}%"
        else:
            rinnovo_bonus = 0
            weekly_score.rinnovo_adj_bonus_band = '0%'

        quality_trim = weekly_score.quality_trim
        if quality_trim is not None:
            quality_bonus = cls._get_bonus_from_bands(quality_trim, cls.QUALITY_BONUS_BANDS)
            weekly_score.quality_bonus_band = f"{quality_bonus}%"
        else:
            quality_bonus = 0
            weekly_score.quality_bonus_band = '0%'

        # 3. Calcola bonus composito pesato
        # Formula: (60% × rinnovo_bonus) + (40% × quality_bonus)
        final_bonus = (
            cls.KPI_WEIGHT_RINNOVO_ADJ * rinnovo_bonus +
            cls.KPI_WEIGHT_QUALITY * quality_bonus
        )
        weekly_score.final_bonus_percentage = round(final_bonus, 2)

        # 4. Applica Super Malus se richiesto
        if apply_super_malus:
            SuperMalusService.apply_super_malus_to_score(weekly_score, quarter)
        else:
            weekly_score.final_bonus_after_malus = weekly_score.final_bonus_percentage

    @classmethod
    def calculate_quarterly_scores(
        cls,
        quarter: str,
        calculated_by_user_id: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Calcola KPI composito trimestrale per tutti i professionisti.

        Trova l'ultima settimana del trimestre per ogni professionista
        e calcola il KPI composito con Super Malus.

        Args:
            quarter: Trimestre (es. "2025-Q4")
            calculated_by_user_id: ID utente che richiede calcolo

        Returns:
            Dict con statistiche
        """
        from .super_malus import SuperMalusService

        start_date, end_date = SuperMalusService.get_quarter_dates(quarter)

        # Trova tutti gli score settimanali del trimestre
        quarterly_scores = db.session.query(QualityWeeklyScore).filter(
            QualityWeeklyScore.quarter == quarter
        ).order_by(
            QualityWeeklyScore.professionista_id,
            desc(QualityWeeklyScore.week_start_date)
        ).all()

        # Raggruppa per professionista, prendi solo l'ultima settimana
        prof_latest_scores = {}
        for score in quarterly_scores:
            if score.professionista_id not in prof_latest_scores:
                prof_latest_scores[score.professionista_id] = score

        stats = {
            'quarter': quarter,
            'professionisti_processati': 0,
            'super_malus_applicati': 0,
            'results': []
        }

        rinnovo_adj_map = cls._get_rinnovo_adj_percentages_bulk(list(prof_latest_scores.keys()), quarter)

        for prof_id, weekly_score in prof_latest_scores.items():
            # Calcola KPI composito con Super Malus
            cls.calculate_quarterly_composite_kpi(
                weekly_score,
                apply_super_malus=True,
                rinnovo_adj_override=rinnovo_adj_map.get(prof_id),
                use_rinnovo_adj_override=True,
            )

            stats['professionisti_processati'] += 1
            if weekly_score.super_malus_applied:
                stats['super_malus_applicati'] += 1

            stats['results'].append({
                'professionista_id': prof_id,
                'quality_trim': weekly_score.quality_trim,
                'rinnovo_adj_percentage': weekly_score.rinnovo_adj_percentage,
                'final_bonus_percentage': weekly_score.final_bonus_percentage,
                'super_malus_applied': weekly_score.super_malus_applied,
                'super_malus_percentage': weekly_score.super_malus_percentage,
                'final_bonus_after_malus': weekly_score.final_bonus_after_malus
            })

        db.session.commit()

        stats['calculated_at'] = datetime.utcnow()
        stats['calculated_by_user_id'] = calculated_by_user_id

        return stats

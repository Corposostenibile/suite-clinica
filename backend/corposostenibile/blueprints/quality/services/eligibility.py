"""
EligibilityService - Servizio per calcolo eleggibilità clienti ai check settimanali.

Criteri eleggibilità:
- Stato servizio specifico 'attivo' per il tipo di professionista (basato su specialty):
  - Nutrizionista (specialty: nutrizione/nutrizionista): stato_nutrizione == 'attivo'
  - Coach (specialty: coach): stato_coach == 'attivo'
  - Psicologo (specialty: psicologia/psicologo): stato_psicologia == 'attivo'
- Ha almeno un professionista assegnato (nutrizionista/coach/psicologa)
- Cliente attivo da almeno 7 giorni (dalla data_inizio_abbonamento)
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_
from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    User,
    UserSpecialtyEnum,
    EleggibilitaSettimanale,
    cliente_nutrizionisti,
    cliente_coaches,
    cliente_psicologi
)


class EligibilityService:
    """Servizio per gestione eleggibilità clienti ai check settimanali."""

    GIORNI_MINIMI_ATTIVO = 7  # Cliente deve essere attivo almeno 7 giorni
    STATI_ELEGGIBILI = ['attivo']  # Solo servizi con stato 'attivo' sono eleggibili

    # Mapping specialty -> tipo servizio da verificare
    # Nutrizione specialties: controlla stato_nutrizione
    NUTRIZIONE_SPECIALTIES = [UserSpecialtyEnum.nutrizione, UserSpecialtyEnum.nutrizionista]
    # Coach specialties: controlla stato_coach
    COACH_SPECIALTIES = [UserSpecialtyEnum.coach]
    # Psicologia specialties: controlla stato_psicologia
    PSICOLOGIA_SPECIALTIES = [UserSpecialtyEnum.psicologia, UserSpecialtyEnum.psicologo]


    @staticmethod
    def get_week_bounds(target_date: Optional[date] = None) -> Tuple[date, date]:
        """
        Calcola inizio (lunedì) e fine (domenica) della settimana per una data.

        Args:
            target_date: Data di riferimento (default: oggi)

        Returns:
            Tuple (week_start, week_end)
        """
        if target_date is None:
            target_date = date.today()

        # ISO weekday: 1=Lun, 7=Dom
        weekday = target_date.isoweekday()
        week_start = target_date - timedelta(days=weekday - 1)  # Lunedì
        week_end = week_start + timedelta(days=6)  # Domenica

        return week_start, week_end

    @classmethod
    def is_cliente_eligible(
        cls,
        cliente: Cliente,
        professionista_id: int,
        week_start: date,
        professionista: Optional[User] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifica se un cliente è eleggibile per il check settimanale.

        Args:
            cliente: Istanza Cliente
            professionista_id: ID professionista da verificare
            week_start: Data inizio settimana (lunedì)
            professionista: Istanza User del professionista (opzionale, verrà caricata se None)

        Returns:
            Tuple (eleggibile: bool, motivo_non_eleggibile: str | None)
        """
        # 0. Carica professionista se non fornito
        if professionista is None:
            professionista = db.session.get(User, professionista_id)
            if not professionista:
                return False, f"Professionista {professionista_id} non trovato"

        # 1. Verifica stato servizio specifico in base alla specialty del professionista
        specialty = professionista.specialty

        if specialty in cls.NUTRIZIONE_SPECIALTIES:
            # Nutrizionista: verifica stato_nutrizione
            stato_servizio = cliente.stato_nutrizione
            if stato_servizio not in cls.STATI_ELEGGIBILI:
                return False, f"Stato nutrizione non eleggibile: {stato_servizio}"
        elif specialty in cls.COACH_SPECIALTIES:
            # Coach: verifica stato_coach
            stato_servizio = cliente.stato_coach
            if stato_servizio not in cls.STATI_ELEGGIBILI:
                return False, f"Stato coach non eleggibile: {stato_servizio}"
        elif specialty in cls.PSICOLOGIA_SPECIALTIES:
            # Psicologo: verifica stato_psicologia
            stato_servizio = cliente.stato_psicologia
            if stato_servizio not in cls.STATI_ELEGGIBILI:
                return False, f"Stato psicologia non eleggibile: {stato_servizio}"
        else:
            # Specialty non riconosciuta, fallback su stato_cliente globale
            if cliente.stato_cliente not in cls.STATI_ELEGGIBILI:
                return False, f"Stato cliente non eleggibile: {cliente.stato_cliente}"

        # 2. Verifica professionista assegnato (colonne singole O relazioni M2M)
        prof_assegnato = (
            # Colonne singole
            cliente.nutrizionista_id == professionista_id or
            cliente.coach_id == professionista_id or
            cliente.psicologa_id == professionista_id or
            # Relazioni M2M
            professionista_id in [n.id for n in cliente.nutrizionisti_multipli] or
            professionista_id in [c.id for c in cliente.coaches_multipli] or
            professionista_id in [p.id for p in cliente.psicologi_multipli]
        )
        if not prof_assegnato:
            return False, f"Professionista {professionista_id} non assegnato al cliente"

        # 3. Verifica giorni attivo (almeno 7 giorni dalla data_inizio_abbonamento)
        # NOTA: check_day NON viene più verificato - ci interessa solo che il cliente
        # compili il check una volta a settimana, non importa quale giorno
        if cliente.data_inizio_abbonamento:
            giorni_attivo = (week_start - cliente.data_inizio_abbonamento).days
            if giorni_attivo < cls.GIORNI_MINIMI_ATTIVO:
                return False, f"Cliente attivo solo da {giorni_attivo} giorni (minimo {cls.GIORNI_MINIMI_ATTIVO})"
        else:
            return False, "Manca data_inizio_abbonamento"

        # Cliente eleggibile
        return True, None

    @classmethod
    def calculate_eligibility_for_week(
        cls,
        week_start: date,
        professionista_id: Optional[int] = None,
        calculated_by_user_id: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Calcola eleggibilità per tutti i clienti di un professionista in una settimana.
        Crea/aggiorna record in eleggibilita_settimanale.

        Args:
            week_start: Data inizio settimana (lunedì)
            professionista_id: ID professionista (None = tutti i professionisti)
            calculated_by_user_id: ID utente che ha richiesto il calcolo

        Returns:
            Dict con statistiche: {
                'total_processed': int,
                'eligible': int,
                'not_eligible': int,
                'professionisti': [ids],
            }
        """
        week_start, week_end = cls.get_week_bounds(week_start)

        # OTTIMIZZAZIONE: Query clienti con almeno un servizio attivo
        # Non filtriamo più su stato_cliente globale, ma su stati servizio specifici
        query = db.session.query(Cliente).filter(
            or_(
                Cliente.stato_nutrizione.in_(cls.STATI_ELEGGIBILI),
                Cliente.stato_coach.in_(cls.STATI_ELEGGIBILI),
                Cliente.stato_psicologia.in_(cls.STATI_ELEGGIBILI)
            )
        )

        if professionista_id:
            # Filtra per professionista: colonne singole O relazioni M2M
            # Subquery per M2M nutrizionisti
            nutrizionisti_select = db.session.query(cliente_nutrizionisti.c.cliente_id).filter(
                cliente_nutrizionisti.c.user_id == professionista_id
            ).statement
            # Subquery per M2M coaches
            coaches_select = db.session.query(cliente_coaches.c.cliente_id).filter(
                cliente_coaches.c.user_id == professionista_id
            ).statement
            # Subquery per M2M psicologi
            psicologi_select = db.session.query(cliente_psicologi.c.cliente_id).filter(
                cliente_psicologi.c.user_id == professionista_id
            ).statement

            query = query.filter(
                or_(
                    # Colonne singole
                    Cliente.nutrizionista_id == professionista_id,
                    Cliente.coach_id == professionista_id,
                    Cliente.psicologa_id == professionista_id,
                    # Relazioni M2M
                    Cliente.cliente_id.in_(nutrizionisti_select),
                    Cliente.cliente_id.in_(coaches_select),
                    Cliente.cliente_id.in_(psicologi_select)
                )
            )

        all_clients = query.all()

        # OTTIMIZZAZIONE: Pre-carica eleggibilità esistenti in un dict
        existing_elig_query = db.session.query(EleggibilitaSettimanale).filter_by(
            week_start_date=week_start
        )
        if professionista_id:
            existing_elig_query = existing_elig_query.filter_by(
                professionista_id=professionista_id
            )

        existing_elig_dict = {}
        for elig in existing_elig_query.all():
            key = (elig.cliente_id, elig.professionista_id)
            existing_elig_dict[key] = elig

        # OTTIMIZZAZIONE: Costruisci mappa cliente -> [professionisti]
        cliente_prof_map = {}
        professionisti_set = set()

        for cliente in all_clients:
            profs = []

            # Colonne singole
            if cliente.nutrizionista_id:
                profs.append(cliente.nutrizionista_id)
                professionisti_set.add(cliente.nutrizionista_id)
            if cliente.coach_id:
                profs.append(cliente.coach_id)
                professionisti_set.add(cliente.coach_id)
            if cliente.psicologa_id:
                profs.append(cliente.psicologa_id)
                professionisti_set.add(cliente.psicologa_id)

            # Relazioni M2M (nutrizionisti_multipli, coaches_multipli, psicologi_multipli)
            for nutrizionista in cliente.nutrizionisti_multipli:
                if nutrizionista.id not in profs:
                    profs.append(nutrizionista.id)
                professionisti_set.add(nutrizionista.id)

            for coach in cliente.coaches_multipli:
                if coach.id not in profs:
                    profs.append(coach.id)
                professionisti_set.add(coach.id)

            for psicologo in cliente.psicologi_multipli:
                if psicologo.id not in profs:
                    profs.append(psicologo.id)
                professionisti_set.add(psicologo.id)

            if profs:
                cliente_prof_map[cliente.cliente_id] = (cliente, profs)

        professionisti_ids = list(professionisti_set)
        if professionista_id:
            professionisti_ids = [professionista_id]

        # OTTIMIZZAZIONE: Pre-carica tutti i professionisti in un dict
        professionisti_dict = {}
        if professionisti_ids:
            users = db.session.query(User).filter(User.id.in_(professionisti_ids)).all()
            professionisti_dict = {u.id: u for u in users}

        total_processed = 0
        eligible_count = 0
        not_eligible_count = 0
        to_add = []

        # OTTIMIZZAZIONE: Loop singolo su coppie cliente-professionista
        for cliente_id, (cliente, prof_ids) in cliente_prof_map.items():
            for prof_id in prof_ids:
                # Filtra se richiesto professionista specifico
                if professionista_id and prof_id != professionista_id:
                    continue

                # Ottieni professionista dal dict pre-caricato
                prof = professionisti_dict.get(prof_id)

                # Verifica eleggibilità (passa professionista per evitare query extra)
                is_eligible, motivo = cls.is_cliente_eligible(
                    cliente, prof_id, week_start, professionista=prof
                )

                giorni_attivo = (
                    (week_start - cliente.data_inizio_abbonamento).days
                    if cliente.data_inizio_abbonamento else None
                )

                # Check se esiste già
                key = (cliente_id, prof_id)
                existing = existing_elig_dict.get(key)

                if existing:
                    # Aggiorna esistente
                    existing.eleggibile = is_eligible
                    existing.motivo_non_eleggibile = motivo
                    existing.stato_cliente_snapshot = cliente.stato_cliente
                    existing.check_day_snapshot = cliente.check_day
                    existing.giorni_attivo_snapshot = giorni_attivo
                else:
                    # Prepara nuovo record (bulk insert dopo)
                    elig = EleggibilitaSettimanale(
                        cliente_id=cliente_id,
                        professionista_id=prof_id,
                        week_start_date=week_start,
                        eleggibile=is_eligible,
                        motivo_non_eleggibile=motivo,
                        check_effettuato=False,
                        stato_cliente_snapshot=cliente.stato_cliente,
                        check_day_snapshot=cliente.check_day,
                        giorni_attivo_snapshot=giorni_attivo
                    )
                    to_add.append(elig)

                total_processed += 1
                if is_eligible:
                    eligible_count += 1
                else:
                    not_eligible_count += 1

        # OTTIMIZZAZIONE: Bulk insert nuovi record
        if to_add:
            db.session.bulk_save_objects(to_add)

        db.session.commit()

        return {
            'total_processed': total_processed,
            'eligible': eligible_count,
            'not_eligible': not_eligible_count,
            'professionisti': professionisti_ids,
            'week_start': week_start,
            'week_end': week_end,
        }

    @staticmethod
    def get_eligible_clients_for_prof(
        professionista_id: int,
        week_start: date
    ) -> List[EleggibilitaSettimanale]:
        """
        Recupera clienti eleggibili per un professionista in una settimana.

        Args:
            professionista_id: ID professionista
            week_start: Data inizio settimana

        Returns:
            Lista di EleggibilitaSettimanale eleggibili
        """
        return db.session.query(EleggibilitaSettimanale).filter_by(
            professionista_id=professionista_id,
            week_start_date=week_start,
            eleggibile=True
        ).all()

    @staticmethod
    def mark_check_done(
        cliente_id: int,
        professionista_id: int,
        week_start: date
    ) -> bool:
        """
        Segna check come effettuato per un cliente.

        Args:
            cliente_id: ID cliente
            professionista_id: ID professionista
            week_start: Data inizio settimana

        Returns:
            True se aggiornato, False se non trovato
        """
        elig = db.session.query(EleggibilitaSettimanale).filter_by(
            cliente_id=cliente_id,
            professionista_id=professionista_id,
            week_start_date=week_start
        ).first()

        if elig:
            elig.check_effettuato = True
            db.session.commit()
            return True

        return False

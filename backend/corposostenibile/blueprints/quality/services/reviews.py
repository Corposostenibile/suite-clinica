"""
ReviewService - Servizio per gestione recensioni Trustpilot e distribuzione bonus BRec.

Logica bonus:
- Richiedente: +0.03
- Altri membri team: +0.02 / (n-1) ciascuno
- Bonus applicato UNA SOLA VOLTA per cliente (lifetime)
"""
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_
from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    User,
    TrustpilotReview,
)


class ReviewService:
    """Servizio per gestione recensioni e calcolo bonus BRec."""

    BONUS_RICHIEDENTE = 0.03  # +0.03 per chi richiede
    BONUS_TEAM_TOTAL = 0.02   # +0.02 totale diviso tra resto team

    @staticmethod
    def get_quarter_string(target_date: Optional[date] = None) -> str:
        """
        Calcola stringa trimestre "YYYY-QX" per una data.

        Args:
            target_date: Data di riferimento (default: oggi)

        Returns:
            Stringa formato "2025-Q4"
        """
        if target_date is None:
            target_date = date.today()

        quarter = (target_date.month - 1) // 3 + 1
        return f"{target_date.year}-Q{quarter}"

    @staticmethod
    def get_client_team(cliente: Cliente) -> List[int]:
        """
        Ottiene lista ID professionisti del team cliente.

        Args:
            cliente: Istanza Cliente

        Returns:
            Lista di user_id dei professionisti assegnati
        """
        team = []
        if cliente.nutrizionista_id:
            team.append(cliente.nutrizionista_id)
        if cliente.coach_id:
            team.append(cliente.coach_id)
        if cliente.psicologa_id:
            team.append(cliente.psicologa_id)
        return team

    @classmethod
    def calculate_brec_distribution(
        cls,
        richiedente_id: int,
        team_ids: List[int]
    ) -> Dict[str, any]:
        """
        Calcola distribuzione bonus BRec per una recensione.

        Args:
            richiedente_id: ID professionista che ha richiesto recensione
            team_ids: Lista ID di tutti i professionisti del team

        Returns:
            Dict {
                'richiedente_id': int,
                'richiedente_bonus': float,
                'team_ids': [int],
                'team_bonus_total': float,
                'team_bonus_each': float,
                'team_count': int
            }
        """
        # Rimuovi richiedente dalla lista team se presente
        altri_team = [tid for tid in team_ids if tid != richiedente_id]
        n_altri = len(altri_team)

        # Calcola bonus per altri membri
        bonus_each = cls.BONUS_TEAM_TOTAL / n_altri if n_altri > 0 else 0.0

        return {
            'richiedente_id': richiedente_id,
            'richiedente_bonus': cls.BONUS_RICHIEDENTE,
            'team_ids': altri_team,
            'team_bonus_total': cls.BONUS_TEAM_TOTAL,
            'team_bonus_each': round(bonus_each, 4),
            'team_count': n_altri
        }

    @classmethod
    def create_review_record(
        cls,
        cliente_id: int,
        richiesta_da_professionista_id: int,
        data_richiesta: datetime,
        pubblicata: bool = False,
        stelle: Optional[int] = None,
        testo_recensione: Optional[str] = None,
        data_pubblicazione: Optional[datetime] = None,
        applied_to_quarter: Optional[str] = None,
        applied_to_week_start: Optional[date] = None,
        confermata_da_hm_id: Optional[int] = None,
        note_interne: Optional[str] = None
    ) -> TrustpilotReview:
        """
        Crea record recensione Trustpilot con distribuzione bonus.

        Args:
            cliente_id: ID cliente
            richiesta_da_professionista_id: ID chi ha richiesto
            data_richiesta: Data richiesta recensione
            pubblicata: Se recensione pubblicata
            stelle: Rating 1-5
            testo_recensione: Testo recensione
            data_pubblicazione: Data pubblicazione
            applied_to_quarter: Trimestre applicazione (es. "2025-Q4")
            applied_to_week_start: Settimana specifica applicazione
            confermata_da_hm_id: ID Health Manager che conferma
            note_interne: Note interne

        Returns:
            TrustpilotReview creata
        """
        # Ottieni cliente e team
        cliente = db.session.get(Cliente, cliente_id)
        if not cliente:
            raise ValueError(f"Cliente {cliente_id} non trovato")

        team_ids = cls.get_client_team(cliente)

        # Calcola distribuzione bonus
        bonus_dist = cls.calculate_brec_distribution(
            richiesta_da_professionista_id,
            team_ids
        )

        # Se non specificato, usa trimestre corrente
        if applied_to_quarter is None:
            applied_to_quarter = cls.get_quarter_string()

        # Crea record
        review = TrustpilotReview(
            cliente_id=cliente_id,
            richiesta_da_professionista_id=richiesta_da_professionista_id,
            data_richiesta=data_richiesta,
            pubblicata=pubblicata,
            data_pubblicazione=data_pubblicazione,
            stelle=stelle,
            testo_recensione=testo_recensione,
            bonus_distribution=bonus_dist,
            applied_to_quarter=applied_to_quarter,
            applied_to_week_start=applied_to_week_start,
            confermata_da_hm_id=confermata_da_hm_id,
            data_conferma_hm=datetime.utcnow() if confermata_da_hm_id else None,
            note_interne=note_interne
        )

        db.session.add(review)
        db.session.commit()

        return review

    @staticmethod
    def confirm_review_published(
        review_id: int,
        stelle: int,
        testo_recensione: str,
        data_pubblicazione: datetime,
        applied_to_week_start: date,
        confermata_da_hm_id: int
    ) -> TrustpilotReview:
        """
        Conferma pubblicazione recensione (azione da Health Manager).

        Args:
            review_id: ID recensione
            stelle: Rating 1-5
            testo_recensione: Testo recensione
            data_pubblicazione: Data pubblicazione
            applied_to_week_start: Settimana di applicazione bonus
            confermata_da_hm_id: ID Health Manager

        Returns:
            TrustpilotReview aggiornata
        """
        review = db.session.get(TrustpilotReview, review_id)
        if not review:
            raise ValueError(f"Review {review_id} non trovata")

        review.pubblicata = True
        review.stelle = stelle
        review.testo_recensione = testo_recensione
        review.data_pubblicazione = data_pubblicazione
        review.applied_to_week_start = applied_to_week_start
        review.confermata_da_hm_id = confermata_da_hm_id
        review.data_conferma_hm = datetime.utcnow()

        # Aggiorna anche Cliente
        cliente = db.session.get(Cliente, review.cliente_id)
        if cliente:
            cliente.ultima_recensione_trustpilot_data = data_pubblicazione
            cliente.recensioni_lifetime_count = (cliente.recensioni_lifetime_count or 0) + 1

        db.session.commit()

        return review

    @staticmethod
    def get_brec_for_professional(
        professionista_id: int,
        week_start: date
    ) -> float:
        """
        Calcola bonus BRec totale per un professionista in una settimana.

        Args:
            professionista_id: ID professionista
            week_start: Data inizio settimana

        Returns:
            Bonus BRec totale (somma di tutti i bonus della settimana)
        """
        # Recensioni pubblicate nella settimana
        reviews = db.session.query(TrustpilotReview).filter(
            TrustpilotReview.pubblicata == True,
            TrustpilotReview.applied_to_week_start == week_start
        ).all()

        total_brec = 0.0

        for review in reviews:
            dist = review.bonus_distribution or {}

            # Check se richiedente
            if dist.get('richiedente_id') == professionista_id:
                total_brec += dist.get('richiedente_bonus', 0.0)

            # Check se in team
            if professionista_id in dist.get('team_ids', []):
                total_brec += dist.get('team_bonus_each', 0.0)

        return round(total_brec, 4)

    @staticmethod
    def get_brec_for_professionals(
        professionista_ids: List[int],
        week_start: date
    ) -> Dict[int, float]:
        """
        Calcola il bonus BRec per più professionisti in una sola passata.

        Args:
            professionista_ids: Lista ID professionisti
            week_start: Data inizio settimana

        Returns:
            Dict {professionista_id: bonus_brec}
        """
        if not professionista_ids:
            return {}

        target_ids = set(professionista_ids)
        totals = {pid: 0.0 for pid in target_ids}

        reviews = db.session.query(TrustpilotReview).filter(
            TrustpilotReview.pubblicata == True,
            TrustpilotReview.applied_to_week_start == week_start
        ).all()

        for review in reviews:
            dist = review.bonus_distribution or {}
            richiedente_id = dist.get('richiedente_id')
            if richiedente_id in target_ids:
                totals[richiedente_id] += dist.get('richiedente_bonus', 0.0)

            team_ids = dist.get('team_ids', []) or []
            team_bonus_each = dist.get('team_bonus_each', 0.0)
            if team_bonus_each:
                for pid in team_ids:
                    if pid in target_ids:
                        totals[pid] += team_bonus_each

        return {pid: round(value, 4) for pid, value in totals.items()}

    @staticmethod
    def get_reviews_for_quarter(
        quarter_string: str,
        professionista_id: Optional[int] = None
    ) -> List[TrustpilotReview]:
        """
        Recupera recensioni pubblicate in un trimestre.

        Args:
            quarter_string: Trimestre (es. "2025-Q4")
            professionista_id: Filtra per professionista (opzionale)

        Returns:
            Lista TrustpilotReview
        """
        query = db.session.query(TrustpilotReview).filter(
            TrustpilotReview.pubblicata == True,
            TrustpilotReview.applied_to_quarter == quarter_string
        )

        if professionista_id:
            # Filtra recensioni dove professionista è coinvolto
            # (richiedente O nel team)
            reviews = query.all()
            filtered = []
            for r in reviews:
                dist = r.bonus_distribution or {}
                if (dist.get('richiedente_id') == professionista_id or
                    professionista_id in dist.get('team_ids', [])):
                    filtered.append(r)
            return filtered

        return query.all()

    @staticmethod
    def has_client_already_reviewed(cliente_id: int) -> bool:
        """
        Verifica se cliente ha già recensione pubblicata (lifetime).

        Args:
            cliente_id: ID cliente

        Returns:
            True se ha già recensito
        """
        count = db.session.query(TrustpilotReview).filter(
            TrustpilotReview.cliente_id == cliente_id,
            TrustpilotReview.pubblicata == True
        ).count()

        return count > 0

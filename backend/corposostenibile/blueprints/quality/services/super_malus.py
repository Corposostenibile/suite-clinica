"""
SuperMalusService - Calcolo Super Malus trimestrale per professionisti.

Il Super Malus si applica al bonus trimestrale quando:
- Cliente ha review negativa (stelle <= 2) O rimborso nel trimestre
- Professionista era assegnato al cliente

Penalità:
- Primario: -50% (solo review/rimborso), -100% (entrambi)
- Secondario: -25% (solo review/rimborso), -50% (entrambi)
- Psicologo: sempre considerato primario
"""
from datetime import date
from typing import List, Dict, Optional, Tuple
import json
from sqlalchemy import and_, or_
from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    User,
    TrustpilotReview,
    PaymentTransaction,
    TransactionTypeEnum,
    FiguraRifEnum,
)


class SuperMalusService:
    """Servizio per calcolo Super Malus trimestrale."""

    # Soglia stelle per review negativa
    NEGATIVE_REVIEW_THRESHOLD = 2

    # Penalità base per ruolo
    MALUS_PRIMARY_SINGLE = 50.0      # -50% per primario con review OR rimborso
    MALUS_PRIMARY_BOTH = 100.0       # -100% per primario con review AND rimborso
    MALUS_SECONDARY_SINGLE = 25.0    # -25% per secondario con review OR rimborso
    MALUS_SECONDARY_BOTH = 50.0      # -50% per secondario con review AND rimborso

    @staticmethod
    def get_quarter_dates(quarter_string: str) -> Tuple[date, date]:
        """
        Converte stringa trimestre in date inizio/fine.

        Args:
            quarter_string: "2025-Q4"

        Returns:
            (start_date, end_date)
        """
        year, q = quarter_string.split("-Q")
        year = int(year)
        quarter = int(q)

        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2

        start_date = date(year, start_month, 1)

        # Fine trimestre
        if end_month == 12:
            end_date = date(year, 12, 31)
        else:
            import calendar
            _, last_day = calendar.monthrange(year, end_month)
            end_date = date(year, end_month, last_day)

        return start_date, end_date

    @staticmethod
    def get_quarter_string(target_date: Optional[date] = None) -> str:
        """Calcola stringa trimestre per una data."""
        if target_date is None:
            target_date = date.today()
        quarter = (target_date.month - 1) // 3 + 1
        return f"{target_date.year}-Q{quarter}"

    @classmethod
    def is_primary_professional(
        cls,
        professionista: User,
        cliente: Cliente
    ) -> bool:
        """
        Determina se professionista è primario per il cliente.

        Regole:
        - Psicologo è SEMPRE primario
        - Altrimenti, primario se corrisponde a figura_di_riferimento

        Args:
            professionista: User professionista
            cliente: Cliente

        Returns:
            True se professionista è primario
        """
        # Psicologo sempre primario
        if professionista.specialty and 'psic' in professionista.specialty.value.lower():
            return True

        # Controlla figura di riferimento
        if not cliente.figura_di_riferimento:
            # Se non specificata, considera primario chi è assegnato
            return True

        figura = cliente.figura_di_riferimento.value.lower()
        specialty = professionista.specialty.value.lower() if professionista.specialty else ""

        # Match figura di riferimento con specialty
        if figura == "nutrizionista" and "nutri" in specialty:
            return True
        if figura == "coach" and "coach" in specialty:
            return True
        if figura == "psicologa" and "psic" in specialty:
            return True

        return False

    @classmethod
    def get_client_professionals(cls, cliente: Cliente) -> List[int]:
        """
        Recupera lista ID professionisti assegnati a un cliente.

        Args:
            cliente: Istanza Cliente

        Returns:
            Lista di user_id
        """
        prof_ids = []
        if cliente.nutrizionista_id:
            prof_ids.append(cliente.nutrizionista_id)
        if cliente.coach_id:
            prof_ids.append(cliente.coach_id)
        if cliente.psicologa_id:
            prof_ids.append(cliente.psicologa_id)
        return prof_ids

    @classmethod
    def get_clients_with_negative_reviews(
        cls,
        professionista_id: int,
        quarter: str
    ) -> List[Dict]:
        """
        Query clienti con review negative nel trimestre dove professionista era assegnato.

        Args:
            professionista_id: ID professionista
            quarter: Trimestre (es. "2025-Q4")

        Returns:
            Lista di dict con info cliente e review
        """
        start_date, end_date = cls.get_quarter_dates(quarter)

        # Trova review negative nel trimestre
        reviews = db.session.query(TrustpilotReview).filter(
            TrustpilotReview.pubblicata == True,
            TrustpilotReview.stelle <= cls.NEGATIVE_REVIEW_THRESHOLD,
            TrustpilotReview.applied_to_quarter == quarter
        ).all()

        results = []
        for review in reviews:
            cliente = review.cliente
            if not cliente:
                continue

            # Verifica se il professionista era assegnato al cliente
            prof_ids = cls.get_client_professionals(cliente)
            if professionista_id not in prof_ids:
                continue

            results.append({
                'cliente_id': review.cliente_id,
                'cliente_nome': getattr(cliente, 'nome_cognome', 'N/A'),
                'review_id': review.id,
                'stelle': review.stelle,
                'data_pubblicazione': review.data_pubblicazione.isoformat() if review.data_pubblicazione else None
            })

        return results

    @classmethod
    def get_clients_with_refunds(
        cls,
        professionista_id: int,
        quarter: str
    ) -> List[Dict]:
        """
        Query clienti con rimborsi nel trimestre dove professionista era assegnato.

        Args:
            professionista_id: ID professionista
            quarter: Trimestre (es. "2025-Q4")

        Returns:
            Lista di dict con info cliente e rimborso
        """
        start_date, end_date = cls.get_quarter_dates(quarter)

        # Trova transazioni di rimborso nel trimestre
        refunds = db.session.query(PaymentTransaction).filter(
            PaymentTransaction.transaction_type == TransactionTypeEnum.rimborso,
            PaymentTransaction.payment_date >= start_date,
            PaymentTransaction.payment_date <= end_date
        ).all()

        results = []
        for refund in refunds:
            cliente_id = refund.cliente_id
            cliente = db.session.get(Cliente, cliente_id)
            if not cliente:
                continue

            # Verifica se il professionista era assegnato al cliente
            prof_ids = cls.get_client_professionals(cliente)
            if professionista_id not in prof_ids:
                continue

            results.append({
                'cliente_id': cliente_id,
                'cliente_nome': getattr(cliente, 'nome_cognome', 'N/A'),
                'payment_id': refund.payment_id,
                'amount': float(refund.refund_amount or refund.amount or 0),
                'payment_date': refund.payment_date.isoformat() if refund.payment_date else None
            })

        return results

    @classmethod
    def calculate_super_malus(
        cls,
        professionista_id: int,
        quarter: str
    ) -> Dict:
        """
        Calcola Super Malus per professionista nel trimestre.

        Args:
            professionista_id: ID professionista
            quarter: Trimestre (es. "2025-Q4")

        Returns:
            Dict con:
                - has_negative_review: bool
                - has_refund: bool
                - malus_percentage: float (0, 25, 50, 100)
                - is_primary: bool (True se primario per almeno un cliente con malus)
                - reason: str (motivo malus)
                - affected_clients: List[dict]
        """
        professionista = db.session.get(User, professionista_id)
        if not professionista:
            return {
                'has_negative_review': False,
                'has_refund': False,
                'malus_percentage': 0.0,
                'is_primary': False,
                'reason': 'Professionista non trovato',
                'affected_clients': []
            }

        # Recupera clienti con problemi
        clients_negative_reviews = cls.get_clients_with_negative_reviews(professionista_id, quarter)
        clients_refunds = cls.get_clients_with_refunds(professionista_id, quarter)

        has_negative_review = len(clients_negative_reviews) > 0
        has_refund = len(clients_refunds) > 0

        if not has_negative_review and not has_refund:
            return {
                'has_negative_review': False,
                'has_refund': False,
                'malus_percentage': 0.0,
                'is_primary': False,
                'reason': None,
                'affected_clients': []
            }

        # Determina se è primario per i clienti con problemi
        affected_client_ids = set()
        for c in clients_negative_reviews:
            affected_client_ids.add(c['cliente_id'])
        for c in clients_refunds:
            affected_client_ids.add(c['cliente_id'])

        is_primary = False
        for cliente_id in affected_client_ids:
            cliente = db.session.get(Cliente, cliente_id)
            if cliente and cls.is_primary_professional(professionista, cliente):
                is_primary = True
                break

        # Calcola penalità
        has_both = has_negative_review and has_refund

        if is_primary:
            malus_percentage = cls.MALUS_PRIMARY_BOTH if has_both else cls.MALUS_PRIMARY_SINGLE
        else:
            malus_percentage = cls.MALUS_SECONDARY_BOTH if has_both else cls.MALUS_SECONDARY_SINGLE

        # Costruisci motivo
        reasons = []
        if has_negative_review:
            reasons.append(f"{len(clients_negative_reviews)} review negative")
        if has_refund:
            reasons.append(f"{len(clients_refunds)} rimborsi")

        role_str = "primario" if is_primary else "secondario"
        reason = f"Professionista {role_str}: {', '.join(reasons)}"

        # Combina clienti affected
        affected_clients = []
        for c in clients_negative_reviews:
            c['type'] = 'review_negativa'
            affected_clients.append(c)
        for c in clients_refunds:
            c['type'] = 'rimborso'
            affected_clients.append(c)

        return {
            'has_negative_review': has_negative_review,
            'has_refund': has_refund,
            'malus_percentage': malus_percentage,
            'is_primary': is_primary,
            'reason': reason,
            'affected_clients': affected_clients
        }

    @classmethod
    def apply_super_malus_to_score(
        cls,
        score,  # QualityWeeklyScore instance
        quarter: str
    ) -> None:
        """
        Calcola e applica Super Malus a un QualityWeeklyScore.

        Aggiorna i campi:
        - has_negative_review
        - has_refund
        - is_primary_for_malus
        - super_malus_percentage
        - super_malus_applied
        - super_malus_reason
        - final_bonus_after_malus

        Args:
            score: QualityWeeklyScore instance
            quarter: Trimestre
        """
        malus_data = cls.calculate_super_malus(score.professionista_id, quarter)

        score.has_negative_review = malus_data['has_negative_review']
        score.has_refund = malus_data['has_refund']
        score.is_primary_for_malus = malus_data['is_primary']
        score.super_malus_percentage = malus_data['malus_percentage']
        score.super_malus_applied = malus_data['malus_percentage'] > 0
        score.super_malus_reason = json.dumps(malus_data['affected_clients']) if malus_data['affected_clients'] else None

        # Calcola bonus dopo malus
        if score.final_bonus_percentage is not None and score.super_malus_percentage > 0:
            reduction = score.final_bonus_percentage * (score.super_malus_percentage / 100)
            score.final_bonus_after_malus = max(0, score.final_bonus_percentage - reduction)
        else:
            score.final_bonus_after_malus = score.final_bonus_percentage

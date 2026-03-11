"""
customers.repository
====================

Layer di *data-access* **solo lettura** per il dominio *customers*.

- Query riutilizzabili e testabili in isolamento                                  
- Nessuna side-effect né logica di validazione—soltanto SQLAlchemy ORM            
- Include helper KPI / analytics, query su *payments* / *renewals* **e** cronologia versione
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

from sqlalchemy import func, select, and_
from sqlalchemy.orm import Query, joinedload, subqueryload, selectinload
from sqlalchemy_continuum import version_class
from werkzeug.exceptions import NotFound

from corposostenibile.extensions import db
from corposostenibile.models import (
    #  — clienti & relazioni principali —
    Cliente,
    #  — pagamenti / rinnovi —
    PaymentTransaction,
    SubscriptionContract,
    SubscriptionRenewal,
    TransactionTypeEnum,
    # — enum professionisti —
    NutrizionistaEnum,
    CoachEnum,
    PsicologaEnum,
)

from .filters import apply_customer_filters

__all__ = ["CustomerRepository", "customers_repo"]


# --------------------------------------------------------------------------- #
#  Eager-loading default (COMMENTATE LE RELAZIONI NON DISPONIBILI)            #
# --------------------------------------------------------------------------- #

_DEFAULT_EAGER_LOAD = (
    subqueryload(Cliente.cartelle),
    # Professionisti per colonna Team nella lista
    selectinload(Cliente.nutrizionisti_multipli),
    selectinload(Cliente.coaches_multipli),
    selectinload(Cliente.psicologi_multipli),
    selectinload(Cliente.health_manager_user),
    # Piani attivi per colonne "Piano Dieta" / "Piano Allenamento" nelle visuali
    selectinload(Cliente.meal_plans),
    selectinload(Cliente.training_plans),
)


def _is_cco_user(user) -> bool:
    specialty = getattr(user, "specialty", None)
    if hasattr(specialty, "value"):
        specialty = specialty.value
    return str(specialty).strip().lower() == "cco" if specialty else False

# --------------------------------------------------------------------------- #
#  Repository                                                                 #
# --------------------------------------------------------------------------- #


class CustomerRepository:
    """Wrapper intorno al modello :class:`Cliente` con utility di lettura."""

    def __init__(self, session: db.scoped_session | None = None) -> None:
        self.session = session or db.session

    # -------------------- query builders ---------------------------------- #

    def _base_query(self, *, eager: bool = False) -> Query:
        qry = self.session.query(Cliente)
        if eager:
            for opt in _DEFAULT_EAGER_LOAD:
                qry = qry.options(opt)
        return qry

    # -------------------- CRUD helpers ------------------------------------ #

    def get_one(self, cliente_id: int, *, eager: bool = True) -> Cliente:
        cliente = (
            self._base_query(eager=eager)
            .filter(Cliente.cliente_id == cliente_id)
            .one_or_none()
        )
        if not cliente:
            raise NotFound(f"Cliente {cliente_id} non trovato.")
        return cliente

    def list(
        self,
        *,
        filters: Mapping[str, Any] | None = None,
        order_by: str | None = "-created_at",
        page: int = 1,
        per_page: int = 25,
        eager: bool = False,
    ):
        """Ritorna una `Pagination` pronta per template/API."""
        from sqlalchemy import case, or_, exists, select
        from corposostenibile.models import (
            TipologiaClienteEnum, UserRoleEnum,
            cliente_nutrizionisti, cliente_coaches, cliente_psicologi, cliente_consulenti,
            CallBonus, CallBonusStatusEnum,
            ClienteProfessionistaHistory,
        )
        from flask_login import current_user

        qry: Query = self._base_query(eager=eager)
        qry = qry.filter(Cliente.show_in_clienti_lista.is_(True))
        if filters:
            qry = apply_customer_filters(qry, filters)  # type: ignore[arg-type]

        # Applica filtro per trial users
        if current_user.is_authenticated and current_user.is_trial:
            if current_user.trial_stage < 2:
                # Stage 1: nessun cliente visibile
                qry = qry.filter(False)  # Query vuota
            elif current_user.trial_stage == 2:
                # Stage 2: solo clienti assegnati
                assigned_ids = [c.cliente_id for c in current_user.trial_assigned_clients]
                if assigned_ids:
                    qry = qry.filter(Cliente.cliente_id.in_(assigned_ids))
                else:
                    qry = qry.filter(False)  # Nessun cliente assegnato
        
        # -------------------------------------------------------------------
        # FILTRO PER RUOLO (Admin, Team Leader, Professionista)
        # -------------------------------------------------------------------
        if current_user.is_authenticated and not current_user.is_trial:
            user_role = getattr(current_user, 'role', None)
            
            # Admin/CCO: vede tutto (nessun filtro)
            if user_role == UserRoleEnum.admin or current_user.is_admin or _is_cco_user(current_user):
                pass  # Nessun filtro aggiuntivo
            # Health Manager: solo clienti assegnati a sé
            elif user_role == UserRoleEnum.health_manager:
                qry = qry.filter(Cliente.health_manager_id == current_user.id)
            
            # Influencer: già gestito in routes.py
            elif user_role == UserRoleEnum.influencer:
                pass  # Già filtrato dalle routes
            
            # Team Leader: vede i pazienti assegnati ai membri del suo team
            elif user_role == UserRoleEnum.team_leader:
                # Raccoglie tutti i member_ids dei team guidati + il team leader stesso
                team_member_ids = set()
                team_member_ids.add(current_user.id)  # Il TL deve vedere anche i propri pazienti
                for team in (current_user.teams_led or []):
                    for member in (team.members or []):
                        team_member_ids.add(member.id)
                
                if team_member_ids:
                    # Filtra i pazienti che hanno almeno un professionista del team assegnato (FK singola o M2M)
                    member_ids_list = list(team_member_ids)
                    qry = qry.filter(
                        or_(
                            # Assegnazione tramite FK singola
                            Cliente.nutrizionista_id.in_(member_ids_list),
                            Cliente.coach_id.in_(member_ids_list),
                            Cliente.psicologa_id.in_(member_ids_list),
                            Cliente.consulente_alimentare_id.in_(member_ids_list),
                            # Assegnato a nutrizionista del team (M2M)
                            exists(
                                select(cliente_nutrizionisti.c.cliente_id)
                                .where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id)
                                .where(cliente_nutrizionisti.c.user_id.in_(member_ids_list))
                            ),
                            # Assegnato a coach del team (M2M)
                            exists(
                                select(cliente_coaches.c.cliente_id)
                                .where(cliente_coaches.c.cliente_id == Cliente.cliente_id)
                                .where(cliente_coaches.c.user_id.in_(member_ids_list))
                            ),
                            # Assegnato a psicologo del team (M2M)
                            exists(
                                select(cliente_psicologi.c.cliente_id)
                                .where(cliente_psicologi.c.cliente_id == Cliente.cliente_id)
                                .where(cliente_psicologi.c.user_id.in_(member_ids_list))
                            ),
                            # Assegnato a consulente del team (M2M)
                            exists(
                                select(cliente_consulenti.c.cliente_id)
                                .where(cliente_consulenti.c.cliente_id == Cliente.cliente_id)
                                .where(cliente_consulenti.c.user_id.in_(member_ids_list))
                            ),
                            # Assegnazione tramite history (es. Medico nel team)
                            exists(
                                select(ClienteProfessionistaHistory.cliente_id).where(
                                    ClienteProfessionistaHistory.cliente_id == Cliente.cliente_id,
                                    ClienteProfessionistaHistory.user_id.in_(member_ids_list),
                                    ClienteProfessionistaHistory.is_active.is_(True),
                                )
                            ),
                        )
                    )
                else:
                    # Team Leader senza membri: nessun paziente visibile
                    qry = qry.filter(False)
            
            # Professionista o altro: vede solo i propri pazienti (FK singola o M2M)
            elif user_role == UserRoleEnum.professionista:
                user_id = current_user.id
                qry = qry.filter(
                    or_(
                        # Assegnazione tramite FK singola
                        Cliente.nutrizionista_id == user_id,
                        Cliente.coach_id == user_id,
                        Cliente.psicologa_id == user_id,
                        Cliente.consulente_alimentare_id == user_id,
                        # Pazienti assegnati come nutrizionista (M2M)
                        exists(
                            select(cliente_nutrizionisti.c.cliente_id)
                            .where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id)
                            .where(cliente_nutrizionisti.c.user_id == user_id)
                        ),
                        # Pazienti assegnati come coach (M2M)
                        exists(
                            select(cliente_coaches.c.cliente_id)
                            .where(cliente_coaches.c.cliente_id == Cliente.cliente_id)
                            .where(cliente_coaches.c.user_id == user_id)
                        ),
                        # Pazienti assegnati come psicologo (M2M)
                        exists(
                            select(cliente_psicologi.c.cliente_id)
                            .where(cliente_psicologi.c.cliente_id == Cliente.cliente_id)
                            .where(cliente_psicologi.c.user_id == user_id)
                        ),
                        # Pazienti assegnati come consulente (M2M)
                        exists(
                            select(cliente_consulenti.c.cliente_id)
                            .where(cliente_consulenti.c.cliente_id == Cliente.cliente_id)
                            .where(cliente_consulenti.c.user_id == user_id)
                        ),
                        # Pazienti con call bonus accettata assegnata a questo professionista
                        exists(
                            select(CallBonus.cliente_id).where(
                                CallBonus.cliente_id == Cliente.cliente_id,
                                CallBonus.professionista_id == user_id,
                                CallBonus.status == CallBonusStatusEnum.accettata,
                            )
                        ),
                        # Assegnazione tramite ClienteProfessionistaHistory (es. Medico)
                        exists(
                            select(ClienteProfessionistaHistory.cliente_id).where(
                                ClienteProfessionistaHistory.cliente_id == Cliente.cliente_id,
                                ClienteProfessionistaHistory.user_id == user_id,
                                ClienteProfessionistaHistory.is_active.is_(True),
                            )
                        ),
                    )
                )
            # health_manager: gestito sopra con admin/CCO (vede tutti i clienti)
        
        # SEMPRE applica l'ordinamento prioritario per tipologia
        # Ordina prima per tipologia (C, B, A hanno priorità), poi per nome
        priority_order = case(
            (Cliente.tipologia_cliente == TipologiaClienteEnum.c, 1),
            (Cliente.tipologia_cliente == TipologiaClienteEnum.b, 2),
            (Cliente.tipologia_cliente == TipologiaClienteEnum.a, 3),
            else_=4
        )
        
        # Applica sempre l'ordinamento per tipologia e poi per nome
        # Ignora il parametro order_by per ora
        qry = qry.order_by(priority_order, Cliente.nome_cognome)
        
        return qry.paginate(page=page, per_page=per_page, error_out=False)


    # --------------------------------------------------------------------- #
    #  History helper                                                       #
    # --------------------------------------------------------------------- #

    def history_for_cliente(
        self,
        cliente_id: int,
        *,
        limit: int | None = 20,
        order_desc: bool = True,
    ):
        """
        Restituisce la cronologia versione del cliente (SQLAlchemy-Continuum).

        :param cliente_id: ID cliente di cui recuperare gli eventi
        :param limit:     massimo numero di versioni da restituire (``None`` = tutte)
        :param order_desc:``True`` ⇒ versioni più recenti in alto
        """
        # 404 se il cliente non esista
        self.get_one(cliente_id, eager=False)

        ClienteVersion = version_class(Cliente)
        qry: Query = self.session.query(ClienteVersion).filter(
            ClienteVersion.cliente_id == cliente_id
        )

        qry = qry.order_by(
            ClienteVersion.transaction_id.desc()
            if order_desc
            else ClienteVersion.transaction_id.asc()
        )

        if limit:
            qry = qry.limit(limit)

        return qry.all()

    # --------------------------------------------------------------------- #
    #  payments / renewals helpers                                          #
    # --------------------------------------------------------------------- #

    def payments_for_cliente(
        self,
        cliente_id: int,
        *,
        order_by: str | Iterable[str] = "-payment_date",
    ) -> List[PaymentTransaction]:
        """Restituisce i :class:`PaymentTransaction` del cliente."""
        self.get_one(cliente_id, eager=False)
        qry: Query = (
            self.session.query(PaymentTransaction)
            .filter(PaymentTransaction.cliente_id == cliente_id)
            .filter(PaymentTransaction.amount.isnot(None))
        )
        if order_by:
            qry = qry.order_by(*self._parse_payment_order(order_by))
        return qry.all()

    def renewals_for_cliente(
        self,
        cliente_id: int,
        *,
        order_by: str | Iterable[str] = "-renewal_payment_date",
    ) -> List[SubscriptionRenewal]:
        """Restituisce i rinnovi di abbonamento per il cliente specificato."""
        self.get_one(cliente_id, eager=False)

        sub_ids = select(SubscriptionContract.subscription_id).filter(
            SubscriptionContract.cliente_id == cliente_id
        )
        qry: Query = self.session.query(SubscriptionRenewal).filter(
            SubscriptionRenewal.subscription_id.in_(sub_ids)
        )
        if order_by:
            qry = qry.order_by(*self._parse_renewal_order(order_by))
        return qry.all()

    # --------------------------------------------------------------------- #

    # --------------------------------------------------------------------- #
    #  KPI / analytics                                                      #
    # --------------------------------------------------------------------- #

    def kpi_counts(self, filters: Mapping[str, Any] | None = None) -> MutableMapping[str, int]:
        qry = self._base_query()
        if filters:
            qry = apply_customer_filters(qry, filters)  # type: ignore[arg-type]
        rows = (
            qry.with_entities(Cliente.stato_cliente, func.count(Cliente.cliente_id))
            .group_by(Cliente.stato_cliente)
            .all()
        )
        return {state.value if state else "unknown": total for state, total in rows}

    def ltv_summary(self, days: int = 90) -> MutableMapping[str, float]:
        # TEMPORANEAMENTE DISABILITATO - Cliente non ha più ltv/ltv_90_gg
        return {"ltv_totale": 0.0, f"ltv_{days}_giorni": 0.0}

    # --------------------------------------------------------------------- #
    #  use-cases specifici                                                  #
    # --------------------------------------------------------------------- #

    def find_duplicates_by_email(self, email: str) -> List[Cliente]:
        # PLACEHOLDER - ritorna lista vuota (campo email non più presente)
        return []

    def expiring_contracts(self, *, days: int = 30) -> List[Tuple[Cliente, date]]:
        # PLACEHOLDER - ritorna lista vuota (subscriptions disabilitate)
        return []

    def late_payments(self, *, grace_days: int = 7) -> List[PaymentTransaction]:
        # PLACEHOLDER - nessuna logica attiva
        return []


    # --------------------------------------------------------------------- #
    #  ordering helpers (shared)                                            #
    # --------------------------------------------------------------------- #

    @staticmethod
    def _parse_order(order_by: str | Iterable[str]) -> List[Any]:
        if isinstance(order_by, str):
            order_by = [s.strip() for s in order_by.split(",") if s.strip()]

        colmap = {
            "created_at": Cliente.created_at,
            "updated_at": Cliente.updated_at,
            "nome": Cliente.nome_cognome,
            "nome_cognome": Cliente.nome_cognome,
            "stato": Cliente.stato_cliente,
        }
        return CustomerRepository._build_ordering(order_by, colmap)

    @staticmethod
    def _parse_payment_order(order_by: str | Iterable[str]) -> List[Any]:
        if isinstance(order_by, str):
            order_by = [order_by]
        colmap = {
            "payment_date": PaymentTransaction.payment_date,
            "amount": PaymentTransaction.amount,
            "method": PaymentTransaction.payment_method,
            "type": PaymentTransaction.transaction_type,
        }
        return CustomerRepository._build_ordering(order_by, colmap)

    @staticmethod
    def _parse_renewal_order(order_by: str | Iterable[str]) -> List[Any]:
        if isinstance(order_by, str):
            order_by = [order_by]
        colmap = {
            "renewal_payment_date": SubscriptionRenewal.renewal_payment_date,
            "renewal_amount": SubscriptionRenewal.renewal_amount,
            "duration": SubscriptionRenewal.renewal_duration_days,
        }
        return CustomerRepository._build_ordering(order_by, colmap)

    # ---------- common builder ------------------------------------------- #

    @staticmethod
    def _build_ordering(keys: Sequence[str], colmap: Mapping[str, Any]) -> List[Any]:
        ordering: List[Any] = []
        for key in keys:
            desc = key.startswith("-")
            col_key = key[1:] if desc else key
            column = colmap.get(col_key)
            if column is None:
                continue
            ordering.append(column.desc() if desc else column.asc())
        if not ordering:
            # fallback: prima colonna del mapping in DESC se esiste
            default_col = next(iter(colmap.values()))
            ordering.append(default_col.desc())
        return ordering


# --------------------------------------------------------------------------- #
#  Singleton                                                                  #
# --------------------------------------------------------------------------- #

customers_repo = CustomerRepository()

"""RBAC helpers per lo scope clienti/professionisti.

Regola operativa attuale:
- per le specialità standard (nutrizione, coach, psicologia) la fonte di verità
  per la visibilità dei clienti è la relazione M2M;
- per il medico, la visibilità resta legata allo storico attivo
  (ClienteProfessionistaHistory);
- il fallback legacy è mantenuto solo per specialità non riconosciute, per non
  bloccare account storici o configurazioni non ancora normalizzate.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import exists, false, or_, select

from corposostenibile.models import (
    CallBonus,
    CallBonusStatusEnum,
    Cliente,
    ClienteProfessionistaHistory,
    TipoProfessionistaEnum,
    User,
)

SPECIALTY_TO_M2M_ATTR = {
    "nutrizione": "nutrizionisti_multipli",
    "coach": "coaches_multipli",
    "psicologia": "psicologi_multipli",
}

SERVICE_TO_SPECIALTY = {
    "nutrizione": "nutrizione",
    "coaching": "coach",
    "psicologia": "psicologia",
}


def _role_value(user: Any) -> str:
    role = getattr(user, "role", None)
    return role.value if hasattr(role, "value") else str(role or "")


def _user_id(user: Any) -> int | None:
    uid = getattr(user, "id", None)
    try:
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None


def normalize_specialty_group_for_rbac(user: Any) -> str | None:
    """Normalizza la specializzazione utente nel gruppo RBAC usato dal backend."""
    specialty = getattr(user, "specialty", None)
    specialty_value = specialty.value if hasattr(specialty, "value") else str(specialty or "")
    specialty_value = specialty_value.strip().lower()
    if specialty_value in ("nutrizionista", "nutrizione"):
        return "nutrizione"
    if specialty_value in ("psicologo", "psicologia", "psicologa"):
        return "psicologia"
    if specialty_value == "coach":
        return "coach"
    if specialty_value == "medico":
        return "medico"
    return None


def _call_bonus_clause(uid: int):
    return exists(
        select(CallBonus.id).where(
            CallBonus.cliente_id == Cliente.cliente_id,
            CallBonus.professionista_id == uid,
            CallBonus.status == CallBonusStatusEnum.accettata.value,
        )
    )


def _medical_history_clause(uid: int):
    return exists(
        select(ClienteProfessionistaHistory.id).where(
            ClienteProfessionistaHistory.cliente_id == Cliente.cliente_id,
            ClienteProfessionistaHistory.user_id == uid,
            ClienteProfessionistaHistory.tipo_professionista == TipoProfessionistaEnum.medico.value,
            ClienteProfessionistaHistory.is_active.is_(True),
        )
    )


def _legacy_professionista_clause(uid: int):
    return or_(
        Cliente.nutrizionista_id == uid,
        Cliente.coach_id == uid,
        Cliente.psicologa_id == uid,
        Cliente.consulente_alimentare_id == uid,
        Cliente.nutrizionisti_multipli.any(User.id == uid),
        Cliente.coaches_multipli.any(User.id == uid),
        Cliente.psicologi_multipli.any(User.id == uid),
        Cliente.consulenti_multipli.any(User.id == uid),
        exists(
            select(ClienteProfessionistaHistory.id).where(
                ClienteProfessionistaHistory.cliente_id == Cliente.cliente_id,
                ClienteProfessionistaHistory.user_id == uid,
                ClienteProfessionistaHistory.is_active.is_(True),
            )
        ),
    )


def professionista_visibility_clause(user: Any, *, include_call_bonus: bool = False):
    """Ritorna la clausola SQLAlchemy per la visibilità dei clienti.

    Per nutrizione / coach / psicologia usa solo la M2M della specialità.
    Per medico usa solo la history attiva di tipo medico.
    """
    uid = _user_id(user)
    if uid is None:
        return false()

    specialty_group = normalize_specialty_group_for_rbac(user)
    if specialty_group == "nutrizione":
        clause = Cliente.nutrizionisti_multipli.any(User.id == uid)
    elif specialty_group == "coach":
        clause = Cliente.coaches_multipli.any(User.id == uid)
    elif specialty_group == "psicologia":
        clause = Cliente.psicologi_multipli.any(User.id == uid)
    elif specialty_group == "medico":
        clause = _medical_history_clause(uid)
    else:
        clause = _legacy_professionista_clause(uid)

    if include_call_bonus:
        clause = or_(clause, _call_bonus_clause(uid))

    return clause


def is_professionista_assigned_to_cliente(
    user: Any,
    cliente: Any,
    *,
    include_call_bonus: bool = False,
) -> bool:
    """Verifica lato oggetto se il professionista è associato al cliente.

    La logica è allineata alla visibilità lista:
    - standard specialty -> solo M2M della specialità
    - medico -> history attiva di tipo medico
    """
    if getattr(user, "is_admin", False):
        return True

    if _role_value(user) != "professionista":
        return False

    uid = _user_id(user)
    if uid is None:
        return False

    specialty_group = normalize_specialty_group_for_rbac(user)
    if specialty_group == "nutrizione":
        assigned = user in (getattr(cliente, "nutrizionisti_multipli", None) or [])
    elif specialty_group == "coach":
        assigned = user in (getattr(cliente, "coaches_multipli", None) or [])
    elif specialty_group == "psicologia":
        assigned = user in (getattr(cliente, "psicologi_multipli", None) or [])
    elif specialty_group == "medico":
        assigned = bool(
            ClienteProfessionistaHistory.query.filter_by(
                cliente_id=cliente.cliente_id,
                user_id=uid,
                tipo_professionista=TipoProfessionistaEnum.medico.value,
                is_active=True,
            ).first()
        )
    else:
        assigned = (
            getattr(cliente, "nutrizionista_id", None) == uid
            or getattr(cliente, "coach_id", None) == uid
            or getattr(cliente, "psicologa_id", None) == uid
            or getattr(cliente, "consulente_alimentare_id", None) == uid
            or user in (getattr(cliente, "nutrizionisti_multipli", None) or [])
            or user in (getattr(cliente, "coaches_multipli", None) or [])
            or user in (getattr(cliente, "psicologi_multipli", None) or [])
            or user in (getattr(cliente, "consulenti_multipli", None) or [])
            or bool(
                ClienteProfessionistaHistory.query.filter_by(
                    cliente_id=cliente.cliente_id,
                    user_id=uid,
                    is_active=True,
                ).first()
            )
        )

    if assigned:
        return True

    if include_call_bonus:
        return bool(
            CallBonus.query.filter_by(
                cliente_id=cliente.cliente_id,
                professionista_id=uid,
                status=CallBonusStatusEnum.accettata.value,
            ).first()
        )

    return False


def is_professionista_assigned_to_service(
    user: Any,
    cliente: Any,
    service_type: str,
    *,
    include_call_bonus: bool = False,
) -> bool:
    """Verifica lato oggetto l'assegnazione a uno specifico servizio.

    Per i profili standard è consentito solo il servizio corrispondente alla
    specialità e la relativa M2M.
    Per il medico viene mantenuta la history attiva di tipo medico.
    """
    if getattr(user, "is_admin", False):
        return True

    if _role_value(user) != "professionista":
        return False

    uid = _user_id(user)
    if uid is None:
        return False

    service_key = str(service_type or "").strip().lower()
    specialty_group = normalize_specialty_group_for_rbac(user)

    if specialty_group == "medico":
        assigned = bool(
            ClienteProfessionistaHistory.query.filter_by(
                cliente_id=cliente.cliente_id,
                user_id=uid,
                tipo_professionista=TipoProfessionistaEnum.medico.value,
                is_active=True,
            ).first()
        )
    else:
        expected_specialty = SERVICE_TO_SPECIALTY.get(service_key)
        if not expected_specialty or specialty_group != expected_specialty:
            assigned = False
        else:
            relation_attr = SPECIALTY_TO_M2M_ATTR[expected_specialty]
            assigned = user in (getattr(cliente, relation_attr, None) or [])

    if assigned:
        return True

    if include_call_bonus:
        return bool(
            CallBonus.query.filter_by(
                cliente_id=cliente.cliente_id,
                professionista_id=uid,
                status=CallBonusStatusEnum.accettata.value,
            ).first()
        )

    return False

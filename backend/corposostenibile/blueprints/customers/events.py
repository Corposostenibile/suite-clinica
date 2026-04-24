"""
customers.events
================

SQLAlchemy event listener per mantenere coerenti i campi *cache* di scadenza
sul modello :class:`Cliente`.

Sincronizza i seguenti campi quando sono ``NULL`` **e** i dati per calcolarli
sono gia` presenti sul record:

* ``data_rinnovo``             = ``data_inizio_abbonamento + durata_programma_giorni``
* ``data_scadenza_nutrizione`` = ``data_inizio_nutrizione + durata_nutrizione_giorni``
* ``data_scadenza_coach``      = ``data_inizio_coach + durata_coach_giorni``
* ``data_scadenza_psicologia`` = ``data_inizio_psicologia + durata_psicologia_giorni``

Regola di sicurezza: valorizza il campo target **solo** se e` ``None``.
Non sovrascrive mai valori gia` impostati (es. override manuali da operatore,
rinnovi anticipati, casi speciali).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import event

from corposostenibile.models import Cliente

logger = logging.getLogger(__name__)


# (field_target, field_inizio, field_durata)
_SCADENZA_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("data_rinnovo",             "data_inizio_abbonamento", "durata_programma_giorni"),
    ("data_scadenza_nutrizione", "data_inizio_nutrizione",  "durata_nutrizione_giorni"),
    ("data_scadenza_coach",      "data_inizio_coach",       "durata_coach_giorni"),
    ("data_scadenza_psicologia", "data_inizio_psicologia",  "durata_psicologia_giorni"),
)


def _coerce_date(value) -> Optional[date]:
    """Converte value in `date` se possibile, altrimenti None.

    Tollera i tipi che possono arrivare al before_update hook:
    - None -> None
    - datetime -> .date()
    - date -> as-is
    - str ISO ("2026-05-07" / "2026-05-07T...") -> parse, o None se invalida
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _compute_scadenza(inizio, durata) -> Optional[date]:
    """Scadenza = inizio + durata giorni, se entrambi validi (durata > 0).

    MAI solleva eccezione: se non e' possibile calcolare ritorna None. Il hook
    chiamante ha gia' un try/except di sicurezza, ma meglio essere difensivi:
    i campi data_* possono arrivare come str se un PATCH bypassa il marshmallow
    schema (es. update diretto via setattr) -> evita TypeError 'str + timedelta'.
    """
    inizio_date = _coerce_date(inizio)
    if inizio_date is None:
        return None
    try:
        durata_int = int(durata) if durata is not None else 0
    except (TypeError, ValueError):
        return None
    if durata_int <= 0:
        return None
    return inizio_date + timedelta(days=durata_int)


def _sync_scadenza_fields(cliente: Cliente) -> None:
    """
    Per ogni coppia (inizio, durata) con target ``None`` e dati validi,
    popola il target. Non tocca mai valori gia` impostati.
    """
    for target, f_inizio, f_durata in _SCADENZA_FIELDS:
        if getattr(cliente, target, None) is not None:
            continue
        computed = _compute_scadenza(
            getattr(cliente, f_inizio, None),
            getattr(cliente, f_durata, None),
        )
        if computed is not None:
            setattr(cliente, target, computed)


@event.listens_for(Cliente, "before_insert")
def _before_insert_sync(mapper, connection, cliente):
    """Valorizza i campi scadenza prima di una INSERT."""
    try:
        _sync_scadenza_fields(cliente)
    except Exception:  # noqa: BLE001 - non bloccare mai la INSERT
        logger.exception(
            "customers.events: sync scadenze fallita in before_insert "
            "(cliente_id=%s)",
            getattr(cliente, "cliente_id", None),
        )


@event.listens_for(Cliente, "before_update")
def _before_update_sync(mapper, connection, cliente):
    """Valorizza i campi scadenza prima di una UPDATE, se ancora NULL."""
    try:
        _sync_scadenza_fields(cliente)
    except Exception:  # noqa: BLE001 - non bloccare mai la UPDATE
        logger.exception(
            "customers.events: sync scadenze fallita in before_update "
            "(cliente_id=%s)",
            getattr(cliente, "cliente_id", None),
        )

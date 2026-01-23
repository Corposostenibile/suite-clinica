"""
customers.tasks
===============

Job Celery asincroni per il feature-package *customers*.

Task presenti
-------------
* **new_customer_notification**   – notifica Slack / e-mail alla creazione
* **remind_expiring_contracts**   – promemoria contratti in scadenza
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

from flask import current_app
from sqlalchemy import func, text
from sqlalchemy.sql import select

from corposostenibile.extensions import celery, db
from corposostenibile.models import (
    Cliente,
)

from .repository import customers_repo  # noqa: E402 – dopo SQLAlchemy

# --------------------------------------------------------------------------- #
#  Helpers notifiche                                                          #
# --------------------------------------------------------------------------- #


def _send_slack_message(text: str) -> None:
    url = current_app.config.get("SLACK_WEBHOOK_URL")
    if not url:  # pragma: no cover
        current_app.logger.debug("Slack webhook non configurato.")
        return
    try:
        import requests  # import locale per evitare dipendenza hard
        requests.post(url, json={"text": text}, timeout=5)
    except Exception:  # pragma: no cover
        current_app.logger.exception("Errore invio Slack")


def _send_email(subject: str, body: str, recipients: List[str]) -> None:
    """
    Placeholder per integrazione SMTP / provider API.
    In DEBUG mostra il contenuto nel log.
    """
    if not recipients:
        current_app.logger.debug("[mail] Nessun destinatario per %s", subject)
        return

    current_app.logger.info(
        "Email [%s] a %s — anteprima corpo: %s",
        subject,
        ", ".join(recipients),
        body[:120],
    )


# --------------------------------------------------------------------------- #
#  Helpers KPI / cache                                                        #
# --------------------------------------------------------------------------- #


def _cache_set(key: str, value, ttl: int = 86_400) -> None:
    """
    Salva <value> in cache (Redis/Memcached). Fallback: log only.
    """
    # Flask-Caching
    cache = current_app.extensions.get("cache")
    if cache:
        cache.set(key, value, timeout=ttl)
        return

    # Redis puro (es. flask-redis)
    rds = current_app.extensions.get("redis")
    if rds:
        import json

        rds.setex(key, ttl, json.dumps(value, default=str))
        return

    current_app.logger.debug("[cache] %s = %s", key, value)  # fallback


# --------------------------------------------------------------------------- #
#  TASK: Notifica nuovo cliente                                               #
# --------------------------------------------------------------------------- #


@celery.task(name="customers.tasks.new_customer_notification")
def new_customer_notification(cliente_id: int) -> None:
    """Invia alert Slack + mail quando viene creato un nuovo cliente."""
    with celery.app.app_context():
        cliente = customers_repo.get_one(cliente_id)
        msg = f":tada: *Nuovo cliente* — {cliente.nome_cognome} (ID {cliente_id})"
        _send_slack_message(msg)
        _send_email(
            "Nuovo cliente acquisito",
            msg,
            current_app.config.get("CUSTOMERS_NOTIFICATION_MAILS", []),
        )


# --------------------------------------------------------------------------- #
#  TASK: Reminder contratti in scadenza                                       #
# --------------------------------------------------------------------------- #


@celery.task(name="customers.tasks.remind_expiring_contracts")
def remind_expiring_contracts(days: int = 15) -> None:
    """
    Invia reminder quotidiano sui contratti che scadono entro *days* giorni.
    """
    with celery.app.app_context():
        upcoming: List[Tuple[Cliente, date]] = customers_repo.expiring_contracts(days=days)
        if not upcoming:
            current_app.logger.debug(
                "[customers.tasks] Nessun contratto in scadenza entro %s gg.", days
            )
            return

        body_lines = [
            f"- {cl.nome_cognome} (ID {cl.cliente_id}) → {end.isoformat()}"
            for cl, end in upcoming
        ]
        body = "\n".join(body_lines)
        subject = f"Contratti in scadenza entro {days} giorni ({len(upcoming)})"

        _send_slack_message(f":alarm_clock: {subject}\n{body}")
        _send_email(
            subject,
            body,
            current_app.config.get("CUSTOMERS_EXPIRY_MAILS", []),
        )
        current_app.logger.info(
            "[customers.tasks] Reminder scadenze inviato: %s clienti.", len(upcoming)
        )


# --------------------------------------------------------------------------- #
#  TASK: Re-compute feedback KPI                                              #
# --------------------------------------------------------------------------- #


def _window_filter(period: str):
    """Ritorna la soglia data per il filtro temporale."""
    today = datetime.utcnow()
    if period == "week":
        return today - timedelta(days=7)
    if period == "month":
        return today - timedelta(days=30)
    if period == "quarter":
        return today - timedelta(days=90)
    if period == "year":
        return today - timedelta(days=365)
    raise ValueError("period must be week|month|quarter|year")




# --------------------------------------------------------------------------- #
#  BEAT SCHEDULE (solo tasks “customers”)                                     #
# --------------------------------------------------------------------------- #

with celery.app.app_context():
    beat = celery.conf.beat_schedule = celery.conf.beat_schedule or {}

    beat.setdefault(
        "customers-remind-expiring-contracts",
        {
            "task": "customers.tasks.remind_expiring_contracts",
            "schedule": 24 * 60 * 60,  # ogni giorno
        },
    )


# Nota:
# ─────────────────────────────────────────────────────────────────────────────
# Tutti i task di natura finanziaria (recompute LTV, report KPI, ecc.) sono
# definiti in `blueprints.accounting.tasks`, che provvede anche
# a registrare il proprio beat_schedule quando viene importato
# dall’application-factory.  Questo modulo resta quindi focalizzato
# esclusivamente sulle operation anagrafiche / di customer-care.

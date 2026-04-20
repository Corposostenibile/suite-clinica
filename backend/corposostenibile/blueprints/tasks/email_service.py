"""
Servizio di invio email per i task.

Attualmente usato SOLO per task di categoria ``onboarding``
(nuova assegnazione professionista → cliente).
"""

from __future__ import annotations

from flask import current_app
from flask_mail import Message
from sqlalchemy.orm import Session as SASession

from corposostenibile.extensions import mail, db
from corposostenibile.models import Cliente, User


def _frontend_base_url() -> str:
    """Risolve la base URL del frontend con fallback sicuri."""
    cfg = current_app.config
    return (
        cfg.get("FRONTEND_BASE_URL")
        or cfg.get("FRONTEND_URL")
        or cfg.get("BASE_URL")
        or ""
    ).rstrip("/")


def _client_detail_url(client_id: int | None) -> str | None:
    if not client_id:
        return None
    base = _frontend_base_url()
    path = f"/clienti-dettaglio/{client_id}"
    return f"{base}{path}" if base else path


def send_onboarding_task_email(task_id: int, assignee_id: int, client_id: int | None) -> bool:
    """Invia email di notifica per l'assegnazione di un nuovo cliente a un professionista.

    Chiamata dal listener ``after_commit`` dopo la creazione del Task di onboarding.
    Safe-by-default: ogni condizione mancante (mail server non configurato,
    utente/cliente non trovati, email assente) logga warning e ritorna False
    senza sollevare eccezioni.
    """
    try:
        if not current_app.config.get("MAIL_SERVER"):
            current_app.logger.warning(
                "[tasks.email] MAIL_SERVER non configurato, skip email onboarding task=%s", task_id
            )
            return False

        # Usiamo una sessione dedicata: il listener viene invocato dopo il commit
        # della session principale (stesso pattern di push_notifications.service).
        with SASession(bind=db.engine) as session:
            assignee = session.query(User).filter(User.id == assignee_id).first()
            cliente = (
                session.query(Cliente).filter(Cliente.cliente_id == client_id).first()
                if client_id
                else None
            )

            if not assignee or not assignee.email:
                current_app.logger.warning(
                    "[tasks.email] Assegnatario %s senza email, skip onboarding task=%s",
                    assignee_id,
                    task_id,
                )
                return False

            if not cliente:
                current_app.logger.warning(
                    "[tasks.email] Cliente %s non trovato, skip onboarding task=%s",
                    client_id,
                    task_id,
                )
                return False

            # Leggo i campi dentro la session per evitare DetachedInstanceError
            cliente_name = cliente.nome_cognome
            cliente_id_val = cliente.cliente_id
            storia_cliente = cliente.storia_cliente
            assignee_email = assignee.email
            assignee_first = (getattr(assignee, "first_name", None) or "").strip()

        first_name = assignee_first or assignee_email
        cliente_display = cliente_name or f"Cliente #{cliente_id_val}"
        subject = f"Nuovo cliente assegnato: {cliente_display}"
        detail_url = _client_detail_url(cliente_id_val)

        storia_section = ""
        if storia_cliente and storia_cliente.strip():
            storia_section = (
                f"\nSTORIA CLIENTE\n"
                f"--------------\n"
                f"{storia_cliente.strip()}\n"
            )

        url_block = f"\nAccedi al dettaglio del cliente qui:\n{detail_url}\n" if detail_url else ""

        body = (
            f"Ciao {first_name},\n\n"
            f"ti e' stato assegnato un nuovo cliente: {cliente_display}.\n"
            f"{storia_section}"
            f"\nAZIONE RICHIESTA\n"
            f"----------------\n"
            f"- Invia il messaggio di benvenuto al cliente\n"
            f"- Leggi i suoi check\n"
            f"{url_block}\n"
            f"Questo messaggio e' stato inviato automaticamente dal sistema Corposostenibile Suite.\n"
            f"Non rispondere a questa email.\n\n"
            f"Cordiali saluti,\n"
            f"Il Team Corposostenibile\n"
        )

        msg = Message(
            subject=subject,
            recipients=[assignee_email],
            body=body,
            sender=current_app.config.get(
                "MAIL_DEFAULT_SENDER", "noreply@corposostenibile.com"
            ),
        )
        mail.send(msg)
        current_app.logger.info(
            "[tasks.email] Email onboarding inviata a %s (task_id=%s, cliente_id=%s)",
            assignee_email,
            task_id,
            cliente_id_val,
        )
        return True
    except Exception:
        current_app.logger.exception(
            "[tasks.email] Errore invio email onboarding task=%s assignee=%s",
            task_id,
            assignee_id,
        )
        return False

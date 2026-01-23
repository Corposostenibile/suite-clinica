"""
auth.email_utils
================

Invio e-mail helper.  Se **Flask-Mail** è configurato usa SMTP,
altrimenti scrive su log (utile in dev / test).
"""

from __future__ import annotations

from typing import Sequence
from pathlib import Path

from flask import current_app
from flask_mail import Mail, Message  # type: ignore
from werkzeug.local import LocalProxy

_mail: Mail | None = None


def _get_mail() -> Mail:
    global _mail
    if _mail is None:
        _mail = Mail(current_app)
    return _mail


mail: Mail = LocalProxy(_get_mail)  # lazy proxy


def send_mail(subject: str, recipients: Sequence[str], body: str) -> None:
    """Invia e-mail (fallback: log)."""
    if not recipients:
        current_app.logger.debug("[mail] SKIP, recipients vuoto")
        return
    try:
        msg = Message(subject, recipients=list(recipients), body=body)
        mail.send(msg)
        current_app.logger.info("[mail] Inviata «%s» a %s", subject, ", ".join(recipients))
    except Exception:  # pragma: no cover
        current_app.logger.exception("[mail] Errore invio – subject: %s", subject)


def send_mail_html(subject: str, recipients: Sequence[str], text_body: str, html_body: str, attachments: dict[str, str] | None = None) -> None:
    """Invia e-mail con versione HTML e testo semplice, con supporto per attachment inline.
    
    Args:
        subject: Oggetto dell'email
        recipients: Lista destinatari
        text_body: Versione testo dell'email
        html_body: Versione HTML dell'email
        attachments: Dict di attachment inline {cid: file_path}
    """
    if not recipients:
        current_app.logger.debug("[mail] SKIP, recipients vuoto")
        return
    try:
        msg = Message(subject, recipients=list(recipients))
        msg.body = text_body
        msg.html = html_body
        
        # Aggiungi attachment inline per le immagini
        if attachments:
            for cid, file_path in attachments.items():
                path = Path(file_path)
                if path.exists():
                    with open(path, 'rb') as f:
                        msg.attach(
                            filename=path.name,
                            content_type=f'image/{path.suffix[1:]}',
                            data=f.read(),
                            disposition='inline',
                            headers={'Content-ID': f'<{cid}>'}
                        )
                        current_app.logger.debug(f"[mail] Attached inline image: {cid}")
                else:
                    current_app.logger.warning(f"[mail] File not found for inline attachment: {file_path}")
        
        mail.send(msg)
        current_app.logger.info("[mail] Inviata HTML «%s» a %s", subject, ", ".join(recipients))
    except Exception:  # pragma: no cover
        current_app.logger.exception("[mail] Errore invio HTML – subject: %s", subject)

"""Servizio di invio email per le review."""

from flask import current_app
from flask_mail import Message
from corposostenibile.extensions import mail


def _frontend_training_url(anchor: str | None = None) -> str:
    frontend_base = (
        current_app.config.get('FRONTEND_BASE_URL')
        or current_app.config.get('FRONTEND_URL')
        or current_app.config.get('BASE_URL')
        or ''
    ).rstrip('/')
    path = '/formazione'
    if anchor:
        path = f'{path}#{anchor}'
    return f'{frontend_base}{path}' if frontend_base else path


def send_review_notification(review):
    """
    Invia una notifica email testuale quando viene creato un nuovo training.
    NON invia email se il training è privato.
    
    Args:
        review: L'oggetto Review appena creato
    """
    try:
        # NON inviare email per training privati
        if review.is_private:
            current_app.logger.info(f'Training {review.id} è privato, skip invio email')
            return False
        
        # Controlla se l'invio email è abilitato
        if not current_app.config.get('MAIL_SERVER'):
            current_app.logger.warning('Email server non configurato, skip invio notifica training')
            return False
        
        reviewer = review.reviewer
        reviewee = review.reviewee
        
        # Costruisci l'URL per visualizzare il training
        review_url = _frontend_training_url()
        
        # Prepara il contenuto testuale dell'email
        subject = f"Hai ricevuto un nuovo training da {reviewer.first_name} {reviewer.last_name}"
        
        # Corpo del messaggio testuale
        body = f"""Ciao {reviewee.first_name},

{reviewer.first_name} {reviewer.last_name} ha scritto un training per te.

DETTAGLI TRAINING
---------------
Titolo: {review.title}
Tipo: {review.review_type}
Data: {review.created_at.strftime('%d/%m/%Y alle %H:%M')}"""

        if review.period_start or review.period_end:
            period_text = ""
            if review.period_start:
                period_text = review.period_start.strftime('%d/%m/%Y')
            if review.period_end:
                if period_text:
                    period_text += f" - {review.period_end.strftime('%d/%m/%Y')}"
                else:
                    period_text = f"fino al {review.period_end.strftime('%d/%m/%Y')}"
            body += f"\nPeriodo di riferimento: {period_text}"
        
        body += f"""

AZIONE RICHIESTA
----------------
Accedi alla Suite per leggere il training completo e confermare la lettura:
{review_url}

È importante che tu prenda visione del training e confermi la lettura.

Questo messaggio è stato inviato automaticamente dal sistema Corposostenibile Suite.
Non rispondere a questa email.

Cordiali saluti,
Il Team Corposostenibile
"""
        
        # Crea e invia il messaggio
        msg = Message(
            subject=subject,
            recipients=[reviewee.email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )
        
        # Se il training non è privato, metti in copia anche il trainer
        if not review.is_private:
            msg.cc = [reviewer.email]
        
        mail.send(msg)
        current_app.logger.info(f'Email training notification sent to {reviewee.email}')
        return True
        
    except Exception as e:
        current_app.logger.error(f'Errore invio email training: {str(e)}')
        return False


def send_message_notification(message, recipient):
    """
    Invia una notifica email quando viene inviato un nuovo messaggio in una review.
    
    Args:
        message: L'oggetto ReviewMessage appena creato
        recipient: L'oggetto User che deve ricevere la notifica
    """
    try:
        # Controlla se l'invio email è abilitato
        if not current_app.config.get('MAIL_SERVER'):
            current_app.logger.warning('Email server non configurato, skip invio notifica messaggio')
            return False
        
        review = message.review
        sender = message.sender
        
        # Costruisci l'URL per visualizzare il training con anchor alla chat
        review_url = _frontend_training_url(f'review-{review.id}-chat')
        
        # Prepara il contenuto testuale dell'email
        subject = f"Nuovo messaggio nel training: {review.title}"
        
        # Corpo del messaggio testuale
        body = f"""Ciao {recipient.first_name},

{sender.first_name} {sender.last_name} ha inviato un nuovo messaggio nel training.

DETTAGLI TRAINING
---------------
Titolo: {review.title}
Tipo: {review.review_type}
Data Training: {review.created_at.strftime('%d/%m/%Y')}

NUOVO MESSAGGIO
---------------
Da: {sender.first_name} {sender.last_name}
Data: {message.created_at.strftime('%d/%m/%Y alle %H:%M')}

Messaggio:
"{message.content[:500]}{'...' if len(message.content) > 500 else ''}"

AZIONE RICHIESTA
----------------
Clicca qui per leggere il messaggio completo e rispondere:
{review_url}

È importante che tu legga il messaggio e, se necessario, fornisca una risposta.

Questo messaggio è stato inviato automaticamente dal sistema Corposostenibile Suite.
Non rispondere a questa email.

Cordiali saluti,
Il Team Corposostenibile
"""
        
        # Crea e invia il messaggio
        msg = Message(
            subject=subject,
            recipients=[recipient.email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )
        
        mail.send(msg)
        current_app.logger.info(f'Email message notification sent to {recipient.email}')
        return True
        
    except Exception as e:
        current_app.logger.error(f'Errore invio email messaggio training: {str(e)}')
        return False


def send_review_request_notification(request):
    """
    Invia una notifica email quando viene richiesto un training.
    
    Args:
        request: L'oggetto ReviewRequest appena creato
    """
    try:
        # Controlla se l'invio email è abilitato
        if not current_app.config.get('MAIL_SERVER'):
            current_app.logger.warning('Email server non configurato, skip invio notifica richiesta training')
            return False
        
        requester = request.requester
        recipient = request.requested_to
        
        # Costruisci l'URL per visualizzare le richieste
        requests_url = _frontend_training_url()
        
        # Prepara il contenuto testuale dell'email
        priority_labels = {
            'low': 'Bassa',
            'normal': 'Normale',
            'high': 'Alta',
            'urgent': 'URGENTE'
        }
        
        subject = f"Nuova richiesta di training da {requester.first_name} {requester.last_name}"
        if request.priority == 'urgent':
            subject = f"🔴 URGENTE - {subject}"
        
        # Corpo del messaggio testuale
        body = f"""Ciao {recipient.first_name},

{requester.first_name} {requester.last_name} ha richiesto un training su:

ARGOMENTO: {request.subject}
PRIORITÀ: {priority_labels.get(request.priority, request.priority)}
DATA RICHIESTA: {request.created_at.strftime('%d/%m/%Y alle %H:%M')}"""

        if request.description:
            body += f"""

DESCRIZIONE DETTAGLIATA:
{request.description}"""
        
        body += f"""

AZIONE RICHIESTA
----------------
Accedi alla Suite per gestire questa richiesta:
{requests_url}

Puoi accettare la richiesta e scrivere il training, oppure rifiutarla fornendo una motivazione.

Questo messaggio è stato inviato automaticamente dal sistema Corposostenibile Suite.
Non rispondere a questa email.

Cordiali saluti,
Il Team Corposostenibile
"""
        
        # Crea e invia il messaggio
        msg = Message(
            subject=subject,
            recipients=[recipient.email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )
        
        mail.send(msg)
        current_app.logger.info(f'Email training request notification sent to {recipient.email}')
        return True
        
    except Exception as e:
        current_app.logger.error(f'Errore invio email richiesta training: {str(e)}')
        return False


def send_review_request_response_notification(request):
    """
    Invia una notifica email quando una richiesta di training riceve risposta.
    
    Args:
        request: L'oggetto ReviewRequest con la risposta
    """
    try:
        # Controlla se l'invio email è abilitato
        if not current_app.config.get('MAIL_SERVER'):
            current_app.logger.warning('Email server non configurato, skip invio notifica risposta richiesta')
            return False
        
        requester = request.requester
        responder = request.requested_to
        
        # Prepara il contenuto in base allo stato
        if request.status == 'completed':
            subject = f"✅ Il tuo training su '{request.subject}' è pronto!"
            
            # URL per vedere il training
            review_url = _frontend_training_url()
            
            body = f"""Ciao {requester.first_name},

Buone notizie! {responder.first_name} {responder.last_name} ha completato il training che avevi richiesto.

ARGOMENTO: {request.subject}
COMPLETATO IL: {datetime.utcnow().strftime('%d/%m/%Y alle %H:%M')}

AZIONE RICHIESTA
----------------
Accedi alla Suite per leggere il training e confermare la lettura:
{review_url}

È importante che tu prenda visione del training e confermi la lettura."""
            
        elif request.status == 'rejected':
            subject = f"Richiesta training '{request.subject}' - Risposta"
            
            body = f"""Ciao {requester.first_name},

{responder.first_name} {responder.last_name} ha esaminato la tua richiesta di training.

ARGOMENTO: {request.subject}
STATO: Non accettata"""
            
            if request.response_notes:
                body += f"""

MOTIVAZIONE:
{request.response_notes}"""
            
            body += """

Puoi contattare direttamente il tuo responsabile per ulteriori chiarimenti o inviare una nuova richiesta più specifica."""
            
        else:
            # Altri stati (accepted, etc.)
            return False
        
        body += """

Questo messaggio è stato inviato automaticamente dal sistema Corposostenibile Suite.
Non rispondere a questa email.

Cordiali saluti,
Il Team Corposostenibile
"""
        
        # Crea e invia il messaggio
        msg = Message(
            subject=subject,
            recipients=[requester.email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )
        
        mail.send(msg)
        current_app.logger.info(f'Email training request response sent to {requester.email}')
        return True
        
    except Exception as e:
        current_app.logger.error(f'Errore invio email risposta richiesta: {str(e)}')
        return False

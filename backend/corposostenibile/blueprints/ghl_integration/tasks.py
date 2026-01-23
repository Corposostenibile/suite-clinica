"""
Celery tasks for asynchronous GHL webhook processing
"""

from celery import current_app as celery_app
from celery.utils.log import get_task_logger
from flask import current_app
from typing import Dict, Any
import json
from datetime import datetime

from corposostenibile import create_app
from corposostenibile.extensions import db
from .processors import OpportunityProcessor
from .validators import WebhookValidator

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name='ghl.process_acconto_open',
    max_retries=3,
    default_retry_delay=300  # 5 minuti
)
def process_acconto_open_webhook(self, payload: Dict[str, Any]):
    """
    Task Celery per processare webhook acconto_open in background

    Args:
        payload: Il payload del webhook già validato

    Returns:
        Dict con i risultati del processamento
    """
    try:
        # Crea app context per accedere al database
        app = create_app()
        with app.app_context():
            logger.info(f"[GHL Task] Processing acconto_open webhook for opportunity {payload.get('ghl_opportunity_id')}")

            # Valida il payload
            is_valid, parsed_data, errors = WebhookValidator.validate_webhook(payload, 'acconto_open')

            if not is_valid:
                logger.error(f"[GHL Task] Invalid payload: {errors}")
                return {
                    'success': False,
                    'errors': errors
                }

            # Processa l'opportunità
            result = OpportunityProcessor.process_acconto_open(parsed_data)

            if result['success']:
                logger.info(
                    f"[GHL Task] Successfully processed acconto_open. "
                    f"Cliente ID: {result['cliente_id']}, "
                    f"Assignment ID: {result['assignment_id']}"
                )

                # Invia notifiche (altro task)
                send_finance_notification.delay(result['cliente_id'], result['assignment_id'])
            else:
                logger.error(f"[GHL Task] Failed to process acconto_open: {result['errors']}")

            return result

    except Exception as exc:
        logger.error(f"[GHL Task] Error in process_acconto_open_webhook: {str(exc)}")

        # Retry con exponential backoff
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))


@celery_app.task(
    bind=True,
    name='ghl.process_chiuso_won',
    max_retries=3,
    default_retry_delay=300
)
def process_chiuso_won_webhook(self, payload: Dict[str, Any]):
    """
    Task Celery per processare webhook chiuso_won in background

    Args:
        payload: Il payload del webhook già validato

    Returns:
        Dict con i risultati del processamento
    """
    try:
        app = create_app()
        with app.app_context():
            logger.info(f"[GHL Task] Processing chiuso_won webhook for opportunity {payload.get('ghl_opportunity_id')}")

            # Valida il payload
            is_valid, parsed_data, errors = WebhookValidator.validate_webhook(payload, 'chiuso_won')

            if not is_valid:
                logger.error(f"[GHL Task] Invalid payload: {errors}")
                return {
                    'success': False,
                    'errors': errors
                }

            # Processa l'opportunità
            result = OpportunityProcessor.process_chiuso_won(parsed_data)

            if result['success']:
                logger.info(
                    f"[GHL Task] Successfully processed chiuso_won. "
                    f"Cliente ID: {result['cliente_id']}, "
                    f"Assignment ID: {result['assignment_id']}"
                )

                # Invia notifiche per assegnazione professionisti
                send_assignment_notification.delay(result['cliente_id'], result['assignment_id'])
            else:
                logger.error(f"[GHL Task] Failed to process chiuso_won: {result['errors']}")

            return result

    except Exception as exc:
        logger.error(f"[GHL Task] Error in process_chiuso_won_webhook: {str(exc)}")
        raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))


@celery_app.task(name='ghl.send_finance_notification')
def send_finance_notification(cliente_id: int, assignment_id: int):
    """
    Invia notifica al team finance per nuovo cliente con acconto

    Args:
        cliente_id: ID del cliente
        assignment_id: ID dell'assegnazione
    """
    try:
        app = create_app()
        with app.app_context():
            from corposostenibile.models import Cliente, ServiceClienteAssignment, User
            from corposostenibile.utils.email import send_email

            # Carica i dati
            cliente = Cliente.query.get(cliente_id)
            assignment = ServiceClienteAssignment.query.get(assignment_id)

            if not cliente or not assignment:
                logger.error(f"[GHL Task] Cliente or assignment not found for notification")
                return

            # Trova utenti finance
            finance_users = User.query.filter_by(role='finance', is_active=True).all()

            if not finance_users:
                logger.warning("[GHL Task] No finance users found for notification")
                return

            # Prepara email
            subject = f"Nuovo Cliente da Verificare: {cliente.nome_cognome}"
            body = f"""
            Un nuovo cliente è stato creato da GHL e richiede verifica pagamento:

            Cliente: {cliente.nome_cognome}
            Email: {cliente.mail}
            Telefono: {cliente.cellulare or 'Non disponibile'}
            Pacchetto: {cliente.programma_attuale or 'Non specificato'}

            Acconto pagato: €{assignment.ghl_opportunity.acconto_pagato if assignment.ghl_opportunity else 'N/D'}
            Importo totale: €{assignment.ghl_opportunity.importo_totale if assignment.ghl_opportunity else 'N/D'}

            Accedi alla dashboard finance per verificare e approvare:
            {current_app.config['BASE_URL']}/finance/dashboard/verify/{assignment_id}
            """

            # Invia email a tutti gli utenti finance
            for user in finance_users:
                try:
                    send_email(user.email, subject, body)
                    logger.info(f"[GHL Task] Finance notification sent to {user.email}")
                except Exception as e:
                    logger.error(f"[GHL Task] Failed to send email to {user.email}: {e}")

    except Exception as e:
        logger.error(f"[GHL Task] Error sending finance notification: {e}")


@celery_app.task(name='ghl.send_assignment_notification')
def send_assignment_notification(cliente_id: int, assignment_id: int):
    """
    Invia notifica per assegnazione professionisti dopo pagamento completo

    Args:
        cliente_id: ID del cliente
        assignment_id: ID dell'assegnazione
    """
    try:
        app = create_app()
        with app.app_context():
            from corposostenibile.models import Cliente, ServiceClienteAssignment, User
            from corposostenibile.utils.email import send_email

            # Carica i dati
            cliente = Cliente.query.get(cliente_id)
            assignment = ServiceClienteAssignment.query.get(assignment_id)

            if not cliente or not assignment:
                logger.error(f"[GHL Task] Cliente or assignment not found for notification")
                return

            # Trova servizio clienti users
            service_users = User.query.filter(
                User.role.in_(['nutrizionista', 'coach', 'psicologa']),
                User.is_active == True
            ).all()

            if not service_users:
                logger.warning("[GHL Task] No service users found for notification")
                return

            # Prepara email
            subject = f"Nuovo Cliente da Assegnare: {cliente.nome_cognome}"
            body = f"""
            Un cliente ha completato il pagamento ed è pronto per l'assegnazione:

            Cliente: {cliente.nome_cognome}
            Email: {cliente.mail}
            Telefono: {cliente.cellulare or 'Non disponibile'}
            Pacchetto: {cliente.programma_attuale or 'Non specificato'}

            Pagamento: COMPLETO ✅

            Accedi alla dashboard servizio clienti per procedere con l'assegnazione:
            {current_app.config['BASE_URL']}/customers/assign/{assignment_id}
            """

            # Invia notifica (per ora a tutti, poi sarà più selettiva)
            for user in service_users[:3]:  # Limita a 3 per non spammare
                try:
                    send_email(user.email, subject, body)
                    logger.info(f"[GHL Task] Assignment notification sent to {user.email}")
                except Exception as e:
                    logger.error(f"[GHL Task] Failed to send email to {user.email}: {e}")

    except Exception as e:
        logger.error(f"[GHL Task] Error sending assignment notification: {e}")


@celery_app.task(
    bind=True,
    name='ghl.retry_failed_webhook',
    max_retries=5
)
def retry_failed_webhook(self, webhook_id: int):
    """
    Riprova a processare un webhook fallito

    Args:
        webhook_id: ID del webhook fallito nel database
    """
    try:
        app = create_app()
        with app.app_context():
            from corposostenibile.models import GHLOpportunity

            opportunity = GHLOpportunity.query.get(webhook_id)
            if not opportunity or opportunity.processed:
                logger.info(f"[GHL Task] Webhook {webhook_id} already processed or not found")
                return

            # Incrementa retry count
            opportunity.retry_count = (opportunity.retry_count or 0) + 1

            if opportunity.retry_count > 5:
                opportunity.error_message = "Max retries exceeded"
                db.session.commit()
                logger.error(f"[GHL Task] Max retries exceeded for webhook {webhook_id}")
                return

            # Riprova a processare basandosi sullo status
            payload = opportunity.webhook_payload
            if opportunity.status == 'acconto_open':
                result = process_acconto_open_webhook.delay(payload)
            elif opportunity.status == 'chiuso_won':
                result = process_chiuso_won_webhook.delay(payload)
            else:
                logger.error(f"[GHL Task] Unknown status for webhook {webhook_id}: {opportunity.status}")
                return

            logger.info(f"[GHL Task] Retrying webhook {webhook_id} (attempt {opportunity.retry_count})")
            db.session.commit()

    except Exception as exc:
        logger.error(f"[GHL Task] Error retrying webhook {webhook_id}: {exc}")
        raise self.retry(exc=exc, countdown=600)  # Retry dopo 10 minuti
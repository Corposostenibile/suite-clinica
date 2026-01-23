"""
Servizi per il blueprint communications.
"""

from typing import List, Optional
from datetime import datetime

from flask import current_app, url_for, render_template
from flask_login import current_user
from flask_mail import Message
from sqlalchemy.exc import SQLAlchemyError

from corposostenibile.extensions import db, mail
from corposostenibile.models import Communication, CommunicationRead, User, Department


class CommunicationService:
    """Servizio per la gestione delle comunicazioni."""
    
    @staticmethod
    def create_communication(
        title: str,
        content: str,
        author: User,
        departments: Optional[List[Department]] = None,
        is_for_all: bool = False
    ) -> Communication:
        """
        Crea una nuova comunicazione e invia le email.
        
        Args:
            title: Titolo della comunicazione
            content: Contenuto HTML della comunicazione
            author: Autore della comunicazione
            departments: Lista dei dipartimenti destinatari
            is_for_all: Se True, invia a tutti i dipartimenti
            
        Returns:
            Communication: La comunicazione creata
        """
        try:
            # Crea la comunicazione
            communication = Communication(
                title=title,
                content=content,
                author_id=author.id,
                is_for_all_departments=is_for_all
            )
            
            # Aggiungi i dipartimenti se non è per tutti
            if not is_for_all and departments:
                communication.departments = departments
            
            db.session.add(communication)
            db.session.commit()
            
            # Invia le email ai destinatari
            CommunicationService._send_notification_emails(communication)
            
            return communication
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Errore creazione comunicazione: {str(e)}")
            raise
    
    @staticmethod
    def mark_as_read(communication: Communication, user: User) -> bool:
        """
        Marca una comunicazione come letta da un utente.
        
        Args:
            communication: La comunicazione
            user: L'utente che ha letto
            
        Returns:
            bool: True se marcata con successo, False se già letta
        """
        # Verifica se già letta
        if communication.has_read(user):
            return False
        
        try:
            read = CommunicationRead(
                communication_id=communication.id,
                user_id=user.id,
                read_at=datetime.utcnow()
            )
            db.session.add(read)
            db.session.commit()
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Errore marcatura lettura: {str(e)}")
            return False
    
    @staticmethod
    def _send_notification_emails(communication: Communication) -> None:
        """Invia email di notifica ai destinatari."""
        recipients = communication.get_recipients()
        
        for recipient in recipients:
            if not recipient.email:
                continue
            
            # Prepara il contesto per l'email
            context = {
                'user': recipient,
                'communication': communication,
                'author_name': communication.author.full_name,
                'communication_url': url_for(
                    'communications.detail',
                    communication_id=communication.id,
                    _external=True
                )
            }
            
            # Prepara il corpo dell'email
            html_body = render_template(
                'communications/email/new_communication.html',
                **context
            )
            
            text_body = f"""
Nuova Comunicazione da {communication.author.full_name}

{communication.title}

Ti preghiamo di accedere alla Suite per leggere la comunicazione completa e confermare la lettura.

Link: {context['communication_url']}

Cordiali saluti,
Il Team di Corpo Sostenibile
"""
            
            # Invia email tramite Flask-Mail
            try:
                msg = Message(
                    subject=f"Nuova Comunicazione da {communication.author.full_name}",
                    recipients=[recipient.email],
                    body=text_body,
                    html=html_body
                )
                mail.send(msg)
            except Exception as e:
                current_app.logger.error(f"Errore invio email a {recipient.email}: {str(e)}")
    
    @staticmethod
    def get_communication_stats(communication: Communication) -> dict:
        """
        Ottiene le statistiche di una comunicazione.
        
        Args:
            communication: La comunicazione
            
        Returns:
            dict: Statistiche della comunicazione
        """
        unread_users = communication.get_unread_users()
        
        return {
            'total_recipients': communication.total_recipients,
            'read_count': communication.read_count,
            'unread_count': communication.unread_count,
            'read_percentage': (
                (communication.read_count / communication.total_recipients * 100)
                if communication.total_recipients > 0 else 0
            ),
            'unread_users': [
                {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'department': user.department.name if user.department else 'N/A'
                }
                for user in unread_users
            ]
        }
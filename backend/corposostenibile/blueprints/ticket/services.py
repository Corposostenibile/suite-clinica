"""
blueprints/ticket/services.py
=============================

Business logic e servizi per il sistema ticketing.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from flask import current_app, render_template_string
from flask_mail import Message
from sqlalchemy import and_, or_, func, case, distinct
from sqlalchemy.exc import SQLAlchemyError

from corposostenibile.extensions import db, mail
from corposostenibile.models import (
    Cliente,
    Department,
    Ticket,
    TicketCategoryEnum,
    TicketComment,
    TicketStatusChange,
    TicketStatusEnum,
    TicketUrgencyEnum,
    User,
)
from .timezone_utils import get_utc_now

from .email_templates import (
    get_new_ticket_email,
    get_status_change_email,
    get_ticket_shared_email,
)


class TicketService:
    """Servizio principale per la gestione dei ticket."""
    
    def __init__(self):
        self.email_service = TicketEmailService()
    
    def create_ticket(
        self,
        requester_first_name: str,
        requester_last_name: str,
        requester_email: str,
        department_id: int,
        title: str,
        description: str,
        urgency: TicketUrgencyEnum,
        requester_department: Optional[str] = None,
        related_client_name: Optional[str] = None,
        cliente_id: Optional[int] = None,
        created_by: Optional[User] = None,
        assigned_to_id: Optional[int] = None,
        category: Optional[TicketCategoryEnum] = None,
        attachments: Optional[List[FileStorage]] = None,
        send_notifications: bool = True
    ) -> Ticket:
        """
        Crea un nuovo ticket e invia notifiche.
        
        Args:
            requester_first_name: Nome del richiedente
            requester_last_name: Cognome del richiedente
            requester_email: Email del richiedente
            department_id: ID del dipartimento destinatario
            title: Titolo del ticket
            description: Descrizione dettagliata
            urgency: Livello di urgenza
            requester_department: Dipartimento del richiedente (opzionale)
            related_client_name: Nome cliente/lead correlato (opzionale)
            send_notifications: Se inviare email di notifica
            
        Returns:
            Ticket creato
            
        Raises:
            SQLAlchemyError: In caso di errore database
        """
        
        # Verifica che il dipartimento esista
        department = Department.query.get(department_id)
        if not department:
            raise ValueError(f"Dipartimento {department_id} non trovato")
        
        # Crea il ticket
        ticket = Ticket(
            requester_first_name=requester_first_name,
            requester_last_name=requester_last_name,
            requester_email=requester_email,
            requester_department=requester_department,
            department_id=department_id,
            title=title,
            description=description,
            urgency=urgency,
            category=category,  # Categoria (solo per dept 13)
            related_client_name=related_client_name,
            cliente_id=cliente_id,
            status=TicketStatusEnum.nuovo,
            ticket_number=Ticket.generate_ticket_number(),
            created_by_id=created_by.id if created_by else None,
        )
        
        # Gestione assegnazione diretta (OBBLIGATORIA)
        if not assigned_to_id:
            raise ValueError("Devi selezionare un membro del dipartimento")
            
        # Verifica che l'utente esista e sia del dipartimento giusto
        assigned_user = User.query.get(assigned_to_id)
        if not assigned_user:
            raise ValueError("Membro selezionato non valido")
            
        # IMPORTANTE: Permettiamo l'assegnazione all'HEAD anche se non è membro diretto
        # L'HEAD può ricevere ticket del dipartimento che gestisce
        is_department_head = (department.head_id == assigned_user.id)
        is_department_member = (assigned_user.department_id == department_id)
        
        # Gestione speciale per Sales Team (Consulenti Sales 1 e 2)
        is_sales_team_member = False
        if department.name in ['Consulenti Sales 1', 'Consulenti Sales 2']:
            # Se il dipartimento è uno dei Sales, verifica se l'utente appartiene a qualsiasi Sales
            sales_depts = Department.query.filter(
                Department.name.in_(['Consulenti Sales 1', 'Consulenti Sales 2'])
            ).all()
            sales_dept_ids = [d.id for d in sales_depts]
            is_sales_team_member = assigned_user.department_id in sales_dept_ids
            # Controlla anche se è head di uno dei Sales
            for sales_dept in sales_depts:
                if sales_dept.head_id == assigned_user.id:
                    is_sales_team_member = True
                    break
        
        if not (is_department_member or is_department_head or is_sales_team_member):
            raise ValueError("Il membro selezionato non appartiene al dipartimento scelto")
        
        # Assegna il ticket usando la relazione many-to-many
        ticket.assigned_users = [assigned_user]
        # Il ticket rimane con status "nuovo" finché non viene preso in carico
        
        # Calcola scadenza
        ticket.due_date = ticket.calculate_due_date()
        
        # Salva il ticket prima di aggiungere allegati (per avere l'ID)
        db.session.add(ticket)
        db.session.flush()  # Ottieni l'ID senza fare commit
        
        # Gestione allegati multipli (se presenti)
        if attachments:
            # Filtra solo i file validi
            valid_files = [f for f in attachments if f and f.filename]
            
            # Limita a 5 file
            if len(valid_files) > 5:
                valid_files = valid_files[:5]
            
            for attachment in valid_files:
                saved_filename, saved_path = self._save_attachment(attachment, ticket.ticket_number)
                if saved_filename and saved_path:
                    from corposostenibile.models import TicketAttachment
                    import os
                    
                    # Calcola la dimensione del file salvato
                    project_root = os.path.dirname(current_app.root_path)
                    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
                    full_path = os.path.join(project_root, upload_folder, saved_path)
                    file_size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                    
                    ticket_attachment = TicketAttachment(
                        ticket_id=ticket.id,
                        filename=saved_filename,
                        file_path=saved_path,
                        file_size=file_size,
                        mime_type=attachment.content_type,
                        uploaded_by_id=created_by.id if created_by else None
                    )
                    db.session.add(ticket_attachment)
                    
                    current_app.logger.info(
                        f"Allegato salvato per ticket {ticket.ticket_number}: {saved_filename}"
                    )
        
        # Se c'è un nome cliente, prova a collegarlo
        if related_client_name:
            # Ricerca fuzzy del cliente
            cliente = Cliente.query.filter(
                Cliente.nome_cognome.ilike(f"%{related_client_name}%")
            ).first()
            if cliente:
                ticket.cliente_id = cliente.cliente_id
        
        try:
            db.session.commit()
            
            # Invia notifiche email
            if send_notifications:
                self._send_new_ticket_notifications(ticket)
            
            current_app.logger.info(
                f"Ticket {ticket.ticket_number} creato con successo"
            )
            
            return ticket
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Errore creazione ticket: {str(e)}")
            raise
    
    def change_status(
        self,
        ticket: Ticket,
        new_status: TicketStatusEnum,
        changed_by: User,
        message: str,
        notify_requester: bool = True
    ) -> TicketStatusChange:
        """
        Cambia lo stato di un ticket e traccia il cambiamento.
        
        Args:
            ticket: Ticket da aggiornare
            new_status: Nuovo stato
            changed_by: Utente che effettua il cambio
            message: Messaggio di aggiornamento
            notify_requester: Se notificare il richiedente
            
        Returns:
            TicketStatusChange creato
        """
        
        if ticket.status == new_status:
            raise ValueError("Il ticket è già in questo stato")
        
        old_status = ticket.status
        
        # Crea record di cambio stato
        status_change = TicketStatusChange(
            ticket_id=ticket.id,
            from_status=old_status,
            to_status=new_status,
            changed_by_id=changed_by.id,
            message=message
        )
        
        # Aggiorna il ticket
        ticket.status = new_status
        
        # Se chiuso, imposta data chiusura
        if new_status == TicketStatusEnum.chiuso:
            import pytz
            # Salviamo in UTC ma considerando l'ora di Roma
            rome_tz = pytz.timezone('Europe/Rome')
            now_rome = datetime.now(rome_tz)
            ticket.closed_at = now_rome.astimezone(pytz.utc).replace(tzinfo=None)
        
        try:
            db.session.add(status_change)
            db.session.commit()
            
            # Invia notifiche
            self._send_status_change_notifications(
                ticket, status_change, notify_requester
            )
            
            current_app.logger.info(
                f"Ticket {ticket.ticket_number} stato cambiato: "
                f"{old_status.value} → {new_status.value}"
            )
            
            return status_change
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Errore cambio stato ticket: {str(e)}")
            raise
    
    def share_with_departments(
        self,
        ticket: Ticket,
        departments: List[Department],
        shared_by: User,
        message: Optional[str] = None
    ) -> None:
        """
        Condivide un ticket con altri dipartimenti.
        
        Args:
            ticket: Ticket da condividere
            departments: Lista dipartimenti con cui condividere
            shared_by: Utente che condivide
            message: Messaggio opzionale
        """
        
        if not departments:
            return
        
        try:
            # Aggiungi dipartimenti
            for dept in departments:
                if dept not in ticket.shared_departments:
                    ticket.shared_departments.append(dept)
            
            db.session.commit()
            
            # Invia notifiche ai nuovi dipartimenti
            self._send_share_notifications(
                ticket, departments, shared_by, message
            )
            
            current_app.logger.info(
                f"Ticket {ticket.ticket_number} condiviso con "
                f"{len(departments)} dipartimenti"
            )
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Errore condivisione ticket: {str(e)}")
            raise
    
    def get_department_tickets(
        self,
        department: Department,
        include_shared: bool = True,
        status_filter: Optional[List[TicketStatusEnum]] = None,
        urgency_filter: Optional[List[TicketUrgencyEnum]] = None,
        limit: Optional[int] = None
    ):
        """
        Ottiene i ticket di un dipartimento.
        
        Args:
            department: Dipartimento
            include_shared: Se includere ticket condivisi
            status_filter: Filtra per stati specifici
            urgency_filter: Filtra per urgenze specifiche
            limit: Limite risultati
            
        Returns:
            Query di ticket
        """
        
        # Query base
        query = Ticket.query
        
        if include_shared:
            # Ticket assegnati O condivisi con il dipartimento
            query = query.filter(
                or_(
                    Ticket.department_id == department.id,
                    Ticket.shared_departments.contains(department)
                )
            )
        else:
            # Solo ticket assegnati
            query = query.filter(Ticket.department_id == department.id)
        
        # Filtri
        if status_filter:
            query = query.filter(Ticket.status.in_(status_filter))
        
        if urgency_filter:
            query = query.filter(Ticket.urgency.in_(urgency_filter))
        
        # Ordinamento: urgenza alta prima, poi per data
        query = query.order_by(
            Ticket.urgency.asc(),  # 1 (alta) viene prima
            Ticket.created_at.desc()
        )
        
        if limit:
            query = query.limit(limit)
        
        return query
    
    def get_overdue_tickets(self) -> List[Ticket]:
        """
        Ottiene tutti i ticket scaduti non ancora chiusi.
        
        Returns:
            Lista di ticket scaduti
        """
        
        return Ticket.query.filter(
            Ticket.status != TicketStatusEnum.chiuso,
            Ticket.due_date < get_utc_now()
        ).all()
    
    def get_ticket_stats(self, department: Optional[Department] = None) -> dict:
        """
        Calcola statistiche sui ticket.
        
        Args:
            department: Se specificato, filtra per dipartimento
            
        Returns:
            Dizionario con statistiche
        """
        
        query = Ticket.query
        
        if department:
            query = self.get_department_tickets(department)
        
        total = query.count()
        
        stats = {
            'total': total,
            'by_status': {},
            'by_urgency': {},
            'overdue': 0,
            'avg_resolution_hours': 0,
            'closure_rate': 0
        }
        
        if total == 0:
            return stats
        
        # Per stato
        for status in TicketStatusEnum:
            count = query.filter(Ticket.status == status).count()
            stats['by_status'][status.value] = {
                'count': count,
                'percentage': (count / total) * 100
            }
        
        # Per urgenza
        for urgency in TicketUrgencyEnum:
            count = query.filter(Ticket.urgency == urgency).count()
            stats['by_urgency'][urgency.value] = {
                'count': count,
                'percentage': (count / total) * 100
            }
        
        # Scaduti
        stats['overdue'] = query.filter(
            Ticket.status != TicketStatusEnum.chiuso,
            Ticket.due_date < get_utc_now()
        ).count()
        
        # Tempo medio risoluzione (solo ticket chiusi)
        closed_tickets = query.filter(
            Ticket.status == TicketStatusEnum.chiuso,
            Ticket.closed_at.isnot(None)
        ).all()
        
        if closed_tickets:
            total_hours = sum(
                (t.closed_at - t.created_at).total_seconds() / 3600
                for t in closed_tickets
            )
            stats['avg_resolution_hours'] = total_hours / len(closed_tickets)
            stats['closure_rate'] = (len(closed_tickets) / total) * 100
        
        return stats
    
    # ─────────────────────── Metodi privati ─────────────────────── #
    
    def _send_new_ticket_notifications(self, ticket: Ticket) -> None:
        """Invia notifiche per nuovo ticket."""
        
        if not current_app.config.get('TICKET_EMAIL_ENABLED', False):
            return
        
        try:
            # Email al richiedente
            self.email_service.send_email(
                to_email=ticket.requester_email,
                subject=f"Ticket #{ticket.ticket_number} - Conferma ricezione",
                html_content=get_new_ticket_email(ticket, is_requester=True)
            )
            
            # Email al capo dipartimento
            if ticket.department.notification_email:
                self.email_service.send_email(
                    to_email=ticket.department.notification_email,
                    subject=f"Nuovo Ticket #{ticket.ticket_number} - {ticket.urgency_label}",
                    html_content=get_new_ticket_email(ticket, is_requester=False)
                )
            
            # Email al membro assegnato (se c'è)
            if ticket.assigned_users:
                for assigned_user in ticket.assigned_users:
                    self.email_service.send_email(
                        to_email=assigned_user.email,
                        subject=f"Nuovo Ticket Assegnato #{ticket.ticket_number} - {ticket.urgency_label}",
                        html_content=get_new_ticket_email(ticket, is_requester=False, is_assigned=True)
                    )
            
        except Exception as e:
            current_app.logger.error(f"Errore invio email nuovo ticket: {str(e)}")
    
    def _send_status_change_notifications(
        self,
        ticket: Ticket,
        status_change: TicketStatusChange,
        notify_requester: bool
    ) -> None:
        """Invia notifiche per cambio stato."""
        
        # Import il nuovo servizio email
        from .email_service import send_status_change_notification
        
        emails_sent = []
        
        # Dividi i destinatari in due categorie:
        # - team_recipients: il team che lavora sul ticket (notifica sempre per coordinamento)
        # - requester_recipients: il richiedente (notifica solo se flag attivo)
        
        team_recipients = set()
        requester_recipients = set()
        
        # Team che lavora sul ticket (riceve sempre notifica)
        # 1. Utenti assegnati
        for user in ticket.assigned_users:
            team_recipients.add(user)
        
        # 2. Head del dipartimento (opzionale, solo per ticket importanti)
        # Commentato per ridurre spam: può essere riattivato se necessario
        # if ticket.department and ticket.department.head:
        #     team_recipients.add(ticket.department.head)
        
        # Richiedente (riceve notifica solo se flag attivo)
        if notify_requester:
            # 1. Creatore del ticket (se è un utente del sistema)
            if ticket.created_by:
                requester_recipients.add(ticket.created_by)
        
        # Email esterna del richiedente
        external_requester_email = None
        if notify_requester and ticket.requester_email:
            # Verifica se l'email non corrisponde già a un utente interno
            all_internal_users = team_recipients | requester_recipients
            is_internal = any(u.email == ticket.requester_email for u in all_internal_users)
            if not is_internal:
                external_requester_email = ticket.requester_email
        
        # Unisci tutti i destinatari da notificare
        all_recipients = team_recipients | requester_recipients
        
        # Invia email a tutti i destinatari selezionati
        for recipient in all_recipients:
            try:
                send_status_change_notification(
                    ticket=ticket,
                    recipient=recipient,
                    changed_by=status_change.changed_by,
                    old_status=status_change.from_status,
                    new_status=status_change.to_status,
                    message=status_change.message
                )
                emails_sent.append(recipient.email)
            except Exception as e:
                current_app.logger.error(
                    f"Errore invio email cambio stato a {recipient.email}: {str(e)}"
                )
        
        # Invia email al richiedente esterno se necessario
        if external_requester_email:
            try:
                # Usa il metodo legacy per email esterne
                self.email_service.send_email(
                    to_email=external_requester_email,
                    subject=f"Ticket #{ticket.ticket_number} - Aggiornamento stato",
                    html_content=get_status_change_email(ticket, status_change)
                )
                emails_sent.append(external_requester_email)
            except Exception as e:
                current_app.logger.error(
                    f"Errore invio email a richiedente esterno: {str(e)}"
                )
        
        # Salva email inviate
        if emails_sent:
            status_change.emails_sent_to = emails_sent
            db.session.commit()
    
    def _send_share_notifications(
        self,
        ticket: Ticket,
        departments: List[Department],
        shared_by: User,
        message: Optional[str]
    ) -> None:
        """Invia notifiche per ticket condiviso."""
        
        if not current_app.config.get('TICKET_EMAIL_ENABLED', False):
            return
        
        try:
            for dept in departments:
                if dept.notification_email:
                    self.email_service.send_email(
                        to_email=dept.notification_email,
                        subject=f"Ticket #{ticket.ticket_number} condiviso con il tuo dipartimento",
                        html_content=get_ticket_shared_email(
                            ticket, dept, shared_by, message
                        )
                    )
            
        except Exception as e:
            current_app.logger.error(f"Errore invio email condivisione: {str(e)}")
    
    def send_assignment_notifications(
        self,
        ticket: Ticket,
        assigned_users: List[User],
        assigned_by: User,
        added_users: Optional[List[User]] = None,
        removed_users: Optional[List[User]] = None
    ) -> None:
        """
        Invia notifiche email per assegnazione ticket.
        
        Args:
            ticket: Ticket assegnato
            assigned_users: Lista utenti attualmente assegnati
            assigned_by: Utente che ha effettuato l'assegnazione
            added_users: Utenti aggiunti (per notifica specifica)
            removed_users: Utenti rimossi (per eventuale notifica)
        """
        
        # Import il nuovo servizio email
        from .email_service import send_assignment_notification
        
        # Se non specificati, considera tutti come nuovi
        if added_users is None:
            added_users = assigned_users
        
        # Invia email a ogni utente assegnato
        for user in added_users:
            try:
                send_assignment_notification(ticket, user, assigned_by)
            except Exception as e:
                current_app.logger.error(
                    f"Errore invio email assegnazione a {user.email}: {str(e)}"
                )
        
        # Notifica anche al creatore del ticket se non è tra gli assegnati
        if ticket.created_by and ticket.created_by not in assigned_users:
            try:
                # Usa il servizio centralizzato per email più semplici
                from .email_service import send_ticket_email
                
                assigned_names = [u.full_name for u in assigned_users]
                ticket_url = current_app.config.get('SERVER_NAME', 'localhost')
                if not ticket_url.startswith(('http://', 'https://')):
                    ticket_url = f"https://{ticket_url}"
                ticket_url = f"{ticket_url}/tickets/{ticket.id}"
                
                # Template inline semplice per il creatore
                html_template = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body { font-family: Arial, sans-serif; background-color: #f4f7f5; margin: 0; padding: 20px; }
                        .container { max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; }
                        .header { background-color: #25B36A; padding: 20px; text-align: center; }
                        .content { padding: 30px; }
                        .button { display: inline-block; background-color: #25B36A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <img src="cid:logo" alt="Corposostenibile" style="height: 60px;">
                            <h2 style="color: white; margin: 10px 0;">Aggiornamento Ticket</h2>
                        </div>
                        <div class="content">
                            <p>Ciao {{ created_by.first_name }},</p>
                            <p>Il ticket <strong>#{{ ticket.ticket_number }}</strong> che hai creato è stato assegnato a:</p>
                            <p><strong>{{ assigned_names|join(', ') }}</strong></p>
                            <p>Assegnato da: {{ assigned_by.full_name }}</p>
                            <p><a href="{{ url }}" class="button">Visualizza Ticket</a></p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # Invia usando render_template_string
                html_content = render_template_string(
                    html_template,
                    created_by=ticket.created_by,
                    ticket=ticket,
                    assigned_names=assigned_names,
                    assigned_by=assigned_by,
                    url=ticket_url
                )
                
                msg = Message(
                    subject=f"Ticket #{ticket.ticket_number} - Aggiornamento assegnazione",
                    recipients=[ticket.created_by.email],
                    html=html_content,
                    sender=current_app.config.get('MAIL_DEFAULT_SENDER')
                )
                
                # Logo
                from pathlib import Path
                logo_path = Path(current_app.root_path) / "static" / "assets" / "immagini" / "Suite.png"
                if logo_path.exists():
                    with open(logo_path, 'rb') as f:
                        msg.attach(
                            filename='Suite.png',
                            content_type='image/png',
                            data=f.read(),
                            disposition='inline',
                            headers={'Content-ID': '<logo>'}
                        )
                
                mail.send(msg)
                
            except Exception as e:
                current_app.logger.error(
                    f"Errore invio email al creatore: {str(e)}"
                )
    
    def send_comment_notifications(
        self,
        ticket: Ticket,
        comment: TicketComment,
        author: User
    ) -> None:
        """
        Invia notifiche email per nuovo commento/nota interna.
        
        Args:
            ticket: Ticket commentato
            comment: Commento aggiunto
            author: Autore del commento
        """
        
        # Import il nuovo servizio email
        from .email_service import send_comment_notification
        
        # Raccogli destinatari (escluso l'autore del commento)
        recipients = set()
        
        # Head del dipartimento
        if ticket.department and ticket.department.head:
            if ticket.department.head.id != author.id:
                recipients.add(ticket.department.head)
        
        # Utenti assegnati
        for user in ticket.assigned_users:
            if user.id != author.id:
                recipients.add(user)
        
        # Creatore del ticket
        if ticket.created_by and ticket.created_by.id != author.id:
            recipients.add(ticket.created_by)
        
        # Se l'autore è l'unico interessato, non inviare email
        if not recipients:
            current_app.logger.info(
                f"Nessun destinatario per la nota del ticket #{ticket.ticket_number} (solo l'autore)"
            )
            return
        
        # Invia email a ogni destinatario
        for recipient in recipients:
            try:
                send_comment_notification(ticket, comment, recipient, author)
            except Exception as e:
                current_app.logger.error(
                    f"Errore invio email nota a {recipient.email}: {str(e)}"
                )
    
    def _save_attachment(self, file: FileStorage, ticket_number: str) -> tuple[Optional[str], Optional[str]]:
        """
        Salva un allegato per il ticket.
        
        Args:
            file: File da salvare
            ticket_number: Numero del ticket
            
        Returns:
            Tupla (filename_salvato, path_relativo) o (None, None) in caso di errore
        """
        
        if not file or not file.filename:
            return None, None
        
        try:
            # Estrai l'estensione e crea un nome sicuro
            filename = secure_filename(file.filename)
            if not filename:
                return None, None
            
            # Estrai estensione
            ext = os.path.splitext(filename)[1].lower()
            
            # Verifica che l'estensione sia permessa
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp'}
            if ext not in allowed_extensions:
                current_app.logger.warning(f"Estensione non permessa per l'allegato: {ext}")
                return None, None
            
            # Crea il nome del file con il numero del ticket
            new_filename = f"{ticket_number}_{filename}"
            
            # Percorso della cartella tickets
            tickets_folder = os.path.join(
                current_app.config.get('UPLOAD_FOLDER', 'uploads'),
                'tickets'
            )
            
            # Crea la cartella se non esiste
            os.makedirs(tickets_folder, exist_ok=True)
            
            # Percorso completo del file
            file_path = os.path.join(tickets_folder, new_filename)
            
            # Salva il file
            file.save(file_path)
            
            # Ritorna il nome del file e il percorso relativo
            relative_path = f"tickets/{new_filename}"
            
            current_app.logger.info(f"Allegato salvato: {relative_path}")
            return new_filename, relative_path
            
        except Exception as e:
            current_app.logger.error(f"Errore salvataggio allegato: {str(e)}")
            return None, None


class TicketKPIService:
    """Servizio per calcolo KPI e metriche del sistema ticketing."""
    
    def get_company_kpis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Calcola KPI aziendali globali.
        
        Args:
            start_date: Data inizio periodo (UTC)
            end_date: Data fine periodo (UTC)
            
        Returns:
            Dict con metriche aziendali
        """
        
        # Query base per il periodo
        period_filter = and_(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        )
        
        # Ticket totali nel periodo
        total_tickets = db.session.query(func.count(Ticket.id)).filter(period_filter).scalar() or 0
        
        # Ticket per stato
        status_counts = db.session.query(
            Ticket.status,
            func.count(Ticket.id)
        ).filter(period_filter).group_by(Ticket.status).all()
        
        status_dict = {status.value: count for status, count in status_counts}
        
        # Ticket aperti attualmente (non solo del periodo)
        open_tickets = db.session.query(func.count(Ticket.id)).filter(
            Ticket.status != TicketStatusEnum.chiuso
        ).scalar() or 0
        
        # Tempo medio risoluzione (solo ticket chiusi nel periodo)
        avg_resolution = db.session.query(
            func.avg(
                func.extract('epoch', Ticket.closed_at - Ticket.created_at) / 3600
            )
        ).filter(
            period_filter,
            Ticket.status == TicketStatusEnum.chiuso,
            Ticket.closed_at.isnot(None)
        ).scalar() or 0
        
        # SLA rispettato (ticket chiusi entro la due_date)
        sla_met = db.session.query(func.count(Ticket.id)).filter(
            period_filter,
            Ticket.status == TicketStatusEnum.chiuso,
            Ticket.closed_at <= Ticket.due_date
        ).scalar() or 0
        
        sla_total = status_dict.get('chiuso', 0)
        sla_percentage = (sla_met / sla_total * 100) if sla_total > 0 else 100
        
        # Ticket per urgenza
        urgency_counts = db.session.query(
            Ticket.urgency,
            func.count(Ticket.id)
        ).filter(period_filter).group_by(Ticket.urgency).all()
        
        # Confronto periodo precedente
        prev_period_start = start_date - (end_date - start_date)
        prev_period_end = start_date
        
        prev_total = db.session.query(func.count(Ticket.id)).filter(
            and_(
                Ticket.created_at >= prev_period_start,
                Ticket.created_at < prev_period_end
            )
        ).scalar() or 0
        
        growth_rate = ((total_tickets - prev_total) / prev_total * 100) if prev_total > 0 else 0
        
        # Dipartimento con più ticket
        top_dept = db.session.query(
            Department.name,
            func.count(Ticket.id).label('count')
        ).join(
            Ticket, Ticket.department_id == Department.id
        ).filter(
            period_filter
        ).group_by(Department.id, Department.name).order_by(
            func.count(Ticket.id).desc()
        ).first()
        
        # Utente più produttivo (più ticket chiusi)
        top_user = db.session.query(
            User.first_name,
            User.last_name,
            func.count(Ticket.id).label('count')
        ).join(
            Ticket.assigned_users
        ).join(
            TicketStatusChange,
            and_(
                TicketStatusChange.ticket_id == Ticket.id,
                TicketStatusChange.to_status == TicketStatusEnum.chiuso
            )
        ).filter(
            and_(
                TicketStatusChange.created_at >= start_date,
                TicketStatusChange.created_at <= end_date
            )
        ).group_by(User.id, User.first_name, User.last_name).order_by(
            func.count(Ticket.id).desc()
        ).first()
        
        return {
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'closed_tickets': status_dict.get('chiuso', 0),
            'in_progress_tickets': status_dict.get('in_lavorazione', 0),
            'waiting_tickets': status_dict.get('in_attesa', 0),
            'new_tickets': status_dict.get('nuovo', 0),
            'avg_resolution_hours': round(avg_resolution, 1),
            'sla_percentage': round(sla_percentage, 1),
            'urgency_high': sum(count for urgency, count in urgency_counts if urgency.value == '1'),
            'urgency_medium': sum(count for urgency, count in urgency_counts if urgency.value == '2'),
            'urgency_low': sum(count for urgency, count in urgency_counts if urgency.value == '3'),
            'growth_rate': round(growth_rate, 1),
            'top_department': top_dept[0] if top_dept else 'N/A',
            'top_department_count': top_dept[1] if top_dept else 0,
            'top_user': f"{top_user[0]} {top_user[1]}" if top_user else 'N/A',
            'top_user_count': top_user[2] if top_user else 0,
            'prev_period_total': prev_total
        }
    
    def get_department_kpis(self, department: Department, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Calcola KPI per un singolo dipartimento.
        
        Args:
            department: Dipartimento
            start_date: Data inizio periodo (UTC)
            end_date: Data fine periodo (UTC)
            
        Returns:
            Dict con metriche del dipartimento
        """
        
        # Query base per ticket del dipartimento nel periodo
        dept_filter = and_(
            Ticket.department_id == department.id,
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        )
        
        # Metriche base
        total_received = db.session.query(func.count(Ticket.id)).filter(dept_filter).scalar() or 0
        
        # Per stato
        status_counts = db.session.query(
            Ticket.status,
            func.count(Ticket.id)
        ).filter(dept_filter).group_by(Ticket.status).all()
        
        status_dict = {status.value: count for status, count in status_counts}
        
        # Tempo medio prima presa in carico (da nuovo a in_lavorazione)
        avg_response = db.session.query(
            func.avg(
                func.extract('epoch', TicketStatusChange.created_at - Ticket.created_at) / 3600
            )
        ).join(
            Ticket, TicketStatusChange.ticket_id == Ticket.id
        ).filter(
            dept_filter,
            TicketStatusChange.from_status == TicketStatusEnum.nuovo,
            TicketStatusChange.to_status == TicketStatusEnum.in_lavorazione
        ).scalar() or 0
        
        # Ticket più vecchio ancora aperto
        oldest_open = db.session.query(
            Ticket.ticket_number,
            Ticket.title,
            func.extract('day', func.now() - Ticket.created_at).label('days_old')
        ).filter(
            Ticket.department_id == department.id,
            Ticket.status != TicketStatusEnum.chiuso
        ).order_by(Ticket.created_at).first()
        
        # KPI per membro del team
        members_kpi = []
        for member in department.members:
            if not member.is_active:
                continue
                
            member_kpi = self.get_user_kpis(member, department, start_date, end_date)
            members_kpi.append({
                'user': member,
                'kpis': member_kpi
            })
        
        # Ordina membri per produttività
        members_kpi.sort(key=lambda x: x['kpis']['closed_tickets'], reverse=True)
        
        # Carico di lavoro medio per membro
        active_members = len([m for m in department.members if m.is_active])
        avg_workload = total_received / active_members if active_members > 0 else 0
        
        return {
            'department': department,
            'total_received': total_received,
            'closed': status_dict.get('chiuso', 0),
            'in_progress': status_dict.get('in_lavorazione', 0),
            'waiting': status_dict.get('in_attesa', 0),
            'new': status_dict.get('nuovo', 0),
            'avg_response_hours': round(avg_response, 1),
            'oldest_open': oldest_open,
            'members_kpi': members_kpi,
            'active_members': active_members,
            'avg_workload': round(avg_workload, 1),
            'resolution_rate': round(status_dict.get('chiuso', 0) / total_received * 100, 1) if total_received > 0 else 0
        }
    
    def get_user_kpis(self, user: User, department: Department, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Calcola KPI per un singolo utente in un dipartimento.
        
        Args:
            user: Utente
            department: Dipartimento di riferimento
            start_date: Data inizio periodo (UTC)
            end_date: Data fine periodo (UTC)
            
        Returns:
            Dict con metriche dell'utente
        """
        
        # Ticket assegnati all'utente nel periodo
        assigned_query = db.session.query(Ticket).join(
            Ticket.assigned_users
        ).filter(
            User.id == user.id,
            Ticket.department_id == department.id,
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        )
        
        total_assigned = assigned_query.count()
        
        # Ticket chiusi dall'utente
        closed_tickets = db.session.query(func.count(distinct(Ticket.id))).join(
            TicketStatusChange,
            TicketStatusChange.ticket_id == Ticket.id
        ).filter(
            TicketStatusChange.changed_by_id == user.id,
            TicketStatusChange.to_status == TicketStatusEnum.chiuso,
            TicketStatusChange.created_at >= start_date,
            TicketStatusChange.created_at <= end_date,
            Ticket.department_id == department.id
        ).scalar() or 0
        
        # Ticket attualmente attivi
        active_tickets = assigned_query.filter(
            Ticket.status != TicketStatusEnum.chiuso
        ).count()
        
        # Tempo medio gestione (per ticket chiusi)
        avg_handling = db.session.query(
            func.avg(
                func.extract('epoch', Ticket.closed_at - Ticket.created_at) / 3600
            )
        ).join(
            Ticket.assigned_users
        ).filter(
            User.id == user.id,
            Ticket.department_id == department.id,
            Ticket.status == TicketStatusEnum.chiuso,
            Ticket.closed_at >= start_date,
            Ticket.closed_at <= end_date
        ).scalar() or 0
        
        # SLA rispettato
        sla_met = db.session.query(func.count(Ticket.id)).join(
            Ticket.assigned_users
        ).filter(
            User.id == user.id,
            Ticket.department_id == department.id,
            Ticket.status == TicketStatusEnum.chiuso,
            Ticket.closed_at <= Ticket.due_date,
            Ticket.closed_at >= start_date,
            Ticket.closed_at <= end_date
        ).scalar() or 0
        
        sla_percentage = (sla_met / closed_tickets * 100) if closed_tickets > 0 else 100
        
        return {
            'total_assigned': total_assigned,
            'closed_tickets': closed_tickets,
            'active_tickets': active_tickets,
            'avg_handling_hours': round(avg_handling, 1),
            'sla_percentage': round(sla_percentage, 1),
            'productivity_score': round(closed_tickets / total_assigned * 100, 1) if total_assigned > 0 else 0
        }


class TicketEmailService:
    """Servizio per invio email tramite Flask-Mail."""
    
    @staticmethod
    def init_app(app):
        """Inizializza il servizio email con la configurazione Flask."""
        # Flask-Mail è già inizializzato in extensions.py
        app.logger.info("[TicketEmail] Servizio email inizializzato con Flask-Mail")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        cc: Optional[List[str]] = None
    ) -> bool:
        """
        Invia email tramite Flask-Mail (SMTP Gmail).
        
        Args:
            to_email: Destinatario
            subject: Oggetto
            html_content: Contenuto HTML
            cc: Lista CC opzionale
            
        Returns:
            True se inviata con successo
        """
        
        try:
            # Verifica che il servizio sia abilitato
            if not current_app.config.get('TICKET_EMAIL_ENABLED', False):
                current_app.logger.info(
                    f"[TicketEmail] Email simulata (servizio disabilitato): {subject} a {to_email}"
                )
                return True
            
            # Crea il messaggio
            msg = Message(
                subject=subject,
                recipients=[to_email],
                cc=cc or [],
                html=html_content,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            
            # Aggiungi anche una versione plain text automatica
            # Rimuove i tag HTML per creare una versione testuale
            import re
            from html.parser import HTMLParser
            
            class HTMLTextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.text = []
                
                def handle_data(self, data):
                    self.text.append(data)
                
                def get_text(self):
                    return ''.join(self.text)
            
            parser = HTMLTextExtractor()
            parser.feed(html_content)
            plain_text = parser.get_text()
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()
            msg.body = plain_text
            
            # Invia l'email
            mail.send(msg)
            
            current_app.logger.info(
                f"[TicketEmail] Email inviata con successo: '{subject}' a {to_email}"
            )
            
            return True
                
        except Exception as e:
            current_app.logger.error(
                f"[TicketEmail] Errore invio email '{subject}' a {to_email}: {str(e)}"
            )
            
            # In development, mostra l'errore completo
            if current_app.debug:
                import traceback
                current_app.logger.error(traceback.format_exc())
            
            return False
    
    def send_message_notification(self, ticket, message, recipient):
        """
        Invia una notifica email per un nuovo messaggio nel ticket.
        
        Args:
            ticket: Il ticket
            message: Il messaggio inviato
            recipient: Il destinatario della notifica
        
        Returns:
            bool: True se l'invio ha avuto successo
        """
        subject = f"Nuovo messaggio nel ticket #{ticket.ticket_number}"
        
        # Crea il contenuto testuale dell'email
        from datetime import timedelta
        base_url = current_app.config.get('BASE_URL', 'https://suite.corposostenibile.com')
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h3>Nuovo messaggio nel Ticket #{ticket.ticket_number}</h3>
            
            <p><strong>{message.sender.first_name} {message.sender.last_name}</strong> ha scritto:</p>
            
            <div style="background: #f5f5f5; padding: 15px; border-left: 3px solid #0ea5e9; margin: 20px 0;">
                {message.content.replace(chr(10), '<br>')}
            </div>
            
            <p style="color: #666;">
                Data: {(message.created_at + timedelta(hours=2)).strftime('%d/%m/%Y alle %H:%M')}
            </p>
            
            <hr style="border: 1px solid #e0e0e0;">
            
            <p><strong>Dettagli Ticket:</strong></p>
            <ul>
                <li>Numero: #{ticket.ticket_number}</li>
                <li>Titolo: {ticket.title}</li>
                <li>Urgenza: {ticket.urgency.value}</li>
                <li>Stato: {ticket.status.value}</li>
            </ul>
            
            <p>
                <a href="{base_url}/ticket/{ticket.id}" style="background: #0ea5e9; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Visualizza Ticket e Rispondi
                </a>
            </p>
            
            <p style="color: #999; font-size: 12px; margin-top: 30px;">
                Questa email è stata inviata automaticamente dal sistema di ticketing di Corpo Sostenibile.
            </p>
        </body>
        </html>
        """
        
        # Invia l'email usando il metodo esistente
        try:
            return self.send_email(
                to_email=recipient.email,
                subject=subject,
                html_content=html_content
            )
        except Exception as e:
            current_app.logger.error(f"Errore nell'invio email per ticket message: {e}")
            return False

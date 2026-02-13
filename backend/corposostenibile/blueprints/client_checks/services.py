"""
client_checks.services
======================

Logica di business per il sistema Client Checks:
- CheckFormService: Gestione form template
- ClientCheckService: Gestione assegnazioni e risposte
- NotificationService: Invio notifiche
- ReportService: Generazione report e statistiche
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional

from flask import current_app, has_request_context, request
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import joinedload

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente, User, Department,
    CheckForm,
    CheckFormField,
    ClientCheckAssignment,
    ClientCheckResponse,
    CheckFormTypeEnum,
    CheckFormFieldTypeEnum,
)


# --------------------------------------------------------------------------- #
#  URL Helpers                                                                 #
# --------------------------------------------------------------------------- #
def _public_checks_base_url() -> str:
    """
    Base URL pubblico per i link check condivisi all'esterno.
    Riusa lo stesso helper usato dai weekly check.
    """
    # Import lazy per evitare dipendenze circolari a livello modulo.
    from .routes import _frontend_base_url

    def _fallback_from_base_url() -> str:
        configured = (current_app.config.get("BASE_URL") or "http://localhost:5001").strip().rstrip("/")
        parsed = urlparse(configured)

        if parsed.scheme and parsed.hostname and parsed.port and 5000 <= parsed.port < 5100:
            frontend_origin = f"{parsed.scheme}://{parsed.hostname}:{parsed.port - 2000}"
            with current_app.test_request_context("/", headers={"Origin": frontend_origin}):
                return _frontend_base_url().rstrip("/")

        with current_app.test_request_context("/", base_url=configured):
            return _frontend_base_url().rstrip("/")

    if has_request_context():
        # Stesso comportamento weekly per richieste browser.
        if (request.headers.get("Origin") or "").strip() or (request.headers.get("Referer") or "").strip():
            return _frontend_base_url().rstrip("/")
        # Caso webhook server-to-server (es. GHL): nessun Origin/Referer.
        return _fallback_from_base_url()

    return _fallback_from_base_url()


# --------------------------------------------------------------------------- #
#  CheckFormService - Gestione Form Template                                 #
# --------------------------------------------------------------------------- #

class CheckFormService:
    """Servizio per la gestione dei form template."""
    
    @staticmethod
    def create_form(
        name: str,
        description: str,
        form_type: CheckFormTypeEnum,
        created_by_id: int,
        department_id: Optional[int] = None,
        fields_data: Optional[List[Dict[str, Any]]] = None,
    ) -> CheckForm:
        """Crea un nuovo form con i suoi campi."""
        try:
            # Crea il form
            form = CheckForm(
                name=name,
                description=description,
                form_type=form_type,
                created_by_id=created_by_id,
                department_id=department_id,
                is_active=True,
            )
            
            db.session.add(form)
            db.session.flush()  # Per ottenere l'ID
            
            # Aggiungi i campi se forniti
            if fields_data:
                for position, field_data in enumerate(fields_data, 1):
                    field = CheckFormField(
                        form_id=form.id,
                        label=field_data.get("label", ""),
                        field_type=CheckFormFieldTypeEnum(field_data.get("field_type", "text")),
                        is_required=field_data.get("is_required", False),
                        position=position,
                        options=field_data.get("options"),
                        placeholder=field_data.get("placeholder"),
                        help_text=field_data.get("help_text"),
                    )
                    db.session.add(field)
            
            db.session.commit()
            current_app.logger.info(f"Form creato: {form.name} (ID: {form.id})")
            return form
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore creazione form: {e}")
            raise
    
    @staticmethod
    def update_form(
        form_id: int,
        name: str,
        description: str,
        form_type: CheckFormTypeEnum,
        department_id: Optional[int] = None,
        fields_data: Optional[List[Dict[str, Any]]] = None,
    ) -> CheckForm:
        """Aggiorna un form esistente."""
        try:
            form = CheckForm.query.get_or_404(form_id)
            
            # Aggiorna i dati del form
            form.name = name
            form.description = description
            form.form_type = form_type
            form.department_id = department_id
            
            # Aggiorna i campi se forniti
            if fields_data is not None:
                # Prima valida tutti i dati dei campi
                new_fields = []
                for position, field_data in enumerate(fields_data, 1):
                    # Validazione dei dati del campo
                    if not field_data.get("label", "").strip():
                        raise ValueError(f"Il campo alla posizione {position} deve avere un'etichetta")
                    
                    field_type_str = field_data.get("field_type", "text")
                    try:
                        field_type = CheckFormFieldTypeEnum(field_type_str)
                    except ValueError:
                        raise ValueError(f"Tipo di campo non valido: {field_type_str}")
                    
                    # Prepara il nuovo campo
                    field = CheckFormField(
                        form_id=form.id,
                        label=field_data.get("label", "").strip(),
                        field_type=field_type,
                        is_required=field_data.get("is_required", False),
                        position=position,
                        options=field_data.get("options"),
                        placeholder=field_data.get("placeholder"),
                        help_text=field_data.get("help_text"),
                    )
                    new_fields.append(field)
                
                # Solo dopo aver validato tutto, procedi con l'aggiornamento
                # Rimuovi i campi esistenti
                existing_fields = CheckFormField.query.filter_by(form_id=form_id).all()
                for existing_field in existing_fields:
                    db.session.delete(existing_field)
                
                # Flush per applicare le eliminazioni prima di aggiungere i nuovi
                db.session.flush()
                
                # Aggiungi i nuovi campi
                for field in new_fields:
                    db.session.add(field)
            
            # Commit finale
            db.session.commit()
            current_app.logger.info(f"Form aggiornato: {form.name} (ID: {form.id})")
            return form
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore aggiornamento form {form_id}: {str(e)}")
            raise
    
    @staticmethod
    def delete_form(form_id: int) -> bool:
        """Elimina un form (soft delete)."""
        try:
            form = CheckForm.query.get_or_404(form_id)
            form.is_active = False
            
            # Disattiva anche le assegnazioni attive
            ClientCheckAssignment.query.filter_by(
                form_id=form_id,
                is_active=True
            ).update({"is_active": False})
            
            db.session.commit()
            current_app.logger.info(f"Form eliminato: {form.name} (ID: {form.id})")
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore eliminazione form: {e}")
            raise
    
    @staticmethod
    def duplicate_form(form_id: int, new_name: str, created_by_id: int) -> CheckForm:
        """Duplica un form esistente."""
        try:
            original_form = (
                CheckForm.query
                .options(joinedload(CheckForm.fields))
                .get_or_404(form_id)
            )
            
            # Crea il nuovo form
            new_form = CheckForm(
                name=new_name,
                description=f"Copia di: {original_form.description}",
                form_type=original_form.form_type,
                created_by_id=created_by_id,
                department_id=original_form.department_id,
                is_active=True,
            )
            
            db.session.add(new_form)
            db.session.flush()
            
            # Duplica i campi
            for field in original_form.fields:
                new_field = CheckFormField(
                    form_id=new_form.id,
                    label=field.label,
                    field_type=field.field_type,
                    is_required=field.is_required,
                    position=field.position,
                    options=field.options,
                    placeholder=field.placeholder,
                    help_text=field.help_text,
                )
                db.session.add(new_field)
            
            db.session.commit()
            current_app.logger.info(f"Form duplicato: {new_form.name} (ID: {new_form.id})")
            return new_form
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore duplicazione form: {e}")
            raise


# --------------------------------------------------------------------------- #
#  ClientCheckService - Gestione Assegnazioni e Risposte                    #
# --------------------------------------------------------------------------- #

class ClientCheckService:
    """Servizio per la gestione delle assegnazioni e risposte."""
    
    @staticmethod
    def assign_form_to_clients(
        form_id: int,
        client_ids: List[int],
        assigned_by_id: int,
        send_notifications: bool = True,
    ) -> List[ClientCheckAssignment]:
        """Assegna un form a una lista di clienti."""
        try:
            assignments = []
            
            for client_id in client_ids:
                # Verifica se esiste già un'assegnazione attiva
                existing = ClientCheckAssignment.query.filter_by(
                    cliente_id=client_id,
                    form_id=form_id,
                    is_active=True
                ).first()
                
                if existing:
                    current_app.logger.warning(
                        f"Assegnazione già esistente: Cliente {client_id}, Form {form_id}"
                    )
                    continue
                
                # Crea nuova assegnazione
                assignment = ClientCheckAssignment(
                    cliente_id=client_id,
                    form_id=form_id,
                    token=ClientCheckAssignment.generate_token(),
                    assigned_by_id=assigned_by_id,
                    is_active=True,
                )
                
                db.session.add(assignment)
                assignments.append(assignment)
            
            db.session.commit()
            
            # Invia notifiche se richiesto
            if send_notifications and assignments:
                NotificationService.send_assignment_notifications(assignments)
            
            current_app.logger.info(
                f"Form {form_id} assegnato a {len(assignments)} clienti"
            )
            return assignments
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore assegnazione form: {e}")
            raise
    
    @staticmethod
    def assign_form_to_client(
        form_id: int,
        client_id: int,
        assigned_by_id: int,
        send_notification: bool = True,
    ) -> ClientCheckAssignment:
        """Assegna un form a un singolo cliente."""
        assignments = ClientCheckService.assign_form_to_clients(
            form_id=form_id,
            client_ids=[client_id],
            assigned_by_id=assigned_by_id,
            send_notifications=send_notification,
        )
        return assignments[0] if assignments else None
    
    @staticmethod
    def save_response(
        assignment_id: int,
        form_data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ClientCheckResponse:
        """Salva una risposta compilata."""
        try:
            assignment = ClientCheckAssignment.query.get_or_404(assignment_id)
            
            # Verifica che l'assegnazione sia attiva
            if not assignment.is_active:
                raise ValueError("Assegnazione non attiva")
            
            # Prepara i dati della risposta (rimuovi campi non necessari)
            response_data = {}
            for field in assignment.form.fields:
                field_key = f"field_{field.id}"
                if field_key in form_data:
                    response_data[str(field.id)] = form_data[field_key]
            
            # Crea la risposta
            response = ClientCheckResponse(
                assignment_id=assignment_id,
                responses=response_data,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            
            db.session.add(response)
            
            # Aggiorna le statistiche dell'assegnazione
            assignment.response_count += 1
            assignment.last_response_at = datetime.utcnow()
            
            db.session.commit()
            
            current_app.logger.info(
                f"Risposta salvata: Assignment {assignment_id}, Cliente {assignment.cliente_id}"
            )
            return response
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore salvataggio risposta: {e}")
            raise
    
    @staticmethod
    def get_client_assignments(
        client_id: int,
        form_type: Optional[CheckFormTypeEnum] = None,
        active_only: bool = True,
    ) -> List[ClientCheckAssignment]:
        """Ottiene le assegnazioni di un cliente."""
        query = (
            ClientCheckAssignment.query
            .options(
                joinedload(ClientCheckAssignment.form),
                joinedload(ClientCheckAssignment.responses)
            )
            .filter_by(cliente_id=client_id)
        )
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        if form_type:
            query = query.join(CheckForm).filter(CheckForm.form_type == form_type)
        
        return query.order_by(desc(ClientCheckAssignment.created_at)).all()
    
    @staticmethod
    def get_form_statistics(form_id: int) -> Dict[str, Any]:
        """Ottiene statistiche per un form specifico."""
        form = CheckForm.query.get_or_404(form_id)
        
        # Statistiche base
        total_assignments = ClientCheckAssignment.query.filter_by(
            form_id=form_id,
            is_active=True
        ).count()
        
        total_responses = (
            db.session.query(func.sum(ClientCheckAssignment.response_count))
            .filter_by(form_id=form_id, is_active=True)
            .scalar() or 0
        )
        
        # Clienti che hanno risposto
        clients_responded = (
            ClientCheckAssignment.query
            .filter_by(form_id=form_id, is_active=True)
            .filter(ClientCheckAssignment.response_count > 0)
            .count()
        )
        
        # Tasso di risposta
        response_rate = (clients_responded / total_assignments * 100) if total_assignments > 0 else 0
        
        # Risposte per giorno (ultimi 30 giorni)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        daily_responses = (
            db.session.query(
                func.date(ClientCheckResponse.created_at).label('date'),
                func.count(ClientCheckResponse.id).label('count')
            )
            .join(ClientCheckAssignment)
            .filter(
                ClientCheckAssignment.form_id == form_id,
                ClientCheckResponse.created_at >= thirty_days_ago
            )
            .group_by(func.date(ClientCheckResponse.created_at))
            .order_by('date')
            .all()
        )
        
        return {
            "form": form,
            "total_assignments": total_assignments,
            "total_responses": total_responses,
            "clients_responded": clients_responded,
            "response_rate": round(response_rate, 2),
            "daily_responses": [
                {"date": str(row.date), "count": row.count}
                for row in daily_responses
            ],
        }


# --------------------------------------------------------------------------- #
#  NotificationService - Invio Notifiche                                     #
# --------------------------------------------------------------------------- #

class NotificationService:
    """Servizio per l'invio di notifiche."""
    
    @staticmethod
    def send_assignment_notifications(assignments: List[ClientCheckAssignment]) -> None:
        """Invia notifiche di assegnazione ai clienti."""
        try:
            for assignment in assignments:
                NotificationService._send_assignment_email(assignment)
            
            current_app.logger.info(f"Notifiche inviate per {len(assignments)} assegnazioni")
            
        except Exception as e:
            current_app.logger.error(f"Errore invio notifiche assegnazione: {e}")
    
    @staticmethod
    def send_response_notifications(response: ClientCheckResponse) -> None:
        """Invia notifiche quando viene ricevuta una risposta."""
        try:
            if response.notifications_sent:
                return
            
            # Notifica al team del dipartimento
            if response.assignment.form.department:
                NotificationService._send_response_team_notification(response)
            
            # Notifica all'assegnatore
            NotificationService._send_response_assignor_notification(response)
            
            # Marca le notifiche come inviate
            response.mark_notifications_sent()
            db.session.commit()
            
            current_app.logger.info(f"Notifiche risposta inviate per Response {response.id}")
            
        except Exception as e:
            current_app.logger.error(f"Errore invio notifiche risposta: {e}")
    
    @staticmethod
    def _send_assignment_email(assignment: ClientCheckAssignment) -> None:
        """Invia email di assegnazione a un cliente."""
        from flask import render_template
        from corposostenibile.blueprints.auth.email_utils import send_mail_html

        try:
            recipient = getattr(assignment.cliente, "mail", None) or getattr(
                assignment.cliente, "email", None
            )
            if not recipient or not str(recipient).strip():
                current_app.logger.warning(
                    f"Cliente {assignment.cliente_id} senza email"
                )
                return

            # Genera URL pubblico
            base_url = _public_checks_base_url()
            public_url = assignment.get_public_url(base_url=base_url)

            context = {
                "cliente": assignment.cliente,
                "form": assignment.form,
                "assignment": assignment,
                "public_url": public_url,
            }

            subject = f"Nuovo questionario: {assignment.form.name}"
            html_body = render_template(
                "client_checks/emails/assignment.html",
                **context
            )
            text_body = (
                f"Ciao {assignment.cliente.nome_cognome},\n\n"
                f"Ti è stato assegnato il questionario: {assignment.form.name}\n\n"
                f"COMPILA QUI: {public_url}\n\n"
                "— Corpo Sostenibile Suite"
            )

            send_mail_html(
                subject=subject,
                recipients=[recipient],
                text_body=text_body,
                html_body=html_body,
            )

            current_app.logger.info(
                f"Email assegnazione inviata a {recipient}"
            )

        except Exception as e:
            current_app.logger.error(f"Errore invio email assegnazione: {e}")
    
    @staticmethod
    def _send_response_team_notification(response: ClientCheckResponse) -> None:
        """Invia notifica al team quando viene ricevuta una risposta."""
        try:
            department = response.assignment.form.department
            if not department:
                return
            
            # Ottieni utenti del dipartimento
            team_users = User.query.filter_by(
                department_id=department.id,
                is_active=True
            ).all()
            
            for user in team_users:
                if not user.email:
                    continue
                
                email_data = {
                    "to": user.email,
                    "subject": f"Nuova risposta: {response.assignment.form.name}",
                    "template": "client_checks/emails/response_team.html",
                    "context": {
                        "user": user,
                        "response": response,
                        "cliente": response.cliente,
                        "form": response.form,
                    },
                }
                
                # send_email(**email_data)
            
            current_app.logger.info(
                f"Notifiche team inviate per Response {response.id}"
            )
            
        except Exception as e:
            current_app.logger.error(f"Errore notifica team: {e}")
    
    @staticmethod
    def _send_response_assignor_notification(response: ClientCheckResponse) -> None:
        """Invia notifica all'utente che ha assegnato il form."""
        try:
            assignor = response.assignment.assigned_by
            if not assignor or not assignor.email:
                return
            
            email_data = {
                "to": assignor.email,
                "subject": f"Risposta ricevuta: {response.assignment.form.name}",
                "template": "client_checks/emails/response_assignor.html",
                "context": {
                    "assignor": assignor,
                    "response": response,
                    "cliente": response.cliente,
                    "form": response.form,
                },
            }
            
            # send_email(**email_data)
            
            current_app.logger.info(
                f"Notifica assignor inviata per Response {response.id}"
            )
            
        except Exception as e:
            current_app.logger.error(f"Errore notifica assignor: {e}")

    @staticmethod
    def send_check_notification_to_professionals(cliente, check_type: str, check_id: int) -> None:
        """
        Invia email ai professionisti associati quando un cliente compila un check.

        Args:
            cliente: Oggetto Cliente
            check_type: Tipo di check ('weekly', 'dca' o 'minor')
            check_id: ID del check compilato
        """
        from corposostenibile.blueprints.auth.email_utils import send_mail

        try:
            # Raccogli tutti i professionisti associati al cliente
            professionals = []

            # Professionisti multipli
            if cliente.nutrizionisti_multipli:
                professionals.extend(cliente.nutrizionisti_multipli)
            if cliente.psicologi_multipli:
                professionals.extend(cliente.psicologi_multipli)
            if cliente.coaches_multipli:
                professionals.extend(cliente.coaches_multipli)

            # Professionisti singoli (se non già nella lista)
            if cliente.nutrizionista_user and cliente.nutrizionista_user not in professionals:
                professionals.append(cliente.nutrizionista_user)
            if cliente.psicologa_user and cliente.psicologa_user not in professionals:
                professionals.append(cliente.psicologa_user)
            if cliente.coach_user and cliente.coach_user not in professionals:
                professionals.append(cliente.coach_user)

            # Filtra solo professionisti con email
            professionals_with_email = [p for p in professionals if p and p.email]

            if not professionals_with_email:
                current_app.logger.info(
                    f"Nessun professionista con email associato al cliente {cliente.nome_cognome}"
                )
                return

            # Prepara il messaggio
            if check_type == 'weekly':
                check_type_label = "Weekly Check"
            elif check_type == 'dca':
                check_type_label = "Check DCA"
            elif check_type == 'minor':
                check_type_label = "Check Minori"
            else:
                check_type_label = "Check"
            subject = f"Nuovo {check_type_label} compilato da {cliente.nome_cognome}"

            body = f"""Ciao,

il cliente {cliente.nome_cognome} ha appena compilato un {check_type_label}.

Questo è un messaggio automatico. Non rispondere a questa email.

---
Corpo Sostenibile Suite
"""

            # Invia email a tutti i professionisti
            for professional in professionals_with_email:
                try:
                    send_mail(
                        subject=subject,
                        recipients=[professional.email],
                        body=body
                    )
                    current_app.logger.info(
                        f"Email inviata a {professional.full_name} ({professional.email}) "
                        f"per {check_type_label} del cliente {cliente.nome_cognome}"
                    )
                except Exception as e:
                    current_app.logger.error(
                        f"Errore invio email a {professional.email}: {e}"
                    )

            current_app.logger.info(
                f"Notifiche {check_type_label} inviate a {len(professionals_with_email)} professionisti "
                f"per il cliente {cliente.nome_cognome}"
            )

        except Exception as e:
            current_app.logger.error(
                f"Errore invio notifiche check al team professionale: {e}",
                exc_info=True
            )


def send_initial_checks_single_email(
    cliente: Cliente,
    assignments: List[ClientCheckAssignment],
) -> None:
    """
    Invia una sola email al cliente con i link ai tre questionari iniziali.

    Usato dal bridge opportunity-data quando GHL invia lead vinta.
    """
    from flask import render_template
    from corposostenibile.blueprints.auth.email_utils import send_mail_html

    recipient = getattr(cliente, "mail", None) or getattr(cliente, "email", None)
    if not recipient or not str(recipient).strip():
        current_app.logger.warning(f"Cliente {cliente.cliente_id} senza email, skip invio")
        return

    base_url = _public_checks_base_url()
    items = [
        {"form": a.form, "public_url": a.get_public_url(base_url=base_url)}
        for a in assignments
    ]

    context = {"cliente": cliente, "assignments": items}
    subject = "I tuoi questionari iniziali"
    html_body = render_template(
        "client_checks/emails/assignment_initial_checks.html",
        **context,
    )
    text_lines = [
        f"Ciao {cliente.nome_cognome},",
        "",
        "Benvenuto! Per avviare il tuo percorso ti chiediamo di compilare i tre questionari iniziali:",
        "",
    ]
    for a in assignments:
        url = a.get_public_url(base_url=base_url)
        text_lines.append(f"- {a.form.name}: {url}")
    text_lines.extend(["", "— Corpo Sostenibile Suite"])
    text_body = "\n".join(text_lines)

    send_mail_html(
        subject=subject,
        recipients=[recipient],
        text_body=text_body,
        html_body=html_body,
    )

    current_app.logger.info(
        f"Email questionari iniziali inviata a {recipient} ({len(assignments)} link)"
    )


# --------------------------------------------------------------------------- #
#  ReportService - Generazione Report                                        #
# --------------------------------------------------------------------------- #

class ReportService:
    """Servizio per la generazione di report e statistiche."""
    
    @staticmethod
    def generate_form_report(
        form_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Genera report completo per un form."""
        form = CheckForm.query.get_or_404(form_id)
        
        # Query base per le risposte
        query = (
            ClientCheckResponse.query
            .join(ClientCheckAssignment)
            .filter(ClientCheckAssignment.form_id == form_id)
        )
        
        if date_from:
            query = query.filter(ClientCheckResponse.created_at >= date_from)
        if date_to:
            query = query.filter(ClientCheckResponse.created_at <= date_to)
        
        responses = query.all()
        
        # Analisi per campo
        field_analysis = {}
        for field in form.fields:
            field_responses = []
            for response in responses:
                value = response.get_response_value(field.id)
                if value is not None:
                    field_responses.append(value)
            
            field_analysis[field.id] = {
                "field": field,
                "total_responses": len(field_responses),
                "response_rate": len(field_responses) / len(responses) * 100 if responses else 0,
                "values": field_responses,
                "analysis": ReportService._analyze_field_responses(field, field_responses),
            }
        
        return {
            "form": form,
            "period": {
                "from": date_from,
                "to": date_to,
            },
            "summary": {
                "total_responses": len(responses),
                "unique_clients": len(set(r.assignment.cliente_id for r in responses)),
                "avg_responses_per_client": len(responses) / len(set(r.assignment.cliente_id for r in responses)) if responses else 0,
            },
            "field_analysis": field_analysis,
            "responses": responses,
        }
    
    @staticmethod
    def _analyze_field_responses(field: CheckFormField, values: List[Any]) -> Dict[str, Any]:
        """Analizza le risposte per un campo specifico."""
        if not values:
            return {"type": "empty"}
        
        if field.field_type in ["text", "textarea", "email"]:
            return {
                "type": "text",
                "avg_length": sum(len(str(v)) for v in values) / len(values),
                "samples": values[:5],  # Prime 5 risposte come esempio
            }
        
        elif field.field_type in ["number", "scale"]:
            numeric_values = [float(v) for v in values if str(v).replace(".", "").isdigit()]
            if numeric_values:
                return {
                    "type": "numeric",
                    "min": min(numeric_values),
                    "max": max(numeric_values),
                    "avg": sum(numeric_values) / len(numeric_values),
                    "count": len(numeric_values),
                }
        
        elif field.field_type in ["select", "radio"]:
            from collections import Counter
            counter = Counter(values)
            return {
                "type": "categorical",
                "distribution": dict(counter),
                "most_common": counter.most_common(5),
            }
        
        elif field.field_type == "checkbox":
            # Per checkbox, i valori potrebbero essere liste
            all_options = []
            for value in values:
                if isinstance(value, list):
                    all_options.extend(value)
                else:
                    all_options.append(value)
            
            from collections import Counter
            counter = Counter(all_options)
            return {
                "type": "multiple_choice",
                "distribution": dict(counter),
                "most_common": counter.most_common(5),
            }
        
        return {"type": "unknown", "sample_values": values[:5]}
    
    @staticmethod
    def generate_client_report(client_id: int) -> Dict[str, Any]:
        """Genera report per un cliente specifico."""
        cliente = Cliente.query.get_or_404(client_id)
        
        assignments = (
            ClientCheckAssignment.query
            .options(
                joinedload(ClientCheckAssignment.form),
                joinedload(ClientCheckAssignment.responses)
            )
            .filter_by(cliente_id=client_id)
            .order_by(desc(ClientCheckAssignment.created_at))
            .all()
        )
        
        # Statistiche generali
        total_assignments = len(assignments)
        total_responses = sum(a.response_count for a in assignments)
        forms_completed = len([a for a in assignments if a.response_count > 0])
        
        # Cronologia risposte
        all_responses = []
        for assignment in assignments:
            all_responses.extend(assignment.responses)
        
        all_responses.sort(key=lambda r: r.created_at, reverse=True)
        
        return {
            "cliente": cliente,
            "summary": {
                "total_assignments": total_assignments,
                "total_responses": total_responses,
                "forms_completed": forms_completed,
                "completion_rate": forms_completed / total_assignments * 100 if total_assignments > 0 else 0,
            },
            "assignments": assignments,
            "recent_responses": all_responses[:10],
            "response_timeline": [
                {
                    "date": r.created_at.date(),
                    "form_name": r.assignment.form.name,
                    "form_type": r.assignment.form.form_type.value,
                }
                for r in all_responses
            ],
        }

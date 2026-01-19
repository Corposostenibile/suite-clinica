"""
leave_notifications.py
======================

Gestione notifiche email per il sistema ferie/permessi.
Supporta workflow two-tier:
- Prima approvazione: Team Leader / Resp. Dipartimento / CCO / CEO
- Seconda approvazione: HR
"""

from typing import List, Optional
from flask import current_app, url_for
from corposostenibile.blueprints.auth.email_utils import send_mail
from corposostenibile.models import User, LeaveRequest, LeaveTypeEnum, LeaveStatusEnum, Department


class LeaveNotificationService:
    """Servizio per l'invio di notifiche email relative a ferie/permessi."""

    # Mappa tipi assenza
    LEAVE_TYPE_MAP = {
        LeaveTypeEnum.ferie: "Ferie",
        LeaveTypeEnum.permesso: "Permesso",
        LeaveTypeEnum.malattia: "Malattia"
    }

    @staticmethod
    def send_request_notification(leave_request: LeaveRequest) -> None:
        """
        Invia notifica quando viene creata una nuova richiesta.
        Destinatario dipende dallo stato:
        - pending_first_approval → first_approver
        - pending_hr → HR
        - richiesta (legacy) → admin
        """
        try:
            recipient_emails = []
            recipient_name = "Responsabile"
            user = leave_request.user
            leave_type = LeaveNotificationService.LEAVE_TYPE_MAP.get(leave_request.leave_type, 'assenza')

            # Determina destinatari in base allo stato
            if leave_request.status == LeaveStatusEnum.pending_first_approval:
                # Notifica al primo approvatore designato
                if leave_request.first_approver:
                    recipient_emails = [leave_request.first_approver.email]
                    recipient_name = leave_request.first_approver.full_name
                else:
                    current_app.logger.warning(
                        f"Richiesta {leave_request.id} pending_first_approval senza first_approver"
                    )
                    return

            elif leave_request.status == LeaveStatusEnum.pending_hr:
                # Notifica HR
                hr_dept = Department.query.filter_by(name='HR').first()
                if hr_dept and hr_dept.members:
                    recipient_emails = [m.email for m in hr_dept.members if m.is_active]
                    recipient_name = "Team HR"
                else:
                    current_app.logger.warning("Dipartimento HR non trovato o senza membri")
                    return

            else:  # Legacy "richiesta"
                # Notifica tutti gli admin
                admins = User.query.filter_by(is_admin=True, is_active=True).all()
                if not admins:
                    current_app.logger.warning("Nessun admin attivo trovato per notifica richiesta ferie")
                    return
                recipient_emails = [admin.email for admin in admins]
                recipient_name = "Amministratori"

            if not recipient_emails:
                current_app.logger.warning(f"Nessun destinatario trovato per richiesta {leave_request.id}")
                return

            subject = f"Nuova richiesta {leave_type} - {user.full_name}"

            body = f"""
Ciao {recipient_name},

Nuova richiesta di {leave_type.lower()} da approvare.

Dettagli richiesta:
-------------------
Dipendente: {user.full_name}
Dipartimento: {user.department.name if user.department else 'N/D'}
Tipo: {leave_type}
Periodo: dal {leave_request.start_date.strftime('%d/%m/%Y')} al {leave_request.end_date.strftime('%d/%m/%Y')}
{'Giorni: ' + str(leave_request.working_days) if leave_request.leave_type != LeaveTypeEnum.permesso else 'Ore: ' + str(leave_request.hours)}

{('Note: ' + leave_request.notes) if leave_request.notes else ''}

Per approvare o rifiutare questa richiesta:
{url_for('team.leave_approvals', _external=True)}

---
Questo è un messaggio automatico dal sistema HR di Corposostenibile.
"""

            send_mail(subject, recipient_emails, body)

        except Exception as e:
            current_app.logger.error(f"Errore invio notifica richiesta ferie: {str(e)}")

    @staticmethod
    def send_first_approval_notification(leave_request: LeaveRequest) -> None:
        """Notifica al dipendente che la prima fase è stata approvata."""
        try:
            user = leave_request.user
            leave_type = LeaveNotificationService.LEAVE_TYPE_MAP.get(leave_request.leave_type, 'assenza')

            approver_name = "Il tuo responsabile"
            if leave_request.first_approver:
                approver_name = leave_request.first_approver.full_name

            subject = f"Richiesta {leave_type} - Approvata dal responsabile"

            body = f"""
Ciao {user.first_name},

La tua richiesta di {leave_type.lower()} è stata APPROVATA dal tuo responsabile.

Dettagli:
---------
Periodo: dal {leave_request.start_date.strftime('%d/%m/%Y')} al {leave_request.end_date.strftime('%d/%m/%Y')}
{'Giorni: ' + str(leave_request.working_days) if leave_request.leave_type != LeaveTypeEnum.permesso else 'Ore: ' + str(leave_request.hours)}

Approvata da: {approver_name}
Data approvazione: {leave_request.first_approved_at.strftime('%d/%m/%Y %H:%M') if leave_request.first_approved_at else 'N/D'}

La richiesta è stata inoltrata a HR per l'approvazione finale.
Riceverai una nuova notifica quando HR avrà completato la verifica.

Puoi visualizzare lo stato nel tuo profilo:
{url_for('team.my_leaves', _external=True)}

---
Il Team HR di Corposostenibile
"""

            send_mail(subject, [user.email], body)

        except Exception as e:
            current_app.logger.error(f"Errore invio notifica prima approvazione: {str(e)}")

    @staticmethod
    def send_hr_pending_notification(leave_request: LeaveRequest) -> None:
        """Notifica a HR che una richiesta è pronta per l'approvazione finale."""
        try:
            hr_dept = Department.query.filter_by(name='HR').first()
            if not hr_dept or not hr_dept.members:
                current_app.logger.warning("Dipartimento HR non trovato o senza membri")
                return

            hr_emails = [m.email for m in hr_dept.members if m.is_active]
            if not hr_emails:
                current_app.logger.warning("Nessun membro HR attivo trovato")
                return

            user = leave_request.user
            leave_type = LeaveNotificationService.LEAVE_TYPE_MAP.get(leave_request.leave_type, 'assenza')

            approver_name = "Responsabile"
            if leave_request.first_approver:
                approver_name = leave_request.first_approver.full_name

            subject = f"Richiesta {leave_type} pronta per approvazione HR - {user.full_name}"

            body = f"""
Ciao Team HR,

Una richiesta di {leave_type.lower()} è stata approvata dal responsabile ed è pronta per la vostra approvazione finale.

Dettagli richiesta:
-------------------
Dipendente: {user.full_name}
Dipartimento: {user.department.name if user.department else 'N/D'}
Tipo: {leave_type}
Periodo: dal {leave_request.start_date.strftime('%d/%m/%Y')} al {leave_request.end_date.strftime('%d/%m/%Y')}
{'Giorni: ' + str(leave_request.working_days) if leave_request.leave_type != LeaveTypeEnum.permesso else 'Ore: ' + str(leave_request.hours)}

Prima approvazione:
- Approvata da: {approver_name}
- Data: {leave_request.first_approved_at.strftime('%d/%m/%Y %H:%M') if leave_request.first_approved_at else 'N/D'}

Per approvare o rifiutare:
{url_for('team.leave_approvals', _external=True)}

---
Questo è un messaggio automatico dal sistema HR di Corposostenibile.
"""

            send_mail(subject, hr_emails, body)

        except Exception as e:
            current_app.logger.error(f"Errore invio notifica HR pending: {str(e)}")

    @staticmethod
    def send_approval_notification(leave_request: LeaveRequest) -> None:
        """Invia notifica al dipendente quando la richiesta viene approvata."""
        try:
            user = leave_request.user
            leave_type = LeaveNotificationService.LEAVE_TYPE_MAP.get(leave_request.leave_type, 'assenza')

            subject = f"Richiesta {leave_type} APPROVATA"

            # Dettagli approvatore
            approver_name = "Il tuo responsabile"
            if leave_request.approved_by:
                approver_name = leave_request.approved_by.full_name
            elif leave_request.first_approver:
                approver_name = leave_request.first_approver.full_name

            body = f"""
Ciao {user.first_name},

La tua richiesta di {leave_type.lower()} è stata APPROVATA!

Dettagli:
---------
Periodo: dal {leave_request.start_date.strftime('%d/%m/%Y')} al {leave_request.end_date.strftime('%d/%m/%Y')}
{'Giorni: ' + str(leave_request.working_days) if leave_request.leave_type != LeaveTypeEnum.permesso else 'Ore: ' + str(leave_request.hours)}

Approvata da: {approver_name}

Puoi visualizzare tutte le tue richieste nel tuo profilo:
{url_for('team.my_leaves', _external=True)}

Buone ferie!

---
Il Team di Corposostenibile
"""

            send_mail(subject, [user.email], body)

        except Exception as e:
            current_app.logger.error(f"Errore invio notifica approvazione: {str(e)}")

    @staticmethod
    def send_rejection_notification(leave_request: LeaveRequest) -> None:
        """Invia notifica al dipendente quando la richiesta viene rifiutata."""
        try:
            user = leave_request.user
            leave_type = LeaveNotificationService.LEAVE_TYPE_MAP.get(leave_request.leave_type, 'assenza')

            subject = f"Richiesta {leave_type} RIFIUTATA"

            body = f"""
Ciao {user.first_name},

Purtroppo la tua richiesta di {leave_type.lower()} è stata RIFIUTATA.

Dettagli:
---------
Periodo richiesto: dal {leave_request.start_date.strftime('%d/%m/%Y')} al {leave_request.end_date.strftime('%d/%m/%Y')}
{'Giorni: ' + str(leave_request.working_days) if leave_request.leave_type != LeaveTypeEnum.permesso else 'Ore: ' + str(leave_request.hours)}

Rifiutata da: {leave_request.approved_by.full_name if leave_request.approved_by else 'Responsabile'}
Motivazione: {leave_request.rejection_reason or 'Non specificata'}

Per maggiori informazioni, ti preghiamo di contattare il tuo responsabile o l'ufficio HR.

Puoi visualizzare tutte le tue richieste e fare una nuova richiesta dal tuo profilo:
{url_for('team.my_leaves', _external=True)}

---
Il Team HR di Corposostenibile
"""

            send_mail(subject, [user.email], body)

        except Exception as e:
            current_app.logger.error(f"Errore invio notifica rifiuto: {str(e)}")

    @staticmethod
    def send_balance_reminder(user: User, balance: dict) -> None:
        """Invia promemoria sul saldo ferie/permessi (opzionale, per reminder periodici)."""
        try:
            subject = "Riepilogo saldo ferie e permessi"

            reminder_text = ""
            if balance['leave_days_available'] > 10:
                reminder_text = f"\nATTENZIONE: Hai ancora {balance['leave_days_available']} giorni di ferie da utilizzare entro la fine dell'anno!\n"

            body = f"""
Ciao {user.first_name},

Ecco il tuo saldo ferie e permessi aggiornato:

FERIE
-----
Giorni disponibili: {balance['leave_days_available']} su {balance['leave_days_total']}
Giorni utilizzati: {balance['leave_days_used']}

PERMESSI (ROL)
--------------
Ore disponibili: {balance['permission_hours_available']} su {balance['permission_hours_total']}
Ore utilizzate: {balance['permission_hours_used']}
{reminder_text}
Per richiedere ferie o permessi, accedi al tuo profilo:
{url_for('team.leave_request', _external=True)}

---
Il Team HR di Corposostenibile
"""

            send_mail(subject, [user.email], body)

        except Exception as e:
            current_app.logger.error(f"Errore invio reminder saldo: {str(e)}")

"""
Sistema di notifiche per cambi di stato clienti.
"""
from flask import current_app
from flask_mail import Message
from corposostenibile.extensions import mail
from corposostenibile.models import Cliente, User, db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def notify_service_ghost(cliente: Cliente, servizio_ghost: str):
    """
    Notifica gli ALTRI professionisti quando un servizio specifico va in ghost.
    
    Args:
        cliente: Il cliente interessato
        servizio_ghost: Il servizio che è andato in ghost (nutrizione, coach, psicologia)
    """
    try:
        # Determina chi ha messo in ghost
        chi_ha_messo_ghost = None
        if servizio_ghost == 'nutrizione':
            chi_ha_messo_ghost = "Il Nutrizionista"
        elif servizio_ghost == 'coach':
            chi_ha_messo_ghost = "Il Coach"
        elif servizio_ghost == 'psicologia':
            chi_ha_messo_ghost = "Lo Psicologo"
        
        # Raccogli i professionisti da notificare (ESCLUSO chi ha messo in ghost)
        professionisti_da_notificare = []
        
        # Se NON è il nutrizionista che ha messo in ghost, notifica i nutrizionisti
        if servizio_ghost != 'nutrizione':
            for nutrizionista in cliente.nutrizionisti_multipli:
                if nutrizionista.email and nutrizionista.is_active:
                    professionisti_da_notificare.append({
                        'email': nutrizionista.email,
                        'nome': f"{nutrizionista.first_name} {nutrizionista.last_name}",
                        'ruolo': 'Nutrizionista'
                    })
        
        # Se NON è il coach che ha messo in ghost, notifica i coach
        if servizio_ghost != 'coach':
            for coach in cliente.coaches_multipli:
                if coach.email and coach.is_active:
                    professionisti_da_notificare.append({
                        'email': coach.email,
                        'nome': f"{coach.first_name} {coach.last_name}",
                        'ruolo': 'Coach'
                    })
        
        # Se NON è lo psicologo che ha messo in ghost, notifica gli psicologi
        if servizio_ghost != 'psicologia':
            for psicologo in cliente.psicologi_multipli:
                if psicologo.email and psicologo.is_active:
                    professionisti_da_notificare.append({
                        'email': psicologo.email,
                        'nome': f"{psicologo.first_name} {psicologo.last_name}",
                        'ruolo': 'Psicologo/a'
                    })
        
        # Notifica sempre i consulenti alimentari
        for consulente in cliente.consulenti_multipli:
            if consulente.email and consulente.is_active:
                professionisti_da_notificare.append({
                    'email': consulente.email,
                    'nome': f"{consulente.first_name} {consulente.last_name}",
                    'ruolo': 'Consulente Alimentare'
                })
        
        # Invia email a ciascun professionista
        for prof in professionisti_da_notificare:
            send_service_ghost_notification(
                recipient_email=prof['email'],
                recipient_name=prof['nome'],
                recipient_role=prof['ruolo'],
                client_name=cliente.nome_cognome,
                chi_ha_messo_ghost=chi_ha_messo_ghost,
                servizio_ghost=servizio_ghost
            )
            
        logger.info(f"Inviate {len(professionisti_da_notificare)} notifiche per servizio {servizio_ghost} in ghost - cliente {cliente.cliente_id}")
        
    except Exception as e:
        logger.error(f"Errore nell'invio notifiche servizio ghost: {e}")


def send_service_ghost_notification(recipient_email, recipient_name, recipient_role, 
                                   client_name, chi_ha_messo_ghost, servizio_ghost):
    """
    Invia email quando un singolo servizio va in ghost.
    """
    try:
        subject = f"⚠️ {chi_ha_messo_ghost} ha messo in GHOST - {client_name}"
        
        body = f"""
Caro/a {recipient_name},

Ti informiamo che <strong>{chi_ha_messo_ghost}</strong> ha messo il cliente 
<strong>{client_name}</strong> in stato GHOST per il servizio <strong>{servizio_ghost}</strong>.

<b>Cosa significa:</b>
• {chi_ha_messo_ghost} non riesce più a contattare o lavorare con questo cliente
• Il cliente potrebbe non rispondere o partecipare al programma per questo servizio
• È importante coordinare con il team per capire la situazione

<b>Azioni suggerite:</b>
• Verifica se anche tu stai avendo difficoltà con questo cliente
• Coordina con {chi_ha_messo_ghost} per capire le cause
• Valuta strategie alternative di contatto
• Aggiorna il tuo stato se necessario

<b>Il tuo ruolo:</b> {recipient_role}

Se anche tu stai avendo difficoltà con questo cliente, considera di aggiornare 
il tuo stato di conseguenza nella piattaforma.

Cordiali saluti,
Il Team Corposostenibile
"""
        
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            html=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )
        
        mail.send(msg)
        logger.info(f"Email servizio ghost inviata a {recipient_email} - {chi_ha_messo_ghost} per cliente {client_name}")
        
    except Exception as e:
        logger.error(f"Errore invio email servizio ghost a {recipient_email}: {e}")


def notify_professionals_on_ghost(cliente: Cliente, servizio_ghost: str = None):
    """
    Invia notifiche email ai professionisti quando un cliente va in ghost.
    
    Args:
        cliente: Il cliente che è andato in ghost
        servizio_ghost: Il servizio specifico che è andato in ghost (nutrizione, coach, psicologia)
    """
    try:
        # Raccogli tutti i professionisti associati al cliente
        professionisti_da_notificare = []
        
        # Nutrizionisti
        for nutrizionista in cliente.nutrizionisti_multipli:
            if nutrizionista.email and nutrizionista.is_active:
                professionisti_da_notificare.append({
                    'email': nutrizionista.email,
                    'nome': f"{nutrizionista.first_name} {nutrizionista.last_name}",
                    'ruolo': 'Nutrizionista'
                })
        
        # Coach
        for coach in cliente.coaches_multipli:
            if coach.email and coach.is_active:
                professionisti_da_notificare.append({
                    'email': coach.email,
                    'nome': f"{coach.first_name} {coach.last_name}",
                    'ruolo': 'Coach'
                })
        
        # Psicologi
        for psicologo in cliente.psicologi_multipli:
            if psicologo.email and psicologo.is_active:
                professionisti_da_notificare.append({
                    'email': psicologo.email,
                    'nome': f"{psicologo.first_name} {psicologo.last_name}",
                    'ruolo': 'Psicologo/a'
                })
        
        # Consulenti alimentari
        for consulente in cliente.consulenti_multipli:
            if consulente.email and consulente.is_active:
                professionisti_da_notificare.append({
                    'email': consulente.email,
                    'nome': f"{consulente.first_name} {consulente.last_name}",
                    'ruolo': 'Consulente Alimentare'
                })
        
        # Invia email a ciascun professionista
        for prof in professionisti_da_notificare:
            send_ghost_notification_email(
                recipient_email=prof['email'],
                recipient_name=prof['nome'],
                recipient_role=prof['ruolo'],
                client_name=cliente.nome_cognome,
                servizio_ghost=servizio_ghost
            )
            
        logger.info(f"Inviate {len(professionisti_da_notificare)} notifiche ghost per cliente {cliente.cliente_id}")
        
    except Exception as e:
        logger.error(f"Errore nell'invio notifiche ghost: {e}")


def send_ghost_notification_email(recipient_email, recipient_name, recipient_role, client_name, servizio_ghost=None):
    """
    Invia l'email di notifica ghost a un singolo professionista.
    """
    try:
        subject = f"⚠️ Cliente in GHOST - {client_name}"
        
        if servizio_ghost:
            body = f"""
Caro/a {recipient_name},

Ti informiamo che il cliente <strong>{client_name}</strong> è passato in stato GHOST 
per il servizio <strong>{servizio_ghost}</strong>.

Questo significa che il cliente non sta più rispondendo o partecipando attivamente al programma.

<b>Azioni suggerite:</b>
• Verifica l'ultimo contatto con il cliente
• Prova a contattare il cliente tramite i canali alternativi
• Coordina con gli altri professionisti del team
• Aggiorna lo stato del cliente quando riprende il contatto

<b>Il tuo ruolo nel team:</b> {recipient_role}

Per maggiori dettagli, accedi alla piattaforma Corposostenibile.

Cordiali saluti,
Il Team Corposostenibile
"""
        else:
            body = f"""
Caro/a {recipient_name},

Ti informiamo che il cliente <strong>{client_name}</strong> è passato in stato GHOST globale.

Tutti i servizi attivi del cliente sono ora in stato ghost, indicando una perdita di contatto 
completa con il programma.

<b>Azioni suggerite:</b>
• Coordinamento immediato con tutto il team
• Tentativo di ricontatto coordinato
• Valutazione delle cause della perdita di contatto
• Piano di recupero se il cliente riprende il contatto

<b>Il tuo ruolo nel team:</b> {recipient_role}

Per maggiori dettagli, accedi alla piattaforma Corposostenibile.

Cordiali saluti,
Il Team Corposostenibile
"""
        
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            html=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )
        
        mail.send(msg)
        logger.info(f"Email ghost inviata a {recipient_email} per cliente {client_name}")
        
    except Exception as e:
        logger.error(f"Errore invio email a {recipient_email}: {e}")


def notify_client_reactivation(cliente: Cliente):
    """
    Notifica i professionisti quando un cliente esce dallo stato ghost.
    """
    try:
        professionisti_da_notificare = []
        
        # Raccogli tutti i professionisti (come sopra)
        for nutrizionista in cliente.nutrizionisti_multipli:
            if nutrizionista.email and nutrizionista.is_active:
                professionisti_da_notificare.append({
                    'email': nutrizionista.email,
                    'nome': f"{nutrizionista.first_name} {nutrizionista.last_name}"
                })
        
        for coach in cliente.coaches_multipli:
            if coach.email and coach.is_active:
                professionisti_da_notificare.append({
                    'email': coach.email,
                    'nome': f"{coach.first_name} {coach.last_name}"
                })
        
        for psicologo in cliente.psicologi_multipli:
            if psicologo.email and psicologo.is_active:
                professionisti_da_notificare.append({
                    'email': psicologo.email,
                    'nome': f"{psicologo.first_name} {psicologo.last_name}"
                })
        
        # Invia email di riattivazione
        for prof in professionisti_da_notificare:
            send_reactivation_email(
                recipient_email=prof['email'],
                recipient_name=prof['nome'],
                client_name=cliente.nome_cognome
            )
            
    except Exception as e:
        logger.error(f"Errore nell'invio notifiche riattivazione: {e}")


def send_reactivation_email(recipient_email, recipient_name, client_name):
    """
    Invia email di notifica quando un cliente esce dallo stato ghost.
    """
    try:
        subject = f"✅ Cliente Riattivato - {client_name}"
        
        body = f"""
Caro/a {recipient_name},

Buone notizie! Il cliente <strong>{client_name}</strong> è uscito dallo stato GHOST 
ed è nuovamente attivo nel programma.

<b>Prossimi passi:</b>
• Riprendi il contatto regolare con il cliente
• Verifica eventuali necessità accumulate durante il periodo ghost
• Aggiorna il piano di lavoro se necessario
• Coordina con il team per un approccio integrato

Accedi alla piattaforma per vedere i dettagli aggiornati del cliente.

Cordiali saluti,
Il Team Corposostenibile
"""
        
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            html=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )
        
        mail.send(msg)
        logger.info(f"Email riattivazione inviata a {recipient_email} per cliente {client_name}")

    except Exception as e:
        logger.error(f"Errore invio email riattivazione a {recipient_email}: {e}")


def send_freeze_notification(cliente: Cliente, frozen_by: User, reason: str = None):
    """
    Invia notifiche email a tutti i professionisti quando un cliente viene messo in FREEZE.

    Args:
        cliente: Il cliente messo in freeze
        frozen_by: L'Health Manager che ha eseguito il freeze
        reason: La motivazione del freeze
    """
    try:
        # Raccogli tutti i professionisti associati al cliente
        professionisti = []

        # Nutrizionisti
        if hasattr(cliente, 'nutrizionisti_multipli'):
            for nutrizionista in cliente.nutrizionisti_multipli:
                if nutrizionista.email and nutrizionista.is_active:
                    professionisti.append({
                        'email': nutrizionista.email,
                        'nome': getattr(nutrizionista, 'full_name', nutrizionista.email),
                        'ruolo': 'Nutrizionista'
                    })

        # Coach
        if hasattr(cliente, 'coaches_multipli'):
            for coach in cliente.coaches_multipli:
                if coach.email and coach.is_active:
                    professionisti.append({
                        'email': coach.email,
                        'nome': getattr(coach, 'full_name', coach.email),
                        'ruolo': 'Coach'
                    })

        # Psicologi
        if hasattr(cliente, 'psicologi_multipli'):
            for psicologo in cliente.psicologi_multipli:
                if psicologo.email and psicologo.is_active:
                    professionisti.append({
                        'email': psicologo.email,
                        'nome': getattr(psicologo, 'full_name', psicologo.email),
                        'ruolo': 'Psicologo'
                    })

        # Consulenti
        if hasattr(cliente, 'consulenti_multipli'):
            for consulente in cliente.consulenti_multipli:
                if consulente.email and consulente.is_active:
                    professionisti.append({
                        'email': consulente.email,
                        'nome': getattr(consulente, 'full_name', consulente.email),
                        'ruolo': 'Consulente'
                    })

        # Invia email a ciascun professionista
        for prof in professionisti:
            _send_freeze_email(
                prof['email'],
                prof['nome'],
                prof['ruolo'],
                cliente.nome_cognome,
                frozen_by.full_name or frozen_by.email,
                reason
            )

        logger.info(f"Notifiche freeze inviate per cliente {cliente.nome_cognome} a {len(professionisti)} professionisti")

    except Exception as e:
        logger.error(f"Errore invio notifiche freeze per cliente {cliente.cliente_id}: {e}")


def send_unfreeze_notification(cliente: Cliente, unfrozen_by: User, resolution: str = None):
    """
    Invia notifiche email a tutti i professionisti quando un cliente viene rimosso da FREEZE.

    Args:
        cliente: Il cliente rimosso da freeze
        unfrozen_by: L'Health Manager che ha rimosso il freeze
        resolution: La storia/risoluzione del freeze
    """
    try:
        # Raccogli tutti i professionisti associati al cliente
        professionisti = []

        # Nutrizionisti
        if hasattr(cliente, 'nutrizionisti_multipli'):
            for nutrizionista in cliente.nutrizionisti_multipli:
                if nutrizionista.email and nutrizionista.is_active:
                    professionisti.append({
                        'email': nutrizionista.email,
                        'nome': getattr(nutrizionista, 'full_name', nutrizionista.email),
                        'ruolo': 'Nutrizionista'
                    })

        # Coach
        if hasattr(cliente, 'coaches_multipli'):
            for coach in cliente.coaches_multipli:
                if coach.email and coach.is_active:
                    professionisti.append({
                        'email': coach.email,
                        'nome': getattr(coach, 'full_name', coach.email),
                        'ruolo': 'Coach'
                    })

        # Psicologi
        if hasattr(cliente, 'psicologi_multipli'):
            for psicologo in cliente.psicologi_multipli:
                if psicologo.email and psicologo.is_active:
                    professionisti.append({
                        'email': psicologo.email,
                        'nome': getattr(psicologo, 'full_name', psicologo.email),
                        'ruolo': 'Psicologo'
                    })

        # Consulenti
        if hasattr(cliente, 'consulenti_multipli'):
            for consulente in cliente.consulenti_multipli:
                if consulente.email and consulente.is_active:
                    professionisti.append({
                        'email': consulente.email,
                        'nome': getattr(consulente, 'full_name', consulente.email),
                        'ruolo': 'Consulente'
                    })

        # Invia email a ciascun professionista
        for prof in professionisti:
            _send_unfreeze_email(
                prof['email'],
                prof['nome'],
                prof['ruolo'],
                cliente.nome_cognome,
                unfrozen_by.full_name or unfrozen_by.email,
                resolution
            )

        logger.info(f"Notifiche unfreeze inviate per cliente {cliente.nome_cognome} a {len(professionisti)} professionisti")

    except Exception as e:
        logger.error(f"Errore invio notifiche unfreeze per cliente {cliente.cliente_id}: {e}")


def _send_freeze_email(recipient_email: str, recipient_name: str, recipient_role: str,
                      client_name: str, frozen_by: str, reason: str = None):
    """Helper per inviare email di notifica freeze."""
    try:
        subject = f"🔒 URGENTE: Cliente {client_name} in stato FREEZE"

        reason_text = f"<p><strong>Motivazione:</strong> {reason}</p>" if reason else ""

        body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <div style="background-color: #dc3545; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="margin: 0;">⚠️ CLIENTE IN STATO FREEZE</h2>
    </div>

    <div style="padding: 20px; background-color: #f8f9fa; border: 1px solid #dee2e6;">
        <p>Caro/a <strong>{recipient_name}</strong> ({recipient_role}),</p>

        <p>Ti informiamo che il cliente <strong style="color: #dc3545;">{client_name}</strong>
        è stato messo in stato <strong>FREEZE</strong> da {frozen_by}.</p>

        {reason_text}

        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0;"><strong>⚠️ IMPORTANTE:</strong></p>
            <ul style="margin: 10px 0;">
                <li>SOSPENDI IMMEDIATAMENTE tutte le attività con questo cliente</li>
                <li>NON programmare nuove call o sessioni</li>
                <li>NON rispondere a messaggi o chat</li>
                <li>Attendi ulteriori comunicazioni dall'Health Manager</li>
            </ul>
        </div>

        <p>L'Health Manager sta gestendo la situazione e fornirà un report dettagliato appena possibile.</p>

        <p style="margin-top: 30px;">
            <a href="{current_app.config.get('SERVER_NAME', 'https://suite.corposostenibile.com')}/customers/{client_name}"
               style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                Visualizza Dettagli Cliente
            </a>
        </p>
    </div>

    <div style="padding: 10px; background-color: #e9ecef; text-align: center; font-size: 12px;">
        Corpo Sostenibile Suite - Notifica Automatica
    </div>
</body>
</html>
"""

        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            html=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )

        mail.send(msg)
        logger.info(f"Email freeze inviata a {recipient_email} per cliente {client_name}")

    except Exception as e:
        logger.error(f"Errore invio email freeze a {recipient_email}: {e}")


def _send_unfreeze_email(recipient_email: str, recipient_name: str, recipient_role: str,
                        client_name: str, unfrozen_by: str, resolution: str = None):
    """Helper per inviare email di notifica unfreeze."""
    try:
        subject = f"✅ Cliente {client_name} rimosso da stato FREEZE"

        resolution_text = f"""
        <div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0;"><strong>Risoluzione:</strong></p>
            <p style="margin: 10px 0;">{resolution}</p>
        </div>
        """ if resolution else ""

        body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
    <div style="background-color: #28a745; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="margin: 0;">✅ CLIENTE RIATTIVATO</h2>
    </div>

    <div style="padding: 20px; background-color: #f8f9fa; border: 1px solid #dee2e6;">
        <p>Caro/a <strong>{recipient_name}</strong> ({recipient_role}),</p>

        <p>Ti informiamo che il cliente <strong style="color: #28a745;">{client_name}</strong>
        è stato <strong>rimosso dallo stato FREEZE</strong> da {unfrozen_by}.</p>

        {resolution_text}

        <div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0;"><strong>✅ PUOI RIPRENDERE:</strong></p>
            <ul style="margin: 10px 0;">
                <li>Le normali attività con il cliente</li>
                <li>La programmazione di call e sessioni</li>
                <li>La risposta a messaggi e chat</li>
                <li>Il percorso terapeutico/di coaching</li>
            </ul>
        </div>

        <p>Se hai domande sulla situazione risolta, contatta l'Health Manager per maggiori dettagli.</p>

        <p style="margin-top: 30px;">
            <a href="{current_app.config.get('SERVER_NAME', 'https://suite.corposostenibile.com')}/customers/{client_name}"
               style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                Visualizza Dettagli Cliente
            </a>
        </p>
    </div>

    <div style="padding: 10px; background-color: #e9ecef; text-align: center; font-size: 12px;">
        Corpo Sostenibile Suite - Notifica Automatica
    </div>
</body>
</html>
"""

        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            html=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )

        mail.send(msg)
        logger.info(f"Email unfreeze inviata a {recipient_email} per cliente {client_name}")

    except Exception as e:
        logger.error(f"Errore invio email unfreeze a {recipient_email}: {e}")
"""
Sistema Notifiche Email - Feedback Global

FASE 2: Email TESTUALI con motivazioni obbligatorie per trasparenza feedback loop.

Invia email testuali per:
- Nuova idea proposta → Owner blueprint
- Nuovo issue segnalato → Team tecnico
- Idea approvata/rigettata/pending/implementata → Utente proponente
- Issue presa in carico/risolta/wontfix → Utente segnalante
"""
from flask import current_app
from flask_mail import Message
from corposostenibile.extensions import mail


def send_idea_notification(improvement, blueprint):
    """
    📧 Notifica owner blueprint quando viene proposta nuova idea.

    Args:
        improvement: BlueprintImprovement instance
        blueprint: BlueprintRegistry instance
    """
    if not blueprint.owner or not blueprint.owner.email:
        current_app.logger.warning(
            f'Blueprint {blueprint.code} non ha owner con email - skip notification'
        )
        return

    try:
        subject = f'💡 Nuova idea proposta per {blueprint.name}'

        body = f"""
Ciao {blueprint.owner.first_name},

È stata proposta una nuova idea di miglioramento per il modulo "{blueprint.name}":

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IDEA: {improvement.title}

Proposta da: {improvement.proposed_by.first_name} {improvement.proposed_by.last_name}
Priorità: {improvement.priority.upper()}

DESCRIZIONE:
{improvement.description}
"""

        # Aggiungi impatto atteso se presente (fix f-string backslash issue)
        if improvement.expected_impact:
            body += f"\nIMPATTO ATTESO:\n{improvement.expected_impact}\n"

        body += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Puoi valutare questa idea e rispondere con motivazione dal Blueprint Registry:
👉 /blueprint-registry/{blueprint.code}

Ricorda: Quando approvi/rigetti/metti in sospeso, la motivazione è OBBLIGATORIA.
L'utente riceverà email con la tua risposta.

--
Sistema Feedback Corposostenibile
"""

        msg = Message(
            subject=subject,
            recipients=[blueprint.owner.email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )

        mail.send(msg)
        current_app.logger.info(
            f'Email nuova idea inviata a {blueprint.owner.email} per idea #{improvement.id}'
        )

    except Exception as e:
        current_app.logger.error(f'Errore invio email nuova idea: {str(e)}')


def send_issue_notification(issue, blueprint):
    """
    📧 Notifica team tecnico quando viene segnalato nuovo issue.

    Args:
        issue: BlueprintIssue instance
        blueprint: BlueprintRegistry instance
    """
    recipients = []

    # Owner blueprint
    if blueprint.owner and blueprint.owner.email:
        recipients.append(blueprint.owner.email)

    # Admin (fallback se non c'è owner)
    admin_emails = current_app.config.get('ADMIN_EMAILS', [])
    if not recipients and admin_emails:
        recipients = admin_emails

    if not recipients:
        current_app.logger.warning(f'Nessun recipient per issue #{issue.id} - skip notification')
        return

    try:
        # Subject diverso per severity
        if issue.severity.value in ['blocker', 'critical']:
            subject = f'🚨 Issue {issue.severity.value.upper()} in {blueprint.name}'
        else:
            subject = f'🐛 Nuovo issue segnalato in {blueprint.name}'

        severity_emoji = {
            'blocker': '🔥',
            'critical': '🚨',
            'major': '⚠️',
            'minor': 'ℹ️'
        }

        body = f"""
{severity_emoji.get(issue.severity.value, '🐛')} NUOVO ISSUE SEGNALATO

Modulo: {blueprint.name}
Severità: {issue.severity.value.upper()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEMA: {issue.title}

Segnalato da: {issue.reported_by.first_name} {issue.reported_by.last_name}
Email: {issue.reported_by.email}

DESCRIZIONE:
{issue.description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Prendi in carico l'issue e rispondi all'utente con un messaggio dal Blueprint Registry:
👉 /blueprint-registry/{blueprint.code}

Quando prendi in carico / risolvi / chiudi come won't fix, il messaggio è OBBLIGATORIO.
L'utente riceverà email con il tuo aggiornamento.

--
Sistema Feedback Corposostenibile
"""

        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )

        mail.send(msg)
        current_app.logger.info(
            f'Email nuovo issue inviata a {", ".join(recipients)} per issue #{issue.id}'
        )

    except Exception as e:
        current_app.logger.error(f'Errore invio email nuovo issue: {str(e)}')


def send_idea_status_email(improvement, status, motivation):
    """
    📧 Notifica utente su cambio stato idea CON MOTIVAZIONE.

    FASE 2: Email testuale con motivazione admin trasparente.

    Args:
        improvement: BlueprintImprovement instance
        status: str ('approved', 'rejected', 'pending', 'implemented')
        motivation: str (motivazione admin)
    """
    if not improvement.proposed_by or not improvement.proposed_by.email:
        current_app.logger.warning(f'Idea #{improvement.id} senza proponente - skip email')
        return

    user = improvement.proposed_by

    # Messaggi personalizzati per status
    if status == 'approved':
        subject = f'✅ La tua idea "{improvement.title}" è stata APPROVATA!'
        emoji = '✅'
        opening = f'Ciao {user.first_name},\n\nOttime notizie! La tua idea è stata approvata dal team! 🎉'

    elif status == 'rejected':
        subject = f'Idea "{improvement.title}" - Feedback del team'
        emoji = '❌'
        opening = f'Ciao {user.first_name},\n\nGrazie per aver condiviso la tua idea. Dopo attenta valutazione, abbiamo deciso di non procedere con questa implementazione.'

    elif status == 'pending':
        subject = f'⏸️ Idea "{improvement.title}" - Richiesta dettagli'
        emoji = '⏸️'
        opening = f'Ciao {user.first_name},\n\nAbbiamo ricevuto la tua idea e ci servono ulteriori informazioni prima di valutarla.'

    elif status == 'implemented':
        subject = f'🎉 La tua idea "{improvement.title}" è STATA IMPLEMENTATA!'
        emoji = '🎉'
        opening = f'Ciao {user.first_name},\n\n🎉 FANTASTICO! La tua idea è stata implementata! 🎉'
    else:
        return

    try:
        body = f"""
{opening}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji} LA TUA IDEA:
"{improvement.title}"

Modulo: {improvement.blueprint.name}
Proposta il: {improvement.created_at.strftime('%d/%m/%Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 MOTIVAZIONE DEL TEAM:

{motivation}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Puoi vedere tutti i tuoi contributi qui:
👉 /feedback/my-contributions
"""

        # Aggiungi messaggio finale (fix f-string backslash issue)
        if status != 'implemented':
            body += "\nContinua a condividere le tue idee! Ogni contributo è prezioso. 💡\n"
        else:
            body += "\nGrazie per il tuo contributo prezioso! Continua a condividere le tue idee! 💡\n"

        body += """
--
Sistema Feedback Corposostenibile
"""

        msg = Message(
            subject=subject,
            recipients=[user.email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )

        mail.send(msg)
        current_app.logger.info(
            f'Email status idea ({status}) inviata a {user.email} per idea #{improvement.id}'
        )

    except Exception as e:
        current_app.logger.error(f'Errore invio email status idea: {str(e)}')


def send_issue_status_email(issue, status, motivation):
    """
    📧 Notifica utente su cambio stato issue CON MOTIVAZIONE.

    FASE 2: Email testuale con motivazione admin trasparente.

    Args:
        issue: BlueprintIssue instance
        status: str ('acknowledged', 'resolved', 'wontfix')
        motivation: str (motivazione/messaggio admin)
    """
    if not issue.reported_by or not issue.reported_by.email:
        current_app.logger.warning(f'Issue #{issue.id} senza reporter - skip email')
        return

    user = issue.reported_by

    # Messaggi personalizzati per status
    if status == 'acknowledged':
        subject = f'👀 Issue "{issue.title}" preso in carico'
        emoji = '👀'
        opening = f'Ciao {user.first_name},\n\nIl team tecnico ha preso in carico il problema che hai segnalato.'

    elif status == 'resolved':
        subject = f'✅ Issue "{issue.title}" RISOLTO'
        emoji = '✅'
        opening = f'Ciao {user.first_name},\n\nOttime notizie! Il problema che hai segnalato è stato risolto! ✅'

    elif status == 'wontfix':
        subject = f'Issue "{issue.title}" - Feedback del team'
        emoji = '🚫'
        opening = f'Ciao {user.first_name},\n\nGrazie per aver segnalato questo problema. Dopo attenta valutazione, abbiamo deciso di non procedere con la fix.'
    else:
        return

    try:
        body = f"""
{opening}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{emoji} IL TUO ISSUE:
"{issue.title}"

Modulo: {issue.blueprint.name}
Severità: {issue.severity.value.upper()}
Segnalato il: {issue.created_at.strftime('%d/%m/%Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💬 MESSAGGIO DEL TEAM:

{motivation}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Puoi vedere tutti i tuoi contributi qui:
👉 /feedback/my-contributions
"""

        # Aggiungi messaggio finale (fix f-string backslash issue)
        if status != 'wontfix':
            body += "\nGrazie per la segnalazione! Continua a segnalarci problemi. 🐛\n"
        else:
            body += "\nGrazie per la comprensione. Continua a segnalarci problemi reali! 🐛\n"

        body += """
--
Sistema Feedback Corposostenibile
"""

        msg = Message(
            subject=subject,
            recipients=[user.email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@corposostenibile.com')
        )

        mail.send(msg)
        current_app.logger.info(
            f'Email status issue ({status}) inviata a {user.email} per issue #{issue.id}'
        )

    except Exception as e:
        current_app.logger.error(f'Errore invio email status issue: {str(e)}')

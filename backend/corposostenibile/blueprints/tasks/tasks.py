from datetime import datetime, timedelta
from sqlalchemy import or_, and_, func

from corposostenibile.extensions import celery, db
from corposostenibile.models import (
    Cliente, 
    Task, 
    TaskCategoryEnum, 
    TaskStatusEnum, 
    TaskPriorityEnum,
    GiornoEnum,
    ClientCheckResponse,
    ClientCheckAssignment
)

# --------------------------------------------------------------------------- #
#  SOLLECITI (Solleciti checks mancati)
# --------------------------------------------------------------------------- #
@celery.task
def generate_solicitations_task():
    """
    Task periodico (giornaliero) per generare solleciti
    se un cliente ha il check_day IERI (o oggi) e non ha inviato nulla.
    
    Logica modificata per Celery:
    - Eseguito ogni mattina (es. 10:00).
    - Cerca clienti con check_day = IERI (per dare tempo fino a fine giornata) o OGGI?
    - Se iteriamo su "ieri", siamo sicuri che la giornata è finita.
    - Se iteriamo su "oggi", controlliamo se hanno mandato il check la SETTIMANA SCORSA (come da richiesta originale).
    
    Richiesta originale: "Oggi è 26 lunedi, il checkday è lunedi. il 19 non è stato inviato il check quindi scatta task".
    Quindi controlliamo i check mancati della settimana precedente nel giorno stesso del check.
    """
    session = db.session
    
    # Mappa giorni python (0=Lun) a GiornoEnum
    weekday_map = {
        0: [GiornoEnum.lun, GiornoEnum.lunedi],
        1: [GiornoEnum.mar, GiornoEnum.martedi],
        2: [GiornoEnum.mer, GiornoEnum.mercoledi],
        3: [GiornoEnum.gio, GiornoEnum.giovedi],
        4: [GiornoEnum.ven, GiornoEnum.venerdi],
        5: [GiornoEnum.sab, GiornoEnum.sabato],
        6: [GiornoEnum.dom, GiornoEnum.domenica],
    }
    
    today = datetime.utcnow().date()
    today_week_day = today.weekday()
    target_days = weekday_map.get(today_week_day, [])
    
    if not target_days:
        return f"Nessun GiornoEnum mappato per {today_week_day}"

    # Trova clienti attivi che hanno check_day OGGI
    clients = Cliente.query.filter(
        Cliente.stato_cliente == 'attivo',
        Cliente.check_day.in_(target_days)
    ).all()
    
    count_created = 0
    
    for client in clients:
        # Verifica se ha inviato check negli ultimi 7 giorni (o meglio, dalla settimana scorsa)
        last_check_date = _get_last_check_date(client)
        
        should_trigger = False
        if not last_check_date:
            should_trigger = True # Mai mandato
        else:
            days_diff = (today - last_check_date).days
            # Se l'ultimo check è più vecchio di 7 giorni (es. 8, 14...) significa che ha saltato l'ultimo
            # Se l'ha mandato oggi (diff=0) o ieri non scatta.
            # Se check_day è oggi, ci aspettiamo che l'ultimo check sia < 7 giorni fa (es. settimana scorsa).
            # Se days_diff >= 7, vuol dire che settimana scorsa non l'ha mandato (o l'ha mandato >7 gg fa).
            if days_diff >= 7:
                should_trigger = True

        if should_trigger:
            # Identifica a chi assegnare il task (Nutrizionista > Coach > Psicologa? O tutti?)
            # Solitamente il Nutrizionista è il principale, o chi segue il cliente.
            # Creiamo un task per il Nutrizionista se presente, altrimenti Coach.
            assignee_id = client.nutrizionista_id or client.coach_id or client.psicologa_id
            
            if not assignee_id:
                continue

            # Evita duplicati (task creato oggi per questo motivo)
            existing_task = Task.query.filter(
                Task.category == TaskCategoryEnum.sollecito,
                Task.client_id == client.cliente_id,
                Task.assignee_id == assignee_id,
                Task.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
            ).first()
            
            if not existing_task:
                task = Task(
                    title=f"Sollecito Check: {client.nome_cognome}",
                    description=f"Il paziente {client.nome_cognome} ha check day oggi ma non risulta check settimana scorsa. Sollecitalo!",
                    category=TaskCategoryEnum.sollecito,
                    status=TaskStatusEnum.todo,
                    priority=TaskPriorityEnum.high,
                    client_id=client.cliente_id,
                    assignee_id=assignee_id,
                    created_at=datetime.utcnow()
                )
                session.add(task)
                count_created += 1
    
    session.commit()
    return f"Generated {count_created} solicitation tasks."


def _get_last_check_date(client):
    """Ritorna la data dell'ultimo check inviato dal cliente."""
    last_check = db.session.query(ClientCheckResponse.created_at)\
        .join(ClientCheckAssignment, ClientCheckResponse.assignment_id == ClientCheckAssignment.id)\
        .filter(ClientCheckAssignment.cliente_id == client.cliente_id)\
        .order_by(ClientCheckResponse.created_at.desc())\
        .first()
        
    if last_check:
        return last_check[0].date()
    return None


# --------------------------------------------------------------------------- #
#  REMINDERS (Scadenze clienti e piani)
# --------------------------------------------------------------------------- #
@celery.task
def generate_reminders_task():
    """
    Task periodico (giornaliero) per controllare scadenze:
    1. Scadenza abbonamento (Cliente)
    2. Scadenza piano nutrizionale (stimata o da campo)
    """
    session = db.session
    today = datetime.utcnow().date()
    count_reminders = 0
    
    # 1. Scadenza Abbonamento (es. 7 giorni prima)
    # Calcoliamo la data di scadenza: data_inizio_abbonamento + durata_programma_giorni
    # Oppure usiamo data_rinnovo se presente.
    
    # Strategia: cerchiamo clienti attivi
    clients = Cliente.query.filter(Cliente.stato_cliente == 'attivo').all()
    
    for client in clients:
        expiration_date = None
        
        # Priorità a data_rinnovo
        if client.data_rinnovo:
            expiration_date = client.data_rinnovo
        elif client.data_inizio_abbonamento and client.durata_programma_giorni:
            expiration_date = client.data_inizio_abbonamento + timedelta(days=client.durata_programma_giorni)
            
        if expiration_date:
            days_to_expire = (expiration_date - today).days
            
            # Trigger a -7 giorni e -1 giorno
            if days_to_expire in [7, 1]:
                assignee_id = client.nutrizionista_id or client.coach_id
                if assignee_id:
                    # Check duplicati
                    if _create_reminder_task(
                        session, 
                        client, 
                        assignee_id, 
                        f"Scadenza Cliente: {client.nome_cognome}",
                        f"Il cliente scade il {expiration_date} (tra {days_to_expire} giorni).",
                        TaskCategoryEnum.reminder,
                        payload={'type': 'client_expiration', 'days_left': days_to_expire}
                    ):
                        count_reminders += 1

        # 2. Scadenza Piano Nutrizionale (es. ogni 4 settimane da dieta_dal?)
        # Se c'è 'dieta_dal', ipotizziamo check ogni 4 settimane? o solo se 'nuova_dieta_dal' è impostata futura?
        # Non essendoci una regola fissa, per ora usiamo una logica semplice:
        # Se 'dieta_dal' è vecchia di 28 giorni esatti (o multipli), ricorda di aggiornare?
        # OPPURE: Il cliente ha un reminder specifico.
        # Implementiamo solo se esplicito. Per ora mettiamo un placeholder logico sulla data dieta.
        
        if client.dieta_dal:
            # Esempio: reminder dopo 4 settimane (28 giorni)
            days_since_diet = (today - client.dieta_dal).days
            if days_since_diet == 28:
                 assignee_id = client.nutrizionista_id
                 if assignee_id:
                     if _create_reminder_task(
                        session,
                        client,
                        assignee_id,
                        f"Revisione Piano: {client.nome_cognome}",
                        f"Il piano nutrizionale è attivo da 4 settimane ({client.dieta_dal}). Valuta revisione.",
                        TaskCategoryEnum.reminder,
                         payload={'type': 'plan_expiration', 'days_active': days_since_diet}
                     ):
                         count_reminders += 1

    session.commit()
    return f"Generated {count_reminders} reminder tasks."

def _create_reminder_task(session, client, assignee_id, title, description, category, payload=None):
    """Helper per creare task se non esiste già oggi."""
    existing = Task.query.filter(
        Task.category == category,
        Task.client_id == client.cliente_id,
        Task.title == title, # Use title uniqueness for specific reminder type
        Task.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).first()
    
    if not existing:
        task = Task(
            title=title,
            description=description,
            category=category,
            status=TaskStatusEnum.todo,
            priority=TaskPriorityEnum.medium,
            client_id=client.cliente_id,
            assignee_id=assignee_id,
            created_at=datetime.utcnow(),
            payload=payload or {}
        )
        session.add(task)
        return True
    return False

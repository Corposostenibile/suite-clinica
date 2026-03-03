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
    WeeklyCheck,
    WeeklyCheckResponse,
    DCACheck,
    DCACheckResponse,
    MinorCheck,
    MinorCheckResponse,
)

# --------------------------------------------------------------------------- #
#  SOLLECITI (Solleciti checks mancati)
# --------------------------------------------------------------------------- #
@celery.task
def generate_solicitations_task():
    """
    Task periodico (giornaliero, 10:00 AM) per generare solleciti.

    Logica: il check_day del cliente era IERI. Se non ha compilato il check
    settimanale negli ultimi 2 giorni (ieri/oggi), scatta il sollecito per
    nutrizionista, coach e psicologo assegnati.

    Solo clienti ATTIVI. Evita duplicati (max 1 sollecito per professionista
    per cliente al giorno).
    """
    session = db.session

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
    yesterday = today - timedelta(days=1)
    yesterday_weekday = yesterday.weekday()
    target_days = weekday_map.get(yesterday_weekday, [])

    if not target_days:
        return f"Nessun GiornoEnum mappato per {yesterday_weekday}"

    # Clienti attivi con check_day = IERI
    clients = Cliente.query.filter(
        Cliente.stato_cliente == 'attivo',
        Cliente.check_day.in_(target_days),
    ).all()

    count_created = 0

    for client in clients:
        last_check_date = _get_last_check_date(client)

        # Se ha compilato ieri o oggi → OK, niente sollecito
        if last_check_date and (today - last_check_date).days <= 1:
            continue

        # Sollecito a tutti i professionisti assegnati
        prof_ids = [client.nutrizionista_id, client.coach_id, client.psicologa_id]
        prof_ids = [pid for pid in prof_ids if pid]

        if not prof_ids:
            continue

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        for assignee_id in prof_ids:
            existing = Task.query.filter(
                Task.category == TaskCategoryEnum.sollecito,
                Task.client_id == client.cliente_id,
                Task.assignee_id == assignee_id,
                Task.created_at >= today_start,
            ).first()

            if not existing:
                task = Task(
                    title=f"Sollecito Check: {client.nome_cognome}",
                    description=(
                        f"Il paziente {client.nome_cognome} aveva check day ieri "
                        f"ma non ha compilato il check settimanale. Sollecitalo!"
                    ),
                    category=TaskCategoryEnum.sollecito,
                    status=TaskStatusEnum.todo,
                    priority=TaskPriorityEnum.high,
                    client_id=client.cliente_id,
                    assignee_id=assignee_id,
                    created_at=datetime.utcnow(),
                )
                session.add(task)
                count_created += 1

    session.commit()
    return f"Generated {count_created} solicitation tasks."


def _get_last_check_date(client):
    """Ritorna la data dell'ultimo check inviato dal cliente (weekly, DCA o minor)."""
    latest = None

    # Weekly check (il più comune)
    wk = (
        db.session.query(WeeklyCheckResponse.submit_date)
        .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
        .filter(WeeklyCheck.cliente_id == client.cliente_id)
        .order_by(WeeklyCheckResponse.submit_date.desc())
        .first()
    )
    if wk and wk[0]:
        latest = wk[0].date() if hasattr(wk[0], "date") else wk[0]

    # DCA check
    dca = (
        db.session.query(DCACheckResponse.submit_date)
        .join(DCACheck, DCACheckResponse.dca_check_id == DCACheck.id)
        .filter(DCACheck.cliente_id == client.cliente_id)
        .order_by(DCACheckResponse.submit_date.desc())
        .first()
    )
    if dca and dca[0]:
        dca_date = dca[0].date() if hasattr(dca[0], "date") else dca[0]
        if not latest or dca_date > latest:
            latest = dca_date

    # Minor check
    mn = (
        db.session.query(MinorCheckResponse.submit_date)
        .join(MinorCheck, MinorCheckResponse.minor_check_id == MinorCheck.id)
        .filter(MinorCheck.cliente_id == client.cliente_id)
        .order_by(MinorCheckResponse.submit_date.desc())
        .first()
    )
    if mn and mn[0]:
        mn_date = mn[0].date() if hasattr(mn[0], "date") else mn[0]
        if not latest or mn_date > latest:
            latest = mn_date

    return latest


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

        # 2. Scadenza Piano Nutrizionale (nuova_dieta_dal)
        if client.nuova_dieta_dal:
            days_to_diet_expire = (client.nuova_dieta_dal - today).days
            if days_to_diet_expire in [7, 3, 0]: # Reminder a -7, -3 e oggi
                 assignee_id = client.nutrizionista_id
                 if assignee_id:
                     if _create_reminder_task(
                        session,
                        client,
                        assignee_id,
                        f"Scadenza Piano Nutrizionale: {client.nome_cognome}",
                        f"Il piano nutrizionale scade/si rinnova il {client.nuova_dieta_dal} (tra {days_to_diet_expire} giorni).",
                        TaskCategoryEnum.reminder,
                         payload={'type': 'plan_expiration', 'subtype': 'nutrition', 'days_left': days_to_diet_expire}
                     ):
                         count_reminders += 1

        # 3. Scadenza Piano Allenamento (nuovo_allenamento_il)
        if client.nuovo_allenamento_il:
            days_to_training_expire = (client.nuovo_allenamento_il - today).days
            if days_to_training_expire in [7, 3, 0]: # Reminder a -7, -3 e oggi
                 assignee_id = client.coach_id
                 if assignee_id:
                     if _create_reminder_task(
                        session,
                        client,
                        assignee_id,
                        f"Scadenza Scheda Allenamento: {client.nome_cognome}",
                        f"La scheda di allenamento scade/si rinnova il {client.nuovo_allenamento_il} (tra {days_to_training_expire} giorni).",
                        TaskCategoryEnum.reminder,
                         payload={'type': 'plan_expiration', 'subtype': 'training', 'days_left': days_to_training_expire}
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

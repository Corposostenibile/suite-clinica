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
    WeeklyCheck, WeeklyCheckResponse,
    DCACheck, DCACheckResponse,
    TypeFormResponse,
    User,
)

# --------------------------------------------------------------------------- #
#  SOLLECITI (Solleciti checks mancati)
# --------------------------------------------------------------------------- #
@celery.task
def generate_solicitations_task():
    """
    Task periodico (giornaliero) per generare solleciti check mancati.

    Logica:
    - Gira ogni mattina.
    - Cerca clienti attivi con check_day = IERI.
    - Se il cliente NON ha inviato nessun check IERI, genera task sollecito
      ai professionisti il cui stato specifico è 'attivo':
        - nutrizionista  → stato_nutrizione == attivo
        - coach          → stato_coach == attivo
        - psicologa      → stato_psicologia == attivo
      (consulente alimentare escluso)
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
        Cliente.check_day.in_(target_days)
    ).all()

    count_created = 0

    for client in clients:
        # Verifica se ha inviato un check IERI
        if _has_check_on_date(client, yesterday):
            continue

        # Professionisti filtrati per stato attivo
        prof_ids = set()

        stato_n = str(client.stato_nutrizione.value) if client.stato_nutrizione else ''
        stato_c = str(client.stato_coach.value) if client.stato_coach else ''
        stato_p = str(client.stato_psicologia.value) if client.stato_psicologia else ''

        if stato_n == 'attivo':
            if client.nutrizionista_id:
                prof_ids.add(client.nutrizionista_id)
            for u in (client.nutrizionisti_multipli or []):
                prof_ids.add(u.id)

        if stato_c == 'attivo':
            if client.coach_id:
                prof_ids.add(client.coach_id)
            for u in (client.coaches_multipli or []):
                prof_ids.add(u.id)

        if stato_p == 'attivo':
            if client.psicologa_id:
                prof_ids.add(client.psicologa_id)
            for u in (client.psicologi_multipli or []):
                prof_ids.add(u.id)

        if not prof_ids:
            continue

        for assignee_id in prof_ids:
            existing_task = Task.query.filter(
                Task.category == TaskCategoryEnum.sollecito,
                Task.client_id == client.cliente_id,
                Task.assignee_id == assignee_id,
                Task.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
            ).first()

            if not existing_task:
                task = Task(
                    title=f"Sollecito Check: {client.nome_cognome}",
                    description=f"Il paziente {client.nome_cognome} aveva check day ieri ({yesterday}) ma non ha inviato il check. Sollecitalo!",
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


def _has_check_on_date(client, target_date):
    """Verifica se il cliente ha inviato almeno un check nella data indicata."""
    # WeeklyCheckResponse
    weekly = (
        db.session.query(WeeklyCheckResponse.id)
        .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
        .filter(
            WeeklyCheck.cliente_id == client.cliente_id,
            func.date(WeeklyCheckResponse.submit_date) == target_date
        )
        .first()
    )
    if weekly:
        return True

    # DCACheckResponse
    dca = (
        db.session.query(DCACheckResponse.id)
        .join(DCACheck, DCACheckResponse.dca_check_id == DCACheck.id)
        .filter(
            DCACheck.cliente_id == client.cliente_id,
            func.date(DCACheckResponse.submit_date) == target_date
        )
        .first()
    )
    if dca:
        return True

    # TypeFormResponse (vecchio sistema)
    tf = (
        db.session.query(TypeFormResponse.id)
        .filter(
            TypeFormResponse.cliente_id == client.cliente_id,
            func.date(TypeFormResponse.submit_date) == target_date
        )
        .first()
    )
    if tf:
        return True

    return False


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

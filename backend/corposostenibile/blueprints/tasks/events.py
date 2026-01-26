from sqlalchemy import event, inspect, and_
from sqlalchemy.orm import attributes
from flask_login import user_logged_in
from flask import current_app
from datetime import datetime, timedelta

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente, 
    ClientCheckResponse, 
    Review, 
    Task, 
    TaskCategoryEnum, 
    TaskStatusEnum, 
    TaskPriorityEnum
)

# --------------------------------------------------------------------------- #
#  1. ONBOARDING (Assegnazione Cliente)
# --------------------------------------------------------------------------- #
@event.listens_for(Cliente, 'after_update')
def trigger_onboarding_task(mapper, connection, target):
    """
    Genera un task di onboarding quando viene assegnato un professionista.
    """
    # Verifica cambiamenti nei campi professionista
    # create_task_session = db.session.object_session(target) # after_update keeps session?
    # Usiamo Connection per insert diretti o Session? 
    # after_update passa connection. Se vogliamo usare ORM, meglio Session.
    # Ma attenzione a creare oggetti durante il flush (potrebbe dare warning).
    # listeners.py usava before_flush per questo motivo.
    # Proviamo con Session.
    
    session = db.session
    if not session:
        return

    # Helper per creare task
    def create_onboard_task(assignee_id, role_name):
        if not assignee_id:
            return
            
        task = Task(
            title=f"Nuovo Cliente: {target.nome_cognome}",
            description=f"Ti è stato assegnato il cliente {target.nome_cognome} come {role_name}. Mandagli il messaggio di benvenuto e leggi i suoi check!",
            category=TaskCategoryEnum.onboarding,
            status=TaskStatusEnum.todo,
            priority=TaskPriorityEnum.high,
            client_id=target.cliente_id,
            assignee_id=assignee_id,
            created_at=datetime.utcnow()
        )
        session.add(task)

    # Campi da monitorare
    prof_fields = {
        'nutrizionista_id': 'Nutrizionista',
        'coach_id': 'Coach',
        'psicologa_id': 'Psicologo/a',
        'health_manager_id': 'Health Manager'
    }

    state = inspect(target)
    for field, role in prof_fields.items():
        hist = state.attrs.get(field).history
        if hist.has_changes():
            # Nuovo valore assegnato (added[0])
            if hist.added and hist.added[0]:
                create_onboard_task(hist.added[0], role)


# --------------------------------------------------------------------------- #
#  2. CHECK RICEVUTO
# --------------------------------------------------------------------------- #
@event.listens_for(ClientCheckResponse, 'after_insert')
def trigger_check_task(mapper, connection, target):
    """
    Genera un task quando un cliente invia un check.
    """
    session = db.session
    if not session:
        return

    # Recupera il cliente e l'assegnazione
    # target.assignment -> CheckAssignment (link to Cliente)
    # Attenzione: related objects potrebbero non essere caricati in after_insert se non in session.
    # Facciamo query se necessario.
    
    # Per sicurezza, usiamo i pulsanti id
    # target.assignment_id
    
    # Nota: Task deve essere assegnato a chi ha assegnato il check (assigned_by_id in CheckAssignment)
    # o al professionista corrente del cliente.
    
    # Carichiamo assignment
    from corposostenibile.models import CheckAssignment
    assignment = session.query(CheckAssignment).get(target.assignment_id)
    
    if assignment and assignment.cliente:
        task = Task(
            title=f"Check Ricevuto: {assignment.cliente.nome_cognome}",
            description=f"Il cliente {assignment.cliente.nome_cognome} ha compilato il check. Leggilo!",
            category=TaskCategoryEnum.check,
            status=TaskStatusEnum.todo,
            priority=TaskPriorityEnum.high,
            client_id=assignment.cliente_id,
            assignee_id=assignment.assigned_by_id, # Chi ha assegnato il check
            created_at=datetime.utcnow(),
            payload={'check_response_id': target.id}
        )
        session.add(task)


# --------------------------------------------------------------------------- #
#  3. FORMAZIONE (Training)
# --------------------------------------------------------------------------- #
@event.listens_for(Review, 'after_insert')
def trigger_training_task(mapper, connection, target):
    """
    Genera un task quando viene assegnata una Review (Training).
    """
    session = db.session
    if not session:
        return
    
    # Consideriamo Training tutte le review o solo specifici tipi?
    # Per ora tutte, come da richiesta generica "Formazione".
    # target.reviewee_id è il destinatario
    
    task = Task(
        title=f"Nuova Formazione Assegnata",
        description=f"Hai ricevuto una nuova formazione/review: '{target.title}'. Leggila!",
        category=TaskCategoryEnum.formazione,
        status=TaskStatusEnum.todo,
        priority=TaskPriorityEnum.medium,
        assignee_id=target.reviewee_id,
        created_at=datetime.utcnow(),
        payload={'review_id': target.id}
    )
    session.add(task)


# --------------------------------------------------------------------------- #
#  4. SOLLECITI (Login Signal)
# --------------------------------------------------------------------------- #
@user_logged_in.connect
def check_solicitations_on_login(sender, user, **extra):
    """
    Al login, controlla se ci sono solleciti da generare per i check mancati.
    """
    # Evitiamo di bloccare il login se crasha
    try:
        _generate_solicitations(user)
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Error generating solicitations for user {user.id}: {e}")

def _generate_solicitations(user):
    from corposostenibile.extensions import db
    from corposostenibile.models import GiornoEnum
    
    # Mappa giorni python (0=Lun) a GiornoEnum
    # GiornoEnum: lun, mar, mer, gio, ven, sab, dom
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
        return

    # Trova clienti attivi del professionista che hanno check_day oggi
    # User potrebbe essere nutrizionista, coach o psicologo
    # Costruiamo filtro OR
    
    clients_query = Cliente.query.filter(
        Cliente.stato_cliente == 'attivo',
        Cliente.check_day.in_(target_days)
    ).filter(
        (Cliente.nutrizionista_id == user.id) |
        (Cliente.coach_id == user.id) |
        (Cliente.psicologa_id == user.id)
    )
    
    clients = clients_query.all()
    
    for client in clients:
        # Verifica se ha inviato check negli ultimi 7 giorni
        last_check_date = _get_last_check_date(client)
        
        # Se non c'è check o è vecchio più di 6 giorni (diamo un margine, se scade oggi magari lo manda stasera)
        # La richiesta dice: "oggi è 26 lunedi, il checkday è lunedi. il 19 non è stato inviato il check quindi scatta task"
        # Quindi controlliamo se NELLA SCORSA SETTIMANA è arrivato.
        
        should_trigger = False
        if not last_check_date:
            should_trigger = True # Mai mandato
        else:
            days_diff = (today - last_check_date).days
            if days_diff >= 7:
                should_trigger = True
                
        if should_trigger:
            # Verifica se abbiamo già creato un sollecito RECENTE (es. oggi) per questo cliente
            # per evitare duplicati ad ogni login
            existing_task = Task.query.filter(
                Task.category == TaskCategoryEnum.sollecito,
                Task.client_id == client.cliente_id,
                Task.assignee_id == user.id,
                Task.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0) # Creato oggi
            ).first()
            
            if not existing_task:
                task = Task(
                    title=f"Sollecito Check: {client.nome_cognome}",
                    description=f"Il paziente {client.nome_cognome} ha check day oggi ma non ha mandato il check settimanale la scorsa settimana. Sollecitalo!",
                    category=TaskCategoryEnum.sollecito,
                    status=TaskStatusEnum.todo,
                    priority=TaskPriorityEnum.high,
                    client_id=client.cliente_id,
                    assignee_id=user.id,
                    created_at=datetime.utcnow()
                )
                db.session.add(task)
    
    db.session.commit()

def _get_last_check_date(client):
    """Ritorna la data dell'ultimo check inviato dal cliente."""
    # Cerchiamo l'ultimo ClientCheckResponse
    # Join via CheckAssignment
    # ClientCheckResponse -> assignment -> cliente
    pass 
    # Query manuale
    from corposostenibile.models import CheckAssignment
    
    last_check = db.session.query(ClientCheckResponse.created_at)\
        .join(CheckAssignment, ClientCheckResponse.assignment_id == CheckAssignment.id)\
        .filter(CheckAssignment.cliente_id == client.cliente_id)\
        .order_by(ClientCheckResponse.created_at.desc())\
        .first()
        
    if last_check:
        return last_check[0].date()
    return None

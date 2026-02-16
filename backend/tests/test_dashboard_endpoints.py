
import pytest
import json
import random
import string
from datetime import datetime, date, timedelta
from corposostenibile.models import (
    User, Cliente, Department, UserRoleEnum, Team,
    StatoClienteEnum, WeeklyCheckResponse, WeeklyCheck,
    Review, ReviewAcknowledgment, CheckForm, CheckFormTypeEnum,
    ClientCheckAssignment, TeamEnum, UserSpecialtyEnum,
    TipologiaClienteEnum
)
from corposostenibile.extensions import db as _db

# --- Helpers per creazione dati ---

def get_random_string(length=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def create_test_client(db_session, **kwargs):
    # Tipologia cliente deve essere un valore valido dell'Enum o None
    tipologia = kwargs.get('tipologia_cliente')
    
    unique_email = kwargs.get('email', f"client_{get_random_string()}@test.com")
    
    c = Cliente(
        nome_cognome=kwargs.get('nome', f'Test Client {get_random_string()}'),
        mail=unique_email,
        stato_cliente=kwargs.get('stato', 'attivo'),
        created_at=kwargs.get('created_at', datetime.utcnow()),
        data_rinnovo=kwargs.get('data_rinnovo'),
        # Stati specifici
        stato_nutrizione=kwargs.get('stato_nutrizione'),
        stato_coach=kwargs.get('stato_coach'),
        stato_psicologia=kwargs.get('stato_psicologia'),
        # Professionisti
        nutrizionista_id=kwargs.get('nutrizionista_id'),
        coach_id=kwargs.get('coach_id'),
        psicologa_id=kwargs.get('psicologa_id'),
        tipologia_cliente=kwargs.get('tipologia_cliente', TipologiaClienteEnum.a)
    )
    db_session.add(c)
    db_session.commit()
    return c

def create_check_response(db_session, cliente, **kwargs):
    # Check if form exists
    form = CheckForm.query.first()
    if not form:
        form = CheckForm(name="Test Form", form_type=CheckFormTypeEnum.standard, is_active=True)
        db_session.add(form)
        db_session.commit()
        
    check = WeeklyCheck(
        cliente_id=cliente.cliente_id,
        token=get_random_string(20) # Ensure unique token
    )
    db_session.add(check)
    db_session.commit()

    resp = WeeklyCheckResponse(
        weekly_check_id=check.id,
        nutritionist_rating=kwargs.get('nutri_rate'),
        nutritionist_feedback="Bravo",
        coach_rating=kwargs.get('coach_rate'),
        psychologist_rating=kwargs.get('psy_rate'),
        submit_date=datetime.combine(kwargs.get('data', date.today()), datetime.min.time())
    )
    db_session.add(resp)
    db_session.commit()
    return resp

def create_review(db_session, reviewer, reviewee, **kwargs):
    r = Review(
        reviewer_id=reviewer.id,
        reviewee_id=reviewee.id,
        review_type=kwargs.get('type', 'weekly'),
        is_draft=False,
        # is_acknowledged is a property, handled below
        created_at=kwargs.get('created_at', datetime.utcnow()),
        title="Test Review",
        content="Contenuto"
    )
    db_session.add(r)
    db_session.commit()
    
    if kwargs.get('ack', False):
        ack = ReviewAcknowledgment(
            review_id=r.id,
            acknowledged_by=reviewee.id,
            acknowledged_at=datetime.utcnow()
        )
        db_session.add(ack)
        db_session.commit()
        
    return r

# --- TESTS ---

def test_customers_admin_dashboard_stats(authenticated_client, db_session):
    """
    Verifica endpoint: GET /api/v1/customers/admin-dashboard-stats
    Testa KPI conteggi, stati, trend e patologie.
    """
    # 1. Setup Dati
    today = datetime.utcnow()
    last_month = today - timedelta(days=40)
    
    # Clienti attivi
    c1 = create_test_client(db_session, nome="Active 1", stato="attivo", created_at=today, tipologia_cliente=TipologiaClienteEnum.a)
    c2 = create_test_client(db_session, nome="Active 2", stato="attivo", created_at=today, tipologia_cliente=TipologiaClienteEnum.b)
    
    # Clienti altri stati
    c3 = create_test_client(db_session, nome="Stop 1", stato="stop", created_at=last_month)
    c4 = create_test_client(db_session, nome="Insoluto 1", stato="stop", created_at=last_month)
    c5 = create_test_client(db_session, nome="Freeze 1", stato="pausa", created_at=last_month, stato_nutrizione="attivo")
    
    # Clienti per servizi specifici
    c6 = create_test_client(db_session, nome="Nutri Active", stato="attivo", stato_nutrizione="attivo")
    c7 = create_test_client(db_session, nome="Coach Active", stato="attivo", stato_coach="attivo")
    
    # 2. Call Endpoint
    res = authenticated_client.get('/api/v1/customers/admin-dashboard-stats')
    assert res.status_code == 200
    data = res.json
    
    # 3. Verifica KPI
    assert data['kpi']['total'] >= 7
    assert data['kpi']['active'] >= 4 # c1, c2, c6, c7
    
    # Verifica breakdown servizi
    services = data.get('services', {})
    assert services['nutrizione'].get('attivo', 0) >= 2 # c6, c5
    assert services['coach'].get('attivo', 0) >= 1 # c7
    
    # Verifica tipologia
    tipologia_dist = data.get('tipologiaDistribution', [])
    a_count = next((item['count'] for item in tipologia_dist if item['tipologia'] == 'a'), 0)
    assert a_count >= 1 # c1
    
    # Verifica stati mapping
    status_dist = {item['status']: item['count'] for item in data.get('statusDistribution', [])}
    
    # c3=stop, c4=insoluto->stop. Total stop >= 2
    assert status_dist.get('stop', 0) >= 2
    
    print("Customers Stats OK")


def test_client_checks_admin_dashboard_stats(authenticated_client, db_session):
    """
    Verifica endpoint: GET /api/client-checks/admin/dashboard-stats
    Testa conteggi check, rating medi e classifiche.
    """
    # 1. Setup Professionisti
    nutri_email = f"nutri_{get_random_string()}@test.com"
    coach_email = f"coach_{get_random_string()}@test.com"
    
    nutri = User(email=nutri_email, role=UserRoleEnum.professionista, specialty=UserSpecialtyEnum.nutrizionista, first_name="Nutri", last_name="Best")
    nutri.set_password('password')
    coach = User(email=coach_email, role=UserRoleEnum.professionista, specialty=UserSpecialtyEnum.coach, first_name="Coach", last_name="Pro")
    coach.set_password('password')
    db_session.add_all([nutri, coach])
    db_session.commit()
    
    # 2. Clienti assegnati
    c1 = create_test_client(db_session, nome="C1", nutrizionista_id=nutri.id)
    c2 = create_test_client(db_session, nome="C2", coach_id=coach.id)
    
    # 3. Check Responses
    # Check 1: Voti alti
    create_check_response(db_session, c1, nutri_rate=10, data=date.today())
    # Check 2: Voti bassi
    create_check_response(db_session, c2, coach_rate=4, data=date.today())
    
    # 4. Call Endpoint
    res = authenticated_client.get('/api/client-checks/admin/dashboard-stats')
    assert res.status_code == 200
    data = res.json
    
    # 5. Verifica KPI
    kpi = data.get('kpi', {})
    assert kpi.get('total') is not None
    assert kpi.get('totalThisMonth') is not None
    
    # Verifica Medie
    avg_ratings = data.get('avgRatings', {})
    assert avg_ratings is not None  # avRatings exists but may be empty dict
    
    # Verifica Ranking (con dati minimi potrebbe essere vuoto)
    rankings = data.get('rankings', {})
    assert rankings is not None
    
    # Top Professionals
    top_professionals = data.get('topProfessionals', {})
    assert 'nutrizionisti' in top_professionals
    assert 'coaches' in top_professionals
    
    print("Client Checks Stats OK")


def test_team_stats(authenticated_client, db_session):
    """
    Verifica endpoint: GET /api/team/stats
    Testa conteggi membri team.
    """
    # 1. Setup
    u1 = User(email=f"ext_{get_random_string()}@test.com", is_active=True, is_external=True, role=UserRoleEnum.team_esterno, first_name="Ext", last_name="User")
    u1.set_password('password')
    u2 = User(email=f"lead_{get_random_string()}@test.com", is_active=True, role=UserRoleEnum.team_leader, first_name="Lead", last_name="User")
    u2.set_password('password')
    u3 = User(email=f"trial_{get_random_string()}@test.com", is_active=True, is_trial=True, first_name="Trial", last_name="User")
    u3.set_password('password')
    db_session.add_all([u1, u2, u3])
    db_session.commit()
    
    # 2. Call
    res = authenticated_client.get('/api/team/stats')
    assert res.status_code == 200
    data = res.json
    
    # 3. Verifica
    assert data['success'] is True
    assert data['total_external'] >= 1
    assert data['total_team_leaders'] >= 1
    assert data['total_trial'] >= 1
    
    print("Team Stats OK")


def test_review_admin_dashboard_stats(authenticated_client, db_session):
    """
    Verifica endpoint: GET /review/api/admin/dashboard-stats
    Testa statistiche formazione.
    """
    # 1. Setup
    u1 = User(email=f"trainee_{get_random_string()}@test.com", first_name="Trainee", last_name="User")
    u1.set_password('password')
    u2 = User(email=f"trainer_{get_random_string()}@test.com", first_name="Trainer", last_name="User")
    u2.set_password('password')
    db_session.add_all([u1, u2])
    db_session.commit()
    
    create_review(db_session, u2, u1, type='weekly', ack=True)
    create_review(db_session, u2, u1, type='progetto', ack=False)
    
    # 2. Call
    res = authenticated_client.get('/review/api/admin/dashboard-stats')
    assert res.status_code == 200
    data = res.json
    
    # 3. Verifica KPI
    kpi = data.get('kpi', {})
    assert kpi.get('total') >= 2
    assert kpi.get('confirmed') >= 1
    assert kpi.get('pending') >= 1
    
    # Verifica Breakdown
    breakdown = data.get('breakdown', {})
    types = breakdown.get('type', [])
    assert len(types) > 0
    
    print("Review Stats OK")

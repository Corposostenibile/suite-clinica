# Blueprint: Team

## Panoramica

Il modulo Team è il sistema HR completo di Corposostenibile Suite. Gestisce dipendenti, ferie, recruiting, certificazioni, OKR personali, weekly report e l'intero ciclo di vita delle risorse umane.

## Funzionalità Principali

### Core HR
- **Anagrafica Dipendenti** con dati completi
- **Gestione Contratti** e documenti HR
- **Organigramma** dinamico e ruoli
- **Certificazioni** con tracking scadenze
- **Gestione Ferie** con workflow approvazione
- **Presenze** e timbrature (TODO)

### Performance Management
- **OKR Personali** allineati con aziendali
- **Weekly Report** strutturati
- **1-on-1 Meetings** tracking
- **Performance Review** (TODO)

### Recruiting (HR Module)
- **Job Openings** con form builder
- **Campagne Recruiting** multi-canale
- **Gestione Candidati** con pipeline
- **Interview Scheduling** integrato
- **Application Tracking** completo

## Struttura File

```
team/
├── __init__.py                  # Blueprint registration
├── routes.py                    # Route principali team
├── forms.py                     # Form dipendenti
├── models/
│   ├── __init__.py
│   └── weekly_report.py         # Modello weekly reports
├── hr/                          # Sotto-modulo recruiting
│   ├── __init__.py
│   ├── routes_dashboard.py     # Dashboard HR
│   ├── routes_openings.py      # Posizioni aperte
│   ├── routes_campaigns.py     # Campagne recruiting
│   ├── routes_candidates.py    # Gestione candidati
│   ├── routes_applications.py  # Application tracking
│   ├── routes_interviews.py    # Colloqui
│   ├── routes_forms.py         # Form builder
│   └── forms.py                # Form recruiting
├── okr_routes.py                # Route OKR personali
├── okr_forms.py                 # Form OKR
├── weekly_report_routes.py      # Route weekly reports
├── weekly_report_forms.py       # Form weekly
├── weekly_report_tasks.py       # Task Celery weekly
├── leave_service.py             # Servizio gestione ferie
├── leave_notifications.py       # Notifiche ferie
├── cli.py                       # Comandi CLI
├── static/
│   └── team/
│       └── hr/
│           └── js/
│               └── opening_form_builder.js
└── templates/
    └── team/
        ├── list.html            # Lista dipendenti
        ├── detail.html          # Profilo dipendente
        ├── dashboard.html       # Dashboard team
        ├── hr/                  # Template recruiting
        ├── leaves/              # Template ferie
        ├── okr/                 # Template OKR
        └── weekly_report/       # Template weekly
```

## Route Principali

### Team Management

| Route | Metodo | Descrizione | Permessi |
|-------|---------|-------------|----------|
| `/team/` | GET | Lista dipendenti | team.view |
| `/team/dashboard` | GET | Dashboard team | team.dashboard |
| `/team/<id>` | GET | Profilo dipendente | team.view |
| `/team/create` | GET/POST | Nuovo dipendente | team.create |
| `/team/<id>/edit` | GET/POST | Modifica dipendente | team.edit |
| `/team/organigramma` | GET | Organigramma | team.view |

### Leave Management

| Route | Metodo | Descrizione | Permessi |
|-------|---------|-------------|----------|
| `/team/leaves/request` | GET/POST | Richiedi ferie | - |
| `/team/leaves/my-requests` | GET | Le mie richieste | - |
| `/team/leaves/approvals` | GET | Da approvare | leave.approve |
| `/team/leaves/report` | GET | Report ferie | leave.report |
| `/team/leaves/settings` | GET/POST | Impostazioni | leave.admin |

### HR & Recruiting

| Route | Metodo | Descrizione | Permessi |
|-------|---------|-------------|----------|
| `/team/hr/` | GET | Dashboard HR | hr.view |
| `/team/hr/openings` | GET | Posizioni aperte | hr.view |
| `/team/hr/opening/create` | GET/POST | Nuova posizione | hr.create |
| `/team/hr/campaigns` | GET | Campagne attive | hr.view |
| `/team/hr/candidates` | GET | Database candidati | hr.view |
| `/team/hr/applications` | GET | Candidature Kanban | hr.view |

## Modelli Database

### Employee

```python
class Employee(TimestampMixin, db.Model):
    __tablename__ = 'employees'
    
    # Dati anagrafici
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    fiscal_code = db.Column(db.String(16), unique=True)
    birth_date = db.Column(db.Date)
    birth_place = db.Column(db.String(100))
    
    # Contatti
    personal_email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    
    # Contratto
    hire_date = db.Column(db.Date, nullable=False)
    contract_type = db.Column(db.Enum(ContractType))
    level = db.Column(db.String(20))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    # HR
    vacation_days = db.Column(db.Integer, default=20)
    remaining_vacation_days = db.Column(db.Float)
    
    # Relazioni
    user = db.relationship('User', back_populates='employee')
    department = db.relationship('Department')
    manager = db.relationship('Employee', remote_side=[id])
    subordinates = db.relationship('Employee', back_populates='manager')
    certifications = db.relationship('Certification')
    leave_requests = db.relationship('LeaveRequest')
    weekly_reports = db.relationship('WeeklyReport')
```

### LeaveRequest

```python
class LeaveRequest(TimestampMixin, db.Model):
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    # Periodo
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_requested = db.Column(db.Float, nullable=False)
    
    # Tipo e stato
    leave_type = db.Column(db.Enum(LeaveType))
    status = db.Column(db.Enum(LeaveStatus), default='pending')
    
    # Approvazione
    approved_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    approved_at = db.Column(db.DateTime)
    
    # Note
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)
```

### WeeklyReport

```python
class WeeklyReport(TimestampMixin, db.Model):
    __tablename__ = 'weekly_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    week_start = db.Column(db.Date, nullable=False)
    
    # Sezioni report
    done_this_week = db.Column(db.JSON)  # Lista attività completate
    planned_next_week = db.Column(db.JSON)  # Piano prossima settimana
    blockers = db.Column(db.JSON)  # Ostacoli/problemi
    highlights = db.Column(db.Text)  # Successi della settimana
    
    # KPI personali
    productivity_score = db.Column(db.Integer)  # 1-10
    wellbeing_score = db.Column(db.Integer)  # 1-10
    
    # Stato
    status = db.Column(db.Enum(ReportStatus), default='draft')
    submitted_at = db.Column(db.DateTime)
```

## Configurazione

```bash
# Ferie
DEFAULT_VACATION_DAYS=20
VACATION_YEAR_START=01-01  # Inizio anno ferie
MAX_CONSECUTIVE_DAYS=15    # Max giorni consecutivi

# Weekly Reports
WEEKLY_REPORT_DAY=5  # Venerdì (0=Lunedì)
WEEKLY_REPORT_REMINDER_HOUR=15  # Ore 15:00
WEEKLY_REPORT_DEADLINE_HOUR=18  # Deadline ore 18:00

# HR/Recruiting
MAX_APPLICATIONS_PER_OPENING=500
APPLICATION_EXPIRY_DAYS=180
INTERVIEW_SLOT_DURATION=60  # minuti

# Certificazioni
CERTIFICATION_EXPIRY_WARNING_DAYS=60,30,7
```

## Utilizzo

### Gestione Dipendenti

```python
from corposostenibile.models import Employee

# Crea nuovo dipendente
employee = Employee(
    first_name="Mario",
    last_name="Rossi",
    fiscal_code="RSSMRA80A01H501Z",
    hire_date=date.today(),
    department_id=1,
    vacation_days=20
)

# Assegna manager
employee.manager = manager_employee

# Crea account utente collegato
user = User(email=f"{first_name.lower()}.{last_name.lower()}@company.com")
employee.user = user
```

### Gestione Ferie

```python
from corposostenibile.blueprints.team.leave_service import LeaveService

service = LeaveService()

# Richiedi ferie
request = service.create_leave_request(
    employee_id=current_user.employee.id,
    start_date=date(2024, 7, 15),
    end_date=date(2024, 7, 26),
    leave_type='vacation',
    reason='Vacanze estive'
)

# Approva ferie (manager)
service.approve_request(
    request_id=request.id,
    approver_id=manager.id,
    notes='Approvato. Buone vacanze!'
)

# Check disponibilità
available = service.check_availability(
    employee_id=employee.id,
    start_date=start,
    end_date=end
)
```

### Weekly Reports

```python
# Crea weekly report
report = WeeklyReport(
    employee_id=current_user.employee.id,
    week_start=get_week_start(),
    done_this_week=[
        {'task': 'Completato feature X', 'impact': 'high'},
        {'task': 'Fix bug critico Y', 'impact': 'medium'}
    ],
    planned_next_week=[
        {'task': 'Iniziare sviluppo feature Z', 'priority': 'high'},
        {'task': 'Code review PR #123', 'priority': 'medium'}
    ],
    productivity_score=8,
    wellbeing_score=7
)
```

## HR & Recruiting

### Form Builder Dinamico

```javascript
// opening_form_builder.js
const formBuilder = new OpeningFormBuilder({
    container: '#form-builder',
    fields: [
        {type: 'text', name: 'full_name', label: 'Nome completo', required: true},
        {type: 'email', name: 'email', label: 'Email', required: true},
        {type: 'file', name: 'cv', label: 'CV', accept: '.pdf,.doc,.docx'},
        {type: 'textarea', name: 'motivation', label: 'Lettera motivazionale'},
        {type: 'select', name: 'experience', label: 'Anni esperienza', options: ['0-2', '3-5', '5+']}
    ]
});
```

### Pipeline Candidati

```python
# Stati candidatura
class ApplicationStatus(enum.Enum):
    NEW = 'new'
    SCREENING = 'screening'
    INTERVIEW_1 = 'interview_1'
    INTERVIEW_2 = 'interview_2'
    OFFER = 'offer'
    HIRED = 'hired'
    REJECTED = 'rejected'

# Muovi candidato nella pipeline
application.status = ApplicationStatus.INTERVIEW_1
application.add_note('Passato screening iniziale. Schedulare colloquio tecnico.')
```

## Comandi CLI

```bash
# Import dipendenti da CSV
flask team import-employees --file dipendenti.csv

# Genera weekly report reminder
flask team send-weekly-reminders

# Report ferie annuale
flask team vacation-report --year 2024 --format pdf

# Pulizia candidature vecchie
flask team cleanup-applications --older-than 180

# Export organigramma
flask team export-org-chart --format png
```

## Testing

```python
def test_leave_request_workflow(client, db_session):
    # Dipendente richiede ferie
    employee = EmployeeFactory()
    
    data = {
        'start_date': '2024-07-15',
        'end_date': '2024-07-20',
        'leave_type': 'vacation',
        'reason': 'Summer holiday'
    }
    
    response = client.post('/team/leaves/request', data=data)
    assert response.status_code == 302
    
    # Manager approva
    request = LeaveRequest.query.first()
    assert request.status == 'pending'
    
    login_as(request.employee.manager.user)
    response = client.post(f'/team/leaves/approve/{request.id}')
    
    request = LeaveRequest.query.first()
    assert request.status == 'approved'
    
    # Giorni ferie aggiornati
    assert employee.remaining_vacation_days < 20
```

## Best Practices

1. **Privacy**
   - Dati sensibili criptati
   - GDPR compliance
   - Audit log accessi

2. **Workflow**
   - Approvazioni gerarchiche
   - Notifiche automatiche
   - Deleghe temporanee

3. **Performance**
   - Cache organigramma
   - Lazy loading subordinati
   - Batch import/export

## Estensioni Future

- [ ] Timbrature e presenze
- [ ] Integrazione buste paga
- [ ] Performance review 360°
- [ ] Learning management
- [ ] Benefits management
- [ ] App mobile dipendenti
- [ ] Chatbot HR
- [ ] Analytics predittive turnover

## Troubleshooting

### Calcolo ferie errato
- Verifica configurazione anno
- Controlla giorni festivi
- Ricalcola manualmente: `flask team recalc-vacation`

### Weekly report non inviati
- Verifica Celery attivo
- Controlla timezone
- Log in `logs/celery.log`

### Form builder non salva
- Verifica permessi cartella upload
- Limite dimensione file
- Console browser per errori JS
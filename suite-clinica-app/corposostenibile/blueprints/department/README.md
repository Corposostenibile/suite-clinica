# Blueprint: Department

## Panoramica

Il blueprint **department** gestisce la struttura organizzativa aziendale, i dipartimenti, i task di reparto e gli OKR (Objectives and Key Results) dipartimentali. È il centro di controllo per la pianificazione strategica e il monitoraggio delle performance.

## Funzionalità Principali

- **Gestione Dipartimenti** con gerarchia e responsabili
- **Sistema OKR** completo (Objectives & Key Results)
- **Task Management** con Kanban board
- **Dashboard Performance** real-time
- **Organigramma** dinamico e interattivo
- **Report OKR** settimanali e trimestrali
- **Allineamento** obiettivi aziendali-dipartimentali
- **Tracking Progress** automatico

## Struttura File

```
department/
├── __init__.py          # Blueprint registration
├── routes.py            # Route gestione dipartimenti
├── forms.py             # Form dipartimenti
├── okr_routes.py        # Route sistema OKR
├── okr_forms.py         # Form OKR
├── helpers.py           # Utility functions
├── static/
│   └── js/
│       └── kanban.js    # Kanban board interattiva
└── templates/
    ├── department/
    │   ├── list.html    # Lista dipartimenti
    │   ├── detail.html  # Dettaglio dipartimento
    │   ├── form.html    # Form creazione/edit
    │   ├── organigramma.html  # Vista organigramma
    │   └── okr/
    │       ├── dashboard.html      # Dashboard OKR
    │       ├── form.html           # Form OKR
    │       ├── weekly_update.html  # Update settimanale
    │       └── _okr_card.html      # Component OKR card
    └── task/
        └── form.html    # Form task
```

## Route Principali

### Dipartimenti

| Route | Metodo | Descrizione | Permessi |
|-------|---------|-------------|----------|
| `/department/` | GET | Lista dipartimenti | department.view |
| `/department/create` | GET/POST | Nuovo dipartimento | department.create |
| `/department/<id>` | GET | Dettaglio con OKR | department.view |
| `/department/<id>/edit` | GET/POST | Modifica dipartimento | department.edit |
| `/department/organigramma` | GET | Vista organigramma | department.view |

### OKR Management

| Route | Metodo | Descrizione | Permessi |
|-------|---------|-------------|----------|
| `/department/okr/` | GET | Dashboard OKR globale | okr.view |
| `/department/okr/create` | GET/POST | Nuovo OKR | okr.create |
| `/department/okr/<id>` | GET | Dettaglio OKR | okr.view |
| `/department/okr/<id>/update` | GET/POST | Update progress | okr.update |
| `/department/okr/<id>/weekly` | GET/POST | Update settimanale | okr.update |

### Task Management

| Route | Metodo | Descrizione | Permessi |
|-------|---------|-------------|----------|
| `/department/<id>/tasks` | GET | Kanban board tasks | department.view |
| `/department/task/create` | POST | Crea task | task.create |
| `/department/task/<id>/move` | POST | Sposta task | task.update |
| `/department/task/<id>/assign` | POST | Assegna task | task.assign |

## Modelli Database

### Department

```python
class Department(TimestampMixin, db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(10), unique=True)  # Es: IT, HR, SALES
    description = db.Column(db.Text)
    
    # Gerarchia
    parent_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    level = db.Column(db.Integer, default=0)
    
    # Responsabile
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    deputy_manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    # Budget e risorse
    annual_budget = db.Column(db.Numeric(12, 2))
    headcount_target = db.Column(db.Integer)
    
    # Stato
    is_active = db.Column(db.Boolean, default=True)
    
    # Relazioni
    employees = db.relationship('Employee', back_populates='department')
    okrs = db.relationship('OKR', back_populates='department')
    tasks = db.relationship('Task', back_populates='department')
    children = db.relationship('Department', backref=db.backref('parent', remote_side=[id]))
```

### OKR (Objectives and Key Results)

```python
class OKR(TimestampMixin, db.Model):
    __tablename__ = 'okrs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Ownership
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    # Objective
    objective = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Timing
    quarter = db.Column(db.String(7))  # Es: 2024-Q1
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    # Type & Priority
    okr_type = db.Column(db.Enum(OKRType))  # company, department, team
    priority = db.Column(db.Enum(Priority))  # P0, P1, P2
    
    # Progress
    progress = db.Column(db.Float, default=0.0)  # 0-100
    confidence = db.Column(db.Float, default=0.7)  # 0-1
    status = db.Column(db.Enum(OKRStatus))  # draft, active, completed, cancelled
    
    # Alignment
    parent_okr_id = db.Column(db.Integer, db.ForeignKey('okrs.id'))
    
    # Relazioni
    key_results = db.relationship('KeyResult', back_populates='okr', cascade='all, delete-orphan')
    updates = db.relationship('OKRUpdate', back_populates='okr')
    tasks = db.relationship('Task', back_populates='okr')
```

### KeyResult

```python
class KeyResult(TimestampMixin, db.Model):
    __tablename__ = 'key_results'
    
    id = db.Column(db.Integer, primary_key=True)
    okr_id = db.Column(db.Integer, db.ForeignKey('okrs.id'))
    
    # Definizione
    description = db.Column(db.String(200), nullable=False)
    
    # Misurazione
    metric_type = db.Column(db.Enum(MetricType))  # number, percentage, boolean
    start_value = db.Column(db.Float, default=0)
    target_value = db.Column(db.Float, nullable=False)
    current_value = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20))  # €, %, users, etc
    
    # Progress
    progress = db.Column(db.Float, default=0.0)  # Auto-calculated
    
    # Tracking
    measurement_frequency = db.Column(db.Enum(Frequency))  # daily, weekly, monthly
    last_updated = db.Column(db.DateTime)
```

### Task

```python
class Task(TimestampMixin, db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Ownership
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    created_by_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    
    # Collegamenti
    okr_id = db.Column(db.Integer, db.ForeignKey('okrs.id'))
    key_result_id = db.Column(db.Integer, db.ForeignKey('key_results.id'))
    
    # Stato Kanban
    status = db.Column(db.Enum(TaskStatus))  # backlog, todo, in_progress, review, done
    priority = db.Column(db.Enum(Priority))
    
    # Timing
    due_date = db.Column(db.Date)
    estimated_hours = db.Column(db.Float)
    actual_hours = db.Column(db.Float)
    
    # Tags
    tags = db.Column(db.JSON)  # ['bug', 'feature', 'urgent']
```

## Configurazione

```bash
# OKR Settings
OKR_QUARTERS_AHEAD=4  # Pianifica fino a 4 quarter avanti
OKR_UPDATE_FREQUENCY=weekly  # weekly, biweekly, monthly
OKR_CONFIDENCE_THRESHOLD=0.5  # Sotto questa soglia = at risk

# Task Management
KANBAN_COLUMNS=backlog,todo,in_progress,review,done
TASK_AUTO_ARCHIVE_DAYS=90  # Archivia task completati dopo 90gg

# Performance
CACHE_ORGANIGRAMMA_TTL=3600  # 1 ora
DASHBOARD_REFRESH_INTERVAL=300  # 5 minuti
```

## Utilizzo

### Gestione OKR

```python
from corposostenibile.models import OKR, KeyResult

# Crea OKR aziendale
company_okr = OKR(
    objective="Aumentare fatturato del 30%",
    quarter="2024-Q1",
    okr_type=OKRType.COMPANY,
    priority=Priority.P0
)

# Aggiungi Key Results
kr1 = KeyResult(
    description="Acquisire 50 nuovi clienti enterprise",
    metric_type=MetricType.NUMBER,
    start_value=120,
    target_value=170,
    unit="clienti"
)
company_okr.key_results.append(kr1)

# Crea OKR dipartimentale allineato
sales_okr = OKR(
    objective="Potenziare team vendite per crescita",
    parent_okr=company_okr,
    department_id=sales_dept.id,
    okr_type=OKRType.DEPARTMENT
)
```

### Update Progress

```python
# Update manuale
kr1.current_value = 145
kr1.progress = ((145 - 120) / (170 - 120)) * 100  # 50%

# Update via service
from corposostenible.blueprints.department.services import OKRService

service = OKRService()
service.update_key_result(
    kr_id=kr1.id,
    current_value=145,
    notes="15 nuovi clienti questo mese"
)

# Weekly update
update = service.create_weekly_update(
    okr_id=okr.id,
    updates={
        'progress': 65,
        'confidence': 0.8,
        'blockers': ['Manca personale vendite'],
        'next_steps': ['Assumere 2 sales rep']
    }
)
```

### Kanban Board

```javascript
// kanban.js - Drag & drop tasks
const kanban = new KanbanBoard({
    container: '#kanban-board',
    columns: ['backlog', 'todo', 'in_progress', 'review', 'done'],
    onTaskMove: async (taskId, newStatus) => {
        await fetch(`/department/task/${taskId}/move`, {
            method: 'POST',
            body: JSON.stringify({status: newStatus})
        });
    }
});
```

## Dashboard e Report

### KPI Dipartimentali

1. **OKR Metrics**
   - Progress medio OKR
   - Confidence score
   - OKR at risk
   - Completion rate

2. **Team Performance**
   - Task completion rate
   - Velocity trend
   - Workload distribution
   - Deadline adherence

3. **Resource Utilization**
   - Budget vs actual
   - Headcount vs target
   - Productivity metrics

### Report Automatici

```python
# Report trimestrale OKR
flask department okr-report --quarter 2024-Q1 --format pdf

# Export organigramma
flask department export-org-chart --format svg

# Analisi performance
flask department performance-analysis --dept IT --period 2024-Q1
```

## API Endpoints

```bash
# Get department OKRs
GET /api/v1/departments/5/okrs?quarter=2024-Q1

# Update key result
PUT /api/v1/key-results/123
{
    "current_value": 145,
    "notes": "Aggiornamento settimanale"
}

# Kanban board state
GET /api/v1/departments/5/kanban

# Create task
POST /api/v1/tasks
{
    "title": "Implementare feature X",
    "department_id": 5,
    "okr_id": 10,
    "assigned_to_id": 25
}
```

## Testing

```python
def test_okr_cascade(db_session):
    # Company OKR
    company_okr = OKR(
        objective="Grow revenue 30%",
        okr_type=OKRType.COMPANY
    )
    
    # Department OKR aligned
    dept_okr = OKR(
        objective="Increase sales team",
        parent_okr=company_okr,
        okr_type=OKRType.DEPARTMENT
    )
    
    # Test cascade
    assert dept_okr.parent_okr == company_okr
    assert company_okr in dept_okr.get_ancestors()
    
def test_progress_calculation(db_session):
    kr = KeyResult(
        start_value=100,
        target_value=200,
        current_value=150
    )
    
    assert kr.calculate_progress() == 50.0
```

## Best Practices

1. **OKR Planning**
   - Max 3-5 OKR per quarter
   - 3-5 Key Results per OKR
   - Misurabile e time-bound
   - Stretch ma raggiungibili

2. **Task Management**
   - WIP limits per colonna
   - Daily standup integration
   - Link sempre a OKR
   - Time tracking accurato

3. **Performance**
   - Cache dashboard pesanti
   - Aggregazioni async
   - Pagination sempre
   - Lazy load sub-departments

## Estensioni Future

- [ ] AI per suggerimenti OKR
- [ ] Integrazione project management
- [ ] Predictive analytics
- [ ] Skill matrix team
- [ ] Resource planning
- [ ] Budget forecasting
- [ ] 360° feedback
- [ ] Gamification OKR

## Troubleshooting

### OKR progress non si aggiorna
- Verifica formula calcolo
- Check job Celery
- Ricalcola: `flask okr recalculate`

### Organigramma lento
- Aumenta cache TTL
- Limita profondità
- Usa vista semplificata

### Kanban non salva
- Verifica permessi
- Check console browser
- WebSocket attivo?
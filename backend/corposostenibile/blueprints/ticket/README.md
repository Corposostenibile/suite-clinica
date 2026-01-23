# Blueprint: Ticket

## Panoramica
Il blueprint **ticket** implementa un sistema completo di ticketing aziendale per Corposostenibile Suite, permettendo la gestione di richieste interne ed esterne, con workflow di approvazione, assegnazione e collaborazione inter-dipartimentale.

## Funzionalità Principali

### 1. Creazione Ticket
- **Form pubblico** per richieste esterne
- **Form autenticato** per richieste interne
- **Upload allegati** multipli
- **Categorizzazione** per dipartimento
- **Priorità e urgenza** configurabili

### 2. Gestione Workflow
- **Stati personalizzabili** (nuovo, in lavorazione, risolto, etc.)
- **Assegnazione** a membri specifici
- **Escalation automatica** per urgenze
- **Timeline completa** modifiche stato
- **SLA tracking** tempi risposta

### 3. Collaborazione
- **Commenti e discussioni** su ticket
- **Condivisione** tra dipartimenti
- **Mention utenti** nei commenti
- **Notifiche email** automatiche
- **Activity log** completo

### 4. Dashboard e Analytics
- **Dashboard personale** "I miei ticket"
- **Vista dipartimentale** per manager
- **KPI e metriche** performance
- **Report esportabili** Excel/PDF
- **Grafici trend** e statistiche

### 5. Integrazioni
- **Cliente tracking** collegamento a clienti
- **Lead management** per nuovi contatti
- **Email gateway** creazione da email
- **API REST** per integrazioni esterne
- **Webhook** per automazioni

## Struttura File

```
ticket/
├── __init__.py              # Blueprint configuration
├── routes.py                # Route handlers principali
├── public_routes.py         # Routes pubbliche (no auth)
├── api_routes.py           # API endpoints
├── forms.py                # WTForms validazione
├── services.py             # Business logic
├── email_service.py        # Servizio notifiche
├── email_templates.py      # Template email HTML
├── permissions.py          # Sistema autorizzazioni
├── helpers.py              # Utility functions
├── timezone_utils.py       # Gestione timezone
├── templates/
│   └── ticket/
│       ├── dashboard.html      # Dashboard principale
│       ├── create.html         # Form creazione
│       ├── detail.html         # Dettaglio ticket
│       ├── edit.html           # Modifica ticket
│       ├── my_tickets.html     # I miei ticket
│       ├── department.html     # Vista dipartimento
│       ├── public/
│       │   ├── form.html       # Form pubblico
│       │   └── success.html    # Conferma invio
│       └── partials/
│           ├── ticket_card.html
│           ├── comment_thread.html
│           └── status_timeline.html
└── static/
    ├── css/
    │   ├── ticket.css
    │   └── public-form.css
    └── js/
        ├── ticket.js           # Interazioni UI
        ├── comments.js         # Sistema commenti
        └── dashboard.js        # Charts e filtri
```

## API Routes

### Ticket Management
| Route | Metodo | Descrizione | Autenticazione |
|-------|--------|-------------|----------------|
| `/tickets/` | GET | Dashboard ticket | Sì |
| `/tickets/create` | GET, POST | Crea nuovo ticket | Sì |
| `/tickets/<id>` | GET | Dettaglio ticket | Sì |
| `/tickets/<id>/edit` | GET, POST | Modifica ticket | Sì |
| `/tickets/<id>/delete` | POST | Elimina ticket | Sì |
| `/tickets/my-tickets` | GET | I miei ticket | Sì |
| `/tickets/department/<id>` | GET | Ticket dipartimento | Sì |

### Workflow Actions
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/tickets/<id>/assign` | POST | Assegna ticket |
| `/tickets/<id>/change-status` | POST | Cambia stato |
| `/tickets/<id>/escalate` | POST | Escalation urgenza |
| `/tickets/<id>/share` | POST | Condividi con dipartimento |
| `/tickets/<id>/merge` | POST | Unisci ticket duplicati |

### Comments & Attachments
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/tickets/<id>/comment` | POST | Aggiungi commento |
| `/tickets/comment/<id>/edit` | POST | Modifica commento |
| `/tickets/<id>/attach` | POST | Upload allegato |
| `/tickets/attachment/<id>/download` | GET | Download allegato |

### Public Routes (No Auth)
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/public/ticket/form` | GET | Form pubblico |
| `/public/ticket/submit` | POST | Invia ticket pubblico |
| `/public/ticket/success` | GET | Pagina conferma |
| `/public/ticket/status/<code>` | GET | Verifica stato |

### API Endpoints
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/api/tickets/search` | GET | Ricerca ticket |
| `/api/tickets/stats` | GET | Statistiche |
| `/api/tickets/export` | GET | Export dati |
| `/api/tickets/<id>/timeline` | GET | Timeline eventi |
| `/api/tickets/kpi` | GET | KPI dashboard |

## Modelli Database

### Ticket
```python
- id: Integer (PK)
- ticket_number: String(20) - unique, auto-generated
- title: String(200) - required
- description: Text - required
- department_id: Integer (FK)
- requester_first_name: String(100)
- requester_last_name: String(100)
- requester_email: String(120)
- requester_department: String(100)
- status: Enum(TicketStatusEnum)
- urgency: Enum(TicketUrgencyEnum)
- assigned_to_id: Integer (FK -> users.id)
- created_by_id: Integer (FK -> users.id)
- cliente_id: BigInteger (FK -> clienti.cliente_id)
- related_client_name: String(200) - for leads
- resolution: Text
- resolved_at: DateTime
- created_at: DateTime
- updated_at: DateTime

# Relationships
- department: Department
- assigned_to: User
- created_by: User
- cliente: Cliente
- comments: TicketComment[]
- attachments: TicketAttachment[]
- status_changes: TicketStatusChange[]
- shared_departments: Department[] (many-to-many)
```

### TicketComment
```python
- id: Integer (PK)
- ticket_id: Integer (FK)
- user_id: Integer (FK)
- comment: Text
- is_internal: Boolean - solo staff
- created_at: DateTime
- updated_at: DateTime

# Relationships
- ticket: Ticket
- user: User
- mentions: User[] (many-to-many)
```

### TicketAttachment
```python
- id: Integer (PK)
- ticket_id: Integer (FK)
- filename: String(255)
- file_path: String(500)
- file_size: Integer
- mime_type: String(100)
- uploaded_by_id: Integer (FK)
- uploaded_at: DateTime

# Relationships
- ticket: Ticket
- uploaded_by: User
```

### TicketStatusChange
```python
- id: Integer (PK)
- ticket_id: Integer (FK)
- old_status: Enum(TicketStatusEnum)
- new_status: Enum(TicketStatusEnum)
- changed_by_id: Integer (FK)
- reason: Text
- changed_at: DateTime

# Relationships
- ticket: Ticket
- changed_by: User
```

## Services

### TicketService
```python
# Creazione e gestione
create_ticket(data) -> Ticket
update_ticket(ticket_id, data) -> Ticket
delete_ticket(ticket_id) -> bool

# Workflow
assign_ticket(ticket_id, user_id) -> bool
change_status(ticket_id, new_status, reason) -> TicketStatusChange
escalate_ticket(ticket_id) -> bool
merge_tickets(source_id, target_id) -> bool

# Collaborazione
add_comment(ticket_id, user_id, comment, is_internal) -> TicketComment
share_with_department(ticket_id, department_id) -> bool

# Notifiche
send_creation_notification(ticket) -> bool
send_assignment_notification(ticket, assignee) -> bool
send_status_change_notification(ticket, change) -> bool
```

### TicketKPIService
```python
# Metriche
get_department_stats(department_id) -> dict
get_user_performance(user_id) -> dict
get_resolution_times() -> dict
get_sla_compliance() -> dict

# Report
generate_monthly_report() -> BytesIO
export_tickets_excel(filters) -> BytesIO
```

### TicketEmailService
```python
# Email gateway
process_incoming_email(email_data) -> Ticket
send_notification(ticket, event_type, recipients) -> bool
generate_ticket_digest() -> str
```

## Sistema Permessi

### Ruoli e Autorizzazioni
```python
# Admin
- Accesso completo a tutti i ticket
- Modifica qualsiasi ticket
- Elimina ticket
- Vista analytics globale

# Department Head
- Gestione ticket proprio dipartimento
- Assegnazione membri team
- Vista KPI dipartimento
- Approvazione escalation

# Department Member
- Vista ticket dipartimento
- Gestione ticket assegnati
- Creazione commenti
- No eliminazione

# User (generico)
- Creazione ticket
- Vista propri ticket
- Commenti su propri ticket
```

### Decoratori Permessi
```python
@can_view_ticket(ticket)
@can_edit_ticket(ticket)
@can_delete_ticket(ticket)
@can_share_ticket(ticket)
```

## Configurazione

### Ticket Settings
```python
# Numerazione ticket
TICKET_NUMBER_PREFIX = 'TK'
TICKET_NUMBER_PADDING = 6  # TK000001

# Stati disponibili
TICKET_STATUSES = [
    'nuovo',
    'in_lavorazione',
    'in_attesa',
    'risolto',
    'chiuso',
    'annullato'
]

# SLA (ore)
TICKET_SLA = {
    'critica': 2,
    'alta': 8,
    'normale': 24,
    'bassa': 72
}

# Upload
TICKET_ATTACHMENT_MAX_SIZE = 10 * 1024 * 1024  # 10MB
TICKET_ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx',
    'png', 'jpg', 'jpeg', 'gif',
    'txt', 'csv', 'zip'
}
```

### Email Settings
```python
TICKET_EMAIL_ENABLED = True
TICKET_EMAIL_FROM = 'tickets@corposostenibile.com'
TICKET_EMAIL_GATEWAY = 'support@corposostenibile.com'
TICKET_NOTIFICATION_TEMPLATE = 'email/ticket_notification.html'
```

## Testing

### Test Suite
```python
def test_ticket_creation():
    """Test creazione ticket con validazione"""

def test_workflow_transitions():
    """Test cambio stati workflow"""

def test_permissions():
    """Test autorizzazioni per ruolo"""

def test_email_notifications():
    """Test invio notifiche email"""

def test_public_form():
    """Test form pubblico senza auth"""

def test_api_endpoints():
    """Test API REST"""
```

## Best Practices

1. **Titoli descrittivi** per ricerca efficace
2. **Categorizzazione corretta** per routing
3. **Priorità realistica** per gestione SLA
4. **Commenti dettagliati** per storico
5. **Allegati compressi** per performance
6. **Chiusura tempestiva** ticket risolti

## Analytics e KPI

### Metriche Principali
- **Tempo medio risoluzione** per priorità
- **Ticket per dipartimento** e trend
- **SLA compliance** percentuale
- **First response time** medio
- **Customer satisfaction** (se abilitato)
- **Backlog aging** ticket aperti

### Dashboard Widgets
- Ticket aperti per stato
- Trend ultimi 30 giorni
- Top requesters
- Performance team
- Heatmap orari creazione

## Migliorie Future

1. **AI Integration**
   - Auto-categorizzazione ticket
   - Suggerimenti risposte
   - Sentiment analysis

2. **Automazioni**
   - Auto-assignment basato su regole
   - Escalation automatica SLA
   - Merge duplicati intelligente

3. **Customer Portal**
   - Self-service KB
   - Tracking pubblico ticket
   - Live chat integration

4. **Mobile App**
   - Gestione ticket mobile
   - Push notifications
   - Quick actions

5. **Advanced Analytics**
   - Predictive analytics
   - Root cause analysis
   - Team workload balancing

## Troubleshooting

### Problema: Email non inviate
```python
# Verifica configurazione
from corposostenibile.blueprints.ticket.services import TicketEmailService
service = TicketEmailService()
service.test_connection()
```

### Problema: Upload fallisce
```bash
# Verifica permessi cartella
ls -la uploads/tickets/
# Deve essere scrivibile da web server
```

### Problema: Numerazione ticket duplicata
```sql
-- Reset sequenza
SELECT MAX(CAST(SUBSTRING(ticket_number, 3) AS INTEGER)) FROM tickets;
-- Aggiorna sequence se necessario
```

## Contatti

**Maintainer**: Team DevOps Corposostenibile
**Ultimo aggiornamento**: Settembre 2024
**Versione**: 2.5.0
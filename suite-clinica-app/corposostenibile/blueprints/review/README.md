# Blueprint: Review (Training)

## Panoramica
Il blueprint **review** (chiamato "Training" nell'interfaccia) gestisce il sistema di valutazioni e feedback tra membri del team, permettendo ai responsabili di fornire recensioni costruttive ai propri collaboratori e facilitando la comunicazione bidirezionale.

## Funzionalità Principali

### 1. Sistema Review
- **Creazione review** da parte di head/admin
- **Bozze salvabili** prima della pubblicazione
- **Notifiche email** automatiche
- **Conferma lettura** obbligatoria
- **Storico completo** delle valutazioni

### 2. Comunicazione Bidirezionale
- **Messaggi** su ogni review
- **Thread discussione** per chiarimenti
- **Notifiche real-time** nuovi messaggi
- **Indicatori non letti** per messaggi

### 3. Review Requests
- **Richieste review** da parte dei membri
- **Approvazione/rifiuto** da responsabile
- **Note e motivazioni** per richieste
- **Tracking stato** richieste

### 4. Gestione Permessi
- **Admin**: accesso completo a tutte le review
- **Head**: gestione membri proprio dipartimento
- **Membri**: solo proprie review e richieste
- **Eccezioni custom** configurabili

### 5. Analytics e Report
- **Dashboard riepilogativa** per manager
- **Statistiche** review per periodo
- **Export dati** per HR
- **Metriche performance** team

## Struttura File

```
review/
├── __init__.py          # Blueprint configuration
├── routes.py            # Route handlers
├── forms.py             # WTForms per review/messaggi
├── email_service.py     # Servizio notifiche email
├── helpers.py           # Utility functions
├── filters.py           # Filtri Jinja custom
├── templates/
│   └── review/
│       ├── index.html           # Lista membri/review
│       ├── detail.html          # Dettaglio review membro
│       ├── create.html          # Form creazione review
│       ├── edit.html            # Modifica review
│       ├── view.html            # Vista singola review
│       ├── messages.html        # Thread messaggi
│       ├── requests/
│       │   ├── list.html        # Lista richieste
│       │   ├── create.html      # Nuova richiesta
│       │   └── respond.html     # Rispondi a richiesta
│       └── partials/
│           ├── review_card.html
│           ├── message_thread.html
│           └── stats_widget.html
└── static/
    ├── css/
    │   └── review.css
    └── js/
        ├── review.js            # Interazioni UI
        └── messages.js          # Chat real-time
```

## API Routes

### Review Routes
| Route | Metodo | Descrizione | Permessi |
|-------|--------|-------------|----------|
| `/review/` | GET | Dashboard review | Login required |
| `/review/member/<id>` | GET | Review di un membro | Can view member |
| `/review/create/<member_id>` | GET, POST | Crea review | Can write review |
| `/review/<id>` | GET | Vista singola review | Can view review |
| `/review/<id>/edit` | GET, POST | Modifica review | Author/Admin |
| `/review/<id>/delete` | POST | Elimina review | Author/Admin |
| `/review/<id>/acknowledge` | POST | Conferma lettura | Reviewee |
| `/review/<id>/publish` | POST | Pubblica bozza | Author |

### Message Routes
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/review/<id>/messages` | GET | Thread messaggi |
| `/review/<id>/message/send` | POST | Invia messaggio |
| `/review/message/<id>/edit` | POST | Modifica messaggio |
| `/review/message/<id>/delete` | POST | Elimina messaggio |
| `/review/messages/mark-read` | POST | Marca come letti |

### Request Routes
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/review/requests` | GET | Lista richieste review |
| `/review/request/create` | GET, POST | Nuova richiesta |
| `/review/request/<id>` | GET | Dettaglio richiesta |
| `/review/request/<id>/respond` | POST | Rispondi a richiesta |
| `/review/request/<id>/cancel` | POST | Annulla richiesta |

### API Endpoints
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/api/review/stats/<user_id>` | GET | Statistiche utente |
| `/api/review/unread-count` | GET | Conteggio non letti |
| `/api/review/export` | GET | Export dati (Admin) |

## Modelli Database

### Review
```python
- id: Integer (PK)
- reviewer_id: Integer (FK -> users.id)
- reviewee_id: Integer (FK -> users.id)
- title: String(200)
- content: Text - contenuto review
- rating: Integer - valutazione 1-5
- period_start: Date
- period_end: Date
- is_draft: Boolean - default True
- published_at: DateTime
- deleted_at: DateTime - soft delete
- created_at: DateTime
- updated_at: DateTime

# Relationships
- reviewer: User
- reviewee: User
- acknowledgment: ReviewAcknowledgment
- messages: ReviewMessage[]
```

### ReviewAcknowledgment
```python
- id: Integer (PK)
- review_id: Integer (FK) - unique
- acknowledged_at: DateTime
- ip_address: String(45)
- user_agent: String(200)
- notes: Text - note opzionali

# Relationships
- review: Review
```

### ReviewMessage
```python
- id: Integer (PK)
- review_id: Integer (FK)
- sender_id: Integer (FK -> users.id)
- message: Text
- is_read: Boolean - default False
- read_at: DateTime
- edited_at: DateTime
- deleted_at: DateTime
- created_at: DateTime

# Relationships
- review: Review
- sender: User
```

### ReviewRequest
```python
- id: Integer (PK)
- requester_id: Integer (FK -> users.id)
- reviewer_id: Integer (FK -> users.id)
- reason: Text - motivazione richiesta
- status: String(20) - pending, approved, rejected
- response: Text - risposta del reviewer
- responded_at: DateTime
- created_at: DateTime

# Relationships
- requester: User
- reviewer: User
```

## Sistema Permessi

### Regole di Accesso
```python
def can_view_member_reviews(user, member):
    """
    - Admin: può vedere tutto
    - Head: può vedere membri del suo dipartimento
    - Membro: può vedere solo le proprie
    - Eccezioni custom configurabili
    """

def can_write_review(user, member):
    """
    - Admin: può scrivere a tutti
    - Head: può scrivere ai membri del suo dipartimento
    - No self-review
    """

def is_department_head(user):
    """Verifica se utente è head di dipartimento"""
```

### Eccezioni Speciali
```python
# Esempio: User #2 può gestire User #64
if user.id == 2 and member.id == 64:
    return True
```

## Email Notifications

### Template Email
```python
send_review_notification(review)
    # Invia email al reviewee con link alla review

send_message_notification(message)
    # Notifica nuovo messaggio nella discussione

send_review_request_notification(request)
    # Notifica richiesta review al responsabile

send_review_request_response_notification(request)
    # Notifica risposta alla richiesta
```

### Configurazione SMTP
```python
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
REVIEW_NOTIFICATION_ENABLED = True
```

## Forms e Validazione

### ReviewForm
```python
- title: StringField (required, max 200)
- content: TextAreaField (required)
- rating: SelectField (1-5)
- period_start: DateField
- period_end: DateField
- is_draft: BooleanField
```

### ReviewMessageForm
```python
- message: TextAreaField (required, max 5000)
- parent_id: HiddenField (per thread)
```

### ReviewRequestForm
```python
- reviewer_id: SelectField (lista responsabili)
- reason: TextAreaField (required)
```

## JavaScript Interattività

### Auto-save Bozze
```javascript
// Salvataggio automatico ogni 30 secondi
setInterval(function() {
    if (isDraft && hasChanges) {
        saveReviewDraft();
    }
}, 30000);
```

### Notifiche Real-time
```javascript
// WebSocket per messaggi
socket.on('new_message', function(data) {
    if (data.review_id === currentReviewId) {
        appendMessage(data);
        showNotification('Nuovo messaggio');
    }
});
```

## Testing

### Test Suite
```python
def test_review_creation():
    """Test creazione review con permessi"""

def test_acknowledgment_flow():
    """Test conferma lettura"""

def test_message_thread():
    """Test discussione su review"""

def test_request_lifecycle():
    """Test richiesta review completa"""

def test_permissions():
    """Test accessi per ruolo"""
```

## Best Practices

1. **Review costruttive** con esempi concreti
2. **Periodicità regolare** (trimestrale consigliata)
3. **Bozze salvate** prima di pubblicare
4. **Follow-up** su punti di miglioramento
5. **Documentazione** obiettivi raggiunti

## Analytics e KPI

### Metriche Tracked
- **Review frequency** per team
- **Response time** acknowledgment
- **Message engagement** rate
- **Request approval** rate
- **Average rating** per dipartimento

### Report Disponibili
- Export Excel review per periodo
- Statistiche dipartimento
- Timeline individuale
- Trend performance

## Migliorie Future

1. **360° Feedback**
   - Peer review
   - Self assessment
   - Multi-rater feedback

2. **Goal Setting**
   - OKR integration
   - Progress tracking
   - Milestone reviews

3. **AI Analysis**
   - Sentiment analysis
   - Suggerimenti miglioramento
   - Pattern recognition

4. **Mobile App**
   - Review on-the-go
   - Push notifications
   - Voice notes

5. **Integration**
   - HR systems
   - Performance management
   - Compensation planning

## Troubleshooting

### Problema: Email non inviate
```python
# Verifica configurazione
print(app.config['MAIL_SERVER'])
print(app.config['REVIEW_NOTIFICATION_ENABLED'])
```

### Problema: Permessi non funzionanti
```sql
-- Verifica relazioni dipartimento
SELECT u.id, u.first_name, d.name, d.head_id
FROM users u
LEFT JOIN departments d ON u.department_id = d.id
WHERE u.id = ?;
```

### Problema: Messaggi non letti
```sql
-- Reset flag messaggi
UPDATE review_messages 
SET is_read = false, read_at = NULL
WHERE review_id = ? AND sender_id != ?;
```

## Contatti

**Maintainer**: Team DevOps Corposostenibile
**Ultimo aggiornamento**: Settembre 2024
**Versione**: 1.8.0
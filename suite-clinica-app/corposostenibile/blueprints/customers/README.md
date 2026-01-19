# Blueprint: Customers

## Panoramica
Il blueprint **customers** è il modulo centrale per la gestione completa dei clienti di Corposostenibile Suite. Gestisce anagrafica, contratti, pagamenti, cartelle cliniche e tutto il lifecycle del cliente.

## Funzionalità Principali

### 1. Gestione Anagrafica
- **CRUD completo** clienti con 50+ campi
- **Ricerca avanzata** con filtri multipli
- **Import/Export** Excel e CSV
- **Storico modifiche** con versioning (SQLAlchemy-Continuum)

### 2. Gestione Contratti e Pagamenti
- **Contratti abbonamento** con date e durate
- **Tracking pagamenti** e transazioni
- **Rinnovi automatici** e manuali
- **Calcolo commissioni** per team vendita

### 3. Servizi Integrati
- **Nutrizione**: assegnazione nutrizionista, piani alimentari
- **Coaching**: assegnazione coach, programmi allenamento
- **Psicologia**: sedute e supporto psicologico
- **Chat**: stato servizio chat dedicato

### 4. Analytics e KPI
- **LTV** (Lifetime Value) e LTGP
- **Statistiche vendite** per periodo
- **Report commissioni** per ruolo
- **Dashboard** con metriche real-time

## Struttura File

```
customers/
├── __init__.py              # Factory e configurazione
├── cli.py                   # Comandi CLI
├── filters.py               # Filtri ricerca avanzata
├── forms.py                 # WTForms validazione
├── models/                  # Modelli aggiuntivi
│   └── snapshots.py        # Snapshot mensili
├── notifications.py         # Sistema notifiche
├── permissions.py           # ACL e autorizzazioni
├── repository.py            # Data access layer
├── routes.py                # Route handlers (67KB!)
├── schemas.py               # Marshmallow serialization
├── services.py              # Business logic (37KB!)
├── signals.py               # Eventi SQLAlchemy
├── sockets.py               # WebSocket real-time
├── tasks.py                 # Task asincroni Celery
├── template_filters.py      # Filtri Jinja custom
├── utils.py                 # Utility functions
├── templates/
│   └── customers/
│       ├── list.html        # Lista principale
│       ├── detail.html      # Dettaglio cliente
│       ├── edit.html        # Form modifica
│       ├── create.html      # Form creazione
│       ├── history.html     # Storico modifiche
│       └── partials/        # Componenti riutilizzabili
└── static/
    ├── css/
    │   └── customers.css
    └── js/
        └── customers.js
```

## API Routes

### HTML Routes
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/customers/` | GET | Lista clienti con filtri |
| `/customers/create` | GET, POST | Nuovo cliente |
| `/customers/<id>` | GET | Dettaglio cliente |
| `/customers/<id>/edit` | GET, POST | Modifica cliente |
| `/customers/<id>/delete` | POST | Elimina cliente |
| `/customers/<id>/history` | GET | Storico modifiche |
| `/customers/<id>/payments` | GET | Lista pagamenti |
| `/customers/<id>/add-payment` | POST | Aggiungi pagamento |
| `/customers/<id>/add-renewal` | POST | Aggiungi rinnovo |
| `/customers/export` | GET | Export Excel/CSV |
| `/customers/import` | POST | Import da file |

### API Endpoints
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/api/customers/search` | GET | Ricerca AJAX |
| `/api/customers/<id>` | GET | JSON cliente |
| `/api/customers/<id>` | PATCH | Update parziale |
| `/api/customers/stats` | GET | Statistiche aggregate |

## Modelli Database

### Cliente (principale)
```python
# Anagrafica
- cliente_id: BigInteger (PK)
- nome_cognome: String(100)
- email: String(120) 
- telefono: String(20)
- data_nascita: Date
- genere: Enum(GenereEnum)

# Stati servizi
- stato_cliente: Enum(attivo, pausa, stop, ghost, insoluto)
- stato_nutrizione: Enum(attivo, pausa, stop, ghost, insoluto)
- stato_coach: Enum(attivo, pausa, stop, ghost, insoluto)
- stato_psicologia: Enum(attivo, pausa, stop, ghost, insoluto)

# Staff assegnato
- nutrizionista: String(100)
- coach: String(100)
- psicologa: String(100)
- personal_consultant_id: Integer (FK)

# Commerciale
- ltv: Numeric(10,2)
- ltgp: Numeric(10,2)
- plusvalenze: Numeric(10,2)
- deposito_iniziale: Numeric(10,2)

# Commissioni
- comm_sales: Numeric(10,2)
- comm_setter: Numeric(10,2)
- comm_coach: Numeric(10,2)
- comm_nutriz: Numeric(10,2)
- comm_psic: Numeric(10,2)

# Metadata
- created_at: DateTime
- updated_at: DateTime
- search_vector: TSVector (Full-text search)
```

### SubscriptionContract
```python
- subscription_id: Integer (PK)
- cliente_id: BigInteger (FK)
- sale_date: Date
- start_date: Date
- end_date: Date
- duration_days: Integer
- initial_deposit: Numeric
- service_type: String
- team_vendita: String

# Relationships
- payments: PaymentTransaction[]
- renewals: SubscriptionRenewal[]
```

### PaymentTransaction
```python
- payment_id: Integer (PK)
- cliente_id: BigInteger (FK)
- payment_date: Date
- amount: Numeric(10,2)
- payment_method: Enum(PagamentoEnum)
- transaction_type: Enum(TransactionTypeEnum)
- note: Text
```

## Services Layer

### CustomerService (principale)
```python
# Metodi principali
create_cliente(data: dict) -> Cliente
update_cliente(cliente_id: int, data: dict) -> Cliente
delete_cliente(cliente_id: int) -> bool
bulk_update(cliente_ids: list, updates: dict) -> int

# Gestione contratti
create_subscription(cliente_id, data) -> SubscriptionContract
add_payment(cliente_id, amount, method) -> PaymentTransaction
add_renewal(subscription_id, data) -> SubscriptionRenewal

# Analytics
calculate_ltv(cliente_id) -> Decimal
get_kpi_summary() -> dict
export_to_excel(filters) -> BytesIO
import_from_excel(file) -> dict
```

### CustomerRepository (data access)
```python
# Query ottimizzate
get_one(cliente_id) -> Cliente
list(filters, page, per_page) -> Pagination
search(query) -> List[Cliente]
history_for_cliente(cliente_id) -> List[ClienteVersion]

# Aggregazioni
kpi_counts(filters) -> dict
ltv_summary(days) -> dict
expiring_contracts(days) -> List[tuple]
```

## Filtri e Ricerca

### Filtri Disponibili
- **Testo**: nome, email, telefono
- **Stati**: stato_cliente, stato_nutrizione, stato_coach, stato_psicologia
- **Date**: created_at, data_nascita (range)
- **Staff**: nutrizionista, coach, psicologa, personal_consultant
- **Commerciali**: ltv_min/max, deposito_min/max
- **Categorie**: tipologia_cliente, categoria, team

### Full-Text Search
```sql
-- PostgreSQL TSVector per ricerca veloce
ALTER TABLE clienti ADD COLUMN search_vector tsvector;
CREATE INDEX ix_clienti_search ON clienti USING gin(search_vector);

-- Trigger per aggiornamento automatico
CREATE TRIGGER update_search_vector 
BEFORE INSERT OR UPDATE ON clienti
FOR EACH ROW EXECUTE FUNCTION update_search_vector();
```

## Permessi (ACL)

### Ruoli e Permessi
```python
# Admin
- customers:* (tutti i permessi)

# Manager
- customers:view
- customers:edit
- customers:export

# Operatore
- customers:view
- customers:edit (solo propri clienti)

# Viewer
- customers:view (read-only)
```

## WebSocket Real-time

### Eventi Socket.IO
```javascript
// Client-side
socket.on('customer_updated', (data) => {
    // Aggiorna UI senza refresh
});

socket.on('payment_received', (data) => {
    // Notifica pagamento
});
```

## Task Asincroni (Celery)

### Task Disponibili
```python
@celery.task
def sync_customer_data():
    """Sincronizza dati con sistemi esterni"""

@celery.task
def generate_monthly_report():
    """Genera report mensile clienti"""

@celery.task
def send_renewal_reminders():
    """Invia reminder rinnovi in scadenza"""
```

## Configurazione

### Variabili Ambiente
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# Redis per cache
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1

# Export
MAX_EXPORT_ROWS=10000
EXPORT_CHUNK_SIZE=1000
```

## Testing

### Test Suite
```python
# tests/test_customers.py
def test_create_cliente():
    """Test creazione nuovo cliente"""

def test_update_stato_servizi():
    """Test update stati multipli"""

def test_calculate_ltv():
    """Test calcolo LTV"""

def test_export_excel():
    """Test export dati"""

def test_permissions():
    """Test ACL e autorizzazioni"""
```


## Performance

### Ottimizzazioni
- **Eager loading** relazioni per N+1 queries
- **Pagination** su liste lunghe
- **Caching** Redis per query frequenti
- **Bulk operations** per update massivi
- **Background jobs** per operazioni pesanti

### Indici Database
```sql
-- Indici per performance
CREATE INDEX ix_clienti_stato ON clienti(stato_cliente);
CREATE INDEX ix_clienti_created ON clienti(created_at DESC);
CREATE INDEX ix_clienti_consultant ON clienti(personal_consultant_id);
CREATE INDEX ix_payments_cliente ON payment_transactions(cliente_id);
```

## Troubleshooting

### Problema: Import Excel fallisce
```python
# Verifica formato file
# Colonne richieste: nome_cognome, email, telefono
# Max 5000 righe per import
```

### Problema: Ricerca lenta
```sql
-- Ricostruisci indice full-text
REINDEX INDEX ix_clienti_search;
VACUUM ANALYZE clienti;
```

### Problema: Storico non tracciato
```python
# Verifica SQLAlchemy-Continuum
from sqlalchemy_continuum import versioning_manager
versioning_manager.plugins
# Deve includere TransactionPlugin
```

## Best Practices

1. **Validazione dati** sempre lato server
2. **Soft delete** invece di cancellazione fisica
3. **Audit trail** per modifiche sensibili
4. **Backup** prima di import massivi
5. **Test** su staging prima di deploy


# Blueprint: Finance

## Panoramica
Il blueprint **finance** gestisce tutti gli aspetti finanziari di Corposostenibile Suite: pacchetti servizi, costi, marginalità, abbonamenti clienti e analisi finanziarie.

## Funzionalità Principali

### 1. Gestione Pacchetti
- **CRUD pacchetti** servizi con prezzi e durate
- **Calcolo margini** automatico
- **Costi professionisti** (nutrizionista, coach, psicologa)
- **Commissioni vendita** configurabili

### 2. Abbonamenti Clienti
- **Tracking abbonamenti** attivi
- **Storico cambi pacchetto**
- **Snapshot mensili** situazione clienti
- **Calcolo MRR** (Monthly Recurring Revenue)

### 3. Analisi Finanziaria
- **Marginalità** per pacchetto e cliente
- **Report vendite** per periodo
- **Proiezioni ricavi** basate su abbonamenti
- **Dashboard KPI** finanziari

### 4. Gestione Anomalie
- **Clienti non matchati** da sistemi esterni
- **Riconciliazione** manuale
- **Alert discrepanze** finanziarie

## Struttura File

```
finance/
├── __init__.py          # Blueprint configuration
├── routes.py            # Route handlers
├── models.py            # Modelli aggiuntivi
├── templates/
│   └── finance/
│       ├── dashboard.html      # Dashboard principale
│       ├── packages/
│       │   ├── list.html      # Lista pacchetti
│       │   ├── detail.html    # Dettaglio pacchetto
│       │   ├── form.html      # Form create/edit
│       │   └── margins.html   # Analisi margini
│       ├── subscriptions/
│       │   ├── list.html      # Lista abbonamenti
│       │   ├── detail.html    # Dettaglio abbonamento
│       │   └── history.html   # Storico cliente
│       └── reports/
│           ├── monthly.html   # Report mensile
│           ├── quarterly.html # Report trimestrale
│           └── mrr.html       # Analisi MRR
└── static/
    ├── css/
    │   └── finance.css
    └── js/
        └── calculations.js     # Calcoli client-side
```

## API Routes

### Package Routes
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/finance/packages` | GET | Lista tutti i pacchetti |
| `/finance/packages/new` | GET, POST | Crea nuovo pacchetto |
| `/finance/packages/<id>` | GET | Dettaglio pacchetto |
| `/finance/packages/<id>/edit` | GET, POST | Modifica pacchetto |
| `/finance/packages/<id>/delete` | POST | Elimina pacchetto |

### Subscription Routes
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/finance/subscriptions` | GET | Lista abbonamenti attivi |
| `/finance/subscriptions/<id>` | GET | Dettaglio abbonamento |
| `/finance/subscriptions/history` | GET | Storico cambi pacchetto |
| `/finance/subscriptions/snapshot` | GET | Snapshot mensile |

### Report Routes
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/finance/reports/monthly` | GET | Report mensile |
| `/finance/reports/quarterly` | GET | Report trimestrale |
| `/finance/reports/mrr` | GET | Analisi MRR |
| `/finance/reports/margins` | GET | Analisi marginalità |

### API Endpoints
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/api/finance/packages/<id>/calculate` | POST | Ricalcolo margini (AJAX) |
| `/api/finance/mrr/current` | GET | MRR corrente |
| `/api/finance/projections` | GET | Proiezioni ricavi |

## Modelli Database

### Package
```python
- id: Integer (PK)
- name: String(100) - unique
- description: Text
- price: Numeric(10,2)
- duration_months: Integer

# Costi mensili
- nutritionist_cost_monthly: Numeric(10,2)
- coach_cost_monthly: Numeric(10,2)
- psychologist_cost_monthly: Numeric(10,2)

# Commissioni e margini
- sales_commission_percent: Numeric(5,2)
- total_cost: Numeric(10,2) - calcolato
- margin: Numeric(10,2) - calcolato
- margin_percent: Numeric(5,2) - calcolato

# Metadata
- notes: Text
- is_active: Boolean - default True
- created_at: DateTime
- updated_at: DateTime
```

### ClienteSubscription
```python
- id: Integer (PK)
- cliente_id: BigInteger (FK)
- package_id: Integer (FK)
- start_date: Date
- end_date: Date
- monthly_amount: Numeric(10,2)
- is_active: Boolean
- cancellation_date: Date
- cancellation_reason: Text
- created_at: DateTime
- updated_at: DateTime

# Relationships
- cliente: Cliente
- package: Package
```

### ClienteMonthlySnapshot
```python
- id: Integer (PK)
- cliente_id: BigInteger (FK)
- month: Date - primo del mese
- package_id: Integer (FK)
- monthly_revenue: Numeric(10,2)
- monthly_cost: Numeric(10,2)
- monthly_margin: Numeric(10,2)
- is_active: Boolean
- created_at: DateTime

# Relationships
- cliente: Cliente
- package: Package
```

### ClientePackageChange
```python
- id: Integer (PK)
- cliente_id: BigInteger (FK)
- old_package_id: Integer (FK)
- new_package_id: Integer (FK)
- change_date: Date
- change_reason: Text
- changed_by: Integer (FK -> users.id)
- created_at: DateTime
```

### UnmatchedFinanceClient
```python
- id: Integer (PK)
- external_id: String(100)
- name: String(200)
- email: String(120)
- amount: Numeric(10,2)
- source_system: String(50)
- import_date: Date
- matched: Boolean - default False
- matched_cliente_id: BigInteger (FK)
- notes: Text
```

## Calcoli Finanziari

### Margine Pacchetto
```python
def calculate_margin(package):
    # Costo totale mensile
    total_cost = (
        package.nutritionist_cost_monthly +
        package.coach_cost_monthly +
        package.psychologist_cost_monthly
    )
    
    # Commissione vendite
    sales_commission = package.price * (package.sales_commission_percent / 100)
    
    # Costo totale durata
    total_package_cost = (total_cost * package.duration_months) + sales_commission
    
    # Margine
    margin = package.price - total_package_cost
    margin_percent = (margin / package.price) * 100 if package.price > 0 else 0
    
    return margin, margin_percent
```

### MRR Calculation
```python
def calculate_mrr():
    # Somma di tutti gli abbonamenti attivi
    active_subs = ClienteSubscription.query.filter_by(is_active=True).all()
    mrr = sum(sub.monthly_amount for sub in active_subs)
    return mrr
```

## Configurazione

### Settings
```python
# Finance settings
DEFAULT_COMMISSION_PERCENT = 10.0
DEFAULT_PACKAGE_DURATION = 3  # mesi

# Currency
CURRENCY_SYMBOL = '€'
CURRENCY_DECIMAL_PLACES = 2

# Report periods
FINANCIAL_YEAR_START = 1  # Gennaio
```

## Testing

### Test Suite
```python
def test_package_margin_calculation():
    """Test calcolo margini pacchetto"""

def test_subscription_lifecycle():
    """Test ciclo vita abbonamento"""

def test_mrr_calculation():
    """Test calcolo MRR"""

def test_snapshot_generation():
    """Test generazione snapshot mensili"""

def test_package_change_tracking():
    """Test tracking cambi pacchetto"""
```

## Report e Dashboard

### KPI Principali
- **MRR** - Monthly Recurring Revenue
- **ARR** - Annual Recurring Revenue  
- **ARPU** - Average Revenue Per User
- **Churn Rate** - Tasso abbandono
- **LTV** - Customer Lifetime Value
- **CAC** - Customer Acquisition Cost
- **Gross Margin** - Margine lordo

### Report Automatici
```python
@celery.task
def generate_monthly_report():
    """Genera report mensile automatico"""
    
@celery.task
def calculate_monthly_snapshots():
    """Calcola snapshot mensili clienti"""
    
@celery.task
def reconcile_external_data():
    """Riconcilia dati da sistemi esterni"""
```

## Best Practices

1. **Aggiornamento prezzi** con storicizzazione
2. **Audit trail** per modifiche finanziarie
3. **Riconciliazione mensile** con contabilità
4. **Alert** per margini negativi
5. **Backup** prima di modifiche massive

## Migliorie Future

1. **Forecasting**
   - Previsioni ricavi ML-based
   - Scenario planning

2. **Automazioni**
   - Import automatico da sistemi contabili
   - Fatturazione elettronica integrata

3. **Analytics Avanzate**
   - Cohort analysis
   - Retention curves
   - Unit economics per canale

4. **Integrazioni**
   - Stripe/PayPal per pagamenti
   - QuickBooks/Fatture in Cloud
   - Business Intelligence tools

5. **Compliance**
   - GDPR data retention
   - Audit log completo
   - Export per commercialista

## Troubleshooting

### Problema: Margini non corretti
```sql
-- Verifica calcoli
SELECT name, price, 
       (nutritionist_cost_monthly + coach_cost_monthly + psychologist_cost_monthly) * duration_months as total_cost,
       margin, margin_percent
FROM packages;
```

### Problema: MRR non aggiornato
```python
# Forza ricalcolo
from corposostenibile.blueprints.finance import calculate_mrr
current_mrr = calculate_mrr()
print(f"MRR attuale: €{current_mrr}")
```

### Problema: Clienti non matchati
```sql
-- Trova clienti non riconciliati
SELECT * FROM unmatched_finance_clients 
WHERE matched = false
ORDER BY import_date DESC;
```


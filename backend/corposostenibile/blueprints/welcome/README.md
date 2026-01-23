# Blueprint: Welcome

## Panoramica
Il blueprint **welcome** fornisce la dashboard principale personalizzata per ogni utente di Corposostenibile Suite, aggregando informazioni chiave da tutti i moduli: OKR, comunicazioni, review, training e notifiche.

## Funzionalità Principali

### 1. Dashboard Personalizzata
- **Vista aggregata** di tutte le informazioni rilevanti
- **Widget dinamici** basati su ruolo utente
- **Notifiche non lette** da tutti i moduli
- **Quick actions** per operazioni frequenti
- **Responsive design** per mobile/tablet

### 2. OKR Overview
- **OKR personali** del trimestre corrente
- **OKR dipartimento** con progressi
- **Key Results** in focus
- **Statistiche performance** real-time
- **Timeline obiettivi** con scadenze

### 3. Centro Notifiche
- **Comunicazioni non lette** aziendali
- **Review pending** da confermare
- **Messaggi training** non letti
- **Richieste approvazione** (per manager)
- **Badge contatori** per ogni categoria

### 4. Quick Access
- **Link rapidi** ai moduli più usati
- **Azioni contestuali** basate su ruolo
- **Ricerca globale** integrata
- **Switch dipartimento** (se multi-dept)
- **Profile shortcuts** personalizzati

### 5. Maintenance Mode
- **Pagina manutenzione** per funzioni WIP
- **Messaggi informativi** per utenti
- **Redirect automatici** quando disponibile

## Struttura File

```
welcome/
├── __init__.py          # Blueprint configuration
├── routes.py            # Route handlers
├── templates/
│   └── welcome/
│       ├── index.html           # Dashboard principale
│       ├── maintenance.html     # Pagina manutenzione
│       └── partials/
│           ├── okr_widget.html      # Widget OKR
│           ├── notifications.html   # Centro notifiche
│           ├── quick_stats.html     # Statistiche rapide
│           └── deadlines.html       # Prossime scadenze
└── static/
    ├── css/
    │   └── welcome.css
    └── js/
        └── dashboard.js         # Interazioni dashboard
```

## API Routes

### Main Routes
| Route | Metodo | Descrizione | Autenticazione |
|-------|--------|-------------|----------------|
| `/welcome/` | GET | Dashboard principale | Sì |
| `/welcome/maintenance` | GET | Pagina manutenzione | Sì |

### Widget Data (via AJAX)
| Route | Metodo | Descrizione |
|-------|--------|-------------|
| `/api/welcome/notifications` | GET | Conteggi notifiche |
| `/api/welcome/okr-summary` | GET | Sommario OKR |
| `/api/welcome/quick-stats` | GET | Statistiche rapide |
| `/api/welcome/deadlines` | GET | Prossime scadenze |

## Data Aggregation

### Comunicazioni Non Lette
```python
# Query comunicazioni accessibili
- Filtra per dipartimento utente
- Esclude comunicazioni inviate dall'utente
- Verifica tabella CommunicationRead
- Ritorna ultime 5 non lette
```

### Review e Training
```python
# Review non confermate
- Review ricevute non draft
- Escluse review private
- Senza acknowledgment

# Messaggi non letti
- In review dove utente è coinvolto
- Da altri utenti
- Flag is_read = False

# Richieste pending (manager)
- Solo per admin/head
- Status = 'pending'
- Ordinate per data
```

### OKR Dashboard
```python
# OKR Personali
- Trimestre corrente
- Status = active
- Max 3 obiettivi
- Include key results

# OKR Dipartimento
- Se utente ha dipartimento
- Trimestre corrente
- Status = active
- Statistiche aggregate
```

## Componenti Dashboard

### Widget OKR
```html
<!-- Mostra obiettivi con progress bar -->
<div class="okr-widget">
    <h3>I miei OKR - Q1 2024</h3>
    <div class="objectives">
        <!-- Lista obiettivi con KR -->
    </div>
    <div class="stats">
        <!-- Metriche aggregate -->
    </div>
</div>
```

### Centro Notifiche
```html
<!-- Badge con contatori -->
<div class="notification-center">
    <a href="/communications">
        <span class="badge">5</span>
        Comunicazioni
    </a>
    <a href="/review">
        <span class="badge">2</span>
        Training
    </a>
</div>
```

### Quick Actions
```html
<!-- Azioni rapide contestuali -->
<div class="quick-actions">
    <button>Crea Ticket</button>
    <button>Report Settimanale</button>
    <button>Richiedi Ferie</button>
</div>
```

## Personalizzazione per Ruolo

### Admin
- Vista completa tutti i dati
- Widget amministrazione
- Link configurazione sistema
- Statistiche globali
- Alert sistema

### Department Head
- Focus su team metrics
- Richieste approvazione prominenti
- OKR dipartimento in evidenza
- Performance team

### Team Member
- Focus su task personali
- OKR individuali
- Comunicazioni dipartimento
- Prossime scadenze

## Performance

### Ottimizzazioni
- **Query aggregate** per ridurre DB calls
- **Caching** dati statici (5 min)
- **Lazy loading** widget secondari
- **Pagination** liste lunghe
- **Async loading** statistiche

### Cache Strategy
```python
# Redis cache per dashboard data
CACHE_TIMEOUT = 300  # 5 minuti

@cache.memoize(timeout=CACHE_TIMEOUT)
def get_dashboard_data(user_id):
    # Aggregazione dati costosa
    pass
```

## Configurazione

### Settings
```python
# Dashboard
DASHBOARD_WIDGETS_PER_ROW = 3
DASHBOARD_MAX_NOTIFICATIONS = 5
DASHBOARD_MAX_OKR_SHOWN = 3
DASHBOARD_REFRESH_INTERVAL = 60  # secondi

# Cache
DASHBOARD_CACHE_TIMEOUT = 300
DASHBOARD_USE_REDIS = True

# Maintenance
MAINTENANCE_MODE = False
MAINTENANCE_MESSAGE = "Sistema in aggiornamento"
```

## JavaScript Interattività

### Auto-refresh
```javascript
// Aggiornamento automatico notifiche
setInterval(function() {
    updateNotificationBadges();
}, 60000);  // Ogni minuto
```

### Widget Collapse
```javascript
// Stato widget salvato in localStorage
$('.widget-header').click(function() {
    $(this).parent().toggleClass('collapsed');
    saveWidgetState();
});
```

## Testing

### Test Suite
```python
def test_dashboard_loads():
    """Test caricamento dashboard"""

def test_notifications_count():
    """Test conteggio notifiche corretto"""

def test_okr_filtering():
    """Test filtro OKR trimestre corrente"""

def test_role_based_widgets():
    """Test widget per ruolo utente"""

def test_maintenance_redirect():
    """Test redirect pagina manutenzione"""
```

## Best Practices

1. **Dashboard leggera** - max 10 query DB
2. **Widget prioritari** above the fold
3. **Notifiche aggregate** non singole
4. **Quick actions** contestuali
5. **Mobile-first** design

## Migliorie Future

1. **Customizzazione**
   - Drag & drop widget
   - Widget marketplace
   - Temi personalizzati

2. **AI Insights**
   - Suggerimenti azioni
   - Anomaly detection
   - Predictive analytics

3. **Real-time Updates**
   - WebSocket notifications
   - Live activity feed
   - Presence indicators

4. **Integrazioni**
   - Calendar sync
   - Email digest
   - Slack notifications

5. **Mobile App**
   - Native dashboard
   - Push notifications
   - Offline mode

## Troubleshooting

### Problema: Dashboard lenta
```python
# Verifica query N+1
from flask_debugtoolbar import DebugToolbarExtension
toolbar = DebugToolbarExtension(app)

# Abilita query logging
app.config['SQLALCHEMY_ECHO'] = True
```

### Problema: Notifiche non aggiornate
```python
# Clear cache
from corposostenibile.extensions import cache
cache.clear()

# Verifica Redis
import redis
r = redis.Redis()
r.ping()  # Deve ritornare True
```

### Problema: Widget non visibili
```javascript
// Reset localStorage
localStorage.removeItem('dashboard_widgets_state');
location.reload();
```

## Accessibilità

### WCAG 2.1 Compliance
- **Contrasto colori** AAA rating
- **Keyboard navigation** completa
- **Screen reader** friendly
- **ARIA labels** su tutti gli elementi
- **Focus indicators** visibili

## Contatti

**Maintainer**: Team DevOps Corposostenibile
**Ultimo aggiornamento**: Settembre 2024
**Versione**: 2.0.0
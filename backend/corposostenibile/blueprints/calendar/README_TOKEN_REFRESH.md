# 🔄 Sistema Auto-Refresh Token Google OAuth

## 📋 Panoramica

Sistema automatico per il refresh dei token Google OAuth prima della scadenza, garantendo che gli utenti non perdano mai la connessione a Google Calendar.

---

## 🎯 Caratteristiche

✅ **Auto-refresh automatico** - I token vengono refreshati 5 minuti prima della scadenza
✅ **Scheduler background** - APScheduler esegue il controllo ogni 5 minuti
✅ **Logging esteso** - Ogni operazione viene loggata per audit
✅ **API Admin** - Endpoint per monitorare e forzare refresh manualmente
✅ **Cleanup automatico** - Token scaduti da >7 giorni vengono eliminati
✅ **Monitoring** - Dashboard metriche salute token
✅ **Graceful degradation** - Se refresh fallisce, elimina token per forzare riautenticazione

---

## 🏗️ Architettura

### Componenti

```
calendar/
├── services.py              - GoogleTokenRefreshService class
├── tasks.py                 - Task periodici (refresh, cleanup, monitoring)
├── scheduler.py             - APScheduler configuration
├── routes.py                - API endpoints admin
└── __init__.py             - Inizializzazione scheduler
```

### Flusso Refresh Automatico

```
1. APScheduler (ogni 5 minuti)
   ↓
2. refresh_google_tokens_task()
   ↓
3. GoogleTokenRefreshService.refresh_all_expiring_tokens(threshold=10min)
   ↓
4. Per ogni token che scade entro 10 min:
   - Usa Google OAuth2 Request() per refresh
   - Aggiorna token_json in DB
   - Aggiorna expires_at (+ 1 ora)
   ↓
5. Log statistiche (refreshed, failed)
```

---

## ⚙️ Configurazione

### Abilitare/Disabilitare Scheduler

Nel file `config.py` o `.env`:

```python
# Abilita scheduler (default: True)
ENABLE_CALENDAR_SCHEDULER = True
```

### Scheduler è disabilitato automaticamente se:
- `app.debug = True` (modalità development)
- `ENABLE_CALENDAR_SCHEDULER = False`

---

## 📊 Scheduler Jobs

### Job 1: Refresh Token
- **Frequenza**: Ogni 5 minuti
- **ID**: `refresh_google_tokens`
- **Funzione**: `refresh_google_tokens_task()`
- **Descrizione**: Refresha tutti i token che scadono entro 10 minuti

### Job 2: Cleanup Token Scaduti
- **Frequenza**: Ogni giorno alle 3:00 AM
- **ID**: `cleanup_expired_tokens`
- **Funzione**: `cleanup_expired_tokens_task()`
- **Descrizione**: Elimina token scaduti da più di 7 giorni

### Job 3: Monitoring Salute
- **Frequenza**: Ogni ora
- **ID**: `monitor_token_health`
- **Funzione**: `monitor_token_health()`
- **Descrizione**: Logga metriche su salute token (healthy, expiring, expired)

---

## 🔌 API Endpoints (Admin Only)

### 1. Status Token

```http
GET /calendar/api/admin/tokens/status
```

**Response:**
```json
{
  "tokens": [
    {
      "user_id": 10,
      "user_name": "Mario Rossi",
      "expires_at": "2025-11-19T18:30:00",
      "expires_in_minutes": 45,
      "is_expired": false,
      "needs_refresh": false
    }
  ],
  "metrics": {
    "total_tokens": 5,
    "healthy": 3,
    "expiring_soon": 1,
    "expired": 1
  }
}
```

---

### 2. Force Refresh Tutti i Token

```http
POST /calendar/api/admin/tokens/refresh
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "refreshed": 2,
    "failed": 0
  },
  "message": "Refresh completato: 2 token aggiornati, 0 falliti"
}
```

---

### 3. Cleanup Token Scaduti

```http
POST /calendar/api/admin/tokens/cleanup
```

**Response:**
```json
{
  "success": true,
  "cleaned": 3,
  "message": "3 token scaduti eliminati"
}
```

---

### 4. Refresh Token Singolo Utente

```http
POST /calendar/api/admin/tokens/{user_id}/refresh
```

**Response:**
```json
{
  "success": true,
  "message": "Token refreshato con successo per user 10",
  "new_expiry": "2025-11-19T19:00:00"
}
```

---

### 5. Status Scheduler

```http
GET /calendar/api/admin/scheduler/status
```

**Response:**
```json
{
  "running": true,
  "jobs": [
    {
      "id": "refresh_google_tokens",
      "name": "Refresh Google OAuth Tokens",
      "next_run": "2025-11-19T17:05:00",
      "trigger": "interval[0:05:00]"
    }
  ],
  "num_jobs": 3
}
```

---

## 🐍 Utilizzo Programmatico

### Import Servizi

```python
from corposostenibile.blueprints.calendar.services import GoogleTokenRefreshService
from corposostenibile.blueprints.calendar.tasks import refresh_google_tokens_task
```

### Refresh Singolo Token

```python
from corposostenibile.models import GoogleAuth

google_auth = GoogleAuth.query.filter_by(user_id=10).first()

# Check se serve refresh
if GoogleTokenRefreshService.refresh_token_if_needed(google_auth):
    print("Token refreshato!")
else:
    print("Token ancora valido")
```

### Force Refresh Manuale

```python
# Refresha TUTTI i token in scadenza
stats = refresh_google_tokens_task()
print(f"Refreshed: {stats['refreshed']}, Failed: {stats['failed']}")
```

### Get Token Status

```python
status_list = GoogleTokenRefreshService.get_token_expiry_status()

for token_status in status_list:
    print(f"{token_status['user_name']}: expires in {token_status['expires_in_minutes']} min")
```

---

## 📝 Logging

Tutti i log del sistema di refresh vanno in:
- Logger: `corposostenibile.blueprints.calendar.services`
- Logger: `corposostenibile.blueprints.calendar.tasks`
- Logger: `corposostenibile.blueprints.calendar.scheduler`

### Livelli Log

```python
logger.info("✅ Token refreshato con successo per user 10")
logger.warning("⚠️ Attenzione: 2 token scaduti richiedono riautenticazione")
logger.error("❌ Errore nel refresh token per user 10: [dettaglio]")
```

### Esempi Log

```
INFO - 🔄 Avvio task refresh token Google OAuth
INFO - Trovati 3 token in scadenza entro 10 minuti
INFO - Token per user 10 sta per scadere, refresh in corso...
INFO - ✅ Token refreshato con successo per user 10
INFO - ✅ Task refresh completato: {'refreshed': 3, 'failed': 0}
```

---

## 🧪 Testing

### Test Manuale via API

```bash
# 1. Check status token (richiede admin login)
curl -X GET http://localhost:5000/calendar/api/admin/tokens/status \
  -H "Cookie: session=YOUR_SESSION_COOKIE"

# 2. Force refresh
curl -X POST http://localhost:5000/calendar/api/admin/tokens/refresh \
  -H "Cookie: session=YOUR_SESSION_COOKIE"

# 3. Check scheduler
curl -X GET http://localhost:5000/calendar/api/admin/scheduler/status \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

### Test Scheduler in Development

Per testare lo scheduler anche in debug mode:

```python
# Nel file config.py o .env
DEBUG = True
ENABLE_CALENDAR_SCHEDULER = True  # Forza abilitazione
```

---

## ⚠️ Troubleshooting

### Scheduler Non Parte

**Problema**: Scheduler disabilitato
**Soluzione**: Verifica `ENABLE_CALENDAR_SCHEDULER=True` e che non sei in debug mode

### Token Non Si Refreshano

**Problema**: Nessun refresh_token salvato
**Soluzione**: L'utente deve riconnettersi a Google Calendar (OAuth richiede `access_type=offline`)

### Errore "Refresh fallito"

**Problema**: Google rifiuta il refresh
**Soluzione**:
1. Verifica credentials Google OAuth
2. Verifica scopes autorizzati
3. Token potrebbe essere revocato → richiedi nuova autenticazione

### Job Duplicati

**Problema**: Scheduler avviato più volte
**Soluzione**: `replace_existing=True` previene duplicati

---

## 🔐 Sicurezza

### Permessi API
- **Tutti gli endpoint `/api/admin/*`** richiedono `current_user.is_admin = True`
- Accesso negato (403) se non admin

### Token Storage
- Token salvati in DB (JSONB encrypted)
- Nessun token in plain text nei log
- Token eliminati automaticamente se irrecuperabili

### Rate Limiting
- Google OAuth API ha rate limits
- Refresh massimo 1 volta ogni 5 minuti per token
- `max_instances=1` previene esecuzioni concorrenti

---

## 📈 Metriche Monitorate

### Salute Token
- `total_tokens`: Numero totale token attivi
- `healthy`: Token validi per >10 minuti
- `expiring_soon`: Token che scadono entro 10 minuti
- `expired`: Token già scaduti

### Refresh Stats
- `refreshed`: Token refreshati con successo
- `failed`: Refresh falliti
- `skipped`: Token ancora validi (nessun refresh necessario)

---

## 🚀 Deployment

### Production Checklist

- [ ] `ENABLE_CALENDAR_SCHEDULER=True`
- [ ] `DEBUG=False`
- [ ] APScheduler configured con timezone corretta
- [ ] Log rotation configurato
- [ ] Monitoring metriche token attivo
- [ ] Backup database google_auth table

### Systemd/Supervisor

Lo scheduler parte automaticamente all'avvio dell'app Flask.

### Docker

Se usi Docker, assicurati che il container abbia timezone corretta:

```dockerfile
ENV TZ=Europe/Rome
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
```

---

## 📚 Dipendenze

### Python Packages

```txt
APScheduler>=3.10.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
Flask>=2.0.0
SQLAlchemy>=1.4.0
```

### Installazione

```bash
pip install APScheduler google-auth google-auth-oauthlib google-api-python-client
```

---

## 🎓 Best Practices

1. **Monitorare regolarmente** - Check `/api/admin/tokens/status` settimanalmente
2. **Cleanup periodico** - Lascia che il job notturno elimini token scaduti
3. **Log rotation** - Configura logrotate per evitare log troppo grandi
4. **Alert su failed** - Imposta alert se `failed > 0` nel refresh
5. **Backup token** - Backup regolare tabella `google_auth`

---

## 📞 Support

Per problemi o domande:
- Check logs in `/var/log/corposostenibile/` (se configurato)
- Usa API admin per diagnostica
- Verifica Google Cloud Console per errori OAuth

---

## 📝 Changelog

### v1.0.0 (2025-11-19)
- ✅ Implementato sistema auto-refresh
- ✅ Scheduler APScheduler con 3 job
- ✅ API Admin completa
- ✅ Logging esteso
- ✅ Monitoring metriche
- ✅ Cleanup automatico

---

## 🏆 Crediti

Implementato da: **Claude Code**
Data: 19 Novembre 2025
Versione: 1.0.0

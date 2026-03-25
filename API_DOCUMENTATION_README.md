# Suite Clinica - Frontend API Documentation

## Panoramica

Questa cartella contiene la documentazione **COMPLETA** di tutti gli endpoint API chiamati dal frontend React.

L'analisi è stata condotta il **25 Marzo 2025** e include:
- **220+ endpoint totali**
- **20 service files** analizzati
- **9 diverse categorie** di endpoint
- **Autenticazione**: 216 endpoint protetti, 4 endpoint pubblici

---

## File di Documentazione

### 1. `FRONTEND_API_ENDPOINTS.md` (43KB - **PRINCIPALE**)
Documentazione completa e dettagliata in formato Markdown con:
- Ogni endpoint con metodo HTTP
- URL completo
- Service file e numero di linea
- Parametri richiesti (query, body)
- Autenticazione richiesta (YES/NO/admin only)
- Note sulla logica speciale

**Usare questo file per:**
- Riferimento completo e dettagliato
- Comprendere tutti i parametri di ogni endpoint
- Sviluppo e debug
- Integrazione con backend

### 2. `FRONTEND_API_ENDPOINTS_SUMMARY.csv` (17KB)
Versione in formato CSV per importazione in Excel, Sheets, database, ecc.

Colonne:
- HTTP_METHOD
- ENDPOINT
- SERVICE_FILE
- LINE
- AUTHENTICATION
- NOTES

**Usare questo file per:**
- Importare dati in strumenti di analisi
- Creare pivot table o report
- Integrazione con sistemi di monitoring
- Comparazione con backend routes

### 3. `FRONTEND_API_ENDPOINTS.json` (7.6KB)
Versione strutturata JSON per integrazione con tools automatici.

**Usare questo file per:**
- API contract testing
- Documentazione API generators (Swagger, etc.)
- Integrazione con CI/CD
- Mock server generation

---

## Struttura della Documentazione Markdown

La documentazione è organizzata in **18 categorie principali**:

1. **AUTHENTICATION & SESSION** (9 endpoint)
   - Login, logout, password reset, impersonation

2. **CUSTOMERS MANAGEMENT** (78 endpoint)
   - CRUD customers, interventions, Trustpilot, video reviews, professional assignments
   - Anamnesi, diary, training plans, locations, call bonus, call rinnovo

3. **CHECKS MANAGEMENT** (13 endpoint)
   - Weekly checks, DCA checks, Minor checks
   - Public check submission
   - Statistics per company/professional

4. **SEARCH** (1 endpoint)
   - Global search

5. **TASKS** (6 endpoint)
   - Task CRUD and management

6. **TEAM MANAGEMENT** (32 endpoint)
   - Team members CRUD
   - Team entity management
   - Professional capacity
   - AI assignments

7. **CALENDAR & MEETINGS** (20 endpoint)
   - Google Calendar integration
   - Meetings management
   - OAuth token management

8. **POST-IT (REMINDERS)** (6 endpoint)
   - Personal post-it notes management

9. **QUALITY SCORES** (8 endpoint)
   - Weekly quality scores
   - Professional rankings
   - Quarterly KPI with Super Malus

10. **TRAINING/REVIEWS** (14 endpoint)
    - Training requests, acknowledgments
    - Team training management
    - Admin training creation

11. **NEWS** (2 endpoint)
    - News list and detail

12. **PUSH NOTIFICATIONS** (5 endpoint)
    - Push subscription management
    - Notification retrieval and marking

13. **TEAM TICKETS** (4 endpoint)
    - Support tickets by patient

14. **GHL INTEGRATION** (14 endpoint)
    - Go High Level CRM integration
    - Calendar mapping
    - Webhook data

15. **ORIGINS MANAGEMENT** (4 endpoint)
    - Customer origins CRUD

16. **TRIAL USERS** (11 endpoint)
    - Trial user management and promotion
    - Client assignment

17. **OLD SUITE INTEGRATION** (4 endpoint)
    - Legacy CRM integration

18. **LOOM INTEGRATION** (6 endpoint)
    - Video recording link management

---

## Informazioni su Autenticazione

### Endpoint Pubblici (NO Auth):
- POST /auth/login
- POST /auth/forgot-password
- POST /auth/reset-password/{token}
- GET /auth/verify-reset-token/{token}
- GET/POST /api/client-checks/public/{checkType}/{token}

### Endpoint Admin-Only:
- GET /auth/impersonate/users
- POST /auth/impersonate/{userId}
- GET /v1/customers/admin-dashboard-stats
- GET /api/client-checks/admin/dashboard-stats
- GET /api/team/stats
- GET /api/team/admin-dashboard-stats
- E molti altri (vedi documentazione completa)

### CSRF Token
- Tutti i service file includono **CSRF token handling**
- Token estratto da: meta tag, cookie, o header
- Automaticamente aggiunto a tutte le richieste

---

## Base URLs

```
/api/                   - Main REST API (baseURL axios instance)
/calendar/              - Calendar service API
/postit/api/            - Post-it service
/quality/api/           - Quality scores service
/review/api/            - Training/Review service
/ghl/api/               - GHL integration
/old-suite/api/         - Old suite integration
/loom/api/              - Loom integration
/customers/             - HTML blueprint endpoints (legacy)
```

---

## Service Files Analizzati

1. **authService.js** - Authentication
2. **clientiService.js** - Customers (LARGEST - 1113 lines)
3. **checkService.js** - Weekly checks
4. **searchService.js** - Global search
5. **taskService.js** - Tasks
6. **teamService.js** - Team management
7. **dashboardService.js** - Dashboard aggregation
8. **calendarService.js** - Calendar integration
9. **postitService.js** - Post-it notes
10. **qualityService.js** - Quality metrics
11. **trainingService.js** - Training/Review system
12. **newsService.js** - News
13. **pushNotificationService.js** - Push notifications
14. **teamTicketsService.js** - Support tickets
15. **ghlService.js** - GHL CRM integration
16. **originsService.js** - Customer origins
17. **trialUserService.js** - Trial user management
18. **oldSuiteService.js** - Old CRM integration
19. **loomService.js** - Loom video integration
20. **publicCheckService.js** - Public check submission

---

## Statistiche

### Per Metodo HTTP:
- **GET**: 120 endpoint (55%)
- **POST**: 70 endpoint (32%)
- **PUT**: 20 endpoint (9%)
- **PATCH**: 5 endpoint (2%)
- **DELETE**: 5 endpoint (2%)

### Per Tipo di Autenticazione:
- **Authenticated (YES)**: 216+ endpoint (98%)
- **Public (NO)**: 4 endpoint (2%)
- **Admin Only**: ~40 endpoint

### Per Categoria:
- **Customers**: 78 endpoint (35%)
- **Team Management**: 32 endpoint (15%)
- **Calendar/Meetings**: 20 endpoint (9%)
- **Training**: 14 endpoint (6%)
- **Checks**: 13 endpoint (6%)
- **GHL Integration**: 14 endpoint (6%)
- **Trial Users**: 11 endpoint (5%)
- **Quality Scores**: 8 endpoint (4%)
- **Other**: 34 endpoint (14%)

---

## Come Usare Questa Documentazione

### Per Sviluppatori Backend:
1. Apri `FRONTEND_API_ENDPOINTS.md`
2. Cerca l'endpoint che devi implementare
3. Verifica parametri, autenticazione, note
4. Implementa l'endpoint con la corretta logica

### Per Tester/QA:
1. Usa `FRONTEND_API_ENDPOINTS_SUMMARY.csv`
2. Importa in Excel per test planning
3. Crea test cases per ogni endpoint
4. Valida parametri e risposte

### Per Integrazione Sistema Esterno:
1. Usa `FRONTEND_API_ENDPOINTS.json`
2. Genera client SDK automatico
3. Crea mock server per testing
4. Integra con strumenti monitoring

### Per Documentazione API:
1. Usa dati da `.json` o `.csv`
2. Genera Swagger/OpenAPI doc
3. Pubblica Postman collection
4. Crea API portal

---

## Note Importanti

### 1. HTML Blueprint Endpoints
Alcuni endpoint non seguono il pattern REST `/api/...` ma usano:
- `/customers/...` - Customer blueprint
- `/calendar/...` - Calendar blueprint
- `/postit/api/...` - Custom basepath
- `/quality/api/...` - Custom basepath

### 2. Interceptor CSRF
Tutti i service file hanno interceptor che:
- Aggiungono CSRF token alle richieste
- Gestiscono 401 Unauthorized (reindirizzano a login)
- Normalizzano URL media (per alcuni service)

### 3. Formdata Upload
Alcuni endpoint supportano `multipart/form-data`:
- Upload avatar team members
- Upload meal plans
- Upload training plans
- Etc.

### 4. Blob Responses
Alcuni endpoint ritornano blob (file):
- Clinical folder export (PDF)
- Meal plan download
- Training plan download

### 5. Errore Comune
Alcuni service usano `axios` direttamente invece di `api` instance:
- `clientiService.js` - Per endpoint custom `/customers/...`
- `publicCheckService.js` - Per check pubblici
- `trainingService.js` - Per `/review/api/...`
- `calendarService.js` - Per `/calendar/...`

---

## Aggiornamenti Futuri

Questa documentazione deve essere **aggiornata** quando:
1. Vengono aggiunti nuovi service files
2. Vengono aggiunti nuovi endpoint
3. Cambiano i parametri di endpoint esistenti
4. Cambiano le route base

Per mantenere aggiornata:
```bash
# Analizzare tutti i service files di nuovo
grep -r "api\." src/services/ | grep -E "\.get\(|\.post\(|\.put\(|\.patch\(|\.delete\("
```

---

## Contatti

Per domande o chiarimenti sulla documentazione API:
- Consultare il backend team per specifiche di implementazione
- Verificare il commit history del codice per cambamenti
- Controllare i test per capire il comportamento atteso

---

**Documentazione generata**: 25 Marzo 2025
**Frontend Version**: React + Vite
**Service Framework**: Axios
**Authentication**: Session-based + CSRF tokens

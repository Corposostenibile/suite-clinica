# Lista Tecnica di Pulizia Codice

> Generata il 30/03/2026 tramite analisi automatica del codebase.
> Organizzazione: Ema (pulizia template + endpoint), Samu (check DB + poi pulizia), Matteo (coordinamento).

---

## Numeri chiave

| Metrica | Valore |
|---|---|
| Route totali backend | ~1016 |
| Route usate dal frontend React | ~240 |
| Template HTML Jinja2 da eliminare | 230+ file |
| Route HTML (`render_template`) da rimuovere | ~350 |
| Blueprint interi senza utilizzo frontend | 25 |
| Webhook / route backend-only da NON toccare | ~35 |

---

## FASE 1 - Eliminazione template HTML e route associate (Ema)

### 1A. Eliminare le cartelle `templates/` dei 26 blueprint

Sono 230+ file `.html` distribuiti nei seguenti blueprint:

- `auth`
- `blueprint_registry`
- `calendar`
- `client_checks`
- `communications`
- `database_registry`
- `department`
- `dev_tracker`
- `feedback`
- `feedback_global`
- `finance`
- `ghl_integration`
- `it_projects`
- `knowledge_base`
- `kpi`
- `manual`
- `news`
- `nutrition`
- `projects`
- `recruiting`
- `respond_io`
- `review`
- `sales_form`
- `suitemind`
- `ticket`
- `welcome`

Percorso tipo: `backend/corposostenibile/blueprints/<nome>/templates/`

Plus i template globali:
- `backend/corposostenibile/templates/base.html`
- `backend/corposostenibile/templates/404.html`
- `backend/corposostenibile/templates/500.html`
- `backend/corposostenibile/templates/maintenance.html`
- `backend/corposostenibile/templates/suitemind/casi_pazienti.html`

### 1B. Eliminare le cartelle `static/` legacy dei blueprint (7 da eliminare)

CSS/JS legacy che servivano i template Flask:

- `customers/static/`
- `department/static/`
- `projects/static/`
- `recruiting/static/`
- `review/static/`
- `team/static/`
- `ticket/static/`

**NON eliminare:**
- `documentation/static/` - serve la documentazione MkDocs
- `pwa/static/` - service worker + icons per la PWA

### 1C. Eliminare gli static globali legacy

`backend/corposostenibile/static/` contiene asset bundle (CSS, JS, fonts, SASS, video, etc.) usati dai template Flask. Verificare che non siano referenziati da nulla prima di eliminare.

### 1D. Rimuovere le funzioni Python che usano `render_template`

~350 chiamate a `render_template()` distribuite in 44 file Python. I piu grossi:

| File | Chiamate `render_template` |
|---|---|
| `it_projects/routes.py` | 26 |
| `client_checks/routes.py` | 25 |
| `recruiting/routes.py` + `kanban.py` + `onboarding.py` | 34 totali |
| `sales_form/views.py` + `public.py` + `admin.py` + `errors.py` | 35 totali |
| `team/weekly_report_routes.py` | 14 |
| `nutrition/views.py` | 14 |
| `knowledge_base/routes.py` | 12 |
| `dev_tracker/routes.py` | 12 |
| `review/routes.py` | 10 |
| `finance/routes.py` + `dashboard.py` | 11 |
| `projects/routes.py` | 8 |
| `department/routes.py` + `team_routes.py` + `okr_routes.py` | 18 totali |
| `respond_io/` (6 file routes) | 16 totali |
| `ticket/routes.py` + `public_routes.py` | 10 totali |
| `auth/routes.py` | 4 + 4 `render_template_string` |
| `communications/routes.py` + `services.py` | 5 |
| `news/routes.py` | 4 |
| `calendar/routes.py` | 4 |
| `blueprint_registry/routes.py` | 4 |
| `feedback/routes.py` | 6 |
| `feedback_global/routes.py` | 3 |
| `ghl_integration/routes.py` | 2 |
| `database_registry/routes.py` | 2 |
| `welcome/routes.py` | 2 |
| `suitemind/routes/main_routes.py` | 2 |
| `manual/routes.py` | 9 |
| `kpi/routes.py` | 1 |

`render_template_string()` da valutare:
- `auth/routes.py` (linee 60, 72, 133, 141) - email template per password reset/change
- `ticket/services.py` (linee 16, 689, 690) - email notifiche ticket
- `knowledge_base/api.py` (linee 311, 312) - preview articoli

### 1E. Rimuovere import e dipendenze correlate

- Rimuovere `from flask import render_template` dove non serve piu
- Rimuovere `filters.py` (template filters Jinja2)
- Pulire `__init__.py` se registra template folders/static folders per blueprint eliminati

---

## FASE 2 - Eliminazione endpoint/blueprint non utilizzati (Ema + Samu)

### 2A. Blueprint INTERI da eliminare (25 blueprint, ~500 route)

Nessuna chiamata dal frontend React:

| Blueprint | Prefix | Route | Note |
|---|---|---|---|
| `appointment_setting` | `/api/appointment-setting` | 8 | Mai usato |
| `blueprint_registry` | `/blueprint-registry` | 13 | Tool interno dev |
| `database_registry` | `/database-registry` | 2 | Tool interno dev |
| `communications` | `/communications` | 7 | Sostituito da React? |
| `department` | `/departments` | 33 | Solo HTML |
| `dev_tracker` | `/dev-tracker` | 19 | Tool interno dev |
| `feedback` | `/feedback` | 10 | **TENERE il webhook Typeform** |
| `feedback_global` | `/feedback` | 10 | - |
| `finance` | `/finance` | 19 | Solo HTML |
| `it_projects` | `/it-projects` | 39 | Solo HTML |
| `knowledge_base` | `/kb` | 33 | Solo HTML |
| `kpi` | `/kpi` | 9 | Solo HTML |
| `manual` | `/manual` | 9 | Solo HTML |
| `marketing_automation` | `/marketing-automation` | 4 | **TENERE OAuth callback + webhook** |
| `nutrition` | `/nutrition` | 29 | Solo HTML |
| `projects` | `/projects` | 26 | Solo HTML |
| `recruiting` | `/recruiting` | 74 | **TENERE route pubbliche apply** |
| `respond_io` | `/respond-io` | 71 | **TENERE i 5 webhook** |
| `sales_form` | `/sales-form` | 70 | **TENERE form pubblici + API submit** |
| `sop_chatbot` | `/api/sop` | 6 | - |
| `suitemind` | `/suitemind` | 7 | - |
| `ticket_bp` | `/tickets` | 38 | Solo HTML |
| `public_ticket_bp` | `/public/ticket` | 4 | **Valutare se serve per utenti esterni** |
| `team_tickets_bp` | `/api/team-tickets` | 21 | - |
| `teams_bot_bp` | `/api/teams-bot` | 1 | **TENERE (MS Teams bot)** |

### 2B. Route singole da eliminare in blueprint USATI

Nei blueprint che il frontend usa, ci sono route HTML duplicate da eliminare:

| Blueprint | Tipo route da eliminare | Quante |
|---|---|---|
| `auth_bp` (HTML) | Route HTML login/forgot/reset/impersonate | 8 |
| `calendar_bp` | Route HTML dashboard/connect/loom-library | 7 |
| `customers_bp` | Route HTML + service_dashboard | ~36 |
| `news_bp` | Route HTML index/detail/create/edit/delete | 10 |
| `review` | Route HTML index/detail/create/edit/stats | 16 |
| `team_bp` | Route HTML OKR/survey/payments/trial/weekly | ~25 |
| `ghl_integration` | Route HTML test/webhook-status | 2 |
| `loom_bp` | `GET /loom/api/recordings/<id>`, `PUT .../association` | 2 |
| `push_notifications` | `GET /api/push/admin/professionisti`, `POST .../admin/send` | 2 |
| `documentation_bp` | Route HTML `/documentation/`, `/documentation/static/` | 3 |

### 2C. Route API inutilizzate in blueprint usati

Endpoint API che esistono nel backend ma il frontend non chiama:

**customers (`/api/v1/customers/`):**
- `GET /hm-coordinatrici-dashboard`
- `GET /{id}/clinical-folder-export`
- `GET /{id}/initial-checks/attachment/{lead_id}/{filename}`
- `GET|POST|PUT|DELETE /{id}/continuity-call-interventions` (4 route)
- `GET /{id}/call-rinnovo-history`, `POST /{id}/call-rinnovo-request`
- `POST /call-rinnovo/{id}/accept|decline|confirm` (3 route)
- `GET /{id}/video-feedback-history`, `POST /{id}/video-feedback-request`
- `POST /video-feedback/{id}/accept|complete` (2 route)

**news (`/api/news/`):**
- `GET /list-all`
- `POST /create`
- `PUT /{id}`
- `DELETE /{id}`

---

## FASE 3 - Commenti e documentazione (Tutti)

### 3A. Aggiungere docstring alle API route attive

I ~240 endpoint usati dal frontend vanno documentati con docstring standard.

### 3B. Pulire commenti obsoleti

- Cercare e rimuovere `# TODO` / `# FIXME` / `# HACK` obsoleti
- Rimuovere codice commentato out
- Rimuovere riferimenti a template/route eliminate

### 3C. Creare README.md

Struttura suggerita:
- Overview progetto (monorepo structure)
- Setup locale (`dev.sh`, Poetry, npm)
- Architecture (backend Flask + frontend React + admin + teams-kanban)
- Reference alla documentazione esistente (`ci_cd_analysis.md`, `docs/vps/`)
- Blueprint attivi e loro scopo
- Ambiente locale (VPS) e produzione (GCP `http://34.154.33.164/`)

---

## ROUTE DA NON TOCCARE (backend-only)

Queste route sono chiamate da sistemi esterni, NON dal frontend React. Vanno mantenute.

### Webhook (sistemi esterni inviano dati qui)

| Route | Sorgente |
|---|---|
| `POST /ghl/webhook/acconto-open` | GoHighLevel |
| `POST /ghl/webhook/nuovo-cliente` | GoHighLevel |
| `POST /ghl/webhook/calendario-prenotato` | GoHighLevel |
| `POST /ghl/webhook/chiuso-won` | GoHighLevel |
| `POST /ghl/webhook/opportunity-data` | GoHighLevel |
| `POST /ghl/webhook/call-bonus-sale` | GoHighLevel |
| `POST /ghl/webhook/ghost-recovery` | GoHighLevel |
| `POST /ghl/webhook/pausa-servizio` | GoHighLevel |
| `POST /old-suite/webhook` | Old Suite |
| `POST /respond-io/webhook/new-contact` | Respond.io |
| `POST /respond-io/webhook/lifecycle-update` | Respond.io |
| `POST /respond-io/webhook/incoming-message` | Respond.io |
| `POST /respond-io/webhook/outgoing-message` | Respond.io |
| `POST /respond-io/webhook/tag-updated` | Respond.io |
| `POST /feedback/webhook` | Typeform |
| `POST /api/v1/customers/trustpilot/webhook` | Trustpilot |
| `POST /marketing-automation/webhook/frameio` | Frame.io |
| `POST /api/teams-bot/messages` | MS Teams Bot |

### OAuth

| Route | Scopo |
|---|---|
| `GET /marketing-automation/oauth/start` | Frame.io OAuth |
| `GET /marketing-automation/oauth/callback` | Frame.io OAuth |
| `GET /calendar/connect` | Google Calendar OAuth |

### Infrastruttura

| Route | Scopo |
|---|---|
| `GET /health` | Health check |
| `GET /manifest.webmanifest` | PWA manifest |
| `GET /service-worker.js` | PWA service worker |
| `GET /icons/<path>` | PWA icons |
| `GET /ws/customers` | WebSocket real-time |
| `GET /<path>` (catch-all) | Serve React SPA |
| `GET /teams-kanban/` | Serve Kanban SPA |

### Form pubblici (utenti esterni)

| Route | Scopo |
|---|---|
| `GET\|POST /sales-form/welcome-form/<code>` | Form vendita pubblico |
| `GET\|POST /sales-form/f/<code>` | Redirect vecchio |
| `GET /sales-form/api/public/config/<code>` | Config form pubblico |
| `POST /sales-form/api/public/submit` | Invio form pubblico |
| `GET /sales-form/public/success\|error` | Pagine conferma |
| `GET\|POST /recruiting/apply/<link_code>` | Candidatura pubblica |
| `POST /recruiting/api/apply` | API candidatura |
| `POST /recruiting/api/apply/upload-cv` | Upload CV |
| `GET\|POST /public/ticket/new` | Ticket pubblico |
| `GET /public/ticket/success\|track\|info` | Pagine ticket pubblico |

---

## Priorita' di esecuzione suggerita

1. **FASE 1A + 1D** (Ema): Eliminare templates + funzioni `render_template` - il grosso del lavoro
2. **FASE 1B + 1C** (Ema): Eliminare cartelle static legacy
3. **FASE 2A** (dopo che Samu finisce i check): Eliminare blueprint inutilizzati interi
4. **FASE 2B + 2C**: Pulire route singole nei blueprint parzialmente usati
5. **FASE 3**: Commenti, docstring, README

---

## Servizi frontend (`corposostenibile-clinica/src/services/`)

Per riferimento, questi sono i 21 service file del frontend che definiscono le ~240 chiamate API attive:

| Service file | Base URL | Endpoint principali |
|---|---|---|
| `api.js` | `/api` | Axios instance base |
| `authService.js` | `/api/auth` | Login, logout, forgot/reset password, impersonate |
| `clientiService.js` | `/api/v1/customers` | CRUD clienti, anamnesi, diary, interventions, trustpilot, marketing, professionisti |
| `checkService.js` | `/api/client-checks` | Check clienti, dashboard, stats |
| `publicCheckService.js` | `/api/client-checks/public` | Check pubblici (weekly, DCA, minor) |
| `teamService.js` | `/api/team` | Members, teams, capacity, assegnazioni |
| `teamTicketsService.js` | `/api/team-tickets` | Ticket team (list, detail, messages) |
| `calendarService.js` | `/calendar/api` | Eventi, meeting, sync, admin tokens |
| `ghlService.js` | `/ghl/api` | Config GHL, calendari, mapping, opportunity |
| `loomService.js` | `/loom/api` + `/ghl/api` | Recordings, meeting loom |
| `oldSuiteService.js` | `/old-suite/api` | Leads vecchia suite |
| `trainingService.js` | `/review/api` | Formazione, richieste, admin |
| `qualityService.js` | `/quality/api` | Score settimanali, KPI, trimestrale |
| `postitService.js` | `/postit/api` | CRUD post-it |
| `trialUserService.js` | `/api/team/trial-users` | CRUD utenti trial |
| `taskService.js` | `/api/tasks` | CRUD task |
| `newsService.js` | `/api/news` | Lista e dettaglio news |
| `searchService.js` | `/api/search` | Ricerca globale |
| `originsService.js` | `/api/v1/customers/origins` | CRUD origini clienti |
| `dashboardService.js` | `/api/v1/customers` | Stats dashboard |
| `pushNotificationService.js` | `/api/push` | Subscription, notifiche |

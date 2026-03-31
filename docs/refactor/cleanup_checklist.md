# Lista Tecnica di Pulizia Codice

> Generata il 30/03/2026 tramite analisi automatica del codebase.
> Organizzazione: Ema (pulizia template + endpoint), Samu (check DB + poi pulizia), Matteo (coordinamento).

---

## Checklist consolidata

Questa sezione e' il punto unico di riferimento sullo stato reale della pulizia documentata in questo file.

### Fase 1 - Template / static / route HTML

- [x] 1A. Rimossi i template HTML legacy dei blueprint e i template globali legacy.
- [x] 1A. Mantenuti solo i template backend ancora necessari a comportamento attivo:
  - `sales_form/templates/sales_form/public/*`
  - `client_checks/templates/client_checks/emails/*`
  - `communications/templates/communications/email/new_communication.html`
- [x] 1B. Rimossi gli static legacy dei blueprint previsti.
- [x] 1C. Puliti gli static globali legacy, mantenendo solo asset ancora necessari (`uploads`, `privacy`, immagini ancora referenziate).
- [x] 1D. Rimosse/disattivate le route HTML legacy con `render_template`.
- [x] 1D. Mantenuti solo i casi ancora ammessi:
  - `sales_form/public.py` per form pubblici esterni
  - `client_checks/services.py` per email backend
  - `communications/services.py` per email backend
  - `auth/routes.py`, `ticket/services.py`, `knowledge_base/api.py` per `render_template_string()` ammessi
- [x] 1E. Rimossi filtri/import Jinja legacy non piu usati (`backend/corposostenibile/filters.py`, `blueprints/review/filters.py`, registrazioni residue, import inutili).
- [x] 1E. Preservato `blueprints/customers/filters.py` perche' contiene logica applicativa/API ancora in uso, non un semplice modulo Jinja legacy.

### Fase 2 - Blueprint ed endpoint inutilizzati

- [ ] 2A. Eliminazione blueprint interi non usati dal frontend React.
- [x] 2A.1. Rimossi i blueprint ad alta confidenza senza eccezioni note: `appointment_setting`, `blueprint_registry`, `database_registry`, `department`, `dev_tracker`, `finance`, `feedback_global`, `kpi`, `manual`, `projects`.
- [ ] 2B. Eliminazione route singole HTML in blueprint ancora usati.

### Fase 3 - Documentazione e commenti

- [ ] 3A. Aggiungere docstring standard alle API route attive.
- [ ] 3B. Rimuovere commenti obsoleti e riferimenti a codice/template eliminati.
- [x] 3A (scope `customers` + `team`): completata aggiunta docstring standard alle API route attive nei blueprint in scope.
- [x] 3B (scope `customers` + `team`): completata pulizia commenti obsoleti/legacy nei file backend in scope.
- [ ] 3C. Creare `README.md` complessivo del progetto.

### Controlli documentazione collegata

- [x] Verificato `ci_cd_analysis.md`: nessun riferimento da aggiornare su template/static legacy della Fase 1.
- [x] Verificata `docs/vps/duckdns_local_dev_vps.md`: i riferimenti a `/static/clinica/*` restano validi come compatibilita' legacy di routing Nginx e non richiedono modifica per questa pulizia.

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

## Stato avanzamento (aggiornato al 30/03/2026)

### Completato

- FASE 1A completata con eccezioni: eliminati i template legacy dei blueprint e i template globali legacy, mantenendo solo i template ancora necessari per form pubblici ed email backend.
- FASE 1B completata: eliminati gli static legacy dei blueprint (`customers`, `department`, `projects`, `recruiting`, `review`, `team`, `ticket`) con eccezioni rispettate (`documentation/static`, `pwa/static`).
- FASE 1C completata: eliminati gli static globali legacy, mantenendo solo asset necessari (`uploads`, `privacy`, immagini ancora referenziate).
- FASE 1D completata con eccezioni: rimosse/disattivate le route HTML legacy con `render_template`, preservando endpoint API/webhook e casi ancora necessari per form pubblici, email e preview controllate.
- FASE 1E completata: rimossi import/dipendenze Jinja legacy non piu usati (`filters.py` globali/review, registrazioni residue, import `render_template` inutili).

### Stato tecnico attuale

- Uso residuo di `render_template` limitato a:
  - `sales_form/public.py` (route pubbliche esterne)
  - `client_checks/services.py` (template email)
  - `communications/services.py` (template email)
- Uso residuo di `render_template_string()` limitato a:
  - `auth/routes.py` (email password reset/change)
  - `ticket/services.py` (email notifiche ticket)
  - `knowledge_base/api.py` (preview articoli)
- Ripristinati solo i template backend ancora necessari al comportamento attivo:
  - `sales_form/templates/sales_form/public/*`
  - `client_checks/templates/client_checks/emails/*`
  - `communications/templates/communications/email/new_communication.html`
- Registrazione blueprint corretta dopo rimozione route HTML (`suitemind` aggiornato a sole API route).
- `welcome` ripristinato con `init_app` minimale per mantenere bootstrap applicazione senza route HTML.

### Verifica test

- Suite `auth` passata (50/50).
- Suite `customers` passata (21/21).
- Avanzamento suite estese in `run_tests.sh` avviato; esecuzione completa ancora da consolidare in un run unico senza timeout/interruzioni.

### Nota operativa

- Per i form pubblici (vendita/recruiting/ticket) la policy resta: non eliminare endpoint esterni senza migrazione esplicita e validazione end-to-end.

---

## FASE 1 - Eliminazione template HTML e route associate (Ema)

### 1A. Eliminare le cartelle `templates/` dei 26 blueprint

Nota aggiornata: l'obiettivo e' rimuovere i template HTML legacy usati dalle vecchie route Flask server-rendered. Non vanno invece eliminati i pochi template ancora necessari a endpoint pubblici esterni o a email backend ancora attive.

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

Nota aggiornata: questa fase e' da considerare completata quando vengono rimossi i `render_template()` legacy legati alle route HTML interne. Restano ammessi solo i casi necessari a:

- form pubblici esterni ancora attivi
- template email backend
- preview controllate lato backend

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

Nota aggiornata: `filters.py` da rimuovere si riferisce ai moduli Jinja legacy non piu usati. Non include moduli omonimi che contengono logica applicativa/API ancora in uso, come `blueprints/customers/filters.py`.

---

## FASE 2 - Eliminazione endpoint/blueprint non utilizzati (Ema + Samu)

### 2A. Blueprint

| Blueprint / area | Prefix | Stato | Decisione | Motivo |
|---|---|---|---|---|
| `appointment_setting` | `/api/appointment-setting` | Fatto | Eliminato | Nessuna chiamata trovata nel mapping/frontend; nessun webhook, OAuth o flusso pubblico da preservare |
| `blueprint_registry` | `/blueprint-registry` | Fatto | Eliminato | Modulo interno di sviluppo; nessuna chiamata frontend o dipendenza operativa trovata |
| `database_registry` | `/database-registry` | Fatto | Eliminato | Modulo interno di sviluppo; nessuna chiamata frontend o dipendenza operativa trovata |
| `department` | `/departments` | Fatto | Eliminato | Solo legacy Flask/HTML; il frontend attivo usa `/team/departments`, non questo prefix |
| `dev_tracker` | `/dev-tracker` | Fatto | Eliminato | Tool interno dev non mappato nel frontend e senza eccezioni operative documentate |
| `finance` | `/finance` | Fatto | Eliminato | Area legacy server-rendered senza service React, webhook o API attive note |
| `feedback_global` | `/feedback` | Fatto | Eliminato | Nessun uso frontend o vincolo esterno trovato; separato dal webhook Typeform di `feedback` |
| `kpi` | `/kpi` | Fatto | Eliminato | Le metriche usate oggi passano da `quality/api/*`; `/kpi` risultava legacy non referenziato |
| `manual` | `/manual` | Fatto | Eliminato | Modulo documentale legacy non usato dal frontend attuale |
| `projects` | `/projects` | Fatto | Eliminato | Solo HTML legacy, senza chiamate frontend o dipendenze backend note |
| `it_projects` | `/it-projects` | Fatto | Eliminato | Backend gia' svuotato; nel frontend restava solo una voce menu senza pagina/API reali |
| `communications` | `/communications` | Fatto | Tenere | Il modulo espone ancora API, permessi, helper globali e notifiche email attive |
| `knowledge_base` | `/kb` | Fatto | Tenere | Il modulo ha ancora API reali, modelli dedicati e logica upload/storage attiva |
| `suitemind` | `/suitemind` | Fatto | Tenere | Esistono API backend reali e route SPA frontend dedicate, quindi la feature e' viva |
| `sop_chatbot` | `/api/sop` | Fatto | Tenere | Il modulo e' usato da `corposostenibile-amministrativa` e ha API/modelli/servizi attivi |
| `feedback` | `/feedback` | Fatto | Tenere | Contiene il webhook Typeform esplicitamente marcato come route da non toccare |
| `marketing_automation` | `/marketing-automation` | Fatto | Tenere | Contiene OAuth callback e webhook Frame.io da preservare |
| `recruiting` | `/recruiting` | Fatto | Tenere | Contiene apply pubblico, submit candidatura e upload CV ancora esposti all'esterno |
| `respond_io` | `/respond-io` | Fatto | Tenere | Contiene webhook esterni ancora attivi, quindi non eliminabile in blocco |
| `sales_form` | `/sales-form` | Fatto | Tenere | Contiene form pubblici, config pubblica e submit ancora attivi |
| `public_ticket_bp` | `/public/ticket` | Fatto | Tenere | Flusso ticket pubblico esterno non ancora validato come dismettibile |
| `teams_bot_bp` | `/api/teams-bot` | Fatto | Tenere | Endpoint bot Teams esplicitamente backend-only da preservare |
| `team_tickets_bp` | `/api/team-tickets` | Fatto | Tenere | Endpoint usati direttamente dal frontend React tramite `teamTicketsService` |
| `ticket_bp` | `/tickets` | Fatto | Tenere | L'HTML legacy e' gia' stato ridotto, ma restano ACL, API, helper, email e file serving attivi |
| `nutrition` | `/nutrition` | Fatto | Tenere | Il modulo espone ancora API reali e supporta feature nutrizione consumate tramite `/customers/*` |

### 2B. Route HTML legacy da trattare

| Blueprint | Route / gruppo | Stato | Decisione |
|---|---|---|---|
| `auth_bp` | login / forgot / reset / impersonate HTML | Fatto | Le pagine HTML non sono piu' un flusso attivo; restano solo endpoint auth JSON/sessione |
| `news_bp` | index/detail/create/edit/delete HTML | Fatto | Il blueprint pagina Flask e' stato rimosso; resta solo `news_api_bp` |
| `review` | index/detail/create/edit/stats HTML | Fatto | Rimosse le route pagina legacy; aggiornati link/redirect/email verso la SPA `/formazione` |
| `ghl_integration` | route HTML test / webhook-status | Fatto | Non risultano route HTML residue da pulire nel modulo attuale |
| `documentation_bp` | `/documentation/` HTML | Fatto | Rimosso l'entrypoint HTML root; mantenuti gli endpoint static/API usati dalla documentazione |
| `calendar_bp` | dashboard / connect / loom-library HTML | Aperto | Va separato l'eventuale HTML legacy dal flow OAuth `GET /calendar/connect`, che non va rotto |
| `customers_bp` | route HTML residue | Aperto | Il dominio clienti e' molto attivo; va tolto solo HTML puro senza toccare API/permessi usati |
| `team_bp` | OKR / survey / payments / trial / weekly HTML | Aperto | Va verificato che ogni pagina legacy abbia gia' una sostituzione React reale |
| `loom_bp` | `recordings/<id>` / `association` | Aperto | Le route non risultano nel mapping principale, ma va escluso un uso secondario prima di rimuoverle |
| `push_notifications` | route admin | Aperto | Le route admin non sono nel frontend clinica, ma potrebbero essere usate da UI/uso operativo separato |
| `ticket_bp` | eventuale HTML residuo | Aperto | Va rimosso solo eventuale HTML morto, lasciando intatti i flussi ticket ancora operativi |

### 2C. API non mappate da verificare

| Blueprint | Endpoint / gruppo | Stato | Decisione |
|---|---|---|---|
| Nessuno confermato al momento | - | Fatto | Nessun candidato forte confermato |
| `customers` | `GET /hm-coordinatrici-dashboard` | Aperto | Non trovato nei frontend verificati; resta da confermare se esiste uso operativo interno |
| `customers` | `GET /{id}/clinical-folder-export` | Aperto | Non trovato nei frontend verificati; potrebbe servire come export manuale/backend |
| `customers` | `GET /{id}/initial-checks/attachment/{lead_id}/{filename}` | Aperto | Non trovato nei frontend verificati; potrebbe essere usato da link backend o allegati storici |
| `customers` | `GET|POST /{id}/continuity-call-interventions` | Aperto | Non trovato nei frontend verificati, ma tocca un dominio cliente ancora molto attivo |
| `customers` | `PUT|DELETE /continuity-call-interventions/{intervention_id}` | Aperto | Non trovato nei frontend verificati, ma tocca un dominio cliente ancora molto attivo |
| `customers` | `GET /{id}/call-rinnovo-history`, `POST /{id}/call-rinnovo-request`, `POST /call-rinnovo/{id}/accept|decline|confirm` | Aperto | Non trovati nei frontend verificati; serve conferma owner prima di considerarli rimovibili |
| `customers` | `GET /{id}/video-feedback-history`, `POST /{id}/video-feedback-request`, `POST /video-feedback/{id}/accept|complete` | Aperto | Non trovati nei frontend verificati; serve conferma owner prima di considerarli rimovibili |
| `customers` | `call-bonus-*` | Fatto | Verificati come usati dal frontend clinica, quindi esclusi dai candidati a rimozione |
| `customers` | `video-review-*` | Fatto | Verificati come usati dal frontend clinica, quindi esclusi dai candidati a rimozione |
| `news` | `GET /api/news/list-all`, `POST /api/news/create`, `PUT /api/news/{id}`, `DELETE /api/news/{id}` | Fatto | Verificati come usati da `corposostenibile-amministrativa`, quindi esclusi dai candidati a rimozione |

---

## FASE 3 - Commenti e documentazione (Tutti)

### 3A. Aggiungere docstring alle API route attive

I ~240 endpoint usati dal frontend vanno documentati con docstring standard.

es: 
```python
@customers_bp.route("/<int:cliente_id>/evaluations/<string:service_type>", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_service_evaluations(cliente_id: int, service_type: str):
    """
    Recupera l'andamento delle valutazioni del cliente per un servizio specifico.
    Include dati da Check Settimanali (vecchi) e Check 2.0 (WeeklyCheckResponse).

    Args:
        cliente_id: ID del cliente
        service_type: Tipo servizio ('nutrizione', 'coaching', 'psicologia')

    Returns:
        JSON con lista valutazioni ordinate per data
    """
```


---

## Frontend API Endpoints Complete Mapping

### AUTENTICAZIONE (6 endpoint)

| Method | Endpoint | Called By | Params | Auth |
|--------|----------|-----------|--------|------|
| POST | /auth/login | Login form | email, password | No |
| POST | /auth/logout | Logout button | - | Yes |
| POST | /auth/forgot-password | Forgot password form | email | No |
| GET | /auth/me | App init, Profile | - | Yes |
| GET | /auth/impersonate/users | Admin panel | - | Yes (Admin) |
| POST | /auth/stop-impersonation | Admin panel | - | Yes (Admin) |

### TEAM & UTENTI (11 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /team/members | Team page | - |
| POST | /team/members | Add member form | name, email, role |
| GET | /team/departments | Team page | - |
| GET | /team/stats | Dashboard | - |
| GET | /team/admin-dashboard-stats | Admin dashboard | - |
| GET | /team/teams | Team management | - |
| POST | /team/teams | Create team form | name, description |
| GET | /team/capacity | Dashboard | - |
| GET | /team/api/assegnazioni | Assignment page | - |
| GET | /trial-users | Admin panel | - |
| POST | /trial-users | Create trial form | user_id, trial_type |

### CALENDAR & EVENTS (11 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /api/connection-status | Calendar page init | - |
| GET | /disconnect | Calendar page | - |
| GET | /api/events | Calendar grid | start, end, filters |
| POST | /api/events | Create event form | title, start, end, etc |
| POST | /api/sync-single-event | Event update | event_id, data |
| GET | /api/team/users | Event attendees | - |
| GET | /api/customers/search | Event customer link | q (search) |
| GET | /api/customers/list | Event dropdown | - |
| GET | /api/admin/tokens/status | Admin panel | - |
| POST | /api/admin/tokens/refresh | Token management | - |
| POST | /api/admin/tokens/cleanup | Token cleanup | - |

### CLIENTI/PAZIENTI (4 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /customers/api/search | Client list search | q (search term) |
| GET | /customers/{id}/stati/{servizio}/storico | Client detail | - |
| GET | /customers/{id}/patologie/storico | Medical history | - |
| GET | /customers/{id}/nutrition/history | Nutrition history | - |

### QUALITA' & REVIEW (5 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /quality/api/weekly-scores | Quality dashboard | - |
| POST | /quality/api/calculate | Calculate quality | - |
| GET | /quality/api/dashboard/stats | Quality dashboard | - |
| POST | /quality/api/calcola-trimestrale | Quarterly calculation | - |
| GET | /quality/api/quarterly-summary | Quarterly view | - |

### TASKS/COMPITI (4 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /tasks/ | Tasks list | filters, page |
| GET | /tasks/stats | Tasks stats widget | - |
| GET | /tasks/filter-options | Task filters | - |
| POST | /tasks/ | Create task form | title, description, etc |

### TRAINING/FORMAZIONE (8 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /my-trainings | Training page | - |
| GET | /my-requests | Training requests | - |
| GET | /received-requests | Received requests | - |
| GET | /given-trainings | Given trainings | - |
| GET | /request-recipients | Recipients dropdown | - |
| POST | /request | Create request form | recipient_id, title, etc |
| GET | /admin/professionals | Admin professionals list | - |
| GET | /admin/dashboard-stats | Admin dashboard | - |

### RICERCA (1 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /search/global | Global search bar | q (search term) |

### NEWS (1 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /news/list | News widget | limit |

### POST-IT (3 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /list | Postit list | - |
| POST | /create | Create postit form | content, target, etc |
| POST | /reorder | Drag & drop reorder | order_data |

### PUSH NOTIFICATIONS (5 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| POST | /push/subscriptions | Register push | subscription |
| GET | /push/public-key | Init push | - |
| DELETE | /push/subscriptions | Unregister push | subscription |
| GET | /push/notifications | Fetch notifications | - |

### LOOM INTEGRATION (2 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /loom/api/patients/search | Loom patient search | q (search) |
| GET | /loom/api/recordings | Loom videos list | patient_id |

### TEAM TICKETS (1 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /team-tickets/ | Tickets list | filters, page |

### INTEGRAZIONI ESTERNE (2 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /leads | Leads import | - |
| POST | /confirm-assignment | Assign lead | lead_id |

### Summary Statistics

- **Total Endpoints**: 67
- **GET requests**: 47
- **POST requests**: 16
- **DELETE requests**: 2

---

### 3B. Pulire commenti obsoleti

- Cercare e rimuovere `# TODO` / `# FIXME` / `# HACK` obsoleti
- Rimuovere codice commentato out

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

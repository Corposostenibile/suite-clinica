# Assegnazioni Sales AI MVP

Branch: `feature/assegnazioni-sales-ai-mvp`

## Obiettivo
Portare in produzione un MVP del pannello **`/assegnazioni-ai`** (suite interna) e del pannello **`/ghl-embed/assegnazioni`** (sales pubblico) usando come fonte canonica **`SalesLead`**.

Stato attuale / direzione confermata:

- `/ghl-embed/assegnazioni` (pubblico sales) legge da `SalesLead` (`source_system='ghl'`) tramite `/api/ghl-assignments` con SSO JWT sales.
- `/assegnazioni-ai` (suite interna) è la pagina madre con due sezioni:
  - **Sales GHL**: dati da `SalesLead` (`source_system='ghl'`)
  - **Storico HM (old-suite)**: da migrare su `ClienteProfessionistaHistory` (alimentata via script C.2 prendendo lo storico da `SalesLead` old-suite / Assegnazioni v1).

`GHLOpportunityData` resta solo come tracciato legacy webhook, non più source operativa per la queue assegnazioni AI corrente.

---

## Stato task: tabella completa

| Task | Stato | Cosa è stato fatto davvero | Note |
|---|---|---|---|
| **A.1 — Backend: blueprint sales_ghl_assignments (`/api/ghl-assignments`)** | **done** | Creato `backend/corposostenibile/blueprints/sales_ghl_assignments/` con endpoint `GET /api/ghl-assignments` | La lista ora è basata su `SalesLead` GHL, non su `ServiceClienteAssignment` |
| **A.2 — Backend: SSO JWT adapter sales (scope=sales, email to sales_user_id)** | **done** | Creato `/api/ghl-assignments/sso/exchange` + JWT HS256 con `scope=sales` e `sales_user_id` | La queue Sales accetta Bearer JWT sales oltre alla sessione legacy |
| **A.3 — Frontend: pagina `/ghl-embed/assegnazioni` (clone UX old_suite)** | **done** | Creata la pagina embed con bootstrap SSO sales, filtri e card in stile old suite | Route canonica per uso GoHighLevel iframe |
| **B.1 — Backend: endpoint `/webhooks/ghl-leads/new` con HMAC SHA-256** | **done** | Creato webhook inbound firmato HMAC e spostato nel blueprint sales dedicato | Salva il lead come `SalesLead` |
| **B.2 — Backend: schema mapping payload GHL verso SalesLead** | **done** | Normalizzazione payload GHL → campi `SalesLead` | Supporta JSON, form-data e wrapper JSON |
| **B.3 — Backend: matcher sales_user da email GHL (exact match)** | **done** | Matching esatto su `User.email` per `sales_user_id` | Niente fallback fuzzy sul nome per l’assegnazione |
| **B.4 — Backend: integra schema payload GHL fornito da Matteo a Emanuele** | **done / adapter flessibile** | Il parser accetta alias multipli e mappe tolleranti | Se arriva uno schema rigidamente ufficiale, si può restringere il mapping |
| **B.5 — Migration: source_system=ghl + index su sales_leads** | **done** | Il modello/migration esistente supporta `source_system` e l’indice; il nuovo flusso scrive `source_system='ghl'` | Nessun ulteriore cambio DB necessario per il nuovo intake |
| **C.1 — Backend: `/ghl/api/admin/assignments-dashboard` con filtri + aggregation** | **done (v2)** | Endpoint aggregato nella blueprint `ghl_integration`; `sales_ghl` su `SalesLead` (`source_system='ghl'`) e `hm_legacy` su `ClienteProfessionistaHistory` (`tipo_professionista='health_manager'`) | Per Storico HM la vista operativa è senza filtri (storico puro) |
| **C.2 — Backend: seed script storico HM completo (`ClienteProfessionistaHistory`)** | **done (apply eseguito in locale)** | Implementato `backend/scripts/seed_hm_history_from_saleslead.py` con soli flag `--dry-run` / `--apply`; crea solo HM history e supporta fallback produzione | Applicato in locale: importati 3 record matchabili (molti clienti prod non presenti in locale) |
| **C.5 — Frontend: RBAC `canAccessAssignmentsDashboard` + sidebar entry + E2E smoke** | **done** | Introdotto helper RBAC dedicato per `/assegnazioni-ai`; route protetta con helper nuovo; sidebar aggiornata con voce `Assegnazioni`; quick link Welcome reso coerente | Script E2E smoke: `node scripts/test_assignments_dashboard_rbac_e2e.mjs` |
| **C.6 — Migration: ai_analysis_snapshot JSONB + populate in confirm-assignment (old_suite + ghl)** | **done** | Snapshot AI salvato in conferma assegnazione old_suite + GHL | Già verificato runtime |

---

## Fonte dati MVP aggiornata

Per il flusso assegnazioni corrente:

- pubblico sales: fonte dati canonica **`SalesLead`**
- suite interna: `SalesLead` per queue Sales GHL + `ClienteProfessionistaHistory` per storico HM (dopo C.2)

Campi rilevanti per il nuovo flusso:

- `first_name`
- `last_name`
- `email`
- `phone`
- `sales_user_id`
- `health_manager_id`
- `origin`
- `client_story`
- `custom_package_name`
- `source_system`
- `source_campaign`
- `source_medium`
- `source_url`
- `referrer_url`
- `landing_page`
- `utm_source`
- `utm_medium`
- `utm_campaign`
- `utm_term`
- `utm_content`
- `form_responses`
- `ai_analysis`
- `ai_analysis_snapshot`
- `status`
- `archived_at`

`GHLOpportunityData` è considerata sorgente legacy di tracciamento webhook, non più fonte primaria della queue assegnazioni AI.

---

## Endpoint GHL

### Legacy / AI flow

`POST /ghl/webhook/opportunity-data`

### Nuovo lead intake sales

`POST /webhooks/ghl-leads/new`

URL completo da configurare in GHL:

- `https://<BASE_URL_PUBBLICO>/webhooks/ghl-leads/new`

### Sicurezza

- firma HMAC SHA-256 sul body
- secret condiviso: `GHL_WEBHOOK_SECRET`
- header firma supportati: `X-GHL-Signature`, `X-Webhook-Signature`, `X-Hub-Signature-256`, `X-Signature`

---

## Mapping payload GHL → SalesLead

### Campi minimi richiesti

- `first_name` / `nome`
- `last_name` / `cognome`
- `email`
- `phone` / `telefono`
- `sales_user_email` consigliato per il matching esatto del sales user

### Campi opzionali supportati

- `health_manager_email`
- `storia`
- `pacchetto`
- `origin`
- `source_campaign`
- `source_medium`
- `source_url`
- `referrer_url`
- `landing_page`
- `utm_source`
- `utm_medium`
- `utm_campaign`
- `utm_term`
- `utm_content`

### Alias per sales_user_email

- `sales_user_email`
- `sales_owner_email`
- `sales_person_email`
- `sales_consultant_email`
- `owner_email`
- `consultant_email`
- `sales_user.email`

### Alias testuali per debug / audit

- `sales_consultant`
- `sales_person`
- `sales_user`
- `sales_owner`
- `sales_rep`
- `consultant`
- `owner`
- `consulente`

### Regole operative

- il record **non dipende** da un formato rigido
- il matching del sales user è **exact match** su email normalizzata
- il matching dell’HM è anch’esso per email normalizzata
- il lead viene salvato con `source_system='ghl'`
- se possibile vengono generati i 3 link check

---

## Controllo finale

- [x] build frontend OK
- [x] test backend GHL OK
- [x] queue e deep-link verificati
- [x] ACL e filtri verificati
- [x] webhook di prova eseguiti con successo
- [x] flow AI end-to-end verificato con script dedicato
- [x] nuovo intake GHL sales salvato come `SalesLead`
- [x] endpoint `/api/ghl-assignments` allineato al nuovo modello Sales
- [x] RBAC `/assegnazioni-ai` allineato (`canAccessAssignmentsDashboard`) + voce sidebar + E2E smoke

---

## Webhook di prova legacy

Script dedicato per testare il webhook GHL sales AI legacy:
- `backend/test_ghl_opportunity_data_webhooks.py`

Casi coperti:
- JSON completo con `opportunity.custom_fields`
- wrapper `payload` come stringa JSON
- form-data con `customData` serializzato in JSON

Esecuzione:

```bash
cd backend && python test_ghl_opportunity_data_webhooks.py
```

---

## Test del nuovo intake SalesLead

```bash
cd backend && poetry run pytest corposostenibile/blueprints/sales_ghl_assignments/tests/test_sales_ghl_assignments.py -q
```

---

## Test C.5 — RBAC dashboard + sidebar (E2E smoke)

```bash
node scripts/test_assignments_dashboard_rbac_e2e.mjs
```

Facoltativo (build frontend):

```bash
cd corposostenibile-clinica && npm run build
```

---

## Test locale: seed lead realistici + Gemini

### 1) Impostare la API key Gemini (solo backend, solo locale)

Nel file `backend/.env` (non versionato) impostare:

```bash
GOOGLE_API_KEY=...  # chiave Gemini server-side
```

Opzionale (override del modello usato da `AIMatchingService`):

```bash
GEMINI_LEAD_CRITERIA_MODEL=gemini-flash-latest
```

### 2) Seed di lead GHL realistici

Script:

```bash
cd backend
poetry run python scripts/seed_ghl_test_leads_realistic.py --sales-email sales.duckdns@corposostenibile.com
```

Pulizia:

```bash
poetry run python scripts/seed_ghl_test_leads_realistic.py --clean
```

Poi aprire (iframe GHL / embed):

- `/ghl-embed/assegnazioni?user_email=<sales_email>`

---

## C.2 — Scope confermato (allineamento chat con Matteo)

### Cosa significa “storico HM completo”

- Interessa **solo la suite interna admin** (non il pannello pubblico sales).
- Riguarda lo storico assegnazioni HM del vecchio flusso **Assegnazioni v1** (`/assegnazioni-old-suite`) oggi salvato in `SalesLead`.
- Obiettivo: avere nel DB storico amministrativo “chi ha assegnato chi” usando `ClienteProfessionistaHistory`, così da mostrare la sezione storico HM in `/assegnazioni-ai`.

### Flusso dati richiesto

1. endpoint usato dalla pagina madre interna:  
   `/ghl/api/admin/assignments-dashboard?...`
2. parte `sales_ghl` continua su `SalesLead` (`source_system='ghl'`)
3. parte `hm_legacy` legge da `ClienteProfessionistaHistory` (`tipo_professionista='health_manager'`)
4. `ClienteProfessionistaHistory` viene popolata da script C.2 prendendo i dati da `SalesLead` old-suite (fallback produzione opzionale)

### Parametri operativi frontend (allineati)

- Tab **Sales GHL**: chiamata con `include_ai=1`, `include_hm=0`
- Tab **Storico HM**: chiamata con `include_ai=0`, `include_hm=1`
- Storico HM: senza filtri UI (no search/no status chips), solo storico HM

### Vincolo importante (non toccare il resto)

- Tutte le nuove assegnazioni continuano ad essere scritte in `SalesLead`.
- Il pannello pubblico sales (`/ghl-embed/assegnazioni`) **non cambia**.
- C.2 è un allineamento storico admin-side, non una modifica del flusso operativo sales.

### Script C.2 implementato

Path:
- `backend/scripts/seed_hm_history_from_saleslead.py`

Comandi:

```bash
cd backend
poetry run python scripts/seed_hm_history_from_saleslead.py --dry-run      # simulazione
poetry run python scripts/seed_hm_history_from_saleslead.py --apply        # applica
```

Regole implementate:
- considera `SalesLead` con `source_system='old_suite'`, `converted_to_client_id` valorizzato e `health_manager_id` presente
- crea **solo** record HM in `ClienteProfessionistaHistory`:
  - `health_manager_id` -> `tipo_professionista='health_manager'`
- crea record history **solo se manca una riga attiva coerente**
- se nel DB locale non ci sono `SalesLead` utili con HM, tenta fallback import da produzione (`PRODUCTION_DATABASE_URL` / `PROD_DATABASE_URL`)
- non tocca M2M né flusso sales pubblico

---

## Prossimi passi

1. Eseguire C.2 in ambiente target (prod/staging) con URL produzione configurato, poi `--apply`
2. Verificare UX `/assegnazioni-ai` in tab HM (storico senza filtri) e tab Sales (filtri attivi)
3. Verificare in staging il flusso pubblico `/ghl-embed/assegnazioni` con link GHL e query `user_email`
4. Eliminare i link residui verso gli URL obsoleti delle assegnazioni sales

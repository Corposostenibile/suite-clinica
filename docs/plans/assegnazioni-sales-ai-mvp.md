# Assegnazioni Sales AI MVP

Branch: `feature/assegnazioni-sales-ai-mvp`

## Obiettivo
Portare in produzione un MVP del pannello **`/assegnazioni-ai`** per gestire le assegnazioni dei **Sales** a partire dai dati GHL.

Il flusso tecnico continua a distinguere due sorgenti:

- **legacy / AI assignments** → `GHLOpportunityData`
- **nuovo lead intake GHL** → `SalesLead` con `source_system='ghl'`

In pratica:

- `GHLOpportunityData` resta la source per il flusso storico `opportunity-data` e per gli endpoint AI già esistenti.
- `SalesLead` è diventato il contenitore canonico del nuovo intake GHL sales.

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
| **C.6 — Migration: ai_analysis_snapshot JSONB + populate in confirm-assignment (old_suite + ghl)** | **done** | Snapshot AI salvato in conferma assegnazione old_suite + GHL | Già verificato runtime |

---

## Fonte dati MVP aggiornata

Per il **nuovo intake GHL sales**, la fonte dati è **`SalesLead`**.

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

La source legacy resta `GHLOpportunityData` per il flusso storico `opportunity-data`.

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

## Prossimi passi

1. Valutare se usare `SalesLead` anche nel flusso `team/assignments/confirm` per il nuovo intake GHL sales
2. Se arriva lo schema finale ufficiale da Matteo/Emanuele, rifinire il mapping del payload
3. Verificare in staging il flusso pubblico `/ghl-embed/assegnazioni` con link GHL e query `user_email`
4. Eliminare i link residui verso gli URL obsoleti delle assegnazioni sales

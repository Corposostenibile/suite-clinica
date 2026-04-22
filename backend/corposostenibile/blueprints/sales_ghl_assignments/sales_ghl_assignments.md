# Sales GHL Assignments

Blueprint dedicato al flusso Sales GHL basato sul modello canonico **`SalesLead`**.

Questo package copre:

1. **SSO Sales JWT**
   - endpoint `POST /api/ghl-assignments/sso/exchange`
   - mapping email → `sales_user_id`
   - JWT HS256 con `scope=sales`

2. **Lista SalesLead GHL**
   - endpoint `GET /api/ghl-assignments`
   - query e filtri per la queue sales
   - accesso via Bearer JWT sales oppure sessione legacy

3. **Webhook inbound GHL**
   - endpoint `POST /webhooks/ghl-leads/new`
   - firma HMAC SHA-256
   - mapping payload → `SalesLead`
   - matching `sales_user` per email esatta

---

## Mount del blueprint

Il package viene registrato così:

- `bp` → `/api/ghl-assignments`
- `sales_ghl_hooks_bp` → `/webhooks`

Endpoint reali esposti dal package:

- `POST /api/ghl-assignments/sso/exchange`
- `GET /api/ghl-assignments`
- `POST /webhooks/ghl-leads/new`

---

## 1) Lista SalesLead GHL

### Obiettivo
Mostrare le lead provenienti da GHL in una queue dedicata ai sales.

### Endpoint

- `GET /api/ghl-assignments`

### SSO Sales JWT

L'endpoint `POST /api/ghl-assignments/sso/exchange` riceve l'email del sales e restituisce un JWT HS256 con:

- `scope = sales`
- `sales_user_id`
- `email`
- `iss = suite-clinica-sales-ghl`

Il token è valido per 8 ore e viene firmato con `GHL_SSO_SIGNING_KEY` (fallback su `SECRET_KEY`).

### Sicurezza

- autenticazione richiesta
- accesso via Bearer JWT sales oppure sessione legacy
- permesso ACL `ghl:view_assignments` per il path sessione

### Query param supportati

- `status=all` per ignorare il filtro stato
- `status=<LEAD_STATUS>` per filtrare per stato
- `q=<testo>` per cercare su nome, email, telefono, unique_code
- `limit=<n>` fino a 300 record

### Dati esposti

Ogni elemento della risposta serializza almeno:

- `id`
- `unique_code`
- `source_system`
- `first_name`
- `last_name`
- `full_name`
- `email`
- `phone`
- `status`
- `sales_user_id`
- `sales_user`
- `health_manager_id`
- `origin`
- `client_story`
- `custom_package_name`
- `form_link_id`
- `converted_to_client_id`
- `ai_analysis`
- `ai_analysis_snapshot`
- `created_at`
- `updated_at`

### Filtro dati

La lista include solo le `SalesLead` con:

- `source_system = 'ghl'`
- `archived_at IS NULL`

---

## 2) Webhook inbound GHL

### Obiettivo
Ricevere un nuovo lead GHL, verificarne la firma e salvarlo come `SalesLead`.

### Endpoint da configurare in GHL

- `POST /webhooks/ghl-leads/new`

URL completo atteso in produzione/staging:

- `https://<BASE_URL_PUBBLICO>/webhooks/ghl-leads/new`

### Sicurezza

Il webhook usa la verifica HMAC del body con:

- `GHL_WEBHOOK_SECRET`

Header firma supportati dal backend:

- `X-GHL-Signature`
- `X-Webhook-Signature`
- `X-Hub-Signature-256`
- `X-Signature`

Formati firma accettati:

- `sha256=<hex>`
- hex puro
- base64 puro

In `development`, se il secret non è configurato, la verifica viene bypassata con warning log.

### Payload accettati

Il webhook accetta:

- JSON puro
- form-data
- wrapper JSON serializzati nei campi:
  - `payload`
  - `data`
  - `body`
  - `raw_payload`

### Campi normalizzati

Il payload viene normalizzato per estrarre:

- `first_name`
- `last_name`
- `email`
- `phone`
- `health_manager_email`
- `sales_user_email`
- `sales_user_name`
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

### Alias supportati per il sales user email

Il backend accetta questi alias per il matching esatto del sales user:

- `sales_user_email`
- `sales_owner_email`
- `sales_person_email`
- `sales_consultant_email`
- `owner_email`
- `consultant_email`
- `sales_user.email`

### Alias supportati per il nome sales

Il backend accetta anche alias testuali per il nome del sales, utili per debug e audit:

- `sales_consultant`
- `sales_person`
- `sales_user`
- `sales_owner`
- `sales_rep`
- `consultant`
- `owner`
- `consulente`

### Cosa succede dopo il salvataggio

1. Il lead viene salvato in `SalesLead`
2. `source_system` viene impostato a `ghl`
3. `sales_user_id` viene risolto con match **esatto** su `User.email`
4. `health_manager_id` viene risolto con match **esatto** su `User.email`
5. Vengono generati i 3 link check se possibile
6. Il backend risponde a GHL con un JSON di conferma

### Nota importante

Questo flusso è quello canonico per i nuovi lead GHL.
Non usa più `GHLOpportunityData` come fonte principale per il lead intake.

---

## Configurazione ambiente

### Variabili principali

```bash
# Lead intake GHL
GHL_WEBHOOK_SECRET=<secret HMAC condiviso con GHL>

# Base URL pubblico
BASE_URL=https://<host>
```

### Riferimento

Vedi anche:

- `backend/.env.example` → sezione **GHL Integration**

---

## Setup operativo

1. Configura il link/launcher GHL per chiamare:
   - `POST /api/ghl-assignments/sso/exchange`
2. Usa l'email del sales come input minimo:
   - `user_email`
3. Salva il JWT restituito e usalo come header:
   - `Authorization: Bearer <token>`
4. Configura il webhook GHL verso:
   - `https://<BASE_URL_PUBBLICO>/webhooks/ghl-leads/new`
5. Imposta la firma HMAC con il secret condiviso:
   - `GHL_WEBHOOK_SECRET`
6. Invia almeno questi campi:
   - `first_name` / `nome`
   - `last_name` / `cognome`
   - `email`
   - `phone` / `telefono`
   - `sales_user_email` (consigliato)

---

## Test e verifica

### Test webhook lead intake

```bash
cd backend && poetry run pytest corposostenibile/blueprints/sales_ghl_assignments/tests/test_sales_ghl_assignments.py -q
```

---

## File chiave

- `__init__.py` → registrazione blueprint e webhook blueprint
- `routes.py` → lista SalesLead GHL
- `hooks.py` → webhook inbound HMAC
- `services.py` → mapping payload → SalesLead

---

## Flusso sintetico

```text
GHL lead webhook
  └── POST /webhooks/ghl-leads/new
        ├── verifica HMAC
        ├── normalizzazione payload
        ├── matching email sales_user / health_manager
        ├── salvataggio SalesLead (source_system='ghl')
        └── generazione link check

Queue Sales
  └── GET /api/ghl-assignments
        └── lista SalesLead GHL
```

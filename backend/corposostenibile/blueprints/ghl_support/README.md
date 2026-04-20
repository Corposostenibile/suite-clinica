# GHL Support Blueprint

Blueprint dedicato alle funzionalità aperte da GoHighLevel per gli utenti sales.

Questo blueprint copre **due flussi distinti**:

1. **Support / Ticketing GHL → ClickUp**
   - accesso embedded via Custom Menu Link
   - creazione ticket
   - sincronizzazione bidirezionale con ClickUp

2. **Lead intake GHL → Suite**
   - webhook inbound firmato HMAC
   - salvataggio lead nel database locale
   - aggancio al flusso di assegnazioni già esistente

---

## Mount del blueprint

Il blueprint viene registrato così:

- `ghl_support_bp` → `/api/ghl-support`
- `ghl_support_hooks_bp` → `/webhooks`

Endpoint reali esposti dal package:

- `POST /api/ghl-support/sso/exchange`
- `GET /api/ghl-support/session/me`
- `POST /api/ghl-support/tickets`
- `GET /api/ghl-support/tickets/mine`
- `GET /api/ghl-support/tickets/<id>`
- `POST /api/ghl-support/tickets/<id>/comments`
- `POST /api/ghl-support/tickets/<id>/attachments`
- `GET /api/ghl-support/attachments/<id>/download`
- `POST /webhooks/clickup-ghl`
- `GET /webhooks/clickup-ghl/health`
- `POST /webhooks/ghl-leads/new`

---

## 1) Flusso support / ticketing

### Obiettivo
Permettere agli utenti GHL di aprire ticket dall’iframe embedded e farli replicare su ClickUp.

### Componenti principali

- `routes.py` → API REST per ticket, allegati e SSO
- `sso.py` → gestione JWT di sessione GHL
- `services/` → logica business e client ClickUp
- `webhooks.py` → ingest eventi ClickUp verso la Suite
- `cli.py` → comandi di setup / test

### Webhook ClickUp
Endpoint:

- `POST /webhooks/clickup-ghl`

Header firma supportati:

- `X-Signature`
- `X-Clickup-Signature`

Secret richiesto:

- `CLICKUP_GHL_WEBHOOK_SECRET`

Algoritmo:

- HMAC-SHA256 del body raw

Formati firma accettati dal backend:

- hex digest
- base64 digest

### Health check

- `GET /webhooks/clickup-ghl/health`

---

## 2) Flusso lead intake GHL

### Obiettivo
Ricevere un nuovo lead da GHL tramite webhook dedicato, verificarne la firma HMAC e salvarlo nel flusso locale delle assegnazioni.

### Endpoint da configurare in GHL

- `POST /webhooks/ghl-leads/new`

URL completo atteso in produzione/staging:

- `https://<BASE_URL_PUBBLICO>/webhooks/ghl-leads/new`

### Sicurezza

Questo endpoint usa la verifica HMAC del body con:

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

- `nome`
- `email`
- `lead_phone`
- `health_manager_email`
- `sales_consultant`
- `storia`
- `pacchetto`
- `durata`

### Alias supportati per il sales owner

Il backend accetta i seguenti alias per il consulente sales:

- `sales_person`
- `sales_user`
- `sales_owner`
- `sales_rep`
- `consultant`
- `owner`
- `consulente`

### Cosa succede dopo il salvataggio

1. Il lead viene salvato in `GHLOpportunityData`
2. Viene valorizzato il `sales_person_id` se il nome è risolvibile
3. Se presente l’email, parte il bridge esistente:
   - creazione/aggiornamento `Cliente`
   - check iniziali
   - eventuale pre-assegnazione
4. Il backend risponde a GHL con un JSON di conferma

### Nota importante

Questo endpoint **non sostituisce** il flusso storico:

- `POST /ghl/webhook/opportunity-data`

Lo affianca come ingresso dedicato per il nuovo webhook lead intake.

---

## Configurazione ambiente

### Variabili principali

```bash
# Lead intake GHL
GHL_WEBHOOK_SECRET=<secret HMAC condiviso con GHL>

# Support / ClickUp bridge
CLICKUP_GHL_INTEGRATION_ENABLED=1
CLICKUP_GHL_WEBHOOK_SECRET=<secret HMAC condiviso con ClickUp>
CLICKUP_GHL_WEBHOOK_URL=https://<host>/webhooks/clickup-ghl
CLICKUP_GHL_SPACE_ID=<space_id>
CLICKUP_GHL_LIST_ID=<list_id>

# Base URL pubblico (utile per documentazione, CLI e setup)
BASE_URL=https://<host>
PUBLIC_CHECKS_BASE_URL=https://<host>
```

### Riferimento

Vedi anche:

- `backend/.env.example` → sezione **GHL Support** e **GHL Integration**

---

## Setup operativo

### A) Lead intake GHL

1. Configura il webhook GHL verso:
   - `https://<BASE_URL_PUBBLICO>/webhooks/ghl-leads/new`
2. Imposta la firma HMAC con il secret condiviso:
   - `GHL_WEBHOOK_SECRET`
3. Invia almeno questi campi:
   - `nome`
   - `email`
   - `telefono`
   - `sales_consultant`

### B) Support / ClickUp

1. Configura il workspace/space/list ClickUp
2. Imposta:
   - `CLICKUP_GHL_WEBHOOK_SECRET`
   - `CLICKUP_GHL_WEBHOOK_URL`
3. Registra il webhook ClickUp verso:
   - `https://<host>/webhooks/clickup-ghl`

---

## Endpoints utili per sviluppo

### SSO embed

`POST /api/ghl-support/sso/exchange`

Usato dalla pagina embedded per trasformare i placeholder GHL in JWT di sessione.

### Session info

`GET /api/ghl-support/session/me`

### Ticketing

- `POST /api/ghl-support/tickets`
- `GET /api/ghl-support/tickets/mine`
- `GET /api/ghl-support/tickets/<id>`
- `POST /api/ghl-support/tickets/<id>/comments`
- `POST /api/ghl-support/tickets/<id>/attachments`
- `GET /api/ghl-support/attachments/<id>/download`

---

## Test e verifica

### Test webhook lead intake

```bash
cd backend && poetry run pytest corposostenibile/blueprints/ghl_support/tests/test_ghl_leads_webhook.py -q
```

### Test webhook GHL opportunity-data

```bash
cd backend && python test_ghl_opportunity_data_webhooks.py
```

### Test flow AI assegnazioni

```bash
cd backend && python test_ghl_ai_assignment_flow.py
```

---

## File chiave

- `__init__.py` → registrazione blueprint
- `routes.py` → API support / ticketing
- `webhooks.py` → webhook ClickUp + webhook lead intake GHL
- `security.py` in `ghl_integration` → verifica HMAC riusata dal lead intake
- `opportunity_bridge.py` in `ghl_integration` → bridge verso cliente/assegnazioni

---

## Flusso sintetico

```text
GHL lead webhook
  └── POST /webhooks/ghl-leads/new
        ├── verifica HMAC
        ├── normalizzazione payload
        ├── salvataggio GHLOpportunityData
        └── bridge → Cliente / assegnazioni

GHL support iframe
  └── POST /api/ghl-support/sso/exchange
        └── JWT sessione

ClickUp ticketing
  └── POST /webhooks/clickup-ghl
        └── sync ticket / commenti / status
```

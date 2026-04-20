# GHL Support Blueprint

Blueprint dedicato alle funzionalità aperte da GoHighLevel per gli utenti sales.

Questo blueprint copre il flusso **Support / Ticketing GHL → ClickUp**.

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

---

## Flusso support / ticketing

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

## Configurazione ambiente

```bash
CLICKUP_GHL_INTEGRATION_ENABLED=1
CLICKUP_GHL_WEBHOOK_SECRET=<secret HMAC condiviso con ClickUp>
CLICKUP_GHL_WEBHOOK_URL=https://<host>/webhooks/clickup-ghl
CLICKUP_GHL_SPACE_ID=<space_id>
CLICKUP_GHL_LIST_ID=<list_id>
```

### Riferimento

Vedi anche:

- `backend/.env.example` → sezione **GHL Support**

---

## Setup operativo

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

### Test webhook ClickUp

In questa fase non abbiamo una suite pytest dedicata al blueprint `ghl_support`.
La verifica del webhook ClickUp va fatta con smoke test manuali o con i test
end-to-end del flusso support quando presenti.

---

## File chiave

- `__init__.py` → registrazione blueprint
- `routes.py` → API support / ticketing
- `webhooks.py` → webhook ClickUp
- `sso.py` → sessione GHL
- `tasks.py` → task di sincronizzazione

---

## Flusso sintetico

```text
GHL support iframe
  └── POST /api/ghl-support/sso/exchange
        └── JWT sessione

ClickUp ticketing
  └── POST /webhooks/clickup-ghl
        └── sync ticket / commenti / status
```

# IT Support Tickets (ClickUp bridge)

Sistema di ticketing IT per gli utenti della Suite Clinica, con replica e
sincronizzazione bidirezionale verso un workspace dedicato su **ClickUp**.

```
Utente Suite ──POST /api/it-support/tickets──▶ it_support blueprint
                                                 │
                                                 ├─▶ DB: ITSupportTicket
                                                 └─▶ Celery task → ClickUp API (create task)
                                                       
ClickUp (IT team lavora)  ──webhook──▶  /webhooks/clickup
                                          │
                                          ├─▶ status update   (ticket.status cache)
                                          └─▶ comment ingest (ITSupportTicketComment direction=from_clickup)
```

## Endpoints

| Method | Path                                              | Auth       | Descrizione |
|-------:|---------------------------------------------------|------------|-------------|
| GET    | `/api/it-support/enums`                           | login      | Valori per i select del form |
| POST   | `/api/it-support/tickets`                         | login      | Crea un ticket (+ enqueue ClickUp) |
| GET    | `/api/it-support/tickets/mine`                    | login      | Lista ticket dell'utente corrente |
| GET    | `/api/it-support/tickets/<id>`                    | login      | Dettaglio (comments + attachments) |
| POST   | `/api/it-support/tickets/<id>/comments`           | login      | Aggiungi commento (→ echo ClickUp) |
| POST   | `/api/it-support/tickets/<id>/attachments`        | login      | Upload allegato (→ sync ClickUp) |
| GET    | `/api/it-support/attachments/<id>/download`       | login      | Download allegato |
| POST   | `/webhooks/clickup`                               | HMAC       | Riceve eventi da ClickUp |
| GET    | `/webhooks/clickup/health`                        | —          | Health probe |

## Configurazione richiesta (env)

```
CLICKUP_INTEGRATION_ENABLED=1
CLICKUP_API_TOKEN=pk_...
CLICKUP_WEBHOOK_SECRET=<hex 32 bytes>
CLICKUP_WORKSPACE_ID=...
CLICKUP_SPACE_ID=...
CLICKUP_LIST_ID=...
CLICKUP_WEBHOOK_URL=https://<host>/webhooks/clickup

# Field UUIDs (da `GET /api/v2/list/<id>/field`)
CLICKUP_FIELD_TIPO=...
CLICKUP_FIELD_MODULO=...
CLICKUP_FIELD_CRITICITA=...
CLICKUP_FIELD_TICKET_ID=...
CLICKUP_FIELD_EMAIL_UTENTE=...
CLICKUP_FIELD_NOME_UTENTE=...
CLICKUP_FIELD_RUOLO=...
CLICKUP_FIELD_SPECIALITA=...
CLICKUP_FIELD_CLIENTE_COINVOLTO=...
CLICKUP_FIELD_BROWSER=...
CLICKUP_FIELD_OS=...
CLICKUP_FIELD_VERSIONE_APP=...
CLICKUP_FIELD_LINK_REGISTRAZIONE=...
CLICKUP_FIELD_ALLEGATO=...

# Dropdown option UUIDs (Tipo, Modulo, Criticità)
CLICKUP_OPT_TIPO_BUG=...
CLICKUP_OPT_TIPO_DATO_ERRATO=...
CLICKUP_OPT_TIPO_ACCESSO=...
CLICKUP_OPT_TIPO_LENTEZZA=...
CLICKUP_OPT_MODULO_ASSEGNAZIONI=...
...
CLICKUP_OPT_CRITICITA_BLOCCANTE=...
CLICKUP_OPT_CRITICITA_NON_BLOCCANTE=...
```

Riferimento completo: `backend/.env.example` sezione *ClickUp Integration*.

## Setup ClickUp iniziale (una-tantum)

1. Crea Workspace (es. *Corposostenibile*)
2. Crea Space (es. *Suite Clinica - Ticket*), imposta **7 statuses** a livello Space:
   `nuovo`, `in triage`, `in lavorazione`, `in attesa utente`, `da testare`, `risolto`, `non valido`
3. Crea una List (es. *Ticket*) dentro lo Space
4. Crea i **14 Custom Fields** nella List con i tipi indicati nel codice
5. Popola le opzioni dei 3 dropdown (Tipo, Modulo, Criticità)
6. Genera Personal API Token (consigliato: service account dedicato)
7. Recupera gli UUID via `GET /api/v2/list/<list_id>/field` e popola il `.env`
8. Registra il webhook puntato a `https://<host>/webhooks/clickup` con eventi:
   `taskStatusUpdated`, `taskCommentPosted`, `taskUpdated`, `taskDeleted`

## Tabelle

- `it_support_tickets` — il ticket (idempotent key: `ticket_number` + `clickup_task_id`)
- `it_support_ticket_comments` — commenti bidirezionali (UNIQUE su `clickup_comment_id`)
- `it_support_ticket_attachments` — allegati (push async su ClickUp)

Enum Postgres: `itsupportticketstatusenum`, `itsupporttickettipoenum`,
`itsupportticketmoduloenum`, `itsupportticketcriticitaenum`.

## Celery tasks

- `it_support.push_ticket_to_clickup(ticket_id)` — create task
- `it_support.push_comment_to_clickup(comment_id)` — echo commento utente
- `it_support.push_attachment_to_clickup(attachment_id)` — upload allegato

Retry con exponential backoff (max 5 tentativi). Su fallimento,
`sync_error` e `sync_attempts` vengono aggiornati sul record.

## Webhook sicurezza

- Verifica HMAC-SHA256 del body con `CLICKUP_WEBHOOK_SECRET`
- Bypass silenzioso in `FLASK_ENV=development` con warning log
- CSRF exempt sul blueprint `it_support_hooks`

## Frontend (clinica)

- Entry point: `SupportWidget.jsx` → pulsante *Apri Ticket IT* → `/supporto/ticket`
- Pagina lista: `pages/support/TicketsPage.jsx`
- Pagina dettaglio: `pages/support/TicketDetail.jsx` (polling 20s per aggiornamenti)
- Service: `services/itSupportService.js`
- Modal form: `components/support/OpenTicketModal.jsx` con template adattivo
  per descrizione in base al tipo

## Idempotenza

| Direzione            | Chiave idempotente     |
|----------------------|------------------------|
| Suite → ClickUp task | `ticket.clickup_task_id` |
| Commento Suite → CU  | `comment.clickup_comment_id` |
| Commento CU → Suite  | `comment.clickup_comment_id` |
| Allegato Suite → CU  | `attachment.synced_to_clickup` |

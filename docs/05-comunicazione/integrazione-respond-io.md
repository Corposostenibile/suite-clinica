# Integrazione Respond.io (WhatsApp/Omnichannel)

> **Categoria**: `comunicazione`
> **Destinatari**: Appointment Setters, Sales, Health Managers
> **Stato**: 🟡 Da aggiornare (modulo parzialmente disattivato in bootstrap)
> **Ultimo aggiornamento**: 27/03/2026

---

## Cos'è e a Cosa Serve

L'integrazione con Respond.io costituisce il layer di comunicazione esterna omnichannel (WhatsApp, Facebook Messenger, Instagram, ecc.) della Suite Clinica. Gestisce in tempo reale la sincronizzazione dei lead, le transizioni del ciclo di vita del contatto (Lifecycle), l'invio di follow-up automatici e il tracciamento delle metriche di messaggistica per monitorare l'efficacia del team di front-end.

In particolare, permette di:
- Monitorare il **ciclo di vita (lifecycle)** di un contatto (es. Nuova Lead, In Target, Prenotato).
- Gestire **follow-up automatici** se un cliente non risponde entro 12 ore.
- Tracciare **metriche giornaliere** di messaggistica e conversioni.
- Automatizzare l'assegnazione dei tag (es. "in_attesa") per segnalare nuovi messaggi agli agenti.

---

## Chi lo Usa

| Ruolo | Utilizzo |
|-------|----------|
| **Appointment Setters** | Gestione operativa delle lead e delle conversazioni inbound |
| **Sales Team** | Monitoraggio dello stato di avanzamento commerciale (Lifecycle) |
| **Health Managers** | Verifica dell'attivazione iniziale dei nuovi clienti |

---

## Flusso Principale (Technical Workflow)

1. **Webhook Ingestion**: Respond.io invia eventi (lifecycle, messaggi) alla Suite.
2. **Lifecycle Sync**: Aggiornamento dello stato commerciale nel database locale.
3. **Automated Follow-up**: Schedulazione via Celery di messaggi di check-in dopo 12h di inattività.
4. **Tag Management**: Aggiunta/rimozione automatica di tag (es. `in_attesa`) su Respond.io via API.
5. **Metric Aggregation**: Consolidamento giornaliero dei volumi di messaggistica (`RespondIODailyMetrics`).

---

## Architettura Tecnica

### Componenti coinvolti

| Layer | Componente | Ruolo |
|-------|------------|-------|
| Webhook | `/respond-io/webhook/*` | Ricezione eventi real-time da Respond.io |
| Client API | `RespondIOClient` | Chiamate outbound REST verso Respond.io |
| Worker | Celery | Scheduling follow-up asincroni e gestione Code |

> Nota implementativa: nel bootstrap del blueprint (`blueprints/respond_io/__init__.py`) l'import esplicito di `webhooks/routes/api_routes` e' commentato. Le route in `webhooks.py` esistono, ma senza import del modulo non vengono registrate automaticamente.

### Ciclo di Vita Webhook

```mermaid
sequenceDiagram
    participant R as Respond.io
    participant S as Suite Clinica
    participant C as Celery Worker
    R->>S: POST /webhook/incoming-message
    S->>S: Verify HMAC Signature
    S-->>R: 200 OK (Always)
    S->>S: Add "in_attesa" Tag
    S->>C: Schedule Follow-up (12h)
```

---

## Endpoint API e Webhook

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/respond-io/webhook/new-contact` | POST | Nuovo contatto (tracking + metriche). |
| `/respond-io/webhook/lifecycle-update` | POST | Cambio lifecycle con aggiornamento metriche e cancellazione follow-up non validi. |
| `/respond-io/webhook/incoming-message` | POST | Messaggio inbound, update mapping canale e gestione tag/follow-up. |
| `/respond-io/webhook/outgoing-message` | POST | Messaggio outbound, rimozione tag `in_attesa` e scheduling follow-up. |
| `/respond-io/webhook/tag-updated` | POST | Aggiornamento tag con logica di cancel/schedule follow-up. |

---

## Modelli di Dati Principali

- `RespondIOLifecycleChange`: Storico dei cambi di stato per ogni contatto.
- `RespondIOFollowupQueue`: Coda dei follow-up programmati (Celery state).
- `RespondIODailyMetrics`: Aggregati giornalieri per il monitoraggio delle performance.

---

## Variabili d'Ambiente Rilevanti

| Variabile | Descrizione | Obbligatoria |
|-----------|-------------|--------------|
| `RESPOND_IO_API_TOKEN` | Token API per chiamate REST outbound | Sì |
| `RESPOND_IO_API_BASE_URL` | Base URL API Respond.io (default `https://api.respond.io/v2`) | No |
| `RESPOND_IO_WEBHOOK_KEY_NEW_CONTACT` | Signing key webhook `new-contact` | Sì |
| `RESPOND_IO_WEBHOOK_KEY_LIFECYCLE` | Signing key webhook `lifecycle-update` | Sì |
| `RESPOND_IO_WEBHOOK_KEY_INCOMING_MESSAGE` | Signing key webhook `incoming-message` | Sì |
| `RESPOND_IO_WEBHOOK_KEY_OUTGOING_MESSAGE` | Signing key webhook `outgoing-message` | Sì |
| `RESPOND_IO_WEBHOOK_KEY_TAG_UPDATED` | Signing key webhook `tag-updated` | Sì |

---

## Note Operative e Casi Limite

- **Firma Webhook**: verifica HMAC-SHA256 base64 tramite header `X-Webhook-Signature`, con chiavi distinte per evento.
- **Risposta 200 OK**: Il sistema ritorna *sempre* 200 OK ai webhook (anche in caso di errore interno dopo il logging) per evitare che Respond.io disconnetta l'endpoint.
- **Quiet Period**: Se il follow-up cade tra mezzanotte e le 7:00 del mattino, viene posticipato alle 7:00 per non disturbare il cliente.
- **Stato bootstrap**: blueprint registrato ma import route commentato nel modulo `respond_io`; se non riattivato, i webhook non risultano effettivamente esposti.

---

## Documenti Correlati

- [Appointment Setting](./appointment-setting.md)
- [Comunicazione Interna](./comunicazione-interna.md)
- [Notifiche Push](./notifiche-push.md)

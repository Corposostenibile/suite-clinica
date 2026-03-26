# Integrazione Respond.io (WhatsApp/Omnichannel)

L'integrazione con **Respond.io** (blueprint `respond_io`) è il layer che gestisce tutta la comunicazione esterna via WhatsApp e altri canali di messaggistica istantanea con i potenziali lead e i clienti attivi.

## Cos'è e a cosa serve
Serve a sincronizzare i dati di contatto tra la Suite Clinica e Respond.io, permettendo di:
- Monitorare il **ciclo di vita (lifecycle)** di un contatto (es. Nuova Lead, In Target, Prenotato).
- Gestire **follow-up automatici** se un cliente non risponde entro 12 ore.
- Tracciare **metriche giornaliere** di messaggistica e conversioni.
- Automatizzare l'assegnazione dei tag (es. "in_attesa") per segnalare nuovi messaggi agli agenti.

## Chi lo usa
- **Appointment Setters**: Per gestire le nuove lead e le conversazioni.
- **Sales**: Per monitorare lo stato di avanzamento della vendita.
- **Health Managers**: Per visualizzare lo stato di attivazione di un cliente nuovo.

## Come funziona (flusso tecnico)

### 1. Webhook Lifecycle
Quando un contatto cambia stato su Respond.io, viene inviato un webhook alla Suite (`/webhook/lifecycle-update`).
- Il sistema registra la transizione nel database (`RespondIOLifecycleChange`).
- Se il nuovo stato non è abilitato per i follow-up (es. è diventato "Non in Target"), eventuali follow-up pendenti vengono cancellati.

### 2. Messaggi in Ingresso/Uscita
Ogni messaggio genera un webhook (`incoming-message` o `outgoing-message`).
- **Ingresso**: Viene aggiunto il tag "in_attesa" su Respond.io per allertare il team.
- **Uscita**: Se l'agente risponde, il tag "in_attesa" viene rimosso. Viene programmato un follow-up per il cliente se non risponde ulteriormente.

### 3. Follow-up Automatici
Il sistema utilizza **Celery** per schedulare messaggi di follow-up (invio automatico "Ciao 💪, hai avuto modo di...") dopo 12 ore di inattività.
- **Quiet Period**: Se il follow-up cade tra mezzanotte e le 7:00 del mattino, viene posticipato alle 7:00 per non disturbare il cliente.

## Architettura Tecnica

### Componenti Principali
- **Blueprint Backend**: `backend/corposostenibile/blueprints/respond_io`
- **Client API**: `RespondIOClient` (in `client.py`) gestisce le chiamate REST verso Respond.io.
- **Task Worker**: Celery gestisce lo scheduling e l'invio dei messaggi asincroni.
- **Websocket**: Notifiche real-time al frontend sulle attività dei messaggi.

## API / Webhook Principali

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/webhook/new-contact` | POST | Registra la creazione di un nuovo contatto. |
| `/webhook/lifecycle-update` | POST | Registra il passaggio di stato (es. Lead -> In Target). |
| `/webhook/incoming-message` | POST | Messaggio ricevuto dal cliente (aggiunge tag "in_attesa"). |
| `/webhook/outgoing-message` | POST | Messaggio inviato dall'agente (rimuove tag "in_attesa", arma follow-up). |

## Modelli di Dati

### `RespondIOLifecycleChange`
Storico dei cambi di stato per ogni contatto.
- `from_lifecycle` / `to_lifecycle`: Lo stato precedente e quello nuovo.
- `channel_name`: Il canale usato (es. WhatsApp).

### `RespondIOFollowupQueue`
Coda dei follow-up programmati.
- `scheduled_at`: Orario previsto per l'invio.
- `status`: `pending`, `sent`, `cancelled` o `failed`.

### `RespondIODailyMetrics`
Aggregati giornalieri per il monitoraggio delle performance.

## Note & Gotcha
- **Firma Webhook**: Tutti i webhook verificano la firma HMAC-SHA256 (`X-Webhook-Signature`) per sicurezza.
- **Risposta 200 OK**: Il sistema ritorna *sempre* 200 OK ai webhook (anche in caso di errore interno dopo il logging) per evitare che Respond.io disconnetta l'endpoint.

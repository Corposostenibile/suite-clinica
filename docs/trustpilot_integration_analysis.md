# Analisi integrazione Trustpilot per tab Marketing paziente

Data analisi: 2026-03-13

## Obiettivo

Capire se il prodotto puo':

1. generare o inviare un link Trustpilot dalla scheda paziente;
2. ricevere un ritorno automatico quando il paziente pubblica davvero la recensione;
3. collegare in modo affidabile la recensione al paziente corretto.

## Risposta breve

Si, il flusso e fattibile.

Il punto importante e che il ritorno non arriva come risposta immediata alla chiamata che genera il link. Arriva tramite webhook asincrono di Trustpilot quando la recensione viene creata, modificata o eliminata.

Il collegamento corretto tra recensione e paziente va fatto usando un `referenceId` generato da noi e salvato sul cliente.

## Cosa conferma la documentazione Trustpilot

- Trustpilot espone Invitations API per:
  - creare inviti email;
  - generare invitation links univoci.
- Trustpilot espone webhook per notificare eventi review:
  - nuova recensione;
  - recensione modificata;
  - recensione eliminata.
- Per le service reviews il payload webhook non include l'email del cliente.
- Il campo corretto da usare per riconciliare la recensione col vostro CRM e `referenceId`.

Fonti ufficiali consultate:

- https://developers.trustpilot.com/invitation-api
- https://developers.trustpilot.com/invitations-api-overview/
- https://developers.trustpilot.com/authentication
- https://developers.trustpilot.com/rate-limiting/
- https://developers.trustpilot.com/deletions-api/
- Help Center Trustpilot: gestione webhook business e payload review, incluso uso di `referenceId`

## Implicazione funzionale per Suite Clinica

Il caso d'uso desiderato e supportato:

1. dalla tab Marketing si genera il link recensione Trustpilot;
2. il link viene copiato o inviato al paziente;
3. Trustpilot riceve la recensione;
4. Trustpilot chiama il nostro endpoint webhook;
5. il backend aggiorna lo stato recensione del paziente.

Il caso d'uso non ancora confermato dalla documentazione verificata:

- stato "email consegnata";
- stato "email aperta";
- stato "link cliccato".

Quindi:

- se per "esito" intendiamo "recensione pubblicata o cambiata", si;
- se intendiamo tracking marketing dell'invito, non risulta confermato.

## Situazione attuale del repository

Esiste gia una base dati interna da riusare:

- modello [`TrustpilotReview`](/home/manu/suite-clinica/backend/corposostenibile/models.py#L13106) pensato oggi per gestione manuale;
- campo cliente [`ultima_recensione_trustpilot_data`](/home/manu/suite-clinica/backend/corposostenibile/models.py#L1966);
- servizi quality su recensioni Trustpilot in [`reviews.py`](/home/manu/suite-clinica/backend/corposostenibile/blueprints/quality/services/reviews.py);
- scheda paziente frontend in [`ClientiDetail.jsx`](/home/manu/suite-clinica/corposostenibile-clinica/src/pages/clienti/ClientiDetail.jsx);
- service frontend clienti in [`clientiService.js`](/home/manu/suite-clinica/corposostenibile-clinica/src/services/clientiService.js);
- API cliente REST sotto `/api/v1/customers/...` in [`routes.py`](/home/manu/suite-clinica/backend/corposostenibile/blueprints/customers/routes.py).

Conclusione pratica: non conviene creare un secondo modello separato. Conviene evolvere `TrustpilotReview` da workflow manuale a workflow API-driven.

## Proposta architetturale

### 1. Dati da salvare

Estendere `TrustpilotReview` con campi tecnici Trustpilot:

- `trustpilot_reference_id` string, unique, indicizzato
- `trustpilot_invitation_id` string nullable
- `trustpilot_review_id` string nullable, unique
- `trustpilot_link` text nullable
- `invitation_method` string nullable
  - valori: `generated_link`, `email_invitation`, `manual`
- `invitation_status` string nullable
  - valori iniziali utili: `generated`, `sent`, `review_created`, `review_updated`, `review_deleted`, `failed`
- `trustpilot_payload_last` JSON nullable
- `webhook_received_at` datetime nullable
- `deleted_at_trustpilot` datetime nullable

Nota: `pubblicata`, `data_pubblicazione`, `stelle`, `testo_recensione` restano utili e vanno mantenuti.

### 2. Regola di mapping paziente

Generare `referenceId` nostro, per esempio:

`sc-{cliente_id}-{uuid-breve}`

Regole:

- univoco nel sistema;
- mai derivato solo dall'email;
- sempre salvato in `TrustpilotReview`;
- passato a Trustpilot quando generiamo link o invito.

### 3. Flusso backend consigliato

#### A. Generazione link

Nuovo endpoint backend autenticato:

- `POST /api/v1/customers/<cliente_id>/trustpilot/link`

Input minimale:

```json
{
  "mode": "generated_link",
  "send_email_via_trustpilot": false
}
```

Azioni:

1. verifica permessi sul cliente;
2. recupera dati paziente;
3. crea record `TrustpilotReview` in stato richiesta;
4. genera `referenceId`;
5. chiama Trustpilot Invitations API;
6. salva `trustpilot_link`, `trustpilot_invitation_id`, `trustpilot_reference_id`;
7. restituisce il link alla UI.

#### B. Invito email Trustpilot

Secondo endpoint opzionale:

- `POST /api/v1/customers/<cliente_id>/trustpilot/invite`

Usa email/nome/locale del paziente e lo stesso `referenceId`.

#### C. Webhook Trustpilot

Nuovo endpoint pubblico:

- `POST /api/integrations/trustpilot/webhook`

Azioni:

1. parse payload;
2. per ogni evento:
   - legge `eventName`;
   - estrae `eventData.referenceId`;
   - cerca `TrustpilotReview` tramite `trustpilot_reference_id`;
   - aggiorna review e cliente;
3. risponde `200` rapidamente;
4. logga e conserva payload grezzo.

### 4. Mapping eventi webhook

Mappatura suggerita:

- `service-review-created`
  - `pubblicata = true`
  - `data_pubblicazione = createdAt`
  - `stelle = stars`
  - `testo_recensione = text`
  - `trustpilot_review_id = id`
  - `invitation_status = review_created`
- `service-review-updated`
  - aggiorna testo, stelle e timestamp
  - `invitation_status = review_updated`
- `service-review-deleted`
  - `pubblicata = false`
  - `deleted_at_trustpilot = now/event time`
  - `invitation_status = review_deleted`

### 5. Aggiornamento dati cliente

Alla review creata:

- aggiornare `Cliente.ultima_recensione_trustpilot_data`;
- incrementare `Cliente.recensioni_lifetime_count` solo se e la prima volta che quella review diventa pubblicata;
- valutare se il bonus quality attuale debba partire automaticamente o restare confermato da HM.

## Decisione consigliata sul bonus

Nel repository esistente il modello attuale nasce per "gestione manuale da HM". Questa parte va decisa esplicitamente, perche l'automazione Trustpilot cambia il processo.

### Opzione consigliata

Automatizzare acquisizione review, ma mantenere una conferma interna per l'applicazione del bonus.

Motivo:

- evita bonus assegnati su review poi cancellate o da verificare;
- preserva compatibilita con la logica quality gia presente;
- riduce regressioni nel modulo quality.

Tradotto in pratica:

- webhook aggiorna review come `pubblicata = true`;
- campo HM di conferma resta separato;
- bonus BRec viene applicato solo dopo conferma interna.

## Proposta UI per tab Marketing

Nuova tab principale in [`ClientiDetail.jsx`](/home/manu/suite-clinica/corposostenibile-clinica/src/pages/clienti/ClientiDetail.jsx):

- id tab: `marketing`
- visibilita iniziale: admin, cco, health manager

Blocchi UI suggeriti:

### Stato Trustpilot

- Ultima richiesta inviata
- Stato review
- Ultima data webhook
- Stelle
- Link pubblico review, se disponibile

### Azioni

- `Genera link recensione`
- `Copia link`
- `Invia invito email Trustpilot`
- `Rigenera link`
- opzionale: `Apri pagina review`

### Storico

- timeline richieste e webhook
- testo recensione
- payload tecnico comprimibile

### Campi utili lato operatore

- professionista richiedente
- note interne marketing
- flag `bonus confermato`

## Endpoint backend proposti

Nuove route consigliate in area customers o nuovo blueprint integrations:

- `GET /api/v1/customers/<cliente_id>/trustpilot`
  - stato attuale + storico sintetico
- `POST /api/v1/customers/<cliente_id>/trustpilot/link`
  - genera link
- `POST /api/v1/customers/<cliente_id>/trustpilot/invite`
  - invia invito email
- `POST /api/integrations/trustpilot/webhook`
  - ricezione eventi Trustpilot

Se volete isolamento migliore dell'integrazione:

- blueprint nuovo `trustpilot_integration`

Se volete time-to-market piu veloce:

- route su `customers/routes.py`

## Sicurezza webhook

La documentazione Trustpilot indica basic auth nell'URL del webhook come meccanismo semplice supportato.

Proposta minima:

- endpoint pubblico dedicato;
- credenziali random in env;
- verifica basic auth;
- logging con masking;
- risposta veloce 200;
- idempotenza su `trustpilot_review_id` e stato evento.

Da non fare:

- whitelist IP Trustpilot, perche usano IP dinamici AWS.

## Variabili ambiente da introdurre

Backend:

- `TRUSTPILOT_API_KEY`
- `TRUSTPILOT_API_SECRET`
- `TRUSTPILOT_BUSINESS_UNIT_ID`
- `TRUSTPILOT_REDIRECT_URI`
- `TRUSTPILOT_WEBHOOK_USERNAME`
- `TRUSTPILOT_WEBHOOK_PASSWORD`
- `TRUSTPILOT_ENABLED`

Possibile aggiunta:

- `TRUSTPILOT_LOCALE_DEFAULT=it-IT`

## Compatibilita con l'architettura attuale

Pattern gia presenti che rendono l'integrazione naturale:

- backend con blueprint separati per integrazioni e webhook;
- `BASE_URL` gia previsto in config per callback esterni;
- cliente detail frontend gia strutturato a tab;
- service frontend centralizzati;
- esistenza del modello `TrustpilotReview`.

## Piano implementativo consigliato

### Fase 1

Obiettivo: visibilita e generazione link.

- estendere schema DB `trustpilot_reviews`;
- endpoint `GET/POST` per stato e generazione link;
- tab Marketing read/write base;
- nessun webhook ancora.

### Fase 2

Obiettivo: automazione esito recensione.

- endpoint webhook pubblico;
- update automatico stato recensione;
- timeline eventi nella UI;
- idempotenza e logging.

### Fase 3

Obiettivo: integrazione con quality bonus.

- collegare review pubblicate a `ReviewService`;
- decidere se bonus automatico o confermato da HM;
- aggiungere test su review create/update/delete.

## Test da prevedere

Backend:

- generazione `referenceId` univoco;
- creazione link con mock Trustpilot API;
- webhook `created`, `updated`, `deleted`;
- idempotenza su doppia consegna webhook;
- review non riconciliata per `referenceId` assente;
- permessi utente su endpoint cliente.

Frontend:

- visualizzazione stato Trustpilot in tab Marketing;
- copy link;
- refresh stato dopo generazione;
- gestione errori endpoint.

## Decisione finale consigliata

La direzione migliore per questo progetto e:

1. riusare `TrustpilotReview` esistente;
2. introdurre `referenceId` come chiave tecnica di riconciliazione;
3. generare link/inviti dalla scheda paziente;
4. ricevere esito recensione via webhook;
5. mantenere separata la conferma bonus quality almeno nella prima versione.

Questa soluzione riduce il rischio, si appoggia bene alla codebase esistente e copre esattamente il bisogno operativo della futura tab Marketing.

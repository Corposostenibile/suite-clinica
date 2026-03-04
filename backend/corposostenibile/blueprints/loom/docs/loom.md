# Integrazione Loom (stato attuale)

Questa pagina riassume come è gestita oggi l'integrazione Loom nel progetto, lato backend e collegamento con frontend.

## Dove vive l'integrazione

- Frontend React clinica: SDK Loom caricato, ma calendario React non ancora integrato con eventi reali (stato "coming soon").
- Backend calendario (fonte eventi): Google Calendar resta la fonte primaria degli eventi.
- Backend GHL: esiste un flusso separato per salvare/leggere `loom_link` usando `ghl_event_id`.
- DB locale: il campo `loom_link` è un arricchimento dati del meeting, non la fonte primaria del calendario.

## Cosa è già presente nel codice

- Hook/client React esistenti:
  - `src/hooks/useLoom.js`
  - `src/services/loomService.js`
- Endpoint backend esistenti per GHL:
  - `POST /api/meeting/loom`
  - `GET /api/meeting/loom/<ghl_event_id>`
- Dashboard calendario legacy (template backend) con gestione Loom già implementata.

## Cosa puoi fare con Loom SDK

- Avviare la registrazione in pagina (pre-record panel / button).
- Gestire gli eventi principali (`insert-click`, `cancel`, `recording-start`, `complete`).
- Ottenere il link condivisibile (`sharedUrl`) e salvarlo nel DB.
- Usare embed/oEmbed per anteprima video e metadati base.

## Limiti attuali (con sola Record SDK)

- Nessuna gestione media backend avanzata (editing/processing lifecycle completo lato server).
- Transcript affidabile completo non garantito via sola Record SDK (per casi avanzati serve API dedicata).
- Nessuna sincronizzazione automatica Loom -> Google Calendar come fonte primaria: Google resta master degli eventi.

## Blueprint coinvolti lato server

- `calendar`: gestione meeting/eventi e arricchimenti (incluso `loom_link`).
- `ghl_integration`: salvataggio/lettura `loom_link` su `ghl_event_id`.
- `loom`: blueprint dedicato dove centralizziamo la documentazione e la futura logica Loom.

## Fonti ufficiali Loom

- https://www.loom.com/sdk
- https://dev.loom.com/docs/record-sdk/details
- https://www.npmjs.com/package/@loomhq/record-sdk
- https://www.npmjs.com/package/@loomhq/embed-sdk

## Nota per i prossimi step frontend

Quando integriamo il widget/flow React definitivo:

1. trigger registrazione da UI contestuale,
2. cattura `sharedUrl` al completamento,
3. persistenza via endpoint backend coerente col dominio evento (Google Calendar vs GHL),
4. visualizzazione link in dettaglio evento e libreria.

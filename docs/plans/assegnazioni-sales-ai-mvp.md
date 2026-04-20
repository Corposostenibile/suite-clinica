# Assegnazioni Sales AI MVP

Branch: `feature/assegnazioni-sales-ai-mvp`

## Obiettivo
Portare in produzione un MVP del pannello **`/assegnazioni-ai`** per gestire le assegnazioni dei **Sales** a partire dai dati GHL.

Il flusso tecnico di riferimento resta quello già usato nelle altre integrazioni GHL:
**webhook → normalizzazione → salvataggio locale → API lista/dettaglio → azioni sul record**.

## Stato attuale
### Già presente nel progetto
- webhook GHL per `opportunity-data`
- entità locale `GHLOpportunityData`
- endpoint:
  - `GET /ghl/api/opportunity-data`
  - `GET /ghl/api/opportunity-data/<id>`
- backend AI assignment già esistente in `team/api.py` con supporto a `opportunity_data_id`
- placeholder frontend su `/assegnazioni-ai`

### Già fatto nel branch
- `GHLOpportunityData` esteso con:
  - `sales_consultant`
  - `sales_person_id`
  - relazione `sales_person`
- webhook `opportunity-data` aggiornato per leggere i campi Sales dal payload GHL
- serializer aggiornato per esporre i campi Sales
- bridge `opportunity_bridge.py` mantiene i check iniziali e valorizza `health_manager_id`
- migration aggiunta per i campi Sales su `ghl_opportunity_data`

## Fonte dati MVP
La fonte dati unica per l’MVP è **`GHLOpportunityData`**.

Campi rilevanti:
- `nome`
- `email`
- `lead_phone`
- `health_manager_email`
- `sales_consultant`
- `sales_person_id`
- `sales_person`
- `storia`
- `pacchetto`
- `durata`
- `ai_analysis`
- `assignments`
- `processed`

## Contratto GHL
### Endpoint
`POST /ghl/webhook/opportunity-data`

### Formati accettati
Il backend accetta JSON e form-data. I dati possono arrivare in:
- `opportunity.custom_fields`
- `opportunity.customData`
- `custom_fields`
- `customData`
- campi top-level
- `contact`

### Campi minimi richiesti
- `name` / `nome` → nome cliente
- `email` → email cliente
- `phone` / `telefono` → telefono cliente
- `sales_consultant` → nome sales di riferimento

### Campi utili opzionali
- `health_manager_email`
- `storia`
- `pacchetto`
- `durata`

### Alias supportati per il sales owner
- `sales_person`
- `sales_user`
- `sales_owner`
- `sales_rep`
- `consultant`
- `owner`
- `consulente`

### Regola operativa
Il record non deve dipendere da un formato rigido: basta mantenere uno degli alias supportati e il backend continuerà a normalizzare i dati.

### Responsabilità lato GHL
- configurare il webhook verso `POST /ghl/webhook/opportunity-data`
- compilare i campi custom con gli alias supportati
- garantire almeno `nome`, `email`, `telefono`, `sales_consultant`
- mantenere stabile il mapping dei campi quando possibile

### Esempio payload JSON
```json
{
  "event_type": "opportunity.data_ready",
  "timestamp": "2026-04-20T10:30:00Z",
  "opportunity": {
    "id": "opp_123456",
    "status": "new",
    "pipeline_name": "Sales Pipeline",
    "custom_fields": {
      "nome": "Mario Rossi",
      "email": "mario.rossi@example.com",
      "telefono": "+39 333 1234567",
      "sales_consultant": "Luca Bianchi",
      "health_manager_email": "hm@example.com",
      "pacchetto": "Premium 90 giorni",
      "durata": "90",
      "storia": "Lead generato da campagne Ads"
    }
  },
  "contact": {
    "id": "contact_987654",
    "name": "Mario Rossi",
    "email": "mario.rossi@example.com",
    "phone": "+39 333 1234567"
  }
}
```

## Flusso target
1. GHL invia il webhook `opportunity-data`
2. il backend normalizza il payload
3. il record viene salvato in `ghl_opportunity_data`
4. il pannello `/assegnazioni-ai` mostra la queue
5. l’utente apre il dettaglio
6. parte analisi AI / matching
7. l’assegnazione viene confermata
8. il record viene marcato come processato / assegnato

## Piano backend
### 1. Ingestione GHL
- mantenere il parser robusto su JSON e form-data
- supportare alias multipli dei campi Sales
- salvare sempre `raw_payload` come fonte di verità tecnica

### 2. Normalizzazione Sales
- usare `sales_consultant` come valore raw/leggibile
- risolvere `sales_person_id` quando il nome è riconosciuto
- esporre il Sales normalizzato via API

### 3. Queue
- usare `GHLOpportunityData` come base della coda
- ordinare per più recenti / non processati
- aggiungere solo i filtri minimi necessari

### 4. Workflow AI
- riusare gli endpoint già presenti in `team/api.py`:
  - `analyze-lead`
  - `match`
  - `confirm`
- verificare il flusso con `opportunity_data_id`

### 5. Stato record
- usare `processed` come stato base
- gli stati UI derivano da:
  - da lavorare
  - in analisi
  - assegnato
  - processato

### 6. Permessi
- accesso solo ai ruoli previsti dal business
- controlli coerenti lato frontend e backend
- nessun accesso alla queue per ruoli non autorizzati

## File backend coinvolti
- `backend/corposostenibile/blueprints/ghl_integration/routes.py`
- `backend/corposostenibile/blueprints/ghl_integration/opportunity_bridge.py`
- `backend/corposostenibile/models.py`
- `backend/migrations/versions/7c8d9e0f1a2b_add_sales_fields_to_ghl_opportunity_data.py`
- `backend/corposostenibile/blueprints/team/api.py`

## Frontend dopo il backend
- sostituire il placeholder di `corposostenibile-clinica/src/pages/team/AssegnazioniAI.jsx`
- rendere `SuiteMindAssignment.jsx` robusto su refresh/deep-link
- consumare la queue da `ghlService.getOpportunityData()`
- verificare i permessi in `rbacScope.js` e `App.jsx`

## Priorità
### P0
- ingestione GHL corretta
- salvataggio Sales owner
- lista/dettaglio affidabili
- confirm assignment funzionante da `opportunity_data_id`

### P1
- filtri utili sulla queue
- miglioramento permessi
- rifinitura payload del serializer

### P2
- UI completa del pannello
- ottimizzazioni UI/UX
- hardening aggiuntivo del webhook

## Fuori scope
- ClickUp per le assegnazioni
- refactor completo della old-suite
- redesign grafico non necessario per l’MVP
- nuove entità DB non indispensabili

## Definition of done
- `/assegnazioni-ai` mostra una queue reale GHL
- ogni record mostra il Sales di riferimento quando disponibile
- il dettaglio apre il flusso AI
- la conferma salva l’assegnazione
- il record viene marcato correttamente
- il tutto resta isolato dal legacy old-suite

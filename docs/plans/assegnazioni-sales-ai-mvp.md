# Assegnazioni Sales AI MVP

Branch: `feature/assegnazioni-sales-ai-mvp`

## Obiettivo
Portare in produzione un MVP del pannello **`/assegnazioni-ai`** per gestire le assegnazioni dei **Sales** a partire dai dati GHL.

Il flusso tecnico di riferimento resta quello già usato nelle altre integrazioni GHL:
**webhook → normalizzazione → salvataggio locale → API lista/dettaglio → azioni sul record**.

## Checklist
### Stato già presente
- [x] webhook GHL per `opportunity-data`
- [x] entità locale `GHLOpportunityData`
- [x] endpoint `GET /ghl/api/opportunity-data`
- [x] endpoint `GET /ghl/api/opportunity-data/<id>`
- [x] backend AI assignment già esistente in `team/api.py` con supporto a `opportunity_data_id`
- [x] pagina `/assegnazioni-ai` con queue GHL reale
- [x] dettaglio `/suitemind/:opportunityId` supporta refresh e deep-link
- [x] `GHLOpportunityData` esteso con `sales_consultant`
- [x] `GHLOpportunityData` esteso con `sales_person_id`
- [x] `GHLOpportunityData` esteso con relazione `sales_person`
- [x] webhook `opportunity-data` aggiornato per leggere i campi Sales dal payload GHL
- [x] serializer aggiornato per esporre i campi Sales
- [x] bridge `opportunity_bridge.py` mantiene i check iniziali e valorizza `health_manager_id`
- [x] migration aggiunta per i campi Sales su `ghl_opportunity_data`

### Da completare per l’MVP
- [x] ingestione GHL corretta
- [x] salvataggio Sales owner
- [x] lista/dettaglio affidabili
- [x] confirm assignment funzionante da `opportunity_data_id`
- [x] filtri utili sulla queue
- [x] miglioramento permessi
- [x] rifinitura payload del serializer
- [x] UI completa del pannello
- [x] ottimizzazioni UI/UX
- [x] hardening aggiuntivo del webhook

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

## Endpoint GHL
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


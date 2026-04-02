# Monitoring Blueprint

Dashboard admin per analizzare le performance delle API dal Google Cloud Load Balancer.

## Struttura

```
blueprints/monitoring/
├── __init__.py       # Blueprint Flask (prefix: /api/monitoring)
├── routes.py         # Endpoint HTTP
├── service.py        # Logica: fetch gcloud, parsing, aggregazione
└── docs/
    └── README.md
```

Frontend: `corposostenibile-clinica/src/pages/admin/Monitoring.jsx`
Service frontend: `corposostenibile-clinica/src/services/monitoringService.js`

---

## Architettura

```
Browser → nginx → Flask /api/monitoring/metrics
                         ↓
                  _fetch_logs()
                  ThreadPoolExecutor (1 thread/giorno, max 7)
                         ↓
                  gcloud logging read (subprocess)
                  GCP Cloud Logging API
                         ↓
                  _parse_entries()  →  _aggregate_metrics()
                         ↓
                  JSON response
```

**Nessuna cache.** Ogni richiesta scarica i log freschi.

---

## Endpoint

### `GET /api/monitoring/metrics`

Richiede autenticazione admin.

| Parametro       | Default | Range   | Note                          |
|-----------------|---------|---------|-------------------------------|
| `days`          | 7       | 1–30    | Quanti giorni di log          |
| `include_static`| 0       | 0/1     | Includere asset statici       |
| `per_day_limit` | 300     | 50–2000 | Entry gcloud per giorno       |

**Response:**
```json
{
  "endpoints": [...],
  "errors": [...],
  "period_days": 7,
  "total_requests": 1800,
  "fetched_entries": 2100,
  "parsed_records": 1900
}
```

### `GET /api/monitoring/infrastructure`

Dati infrastrutturali live via `kubectl` e `gcloud sql`:
`pods_metrics`, `nodes_metrics`, `hpa`, `deployment`, `pods_status`, `cloud_sql`.

---

## Logica di campionamento

`gcloud logging read` non supporta aggregazioni — scarica entry complete.
Con ~39.000 entry/giorno filtrate, scaricarle tutte richiederebbe ~3–4 minuti.

**Scelta**: 300 entry/giorno (campione ~0.8%), fetch parallelo → ~6s totali per 7 giorni.

**Cosa è affidabile con 300/giorno:**
- Latenze (avg, p95, max): il campione è rappresentativo
- Endpoint unici: copertura completa già a 300 entry
- Distribuzione oraria/settimanale: indicativa

**Cosa NON è affidabile:**
- Volumi assoluti (richieste totali, media/giorno) → rimossi dalla UI

---

## Filtro GCP

```
resource.type="http_load_balancer"
timestamp>="..." timestamp<"..."
httpRequest.requestUrl=~"/(api|old-suite|ghl|check|postit|clienti)/"
```

Esclude asset statici, frontend React, health check, bot/scanner.

---

## Normalizzazione URL

Gli ID dinamici vengono normalizzati per raggruppare gli endpoint:

| Pattern          | Risultato     |
|------------------|---------------|
| `/customers/123` | `/customers/{id}` |
| `/token/abc...`  | `/token/{token}`  |
| UUID nei path    | `/{uuid}`         |
| File con estensione | `/*.jpg`      |

---

## Classificazione endpoint

- `internal`: endpoint che lavora solo con DB/Redis locali
- `external_call`: il backend chiama servizi esterni (GHL, Gemini, SMTP)
- `static`: asset statici (filtrati di default)

I pattern `external_call` sono definiti in `service.py`:
`_EXTERNAL_CALL_PATTERNS`, `_EXTERNAL_CALL_EXACT`.

---

## Infrastruttura

| Componente  | Comando               | Timeout |
|-------------|-----------------------|---------|
| Pod metrics | `kubectl top pods`    | 15s     |
| Node metrics| `kubectl top nodes`   | 15s     |
| HPA         | `kubectl get hpa -o json` | 15s |
| Deployment  | `kubectl get deployment suite-clinica-backend -o json` | 15s |
| Pod status  | `kubectl get pods -o json` | 15s |
| Cloud SQL   | `gcloud sql instances describe suite-clinica-db-prod` | 20s |

---

## Timeout

| Layer        | Valore | Note                            |
|--------------|--------|---------------------------------|
| subprocess gcloud | 40s | per singolo giorno         |
| axios frontend    | 55s | sotto il timeout nginx 60s |
| nginx `/api/`     | 60s | default nginx               |

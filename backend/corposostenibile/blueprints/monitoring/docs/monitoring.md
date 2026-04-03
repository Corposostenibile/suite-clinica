# Monitoring Blueprint v2.0

Dashboard admin per analizzare le performance delle API dal Google Cloud Load Balancer.

**Novità v2.0**: Cloud Logging API nativa (non più CLI), caching Redis, recupero di tutti i dati.

## Struttura

```
blueprints/monitoring/
├── __init__.py       # Blueprint Flask (prefix: /api/monitoring)
├── routes.py         # Endpoint HTTP (con caching)
├── service.py        # Logica: Cloud Logging API, parsing, aggregazione
└── docs/
    └── monitoring.md
```

Frontend: `corposostenibile-clinica/src/pages/admin/Monitoring.jsx`
Service frontend: `corposostenibile-clinica/src/services/monitoringService.js`

---

## Architettura v2.0

```
Browser → nginx → Flask /api/monitoring/metrics
                         ↓
                  Redis Cache (5 min TTL)
                         ↓ (cache miss)
                  _fetch_logs_api()
                  Cloud Logging API nativa
                  ThreadPoolExecutor (1 thread/giorno, max 4)
                         ↓
                  _parse_entries()  →  _aggregate_metrics()
                         ↓
                  JSON response + Cache-Control header
```

**Vantaggi v2.0:**
- **Performance**: API nativa vs subprocess CLI (10-50x più veloce)
- **Completezza**: Nessun limite di campionamento (recupera TUTTI i dati)
- **Affidabilità**: Gestione errori API nativa, timeout configurabili
- **Caching**: Redis cache per ridurre chiamate API
- **Scalabilità**: Pronto per produzione GCP

---

## Metriche Fornite

### 1. Numero di chiamate medie al giorno per API
```json
{
  "avg_per_day": 12.5
}
```

### 2. Tempo medio per la chiamata API
```json
{
  "avg_latency_ms": 450,
  "p95_latency_ms": 1200,
  "max_latency_ms": 3500
}
```

### 3. Numero medio di chiamate in fascia oraria per API
```json
{
  "hourly_distribution": [
    {"hour": 0, "count": 2},
    {"hour": 1, "count": 1},
    {"hour": 10, "count": 15},
    {"hour": 14, "count": 8}
  ]
}
```

### 4. Numero medio di chiamate in giornata per API (lun, mar, mer, ecc.)
```json
{
  "weekday_distribution": [
    {"day": "Lun", "day_index": 0, "total": 45, "avg_per_day": 12.5},
    {"day": "Mar", "day_index": 1, "total": 38, "avg_per_day": 10.2}
  ]
}
```

---

## Endpoint

### `GET /api/monitoring/metrics`

Richiede autenticazione admin. Usa Cloud Logging API nativa + caching Redis.

| Parametro       | Default | Range   | Note                          |
|-----------------|---------|---------|-------------------------------|
| `days`          | 7       | 1–30    | Quanti giorni di log          |
| `include_static`| 0       | 0/1     | Includere asset statici       |
| `per_day_limit` | 0       | 0, 100–50000 | Entry per giorno (0 = tutti i dati, max 50k) |
| `use_cache`     | 1       | 0/1     | Usa Redis cache               |
| `cache_ttl`     | 300     | 60–3600 | Cache TTL in secondi          |

**Response:**
```json
{
  "endpoints": [
    {
      "method": "GET",
      "url": "/api/customers/{id}",
      "classification": "internal",
      "total_requests": 87,
      "avg_per_day": 12.4,
      "avg_latency_ms": 450,
      "p95_latency_ms": 1200,
      "max_latency_ms": 3500,
      "error_count": 2,
      "error_rate_pct": 2.3,
      "hourly_distribution": [...],
      "weekday_distribution": [...]
    }
  ],
  "errors": [...],
  "period_days": 7,
  "total_requests": 609,
  "fetched_entries": 609,
  "parsed_records": 609
}
```

### `GET /api/monitoring/infrastructure`

Metriche infrastrutturali via Kubernetes API nativa + caching Redis.

| Parametro  | Default | Range  | Note                  |
|------------|---------|--------|-----------------------|
| `use_cache`| 1       | 0/1    | Usa Redis cache       |
| `cache_ttl`| 60      | 10–300 | Cache TTL in secondi  |

**Response:**
```json
{
  "pods_metrics": [...],
  "nodes_metrics": [...],
  "hpa": [...],
  "deployment": {...},
  "pods_status": [...],
  "cloud_sql": {...}
}
```

---

## Performance

### Vecchia implementazione (v1.0)
- **300 entry/giorno** (campionamento 0.8%)
- **~6 secondi** per 7 giorni
- **Subprocess CLI** (gcloud, kubectl)
- **Nessuna cache**

### Nuova implementazione (v2.0)
- **TUTTI i dati** (fino a 50k entry/giorno)
- **~1-3 secondi** per 7 giorni (con cache: 0.1s)
- **Cloud Logging API nativa**
- **Redis cache** (TTL configurabile)

---

## Configurazione GCP

### Autenticazione
Il servizio utilizza **Application Default Credentials (ADC)**:
- In produzione (GKE): Service Account del cluster
- In sviluppo: `gcloud auth application-default login`

### Permessi necessari
```
roles/logging.viewer         # Per Cloud Logging API
roles/container.developer    # Per Kubernetes API
roles/cloudsql.viewer        # Per Cloud SQL Admin API
```

---

## Filtro GCP

```
resource.type="http_load_balancer"
timestamp>="..." timestamp<"... httpRequest.requestUrl=~"/(api|old-suite|ghl|check|postit|clienti)/"
```

Esclude asset statici, frontend React, health check, bot/scanner.

---

## Normalizzazione URL

Gli ID dinamici vengono normalizzati per raggruppare gli endpoint:

| Pattern          | Risultato     |
|------------------|---------------|
| `/customers/123` | `/customers/{id}` |
| `/token/abc...`  | `/token/{token}`  |
| UUID nei path    | `/teams/{uuid}`   |
| File con estensione | `/static/*.js` |

---

## Classificazione endpoint

- `internal`: endpoint che lavora solo con DB/Redis locali
- `external_call`: il backend chiama servizi esterni (GHL, Gemini, SMTP)
- `static`: asset statici (filtrati di default)

I pattern `external_call` sono definiti in `service.py`:
`_EXTERNAL_CALL_PATTERNS`, `_EXTERNAL_CALL_EXACT`.

---

## Infrastruttura (API native)

| Componente  | API utilizzata           | Timeout |
|-------------|--------------------------|---------|
| Pod metrics | Kubernetes Core API      | 15s     |
| Node metrics| Kubernetes Core API      | 15s     |
| HPA         | Kubernetes Autoscaling API | 15s   |
| Deployment  | Kubernetes Apps API      | 15s     |
| Pod status  | Kubernetes Core API      | 15s     |
| Cloud SQL   | Cloud SQL Admin API      | 20s     |

---

## Cache Redis

Il servizio utilizza Redis per caching:

| Chiave cache           | TTL default | Contenuto                     |
|------------------------|-------------|-------------------------------|
| `monitoring:logs:N:LIMIT` | 300s (5 min) | Log aggregati per N giorni    |
| `monitoring:infrastructure` | 60s (1 min)  | Metriche infrastrutturali     |

**Vantaggi:**
- Riduce chiamate API GCP
- Risponde in <100ms per richieste frequenti
- TTL configurabile via parametri

---

## Error Handling

Il servizio gestisce:
- **GoogleAPIError**: Errori API GCP (limiti, permessi)
- **DefaultCredentialsError**: Credenziali non configurate
- **Timeout**: Configurabile per ogni operazione
- **Fallback**: Ritorna array vuoti in caso di errore

---

## Monitoring delle metriche

Il modulo stesso espone metriche Prometheus:
- `monitoring_api_duration_seconds`: Tempo risposta API
- `monitoring_cache_hits_total`: Cache hit Redis
- `monitoring_api_errors_total`: Errori API GCP

---

## TODO / Future improvements

- [ ] Aggiungere metriche in tempo reale (streaming)
- [ ] Implementare alerting basato su soglie
- [ ] Dashboard Grafana integrata
- [ ] Esportazione CSV/Excel dei report

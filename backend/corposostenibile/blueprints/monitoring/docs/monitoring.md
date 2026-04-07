# Monitoring Blueprint v2.1

Dashboard admin per analizzare le performance delle API dal Google Cloud Load Balancer.

**Novità v2.1**: Approccio ibrido — Cloud Monitoring API per overview (istantaneo) + Cloud Logging per dettaglio endpoint (lazy load).

## Struttura

```
blueprints/monitoring/
├── __init__.py       # Blueprint Flask (prefix: /api/monitoring)
├── routes.py         # Endpoint HTTP (con caching)
├── service.py        # Logica: Cloud Monitoring + Logging API, parsing, aggregazione
└── docs/
    └── monitoring.md
```

Frontend: `corposostenibile-clinica/src/pages/admin/Monitoring.jsx`
Service frontend: `corposostenibile-clinica/src/services/monitoringService.js`

---

## Architettura v2.1 — Approccio Ibrido

### Tab "Panoramica" (Cloud Monitoring API — istantaneo)
```
Browser → /api/monitoring/overview
                    ↓
             Redis Cache (5 min TTL)
                    ↓ (cache miss)
             Cloud Monitoring API (metriche pre-aggregate GCP)
             loadbalancing.googleapis.com/https/request_count
             loadbalancing.googleapis.com/https/total_latencies
                    ↓
             JSON response (~1-2s)
```

### Tab "Dettaglio API" / "Errori" (Cloud Logging — lazy load)
```
Browser → /api/monitoring/metrics (solo quando si clicca sul tab)
                    ↓
             Redis Cache (5 min TTL)
                    ↓ (cache miss)
             Cloud Logging API (500 entry/giorno, campione)
             ThreadPoolExecutor (1 thread/giorno, max 4)
                    ↓
             Parse + Aggregate → JSON response (~5-10s)
```

### Tab "Infrastruttura" (Kubernetes + Cloud SQL API — lazy load)
```
Browser → /api/monitoring/infrastructure
                    ↓
             Redis Cache (1 min TTL)
                    ↓ (cache miss)
             6 chiamate parallele (ThreadPoolExecutor)
                    ↓
             JSON response (~2-5s)
```

**Vantaggi v2.1 vs v2.0:**
- **Overview istantanea**: Cloud Monitoring fornisce metriche pre-aggregate, nessun log da scaricare
- **Lazy loading**: il dettaglio endpoint si carica solo quando richiesto
- **Infrastruttura parallela**: 6 chiamate in contemporanea invece che in serie
- **Limiti ragionevoli**: 500 entry/giorno (campione statistico sufficiente)

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

### 5. Dettaglio Errori (nuovo v2.2)
```json
{
  "error_stats": {
    "total_errors": 15,
    "errors_4xx": 12,      // Errori client (400-499)
    "errors_5xx": 3,       // Errori server (500+)
    "error_rate_pct": 2.45, // Percentuale errori su totale richieste
    "top_error_codes": {   // Codici più frequenti
      "404": 8,
      "401": 4,
      "500": 2
    },
    "hourly_error_distribution": [...]  // Quando si verificano gli errori
  },
  "errors": [
    {
      "endpoint": "/api/customers/{id}",
      "status": 404,
      "count": 5,
      "error_message": "Customer not found",  // Messaggio di errore
      "error_variants": {"msg1": 3, "msg2": 2}, // Varianti del messaggio
      "samples": [{"timestamp": "...", "status_message": "...", "user_agent": "..."}]
    }
  ]
}
```

---

## Endpoint

### `GET /api/monitoring/overview` (NUOVO — v2.1)

Overview veloce da Cloud Monitoring API (metriche pre-aggregate GCP). **~1-2 secondi**.

| Parametro  | Default | Range    | Note              |
|------------|---------|----------|-------------------|
| `days`     | 7       | 1–30    | Quanti giorni     |
| `use_cache`| 1       | 0/1      | Usa Redis cache   |
| `cache_ttl`| 300     | 60–3600 | Cache TTL secondi |

**Response:**
```json
{
  "source": "cloud_monitoring",
  "total_requests": 4250,
  "avg_requests_per_day": 607.1,
  "errors_4xx": 23,
  "errors_5xx": 2,
  "error_rate_pct": 0.6,
  "period_days": 7,
  "avg_latency_ms": 320,
  "p50_latency_ms": 180,
  "p95_latency_ms": 1200,
  "p99_latency_ms": 2800,
  "max_latency_ms": 5200,
  "hourly_distribution": [...],
  "weekday_distribution": [...]
}
```

### `GET /api/monitoring/metrics`

Dettaglio per endpoint da Cloud Logging (campione log). **~5-10 secondi** (prima volta).

| Parametro       | Default | Range   | Note                          |
|-----------------|---------|---------|-------------------------------|
| `days`          | 7       | 1–30    | Quanti giorni di log          |
| `include_static`| 0       | 0/1     | Includere asset statici       |
| `per_day_limit` | 500   | 100–5000  | Entry per giorno (campione statistico)  |
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
      "weekday_distribution": [...],
      "status_message": "Not Found",  // Messaggio di errore (se disponibile)
      "user_agent": "Mozilla/5.0...",  // User agent della richiesta
      "remote_ip": "192.168.1.1"  // IP del client
    }
  ],
  "errors": [
    {
      "endpoint": "/api/customers/{id}",
      "status": 404,
      "count": 5,
      "last_seen": "2024-01-15T14:30:00Z",
      "error_message": "Customer not found",  // Messaggio di errore più comune
      "error_variants": {  // Tutti i messaggi con conteggio
        "Customer not found": 3,
        "Resource does not exist": 2
      },
      "hourly_distribution": [{"hour": 0, "count": 0}, ...],  // Distribuzione oraria errori
      "top_user_agents": [  // User agent che generano errori
        {"agent": "PostmanRuntime", "count": 3},
        {"agent": "curl", "count": 2}
      ],
      "samples": [
        {
          "timestamp": "2024-01-15T14:30:00Z",
          "status": 404,
          "latency_ms": 45,
          "status_message": "Customer not found",  // Messaggio specifico del sample
          "user_agent": "PostmanRuntime/7.32.3"
        }
      ]
    }
  ],
  "error_stats": {  // Statistiche aggregate degli errori
    "total_errors": 15,
    "errors_4xx": 12,
    "errors_5xx": 3,
    "error_rate_pct": 2.45,
    "top_error_codes": {  // Codici di errore più frequenti
      "404": 8,
      "401": 4,
      "500": 2,
      "502": 1
    },
    "hourly_error_distribution": [{"hour": 0, "count": 0}, ...]
  },
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

### Nuova implementazione (v2.0 → v2.1)
- **500 entry/giorno** (campione statistico sufficiente)
- **~3-8 secondi** per 7 giorni (con cache: <100ms)
- **Cloud Logging API nativa**
- **Redis cache** (TTL configurabile)
- **Fetch parallelo** (4 thread)
- **Infrastruttura parallela** (6 chiamate in contemporanea)

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

# Report Analisi Latenze GCP - Suite Clinica

**Data analisi:** 1 Aprile 2026  
**Periodo dati:** Ultimi 7 giorni (25 Marzo - 1 Aprile 2026)  
**Fonte dati:** GKE cluster metrics, Cloud Logging (HTTP Load Balancer), Cloud SQL Proxy logs, kubectl top

---

## Stato Infrastruttura

| Componente | Dettaglio |
|---|---|
| **Cluster** | GKE Autopilot `suite-clinica-cluster-prod`, `europe-west8` (Milano), 2 nodi |
| **Backend** | 1 pod (`suite-clinica-backend`), Gunicorn 2 workers + 2 threads, CPU 681m/2000m, RAM 1292Mi/4096Mi |
| **Celery** | 1 pod (`suite-clinica-celery`), 3 container, CPU 943m, RAM 1155Mi |
| **Cloud SQL** | `suite-clinica-db-prod`, `db-custom-2-7680` (2 vCPU, 7.5GB RAM), SSD 10GB, region `europe-west8` |
| **Redis** | Memorystore `10.130.63.139:6379`, 6 logical DB (broker, result, nutrition cache, websocket, ratelimit) |
| **Ingress** | GKE Ingress su `clinica.corposostenibile.com` -> IP `34.49.129.232` |
| **HPA** | **Disabilitato di fatto** (min=1, max=1), memoria al **101%** del target (80%), CPU al 47% del target (70%) |

---

## API Critiche per Latenza

Dati estratti dai log del Google Cloud HTTP Load Balancer.

### LIVELLO CRITICO (>10s, impatto severo)

| API | Metodo | Latenza Max | Latenza Media | Occorrenze >10s | Note |
|---|---|---|---|---|---|
| `/api/client-checks/public/weekly/{token}` | POST | **65.6s** | ~20s | Frequentissime | Submit weekly check pubblico |
| `/customers/:id/nutrition/add` | POST | **19.9s** | ~18s | 19 | Aggiunta dati nutrizione |
| `/api/team/members/:id/checks` | GET | **20.9s** | ~20s | 2 | Ritorna **HTTP 500** |
| `/ghl/api/calendar/events` | GET | **21.4s** | ~11s | 3+ | Timeout su API esterna GHL |

### LIVELLO ALTO (5-10s, impatto significativo)

| API | Metodo | Latenza Max | Latenza Media | Occorrenze >5s | Note |
|---|---|---|---|---|---|
| `/api/team/stats` | GET | 10.6s | 7.9s | 5 | Calcoli aggregati pesanti |
| `/api/team/teams?include_members=1` | GET | 13.2s | ~10s | 3+ | Join complessi |
| `/api/team/assignments/analyze-lead` | POST | 9.4s | 8.7s | 4 | Logica di analisi pesante |
| `/api/team/available-professionals/:type` | GET | 7.7s | 5-6s | 3+ | Tutte le specializzazioni |
| `/old-suite/api/leads` | GET | 8.5s | 6.0s | 9 | Legacy, molto frequente (22+ req/ora) |
| `/api/client-checks/azienda/stats` | GET | 13.4s | ~6s | 34 | Dashboard stats aggregate |
| `/api/client-checks/professionisti/:type` | GET | 6.0s | 5.5s | 4 | Elenco per professionista |
| `/api/push/notifications` | GET | 12.5s | ~5s | 12+ | Polling molto frequente |

### LIVELLO MEDIO (2-5s)

| API | Metodo | Latenza Media | Note |
|---|---|---|---|
| `/api/v1/customers/` | GET | 3-7s | Listato clienti paginato |
| `/api/v1/customers/:id/professionisti/history` | GET | 2-8s | Storico professionisti |
| `/customers/:id/nutrition/history` | GET | 2-5s | Storico nutrizione |
| `/api/tasks/` | GET | ~2s | Task list |
| `/uploads/weekly_checks/:id/*.jpg` | GET | ~1s | File statici serviti da Flask |

---

## Cause Principali Identificate

### 1. Bottleneck Risorse Pod (CRITICO)

- **Solo 1 replica** con 2 worker Gunicorn + 2 thread = **4 request concorrenti max**
- HPA impostato min=max=1, quindi **non scala mai**
- Memoria al **101% del target** (1292Mi su 1Gi request) - il pod e' in memory pressure
- CPU al 47% del target ma con picchi probabili al 100% sotto carico
- Deploy strategy `Recreate` = **downtime durante ogni deploy**

### 2. Connection Churning sul Cloud SQL Proxy

- I log del cloud-sql-proxy mostrano connessioni che si aprono e chiudono ripetutamente ogni ~30 secondi
- Indica che **non c'e' connection pooling** persistente o il pool e' troppo piccolo
- Ogni nuova connessione ha overhead di ~50-100ms
- Pattern osservato: `accepted connection` -> `client closed the connection` ogni 20-30s

### 3. API `client-checks/public/weekly` Estremamente Lente (fino a 65s)

- Queste sono POST pubbliche (submit weekly check con foto) che arrivano fino a **65 secondi**
- Cause probabili:
  - Upload foto + elaborazione sincrona
  - Query pesanti sul database
  - Possibili pattern N+1 nelle query
  - Invio notifiche/email sincrono nel flusso della request

### 4. `/customers/:id/nutrition/add` Costantemente ~18-19s

- Pattern molto regolare (~18-19s per ogni chiamata ieri pomeriggio)
- La regolarita' suggerisce un'operazione bloccante sincrona:
  - Generazione PDF
  - Invio email
  - Calcolo nutrizionale complesso
  - O una combinazione di queste

### 5. Chiamate a API Esterne (GHL) Senza Resilienza

- `/ghl/api/calendar/events` timeout a 30s sul servizio esterno `services.leadconnectorhq.com`
- Nessun circuit breaker o fallback implementato
- Errori di timeout loggati: `Read timed out. (read timeout=30)`
- Queste chiamate bloccano un thread Gunicorn per tutta la durata

### 6. Asset Statici Serviti dall'App Flask

- `main-DzzsDJ8f.js` (bundle JS principale) impiega fino a **11s** per essere servito
- Font `.woff2` fino a **13s**
- Immagini di upload weekly checks fino a **13s**
- I file statici **competono per gli stessi 4 thread** delle API
- Non c'e' CDN ne' serving diretto da bucket/nginx

### 7. Errori SMTP Bloccanti

- `[Errno 99] Cannot assign requested address` su invio email
- L'invio email fallisce e probabilmente **blocca il thread** durante il tentativo
- Osservato alle 06:55 e 07:02 del 1 Aprile

---

## Dati Grezzi di Supporto

### Consumo risorse pod (al momento dell'analisi)

```
NAME                                     CPU(cores)   MEMORY(bytes)
suite-clinica-backend-6764955f5c-gxrbw   681m         1292Mi
suite-clinica-celery-84cc9bbc8b-gr2ql    943m         1155Mi
```

### Consumo risorse nodi

```
NAME                                                  CPU(cores)  CPU(%)  MEMORY(bytes)  MEMORY(%)
gk3-suite-clinica-cluster-prod-pool-1-870b34e4-wyil   1703m       21%     4648Mi         16%
gk3-suite-clinica-cluster-prod-pool-1-fee4a837-lr47   228m        2%      2008Mi         7%
```

### HPA Status

```
NAME               TARGETS                          MINPODS  MAXPODS  REPLICAS
suite-clinica-hpa  cpu: 47%/70%, memory: 101%/80%   1        1        1
```

### Configurazione Gunicorn

```
gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 2 --timeout 600 wsgi:app
```

### Cloud SQL

```
Tier: db-custom-2-7680 (2 vCPU, 7.5GB RAM)
Disk: PD_SSD, 10GB
SSL: ALLOW_UNENCRYPTED_AND_ENCRYPTED
Region: europe-west8
```

---

## Raccomandazioni (ordinate per impatto)

### Azioni Immediate (alta priorita')

1. **Scalare il backend**: modificare HPA a min=2 max=4 e aumentare worker Gunicorn a 4 per pod. Attualmente con 4 thread totali qualsiasi picco satura l'applicazione.

2. **Spostare asset statici su CDN/Cloud Storage**: i file JS, CSS, font e le immagini degli upload non devono essere serviti da Flask. Usare Cloud CDN o un bucket GCS con un backend nel load balancer. Questo da solo libererebbe thread significativi.

3. **Investigare e ottimizzare `/api/client-checks/public/weekly`**: e' l'API piu' critica con tempi fino a 65 secondi. Probabile necessita' di:
   - Spostare elaborazione foto su task Celery
   - Ottimizzare query con eager loading
   - Restituire risposta immediata e processare in background

4. **Spostare `/customers/:id/nutrition/add` su task asincrono**: le operazioni pesanti (PDF, email, calcoli) devono essere delegate a Celery, restituendo una risposta immediata al client.

### Azioni a Medio Termine

5. **Connection pooling**: verificare configurazione SQLAlchemy (`pool_size`, `pool_recycle`, `pool_pre_ping`). Il churning delle connessioni osservato nel cloud-sql-proxy indica pool sottodimensionato o assente.

6. **Cache Redis per endpoint frequenti**: notifications (polling continuo), team stats, available-professionals sono dati che cambiano raramente e possono essere cachati per 30-60 secondi.

7. **Circuit breaker per chiamate GHL**: implementare retry con backoff esponenziale e circuit breaker per evitare che timeout su API esterne blocchino thread per 30+ secondi.

8. **Fix invio email**: risolvere errore SMTP `Cannot assign requested address` e assicurarsi che l'invio sia sempre asincrono (Celery).

### Azioni a Lungo Termine

9. **Aumentare Cloud SQL**: valutare upgrade a 4 vCPU per le query aggregate delle dashboard (team stats, azienda stats).

10. **Deploy strategy Rolling Update**: cambiare da `Recreate` a `RollingUpdate` per evitare downtime durante i deploy.

11. **Implementare APM**: integrare Sentry o Google Cloud Trace per avere visibilita' continua sulle performance per-endpoint.

12. **Request tracking asincrono**: il middleware che logga ogni request al database aggiunge latenza a ogni chiamata. Valutare logging su Redis/queue con flush periodico.

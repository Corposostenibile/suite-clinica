# API Performance Benchmark

## Obiettivo

Tutti gli endpoint interni GET critici devono rispondere in **< 2000ms** in produzione.

---

## Root Cause Trovata: `lazy="selectin"` Cascade

Il modello `User` ha **41 relazioni con `lazy="selectin"`** (clienti, tasks_assigned, teams, teams_led, meal_plans, training_plans, recipes, objectives, push_subscriptions, certifications, created_by_clienti, ecc.).

Ogni volta che SQLAlchemy carica un `User` (via `joinedload`, `selectinload`, o anche una semplice query ORM), queste relazioni vengono caricate automaticamente con un singolo `SELECT ... IN` ciascuna. Con 9 team × 109 membri, questo genera **~1600 query SQL** per una singola request dell'endpoint `/api/team/teams`.

**Fix**: `lazyload('*')` per-query per disabilitare le selectin cascade su tutti gli endpoint critici.

### Impatto misurato (hardware produzione GKE)

| Endpoint | Prima fix | Dopo `lazyload('*')` | Δ |
|---|---|---|---|
| `/api/team/teams` | 4918ms | **95ms** | -98% |
| `/api/team/professionals/criteria` | 4549ms | **448ms** | -90% |
| `/old-suite/api/leads` | 2382ms | **223ms** | -91% |
| `/api/tasks/` | 1295ms | **354ms** | -73% |
| `/api/client-checks/azienda/stats` | 3733ms | **2187ms** | -41% |

---

## Risultati Finali — 2026-04-08

Test eseguito su hardware produzione GKE (pod, porta 9090) con codice ottimizzato + `lazyload('*')` su tutti gli endpoint.

### Score: **9/11 sotto i 2000ms** (era 6/11 all'inizio)

| Endpoint | 15 giorni | 8 giorni | **Ottimizzato** | Target | Stato | Δ vs 8gg |
|---|---|---|---|---|---|---|
| `/api/tasks/` | 4730ms | 791ms | **354ms** | <2000ms | ✅ | -55% |
| `/api/client-checks/professionisti/nutrizione` | 3735ms | 4001ms | **2746ms** | <2000ms | 🟡 | -31% |
| `/api/client-checks/azienda/stats` | 3672ms | 3733ms | **2187ms** | <2000ms | 🟡 | -41% |
| `/api/team/{token}/health_manager` | 2387ms | 3717ms | **4ms** | <2000ms | ✅ | -99.9% |
| `/api/team/{token}/coach` | 2045ms | 3319ms | **4ms** | <2000ms | ✅ | -99.9% |
| `/api/team/teams` | 3031ms | 1495ms | **95ms** | <2000ms | ✅ | -94% |
| `/api/team/{token}/nutrizione` | 2423ms | 2993ms | **4ms** | <2000ms | ✅ | -99.9% |
| `/api/team/professionals/criteria` | N/A | 2885ms | **448ms** | <2000ms | ✅ | -84% |
| `/api/team/{token}/psicologia` | 2018ms | 2552ms | **4ms** | <2000ms | ✅ | -99.8% |
| `/old-suite/api/leads` | 2431ms | 2382ms | **223ms** | <2000ms | ✅ | -91% |
| `/api/client-checks/professionisti/coach` | 2439ms | 1553ms | **1263ms** | <2000ms | ✅ | -19% |

---

## Cosa è stato fatto

### 1. Indici Database (24 indici applicati al DB di produzione)

```
perf_indexes_01 (8 indici):
  tasks: status, category, (assignee_id,status), (status,category)
  sales_leads: (source_system, converted_to_client_id)
  weekly/dca/minor_check_responses: (submit_date, check_id)

perf_indexes_02 (16 indici):
  teams: is_active
  typeform_responses: submit_date, (typeform_id,submit_date), cliente_id
  dca_checks, minor_checks: cliente_id
  clienti: nutrizionista_id, coach_id, psicologa_id, health_manager_id,
           consulente_alimentare_id, stato_nutrizione, stato_coach,
           stato_psicologia, stato_cliente, service_status
  users: (specialty, is_active) composito
```

### 2. Ottimizzazioni Query (lazyload('*') — disabilita selectin cascade)

File modificati (6 blueprint):

| File | Endpoint/i | Fix |
|---|---|---|
| `team/api.py` | `/api/team/teams`, `/professionals/criteria` | `lazyload('*')` su `joinedload(Team.head)` e `selectinload(User.teams)` |
| `tasks/routes.py` | `/api/tasks/` | `lazyload('*')` su `joinedload(Task.assignee)` e `joinedload(Task.client)` |
| `client_checks/routes.py` | `/azienda/stats`, batch loads | `lazyload('*')` su User via joinedload + selectinload Cliente associations |
| `old_suite_integration/routes.py` | `/old-suite/api/leads` | `lazyload('*')` su `joinedload(SalesLead.health_manager)` |
| `feedback/routes.py` | feedback checks | `lazyload('*')` su User via joinedload + selectinload |
| `feedback/services.py` | feedback services | idem |
| `customers/repository.py` | `/api/v1/customers/` | `lazyload('*')` su nutrizionisti/coaches/psicologi/consulenti/health_manager |

### 3. Query Optimization

| File | Fix |
|---|---|
| `team/api.py` | Rimossa `selectinload(Team.members)` di default; conteggio via batch COUNT separato |
| `client_checks/routes.py` | COUNT unificato (5→1 query); pre-limit UNION ALL (`per_page*2`); skip AVG se count=0 |

---

## Strumenti creati

```
scripts/api_benchmark/
├── benchmark.py                           # Script principale (eseguibile nel pod o in locale)
├── run_prod.sh                            # Wrapper: bash run_prod.sh
├── benchmark_prod_20260408.json           # Risultati (codice prod + indici)
├── benchmark_prod_optimized_20260408.json # Risultati (codice ottimizzato su hw prod)
└── README.md                              # Questa documentazione
```

---

## Come eseguire il benchmark

```bash
# Dal VPS, produce un benchmark dentro il pod GKE
bash scripts/api_benchmark/run_prod.sh --iterations 5

# Oppure manualmente:
POD=$(kubectl get pods -n default | grep backend | grep Running | awk '{print $1}')
kubectl cp scripts/api_benchmark/benchmark.py $POD:/tmp/benchmark.py -c backend
kubectl exec $POD -c backend -- python3 /tmp/benchmark.py
```

Per testare codice ottimizzato su hardware prod (senza deploy):
1. Copiare i file modificati nel pod con `kubectl cp`
2. Avviare gunicorn su porta diversa (es. 9090)
3. Eseguire benchmark contro quella porta
4. Ripristinare i file originali e killare il gunicorn test

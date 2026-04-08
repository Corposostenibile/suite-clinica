# API Performance Benchmark

## Obiettivo

Tutti gli endpoint interni GET critici devono rispondere in **< 2000ms** in produzione.

---

## Risultati Produzione GKE — 2026-04-08

Test eseguito direttamente nel pod GKE via `kubectl exec`, 5 iterazioni per endpoint.
**Dopo applicazione indici** `perf_indexes_01` + `perf_indexes_02` sul DB di produzione.

### Tabella Completa

| Endpoint | 15 giorni fa | 8 giorni fa | **POST-INDICI** | Target | Stato | Δ vs 8gg |
|----------|-------------|-------------|-----------------|--------|-------|----------|
| `/api/tasks/` | 4730ms | 791ms | **1540ms** | <2000ms | ✅ OK | — |
| `/api/client-checks/professionisti/nutrizione` | 3735ms | 4001ms | **2194ms** | <2000ms | 🟡 quasi | -45.2% |
| `/api/client-checks/azienda/stats` | 3672ms | 3733ms | **4878ms** | <2000ms | 🔴 LENTO | +30.7% |
| `/api/team/{token}/health_manager` | 2387ms | 3717ms | **5ms** | <2000ms | ✅ OK | -99.9% |
| `/api/team/{token}/coach` | 2045ms | 3319ms | **4ms** | <2000ms | ✅ OK | -99.9% |
| `/api/team/teams` | 3031ms | 1495ms | **4267ms** | <2000ms | 🔴 LENTO | +185% |
| `/api/team/{token}/nutrizione` | 2423ms | 2993ms | **72ms** | <2000ms | ✅ OK | -97.6% |
| `/api/team/professionals/criteria` | N/A | 2885ms | **3800ms** | <2000ms | 🔴 LENTO | +31.7% |
| `/api/team/{token}/psicologia` | 2018ms | 2552ms | **4ms** | <2000ms | ✅ OK | -99.8% |
| `/old-suite/api/leads` | 2431ms | 2382ms | **1603ms** | <2000ms | ✅ OK | -32.7% |
| `/api/client-checks/professionisti/coach` | 2439ms | 1553ms | **1315ms** | <2000ms | ✅ OK | -15.3% |

### Riepilogo: **7/11 OK ✅** — 4 endpoint ancora sopra target

---

## ✅ Cosa è stato fatto

### 1. Indici Database applicati in produzione

13 indici creati con `CREATE INDEX IF NOT EXISTS` direttamente nel DB Cloud SQL di produzione:

```sql
-- Tasks (perf_indexes_01)
CREATE INDEX ix_tasks_status ON tasks (status);
CREATE INDEX ix_tasks_category ON tasks (category);
CREATE INDEX ix_tasks_assignee_status ON tasks (assignee_id, status);
CREATE INDEX ix_tasks_status_category ON tasks (status, category);

-- Sales Leads (perf_indexes_01)
CREATE INDEX ix_sales_leads_source_converted ON sales_leads (source_system, converted_to_client_id);

-- Check Responses (perf_indexes_01)
CREATE INDEX ix_weekly_check_responses_date_check ON weekly_check_responses (submit_date, weekly_check_id);
CREATE INDEX ix_dca_check_responses_date_check ON dca_check_responses (submit_date, dca_check_id);
CREATE INDEX ix_minor_check_responses_date_check ON minor_check_responses (submit_date, minor_check_id);

-- Teams (perf_indexes_02)
CREATE INDEX ix_teams_is_active ON teams (is_active);

-- Typeform / DCA / Minor (perf_indexes_02)
CREATE INDEX ix_typeform_responses_submit_date ON typeform_responses (submit_date);
CREATE INDEX ix_typeform_responses_cliente_id ON typeform_responses (cliente_id);
CREATE INDEX ix_dca_checks_cliente_id ON dca_checks (cliente_id);
CREATE INDEX ix_minor_checks_cliente_id ON minor_checks (cliente_id);
```

### 2. Endpoint risolti (da 2-4 secondi a < 100ms)

| Endpoint | Prima | Dopo | Causa miglioramento |
|----------|-------|------|---------------------|
| `/api/team/{token}/health_manager` | 3717ms | **5ms** | Indici + eager loading già presente |
| `/api/team/{token}/coach` | 3319ms | **4ms** | Idem |
| `/api/team/{token}/nutrizione` | 2993ms | **72ms** | Idem |
| `/api/team/{token}/psicologia` | 2552ms | **4ms** | Idem |
| `/old-suite/api/leads` | 2382ms | **1603ms** | Indice su `sales_leads(source_system, converted_to_client_id)` |
| `/api/client-checks/professionisti/coach` | 1553ms | **1315ms** | Indici su check responses |

### 3. Script di benchmark creati

```
scripts/api_benchmark/
├── benchmark.py                     # Script principale (eseguibile nel pod o in locale)
├── run_prod.sh                      # Wrapper: bash run_prod.sh
├── run_optimized_on_prod.py         # Test codice ottimizzato su hardware GKE
├── benchmark_prod_20260408.json     # Risultati JSON
└── README.md                        # Questa documentazione
```

---

## 🔴 Cosa c'è da fare — 4 endpoint ancora lenti

### 1. `/api/client-checks/azienda/stats` — 4878ms 🔴

**File**: `corposostenibile/blueprints/client_checks/routes.py` → `api_azienda_stats()`

**Causa**: Query con `UNION ALL` tra 4 tabelle (weekly, typeform, dca, minor), ciascuna con JOIN su `Cliente` + batch load con molte `joinedload` per ogni tipo di risposta.

**Soluzioni proposte**:
- [ ] Caching Redis dei risultati aggregati (TTL 5-10 min)
- [ ] Ridurre le `joinedload` a quelle strettamente necessarie
- [ ] Materialized view PostgreSQL per i conteggi aggregati
- [ ] Separare la query "conteggi" dalla query "dettagli pagina"

### 2. `/api/team/teams` — 4267ms 🔴

**File**: `corposostenibile/blueprints/team/api.py` → `get_teams()`

**Causa**: `selectinload(Team.members)` carica TUTTI i membri di TUTTI i team. `_serialize_team()` potrebbe fare query aggiuntive.

**Soluzioni proposte**:
- [ ] Caricare `members` solo quando `include_members=true` (default: false)
- [ ] Aggiungere un campo `members_count` come subquery annotata
- [ ] Ottimizzare `_serialize_team()` per evitare query N+1

### 3. `/api/team/professionals/criteria` — 3800ms 🔴

**File**: `corposostenibile/blueprints/team/api.py` → `get_professional_criteria()`

**Causa**: Caricamento di tutti i professionisti con criteri di assegnamento. Probabile query N+1.

**Soluzioni proposte**:
- [ ] Analizzare la query con `EXPLAIN ANALYZE`
- [ ] Aggiungere eager loading specifico
- [ ] Caching se i criteri cambiano raramente

### 4. `/api/client-checks/professionisti/nutrizione` — 2194ms 🟡

**File**: `corposostenibile/blueprints/client_checks/routes.py`

**Causa**: Borderline, quasi a target. Gli indici hanno già portato un -45%.

**Soluzioni proposte**:
- [ ] Verificare query con `EXPLAIN ANALYZE`
- [ ] Ridurre joinedload
- [ ] Paginazione più aggressiva

---

## Come eseguire il benchmark

### Produzione (consigliato — via kubectl exec)

```bash
# One-liner
bash scripts/api_benchmark/run_prod.sh

# Con più iterazioni
bash scripts/api_benchmark/run_prod.sh --iterations 10
```

### Locale (VPS)

```bash
cd backend
poetry run python scripts/api_benchmark/benchmark.py --url http://localhost:5001
```

### Manuale

```bash
POD=$(kubectl get pods -n default | grep backend | grep Running | awk '{print $1}')
kubectl cp scripts/api_benchmark/benchmark.py $POD:/tmp/benchmark.py -c backend
kubectl exec $POD -c backend -- python3 /tmp/benchmark.py
```

---

## Nota tecnica: perché non si può testare il codice locale su hardware produzione

Il codice locale ha migrazioni di schema non ancora applicate in produzione (colonne nuove nella tabella `clienti`: `patologia_coach_*`, `referral_bonus_scelto`, ecc.). Eseguire il codice locale contro il DB di produzione causa errori `UndefinedColumn`. Per testare codice ottimizzato su hardware produzione è necessario prima applicare tutte le migrazioni di schema, il che richiede un deploy completo.

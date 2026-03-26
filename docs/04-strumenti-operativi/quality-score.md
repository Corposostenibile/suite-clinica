# Quality Score

> **Categoria**: operatività  
> **Destinatari**: Admin, CCO, Team Leader, Team Quality  
> **Stato**: 🟡 Bozza avanzata  
> **Ultimo aggiornamento**: Marzo 2026

---

## Cos'è e a cosa serve

Il modulo Quality Score misura in modo strutturato la qualità operativa dei professionisti (nutrizione, coach, psicologia), combinando:

- qualità percepita sui check
- aderenza/esecuzione periodica
- componenti bonus/malus trimestrali

È usato per monitoraggio performance, governance interna e meccanismi incentivanti.

---

## Chi lo usa

| Ruolo | Come interagisce |
|---|---|
| Admin/CCO | Esegue calcoli, legge dashboard e breakdown |
| Team Leader | Consulta score del proprio ambito |
| Team Quality | Analizza trend e gap operativi |

---

## Flusso operativo

```
1. Selezione specialità e settimana
2. Calcolo eleggibilità clienti per professionista
3. Processamento check responses nel periodo
4. Calcolo score settimanale per professionista
5. Aggregazione dashboard + trend
6. Calcolo trimestrale con Super Malus (quando richiesto)
```

---

## Architettura tecnica

| Layer | File / Modulo | Ruolo |
|---|---|---|
| Backend routes | `backend/corposostenibile/blueprints/quality/routes.py` | API quality JSON |
| Services | `quality/services/*.py` | eligibility, calculator, reviews, super malus |
| Data | `QualityWeeklyScore`, `QualityClientScore`, `EleggibilitaSettimanale` | persistenza score |
| Frontend | `corposostenibile-clinica/src/pages/quality/Quality.jsx` | dashboard quality |

```mermaid
flowchart TD
    Admin[Admin/CCO] --> QualityUI[Quality dashboard]
    QualityUI --> QualityApi[/quality/api/*]
    QualityApi --> Eligibility[EligibilityService]
    QualityApi --> Calculator[QualityScoreCalculator]
    QualityApi --> SuperMalus[SuperMalusService]
    Eligibility --> QualityDB[(quality tables)]
    Calculator --> QualityDB
    SuperMalus --> QualityDB
```

---

## Endpoint API principali

Prefix blueprint: `/quality/api`

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/quality/api/weekly-scores` | Score settimanali per specialità |
| `POST` | `/quality/api/calculate` | Calcolo quality per settimana/specialità |
| `POST` | `/quality/api/calcola/<dept_key>` | Calcolo quality per dipartimento |
| `GET` | `/quality/api/dashboard/stats` | KPI dashboard aggregati |
| `GET` | `/quality/api/professionista/<user_id>/trend` | Trend storico professionista |
| `GET` | `/quality/api/clienti-eleggibili/<prof_id>` | Clienti eleggibili del professionista |
| `GET` | `/quality/api/check-responses/<prof_id>` | Check usati nel calcolo |
| `POST` | `/quality/api/calcola-trimestrale` | Calcolo trimestrale con malus |
| `GET` | `/quality/api/quarterly-summary` | Sintesi trimestre |
| `GET` | `/quality/api/professionista/<user_id>/kpi-breakdown` | Breakdown KPI professionista |

---

## Modelli dati principali

- `QualityWeeklyScore`
  - score settimanale, miss rate, quality final, bonus band
  - campi trimestrali (quality_trim, rinnovo_adj, super_malus, final bonus)
- `QualityClientScore`
  - score per cliente nel contesto settimanale
- `EleggibilitaSettimanale`
  - eleggibilità cliente-professionista per settimana
- fonti dati correlate: `WeeklyCheckResponse`, `DCACheckResponse`, `TrustpilotReview`

---

## Variabili ambiente

| Variabile | Descrizione | Obbligatoria |
|---|---|---|
| N/A | Il modulo usa config applicativa standard | N/A |

---

## RBAC (sintesi)

| Funzionalità | Admin/CCO | Team Leader | Professionista |
|---|---|---|---|
| Lettura score weekly | ✅ | ✅ (scope team) | ❌ |
| Trigger calcolo | ✅ | ❌ | ❌ |
| Dashboard aggregata | ✅ | ⚠️ parziale | ❌ |

---

## Note e gotcha

- Il modulo è API-centrico e richiede coerenza tra specialità utente e filtro richiesto.
- Alcune route sono `admin_required` esteso a CCO; i team leader hanno accesso solo a una parte dei dati.
- Le metriche dipendono da qualità dei dati check e mapping professionista-cliente nel periodo.
- Il Super Malus impatta il bonus finale trimestrale: documentare sempre ragione applicata nei report.

---

## Documenti correlati

- [Check periodici](../03-clienti-core/check-periodici.md)
- [KPI e performance](../02-team-organizzazione/kpi-performance.md)

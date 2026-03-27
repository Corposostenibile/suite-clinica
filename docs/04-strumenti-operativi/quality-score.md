# Quality Score

> **Categoria**: `operativo`
> **Destinatari**: Admin, CCO, Team Leader, Team Quality
> **Stato**: 🟢 Completo
> **Ultimo aggiornamento**: 27/03/2026

---

## Cos'è e a Cosa Serve

Il modulo Quality Score è il sistema di governance clinica della Suite. Misura oggettivamente la qualità del lavoro dei professionisti (Nutrizione, Coaching, Psicologia) aggregando feedback dei pazienti, aderenza alle scadenze e valutazioni dei coordinatori. I dati vengono calcolati su base settimanale e consolidati trimestralmente per determinare bonus operativi e aree di miglioramento.

---

## Chi lo Usa

| Ruolo | Utilizzo |
|-------|----------|
| **CCO / Admin** | Esecuzione calcoli massivi e analisi strategica delle performance |
| **Team Leader** | Monitoraggio della qualità media del proprio team e coaching individuale |
| **Team Quality** | Audit granulare degli score e gestione Super Malus |

---

## Flusso Principale (Technical Workflow)

1. **Eligibility Filter**: Identificazione dei clienti attivi gestiti dal professionista nel periodo.
2. **Data Ingestion**: Recupero dei Weekly Check e DCA Check ricevuti nella settimana.
3. **Rating Calculation**: Aggregazione dei voti (0-10) ponderati per specialità.
4. **Adherence Audit**: Calcolo della "Miss Rate" (check non letti o non pervenuti).
5. **Periodic Consolidation**: Generazione dello score settimanale (`QualityWeeklyScore`).
6. **Quarterly Bonus**: Calcolo trimestrale con applicazione di Bonus/Malus e Super Malus.

---

## Architettura Tecnica

### Componenti coinvolti

| Layer | Componente | Ruolo |
|-------|------------|-------|
| Logic | `CalculatorService` | Core engine per il calcolo delle medie |
| Eligibility | `EligibilityService` | Filtro RBAC e stati cliente nel tempo |
| Backend | `quality_bp` | API REST per dashboard e trend |

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

## Modelli di Dati Principali

- `QualityWeeklyScore`
  - score settimanale, miss rate, quality final, bonus band
  - campi trimestrali (quality_trim, rinnovo_adj, super_malus, final bonus)
- `QualityClientScore`
  - score per cliente nel contesto settimanale
- `EleggibilitaSettimanale`
  - eleggibilità cliente-professionista per settimana
- fonti dati correlate: `WeeklyCheckResponse`, `DCACheckResponse`, `TrustpilotReview`

---

## Variabili d'Ambiente Rilevanti

| Variabile | Descrizione | Obbligatoria |
|---|---|---|
| N/A | Il modulo usa config applicativa standard | N/A |

---

## Permessi e Ruoli (RBAC)

| Funzionalità | Admin/CCO | Team Leader | Professionista |
|---|---|---|---|
| Lettura score weekly | ✅ | ✅ (scope team) | ❌ |
| Trigger calcolo | ✅ | ❌ | ❌ |
| Dashboard aggregata | ✅ | ⚠️ parziale | ❌ |

---

## Note Operative e Casi Limite

- Il modulo è API-centrico e richiede coerenza tra specialità utente e filtro richiesto.
- Alcune route sono `admin_required` esteso a CCO; i team leader hanno accesso solo a una parte dei dati.
- Le metriche dipendono da qualità dei dati check e mapping professionista-cliente nel periodo.
- Il Super Malus impatta il bonus finale trimestrale: documentare sempre ragione applicata nei report.

---

## Documenti Correlati

- [Check periodici](../03-clienti-core/check-periodici.md)
- [KPI e performance](../02-team-organizzazione/kpi-performance.md)

# Dashboard Suite Clinica — Mappatura dati e analisi possibili

Documento guida: modelli, campi utili per le dashboard, dati già esposti dagli endpoint, analisi già calcolate e analisi possibili con i dati esistenti. Riferimento per implementazioni coerenti e calcoli verificabili.


## 1. Modelli e campi utili per dashboard

### 1.1 Cliente (tabella clienti)

| Gruppo | Campi | Uso dashboard |
|--------|-------|----------------|
| Anagrafica | nome_cognome, data_di_nascita, genere, paese, origine_id, macrocategoria, programma_attuale, programma_attuale_dettaglio, tipologia_cliente | KPI, distribuzioni (genere, programma, tipologia), trend, origini |
| Stati e servizi | stato_cliente (attivo/ghost/pausa/stop), stato_nutrizione, stato_coach, stato_psicologia, stato_*_data, is_frozen, freeze_date | KPI conteggi, distribuzione per servizio, analisi freeze |
| Date e scadenze | data_inizio_abbonamento, data_rinnovo, durata_programma_giorni, data_inizio_* / data_scadenza_* (nutrizione, coach, psicologia), created_at | Nuovi clienti, in scadenza (30 gg), retention, permanenza media |
| Team e professionisti | di_team, nutrizionista_id, coach_id, psicologa_id, health_manager_id, consulente_alimentare_id, figura_di_riferimento (+ relazioni multipli) | Filtri per team/TL, carico professionisti, assegnazioni |
| Patologie | 16+ campi boolean (IBS, reflusso, gastrite, DCA, insulino-resistenza, diabete, …) + psicologia (DCA, obesità psicoemotiva, ansia/umore, …) | Distribuzione patologie, segmentazione |
| Engagement | check_day, check_saltati, reach_out_*, video_feedback, trasformazione_fisica, exit_call_svolta, recensione_accettata, sedute_psicologia_comprate, sedute_psicologia_svolte | Compliance check, engagement, utilizzo sedute |
| Finance | rate_cliente_sales, deposito_iniziale, modalita_pagamento | Revenue/LTV, distribuzione pagamento |


### 1.2 User (tabella users)

| Gruppo | Campi | Uso dashboard |
|--------|-------|----------------|
| Ruolo e specialità | role (admin, team_leader, professionista, team_esterno), specialty (nutrizione, nutrizionista, psicologia, psicologo, coach, amministrazione, cco) | Conteggi per ruolo/specialty, filtri TL |
| Stato | is_active, is_trial, is_external | KPI team, trial, esterni |
| Quality | quality_score_month, quality_score_trim, quality_score_final, bonus_band, trend_indicator | Quality summary, top performers, trend |
| Capacità | max_clients, current_client_count | Carico, utilizzo capacità |
| Altro | department_id, last_name (obbligatorio) | Filtri, visualizzazioni |


### 1.3 Check (WeeklyCheckResponse, DCA, Minor)

| Modello / campi | Uso dashboard |
|-----------------|----------------|
| WeeklyCheckResponse: nutritionist_rating, psychologist_rating, coach_rating, progress_rating (1-10), submit_date, digestion_rating, energy_rating, strength_rating, sleep_rating, mood_rating, motivation_rating | Medie per categoria, trend, distribuzione bande, top/bottom professionisti, metriche fisiche/wellness |
| DCACheckResponse, MinorCheckResponse: submit_date, risposte specifiche | Conteggi per tipo (weekly/dca/minor), trend |
| ClientCheckReadConfirmation: response_id, user_id, response_type | Conteggio check non letti |


### 1.4 Review / Formazione

| Modello / campi | Uso dashboard |
|-----------------|----------------|
| Review: review_type (settimanale/mensile/progetto/miglioramento), reviewer_id, reviewee_id, is_draft, created_at | KPI totali, per tipo, trend mensile, top formatori/destinatari |
| ReviewAcknowledgment (relazione acknowledgment su Review) | Conteggio confermati, tasso conferma |
| ReviewRequest: status (pending/completed) | Richieste in attesa |


### 1.5 Quality

| Modello / campi | Uso dashboard |
|-----------------|----------------|
| QualityWeeklyScore: week_start_date, quality_week, quality_month, quality_trim, quality_final, bonus_band (100%/60%/30%/0%), trend_indicator (up/down/stable), calculation_status | Medie quality, distribuzione bonus, trend settimanale, top performers |


### 1.6 Finance (per analisi avanzate)

| Modello / campi | Uso dashboard |
|-----------------|----------------|
| SubscriptionContract: sale_date, start_date, end_date, duration_days, initial_deposit, rate_cliente_sales, service_type | Revenue, LTV, durata contratti |
| PaymentTransaction: payment_date, amount, payment_method, transaction_type, refund_amount | Incassi, rimborsi |
| SubscriptionRenewal: renewal_payment_date, renewal_amount, renewal_duration_days | Rinnovi |
| Commission, SalesPerson | Commissioni, vendite |


---


## 2. Per area: dati esposti, analisi già calcolate, analisi possibili

### 2.1 Area Pazienti (Clienti)

**Dati già esposti** (endpoint `/api/v1/customers/admin-dashboard-stats`):

- kpi: total, active, ghost, pausa, stop, newMonth, newPrevMonth, inScadenza
- statusDistribution: [{ status, count }]
- tipologiaDistribution: [{ tipologia, count }]
- services: { nutrizione, coach, psicologia } → ciascuno { attivo, pausa, stop, ghost }
- monthlyTrend: [{ month, count }] (ultimi 12 mesi)
- patologie: [{ name, count }] ordinato per count
- genderDistribution: [{ gender, count }]
- programmaDistribution: [{ programma, count }] (attivi, top 10)
- paymentDistribution: [{ method, count }] (attivi)

**Analisi già calcolate:**

- KPI clienti per stato globale e per servizio
- Distribuzione stati, tipologia, genere, programma, pagamento
- Trend nuovi clienti (12 mesi)
- Clienti in scadenza entro 30 gg
- Confronto nuovi mese corrente vs mese precedente
- Top patologie

**Analisi possibili (dati disponibili, non ancora implementate):**

- Distribuzione origini (Cliente.origine_id → Origine)
- Distribuzione geografica (paese)
- Distribuzione demografica (età da data_di_nascita)
- Churn / retention (stato_cliente + stato_*_data, data_rinnovo)
- Analisi freeze (ClienteFreezeHistory, is_frozen, freeze_date)
- Flussi stato (StatoServizioLog)
- Sedute psicologia: comprate vs svolte (sedute_psicologia_comprate, sedute_psicologia_svolte)
- Revenue / LTV (PaymentTransaction, rate_cliente_sales, SubscriptionContract)


### 2.2 Area Check

**Dati già esposti** (endpoint `/api/client-checks/admin/dashboard-stats`):

- kpi: totalAll, totalMonth, totalPrevMonth, avgQuality, unreadCount
- ratings: nutrizionista, coach, psicologo, progresso (medie ultimi 30 gg)
- typeBreakdown: weekly, dca, minor → { total, month }
- topProfessionals: nutrizionisti, coaches, psicologi → [{ name, avg, count }]
- recentResponses: ultimi 15 con rating e media
- ratingsDistribution: low, medium, good, excellent
- monthlyTrend: ultimi 6 mesi (month, count, avgProgress)
- physicalAvgs: digestione, energia, forza, sonno, umore, motivazione

**Analisi già calcolate:**

- Conteggi totali e per mese (corrente e precedente)
- Medie rating per categoria (ultimi 30 gg)
- Top professionisti per rating (soglia ≥ 3 check)
- Trend mensile check e progresso
- Distribuzione per fascia di voto
- Medie metriche fisiche/wellness
- Check non letti (per utente corrente)

**Analisi possibili (dati disponibili, non ancora implementate):**

- Check compliance: confronto submit_date con Cliente.check_day (rispetto giorno preferito)
- Tasso check saltati per cliente/team (check_saltati, storico risposte)
- Trend per singolo professionista o per team (con filtri RBAC)


### 2.3 Area Professionisti / Team

**Dati già esposti** (endpoint `/api/team/admin-dashboard-stats`):

- kpi: totalAll, totalActive, totalInactive, totalAdmins, totalTrial, totalTeamLeaders, totalProfessionisti, totalExternal
- specialtyDistribution, roleDistribution (count, label)
- qualitySummary: avgQuality, avgMonth, avgTrim, bonusBands, trendUp, trendDown, trendStable
- topPerformers: top 10 per quality_final
- trialUsers: lista con dettagli
- qualityTrend: ultime 8 settimane (week, avgQuality, count)
- teamsSummary: id, name, team_type, head_name, member_count
- clientLoad: per nutrizione/coach/psicologia { clients, professionals, avgLoad }

**Analisi già calcolate:**

- Conteggi utenti per ruolo e specialità
- Quality media (settimana, mese, trimestre) e distribuzione bonus
- Trend quality (up/down/stable)
- Top 10 per quality score
- Carico clienti per specialty (clienti, professionisti, media per professionista)
- Riepilogo team (membri, tipo, head)

**Analisi possibili (dati disponibili, non ancora implementate):**

- Capacity utilization esplicito (current_client_count / max_clients per utente)
- Trend quality per singolo professionista o per team
- Confronto carico tra team o tra periodi


### 2.4 Area Formazione (Review)

**Dati già esposti** (endpoint `/review/api/admin/dashboard-stats`):

- kpi: totalTrainings, totalAcknowledged, totalPending, totalDrafts, thisMonth, lastMonth, ackRate, totalRequests, pendingRequests
- byType: [{ type, label, count }]
- monthlyTrend: ultimi 6 mesi (month, year, total, acknowledged)
- topReviewers, topReviewees: top 10 con count
- recentTrainings: ultimi 10 con dettagli e isAcknowledged

**Analisi già calcolate:**

- KPI training (totali, confermati, in attesa, bozze)
- Tasso conferma (ackRate)
- Trend mensile e confronto mese corrente vs precedente
- Distribuzione per tipo (settimanale, mensile, progetto, miglioramento)
- Top formatori e destinatari
- Ultimi training

**Analisi possibili (dati disponibili, non ancora implementate):**

- Trend per tipo di review
- Tempo medio tra creazione e acknowledgment
- Distribuzione per team o per reviewee (formazione ricevuta per team)


### 2.5 Area Quality

**Dati già esposti:**

- In `/api/team/admin-dashboard-stats`: qualitySummary, qualityTrend, topPerformers (quality_final), bonusBands, trend indicators
- Endpoint dedicato `/quality/api/dashboard/stats` (quality blueprint): statistiche generali per la settimana corrente

**Analisi già calcolate:**

- Medie quality (final, month, trim)
- Distribuzione bande bonus (100%, 60%, 30%, 0%)
- Trend up/down/stable
- Top performers per quality_final
- Trend ultime 8 settimane

**Analisi possibili (dati disponibili, non ancora implementate):**

- Storico settimanale quality per singolo professionista
- Confronto quality tra team
- Correlazione quality vs rating check (se stesso periodo)


---


## 3. Schema ruoli: cosa deve vedere chi

| Ruolo | Panoramica | Tab Pazienti | Tab Check | Tab Professionisti | Tab Formazione | Tab Quality |
|-------|------------|--------------|-----------|---------------------|----------------|-------------|
| **Admin** | KPI globali (pazienti filtrati da /stats? no – vedi nota), check (medie globali + responses), team | Dati globali admin-dashboard-stats | Dati globali admin | Dati globali admin | Dati globali review | Quality summary/trend globali |
| **Team Leader** | KPI pazienti filtrati (solo clienti del team), check: oggi medie globali + responses filtrate (incongruenza), team | Da definire: stesso calcolo di admin ma filtrato per clienti dei membri del team | Stesso calcolo filtrato per check dei clienti del team | Stesso calcolo filtrato per membri dei team gestiti | Stesso calcolo filtrato per reviewer/reviewee del team | Quality per i propri team |
| **Membro (professionista)** | Solo i propri KPI (clienti propri), check propri, team come info | Solo i propri clienti | Solo i check dei propri clienti | Solo i propri dati (quality, carico) | Training ricevuti/erogati | Solo il proprio quality |

**Nota:** oggi in Panoramica i KPI pazienti per admin arrivano da `/stats` che applica `apply_role_filtering`; per admin il filtro può essere “tutti”. Per TL le stesse API restituiscono dati filtrati. Le tab dedicate oggi usano endpoint admin senza filtro; per TL e Membro andranno introdotte varianti filtrate (stessi calcoli, filtro per team/utente) o restrizioni di accesso alla tab.


## 4. Riepilogo analisi possibili non ancora implementate

- Distribuzione origini e geografica (paese)
- Churn / retention da stati e date
- Freeze analysis (ClienteFreezeHistory)
- Sedute psicologia comprate vs svolte
- Revenue / LTV (PaymentTransaction, contratti, rate_cliente_sales)
- Check compliance (submit vs check_day)
- Capacity utilization esplicito (per utente)
- Quality storico per singolo professionista o per team
- Formazione: tempo medio a conferma, distribuzione per team

Questa mappatura va usata come guida per decidere quali KPI e grafici introdurre nelle dashboard admin, TL e membro, garantendo che ogni metrica abbia fonte dati e formula chiare e che i filtri ruolo siano applicati in modo coerente.

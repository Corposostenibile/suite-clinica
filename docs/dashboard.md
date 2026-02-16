# Dashboard Suite Clinica — Guida unica

Documento di riferimento per le dashboard: cosa è stato fatto, stato attuale, come procedere nelle prossime sessioni.


---

## 1. Cosa abbiamo fatto (riepilogo)

- **Documentazione e piano:** Report sulle dashboard esistenti, mappatura dati/endpoint, schema guida per implementazioni e test.
- **Fix backend:**
  - **Check:** in `/api/client-checks/azienda/stats` le medie (avg_nutrizionista, avg_psicologo, avg_coach) ora usano lo stesso filtro RBAC delle responses: per Team Leader/professionista le medie sono coerenti con la lista filtrata.
  - **Review:** nell’endpoint `/review/api/admin/dashboard-stats` sostituito l’uso di `Review.is_acknowledged` (property non queryable) con `join(Review.acknowledgment)`.
- **Welcome.jsx:** Sbloccati i tab **Pazienti, Check, Professionisti, Formazione** con il rendering dei componenti già presenti (PazientiTab, CheckTab, ProfessionistiTab, FormazioneTab) e caricamento dati al cambio tab. Aggiunto il tab **Quality** (QualityTab) che usa gli stessi dati di team/admin-dashboard-stats (qualitySummary, qualityTrend, topPerformers). Tab **Chat** lasciato in "In implementazione".
- **Test:** In `backend/tests/test_dashboard_endpoints.py` i 4 endpoint dashboard sono testati (clienti, check, team, review); corretti i nomi delle chiavi in risposta (`ratings`, `totalMonth`/`totalPrevMonth`, `totalTrainings`/`totalAcknowledged`/`byType`). In `conftest.py` impostato `expire_on_commit=False` sulla sessione di test per evitare DetachedInstanceError al login. Esecuzione: `cd backend && poetry run pytest tests/test_dashboard_endpoints.py -v`.


---

## 2. Stato attuale

### Tab Welcome e fonti dati

| Tab | Contenuto | Endpoint / dati | Note |
|-----|-----------|------------------|------|
| Panoramica | KPI pazienti, team, valutazioni medie, check negativi, top professionisti, quick links | `/api/v1/customers/stats`, `/api/client-checks/azienda/stats?period=month`, `/api/team/stats`, trialUserService | Filtro ruolo su customers e su check (responses + medie). |
| Pazienti | KPI, distribuzioni, trend, patologie, programma, pagamento | `clientiService.getAdminDashboardStats()` → `/api/v1/customers/admin-dashboard-stats` | Solo admin (dati globali). |
| Check | KPI, medie rating, tipo, top professionisti, ultimi check, trend, metriche fisiche | `checkService.getAdminDashboardStats()` → `/api/client-checks/admin/dashboard-stats` | kpi, ratings, typeBreakdown, topProfessionals, recentResponses, ecc. |
| Professionisti | KPI team, specialty/role, quality summary, top performers, trial, client load, team summary | `teamService.getAdminDashboardStats()` → `/api/team/admin-dashboard-stats` | Stesso endpoint usato anche per Quality. |
| Formazione | KPI training, tipo, trend mensile, top formatori/destinatari, ultimi training | `trainingService.getDashboardStats()` → `/review/api/admin/dashboard-stats` | kpi (totalTrainings, totalAcknowledged, byType, monthlyTrend, topReviewers, topReviewees, recentTrainings). |
| Quality | Quality media (settimana/mese/trimestre), trend, bonus bands, trend 8 settimane, top 10 | Stessi dati di Professionisti (profData) | qualitySummary, qualityTrend, topPerformers. |
| Chat | "In implementazione" | — | Da definire quando ci saranno fonte dati e metriche (es. chat pazienti, Respond.io). |

### Endpoint in sintesi

| Endpoint | Filtro ruolo | Uso |
|----------|--------------|-----|
| GET /api/v1/customers/stats | Sì (apply_role_filtering) | Panoramica KPI pazienti |
| GET /api/v1/customers/admin-dashboard-stats | No | Tab Pazienti |
| GET /api/client-checks/azienda/stats | Sì (responses + medie) | Panoramica check |
| GET /api/client-checks/admin/dashboard-stats | No | Tab Check |
| GET /api/team/stats | No | Panoramica team |
| GET /api/team/admin-dashboard-stats | No (solo admin) | Tab Professionisti + Tab Quality |
| GET /review/api/admin/dashboard-stats | No (admin o dept 17) | Tab Formazione |

Chiavi risposta principali (camelCase dove indicato): customers kpi `newMonth`, `newPrevMonth`, `inScadenza`; check `ratings`, `recentResponses`, `totalMonth`, `totalPrevMonth`; review `totalTrainings`, `totalAcknowledged`, `byType`, `recentTrainings`.


---

## 3. Come procedere nelle prossime sessioni

### 3.1 Dashboard per Team Leader e Membro

- **Obiettivo:** Stessi tipi di KPI e grafici delle tab attuali, ma filtrati per ruolo.
- **Team Leader:** Filtro per clienti/membri dei team che gestisce; stessi endpoint o nuovi endpoint (es. stessi calcoli con `?team_id=…` o logica `apply_role_filtering` lato backend).
- **Membro (professionista):** Solo i propri clienti, i propri check, il proprio quality e carico; training ricevuti/erogati.
- **Passi suggeriti:** (1) introdurre varianti degli endpoint esistenti che accettano filtro ruolo (o riusare `apply_role_filtering` dove già presente); (2) in frontend mostrare le stesse tab ma con dati filtrati in base all’utente; (3) eventuale restrizione di accesso (es. tab Pazienti solo admin o anche TL con dati filtrati).

### 3.2 Altre analisi da integrare (dati già disponibili)

- **Pazienti:** Distribuzione origini (origine_id), geografica (paese), churn/retention (stati + date), analisi freeze, sedute psicologia comprate vs svolte, revenue/LTV (PaymentTransaction, rate_cliente_sales, contratti).
- **Check:** Compliance (submit_date vs check_day), tasso check saltati, trend per professionista/team con RBAC.
- **Professionisti/Quality:** Capacity utilization esplicito (current_client_count / max_clients), trend quality per singolo/team.
- **Formazione:** Tempo medio a conferma, distribuzione per team.

Prima di aggiungere un KPI: definire fonte dati (modello/query/endpoint), formula, filtro ruolo e un check di sanity (es. somma distribuzioni = totale).

### 3.3 Tab Chat

La pagina `/chat` è un placeholder "Chat con i Pazienti" (funzionalità futura). **Consiglio:** tenere il tab Chat in "In implementazione" finché non sono definiti fonte dati e metriche (es. conversazioni, messaggi non letti, integrazione Respond.io).


---

## 4. Principi e checklist

- **Dashboard semplici e snelli:** solo KPI e grafici utili; calcoli verificabili e coerenti con i filtri RBAC.
- **Per ogni nuovo indicatore:** (1) fonte dati (modello + query/endpoint), (2) formula, (3) filtro ruolo applicato, (4) test di sanity (es. somma distribuzioni = totale), (5) naming coerente con API (camelCase dove usato in risposta).


---

## 5. Test dei calcoli

- **Esecuzione:** da repository, `cd backend && poetry run pytest tests/test_dashboard_endpoints.py -v`.
- **Cosa fanno i test:** creano dati di esempio (clienti, check, review, utenti), chiamano i 4 endpoint dashboard, verificano status 200 e presenza delle chiavi attese; dove possibile assert sui conteggi (es. `total >= N`, `active >= M`). I test usano le chiavi effettive dell’API (`ratings`, `totalMonth`, `totalPrevMonth`, `totalTrainings`, `totalAcknowledged`, `byType`).
- **Assert più stretti (opzionale):** con DB di test vuoto o resettato, creare un dataset noto (es. 5 clienti, 3 attivi) e fare assert esatti sui numeri. In ambiente condiviso è ragionevole limitarsi a sanity check.


---

## 6. Riferimento modelli (sintesi)

- **Cliente:** stato_cliente, stati per servizio, date (created_at, data_rinnovo, scadenze), tipologia, programma, patologie, team, professionisti assegnati, check_day, check_saltati, engagement, modalita_pagamento, rate_cliente_sales.
- **User:** role, specialty, is_active, is_trial, quality_score_*, bonus_band, trend_indicator, max_clients, current_client_count.
- **Check:** WeeklyCheckResponse (rating 1–10, submit_date), DCA/Minor, ClientCheckReadConfirmation.
- **Review:** review_type, reviewer/reviewee, acknowledgment (modello separato), is_draft.
- **Quality:** QualityWeeklyScore (week_start_date, quality_final/month/trim, bonus_band, trend_indicator).
- **Finance (per analisi avanzate):** SubscriptionContract, PaymentTransaction, rate_cliente_sales.

Schema ruoli (cosa vede chi): Admin = dati globali; Team Leader = stessi dati filtrati per team; Membro = solo propri clienti/check/quality/formazione. Le tab dedicate oggi usano endpoint admin; per TL e Membro andranno varianti filtrate o restrizioni di accesso.

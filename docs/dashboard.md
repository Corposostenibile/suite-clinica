# Dashboard Suite Clinica — Guida unica

Documento di riferimento per le dashboard: cosa è stato fatto, stato attuale, come procedere nelle prossime sessioni.

---

## 1. Cosa abbiamo fatto

- **Documentazione e piano:** Report sulle dashboard esistenti, mappatura dati/endpoint, schema guida per implementazioni e test.
- **Fix backend:**
  - **Check:** in `/api/client-checks/azienda/stats` le medie (avg_nutrizionista, avg_psicologo, avg_coach) ora usano lo stesso filtro RBAC delle responses: per Team Leader/professionista le medie sono coerenti con la lista filtrata.
  - **Review:** nell’endpoint `/review/api/admin/dashboard-stats` sostituito l’uso di `Review.is_acknowledged` (property non queryable) con `join(Review.acknowledgment)`.
- **Welcome.jsx:** Sbloccati i tab **Pazienti, Check, Professionisti, Formazione** con il rendering dei componenti già presenti (PazientiTab, CheckTab, ProfessionistiTab, FormazioneTab) e caricamento dati al cambio tab. Aggiunto il tab **Quality** (QualityTab) che usa gli stessi dati di team/admin-dashboard-stats (qualitySummary, qualityTrend, topPerformers). Tab **Chat** lasciato in "In implementazione".
- **Test:** In `backend/tests/test_dashboard_endpoints.py` i 4 endpoint dashboard sono testati (clienti, check, team, review); corretti i nomi delle chiavi in risposta (`ratings`, `totalMonth`/`totalPrevMonth`, `totalTrainings`/`totalAcknowledged`/`byType`). In `conftest.py` impostato `expire_on_commit=False` sulla sessione di test per evitare DetachedInstanceError al login. Esecuzione: `cd backend && poetry run pytest tests/test_dashboard_endpoints.py -v`.
- **Dashboard per Team Leader e Membro (3.1):** Tutti gli endpoint dashboard (Pazienti, Check, Professionisti/Quality, Formazione) applicano ora il filtro per ruolo: Admin = dati globali, Team Leader = dati dei team che gestisce, Professionista = solo i propri dati. Stessi URL, risposta filtrata lato backend. Helper RBAC: `apply_role_filtering` (customers), `get_accessible_clients_query` (client_checks/rbac.py), `_get_visible_user_ids_for_dashboard` (team), `_review_dashboard_visible_user_ids` (review). Test estesi con utente professionista e team admin-dashboard-stats.

## 2. Stato attuale

### Tab Welcome e fonti dati

| Tab | Contenuto | Endpoint / dati | Note |
|-----|-----------|------------------|------|
| Panoramica | KPI pazienti, team, valutazioni medie, check negativi, top professionisti, quick links | `/api/v1/customers/stats`, `/api/client-checks/azienda/stats?period=month`, `/api/team/stats`, trialUserService | Filtro ruolo su customers e su check (responses + medie). |
| Pazienti | KPI, distribuzioni, trend, patologie, programma, pagamento | `clientiService.getAdminDashboardStats()` → `/api/v1/customers/admin-dashboard-stats` | Filtro ruolo: admin=all, TL=team, professionista=own. |
| Check | KPI, medie rating, tipo, top professionisti, ultimi check, trend, metriche fisiche | `checkService.getAdminDashboardStats()` → `/api/client-checks/admin/dashboard-stats` | Filtro ruolo (client_checks/rbac). kpi, ratings, typeBreakdown, topProfessionals, recentResponses. |
| Professionisti | KPI team, specialty/role, quality summary, top performers, trial, client load, team summary | `teamService.getAdminDashboardStats()` → `/api/team/admin-dashboard-stats` | Filtro ruolo (visible user ids). Stesso endpoint per Quality. |
| Formazione | KPI training, tipo, trend mensile, top formatori/destinatari, ultimi training | `trainingService.getDashboardStats()` → `/review/api/admin/dashboard-stats` | Filtro ruolo (admin/dept17=all, TL=team, prof=own). kpi, byType, monthlyTrend, topReviewers, topReviewees, recentTrainings. |
| Quality | Quality media (settimana/mese/trimestre), trend, bonus bands, trend 8 settimane, top 10 | Stessi dati di Professionisti (profData) | qualitySummary, qualityTrend, topPerformers. |
| Chat | "In implementazione" | — | Da definire quando ci saranno fonte dati e metriche (es. chat pazienti, Respond.io). |

### Endpoint in sintesi

| Endpoint | Filtro ruolo | Uso |
|----------|--------------|-----|
| GET /api/v1/customers/stats | Sì (apply_role_filtering) | Panoramica KPI pazienti |
| GET /api/v1/customers/admin-dashboard-stats | Sì (apply_role_filtering) | Tab Pazienti |
| GET /api/client-checks/azienda/stats | Sì (responses + medie) | Panoramica check |
| GET /api/client-checks/admin/dashboard-stats | Sì (get_accessible_clients_query) | Tab Check |
| GET /api/team/stats | No | Panoramica team |
| GET /api/team/admin-dashboard-stats | Sì (visible user ids; accessibile a tutti i ruoli) | Tab Professionisti + Tab Quality |
| GET /review/api/admin/dashboard-stats | Sì (reviewer/reviewee in visible set; accessibile a tutti) | Tab Formazione |

Chiavi risposta principali (camelCase dove indicato): customers kpi `newMonth`, `newPrevMonth`, `inScadenza`; check `ratings`, `recentResponses`, `totalMonth`, `totalPrevMonth`; review `totalTrainings`, `totalAcknowledged`, `byType`, `recentTrainings`.


---

## 3. Come procedere nelle prossime sessioni

### 3.1 Dashboard per Team Leader e Membro — Completato

- **Obiettivo:** Stessi tipi di KPI e grafici delle tab attuali, ma filtrati per ruolo. **Implementato:** stessi endpoint, risposta filtrata in base a `current_user` (nessun cambio frontend).
- **Team Leader:** Vede clienti/membri dei team che gestisce; check/quality/formazione limitati a quei membri.
- **Membro (professionista):** Vede solo i propri clienti, check, quality e training (ricevuti/erogati).
- **Implementazione:** Customers usa `apply_role_filtering`; Check usa `client_checks/rbac.get_accessible_clients_query()`; Team `_get_visible_user_ids_for_dashboard()`; Review `_review_dashboard_visible_user_ids()`.

### 3.2 Altre analisi da integrare (dati già disponibili)

- **Pazienti:** Distribuzione origini (origine_id), geografica (paese), churn/retention (stati + date), analisi freeze, sedute psicologia comprate vs svolte, revenue/LTV (PaymentTransaction, rate_cliente_sales, contratti).
- **Check:** Compliance (submit_date vs check_day), tasso check saltati, trend per professionista/team con RBAC.
- **Professionisti/Quality:** Capacity utilization esplicito (current_client_count / max_clients), trend quality per singolo/team.
- **Formazione:** Tempo medio a conferma, distribuzione per team.

Prima di aggiungere un KPI: definire fonte dati (modello/query/endpoint), formula, filtro ruolo e un check di sanity (es. somma distribuzioni = totale).

### 3.3 Tab Chat

La pagina `/chat` è un placeholder "Chat con i Pazienti". 
**Consiglio:** tenere il tab Chat in "In implementazione" finché non sono definiti fonte dati e metriche.


---

## 4. Utenti di prova per test manuale (filtri per ruolo)

Per testare la dashboard con dati coerenti e verificare i calcoli per ruolo:

1. **Crea gli utenti di prova:**  
   `cd backend && poetry run python scripts/seed_dashboard_test_users.py`

2. **Credenziali (password unica per tutti):** `Dashboard1!`
   - **Admin:** `dashboard_admin@example.com` — vede tutti i dati
   - **Team Leader:** `dashboard_tl@example.com` — vede team "Team Nutrizione Dashboard Test", il professionista e i suoi 3 clienti/check/formazione
   - **Professionista:** `dashboard_prof@example.com` — vede solo i propri 3 clienti (Paziente Test Alpha/Beta/Gamma), i relativi check, il proprio quality score e le 2 review formazione (TL→Prof e Prof→TL)

3. **Cosa verifica:** accedendo con `dashboard_prof@example.com` in ogni tab (Pazienti, Check, Professionisti, Quality, Formazione) devono comparire solo i dati filtrati (3 clienti, 7 risposte check totali, 1 quality, 2 training). Con il TL vedi gli stessi dati del team; con l’admin vedi il dataset completo.

4. **Qualità dei calcoli:** i check hanno rating deterministici (8, 9, 7) e il professionista ha un QualityWeeklyScore con `quality_final=85`; puoi controllare che le medie e i KPI in dashboard siano coerenti con questi valori.

---

## 5. Test dei calcoli (pytest)

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

Schema ruoli (cosa vede chi): Admin = dati globali; Team Leader = stessi dati filtrati per team; Membro = solo propri clienti/check/quality/formazione. Gli endpoint dashboard (admin-dashboard-stats) applicano questo filtro in base al ruolo dell’utente autenticato; le tab sono le stesse per tutti con dati già filtrati.

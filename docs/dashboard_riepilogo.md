# Dashboard Suite Clinica — Riepilogo Completo

Documento di riferimento con tutto ciò che è stato scoperto, deciso e fatto per le dashboard.


## STATO ATTUALE DI WELCOME.JSX

Il file è `corposostenibile-clinica/src/pages/Welcome.jsx` (2500+ righe).

Ha 7 tab definiti nella costante TABS: panoramica, chat, formazione, pazienti, check, quality, professionisti.

Solo "Panoramica" mostra contenuto reale: KPI pazienti, team, valutazioni medie, check negativi, top professionisti, quick links.

Il placeholder "In implementazione" alla riga 277 è stato sostituito con `activeTab === 'panoramica' ? (...)` ma manca ancora il rendering per gli altri tab — servono le clausole `else if` per formazione, pazienti, check, professionisti.

Stato loading e funzioni di caricamento per i 4 tab sono GIÀ implementate:
- `pazientiData` / `pazientiLoading` / `loadPazientiData()` → chiama `clientiService.getAdminDashboardStats()`
- `checkDashData` / `checkDashLoading` / `loadCheckDashData()` → chiama `checkService.getAdminDashboardStats()`
- `profData` / `profLoading` / `loadProfData()` → chiama `teamService.getAdminDashboardStats()`
- `trainingData` / `trainingLoading` / `loadTrainingData()` → chiama `trainingService.getDashboardStats()`

Il trigger dei caricamenti al cambio tab è GIÀ implementato nell'useEffect alla riga 131-144.


## COME SBLOCCARE I TAB

Alla riga 276-277 attuale:

```jsx
{activeTab === 'panoramica' ? (
  <>
    {/* tutto il contenuto panoramica... */}
  </>
```

Va modificato in:

```jsx
{activeTab === 'panoramica' ? (
  <>
    {/* tutto il contenuto panoramica... */}
  </>
) : activeTab === 'pazienti' ? (
  <PazientiDashboard data={pazientiData} loading={pazientiLoading} error={pazientiError} onRetry={() => { setPazientiLoaded(false); loadPazientiData(); }} />
) : activeTab === 'check' ? (
  <CheckDashboard data={checkDashData} loading={checkDashLoading} error={checkDashError} onRetry={() => { setCheckDashLoaded(false); loadCheckDashData(); }} />
) : activeTab === 'professionisti' ? (
  <ProfessionistiDashboard data={profData} loading={profLoading} error={profError} onRetry={() => { setProfLoaded(false); loadProfData(); }} />
) : activeTab === 'formazione' ? (
  <FormazioneDashboard data={trainingData} loading={trainingLoading} />
) : (
  <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
    <div className="card-body text-center py-5">
      <h5 className="text-muted mb-3">In implementazione</h5>
    </div>
  </div>
)}
```

I 4 componenti vanno creati come file separati in `src/pages/dashboard/` o `src/components/dashboard/`.


## ENDPOINT BACKEND E STRUTTURA RISPOSTE

Ogni endpoint è già funzionante. Qui sotto trovi l'URL esatto, cosa restituisce e la struttura JSON.


### 1. PAZIENTI — GET /api/v1/customers/admin-dashboard-stats

Restituisce (backend usa camelCase in kpi):

- kpi: total, active, ghost, pausa, stop, newMonth, newPrevMonth, inScadenza (clienti in scadenza entro 30 gg)
- statusDistribution: array di oggetti { status: "attivo", count: 123 }
- tipologiaDistribution: array di oggetti { tipologia: "a", count: 45 }
- services: oggetto con chiavi nutrizione, coach, psicologia — ogni chiave ha { attivo: N, pausa: N, stop: N, ghost: N }
- monthlyTrend: array di oggetti { month: "2026-01", count: 12 } (ultimi 12 mesi)
- patologie: array di oggetti { name: "ibs", count: 8 } ordinato per count decrescente
- genderDistribution: array di oggetti { gender: "F", count: 100 }
- programmaDistribution: array
- paymentDistribution: array

Valori validi per StatoClienteEnum: attivo, ghost, pausa, stop (NON "insoluto", NON "freeze").
Il backend normalizza internamente: insoluto → stop, freeze → pausa.

Valori validi per TipologiaClienteEnum: a, b, c, stop, recupero, pausa_gt_30.


### 2. CHECK — GET /api/client-checks/admin/dashboard-stats

Restituisce (naming effettivo in backend):

- kpi: oggetto con totalAll, totalMonth, totalPrevMonth, avgQuality, unreadCount
- ratings: oggetto con nutrizionista, coach, psicologo, progresso (medie ultimi 30 gg)
- typeBreakdown: oggetto con chiavi weekly, dca, minor — ogni chiave ha { total: N, month: N }
- topProfessionals: oggetto con chiavi nutrizionisti, coaches, psicologi — array di { name, avg, count }
- recentResponses: array ultimi 15 check con id, cliente, date, dateIso, nutrizionista, coach, psicologo, progresso, avg
- ratingsDistribution: low/medium/good/excellent (bande 1-4, 5-6, 7-8, 9+)
- monthlyTrend: ultimi 6 mesi con month, count, avgProgress
- physicalAvgs: medie digestione, energia, forza, sonno, umore, motivazione (ultimi 30 gg)

NOTA: il doc precedente usava "avgRatings" e "recentSubmissions"; in backend sono "ratings" e "recentResponses". "totalLastMonth" in doc corrisponde a "totalPrevMonth" in risposta.


### 3. PROFESSIONISTI/TEAM — GET /api/team/admin-dashboard-stats

(La tab Professionisti usa questo endpoint. GET /api/team/stats è usato solo dalla Panoramica.)

Restituisce:

- success: true
- kpi: totalAll, totalActive, totalInactive, totalAdmins, totalTrial, totalTeamLeaders, totalProfessionisti, totalExternal
- specialtyDistribution: per specialità (count, label)
- roleDistribution: per ruolo (count, label)
- qualitySummary: avgQuality, avgMonth, avgTrim, bonusBands (100%/60%/30%/0%), trendUp, trendDown, trendStable
- topPerformers: top 10 per quality_final (id, name, specialty, quality_final, quality_month, bonus_band, trend, avatar_path)
- trialUsers: lista trial con id, name, specialty, trial_stage, avatar_path, created_at
- qualityTrend: ultime 8 settimane (week, avgQuality, count)
- teamsSummary: id, name, team_type, head_name, member_count
- clientLoad: per nutrizione/coach/psicologia { clients, professionals, avgLoad }

NOTA: in codice non esiste un campo "capacityUtilization" esplicito; l’utilizzo capacità è rappresentato da clientLoad.avgLoad (clienti per professionista per specialty).


### 4. FORMAZIONE/REVIEW — GET /review/api/admin/dashboard-stats

Restituisce:

- kpi: training totali, confermati (acknowledged), in attesa, bozze, tasso conferma percentuale
- typeBreakdown: conteggi per tipo (settimanale, mensile, progetto, miglioramento)
- monthlyTrend: array ultimi 6 mesi con { month, total, acknowledged }
- topReviewers: top 10 formatori con conteggi
- topReviewees: top 10 destinatari con conteggi
- recentReviews: ultimi 10 training con dettagli


## FIX BACKEND GIÀ APPLICATI

### Fix 1: review/routes.py — Review.is_acknowledged

Il file `backend/corposostenibile/blueprints/review/routes.py` aveva un bug nell'endpoint `/api/admin/dashboard-stats`.

Usava `Review.is_acknowledged == True` nei filtri SQLAlchemy, ma `is_acknowledged` è una property Python (non una colonna DB), definita così nel modello:

```python
@property
def is_acknowledged(self):
    return self.acknowledgment is not None
```

Non si può usare nelle query SQLAlchemy. Il fix sostituisce:
- `filter(Review.is_acknowledged == True)` → `filter(Review.acknowledgment.has())`
- Per contare acknowledged: usare join con ReviewAcknowledgment

Le righe modificate sono intorno a 2050-2053 e 2107-2111.


### Fix 2: Valori Enum nei test

I test in `backend/tests/test_dashboard_endpoints.py` usavano valori enum non validi:
- "insoluto" → corretto in "stop" (insoluto non esiste in StatoClienteEnum)
- "freeze" → corretto in "pausa" (freeze non esiste in StatoClienteEnum)
- "trasformazione" → corretto in TipologiaClienteEnum.a (trasformazione è in CatEnum, non TipologiaClienteEnum)


## MODELLI DATI PRINCIPALI — Campi Rilevanti per Dashboard

### Cliente (tabella clienti) — 100+ campi

Anagrafica: nome_cognome, data_di_nascita, genere, paese, origine/origine_id, macrocategoria, programma_attuale, programma_attuale_dettaglio, tipologia_cliente

Stati e servizi:
- stato_cliente (Enum: attivo/ghost/pausa/stop)
- stato_nutrizione, stato_coach, stato_psicologia (Enum per servizio)
- stato_*_data (DateTime per tracciabilità cambio stato)
- is_frozen, freeze_date

Date e scadenze:
- data_inizio_abbonamento, data_rinnovo, durata_programma_giorni
- data_inizio_nutrizione/coach/psicologia
- data_scadenza_nutrizione/coach/psicologia
- created_at

Team e professionisti:
- di_team (Enum: jessica, carlotta, valentina, eleonora, aurora)
- nutrizionista/nutrizionista_id, coach/coach_id, psicologa/psicologa_id
- health_manager_id, consulente_alimentare_id, figura_di_riferimento

Patologie (16 campi boolean + 2 "altro"):
- Nutrizione: IBS, reflusso, gastrite, DCA, insulino-resist., diabete, dislipidemie, steatosi, ipertensione, PCOS, endometriosi, obesità, osteoporosi, diverticolite, Crohn, stitichezza, tiroidee
- Psicologia: DCA, obesità psicoemotiva, ansia/umore/cibo, comportamenti disfunzionali, immagine corporea, psicosomatiche, relazionali

Engagement: check_day, check_saltati, reach_out_*, video_feedback, trasformazione_fisica, exit_call_svolta, recensione_accettata, sedute_psicologia_comprate/svolte

Finance: rate_cliente_sales, deposito_iniziale, modalita_pagamento


### User (tabella users)

- role: admin, team_leader, professionista, team_esterno
- specialty: nutrizione, nutrizionista, psicologia, psicologo, coach, amministrazione, cco
- is_active, is_trial, is_external
- department_id
- quality_score_month, quality_score_trim, quality_score_final, bonus_band, trend_indicator
- max_clients, current_client_count
- last_name (nullable=False, obbligatorio)


### Check Settimanali

- WeeklyCheckResponse: nutritionist_rating, psychologist_rating, coach_rating, progress_rating (1-10), submit_date, is_read
- DCACheckResponse: submit_date, risposte specifiche DCA
- MinorCheckResponse: submit_date, risposte semplificate
- ClientCheckReadConfirmation: tracking lettura check da parte professionista


### Finance (Contratti e Pagamenti)

- SubscriptionContract: sale_date, start_date, end_date, duration_days, initial_deposit, rate_cliente_sales, service_type
- PaymentTransaction: payment_date, amount, payment_method, transaction_type, refund_amount
- SubscriptionRenewal: renewal_payment_date, renewal_amount, renewal_duration_days
- Commission: role, importo
- SalesPerson: totale_venduto_storico


### Quality Score

- QualityWeeklyScore: quality_week, quality_month, quality_trim, quality_final, bonus_band (100%/60%/30%/0%), trend_indicator (up/down/stable)


### Review / Formazione

- Review: review_type (settimanale/mensile/progetto/miglioramento), reviewer_id, reviewee_id, is_acknowledged (property, non colonna!), is_draft
- ReviewAcknowledgment: modello separato legato a Review via relazione "acknowledgment"
- ReviewRequest: status (pending/completed)


## SERVIZI FRONTEND GIÀ DISPONIBILI

- clientiService.getAdminDashboardStats() → GET /api/v1/customers/admin-dashboard-stats
- checkService.getAdminDashboardStats() → GET /api/client-checks/admin/dashboard-stats
- teamService.getAdminDashboardStats() → GET /api/team/admin-dashboard-stats
- trainingService.getDashboardStats() → GET /review/api/admin/dashboard-stats
- dashboardService.calculateProfessionalRankings(responses) → calcolo frontend rankings
- dashboardService.calculateTeamRatings(responses, teams) → calcolo frontend rating per team
- dashboardService.filterNegativeChecks(responses) → filtro check con voti &lt; 7 (non ≤ 4)


## ANALISI POSSIBILI CON DATI DISPONIBILI

Già calcolate dagli endpoint:
- KPI Clienti (attivi/ghost/pausa/stop)
- Distribuzione stati per servizio
- Trend nuovi clienti (12 mesi)
- Rating medi professionisti
- Top/bottom professionisti
- Quality scores
- Training KPI
- Distribuzione patologie
- Clienti in scadenza (30gg)
- Capacità professionisti

Da sviluppare ma dati disponibili:
- Distribuzione origini (via Cliente.origine_id → Origine)
- Revenue/LTV (via PaymentTransaction.amount, Cliente.rate_cliente_sales)
- Check compliance (WeeklyCheckResponse.submit_date vs Cliente.check_day)
- Churn rate (Cliente.stato_cliente + stato_cliente_data)
- Freeze analysis (ClienteFreezeHistory)
- Flussi stato (StatoServizioLog)
- Distribuzione demografica (genere, data_di_nascita)
- Distribuzione geografica (paese)
- Sedute psicologia (sedute_comprate/svolte)


## PIANO FASI PROPOSTO

Fase 1 — Quick Win (priorità alta):
Sbloccare i 4 tab in Welcome.jsx creando 4 componenti separati che rendono i dati già caricati.

Fase 2 — Tab Quality (nuovo):
Creare componente QualityTab usando i dati già calcolati da team/api/admin-dashboard-stats (campo qualitySummary). Aggiungere endpoint dedicato per storico settimanale quality.

Fase 3 — Dashboard Team Leader e Membro:
Creare endpoint filtrati per ruolo (stessi calcoli, filtro per team/utente). Creare pagine specifiche per ruolo.

Fase 4 — Analisi Avanzate:
Finance tab, Retention/churn analysis, Trend storici con ClienteMonthlySnapshot.


---

## REPORT DASHBOARD ESISTENTI (estensione)

### Stato reale per tab e fonti dati

| Tab | Contenuto attuale | Endpoint / fonte dati | Filtro ruolo |
|-----|-------------------|------------------------|--------------|
| Panoramica | KPI pazienti, team, valutazioni medie, check negativi, top professionisti, quick links | `/api/v1/customers/stats`, `/api/client-checks/azienda/stats?period=month`, `/api/team/stats`, trialUserService.getAll() | Customers: sì (apply_role_filtering). Check: solo sulle responses (medie no). Team: no. |
| Pazienti | Solo loader; nessun rendering | clientiService.getAdminDashboardStats() → `/api/v1/customers/admin-dashboard-stats` | No (conteggi globali) |
| Check | Solo loader; nessun rendering | checkService.getAdminDashboardStats() → `/api/client-checks/admin/dashboard-stats` | No |
| Professionisti | Solo loader; nessun rendering | teamService.getAdminDashboardStats() → `/api/team/admin-dashboard-stats` | No (solo admin) |
| Formazione | Solo loader; nessun rendering | trainingService.getDashboardStats() → `/review/api/admin/dashboard-stats` | No (admin o department_id 17) |
| Quality | Nessun caricamento né UI | — | — |
| Chat | Nessun caricamento né UI | — | — |

In Panoramica i KPI pazienti per un Team Leader sono quindi filtrati (solo suoi clienti); le medie check sono invece calcolate su tutti i check (vedi Rischi calcoli).


### Tabella endpoint (URL, metodo, filtro ruolo, struttura risposta)

| Endpoint | Metodo | Filtro ruolo | Chiavi principali risposta |
|----------|--------|--------------|---------------------------|
| /api/v1/customers/stats | GET | Sì (apply_role_filtering) | total_clienti, nutrizione_attivo, coach_attivo, psicologia_attivo, kpi: { total_active, new_month, percent_scadenza }, charts: { new_customers_monthly, status_distribution } |
| /api/v1/customers/admin-dashboard-stats | GET | No | kpi (total, active, ghost, pausa, stop, newMonth, newPrevMonth, inScadenza), statusDistribution, tipologiaDistribution, services, monthlyTrend, patologie, genderDistribution, programmaDistribution, paymentDistribution |
| /api/client-checks/azienda/stats | GET | Sì solo su responses; medie no | success, period, stats: { avg_nutrizionista, avg_psicologo, avg_coach, avg_progresso }, responses[], pagination |
| /api/client-checks/admin/dashboard-stats | GET | No | kpi, ratings, typeBreakdown, topProfessionals, recentResponses, ratingsDistribution, monthlyTrend, physicalAvgs |
| /api/team/stats | GET | No | success, total_members, total_active, total_admins, total_trial, total_team_leaders, total_professionisti, total_external |
| /api/team/admin-dashboard-stats | GET | No (solo admin) | success, kpi, specialtyDistribution, roleDistribution, qualitySummary, topPerformers, trialUsers, qualityTrend, teamsSummary, clientLoad |
| /review/api/admin/dashboard-stats | GET | No (admin o dept 17) | success, kpi, byType, monthlyTrend, topReviewers, topReviewees, recentTrainings |


### Discrepanze doc / implementazione

- **Check admin:** in doc erano indicati `avgRatings` e `recentSubmissions`; in backend sono `ratings` e `recentResponses`. `totalLastMonth` in doc → `totalPrevMonth` in risposta.
- **Customers admin:** backend restituisce camelCase in kpi (`newMonth`, `newPrevMonth`, `inScadenza`); il doc usava a volte snake_case.
- **Team:** il doc citava `capacityUtilization`; in codice è presente solo `clientLoad` (con clients, professionals, avgLoad per specialty).
- **Team endpoint per tab:** la tab Professionisti usa `admin-dashboard-stats`, non `stats`; la Panoramica usa `stats` per i conteggi team.


### Rischi calcoli

- **Check in Panoramica (utente non admin):** l’endpoint `/azienda/stats` applica RBAC sulla lista `responses` (il TL vede solo i check dei propri clienti), ma le **medie** in `stats` (avg_nutrizionista, avg_psicologo, avg_coach) sono calcolate **senza** applicare lo stesso filtro: sono quindi medie globali. Le card “Valutazioni medie” e i rankings/team ratings in Panoramica per un TL mostrano: medie globali in alto, mentre tabelle/rankings sono derivati dalle responses filtrate. Possibile incongruenza da correggere applicando lo stesso filtro anche alla query delle medie.
- **Pazienti:** in Panoramica un TL vede total_clienti e attivi per servizio filtrati; aprendo la tab Pazienti (quando sbloccata) vedrebbe dati da admin-dashboard-stats cioè globali. Decidere se la tab Pazienti deve essere solo admin o esporre una variante filtrata per TL.
- **filterNegativeChecks:** la soglia in frontend è &lt; 7; il backend in ratingsDistribution usa bande 1-4 (low), 5-6 (medium), 7-8 (good), 9+ (excellent). Coerenza da verificare se si vogliono allineare le definizioni di “negativo”.


---

## SCHEMA GUIDA PER LE IMPLEMENTAZIONI

Documento di riferimento: [dashboard_mappatura_dati.md](dashboard_mappatura_dati.md). Qui: principi, checklist e ordine di implementazione per procedere con qualità e calcoli corretti.


### Principi

- **Dashboard semplici e snelle:** solo KPI e grafici utili; evitare metriche decorative o non utilizzate.
- **Niente dati inutili o non calcolati correttamente:** ogni valore deve avere una fonte chiara (modello, query, endpoint) e una formula verificabile.
- **Calcoli coerenti con i filtri (RBAC):** se la vista è filtrata per ruolo (es. Team Leader vede solo il suo team), tutte le aggregazioni (conteggi, medie, trend) devono usare lo stesso filtro. Esempio da correggere: medie check in Panoramica per TL devono essere calcolate sui soli check dei clienti accessibili al TL, non su tutti i check.
- **Verificabilità:** dove possibile, test di sanity (es. somma delle distribuzioni = totale; confronto con conteggi grezzi).


### Checklist pre-implementazione (per ogni KPI o grafico)

Prima di aggiungere o modificare un indicatore:

1. **Fonte dati:** quale modello (tabella) e quale query o endpoint fornisce il dato? Indicare file e funzione/route.
2. **Formula:** come si calcola il valore (es. media ultimi 30 gg, conteggio con filtro stato = attivo)?
3. **Filtro ruolo:** l’endpoint o la query applica `apply_role_filtering` (o equivalente per check/team)? Se la dashboard è per TL o membro, il risultato deve essere filtrato per team/utente.
4. **Test di sanity:** come verificare che il numero sia plausibile (es. somma statusDistribution = total; medie comprese tra 1 e 10 per i rating)?
5. **Naming:** uso coerente di camelCase/snake_case tra backend e frontend e con la documentazione (vedi Discrepanze doc/implementazione).


### Ordine suggerito di implementazione

1. **Allineare documentazione e naming**  
   Aggiornare doc e, se necessario, frontend/backend per usare gli stessi nomi (es. `ratings` / `recentResponses` per check; camelCase in kpi customers; rimuovere riferimenti a `capacityUtilization` dove non esiste e usare `clientLoad`).

2. **Correggere incongruenze nei calcoli**  
   - Medie check: applicare lo stesso filtro RBAC usato per le `responses` anche alla query che calcola le medie in `/azienda/stats`, così che in Panoramica un TL veda medie coerenti con la lista filtrata.  
   - Decidere se la tab Pazienti per TL deve usare un endpoint filtrato (stessi KPI ma solo clienti del team) o restare solo admin.

3. **Sbloccare i 4 tab (Pazienti, Check, Professionisti, Formazione)**  
   Creare i componenti `PazientiDashboard`, `CheckDashboard`, `ProfessionistiDashboard`, `FormazioneDashboard` che consumano rispettivamente `clientiService.getAdminDashboardStats()`, `checkService.getAdminDashboardStats()`, `teamService.getAdminDashboardStats()`, `trainingService.getDashboardStats()`, e inserire il blocco `else if` in Welcome.jsx come descritto in “Come sbloccare i tab”. Nessun nuovo endpoint in questa fase.

4. **Tab Quality**  
   Creare il componente Quality (es. QualityDashboard o QualityTab) usando i dati già presenti in `teamService.getAdminDashboardStats()` (qualitySummary, qualityTrend, topPerformers). Valutare un endpoint dedicato per lo storico settimanale quality se necessario.

5. **Varianti per Team Leader e Membro**  
   Per ogni area (Pazienti, Check, Professionisti, Formazione, Quality): definire endpoint o parametri che riusano gli stessi calcoli ma con filtro per team (TL) o per utente (membro). Esporre le dashboard/pagine specifiche per ruolo mantenendo coerenza RBAC.


## FILE MODIFICATI IN QUESTA SESSIONE

- backend/corposostenibile/blueprints/review/routes.py — Fix filtro is_acknowledged nell'endpoint dashboard-stats
- backend/tests/test_dashboard_endpoints.py — Nuovo file con test per i 4 endpoint
- backend/tests/conftest.py — Nuovo file con fixture pytest (app, client, db_session, admin user)
- corposostenibile-clinica/src/pages/Welcome.jsx — Rimosso placeholder "In implementazione" (solo la condizione, manca ancora il rendering)

File non modificati ma da modificare:
- backend/corposostenibile/config.py — potrebbe essere stato toccato accidentalmente, verificare con git diff

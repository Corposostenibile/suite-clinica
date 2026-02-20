# Dashboard Suite Clinica — Riepilogo Completo

---

## MOBILE / TABLET — TOP BAR E HAMBURGER (RISOLTO)

**Branch:** `feature/mobile-tabs-scroll`  
**Ultimo commit:** fix(mobile) top bar tablet – hamburger cliccabile e senza sovrapposizione.

### Situazione
- Su tablet (es. 1000×1170) l’hamburger e la barra di ricerca si sovrapponevano e il menu laterale non si apriva.
- Causa: sotto 1200px il tema usava `data-sidebar-style="mini"` invece di `"overlay"`, quindi il click sull’hamburger non attivava la sidebar; in più gli stili del template non erano allineati al breakpoint 1199px.

### Modifiche effettuate
1. **ThemeContext.jsx** — Sotto 1200px la sidebar è sempre in `overlay`, così l’hamburger apre il menu (come su smartphone).
2. **DashboardLayout.jsx** — Breakpoint top bar compatta a 1199px (logo nascosto, solo hamburger + ricerca).
3. **mobile-header.css** — `z-index` su nav-header/nav-control, hamburger sempre visibile in modalità compatta (niente sovrapposizione con la ricerca).
4. **template.css** — Media query portate a 1199px per nav-header, nav-control e header; hamburger nascosto solo da 1200px in su (stile compact).

### Prossimi passi (mobile/tablet)
- [ ] Test su dispositivi reali (tablet Android/iPad) e varie risoluzioni.
- [ ] Verificare che il backdrop e la chiusura al cambio route funzionino ovunque.
- [ ] Eventuale merge di `feature/mobile-tabs-scroll` in `main`/`develop` dopo review.

---

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

Restituisce:

- kpi: oggetto con total, active, ghost, pausa, stop, new_month, expiring_30d, prev_month_comparison
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

Restituisce:

- kpi: oggetto con total, totalThisMonth, totalLastMonth, weeklyCount, dcaCount, minorCount
- avgRatings: oggetto con medie per categoria (può essere vuoto se non ci sono dati)
- rankings: oggetto con classifiche professionisti
- topProfessionals: oggetto con chiavi nutrizionisti, coaches, psicologi — ogni chiave è un array di oggetti
- recentSubmissions: array degli ultimi check inviati con avg, cliente, coach, date, dateIso, id, nutrizionista, progresso, psicologo
- typeBreakdown: oggetto con chiavi dca, minor, weekly — ogni chiave ha { month: N, total: N }

NOTA: la struttura NON ha un campo "stats". Le medie sono in "avgRatings", i conteggi in "kpi".


### 3. PROFESSIONISTI/TEAM — GET /api/team/stats

Restituisce:

- kpi: totale utenti, attivi, inattivi, admin, trial, team leaders, professionisti, esterni
- specialtyDistribution: distribuzione per specialità
- roleDistribution: distribuzione per ruolo
- qualitySummary: media quality month/trim, bonus bands, trend indicators
- trialUsers: lista utenti trial con dettagli
- topPerformers: classifica per quality score
- clientLoad: clienti per professionista
- capacityUtilization: utilizzo capacità (current_client_count / max_clients)


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
- teamService.getAdminDashboardStats() → GET /api/team/stats
- trainingService.getDashboardStats() → GET /review/api/admin/dashboard-stats
- dashboardService.calculateProfessionalRankings(responses) → calcolo frontend rankings
- dashboardService.calculateTeamRatings(responses, teams) → calcolo frontend rating per team
- dashboardService.filterNegativeChecks(responses) → filtro check con voti <= 4


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


## FILE MODIFICATI IN QUESTA SESSIONE

- backend/corposostenibile/blueprints/review/routes.py — Fix filtro is_acknowledged nell'endpoint dashboard-stats
- backend/tests/test_dashboard_endpoints.py — Nuovo file con test per i 4 endpoint
- backend/tests/conftest.py — Nuovo file con fixture pytest (app, client, db_session, admin user)
- corposostenibile-clinica/src/pages/Welcome.jsx — Rimosso placeholder "In implementazione" (solo la condizione, manca ancora il rendering)

File non modificati ma da modificare:
- backend/corposostenibile/config.py — potrebbe essere stato toccato accidentalmente, verificare con git diff

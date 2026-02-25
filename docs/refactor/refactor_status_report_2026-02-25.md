# Refactor Visuali & Permessi - Stato Lavori (25/02/2026)

## Contesto

Report di allineamento prima del deploy GCP, basato su:

- `docs/refactor/refactor.txt` (messaggi/brief operativo)
- commit del branch `fix/roles-visuals-refactor`
- verifica branch `origin/feature/team-check-associati-e-hm`

Branch di lavoro corrente:

- `fix/roles-visuals-refactor`

HEAD corrente (prima del prossimo commit):

- `ffc6df2` (`refactor: scope team leader ai assignments and quality`)

Nota:

- Dopo la verifica del branch feature è stato integrato localmente un fix aggiuntivo su `backend/corposostenibile/blueprints/team/api.py` (API check associati + eager load HM), non ancora committato al momento di questo report.

## Commit Principali (branch `fix/roles-visuals-refactor`)

- `cdaa347` `refactor: fix paziente team HM and profilo check UI`
- `0c2a1e8` `refactor: fix team cards leader avatar and duplicate name`
- `9cf247c` `refactor: add admin task filters by team and assignee`
- `2a616cc` `refactor: restrict team leader dashboard and check views`
- `66b9eed` `refactor: add team leader task assignee filter`
- `b45b1ab` `refactor: restrict team leader team and clienti views`
- `d5499ea` `refactor: enable team leader training team management`
- `3119b7f` `fix: show health manager in clienti views and split parity step`
- `5e3f1dd` `refactor: align profilo check modal with patient check detail`
- `3abe82b` `docs: rename vps guide for local duckdns development`
- `195e254` `fix: sync team heads with team leader role`
- `175528f` `fix: normalize training request recipients payload`
- `ffc6df2` `refactor: scope team leader ai assignments and quality`

## Stato Implementato (Done)

### Paziente / Team UI

- HM visibile nella card sinistra del dettaglio paziente.
- HM visibile nell’elenco pazienti (backend schema + frontend fallback robusti).
- HM mostrato subito senza necessità di cliccare il tab `Team` (preload storico assegnazioni).

### Dettaglio Professionista / Check

- In tab `Check` del profilo professionista si vede solo la valutazione del professionista corrente.
- Click su check apre modal dettaglio.
- Modal `Profilo` riallineato alla struttura della scheda check paziente (con vincolo di visibilità sulla sola valutazione/feedback pertinenti).

### Team UI

- Rimosso nome team leader duplicato nelle card team.
- Avatar card team = foto team leader (fallback robusto).

### Task / Admin

- Admin/CCO vede tutti i task (fatti/non fatti).
- Filtri aggiunti per team, assegnatario, ruolo, specialità.

### Team Leader - Scope Permessi (blocchi principali)

- `Dashboard` hardening UI:
  - nascosti KPI globali e tab globali non consentiti
  - stop fetch dataset globali per `team_leader`
- `Check`:
  - filtro ruolo/specialità bloccato al ruolo del TL
  - professionisti filtro limitati al team/specialità del TL
  - modal/tabella con valutazioni non cross-ruolo
- `Task`:
  - filtro professionista per membri del proprio team
  - colonna assegnatario visibile al TL
- `Training`:
  - TL vede training dei membri del team
  - TL può scrivere/assegnare training ai membri del team
  - `Richiedi Training`: destinatari non più vuoti (payload backend normalizzato)
- `Team`:
  - TL vede solo i team guidati (lista/dettaglio)
- `Professionisti`:
  - TL vede solo membri del proprio team
- `Clienti` (UI):
  - visuali/filtri/KPI cross-dipartimento non pertinenti nascosti/limitati in base alla specialità TL

### Assegnazioni AI (Team Leader)

- TL non vede più professionisti globali in `Assegnazioni AI`.
- `GET /team/professionals/criteria` limitato ai membri dei team guidati.
- `POST /team/assignments/match` filtrato allo scope TL (no suggerimenti fuori team).
- `POST /team/assignments/confirm` bloccato se tenta assegnazione fuori scope TL.
- Frontend non usa più endpoint debug `ghl/opportunity-data-debug`, ma endpoint autenticato.
- `Quality` menu/route per TL abilitati in sola lettura (vedi sezione Quality).

### Quality (Team Leader)

- Menu `Quality` visibile al TL.
- Route `/quality` accessibile al TL.
- Backend `weekly-scores` consente accesso TL ma solo:
  - team guidati
  - specialità del TL
- UI `Quality` per TL in sola lettura:
  - niente calcolo quality
  - niente vista trimestrale

### Formazione / Richieste Ricevute

- Rimossa copy fuorviante “gestisci da Quality”.
- Gestione inline direttamente in `Formazione`:
  - textarea risposta/note
  - `Accetta`
  - `Rifiuta`
  - CTA `Scrivi Training` dopo accettazione
- Aggiunto endpoint JSON backend `POST /review/api/request/<id>/respond`.

### Ruolo Team Leader (coerenza dati)

- Migrazione dati Alembic:
  - chi è `head` di team viene promosso a `team_leader`
- Logica runtime su Team API:
  - assegnando un `head_id` a un team, promozione automatica a `team_leader`
- Fix dati applicato sul VPS locale (DuckDNS), con necessità di logout/login per aggiornare la sessione.

### Deploy / Infra / Docs

- `cloudbuild.yaml` migliorato: step post-deploy separati (`db upgrade` / `verify_schema_parity`) per debug migliore dei failure.
- Doc VPS rinominata e chiarita (ambiente shared local dev su VPS).

## Stato Parziale / Da Validare (In Progress)

### Dashboard Team Leader

Stato:

- hardening visibilità fatto (niente leak globali)
- manca una dashboard realmente “team-specific” con KPI utili (non solo nascondere dati)

### Check Team Leader - Scope Dati

Stato:

- UI e filtri sono allineati
- da validare end-to-end che la lista check sia sempre limitata al team via RBAC backend (`/client-checks/azienda/stats`)

### Task Team Leader

Stato:

- filtro professionista team aggiunto
- da validare end-to-end con account TL (task team, fatte + non fatte, conteggi)

### Clienti Team Leader - Scope Dati (non solo UI)

Stato:

- UI/filtri/KPI cross-dipartimento limitati
- da validare RBAC endpoint clienti per garantire assenza di leak cross-team/cross-dipartimento lato dati

### Formazione - Richieste Ricevute

Stato:

- gestione inline accetta/rifiuta + note + CTA scrivi training implementata
- eventuale “chat thread dedicata” sulla richiesta non ancora implementata (da valutare se davvero necessaria rispetto al flusso training + discussione)

## Da Fare / Non Ancora Coperto (da `docs/refactor/refactor.txt`)

Questi punti risultano ancora aperti o non verificati in questo ciclo:

- UI sidebar/topbar:
  - margine tasto sidebar destro
  - colore `X` chiusura sidebar (blu -> verde)
  - colore highlight icone sidebar chiusa
  - topbar immagine profilo non corretta
  - topbar ruolo TL mostrato come “Professionista” (da verificare dopo sync ruolo/sessione)
- Avatar/immagini profilo in varie sezioni (alcuni fix fatti, ma non tutto è stato ricontrollato):
  - dashboard admin immagini profilo professionisti
  - immagini profilo in tab paziente (`Team`, `Nutrizione`, `Coach`, `Psicologia`)
  - team dettaglio membri (da validare)
  - dettaglio professionista immagine profilo (da validare)
  - immagini profilo in `Check` (vista azienda/liste) da ricontrollare sistematicamente
- `Creazione link check non funziona` (non affrontato in questo blocco)
- `Capienza`:
  - logica conteggio “clienti assegnati” deve usare stato attivo del professionista per ruolo (bug segnalato, non ancora corretto)
- `Quality`:
  - test completo del flusso (oltre ai permessi TL)
- `In Prova`:
  - test completo del flusso
- Visuale `professionista` (non TL):
  - refactor complessivo permessi/visibilità ancora da rivedere (richiesta esplicita in `refactor.txt`)

## Verifica Branch `feature/team-check-associati-e-hm`

Branch verificato:

- `origin/feature/team-check-associati-e-hm` (`2d1020d`, `2e40485`)

### Cosa era già coperto in `fix/roles-visuals-refactor`

- HM in `clienti-lista` / `clienti-dettaglio`
- Modal check in `Profilo` e filtro “solo valutazione del professionista”
- Allineamento modal check con scheda check paziente (implementazione diversa ma più completa)

### Cosa mancava ed è stato integrato localmente ora

Da `2d1020d` / `2e40485`:

- Fix possibile `500` su `GET /api/team/members/:id/checks`
  - confronto `submit_date` con `datetime` (`start_dt` / `end_dt`)
  - serializzazione difensiva `nome/avatar` per professionisti nei check associati
- Eager load `health_manager_user` in `GET /api/team/members/:id/clients` (supporto colonna HM in Profilo)

### Cosa NON è stato importato dal branch feature (per scelta)

- `CheckResponseDetailModal.jsx` dedicato:
  - già superseduto da una soluzione equivalente/migliore integrata nel branch corrente
- script dev (`seed_team_check_associati_test.py`, `apply_weekly_check_user_columns.py`):
  - non necessari al deploy produzione di questo blocco
- modifiche `vite.config.js` del branch feature:
  - da non sovrascrivere senza necessità (rischio side-effect su routing/proxy)

## Stato Pre-Deploy GCP (aggiornato)

Prima del deploy GCP consigliato:

1. Committare i cambi locali successivi a `ffc6df2`:
   - fix `team/api.py` (check associati + eager load HM)
   - questo report `docs/refactor/refactor_status_report_2026-02-25.md`
2. Push branch `fix/roles-visuals-refactor`
3. Deploy GCP produzione
4. Smoke test mirati:
   - login team leader (es. Alice)
   - `Assegnazioni AI` (solo team propri)
   - `Quality` (solo team/specialità TL, no calcolo)
   - `Formazione > Richieste ricevute` (accetta/rifiuta/CTA scrivi training)
   - `Profilo professionista > Check associati` (no 500)

## Riferimento Rapido (tracker operativo)

Tracker corrente:

- `docs/refactor/refactor_tasks.md`

Questo file è il dettaglio operativo sintetico per task (`[x]`, `[~]`), mentre il presente report è il riepilogo “narrativo” con commit + gap.

# Refactor Ruoli e Visuali - Status Report
Struttura:

- prima lo stato dei punti emersi dai messaggi, divisi per ruolo (`Admin`, `Team Leader`, `Professionista`) e sezioni trasversali UI
- poi una sezione separata `Extra svolto (fuori messaggi)` con attività utili fatte in più

## Riepilogo rapido

- Molti punti urgenti su `Team Leader` sono stati affrontati (dashboard/check/task/team/professionisti/clienti/training/assegnazioni AI/quality)
- È stato aggiunto un refactor RBAC trasversale frontend (route/menu/pagine) + hardening backend sugli endpoint `Team` usati dal profilo
- `Professionista` è ora molto più vincolato lato visuali/route (dashboard scoped, no pagine globali team/check/quality)
- Restano aperti validazioni end-to-end e hardening ACL granulari su azioni di `ClientiDetail`, oltre a punti UI/avatar/sidebar/topbar + `Capienza`

## Stato per Sezione

### Trasversale UI / Visuali (non legato a un solo ruolo)

#### Fatto

- HM visibile:
  - card sinistra dettaglio paziente
  - elenco pazienti
- `Teams`:
  - nome team leader non duplicato
  - icona/team avatar sostituita con foto team leader
- `Dettaglio professionista > Check`:
  - solo valutazione del professionista corrente
  - click apre modal check
  - modal allineato alla scheda check paziente (stesso impianto, con vincolo di visibilità)
- RBAC frontend condiviso:
  - helper centralizzati (`role/scope`) per `team_leader` / `professionista`
  - route guard estesi (non solo hide menu)
  - sidebar coerente con permessi (voci globali nascoste al professionista)

## Admin

### Fatto (da messaggi)

- `Task`: admin deve vedere tutti i task (fatti + non fatti)
  - implementato
  - aggiunti filtri admin (`team`, `assegnatario`, `ruolo`, `specialità`)

## Team Leader (TL)

Questa è la parte più corposa e prioritaria nei messaggi.

### Fatto / molto avanzato

#### Dashboard (messa in sicurezza + prima dashboard team-scoped)

- Nascosti dati globali che TL non deve vedere:
  - KPI altri dipartimenti
  - medie valutazioni altri team
  - totali globali (membri, trial, esterni, ecc.)
- Nascoste tab/dashboard globali non pertinenti
- Ridotto caricamento dataset globali per TL
- `Welcome` TL con dashboard scoped (operativa) al posto del placeholder “vista limitata”
  - KPI/task/formazione/quality summary su dataset filtrato per scope TL
  - quick actions verso moduli operativi

Nota:

- il ramo admin/CCO resta dashboard legacy completa
- il ramo TL è ora usabile operativamente ma va ancora validato end-to-end sui dati reali

#### Check

- TL vede solo il filtro del proprio ruolo/specialità (es. nutrizione -> niente coach/psicologia)
- professionisti filtro limitati al team/specialità del TL
- nel dettaglio/modal non vengono mostrate valutazioni/feedback cross-ruolo

#### Task

- TL può filtrare per professionista del proprio team
- colonna assegnatario visibile al TL

#### Training

- TL può vedere training membri team
- TL può scrivere/assegnare training ai membri team
- `Richiedi Training`: destinatari non più vuoti (fix payload backend)
- `Richieste ricevute`:
  - gestione direttamente in `Formazione` (accetta/rifiuta + risposta inline)
  - CTA `Scrivi Training` dalla richiesta accettata
  - rimossa indicazione errata verso `Quality`

#### Team / Professionisti

- TL vede solo il proprio team (lista/dettaglio)
- TL vede solo professionisti del proprio team
- route guard anche via URL (`/team*`, `/teams*`) allineati ai permessi

#### Clienti (visuale TL)

- rimossi/nascosti elementi cross-dipartimento non pertinenti in UI:
  - KPI di altri ruoli
  - visuali `Coach` / `Psicologia` (se TL nutrizione, ecc.)
  - filtri di altri ruoli non pertinenti

#### Assegnazioni AI

- TL vede solo i propri team/professionisti (fix backend + frontend)
- niente suggerimenti/assegnazioni fuori scope via API (`match`, `confirm`)
- frontend non usa endpoint debug pubblico per i lead

#### Quality

- TL può vedere la pagina `Quality`
- accesso limitato ai propri team / propria specialità
- UI in sola lettura (no calcolo / no trimestrale)

#### RBAC backend (supporto a profilo/team)

- hardening endpoint team profile:
  - `/api/team/members/<id>/clients`
  - `/api/team/members/<id>/checks`
- ACL applicata:
  - admin/CCO: tutto
  - TL: solo sé stesso + membri dei propri team
  - professionista: solo sé stesso

## Professionista

### Fatto (punti emersi nei messaggi)

- `Dettaglio professionista > Check`:
  - visibile solo la valutazione del professionista corrente
  - click apre modal dettaglio check
- Route/menu permessi:
  - no accesso a `Quality`, `Check` globale, `Team/Professionisti`, `Capienze`, `In Prova`, `Assegnazioni AI`
  - redirect via URL (non solo hide sidebar)
- `Welcome`:
  - dashboard personale scoped (no KPI globali/cross-team)
- `Check`:
  - redirect da `CheckAzienda` globale verso area personale (`Profilo > Check`)
- `Team` / `Profilo`:
  - accesso al solo proprio profilo (blocco/redirect su profili altrui)
  - tabs `Profilo` ridotti (niente `Team guidati` / `Quality`)
- `Clienti lista`:
  - visuale semplificata (no filtri/statistiche cross-ruolo, no visuali reparto multiple)
  - nascosta azione di modifica lista per professionista
- `Dettaglio paziente` (hardening iniziale):
  - tab principali filtrati per specialità del professionista
  - blocco salvataggio globale scheda paziente per professionista

### Da validare / ancora parziale

- `ClientiDetail`:
  - servono ancora gate granulari su CTA/azioni interne per tab (assegnazioni, interruzioni, call bonus, ecc.)
  - manca audit completo ACL backend sugli endpoint `customers/*` richiamati dalla scheda
- `Formazione` / `Task`:
  - UI già coerente in gran parte, ma da validare con utenti reali professionista su casi limite

## Extra svolto (fuori messaggi, ma utile)

Questa sezione **non deriva direttamente dalla nostra discussione**, ma raccoglie attività fatte durante il lavoro e utili per stabilità/deploy.

### Aggiornamento implementazione RBAC (frontend + backend) - 2026-02-26

Dettaglio operativo di quanto implementato in questo step (oltre al riepilogo per ruolo sopra).

#### Frontend - centralizzazione permessi / route guard

- Nuovo modulo helper RBAC:
  - `corposostenibile-clinica/src/utils/rbacScope.js`
  - helper introdotti: `isAdminOrCco`, `isTeamLeaderRestricted`, `isProfessionistaStandard`, `normalizeSpecialtyGroup`, `canAccess*`
- `RoleProtectedRoute` esteso:
  - supporto a predicato `allowIf` (oltre a `allowedRoles`/`deniedRoles`)
  - redirect configurabile (`redirectTo`)
- Guard route-level aggiunti/estesi in `App.jsx`:
  - `team-lista`, `team-capienza`, `team-nuovo`, `team-modifica/:id`
  - `teams`, `teams-nuovo`, `teams-dettaglio/:id`, `teams-modifica/:id`
  - `assegnazioni-ai`
  - `in-prova*`
  - `quality`
  - `check-azienda`
  - `team-dettaglio/:id` con guard dedicato (professionista può aprire solo il proprio profilo)

#### Frontend - sidebar/menu

- `SideBar` allineata al RBAC centralizzato:
  - nascoste voci globali al `professionista` (`Quality`, `Check`, `Assegnazioni`, `Capienze`, `In Prova`, `Team/Professionisti`)
  - eliminata dipendenza da condizioni duplicate sparse (riuso helper RBAC)

#### Frontend - dashboard role-scoped (`Welcome`)

- `Welcome` separata per ruolo:
  - `admin/CCO`: mantiene dashboard legacy completa
  - `team_leader` (non admin/cco): dashboard scoped operativa (KPI/list task/formazione/quality summary nel proprio scope)
  - `professionista`: dashboard personale scoped (niente KPI globali/cross-team)
- Implementazione:
  - componente dashboard role-scoped dedicato
  - wrapper `Welcome` che instrada al ramo corretto
- Nota:
  - per TL è stato riusato l’endpoint già filtrato `team/admin-dashboard-stats` (non è ancora stato introdotto un endpoint aggregato TL dedicato)

#### Frontend - hardening visuali `Professionista`

- `CheckAzienda`:
  - redirect professionista verso `Profilo > Check`
- `TeamList`:
  - redirect professionista verso `/profilo`
- `Profilo`:
  - blocco/redirect se professionista tenta profilo altrui
  - tabs ridotti per professionista (`no Team guidati`, `no Quality`)
- `ClientiList`:
  - visuale semplificata per professionista (no stats/filtri cross-ruolo)
  - no visuali reparto multiple
  - tasto modifica rimosso dalla lista
- `ClientiDetail` (fase 1 hardening):
  - tabs principali filtrati in base alla specialità del professionista
  - blocco salvataggio globale scheda paziente
  - **restano da chiudere** CTA/azioni granulari interne alle tab (vedi “Cosa manca da fare”)

#### Backend - hardening ACL endpoint Team (supporto profilo)

- In `backend/corposostenibile/blueprints/team/api.py`:
  - nuovo helper ACL per endpoint scoped `/members/<id>/*`
  - enforcement su:
    - `/api/team/members/<id>/clients`
    - `/api/team/members/<id>/checks`
- Policy applicata:
  - admin/CCO: tutto
  - TL: sé stesso + membri dei propri team
  - professionista: solo sé stesso

#### Verifiche tecniche eseguite

- Python syntax check:
  - `python3 -m py_compile backend/corposostenibile/blueprints/team/api.py` ✅
- Frontend build:
  - `npm run build` (Vite) ✅
  - build completata con warning dimensione chunk (non bloccante)

### Coerenza ruolo `team_leader` (dati + logica)

- Migrazione dati Alembic:
  - promozione automatica a `team_leader` per utenti che sono `head` di team
- Logica Team API:
  - auto-promozione quando si assegna `head_id` a un team

Motivo:

- nei messaggi/validazioni reali l’utente Alice risultava `head` di team ma `role=professionista`, causando UI/permessi incoerenti

## Cosa manca da fare (sezione unica)

### Trasversale UI / Visuali

- `P1` Sidebar / topbar UI:
  - tasto sidebar destra senza margine destro
  - `X` blu da lasciare verde
  - evidenziazione icone sidebar chiusa (blu) da rivedere
- `P1` Topbar:
  - immagine profilo non corretta
  - TL che appare ancora come “Professionista” (da verificare dopo refresh sessione e rollout completo dati/ruolo)
- `P1` Avatar/immagini profilo da verificare/correggere nelle pagine citate nei messaggi:
  - dashboard admin (foto professionisti)
  - tab paziente (`Team`, `Nutrizione`, `Coach`, `Psicologia`)
  - `Check` (liste/pagina check)
  - `Team dettaglio` membri
  - `Dettaglio professionista`
- `P0` `Creazione link check non funziona` (verifica/fix puntuale)
- `P1` `Tab medico sbagliata`:
  - nei messaggi indicato come fix già fatto da Samu, da verificare/allineare sul branch corrente

### Admin (Questi includono anche team leader molto probabilmente)

- `P0` `Capienza`:
  - correggere logica conteggio “clienti assegnati” considerando stato attivo del professionista per ruolo
- `P1` `Quality`:
  - test completo del flusso admin
- `P1` `In Prova`:
  - test completo del flusso

### Team Leader (TL)

- `P0` `Check TL`:
  - validare end-to-end scope dati team (oltre ai filtri UI)
- `P0` `Task TL`:
  - validare flusso completo team (fatte/non fatte/conteggi)
- `P0` `Clienti TL`:
  - validare RBAC lato dati (non solo UI)
- `P1` `Dashboard TL`:
  - validare KPI/liste su dati reali (scope team corretto in tutti i widget)
  - `P2` eventualmente introdurre endpoint aggregato dedicato se il riuso dell’endpoint dashboard team non basta/performance
- `P2` `Training richieste ricevute`:
  - decidere se serve una vera chat/thread dedicata alla richiesta oltre alla gestione inline già implementata

### Professionista

- `P0` Hardening ACL backend su endpoint `customers` / `check` / `training` usati da `ClientiDetail` (azioni e dati granulari)
- `P0` `ClientiDetail` professionista:
  - chiudere CTA/azioni interne tab non consentite (assegnazioni/interruzioni/call bonus/azioni cross-ruolo)
  - allineare visibilità dati sensibili per ruolo su tab attive
- `P1` Validazione end-to-end del refactor visuale/permessi `Professionista` (dashboard/check/task/clienti/team/formazione)
- `P1` Ricontrollo topbar/ruolo/avatar lato professionista

### Checklist sintetica (ordine consigliato)

- `P0` Professionista: ACL backend granulari (`customers/check/training`) + hardening CTA in `ClientiDetail`
- `P0` TL: validazione end-to-end `Check` / `Task` / `Clienti` su dati reali (scope team)
- `P0` `Capienza`: fix conteggio clienti assegnati
- `P0` Fix `Creazione link check`
- `P1` Verifiche UI trasversali (sidebar/topbar/avatar/tab medico)
- `P1` Validazione dashboard TL team-scoped e refactor professionista end-to-end
- `P1` Test completi `Quality` admin e `In Prova`
- `P2` Decisione prodotto su thread/chat per richieste training
- `P2` Eventuale endpoint aggregato TL dedicato (se necessario per performance/manutenibilità)

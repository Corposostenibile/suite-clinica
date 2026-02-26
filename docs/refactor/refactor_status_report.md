# Refactor Ruoli e Visuali - Status Report
Struttura:

- prima lo stato dei punti emersi dai messaggi, divisi per ruolo (`Admin`, `Team Leader`, `Professionista`) e sezioni trasversali UI
- poi una sezione separata `Extra svolto (fuori messaggi)` con attività utili fatte in più

## Riepilogo rapido

- Molti punti urgenti su `Team Leader` sono stati affrontati (dashboard/check/task/team/professionisti/clienti/training/assegnazioni AI/quality)
- È stato aggiunto un refactor RBAC trasversale frontend (route/menu/pagine) + hardening backend sugli endpoint `Team` usati dal profilo
- `Professionista` è ora molto più vincolato lato visuali/route (dashboard scoped, no pagine globali team/check/quality)
- Restano aperti soprattutto validazioni end-to-end (TL/professionista), micro-azioni residuali in `ClientiDetail` e punti UI/avatar/sidebar/topbar + `Capienza`

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
  - restano da rifinire alcune azioni secondarie dentro le tab
  - serve un controllo finale con test manuali per confermare che non ci siano bypass residui
- `Formazione` / `Task`:
  - UI già coerente in gran parte, ma da validare con utenti reali professionista su casi limite

## Extra svolto (fuori messaggi, ma utile)

Questa sezione **non deriva direttamente dalla nostra discussione**, ma raccoglie attività fatte durante il lavoro e utili per stabilità/deploy.

### Aggiornamento permessi/visuali (frontend + backend) - 2026-02-26

In questo step è stato fatto un consolidamento generale dei permessi, per ridurre differenze tra ciò che l’utente vede in UI e ciò che può realmente fare.

#### Frontend - permessi più coerenti (route + menu + pagine)

- I controlli ruolo sono stati centralizzati (meno condizioni sparse nelle pagine).
- Le pagine ora sono protette anche da accesso diretto via URL, non solo dal menu.
- La sidebar del `professionista` mostra solo le sezioni utili al suo lavoro.

#### Frontend - dashboard separate per ruolo (`Welcome`)

- `admin/CCO`: mantiene dashboard completa
- `team_leader`: dashboard operativa limitata al proprio team
- `professionista`: dashboard personale (senza dati globali)

#### Frontend - `Professionista` più limitato dove serve

- Redirect/blocchi su pagine globali non di competenza (`Quality`, `Check` globale, `Team`, ecc.)
- Accesso consentito solo al proprio profilo (non ai profili di altri professionisti)
- `ClientiList` semplificata (meno filtri/statistiche non pertinenti)
- `ClientiDetail` filtrata per specialità del professionista
- Bloccato il salvataggio globale della scheda paziente per `professionista`

#### Frontend - `Team Leader` su `ClientiDetail` (step aggiuntivo)

- Anche il `Team Leader` ora usa una vista più coerente con la propria specialità nella scheda paziente:
  - tab principali servizio-specifiche filtrate per specialità (`nutrizione` / `coaching` / `psicologia`)
  - azioni principali nelle sezioni (piani/diari/luoghi) allineate alla specialità visibile
- Obiettivo:
  - evitare che il TL lavori su sezioni fuori specialità solo perché la scheda paziente è raggiungibile

#### Backend - controlli reali lato server (non solo UI)

- Endpoint team/profilo protetti con regole coerenti:
  - `admin/CCO`: tutto
  - `team_leader`: sé stesso + membri del proprio team
  - `professionista`: solo sé stesso
- Migliorati i controlli lato server sulle azioni della scheda paziente (`ClientiDetail`) per evitare bypass via chiamate manuali/API.

#### Backend - scheda paziente (`ClientiDetail`) resa più sicura

- Il `professionista` può operare solo nella propria area (nutrizione/coaching/psicologia) se è davvero assegnato a quel paziente.
- Bloccate lato server azioni non consentite come assegnazioni/interruzioni professionisti.
- Rafforzati anche controlli su check e storico check per impedire accessi fuori perimetro.
- Coperti anche endpoint legacy usati dalla scheda (piani, luoghi, storici) per evitare buchi residui.
- Step aggiuntivo TL:
  - i controlli service-specifici usati dalla scheda paziente verificano anche che il `Team Leader` sia nel perimetro clienti del proprio team (non solo il `professionista`)
  - aggiunto controllo di perimetro anche sull’endpoint principale della scheda paziente (`GET /api/v1/customers/<id>`) e sulle operazioni principali (`PATCH/DELETE/history`)

#### Frontend - bottoni/azioni della scheda paziente (`ClientiDetail`)

- Nascoste o bloccate le CTA principali non consentite al `professionista`:
  - assegnazioni/interruzioni professionisti
  - generazione link check
  - richiesta call bonus
  - eliminazione paziente
- Aggiunti controlli anche su alcune azioni interne alle tab (piani/diari/luoghi) in base alla specialità.
- Restano da rifinire solo alcuni casi secondari (vedi sezione finale “Cosa manca da fare”).

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
- `P0` `ClientiDetail TL`:
  - validare su casi reali che tab/azioni siano coerenti con specialità TL
  - verificare 403 backend su cliente fuori team nelle azioni service-specifiche della scheda
- `P1` `Dashboard TL`:
  - validare KPI/liste su dati reali (scope team corretto in tutti i widget)
  - `P2` eventualmente introdurre endpoint aggregato dedicato se il riuso dell’endpoint dashboard team non basta/performance
- `P2` `Training richieste ricevute`:
  - decidere se serve una vera chat/thread dedicata alla richiesta oltre alla gestione inline già implementata

### Professionista

- `P0` Chiusura permessi reali su `ClientiDetail` (backend + UI)
  - **quasi chiuso**: coperti i punti principali della scheda paziente (azioni, check, piani, luoghi, storici)
  - residuo: controllo finale su casi minori + smoke test manuale
- `P0` `ClientiDetail` professionista:
  - chiudere CTA secondarie/micro-azioni tab-specifiche ancora non allineate
  - rifinire visibilità dati sensibili per ruolo su alcune tab attive (audit finale)
- `P1` Validazione end-to-end del refactor visuale/permessi `Professionista` (dashboard/check/task/clienti/team/formazione)
- `P1` Ricontrollo topbar/ruolo/avatar lato professionista

### Checklist sintetica (ordine consigliato)

- `P0` Professionista: chiusura residui `ClientiDetail` (CTA secondarie + controllo finale + smoke test)
- `P0` TL: validazione end-to-end `Check` / `Task` / `Clienti` su dati reali (scope team)
- `P0` `Capienza`: fix conteggio clienti assegnati
- `P0` Fix `Creazione link check`
- `P1` Verifiche UI trasversali (sidebar/topbar/avatar/tab medico)
- `P1` Validazione dashboard TL team-scoped e refactor professionista end-to-end
- `P1` Test completi `Quality` admin e `In Prova`
- `P2` Decisione prodotto su thread/chat per richieste training
- `P2` Eventuale endpoint aggregato TL dedicato (se necessario per performance/manutenibilità)

# Refactor Ruoli e Visuali - Status Report (2026-02-25)
Struttura:

- prima lo stato dei punti emersi dai messaggi, divisi per ruolo (`Admin`, `Team Leader`, `Professionista`) e sezioni trasversali UI
- poi una sezione separata `Extra svolto (fuori messaggi)` con attività utili fatte in più

## Riepilogo rapido

- Molti punti urgenti su `Team Leader` sono stati affrontati (dashboard/check/task/team/professionisti/clienti/training/assegnazioni AI/quality)
- Alcuni punti sono solo **messi in sicurezza** (hide/limit UI) ma vanno ancora **validati end-to-end** 
- Restano aperti diversi punti UI/avatar/sidebar/topbar + `Capienza`, test completi `Quality`/`In Prova`

## Stato per Sezione (da `refactor.txt`)

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

#### Parziale / da verificare

- HM / avatar in `Profilo` team e tab associate:
  - supporto dati e fix principali presenti
  - da ricontrollare visivamente in tutti i tab citati (Team/Nutrizione/Coach/Psicologia)

#### Ancora aperto (citato nei messaggi)

- Sidebar / topbar UI:
  - tasto sidebar destra senza margine destro
  - `X` blu da lasciare verde
  - evidenziazione icone sidebar chiusa (blu) da rivedere
- Topbar:
  - immagine profilo non corretta
  - TL che appare ancora come “Professionista” (dipende anche da ruolo/sessione; vedi extra su sync ruolo)
- Avatar/immagini profilo da verificare/correggere in più pagine:
  - dashboard admin (foto professionisti)
  - tab paziente (`Team`, `Nutrizione`, `Coach`, `Psicologia`)
  - `Check` (liste/pagina check)
  - `Team dettaglio` membri
  - `Dettaglio professionista`
- `Creazione link check non funziona`
- `Tab medico sbagliata`:
  - nei messaggi è indicato come “fix già fatto da Samu”, quindi qui resta **da verificare / allineare branch**, non trattato in questo ciclo

## Admin

### Fatto (da messaggi)

- `Task`: admin deve vedere tutti i task (fatti + non fatti)
  - implementato
  - aggiunti filtri admin (`team`, `assegnatario`, `ruolo`, `specialità`)

### Da testare / aperto (da messaggi)

- `Quality`: “abbiamo testato tutto il flusso correttamente?”
  - permessi/route toccati in questo ciclo per TL, ma per admin resta richiesta di **test flusso completo**
- `In Prova`: “abbiamo testato tutto il flusso correttamente?”
  - **test completo ancora da fare**
- `Capienza`:
  - bug logico segnalato nei messaggi (conteggio su clienti assegnati solo se stato ruolo professionista è attivo)
  - **non ancora corretto**

## Team Leader (TL)

Questa è la parte più corposa e prioritaria nei messaggi di `refactor.txt`.

### Fatto / molto avanzato

#### Dashboard (messa in sicurezza)

- Nascosti dati globali che TL non deve vedere:
  - KPI altri dipartimenti
  - medie valutazioni altri team
  - totali globali (membri, trial, esterni, ecc.)
- Nascoste tab/dashboard globali non pertinenti
- Ridotto caricamento dataset globali per TL

Nota:

- questo step è soprattutto **hardening visibilità**
- manca una dashboard TL “completa” con metriche team-specific

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

### Parziale / da validare end-to-end

- `Dashboard TL`:
  - sicurezza visibilità ok
  - manca versione finale con KPI team-specific reali
- `Check TL`:
  - UI/filtri ok
  - da validare che la lista dati sia sempre correttamente team-scoped (RBAC endpoint)
- `Task TL`:
  - filtro team presente
  - da validare flusso completo (fatte/non fatte/conteggi) con account TL reale
- `Clienti TL`:
  - UI limitata correttamente
  - da validare lato dati che non ci siano leak cross-team/cross-dipartimento
- `Training richieste ricevute`:
  - gestione inline implementata
  - resta da decidere se serve una vera “chat thread” dedicata alla richiesta (nei messaggi è stato chiesto come UX ideale)

## Professionista

### Fatto (punti emersi nei messaggi)

- `Dettaglio professionista > Check`:
  - visibile solo la valutazione del professionista corrente
  - click apre modal dettaglio check

### Aperto / da rivedere (esplicitamente nei messaggi)

- “rivedere tutta la visuale professionista”
  - richiesto nei messaggi, ma non ancora affrontato in modo sistematico in questo ciclo
- verifica permessi/visibilità sezione per sezione (dashboard/check/task/clienti/team/formazione)
- eventuali problemi topbar/ruolo/avatar lato professionista ancora da ricontrollare

## Punti tecnici derivati dai messaggi (allineamento necessario prima del deploy)

### Verifica branch `feature/team-check-associati-e-hm`

Controllo eseguito su `origin/feature/team-check-associati-e-hm`.

Esito:

- gran parte dei fix di quel branch è già coperta nel branch corrente
- è stato individuato e integrato localmente un fix utile da quel branch:
  - fix `500` possibile su `GET /api/team/members/:id/checks` (confronto `DateTime`)
  - serializzazione difensiva nome/avatar nei check associati
  - eager load `health_manager_user` in `GET /api/team/members/:id/clients`

## Extra svolto (fuori messaggi, ma utile)

Questa sezione **non deriva direttamente da `refactor.txt`**, ma raccoglie attività fatte durante il lavoro e utili per stabilità/deploy.

### Coerenza ruolo `team_leader` (dati + logica)

- Migrazione dati Alembic:
  - promozione automatica a `team_leader` per utenti che sono `head` di team
- Logica Team API:
  - auto-promozione quando si assegna `head_id` a un team

Motivo:

- nei messaggi/validazioni reali l’utente Alice risultava `head` di team ma `role=professionista`, causando UI/permessi incoerenti

### Cloud Build / deploy

- `cloudbuild.yaml` migliorato:
  - separati step post-deploy (`flask db upgrade` / `verify_schema_parity`)
  - facilita diagnosi di failure (`exit 137`)

### Documentazione VPS

- guida VPS/DuckDNS rinominata e chiarita come ambiente di sviluppo condiviso su VPS

## Commit di riferimento (branch `fix/roles-visuals-refactor`)

Commit principali collegati ai punti sopra:

- `cdaa347` HM paziente + profilo check UI
- `0c2a1e8` team card leader avatar / nome duplicato
- `9cf247c` task admin (filtri globali)
- `2a616cc` dashboard/check TL hardening
- `66b9eed` filtro professionista task TL
- `b45b1ab` team/professionisti/clienti TL
- `d5499ea` training TL team management
- `3119b7f` HM clienti views + cloudbuild split parity step
- `5e3f1dd` modal check profilo allineato a scheda check paziente
- `195e254` sync team heads -> role team_leader
- `175528f` fix destinatari richieste training
- `ffc6df2` scope TL su assegnazioni AI + quality

## Cosa manca prima del deploy GCP (pratico)

Stato locale attuale (dopo questo report):

- fix locale non ancora committato su `backend/corposostenibile/blueprints/team/api.py` (integrazione dal branch `feature/team-check-associati-e-hm`)
- questo report `.md`

Passi consigliati:

1. `commit + push` dei cambi locali rimasti
2. deploy GCP
3. smoke test mirato per:
   - TL: `Dashboard`, `Check`, `Task`, `Assegnazioni AI`, `Quality`, `Formazione richieste ricevute`
   - `Profilo professionista > Check associati` (assenza 500)
   - `Pazienti` HM in lista + dettaglio

# Refactor Ruoli e Visuali - Status Report
Struttura:

- prima lo stato dei punti emersi dai messaggi, divisi per ruolo (`Admin`, `Team Leader`, `Professionista`) e sezioni trasversali UI
- poi una sezione separata `Extra svolto (fuori messaggi)` con attività utili fatte in più

## Riepilogo rapido

- Molti punti urgenti su `Team Leader` sono stati affrontati (dashboard/check/task/team/professionisti/clienti/training/assegnazioni AI/quality)
- Alcuni punti sono solo **messi in sicurezza** (hide/limit UI) ma vanno ancora **validati end-to-end** 
- Restano aperti diversi punti UI/avatar/sidebar/topbar + `Capienza`, test completi `Quality`/`In Prova`

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

## Admin

### Fatto (da messaggi)

- `Task`: admin deve vedere tutti i task (fatti + non fatti)
  - implementato
  - aggiunti filtri admin (`team`, `assegnatario`, `ruolo`, `specialità`)

## Team Leader (TL)

Questa è la parte più corposa e prioritaria nei messaggi.

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

## Professionista

### Fatto (punti emersi nei messaggi)

- `Dettaglio professionista > Check`:
  - visibile solo la valutazione del professionista corrente
  - click apre modal dettaglio check

## Extra svolto (fuori messaggi, ma utile)

Questa sezione **non deriva direttamente dalla nostra discussione**, ma raccoglie attività fatte durante il lavoro e utili per stabilità/deploy.

### Coerenza ruolo `team_leader` (dati + logica)

- Migrazione dati Alembic:
  - promozione automatica a `team_leader` per utenti che sono `head` di team
- Logica Team API:
  - auto-promozione quando si assegna `head_id` a un team

Motivo:

- nei messaggi/validazioni reali l’utente Alice risultava `head` di team ma `role=professionista`, causando UI/permessi incoerenti

## Cosa manca da fare (sezione unica)

### Trasversale UI / Visuali

- Sidebar / topbar UI:
  - tasto sidebar destra senza margine destro
  - `X` blu da lasciare verde
  - evidenziazione icone sidebar chiusa (blu) da rivedere
- Topbar:
  - immagine profilo non corretta
  - TL che appare ancora come “Professionista” (da verificare dopo refresh sessione e rollout completo dati/ruolo)
- Avatar/immagini profilo da verificare/correggere nelle pagine citate nei messaggi:
  - dashboard admin (foto professionisti)
  - tab paziente (`Team`, `Nutrizione`, `Coach`, `Psicologia`)
  - `Check` (liste/pagina check)
  - `Team dettaglio` membri
  - `Dettaglio professionista`
- `Creazione link check non funziona` (verifica/fix puntuale)
- `Tab medico sbagliata`:
  - nei messaggi indicato come fix già fatto da Samu, da verificare/allineare sul branch corrente

### Admin (Questi includono anche team leader molto probabilmente)

- `Capienza`:
  - correggere logica conteggio “clienti assegnati” considerando stato attivo del professionista per ruolo
- `Quality`:
  - test completo del flusso admin
- `In Prova`:
  - test completo del flusso

### Team Leader (TL)

- `Dashboard TL`:
  - completare dashboard team-specific (ora hardening visibilità, non dashboard finale)
- `Check TL`:
  - validare end-to-end scope dati team (oltre ai filtri UI)
- `Task TL`:
  - validare flusso completo team (fatte/non fatte/conteggi)
- `Clienti TL`:
  - validare RBAC lato dati (non solo UI)
- `Training richieste ricevute`:
  - decidere se serve una vera chat/thread dedicata alla richiesta oltre alla gestione inline già implementata

### Professionista

- Refactor sistematico visuale/permessi `Professionista` (sezione per sezione)
- Verifica specifica di dashboard/check/task/clienti/team/formazione in scope professionista
- Ricontrollo topbar/ruolo/avatar lato professionista

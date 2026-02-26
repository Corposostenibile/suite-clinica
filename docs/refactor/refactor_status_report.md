# Refactor Ruoli e Visuali - Status Report

## Riepilogo rapido

- Il refactor permessi/visuali è avanzato su `Team Leader` e `Professionista`, con miglioramenti sia frontend (route/menu/dashboard/UI) sia backend (controlli reali lato server).
- La parte più delicata (`ClientiDetail`, scheda paziente) è stata rafforzata per `Team Leader` e `Professionista`, ma resta da chiudere con validazioni end-to-end e alcuni residui di micro-azioni.
- Restano aperti soprattutto: QA su scope dati `Team Leader` (`Clienti` / `Check` / `Task`), `Capienza`, e rifiniture UI trasversali (`topbar`, `avatar`, `sidebar`).

## Mappa Ruoli (riferimento per leggere il report)

- `Admin/CCO`
  - accesso globale ai moduli e ai dati (salvo eventuali limitazioni funzionali specifiche di pagina)
- `Team Leader`
  - accesso limitato a team/specialità di competenza
  - no dati globali/cross-team fuori perimetro
- `Professionista`
  - accesso limitato a operatività personale e clienti assegnati
  - no pagine/moduli globali di coordinamento

Nota coerenza ruoli:
- È stata introdotta coerenza tra `head` di team e ruolo `team_leader` (migrazione + auto-promozione in logica Team API) per evitare UI/permessi incoerenti.

## Stato per Sezione della Suite

### Welcome / Dashboard

- `Stato`: `Parziale (avanzato)`
- `Admin/CCO`
  - mantiene dashboard completa (ramo legacy)
  - da validare con test funzionale completo su dati reali
- `Team Leader`
  - dashboard team-scoped operativa su `Welcome` (al posto del placeholder “vista limitata”)
  - nascosti KPI/tab globali non pertinenti
  - quick actions verso moduli operativi
  - da validare su dati reali: coerenza KPI/liste per scope team/specialità
- `Professionista`
  - dashboard personale scoped (senza KPI globali/cross-team)
- `Note`
  - TL usa una dashboard operativa già utilizzabile, ma la validazione dati reale è ancora `P1`

### Sidebar / Route / Accesso pagine

- `Stato`: `Fatto (con QA residuo)`
- `Admin/CCO`
  - accesso globale (come atteso)
- `Team Leader`
  - route/menu coerenti con moduli team
  - accesso via URL allineato ai permessi su aree `team/professionisti`
- `Professionista`
  - no accesso a pagine globali: `Quality`, `Check` globale, `Team/Professionisti`, `Capienze`, `In Prova`, `Assegnazioni AI`
  - redirect/blocco anche via URL (non solo hide sidebar)
  - sidebar ridotta alle sezioni operative personali
- `Note`
  - controlli frontend centralizzati (`role/scope`) per ridurre logica sparsa

### Team / Professionisti / Profilo

- `Stato`: `Parziale (molto avanzato)`
- `Admin/CCO`
  - pieno accesso a team e professionisti
- `Team Leader`
  - vede solo il proprio team (lista/dettaglio)
  - vede solo professionisti del proprio team
  - route guard allineati ai permessi anche via URL
- `Professionista`
  - accesso consentito solo al proprio profilo
  - blocco/redirect su profili altrui
  - tabs profilo ridotti (es. no `Team guidati`, no `Quality`)
- `Note`
  - `Dettaglio professionista > Check`: visibile solo la valutazione del professionista corrente, con modal allineato alla scheda check paziente
  - backend team profile hardening su `/api/team/members/<id>/clients` e `/api/team/members/<id>/checks`:
    - `admin/CCO`: tutto
    - `TL`: sé stesso + membri dei propri team
    - `professionista`: solo sé stesso

### Clienti (lista)

- `Stato`: `Parziale (avanzato)`
- `Admin/CCO`
  - visuale completa (da validare con QA funzionale)
- `Team Leader`
  - rimossi/nascosti elementi cross-dipartimento non pertinenti
  - filtri coerenti con team/specialità del TL
  - da validare end-to-end lato dati (non solo UI)
- `Professionista`
  - visuale semplificata (no filtri/statistiche cross-ruolo)
  - no visuali reparto multiple
  - azioni lista non pertinenti nascoste
  - lista attesa come perimetro “clienti assegnati” (da confermare con QA su dati reali)

### ClientiDetail (scheda paziente)

- `Stato`: `Parziale (avanzato, con QA P0)`
- `Admin/CCO`
  - operatività completa attesa
  - da validare con smoke test funzionale su flussi principali
- `Team Leader`
  - frontend:
    - tab principali servizio-specifiche filtrate per specialità TL (`nutrizione` / `coaching` / `psicologia`)
    - azioni principali nelle sezioni (piani/diari/luoghi) allineate alla specialità visibile
  - backend:
    - controlli service-specifici verificano anche il perimetro clienti del team del TL
    - controllo di perimetro anche su endpoint principale scheda (`GET /api/v1/customers/<id>`) e operazioni principali (`PATCH/DELETE/history`)
  - da validare:
    - coerenza tab/azioni su casi reali
    - `403` su cliente fuori team nelle azioni service-specifiche
- `Professionista`
  - frontend:
    - tab principali filtrati per specialità del professionista
    - blocco salvataggio globale scheda paziente
    - CTA principali non consentite nascoste/bloccate (`assegnazioni`, `link check`, `call bonus`, `eliminazione paziente`)
    - controlli aggiunti a varie azioni tab-specifiche (piani/diari/luoghi) in base alla specialità
  - backend:
    - controlli service-specifici per limitare il professionista alla propria area (`nutrizione` / `coaching` / `psicologia`) e ai soli clienti in perimetro
    - blocco lato server su azioni non consentite (assegnazioni/interruzioni professionisti, call bonus fuori scope, accessi check/storici fuori perimetro)
    - coperti anche endpoint legacy della scheda (`piani`, `luoghi`, `storici`) per ridurre bypass residui
  - da validare:
    - chiusura micro-CTA/azioni secondarie residue
    - audit finale visibilità dati sensibili su tab attive
    - smoke test manuale finale (cliente assegnato vs non assegnato)
- `Note`
  - questa è la sezione prioritaria del refactor RBAC/visuale

### Check

- `Stato`: `Parziale (avanzato)`
- `Admin/CCO`
  - accesso globale (da testare end-to-end)
- `Team Leader`
  - filtro limitato al proprio ruolo/specialità
  - professionisti filtro limitati a team/specialità del TL
  - dettaglio/modal senza valutazioni/feedback cross-ruolo
  - da validare end-to-end lo scope dati team (oltre ai filtri UI)
- `Professionista`
  - no `CheckAzienda` globale
  - redirect verso area personale (`Profilo > Check`)
- `Da fare / Aperto`
  - `P0` fix puntuale `Creazione link check non funziona`

### Task

- `Stato`: `Parziale (avanzato)`
- `Admin/CCO`
  - vede tutti i task (fatti + non fatti)
  - filtri admin aggiunti (`team`, `assegnatario`, `ruolo`, `specialità`)
- `Team Leader`
  - può filtrare per professionista del proprio team
  - colonna assegnatario visibile
  - da validare flusso completo team (fatte/non fatte/conteggi)
- `Professionista`
  - UI coerente in gran parte con task personali
  - da validare con utenti reali su casi limite

### Formazione

- `Stato`: `Parziale (avanzato)`
- `Admin/CCO`
  - da validare con QA funzionale completo se usato come vista globale/coordinamento
- `Team Leader`
  - vede training membri team
  - può scrivere/assegnare training ai membri team
  - `Richiedi Training`: destinatari non più vuoti (fix payload backend)
  - `Richieste ricevute`: gestione direttamente in `Formazione` (accetta/rifiuta + risposta inline)
  - CTA `Scrivi Training` dalla richiesta accettata
  - rimossa indicazione errata verso `Quality`
- `Professionista`
  - flusso personale in gran parte coerente
  - da validare su casi limite reali
- `Note`
  - possibile miglioramento futuro: thread/chat dedicata per richieste (decisione prodotto)

### Quality

- `Stato`: `Parziale`
- `Admin/CCO`
  - accesso previsto completo, da testare end-to-end
- `Team Leader`
  - accesso limitato a propri team / propria specialità
  - UI in sola lettura (no calcolo / no trimestrale)
- `Professionista`
  - non accessibile

### Assegnazioni AI

- `Stato`: `Parziale (avanzato)`
- `Admin/CCO`
  - accesso globale atteso (da verificare con QA funzionale)
- `Team Leader`
  - vede solo propri team/professionisti
  - niente suggerimenti/assegnazioni fuori scope via API (`match`, `confirm`)
  - frontend non usa endpoint debug pubblico per i lead
- `Professionista`
  - non accessibile

### Capienza

- `Stato`: `Da fare (P0)`
- `Admin/CCO`
  - da correggere logica conteggio “clienti assegnati” considerando stato attivo del professionista per ruolo
- `Team Leader`
  - da chiarire/validare se il comportamento atteso è condiviso con admin nella vista disponibile
- `Professionista`
  - non prevista come area operativa

### UI trasversale (Topbar / Avatar / Sidebar visual)

- `Stato`: `Parziale`
- `Tutti i ruoli` (con impatto variabile per pagina)
  - aperti alcuni difetti visuali su sidebar/topbar
  - avatar/immagini profilo da verificare in più pagine
- `Da fare`
  - sidebar/topbar UI:
    - tasto sidebar destra senza margine destro
    - `X` blu da lasciare verde
    - evidenziazione icone sidebar chiusa (blu) da rivedere
  - topbar:
    - immagine profilo non corretta
    - TL che appare ancora come “Professionista” (da verificare dopo refresh sessione e rollout completo dati/ruolo)
  - avatar/immagini profilo da verificare/correggere:
    - dashboard admin (foto professionisti)
    - tab paziente (`Team`, `Nutrizione`, `Coach`, `Psicologia`)
    - `Check` (liste/pagina check)
    - `Team dettaglio` membri
    - `Dettaglio professionista`
  - `Tab medico` da verificare/allineare sul branch corrente

## Verifiche tecniche eseguite

- Python syntax check (`py_compile`) sui moduli backend modificati ✅
- Frontend build `npm run build` (Vite) ✅
- Build completata con warning dimensione chunk (non bloccante)

## Cosa manca da fare (P0 / P1 / P2)

### P0 (bloccanti / alta priorità)

- `ClientiDetail (Professionista)`
  - chiudere micro-CTA/azioni secondarie tab-specifiche residue
  - audit finale visibilità dati sensibili su tab attive
  - smoke test manuale finale (cliente assegnato vs non assegnato)
- `ClientiDetail (Team Leader)`
  - validare su casi reali coerenza tab/azioni per specialità TL
  - verificare `403` backend su cliente fuori team nelle azioni service-specifiche
- `Check` / `Task` / `Clienti` (`Team Leader`)
  - validazione end-to-end scope dati team (oltre ai filtri UI)
- `Capienza`
  - fix logica conteggio “clienti assegnati”
- `Check`
  - fix `Creazione link check non funziona`

### P1 (importanti, non bloccanti)

- `Welcome / Dashboard`
  - validazione KPI/liste TL su dati reali (scope team corretto in tutti i widget)
- `Professionista` (QA end-to-end)
  - validazione completa refactor visuale/permessi su `dashboard`, `check`, `task`, `clienti`, `team/profilo`, `formazione`
- `UI trasversale`
  - fix topbar/avatar/sidebar visual (`margini`, `X`, highlight, immagini profilo, ruolo TL in topbar)
  - verifica/allineamento `Tab medico`
- `Quality` (`Admin/CCO`)
  - test completo del flusso
- `In Prova` (`Admin/CCO`)
  - test completo del flusso

### P2 (miglioramenti / decisioni)

- `Formazione`
  - decidere se introdurre una chat/thread dedicata per `Richieste ricevute` oltre alla gestione inline
- `Welcome / Dashboard TL`
  - valutare endpoint aggregato dedicato (se il riuso dell’endpoint dashboard attuale non basta per performance/manutenibilità)

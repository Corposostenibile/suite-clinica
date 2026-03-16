# Piano Capienza e Tipologie di Supporto

## Metadata

- Branch di lavoro: `feature/capienza-tipologie-supporto`
- Base branch: `main`
- Base commit usato per il branch: `47e33ec7`
- Fonte: trascrizione call tra Matteo Volpara, Emanuele Mastronardi e Samuele Vecchi
- Data piano: 2026-03-16

## Obiettivo

Rendere la sezione capienza affidabile per la crescita del team professionisti, introducendo una logica di carico ponderato basata su:

- tipologia di supporto per nutrizione
- tipologia di supporto per coach
- categoria `A / B / C / secondario`
- conteggio dei soli clienti attivi per il servizio rilevante
- pesi configurabili lato admin/CCO

L'obiettivo operativo e' evitare una lettura fuorviante della saturazione dei professionisti e supportare assegnazioni e reporting coerenti con il pacchetto venduto.

## Decisioni emerse dalla call

1. La capienza e' una metrica fondamentale, non opzionale, e deve misurare il carico reale dei professionisti.
2. La tipologia non deve piu' essere trattata come un unico valore globale sufficiente per questo caso d'uso.
3. Servono due campi distinti di supporto:
   - `tipologia_supporto_nutrizione`
   - `tipologia_supporto_coach`
4. I valori attesi per i due campi sono: `a`, `b`, `c`, `secondario`.
5. La tipologia arriva gia' dal nome pacchetto/webhook GHL nel formato concettuale `programma - durata - tipologia` e oggi non viene estratta correttamente.
6. Per i nuovi clienti l'assegnazione deve partire gia' con la tipologia valorizzata in automatico.
7. Per lo storico Matteo prevede una bonifica a script direttamente sul database di produzione, dopo che i nuovi campi saranno disponibili.
8. La pagina capienza deve mostrare, per professionista, il breakdown dei clienti attivi per categoria e la capienza ponderata risultante.
9. Lo psicologo pesa sempre `1`, indipendentemente dalla tipologia.
10. I pesi devono essere gestibili in una pagina admin dedicata, con separazione logica tra nutrizione e coach; accesso operativo previsto per Roberto Roccaro / CCO.

## Stato attuale su `main`

### Gia' presente

- Backend e frontend hanno gia' una prima implementazione di capienza ponderata per `A / B / C`.
- Esiste gia' la tabella `capacity_type_weights` con API admin per leggere e aggiornare i pesi.
- La pagina team capienza mostra gia' conteggi `A / B / C`, capienza ponderata e percentuale ponderata.
- Il backend calcola il breakdown tipologico per ruolo in `backend/corposostenibile/blueprints/team/api.py`.

### Gap rispetto alla call

- Manca la categoria `secondario`.
- I pesi sono globali per `A / B / C`, non separati per nutrizione e coach.
- Non esistono ancora i campi dedicati `tipologia_supporto_nutrizione` e `tipologia_supporto_coach`.
- La valorizzazione automatica da pacchetto/webhook non copre la tipologia finale indicata dopo la durata.
- Il calcolo capienza usa ancora `Cliente.tipologia_cliente`, mentre la call richiede una logica di supporto distinta per area professionale.
- Va verificato che tutti i conteggi mostrati in tabella usino solo clienti attivi del servizio corretto, senza regressioni sui fix gia' fatti.

## Piano di lavoro

### Fase 1: allineamento funzionale e mapping dati

- Formalizzare il mapping pacchetto -> professionisti richiesti -> tipologia supporto per nutrizione e coach.
- Definire con precisione come interpretare i codici pacchetto:
  - prima lettera = professionista primario
  - seconda lettera = professionista secondario
  - suffisso finale dopo durata = tipologia `A/B/C`
- Chiarire i casi con psicologo, che resta fuori dalla ponderazione tipologica e vale sempre `1`.
- Verificare dove la nomenclatura pacchetto entra oggi nel flusso:
  - webhook GHL
  - eventuale old suite integration
  - assegnazioni manuali o bridge intermedi

### Fase 2: modello dati e migrazioni

- Aggiungere sul cliente due nuovi campi persistenti:
  - `tipologia_supporto_nutrizione`
  - `tipologia_supporto_coach`
- Introdurre enum o validazione coerente con i valori `a`, `b`, `c`, `secondario`.
- Estendere il modello pesi per supportare il requisito reale della call:
  - opzione minima: aggiungere `secondario` ai pesi globali
  - opzione corretta rispetto alla call: pesi distinti per area `nutrizione` e `coach`, con chiave composta tipo `area + tipologia`
- Preparare migrazione Alembic e default iniziali.

### Fase 3: valorizzazione automatica nei flussi nuovi

- Aggiornare il parsing del pacchetto in ingresso da GHL per estrarre anche la tipologia finale.
- Popolare automaticamente i nuovi campi supporto nel flusso di creazione/aggiornamento cliente.
- Garantire che le assegnazioni future partano con i campi gia' compilati, senza intervento manuale.
- Verificare se il modulo `package_requirements.py` va esteso oppure se serve un parser dedicato per non sovraccaricare la logica attuale.

### Fase 4: adeguamento logica backend capienza

- Spostare il calcolo della capienza ponderata da `tipologia_cliente` ai nuovi campi di supporto distinti per ruolo.
- Per nutrizione:
  - usare `tipologia_supporto_nutrizione`
- Per coach:
  - usare `tipologia_supporto_coach`
- Per psicologia:
  - mantenere peso fisso a `1`
- Includere nel breakdown anche `secondario`.
- Garantire che il totale clienti mostri solo clienti attivi per il servizio rilevante:
  - `stato_nutrizione == attivo`
  - `stato_coach == attivo`
  - `stato_psicologia == attivo`
- Verificare il comportamento Health Manager, che nella call non e' il focus principale ma non deve regredire.

### Fase 5: configurazione admin pesi

- Evolvere la schermata admin pesi per aderire alla struttura finale:
  - tab nutrizione
  - tab coach
- Ogni tab deve permettere di configurare i pesi di:
  - `A`
  - `B`
  - `C`
  - `secondario`
- Limitare l'accesso operativo ai ruoli previsti, mantenendo almeno `admin/CCO`.
- Se richiesto, aggiungere una regola piu' restrittiva specifica per Roberto Roccaro.

### Fase 6: aggiornamento UI pagina capienza

- Mostrare per ciascun professionista:
  - totale clienti attivi
  - numero clienti `A`
  - numero clienti `B`
  - numero clienti `C`
  - numero clienti `secondario`
  - capienza ponderata
  - percentuale rispetto alla capienza contrattuale
- Valutare se la vista debba essere separata per area o mantenuta in una sola tabella con colonne contestuali.
- Rendere esplicito che la percentuale va calcolata sulla capienza ponderata, non sul semplice conteggio clienti.

### Fase 7: storico, bonifica e rollout

- Consegnare i nuovi campi pronti per la bonifica storica.
- Matteo eseguira' lo script di backfill sui dati esistenti in produzione, derivando i valori dal pacchetto.
- Dopo il backfill:
  - verificare alcuni professionisti campione
  - confrontare somma per categoria con totale clienti attivi
  - validare la percentuale ponderata rispetto alla capienza contrattuale reale
- Eseguire validazione nell'ambiente produzione GCP: `http://34.154.33.164/`

## Dipendenze tecniche da considerare

- `backend/corposostenibile/blueprints/team/api.py`
- `backend/corposostenibile/models.py`
- `backend/corposostenibile/package_requirements.py`
- `backend/corposostenibile/blueprints/ghl_integration/*`
- `corposostenibile-clinica/src/pages/team/TeamCapacity.jsx`
- `corposostenibile-clinica/src/pages/admin/CapacityWeightSettings.jsx`

## Rischi principali

- Ambiguita' sulla semantica tra `tipologia_cliente` esistente e nuove tipologie di supporto.
- Possibili regressioni nei conteggi se lo stesso cliente e' agganciato tramite piu' relazioni per lo stesso ruolo.
- Incongruenza tra pesi globali gia' introdotti su `main` e requisito nuovo di pesi separati per nutrizione/coach.
- Dati storici incompleti o sporchi fino a quando il backfill non viene eseguito.

## Criteri di accettazione

1. Un nuovo cliente creato da webhook con pacchetto nel formato previsto valorizza automaticamente i campi supporto corretti.
2. La pagina capienza mostra solo clienti attivi del servizio rilevante.
3. La somma delle categorie visualizzate coincide con il totale clienti attivi del professionista.
4. La capienza ponderata usa i pesi configurati e include `secondario`.
5. Lo psicologo continua a valere `1` sempre.
6. I pesi sono modificabili dalla pagina admin prevista e l'effetto e' immediato nel calcolo.
7. Dopo il backfill storico, i numeri in produzione risultano coerenti su un campione validato.

## Nota operativa

Su `main` esiste gia' una base implementativa per la capienza ponderata. Il lavoro di questo branch non deve ricostruire da zero quella parte, ma estenderla per coprire:

- campi supporto distinti
- categoria `secondario`
- parsing corretto del pacchetto
- pesi separati per area professionale se confermati come requisito definitivo

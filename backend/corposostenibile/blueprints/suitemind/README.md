# Blueprint Suitemind

Questo blueprint (`suitemind`) integra funzionalità di intelligenza artificiale per la gestione e l'interazione con i dati dei clienti, principalmente tramite un'interfaccia di chat. Permette agli utenti di interrogare i dati PostgreSQL in linguaggio naturale e ricevere risposte intelligenti.

## Struttura del Blueprint

Il blueprint `suitemind` è organizzato nelle seguenti sottocartelle:

- `assets/`: Contiene risorse statiche come immagini.
- `routes/`: Definisce gli endpoint API e le rotte web per il blueprint.
- `services/`: Contiene la logica di business e l'integrazione con servizi esterni (es. database, modelli LLM).
- `templates/`: Contiene i file HTML per l'interfaccia utente.
- `utils/`: Contiene funzioni di utilità e moduli di supporto.

### 1. `assets/`

Questa cartella contiene le risorse statiche utilizzate dal blueprint. Attualmente include:

- `images/`: Immagini come il logo di Suitemind (`suitemind.jpeg`).

### 2. `routes/`

Questa cartella definisce le rotte del blueprint, separando la logica delle API da quella delle pagine web principali.

- `api_routes.py`: Definisce gli endpoint API per l'interazione con i servizi di Suitemind, come la chat con PostgreSQL.
- `main_routes.py`: Definisce le rotte per le pagine web principali, come la pagina della chat (`index.html`).

### 3. `services/`

Questa cartella contiene la logica di business principale e l'integrazione con il database PostgreSQL e i modelli di linguaggio (LLM) tramite Ollama. I servizi sono progettati per essere modulari e riutilizzabili.

- `__init__.py`: Questo file è responsabile dell'inizializzazione dei servizi all'interno del blueprint `suitemind`. Contiene la funzione `get_postgres_suitemind_service()` che restituisce un'istanza del `PostgresSuitemindService`. Questo approccio garantisce che il servizio sia disponibile per le rotte API e altre parti del blueprint in modo controllato.
- `postgres_suitemind_service.py`: Questo è il cuore del servizio Suitemind per l'interazione con PostgreSQL. La classe `PostgresSuitemindService` orchestra l'intero flusso di lavoro per rispondere alle query degli utenti. Le sue responsabilità includono:
    - **Inizializzazione**: Accetta un'istanza di `SQLDatabase` per connettersi al database PostgreSQL.
    - **Orchestrazione**: Gestisce la logica per analizzare la query dell'utente, determinare se riguarda i dati dei clienti, generare e eseguire query SQL, formattare i risultati e generare una risposta intelligente utilizzando modelli LLM (tramite Ollama).
    - **Gestione del Contesto**: Assicura che le operazioni sul database avvengano all'interno di un contesto applicativo Flask valido, inizializzando `SQLDatabase` solo quando un contesto è attivo.
    - **Integrazione LLM**: Utilizza modelli di linguaggio per interpretare le query in linguaggio naturale e formulare risposte comprensibili basate sui dati recuperati.

### 4. `templates/`

Questa cartella contiene i file HTML che definiscono l'interfaccia utente del blueprint.

- `index.html`: La pagina principale della chat di Suitemind, dove gli utenti possono interagire con il sistema.

### 5. `utils/`

Questa cartella contiene moduli di utilità e funzioni di supporto utilizzate in tutto il blueprint.

- `logging.py`: Configurazione e gestione del logging per il blueprint.

## Flusso di Lavoro Generale

1. **Richiesta Utente**: L'utente interagisce con l'interfaccia web (`index.html`) e invia una query.
2. **Routing**: La richiesta viene gestita da `main_routes.py` (per la pagina) o `api_routes.py` (per le interazioni API).
3. **Servizi**: Gli endpoint API in `api_routes.py` invocano i servizi definiti in `services/` (es. `postgres_suitemind_service.py`).
4. **Elaborazione**: Il servizio elabora la query, interagisce con il database PostgreSQL (se necessario) e/o con i modelli LLM per generare una risposta.
5. **Risposta**: La risposta viene restituita all'interfaccia utente e visualizzata nella chat.
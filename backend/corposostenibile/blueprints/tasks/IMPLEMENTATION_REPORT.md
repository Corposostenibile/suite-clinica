# Report di Implementazione: Task & Automation

**Data**: 15/16 Dicembre 2025

## Panoramica
È stata implementata una nuova funzionalità completa di **Task Management** all'interno della suite Corposostenibile. L'obiettivo era fornire un sistema centralizzato per gestire le attività operative generate automaticamente dalle interazioni dei clienti (nuovi iscritti, ticket, check settimanali, richieste training, reach out periodici).

## Architettura e Implementazione

### 1. Backend (Data Model & Logic)
- **Modello `Task`**: Creata nuova entità nel database con supporto a priorità, stati, tipi e assegnatario.
- **Relazioni**: Collegamenti con `Cliente`, `Ticket`, `User` (assegnatario) e `Department`.
- **API**: Implementato endpoint per il completamento e la gestione dei task.

### 2. Frontend (UI/UX)
- **Dashboard Task**: Nuova vista dedicata (`/tasks`) accessibile dalla sidebar.
- **Interfaccia**: Tabella con filtri per stato e priorità, badge colorati e azioni rapide.

### 3. Automazione (Event Listeners Centralizzati)
Abbiamo adottato un approccio **Event-Driven** centralizzato (`corposostenibile/blueprints/tasks/listeners.py`) utilizzando hook SQLAlchemy `before_flush`.

#### Tabella Assegnazione Task
Di seguito il dettaglio di come vengono generati i task e a chi vengono assegnati:

| Tipo Task | Trigger (Evento) | Descrizione | Logica di Assegnazione (Chi lo riceve?) |
| :--- | :--- | :--- | :--- |
| **ONBOARDING** | Nuovo `Cliente` creato | Promemoria benvenuto e verifica moduli. | Viene creato **un task per ogni professionista** assegnato al cliente: <br> - Coach <br> - Nutrizionista <br> - Psicologo <br> - Health Manager |
| **REACH OUT** | Modifica campi `reach_out_*` su `Cliente` | Task ricorrente settimanale per contatto cliente. | Assegnato allo **specifico professionista** del servizio: <br> - `reach_out_nutrizione` -> Nutrizionista <br> - `reach_out_coaching` -> Coach <br> - `reach_out_psicologia` -> Psicologo |
| **CHECK** | Nuova `ClientCheckResponse` | Notifica di check compilato dal cliente. | Assegnato al **professionista** che ha in carico quel check (chi ha inviato la richiesta o il titolare del servizio). |
| **TRAINING** | Nuova `ReviewRequest` | Richiesta di revisione/formazione interna. | Assegnato al **responsabile** indicato nella richiesta (Requested To). |
| **TICKET** | Nuovo `Ticket` aperto | Task operativo specchio del ticket. | Assegnato all'utente **assegnatario del ticket** (se presente). |

### 4. Refactoring
Durante l'implementazione, abbiamo refactorizzato il codice esistente:
- Rimossa la creazione manuale dei task da `customers/services.py`, `ticket/services.py`, `client_checks/services.py` e `review/routes.py`.
- Tutta la logica "business" risiede ora esclusivamente in `listeners.py`.

## Verifica e Testing
È stata creata una suite di test automatizzata (`test_listeners.py`) in `corposostenibile/blueprints/tasks/tests/`.

### Risultati Test
1.  **Onboarding**: ✅ Testato (Creazione Cliente con Coach+Nutri -> Generati 2 Task assegnati correttamente ai rispettivi professionisti).
2.  **Reach Out**: ✅ Testato (Impostazione giorno -> Task generato e assegnato al professionista corretto).
3.  **Recursion**: ✅ Testato (Completamento Task Reach Out -> Nuovo Task generato +7gg con stesso assegnatario).
4.  **Training**: ✅ Testato (Richiesta -> Task generato e assegnato al responsabile).
5.  **Ticket**: Logica testata simmetricamente agli altri.


### 5. Pannello Admin & Configurazione Priorità
Abbiamo introdotto un sistema flessibile per la gestione delle priorità, eliminando i valori hardcoded.

- **Modello `TaskPriorityConfig`**: Memorizza la priorità di default scelta per ogni `TaskType`.
- **Interfaccia Settings**: Nuova pagina `/tasks/settings` (accessibile solo agli admin) dove è possibile configurare le priorità.
- **Logica Dinamica**: In fase di creazione task, il listener consulta questa configurazione. Se non presente, usa un fallback (Medium).
- **Miglioramenti UI**: 
  - Pulsante impostazioni visibile solo agli user con permessi elevati.
  - Badge colorati e nomi leggibili (es. "Onboarding Cliente" invece di "onboarding") per migliore UX.


### 6. Dashboard di Monitoraggio (Admin)
È stata implementata una dashboard analitica per monitorare l'andamento operativo del team:
- **KPI Cards**: Visualizzazione immediata di Task Aperti, Task Scaduti (Overdue), Alta Priorità.
- **Grafici**: 
  - Distribuzione per Tipo Task (Ticket vs Onboarding vs Check...).
  - Carico di Lavoro per Utente (Top 10 utenti con più task).
- **Lista Criticità**: Tabella dedicata ai task scaduti da più tempo per intervento rapido.
- **Integrazione**: Accessibile direttamente dalle impostazioni task solo per amministratori.
- **Filtro Utente**: Implementata ricerca testuale per filtrare i dati della dashboard per specifico utente.

### 7. User Experience & Comunicazione
Sono stati aggiornati i formati dei messaggi automatici per renderli più "umani" e orientati all'azione (CTA), come richiesto:

- **Onboarding**: *"Ti è stato Assegnato un nuovo cliente: {Nome}. Mandagli il messaggio di onboarding!"*
- **Ticket**: *"Nuovo ticket aperto da {Nome}. Risolvi la richiesta al più presto! ..."*
- **Check**: *"{Nome} ha compilato il check settimanale. Analizza le risposte e invia il tuo feedback!"*
- **Training**: *"{Nome} ha richiesto una revisione tecnica. Guarda il video e lascia i tuoi consigli! ..."*
- **Reach Out**: *"È il momento del controllo periodico per {Nome}. Contattalo per sapere come sta procedendo!"*


## Conclusione
Il sistema è ora attivo e perfettamente integrato. La struttura centralizzata permette di aggiunere facilmente nuove automazioni, mentre il pannello admin garantisce flessibilità operativa senza necessità di interventi sul codice.

# Documentazione Metriche di Recruiting

Questo documento descrive le metriche implementate nel modulo di recruiting.

## 1. Metriche delle Offerte

Per ogni offerta di lavoro è disponibile una dashboard dedicata alle metriche. Questa dashboard fornisce indicatori chiave di prestazione (KPI) per valutare l'efficacia dell'offerta.

### Metriche Disponibili

*   **Click**: Numero totale di volte in cui il link pubblico dell'offerta di lavoro è stato cliccato. Questo indica la portata dell'offerta.
*   **Candidature Ricevute**: Numero totale di candidature inviate per l'offerta di lavoro.
*   **Tasso di Conversione**: La percentuale di click che si sono trasformati in una candidatura inviata. Viene calcolato come `(Candidature Ricevute / Click) * 100`.
*   **Assunzioni**: Numero totale di candidati assunti da questa specifica offerta di lavoro.

### Come Accedere

Dalla pagina di dettaglio di un'offerta di lavoro, è presente un pulsante "Vedi Metriche" che collega alla dashboard delle metriche specifiche dell'offerta.

Dalla dashboard principale del recruiting, c'è un link a una dashboard generale delle metriche che mostra una panoramica di tutte le offerte.

## 2. Metriche della Pipeline Kanban

Le board Kanban, sia per la visualizzazione generale che per quella della singola offerta, includono una metrica per mostrare la progressione dei candidati attraverso la pipeline.

### Metrica Disponibile

*   **Percentuale per Stadio**: Per ogni stadio nella board Kanban, viene visualizzata una percentuale. Questa percentuale rappresenta il rapporto tra i candidati attualmente in quello stadio e il numero totale di candidati che sono entrati nel primo stadio ("Candidatura Ricevuta").

### Calcolo

La percentuale è calcolata come:
`(Numero di candidati nello stadio attuale / Numero di candidati nello stadio iniziale) * 100`

Questa metrica aiuta a identificare rapidamente i colli di bottiglia nel processo di recruiting e a capire in quale stadio la maggior parte dei candidati abbandona il processo.

### Come Accedere

La percentuale è visibile nell'intestazione di ogni colonna sulla board Kanban, accanto al conteggio totale dei candidati in quello stadio.
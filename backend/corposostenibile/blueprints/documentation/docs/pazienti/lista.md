# 👥 Lista Pazienti — Guida completa per professionisti

Questa pagina è il tuo centro operativo principale: qui gestisci tutti i pazienti, applichi filtri rapidi e accedi alle azioni quotidiane. È progettata per essere efficiente e sicura, con tutto quello che serve per lavorare al meglio.

## 🏠 Come Arrivare Qui

- Dal menu principale: "Pazienti" → "Lista Pazienti"
- Da altre pagine: cerca il link "Lista Pazienti" nel menu laterale
- URL diretta: `/clienti-lista` (si apre automaticamente se sei loggato)

## 🟢 Quello che Vedi Subito (Dashboard Rapida)

### I 4 Numeri in Alto (Statistiche Veloci)
- **Pazienti Totali**: Quanti pazienti sono registrati complessivamente
- **Nutrizionista Attivo**: Quanti seguono attivamente un piano alimentare
- **Coach Attivo**: Quanti fanno allenamento con un coach
- **Psicologo Attivo**: Quanti sono in percorso psicologico

**Perché sono utili**: Ti danno un'istantanea della situazione clinica. Se vedi molti "Ghost", sai che devi fare follow-up.

### Come Si Aggiornano
- Automaticamente al caricamento della pagina
- Si aggiornano quando salvi modifiche in altre schede
- Riflettono sempre i filtri attivi (se filtri per "Attivo", i numeri cambiano)

## 🔍 Sistema di Ricerca e Filtraggio (Passo-Passo Dettagliato)

La barra dei filtri è sotto i numeri. Ecco come usarla al meglio:

### 1. **Ricerca per Nome (Campo Testo)**
- **Cosa fa**: Ricerca nel nome completo del paziente
- **Come**: Scrivi e aspetta (debounce automatico di 300ms)
- **Esempi**:
  - "Mario Rossi" → trova il paziente
  - "Mario" → trova chi contiene "Mario"
  - "Rossi" → trova chi contiene "Rossi"
- **Suggerimenti**: Se non trovi, prova con meno caratteri o controlla l'ortografia

### 2. **Filtro Stato Cliente**
- **Opzioni disponibili**:
  - **Attivo**: Segue il programma regolarmente
  - **Pausa**: Temporaneamente fermo
  - **Ghost**: Non risponde (criticità!)
  - **Insoluto**: Pagamento pendente
  - **Stop**: Ha terminato il programma
  - **Freeze**: Bloccato per motivi medici/personali
- **Quando usare**: Per organizzare la giornata per priorità

### 3. **Filtro Tipologia**
- **Opzioni**: A, B, C
- **Cosa significa**: Livello complessità/tipo abbonamento (chiedi all'admin)
- **Uso pratico**: Per segmentare pazienti per lotto

### 4. **Filtro per Professionista**
- **Nutrizionista**: Vedi pazienti assegnati a quel nutrizionista
- **Coach**: Vedi pazienti assegnati a quel coach
- **Psicologa**: Vedi pazienti assegnati a quella psicologa
- **Nota**: Sono filtri dinamici (carichi dal team attivo)

### 5. **Pulsante Reset**
- **Icona**: Freccia circolare di refresh
- **Funzione**: Cancella TUTTI i filtri e ricarica la lista
- **Quando usare**: Tornare alla vista completa

**Funzione avanzata - URL State**: L'URL si aggiorna con i filtri. Puoi copiarlo per ricerche frequenti.

## 📋 La Tabella Principale (Cuore della Pagina)

Ogni riga è un paziente. Ecco cosa significa ogni colonna:

### Colonna "Nome Cognome"
- **Cosa vedi**: Nome completo del paziente
- **Cosa fare**: **Clicca qui** per aprire la scheda completa
- **Stile**: Link blu che diventa viola al passaggio del mouse

### Colonna "Team"
- **Cosa vedi**: Cerchietti colorati con iniziali professionisti
- **Ho visto renderizzare**:
  - Health Manager (HM) - Viola
  - Nutrizionista/i (N) - Verde
  - Coach (C) - Blu
  - Psicologo/i (P) - Rosa
  - Consulente/i (CA) - Giallo
- **Interazione**: Pass il mouse per tooltip con nome completo
- **Nota**: Se nessun team assegnato, vedi un trattino (—)

### Colonna "Data Inizio"
- **Cosa vedi**: Quando è diventato paziente (gg/mm/aaaa)
- **Perché importante**: Per calcolare la durata del percorso
- **Uso**: Filtra per "nuovi ingressi del mese"

### Colonna "Data Rinnovo"
- **Cosa vedi**: Quando scade l'abbonamento
- **Perché critica**: Se vicina, contatta il paziente!
- **Colore**: Rosso se urgente
- **Azione**: Clicca per aprire la scheda e gestire il rinnovo

### Colonna "Programma"
- **Cosa vedi**: Tipo di percorso (es. "Percorso Completo", "Solo Nutrizione")
- **Badge**: Rettangolo colorato blu chiaro
- **Uso**: Per capire il livello di impegno del paziente

### Colonna "Stato"
- **Cosa vedi**: Badge colorato con lo stato attuale
- **Colori**:
  - 🟢 Verde: Attivo (tutto ok)
  - 🟠 Arancione: Pausa (temporaneo)
  - 🔘 Blu: Ghost (non risponde)
  - 🔴 Rosso: Insoluto (pagamento)
  - 🟣 Viola: Freeze (bloccato)
- **Perché utile**: Identifica subito i problemi

### Colonna "Azioni"
- **Occhio verde**: Apri la scheda dettaglio in visualizzazione
- **Matita blu**: Apri la scheda nel modulo modifica
- **Entrambi i pulsanti**: Conducono alla scheda completa (`/clienti-dettaglio/:id`)
- **Stile**: Bottoni piccoli circolari, cambiano background al hover

## 🔄 Paginazione (Quando Hai Molti Pazienti)

- **Posizione**: Sotto la tabella
- **Informazioni**: "Pagina 2 di 5 • 127 risultati"
- **Controlli**:
  - «« Prima pagina
  - « Pagina precedente
  - 1 2 3 4 5 (numeri cliccabili)
  - » Pagina successiva
  - »» Ultima pagina
- **Configurazione**: 25 pazienti per pagina (standard)

## 🎯 Scenari Operativi Quotidiani

### Scenario 1: "Organizzo la mia giornata"
1. Filtro per il mio ruolo (es. "Nutrizionista: [Mio Nome]")
2. Filtro per "Stato: Attivo"
3. Ordino per "Data Rinnovo" (i più urgenti prima)
4. Chiamo i pazienti uno per uno

### Scenario 2: "Gestisco i pazienti problematici"
1. Filtro per "Stato: Ghost"
2. Per ognuno: clicco nome → vedo contatti → chiamo
3. Dopo chiamata: aggiorno stato in scheda (se necessario)

### Scenario 3: "Controllo rinnovi settimanali"
1. Filtro per "Data Rinnovo" entro 7 giorni
2. Per ognuno: clicco nome → sezione "Programma" → gestisco rinnovo
3. Contatto paziente per conferma

### Scenario 4: "Valuto nuovi ingressi"
1. Filtro per "Data Inizio" ultimo mese
2. Controllo che abbiano team assegnato
3. Verifico che abbiano fatto check iniziali

### Scenario 5: "Report per direzione"
1. Nessun filtro (vista completa)
2. Guardo i numeri in alto
3. Esporto o copio i dati per report

> [!TIP]
> **Ricorda**: Questa è la tua dashboard principale. Inizia sempre da qui per pianificare efficacemente il lavoro con i pazienti.

> [!IMPORTANT]
> **Aggiornamenti**: Quando modifichi una scheda paziente, torna qui per vedere i cambiamenti nei numeri e nella lista.

> [!NOTE]
> **Performance**: La pagina gestisce migliaia di pazienti grazie alla paginazione intelligente e ai filtri server-side.
---

> [!TIP]
> **Ricorda**: Questa è la tua dashboard principale. Inizia sempre da qui per pianificare efficacemente il lavoro con i pazienti.

> [!IMPORTANT]
> **Aggiornamenti**: Quando modifichi una scheda paziente, torna qui per vedere i cambiamenti nei numeri e nella lista.

> [!NOTE]
> **Performance**: La pagina gestisce migliaia di pazienti grazie alla paginazione intelligente e ai filtri server-side.


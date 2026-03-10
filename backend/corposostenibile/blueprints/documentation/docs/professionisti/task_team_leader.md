# 📋 Sistema Task — Guida Team Leader

Per un Team Leader la pagina Task e una vista di coordinamento del lavoro. Non serve solo a vedere attivita aperte: deve mostrarti dove si accumula il backlog, quali ruoli sono in difficolta e dove va fatto coaching operativo.

## Cosa fai qui come Team Leader

- Identifichi task scaduti, in stallo o non presi in carico.
- Filtri per assegnatario, ruolo e specialita per capire dove intervenire.
- Usi completati e backlog per leggere continuita, puntualita e qualita esecutiva.

## Domande a cui deve rispondere questa pagina

- Chi e in ritardo sulle attivita critiche?
- Quale ruolo o specialita sta accumulando lavoro?
- Dove serve supporto, chiarezza o riallocazione?

# 📋 Sistema Task — Guida completa per professionisti

Il sistema Task è il tuo assistente digitale personale per gestire tutte le attività quotidiane, scadenze e solleciti. È progettato per aiutarti a non dimenticare nulla e organizzare il lavoro in modo efficiente.

## 🏠 Come Arrivare Qui

- Dal menu principale: "Task" o "Le tue Attività"
- URL diretta: `/task`
- È accessibile solo ai professionisti autorizzati

## 🟢 Quello che Vedi Subito (Dashboard Task)

![Dashboard Task](../screenshots/task/dashboard_task.png)

### Le 6 Card Statistiche (In Alto)

Ogni card rappresenta una categoria di task con il numero di attività aperte:

#### 📋 **Onboarding** (Blu)
- **Cosa sono**: Attività di benvenuto per nuovi clienti
- **Esempi**: "Call iniziale con Mario Rossi", "Invio materiale di benvenuto"
- **Quando appaiono**: Automaticamente quando un cliente viene assegnato

#### ✅ **Check** (Verde)
- **Cosa sono**: Controlli periodici e valutazioni
- **Esempi**: "Check settimanale cliente", "Valutazione mensile progresso"
- **Quando appaiono**: Secondo il calendario check del cliente

#### ⏰ **Reminder** (Arancione)
- **Cosa sono**: Promemoria per scadenze importanti
- **Esempi**: "Scadenza abbonamento tra 7 giorni", "Rinnovo piano alimentare"
- **Quando appaiono**: Automaticamente prima delle scadenze critiche

#### 📚 **Formazione** (Viola)
- **Cosa sono**: Attività di apprendimento e training
- **Esempi**: "Corso online da completare", "Aggiornamento procedure"
- **Quando appaiono**: Quando vengono assegnati corsi o formazioni

#### 🚨 **Solleciti** (Rosso)
- **Cosa sono**: Richiami per clienti che non rispondono
- **Esempi**: "Cliente non ha fatto check settimana scorsa", "Sollecito appuntamento mancato"
- **Quando appaiono**: Automaticamente quando un cliente diventa "ghost"

#### 📝 **Generico** (Grigio)
- **Cosa sono**: Task manuali creati dai colleghi
- **Esempi**: "Chiamare fornitore", "Aggiornare documentazione"
- **Quando appaiono**: Quando un collega ti assegna un task manuale

**Cliccando su una card**: Filtra automaticamente i task di quella categoria.

## 📊 La Tabella Principale (Lista Task)

![Tabella Task](../screenshots/task/la_tua_lista_attivita.png)

### Come È Organizzata
- **Righe**: Ogni riga è un task da completare
- **Colonne**: Checkbox, Attività, Categoria, Cliente, Scadenza, Priorità, Azioni

### Colonna "Checkbox" (Completamento)
- **Vuota**: Task da fare
- **Spuntata**: Task completato
- **Come completare**: Clicca sulla checkbox per segnare come fatto
- **Effetto**: Il task sparisce dalla vista (se non stai mostrando i completati)

### Colonna "Attività"
- **Titolo**: Descrizione breve del task
- **Descrizione**: Dettagli aggiuntivi (se presenti)
- **Stile**: Barrato quando completato

### Colonna "Categoria"
- **Badge colorato**: Identifica il tipo di task
- **Icona**: Aiuta a riconoscere velocemente il tipo

### Colonna "Cliente"
- **Nome**: Cliente collegato al task (se presente)
- **Avatar**: Iniziali del cliente in un cerchio
- **Vuoto**: Task non collegato a un cliente specifico

### Colonna "Scadenza"
- **Oggi/Ieri**: Date relative per task urgenti
- **Data**: Giorno e mese per task futuri
- **Rosso**: Task scaduti (da fare urgentemente!)

### Colonna "Priorità"
- **Colore**: Verde (bassa), Giallo (media), Rosso (alta/urgente)
- **Pallino**: Indicatore visivo accanto al testo

### Colonna "Azioni"
- **Freccia destra**: Pulsante "Vai" per task collegati
- **Visibile solo**: Per task non completati e con collegamenti

## 🔄 Filtri e Navigazione

![Filtri](../screenshots/task/filtri_comodi.png)

### Tab in Alto (Filtraggio per Categoria)
- **Tutti**: Mostra tutti i task aperti
- **Per categoria**: Mostra solo quella categoria
- **Conteggio**: Numero di task per ogni tab
- **Nasconde tab vuote**: Se non hai task in una categoria, il tab sparisce

### Switch "Mostra Completate"
- **Posizione**: In alto a destra
- **Funzione**: Mostra anche i task già completati
- **Uso**: Per vedere lo storico o ricontrollare qualcosa

### Pulsante Refresh
- **Icona**: Freccia circolare
- **Funzione**: Ricarica la lista e le statistiche
- **Quando usare**: Se vedi dati vecchi o dopo modifiche

## 🚀 Navigazione Intelligente

### Come Funziona il Pulsante "Vai"
Quando clicchi "Vai" su un task, il sistema ti porta automaticamente:

#### Per Task "Check"
- **Destinazione**: Scheda cliente, tab "Check"
- **Perché**: Per gestire i controlli periodici

#### Per Task "Solleciti" e "Onboarding"
- **Destinazione**: Scheda cliente principale
- **Perché**: Per contattare il cliente o gestire l'ingresso

#### Per Task "Reminder"
- **Destinazione**: Scheda cliente principale
- **Perché**: Per gestire scadenze e rinnovi

#### Per Task "Formazione"
- **Destinazione**: Link esterno o sezione formazione
- **Perché**: Per accedere ai materiali didattici

#### Per Task "Generico"
- **Destinazione**: Dipende dal payload del task
- **Perché**: Collegamento personalizzato dal creatore
---

> [!TIP]
> **Il sistema Task è il tuo assistente**: Aiuta a non dimenticare nulla e mantiene organizzato il lavoro con i clienti.

> [!IMPORTANT]
> **Task automatici**: Sono generati dal sistema per tua sicurezza. Non ignorarli!

> [!NOTE]
> **Pulizia automatica**: I task completati vengono nascosti per mantenere la lista gestibile.</content>

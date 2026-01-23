# SuiteMind PostgreSQL Services

Questa cartella contiene i servizi per l'integrazione diretta di PostgreSQL con SuiteMind, permettendo query in linguaggio naturale sui dati dei clienti.

## Architettura

Il sistema è composto da tre componenti principali:

### 1. PostgresQueryAgent (`postgres_query_agent.py`)
- **Scopo**: Genera query SQL basate su input in linguaggio naturale
- **Modello**: Utilizza `gemma3:4b` tramite Ollama
- **Sicurezza**: Implementa regole di sicurezza per prevenire query dannose
- **Schema**: Conosce la struttura completa della tabella `clienti`

**Caratteristiche**:
- Genera solo query `SELECT`
- Aggiunge automaticamente `LIMIT` per performance
- Usa `ILIKE` per ricerche testuali case-insensitive
- Valida le query generate
- Fornisce spiegazioni delle query in linguaggio naturale

### 2. PostgresCustomerService (`postgres_customer_service.py`)
- **Scopo**: Esegue le query SQL e formatta i risultati
- **Database**: Si connette direttamente al database PostgreSQL tramite SQLAlchemy
- **Formattazione**: Converte i risultati in formato JSON leggibile

**Funzionalità**:
- Esecuzione sicura delle query SQL
- Formattazione intelligente dei nomi delle colonne
- Conversione automatica dei tipi di dati
- Gestione degli errori e logging
- Preparazione del contesto per l'LLM

### 3. PostgresSuitemindService (`postgres_suitemind_service.py`)
- **Scopo**: Servizio principale che orchestrare tutto il flusso
- **Integrazione**: Combina PostgreSQL con Ollama per risposte intelligenti
- **Routing**: Determina automaticamente se una query riguarda i clienti

**Flusso di lavoro**:
1. Analizza la query dell'utente
2. Determina se riguarda i clienti
3. Genera e esegue la query SQL
4. Formatta i risultati
5. Genera una risposta intelligente con Ollama

## API Endpoints

### `/api/postgres-chat` (POST)
Endpoint principale per le query con PostgreSQL.

**Request**:
```json
{
  "query": "Mostrami tutti i clienti attivi",
  "context": {}  // opzionale
}
```

**Response**:
```json
{
  "success": true,
  "response": "Ho trovato 45 clienti attivi...",
  "customer_data": {
    "total_found": 45,
    "results": [...],
    "sql_query": "SELECT * FROM clienti WHERE stato_cliente = 'attivo'",
    "query_explanation": "Questa query cerca tutti i clienti..."
  },
  "user_query": "Mostrami tutti i clienti attivi",
  "type": "customer_query",
  "processing_time": 1.23
}
```

### `/api/postgres-info` (GET)
Informazioni sul servizio PostgreSQL.

**Response**:
```json
{
  "success": true,
  "data": {
    "service_name": "PostgreSQL SuiteMind Service",
    "version": "1.0.0",
    "capabilities": [...],
    "database_info": {...},
    "supported_queries": [...]
  }
}
```

## Esempi di Query Supportate

### Ricerca Clienti
- "Mostrami tutti i clienti attivi"
- "Cerca clienti con nome Mario"
- "Clienti che hanno pagato più di 1000 euro"
- "Chi sono i clienti seguiti dal nutrizionista X?"

### Statistiche
- "Quanti clienti abbiamo in totale?"
- "Clienti per stato (attivo, ghost, pausa)"
- "Media dei depositi iniziali"

### Filtri Avanzati
- "Clienti italiani con programma Coaching"
- "Clienti registrati negli ultimi 30 giorni"
- "Clienti con email Gmail"

## Sicurezza

Il sistema implementa diverse misure di sicurezza:

1. **Validazione Query**: Solo query `SELECT` sono permesse
2. **Limiti**: Tutte le query hanno un `LIMIT` automatico
3. **Sanitizzazione**: Input sanitizzato per prevenire SQL injection
4. **Logging**: Tutte le query sono loggate per audit
5. **Errori**: Gestione sicura degli errori senza esporre dettagli interni

## Configurazione

### Modelli Ollama Richiesti
- `gemma3:4b`: Per generazione query SQL
- `gemma2:9b`: Per generazione risposte (raccomandato)

### Database
Il servizio si connette automaticamente al database PostgreSQL configurato nell'applicazione Flask tramite SQLAlchemy.

## Logging

Tutti i servizi utilizzano il sistema di logging centralizzato di SuiteMind:
- Query SQL generate ed eseguite
- Errori e eccezioni
- Tempi di elaborazione
- Risultati delle ricerche

## Estensibilità

Il sistema è progettato per essere facilmente estendibile:

1. **Nuove Tabelle**: Aggiungere nuovi schemi in `PostgresQueryAgent`
2. **Nuovi Modelli**: Cambiare i modelli Ollama utilizzati
3. **Formattazione**: Personalizzare la formattazione dei risultati
4. **Validazione**: Aggiungere nuove regole di sicurezza

## Confronto con Sistema Embedding

| Caratteristica | PostgreSQL | Embedding (Qdrant) |
|---|---|---|
| **Velocità** | Molto veloce per query strutturate | Veloce per ricerca semantica |
| **Precisione** | Esatta per criteri specifici | Buona per somiglianza semantica |
| **Flessibilità** | Query SQL complete | Ricerca per similarità |
| **Dati Real-time** | Sempre aggiornati | Richiede re-indicizzazione |
| **Complessità Query** | Supporta JOIN, aggregazioni | Limitata a ricerca vettoriale |
| **Manutenzione** | Nessuna indicizzazione richiesta | Richiede gestione indici |

## Quando Usare PostgreSQL vs Embedding

**Usa PostgreSQL quando**:
- Hai bisogno di dati sempre aggiornati
- Vuoi query complesse con filtri multipli
- Hai bisogno di aggregazioni e statistiche
- Vuoi ricerche esatte per criteri specifici

**Usa Embedding quando**:
- Vuoi ricerca semantica ("clienti simili a...")
- Hai testi lunghi da analizzare
- Vuoi raccomandazioni basate su similarità
- La precisione esatta non è critica
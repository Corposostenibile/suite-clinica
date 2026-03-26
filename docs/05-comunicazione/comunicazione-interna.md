# Comunicazione Interna (Annunci)

Il modulo **Comunicazione Interna** (blueprint `communications`) gestisce il sistema di bacheca aziendale, permettendo al team amministrativo e ai responsabili di inviare annunci, avvisi e comunicazioni importanti ai collaboratori.

## Cos'è e a cosa serve
Serve a centralizzare le comunicazioni istituzionali dell'azienda, superando la dispersione dei messaggi su chat informali. Permette di:
- Inviare annunci a **tutto il team** o a **specifici dipartimenti** (es. solo Nutrizionisti).
- Richiedere una **conferma di lettura** individuale per comunicazioni critiche.
- Monitorare le **statistiche di visualizzazione** in tempo reale.

## Chi lo usa
- **Amministratori / CCO**: Possono creare comunicazioni globali e vedere tutte le statistiche.
- **Head of Department**: Possono creare comunicazioni per il proprio dipartimento.
- **Tutto il personale**: Possono leggere le comunicazioni ricevute e confermare la lettura.

## Come funziona (flusso utente)
1. L'autore accede alla sezione Comunicazioni → Invia Nuova.
2. Compila il titolo, il contenuto (HTML/Rich Text) e seleziona i destinatari.
3. Al momento dell'invio, la comunicazione appare nella bacheca dei destinatari.
4. L'utente riceve un avviso visivo (badge) e può cliccare sulla comunicazione per leggerla.
5. Se richiesto, l'utente clicca su "Segna come letto".

## Architettura Tecnica
Il modulo è implementato come un blueprint Flask con un sistema di permessi basato sulla funzione `can_create_communication`.

### Componenti Principali
- **Backend Blueprint**: `backend/corposostenibile/blueprints/communications`
- **Frontend**: Componente React `ChatBox.jsx` e pagine `Chat.jsx` (utilizzate come bacheca).
- **Servizi**: `CommunicationService` gestisce la creazione e il conteggio delle letture.

## API / Endpoint Principali

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/communications/` | GET | Lista comunicazioni ricevute dall'utente corrente. |
| `/communications/sent` | GET | Elenco comunicazioni inviate dall'autore (Admin/Head). |
| `/communications/create` | POST | Creazione di un nuovo annuncio. |
| `/api/communications/unread-count` | GET | Ritorna il numero di messaggi non letti per il badge UI. |
| `/api/communications/<id>/mark-read` | POST | Conferma di lettura per una specifica comunicazione. |

## Modelli di Dati

### `Communication`
L'entità principale che rappresenta l'annuncio.
- `title`: Titolo dell'annuncio.
- `content`: Testo della comunicazione.
- `author_id`: Riferimento all'utente che ha creato l'annuncio.
- `is_for_all`: Boolean per invio a tutta l'azienda.

### `CommunicationReads`
Tabella di join per il tracking delle letture.
- `communication_id`: FK alla comunicazione.
- `user_id`: FK all'utente che ha letto.
- `read_at`: Timestamp della lettura.

## Note & Gotcha
- **Visibilità**: Una comunicazione inviata a un dipartimento è visibile solo agli utenti che hanno quel dipartimento impostato nel profilo.
- **Priority**: Al momento il sistema non gestisce priorità diverse (es. "urgente"), ma è previsto nelle migliorie future.

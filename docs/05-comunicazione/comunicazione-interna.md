# Comunicazione Interna (Annunci)

> **Categoria**: `comunicazione`
> **Destinatari**: Tutto il personale, Admin, Team Leader
> **Stato**: 🟢 Completo
> **Ultimo aggiornamento**: 27/03/2026

---

## Cos'è e a Cosa Serve

Il modulo Comunicazione Interna gestisce il sistema di bacheca aziendale digitale. Permette al team amministrativo e ai responsabili di dipartimento di inviare annunci, avvisi tecnici e comunicazioni istituzionali in modo tracciabile, differenziando i destinatari per ruolo o area di competenza e garantendo la conferma di lettura per le informazioni critiche.

## Cos'è e a cosa serve
Serve a centralizzare le comunicazioni istituzionali dell'azienda, superando la dispersione dei messaggi su chat informali. Permette di:
- Inviare annunci a **tutto il team** o a **specifici dipartimenti** (es. solo Nutrizionisti).
- Richiedere una **conferma di lettura** individuale per comunicazioni critiche.
- Monitorare le **statistiche di visualizzazione** in tempo reale.

## Chi lo Usa

| Ruolo | Utilizzo |
|-------|----------|
| **Admin / CCO** | Creazione di annunci globali e monitoraggio della "Read Rate" aziendale |
| **Head of Department** | Invio di comunicazioni mirate ai membri del proprio dipartimento |
| **Tutto il personale** | Consultazione bacheca e conferma lettura delle direttive ricevute |

## Flusso Principale (Technical Workflow)

1. **Publishing**: L'autore redige l'annuncio e seleziona i dipartimenti target.
2. **Notification**: Il sistema attiva un badge visivo sulla UI del destinatario.
3. **Engagement**: L'utente apre la comunicazione (`Communication`).
4. **Read Confirmation**: Se richiesto, l'utente preme "Segna come letto", attivando un record `CommunicationReads`.
5. **Monitoring**: L'autore consulta la percentuale di lettura e l'elenco degli utenti in sospeso.
 Industrial 

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

# Notifiche Push (PWA)

Il sistema di **Notifiche Push** (blueprint `push_notifications`) permette alla Suite Clinica di inviare avvisi in tempo reale direttamente sul browser o sul dispositivo mobile del professionista (tramite PWA).

## Cos'è e a cosa serve
Serve a garantire che il team sia costantemente aggiornato sulle attività critiche senza dover ricaricare la pagina. Permette di:
- Ricevere una notifica quando viene **assegnato un nuovo task**.
- Ricevere avvisi amministrativi manuali inviati dalla direzione.
- Gestire un centro notifiche interno (`AppNotification`) per consultare lo storico degli avvisi.

## Chi lo usa
- **Professionisti (Nutrizionisti, Coach, ecc.)**: Per restare aggiornati sui task e sui pazienti.
- **Admin**: Per inviare comunicazioni "flash" urgenti al team.

## Come funziona (flusso tecnico)

### 1. Sottoscrizione Browser
Quando un utente accede alla Suite, il frontend richiede il permesso per le notifiche e invia l'`endpoint` e le chiavi crittografiche (`p256dh`, `auth`) al backend (`/subscriptions`).

### 2. Invio Notifica
- Il backend genera un record `AppNotification` (per lo storico interno).
- Viene inviato il payload crittografato al server di push del browser (Google, Mozilla, ecc.) utilizzando il protocollo **VAPID**.
- Il browser riceve il messaggio e mostra il popup nativo, anche se la tab della Suite è chiusa (se il service worker è attivo).

### 3. Integrazione Task
Ogni volta che viene assegnato un task (blueprint `tasks`), viene invocata la funzione `send_task_assigned_push`, che automatizza l'invio della notifica all'assegnatario.

## Architettura Tecnica

### Componenti Principali
- **Backend Blueprint**: `backend/corposostenibile/blueprints/push_notifications`
- **Libreria**: `pywebpush` per la gestione del protocollo WebPush.
- **Configurazione**: Richiede chiavi `VAPID_PUBLIC_KEY` e `VAPID_PRIVATE_KEY` nel file `.env`.

## API / Endpoint Principali

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/public-key` | GET | Ritorna la chiave pubblica VAPID per il frontend. |
| `/subscriptions` | POST | Registra o aggiorna un dispositivo per le notifiche. |
| `/notifications` | GET | Lista delle notifiche ricevute dall'utente (centro notifiche). |
| `/notifications/<id>/read` | POST | Segna una notifica come letta. |
| `/admin/send` | POST | (Admin) Invia una notifica push manuale a un utente. |

## Modelli di Dati

### `AppNotification`
Lo storico delle notifiche visibili nell'interfaccia utente.
- `title`, `body`, `url`, `is_read`.

### `PushSubscription`
Il link tecnico tra l'utente e il suo browser/dispositivo.
- `endpoint`: URL univoco del client.
- `p256dh`, `auth`: Chiavi per la crittografia.
- `user_agent`: Informazioni sul browser.

## Note & Gotcha
- **HTTPS**: Le notifiche push funzionano esclusivamente in ambienti sicuri (HTTPS).
- **Service Worker**: Richiedono che il Service Worker della PWA sia correttamente installato e attivo nel frontend.
- **Scadenza**: Le sottoscrizioni possono scadere o essere revocate dal browser; il sistema gestisce la pulizia in caso di errore 410 (Gone).

# Appointment Setting

> **Categoria**: `comunicazione`
> **Destinatari**: Appointment Setters, CCO, Admin
> **Stato**: 🟢 Completo
> **Ultimo aggiornamento**: 27/03/2026

---

## Cos'è e a Cosa Serve

Il modulo Appointment Setting è dedicato al monitoraggio analitico delle performance del team di front-end che gestisce il primo contatto con le lead. Permette di misurare l'efficacia del processo di vendita iniziale attraverso l'analisi dei funnel di conversione, dei tempi di risposta e della produttività dei singoli operatori (messaggi inviati, contatti chiusi, conversazioni assegnate).

## Cos'è e a cosa serve
Serve a misurare l'efficacia della comunicazione iniziale e del processo di vendita. Permette di:
- Caricare dati storici di messaggistica ed efficacia (spesso derivanti da esportazioni CSV di Respond.io).
- Analizzare il numero di **messaggi inviati**, **contatti unici chiusi** e **conversazioni assegnate** per ogni operatore.
- Visualizzare il **Funnel di Vendita**: tassi di conversione tra le varie fasi (es. In Target -> Prenotato).
- Calcolare i **tempi medi** di permanenza in una fase e i tassi di abbandono.

## Chi lo usa
- **Appointment Setters**: Per monitorare i propri target e performance.
- **CCO (Chief Clinical Officer)**: Per analizzare la qualità del lead overflow e l'efficienza del team.
- **Admin**: Per caricare i dati mensili e gestire la base dati del funnel.

## Come funziona (flusso utente)
1. L'utente carica i dati mensili tramite l'interfaccia amministrativa (POST API).
2. Il sistema esegue un "upsert": se i dati per l'utente/mese/anno esistono già, li aggiorna; altrimenti ne crea di nuovi.
3. I grafici nella dashboard della Suite Clinica interrogano questi endpoint per mostrare l'andamento del funnel nel tempo.

## Architettura Tecnica

### Componenti Principali
- **Backend Blueprint**: `backend/corposostenibile/blueprints/appointment_setting`
- **Frontend**: Dashboard amministrative e grafici di analytics.
- **Data Ingestion**: Logica di parsing in `api.py` che riceve payload JSON strutturati.

## API / Endpoint Principali

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/api/appointment-setting/messages` | GET | Ritorna le statistiche messaggi mensili. |
| `/api/appointment-setting/messages` | POST | Caricamento massivo statistiche utente/mese. |
| `/api/appointment-setting/contacts` | GET | Ritorna le statistiche contatti giornalieri. |
| `/api/appointment-setting/funnel` | GET | Ritorna i dati aggregati del funnel di vendita. |
| `/api/appointment-setting/funnel` | POST | Salva i breakdown dei tassi di conversione per fase. |

## Modelli di Dati

### `AppointmentSettingMessage`
Statistiche mensili per ogni utente.
- `messaggi_inviati`, `contatti_unici_chiusi`, `conversazioni_assegnate`, `conversazioni_chiuse`.

### `AppointmentSettingContact`
Dettaglio giornaliero dei contatti gestiti.
- `giorno`, `mese`, `anno`.

### `AppointmentSettingFunnel`
Breakdown tecnico delle fasi del lifecycle.
- `fase`: Nome della fase (es. Cold, Under, In Target).
- `tasso_conversione`, `tempo_medio_fase`, `tasso_abbandono`.

## Note & Gotcha
- **Upsert**: Tutte le operazioni di POST sono idempotent (sovrascrivono i record esistenti per la stessa chiave temporale/utente).
- **Relazione con Respond.io**: Sebbene i dati provengano da Respond.io, questo modulo gestisce dati *aggregati* e non i singoli messaggi in real-time (compito del blueprint `respond_io`).

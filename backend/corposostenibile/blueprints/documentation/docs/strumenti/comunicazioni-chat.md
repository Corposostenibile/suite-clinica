# Comunicazioni e Chat

> **Categoria**: `operativo`
> **Destinatari**: Professionisti, Team Leader, Admin
> **Stato**: 🟢 Completo
> **Ultimo aggiornamento**: 27/03/2026

---

## Cos'è e a Cosa Serve

Quest'area comprende gli strumenti di comunicazione interna strutturata e i canali di messaggistica con il paziente. Le **Comunicazioni Interne** servono a distribuire annunci, direttive o avvisi tecnici a dipartimenti specifici con tracciamento della lettura. La **Chat Paziente** è attualmente in fase di placeholder operativo per integrazioni future, garantendo una UI coerente per la conversazione assistita.

---

## Chi lo Usa

| Ruolo | Utilizzo |
|-------|----------|
| **Admin / Head Dipartimento** | Creazione di annunci e monitoraggio della "Read Rate" del team |
| **Professionisti** | Ricezione di comunicazioni di servizio e accesso alla chat paziente |
| **Sviluppatori** | Implementazione del bridge conversazionale (React) |

---

## Flusso Principale (Technical Workflow)

1. **Publishing**: L'autore crea una `Communication` definendo il target (globale o dipartimentale).
2. **Distribution**: Il sistema associa la comunicazione agli utenti target via `communication_departments`.
3. **Engagement**: L'utente visualizza l'annuncio e attiva il trigger `mark-read`.
4. **Audit**: L'amministratore consulta le statistiche di lettura (`unread-users`).
5. **Chat Interface**: Reindirizzamento dell'utente all'area React placeholder per future interazioni.

---

## Architettura Tecnica

### Componenti coinvolti

| Layer | File / Modulo | Ruolo |
|-------|--------------|-------|
| Backend | `blueprints/communications/` | Logic comunicazioni e tracciamento |
| Legacy | `templates/communications/` | UI Jinja per annunci interni |
| React | `src/pages/chat/Chat.jsx` | UI React placeholder per chat |

```mermaid
flowchart TD
    Author[Admin o Head] --> CommUI[UI Comunicazioni]
    CommUI --> CommRoutes[/communications/*]
    CommRoutes --> CommDB[(communications + reads)]
    Reader[Collaboratore] --> CommUI
    Reader --> MarkRead[/communications/:id/mark-read]
    Reader --> ChatPage[/chat placeholder]
```

---

## Endpoint API Principali

### API comunicazioni

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/communications/api/<id>/stats` | Statistiche lettura |
| `GET` | `/communications/api/<id>/unread-users` | Utenti che non hanno letto |

---

## Modelli di Dati Principali

---

## Variabili d'Ambiente Rilevanti

| Variabile | Descrizione | Obbligatoria |
|---|---|---|
| `MAIL_*` | Invio email notifiche legate alle comunicazioni | Dipende deployment |

---

## Permessi e Ruoli (RBAC)

| Funzionalità | Admin | Head dipartimento | Collaboratore |
|---|---|---|---|
| Crea comunicazione | ✅ | ✅ (scope dip.) | ❌ |
| Legge comunicazioni ricevute | ✅ | ✅ | ✅ |
| Vede statistiche complete | ✅ | ✅ autore/ambito | ❌ |

---

## Note Operative e Casi Limite

---

## Documenti Correlati

- [Area 05 comunicazione e integrazioni](../comunicazione/README.md)
- [Task e calendario](./task-calendario.md)

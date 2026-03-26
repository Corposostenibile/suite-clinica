# Comunicazioni e Chat

> **Categoria**: operatività  
> **Destinatari**: Professionisti, Team Leader, Admin  
> **Stato**: 🟡 Bozza avanzata  
> **Ultimo aggiornamento**: Marzo 2026

---

## Cos'è e a cosa serve

Quest'area copre gli strumenti operativi di comunicazione interna e la parte chat in prodotto:

- **Comunicazioni interne**: annunci strutturati per dipartimenti, con tracking lettura.
- **Chat operativa**: area UI prevista per conversazione con pazienti (attualmente in modalità "prossimamente").

Serve a distribuire informazioni interne in modo tracciabile e preparare il canale conversazionale paziente-team.

---

## Chi lo usa

| Ruolo | Come interagisce |
|---|---|
| Admin | Crea comunicazioni globali e monitora letture |
| Head di dipartimento | Crea comunicazioni target per il proprio dipartimento |
| Collaboratori | Leggono comunicazioni ricevute e confermano lettura |

---

## Flusso principale

```
1. Admin/Head crea una comunicazione
2. Seleziona dipartimenti destinatari (o invio globale)
3. Il sistema pubblica la comunicazione e notifica i destinatari
4. Gli utenti leggono e marcano come letta
5. Autore/Admin consulta le statistiche di lettura
```

Per la chat paziente:
```
1. Utente apre /chat
2. Visualizza schermata informativa "Prossimamente"
3. Nessuna persistenza messaggi attiva in questa release
```

---

## Architettura tecnica

| Layer | File / Modulo | Ruolo |
|---|---|---|
| Backend | `backend/corposostenibile/blueprints/communications/` | Gestione comunicazioni interne |
| Frontend (legacy/Jinja) | `communications/templates/communications/*.html` | UI comunicazioni |
| Frontend React | `corposostenibile-clinica/src/pages/chat/Chat.jsx` | Placeholder chat paziente |
| Permessi | `communications/permissions.py` | Scope accesso comunicazioni |

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

## Endpoint principali

### Comunicazioni (HTML + action)

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/communications/` | Lista comunicazioni ricevute |
| `GET` | `/communications/sent` | Lista comunicazioni inviate |
| `GET/POST` | `/communications/create` | Creazione comunicazione |
| `GET` | `/communications/<id>` | Dettaglio comunicazione |
| `POST` | `/communications/<id>/mark-read` | Conferma lettura |
| `POST` | `/communications/<id>/delete` | Eliminazione (permessi dedicati) |

### API comunicazioni

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/communications/api/<id>/stats` | Statistiche lettura |
| `GET` | `/communications/api/<id>/unread-users` | Utenti che non hanno letto |

---

## Modelli dati principali

- `Communication`
  - titolo, contenuto, autore, target globale o per dipartimenti
- `communication_reads` (join)
  - tracking lettura per utente
- `communication_departments` (join)
  - targeting dipartimentale

---

## Variabili ambiente

| Variabile | Descrizione | Obbligatoria |
|---|---|---|
| `MAIL_*` | Invio email notifiche legate alle comunicazioni | Dipende deployment |

---

## RBAC (sintesi)

| Funzionalità | Admin | Head dipartimento | Collaboratore |
|---|---|---|---|
| Crea comunicazione | ✅ | ✅ (scope dip.) | ❌ |
| Legge comunicazioni ricevute | ✅ | ✅ | ✅ |
| Vede statistiche complete | ✅ | ✅ autore/ambito | ❌ |

---

## Note e gotcha

- La chat React (`/chat`) al momento è intenzionalmente non attiva lato messaggistica.
- Le comunicazioni interne usano ancora una UI server-rendered (Jinja), non la stessa UX React delle pagine clienti.
- Per il tracciamento letture la coerenza permessi è centrale: evitare bypass lato template.

---

## Documenti correlati

- [Area 05 comunicazione e integrazioni](../05-comunicazione/README.md)
- [Task e calendario](./task-calendario.md)

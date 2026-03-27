# Ricerca Globale

> **Categoria**: `operativo`
> **Destinatari**: Professionisti, Team Leader, Admin
> **Stato**: 🟢 Completo
> **Ultimo aggiornamento**: 27/03/2026

---

## Cos'è e a Cosa Serve

La Ricerca Globale è lo strumento di navigazione rapida della Suite. Consente di trovare istantaneamente informazioni distribuite in moduli diversi (Pazienti, Check, Professionisti, Formazione) inserendo una query testuale unica. Il backend aggrega i risultati applicando filtri RBAC in tempo reale per garantire la privacy dei dati.

---

## Chi lo Usa

| Ruolo | Utilizzo |
|-------|----------|
| **Professionisti** | Ricerca rapida di pazienti e dei relativi check o training assegnati |
| **Team Leader** | Ricerca estesa ai membri del proprio team e alle loro attività |
| **Admin** | Ricerca trasversale su tutta l'anagrafica e la cronologia operativa |

---

## Flusso Principale (Technical Workflow)

1. **Query Entry**: L'utente inserisce almeno 2 caratteri nella barra di ricerca.
2. **Aggregated Fetch**: Il frontend chiama l'API globale passandogli query e categoria opzionale.
3. **RBAC Scoping**: Il backend filtra le query SQLAlchemy in base ai permessi dell'utente loggato.
4. **Serialization**: I risultati vengono raggruppati per categoria con conteggi e link diretti.
5. **Navigation**: L'utente seleziona il risultato e viene reindirizzato alla pagina di dettaglio.

---

## Architettura Tecnica

### Componenti coinvolti

| Layer | Componente | Ruolo |
|-------|------------|-------|
| Frontend | `GlobalSearchPage.jsx` | UI di ricerca e rendering risultati |
| Backend | `search_bp` | Centralina di ricerca cross-modulo |
| Data | `search/routes.py` | Query SQLAlchemy su Cliente, User, Review |

```mermaid
flowchart TD
    User[Utente] --> SearchPage[GlobalSearchPage]
    SearchPage --> SearchApi[/api/search/global]
    SearchApi --> Pazienti[(Cliente)]
    SearchApi --> Checks[(WeeklyCheckResponse)]
    SearchApi --> Users[(User)]
    SearchApi --> Trainings[(Review + ReviewMessage)]
```

---

## Endpoint API Principali

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/search/global` | Ricerca cross-modulo |

### Query Parametri

| Parametro | Tipo | Note |
|---|---|---|
| `q` | string | Query ricerca (min 2 char) |
| `category` | string | `paziente`, `check`, `professional`, `training` |
| `page` | int | Pagina risultati |
| `per_page` | int | Numero risultati per pagina |

---

## Permessi e Ruoli (RBAC)

| Ruolo | Scope ricerca |
|---|---|
| **Admin** | Nessun filtro aggiuntivo |
| **Team Leader** | Solo entità nel perimetro del proprio team |
| **Professionista** | Solo entità collegate ai propri clienti/attività |

---

## Note Operative e Casi Limite

- Query con meno di 2 caratteri tornano risultato vuoto (comportamento intenzionale).
- Le categorie non hanno lo stesso costo query: `training` e `check` possono essere più pesanti.
- I link risultato dipendono dalla struttura route frontend (es. `/clienti-dettaglio/:id`, `/formazione?...`).
- Quando si aggiungono nuove entità ricercabili, aggiornare `counts`, serializer risultato e mapping categoria.

---

## Documenti Correlati

- [Gestione clienti](../03-clienti-core/gestione-clienti.md)
- [Check periodici](../03-clienti-core/check-periodici.md)
- [Task e calendario](./task-calendario.md)

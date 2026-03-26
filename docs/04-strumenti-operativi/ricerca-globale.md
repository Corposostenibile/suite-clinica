# Ricerca Globale

> **Categoria**: operatività  
> **Destinatari**: Professionisti, Team Leader, Admin  
> **Stato**: 🟡 Bozza avanzata  
> **Ultimo aggiornamento**: Marzo 2026

---

## Cos'è e a cosa serve

La Ricerca Globale consente di trovare rapidamente informazioni distribuite in più aree della suite da un unico punto.

La ricerca aggrega risultati su categorie diverse:

- pazienti
- check
- professionisti
- training/formazione

Riduce il tempo di navigazione tra moduli e migliora la produttività operativa.

---

## Chi lo usa

| Ruolo | Come interagisce |
|---|---|
| Professionista | Ricerca pazienti, check e training nel proprio perimetro |
| Team Leader | Ricerca estesa al proprio team |
| Admin | Ricerca trasversale completa |

---

## Flusso principale

```
1. L'utente apre la pagina Ricerca Globale
2. Inserisce query (minimo 2 caratteri)
3. Il frontend chiama endpoint search globale
4. Il backend applica scope RBAC
5. I risultati sono restituiti per categoria con count e paginazione
6. L'utente apre il dettaglio dal link suggerito
```

---

## Architettura tecnica

| Layer | File / Modulo | Ruolo |
|---|---|---|
| Frontend | `corposostenibile-clinica/src/pages/GlobalSearchPage.jsx` | Interfaccia ricerca |
| Backend | `backend/corposostenibile/blueprints/search/routes.py` | Endpoint search aggregato |
| App init | `backend/corposostenibile/__init__.py` | Registrazione prefix API |
| DB | `Cliente`, `WeeklyCheckResponse`, `User`, `Review`, `ReviewMessage` | Sorgenti risultati |

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

## Endpoint principali

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/search/global` | Ricerca cross-modulo |

### Query params

| Parametro | Tipo | Note |
|---|---|---|
| `q` | string | Query ricerca (min 2 char) |
| `category` | string | `paziente`, `check`, `professional`, `training` |
| `page` | int | Pagina risultati |
| `per_page` | int | Numero risultati per pagina |

Risposta:
- `results[]`
- `counts` per categoria
- `pagination`

---

## RBAC e visibilità

| Ruolo | Scope ricerca |
|---|---|
| Admin | Nessun filtro aggiuntivo |
| Team Leader | Solo entità nel perimetro del proprio team |
| Professionista | Solo entità collegate ai propri clienti/attività |

Il backend applica il filtro direttamente nella query SQLAlchemy per ogni categoria risultato.

---

## Variabili ambiente

| Variabile | Descrizione | Obbligatoria |
|---|---|---|
| N/A | Nessuna variabile specifica dedicata al modulo search | N/A |

---

## Note e gotcha

- Query con meno di 2 caratteri tornano risultato vuoto (comportamento intenzionale).
- Le categorie non hanno lo stesso costo query: `training` e `check` possono essere più pesanti.
- I link risultato dipendono dalla struttura route frontend (es. `/clienti-dettaglio/:id`, `/formazione?...`).
- Quando si aggiungono nuove entità ricercabili, aggiornare `counts`, serializer risultato e mapping categoria.

---

## Documenti correlati

- [Gestione clienti](../03-clienti-core/gestione-clienti.md)
- [Check periodici](../03-clienti-core/check-periodici.md)
- [Task e calendario](./task-calendario.md)

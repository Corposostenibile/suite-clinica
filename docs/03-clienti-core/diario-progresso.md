# Diario e Progresso Cliente

> **Categoria**: clienti  
> **Destinatari**: Sviluppatori, Professionisti, Team Leader  
> **Stato**: 🟡 Bozza avanzata  
> **Ultimo aggiornamento**: Marzo 2026

---

## Cos'è e a cosa serve

L'area Diario e Progresso raccoglie due funzionalità complementari:

- **Diario clinico per servizio** (nutrizione, coaching, psicologia): note operative datate, modificabili e storicizzate.
- **Progresso paziente**: grafici, trend e confronto fotografico "prima/dopo" basati sui check periodici.

L'obiettivo è dare ai professionisti una lettura rapida dell'evoluzione del paziente, senza perdere il contesto storico.

---

## Chi lo usa

| Ruolo | Come interagisce |
|---|---|
| Professionista | Inserisce note diario e interpreta i trend progresso |
| Team Leader | Supervisione dei percorsi del proprio team |
| Admin/CCO | Controllo trasversale e supporto operativo |

---

## Flusso principale

```
1. L'utente apre la scheda paziente
2. Usa il diario nel tab di servizio (Nutrizione/Coaching/Psicologia)
3. Aggiunge note contestualizzate per data
4. Passa al tab Progresso
5. Analizza grafici parametri + confronto foto prima/dopo
6. Usa le evidenze per adattare piano e comunicazione col paziente
```

---

## Architettura tecnica

### Componenti coinvolti

| Layer | File / Modulo | Ruolo |
|---|---|---|
| Frontend | `corposostenibile-clinica/src/pages/clienti/DiarioModal.jsx` | Modal diario riusabile per le liste |
| Frontend | `corposostenibile-clinica/src/pages/clienti/ClientiDetail.jsx` | Diario e progresso nella scheda paziente |
| Frontend | `corposostenibile-clinica/src/pages/clienti/ProgressoTab.jsx` | Grafici e confronto foto |
| Service | `corposostenibile-clinica/src/services/clientiService.js` | API diary/anamnesi/metrics |
| Backend | `backend/corposostenibile/blueprints/customers/routes.py` | Endpoints diario + aggregazione dati progresso |

### Flusso dati

```mermaid
flowchart TD
    User[Professionista] --> DiarioUI[DiarioModal o tab Diario]
    User --> ProgressoUI[ProgressoTab]
    DiarioUI --> DiaryApi[/api/v1/customers/:id/diary/:serviceType]
    ProgressoUI --> MetricsApi[/api/v1/customers/:id/feedback-metrics]
    ProgressoUI --> ChecksApi[/api/v1/customers/:id/weekly-checks-metrics]
    DiaryApi --> DiaryTable[(service_diary_entries)]
    MetricsApi --> WeeklyChecks[(weekly_check_responses)]
    MetricsApi --> DcaChecks[(dca_check_responses)]
```

---

## Endpoint principali

### Diario per servizio

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/v1/customers/<id>/diary/<service_type>` | Legge le note diario |
| `POST` | `/api/v1/customers/<id>/diary/<service_type>` | Crea nuova nota |
| `PUT` | `/api/v1/customers/<id>/diary/<service_type>/<entry_id>` | Aggiorna nota |
| `DELETE` | `/api/v1/customers/<id>/diary/<service_type>/<entry_id>` | Elimina nota |
| `GET` | `/api/v1/customers/<id>/diary/<service_type>/<entry_id>/history` | Storico voce |

`service_type` valido: `nutrizione`, `coaching`, `psicologia`.

### Progresso

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/v1/customers/<id>/feedback-metrics` | KPI e segnali sintetici |
| `GET` | `/api/v1/customers/<id>/weekly-checks-metrics` | Metriche derivate dai check |

---

## Modelli dati principali

- `ServiceDiaryEntry`
  - `cliente_id`, `service_type`, `entry_date`, `content`, `author_user_id`
- `WeeklyCheckResponse`
  - rating benessere, peso, foto front/side/back, feedback professionisti
- `DCACheckResponse`
  - metriche dedicate area psicologica/DCA
- `TypeFormResponse` (fallback foto iniziali in alcune viste confronto)

---

## Variabili d'ambiente rilevanti

| Variabile | Descrizione | Obbligatoria |
|---|---|---|
| `BASE_URL` | Coerenza URL frontend/backend per chiamate API | Sì |
| `VITE_BACKEND_URL` | Endpoint backend usato dalla SPA in dev | Sì (dev) |

---

## Permessi e ruoli (RBAC)

| Funzionalità | Admin/CCO | Team Leader | Professionista |
|---|---|---|---|
| Leggere diario cliente | ✅ | ✅ nel proprio scope | ✅ nel proprio scope |
| Scrivere diario cliente | ✅ | ✅ nel proprio scope | ✅ nel proprio scope |
| Eliminare voce diario | ✅ | ⚠️ dipende policy | ❌ default |
| Visualizzare progresso | ✅ | ✅ nel proprio scope | ✅ nel proprio scope |

---

## Note e gotcha

- Errore comune: usare `serviceType="coach"` nel modal diario. Il valore corretto API è `coaching`.
- Il modal diario usa `createPortal(..., document.body)`: senza container valido React lancia `Target container is not a DOM element`.
- La resa grafica progresso dipende dalla qualità/storicità dei check: con pochi dati alcuni grafici risultano vuoti.
- Il confronto "Prima & Dopo" usa la prima immagine disponibile (incluso fallback typeform) e l'ultima immagine valida.

---

## Documenti correlati

- [Check periodici](./check-periodici.md)
- [Gestione clienti](./gestione-clienti.md)
- [Modulo nutrizione](./modulo-nutrizione.md)

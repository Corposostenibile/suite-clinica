# Suite Clinica Corposostenibile

Piattaforma gestionale interna per supportare l'intero ciclo di vita del paziente: dall'acquisizione al follow-up clinico, con moduli per nutrizione, coaching, psicologia, comunicazione e operations.

---

## Struttura del monorepo

```
suite-clinica/
├── backend/                        # Flask API (Python 3.11+)
│   └── corposostenibile/
│       ├── blueprints/             # Moduli funzionali (~44 blueprint)
│       └── __init__.py             # App factory
├── corposostenibile-clinica/       # Frontend principale (React 19 + Vite)
├── corposostenibile-amministrativa/ # Pannello admin (React + Vite)
├── teams-kanban/                   # Kanban SPA per MS Teams (React + Vite)
├── videocall-service/              # Servizio videochiamate
├── docs/                           # Documentazione centralizzata
├── k8s/                            # Configurazioni Kubernetes
├── scripts/                        # Script di utilità
├── dev.sh                          # Script setup ambiente locale
└── cloudbuild.yaml                 # Pipeline CI/CD GCP
```

---

## Setup locale

### Prerequisiti

- Python 3.11+ con [Poetry](https://python-poetry.org/)
- Node.js 18+
- PostgreSQL + Redis attivi

### Avvio

```bash
# Avvia backend + frontend per il proprio utente (manu | samu | matte)
./dev.sh fullstack samu

# Solo frontend
./dev.sh frontend samu

# Solo backend in modalità debug
./dev.sh debug samu
```

Le porte sono assegnate per sviluppatore:

| Dev   | Backend | Frontend |
|-------|---------|----------|
| manu  | 5001    | 3001     |
| samu  | 5002    | 3002     |
| matte | 5003    | 3003     |

Il database PostgreSQL è condiviso sulla porta `5432`.

### Backend (standalone)

```bash
cd backend
poetry install
poetry run flask run --port 5002
```

### Frontend (standalone)

```bash
cd corposostenibile-clinica
npm install
npm run dev
```

---

## Architettura

```
Utenti (browser)
      │
      ▼
React SPA (corposostenibile-clinica)
      │  chiamate API
      ▼
Flask Backend (/api/...)
      │
      ├── PostgreSQL   (dati applicativi + Continuum versioning)
      ├── Redis        (Celery broker + cache)
      └── Celery       (task asincroni: email, webhook, sync)
```

Il backend Flask serve anche:
- la React SPA tramite catch-all route (`GET /<path>`)
- la Kanban SPA su `/teams-kanban/`
- form pubblici su `/sales-form/`, `/recruiting/`, `/public/ticket/`
- webhook da sistemi esterni (GoHighLevel, Respond.io, Typeform, Frame.io, MS Teams)

**Stack principale:**
- Backend: Flask 3.0, SQLAlchemy, Flask-Login, Flask-Migrate, Celery
- Frontend: React 19, React Router 7, Axios, Recharts, Vite
- AI: LangChain 0.3, Anthropic SDK, Qdrant (ricerca vettoriale)
- Infrastruttura: GCP Cloud Run, Cloud SQL (PostgreSQL), Cloud Build CI/CD

---

## Blueprint attivi (usati dal frontend)

| Blueprint | Prefix | Funzione |
|---|---|---|
| `auth` | `/auth` | Login, logout, reset password, impersonation |
| `customers` | `/api/v1/customers` | Scheda paziente, anamnesi, diario, nutrizione, trustpilot |
| `team` | `/team` | Membri, team, capacità, assegnazioni, utenti trial |
| `calendar` | `/calendar` | Calendario eventi Google, sincronizzazione |
| `client_checks` | `/api/client-checks` | Check settimanali, dashboard, check pubblici |
| `tasks` | `/api/tasks` | Gestione task interni |
| `review` | `/review/api` | Formazione, richieste, admin |
| `quality` | `/quality/api` | Quality score, KPI settimanali, trimestrale |
| `postit` | `/postit/api` | Post-it personali |
| `news` | `/api/news` | Feed notizie interne |
| `search` | `/api/search` | Ricerca globale |
| `loom` | `/loom/api` | Registrazioni video Loom |
| `push_notifications` | `/api/push` | Notifiche push PWA |
| `team_tickets` | `/api/team-tickets` | Ticket del team |
| `ghl_integration` | `/ghl` | Configurazione e dati GoHighLevel |
| `old_suite` | `/old-suite/api` | Import lead dalla vecchia suite |
| `pwa` | `/` | PWA manifest, service worker, icone |
| `documentation` | `/documentation` | Documentazione MkDocs |

**Blueprint con route pubbliche esterne (non eliminabili):**
- `sales_form` — form vendita (`/sales-form/welcome-form/<code>`)
- `recruiting` — candidature (`/recruiting/apply/<link_code>`)
- `ticket` (public) — ticket pubblici (`/public/ticket/new`)

**Webhook da sistemi esterni (non eliminabili):**
- GoHighLevel, Respond.io, Typeform, Frame.io, MS Teams Bot

---

## Ambienti

| Ambiente | URL | Note |
|---|---|---|
| Locale (VPS) | Configurato via DuckDNS | Vedi [duckdns_local_dev_vps.md](docs/01-infrastruttura/duckdns_local_dev_vps.md) |
| Produzione | `http://34.154.33.164/` (GCP) | Cloud Run + Cloud SQL |

La pipeline CI/CD è documentata in [ci_cd_analysis.md](docs/01-infrastruttura/ci_cd_analysis.md).

---

## Documentazione

La documentazione completa è in [`docs/`](docs/README.md), organizzata per area:

| Sezione | Contenuto |
|---|---|
| [00 — Panoramica](docs/00-panoramica/overview.md) | Architettura generale, macro aree |
| [01 — Infrastruttura](docs/01-infrastruttura/) | CI/CD, GCP, VPS, migrazione |
| [02 — Team e organizzazione](docs/02-team-organizzazione/) | Auth, RBAC, professionisti, KPI |
| [03 — Clienti core](docs/03-clienti-core/) | Scheda paziente, check, nutrizione, diario |
| [04 — Strumenti operativi](docs/04-strumenti-operativi/) | Task, calendario, ticket, quality score |
| [05 — Comunicazione e integrazioni](docs/05-comunicazione/) | Respond.io, GHL, SuiteMind AI, Trustpilot |
| [06 — Sviluppo e varie](docs/06-sviluppo-e-varie/) | Refactor, stato tecnico |
| [07 — Guide ruoli](docs/07-guide-ruoli/) | Manuali operativi per ogni ruolo |

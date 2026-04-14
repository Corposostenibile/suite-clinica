# Documentazione Permessi - Sistema Guida

> **File**: `DOCUMENTATION_PERMISSIONS.md`
> **Blueprint**: `documentation`
> **Ultimo aggiornamento**: 14/04/2026

---

## Riepilogo Rapido

| Simbolo | Significato |
|---------|-------------|
| 🟢 | Accesso libero |
| 🟡 | Accesso condizionato |
| 🔴 | Accesso negato |
| 🔒 | Solo Admin/CCO |

---

## Tabella Permessi per Sezione

### Getting Started

| Documento | Admin/CCO | Team Leader | Professionista | Note |
|-----------|-----------|-------------|----------------|------|
| index.md (Benvenuto) | 🟢 | 🟢 | 🟢 | Tutti autenticati |
| panoramica/overview.md | 🟢 | 🟢 | 🟢 | |
| panoramica/template-documento.md | 🟢 | 🟢 | 🟢 | |

### Area Clinica — Pazienti

| Documento | Admin/CCO | TL Nutrizione | TL Coaching | TL Psicologia | Professionista |
|-----------|-----------|---------------|-------------|---------------|----------------|
| lista_team_leader | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 |
| lista_team_leader_nutrizione | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 |
| lista_team_leader_coaching | 🟢 | 🔴 | 🟡 | 🔴 | 🔴 |
| lista_team_leader_psicologia | 🟢 | 🔴 | 🔴 | 🟡 | 🔴 |
| lista_professionista | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |
| lista_professionista_nutrizione | 🟢 | 🟢 | 🔴 | 🔴 | 🟡 |
| lista_professionista_coaching | 🟢 | 🔴 | 🟢 | 🔴 | 🟡 |
| lista_professionista_psicologia | 🟢 | 🔴 | 🔴 | 🟢 | 🟡 |

> **Logica**: `_team_leader` → richiede ruolo team_leader; `_nutrizione/_coaching/_psicologia` → richiede specialty corrispondente

### Area Clinica — Scheda Dettaglio

| Documento | Admin/CCO | TL Nutrizione | TL Coaching | TL Psicologia | Professionista |
|-----------|-----------|---------------|-------------|---------------|----------------|
| dettaglio_team_leader | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 |
| dettaglio_team_leader_nutrizione | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 |
| dettaglio_team_leader_coaching | 🟢 | 🔴 | 🟡 | 🔴 | 🔴 |
| dettaglio_team_leader_psicologia | 🟢 | 🔴 | 🔴 | 🟡 | 🔴 |
| dettaglio_professionista | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |
| dettaglio_professionista_nutrizione | 🟢 | 🟢 | 🔴 | 🔴 | 🟡 |
| dettaglio_professionista_coaching | 🟢 | 🔴 | 🟢 | 🔴 | 🟡 |
| dettaglio_professionista_psicologia | 🟢 | 🔴 | 🔴 | 🟢 | 🟡 |

### Area Clinica — Task

| Documento | Admin/CCO | TL Nutrizione | TL Coaching | TL Psicologia | Professionista |
|-----------|-----------|---------------|-------------|---------------|----------------|
| task_team_leader | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 |
| task_team_leader_nutrizione | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 |
| task_team_leader_coaching | 🟢 | 🔴 | 🟡 | 🔴 | 🔴 |
| task_team_leader_psicologia | 🟢 | 🔴 | 🔴 | 🟡 | 🔴 |
| task_professionista | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |
| task_professionista_nutrizione | 🟢 | 🟢 | 🔴 | 🔴 | 🟡 |
| task_professionista_coaching | 🟢 | 🔴 | 🟢 | 🔴 | 🟡 |
| task_professionista_psicologia | 🟢 | 🔴 | 🔴 | 🟢 | 🟡 |

### Area Clinica — Formazione

| Documento | Admin/CCO | TL Nutrizione | TL Coaching | TL Psicologia | Professionista |
|-----------|-----------|---------------|-------------|---------------|----------------|
| formazione_team_leader | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 |
| formazione_team_leader_nutrizione | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 |
| formazione_team_leader_coaching | 🟢 | 🔴 | 🟡 | 🔴 | 🔴 |
| formazione_team_leader_psicologia | 🟢 | 🔴 | 🔴 | 🟡 | 🔴 |
| formazione_professionista | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |
| formazione_professionista_nutrizione | 🟢 | 🟢 | 🔴 | 🔴 | 🟡 |
| formazione_professionista_coaching | 🟢 | 🔴 | 🟢 | 🔴 | 🟡 |
| formazione_professionista_psicologia | 🟢 | 🔴 | 🔴 | 🟢 | 🟡 |

### Area Clinica — Check Azienda

| Documento | Admin/CCO | TL Nutrizione | TL Coaching | TL Psicologia | Professionista |
|-----------|-----------|---------------|-------------|---------------|----------------|
| check_azienda_team_leader | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 |
| check_azienda_team_leader_nutrizione | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 |
| check_azienda_team_leader_coaching | 🟢 | 🔴 | 🟡 | 🔴 | 🔴 |
| check_azienda_team_leader_psicologia | 🟢 | 🔴 | 🔴 | 🟡 | 🔴 |
| check_azienda_professionista | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |
| check_azienda_professionista_nutrizione | 🟢 | 🟢 | 🔴 | 🔴 | 🟡 |
| check_azienda_professionista_coaching | 🟢 | 🔴 | 🟢 | 🔴 | 🟡 |
| check_azienda_professionista_psicologia | 🟢 | 🔴 | 🔴 | 🟢 | 🟡 |

### Area Clinica — Altro

| Documento | Admin/CCO | Team Leader | Professionista | Note |
|-----------|-----------|-------------|----------------|------|
| check-periodici.md | 🟢 | 🟢 | 🟢 | |
| diario-progresso.md | 🟢 | 🟢 | 🟢 | |
| modulo-nutrizione.md | 🟢 | 🟢 | 🟢 | Contenuto per specialisti |
| piano_medico_nutrizione.md | 🟢 | 🟢 | 🟢 | Contenuto per specialisti |
| test_medico_passo_passo.md | 🟢 | 🟢 | 🟢 | Guida test/QA |

### Strumenti

| Documento | Admin/CCO | Team Leader | Professionista | Note |
|-----------|-----------|-------------|----------------|------|
| task-calendario.md | 🟢 | 🟢 | 🟢 | |
| comunicazioni-chat.md | 🟢 | 🟢 | 🟢 | |
| ticket-supporto.md | 🟢 | 🟢 | 🟢 | |
| ricerca-globale.md | 🟢 | 🟢 | 🟢 | |
| quality-score.md | 🟢 | 🟢 | 🔴 | Solo TL + Admin |

### Comunicazione

| Documento | Admin/CCO | Team Leader | Professionista | Note |
|-----------|-----------|-------------|----------------|------|
| comunicazione-interna.md | 🟢 | 🟢 | 🟢 | |
| notifiche-push.md | 🟢 | 🟢 | 🟢 | |
| appointment-setting.md | 🟢 | 🟢 | 🟢 | Contenuto per Setter |
| integrazione-respond-io.md | 🟢 | 🟢 | 🟢 | Contenuto per Sales |
| integrazione-gohighlevel-webhook.md | 🟢 | 🟢 | 🟢 | Contenuto per Dev |
| suitemind-ai-sop-chatbot.md | 🟢 | 🟢 | 🟢 | Contenuto per Dev/TL |
| trustpilot-review-automation.md | 🟢 | 🟢 | 🟢 | Contenuto per Marketing |

> **Nota**: comunicazione ha accesso generico. Controlli granulari a livello applicativo (es. appointment-setting visibile solo a setter nella UI)

### Guide per Ruolo

| Documento | Admin/CCO | Team Leader | Coach | Nutrizionista | Psicologo | Health Manager | Professionista |
|-----------|-----------|-------------|-------|---------------|-----------|----------------|----------------|
| guida-team-leader | 🟢 | 🟡 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 |
| guida-coach | 🟢 | 🔴 | 🟡 | 🔴 | 🔴 | 🔴 | 🔴 |
| guida-nutrizionista | 🟢 | 🔴 | 🔴 | 🟡 | 🔴 | 🔴 | 🔴 |
| guida-psicologo | 🟢 | 🔴 | 🔴 | 🔴 | 🟡 | 🔴 | 🔴 |
| guida-health-manager | 🟢 | 🔴 | 🔴 | 🔴 | 🔴 | 🟡 | 🔴 |

> **Logica**: ognuno vede solo la guida del proprio ruolo/specialty

### Amministrazione e IT 🔒

| Documento | Admin/CCO | Team Leader | Professionista | Note |
|-----------|-----------|-------------|----------------|------|
| **Organizzazione** | | | | |
| autenticazione.md | 🔒 | 🔴 | 🔴 | |
| team-professionisti.md | 🔒 | 🔴 | 🔴 | |
| kpi-performance.md | 🔒 | 🔴 | 🔴 | |
| **Infrastruttura** | | | | |
| ci_cd_analysis.md | 🔒 | 🔴 | 🔴 | |
| gcp_infrastructure_setup_report.md | 🔒 | 🔴 | 🔴 | |
| infrastructure_compliance_report.md | 🔒 | 🔴 | 🔴 | |
| rapporto_infrastruttura_2026.md | 🔒 | 🔴 | 🔴 | |
| procedura_migrazione.md | 🔒 | 🔴 | 🔴 | |
| duckdns_local_dev_vps.md | 🔒 | 🔴 | 🔴 | |
| **Sviluppo** | | | | |
| refactor_status_report.md | 🔒 | 🔴 | 🔴 | |
| refining_refactor_plan.md | 🔒 | 🔴 | 🔴 | |
| report-completamento-documentazione.md | 🔒 | 🔴 | 🔴 | |
| **Sistema** | | | | |
| SYSTEM_DOCUMENTATION.md | 🔒 | 🔴 | 🔴 | |

---

## Schema Logica Permessi

```
check_path_permission(path):
  │
  ├─ 1. Non autenticato? → ❌ 403
  ├─ 2. Admin/CCO? → ✅ Accesso completo
  ├─ 3. Prima sezione in ADMIN_ONLY? → ❌ 403
  ├─ 4. guide-ruoli? → _check_guide_ruoli_access()
  ├─ 5. team? → Solo TL (non professionisti)
  ├─ 6. strumenti/quality-score? → Solo TL
  ├─ 7. comunicazione? → ✅ Tutti (controlli granulari separati)
  ├─ 8. {pazienti, professionisti, azienda}?
  │     ├─ 'team_leader' nel path? → Check ruolo
  │     └─ Specialty nel slug? → Check specialty
  └─ 9. Altro (panoramica, clienti-core) → ✅ Tutti
```

## Variabili Configurazione

```python
# __init__.py - Costanti principali
ALLOWED_SPECIALTY_KEYS = {'nutrizione', 'coaching', 'psicologia'}
ADMIN_ONLY_SECTIONS = {'infrastruttura', 'sviluppo', 'SYSTEM_DOCUMENTATION'}
ADMIN_AND_TL_SECTIONS = {'team', 'strumenti', 'comunicazione'}
```

## Frontend - Filtri Sidebar

| Sezione Sidebar | Filtro |
|-----------------|--------|
| Generale | Nessuno (tutti) |
| Area Clinica | Variante ruolo/specialty |
| Strumenti | Nessuno (tutti) |
| Comunicazione | Nessuno (tutti) |
| Guide per Ruolo | Solo propria guida |
| Amministrazione e IT | `adminOnly: true` → nascosto a non-admin |

---

## Note

- I permessi sono gestiti sia **backend** (`check_path_permission`) sia **frontend** (filtro sidebar API)
- I file statici sono serviti da `/documentation/static/<path>` con controllo permessi
- La navigazione è restituita da `/api/documentation/nav` con filtri già applicati
- Dopo modifiche ai sorgenti (.md), eseguire `mkdocs build` per rigenerare static

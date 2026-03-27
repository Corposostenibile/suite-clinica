# Documentazione — Suite Clinica Corposostenibile

Questa cartella contiene la documentazione centralizzata della Suite Clinica.

Obiettivo: mantenere una documentazione utile sia al team tecnico sia ai ruoli operativi, con struttura stabile e aggiornabile nel tempo.

## Convenzioni struttura (decisione attuale)

- Le aree restano organizzate con prefisso numerico (`00-`, `01-`, ...).
- L'area `05-comunicazione` viene mantenuta come **contenitore di comunicazione + integrazioni esterne**.
- Ogni nuovo file usa naming in `kebab-case.md`.
- Documento guida di stile: [template-documento.md](./00-panoramica/template-documento.md).

## Indice principale

### 00 — Panoramica
- [Panoramica generale](./00-panoramica/overview.md)
- [Template documento standard](./00-panoramica/template-documento.md)

### 01 — Infrastruttura
- [Analisi CI/CD](./01-infrastruttura/ci_cd_analysis.md)
- [Setup infrastruttura GCP](./01-infrastruttura/gcp_infrastructure_setup_report.md)
- [Compliance infrastruttura](./01-infrastruttura/infrastructure_compliance_report.md)
- [Rapporto infrastruttura 2026](./01-infrastruttura/rapporto_infrastruttura_2026.md)
- [Procedura migrazione](./01-infrastruttura/procedura_migrazione.md)
- [DuckDNS local dev VPS](./01-infrastruttura/duckdns_local_dev_vps.md)

### 02 — Team e organizzazione
- [Autenticazione](./02-team-organizzazione/autenticazione.md)
- [Team e professionisti](./02-team-organizzazione/team-professionisti.md)
- [KPI e performance](./02-team-organizzazione/kpi-performance.md)

### 03 — Clienti core
- [Gestione clienti](./03-clienti-core/gestione-clienti.md)
- [Check periodici](./03-clienti-core/check-periodici.md)
- [Modulo nutrizione](./03-clienti-core/modulo-nutrizione.md)
- [Diario e progresso](./03-clienti-core/diario-progresso.md)
- [Piano medico nutrizione](./03-clienti-core/piano_medico_nutrizione.md)
- [Guida al test medico](./03-clienti-core/test_medico_passo_passo.md)

### 04 — Strumenti operativi
- [Task e calendario](./04-strumenti-operativi/task-calendario.md)
- [Ticket e supporto](./04-strumenti-operativi/ticket-supporto.md)
- [Comunicazioni e chat](./04-strumenti-operativi/comunicazioni-chat.md)
- [Quality score](./04-strumenti-operativi/quality-score.md)
- [Ricerca globale](./04-strumenti-operativi/ricerca-globale.md)

### 05 — Comunicazione e integrazioni
- [Overview area 05](./05-comunicazione/README.md)
- [Comunicazione interna](./05-comunicazione/comunicazione-interna.md)
- [Integrazione Respond.io](./05-comunicazione/integrazione-respond-io.md)
- [Appointment Setting](./05-comunicazione/appointment-setting.md)
- [Notifiche push](./05-comunicazione/notifiche-push.md)
- [Integrazione GHL webhook](./05-comunicazione/integrazione-gohighlevel-webhook.md)
- [SuiteMind AI e SOP chatbot](./05-comunicazione/suitemind-ai-sop-chatbot.md)
- [Trustpilot e review automation](./05-comunicazione/trustpilot-review-automation.md)

### 06 — Sviluppo e varie
- [Report completamento documentazione](./06-sviluppo-e-varie/report-completamento-documentazione.md)
- [Refactor status report](./06-sviluppo-e-varie/refactor_status_report.md)
- [Refining refactor plan](./06-sviluppo-e-varie/refining_refactor_plan.md)

### 07 — Guide ruoli operativi
- [Guida Nutrizionista](./07-guide-ruoli/guida-nutrizionista.md)
- [Guida Coach](./07-guide-ruoli/guida-coach.md)
- [Guida Psicologo](./07-guide-ruoli/guida-psicologo.md)
- [Guida Health Manager](./07-guide-ruoli/guida-health-manager.md)
- [Guida Team Leader](./07-guide-ruoli/guida-team-leader.md)

## Tracker stato documentazione

| Documento | Owner | Stato | Ultimo aggiornamento | Prossima revisione |
|---|---|---|---|---|
| `00-panoramica/overview.md` | Team IT | 🟢 Completo | 27/03/2026 | 06/2026 |
| `02-team-organizzazione/autenticazione.md` | Team IT | 🟢 Completo | 27/03/2026 | 06/2026 |
| `03-clienti-core/gestione-clienti.md` | Team IT | 🟢 Completo | 27/03/2026 | 05/2026 |
| `04-strumenti-operativi/task-calendario.md` | Team IT | 🟢 Completo | 27/03/2026 | 06/2026 |
| `05-comunicazione/integrazione-respond-io.md` | Team IT | 🟢 Completo | 27/03/2026 | 06/2026 |
| `05-comunicazione/integrazione-gohighlevel-webhook.md` | Team IT | 🟡 Bozza avanzata | 27/03/2026 | 04/2026 |
| `05-comunicazione/suitemind-ai-sop-chatbot.md` | Team IT | 🟡 Bozza avanzata | 27/03/2026 | 04/2026 |
| `05-comunicazione/trustpilot-review-automation.md` | Team IT | 🟡 Bozza avanzata | 27/03/2026 | 04/2026 |
| `07-guide-ruoli/guida-nutrizionista.md` | Team IT | 🟢 Completo | 27/03/2026 | 06/2026 |

---
Ultimo aggiornamento: Marzo 2026

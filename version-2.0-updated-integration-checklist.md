# Version 2.0 Updated - Integrazione Checklist

Branch target: `version-2.0-updated`

## 1) Trustpilot / Tab Marketing

- [x] Integrare base da `feature/optimizations` (link, invio mail, webhook, tab marketing)
- [ ] Verificare config/env Trustpilot (API key/secret, business unit/user IDs, template, sender, webhook creds) in ambiente target
- [x] Garantire fallback robusti con credenziali mancanti (no crash, messaggi chiari)
- [x] Completare coerenza FE/BE del flusso marketing

## 2) Video recensione nella tab Marketing

- [x] Integrare feature video recensione (base BE/FE + migrazioni)
- [x] Flusso end-to-end: prenotazione -> conferma HM -> Loom link
- [x] Stati processo espliciti (booked / hm_confirmed)
- [x] Verifiche base su persistenza/validazioni/permessi/storico
- [x] Verificare compatibilita con booking/calendario HM esistente
- [ ] Rimozione placeholder/mock residui e coerenza UI finale

## 3) Call bonus

- [x] Portare modifiche da `call_bonus_fix` (flow + enum + side effects task/notifiche)
- [ ] Verifica completa FE/BE (stati, trigger, assegnazioni, visualizzazione)
- [ ] Verifica regressioni KPI/conteggi/timeline paziente

## 4) Capienza e tipologie supporto

- [x] Verificare integrazione completa da `feature/capienza-tipologie-supporto`
- [ ] Eliminare residui logica tipologia unica
- [ ] Validare allineamento dettaglio paziente/filtri/liste/query/KPI/parsing GHL
- [ ] Verificare pesi capienza + ordine migrazioni/seed

## 5) Paziente / HM / Onboarding / Customer Care

- [x] Integrare integralmente da `feature/paziente-hm-tab-capienza-docs`
- [x] Verificare catena lead -> cliente (persistenza + lettura FE)
- [ ] Rifiniture UI: naming/layout/storico/ordinamento/validazioni/UX

## 6) Teams notifications / guida Teams

- [x] Integrare codice da `feature/sumi-teams-notifications`
- [x] Verificare non regressione su altri flussi
- [ ] Aggiornare documentazione interna accessi Microsoft (solo comportamento reale)

## 7) Marketing automation / Frameio

- [x] Integrare `feature/marketing-automation-frameio`
- [x] Risolvere conflitti e verificare dipendenze/env/feature flag/permessi/UI

## 8) Fix tab Team: team leader non assegnabili

- [x] Portare fix da `main` (endpoint professionisti assegnabili include team leader)
- [ ] Test regressione assegnazione team leader

## 9) Calendario / creazione eventi

- [x] Verificare stato attuale in `version-2.0-updated` (assente/parziale/mock)
- [x] Completare creazione eventi da pagina calendario con calendari collegati
- [x] Verificare integrazione API GHL + error handling + UI feedback
- [x] Predisporre mock/stub test per evitare creazioni reali automatiche

## 10) Clinica / Tab patologie coach

- [x] Verificare implementazione tab patologie coach + campo "Altro"
- [x] Se mancante: sviluppare FE/BE e validazioni
- [x] Verificare visualizzazione/editing nel dettaglio paziente

## Operativo trasversale

- [x] Confronto per step: cosa c'e / cosa manca / differenze reali (no merge cieco)
- [x] Verifica migrazioni Alembic (catena, duplicati, compatibilita)
- [x] Test unit/integration parti toccate
- [x] Build frontend principali (`corposostenibile-clinica`, `teams-kanban`)
- [ ] Smoke test manuali flussi critici
- [ ] Report finale pre-live (integrazioni, conflitti, migrazioni, blocchi esterni, rischi residui)

## Ultimo avanzamento (2026-03-20)

- Backend test suite integrazione rieseguita: 14/14 pass su GHL safety/security/task dispatch + capienza/tipologie.
- Test scope guard `ClientiDetail` rieseguito: 1/1 pass.
- Alembic verificato: `coach_pathologies_01 (head)` sia su `db heads` sia su `db current`.
- Build frontend verificata: `corposostenibile-clinica` OK, `teams-kanban` OK (dopo install dipendenze locali).
- Hardening Trustpilot completato su codice: webhook endpoint + auth Basic + parsing robusto + fallback config mancanti + messaggi FE espliciti.
- Smoke tecnico rieseguito: build FE principali OK + Alembic heads/current OK.
- Smoke backend mirato completato: 22/22 test pass (Trustpilot, GHL security/dispatch/calendar safety, capienza/support types, scope guards, bridge HM assignment).
- Allineamento bridge GHL completato: resolve `health_manager_id` by email e persistenza su `cliente`/`opp_data`.
- Allineamento video recensione completato: obbligo HM assegnato per booking + link calendario HM in tab Marketing + error handling UX.

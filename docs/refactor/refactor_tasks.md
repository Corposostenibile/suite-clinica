# Refactor Tasks

## Paziente / Team UI

- [x] Mostrare `HM` (Health Manager) nel team della card sinistra del dettaglio paziente (`ClientiDetail`).
- [x] Mostrare `HM` nell'elenco pazienti (fix resilienza dati `snake_case` / `camelCase` in `ClientiListaNutrizione`).

## Dettaglio Professionista / Check

- [x] Mostrare solo la valutazione del professionista corrente nella tab check del profilo (`team/Profilo`).
- [x] Click su riga check apre modal dettaglio (con fetch dettaglio check) nella tab check del profilo (`team/Profilo`).

## Team UI

- [x] In `teams`, rimosso il nome team leader duplicato nella card (titolo card = leader; info team spostate sotto).
- [x] In `teams`, avatar principale card usa la foto del team leader (fallback robusto `avatar_path`/`avatar_url`).

## Task / Admin

- [x] Admin/CCO vede tutti i task (fatti e non fatti tramite toggle esistente) con filtri aggiuntivi per team, assegnatario, ruolo e specialità (`task/Task.jsx` + `/api/tasks`).

## Team Leader / Permessi Visuale

- [~] Dashboard: limitare KPI a solo proprio dipartimento/team (no KPI cross-dipartimento). (step UI: KPI globali nascosti in `Welcome` per `team_leader`; manca dashboard team-specific)
- [~] Dashboard: rimuovere medie valutazioni altri team e totali globali per `team_leader`. (step UI `Welcome` fatto)
- [~] Dashboard: nascondere sezioni/filtri non pertinenti ad altri ruoli (es. coach/psicologia se non pertinenti). (tab dashboard globali nascosti in `Welcome`)
- [~] Check: mostrare solo check del proprio team per `team_leader`. (UI/endpoint professionisti allineati; lista check dipende da RBAC `get_accessible_clients_query` su `/client-checks/azienda/stats`)
- [x] Check: limitare filtri alla sola specialità/ruolo del `team_leader`. (`CheckAzienda`: profType bloccato + dropdown professionisti del proprio team)
- [~] Task: validare visuale `team_leader` (task team, fatte + da fare) e allineare UX filtri. (aggiunto filtro professionista del proprio team in `task/Task.jsx`; da validare end-to-end con account TL)
- [x] Training: permettere a `team_leader` di vedere training dei membri del team. (UI `Formazione` abilita "Gestione Team"; backend `review/api/admin/trainings/<user_id>` scope team leader)
- [x] Training: permettere a `team_leader` di assegnare/scrivere training ai membri del team. (backend `can_write_review` aggiornato a team many-to-many; UI `Formazione` "Scrivi Training" su membri team)
- [~] Training: richieste ricevute TL gestibili direttamente in `Formazione` (accetta/rifiuta + risposta inline + CTA "Scrivi Training" in card richiesta; eventuale chat thread dedicata ancora da valutare)
- [x] Team: `team_leader` vede solo il proprio team (lista/dettaglio). (RBAC backend `/api/team/teams*` + UI azioni create/edit limitate)
- [x] Professionisti: `team_leader` vede solo professionisti del proprio team. (RBAC backend `/api/team/members*` + UI no KPI/azioni admin)
- [x] Assegnazioni AI: `team_leader` vede solo professionisti/team del proprio scope. (backend `/api/team/professionals/criteria` + `match/confirm` limitati; frontend usa endpoint GHL autenticato)
- [x] Quality: `team_leader` può vedere la pagina quality dei propri team in sola lettura. (menu+route abilitati; `weekly-scores` backend scoped a team guidati + specialità TL; UI blocca calcolo/trimestrale)
- [~] Clienti: limitare a soli clienti del proprio team/dipartimento. (da validare RBAC endpoint clienti con account TL)
- [~] Clienti: rimuovere visuali cross-dipartimento non pertinenti (es. “visuale coach/psicologia”). (UI `ClientiList`: pulsanti visuale + KPI + filtri base coerenti con specialità TL)

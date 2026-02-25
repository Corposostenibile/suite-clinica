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

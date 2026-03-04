# Blueprint Loom: Nuovo Flusso Support Widget

## Contesto: prima vs ora

### Prima (esistente, non toccato)
- `calendar` e `ghl_integration` già gestiscono casi Loom legati a meeting/eventi (`loom_link` su `Meeting`).
- Quella logica resta attiva e invariata per compatibilità operativa.

### Ora (nuovo, separato)
- In `blueprints/loom` stiamo costruendo un flusso indipendente per il widget di supporto.
- Questo flusso non dipende da calendario/GHL.
- Salva registrazioni Loom in una libreria dedicata, con:
  - `submitter` obbligatorio (utente che invia),
  - `cliente` opzionale (associazione paziente),
  - visibilità governata da permessi ruolo/team.

## UX target del widget

1. L’utente clicca **Registra Loom** nel widget di supporto.
2. A registrazione completata, la suite chiede se associare il Loom a un paziente.
3. Se sì, l’utente seleziona il paziente via ricerca (select con search).
4. Il backend salva la registrazione nella libreria personale/team/admin.

## Permessi libreria Loom

- `professionista` (coach/psicologo/nutrizionista): vede solo i propri Loom.
- `team_leader`: vede i Loom dei membri del proprio team (scope team).
- `admin`: vede tutti i Loom.

## Modello dati dedicato

Tabella: `loom_recordings` (nuovo modello `LoomRecording`)

Campi chiave:
- `loom_link` (obbligatorio)
- `submitter_user_id` (obbligatorio)
- `cliente_id` (opzionale)
- `title`, `note`, `source`
- timestamp (`created_at`, `updated_at`)

## API attuali nel blueprint `loom`

Prefix blueprint: `/loom`

- `POST /loom/api/recordings`
  - crea registrazione
  - `submitter_user_id` = utente corrente
  - `cliente_id` opzionale, validato con ACL

- `GET /loom/api/recordings`
  - lista libreria con scope permessi
  - filtri base: `cliente_id`, `with_cliente`, `submitter_user_id` (se autorizzato)

- `GET /loom/api/recordings/<id>`
  - dettaglio singola registrazione con controllo ACL

- `PUT /loom/api/recordings/<id>/association`
  - aggiorna/rimuove associazione paziente (`cliente_id` nullable)

- `GET /loom/api/patients/search?q=...`
  - ricerca pazienti per la select nel widget
  - risultati già filtrati per permessi utente

## Nota implementativa

Questa è la base backend per il nuovo flusso separato.
Nel frontend React andrà collegata la UX del widget (trigger registrazione, scelta paziente, submit API, vista libreria).

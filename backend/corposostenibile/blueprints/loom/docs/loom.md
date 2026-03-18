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
3. Se sì, l’utente seleziona il paziente via ricerca.
4. Il backend salva la registrazione nella libreria personale/team/admin.

## Permessi libreria Loom

- `professionista`: vede solo i propri Loom.
- `team_leader`: vede i Loom dei membri del proprio team.
- `admin`: vede tutti i Loom.

## Modello dati dedicato

Tabella: `loom_recordings` (modello `LoomRecording`)

Campi chiave:
- `loom_link` obbligatorio
- `submitter_user_id` obbligatorio
- `cliente_id` opzionale
- `title`, `note`, `source`
- timestamp `created_at`, `updated_at`

## API attuali nel blueprint `loom`

Prefix blueprint: `/loom`

- `POST /loom/api/recordings`
- `GET /loom/api/recordings`
- `GET /loom/api/recordings/<id>`
- `PUT /loom/api/recordings/<id>/association`
- `GET /loom/api/patients/search?q=...`

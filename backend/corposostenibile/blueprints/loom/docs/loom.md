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

## Stato integrazione frontend (aggiornamento)

- Il bottone `Registra Loom` nel Support Widget è attivo.
- Il recorder Loom viene aperto e, su `insert`, viene chiamata:
  - `POST /loom/api/recordings`
- Il salvataggio iniziale è con:
  - `submitter_user_id` obbligatorio (utente loggato),
  - `cliente_id` non ancora richiesto nello step corrente (arriverà dopo).

## Configurazione ambiente (VPS dev/stage)

### Variabili frontend

Nel frontend React (`corposostenibile-clinica`) servono:

- `VITE_LOOM_PUBLIC_APP_ID=<public_app_id_loom>`
- opzionale: `VITE_LOOM_SDK_SCRIPT_URL=/static/js/loom-sdk.bundle.js`

Note:
- `VITE_LOOM_PUBLIC_APP_ID` deve essere l'App ID Loom con dominio autorizzato.
- Su VPS locale/stage (`https://suite-clinica.duckdns.org`) usare l'app Loom che include quel dominio in allowlist (es. sandbox).

### Proxy dev Vite

In sviluppo il dev server deve proxyare il blueprint:
- `/loom -> backendUrl`

Senza questo proxy, la `POST /loom/api/recordings` risponde `404` dal frontend.

### Come farlo provare a un collaboratore

1. Creare/fornire un account Loom autorizzato all'uso del Record SDK.
2. Verificare nel Loom Developer Portal che il dominio usato dal collaboratore sia autorizzato:
   - `localhost` e/o `127.0.0.1` per test locale,
   - `suite-clinica.duckdns.org` per VPS stage.
3. Consegnare al collaboratore:
   - valore di `VITE_LOOM_PUBLIC_APP_ID`,
   - URL ambiente da usare.
4. Il collaboratore deve:
   - fare login su Loom nello stesso browser,
   - consentire cookie necessari (no blocco terze parti per Loom),
   - disattivare eventuali estensioni che bloccano script/cookie Loom durante il test.

Non è necessario usare una “sandbox” applicativa del progetto: serve una app Loom con domini corretti + account Loom autorizzato.

## Produzione GCP

Per produzione su `http://34.154.33.164/` (da validare su dominio finale):

1. Creare un'app Loom dedicata produzione (consigliato separata da sandbox/stage).
2. Inserire in allowlist i domini reali di produzione (non solo IP, appena definiti).
3. Impostare nel frontend build di produzione:
   - `VITE_LOOM_PUBLIC_APP_ID=<public_app_id_production>`
4. Verificare che il backend serva `/static/js/loom-sdk.bundle.js` anche in produzione.
5. Verificare end-to-end:
   - Record -> Insert -> `POST /loom/api/recordings` -> record presente in libreria con ACL corretta.

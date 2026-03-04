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
- Dopo la registrazione viene mostrata UI nativa suite (non modale Loom):
  - salvataggio/conferma nella suite,
  - ricerca paziente (`/loom/api/patients/search`) e associazione opzionale.

## Libreria Loom frontend (nuova pagina)

- Nuova pagina React: `Libreria Loom` con route dedicata.
- Collegamento inserito nel menu laterale.
- Fonte dati: `GET /loom/api/recordings`.
- Azioni disponibili in lista:
  - `Apri` link Loom,
  - `Copia` link.

### UX per ruoli

- Admin:
  - vista in stile Capienza,
  - filtri `Tutti / Nutrizione / Coach / Psicologia`,
  - filtro `Team`,
  - raggruppamento per team (come Capienza).
- Team leader:
  - vista tabellare coerente con Capienza, scope già limitato dal backend al proprio team.
- Professionista:
  - vista tabellare semplificata, scope ai propri Loom.

## Compatibilità API lato autenticazione

- Corretto comportamento non autorizzato per rotte `/loom/api/*`:
  - risposta JSON `401`,
  - evita ritorno HTML login page su chiamate AJAX frontend.

## Produzione GCP

Per produzione su `http://34.154.33.164/` (da validare su dominio finale), fare solo i seguenti passaggi:

1. Creare un'app Loom dedicata produzione (consigliato separata da sandbox/stage).
2. Inserire in allowlist i domini reali di produzione (non solo IP, appena definiti).
3. Impostare nel frontend build di produzione:
   - `VITE_LOOM_PUBLIC_APP_ID=<public_app_id_production>`
   - opzionale: `VITE_LOOM_SDK_SCRIPT_URL=/static/js/loom-sdk.bundle.js`
4. Verificare che il backend serva `/static/js/loom-sdk.bundle.js` anche in produzione.
5. Verificare end-to-end:
   - Record -> Insert -> `POST /loom/api/recordings` -> record presente in libreria con ACL corretta.

## Nota tecnica attuale (dipendenza temporanea)

- Al momento l'integrazione React clinica dipende da:
  - `/static/js/loom-sdk.bundle.js`
- Motivo: con stack frontend React 19, la versione npm ufficiale `@loomhq/record-sdk` genera incompatibilità runtime.

## Nota operativa SW/PWA (ambiente DuckDNS locale VPS)

- L'ambiente `https://suite-clinica.duckdns.org` è locale/shared con PWA attiva.
- Per limitare il problema "versione vecchia finché non hard refresh":
  - service worker configurato con update check periodico,
  - apply update automatico quando disponibile.

## Cosa monitorare per passare a npm ufficiale

Monitorare periodicamente:

1. `@loomhq/record-sdk` su npm:
   - changelog/versione con peer dependency compatibile React 19 (`react`/`react-dom`).
   - link: https://www.npmjs.com/package/@loomhq/record-sdk
2. Documentazione ufficiale Loom Record SDK:
   - update espliciti su supporto React 19.
   - link: https://dev.loom.com/docs/record-sdk/getting-started
   - link: https://www.loom.com/sdk
3. Test interno di smoke:
   - install package ufficiale,
   - init SDK senza errori runtime,
   - `openPreRecordPanel` + `insert` + salvataggio backend OK.

Criterio di uscita dalla dipendenza al bundle:
- appena package npm è ufficialmente compatibile con React 19 **e** smoke test interno è verde end-to-end.

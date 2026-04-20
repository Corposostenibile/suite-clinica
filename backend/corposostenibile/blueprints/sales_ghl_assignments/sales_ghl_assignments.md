# Sales GHL Assignments

Blueprint alias per esporre la lista delle assegnazioni GHL sotto un path più esplicito:

- `GET /api/ghl-assignments`

## Scopo

Questo blueprint non introduce una nuova logica di business. Riusa la stessa
sorgente dati e lo stesso schema risposta di `ghl_integration` per avere un
endpoint stabile e leggibile per tooling, integrazioni e documentazione.

## Sicurezza

L'endpoint richiede:

- autenticazione utente
- permesso ACL `ghl:view_assignments`

## Risposta

Il payload restituito è allineato a quello di `GET /ghl/api/assignments`:

- `assignments[]`
- `total`

## Nota operativa

Questo blueprint è un alias architetturale. Il backend continua a considerare
`ghl_integration` come fonte principale della logica GHL.

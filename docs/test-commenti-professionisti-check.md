# Test: Commenti professionisti sui check compilati dal cliente

## Obiettivo

Verificare che un professionista possa **inserire/aggiornare/rimuovere** un commento (unico, sostituibile) su una **compilazione** di check periodico (weekly / dca / minor) e che il commento sia **persistente**.

---

## Prerequisiti

- Backend e frontend avviati.
- Utente loggato con permessi per vedere i check del cliente.
- Almeno un cliente con almeno una compilazione (risposta) di check.

---

## Test 1 — Check Azienda

1. Apri pagina **Check Azienda**.
2. Clicca una riga in tabella per aprire il **modal dettaglio risposta**.
3. Trova la sezione **Commento professionista**.
4. Inserisci testo (es. `Test commento da Check Azienda`) e clicca **Salva commento**.
5. Atteso:
   - il commento appare sopra la textarea,
   - mostra autore e data,
   - nessun errore in console/log.
6. Modifica testo e salva di nuovo → deve aggiornarsi.
7. Svuota textarea e salva → commento rimosso.

---

## Test 2 — Scheda Cliente → Check periodici

1. Apri un cliente.
2. Vai al tab **Check periodici** (storico compilazioni).
3. Clicca **Visualizza dettagli** su una riga.
4. Nella sezione **Commento professionista**, salva un commento.
5. Chiudi e riapri il modal della stessa risposta → il commento deve restare.

---

## Test 3 — Tipi di check

Ripeti almeno una volta per ciascun tipo disponibile:

- `weekly`
- `dca`
- `minor`

La sezione commento deve funzionare allo stesso modo per tutti.

---

## Test API (opzionale)

- GET dettaglio:
  - `GET /api/client-checks/response/<type>/<id>` deve includere:
    - `professional_comment`
    - `professional_comment_at`
    - `professional_comment_by_name`
- PATCH commento:
  - `PATCH /api/client-checks/response/<type>/<id>/comment` con body `{ "comment": "..." }`
  - stringa vuota = rimozione commento


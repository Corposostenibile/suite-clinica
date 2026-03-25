# Test Medico – Guida passo passo (credenziali e flusso)

Questa guida spiega **con quali credenziali** fare **cosa**, per verificare che il Medico veda i pazienti assegnati e che le modifiche Nutrizione funzionino.

---

## Ruoli e credenziali da usare

- **Admin** (o utente con accesso completo): per creare il Medico, assegnarlo ai pazienti e controllare che tutto sia configurato.
- **Medico (Alex Zanardi)**: per verificare che veda **solo** i pazienti a cui è assegnato.

---

## Passo 1 – Creare il Medico (se non esiste)

1. Accedi con un utente **Admin** (es. il tuo utente principale).
2. Vai in **Team** → **Lista Team** (o il link che porta alla lista membri).
3. Clicca **Nuovo Membro** (o **Aggiungi membro**).
4. Compila:
   - Nome: **Alex**
   - Cognome: **Zanardi**
   - Email: **alex.zanardi@...** (una email univoca)
   - Password e conferma password.
   - **Ruolo**: **Professionista**
   - **Specializzazione**: **Medico**
5. Salva con **Crea Membro**.

---

## Passo 2 – Assegnare il Medico a un paziente

1. Resta con l’utente **Admin**.
2. Vai in **Clienti** → apri un paziente (es. Mario Rossi).
3. Apri la tab **Team** (nella scheda del cliente).
4. Nella sezione **Medico** (o “Assegnazioni” / “Professionisti”):
   - Clicca **Assegna** (o “Aggiungi medico”).
   - Scegli **Alex Zanardi** (il Medico creato).
   - Inserisci **data inizio** e **motivazione** (es. “Controllo semestrale”).
   - Conferma.
5. Verifica che in tab **Team** compaia **Alex Zanardi** come Medico assegnato.

---

## Passo 3 – Verificare che il Medico veda i pazienti (lista clienti)

1. **Esci** dall’account Admin (logout).
2. Accedi con le **credenziali del Medico** (Alex Zanardi: email e password impostate al Passo 1).
3. Vai in **Clienti** (o **Lista clienti** / **Pazienti**).
4. **Risultato atteso**: nella lista compare **solo** il paziente a cui hai assegnato il Medico (es. Mario Rossi). Non devono comparire altri pazienti.
5. Se la lista è vuota: torna al Passo 2 e controlla che l’assegnazione Medico sia salvata e attiva nella tab Team del paziente.

---

## Passo 4 – Verificare la scheda Nutrizione (vista Medico)

1. Sempre con **Medico (Alex Zanardi)** loggato.
2. Dalla lista clienti, apri il **paziente a cui è assegnato** (es. Mario Rossi).
3. Apri la tab **Nutrizione**.
4. Controlla:
   - **Panoramica**: nella sezione **Medico assegnato** deve comparire **Alex Zanardi** (e solo lui, se è l’unico medico assegnato).
   - **Setup**: nella sezione **Date call di visita** (o “Call iniziale nutrizionista”) deve comparire la data se è stata impostata.
   - **Non** deve esserci la tab **Piano Alimentare**.
   - **Patologie e Anamnesi**: una sola tab con le 5 sottosezioni (Remota, Prossima, Familiare, Stile di vita, Terapie e allergie).
   - **Diario** e **Note Alert**: presenti e utilizzabili come prima.

---

## Passo 5 – Verificare con Admin che tutto sia coerente

1. Esci dal Medico e accedi di nuovo con **Admin**.
2. Apri lo **stesso paziente** (es. Mario Rossi).
3. In **Nutrizione** verifica che:
   - Panoramica mostri il Medico assegnato (Alex Zanardi).
   - Setup mostri le date call di visita.
   - Tab Piano Alimentare non ci sia.
   - Tab Patologie e Anamnesi sia unificata con le 5 sezioni.

---

## Riepilogo credenziali

| Cosa fare | Con chi accedere |
|----------|------------------|
| Creare il membro Medico | **Admin** |
| Assegnare il Medico a un paziente (tab Team) | **Admin** |
| Vedere la lista “i miei pazienti” | **Medico (Alex Zanardi)** |
| Aprire scheda cliente e tab Nutrizione come Medico | **Medico (Alex Zanardi)** |
| Controllare configurazione e dati completi | **Admin** |

---

## Se il Medico non vede nessun paziente

- Controlla che l’assegnazione nella tab **Team** del paziente sia **attiva** (data inizio compilata, nessuna data fine).
- Verifica di essere loggato con l’account **Medico** (nome in alto a destra / profilo).
- Ricarica la pagina (o fai un refresh forzato Ctrl+Shift+R) dopo l’assegnazione.

Dopo le modifiche al backend (filtri su `ClienteProfessionistaHistory`), il Medico vede in lista **solo** i clienti per cui esiste un’assegnazione attiva con tipo “medico” e il suo `user_id`.

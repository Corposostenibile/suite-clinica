# 📋 Sistema Check Iniziali e Settimanali per Clienti

## 📌 OVERVIEW DEL PROGETTO
**Obiettivo**: Sostituire il sistema TypeForm attuale con un sistema interno di form builder che permetta la creazione di check iniziali e settimanali per i clienti, con notifiche automatiche ai professionisti.
**Priorità**: Alta
**Blueprint da creare**: `client_checks`

## 🎯 REQUISITI FUNZIONALI

1.  **Form Builder per Admin/Responsabili**
    *   Gli admin e i responsabili di dipartimento devono poter creare:
        *   **Check Iniziali**: Form compilati una sola volta all'inizio del percorso
        *   **Check Settimanali**: Form compilati periodicamente dai clienti
    *   Il form builder deve supportare diversi tipi di campi (testo, numero, select, radio, checkbox, textarea, scala 1-10)
    *   Possibilità di marcare campi come obbligatori
    *   Ordinamento drag&drop dei campi

2.  **Associazione Form-Cliente**
    *   Nel dettaglio cliente (`/customers/<id>`) aggiungere pulsanti per:
        *   Selezionare il check iniziale da assegnare
        *   Selezionare il check settimanale da assegnare
    *   Generazione link univoco per cliente per ogni form

3.  **Compilazione e Visualizzazione**
    *   Link pubblico univoco per la compilazione (no login richiesto)
    *   Visualizzazione risposte in due tab separate nel dettaglio cliente:
        *   Tab "Check Iniziale"
        *   Tab "Check Settimanale"
    *   Storico di tutte le compilazioni con timestamp

4.  **Sistema Notifiche**
    *   Email automatica a TUTTI i professionisti associati al cliente quando viene compilato un check
    *   L'email deve specificare:
        *   Nome cliente
        *   Tipo di check (iniziale/settimanale)
        *   Link diretto alle risposte

## 🏗️ ARCHITETTURA TECNICA

### 📂 STRUTTURA FILE DA CREARE
**Cartella principale**: `corposostenibile/blueprints/client_checks/`

**File Python necessari**:
*   `__init__.py` - Registrazione e configurazione del blueprint
*   `routes.py` - Tutte le route e gli endpoint del modulo
*   `forms.py` - Classi WTForms per validazione lato server
*   `services.py` - Logica di business e operazioni database
*   `helpers.py` - Funzioni di utility e controllo permessi

**Template HTML necessari (in `templates/client_checks/`)**:
*   `form_builder.html` - Interfaccia drag&drop per creare form
*   `form_list.html` - Tabella con lista dei form creati
*   `form_preview.html` - Anteprima del form durante la creazione
*   `public_form.html` - Form pubblico compilabile dai clienti
*   `responses_view.html` - Visualizzazione risposte compilate
*   `thank_you.html` - Pagina di ringraziamento post-compilazione

### 🗄️ MODELLI DATABASE DA CREARE
**Percorso file**: `/corposostenibile/blueprints/client_checks/models.py`

**Modelli necessari**:

1.  **CheckForm** - Tabella principale per i template dei form
    *   Contiene nome, descrizione e tipo (iniziale/settimanale)
    *   Collegato all'utente che l'ha creato e opzionalmente a un dipartimento
    *   Ha un flag `is_active` per abilitare/disabilitare form
    *   Relazione one-to-many con i campi del form
2.  **CheckFormField** - Tabella per i singoli campi del form
    *   Ogni campo ha un tipo (text, number, select, radio, checkbox, textarea, scale, date)
    *   Può essere marcato come obbligatorio
    *   Ha una posizione per l'ordinamento
    *   Per campi select/radio/checkbox salva le opzioni in formato JSON
    *   Per campi scale salva min/max valori
3.  **ClientCheckAssignment** - Tabella di associazione form-cliente
    *   Collega un form specifico a un cliente specifico
    *   Genera e memorizza un token univoco per il link pubblico
    *   Traccia chi ha assegnato il form e quando
    *   Mantiene statistiche di compilazione
4.  **ClientCheckResponse** - Tabella per salvare le risposte compilate
    *   Collegata all'assignment tramite foreign key
    *   Salva tutte le risposte in formato JSON
    *   Memorizza timestamp, IP e user agent di compilazione
    *   Traccia se le notifiche sono state inviate

**ENUM da aggiungere**:
*   `CheckFormTypeEnum` con valori: `iniziale`, `settimanale`
*   `CheckFormFieldTypeEnum` con valori: `text`, `number`, `email`, `textarea`, `select`, `radio`, `checkbox`, `scale`, `date`

---

## 💻 IMPLEMENTAZIONE DETTAGLIATA

### 1️⃣ **Creare il Blueprint**
**File da creare:**
`/corposostenibile/blueprints/client_checks/__init__.py`

Questo file deve:
-   Definire il blueprint con nome `'client_checks'`
-   Impostare il prefisso URL a `'/client-checks'`
-   Specificare la cartella templates locale
-   Importare il modulo routes alla fine

### 2️⃣ **Registrare il Blueprint**
**File da modificare:** `/corposostenibile/__init__.py`

**Modifiche da fare:**
1.  Nella sezione degli import dei blueprint (cerca commenti come "Import blueprint" intorno alla riga 250-262), aggiungere l'import del nuovo blueprint `client_checks`
2.  Nella sezione di registrazione dei blueprint (cerca dove vengono chiamati `app.register_blueprint()` intorno alla riga 267-277), registrare il nuovo blueprint

**Importante:** Mantenere l'ordine già presente nel file

### 3️⃣ **Routes Principali**
**File da creare:**
`/corposostenibile/blueprints/client_checks/routes.py`

**Route da implementare:**
1.  **`/` (GET)** - Lista di tutti i form creati
    *   Solo per admin e responsabili dipartimento
    *   Mostra form attivi con possibilità di modifica/eliminazione
2.  **`/builder` (GET/POST)** - Form builder per creazione
    *   GET: mostra interfaccia form builder
    *   POST: salva nuovo form tramite AJAX
3.  **`/builder/<id>` (GET/POST)** - Form builder per modifica
    *   Come sopra ma carica form esistente
4.  **`/assign/<cliente_id>` (POST)** - Assegnazione form a cliente
    *   Verifica permessi (admin o professionista associato)
    *   Genera token univoco
    *   Redirect al dettaglio cliente
5.  **`/public/<token>` (GET/POST)** - Form pubblico
    *   Non richiede autenticazione
    *   GET: mostra form da compilare
    *   POST: salva risposte e invia notifiche
    *   **IMPORTANTE**: disabilitare CSRF per questa route
6.  **`/responses/<cliente_id>` (GET)** - Visualizza risposte
    *   Mostra tutte le compilazioni divise per tipo
    *   Solo per admin e professionisti associati

**Import necessari:**
-   **Flask**: `render_template`, `request`, `jsonify`, `flash`, `redirect`, `url_for`, `abort`
-   **Flask-Login**: `login_required`, `current_user`
-   **Models**: `CheckForm`, `CheckFormField`, `ClientCheckAssignment`, `ClientCheckResponse`, `Cliente`, `User`, `db`
-   **Extensions**: `csrf` (per exempt decorator)
-   **Services locali**: `create_form`, `update_form`, `assign_form_to_client`, `save_client_response`, `send_completion_notifications`
-   **Helpers locali**: `can_manage_forms`, `get_form_or_404`

### 4️⃣ **Services**
**File da creare:**
`/corposostenibile/blueprints/client_checks/services.py`

**Funzioni da implementare:**
1.  **`create_form(data, user)`**
    *   Riceve i dati del form in formato dict e l'utente che lo crea
    *   Crea l'oggetto `CheckForm` con nome, descrizione, tipo
    *   Per ogni campo nei dati, crea un `CheckFormField` collegato
    *   Salva tutto nel database e ritorna il form creato
2.  **`update_form(form, data)`**
    *   Riceve il form esistente e i nuovi dati
    *   Aggiorna nome e descrizione del form
    *   Elimina tutti i campi esistenti
    *   Ricrea i campi con i nuovi dati
    *   Salva le modifiche
3.  **`assign_form_to_client(cliente, form_id, user)`**
    *   Verifica se esiste già un'assegnazione per quella coppia cliente-form
    *   Se esiste, la riattiva
    *   Altrimenti crea una nuova `ClientCheckAssignment`
    *   Genera token univoco di 32 caratteri con `secrets.token_urlsafe()`
    *   Salva e ritorna l'assignment
4.  **`save_client_response(assignment, form_data)`**
    *   Estrae le risposte dal `form_data` basandosi sui `field_id`
    *   Gestisce campi checkbox che possono avere valori multipli
    *   Crea `ClientCheckResponse` con le risposte in formato JSON
    *   Aggiorna contatore e timestamp sull'assignment
    *   Salva e ritorna la response
5.  **`send_completion_notifications(response)`**
    *   Recupera cliente e form dalla response
    *   Raccoglie email di nutrizionista, coach e psicologo se presenti
    *   Prepara email HTML con nome cliente, tipo check e link alle risposte
    *   Invia email tramite Flask-Mail
    *   Marca la response come notificata
    *   Gestisce errori di invio con logging

### 5️⃣ **Helpers**
**File da creare:**
`/corposostenibile/blueprints/client_checks/helpers.py`

**Funzioni helper da implementare:**
1.  **`can_manage_forms()`**
    *   Verifica se l'utente corrente può creare/modificare form
    *   Ritorna `True` se l'utente è admin
    *   Ritorna `True` se l'utente è responsabile di almeno un dipartimento
    *   Altrimenti ritorna `False`
2.  **`get_form_or_404(form_id)`**
    *   Recupera il form dal database o ritorna 404 se non esiste
    *   Se l'utente non è admin, verifica che il form appartenga al suo dipartimento
    *   Se non ha permessi, lancia `abort(403)`
    *   Ritorna l'oggetto form se tutto ok

---

## 🎨 INTEGRAZIONE NEL DETTAGLIO CLIENTE

### Modificare il template del dettaglio cliente
**File da modificare:**
`/corposostenibile/blueprints/customers/templates/customers/detail_editable.html`

**Dove trovare la sezione:** Cercare `<ul class="nav nav-tabs">` (intorno alla riga 850)

**Cosa aggiungere nei tab header:**
Dopo il tab "Allegati" e prima di quello "Storico" (circa riga 850), aggiungere due nuovi elementi della lista per i tab:
-   Un tab con icona clipboard-check per "Check 
"
-   Un tab con icona calendar-check per "Check Settimanale"
-   Entrambi devono usare Bootstrap `data-bs-toggle="tab"` per il funzionamento

**Contenuti dei tab da aggiungere:**
Nella sezione `tab-content` (cercare questo `div` nel file), prima del tab "Storico", aggiungere:

**1. Tab Check Iniziale:**
-   Creare un div con classe `"tab-pane fade"` e id `"check-iniziale"`
-   Inserire una card Bootstrap con:
    -   **Header della card:**
        -   Titolo "Check Iniziale" allineato a sinistra
        -   Pulsante "Assegna Check" allineato a destra (visibile solo per admin e professionisti associati)
        -   Il pulsante deve aprire un modal con `data-bs-target="#assignInitialCheckModal"`
    -   **Body della card:**
        -   Usare filtro Jinja2 per recuperare l'assignment di tipo "iniziale" dal cliente
        -   **Se esiste un assignment:**
            -   Alert info con nome del form assegnato
            -   Link univoco di compilazione in un tag `<code>`
            -   Pulsante per copiare il link negli appunti
            -   Tabella con lista delle compilazioni (data e pulsante visualizza)
            -   Se non ci sono compilazioni, mostrare messaggio "Nessuna compilazione ancora ricevuta"
        -   **Se non esiste assignment:**
            -   Mostrare messaggio "Nessun check iniziale assegnato"

**2. Tab Check Settimanale:**
-   Struttura identica al Tab Check Iniziale ma con:
    -   id `"check-settimanale"`
    -   Titolo "Check Settimanale"
    -   `data-bs-target="#assignWeeklyCheckModal"` per il pulsante
    -   Filtrare assignment per tipo "settimanale"
    -   Messaggi adattati per check settimanale

**3. Modal per Assegnazione Check Iniziale:**
-   Modal Bootstrap standard con id `"assignInitialCheckModal"`
-   Form che punta all'endpoint `'client_checks.assign_to_client'` con metodo `POST`
-   Includere:
    -   Token CSRF
    -   Campo hidden `"form_type"` con valore `"iniziale"`
    -   Select per scegliere il form da assegnare (popolato con `available_initial_forms`)
    -   Pulsanti Annulla e Assegna nel footer

**4. Modal per Assegnazione Check Settimanale:**
-   Identico al modal iniziale ma con:
    -   id `"assignWeeklyCheckModal"`
    -   Campo hidden `"form_type"` con valore `"settimanale"`
    -   Select popolato con `available_weekly_forms`

**5. JavaScript per funzionalità copia:**
-   Implementare funzione `copyToClipboard(text)` che:
    -   Usa l'API `navigator.clipboard.writeText()`
    -   Mostra alert di conferma dopo la copia
    -   Gestisce eventuali errori di permessi del browser

### Modificare la route del dettaglio cliente
**File da modificare:**
`/corposostenibile/blueprints/customers/routes.py`

**Nella funzione `detail()` (cerca intorno alla riga 300):**
1.  **Prima del `return render_template` esistente:**
    -   Importare il modello `CheckForm` da `corposostenibile.models` (se non già importato)
    -   Eseguire una query per recuperare tutti i `CheckForm` dove:
        -   `form_type` è `'iniziale'` e `is_active` è `True`
    -   Eseguire un'altra query per recuperare tutti i `CheckForm` dove:
        -   `form_type` è `'settimanale'` e `is_active` è `True`
    -   Salvare i risultati in due variabili: `available_initial_forms` e `available_weekly_forms`
2.  **Nel `return render_template` esistente:**
    -   Mantenere TUTTI i parametri già presenti
    -   Aggiungere alla fine i due nuovi parametri:
        -   `available_initial_forms`: la lista dei form iniziali
        -   `available_weekly_forms`: la lista dei form settimanali

**Nota importante:** Il template si chiama `"customers/detail_editable.html"` e tutti i parametri esistenti devono rimanere invariati

---

## 🎨 TEMPLATE FORM BUILDER
**File da creare:**
`/corposostenibile/blueprints/client_checks/templates/client_checks/form_builder.html`

**Struttura del template da implementare:**

**Il template deve:**
1.  Estendere il template base del progetto
2.  Avere titolo "Form Builder - Check Clienti"

**Layout a due colonne:**

**Colonna sinistra (8/12):**
-   Form con `id="formBuilder"` contenente:
    -   Campo input per nome form (required)
    -   Textarea per descrizione (opzionale)
    -   Select per tipo form (iniziale/settimanale)
    -   Sezione "Campi Form" con pulsante "Aggiungi Campo"
    -   Container vuoto con `id="fieldsContainer"` per i campi dinamici
    -   Se in modalità modifica, pre-popolare con dati esistenti
    -   Pulsanti Salva e Annulla

**Colonna destra (4/12):**
-   Card "Anteprima" con `id="previewContainer"`
-   Mostra preview in tempo reale del form

**JavaScript necessario:**
1.  **Funzione `addField()`:**
    -   Incrementa contatore campi
    -   Aggiunge HTML dinamico per nuovo campo con:
        -   Input per label del campo
        -   Select per tipo campo (text, number, email, textarea, select, radio, checkbox, scale, date)
        -   Container per opzioni aggiuntive (mostrate solo per select/radio/checkbox/scale)
        -   Checkbox per campo obbligatorio
        -   Pulsante elimina campo
    -   Chiama `updatePreview()`
2.  **Funzione `removeField(fieldId)`:**
    -   Rimuove il campo dal DOM
    -   Chiama `updatePreview()`
3.  **Funzione `updateFieldOptions(fieldId)`:**
    -   Mostra/nasconde opzioni basate sul tipo campo:
        -   Per select/radio/checkbox: textarea per lista opzioni
        -   Per scale: input numerici per min/max
        -   Per altri tipi: nessuna opzione aggiuntiva
    -   Chiama `updatePreview()`
4.  **Funzione `updatePreview()`:**
    -   Legge tutti i campi dal `fieldsContainer`
    -   Genera HTML di preview con form simulato
    -   Aggiorna `previewContainer`
5.  **Event listener su `submit`:**
    -   Previene submit standard
    -   Raccoglie dati di tutti i campi in array
    -   Crea oggetto JSON con nome, descrizione, tipo e campi
    -   Invia via `fetch` POST con header JSON e CSRF token
    -   Su successo, redirect alla lista form
    -   Su errore, mostra alert

**Note implementative:**
-   Usare Bootstrap 5 per styling
-   Icone FontAwesome per pulsanti
-   Template string JavaScript per generazione HTML dinamico
-   CSRF token da Jinja2 per sicurezza POST

## 🧪 TEST E VALIDAZIONE
**Test da eseguire:**
1.  **Test Form Builder:**
    *   Creare form con diversi tipi di campi
    *   Verificare ordinamento drag&drop
    *   Testare validazioni `required`
2.  **Test Assegnazione:**
    *   Assegnare form a cliente
    *   Verificare generazione link univoco
    *   Testare permessi (solo admin/professionisti associati)
3.  **Test Compilazione:**
    *   Accedere al link pubblico
    *   Compilare form con tutti i tipi di campo
    *   Verificare salvataggio risposte
4.  **Test Notifiche:**
    *   Verificare invio email a tutti i professionisti
    *   Controllare contenuto email
    *   Testare link nella email
5.  **Test Visualizzazione:**
    *   Verificare tab nel dettaglio cliente
    *   Controllare lista risposte
    *   Testare visualizzazione dettaglio risposte

## 📁 CHECKLIST FINALE
- [ ] Creare cartella blueprint `/corposostenibile/blueprints/client_checks/`
- [ ] Aggiungere modelli in `models.py`
- [ ] Eseguire migration database
- [ ] Implementare `routes.py`, `services.py`, `helpers.py`
- [ ] Creare template `form_builder.html`
- [ ] Creare template `public_form.html`
- [ ] Creare template `responses_view.html`
- [ ] Modificare `detail_editable.html` per aggiungere tab
- [ ] Modificare `customers/routes.py` per passare form disponibili
- [ ] Registrare blueprint in `__init__.py`
- [ ] Configurare CSRF exemption per route pubblica
- [ ] Testare form builder
- [ ] Testare assegnazione a cliente
- [ ] Testare compilazione pubblica
- [ ] Testare invio notifiche email
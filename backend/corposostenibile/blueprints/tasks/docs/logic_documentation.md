# Documentazione Logica Trigger e Task Automatici

Questo documento descrive la logica di implementazione per la generazione automatica dei Task nel sistema.

## 1. Listeners SQLAlchemy (Eventi in Tempo Reale)

Intercettiamo gli eventi del database per creare task immediati.

### Onboarding (Assegnazione Cliente)
*   **Trigger**: `Cliente` (SQLAlchemy `after_update`)
*   **Codice**: `tasks/events.py` -> `trigger_onboarding_task`
*   **Logica**:
    Se vengono modificati i campi `nutrizionista_id`, `coach_id` o `psicologa_id`:
    1.  Verifica che il valore sia cambiato (tramite `inspect(target).attrs.get(field).history`).
    2.  Genera un task per il nuovo professionista assegnato.

### Check Ricevuto
*   **Trigger**: `ClientCheckResponse` (SQLAlchemy `after_insert`)
*   **Codice**: `tasks/events.py` -> `trigger_check_task`
*   **Logica**:
    Quando un cliente invia un check:
    1.  Recupera l'`assignment` collegato per risalire al cliente e al professionista (`assigned_by_id`).
    2.  Genera un task per il professionista che ha assegnato il check.

### Formazione (Training)
*   **Trigger**: `Review` (SQLAlchemy `after_insert`)
*   **Codice**: `tasks/events.py` -> `trigger_training_task`
*   **Logica**:
    Quando viene assegnata una review/formazione:
    1.  Genera un task per il destinatario (`reviewee_id`).

---

## 2. Periodic Tasks (Celery Beat)

Task pianificati (Cron) per controlli giornalieri.

### Solleciti (Check mancati)
*   **Tipo**: Periodic Task
*   **Codice**: `tasks/tasks.py` -> `generate_solicitations_task`
*   **Frequenza**: Giornaliera (es. 10:00 AM)
*   **Logica Implementata**:
    1.  Mappa il giorno corrente (Python `weekday()`) al `GiornoEnum` del database (es. `0 -> Lunedi`).
    2.  Cerca tutti i clienti **attivi** che hanno il check in quel giorno.
    3.  Per ogni cliente, verifica la data dell'ultimo check inviato.
    4.  Calcola `days_diff = (today - last_check_date).days`.
    5.  Se `days_diff >= 7` (nessun check nell'ultima settimana), genera il task.

    ```python
    # Esempio Semplificato
    last_check_date = _get_last_check_date(client)
    if not last_check_date:
        should_trigger = True # Mai inviato
    else:
        days_diff = (today - last_check_date).days
        # Se oggi è il check day, ci aspettiamo un check oggi o massimo 6 giorni fa
        if days_diff >= 7:
            should_trigger = True
    ```

### Reminders (Scadenze)
*   **Tipo**: Periodic Task
*   **Codice**: `tasks/tasks.py` -> `generate_reminders_task`
*   **Frequenza**: Giornaliera (es. 08:00 AM)
*   **Logica Implementata**:

    **A. Scadenza Abbonamento Cliente**
    1.  Calcola la data di scadenza:
        *   Priorità a `data_rinnovo`.
        *   Fallback su `data_inizio_abbonamento + durata_programma_giorni`.
    2.  Controlla quanti giorni mancano a oggi (`days_to_expire`).
    3.  Genera un task se mancano esattamente **7 giorni** o **1 giorno**.

    ```python
    # Esempio Semplificato
    if expiration_date:
        days_to_expire = (expiration_date - today).days
        if days_to_expire in [7, 1]:
             # Crea Task
    ```

    **B. Scadenza Piano Nutrizionale**
    1.  Controlla il campo `nuova_dieta_dal` (data prevista prossimo aggiornamento).
    2.  Genera un task se mancano **7, 3 o 0 giorni**.

    ```python
    if client.nuova_dieta_dal:
        days = (client.nuova_dieta_dal - today).days
        if days in [7, 3, 0]:
             # Crea Task Scadenza Piano Nutrizionale
    ```

    **C. Scadenza Piano Allenamento**
    1.  Controlla il campo `nuovo_allenamento_il` (data aggiornamento scheda).
    2.  Genera un task se mancano **7, 3 o 0 giorni**.

    ```python
    if client.nuovo_allenamento_il:
        days = (client.nuovo_allenamento_il - today).days
        if days in [7, 3, 0]:
             # Crea Task Scadenza Allenamento
    ```

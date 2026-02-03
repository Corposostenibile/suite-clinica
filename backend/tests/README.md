# Test

## Email riepilogo check settimanale

**Test unitari** (mock di invio email e template):

```bash
cd backend
poetry run pytest tests/test_weekly_check_summary_email.py -v
```

**Test manuale** (invio email reale a un cliente):

1. Assicurati che nel DB ci sia almeno una `WeeklyCheckResponse` e che il cliente associato abbia `mail` valorizzato.
2. Dalla cartella `backend`:

   ```bash
   # Invia riepilogo per l’ultima risposta salvata
   poetry run python scripts/send_weekly_check_summary_email.py

   # Invia riepilogo per una risposta specifica (es. id 42)
   poetry run python scripts/send_weekly_check_summary_email.py 42
   ```

3. Controlla la casella `cliente.mail` (o i log se l’SMTP non è configurato).

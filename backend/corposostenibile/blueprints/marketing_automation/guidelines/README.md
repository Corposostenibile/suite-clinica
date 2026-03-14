# Linee guida per caption (Marketing Automation)

Copia qui i due PDF usati per istruire Claude:

- **Principi Corposostenibile.pdf** – principi di brand e corposostenibile
- **Come scrivere le Descrizioni.pdf** – come scrivere le descrizioni per social

Dopo averli copiati, dalla root del repo esegui:

```bash
cd backend && poetry run python -m corposostenibile.blueprints.marketing_automation.extract_guidelines_text
```

Lo script estrae il testo e scrive `guidelines_extracted.txt` in questa cartella; le linee guida in codice vengono aggiornate a partire da quel file.

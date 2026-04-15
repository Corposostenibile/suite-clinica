# Import TypeForm CSV - Documentazione

## Panoramica

Questo script importa i vecchi questionari TypeForm (file CSV) nel sistema nuovo, nella tabella `typeform_responses`.

I questionari TypeForm erano compilati dai pazienti prima della migrazione al nuovo sistema di check. Non devono essere confusi con i "Check Settimanali" - sono **Check Iniziali** compilati all'inizio del percorso.

## Struttura File

```
scripts/typeform_import/
├── TYPEFORM_IMPORT.md          # Questa documentazione
└── import_typeform_csv.py      # Script di import
```

## CSV Disponibili

I CSV si trovano nella cartella `typeforms_checks/` (esterna al repo):

| File | Descrizione | Tipo |
|------|-------------|------|
| Health Check Fisico Iniziale CorpoSostenibile 1.csv | Check iniziale fisico | Check 1/2 |
| Health Check Fisico Iniziale CorpoSostenibile 2.csv | Check iniziale fisico | Check 1/2 |
| Health Check Fisico Iniziale CorpoSostenibile 3.csv | Check iniziale fisico | Check 1/2 |
| Check Psico-Alimentare Iniziale CorpoSostenibile 1.csv | Check psicologico | Check 3 |
| Check Psico-Alimentare Iniziale CorpoSostenibile 2.csv | Check psicologico | Check 3 |
| Check Psico-Alimentare Iniziale CorpoSostenibile 3.csv | Check psicologico | Check 3 |
| check_fisico_posturale_iniziale.csv | Check postura (senza nome) | N/A |

## Utilizzo

### Dry Run (simulazione)

```bash
cd backend
poetry run python ../scripts/typeform_import/import_typeform_csv.py --dry-run
```

### Import Reale

```bash
cd backend
poetry run python ../scripts/typeform_import/import_typeform_csv.py --no-dry-run
```

### Opzioni

| Opzione | Descrizione |
|---------|-------------|
| `--dry-run` | Simula l'import senza salvare (default) |
| `--no-dry-run` | Esegue l'import reale |
| `--folder PATH` | Cartella contenente i CSV (default: `../typeforms_checks`) |

## Logica di Matching

Lo script cerca di associare ogni risposta TypeForm a un cliente esistente nel DB:

1. **Exact match**: confronto case-insensitive su `nome_cognome`
2. **Fuzzy match**: similiare >= 85% usando SequenceMatcher
3. **Unmatched**: se non trova match, la risposta è salvata senza `cliente_id`

## Struttura Dati Importati

### TypeFormResponse (tabella DB)

| Campo | Descrizione |
|-------|-------------|
| `typeform_id` | ID univoco dalla risposta TypeForm (# colonna CSV) |
| `first_name` | Nome |
| `last_name` | Cognome |
| `submit_date` | Data compilazione |
| `raw_response_data` | JSON con tutte le risposte grezze |
| `cliente_id` | FK a cliente (se match trovato) |
| `is_matched` | Boolean: se è stato associato a un cliente |
| `weight` | Peso (se presente nelle risposte) |

### Dati Grezzi (`raw_response_data`)

Contiene tutte le domande e risposte dal CSV, esclusi i campi metadata:

```json
{
  "*Peso*": "70",
  "*Altezza*": "172",
  "*Professione:*": "Insegnante",
  "Valuta la tua digestione:": "8",
  ...
}
```

## Visualizzazione Frontend

### Dove appaiono i TypeForm importati

I TypeForm importati appaiono in:

**Check Iniziali → Storico TypeForm**

Non appaiono nella scheda "Check Periodici" (che contiene solo Weekly, DCA, Minor).

### Modalità di visualizzazione

1. **Lista**: mostra data, peso (se presente)
2. **Dettaglio**: apre modal con:
   - Badge distintivo "TypeForm"
   - Griglia risposte (prime 20)
   - Foto (se presenti)

## Statistiche Import

- **Totale risposte**: ~18,000
- **Matchati**: ~17,700 (94%)
- **Non matchati**: ~500 (6%)

## Casi Particolari

### check_fisico_posturale_iniziale.csv

Questo file CSV ha 54 righe ma tutte senza nome/cognome, quindi nessuna è stata matchata. Queste risposte sono comunque importate ma non associabili a clienti.

### Duplicati

Lo script controlla `typeform_id` prima di importare. Se una risposta esiste già, viene saltata (idempotenza).

## Reset / Rilancio

Per rilanciare l'import (es. dopo aver aggiunto nuovi CSV):

```bash
# Verificare count attuale
poetry run python -c "
from corposostenibile import create_app
from corposostenibile.models import TypeFormResponse
app = create_app()
with app.app_context():
    print(f'Attuali: {TypeFormResponse.query.count()}')
"

# Rilanciare import
poetry run python ../scripts/typeform_import/import_typeform_csv.py --no-dry-run
```

## Query Utili

### Trovare un cliente con TypeForm

```sql
SELECT c.cliente_id, c.nome_cognome, COUNT(t.id) as tf_count
FROM clienti c
JOIN typeform_responses t ON c.cliente_id = t.cliente_id
GROUP BY c.cliente_id, c.nome_cognome
ORDER BY tf_count DESC
LIMIT 10;
```

### Risposte non matchate

```sql
SELECT id, first_name, last_name, submit_date
FROM typeform_responses
WHERE is_matched = false
ORDER BY submit_date DESC;
```

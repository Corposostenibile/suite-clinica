Script locali per ripristinare e popolare il DB di sviluppo.

Scopo:
- tenere separati gli script "operativi locali" dagli script di migrazione (`migration_scripts`)
- riusare l'output SQL migrato già generato in `backend/backups/migration_output_local/`

Flusso consigliato (dopo `./dev.sh reset-db manu`):
1. `poetry run python scripts/local_db_ops/stamp_heads.py`
2. `poetry run python scripts/local_db_ops/import_cached_migrated_sql.py`

Se `flask db current` / `flask db upgrade` falliscono per revisioni Alembic mancanti nel DB locale
(es. dump/import vecchi con `alembic_version` sporca), riallineare prima:
1. `poetry run python scripts/local_db_ops/repair_alembic_version.py`
2. `poetry run flask db current`

Note:
- `dev.sh reset-db` può fallire su `flask db upgrade` per mismatch storico Alembic/schema (`ghl_event_id` già presente).
- `stamp_heads.py` allinea Alembic allo schema creato da `flask create-db`.
- `repair_alembic_version.py` riscrive `alembic_version` con gli head reali presenti nel repository.
- `import_cached_migrated_sql.py` importa il dump SQL migrato locale e reimposta l'utente `dev@corposostenibile.it`.
- `backfill_support_types_from_program.py` popola `tipologia_supporto_nutrizione` / `tipologia_supporto_coach`
  a partire da `clienti.programma_attuale`, con supporto `--dry-run` e `--overwrite`.

Script manuali per seed/popolamento dati e utility locali.

Questa cartella contiene gli script che prima stavano direttamente in `backend/scripts/`.

Struttura consigliata:
- `migration_scripts/` -> migrazione schema/dati old->new
- `local_db_ops/` -> operazioni locali sul DB (stamp/import/reset helper)
- `dev_data_scripts/` -> seed, popolamento e script manuali per sviluppo/test

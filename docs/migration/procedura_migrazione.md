# Guida alla Migrazione Manuale del Database

Questa guida descrive la procedura utilizzata per migrare i dati dalla "Old Suite" alla nuova infrastruttura su Google Cloud Platform (Cloud SQL).

## Componenti Principali
- **Script di Migrazione**: `backend/scripts/migration_scripts/schema_comparator.py`
  - Gestisce il parsing del dump della vecchia Suite, la mappatura dei dati sul nuovo schema e la generazione di un dump SQL compatibile.
  - Include logica per gestire duplicati (`ON CONFLICT`) e mappe di priorità per rispettare i vincoli di Foreign Key.
- **Job Kubernetes**: `k8s/db-migration-job.yaml`
  - Esegue la migrazione all'interno del cluster GKE.
  - Utilizza Cloud SQL Auth Proxy per la connessione sicura al database.

## Procedura di Esecuzione

### 1. Caricamento dei Backup
I backup devono essere presenti nel Persistent Volume Claim `db-backups-pvc`. 
- Percorso backup nuova suite (schema): `/data/backups/new_suite_backups/`
- Percorso backup vecchia suite (dati): `/data/backups/old_suite_backups/`

### 2. Trucco della ConfigMap (Debug Veloce)
Per evitare di rebuildare l'immagine Docker ad ogni modifica dello script, carichiamo lo script come ConfigMap e lo montiamo nel Job:

```bash
# Crea/Aggiorna la ConfigMap dallo script locale
kubectl create configmap migration-script-config --from-file=backend/scripts/migration_scripts/schema_comparator.py -o yaml --dry-run=client | kubectl apply -f -
```

### 3. Avvio del Job
Assicurarsi che il file `k8s/db-migration-job.yaml` punti all'immagine corretta e monti la ConfigMap.

```bash
# Elimina eventuali job precedenti
kubectl delete job suite-clinica-db-migration --ignore-not-found

# Applica il Job
kubectl apply -f k8s/db-migration-job.yaml

# Monitora i log
POD_NAME=$(kubectl get pods -l job-name=suite-clinica-db-migration --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
kubectl logs -f $POD_NAME -c migrator
```

## Note Tecniche Importanti
- **Errori SQL**: Nel Job è impostato `psql -v ON_ERROR_STOP=0` per permettere alla migrazione di procedere anche se alcuni record orfani o sporchi del vecchio DB violano i vincoli di integrità.
- **Idempotenza**: Lo script usa `ON CONFLICT (...) DO NOTHING` per le tabelle principali. Se rilanciato, non duplicherà i dati esistenti.
- **Sequenze ID**: Lo script genera automaticamente i comandi `SELECT setval(...)` alla fine per sincronizzare i contatori degli ID autoincrementali con i dati migrati.

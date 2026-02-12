# Guida alla Migrazione Manuale (Database e Upload)

Questa guida descrive la procedura utilizzata per migrare i dati e i file dalla "Old Suite" alla nuova infrastruttura su Google Cloud Platform.

## Componenti Principali
- **Script di Migrazione Database**: `backend/scripts/migration_scripts/schema_comparator.py`
  - Gestisce il parsing del dump della vecchia Suite, la mappatura dei dati sul nuovo schema e la generazione di un dump SQL compatibile.
- **Job Migrazione Database**: `k8s/db-migration-job.yaml`
  - Esegue la migrazione all'interno del cluster GKE.
- **Job Migrazione Upload**: `k8s/uploads-migration-job.yaml`
  - Scarica l'archivio degli upload da Google Cloud Storage e lo estrae nel Persistent Volume Claim dedicato.

## Procedura di Esecuzione

### 1. Preparazione dei Backup (Database)
I backup devono essere presenti nel Persistent Volume Claim `db-backups-pvc`. 
- Percorso backup nuova suite (schema): `/data/backups/new_suite_backups/`
- Percorso backup vecchia suite (dati): `/data/backups/old_suite_backups/`

#### Creazione Backup Schema (Nuova Suite)
Se il backup dello schema della nuova suite non è disponibile o deve essere aggiornato, utilizzare il Job dedicato:

```bash
# Avvia il job di backup dello schema
kubectl apply -f k8s/db-backup-schema-job.yaml

# Attendi il completamento e verifica i log
kubectl logs -l job-name=suite-clinica-db-backup-schema -c backup-tool

# Una volta terminato, elimina il job
kubectl delete job suite-clinica-db-backup-schema
```
Il file verrà salvato in `/data/backups/new_suite_backups/schema_latest.sql` all'interno del PVC.

### 2. Trucco della ConfigMap (Debug Veloce)
Per evitare di rebuildare l'immagine Docker ad ogni modifica dello script, carichiamo lo script come ConfigMap e lo montiamo nel Job:

```bash
# Crea/Aggiorna la ConfigMap dallo script locale
kubectl create configmap migration-script-config --from-file=backend/scripts/migration_scripts/schema_comparator.py -o yaml --dry-run=client | kubectl apply -f -
```

### 3. Avvio del Job
Assicurarsi che il file `k8s/db-migration-job.yaml` punti all'immagine corretta e monti la ConfigMap.
Verificare inoltre che `OLD_SUITE_BACKUP` nel Job punti a un file realmente presente in `/data/backups/old_suite_backups/`.

```bash
# Se presente, rimuovi il pod manuale di debug (può bloccare il PVC per multi-attach)
kubectl delete pod manual-db-migrator --ignore-not-found

# Elimina eventuali job precedenti
kubectl delete job suite-clinica-db-migration --ignore-not-found

# Applica il Job
kubectl apply -f k8s/db-migration-job.yaml

# Monitora i log
POD_NAME=$(kubectl get pods -l job-name=suite-clinica-db-migration --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
kubectl logs -f $POD_NAME -c migrator
```

### 3.1 Diagnostica Rapida (se il Job fallisce)

```bash
# Stato pod del job
kubectl get pods -l job-name=suite-clinica-db-migration -o wide

# Eventi e motivo del fallimento (mount, secret, configmap, immagine, ecc.)
kubectl describe pod -l job-name=suite-clinica-db-migration

# Log container migrator
kubectl logs -l job-name=suite-clinica-db-migration -c migrator --tail=200

# Log Cloud SQL Proxy (connessione DB)
kubectl logs -l job-name=suite-clinica-db-migration -c cloud-sql-proxy --tail=200
```

Errori comuni:
- `OLD_SUITE_BACKUP not found`: path dump vecchia suite non valido o file assente nel PVC.
- `Multi-Attach error for volume ... db-backups-pvc`: esiste un altro pod (es. `manual-db-migrator`) che sta già montando il PVC.
- `configmap "migration-script-config" not found`: rieseguire la creazione ConfigMap (step 2).
- `secret "db-credentials" / "sql-proxy-key" not found`: secret mancanti nel namespace corrente.
- `pg_isready timeout` o errori proxy: credenziali Cloud SQL o connectivity issue verso istanza DB.

### 4. Migrazione degli Upload
I file di upload vengono migrati direttamente da un bucket Google Cloud Storage a un PVC dedicato (`uploads-pvc`).

```bash
# Crea il PVC se non esiste
kubectl apply -f k8s/uploads-pvc.yaml

# Avvia il job di migrazione degli upload
kubectl apply -f k8s/uploads-migration-job.yaml

# Monitora i log (operazione lunga, circa 70GB compressi)
kubectl logs -f job/suite-clinica-uploads-migration
```

Il job scarica l'archivio `.tar.gz` tramite pipe ed estrae i file direttamente in `/var/corposostenibile/uploads/` nel PVC, evitando di occupare spazio temporaneo sul disco del pod.

## Note Tecniche Importanti
- **Errori SQL**: Nel Job è impostato `psql -v ON_ERROR_STOP=0` per permettere alla migrazione di procedere anche se alcuni record orfani o sporchi del vecchio DB violano i vincoli di integrità.
- **Idempotenza**: Lo script usa `ON CONFLICT (...) DO NOTHING` per le tabelle principali. Se rilanciato, non duplicherà i dati esistenti.
- **Sequenze ID**: Lo script genera automaticamente i comandi `SELECT setval(...)` alla fine per sincronizzare i contatori degli ID autoincrementali con i dati migrati.
- **Filtro utenti/professionisti**: la migrazione importa tutti gli utenti non professionisti; per i ruoli `professionista`/`team_leader` importa solo i nominativi presenti in `OFFICIAL_ORGANIGRAMMA`. In questo modo `/team-lista` non mostra professionisti fuori lista ufficiale.
- **Campi obbligatori utenti**: durante la generazione dump vengono normalizzati `role`, `specialty` e booleani (`is_admin`, `is_active`, `is_external`, `is_trial`) per evitare errori `NOT NULL`/enum su `users`.
- **ConfigMap obbligatoria dopo modifiche script**: se si modifica `schema_comparator.py`, rieseguire sempre lo step 2 (update `migration-script-config`) prima di rilanciare il Job.

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
kubectl create configmap migration-script-config \
  --from-file=backend/scripts/migration_scripts/schema_comparator.py \
  --from-file=backend/scripts/migration_scripts/verify_schema_parity.py \
  -o yaml --dry-run=client | kubectl apply -f -
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
- `can't find '__main__' module in '/app/scripts/migration_scripts/verify_schema_parity.py'`: la ConfigMap `migration-script-config` contiene solo `schema_comparator.py`. Ricrearla includendo anche `verify_schema_parity.py`, poi rilanciare il Job (oppure completare manualmente solo gli step finali se il replay dati è già terminato).
- `secret "db-credentials" / "sql-proxy-key" not found`: secret mancanti nel namespace corrente.
- `pg_isready timeout` o errori proxy: credenziali Cloud SQL o connectivity issue verso istanza DB.
- `FailedScheduling` (es. `Insufficient memory/cpu` o `didn't match Pod's node affinity/selector`): capacità cluster insufficiente o vincoli zona/affinity incompatibili con il PVC.
- `Evicted: exceeded local ephemeral storage limit`: il pod ha saturato disco temporaneo locale. La versione aggiornata del Job usa temp su PVC (`/data/backups/migration_output/tmp`) e risorse `ephemeral-storage` aumentate.
- `SIGTERM` durante la generazione/import: in Autopilot può avvenire per scale-down/defrag del nodo; verificare eventi del namespace e rilanciare il Job.
- `BackoffLimitExceeded` dopo `ScaleDown`/`Killing` del pod: il nodo è stato ridotto durante una migration lunga. Aumentare `backoffLimit` e rilanciare il job.

### 3.2 Scheduling e Risorse (quando il pod resta Pending)

Se il pod del job non schedula:

```bash
# Vedi il motivo preciso
kubectl describe pod -l job-name=suite-clinica-db-migration

# Vedi risorse attuali dei nodi
kubectl get nodes -o wide
```

Linee guida:
- Evitare `nodeSelector` rigidi di zona nel Job, a meno che sia necessario.
- Non usare toleration verso nodi in dismissione (`autoscaling.gke.io/defrag-candidate`, `ToBeDeletedByClusterAutoscaler`) per job lunghi di migrazione: aumenta il rischio di kill a metà.
- Se c'è `Insufficient memory/cpu`, aumentare capacità del node pool oppure ridurre le `requests` del container `migrator` (non solo i `limits`).
- Se compare mismatch con PVC node affinity, usare nodi nella stessa zona del volume.

Valori consigliati per il container `migrator`:
- `requests`: `cpu: 300m`, `memory: 512Mi`, `ephemeral-storage: 2Gi`
- `limits`: `cpu: 1000m`, `memory: 3Gi`, `ephemeral-storage: 8Gi`

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
- **Ordine di import FK-aware**: lo script genera SQL ordinando le tabelle per dipendenze foreign key (prima principali, poi dipendenti) per ridurre errori FK non necessari.
- **Errori SQL**: Nel Job è impostato `psql -v ON_ERROR_STOP=0` per permettere alla migrazione di procedere anche se alcuni record orfani o sporchi del vecchio DB violano i vincoli di integrità.
- **Idempotenza**: Lo script usa `ON CONFLICT (...) DO NOTHING` per le tabelle principali. Se rilanciato, non duplicherà i dati esistenti.
- **Sequenze ID**: Lo script genera automaticamente i comandi `SELECT setval(...)` alla fine per sincronizzare i contatori degli ID autoincrementali con i dati migrati.
  - La sincronizzazione ora copre sia colonne `SERIAL` (`nextval(...)`) sia colonne `IDENTITY` (PostgreSQL 10+), per evitare errori `duplicate key ... pkey` dopo import.
- **Import completo**: lo script importa tutte le tabelle presenti nel dump old che esistono anche nello schema target.
- **Esclusione tabelle rumorose**: `activity_log` è esclusa di default dalla migrazione tramite `MIGRATION_EXCLUDED_TABLES` per evitare cascata di errori su FK storici non essenziali.
- **Modalità organigramma (opzionale)**: impostando `STRICT_ORGANIGRAM=1` lo script torna al comportamento restrittivo (filtra professionisti fuori organigramma ufficiale e ricostruisce `teams`/`team_members`).
- **Dati Check Azienda**: la migrazione deve includere anche le tabelle `weekly_checks`, `weekly_check_responses` e `weekly_check_link_assignments` (oltre a `dca_*` e `minor_*` se presenti), altrimenti la pagina `/check-azienda` risulta vuota anche con applicazione funzionante.
- **Campi obbligatori utenti**: durante la generazione dump vengono normalizzati `role`, `specialty` e booleani (`is_admin`, `is_active`, `is_external`, `is_trial`) per evitare errori `NOT NULL`/enum su `users`.
- **`team_members` derivata se assente nel dump**: nel ramo streaming (`STRICT_ORGANIGRAM=0`), se il dump non contiene righe `team_members`, lo script ricostruisce la tabella usando almeno i `head_id` dei `teams` e arricchisce con l'organigramma ufficiale (`OFFICIAL_TEAMS`) quando trova corrispondenze nome->utente.
- **Temp su PVC obbligatorio**: il Job imposta `TMPDIR` e `MIGRATION_TMP_DIR` su `/data/backups/migration_output/tmp`; evitare `/tmp` locale per non incorrere in eviction.
- **ConfigMap obbligatoria dopo modifiche script**: se si modifica `schema_comparator.py`, rieseguire sempre lo step 2 (update `migration-script-config`) prima di rilanciare il Job.

### Recovery rapido (errore finale dopo replay dati già completato)

Se il Job fallisce solo nel post-check finale (es. `verify_schema_parity.py`) ma il replay tabelle è già completato:

1. Fermare il Job rilanciato automatico (`kubectl delete job suite-clinica-db-migration`)
2. Correggere la ConfigMap (`migration-script-config`)
3. Eseguire manualmente sul pod backend:
   - `PYTHONPATH=/app python /app/scripts/migration_scripts/verify_schema_parity.py`
   - eventuale upsert utente `dev@corposostenibile.it`
   - snapshot conteggi finali

Questo evita di rifare l'intera migrazione dati.

### Verifica rapida post-migrazione (sequence autoincrement)

Se dopo la migrazione compare un errore tipo `duplicate key value violates unique constraint ..._pkey` su una tabella con `id` autoincrement, verificare/riallineare la sequence della tabella.

Esempio (`cliente_professionista_history`):

```sql
SELECT setval(
  pg_get_serial_sequence('cliente_professionista_history', 'id'),
  COALESCE((SELECT MAX(id) FROM cliente_professionista_history), 0) + 1,
  false
);
```

## Hardening Operativo (obbligatorio)

- **Mai usare `flask db stamp head` come fallback automatico**: se `flask db upgrade` fallisce, il deploy deve fallire. Lo `stamp` senza upgrade reale causa disallineamento schema/model (colonne e tabelle mancanti in produzione).
- **Rigenerare sempre lo schema target prima della migrazione dati**: lo script ora supporta refresh automatico del file `NEW_SUITE_BACKUP` via `pg_dump --schema-only` (env `MIGRATION_REFRESH_NEW_SCHEMA=1`, `MIGRATION_SCHEMA_REFRESH_STRICT=1`).
- **Fail-fast su parità schema**: dopo le migration Alembic, eseguire un check di parità schema/model (tabelle + colonne + enum attesi) e bloccare il deploy in caso di mismatch.

## Caso PVC Zonal Bloccato (GKE Autopilot)

Sintomo tipico:
- `0/n nodes are available: node(s) didn't match PersistentVolume's node affinity`
- eventi con `TriggeredScaleUp` seguiti da `FailedScaleUp ... GCE out of resources` nella zona del disco.

Causa:
- `db-backups-pvc` è legato a un disco zonale (es. `europe-west8-b`) ma il cluster non ha nodi schedulabili in quella zona.

Workaround pratico:
1. Fare snapshot del disco sorgente zonale.
2. Creare un nuovo disco da snapshot in una zona con nodi disponibili (es. `europe-west8-c`).
3. Creare `PV/PVC` statici legati al nuovo disco.
4. Puntare il Job migrazione al nuovo claim (`claimName` aggiornato).

## Caso Rollout Backend Bloccato per Multi-Attach (`uploads-pvc`)

Sintomo osservato (deploy applicativo, non job di migrazione):
- `kubectl rollout status deployment/suite-clinica-backend` resta in attesa
- il nuovo pod backend resta in `ContainerCreating`
- `kubectl describe pod ...` mostra `FailedAttachVolume` con `Multi-Attach error` su `uploads-pvc`

Causa:
- `uploads-pvc` è montato dal backend ed è `ReadWriteOnce`
- con strategia `RollingUpdate` il Deployment prova ad avviare il nuovo pod prima di terminare quello vecchio
- il volume non può essere montato contemporaneamente da entrambi i pod

Workaround operativo (downtime breve):
1. Scalare temporaneamente il deployment a `0` per liberare il PVC.
2. Scalare di nuovo a `1`.
3. Attendere il rollout del nuovo pod e poi rieseguire i passaggi post-deploy (migration/parity/seed) se Cloud Build è andato in timeout/failure.
4. Verificare anche lo step post-deploy di sync criteri AI (`sync_criteria_prod.py`): non fa parte della migrazione DB e va eseguito/controllato separatamente.

Comandi:
```bash
kubectl scale deploy/suite-clinica-backend --replicas=0
kubectl scale deploy/suite-clinica-backend --replicas=1
kubectl rollout status deployment/suite-clinica-backend --timeout=300s
```

Mitigazione raccomandata:
- usare una strategia di deploy compatibile con PVC `RWO` (`Recreate` oppure `RollingUpdate` con `maxSurge: 0`)

## Incidente Reale: 21 Febbraio 2026 (GKE scale-down)

Sintomo osservato:
- Job `suite-clinica-db-migration` terminato con `BackoffLimitExceeded`.
- Eventi pod: `ScaleDown` seguito da `Killing` dei container `migrator`/`cloud-sql-proxy`.

Causa:
- Pod di migrazione eseguito su nodo entrato in fase di rimozione/autoscaling durante un run lungo.

Mitigazione applicata:
1. `backoffLimit` alzato a `6` in `k8s/db-migration-job.yaml`.
2. Rimosse toleration verso nodi candidati a rimozione (`autoscaling.gke.io/defrag-candidate`, `ToBeDeletedByClusterAutoscaler`).
3. Rilancio del job con monitoraggio eventi/log fino a completamento.

Comando diagnostico rapido:
```bash
kubectl get events -n default --sort-by=.lastTimestamp | rg "suite-clinica-db-migration|ScaleDown|Killing|BackoffLimitExceeded"
```

# Analisi CI/CD GCP (stato operativo per deploy PWA)

Target: Developers / DevOps
Stack: GitHub -> Cloud Build -> Artifact Registry -> GKE Autopilot -> GCE Ingress (HTTPS)

Questo documento descrive la pipeline attuale e i manifest necessari per esporre l'app come sito web normale + PWA su dominio HTTPS.

## 1) Flusso deploy

1. Push su branch trigger (es. `main`)
2. Cloud Build esegue `cloudbuild.yaml`
3. Build immagine Docker multi-stage (frontend React build + backend Flask runtime)
4. Push immagine su Artifact Registry
5. Deploy su GKE con `gke-deploy`:
- `k8s/deployment.yaml`
- `k8s/service.yaml`
- `k8s/frontendconfig.yaml`
- `k8s/managed-certificate.yaml`
- `k8s/ingress.yaml`
- `k8s/hpa.yaml`
6. Post-deploy:
- migrazioni DB (`flask db upgrade` via `kubectl exec`)
- seed check iniziali (`seed_initial_checks.py` via `kubectl exec`, automatico in `cloudbuild.yaml`)
- sync criteri AI (`PYTHONPATH=/app python /app/scripts/migration_scripts/sync_criteria_prod.py` via `kubectl exec`)

Nota operativa:
- `sync_criteria_prod.py` è uno step post-deploy separato dalla migrazione DB
- in produzione deve aggiornare i criteri degli utenti esistenti; la creazione automatica utenti mancanti va evitata (modalità safe di default)

## 2) Componenti Kubernetes rilevanti per PWA

### 2.1 Deployment (`k8s/deployment.yaml`)

Punti chiave:
- app esposta internamente su `:8080` (gunicorn)
- cookie/sessione configurati per HTTPS:
  - `SESSION_COOKIE_SECURE=true`
  - `SESSION_COOKIE_SAMESITE=Lax`
  - `PREFERRED_URL_SCHEME=https`
- `SPA_HANDLE_AUTH_ROUTES=1` per servire le route `/auth/*` tramite SPA React
- per push PWA task servono anche:
  - `VAPID_PUBLIC_KEY`
  - `VAPID_PRIVATE_KEY`
  - `VAPID_CLAIMS_SUB`

### 2.2 Service (`k8s/service.yaml`)

- tipo: `ClusterIP`
- annotation NEG: `cloud.google.com/neg: '{"ingress": true}'`
- porta servizio: `80 -> 8080`

### 2.3 Ingress (`k8s/ingress.yaml`)

- classe: `gce`
- host: `clinica.corposostenibile.com`
- path `/*` verso `suite-clinica-service:80`
- annoto:
  - managed certificate (`clinica-corposostenibile-cert`)
  - frontend config (redirect HTTPS)

### 2.4 Managed Certificate (`k8s/managed-certificate.yaml`)

- certificato TLS gestito da Google per il dominio pubblico

### 2.5 FrontendConfig (`k8s/frontendconfig.yaml`)

- redirect HTTP -> HTTPS abilitato

## 3) URL e comportamento atteso

URL canonici (no prefisso tecnico):
- `https://<dominio>/auth/login`
- `https://<dominio>/clienti-lista`

PWA:
- `https://<dominio>/manifest.webmanifest`
- `https://<dominio>/sw.js`

API backend sullo stesso host:
- `https://<dominio>/api/...`
- `https://<dominio>/ghl/...`
- `https://<dominio>/review/...`
- endpoint push:
  - `https://<dominio>/api/push/public-key`
  - `https://<dominio>/api/push/subscriptions`

## 4) Cloud Build (estratto)

`cloudbuild.yaml` deploya i manifest principali e aggiorna l'immagine:

```yaml
- name: 'gcr.io/cloud-builders/gke-deploy'
  args:
    - run
    - --filename=k8s/deployment.yaml
    - --filename=k8s/service.yaml
    - --filename=k8s/frontendconfig.yaml
    - --filename=k8s/managed-certificate.yaml
    - --filename=k8s/ingress.yaml
    - --filename=k8s/hpa.yaml
    - --location=europe-west8
    - --cluster=suite-clinica-cluster-prod
    - --image=europe-west8-docker.pkg.dev/$PROJECT_ID/suite-clinica-repo/backend:$COMMIT_SHA
```

Nota:
- le env runtime documentate devono essere presenti nel deployment GKE (`k8s/deployment.yaml`)
- i valori sensibili vanno in Secret Kubernetes (es. `k8s/app-integrations-secret.example.yaml` -> `app-integrations`)
- se il deploy viene lanciato manualmente con `gcloud builds submit`, passare sempre `COMMIT_SHA` nelle substitutions (altrimenti il tag immagine resta vuoto e lo step Docker fallisce):

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=COMMIT_SHA=$(git rev-parse HEAD) \
  .
```

## 5) Checklist go-live GCP

1. DNS: punta il dominio all'IP del Load Balancer creato da Ingress
2. Certificato managed: stato `Active`
3. Pod backend `Ready`
4. Migrazioni DB applicate (obbligatorio, incluse tabelle push)
5. Seed check iniziali applicato (Check 1 PDF + Check 2 mockup)
6. Verifica endpoint:

```bash
kubectl exec deploy/suite-clinica-backend -- flask db upgrade
kubectl exec deploy/suite-clinica-backend -- python corposostenibile/blueprints/client_checks/scripts/seed_initial_checks.py
curl -I https://<dominio>/auth/login
curl -I https://<dominio>/manifest.webmanifest
curl -I https://<dominio>/sw.js
curl -i https://<dominio>/api/auth/me | head -n 20
```

Post-deploy manuale (se il build Cloud fallisce dopo il rollout immagine):

```bash
kubectl exec deploy/suite-clinica-backend -c backend -- bash -lc '
  set -euo pipefail
  flask db upgrade
  PYTHONPATH=/app python /app/scripts/migration_scripts/verify_schema_parity.py
'
```

### Variabili env consigliate (GHL + Respond.io)

Per il flusso lead GHL -> invio check iniziali -> sync chat Respond.io, configurare almeno:

- `RESPOND_IO_API_TOKEN`
- `RESPOND_IO_API_BASE_URL` (default: `https://api.respond.io/v2`)
- `RESPOND_IO_DEFAULT_CHANNEL_ID` (opzionale; se assente usa l'ultimo canale del contatto)
- `GHL_GLOBAL_STATUS_WEBHOOK_MODE` (`mock` default, oppure `live`)
- `GHL_GLOBAL_STATUS_WEBHOOK_URL` (obbligatoria in `live`; endpoint ricezione evento stato globale cliente)

Nota operativa:
- all'arrivo del lead (`/ghl/webhook/opportunity-data`) il bridge assegna la conversazione al `health_manager_email` ricevuto da GHL usando l'identifier del contatto (`phone:` preferito, fallback `email:`) e invia un messaggio testuale mock.
- quando `stato_cliente` globale passa a `pausa` o `ghost`, viene emesso evento `cliente.global_status.changed` dopo commit DB (in `mock` viene loggato senza chiamata HTTP esterna).

Push check (utente autenticato):

```bash
curl -i https://<dominio>/api/push/public-key
```

## 6) Problemi comuni

### 6.1 Certificato managed resta in provisioning

- DNS non ancora propagato o non puntato al LB
- host in `managed-certificate.yaml` non coerente col dominio reale

### 6.2 Login route non renderizzata da SPA

- verificare env `SPA_HANDLE_AUTH_ROUTES=1` in `k8s/deployment.yaml`
- verificare che il build frontend sia incluso nell'immagine Docker

### 6.3 Sessione non persistente in produzione

- verificare `SESSION_COOKIE_SECURE=true`
- verificare che l'accesso avvenga solo in HTTPS

### 6.4 Push task non arriva

- verificare variabili VAPID nel deployment
- verificare migrazione `push_subscriptions` applicata
- verificare che l'utente abbia autorizzato le notifiche nel browser/PWA

### 6.5 Rollout bloccato con PVC `uploads-pvc` (Multi-Attach)

Sintomo:
- `kubectl rollout status deployment/suite-clinica-backend` resta in attesa
- il nuovo pod backend resta `ContainerCreating`
- eventi pod con `FailedAttachVolume ... Multi-Attach error` sul PVC `uploads-pvc`

Causa:
- `uploads-pvc` è montato in `ReadWriteOnce`
- il Deployment usa `RollingUpdate` (`maxSurge > 0`), quindi durante il rollout prova a tenere vecchio e nuovo pod insieme
- il nuovo pod non può montare il PVC finché il vecchio pod non rilascia il volume

Workaround operativo (downtime breve):
1. Forzare lo spegnimento del pod vecchio o scalare il deployment a `0`.
2. Riportare il deployment a `1`.
3. Verificare rollout e readiness.

Comandi utili:

```bash
kubectl describe pod <nuovo-pod>
kubectl scale deploy/suite-clinica-backend --replicas=0
kubectl scale deploy/suite-clinica-backend --replicas=1
kubectl rollout status deployment/suite-clinica-backend --timeout=900s
```

Mitigazione consigliata:
- configurare una strategia di rollout compatibile con PVC `RWO` (es. `Recreate` oppure `RollingUpdate` con `maxSurge: 0` e `maxUnavailable: 1`)

Stato attuale su `main` (4 marzo 2026):
- `k8s/deployment.yaml` è a `replicas: 1` e usa `RollingUpdate` con `maxSurge: 1` e `maxUnavailable: 0`
- `k8s/hpa.yaml` è presente ma con `minReplicas: 1` e `maxReplicas: 1` (nessun autoscaling effettivo)
- con PVC `uploads-pvc` in `ReadWriteOnce`, questa combinazione può riattivare il rischio `Multi-Attach` nei rollout
- mitigazione consigliata: tornare a `maxSurge: 0`/`maxUnavailable: 1` oppure usare `Recreate` finché `uploads-pvc` resta `RWO`

### 6.6 `sync_criteria_prod.py` fallisce dopo riordino script

Sintomo:
- step post-deploy Cloud Build termina con errore file non trovato per `Criteri Ai.xlsx`

Possibile causa:
- lo script `sync_criteria_prod.py` usa un path relativo/hardcoded non più valido dopo il riordino di `backend/scripts`

Impatto:
- non blocca il deploy dell'immagine o le migration Alembic
- blocca solo la sincronizzazione criteri automatica post-deploy

Verifica manuale:

```bash
kubectl exec deploy/suite-clinica-backend -c backend -- bash -lc '
  ls -l /app/scripts/migration_scripts/sync_criteria_prod.py
  ls -l "/app/corposostenibile/blueprints/sales_form/assegnazioni_xlsx/Criteri Ai.xlsx"
'
```

### 6.7 Cloud Build `FAILURE` ma build/push/deploy immagine riusciti (timeout rollout)

Sintomo (caso reale 26 febbraio 2026):
- Cloud Build fallisce allo step `kubectl rollout status ... --timeout=300s`
- gli step precedenti (`docker build`, `docker push`, `kubectl set image`) risultano completati
- il nuovo pod backend non raggiunge `Ready` entro timeout durante il warm-up

Causa:
- il backend può impiegare più di `300s` a superare la readiness in alcuni rollout (startup lento / warm-up)
- Cloud Build marca `FAILURE` per timeout rollout, anche se immagine e deploy sono già stati applicati

Mitigazioni applicate:
- `cloudbuild.yaml`: timeout rollout aumentato a `900s`
- `k8s/deployment.yaml`: aggiunta `startupProbe` sul backend per evitare restart/liveness prematuri durante lo startup
- `k8s/deployment.yaml`: `readinessProbe`/`livenessProbe` rese meno aggressive (timeout/failure threshold più tolleranti)

Verifica consigliata:
```bash
kubectl get pods -n default | grep suite-clinica-backend
kubectl describe pod <pod-backend>
kubectl rollout status deployment/suite-clinica-backend --timeout=900s
curl -I https://clinica.corposostenibile.com/auth/login
```

Nota operativa:
- se la produzione va giù durante il rollout (1 replica), fare rollback immediato dell'immagine e indagare `/health`:

```bash
kubectl set image deployment/suite-clinica-backend \
  backend=europe-west8-docker.pkg.dev/suite-clinica/suite-clinica-repo/backend:<tag_stabile>
```

## 8) Strategia di Test Professionale (Continuous Integration)

Per garantire la stabilità della pipeline in produzione (evitando timeout e race condition), è stata definita la seguente strategia professionale:

### 8.1 Ottimizzazione Suite di Test
- **Esecuzione Sequenziale (Stato Attuale):** La suite viene eseguita tramite uno script `run_tests.sh` che isola i moduli (Auth, Team, Calendar, ecc.). Questo previene corruzioni del database e permette un report dettagliato per modulo.
- **Strategia Transazionale:** Ogni test viene avvolto in transazioni (savepoints) invece di `TRUNCATE CASCADE`, riducendo drasticamente il tempo di setup/teardown.
- **Factory Scope:** Le Factory Boy sono configurate a livello di sessione (`session-scope`) per evitare il re-setup costante.

### 8.2 Roadmap per Pipeline CI/CD Scalabile
Per automatizzare i test in Cloud Build/GitHub Actions, la pipeline dovrà evolvere verso:
1. **Parallelizzazione (Bucket Partitioning):** Eseguire i test in parallelo su "bucket" definiti, garantendo che ogni worker operi su un proprio database isolato (dinamicamente creato tramite variabili d'ambiente `TEST_DB_NAME_{WORKER_ID}`).
2. **Database Effimero:** Utilizzare un container Postgres "sidecar" nei manifest di CI/CD, eliminando la dipendenza da un database fisico esterno.
3. **Reportistica:** Esportare i risultati in formato Junit XML per integrare le dashboard di fallimento direttamente su GitHub/GCP Cloud Build.

### 8.3 Comando di esecuzione pipeline
In fase di test della pipeline, utilizzare:
```bash
bash ./backend/run_tests.sh
```
Questo comando garantisce un'esecuzione deterministica dell'intera suite.


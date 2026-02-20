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
6. Post-deploy:
- migrazioni DB (`flask db upgrade` via `kubectl exec`)
- seed check iniziali (`seed_initial_checks.py` via `kubectl exec`, automatico in `cloudbuild.yaml`)
- sync criteri (`python scripts/sync_criteria_prod.py` via `kubectl exec`)

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
- host: `suite-clinica.duckdns.org`
- path `/*` verso `suite-clinica-service:80`
- annoto:
  - managed certificate
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
    - --location=europe-west8
    - --cluster=suite-clinica-cluster-prod
    - --image=europe-west8-docker.pkg.dev/$PROJECT_ID/suite-clinica-repo/backend:$COMMIT_SHA
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

### Variabili env consigliate (GHL + Respond.io)

Per il flusso lead GHL -> invio check iniziali -> sync chat Respond.io, configurare almeno:

- `RESPOND_IO_API_TOKEN`
- `RESPOND_IO_API_BASE_URL` (default: `https://api.respond.io/v2`)
- `RESPOND_IO_DEFAULT_CHANNEL_ID` (opzionale; se assente usa l'ultimo canale del contatto)

Nota operativa:
- all'arrivo del lead (`/ghl/webhook/opportunity-data`) il bridge assegna la conversazione al `health_manager_email` ricevuto da GHL usando l'identifier del contatto (`phone:` preferito, fallback `email:`) e invia un messaggio testuale mock.

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

## 7) Hardening raccomandato

- Spostare segreti (DB/Redis/SECRET_KEY) in Secret Manager + Kubernetes Secret
- Evitare credenziali hardcoded nei manifest
- Aggiungere policy di rollout e probe avanzate dove necessario

# CI/CD Test Integration - GCP Cloud Build

Questo documento descrive come integrare la suite di test (325 test) nel pipeline CI/CD GCP.

## 📋 Sommario

- **File Test**: 8 file con 325 test complessivi
- **Copertura**: 61/63 endpoint API (97%)
- **Tempo Esecuzione**: ~30 minuti (full suite)
- **Cloud Build Config**: `cloudbuild-test.yaml`

---

## 🏗️ Architettura CI/CD

```
GitHub Push (PR o main)
    ↓
Cloud Build Trigger
    ├─ cloudbuild.yaml (Build + Deploy to Production)
    └─ cloudbuild-test.yaml (Test Suite Validation)
        ├─ PostgreSQL Test DB (via Cloud SQL Proxy)
        ├─ Redis (Celery broker - optional)
        └─ Coverage Report → Cloud Storage
```

### Due Pipeline Separate

1. **cloudbuild.yaml** (Main Build Pipeline)
   - Build immagine Docker
   - Push su Artifact Registry
   - Deploy a GKE
   - Migrazioni DB
   - Sync criteri

2. **cloudbuild-test.yaml** (Test Pipeline - NUOVO)
   - Esegue test suite
   - Genera coverage report
   - Upload artifacts a Cloud Storage
   - Notifica risultati

---

## 🔧 Setup GCP

### 1. Creare Cloud Storage Bucket per Test Artifacts

```bash
gcloud storage buckets create gs://PRODJECTID-suite-clinica-test-artifacts \
  --location=EUROPE \
  --project=PROJECTID
```

### 2. Creare Service Account per Test Runner

```bash
# Creare service account
gcloud iam service-accounts create suite-clinica-test-runner \
  --display-name="Suite Clinica Test Runner" \
  --project=PROJECTID

# Assegnare permessi Cloud SQL
gcloud projects add-iam-policy-binding PROJECTID \
  --member=serviceAccount:suite-clinica-test-runner@PROJECTID.iam.gserviceaccount.com \
  --role=roles/cloudsql.client

# Assegnare permessi Cloud Storage
gcloud projects add-iam-policy-binding PROJECTID \
  --member=serviceAccount:suite-clinica-test-runner@PROJECTID.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin

# Assegnare permessi Cloud Build
gcloud projects add-iam-policy-binding PROJECTID \
  --member=serviceAccount:suite-clinica-test-runner@PROJECTID.iam.gserviceaccount.com \
  --role=roles/cloudbuild.builds.editor
```

### 3. Configurare Cloud Build Trigger

#### Per test su Pull Requests:

```bash
gcloud builds triggers create github \
  --name="suite-clinica-test-pr" \
  --repo-name=suite-clinica \
  --repo-owner=Corposostenibile \
  --push-branch="^(main|develop|feature/.+)$" \
  --build-config=cloudbuild-test.yaml \
  --project=PROJECTID
```

#### Per test su main branch (pre-deploy):

```bash
gcloud builds triggers create github \
  --name="suite-clinica-test-main" \
  --repo-name=suite-clinica \
  --repo-owner=Corposostenibile \
  --push-branch="^main$" \
  --build-config=cloudbuild-test.yaml \
  --service-account=projects/PROJECTID/serviceAccounts/suite-clinica-test-runner@PROJECTID.iam.gserviceaccount.com \
  --project=PROJECTID
```

---

## 📊 Test Execution Flow

### Step 1: Test Discovery
```
tests/api/
├── test_auth_api.py (50 tests)
├── test_customers_api.py (21 tests)
├── test_team_api.py (70 tests)
├── test_calendar_api.py (50 tests)
├── test_quality_api.py (52 tests)
├── test_tasks_api.py (26 tests)
├── test_review_api.py (25 tests)
└── test_integrations_api.py (31 tests)
                          ↓
                     325 tests total
```

### Step 2: Test Execution (in Cloud Build)

```bash
# 1. Setup Environment
export FLASK_ENV=testing
export DATABASE_URL=postgresql://test:test@postgres:5432/suite_clinica_test

# 2. Install Dependencies
poetry install

# 3. Run Tests with Coverage
poetry run pytest tests/api/ \
  -v \
  --cov=corposostenibile \
  --cov-report=html \
  --junit-xml=test-results.xml
```

### Step 3: Artifact Upload

```
test-results.xml
test-report.html
coverage-report/
test-output.log
    ↓
gs://PROJECTID-suite-clinica-test-artifacts/build-$BUILD_ID/
```

---

## 🎯 Test Categories & Endpoints

| Categoria | Tests | Endpoints | Status |
|-----------|-------|-----------|--------|
| Auth | 50 | 6 | ✅ Passing |
| Customers | 21 | 4 | ✅ Passing |
| Team | 70 | 31 | 🔄 67% passing |
| Calendar | 50 | 16 | ✅ Passing |
| Quality | 52 | 10 | 🔄 Verification pending |
| Tasks | 26 | 5 | 🔄 New |
| Review/Training | 25 | 8 | 🔄 New |
| Integrations | 31 | 14 | 🔄 New |
| **TOTAL** | **325** | **61** | **97% Coverage** |

---

## 🚀 Comandi Utili

### Eseguire Test Localmente

```bash
# Setup ambiente di test
cd backend
export FLASK_ENV=testing
export DATABASE_URL=postgresql://username:password@localhost:5432/suite_clinica_test

# Install dipendenze
poetry install

# Run all tests
poetry run pytest tests/api/ -v

# Run specific category
poetry run pytest tests/api/test_auth_api.py -v

# Run con coverage
poetry run pytest tests/api/ --cov=corposostenibile --cov-report=html

# Run con output dettagliato
poetry run pytest tests/api/ -xvs
```

### Lanciare Build Manualmente

```bash
# Trigger test build
gcloud builds submit \
  --config=cloudbuild-test.yaml \
  --substitutions=BRANCH_NAME=main \
  .

# Trigger main build
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=COMMIT_SHA=$(git rev-parse HEAD) \
  .
```

### Visualizzare Risultati

```bash
# Visualizzare test artifacts
gsutil ls gs://PROJECTID-suite-clinica-test-artifacts/

# Download coverage report
gsutil -m cp -r \
  gs://PROJECTID-suite-clinica-test-artifacts/build-BUILD_ID/coverage-report \
  ./local-coverage/
```

---

## ⚙️ Configurazione Cloud SQL Proxy

Il `cloudbuild-test.yaml` usa Cloud SQL Proxy per connessione al database test. Configurazione:

```yaml
env:
  - DATABASE_URL=postgresql://test:test@postgres:5432/suite_clinica_test
```

**Prerequisiti:**
1. Cloud SQL instance con database `suite_clinica_test`
2. User `test` con password configurato
3. Service account con permesso `cloudsql.client`

---

## 📝 Pre-requisiti per Environment di Test

### Database Test
```sql
CREATE DATABASE suite_clinica_test;
CREATE USER test WITH PASSWORD 'test';
GRANT ALL PRIVILEGES ON DATABASE suite_clinica_test TO test;
```

### Environment Variables (in Cloud Build Secret Manager)

```bash
# Setup secrets
gcloud secrets create DB_TEST_URL --data-file=- <<EOF
postgresql://test:test@postgres:5432/suite_clinica_test
EOF

gcloud secrets create FLASK_ENV --data-file=- <<EOF
testing
EOF
```

---

## 🔍 Debugging Test Failures

### View Cloud Build Logs

```bash
# Stream build logs
gcloud builds log BUILD_ID --stream

# Tail last 100 lines
gcloud builds log BUILD_ID | tail -100

# Filter for errors
gcloud builds log BUILD_ID | grep -i error
```

### Local Test Reproduction

```bash
# Eseguire same test che fallisce in Cloud Build
poetry run pytest tests/api/test_auth_api.py::TestAuthLogin::test_login_success_with_valid_credentials -xvs

# Con traceback completo
poetry run pytest -xvs --tb=long
```

### Coverage Analysis

```bash
# Generate coverage report
poetry run pytest tests/api/ --cov=corposostenibile --cov-report=html

# View report
open htmlcov/index.html
```

---

## 🚨 Common Issues & Troubleshooting

### Database Connection Timeout

**Sintomo**: `psycopg2.OperationalError: could not connect to server`

**Soluzione:**
1. Verificare Cloud SQL instance è running
2. Verificare security groups consento connessioni da Cloud Build
3. Verificare credentials database sono corretti

### Import Errors in Tests

**Sintomo**: `ModuleNotFoundError: No module named 'corposostenibile'`

**Soluzione:**
```bash
cd backend  # MUST be in backend directory
poetry run pytest tests/api/
```

### Test Timeout

**Sintomo**: Test stuck for >30 minutes

**Soluzione:**
- Aumentare `timeout` in `cloudbuild-test.yaml` (attualmente 1800s)
- Parallelizzare test con `-n` flag (pytest-xdist)
- Controllare query slow in DB test

### Artifact Upload Fails

**Sintomo**: `AccessDenied` error su gsutil cp

**Soluzione:**
1. Verificare service account ha `roles/storage.objectAdmin`
2. Verificare bucket esiste
3. Verificare path è corretto

---

## 📈 Performance Optimization

### Parallelizzare Test Execution

```bash
# Install pytest-xdist
poetry add pytest-xdist --group dev

# Run tests in parallel (4 workers)
poetry run pytest tests/api/ -n 4
```

### Cache Docker Layers

Nel `cloudbuild-test.yaml`, usa `--cache-from` per velocizzare build:

```dockerfile
docker build \
  --cache-from gcr.io/PROJECT_ID/suite-clinica:latest \
  -t suite-clinica:test .
```

### Skip Slow Tests in CI

Creare marker per test lenti:

```python
@pytest.mark.slow
def test_slow_operation():
    pass
```

Eseguire senza slow tests:

```bash
poetry run pytest tests/api/ -m "not slow"
```

---

## 🔐 Security Considerations

1. **Database Credentials**: Usa Secret Manager, mai inline
2. **Service Account Keys**: Preferisci Workload Identity
3. **Coverage Report**: Non esporre token o password nei report
4. **Test Data**: Usa fixture con dati mock, non dati production

---

## 📞 Support

Per problemi:
1. Verificare CloudBuild logs: `gcloud builds log BUILD_ID`
2. Eseguire test localmente per riprodurre issue
3. Controllare test fixtures e conftest per errors setup

---

## ✅ Checklist Deployment

- [ ] `cloudbuild-test.yaml` committato
- [ ] Cloud Storage bucket creato
- [ ] Service account configurato
- [ ] Cloud Build trigger impostato
- [ ] Database test configurato
- [ ] Test eseguiti localmente con successo
- [ ] Coverage report generato
- [ ] Secrets configurati in Secret Manager
- [ ] IAM permissions verificati
- [ ] First Cloud Build run eseguito e verificato


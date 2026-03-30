# Suite Clinica - Test Suite Documentation

## Executive Summary

Comprehensive pytest test infrastructure for suite-clinica backend covering **67 frontend API endpoints**.

**Current Status:** 326 tests implemented, **324 passing** (99.4%)

| Category | Tests | Status |
|----------|-------|--------|
| Authentication API | 51 | 50 passing, 1 pre-existing bug |
| Customer API | 21 | 100% passing |
| Team API | 70 | 100% passing |
| Calendar API | 50 | 100% passing |
| Quality API | 52 | 100% passing |
| Tasks API | 26 | 100% passing |
| Review/Training API | 25 | 100% passing |
| Integrations API | 31 | 30 passing, 1 pre-existing bug |

**Performance:** 326 test in ~2 min 30s (invocazione singola, sequenziale)

---

## Test Infrastructure (Aggiornato 2026-03-30)

### Transaction Rollback Isolation (SAVEPOINT pattern)

L'infrastruttura di test e' stata migrata da **TRUNCATE CASCADE** a **transaction rollback** per l'isolamento dei test. Questo approccio e' ~10-50x piu' veloce del TRUNCATE su ~40 tabelle.

**Come funziona:**
1. Prima di ogni test, si apre una connessione dedicata e si avvia una transazione esterna
2. `FSASession.get_bind()` viene monkey-patched per instradare tutte le query attraverso questa connessione
3. La sessione viene configurata con `join_transaction_mode="create_savepoint"`: ogni `session.commit()` crea/rilascia un SAVEPOINT invece di un vero COMMIT
4. A fine test, la transazione esterna viene rollbackata — nessun dato persiste nel DB
5. `expire_on_commit=False` previene `DetachedInstanceError` quando Flask-SQLAlchemy fa teardown della sessione dopo le request HTTP

**File modificati:**

| File | Modifica |
|------|----------|
| `tests/conftest.py` | Fixture `db_session` riscritta: SAVEPOINT rollback invece di TRUNCATE. Usa `join_transaction_mode="create_savepoint"`, monkey-patch di `get_bind()`, e `expire_on_commit=False`. |
| `corposostenibile/middleware/tracking.py` | Aggiunto early return quando `app.config['TESTING']` e' true — il middleware tracking usa `db.engine.begin()` che apre una connessione separata, incompatibile con l'isolamento transazionale. |
| `run_tests.sh` | Riscritto: invocazione singola di pytest con flag `--parallel`/`--seq`. |

### Dettagli tecnici del fix

**Problema 1 — FK violation nel tracking middleware:**
Il middleware `tracking.py` (riga 62) usa `db.engine.begin()` che apre una connessione **separata dal pool**, completamente esterna alla transazione di test. Quella connessione non vede i dati uncommitted (es. l'utente di test) → FK constraint fail su `global_activity_log.user_id_fkey`. **Fix:** skip del tracking middleware quando `TESTING=True`.

**Problema 2 — DetachedInstanceError:**
Dopo una HTTP request, il teardown di Flask-SQLAlchemy chiama `db.session.remove()`, che distacca gli oggetti ORM. Quando il codice di test accede successivamente agli attributi (es. `user.email`), questi tentano lazy-load ma non sono piu' legati a una sessione. **Fix:** `expire_on_commit=False` nella configurazione della sessione di test.

---

## Bug pre-esistenti (non legati all'infrastruttura di test)

I seguenti 2 test falliscono per bug applicativi, **non** per problemi dell'infrastruttura di test:

1. **`test_impersonate_non_admin`** (`test_auth_api.py:612`)
   - **Atteso:** 403 Forbidden
   - **Ricevuto:** 405 Method Not Allowed
   - **Causa:** Il test usa il metodo HTTP sbagliato oppure la route non gestisce quel metodo

2. **`test_leads_requires_login`** (`test_integrations_api.py:329`)
   - **Atteso:** 401 Unauthorized o 302 Found
   - **Ricevuto:** 200 OK
   - **Causa:** L'endpoint `/leads` non applica `@login_required` o equivalente

---

## Frontend API Endpoints Complete Mapping

### AUTENTICAZIONE (6 endpoint)

| Method | Endpoint | Called By | Params | Auth |
|--------|----------|-----------|--------|------|
| POST | /auth/login | Login form | email, password | No |
| POST | /auth/logout | Logout button | - | Yes |
| POST | /auth/forgot-password | Forgot password form | email | No |
| GET | /auth/me | App init, Profile | - | Yes |
| GET | /auth/impersonate/users | Admin panel | - | Yes (Admin) |
| POST | /auth/stop-impersonation | Admin panel | - | Yes (Admin) |

### TEAM & UTENTI (11 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /team/members | Team page | - |
| POST | /team/members | Add member form | name, email, role |
| GET | /team/departments | Team page | - |
| GET | /team/stats | Dashboard | - |
| GET | /team/admin-dashboard-stats | Admin dashboard | - |
| GET | /team/teams | Team management | - |
| POST | /team/teams | Create team form | name, description |
| GET | /team/capacity | Dashboard | - |
| GET | /team/api/assegnazioni | Assignment page | - |
| GET | /trial-users | Admin panel | - |
| POST | /trial-users | Create trial form | user_id, trial_type |

### CALENDAR & EVENTS (11 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /api/connection-status | Calendar page init | - |
| GET | /disconnect | Calendar page | - |
| GET | /api/events | Calendar grid | start, end, filters |
| POST | /api/events | Create event form | title, start, end, etc |
| POST | /api/sync-single-event | Event update | event_id, data |
| GET | /api/team/users | Event attendees | - |
| GET | /api/customers/search | Event customer link | q (search) |
| GET | /api/customers/list | Event dropdown | - |
| GET | /api/admin/tokens/status | Admin panel | - |
| POST | /api/admin/tokens/refresh | Token management | - |
| POST | /api/admin/tokens/cleanup | Token cleanup | - |

### CLIENTI/PAZIENTI (4 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /customers/api/search | Client list search | q (search term) |
| GET | /customers/{id}/stati/{servizio}/storico | Client detail | - |
| GET | /customers/{id}/patologie/storico | Medical history | - |
| GET | /customers/{id}/nutrition/history | Nutrition history | - |

### QUALITA' & REVIEW (5 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /quality/api/weekly-scores | Quality dashboard | - |
| POST | /quality/api/calculate | Calculate quality | - |
| GET | /quality/api/dashboard/stats | Quality dashboard | - |
| POST | /quality/api/calcola-trimestrale | Quarterly calculation | - |
| GET | /quality/api/quarterly-summary | Quarterly view | - |

### TASKS/COMPITI (4 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /tasks/ | Tasks list | filters, page |
| GET | /tasks/stats | Tasks stats widget | - |
| GET | /tasks/filter-options | Task filters | - |
| POST | /tasks/ | Create task form | title, description, etc |

### TRAINING/FORMAZIONE (8 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /my-trainings | Training page | - |
| GET | /my-requests | Training requests | - |
| GET | /received-requests | Received requests | - |
| GET | /given-trainings | Given trainings | - |
| GET | /request-recipients | Recipients dropdown | - |
| POST | /request | Create request form | recipient_id, title, etc |
| GET | /admin/professionals | Admin professionals list | - |
| GET | /admin/dashboard-stats | Admin dashboard | - |

### RICERCA (1 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /search/global | Global search bar | q (search term) |

### NEWS (1 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /news/list | News widget | limit |

### POST-IT (3 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /list | Postit list | - |
| POST | /create | Create postit form | content, target, etc |
| POST | /reorder | Drag & drop reorder | order_data |

### PUSH NOTIFICATIONS (5 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| POST | /push/subscriptions | Register push | subscription |
| GET | /push/public-key | Init push | - |
| DELETE | /push/subscriptions | Unregister push | subscription |
| GET | /push/notifications | Fetch notifications | - |

### LOOM INTEGRATION (2 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /loom/api/patients/search | Loom patient search | q (search) |
| GET | /loom/api/recordings | Loom videos list | patient_id |

### TEAM TICKETS (1 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /team-tickets/ | Tickets list | filters, page |

### INTEGRAZIONI ESTERNE (2 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /leads | Leads import | - |
| POST | /confirm-assignment | Assign lead | lead_id |

### Summary Statistics

- **Total Endpoints**: 67
- **GET requests**: 47
- **POST requests**: 16
- **DELETE requests**: 2

---

## Command Reference

### Eseguire i test

```bash
cd /home/manu/suite-clinica/backend

# Tutti i test API (326 test, invocazione singola) — MODO CONSIGLIATO
./run_tests.sh

# Parallelo con pytest-xdist
./run_tests.sh --parallel

# Passare flag extra a pytest (es. solo auth)
./run_tests.sh -- -k auth

# Singolo file
poetry run pytest tests/api/test_auth_api.py -v

# Singola classe
poetry run pytest tests/api/test_auth_api.py::TestAuthLogin -v

# Singolo test
poetry run pytest tests/api/test_auth_api.py::TestAuthLogin::test_login_success_with_valid_credentials -v

# Con coverage report
poetry run pytest tests/api/ --cov=corposostenibile --cov-report=html

# Stop al primo fallimento
poetry run pytest tests/api/ -x

# Solo test falliti nell'ultima esecuzione
poetry run pytest tests/api/ --lf
```

### Database Configuration

- **Test DB:** `suite_clinica_dev_manu_prodclone`
- **User:** `suite_clinica`
- **Password:** `password`
- **Host:** `localhost`
- **Port:** `5432`

---

## Implementation Patterns

### Protected Endpoint Test Pattern

```python
def test_endpoint(self, api_client, admin_user):
    """Test protected endpoint"""
    api_client.login(admin_user)

    response = api_client.get('/api/endpoint')

    assert response.status_code == HTTPStatus.OK
    assert 'expected_field' in response.json
```

### Login Endpoint Test Pattern

```python
def test_login_success(self, api_client, login_test_user):
    """Test login endpoint with real credentials"""
    response = api_client.post('/api/auth/login', json={
        'email': login_test_user.email,
        'password': 'TestPassword123!'
    })

    assert response.status_code == HTTPStatus.OK
    assert response.json['success'] is True
```

### Create Test Data Pattern

```python
def test_with_custom_user(self, api_client, db_session):
    """Test with manually created user"""
    user = User(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        password_hash=generate_password_hash('TestPass123!'),
        role=UserRoleEnum.professionista
    )
    db_session.add(user)
    db_session.commit()

    api_client.login(user)
    response = api_client.get('/api/endpoint')
    assert response.status_code == HTTPStatus.OK
```

---

## Project Structure

```
/backend/tests/
├── __init__.py
├── conftest.py                    # Main fixtures (app, db_session with SAVEPOINT rollback)
├── factories.py                   # Factory Boy factories
├── utils/
│   ├── __init__.py
│   └── db_helpers.py             # Database setup utilities
└── api/
    ├── __init__.py
    ├── conftest.py               # API-specific fixtures (api_client, users)
    ├── test_auth_api.py          # 51 authentication tests (50 pass, 1 pre-existing bug)
    ├── test_auth_api_fix.py      # 1 auth fix test
    ├── test_customers_api.py     # 21 customer tests (100% pass)
    ├── test_team_api.py          # 70 team tests (100% pass)
    ├── test_calendar_api.py      # 50 calendar tests (100% pass)
    ├── test_quality_api.py       # 52 quality tests (100% pass)
    ├── test_tasks_api.py         # 26 tasks tests (100% pass)
    ├── test_review_api.py        # 25 review/training tests (100% pass)
    └── test_integrations_api.py  # 31 integrations tests (30 pass, 1 pre-existing bug)

# Total: 326 tests, 324 passing (99.4%)
```

### Database Isolation (come funziona)

Ogni test gira dentro una transazione che viene rollbackata a fine test.
- `db_session` fixture apre una connessione dedicata e avvia una transazione esterna
- `FSASession.get_bind()` viene monkey-patched per usare quella connessione
- `session.commit()` crea SAVEPOINT (non COMMIT reale)
- A fine test → `transaction.rollback()` → stato DB pulito, zero overhead di TRUNCATE
- Il tracking middleware (`tracking.py`) viene disabilitato in test perche' usa `db.engine.begin()` (connessione separata)

### Testing Guidelines

- Sempre testare sia i casi di successo che di errore
- Includere test di validazione degli errori
- Testare authorization (403) vs not found (404)
- Validare la struttura dei dati di risposta
- Controllare che gli status code rispettino gli standard HTTP

### Troubleshooting

- Se i test falliscono per stato del DB, controllare la fixture `db_session` in `tests/conftest.py`
- Per problemi di timing, verificare la gestione delle transazioni
- Per problemi di auth, verificare che `api_client.login()` sia chiamato prima della request
- `SAWarning: nested transaction already deassociated`: warning innocuo con SAVEPOINT pattern, si puo' ignorare

---

## CI/CD Integration

Tests are integrated with GCP Cloud Build via:
- `cloudbuild.yaml` - Main build and deploy pipeline
- `cloudbuild-test.yaml` - Test suite validation

See `/docs/CI_CD_TEST_INTEGRATION.md` for detailed setup instructions.

---

## Repository Info

- **Branch:** `version-2.0-updated-tests-cicd`
- **Test DB:** `suite_clinica_dev_manu_prodclone`
- **Remote:** GitHub (corposostenibile-suite)

Last Updated: 2026-03-30

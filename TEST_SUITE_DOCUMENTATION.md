# Suite Clinica - Test Suite Documentation

## Executive Summary

Comprehensive pytest test infrastructure for suite-clinica backend covering **67 frontend API endpoints**. 

**Current Status:** 71 tests implemented and passing (31% complete)
- ✅ Authentication API: 50 tests (100% passing)
- ✅ Customer API: 21 tests (100% passing)

---

## 📊 Frontend API Endpoints Complete Mapping

### 📋 AUTENTICAZIONE (6 endpoint)

| Method | Endpoint | Called By | Params | Auth |
|--------|----------|-----------|--------|------|
| POST | /auth/login | Login form | email, password | No |
| POST | /auth/logout | Logout button | - | Yes |
| POST | /auth/forgot-password | Forgot password form | email | No |
| GET | /auth/me | App init, Profile | - | Yes |
| GET | /auth/impersonate/users | Admin panel | - | Yes (Admin) |
| POST | /auth/stop-impersonation | Admin panel | - | Yes (Admin) |

### 👥 TEAM & UTENTI (11 endpoint)

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

### 📅 CALENDAR & EVENTS (11 endpoint)

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

### 🏥 CLIENTI/PAZIENTI (4 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /customers/api/search | Client list search | q (search term) |
| GET | /customers/{id}/stati/{servizio}/storico | Client detail | - |
| GET | /customers/{id}/patologie/storico | Medical history | - |
| GET | /customers/{id}/nutrition/history | Nutrition history | - |

### 📊 QUALITÀ & REVIEW (5 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /quality/api/weekly-scores | Quality dashboard | - |
| POST | /quality/api/calculate | Calculate quality | - |
| GET | /quality/api/dashboard/stats | Quality dashboard | - |
| POST | /quality/api/calcola-trimestrale | Quarterly calculation | - |
| GET | /quality/api/quarterly-summary | Quarterly view | - |

### 📝 TASKS/COMPITI (4 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /tasks/ | Tasks list | filters, page |
| GET | /tasks/stats | Tasks stats widget | - |
| GET | /tasks/filter-options | Task filters | - |
| POST | /tasks/ | Create task form | title, description, etc |

### 🎓 TRAINING/FORMAZIONE (8 endpoint)

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

### 🔍 RICERCA (1 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /search/global | Global search bar | q (search term) |

### 📰 NEWS (1 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /news/list | News widget | limit |

### 📌 POST-IT (3 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /list | Postit list | - |
| POST | /create | Create postit form | content, target, etc |
| POST | /reorder | Drag & drop reorder | order_data |

### 🔔 PUSH NOTIFICATIONS (5 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| POST | /push/subscriptions | Register push | subscription |
| GET | /push/public-key | Init push | - |
| DELETE | /push/subscriptions | Unregister push | subscription |
| GET | /push/notifications | Fetch notifications | - |

### 🎥 LOOM INTEGRATION (2 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /loom/api/patients/search | Loom patient search | q (search) |
| GET | /loom/api/recordings | Loom videos list | patient_id |

### 🏢 TEAM TICKETS (1 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /team-tickets/ | Tickets list | filters, page |

### 🔗 INTEGRAZIONI ESTERNE (2 endpoint)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /leads | Leads import | - |
| POST | /confirm-assignment | Assign lead | lead_id |

### 📊 Summary Statistics

- **Total Endpoints**: 67
- **GET requests**: 47
- **POST requests**: 16
- **DELETE requests**: 2

---

## ✅ Completed Test Suites

### Authentication API Tests (50 tests - 100% passing)

**Test File:** `/backend/tests/api/test_auth_api.py`

#### Login Tests (11 tests)
- ✅ Successful login with valid credentials
- ✅ Login with remember_me flag
- ✅ Login when already authenticated
- ✅ Invalid email rejection
- ✅ Wrong password rejection
- ✅ Missing email validation
- ✅ Missing password validation
- ✅ Empty body validation
- ✅ Inactive user rejection
- ✅ Case-insensitive email handling
- ✅ Non-admin user login

#### Logout Tests (3 tests)
- ✅ Successful logout
- ✅ Logout without authentication (401)
- ✅ Protected endpoints require re-login

#### /me Endpoint Tests (4 tests)
- ✅ Get authenticated user info
- ✅ Not authenticated returns empty
- ✅ User data structure validation
- ✅ Impersonation info inclusion

#### Password Reset Tests (11 tests)
- ✅ Forgot password request
- ✅ Non-existent email privacy (returns success)
- ✅ Missing email validation
- ✅ Already authenticated rejection
- ✅ Case-insensitive email handling
- ✅ Invalid reset token rejection
- ✅ Authenticated user rejection
- ✅ Mismatched passwords rejection
- ✅ Password too short validation
- ✅ No uppercase letter validation
- ✅ No number validation
- ✅ No special character validation

#### Impersonation Tests (17 tests)
- ✅ List users for impersonation (admin)
- ✅ Non-admin rejection (403)
- ✅ Unauthenticated rejection (401)
- ✅ Inactive users excluded
- ✅ Admin excluded from list
- ✅ User data structure validation
- ✅ Start impersonation success
- ✅ Non-admin cannot impersonate
- ✅ Unauthenticated cannot impersonate
- ✅ Non-existent user rejection
- ✅ Cannot impersonate self
- ✅ Cannot impersonate while already impersonating
- ✅ Stop impersonation success
- ✅ Stop when not impersonating
- ✅ Stop without authentication
- ✅ Return to correct admin user
- ✅ Impersonation log creation

### Customer API Tests (21 tests - 100% passing)

**Test File:** `/backend/tests/api/test_customers_api.py`

All customer CRUD operations, filtering, pagination, authorization, and edge cases covered.

---

## 🏗️ Test Infrastructure

### ✅ Completed Setup

- **PostgreSQL test database** with proper isolation
- **pytest fixtures:**
  - `app` - Flask test application
  - `db_session` - Isolated database session per test
  - `client` - Flask test client
  - `api_client` - API-specific client with JSON headers
  - `authenticated_client` - Pre-authenticated test client

- **Factory Boy factories** for all core models:
  - `DepartmentFactory`
  - `TeamFactory`
  - `UserFactory`
  - `ClienteFactory`

- **Database isolation:**
  - TRUNCATE CASCADE between tests
  - Function-scoped sessions
  - Automatic cleanup

- **Authentication handling:**
  - Flask-Login mocking via patching
  - CSRF exemption for API endpoints
  - Dual test patterns for login vs protected endpoints

### Key Design Decisions

#### Test User Fixtures
- Dedicated `login_test_user` and `admin_login_test_user` fixtures
- Explicitly committed to database for API testing
- Consistent test passwords for manual user creation
- Separate fixtures for login endpoint (real credentials) vs other tests (mocked)

#### Database Isolation
- TRUNCATE CASCADE for fast cleanup between tests
- Function-scoped db_session ensures test isolation
- Factory Boy configured with db.session for automatic commit

#### Authentication Testing Pattern
1. **Real API calls** (login endpoint): Use fixtures with committed users, actual password comparison
2. **Protected endpoints**: Use `api_client.login(user)` mock for simplified testing

---

## 📋 Test Metrics

| Category | Endpoints | Tests | Status |
|----------|-----------|-------|--------|
| Authentication | 6 | 50 | ✅ 100% Complete |
| Customers | 4 | 21 | ✅ 100% Complete |
| Team & Users | 11 | - | ⏳ Pending |
| Calendar | 11 | - | ⏳ Pending |
| Quality | 5 | - | ⏳ Pending |
| Tasks | 4 | - | ⏳ Pending |
| Training | 8 | - | ⏳ Pending |
| Other | 20 | - | ⏳ Pending |
| **TOTAL** | **67** | **71** | **✅ 31% Complete** |

---

## 🚀 Phase 2 - Remaining Work

### High Priority
1. **Team & Users Tests** (11 endpoints)
   - Team CRUD, members, departments, stats, capacity

2. **Calendar Tests** (11 endpoints)
   - Events CRUD, sync, attendees, token management

3. **Quality Tests** (5 endpoints)
   - Weekly/quarterly scores, calculations, dashboard

### Medium Priority
4. **Tasks Tests** (4 endpoints)
5. **Training Tests** (8 endpoints)
6. **Integrations** (13 endpoints)
   - Search, News, Postit, Push, Loom, Tickets, External

### Lower Priority
7. **CI/CD Integration**
   - GitHub Actions workflow
   - Test coverage reporting
   - Branch protection rules

### Estimated Timeline
- Team API: 2-3 hours
- Calendar API: 2-3 hours
- Quality API: 1-2 hours
- Others: 4-5 hours
- **Total Phase 2: ~10-15 hours**

---

## 📚 Command Reference

### Run Tests

```bash
cd /home/manu/suite-clinica/backend

# All auth tests (50 tests)
poetry run pytest tests/api/test_auth_api.py -v

# All customer tests (21 tests)
poetry run pytest tests/api/test_customers_api.py -v

# All API tests
poetry run pytest tests/api/ -v

# Specific test class
poetry run pytest tests/api/test_auth_api.py::TestAuthLogin -v

# Specific test
poetry run pytest tests/api/test_auth_api.py::TestAuthLogin::test_login_success_with_valid_credentials -v

# With coverage
poetry run pytest tests/api/ --cov=corposostenibile --cov-report=html

# Run and stop on first failure
poetry run pytest tests/api/ -x
```

### Database Configuration

- **Test DB:** `suite_clinica_dev_manu_prodclone`
- **User:** `suite_clinica`
- **Password:** `password`
- **Host:** `localhost`
- **Port:** `5432`

---

## 🔧 Implementation Patterns

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

## 📂 Project Structure

```
/backend/tests/
├── __init__.py
├── conftest.py                    # Main fixtures (app, db_session, client)
├── factories.py                   # Factory Boy factories
├── utils/
│   ├── __init__.py
│   └── db_helpers.py             # Database setup utilities
└── api/
    ├── __init__.py
    ├── conftest.py               # API-specific fixtures (api_client, users)
    ├── test_auth_api.py          # 50 authentication tests ✅
    └── test_customers_api.py     # 21 customer tests ✅
    
# To be created:
# test_team_api.py                # Team & users tests
# test_calendar_api.py            # Calendar tests
# test_quality_api.py             # Quality tests
# test_tasks_api.py               # Task tests
# test_training_api.py            # Training tests
# test_integrations_api.py        # Search, News, Postit, Push, Loom, Tickets
```

---

## 📝 Notes for Next Development Phase

### Pattern Rules
1. Use `login_test_user` and `admin_login_test_user` fixtures for login endpoint tests
2. Use `api_client.login(user)` mock for protected endpoints
3. Organize tests into classes by endpoint or HTTP method
4. Each test should have clear docstring explaining what it tests

### Database Behavior
- TRUNCATE CASCADE happens automatically at test start via `db_session` fixture
- Each test starts with clean state
- Factory-created objects are auto-committed to session
- Manually created objects must be explicitly committed

### Testing Guidelines
- Always test both success and error cases
- Include validation error tests
- Test authorization (403) vs not found (404)
- Validate response data structure
- Check status codes match HTTP standards

### For Issues
- Test database is isolated per test function
- If tests fail due to database state, check db_session fixture
- For timing issues, check transaction management
- For auth issues, verify api_client.login() is called before request

---

## Repository Info

- **Branch:** `version-2.0-updated-tests-cicd`
- **Test DB:** `suite_clinica_dev_manu_prodclone`
- **Remote:** GitHub (corposostenibile-suite)

Last Updated: 2025-03-25

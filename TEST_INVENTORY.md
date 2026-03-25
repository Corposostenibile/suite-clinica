# 📋 TEST INVENTORY - suite-clinica Backend

## Summary
- **Total Test Files**: 26
- **Total Test Functions**: ~137  
- **Current Status**: 68 passing ✅ | 3 failing ❌ | 4 skipped ⏭️ | 61 errors ⚠️

---

## 📊 Test Distribution

```
QUALITY Module (51 tests)          ████████████████████░ 37%
├─ Units (37 tests)               ✅ Mostly passing
├─ Integration (14 tests)          ⚠️ Fixture scope issues
└─ E2E (2 tests)                   ⚠️ Need DB setup

CLIENT_CHECKS Module (23 tests)    ██████░                16%
├─ Model Tests (23 tests)          ⚠️ Fixture issues
└─ Full integration workflows       ⚠️ DB table missing

TEAM Module (18 tests)             █████░                 13%
├─ AI Assignment                   ⚠️ Custom app setup
├─ Capacity & Metrics (8 tests)    ✅ Some passing
├─ GHL Integration (5 tests)       ⚠️ Fixture issues
└─ Team Support (3 tests)          ✅ Some passing

CUSTOMERS Module (4 tests)         █░                      3%
├─ Scope Guards (1 test)           ✅ 
└─ Webhooks (3 tests)              ✅

LOOM Module (4 tests)              █░                      3%
├─ Permissions (4 tests)           ✅

GHL_INTEGRATION Module (2 tests)   ░                       1%
├─ Opportunity Bridge (2 tests)    ⚠️

RECRUITING Module (0 tests)        ░                       0%
└─ Metrics Service                 ❌ Empty test file

TASKS Module (7 tests)             ██░                     5%
├─ Celery & Events (3 tests)       ⚠️
└─ Listeners (4 tests)             ⏭️ SKIPPED

ROOT LEVEL (1 test)                ░                       1%
└─ GHL E2E Flow (1 test)           ⚠️
```

---

## 🧪 Test Type Breakdown

### Unit Tests (No DB) ~60 tests
- **Quality Calculator Units** (20 tests)
  - Miss rate penalties (8 tests)
  - Bonus bands (5 tests) 
  - Bonus calculation (2 tests)
  - Quality formula (3 tests)
  - KPI weights (2 tests)

- **Quality Eligibility Units** (4 tests)
  - Eligibility logic

- **Super Malus Units** (13 tests)
  - Super malus formula

- **Reviews Units** (5 tests)
  - Review logic

- **Other Units** (15 tests)
  - Trustpilot parsing
  - Webhook handling
  - Permission checks

**Status**: ✅ ~50 passing | ⚠️ ~10 with fixture scope issues

### Integration Tests (With DB) ~50 tests
- **Quality Calculator Integration** (9 tests)
  - Raw/final scoring
  - Rolling averages
  - Quarterly composite
  
- **Quality Eligibility Integration** (9 tests)
  - Professional eligibility
  - Weekly calculations
  
- **Quality Filters** (7 tests)
  - Review filtering
  - Rinnovo filtering
  - Check response filtering

- **Super Malus Integration** (11 tests)
  - Professional identification
  - Malus calculation

- **Client Checks Integration** (23 tests)
  - Form CRUD
  - Assignment tracking
  - Response handling
  - Workflow integration

- **Other Integration** (10 tests)
  - Team capacity
  - GHL flows
  - Celery tasks

**Status**: ⚠️ ~15 passing | ❌ ~35 with DB/fixture issues

### API Tests (HTTP Endpoints) ~3 tests
- **test_ghl_flow.py** (1 test)
  - E2E GHL webhook → opportunity flow

- **test_ai_assignment.py** (0 visible tests)
  - Uses custom Flask app setup

- **test_opportunity_bridge_hm_assignment.py** (2 tests)
  - GHL bridge logic

**Status**: ⚠️ Minimal! Missing 200+ customer/auth/team API endpoints

---

## 📂 What's Actually Tested

### ✅ Well Tested
1. **Quality Scoring System** (51 tests)
   - Penalty calculations
   - Bonus band logic
   - Eligibility checks
   - Super malus formula
   - Quarterly KPI

2. **Client Check Forms** (23 tests)
   - Form CRUD
   - Field management
   - Assignment workflow
   - Response tracking

3. **Team Module** (18 tests)
   - Capacity metrics
   - AI assignment logic
   - GHL calendar sync
   - Task dispatch

### ⚠️ Partially Tested
1. **GHL Integration** (2-3 tests)
   - Only bridge & flow testing
   - Missing most GHL endpoints

2. **Tasks/Celery** (7 tests)
   - Basic execution
   - Event listeners

### ❌ NOT Tested (API Endpoints)
1. **Customers** (172 API endpoints!)
   - GET /api/customers
   - POST /api/customers/create
   - PUT /api/customers/:id
   - DELETE /api/customers/:id
   - All client detail views
   - All client diary/meal/training endpoints
   - ⬅️ **CRITICAL GAP!**

2. **Auth** (9 endpoints)
   - POST /login
   - POST /logout
   - POST /password-reset
   - POST /password-confirm
   - Missing!

3. **Dashboard** (20+ endpoints)
   - Missing!

4. **Search** (Multiple endpoints)
   - Missing!

5. **News/Notifications/Postits/etc**
   - Missing!

---

## 🔴 Critical Issues to Fix

### Fixture Scope Issues (Causing 61 errors)
- Local conftest.py files have session-scope apps
- Root conftest.py has function-scope apps
- Tables not created for each test
- **Solution**: Standardize all conftest.py to use function scope

### Missing API Tests
- Only 3 tests for HTTP endpoints
- Frontend calls 250+ API endpoints
- None of the high-traffic endpoints have tests
- **Solution**: Add API test suite for customers, auth, dashboard

### Test Structure Issues
- Some tests use custom app creation (test_listeners.py)
- Some skip pytest fixtures entirely
- Hardcoded database URIs in some conftest files
- **Solution**: Refactor to use centralized pytest fixtures

---

## 📈 Passing vs Failing Details

### Currently Passing (68)
- All quality calculator unit tests (20)
- Most trustpilot webhook tests (3)
- Some team capacity tests (6)
- Loom permission tests (4)
- GHL opportunity bridge tests (2)
- ~33 other tests

### Currently Failing (3)
- client_checks model tests (fixture scope)
- Some quality integration tests (fixture scope)
- Some team tests (fixture scope)

### Currently Erroring (61)
- client_checks integration (DB table "users" missing)
- quality integration tests (DB table missing)
- team module tests (DB table missing)
- Root cause: Function-scope app not creating tables properly

### Currently Skipped (4)
- test_listeners.py (needs refactoring)
- test_ai_assignment.py custom app tests

---

## 📝 Example Tests

### Unit Test Example (test_calculator_units.py)
```python
class TestMissRatePenalty:
    """Fasce Quality Malus: % check mancanti → punti"""
    def test_zero_miss_rate(self):
        assert QualityScoreCalculator._get_miss_rate_penalty(0.0) == 0.0
    def test_fascia_5_10(self):
        assert QualityScoreCalculator._get_miss_rate_penalty(0.06) == 0.5
```

### Integration Test Example (test_models.py)
```python
class TestCheckForm:
    def test_create_check_form(self, db, sample_user, sample_department):
        form = CheckForm(name='Test', form_type=CheckFormTypeEnum.iniziale, ...)
        db.session.add(form)
        db.session.commit()
        assert form.id is not None
```

### API Test Example (test_ghl_flow.py)
```python
def test_full_ghl_webhook_to_opportunity_flow():
    response = client.post('/ghl/webhook/acconto-open', json={...})
    assert response.status_code == 200
```

---

## 🎯 Next Actions

1. **Fix Fixture Scope** - Make 61 errors become 68 passing
2. **Add API Test Suite** - Create tests for:
   - /api/customers/* (GET, POST, PUT, DELETE)
   - /api/auth/* (login, logout, password reset)
   - /api/dashboard/* (overview, metrics)
   - /api/quality/* (scores, reports)
3. **Integrate CICD** - Run tests automatically on commits
4. **Set Coverage Target** - Aim for 70%+ on main modules

---

**Generated**: 2026-03-25
**Status**: ✅ Configuration complete | ⚠️ Tests need fixture fixes | ❌ API tests needed

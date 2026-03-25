# Backend Documentation Index

This is your complete guide to understanding the backend codebase structure. Use this index to find the information you need.

---

## Quick Navigation

### For First-Time Review
Start here: **BACKEND_ANALYSIS_SUMMARY.md**
- Overview of the Flask architecture
- Direct answers to the initial questions
- Key technical patterns
- Blueprint registration overview

### For Detailed Implementation
See: **backend_structure_analysis.md**
- Complete endpoint listing for each blueprint
- Request/response examples
- Authentication & authorization details
- Service-specific documentation

### For Day-to-Day Development
Use: **BACKEND_QUICK_REFERENCE.md**
- Quick endpoint lookup
- Code patterns and examples
- Common imports and decorators
- Debugging tips

---

## Questions Answered

### Question 1: What is the main Flask app initialization file?

**Answer**: `/backend/corposostenibile/__init__.py`

Key function: `create_app(config_name: str | None = None) -> Flask`

This file:
- Initializes the Flask application factory
- Registers all blueprints in one place (lines 353-427)
- Sets up extensions (database, login manager, etc.)
- Configures error handling and React SPA integration
- Registers Jinja2 filters and global variables

### Question 2: How are blueprints registered?

**Answer**: Via `init_app()` functions called from main `__init__.py`

Each blueprint follows this pattern:
1. Define in `/blueprints/<name>/__init__.py`
2. Has `init_app(app)` function that calls `app.register_blueprint()`
3. Called from main app in `corposostenibile/__init__.py`

All imports and registrations happen in `corposostenibile/__init__.py:353-427`

### Question 3: What are the main route files?

**Answer**: See the table below

---

## Blueprint Routes Summary

| # | Blueprint | File | URL Prefix | Main Endpoint | Lines |
|---|-----------|------|-----------|---|-------|
| 1 | **auth** | `auth/routes.py` | `/auth` | `POST /api/auth/login` | 392 |
| 2 | **team** | `team/api.py` | `/api/team` | `GET /api/team/members` | 3154 |
| 3 | **calendar** | `calendar/routes.py` | `/calendar` | `POST /calendar/api/events` | 56KB |
| 4 | **customers** | `customers/routes.py` | `/customers` | `GET /api/customers/` | 375KB |
| 5 | **quality** | `quality/routes.py` | `/quality/api` | `GET /quality/api/weekly-scores` | 31KB |
| 6 | **review** | `review/routes.py` | `/review` | `POST /review/request` | 79KB |
| 7 | **tasks** | `tasks/routes.py` | `/api/tasks` | `GET /api/tasks/` | 18KB |

---

## Complete Blueprint Reference

### 1. AUTH Blueprint

**Location**: `/backend/corposostenibile/blueprints/auth/`

**Key Files**:
- `__init__.py` - LoginManager configuration
- `routes.py` - HTML login forms
- `api.py` - REST API for React frontend

**Main Endpoints**:
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Current user info
- `POST /api/auth/logout` - User logout
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password/<token>` - Reset password
- `POST /api/auth/impersonate/<user_id>` - Admin impersonation

**Authentication**: Flask-Login session-based
**Key Features**: Password reset, remember-me, admin impersonation

---

### 2. TEAM Blueprint

**Location**: `/backend/corposostenibile/blueprints/team/`

**Key Files**:
- `api.py` - Main API endpoints (3154 lines)
- `routes.py` - HTML routes
- `ai_matching_service.py` - Professional matching
- `weekly_report_routes.py` - Weekly reports

**Main Endpoints**:
- `GET /api/team/members` - List team members
- `POST /api/team/members` - Create member
- `POST /api/team/assignments/match` - AI-match professionals
- `GET /api/team/capacity` - Capacity metrics
- `GET /api/team/teams` - List teams

**Authentication**: Required (Flask-Login)
**Key Features**: AI-powered matching, capacity tracking, weekly reports

---

### 3. CALENDAR Blueprint

**Location**: `/backend/corposostenibile/blueprints/calendar/`

**Key Files**:
- `routes.py` - Calendar operations
- `services.py` - Google Calendar API
- `scheduler.py` - Token auto-refresh

**Main Endpoints**:
- `GET /calendar/connect` - Google OAuth
- `GET /calendar/api/events` - Get events
- `POST /calendar/api/events` - Create event
- `GET /calendar/api/admin/tokens/status` - Admin token management

**Authentication**: Flask-Login + Google OAuth2
**Key Features**: Google Calendar sync, token management

---

### 4. CUSTOMERS Blueprint

**Location**: `/backend/corposostenibile/blueprints/customers/`

**Key Files**:
- `routes.py` - Customer operations (375KB)
- `services.py` - Business logic
- `filters.py` - Data filtering (67KB)

**Main Endpoints**:
- `GET /api/customers/` - List customers
- `POST /api/customers/` - Create customer
- `POST /customers/<id>/professionisti/assign` - Assign professional
- `POST /customers/<id>/diet/add` - Add meal plan
- `POST /customers/<id>/training/add` - Add training

**Authentication**: Required (Flask-Login)
**Key Features**: Customer lifecycle, meal plans, training plans, professional assignment

---

### 5. QUALITY Blueprint

**Location**: `/backend/corposostenibile/blueprints/quality/`

**Key Files**:
- `routes.py` - Quality score endpoints
- `services/` - Score calculation

**Main Endpoints**:
- `GET /quality/api/weekly-scores` - Weekly scores
- `POST /quality/api/calculate` - Calculate score
- `GET /quality/api/quarterly-summary` - Quarterly data

**Authentication**: Required (Flask-Login)
**Key Features**: Quality scoring, trend analysis

---

### 6. REVIEW Blueprint

**Location**: `/backend/corposostenibile/blueprints/review/`

**Key Files**:
- `routes.py` - Reviews and training (79KB)
- `email_service.py` - Notifications

**Main Endpoints**:
- `POST /review/create/<user_id>` - Create review
- `POST /review/request` - Request training
- `GET /review/api/my-trainings` - My trainings

**Authentication**: Required (Flask-Login)
**Key Features**: Performance reviews, training requests, messaging

---

### 7. TASKS Blueprint

**Location**: `/backend/corposostenibile/blueprints/tasks/`

**Key Files**:
- `routes.py` - Task endpoints
- `events.py` - Event listeners
- `tasks.py` - Celery async tasks

**Main Endpoints**:
- `GET /api/tasks/` - List tasks
- `POST /api/tasks/` - Create task
- `PUT /api/tasks/<id>` - Update task

**Authentication**: Required (Flask-Login)
**Key Features**: Task management, filtering, visibility scoping

---

## Authentication & Authorization

### Session-Based Authentication
- **Manager**: Flask-Login with session cookies
- **User ID Storage**: In session, loaded by `User.query.get(user_id)`
- **Login View**: `auth.login`
- **Session Protection**: "basic" mode
- **Remember Me**: 30-day cookie

### Protected Routes
All routes use `@login_required` decorator from Flask-Login

### Permission Checks
Custom decorators check `current_user` properties:
- `current_user.is_admin`
- `current_user.is_manager`
- `current_user.is_professional`
- etc.

### Example
```python
from flask_login import login_required, current_user

@bp.route('/admin-endpoint')
@login_required
def admin_endpoint():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify({"success": True})
```

---

## Request/Response Formats

### Standard Login Request
```json
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password123",
  "remember_me": false
}
```

### Standard Success Response
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "John Doe",
    "email": "user@example.com"
  }
}
```

### Standard Error Response
```json
{
  "success": false,
  "error": "Descriptive error message"
}
```

### List Response with Pagination
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

---

## File Structure

```
/backend/
├── corposostenibile/
│   ├── __init__.py              # Main app factory
│   ├── config.py                # Configuration
│   ├── extensions.py            # Flask extensions
│   ├── models.py                # Database models
│   ├── filters.py               # Jinja filters
│   └── blueprints/
│       ├── auth/
│       │   ├── __init__.py      # init_app()
│       │   ├── routes.py        # HTML routes
│       │   └── api.py           # REST API
│       ├── team/
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   ├── api.py           # Main API endpoints
│       │   └── ...
│       ├── calendar/
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   └── ...
│       ├── customers/
│       │   ├── __init__.py
│       │   ├── routes.py        # All customer routes
│       │   └── ...
│       ├── quality/
│       │   ├── __init__.py
│       │   └── routes.py
│       ├── review/
│       │   ├── __init__.py
│       │   └── routes.py
│       └── tasks/
│           ├── __init__.py
│           └── routes.py
├── wsgi.py                      # WSGI entry point
└── ...
```

---

## Development Tips

### Adding a New Endpoint

1. **Create the route** in `/blueprints/<name>/routes.py`:
```python
@bp.route('/api/new', methods=['GET', 'POST'])
@login_required
def new_endpoint():
    return jsonify({"success": True})
```

2. **Update blueprint __init__.py** if needed

3. **No extra registration needed** - already in main `__init__.py`

### Checking Current Routes

```bash
cd /backend
flask routes
```

### Testing an Endpoint

```bash
curl -X GET http://localhost:5000/api/team/members \
  -H "Content-Type: application/json"
```

### Database Query

```bash
flask shell
>>> from corposostenibile.models import User
>>> User.query.all()
```

---

## Configuration

**Location**: `/backend/corposostenibile/config.py`

- Development config
- Production config (GCP)
- Testing config

**Load Method**: `Config.get(config_name)`

---

## Extensions

**Location**: `/backend/corposostenibile/extensions.py`

- `db` - SQLAlchemy ORM
- `login_manager` - Flask-Login
- `csrf` - CSRF protection
- `celery` - Async tasks
- `redis` - Caching
- `google_bp` - Google OAuth2

---

## Common Imports

```python
# Flask
from flask import Blueprint, jsonify, request, current_app

# Authentication
from flask_login import login_required, current_user

# Database
from corposostenibile.extensions import db
from corposostenibile.models import User, Cliente, Team, etc.

# Utils
from werkzeug.security import generate_password_hash, check_password_hash
```

---

## Related Documentation

- **GCP Deployment**: See `ci_cd_analysis.md`
- **Local Development (VPS)**: See `docs/vps/duckdns_local_dev_vps.md`
- **Frontend API Endpoints**: See `FRONTEND_API_ENDPOINTS.md`
- **Test Suite**: See `TEST_SUITE_ANALYSIS.md`

---

## Quick Links

### Essential Files
- Main App: `/backend/corposostenibile/__init__.py`
- Configuration: `/backend/corposostenibile/config.py`
- Models: `/backend/corposostenibile/models.py`
- Extensions: `/backend/corposostenibile/extensions.py`

### Blueprint Locations
- Auth: `/backend/corposostenibile/blueprints/auth/`
- Team: `/backend/corposostenibile/blueprints/team/`
- Calendar: `/backend/corposostenibile/blueprints/calendar/`
- Customers: `/backend/corposostenibile/blueprints/customers/`
- Quality: `/backend/corposostenibile/blueprints/quality/`
- Review: `/backend/corposostenibile/blueprints/review/`
- Tasks: `/backend/corposostenibile/blueprints/tasks/`

### Documentation Files
- **This File**: `BACKEND_DOCUMENTATION_INDEX.md`
- **Summary**: `BACKEND_ANALYSIS_SUMMARY.md`
- **Quick Reference**: `BACKEND_QUICK_REFERENCE.md`
- **Detailed Analysis**: `backend_structure_analysis.md`

---

## Summary

The backend is a Flask application with:
- **7 main blueprints** serving different features
- **Blueprint-based architecture** for modularity
- **Session-based authentication** with Flask-Login
- **JSON REST API** for React frontend
- **SQLAlchemy ORM** for database access
- **Consistent patterns** across all blueprints

All blueprints are registered in the main `__init__.py`, making the architecture transparent and easy to understand.

---

**Last Updated**: March 25, 2024
**Status**: Complete Analysis

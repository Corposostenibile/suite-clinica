# Backend Codebase Analysis - Executive Summary

## Overview

This document summarizes the analysis of the backend Flask application structure. The backend is organized as a modular, blueprint-based architecture with a clear separation of concerns.

---

## Question 1: Main Flask App Initialization File

**Answer**: `/backend/corposostenibile/__init__.py`

**Key Function**: `create_app(config_name: str | None = None) -> Flask`

This single entry point:
- Initializes the Flask application
- Loads configuration (development/production/testing)
- Sets up all extensions (database, login manager, Celery, etc.)
- Registers all blueprints
- Configures error handling
- Sets up React SPA integration
- Initializes Jinja2 filters and global variables

---

## Question 2: Blueprint Registration

All blueprints are imported and registered in a single location: **`corposostenibile/__init__.py` lines 353-427**

### Registration Pattern
Each blueprint has an `init_app(app)` function:

```python
# In blueprint's __init__.py
def init_app(app: Flask):
    app.register_blueprint(bp, url_prefix="/prefix")
    # Optional: CLI, ACL, Jinja filters
```

Then in main `__init__.py`:
```python
blueprint.init_app(app)  # Called at app creation time
```

---

## Question 3: Main Route Files

### Summary Table

| Blueprint | Init File | Routes File | URL Prefix | Auth | Lines |
|-----------|-----------|-------------|-----------|------|-------|
| **auth** | `auth/__init__.py` | `auth/routes.py` | `/auth` | SessionBased | 392 |
| **team** | `team/__init__.py` | `team/api.py` | `/api/team` | Required | 3154 |
| **calendar** | `calendar/__init__.py` | `calendar/routes.py` | `/calendar` | Required + OAuth | 56KB |
| **customers** | `customers/__init__.py` | `customers/routes.py` | `/customers` | Required | 375KB |
| **quality** | `quality/__init__.py` | `quality/routes.py` | `/quality/api` | Required | 31KB |
| **review** | `review/__init__.py` | `review/routes.py` | `/review` | Required | 79KB |
| **tasks** | `tasks/__init__.py` | `tasks/routes.py` | `/api/tasks` | Required | 18KB |

---

## Authentication Requirements

### Session-Based Authentication
**Location**: `auth/__init__.py`

```python
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.session_protection = "basic"
login_manager.remember_cookie_duration = timedelta(days=30)
```

### Implementation
- **Method**: Flask-Login with session cookies
- **User Loading**: By ID from database
- **CSRF Protection**: Token-based (cookie + header)
- **Protected Routes**: `@login_required` decorator

### API Entry Points
- `POST /api/auth/login` - Returns user object and session
- `GET /api/auth/me` - Check authentication status
- `POST /api/auth/logout` - Clear session

---

## Request Parameters & Response Formats

### Standard Login Request
```json
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "password123",
  "remember_me": false
}
```

### Standard Login Response
```json
{
  "success": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "admin",
    "teams": [...],
    "avatar_url": "/uploads/..."
  },
  "redirect": "/welcome"
}
```

### Standard Error Response
```json
{
  "success": false,
  "error": "Descriptive error message"
}
```

### List Responses
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

## Detailed Blueprint Analysis

### 1. AUTH Blueprint
**File**: `/backend/corposostenibile/blueprints/auth/`

**Main Routes**:
- `POST /api/auth/login` - JSON login
- `POST /api/auth/logout` - JSON logout
- `GET /api/auth/me` - Current user info
- `POST /api/auth/forgot-password` - Request reset
- `GET /api/auth/verify-reset-token/<token>` - Verify token
- `POST /api/auth/reset-password/<token>` - Reset password
- `GET /api/auth/impersonate/users` - List users to impersonate (admin)
- `POST /api/auth/impersonate/<user_id>` - Start impersonation
- `POST /api/auth/stop-impersonation` - Stop impersonation

**Authentication**: Public for login, required for logout/impersonate
**Request Format**: JSON body with email/password
**Response Format**: JSON with user object

---

### 2. TEAM Blueprint
**File**: `/backend/corposostenibile/blueprints/team/`

**Main Routes**:
- `GET/POST /api/team/members` - List/create members
- `GET/PUT/DELETE /api/team/members/<user_id>` - Manage member
- `POST /api/team/members/<user_id>/toggle` - Activate/deactivate
- `POST /api/team/members/<user_id>/avatar` - Upload avatar
- `GET /api/team/members/<user_id>/clients` - Get assigned clients
- `GET /api/team/teams` - List teams
- `POST /api/team/teams` - Create team
- `GET/PUT/DELETE /api/team/teams/<team_id>` - Manage teams
- `POST /api/team/assignments/match` - AI-match professionals
- `GET /api/team/capacity` - Capacity metrics
- `GET /api/team/admin-dashboard-stats` - Dashboard data

**Authentication**: Required (Flask-Login)
**Authorization**: Role-based (admin, manager, team leader)
**Request Format**: JSON with member/team data
**Response Format**: JSON with status and objects

---

### 3. CALENDAR Blueprint
**File**: `/backend/corposostenibile/blueprints/calendar/`

**Main Routes**:
- `GET /calendar/connect` - Start Google OAuth
- `GET /calendar/disconnect` - Disconnect account
- `GET /calendar/api/events` - Get events
- `POST /calendar/api/events` - Create event
- `DELETE /calendar/api/event/<google_event_id>` - Delete event
- `GET /calendar/api/connection-status` - Check connection
- `GET /calendar/api/admin/tokens/status` - Admin: token status
- `POST /calendar/api/admin/tokens/refresh` - Admin: force refresh

**Authentication**: Required (Flask-Login) + Google OAuth2
**Authorization**: Admin for token management
**External Integration**: Google Calendar API
**Request Format**: JSON with event data
**Response Format**: JSON with events/status

---

### 4. CUSTOMERS Blueprint
**File**: `/backend/corposostenibile/blueprints/customers/`

**Main Routes**:
- `GET/POST /api/customers/` - List/create customers
- `GET/PATCH/DELETE /api/customers/<cliente_id>` - Manage customer
- `POST /customers/<cliente_id>/professionisti/assign` - Assign professional
- `POST /customers/<cliente_id>/diet/add` - Add meal plan
- `POST /customers/<cliente_id>/training/add` - Add training plan
- `GET /customers/<cliente_id>/training/history` - Training history
- `POST /customers/<cliente_id>/freeze` - Freeze account
- `POST /customers/<cliente_id>/unfreeze` - Unfreeze account
- `GET /api/customers/<cliente_id>/clinical-folder-export` - Export PDF

**Authentication**: Required (Flask-Login)
**Authorization**: Role-based (admin, health_manager, professional)
**Request Format**: JSON with customer/plan data, multipart for files
**Response Format**: JSON with status/objects, PDF export

---

### 5. QUALITY Blueprint
**File**: `/backend/corposostenibile/blueprints/quality/`

**Main Routes**:
- `GET /quality/api/weekly-scores` - Weekly scores
- `GET /quality/api/professionista/<user_id>/trend` - Trend analysis
- `POST /quality/api/calculate` - Calculate score
- `POST /quality/api/calcola/<dept_key>` - Department calculation
- `GET /quality/api/quarterly-summary` - Quarterly data

**Authentication**: Required (Flask-Login)
**Authorization**: Admin for calculations
**Request Format**: JSON with parameters
**Response Format**: JSON with scores/metrics

---

### 6. REVIEW Blueprint
**File**: `/backend/corposostenibile/blueprints/review/`

**Main Routes**:

**Reviews**:
- `GET /review/` - List reviews
- `POST /review/create/<user_id>` - Create review
- `POST /review/edit/<review_id>` - Edit review
- `POST /review/acknowledge/<review_id>` - Acknowledge
- `POST /review/message/<review_id>` - Send message

**Training**:
- `POST /review/request` - Request training
- `GET /review/requests/my` - My requests
- `GET /review/requests/received` - Received requests
- `POST /review/request/<request_id>/respond` - Respond to request

**Admin API**:
- `GET /review/api/admin/professionals` - List professionals
- `GET /review/api/admin/trainings/<user_id>` - User trainings
- `POST /review/api/admin/trainings/<user_id>` - Create training

**Authentication**: Required (Flask-Login)
**Authorization**: Manager for reviews, admin for management
**Request Format**: JSON with review/training data
**Response Format**: JSON with status/objects

---

### 7. TASKS Blueprint
**File**: `/backend/corposostenibile/blueprints/tasks/`

**Main Routes**:
- `GET /api/tasks/` - List tasks (filtered, paginated)
- `POST /api/tasks/` - Create task
- `PUT /api/tasks/<task_id>` - Update task
- `GET /api/tasks/stats` - Statistics
- `GET /api/tasks/filter-options` - Available filters

**Authentication**: Required (Flask-Login)
**Authorization**: Role-based visibility
**Request Format**: JSON with task data and filters
**Response Format**: JSON with tasks/stats

---

## Key Technical Patterns

### 1. Blueprint Pattern
```python
# Define
bp = Blueprint('name', __name__, url_prefix='/prefix')

@bp.route('/endpoint', methods=['GET', 'POST'])
@login_required
def endpoint():
    return jsonify({"success": True})

# Initialize
def init_app(app):
    app.register_blueprint(bp)

# Register in main app
from .blueprint_name import init_app
init_app(app)
```

### 2. Error Handling
```python
try:
    # Process
    return jsonify({"success": True, "data": result})
except Exception as e:
    app.logger.error(f"Error: {e}")
    return jsonify({"success": False, "error": str(e)}), 500
```

### 3. Permission Checking
```python
from flask_login import login_required, current_user

@bp.route('/admin-only')
@login_required
def admin_endpoint():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    # Handle request
```

### 4. Database Access
```python
from corposostenibile.models import User
from corposostenibile.extensions import db

# Create
user = User(email="test@example.com", ...)
db.session.add(user)
db.session.commit()

# Read
user = User.query.get(user_id)
users = User.query.filter_by(active=True).all()

# Update
user.name = "New Name"
db.session.commit()

# Delete
db.session.delete(user)
db.session.commit()
```

---

## Configuration & Extensions

### Configuration
**File**: `/backend/corposostenibile/config.py`
- Loads from environment variables
- Separate configs for development/production/testing

### Extensions
**File**: `/backend/corposostenibile/extensions.py`
- `db` - SQLAlchemy ORM
- `login_manager` - Flask-Login
- `csrf` - CSRF protection
- `celery` - Async tasks
- `redis` - Caching/sessions
- `google_bp` - Google OAuth2

---

## Development Workflow

### To Add a New Endpoint

1. Create `/blueprints/<feature>/routes.py`:
```python
from flask import Blueprint, jsonify, request
from flask_login import login_required

bp = Blueprint('feature', __name__)

@bp.route('/api/endpoint', methods=['GET', 'POST'])
@login_required
def endpoint():
    data = request.get_json()
    # Process
    return jsonify({"success": True, "data": result})
```

2. Create/update `/blueprints/<feature>/__init__.py`:
```python
from .routes import bp

def init_app(app):
    app.register_blueprint(bp)
```

3. Import and register in main `__init__.py`:
```python
from .blueprints.feature import init_app
init_app(app)
```

---

## Files Reference

### Essential Files
| File | Purpose |
|------|---------|
| `__init__.py` | Main Flask factory |
| `config.py` | Configuration classes |
| `extensions.py` | Flask extensions setup |
| `models.py` | Database models |
| `wsgi.py` | WSGI entry point |

### Per-Blueprint Files
| File | Purpose |
|------|---------|
| `__init__.py` | init_app() function |
| `routes.py` | HTTP route handlers |
| `api.py` | REST API endpoints |
| `forms.py` | WTForms definitions |
| `services.py` | Business logic |
| `models/` | Blueprint-specific models |
| `templates/` | Jinja2 templates |
| `static/` | CSS, JS, images |

---

## Testing

Tests are located in `/backend/tests/` following pytest conventions.

### Running Tests
```bash
cd /backend
pytest                    # Run all tests
pytest tests/test_auth.py # Run specific test file
pytest -v                 # Verbose output
```

---

## Deployment

**GCP Deployment**: See `ci_cd_analysis.md` for Cloud Build pipeline
**VPS/Local**: See `docs/vps/duckdns_local_dev_vps.md` for local development

---

## Summary

The backend is a well-structured Flask application using blueprints for modularity. Each blueprint:
- Has a clear URL prefix
- Implements authentication via Flask-Login
- Returns JSON responses
- Uses SQLAlchemy for database access
- Follows a consistent pattern for error handling

All blueprints are registered in the main `__init__.py` file, making it easy to understand the complete API surface at a glance.

---

## Documents Available

1. **backend_structure_analysis.md** - Detailed analysis of all blueprints
2. **BACKEND_QUICK_REFERENCE.md** - Quick lookup guide with examples
3. **BACKEND_ANALYSIS_SUMMARY.md** - This document (overview)


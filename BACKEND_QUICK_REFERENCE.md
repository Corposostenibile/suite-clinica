# Backend Quick Reference Guide

## File Locations

### Main Files
- **Flask App Factory**: `/backend/corposostenibile/__init__.py` → `create_app()`
- **Config**: `/backend/corposostenibile/config.py`
- **Extensions**: `/backend/corposostenibile/extensions.py`
- **Models**: `/backend/corposostenibile/models.py`
- **WSGI Entry**: `/backend/wsgi.py`

### Blueprint Entry Points
All blueprints follow this pattern:
```
/blueprints/<blueprint_name>/
  ├── __init__.py          # init_app(app) function
  ├── routes.py            # HTML routes
  ├── api.py (optional)    # JSON API routes
  └── ...
```

---

## 1. AUTH Blueprint

**Location**: `/backend/corposostenibile/blueprints/auth/`

### Key Files
- `routes.py` - HTML login/logout forms
- `api.py` - REST API for React (login, logout, forgot-password, etc.)
- `__init__.py` - LoginManager configuration

### Session Setup
```python
# In auth/__init__.py
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.session_protection = "basic"
login_manager.remember_cookie_duration = timedelta(days=30)
```

### Quick API Examples
```bash
# Login
POST /api/auth/login
{ "email": "user@example.com", "password": "xxx", "remember_me": false }

# Get current user
GET /api/auth/me

# Logout
POST /api/auth/logout
```

---

## 2. TEAM Blueprint

**Location**: `/backend/corposostenibile/blueprints/team/`

### Main File
- `api.py` - 3154 lines, all API endpoints

### Key Endpoints
```bash
# Members
GET    /api/team/members
POST   /api/team/members
GET    /api/team/members/<user_id>
PUT    /api/team/members/<user_id>
DELETE /api/team/members/<user_id>

# Professional Matching
POST /api/team/assignments/analyze-lead
POST /api/team/assignments/match
POST /api/team/assignments/confirm

# Capacity
GET  /api/team/capacity
GET  /api/team/capacity-weights
PUT  /api/team/capacity/<user_id>
```

### Features
- AI-powered professional matching
- Capacity/workload tracking
- Team management
- Weekly report automation

---

## 3. CALENDAR Blueprint

**Location**: `/backend/corposostenibile/blueprints/calendar/`

### Integration
- Google Calendar OAuth2
- Token auto-refresh
- Event sync

### Key Endpoints
```bash
# Connection
GET /calendar/connect
GET /calendar/disconnect
GET /calendar/api/connection-status

# Events
GET  /calendar/api/events
POST /calendar/api/events
DELETE /calendar/api/event/<google_event_id>

# Admin Token Management
GET  /calendar/api/admin/tokens/status
POST /calendar/api/admin/tokens/refresh
POST /calendar/api/admin/tokens/<user_id>/refresh
```

---

## 4. CUSTOMERS Blueprint

**Location**: `/backend/corposostenibile/blueprints/customers/`

### Main File
- `routes.py` - 375KB file with all customer operations

### Key Endpoints
```bash
# Customers
GET    /api/customers/
POST   /api/customers/
GET    /api/customers/<cliente_id>
PATCH  /api/customers/<cliente_id>
DELETE /api/customers/<cliente_id>

# Professional Assignment
POST   /customers/<cliente_id>/professionisti/assign
POST   /customers/<cliente_id>/professionisti/<history_id>/interrupt

# Plans
POST   /customers/<cliente_id>/diet/add
POST   /customers/<cliente_id>/training/add
GET    /customers/<cliente_id>/training/history

# Export
GET    /api/customers/<cliente_id>/clinical-folder-export  # PDF
```

### Features
- Customer lifecycle management
- Professional assignment
- Meal plan management
- Training plan management
- History tracking (undo/restore)
- Freeze/unfreeze accounts
- Clinical folder export

---

## 5. QUALITY Blueprint

**Location**: `/backend/corposostenibile/blueprints/quality/`

### Key Endpoints
```bash
GET  /quality/api/weekly-scores
GET  /quality/api/professionista/<user_id>/trend
POST /quality/api/calculate
POST /quality/api/calcola/<dept_key>
GET  /quality/api/quarterly-summary
```

### Features
- Quality score calculations
- Department-level scoring
- Professional trend analysis
- Quarterly summaries

---

## 6. REVIEW Blueprint

**Location**: `/backend/corposostenibile/blueprints/review/`

### Types
1. **Reviews** - Performance reviews
2. **Training** - Training requests and tracking

### Key Endpoints
```bash
# Reviews
GET    /review/
GET    /review/member/<user_id>
POST   /review/create/<user_id>
POST   /review/edit/<review_id>
POST   /review/acknowledge/<review_id>
POST   /review/message/<review_id>

# Training
POST   /review/request
GET    /review/requests/my
GET    /review/requests/received
POST   /review/request/<request_id>/respond

# API (React)
GET    /review/api/my-trainings
GET    /review/api/my-requests
POST   /review/api/request
GET    /review/api/admin/trainings/<user_id>
```

### Features
- Manager-to-staff reviews
- Training request workflow
- Message threading
- Admin management

---

## 7. TASKS Blueprint

**Location**: `/backend/corposostenibile/blueprints/tasks/`

### Key Endpoints
```bash
GET  /api/tasks/
POST /api/tasks/
PUT  /api/tasks/<task_id>
GET  /api/tasks/stats
GET  /api/tasks/filter-options
```

### Task Properties
- Status: open, in_progress, done, cancelled
- Visibility: global, department, user
- Filtering: by status, assignee, department, priority

---

## Authentication & Authorization

### Session-Based Auth
- Flask-Login manages sessions
- User loaded from DB by ID
- CSRF protection on all mutations
- Remember-me cookie (30 days)

### Role Hierarchy
- `admin` - Full system access
- `manager` - Team/department management
- `professional` - Own data + assigned clients
- `health_manager` - Health-specific data
- Other specialized roles per feature

### Pattern: Checking Permissions
```python
from flask_login import login_required, current_user

@bp.route('/endpoint')
@login_required
def endpoint():
    # Check role
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Check permission
    if not current_user.has_permission('specific:action'):
        return jsonify({"error": "Forbidden"}), 403
```

---

## Common API Response Formats

### Success
```json
{
  "success": true,
  "data": { ... }
}
```

### Error
```json
{
  "success": false,
  "error": "Descriptive error message"
}
```

### List with Pagination
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

## Typical Request Flow

1. **Client (React)** sends request to `/api/endpoint`
2. **Flask Router** directs to blueprint route
3. **@login_required** checks session
4. **Permission decorator** checks access
5. **Route handler** validates input
6. **Service layer** processes business logic
7. **Database** performs CRUD
8. **Response** returned as JSON

---

## Development Workflow

### Adding New Endpoint
```python
# In /blueprints/<name>/routes.py or api.py
from flask import Blueprint, jsonify, request
from flask_login import login_required

bp = Blueprint('name', __name__)

@bp.route('/api/new-endpoint', methods=['GET'])
@login_required
def new_endpoint():
    data = request.get_json()
    # Process
    return jsonify({"success": True, "data": result})
```

### Register in __init__.py
```python
def init_app(app: Flask):
    app.register_blueprint(bp, url_prefix="/api")
```

### Call from main app
```python
# In corposostenibile/__init__.py create_app()
from .blueprints import your_blueprint
your_blueprint.init_app(app)
```

---

## Database & Models

### Key Models
- `User` - Team members
- `Cliente` - Customers/clients
- `Team` - Team groupings
- `Review` - Performance reviews
- `TrainingRequest` - Training requests
- `Task` - Task management
- And many more in `/corposostenibile/models.py`

### Query Pattern
```python
from corposostenibile.models import User
user = User.query.get(user_id)
users = User.query.filter_by(active=True).all()
```

---

## Common Decorators

### Authentication
```python
from flask_login import login_required
@login_required
def endpoint(): ...
```

### CSRF
```python
from flask_wtf.csrf import csrf_protect
@app.route('/form', methods=['POST'])
@csrf_protect
def form(): ...
```

### Custom Permission
```python
def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/admin-only')
@admin_required
def admin_endpoint(): ...
```

---

## File Size Reference

| File | Size | Purpose |
|------|------|---------|
| customers/routes.py | 375KB | Customer operations |
| team/api.py | ~130KB | Team management API |
| review/routes.py | 79KB | Reviews & training |
| calendar/routes.py | 56KB | Calendar operations |
| customers/filters.py | 67KB | Data filtering |
| quality/routes.py | 31KB | Quality scoring |
| tasks/routes.py | 18KB | Task management |
| auth/routes.py | 392 lines | Authentication |

---

## Key Imports for Routes

```python
# Flask basics
from flask import Blueprint, jsonify, request, current_app

# Authentication
from flask_login import login_required, current_user

# Database
from corposostenibile.extensions import db
from corposostenibile.models import User, Cliente, Team, etc.

# Utilities
from werkzeug.security import generate_password_hash, check_password_hash
```

---

## Debugging Tips

### View Active Routes
```bash
flask routes
```

### Check Database
```bash
flask shell
>>> from corposostenibile.models import User
>>> User.query.all()
```

### Test API Endpoint
```bash
curl -X GET http://localhost:5000/api/endpoint \
  -H "Content-Type: application/json"
```

### Check Logs
```bash
# Application logs in Flask debug mode
# Check console for errors and warnings
```


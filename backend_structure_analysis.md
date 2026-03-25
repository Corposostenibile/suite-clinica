# Backend Codebase Structure Analysis

## 1. Main Flask App Initialization

**File**: `/home/manu/suite-clinica/backend/corposostenibile/__init__.py`

- **Function**: `create_app(config_name: str | None = None) -> Flask`
- **Purpose**: Application factory that initializes Flask app with all extensions and blueprints
- **Key Components**:
  - Configuration loading (development/production/testing)
  - Extension initialization (db, redis, login_manager, celery, etc.)
  - Jinja2 filters registration
  - Error handling (JSON-first approach)
  - React SPA integration with fallback to Flask templates
  - CSRF protection with cookie setup
  - Google OAuth integration
  - PostgreSQL ENUM registration

---

## 2. Blueprint Registration System

### Main Entry Point
**File**: `/home/manu/suite-clinica/backend/corposostenibile/__init__.py` (lines 353-427)

All blueprints are imported and registered in `create_app()`:

```python
from .blueprints import (
    auth, customers, team, department, welcome, nutrition,
    ticket, communications, respond_io, feedback, review,
    projects, knowledge_base, finance, recruiting, ghl_integration,
    old_suite_integration, calendar, client_checks, sales_form,
    suitemind, feedback_global, manual, kpi, appointment_setting,
    tasks, documentation, loom, search, sop_chatbot, team_tickets,
    push_notifications,
)
```

---

## 3. Auth Blueprint

**Path**: `/home/manu/suite-clinica/backend/corposostenibile/blueprints/auth/`

### Files Structure
- `__init__.py` - Blueprint initialization and LoginManager setup
- `routes.py` - Jinja template routes (HTML forms)
- `api.py` - REST API endpoints for React frontend
- `forms.py` - WTForms for HTML forms
- `email_utils.py` - Email sending utilities
- `cli.py` - CLI commands

### Initialization (routes.py)
```python
auth_bp = Blueprint("auth", __name__, template_folder="templates", static_folder="static")
```
- **URL Prefix**: `/auth`
- **Registered in**: `auth.init_app(app)` at `corposostenibile/__init__.py:400`

### Main Routes

#### HTML Routes (routes.py)
| Route | Method | Purpose |
|-------|--------|---------|
| `/auth/login` | GET, POST | Login form (Jinja template) |
| `/auth/logout` | POST | Logout user |
| `/auth/forgot-password` | GET, POST | Password reset request form |
| `/auth/reset-password/<token>` | GET, POST | Password reset form |
| `/auth/impersonate` | GET | List users to impersonate (admin) |
| `/auth/impersonate/<user_id>` | POST | Start impersonation |
| `/auth/stop-impersonation` | POST | Stop impersonation |

#### API Routes (api.py) - For React Frontend
| Route | Method | Purpose | Auth Required |
|-------|--------|---------|---|
| `/api/auth/login` | POST | JSON login endpoint | No |
| `/api/auth/logout` | POST | JSON logout endpoint | Yes |
| `/api/auth/me` | GET | Get current user info | No (returns auth status) |
| `/api/auth/forgot-password` | POST | Request password reset email | No |
| `/api/auth/verify-reset-token/<token>` | GET | Verify reset token validity | No |
| `/api/auth/reset-password/<token>` | POST | Reset password with token | No |
| `/api/auth/impersonate/users` | GET | List impersonatable users | Yes (admin) |
| `/api/auth/impersonate/<user_id>` | POST | Start impersonation | Yes (admin) |
| `/api/auth/stop-impersonation` | POST | Stop impersonation | Yes |

### Authentication & Permissions
- **Login Manager**: Uses Flask-Login with session-based authentication
- **Session Protection**: "basic" mode enabled
- **User Loader**: Queries User model by ID from session
- **Login View**: Redirects to `auth.login` when unauthorized
- **Remember Me**: Cookie duration = 30 days (configurable)

### API Request/Response Examples

**POST /api/auth/login**
```json
Request:
{
  "email": "user@example.com",
  "password": "password123",
  "remember_me": false
}

Response (Success):
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

Response (Error):
{
  "success": false,
  "error": "Email non trovata. Verifica l'indirizzo inserito."
}
```

**GET /api/auth/me**
```json
Authenticated:
{
  "authenticated": true,
  "user": {...},
  "impersonating": false,
  "original_admin_name": null
}

Not Authenticated:
{
  "authenticated": false
}
```

---

## 4. Team/Users Blueprint

**Path**: `/home/manu/suite-clinica/backend/corposostenibile/blueprints/team/`

### Files Structure
- `__init__.py` - Blueprint initialization
- `routes.py` - HTML routes
- `api.py` - REST API endpoints (main file, 3154 lines)
- `forms.py` - WTForms
- `anonymous_survey_routes.py` - Survey endpoints
- `okr_routes.py` - OKR (Objectives & Key Results) endpoints
- `trial_routes.py` & `trial_api.py` - Trial management
- `trial_permissions.py` - Trial access control
- `team_payments_routes.py` - Payment tracking
- `weekly_report_routes.py` - Weekly report endpoints
- `weekly_report_tasks.py` - Scheduled report tasks
- `ai_matching_service.py` - AI-based professional matching
- `criteria_service.py` - Professional criteria management
- `leave_service.py` - Leave/absence management
- `leave_notifications.py` - Absence notifications

### Initialization
```python
team_bp = Blueprint("team", __name__, static_folder="static")
team_api_bp = Blueprint("team_api", __name__, url_prefix="/api/team")
weekly_report_bp = Blueprint("weekly_report", __name__, url_prefix="/team/weekly-reports")
```
- **URL Prefixes**: `/team`, `/api/team`, `/team/weekly-reports`
- **Registered in**: `team.init_app(app)` at `corpsostenibile/__init__.py:401`

### Main API Routes (api.py)

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/team/members` | GET | List all team members |
| `/api/team/members` | POST | Create new team member |
| `/api/team/members/<user_id>` | GET | Get member details |
| `/api/team/members/<user_id>` | PUT | Update member |
| `/api/team/members/<user_id>` | DELETE | Delete member |
| `/api/team/members/<user_id>/toggle` | POST | Toggle member active status |
| `/api/team/members/<user_id>/avatar` | POST | Upload member avatar |
| `/api/team/members/<user_id>/clients` | GET | Get assigned clients for member |
| `/api/team/members/<user_id>/checks` | GET | Get client checks for member |
| `/api/team/departments` | GET | List departments |
| `/api/team/stats` | GET | Team statistics |
| `/api/team/professionals/criteria` | GET | Get professional matching criteria |
| `/api/team/professionals/<user_id>/criteria` | PUT | Update professional criteria |
| `/api/team/professionals/<user_id>/toggle-available` | PUT | Toggle professional availability |
| `/api/team/criteria/schema` | GET | Get criteria schema |
| `/api/team/assignments/analyze-lead` | POST | Analyze client story for matching |
| `/api/team/assignments/match` | POST | Match professionals to client |
| `/api/team/assignments/confirm` | POST | Confirm assignment |
| `/api/team/teams` | GET | List teams |
| `/api/team/teams` | POST | Create team |
| `/api/team/teams/<team_id>` | GET, PUT, DELETE | Manage teams |
| `/api/team/teams/<team_id>/members` | POST | Add member to team |
| `/api/team/teams/<team_id>/members/<user_id>` | DELETE | Remove member from team |
| `/api/team/capacity` | GET | Get professional capacity metrics |
| `/api/team/capacity-weights` | GET, PUT | Manage capacity calculation weights |
| `/api/team/capacity/<user_id>` | PUT | Update professional capacity |
| `/api/team/admin-dashboard-stats` | GET | Admin dashboard statistics |

### Key Features
- **Member Management**: CRUD operations on team members
- **AI Matching Service**: Matches professionals to clients based on criteria
- **Capacity Management**: Tracks and manages professional workload
- **Weekly Reports**: Scheduled report generation and sending
- **Trial Management**: Manages trial periods for clients
- **OKR System**: Objectives and Key Results tracking
- **Leave Management**: Handles professional absences

---

## 5. Calendar Blueprint

**Path**: `/home/manu/suite-clinica/backend/corposostenibile/blueprints/calendar/`

### Files Structure
- `__init__.py` - Blueprint initialization
- `routes.py` - Main calendar routes (56KB)
- `services.py` - Google Calendar API service layer
- `scheduler.py` - Token refresh scheduler
- `tasks.py` - Async tasks for syncing
- `cli.py` - CLI commands
- `forms.py` - WTForms

### Initialization
```python
calendar_bp = Blueprint("calendar", __name__, template_folder="templates", 
                       static_folder="static", url_prefix="/calendar")
```
- **URL Prefix**: `/calendar`
- **Registered in**: `calendar.init_app(app)` at `corposostenibile/__init__.py:414`

### Main Routes

| Route | Method | Purpose | Auth |
|-------|--------|---------|------|
| `/calendar/connect` | GET | Initiate Google OAuth | Yes |
| `/calendar/disconnect` | GET | Disconnect Google account | Yes |
| `/calendar/dashboard` | GET | Calendar dashboard view | Yes |
| `/calendar/sync` | GET | Sync Google Calendar events | Yes |
| `/calendar/meetings/<cliente_id>` | GET | List meetings for client | Yes |
| `/calendar/meeting/<meeting_id>/details` | GET, POST | View/edit meeting | Yes |
| `/calendar/loom-library` | GET | Loom video library | Yes |
| `/calendar/api/events` | GET | Get events (JSON) | Yes |
| `/calendar/api/events` | POST | Create event | Yes |
| `/calendar/api/meetings/<cliente_id>` | GET | Get client meetings (JSON) | Yes |
| `/calendar/api/meeting/<meeting_id>` | GET, PUT, DELETE | Manage meeting (JSON) | Yes |
| `/calendar/api/event/<google_event_id>` | DELETE | Delete event by Google ID | Yes |
| `/calendar/api/sync-single-event` | POST | Sync single event | Yes |
| `/calendar/api/connection-status` | GET | Check Google connection | Yes |
| `/calendar/api/team/users` | GET | Get team members | Yes |
| `/calendar/api/customers/search` | GET | Search customers | Yes |
| `/calendar/api/customers/<cliente_id>/minimal` | GET | Get customer minimal info | Yes |
| `/calendar/api/customers/list` | GET | List all customers | Yes |
| `/calendar/api/admin/tokens/status` | GET | Admin: check token status | Yes (admin) |
| `/calendar/api/admin/tokens/refresh` | POST | Admin: force token refresh | Yes (admin) |
| `/calendar/api/admin/tokens/<user_id>/refresh` | POST | Admin: refresh user token | Yes (admin) |
| `/calendar/api/admin/tokens/cleanup` | POST | Admin: cleanup expired tokens | Yes (admin) |
| `/calendar/api/admin/scheduler/status` | GET | Admin: scheduler status | Yes (admin) |

### Authentication
- **OAuth**: Google Calendar OAuth2 (flask-dance)
- **Token Management**: Auto-refresh tokens, admin can force refresh
- **Session**: Flask-login required for most endpoints
- **Admin Functions**: Limited to admin users

### Request/Response Format
- **Content-Type**: `application/json`
- **POST event example**:
```json
{
  "title": "Follow-up call",
  "description": "Customer check-in",
  "start_time": "2024-03-25T14:00:00",
  "end_time": "2024-03-25T14:30:00",
  "google_calendar_id": "primary"
}
```

---

## 6. Customers/Clients Blueprint

**Path**: `/home/manu/suite-clinica/backend/corposostenibile/blueprints/customers/`

### Files Structure
- `__init__.py` - Blueprint initialization
- `routes.py` - Main routes (375KB - massive file)
- `api.py` - (not present in files list)
- `services.py` - Business logic layer
- `repository.py` - Data access layer
- `forms.py` - WTForms
- `filters.py` - Data filtering (67KB)
- `permissions.py` - Access control
- `notifications.py` - Email/notification system
- `schemas.py` - Data validation schemas
- `utils.py` - Utility functions
- `cli.py` - CLI commands
- `models/` - Customer-related models
- `tasks.py` - Celery async tasks

### Initialization
```python
customers_bp = Blueprint("customers", __name__, static_folder="static", 
                         url_prefix="/customers", cli_group="customers")
api_bp = Blueprint("api", __name__, url_prefix="/api/customers")
```
- **URL Prefixes**: `/customers`, `/api/customers`
- **Registered in**: `customers.init_app(app)` at `corposostenibile/__init__.py:399`

### Main Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/customers/dashboard/data` | POST | Dashboard metrics |
| `/customers/<cliente_id>/history/json` | GET | Customer history |
| `/customers/<cliente_id>/history/<tx_id>/restore` | POST | Restore from history |
| `/customers/<cliente_id>/field` | PATCH | Update single field |
| `/customers/<cliente_id>/update` | POST, OPTIONS | Update multiple fields |
| `/customers/<cliente_id>/delete` | POST | Delete customer |
| `/customers/<cliente_id>/freeze` | POST | Freeze customer account |
| `/customers/<cliente_id>/unfreeze` | POST | Unfreeze customer account |
| `/customers/<cliente_id>/freeze-history` | GET | Get freeze history |
| `/customers/<cliente_id>/professionisti/assign` | POST | Assign professional |
| `/customers/<cliente_id>/professionisti/<history_id>/interrupt` | POST | Remove professional |
| `/customers/<cliente_id>/professionisti/history` | GET | Professional assignment history |
| `/customers/<cliente_id>/evaluations/<service_type>` | GET | Service evaluations |
| `/customers/<cliente_id>/create-lead-for-checks` | POST | Create lead for initial checks |
| `/customers/<cliente_id>/call-bonus` | POST | Create call bonus |
| `/customers/call-bonus/<call_bonus_id>/response` | POST | Update call bonus response |
| `/customers/call-bonus/<call_bonus_id>/hm-confirm` | POST | Health manager confirmation |
| `/customers/<cliente_id>/diet/add` | POST | Add meal plan |
| `/customers/<cliente_id>/diet/change` | POST | Change meal plan |
| `/customers/<cliente_id>/diet/history` | GET | Meal plan history |
| `/customers/<cliente_id>/training/add` | POST | Add training plan |
| `/customers/<cliente_id>/training/change` | POST | Change training plan |
| `/customers/<cliente_id>/training/history` | GET | Training plan history |
| `/customers/<cliente_id>/training/<plan_id>/versions` | GET | Training versions |
| `/customers/<cliente_id>/training/<plan_id>/download` | GET | Download training plan |
| `/customers/<cliente_id>/training/<plan_id>/extra-files/add` | POST | Add extra files |
| `/customers/<cliente_id>/training/<plan_id>/extra-files/<file_id>` | DELETE | Remove file |
| `/customers/<cliente_id>/training/<plan_id>/extra-files/<file_id>/download` | GET | Download file |
| `/customers/<cliente_id>/professionisti/history` | GET | Professional history |
| `/customers/<cliente_id>/customer-care-interventions` | GET, POST | Customer care |
| `/customers/<cliente_id>/check-in-interventions` | GET, POST | Check-in interventions |
| `/customers/<cliente_id>/continuity-call-interventions` | GET, POST | Continuity calls |

### API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/customers/` | GET | List customers (paginated) |
| `/api/customers/` | POST | Create customer |
| `/api/customers/<cliente_id>` | GET | Get customer details |
| `/api/customers/<cliente_id>` | PATCH | Update customer |
| `/api/customers/<cliente_id>` | DELETE | Delete customer |
| `/api/customers/<cliente_id>/history` | GET | Customer history |
| `/api/customers/expiring` | GET | Expiring services |
| `/api/customers/unsatisfied` | GET | Unsatisfied customers |
| `/api/customers/stats` | GET | General statistics |
| `/api/customers/admin-dashboard-stats` | GET | Admin dashboard data |
| `/api/customers/origins` | GET, POST | Customer origins/sources |
| `/api/customers/origins/<origin_id>` | PUT, DELETE | Manage origin |
| `/api/customers/<cliente_id>/feedback-metrics` | GET | Feedback metrics |
| `/api/customers/<cliente_id>/weekly-checks-metrics` | GET | Check metrics |
| `/api/customers/<cliente_id>/initial-checks` | GET | Initial assessment results |
| `/api/customers/<cliente_id>/clinical-folder-export` | GET | Export as PDF |
| `/api/customers/hm-coordinatrici-dashboard` | GET | Health manager dashboard |
| `/api/customers/<cliente_id>/stati/<servizio>/storico` | GET | Service status history |
| `/api/customers/<cliente_id>/patologie/storico` | GET | Pathology history |

### Key Features
- **Customer CRUD**: Full lifecycle management
- **Professional Assignment**: AI-powered matching and manual assignment
- **Meal Plans**: Nutrition planning and management
- **Training Plans**: Training schedule and material management
- **History Tracking**: Audit trail of all changes
- **Freeze/Unfreeze**: Pause customer accounts
- **Dashboard**: Comprehensive analytics and metrics
- **Export**: PDF export of clinical folder

---

## 7. Quality Blueprint

**Path**: `/home/manu/suite-clinica/backend/corposostenibile/blueprints/quality/`

### Files Structure
- `__init__.py` - Blueprint initialization
- `routes.py` - All quality score endpoints (31KB)
- `services/` - Service layer for calculations

### Initialization
```python
bp = Blueprint('quality', __name__, url_prefix='/quality/api', template_folder='templates')
```
- **URL Prefix**: `/quality/api`
- **Registered in**: Direct registration in main `__init__.py:462`

### Main Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/quality/api/weekly-scores` | GET | Get weekly quality scores |
| `/quality/api/professionista/<user_id>/trend` | GET | Professional quality trend |
| `/quality/api/dashboard/stats` | GET | Quality dashboard statistics |
| `/quality/api/calculate` | POST | Calculate quality score |
| `/quality/api/calcola/<dept_key>` | POST | Calculate by department |
| `/quality/api/clienti-eleggibili/<prof_id>` | GET | Get eligible clients for professional |
| `/quality/api/check-responses/<prof_id>` | GET | Get professional's check responses |
| `/quality/api/calcola-trimestrale` | POST | Calculate quarterly score |
| `/quality/api/quarterly-summary` | GET | Quarterly summary |
| `/quality/api/professionista/<user_id>/kpi-breakdown` | GET | Professional KPI breakdown |

### Authentication
- All routes require login
- **Admin Functions**: `admin_required` decorator for special operations
- **Team Leader Access**: Specific routes limited to team leaders

---

## 8. Review/Training Blueprint

**Path**: `/home/manu/suite-clinica/backend/corposostenibile/blueprints/review/`

### Files Structure
- `__init__.py` - Blueprint initialization
- `routes.py` - All review and training routes (79KB)
- `forms.py` - WTForms
- `helpers.py` - Helper functions
- `email_service.py` - Email notifications
- `filters.py` - Jinja filters

### Initialization
```python
bp = Blueprint('review', __name__, template_folder='templates', 
               static_folder='static', url_prefix='/review')
```
- **URL Prefix**: `/review`
- **Registered in**: `review.init_app(app)` at `corposostenibile/__init__.py:407`

### Main Routes (Reviews)

| Route | Method | Purpose |
|-------|--------|---------|
| `/review/` | GET | List reviews |
| `/review/member/<user_id>` | GET | Member review details |
| `/review/create/<user_id>` | GET, POST | Create new review |
| `/review/edit/<review_id>` | GET, POST | Edit review |
| `/review/acknowledge/<review_id>` | POST | Acknowledge reading review |
| `/review/delete/<review_id>` | POST | Delete review |
| `/review/message/<review_id>` | POST | Send message in review |
| `/review/message/<message_id>/read` | POST | Mark message as read |
| `/review/messages/mark-all-read/<review_id>` | POST | Mark all as read |
| `/review/stats` | GET | Review statistics |

### Training Request Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/review/request` | GET, POST | Request training from manager |
| `/review/requests/my` | GET | List my training requests |
| `/review/requests/received` | GET | List received requests |
| `/review/request/<request_id>/respond` | GET, POST | Respond to request |
| `/review/request/<request_id>/create-training` | GET, POST | Create training from request |
| `/review/request/<request_id>/cancel` | POST | Cancel request |

### API Routes (React)

| Route | Method | Purpose |
|-------|--------|---------|
| `/review/api/my-trainings` | GET | Get my trainings |
| `/review/api/my-requests` | GET | Get my requests |
| `/review/api/received-requests` | GET | Received requests |
| `/review/api/given-trainings` | GET | Trainings given by user |
| `/review/api/request-recipients` | GET | Who to send requests to |
| `/review/api/request` | POST | Create training request |
| `/review/api/request/<request_id>/cancel` | POST | Cancel request |
| `/review/api/request/<request_id>/respond` | POST | Respond to request |
| `/review/api/<review_id>/acknowledge` | POST | Acknowledge review |
| `/review/api/<review_id>/message` | POST | Send message |
| `/review/api/<review_id>/mark-all-read` | POST | Mark all messages read |
| `/review/api/admin/professionals` | GET | Admin: list professionals |
| `/review/api/admin/trainings/<user_id>` | GET | Admin: user trainings |
| `/review/api/admin/trainings/<user_id>` | POST | Admin: create training |
| `/review/api/admin/dashboard-stats` | GET | Admin dashboard stats |

### Key Features
- **Reviews**: Performance reviews by managers
- **Training Tracking**: Request, creation, and tracking of training
- **Messaging**: Communication within review context
- **Admin Management**: Full CRUD for admins
- **Email Notifications**: Automatic notifications on important events

---

## 9. Tasks Blueprint

**Path**: `/home/manu/suite-clinica/backend/corposostenibile/blueprints/tasks/`

### Files Structure
- `__init__.py` - Blueprint initialization
- `routes.py` - Task management endpoints (18KB)
- `tasks.py` - Celery async tasks (11KB)
- `events.py` - Event listeners for task changes (15KB)
- `teams_tasks.py` - Team-specific task logic (2KB)

### Initialization
```python
bp = Blueprint('tasks', __name__)
```
- **URL Prefix**: `/api/tasks` (inferred from routes)
- **Registered in**: `tasks.init_app(app)` at `corposostenibile/__init__.py:422`

### Main Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/tasks/` | GET | List tasks (paginated, filtered) |
| `/api/tasks/` | POST | Create new task |
| `/api/tasks/<task_id>` | PUT | Update task |
| `/api/tasks/stats` | GET | Task statistics |
| `/api/tasks/filter-options` | GET | Available filter options |

### Task Properties
- **Status**: open, in_progress, done, cancelled
- **Visibility**: Global, department-level, or user-specific
- **Filtering**: By status, assignee, department, priority

### Key Features
- **Visibility Scoping**: Tasks visible based on user role
- **Admin Filtering**: Additional admin-only filters
- **Statistics**: Dashboard metrics for task overview
- **Event-driven**: Changes trigger events (listeners registered)

---

## Summary Table: Blueprint Registration

| Blueprint | URL Prefix | Routes File | Init Location |
|-----------|-----------|-------------|---|
| **auth** | `/auth` | routes.py (392 lines) | `corposostenibile/__init__.py:400` |
| **team** | `/team`, `/api/team` | api.py (3154 lines) | `corposostenibile/__init__.py:401` |
| **calendar** | `/calendar` | routes.py (56KB) | `corposostenibile/__init__.py:414` |
| **customers** | `/customers`, `/api/customers` | routes.py (375KB) | `corposostenibile/__init__.py:399` |
| **quality** | `/quality/api` | routes.py (31KB) | `corposostenibile/__init__.py:462` |
| **review** | `/review` | routes.py (79KB) | `corposostenibile/__init__.py:407` |
| **tasks** | `/api/tasks` | routes.py (18KB) | `corposostenibile/__init__.py:422` |

---

## Key Authentication & Authorization Patterns

### Session-Based Authentication
- **Login Manager**: Flask-Login with session protection
- **User Loader**: Loads user from session by ID
- **Login Required**: `@login_required` decorator
- **CSRF Protection**: Enabled with token in cookie

### Role-Based Access Control
- **Roles**: admin, manager, professional, health_manager, etc.
- **ACL System**: `SimpleACL` in-memory (allows/checks permissions)
- **Decorators**: Custom decorators for role/permission checks
- **Route-level Guards**: Checks in route handlers

### Request/Response Format
- **HTML Routes**: Jinja2 template rendering
- **API Routes**: JSON with standard response format
- **Error Handling**: JSON error responses with appropriate HTTP status codes
- **CSRF**: Token validated for POST/PUT/DELETE requests

---

## Common Patterns

### Blueprint Registration Pattern
```python
# In __init__.py
def init_app(app: Flask):
    app.register_blueprint(bp, url_prefix="/prefix")
    # Optional: CLI, ACL, filters
```

### API Response Format
```json
Success:
{
  "success": true,
  "data": {...}
}

Error:
{
  "success": false,
  "error": "Error message"
}
```

### Authentication Check Pattern
```python
from flask_login import login_required, current_user

@bp.route('/endpoint')
@login_required
def endpoint():
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    # Handle request
```


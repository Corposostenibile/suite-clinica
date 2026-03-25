# Frontend API Endpoints Mapping

Elenco completo di TUTTI gli endpoint API chiamati dal frontend React.
Organizzati per categoria di business logic.

## 📋 AUTENTICAZIONE (6 endpoint)

### Authentication Service (authService.js)

| Method | Endpoint | Called By | Params | Auth |
|--------|----------|-----------|--------|------|
| POST | /auth/login | Login form | email, password | No |
| POST | /auth/logout | Logout button | - | Yes |
| POST | /auth/forgot-password | Forgot password form | email | No |
| GET | /auth/me | App init, Profile | - | Yes |
| GET | /auth/impersonate/users | Admin panel | - | Yes (Admin) |
| POST | /auth/stop-impersonation | Admin panel | - | Yes (Admin) |

---

## 👥 TEAM & UTENTI (11 endpoint)

### Team Service (teamService.js)

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

### Trial Users Service (trialUserService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /trial-users | Admin panel | - |
| POST | /trial-users | Create trial form | user_id, trial_type |
| GET | /trial-users/supervisors | Trial management | - |

---

## 📅 CALENDAR & EVENTS (11 endpoint)

### Calendar Service (calendarService.js)

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

---

## 🏥 CLIENTI/PAZIENTI (4 endpoint)

### Clienti Service (clientiService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /customers/api/search | Client list search | q (search term) |
| GET | /customers/{id}/stati/{servizio}/storico | Client detail | - |
| GET | /customers/{id}/patologie/storico | Medical history | - |
| GET | /customers/{id}/nutrition/history | Nutrition history | - |

### Dashboard Service (dashboardService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /v1/customers/stats | Main dashboard | - |

### Calendar Customer Search (ghlService.js + calendarService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /calendar/api/customers/search | Calendar integration | q (search) |

---

## 📊 QUALITÀ & REVIEW (5 endpoint)

### Quality Service (qualityService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /quality/api/weekly-scores | Quality dashboard | - |
| POST | /quality/api/calculate | Calculate quality | - |
| GET | /quality/api/dashboard/stats | Quality dashboard | - |
| POST | /quality/api/calcola-trimestrale | Quarterly calculation | - |
| GET | /quality/api/quarterly-summary | Quarterly view | - |

---

## 📝 TASKS/COMPITI (4 endpoint)

### Task Service (taskService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /tasks/ | Tasks list | filters, page |
| GET | /tasks/stats | Tasks stats widget | - |
| GET | /tasks/filter-options | Task filters | - |
| POST | /tasks/ | Create task form | title, description, etc |

---

## 🎓 TRAINING/FORMAZIONE (8 endpoint)

### Training Service (trainingService.js)

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

---

## 🔍 RICERCA (1 endpoint)

### Search Service (searchService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /search/global | Global search bar | q (search term) |

---

## 📰 NEWS (1 endpoint)

### News Service (newsService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /news/list | News widget | limit |

---

## 📌 POST-IT (3 endpoint)

### Postit Service (postitService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /list | Postit list | - |
| POST | /create | Create postit form | content, target, etc |
| POST | /reorder | Drag & drop reorder | order_data |

---

## 🔔 PUSH NOTIFICATIONS (5 endpoint)

### Push Notification Service (pushNotificationService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| POST | /push/subscriptions | Register push | subscription |
| GET | /push/public-key | Init push | - |
| DELETE | /push/subscriptions | Unregister push | subscription |
| GET | /push/notifications | Fetch notifications | - |

---

## 🎥 LOOM INTEGRATION (2 endpoint)

### Loom Service (loomService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /loom/api/patients/search | Loom patient search | q (search) |
| GET | /loom/api/recordings | Loom videos list | patient_id |

---

## 🏢 TEAM TICKETS (1 endpoint)

### Team Tickets Service (teamTicketsService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /team-tickets/ | Tickets list | filters, page |

---

## 🔗 INTEGRAZIONI ESTERNE (2 endpoint)

### Old Suite Service (oldSuiteService.js)

| Method | Endpoint | Called By | Params |
|--------|----------|-----------|--------|
| GET | /leads | Leads import | - |
| POST | /confirm-assignment | Assign lead | lead_id |

---

## 📊 SUMMARY

- **Total Endpoints**: 67
- **GET requests**: 47
- **POST requests**: 16
- **DELETE requests**: 2
- **PUT requests**: 0
- **PATCH requests**: 0

### By Category:
- Authentication: 6
- Team & Users: 11
- Calendar: 11
- Clients: 4
- Quality: 5
- Tasks: 4
- Training: 8
- Search: 1
- News: 1
- Postit: 3
- Push Notifications: 5
- Loom: 2
- Team Tickets: 1
- External: 2


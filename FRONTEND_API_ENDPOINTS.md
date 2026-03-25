# SUITE CLINICA - FRONTEND API ENDPOINTS ANALYSIS

Documento completo di tutti gli endpoint API chiamati dal frontend React.
Data analisi: 2025-03-25

---

## AUTHENTICATION & SESSION

### POST /auth/login
- **Service**: authService.js (line 8)
- **Params**: `{ email, password, remember_me }`
- **Auth**: NO (public endpoint)
- **Notes**: Login with credentials

### POST /auth/logout
- **Service**: authService.js (line 20)
- **Params**: None
- **Auth**: YES
- **Notes**: Logout current user

### GET /auth/me
- **Service**: authService.js (line 55)
- **Params**: None
- **Auth**: YES
- **Notes**: Get current user info

### POST /auth/forgot-password
- **Service**: authService.js (line 28)
- **Params**: `{ email }`
- **Auth**: NO
- **Notes**: Request password reset email

### POST /auth/reset-password/{token}
- **Service**: authService.js (line 36)
- **Params**: `{ password, password2 }`
- **Auth**: NO
- **Notes**: Reset password with token

### GET /auth/verify-reset-token/{token}
- **Service**: authService.js (line 47)
- **Params**: None
- **Auth**: NO
- **Notes**: Verify reset token validity

### GET /auth/impersonate/users
- **Service**: authService.js (line 63)
- **Params**: None
- **Auth**: YES (admin only)
- **Notes**: List users for impersonation

### POST /auth/impersonate/{userId}
- **Service**: authService.js (line 71)
- **Params**: None
- **Auth**: YES (admin only)
- **Notes**: Start impersonation as another user

### POST /auth/stop-impersonation
- **Service**: authService.js (line 79)
- **Params**: None
- **Auth**: YES
- **Notes**: Stop impersonation and return to admin account

---

## CUSTOMERS MANAGEMENT

### GET /v1/customers/
- **Service**: clientiService.js (line 258)
- **Params**: `{ page, per_page, search, stato, filtri... }`
- **Auth**: YES
- **Notes**: Get paginated list of customers with filters

### GET /v1/customers/{id}
- **Service**: clientiService.js (line 268)
- **Params**: None
- **Auth**: YES
- **Notes**: Get single customer details

### POST /v1/customers/
- **Service**: clientiService.js (line 278)
- **Params**: Customer data object
- **Auth**: YES
- **Notes**: Create new customer

### PATCH /v1/customers/{id}
- **Service**: clientiService.js (line 289)
- **Params**: Updated customer data
- **Auth**: YES
- **Notes**: Update customer (partial update)

### DELETE /v1/customers/{id}
- **Service**: clientiService.js (line 311)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete customer (soft delete likely)

### GET /v1/customers/{id}/history
- **Service**: clientiService.js (line 322)
- **Params**: `{ limit = 20 }`
- **Auth**: YES
- **Notes**: Get customer history/changes

### GET /v1/customers/stats
- **Service**: clientiService.js (line 331), dashboardService.js (line 18)
- **Params**: None
- **Auth**: YES
- **Notes**: Get customer KPI stats (total, active by specialty, new this month)

### GET /v1/customers/admin-dashboard-stats
- **Service**: clientiService.js (line 340)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Comprehensive admin dashboard stats with KPIs and distributions

### GET /v1/customers/ [view=nutrizione]
- **Service**: clientiService.js (line 352)
- **Params**: `{ ...params, view: 'nutrizione' }`
- **Auth**: YES
- **Notes**: Get customers for Nutrizione specialty view

### GET /v1/customers/ [view=coach]
- **Service**: clientiService.js (line 367)
- **Params**: `{ ...params, view: 'coach' }`
- **Auth**: YES
- **Notes**: Get customers for Coach specialty view

### GET /v1/customers/ [view=psicologia]
- **Service**: clientiService.js (line 382)
- **Params**: `{ ...params, view: 'psicologia' }`
- **Auth**: YES
- **Notes**: Get customers for Psychology specialty view

### GET /v1/customers/expiring
- **Service**: clientiService.js (line 392)
- **Params**: `{ page, per_page, ... }`
- **Auth**: YES
- **Notes**: Get customers with expiring subscriptions

### GET /v1/customers/unsatisfied
- **Service**: clientiService.js (line 397)
- **Params**: `{ page, per_page, ... }`
- **Auth**: YES
- **Notes**: Get customers with unsatisfied ratings

### GET /v1/customers/hm-coordinatrici-dashboard
- **Service**: clientiService.js (line 402, 407)
- **Params**: `{ cliente_id, page, per_page, ... }`
- **Auth**: YES (health managers)
- **Notes**: HM coordinators dashboard view

### GET /v1/customers/specialty-kpi
- **Service**: clientiService.js (line 428)
- **Params**: `{ specialty, professional_id }`
- **Auth**: YES
- **Notes**: Get KPI stats by specialty and optional professional

### GET /v1/customers/{id}/feedback-metrics
- **Service**: clientiService.js (line 438)
- **Params**: None
- **Auth**: YES
- **Notes**: Get feedback/satisfaction metrics for customer

### GET /v1/customers/{id}/initial-checks
- **Service**: clientiService.js (line 448)
- **Params**: None
- **Auth**: YES
- **Notes**: Get initial checks (Check 1, 2) from lead assignment

### GET /v1/customers/{id}/weekly-checks-metrics
- **Service**: clientiService.js (line 458)
- **Params**: None
- **Auth**: YES
- **Notes**: Get weekly checks metrics data

### GET /v1/customers/{id}/customer-care-interventions
- **Service**: clientiService.js (line 470)
- **Params**: None
- **Auth**: YES
- **Notes**: Get customer care interventions list

### POST /v1/customers/{id}/customer-care-interventions
- **Service**: clientiService.js (line 481)
- **Params**: Intervention data object
- **Auth**: YES
- **Notes**: Create new customer care intervention

### PUT /v1/customers/customer-care-interventions/{interventionId}
- **Service**: clientiService.js (line 492)
- **Params**: Updated intervention data
- **Auth**: YES
- **Notes**: Update customer care intervention

### DELETE /v1/customers/customer-care-interventions/{interventionId}
- **Service**: clientiService.js (line 502)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete customer care intervention

### GET /v1/customers/{id}/check-in-interventions
- **Service**: clientiService.js (line 509)
- **Params**: None
- **Auth**: YES
- **Notes**: Get check-in interventions for customer

### POST /v1/customers/{id}/check-in-interventions
- **Service**: clientiService.js (line 514)
- **Params**: Intervention data
- **Auth**: YES
- **Notes**: Create check-in intervention

### PUT /v1/customers/check-in-interventions/{interventionId}
- **Service**: clientiService.js (line 519)
- **Params**: Updated data
- **Auth**: YES
- **Notes**: Update check-in intervention

### DELETE /v1/customers/check-in-interventions/{interventionId}
- **Service**: clientiService.js (line 524)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete check-in intervention

### GET /v1/customers/trustpilot-overview
- **Service**: clientiService.js (line 531)
- **Params**: Optional filters
- **Auth**: YES
- **Notes**: Get Trustpilot reviews overview

### GET /v1/customers/{id}/trustpilot
- **Service**: clientiService.js (line 536)
- **Params**: None
- **Auth**: YES
- **Notes**: Get Trustpilot status for customer

### POST /v1/customers/{id}/trustpilot/link
- **Service**: clientiService.js (line 541)
- **Params**: Optional data
- **Auth**: YES
- **Notes**: Generate Trustpilot review link

### POST /v1/customers/{id}/trustpilot/invite
- **Service**: clientiService.js (line 546)
- **Params**: Optional data
- **Auth**: YES
- **Notes**: Send Trustpilot review invite

### GET /v1/customers/{id}/video-review-requests
- **Service**: clientiService.js (line 553)
- **Params**: None
- **Auth**: YES
- **Notes**: Get video review requests for customer

### POST /v1/customers/{id}/video-review-requests/booked
- **Service**: clientiService.js (line 558)
- **Params**: Optional data
- **Auth**: YES
- **Notes**: Create video review booked event

### POST /v1/customers/video-review-requests/{requestId}/hm-confirm
- **Service**: clientiService.js (line 563)
- **Params**: Confirmation data
- **Auth**: YES (HM)
- **Notes**: HM confirms video review

### GET /v1/customers/{id}/clinical-folder-export
- **Service**: clientiService.js (line 568)
- **Params**: None
- **Auth**: YES
- **Notes**: Export clinical folder as PDF (blob response)

### GET /v1/customers/{clienteId}/professionisti/history
- **Service**: clientiService.js (line 579)
- **Params**: None
- **Auth**: YES
- **Notes**: Get professional assignment history

### POST /v1/customers/{clienteId}/professionisti/assign
- **Service**: clientiService.js (line 590)
- **Params**: `{ tipo_professionista, user_id, data_dal, motivazione_aggiunta }`
- **Auth**: YES
- **Notes**: Assign professional to customer

### POST /v1/customers/{clienteId}/professionisti/{historyId}/interrupt
- **Service**: clientiService.js (line 602)
- **Params**: `{ motivazione_interruzione, data_al }`
- **Auth**: YES
- **Notes**: Interrupt professional assignment

### POST /v1/customers/{clienteId}/professionisti/legacy/interrupt
- **Service**: clientiService.js (line 613)
- **Params**: `{ user_id, tipo_professionista, motivazione_interruzione }`
- **Auth**: YES
- **Notes**: Interrupt legacy professional assignment

### GET /customers/api/search
- **Service**: clientiService.js (line 627) - HTML blueprint endpoint
- **Params**: `{ q }`
- **Auth**: YES
- **Notes**: Search customers (not REST API)

### GET /customers/{clienteId}/stati/{servizio}/storico
- **Service**: clientiService.js (line 734) - HTML blueprint endpoint
- **Params**: None
- **Auth**: YES
- **Notes**: Get state history for service (nutrizione, coach, psicologia, etc.)

### GET /customers/{clienteId}/patologie/storico
- **Service**: clientiService.js (line 745) - HTML blueprint endpoint
- **Params**: None
- **Auth**: YES
- **Notes**: Get pathology history

### GET /customers/{clienteId}/nutrition/history
- **Service**: clientiService.js (line 758) - HTML blueprint endpoint
- **Params**: None
- **Auth**: YES
- **Notes**: Get meal plans history

### GET /customers/{clienteId}/nutrition/{planId}/versions
- **Service**: clientiService.js (line 769) - HTML blueprint endpoint
- **Params**: None
- **Auth**: YES
- **Notes**: Get meal plan versions

### GET /customers/{clienteId}/nutrition/{planId}/download
- **Service**: clientiService.js (line 780)
- **Params**: None
- **Auth**: YES
- **Notes**: Download meal plan PDF (URL only, not API call)

### POST /customers/{clienteId}/nutrition/change
- **Service**: clientiService.js (line 791) - HTML blueprint endpoint
- **Params**: FormData with plan_id, start_date, end_date, notes, change_reason, file
- **Auth**: YES
- **Notes**: Update meal plan (multipart/form-data)

### GET /v1/customers/{clienteId}/anamnesi/{serviceType}
- **Service**: clientiService.js (line 807)
- **Params**: None
- **Auth**: YES
- **Notes**: Get anamnesi for service (nutrizione, coaching, psicologia)

### POST /v1/customers/{clienteId}/anamnesi/{serviceType}
- **Service**: clientiService.js (line 819)
- **Params**: `{ content }`
- **Auth**: YES
- **Notes**: Create/update anamnesi

### GET /v1/customers/{clienteId}/diary/{serviceType}
- **Service**: clientiService.js (line 832)
- **Params**: None
- **Auth**: YES
- **Notes**: Get diary entries for service

### POST /v1/customers/{clienteId}/diary/{serviceType}
- **Service**: clientiService.js (line 847)
- **Params**: `{ content, entry_date }`
- **Auth**: YES
- **Notes**: Create diary entry

### PUT /v1/customers/{clienteId}/diary/{serviceType}/{entryId}
- **Service**: clientiService.js (line 863)
- **Params**: `{ content, entry_date }`
- **Auth**: YES
- **Notes**: Update diary entry

### DELETE /v1/customers/{clienteId}/diary/{serviceType}/{entryId}
- **Service**: clientiService.js (line 875)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete diary entry

### GET /v1/customers/{clienteId}/diary/{serviceType}/{entryId}/history
- **Service**: clientiService.js (line 887)
- **Params**: None
- **Auth**: YES
- **Notes**: Get diary entry edit history

### GET /customers/{clienteId}/training/history
- **Service**: clientiService.js (line 899) - HTML blueprint endpoint
- **Params**: None
- **Auth**: YES
- **Notes**: Get training plans history

### POST /customers/{clienteId}/training/add
- **Service**: clientiService.js (line 910) - HTML blueprint endpoint
- **Params**: FormData with name, start_date, end_date, notes, piano_allenamento_file
- **Auth**: YES
- **Notes**: Add training plan (multipart/form-data)

### GET /customers/{clienteId}/training/{planId}/versions
- **Service**: clientiService.js (line 924) - HTML blueprint endpoint
- **Params**: None
- **Auth**: YES
- **Notes**: Get training plan versions

### GET /customers/{clienteId}/training/{planId}/download
- **Service**: clientiService.js (line 935)
- **Params**: None
- **Auth**: YES
- **Notes**: Download training plan PDF (URL only)

### POST /customers/{clienteId}/training/change
- **Service**: clientiService.js (line 945) - HTML blueprint endpoint
- **Params**: FormData
- **Auth**: YES
- **Notes**: Update training plan (multipart/form-data)

### GET /customers/{clienteId}/location/history
- **Service**: clientiService.js (line 960) - HTML blueprint endpoint
- **Params**: None
- **Auth**: YES
- **Notes**: Get training locations history

### POST /customers/{clienteId}/location/add
- **Service**: clientiService.js (line 971) - HTML blueprint endpoint
- **Params**: `{ location, start_date, end_date, notes }`
- **Auth**: YES
- **Notes**: Add training location

### POST /customers/{clienteId}/location/change/{locationId}
- **Service**: clientiService.js (line 983) - HTML blueprint endpoint
- **Params**: `{ location, start_date, end_date, notes, change_reason }`
- **Auth**: YES
- **Notes**: Update training location

### GET /v1/customers/{clienteId}/call-bonus-history
- **Service**: clientiService.js (line 995)
- **Params**: None
- **Auth**: YES
- **Notes**: Get call bonus history

### POST /v1/customers/{clienteId}/call-bonus-request
- **Service**: clientiService.js (line 1006)
- **Params**: `{ tipo_professionista, note_richiesta }`
- **Auth**: YES
- **Notes**: Create call bonus request with AI analysis

### POST /v1/customers/call-bonus-select/{callBonusId}
- **Service**: clientiService.js (line 1017)
- **Params**: `{ professional_id }`
- **Auth**: YES
- **Notes**: Select professional for call bonus

### POST /v1/customers/call-bonus-confirm/{callBonusId}
- **Service**: clientiService.js (line 1029)
- **Params**: None
- **Auth**: YES
- **Notes**: Confirm call bonus booking

### POST /v1/customers/call-bonus-decline/{callBonusId}
- **Service**: clientiService.js (line 1039)
- **Params**: None
- **Auth**: YES
- **Notes**: Decline call bonus (professional refuses)

### POST /v1/customers/call-bonus-interest/{callBonusId}
- **Service**: clientiService.js (line 1051)
- **Params**: `{ interested, motivazione }`
- **Auth**: YES
- **Notes**: Respond to call bonus interest (professional confirms/refuses patient interest)

### GET /v1/customers/{clienteId}/call-rinnovo-history
- **Service**: clientiService.js (line 1066)
- **Params**: None
- **Auth**: YES
- **Notes**: Get call rinnovo (renewal) history

### POST /v1/customers/{clienteId}/call-rinnovo-request
- **Service**: clientiService.js (line 1077)
- **Params**: `{ tipo_professionista, note_richiesta }`
- **Auth**: YES
- **Notes**: Create call rinnovo request

### POST /v1/customers/call-rinnovo/{callRinnovoId}/accept
- **Service**: clientiService.js (line 1087)
- **Params**: None
- **Auth**: YES
- **Notes**: Accept call rinnovo

### POST /v1/customers/call-rinnovo/{callRinnovoId}/decline
- **Service**: clientiService.js (line 1097)
- **Params**: None
- **Auth**: YES
- **Notes**: Decline call rinnovo

### POST /v1/customers/call-rinnovo/{callRinnovoId}/confirm
- **Service**: clientiService.js (line 1108)
- **Params**: `{ note_hm }`
- **Auth**: YES
- **Notes**: Confirm call rinnovo as completed

---

## CHECKS MANAGEMENT

### GET /api/client-checks/cliente/{clienteId}/checks
- **Service**: checkService.js (line 55)
- **Params**: None
- **Auth**: YES
- **Notes**: Get all checks and responses for a client

### POST /api/client-checks/generate/{checkType}/{clienteId}
- **Service**: checkService.js (line 66)
- **Params**: None (checkType: weekly, dca, minor)
- **Auth**: YES
- **Notes**: Generate or retrieve check link for client

### GET /api/client-checks/da-leggere
- **Service**: checkService.js (line 77)
- **Params**: None
- **Auth**: YES
- **Notes**: Get unread checks for current professional

### POST /api/client-checks/conferma-lettura/{responseType}/{responseId}
- **Service**: checkService.js (line 88)
- **Params**: None
- **Auth**: YES
- **Notes**: Confirm check has been read (weekly_check or dca_check)

### GET /api/client-checks/response/{responseType}/{responseId}
- **Service**: checkService.js (line 101)
- **Params**: None
- **Auth**: YES
- **Notes**: Get detailed response data (weekly, dca, minor)

### GET /api/client-checks/azienda/stats
- **Service**: checkService.js (line 133)
- **Params**: `{ period, start_date, end_date, prof_type, prof_id, page, per_page, check_type }`
- **Auth**: YES
- **Notes**: Get company-wide check statistics

### GET /api/client-checks/admin/dashboard-stats
- **Service**: checkService.js (line 142)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Get comprehensive admin dashboard stats for checks

### GET /api/client-checks/professionisti/{profType}
- **Service**: checkService.js (line 152)
- **Params**: None
- **Auth**: YES
- **Notes**: Get list of professionals by type (nutrizione, coach, psicologia)

### GET /api/client-checks/initial-assignments
- **Service**: checkService.js (line 166)
- **Params**: `{ client_search, status, page, per_page, client_ids }`
- **Auth**: YES
- **Notes**: Get initial checks assignments aggregated by lead

### GET /api/client-checks/initial-assignments/{leadId}/check/{checkNumber}/response
- **Service**: checkService.js (line 186)
- **Params**: None
- **Auth**: YES
- **Notes**: Get compiled initial check response detail for a lead

### GET /api/client-checks/public/{checkType}/{token}
- **Service**: publicCheckService.js (line 34)
- **Params**: None
- **Auth**: NO (public)
- **Notes**: Get check info and client data by token

### POST /api/client-checks/public/{checkType}/{token}
- **Service**: publicCheckService.js (line 66, 81, 92)
- **Params**: FormData (weekly) or JSON (dca, minor)
- **Auth**: NO (public)
- **Notes**: Submit check response (weekly, dca, or minor)

---

## SEARCH

### GET /api/search/global
- **Service**: searchService.js (line 5)
- **Params**: `{ q, category, page, per_page }`
- **Auth**: YES
- **Notes**: Global search across entities

---

## TASKS

### GET /api/tasks/
- **Service**: taskService.js (line 9)
- **Params**: `{ category, completed, priority, ... }`
- **Auth**: YES
- **Notes**: Get list of tasks with filters

### GET /api/tasks/stats
- **Service**: taskService.js (line 17)
- **Params**: None
- **Auth**: YES
- **Notes**: Get task statistics

### GET /api/tasks/filter-options
- **Service**: taskService.js (line 22)
- **Params**: None
- **Auth**: YES
- **Notes**: Get available filter options

### POST /api/tasks/
- **Service**: taskService.js (line 31)
- **Params**: Task data object
- **Auth**: YES
- **Notes**: Create new task (manual)

### PUT /api/tasks/{id}
- **Service**: taskService.js (line 41, 60)
- **Params**: Updated task data
- **Auth**: YES
- **Notes**: Update task

### DELETE /api/tasks/{id}
- **Service**: taskService.js (line 50)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete task

---

## TEAM MANAGEMENT

### GET /api/team/members
- **Service**: teamService.js (line 163)
- **Params**: Optional filters
- **Auth**: YES
- **Notes**: Get list of team members with filters and pagination

### GET /api/team/members/{id}
- **Service**: teamService.js (line 171)
- **Params**: None
- **Auth**: YES
- **Notes**: Get single team member details

### POST /api/team/members
- **Service**: teamService.js (line 179)
- **Params**: Member data object
- **Auth**: YES
- **Notes**: Create new team member

### PUT /api/team/members/{id}
- **Service**: teamService.js (line 187)
- **Params**: Updated member data
- **Auth**: YES
- **Notes**: Update team member

### DELETE /api/team/members/{id}
- **Service**: teamService.js (line 195)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete team member

### POST /api/team/members/{id}/toggle
- **Service**: teamService.js (line 203)
- **Params**: None
- **Auth**: YES
- **Notes**: Toggle team member active status

### POST /api/team/members/{id}/avatar
- **Service**: teamService.js (line 213)
- **Params**: FormData with 'avatar' file
- **Auth**: YES
- **Notes**: Upload avatar for team member (multipart/form-data)

### GET /api/team/departments
- **Service**: teamService.js (line 223)
- **Params**: None
- **Auth**: YES
- **Notes**: Get departments list

### GET /api/team/stats
- **Service**: teamService.js (line 231)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Get team statistics

### GET /api/team/admin-dashboard-stats
- **Service**: teamService.js (line 239)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Get comprehensive admin dashboard stats for professionals

### GET /api/team/teams
- **Service**: teamService.js (line 250)
- **Params**: `{ team_type, active, q }`
- **Auth**: YES
- **Notes**: Get list of teams with optional filters

### GET /api/team/teams/{id}
- **Service**: teamService.js (line 258)
- **Params**: None
- **Auth**: YES
- **Notes**: Get single team by ID with members

### POST /api/team/teams
- **Service**: teamService.js (line 267)
- **Params**: `{ name, team_type, head_id, description, member_ids }`
- **Auth**: YES
- **Notes**: Create new team

### PUT /api/team/teams/{id}
- **Service**: teamService.js (line 277)
- **Params**: `{ name, head_id, description, is_active, member_ids }`
- **Auth**: YES
- **Notes**: Update team

### DELETE /api/team/teams/{id}
- **Service**: teamService.js (line 285)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete team (soft delete)

### POST /api/team/teams/{teamId}/members
- **Service**: teamService.js (line 293)
- **Params**: `{ user_id }`
- **Auth**: YES
- **Notes**: Add member to team

### DELETE /api/team/teams/{teamId}/members/{userId}
- **Service**: teamService.js (line 301)
- **Params**: None
- **Auth**: YES
- **Notes**: Remove member from team

### GET /api/team/available-leaders/{teamType}
- **Service**: teamService.js (line 309)
- **Params**: None
- **Auth**: YES
- **Notes**: Get available team leaders for a team type

### GET /api/team/available-professionals/{teamType}
- **Service**: teamService.js (line 317)
- **Params**: None
- **Auth**: YES
- **Notes**: Get available professionals for a team type

### GET /api/team/members/{memberId}/clients
- **Service**: teamService.js (line 327)
- **Params**: `{ page, per_page, q, stato }`
- **Auth**: YES
- **Notes**: Get clients associated with a team member (professional)

### GET /api/team/members/{memberId}/checks
- **Service**: teamService.js (line 337)
- **Params**: `{ period, start_date, end_date, page, per_page }`
- **Auth**: YES
- **Notes**: Get check responses from clients associated with team member

### GET /api/team/capacity
- **Service**: teamService.js (line 348)
- **Params**: Optional filters
- **Auth**: YES
- **Notes**: Get professional capacity rows (admin/cco: all, team_leader: own members)

### PUT /api/team/capacity/{userId}
- **Service**: teamService.js (line 356)
- **Params**: `{ capienza_contrattuale }`
- **Auth**: YES (admin/cco)
- **Notes**: Update contractual capacity for professional

### GET /api/team/api/assegnazioni
- **Service**: teamService.js (line 420)
- **Params**: Optional filters
- **Auth**: YES
- **Notes**: Get all professionals for AI assignments

### GET /api/team/api/assegnazioni/{userId}
- **Service**: teamService.js (line 428)
- **Params**: None
- **Auth**: YES
- **Notes**: Get single professional's assignment data

### POST /api/team/api/assegnazioni/{userId}
- **Service**: teamService.js (line 438)
- **Params**: `{ specializzazione, target_ideale, problematiche_efficaci, target_non_ideale, link_calendario, note_aggiuntive }`
- **Auth**: YES
- **Notes**: Update professional's assignment AI notes

### POST /api/team/api/assegnazioni/{userId}/toggle-disponibile
- **Service**: teamService.js (line 446)
- **Params**: None
- **Auth**: YES
- **Notes**: Toggle professional's availability for assignments

---

## CALENDAR & MEETINGS

### GET /calendar/api/connection-status
- **Service**: calendarService.js (line 101)
- **Params**: None
- **Auth**: YES
- **Notes**: Check if user is connected to Google Calendar

### GET /calendar/disconnect
- **Service**: calendarService.js (line 110)
- **Params**: None
- **Auth**: YES
- **Notes**: Disconnect from Google Calendar

### GET /calendar/api/events
- **Service**: calendarService.js (line 129)
- **Params**: `{ start, end }`
- **Auth**: YES
- **Notes**: Get events from Google Calendar

### POST /calendar/api/events
- **Service**: calendarService.js (line 139)
- **Params**: Event data object
- **Auth**: YES
- **Notes**: Create new event in Google Calendar

### DELETE /calendar/api/event/{googleEventId}
- **Service**: calendarService.js (line 149)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete event by Google event ID

### GET /calendar/api/meeting/{meetingId}
- **Service**: calendarService.js (line 161)
- **Params**: None
- **Auth**: YES
- **Notes**: Get meeting details by ID

### PUT /calendar/api/meeting/{meetingId}
- **Service**: calendarService.js (line 172)
- **Params**: Fields to update
- **Auth**: YES
- **Notes**: Update meeting details

### DELETE /calendar/api/meeting/{meetingId}
- **Service**: calendarService.js (line 182)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete meeting

### GET /calendar/api/meetings/{clienteId}
- **Service**: calendarService.js (line 195)
- **Params**: `{ user_id }`
- **Auth**: YES
- **Notes**: Get meetings for specific client

### POST /calendar/api/sync-single-event
- **Service**: calendarService.js (line 205)
- **Params**: Event data including google_event_id
- **Auth**: YES
- **Notes**: Sync single event to database

### GET /calendar/api/team/users
- **Service**: calendarService.js (line 216)
- **Params**: None
- **Auth**: YES
- **Notes**: Get list of team users

### GET /calendar/api/customers/search
- **Service**: calendarService.js (line 230)
- **Params**: `{ q, limit }`
- **Auth**: YES
- **Notes**: Search customers by name (min 3 chars)

### GET /calendar/api/customers/list
- **Service**: calendarService.js (line 241)
- **Params**: None
- **Auth**: YES
- **Notes**: Get all customers list

### GET /calendar/api/customers/{clienteId}/minimal
- **Service**: calendarService.js (line 251)
- **Params**: None
- **Auth**: YES
- **Notes**: Get minimal customer info by ID

### GET /calendar/api/admin/tokens/status
- **Service**: calendarService.js (line 273)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Get status of all OAuth tokens

### POST /calendar/api/admin/tokens/refresh
- **Service**: calendarService.js (line 282)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Force refresh all expiring tokens

### POST /calendar/api/admin/tokens/cleanup
- **Service**: calendarService.js (line 291)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Cleanup expired tokens

### POST /calendar/api/admin/tokens/{userId}/refresh
- **Service**: calendarService.js (line 301)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Refresh specific user's token

---

## POST-IT (REMINDERS)

### GET /postit/api/list
- **Service**: postitService.js (line 86)
- **Params**: None (cache-control headers, timestamp query param)
- **Auth**: YES
- **Notes**: Get all post-its for current user

### POST /postit/api/create
- **Service**: postitService.js (line 104)
- **Params**: `{ content, color, reminderAt }`
- **Auth**: YES
- **Notes**: Create new post-it

### GET /postit/api/{id}
- **Service**: postitService.js (line 114)
- **Params**: None
- **Auth**: YES
- **Notes**: Get single post-it

### PUT /postit/api/{id}
- **Service**: postitService.js (line 125)
- **Params**: `{ content, color, reminderAt, position }`
- **Auth**: YES
- **Notes**: Update post-it

### DELETE /postit/api/{id}
- **Service**: postitService.js (line 135)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete post-it

### POST /postit/api/reorder
- **Service**: postitService.js (line 145)
- **Params**: `{ order: [id1, id2, ...] }`
- **Auth**: YES
- **Notes**: Reorder post-its

---

## QUALITY SCORES

### GET /quality/api/weekly-scores
- **Service**: qualityService.js (line 172)
- **Params**: `{ specialty, week, team_id }`
- **Auth**: YES
- **Notes**: Get weekly quality scores for a specialty

### GET /quality/api/professionista/{professionistaId}/trend
- **Service**: qualityService.js (line 182)
- **Params**: None
- **Auth**: YES
- **Notes**: Get quality trend for professional (last 12 weeks)

### GET /quality/api/clienti-eleggibili/{professionistaId}
- **Service**: qualityService.js (line 193)
- **Params**: `{ week }`
- **Auth**: YES
- **Notes**: Get eligible clients for professional in a week

### GET /quality/api/check-responses/{professionistaId}
- **Service**: qualityService.js (line 207)
- **Params**: `{ week, dept }`
- **Auth**: YES
- **Notes**: Get check responses for professional in a week

### POST /quality/api/calculate
- **Service**: qualityService.js (line 222)
- **Params**: `{ specialty, week, team_id }`
- **Auth**: YES
- **Notes**: Calculate quality scores for specialty and week

### GET /quality/api/dashboard/stats
- **Service**: qualityService.js (line 231)
- **Params**: None
- **Auth**: YES
- **Notes**: Get dashboard stats for current week

### POST /quality/api/calcola-trimestrale
- **Service**: qualityService.js (line 241)
- **Params**: `{ quarter }`
- **Auth**: YES
- **Notes**: Calculate quarterly composite KPI with Super Malus

### GET /quality/api/quarterly-summary
- **Service**: qualityService.js (line 251)
- **Params**: `{ quarter }`
- **Auth**: YES
- **Notes**: Get quarterly summary with Super Malus details

### GET /quality/api/professionista/{professionistaId}/kpi-breakdown
- **Service**: qualityService.js (line 264)
- **Params**: `{ quarter }`
- **Auth**: YES
- **Notes**: Get KPI breakdown for professional in quarter

---

## TRAINING/REVIEWS

### GET /review/api/my-trainings
- **Service**: trainingService.js (line 63)
- **Params**: Optional params
- **Auth**: YES
- **Notes**: Get trainings received by current user

### GET /review/api/my-requests
- **Service**: trainingService.js (line 72)
- **Params**: None
- **Auth**: YES
- **Notes**: Get training requests sent by user

### GET /review/api/received-requests
- **Service**: trainingService.js (line 81)
- **Params**: None
- **Auth**: YES
- **Notes**: Get training requests received (where others ask training from me)

### GET /review/api/given-trainings
- **Service**: trainingService.js (line 90)
- **Params**: None
- **Auth**: YES
- **Notes**: Get trainings given by user (as reviewer/trainer)

### GET /review/api/request-recipients
- **Service**: trainingService.js (line 99)
- **Params**: None
- **Auth**: YES
- **Notes**: Get possible training request recipients

### POST /review/api/request
- **Service**: trainingService.js (line 109)
- **Params**: `{ subject, description, priority, recipient_id }`
- **Auth**: YES
- **Notes**: Create new training request

### POST /review/api/request/{requestId}/cancel
- **Service**: trainingService.js (line 119)
- **Params**: None
- **Auth**: YES
- **Notes**: Cancel pending training request

### POST /review/api/request/{requestId}/respond
- **Service**: trainingService.js (line 129)
- **Params**: `{ action: 'accept'|'reject', response_notes }`
- **Auth**: YES
- **Notes**: Respond to received training request

### POST /review/api/{reviewId}/acknowledge
- **Service**: trainingService.js (line 140)
- **Params**: `{ notes }`
- **Auth**: YES
- **Notes**: Confirm reading of training

### POST /review/api/{reviewId}/message
- **Service**: trainingService.js (line 151)
- **Params**: `{ content }`
- **Auth**: YES
- **Notes**: Send message in training chat

### POST /review/api/{reviewId}/mark-all-read
- **Service**: trainingService.js (line 161)
- **Params**: None
- **Auth**: YES
- **Notes**: Mark all messages in training as read

### GET /review/api/admin/professionals
- **Service**: trainingService.js (line 172)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Get list of all active professionals

### GET /review/api/admin/trainings/{userId}
- **Service**: trainingService.js (line 182)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Get trainings for specific user

### POST /review/api/admin/trainings/{userId}
- **Service**: trainingService.js (line 193)
- **Params**: `{ title, content, review_type, strengths, improvements, goals, period_start, period_end, is_private }`
- **Auth**: YES (admin)
- **Notes**: Create training for specific user

### GET /review/api/admin/dashboard-stats
- **Service**: trainingService.js (line 202)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Get global training dashboard stats

---

## NEWS

### GET /api/news/list
- **Service**: newsService.js (line 5)
- **Params**: Optional params
- **Auth**: YES
- **Notes**: Get news list

### GET /api/news/{id}
- **Service**: newsService.js (line 10)
- **Params**: None
- **Auth**: YES
- **Notes**: Get news detail

---

## PUSH NOTIFICATIONS

### GET /api/push/public-key
- **Service**: pushNotificationService.js (line 34, 78)
- **Params**: None
- **Auth**: YES
- **Notes**: Get push notification public key

### POST /api/push/subscriptions
- **Service**: pushNotificationService.js (line 27)
- **Params**: `{ subscription }`
- **Auth**: YES
- **Notes**: Upsert push notification subscription

### DELETE /api/push/subscriptions
- **Service**: pushNotificationService.js (line 119, 121)
- **Params**: `{ endpoint }` (optional)
- **Auth**: YES
- **Notes**: Delete push notification subscription

### GET /api/push/notifications
- **Service**: pushNotificationService.js (line 133)
- **Params**: `{ unread_only, limit }`
- **Auth**: YES
- **Notes**: Get push notifications

### POST /api/push/notifications/{notificationId}/read
- **Service**: pushNotificationService.js (line 151)
- **Params**: None
- **Auth**: YES
- **Notes**: Mark notification as read

---

## TEAM TICKETS

### GET /api/team-tickets/
- **Service**: teamTicketsService.js (line 5)
- **Params**: `{ cliente_id, ... }`
- **Auth**: YES
- **Notes**: List tickets by patient

### GET /api/team-tickets/{id}
- **Service**: teamTicketsService.js (line 12)
- **Params**: None
- **Auth**: YES
- **Notes**: Get single ticket

### GET /api/team-tickets/{ticketId}/messages
- **Service**: teamTicketsService.js (line 17)
- **Params**: None
- **Auth**: YES
- **Notes**: Get ticket messages

### GET /api/team-tickets/attachments/{attId}
- **Service**: teamTicketsService.js (line 22)
- **Params**: None
- **Auth**: YES
- **Notes**: Get attachment URL

---

## GHL INTEGRATION

### GET /ghl/api/config
- **Service**: ghlService.js (line 60)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Get GHL configuration

### POST /ghl/api/config
- **Service**: ghlService.js (line 69)
- **Params**: `{ api_key, location_id, is_active }`
- **Auth**: YES (admin)
- **Notes**: Update GHL configuration

### POST /ghl/api/config/test
- **Service**: ghlService.js (line 77)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Test GHL connection

### GET /ghl/api/calendars
- **Service**: ghlService.js (line 89)
- **Params**: None
- **Auth**: YES
- **Notes**: Get all GHL calendars

### GET /ghl/api/users
- **Service**: ghlService.js (line 97)
- **Params**: None
- **Auth**: YES
- **Notes**: Get all GHL users

### GET /ghl/api/mapping
- **Service**: ghlService.js (line 109)
- **Params**: None
- **Auth**: YES
- **Notes**: Get user-calendar mapping

### POST /ghl/api/mapping
- **Service**: ghlService.js (line 120)
- **Params**: `{ user_id, ghl_calendar_id, ghl_user_id }`
- **Auth**: YES
- **Notes**: Update single user mapping

### POST /ghl/api/mapping/bulk
- **Service**: ghlService.js (line 133)
- **Params**: `{ mappings: [...] }`
- **Auth**: YES
- **Notes**: Update multiple user mappings at once

### GET /ghl/api/calendar/events
- **Service**: ghlService.js (line 150)
- **Params**: `{ start, end, user_id }`
- **Auth**: YES
- **Notes**: Get calendar events for user

### POST /ghl/api/calendar/events
- **Service**: ghlService.js (line 159)
- **Params**: Event data
- **Auth**: YES
- **Notes**: Create calendar event in GHL

### GET /calendar/api/customers/search
- **Service**: ghlService.js (line 171)
- **Params**: `{ q, limit }`
- **Auth**: YES
- **Notes**: Search Suite customers for calendar assignment (Calendar blueprint)

### GET /ghl/api/calendar/team-members
- **Service**: ghlService.js (line 182)
- **Params**: None
- **Auth**: YES
- **Notes**: Get team members visible for calendar filtering

### GET /ghl/api/calendar/free-slots
- **Service**: ghlService.js (line 192)
- **Params**: `{ start, end }`
- **Auth**: YES
- **Notes**: Get free slots for current user's calendar

### GET /ghl/api/calendar/connection-status
- **Service**: ghlService.js (line 202)
- **Params**: None
- **Auth**: YES
- **Notes**: Get GHL connection status for current user

### GET /ghl/api/webhook-urls
- **Service**: ghlService.js (line 214)
- **Params**: None
- **Auth**: YES
- **Notes**: Get webhook URLs for this backend

### GET /ghl/api/opportunity-data
- **Service**: ghlService.js (line 226)
- **Params**: None
- **Auth**: YES
- **Notes**: Get all opportunity data from webhooks

### GET /ghl/api/opportunity-data/{id}
- **Service**: ghlService.js (line 234)
- **Params**: None
- **Auth**: YES
- **Notes**: Get single opportunity data by ID

### POST /ghl/api/opportunity-data/clear
- **Service**: ghlService.js (line 242)
- **Params**: None
- **Auth**: YES (admin)
- **Notes**: Clear all opportunity data

---

## ORIGINS MANAGEMENT

### GET /api/v1/customers/origins
- **Service**: originsService.js (line 12)
- **Params**: None
- **Auth**: YES
- **Notes**: Get list of all origins

### POST /api/v1/customers/origins
- **Service**: originsService.js (line 30)
- **Params**: `{ name, active }`
- **Auth**: YES
- **Notes**: Create new origin

### PUT /api/v1/customers/origins/{id}
- **Service**: originsService.js (line 48)
- **Params**: Origin data
- **Auth**: YES
- **Notes**: Update origin

### DELETE /api/v1/customers/origins/{id}
- **Service**: originsService.js (line 65)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete origin

---

## TRIAL USERS

### GET /api/team/trial-users
- **Service**: trialUserService.js (line 74)
- **Params**: None
- **Auth**: YES
- **Notes**: Get all trial users

### GET /api/team/trial-users/{userId}
- **Service**: trialUserService.js (line 84)
- **Params**: None
- **Auth**: YES
- **Notes**: Get single trial user with assigned clients

### POST /api/team/trial-users
- **Service**: trialUserService.js (line 94)
- **Params**: `{ email, first_name, last_name, password, ... }`
- **Auth**: YES
- **Notes**: Create new trial user

### PUT /api/team/trial-users/{userId}
- **Service**: trialUserService.js (line 105)
- **Params**: Fields to update
- **Auth**: YES
- **Notes**: Update trial user

### DELETE /api/team/trial-users/{userId}
- **Service**: trialUserService.js (line 115)
- **Params**: None
- **Auth**: YES
- **Notes**: Delete trial user

### POST /api/team/trial-users/{userId}/promote
- **Service**: trialUserService.js (line 127)
- **Params**: None
- **Auth**: YES
- **Notes**: Promote trial user to next stage

### POST /api/team/trial-users/{userId}/assign-clients
- **Service**: trialUserService.js (line 141)
- **Params**: `{ cliente_ids, notes }`
- **Auth**: YES
- **Notes**: Assign clients to trial user

### DELETE /api/team/trial-users/{userId}/remove-client/{clienteId}
- **Service**: trialUserService.js (line 155)
- **Params**: None
- **Auth**: YES
- **Notes**: Remove client from trial user

### GET /api/team/trial-users/available-clients
- **Service**: trialUserService.js (line 171)
- **Params**: `{ user_id, search, page, per_page }`
- **Auth**: YES
- **Notes**: Get available clients for assignment

### GET /api/team/trial-users/supervisors
- **Service**: trialUserService.js (line 183)
- **Params**: `{ specialty }`
- **Auth**: YES
- **Notes**: Get list of potential supervisors

---

## OLD SUITE INTEGRATION

### GET /old-suite/api/leads
- **Service**: oldSuiteService.js (line 50)
- **Params**: None
- **Auth**: YES
- **Notes**: Get all leads from old suite webhooks

### GET /old-suite/api/leads/{id}
- **Service**: oldSuiteService.js (line 58)
- **Params**: None
- **Auth**: YES
- **Notes**: Get single lead by ID

### GET /old-suite/api/leads/{leadId}/check/{checkNumber}
- **Service**: oldSuiteService.js (line 66)
- **Params**: None
- **Auth**: YES
- **Notes**: Get check response detail for a lead

### POST /old-suite/api/confirm-assignment
- **Service**: oldSuiteService.js (line 74)
- **Params**: Assignment payload
- **Auth**: YES
- **Notes**: Confirm assignment for lead (converts to Cliente)

---

## LOOM INTEGRATION

### POST /loom/api/recordings
- **Service**: loomService.js (line 55) - Direct axios call
- **Params**: `{ loom_link, title, note, cliente_id }`
- **Auth**: YES
- **Notes**: Save support recording with Loom link

### GET /loom/api/patients/search
- **Service**: loomService.js (line 75) - Direct axios call
- **Params**: `{ q, limit }`
- **Auth**: YES
- **Notes**: Search patients by name

### GET /loom/api/recordings
- **Service**: loomService.js (line 86) - Direct axios call
- **Params**: `{ cliente_id, with_cliente, submitter_user_id }`
- **Auth**: YES
- **Notes**: Get recordings with optional filters

### POST /ghl/api/meeting/loom
- **Service**: loomService.js (line 112)
- **Params**: `{ ghl_event_id, loom_link, title, start_time, end_time, cliente_id, ghl_calendar_id }`
- **Auth**: YES
- **Notes**: Save Loom link for GHL event and create/update Meeting locally

### GET /ghl/api/meeting/loom/{ghlEventId}
- **Service**: loomService.js (line 131)
- **Params**: None
- **Auth**: YES
- **Notes**: Get Loom link for GHL event

---

## SUMMARY STATISTICS

Total Endpoints Found: **220+**

### By Category:
- **Authentication**: 9 endpoints
- **Customers**: 78 endpoints
- **Checks**: 13 endpoints
- **Search**: 1 endpoint
- **Tasks**: 6 endpoints
- **Team Management**: 32 endpoints
- **Calendar/Meetings**: 20 endpoints
- **Post-it/Reminders**: 6 endpoints
- **Quality Scores**: 8 endpoints
- **Training/Reviews**: 14 endpoints
- **News**: 2 endpoints
- **Push Notifications**: 5 endpoints
- **Team Tickets**: 4 endpoints
- **GHL Integration**: 14 endpoints
- **Origins**: 4 endpoints
- **Trial Users**: 11 endpoints
- **Old Suite Integration**: 4 endpoints
- **Loom Integration**: 6 endpoints

### Authentication Status:
- **Public Endpoints**: 4 (login, forgot-password, reset-password, verify-reset-token, public checks)
- **Authenticated**: 216+

### Base URLs:
1. `/api/` - Main REST API (baseURL in api.js)
2. `/calendar/` - Calendar service API
3. `/postit/api/` - Post-it service
4. `/quality/api/` - Quality service
5. `/review/api/` - Training/Review service
6. `/ghl/api/` - GHL integration
7. `/old-suite/api/` - Old suite integration
8. `/loom/api/` - Loom integration (mixed with /ghl/api)
9. `/customers/` - HTML blueprint endpoints (legacy)


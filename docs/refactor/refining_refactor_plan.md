
# Refactor Permessi/Visuali Team Leader + Professionista (focus: RBAC reale + Dashboard TL team-specific)

## Sintesi

Obiettivo: completare il refactor permessi/visuali per professionista normale e chiudere il lavoro TL con una dashboard realmente team-specific (non solo hide UI), con enforcement backend dove oggi c’è ancora
solo hardening frontend.

Success criteria:

- Professionista vede solo dati/azioni coerenti con il proprio scope operativo.
- Team Leader vede solo dati del proprio team/specialità sia in UI sia lato API.
- Welcome per TL diventa dashboard operativa team-specific completa.
- Le pagine fuori scope non sono solo nascoste nel menu: restituiscono redirect/403 coerenti.

## Scelte confermate (locking)

- Professionista su dettaglio cliente: solo dati/tab/azioni del proprio ruolo + info base cliente.
- Professionista sezione Team: solo proprio profilo (no lista team, no elenco membri).
- Dashboard TL: baseline “operativa team completa” (KPI team + task + check + clienti + formazione del solo team/specialità, senza benchmark globali).

## Perimetro funzionale finale per ruolo

### Team Leader (non admin/cco)

- Può vedere:
- Welcome team-specific (solo proprio team/specialità)
- Task del proprio team (con filtro per membro team)
- Clienti del proprio perimetro (team/specialità)
- Check del proprio perimetro (team/specialità)
- Formazione team (già quasi pronta, da validare end-to-end)
- Team / Professionisti del proprio team
- Quality in lettura limitata al proprio team/specialità
- Capienze solo membri del proprio team (già base backend presente)
- Non deve vedere:
- KPI globali piattaforma
- confronti cross-team/cross-dipartimento
- professionisti/team fuori dal proprio scope
- azioni admin/cco (global management, settings, trial management completo se fuori scope)
- Necessario completare:
- dashboard Welcome team-specific vera (oggi è hardening + placeholder)

### Professionista (normale)

- Può vedere:
- Welcome personale (dashboard personale)
- Task assegnati a sé
- Formazione propria (training ricevuti/richieste inviate; nessuna gestione team)
- Clienti solo assegnati a sé
- Dettaglio cliente solo se assegnato, con solo sezioni/azioni del proprio ruolo
- Profilo proprio (/profilo o /team-dettaglio/:self)
- Check propri dati solo dentro profilo (Profilo > Check) o dashboard personale
- Non deve vedere:
- Quality pagina globale
- Assegnazioni AI
- Capienze
- Team list, Teams entity, dettagli altri professionisti
- In Prova
- CheckAzienda globale (cross-professionista/cross-team)
- filtri/pannelli admin/TL in Clienti, Task, Check, Formazione
- dati/azioni altri ruoli nel dettaglio cliente (es. tab coach/psicologia/nutrizione non propri)
- azioni di assegnazione/interruzione professionisti, call bonus fuori proprio perimetro, edit strutturali paziente fuori proprio ruolo

## Architettura del refactor (decision-complete)

## 1. Centralizzare policy frontend (evitare if sparsi)

File target principali:

- corposostenibile-clinica/src/components/RoleProtectedRoute.jsx
- corposostenibile-clinica/src/jsx/layouts/nav/SideBar.jsx
- corposostenibile-clinica/src/App.jsx
- Nuovo file: corposostenibile-clinica/src/services/rbacScope.js (o src/utils/rbacScope.js)

Implementare una policy centralizzata con helper puri:

- getEffectiveRole(user) con fallback coerente (admin > role field)
- isAdminOrCco(user)
- isTeamLeaderRestricted(user)
- isProfessionistaStandard(user)
- getClinicalScope(user) → { roleType, specialtyGroup, visibleUserMode }
- canAccessRoute(user, routeKey)
- canViewClientSection(user, sectionKey, clientContext)
- canEditClientSection(user, sectionKey, clientContext)
- canViewGlobalCheckPage(user)
- canViewTeamModuleList(user)
- canViewOtherProfessionalProfile(user, targetUserId)

Decisione tecnica:

- Le pagine continueranno a leggere user dal context, ma useranno helper comuni per render/redirect.
- Ridurre condizioni inline tipo user?.role === 'team_leader' sparse dove possibile.

## 2. Enforce backend RBAC (non solo hide UI)

File target backend:

- backend/corposostenibile/blueprints/team/api.py
- backend/corposostenibile/blueprints/tasks/routes.py
- backend/corposostenibile/blueprints/quality/routes.py (validazione regressione)
- backend/corposostenibile/blueprints/customers/routes.py (endpoint lista/dettaglio/azioni usati dal frontend React)
- Eventuali endpoint check/training usati dal frontend (da audit mirato durante implementazione)

Regola generale:

- Ogni endpoint usato da visuali TL/professionista deve applicare ACL server-side basata su current_user, non fidarsi dei filtri passati dal client.

Hardening minimo obbligatorio:

- Verificare e completare ACL in /api/team/members/<id>/clients e /api/team/members/<id>/checks:
- admin/cco: tutto
- team_leader: solo self o membri propri team
- professionista: solo self
- Restituire 403 con payload JSON coerente (success:false, message)
- Audit endpoint customers usati da ClientiList / ClientiDetail:
- Professionista: solo clienti assegnati
- Team Leader: solo clienti del proprio team/specialità
- Bloccare azioni mutate fuori scope (assegna/interrompi professionista, call bonus AI, ecc.)
- Audit endpoint check globale (CheckAzienda) per bloccare professionista standard se pagina resta raggiungibile da URL
- Audit endpoint training per garantire che il professionista non possa leggere/gestire training di altri passando ID arbitrari

## 3. Dashboard TL team-specific (nuova Welcome per TL)

File target:

- corposostenibile-clinica/src/pages/Welcome.jsx
- corposostenibile-clinica/src/services/dashboardService.js
- Backend consigliato: nuovo endpoint aggregato TL in backend/corposostenibile/blueprints/team/api.py

Decisione API:

- Aggiungere endpoint aggregato nuovo, invece di comporre 6 chiamate frontend con filtri e ACL duplicati.
- Endpoint proposto: GET /api/team/team-leader-dashboard
- ACL: solo team_leader, admin, cco
- Per team_leader: dati limitati ai team guidati + specialty coerente
- Per admin/cco: opzionale supporto team_id query param per debug/validazione (non necessario alla UI iniziale)

Payload proposto (stabile e semplice):

- scope: team IDs, specialty, team names
- kpi: membri attivi team, clienti attivi team, check ultimi 30gg, task aperti team, training pendenti/richieste ricevute
- task: summary per categoria + lista ultimi task team
- check: medie team, trend breve, ultimi check critici del team
- clienti: stati principali + scadenze/attenzioni
- formazione: richieste ricevute/da gestire + training aperti team
- professionisti: snapshot membri team (carico/check/task/training)
- quick_links: facoltativo lato backend = no (meglio statici frontend)

Frontend Welcome:

- Sostituire il ramo isRestrictedTeamLeaderDashboard con dashboard reale.
- Rimuovere placeholder “Vista Team Leader limitata”.
- Tabs TL ammessi nella dashboard:
- panoramica
- task
- check
- clienti
- formazione
- professionisti
- Escludere tab globali non coerenti (quality dentro Welcome se ridondante; chat se non porta valore operativo TL in questa dashboard)
- Mantiene pulsante refresh con reload dell’endpoint TL unico.

## 4. Refactor Professionista sezione per sezione (UI + route guard)

File target principali frontend:

- corposostenibile-clinica/src/App.jsx
- corposostenibile-clinica/src/jsx/layouts/nav/SideBar.jsx
- corposostenibile-clinica/src/pages/Welcome.jsx
- corposostenibile-clinica/src/pages/clienti/ClientiList.jsx
- corposostenibile-clinica/src/pages/clienti/ClientiDetail.jsx
- corposostenibile-clinica/src/pages/check/CheckAzienda.jsx
- corposostenibile-clinica/src/pages/task/Task.jsx
- corposostenibile-clinica/src/pages/formazione/Formazione.jsx
- corposostenibile-clinica/src/pages/team/TeamList.jsx
- corposostenibile-clinica/src/pages/team/Profilo.jsx

Implementazione per pagina (decisioni precise):

- SideBar.jsx
- Nascondere menu per professionista: Assegnazioni, Quality, Capienze, In Prova, Team list/gestione (se presente come voce separata)
- Lasciare Profilo, Task, Formazione, Clienti
- App.jsx
- Aggiungere RoleProtectedRoute su pagine globali fuori scope professionista:
- /admin/assegnazioni-dashboard già ok
- /quality già ok
- aggiungere guard per /team-lista, /team-capienza, /teams*, /in-prova*, /check-azienda
- Per /team-dettaglio/:id: consentire solo admin/cco/TL; professionista solo se :id === currentUser.id
- Welcome.jsx
- Introdurre ramo dashboard personale (professionista) distinto da admin e TL:
- KPI personali minimi (task aperti, clienti assegnati, check recenti, training aperti)
- quick links personali
- nessun dato globale/cross-team
- ClientiList.jsx
- Professionista: forzare filtro backend “solo assegnati a me” (via endpoint/ACL backend)
- Nascondere filtri per professionisti multipli/altri ruoli
- Nascondere KPI cross-dipartimento/cross-team
- Nascondere azioni non consentite (creazione cliente se non prevista; se oggi business la consente, mantenerla esplicita)
- ClientiDetail.jsx
- Aggiungere gate centrali per:
- accesso pagina solo se backend autorizza
- tabs principali visibili solo se coerenti al ruolo del professionista
- azioni di assegnazione/interruzione professionisti OFF
- call bonus: consentire solo azioni del professionista assegnato (se già supportato backend), altrimenti read-only o hidden
- Ogni sezione sensibile deve usare canViewClientSection/canEditClientSection
- CheckAzienda.jsx
- Professionista: route negata (redirect a /profilo?tab=check o /welcome)
- Team Leader: mantenere vista filtrata team/specialità
- Task.jsx
- Professionista: solo task propri (già probabile lato backend), rimuovere filtri admin/TL
- Formazione.jsx
- Professionista: tab/azioni team management nascosti; solo propri training/richieste
- TeamList.jsx
- Professionista: route negata
- Profilo.jsx
- Se professionista prova ad aprire profilo altrui via URL → redirect al proprio profilo
- Tabs visibili per professionista:
- info
- clienti
- check
- formazione
- task
- Non visibili:
- teams (se mostra altri membri)
- quality (globale/analytics professionista non prevista qui per ruolo standard)
- capienza

## 5. Matrice permessi dati nel dettaglio cliente (professionista)

Decisione esplicita da implementare:

- Base sempre visibile se autorizzato al cliente:
- anagrafica essenziale, stato percorso, dati contatto essenziali (se già necessari operativamente)
- Sezioni di ruolo:
- nutrizionista vede solo area nutrizione + check pertinenti + note/azioni del proprio ruolo
- coach vede solo area coaching + check pertinenti + note/azioni del proprio ruolo
- psicologo vede solo area psicologia + check pertinenti + note/azioni del proprio ruolo
- medico vede solo area medico (quando presente)
- Sezioni cross-ruolo non visibili (non solo read-only), come da decisione utente
- Team tab clinico completo non visibile a professionista normale (o ridotto a badge “miei ruoli assegnati” senza dettagli altri ruoli)

## 6. Ordine di implementazione (per ridurre regressioni)

1. Centralizzare helper RBAC frontend + route guards (App, SideBar, RoleProtectedRoute).
2. Hardening backend ACL endpoint team member clients/checks + audit endpoint clienti/check/training.
3. Refactor Professionista pagine core (ClientiList, ClientiDetail, CheckAzienda, Profilo, Task, Formazione).
4. Implementare endpoint aggregato TL dashboard.
5. Sostituire placeholder TL in Welcome con dashboard team-specific.
6. QA cross-role e correzioni UI residuali (topbar ruolo/avatar fuori scope di questo piano ma da ricontrollare in test finale).

## Modifiche/aggiunte a API, interfacce, tipi pubblici

### Backend API (nuovo)

- GET /api/team/team-leader-dashboard
- Response JSON nuovo (aggregato team-specific)
- Errori: 403 per ruolo non ammesso, 200 con payload scope-limitato per TL

### Backend API (breaking behavior intenzionale)

- Endpoint esistenti possono iniziare a rispondere 403 in casi prima “silenziosamente consentiti”:
- /api/team/members/<id>/clients
- /api/team/members/<id>/checks
- endpoint customers/checks/training fuori scope
- Non è breaking per business desiderato; è hardening di sicurezza.

### Frontend (nuovi helper)

- Nuovo modulo policy RBAC condiviso (rbacScope.js)
- Nessun cambiamento visibile alle API di componenti pubblici, ma riduzione di logica inline e uso helper centrali.

## Test cases e scenari di accettazione

### Test ruolo Professionista

- Accede a /welcome e vede solo dashboard personale (nessun KPI globale/cross-team).
- Sidebar non mostra Quality, Assegnazioni, Capienze, Team list, In Prova.
- Accesso diretto URL a /quality, /admin/assegnazioni-dashboard, /team-lista, /check-azienda, /teams → redirect o blocco coerente.
- mostra info base + solo sezione del proprio ruolo
- non mostra azioni assegnazione/interruzione professionisti
- ClientiDetail di cliente non assegnato → 403/redirect.
- /team-dettaglio/:id_altrui → redirect al proprio profilo.
- Formazione non consente gestione team / assegnazione training a membri team.

### Test ruolo Team Leader

- Welcome mostra dashboard team-specific (no placeholder “vista limitata”).
- Tutti i numeri della dashboard TL sono coerenti solo con team/specialità del TL.
- Nessun KPI globale/cross-team visibile.
- Task, Clienti, Check, Formazione, Quality filtrano correttamente al team.
- Chiamate API con user_id di professionista fuori team su endpoint member clients/checks → 403.
- Accesso a profili professionisti del proprio team → consentito.
- Accesso a profili fuori team → negato (se policy backend già supporta; altrimenti aggiungere hardening).


### Test sicurezza (manuale/API)

- Provare parametri manipolati in query (assignee_id, team_id, professionista_id) da frontend professionista/TL.
- Verificare che backend ignori/limiti richieste fuori scope e non ritorni dati extra.

- Dashboard TL team-specific viene implementata con endpoint aggregato nuovo (non con composizione di endpoint globali filtrati dal client).
- role utente lato backend è già coerentizzato dalla migrazione/fix (head → team_leader); il frontend usa comunque helper robusti per evitare mismatch temporanei di sessione.

## Note operative (vincoli di implementazione)

- Fare prima enforcement backend e route guard, poi rifinitura UI, per evitare “sicurezza percepita” non reale.
- Mantenere messaggi d’errore/redirect coerenti e non rumorosi per l’utente finale.
- Introdurre pochi helper riusabili invece di moltiplicare condizioni per pagina.


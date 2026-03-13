import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useParams } from 'react-router-dom';

// Context
import ThemeContextProvider from './context/ThemeContext';

// Auth pages
import Login from './pages/Login';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';

// Dashboard layout & pages
import DashboardLayout from './layouts/DashboardLayout';
import Welcome from './pages/Welcome';

// Team pages
import { TeamList, TeamAdd, TeamCapacity, Profilo, TeamsList, TeamsAdd, TeamsDetail, AssegnazioniAI, SuiteMindAssignment, CriteriProfessionisti } from './pages/team';

// Trial (In Prova) pages
import { TrialUsersList, TrialUserDetail, TrialUserForm, AssignClients } from './pages/trial';

// Clienti pages
import {
  ClientiList,
  ClientiAdd,
  ClientiDetail,
  ClientiListaNutrizione,
  ClientiListaCoach,
  ClientiListaPsicologia,
} from './pages/clienti';

// Chat pages
import { Chat } from './pages/chat';

// Task pages
import { Task } from './pages/task';

// Formazione pages
import { Formazione } from './pages/formazione';

// Quality pages
import { Quality } from './pages/quality';

// Check pages
import { CheckAzienda, CheckDaLeggere } from './pages/check';

// Calendario pages
import { Calendario } from './pages/calendario';

// Support pages
import { Support, SupportDetail } from './pages/support';

// Search pages
import GlobalSearchPage from './pages/GlobalSearchPage';

// Documentation
import Documentation from './pages/documentation/Documentation';
import LoomLibrary from './pages/loom/LoomLibrary';

// Novità
import Novita from './pages/Novita';

// Admin pages
import { GHLSettings, OriginSettings, ImpersonateUser } from './pages/admin';

// Components
import RoleProtectedRoute from './components/RoleProtectedRoute';
import { useAuth } from './context/AuthContext';
import {
  canAccessAiAssignments,
  canAccessCapacity,
  canAccessGlobalCheckPage,
  canAccessLoomLibrary,
  canAccessQualityPage,
  canAccessSecondaryModules,
  canAccessSpecializzazione,
  canAccessTaskPage,
  canAccessTeamLists,
  canAccessTrainingPage,
  canAccessTrialPages,
  canViewOtherProfessionalProfile,
  isAdminOrCco,
} from './utils/rbacScope';

// Public pages (no auth required)
import {
  PublicLayout,
  WeeklyCheckForm,
  DCACheckForm,
  MinorCheckForm,
  CheckSuccess,
} from './pages/public';

function PublicClientCheckRedirect() {
  const { token } = useParams();

  useEffect(() => {
    if (!token) return;
    const target = `${window.location.protocol}//${window.location.hostname}:5001/client-checks/public/${token}${window.location.search}${window.location.hash}`;
    window.location.replace(target);
  }, [token]);

  return null;
}

function TeamDetailRouteGuard({ children }) {
  const { user, loading } = useAuth();
  const { id } = useParams();

  if (loading) return null;
  if (!user) return <Navigate to="/auth/login" replace />;
  if (!id) return children;
  if (isAdminOrCco(user) || canViewOtherProfessionalProfile(user)) return children;
  return Number(id) === Number(user.id) ? children : <Navigate to="/profilo" replace />;
}

function App() {
  return (
    <ThemeContextProvider>
      <Router basename={import.meta.env.BASE_URL}>
        <Routes>
          {/* Auth Routes (no layout) */}
          <Route path="/auth/login" element={<Login />} />
          <Route path="/auth/forgot-password" element={<ForgotPassword />} />
          <Route path="/auth/reset-password/:token" element={<ResetPassword />} />

          {/* Public Check Routes (no auth required) */}
          <Route element={<PublicLayout />}>
            <Route path="/check/weekly/:token" element={<WeeklyCheckForm />} />
            <Route path="/check/dca/:token" element={<DCACheckForm />} />
            <Route path="/check/minor/:token" element={<MinorCheckForm />} />
            <Route path="/check/:checkType/:token/success" element={<CheckSuccess />} />
          </Route>
          <Route path="/client-checks/public/:token" element={<PublicClientCheckRedirect />} />

          {/* Dashboard Routes (with layout) */}
          <Route element={<DashboardLayout />}>
            <Route path="/welcome" element={<Welcome />} />

            {/* Team Member Routes */}
            <Route path="/team-lista" element={
              <RoleProtectedRoute allowIf={canAccessTeamLists}>
                <TeamList />
              </RoleProtectedRoute>
            } />
            <Route path="/team-capienza" element={
              <RoleProtectedRoute allowIf={canAccessCapacity}>
                <TeamCapacity />
              </RoleProtectedRoute>
            } />
            <Route path="/team-nuovo" element={<RoleProtectedRoute allowIf={canAccessTeamLists}><TeamAdd /></RoleProtectedRoute>} />
            <Route path="/team-dettaglio/:id" element={
              <TeamDetailRouteGuard>
                <Profilo />
              </TeamDetailRouteGuard>
            } /> {/* Redirect to Profilo for detail */}
            <Route path="/team-modifica/:id" element={<RoleProtectedRoute allowIf={canAccessTeamLists}><TeamAdd /></RoleProtectedRoute>} />

            {/* Team Entity Routes */}
            <Route path="/teams" element={<RoleProtectedRoute allowIf={canAccessTeamLists}><TeamsList /></RoleProtectedRoute>} />
            <Route path="/teams-nuovo" element={<RoleProtectedRoute allowIf={canAccessTeamLists}><TeamsAdd /></RoleProtectedRoute>} />
            <Route path="/teams-dettaglio/:id" element={<RoleProtectedRoute allowIf={canAccessTeamLists}><TeamsDetail /></RoleProtectedRoute>} />
            <Route path="/teams-modifica/:id" element={<RoleProtectedRoute allowIf={canAccessTeamLists}><TeamsAdd /></RoleProtectedRoute>} />

            {/* AI Assignments */}
            <Route path="/assegnazioni-ai" element={
              <RoleProtectedRoute allowIf={canAccessAiAssignments}>
                <AssegnazioniAI />
              </RoleProtectedRoute>
            } />
            <Route path="/suitemind/:opportunityId" element={
              <RoleProtectedRoute allowIf={canAccessAiAssignments}>
                <SuiteMindAssignment />
              </RoleProtectedRoute>
            } />
            <Route path="/criteri-professionisti" element={
              <RoleProtectedRoute allowIf={canAccessSpecializzazione}>
                <CriteriProfessionisti />
              </RoleProtectedRoute>
            } />

            {/* In Prova (Trial Users) */}
            <Route path="/in-prova" element={<RoleProtectedRoute allowIf={canAccessTrialPages}><TrialUsersList /></RoleProtectedRoute>} />
            <Route path="/in-prova/nuovo" element={<RoleProtectedRoute allowIf={canAccessTrialPages}><TrialUserForm /></RoleProtectedRoute>} />
            <Route path="/in-prova/:userId" element={<RoleProtectedRoute allowIf={canAccessTrialPages}><TrialUserDetail /></RoleProtectedRoute>} />
            <Route path="/in-prova/:userId/modifica" element={<RoleProtectedRoute allowIf={canAccessTrialPages}><TrialUserForm /></RoleProtectedRoute>} />
            <Route path="/in-prova/:userId/assegna-clienti" element={<RoleProtectedRoute allowIf={canAccessTrialPages}><AssignClients /></RoleProtectedRoute>} />

            {/* Clienti Routes */}
            <Route path="/clienti-lista" element={<ClientiList />} />
            <Route path="/clienti-nuovo" element={<RoleProtectedRoute allowIf={canAccessSecondaryModules}><ClientiAdd /></RoleProtectedRoute>} />
            <Route path="/clienti-dettaglio/:id" element={<ClientiDetail />} />
            <Route path="/clienti-modifica/:id" element={<RoleProtectedRoute allowIf={canAccessSecondaryModules}><ClientiAdd /></RoleProtectedRoute>} />
            <Route path="/clienti-nutrizione" element={<ClientiListaNutrizione />} />
            <Route path="/clienti-coach" element={<ClientiListaCoach />} />
            <Route path="/clienti-psicologia" element={<ClientiListaPsicologia />} />

            {/* Chat */}
            <Route path="/chat" element={<RoleProtectedRoute allowIf={canAccessSecondaryModules}><Chat /></RoleProtectedRoute>} />

            {/* Task */}
            <Route path="/task" element={<RoleProtectedRoute allowIf={canAccessTaskPage}><Task /></RoleProtectedRoute>} />

            {/* Formazione */}
            <Route path="/formazione" element={<RoleProtectedRoute allowIf={canAccessTrainingPage}><Formazione /></RoleProtectedRoute>} />

            {/* Quality */}
            <Route path="/quality" element={
              <RoleProtectedRoute allowIf={canAccessQualityPage}>
                <Quality />
              </RoleProtectedRoute>
            } />

            {/* Check */}
            <Route path="/check-azienda" element={
              <RoleProtectedRoute allowIf={canAccessGlobalCheckPage}>
                <CheckAzienda />
              </RoleProtectedRoute>
            } />
            <Route path="/check-da-leggere" element={<RoleProtectedRoute allowIf={canAccessGlobalCheckPage}><CheckDaLeggere /></RoleProtectedRoute>} />

            {/* Calendario */}
            <Route path="/calendario" element={<RoleProtectedRoute allowIf={canAccessSecondaryModules}><Calendario /></RoleProtectedRoute>} />
            <Route path="/loom-library" element={<RoleProtectedRoute allowIf={canAccessLoomLibrary}><LoomLibrary /></RoleProtectedRoute>} />
            <Route path="/comunicazioni" element={<div className="card p-4">Comunicazioni (coming soon)</div>} />
            <Route path="/profilo" element={<RoleProtectedRoute allowIf={canAccessSecondaryModules}><Profilo /></RoleProtectedRoute>} />

            {/* Support */}
            <Route path="/supporto" element={<Support />} />
            <Route path="/supporto/:section" element={<SupportDetail />} />

            {/* Global Search */}
            <Route path="/ricerca-globale" element={<GlobalSearchPage />} />

            {/* Novità */}
            <Route path="/novita" element={<Novita />} />

            {/* Documentazione */}
            <Route path="/documentazione" element={<Documentation />} />

            {/* Admin Pages */}
            <Route path="/admin/ghl-settings" element={<GHLSettings />} />
            <Route path="/admin/origins" element={<OriginSettings />} />
            <Route path="/admin/impersonate" element={
              <RoleProtectedRoute allowedRoles={['admin']}>
                <ImpersonateUser />
              </RoleProtectedRoute>
            } />
          </Route>

          {/* Default redirect to welcome */}
          <Route path="/" element={<Navigate to="/welcome" replace />} />
          <Route path="/dashboard" element={<Navigate to="/welcome" replace />} />

          {/* Catch all - redirect to welcome */}
          <Route path="*" element={<Navigate to="/welcome" replace />} />
        </Routes>
      </Router>
    </ThemeContextProvider>
  );
}

export default App;

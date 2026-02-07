import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

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
import { TeamList, TeamAdd, Profilo, TeamsList, TeamsAdd, TeamsDetail, AssegnazioniAI } from './pages/team';

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
import { Support } from './pages/support';

// Search pages
import GlobalSearchPage from './pages/GlobalSearchPage';

// Documentation
import Documentation from './pages/documentation/Documentation';

// Admin pages
import { GHLSettings, OriginSettings } from './pages/admin';

// Components
import AdminRoute from './components/AdminRoute';

// Public pages (no auth required)
import {
  PublicLayout,
  WeeklyCheckForm,
  DCACheckForm,
  MinorCheckForm,
  CheckSuccess,
} from './pages/public';

function App() {
  return (
    <ThemeContextProvider>
      <Router>
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

          {/* Dashboard Routes (with layout) */}
          <Route element={<DashboardLayout />}>
            <Route path="/welcome" element={<Welcome />} />

            {/* Team Member Routes */}
            <Route path="/team-lista" element={<TeamList />} />
            <Route path="/team-nuovo" element={<TeamAdd />} />
            <Route path="/team-dettaglio/:id" element={<Profilo />} /> {/* Redirect to Profilo for detail */}
            <Route path="/team-modifica/:id" element={<TeamAdd />} />

            {/* Team Entity Routes */}
            <Route path="/teams" element={<TeamsList />} />
            <Route path="/teams-nuovo" element={<TeamsAdd />} />
            <Route path="/teams-dettaglio/:id" element={<TeamsDetail />} />
            <Route path="/teams-modifica/:id" element={<TeamsAdd />} />

            {/* AI Assignments */}
            <Route path="/assegnazioni-ai" element={<AssegnazioniAI />} />

            {/* In Prova (Trial Users) */}
            <Route path="/in-prova" element={<TrialUsersList />} />
            <Route path="/in-prova/nuovo" element={<TrialUserForm />} />
            <Route path="/in-prova/:userId" element={<TrialUserDetail />} />
            <Route path="/in-prova/:userId/modifica" element={<TrialUserForm />} />
            <Route path="/in-prova/:userId/assegna-clienti" element={<AssignClients />} />

            {/* Clienti Routes */}
            <Route path="/clienti-lista" element={<ClientiList />} />
            <Route path="/clienti-nuovo" element={<ClientiAdd />} />
            <Route path="/clienti-dettaglio/:id" element={<ClientiDetail />} />
            <Route path="/clienti-modifica/:id" element={<ClientiAdd />} />
            <Route path="/clienti-nutrizione" element={<ClientiListaNutrizione />} />
            <Route path="/clienti-coach" element={<ClientiListaCoach />} />
            <Route path="/clienti-psicologia" element={<ClientiListaPsicologia />} />

            {/* Chat */}
            <Route path="/chat" element={<Chat />} />

            {/* Task */}
            <Route path="/task" element={<Task />} />

            {/* Formazione */}
            <Route path="/formazione" element={<Formazione />} />

            {/* Quality */}
            <Route path="/quality" element={
              <AdminRoute>
                <Quality />
              </AdminRoute>
            } />

            {/* Check */}
            <Route path="/check-azienda" element={<CheckAzienda />} />
            <Route path="/check-da-leggere" element={<CheckDaLeggere />} />

            {/* Calendario */}
            <Route path="/calendario" element={<Calendario />} />
            <Route path="/comunicazioni" element={<div className="card p-4">Comunicazioni (coming soon)</div>} />
            <Route path="/profilo" element={<Profilo />} />

            {/* Support */}
            <Route path="/supporto" element={<Support />} />

            {/* Global Search */}
            <Route path="/ricerca-globale" element={<GlobalSearchPage />} />

            {/* Documentazione */}
            <Route path="/documentazione" element={<Documentation />} />

            {/* Admin Pages */}
            <Route path="/admin/ghl-settings" element={<GHLSettings />} />
            <Route path="/admin/origins" element={<OriginSettings />} />
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

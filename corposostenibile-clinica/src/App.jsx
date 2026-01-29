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

// Admin pages
import { GHLSettings, OriginSettings } from './pages/admin';

// Components
import AdminRoute from './components/AdminRoute';

// ... existing imports ...

            {/* Quality */}
            <Route path="/quality" element={
              <AdminRoute>
                <Quality />
              </AdminRoute>
            } />

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

import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Context
import ThemeContextProvider from './context/ThemeContext';

// Auth pages
import Login from './pages/Login';

// Dashboard layout & pages
import DashboardLayout from './layouts/DashboardLayout';

// Pages
import AppointmentSetting from './pages/AppointmentSetting';
import SOPDocuments from './pages/sop/SOPDocuments';
import SOPChat from './pages/sop/SOPChat';
import TeamTicketsDashboard from './pages/team-tickets/TeamTicketsDashboard';
import TeamTicketDetail from './pages/team-tickets/TeamTicketDetail';
import TeamTicketsAnalytics from './pages/team-tickets/TeamTicketsAnalytics';

function App() {
  return (
    <ThemeContextProvider>
      <Router>
        <Routes>
          {/* Auth Routes (no layout) */}
          <Route path="/auth/login" element={<Login />} />

          {/* Dashboard Routes (with layout) */}
          <Route element={<DashboardLayout />}>
            {/* Appointment Setting */}
            <Route path="/appointment-setting" element={<AppointmentSetting />} />

            {/* SOP Chatbot */}
            <Route path="/sop-documents" element={<SOPDocuments />} />
            <Route path="/sop-chat" element={<SOPChat />} />

            {/* Team Tickets */}
            <Route path="/team-tickets" element={<TeamTicketsDashboard />} />
            <Route path="/team-tickets/analytics" element={<TeamTicketsAnalytics />} />
            <Route path="/team-tickets/:id" element={<TeamTicketDetail />} />
          </Route>

          {/* Default redirect to appointment-setting */}
          <Route path="/" element={<Navigate to="/appointment-setting" replace />} />
          <Route path="/welcome" element={<Navigate to="/appointment-setting" replace />} />
          <Route path="/dashboard" element={<Navigate to="/appointment-setting" replace />} />

          {/* Catch all - redirect to appointment-setting */}
          <Route path="*" element={<Navigate to="/appointment-setting" replace />} />
        </Routes>
      </Router>
    </ThemeContextProvider>
  );
}

export default App;

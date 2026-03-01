/**
 * PublicLayout - Layout per pagine pubbliche senza autenticazione
 * Usato per i form dei check compilabili dai clienti
 */

import { Outlet } from 'react-router-dom';
import './checks/PublicChecks.css';

function PublicLayout() {
  return (
    <div className="public-layout">
      {/* Header */}
      <header className="public-header">
        <div className="public-header-inner">
          <img
            src="/static/images/logo-foglia-green.png"
            alt="CorpoSostenibile"
            className="public-header-logo"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
          <span className="public-header-brand">CorpoSostenibile</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="public-main">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="public-footer">
        <p style={{ margin: 0 }}>
          &copy; {new Date().getFullYear()} CorpoSostenibile
        </p>
      </footer>
    </div>
  );
}

export default PublicLayout;

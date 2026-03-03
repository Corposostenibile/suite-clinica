/**
 * PublicLayout - Layout per pagine pubbliche senza autenticazione
 * Usato per i form dei check compilabili dai clienti
 */

import { Outlet } from 'react-router-dom';
import logoFoglia from '../../images/logo-foglia-white.png';
import './checks/PublicChecks.css';

function PublicLayout() {
  return (
    <div className="public-layout">
      {/* Header */}
      <header className="public-header">
        <div className="public-header-inner">
          <img
            src={logoFoglia}
            alt="CorpoSostenibile"
            className="public-header-logo"
          />
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

/**
 * PublicLayout - Layout per pagine pubbliche senza autenticazione
 * Usato per i form dei check compilabili dai clienti
 */

import { Outlet } from 'react-router-dom';

const styles = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
  },
  header: {
    background: 'white',
    borderBottom: '1px solid #e2e8f0',
    padding: '16px 24px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
  },
  logo: {
    height: '40px',
  },
  main: {
    padding: '24px',
    maxWidth: '800px',
    margin: '0 auto',
  },
  footer: {
    textAlign: 'center',
    padding: '24px',
    color: '#64748b',
    fontSize: '14px',
  },
};

function PublicLayout() {
  return (
    <div style={styles.container}>
      {/* Header */}
      <header style={styles.header}>
        <div className="d-flex align-items-center justify-content-center">
          <img
            src="/static/images/logo-foglia-green.png"
            alt="CorpoSostenibile"
            style={styles.logo}
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
          <span className="ms-2 fw-semibold text-dark" style={{ fontSize: '1.25rem' }}>
            CorpoSostenibile
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main style={styles.main}>
        <Outlet />
      </main>

      {/* Footer */}
      <footer style={styles.footer}>
        <p className="mb-0">
          &copy; {new Date().getFullYear()} CorpoSostenibile - Tutti i diritti riservati
        </p>
      </footer>
    </div>
  );
}

export default PublicLayout;

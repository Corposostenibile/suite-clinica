import { useState, useContext, useEffect } from 'react';
import { Outlet, useLocation, Link } from 'react-router-dom';
import { Modal } from 'react-bootstrap';
import NavHader from '../jsx/layouts/nav/NavHader';
import SideBar from '../jsx/layouts/nav/SideBar';
import Header from '../jsx/layouts/nav/Header';
import ChatBox from '../jsx/layouts/ChatBox';
import { ThemeContext } from '../context/ThemeContext';
import { AuthProvider, useAuth } from '../context/AuthContext';
import authService from '../services/authService';

/// Style (mobile-header.css è importato in App.jsx)
import '../styles/design-tokens.css';
import '../styles/template.css';
import '../styles/custom-overrides.css';

const COMPACT_TOP_BAR_BREAKPOINT = 1199;

function DashboardContent() {
  const { menuToggle, setMenuToggle } = useContext(ThemeContext);
  const { user, loading } = useAuth();
  const [toggle, setToggle] = useState("");
  const location = useLocation();
  const [compactTopBar, setCompactTopBar] = useState(window.innerWidth <= COMPACT_TOP_BAR_BREAKPOINT);
  const [showTicketModal, setShowTicketModal] = useState(false);

  const onClick = (name) => setToggle(toggle === name ? "" : name);

  useEffect(() => {
    const onResize = () => setCompactTopBar(window.innerWidth <= COMPACT_TOP_BAR_BREAKPOINT);
    window.addEventListener('resize', onResize);
    onResize();
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Auto-close sidebar on route change (mobile navigation)
  useEffect(() => {
    if (window.innerWidth <= COMPACT_TOP_BAR_BREAKPOINT && menuToggle) {
      setMenuToggle(false);
    }
  }, [location.pathname]);

  // Close sidebar when clicking outside (backdrop)
  const handleBackdropClick = () => {
    setMenuToggle(false);
  };

  if (loading) {
    return (
      <div id="preloader">
        <div className="sk-three-bounce">
          <div className="sk-child sk-bounce1"></div>
          <div className="sk-child sk-bounce2"></div>
          <div className="sk-child sk-bounce3"></div>
        </div>
      </div>
    );
  }

  return (
    <div
      id="main-wrapper"
      className={`show ${menuToggle ? "menu-toggle" : ""} ${compactTopBar ? "compact-topbar" : ""}`}
    >
      {/* Nav Header */}
      <NavHader compactTopBar={compactTopBar} />

      {/* ChatBox / Right Sidebar */}
      <ChatBox onClick={() => onClick("chatbox")} toggle={toggle} />

      {/* Header */}
      <Header compactTopBar={compactTopBar} onNote={() => onClick("chatbox")} />

      {/* Mobile sidebar backdrop */}
      {menuToggle && (
        <div
          className="sidebar-backdrop"
          onClick={handleBackdropClick}
        />
      )}

      {/* Sidebar */}
      <SideBar />

      {/* Content Body */}
      <div className="content-body">
        <div className="container-fluid">
          {user?.impersonating && (
            <div style={{
              background: 'linear-gradient(135deg, #f59e0b, #d97706)',
              color: '#fff',
              padding: '12px 20px',
              borderRadius: '14px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '10px',
              boxShadow: '0 2px 12px rgba(245, 158, 11, 0.25)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px', fontWeight: 600 }}>
                <i className="ri-spy-line" style={{ fontSize: '20px' }}></i>
                <span>
                  Stai navigando come <strong>{user.full_name}</strong>
                  {user.original_admin_name && (
                    <span style={{ opacity: 0.85, fontWeight: 400, marginLeft: '6px' }}>
                      (admin: {user.original_admin_name})
                    </span>
                  )}
                </span>
              </div>
              <button
                onClick={async () => {
                  try {
                    await authService.stopImpersonation();
                    window.location.href = '/welcome';
                  } catch (err) {
                    console.error('Error stopping impersonation:', err);
                  }
                }}
                style={{
                  padding: '6px 18px',
                  border: '1.5px solid rgba(255,255,255,0.5)',
                  borderRadius: '10px',
                  background: 'rgba(255,255,255,0.15)',
                  color: '#fff',
                  fontSize: '13px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'background 0.2s',
                }}
                onMouseEnter={(e) => e.target.style.background = 'rgba(255,255,255,0.3)'}
                onMouseLeave={(e) => e.target.style.background = 'rgba(255,255,255,0.15)'}
              >
                Torna al tuo account
              </button>
            </div>
          )}
          <Outlet context={{ user }} />
        </div>
      </div>

      {/* Footer */}
      <div className="footer">
        <div className="footer-links">
          <Link to="/supporto" className="footer-link" onClick={() => window.scrollTo(0, 0)}>
            <i className="mdi mdi-lifebuoy"></i> Supporto
          </Link>
          <span className="footer-divider"></span>
          <button className="footer-link" onClick={() => setShowTicketModal(true)}>
            <i className="mdi mdi-ticket-outline"></i> Apri un Ticket
          </button>
          <span className="footer-divider"></span>
          <Link to="/novita" className="footer-link" onClick={() => window.scrollTo(0, 0)}>
            <i className="mdi mdi-rocket"></i> Novità
          </Link>
        </div>
        <div className="copyright">
          <p>© <span className="text-success fw-semibold">Suite Clinica</span> · v1.0 · Sviluppata col ❤️ dal team IT</p>
        </div>
      </div>

      {/* Ticket Modal */}
      <Modal show={showTicketModal} onHide={() => setShowTicketModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Supporto Suite Clinica</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>
            Per supporto ed assistenza sulla suite clinica si chiede cortesemente di aprire un ticket a <strong>Emanuele Mastronardi</strong>.
          </p>
          <p className="mb-0">
            Se non hai accesso al sistema di ticketing, invia un email a{' '}
            <a href="mailto:e.mastronardi@corposostenibile.it"><strong>e.mastronardi@corposostenibile.it</strong></a>.
          </p>
        </Modal.Body>
        <Modal.Footer>
          <button className="btn btn-primary" onClick={() => setShowTicketModal(false)}>
            Ho capito
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

function DashboardLayout() {
  return (
    <AuthProvider>
      <DashboardContent />
    </AuthProvider>
  );
}

export default DashboardLayout;

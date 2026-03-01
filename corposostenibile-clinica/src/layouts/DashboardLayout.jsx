import { useState, useContext } from 'react';
import { Outlet, Link } from 'react-router-dom';
import { Modal } from 'react-bootstrap';
import NavHader from '../jsx/layouts/nav/NavHader';
import SideBar from '../jsx/layouts/nav/SideBar';
import Header from '../jsx/layouts/nav/Header';
import ChatBox from '../jsx/layouts/ChatBox';
import { ThemeContext } from '../context/ThemeContext';
import { AuthProvider, useAuth } from '../context/AuthContext';

/// Style
import '../styles/template.css';
import '../styles/custom-overrides.css';

function DashboardContent() {
  const { menuToggle } = useContext(ThemeContext);
  const { user, loading } = useAuth();
  const [toggle, setToggle] = useState("");
  const [showTicketModal, setShowTicketModal] = useState(false);

  const onClick = (name) => setToggle(toggle === name ? "" : name);

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
    <div id="main-wrapper" className={`show ${menuToggle ? "menu-toggle" : ""}`}>
      {/* Nav Header */}
      <NavHader />

      {/* ChatBox / Right Sidebar */}
      <ChatBox onClick={() => onClick("chatbox")} toggle={toggle} />

      {/* Header */}
      <Header onNote={() => onClick("chatbox")} />

      {/* Sidebar */}
      <SideBar />

      {/* Content Body */}
      <div className="content-body">
        <div className="container-fluid">
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

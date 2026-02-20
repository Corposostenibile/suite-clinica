import { useState, useContext, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import NavHader from '../jsx/layouts/nav/NavHader';
import SideBar from '../jsx/layouts/nav/SideBar';
import Header from '../jsx/layouts/nav/Header';
import ChatBox from '../jsx/layouts/ChatBox';
import { ThemeContext } from '../context/ThemeContext';
import { AuthProvider, useAuth } from '../context/AuthContext';

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
          <Outlet context={{ user }} />
        </div>
      </div>

      {/* Footer */}
      <div className="footer">
        <div className="copyright">
          <p>Copyright © <span className="text-success fw-semibold">CorpoSostenibile</span> 2026</p>
        </div>
      </div>
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

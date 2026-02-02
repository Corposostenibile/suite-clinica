import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

// Icons
import welcomeIcon from '../images/icons/welcome.png';
import customersIcon from '../images/icons/customers.png';
import teamIcon from '../images/icons/team.png';
import profiloIcon from '../images/icons/profilo.png';

function Sidebar({ user, collapsed, onMobileClose }) {
  const location = useLocation();
  const [activeMenu, setActiveMenu] = useState('');
  const [activeSubmenu, setActiveSubmenu] = useState('');

  const path = location.pathname;

  // Auto-activate menu based on current path
  useEffect(() => {
    // Check Clienti submenu
    if (path.startsWith('/customers')) {
      setActiveMenu('Clienti');
    }
    // Check Profilo submenu
    else if (path.startsWith('/profile')) {
      setActiveMenu('Profilo');
    }
    // Check Team submenu
    else if (path.startsWith('/team')) {
      setActiveMenu('Team');
    }
  }, [path]);

  const handleMenuClick = (menuTitle) => {
    if (activeMenu === menuTitle) {
      setActiveMenu('');
    } else {
      setActiveMenu(menuTitle);
    }
  };

  const handleSubmenuClick = (submenuTitle) => {
    if (activeSubmenu === submenuTitle) {
      setActiveSubmenu('');
    } else {
      setActiveSubmenu(submenuTitle);
    }
  };

  const isActive = (itemPath) => path === itemPath;
  const isMenuOpen = (menuTitle) => activeMenu === menuTitle;

  return (
    <div className={`deznav ${collapsed ? '' : 'active'}`}>
      <div className="deznav-scroll">
        <ul className="metismenu" id="menu">

          {/* Dashboard */}
          <li className={isActive('/welcome') ? 'mm-active' : ''}>
            <Link to="/welcome">
              <img src={welcomeIcon} className="menu-icon" alt="" />
              <span className="nav-text">Dashboard</span>
            </Link>
          </li>

          {/* === SEZIONE CLIENTI === */}
          <li className="nav-label">Clienti</li>

          {/* Clienti - con submenu per admin */}
          {user?.is_admin ? (
            <li className={`${isMenuOpen('Clienti') ? 'mm-active' : ''}`}>
              <Link
                to="#"
                className="has-arrow ai-icon"
                onClick={(e) => { e.preventDefault(); handleMenuClick('Clienti'); }}
              >
                <img src={customersIcon} className="menu-icon" alt="" />
                <span className="nav-text">Clienti</span>
              </Link>
              <ul className={isMenuOpen('Clienti') ? 'mm-show' : ''}>
                <li className={isActive('/customers') ? 'mm-active' : ''}>
                  <Link to="/customers">Elenco Generale</Link>
                </li>
                {/* --- Specialized Views --- */}
                <li className={isActive('/clienti-nutrizione') ? 'mm-active' : ''}>
                  <Link to="/clienti-nutrizione">Nutrizione</Link>
                </li>
                <li className={isActive('/clienti-coach') ? 'mm-active' : ''}>
                  <Link to="/clienti-coach">Coaching</Link>
                </li>
                <li className={isActive('/clienti-psicologia') ? 'mm-active' : ''}>
                  <Link to="/clienti-psicologia">Psicologia</Link>
                </li>
                {/* --- Operational Views --- */}
                <li className={isActive('/customers/in-scadenza') ? 'mm-active' : ''}>
                  <Link to="/customers/in-scadenza">In Scadenza</Link>
                </li>
                <li className={isActive('/customers/recupero-ghost') ? 'mm-active' : ''}>
                  <Link to="/customers/recupero-ghost">Recupero Ghost</Link>
                </li>
              </ul>
            </li>
          ) : (
            <li className={isActive('/customers') ? 'mm-active' : ''}>
              <Link to="/customers">
                <img src={customersIcon} className="menu-icon" alt="" />
                <span className="nav-text">Clienti</span>
              </Link>
            </li>
          )}

          {/* === SEZIONE TEAM === */}
          <li className="nav-label">Team</li>

          {/* Profilo */}
          <li className={`${isMenuOpen('Profilo') ? 'mm-active' : ''}`}>
            <Link
              to="#"
              className="has-arrow ai-icon"
              onClick={(e) => { e.preventDefault(); handleMenuClick('Profilo'); }}
            >
              <img src={profiloIcon} className="menu-icon" alt="" />
              <span className="nav-text">{user?.first_name || 'Profilo'}</span>
            </Link>
            <ul className={isMenuOpen('Profilo') ? 'mm-show' : ''}>
              <li className={isActive('/profile') ? 'mm-active' : ''}>
                <Link to="/profile">Il Tuo Profilo</Link>
              </li>
              <li className={isActive('/profile/okr') ? 'mm-active' : ''}>
                <Link to="/profile/okr">I Tuoi OKR</Link>
              </li>
            </ul>
          </li>

          {/* Team */}
          <li className={`${isMenuOpen('Team') ? 'mm-active' : ''}`}>
            <Link
              to="#"
              className="has-arrow ai-icon"
              onClick={(e) => { e.preventDefault(); handleMenuClick('Team'); }}
            >
              <img src={teamIcon} className="menu-icon" alt="" />
              <span className="nav-text">Team</span>
            </Link>
            <ul className={isMenuOpen('Team') ? 'mm-show' : ''}>
              <li className={isActive('/team') ? 'mm-active' : ''}>
                <Link to="/team">Lista Team</Link>
              </li>
              {user?.is_admin && (
                <li className={isActive('/team/birthdays') ? 'mm-active' : ''}>
                  <Link to="/team/birthdays">Compleanni</Link>
                </li>
              )}
            </ul>
          </li>

          {/* === SEZIONE RISORSE === */}
          <li className="nav-label">Risorse</li>
          <li className={isActive('/documentazione') ? 'mm-active' : ''}>
            <Link to="/documentazione">
              <i className="ri-book-read-line menu-icon-ri"></i>
              <span className="nav-text">Documentazione</span>
            </Link>
          </li>


          {/* === SEZIONE IT (solo admin) === */}
          {user?.is_admin && (
            <>
              <li className="nav-label">IT</li>
              <li className={isActive('/it/projects') ? 'mm-active' : ''}>
                <Link to="/it/projects">
                  <i className="ri-folder-line menu-icon-ri"></i>
                  <span className="nav-text">Progetti</span>
                </Link>
              </li>
            </>
          )}

        </ul>
      </div>
    </div>
  );
}

export default Sidebar;

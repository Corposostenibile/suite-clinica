import React, { useContext, useState } from "react";

import { Link } from "react-router-dom";
/// Scroll

import { Dropdown } from "react-bootstrap";

/// Image
import defaultAvatar from "../../../images/profile/pic1.jpg";

import { ThemeContext } from "../../../context/ThemeContext";
import { useAuth } from "../../../context/AuthContext";
import { SVGICON } from "../../constant/theme.jsx";
import GlobalSearch from "../../../components/GlobalSearch";

// Role labels in Italian
const ROLE_LABELS = {
  admin: 'Amministrazione',
  amministratore: 'Amministrazione',
  cco: 'CCO',
  coordinatore: 'Coordinatore',
  team_leader: 'Team Leader',
  professionista: 'Professionista',
  team_esterno: 'Team Esterno',
  consulente: 'Consulente',
  nutrizionista: 'Nutrizionista',
  coach: 'Coach',
  psicologo: 'Psicologo',
};

const Header = ({ onNote }) => {
  const { background, changeBackground } = useContext(ThemeContext);
  const { user, logout } = useAuth();

  function ThemeChange() {
    if (background.value === "light") {
      changeBackground({ value: "dark" });
    } else {
      changeBackground({ value: "light" })
    }
  }
  const [fullScreen, setFullScreen] = useState(false);
  const onFullScreen = () => {
    var elem = document.documentElement;
    setFullScreen(elem ? true : false);

    if (elem.requestFullscreen) {
      elem.requestFullscreen();
    } else if (elem.webkitRequestFullscreen) {
      elem.webkitRequestFullscreen();
    } else if (elem.msRequestFullscreen) {
      elem.msRequestFullscreen();
    }
  };
  const offFullScreen = () => {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    } else if (document.webkitExitFullscreen) {
      /* Safari */
      document.webkitExitFullscreen();
    } else if (document.msExitFullscreen) {
      /* IE11 */
      document.msExitFullscreen();
    }
    setFullScreen(false);
  };
  return (
    <div className="header" style={{ backdropFilter: 'blur(10px)', background: 'rgba(255, 255, 255, 0.9)', borderBottom: '1px solid #e2e8f0' }}>
      <div className="header-content">
        <nav className="navbar navbar-expand">
          <div className="collapse navbar-collapse justify-content-between">
            <div className="header-left">
              <GlobalSearch />
            </div>
            <ul className="navbar-nav header-right">
              <li className="nav-item dropdown notification_dropdown">
                <Link
                  to="/supporto"
                  className="nav-link bell pulse-hover"
                  title="Supporto"
                  style={{ transition: 'all 0.3s ease' }}
                >
                  <i className="fas fa-question-circle" style={{ fontSize: '20px', color: '#64748b' }} />
                </Link>
              </li>
              {fullScreen ? (
                <li
                  className="nav-item dropdown notification_dropdown"
                  onClick={() => offFullScreen()}
                >
                  <Link className="nav-link dz-fullscreen active" to="#">
                    <svg
                      id="icon-full"
                      viewBox="0 0 24 24"
                      width={20}
                      height={20}
                      stroke="#64748b"
                      strokeWidth={2}
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="css-i6dzq1"
                    >
                      <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                    </svg>

                    <svg
                      id="icon-minimize"
                      width={20}
                      height={20}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#64748b"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="feather feather-minimize"
                    >
                      <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                    </svg>
                  </Link>
                </li>
              ) : (
                <li className="nav-item dropdown notification_dropdown">
                  <Link
                    className="nav-link dz-fullscreen"
                    to="#"
                    onClick={() => onFullScreen()}
                    style={{ transition: 'all 0.3s ease' }}
                  >
                    <svg
                      id="icon-full"
                      viewBox="0 0 24 24"
                      width={20}
                      height={20}
                      stroke="#64748b"
                      strokeWidth={2}
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="css-i6dzq1"
                    >
                      <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                    </svg>
                    <svg
                      id="icon-minimize"
                      width={20}
                      height={20}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#64748b"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="feather feather-minimize"
                    >
                      <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                    </svg>
                  </Link>
                </li>
              )}
              <Dropdown as="li" className="nav-item notification_dropdown">
                <Dropdown.Toggle variant="" as="a"
                  className="nav-link i-false c-pointer dropdown-toggle-no-caret"
                  role="button"
                  data-toggle="dropdown"
                  style={{ display: 'flex', alignItems: 'center', transition: 'all 0.3s ease' }}
                >
                  <i className="ri-notification-3-line" style={{ fontSize: '20px', color: '#64748b' }}></i>
                </Dropdown.Toggle>
                <Dropdown.Menu align="end" style={{ minWidth: '320px', border: 'none', boxShadow: '0 10px 40px rgba(0,0,0,0.1)', borderRadius: '16px' }}>
                  <div className="p-4 text-center">
                    <div className="mb-3">
                      <i className="ri-microsoft-fill" style={{ fontSize: '48px', color: '#5059C9' }}></i>
                    </div>
                    <h6 className="mb-2 fw-bold" style={{ color: '#1e293b' }}>Notifiche su Microsoft Teams</h6>
                    <p className="text-muted mb-3" style={{ fontSize: '13px', lineHeight: '1.5' }}>
                      Le notifiche verranno inviate direttamente su <strong>Microsoft Teams</strong>.
                    </p>
                    <div className="p-2 bg-light rounded-3" style={{ fontSize: '11px', color: '#94a3b8' }}>
                      Suite Clinica ottimizzata per Microsoft Teams
                    </div>
                  </div>
                </Dropdown.Menu>
              </Dropdown>
              <Dropdown as="li" className="nav-item dropdown header-profile">
                <Dropdown.Toggle variant="" as="a" className="nav-link i-false c-pointer dropdown-toggle-no-caret" style={{ background: '#f8fafc', borderRadius: '12px', padding: '6px 12px', marginLeft: '12px', border: '1px solid #f1f5f9' }}>
                  <img src={user?.avatar_path || defaultAvatar} width={34} height={34} alt="" style={{ borderRadius: '10px' }} />
                  <div className="header-info ms-2">
                    <span style={{ fontSize: '13px' }}>Ciao, <strong style={{ color: '#1e293b' }}>{user?.first_name || 'Utente'}</strong></span>
                    <small style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 600 }}>{ROLE_LABELS[user?.role] || user?.role || 'Profilo'}</small>
                  </div>
                </Dropdown.Toggle>
                <Dropdown.Menu align="end" className="mt-2 dropdown-menu-end" style={{ border: 'none', boxShadow: '0 10px 40px rgba(0,0,0,0.1)', borderRadius: '16px', padding: '10px' }}>
                  <Link to="/profilo" className="dropdown-item ai-icon d-flex align-items-center p-2 rounded-3">
                    <div className="icon-wrapper-profile bg-primary-light d-flex align-items-center justify-content-center me-2" style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(80, 89, 201, 0.1)' }}>
                      <i className="ri-user-line text-primary" style={{ fontSize: '16px' }}></i>
                    </div>
                    <span className="fw-semibold" style={{ fontSize: '14px' }}>Mio Profilo</span>
                  </Link>
                  <button onClick={logout} className="dropdown-item ai-icon d-flex align-items-center p-2 rounded-3 mt-1">
                    <div className="icon-wrapper-logout bg-danger-light d-flex align-items-center justify-content-center me-2" style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.1)' }}>
                      <i className="ri-logout-box-r-line text-danger" style={{ fontSize: '16px' }}></i>
                    </div>
                    <span className="fw-semibold text-danger" style={{ fontSize: '14px' }}>Esci</span>
                  </button>
                </Dropdown.Menu>
              </Dropdown>
              <li className="nav-item right-sidebar ms-2">
                <Link
                  to="#"
                  className="nav-link bell i-false c-pointer ai-icon p-2"
                  onClick={() => onNote && onNote()}
                  style={{ background: '#f1f5f9', borderRadius: '12px', width: '42px', height: '42px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                >
                  <svg id="icon-menu" viewBox="0 0 24 24" width="22" height="22" stroke="#64748b" strokeWidth="2" fill="none"
                    strokeLinecap="round" strokeLinejoin="round" className="css-i6dzq1 hoverEffect"
                  >
                    <rect x="3" y="3" width="7" height="7" rx="1"></rect>
                    <rect x="14" y="3" width="7" height="7" rx="1"></rect>
                    <rect x="14" y="14" width="7" height="7" rx="1"></rect>
                    <rect x="3" y="14" width="7" height="7" rx="1"></rect>
                  </svg>
                </Link>
              </li>
            </ul>
          </div>
        </nav>
      </div>
    </div>
  );
};

export default Header;

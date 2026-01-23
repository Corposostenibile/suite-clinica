import React, { useContext, useState } from "react";

import { Link } from "react-router-dom";
/// Scroll

import { Dropdown } from "react-bootstrap";

/// Image
import defaultAvatar from "../../../images/profile/pic1.jpg";

import { ThemeContext } from "../../../context/ThemeContext";
import { useAuth } from "../../../context/AuthContext";
import { SVGICON } from "../../constant/theme.jsx";

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
    <div className="header">
      <div className="header-content">
        <nav className="navbar navbar-expand">
          <div className="collapse navbar-collapse justify-content-between">
            <div className="header-left">
              <div className="search_bar dropdown">
                <span className="search_icon p-3 c-pointer" data-bs-toggle="dropdown">
                  <i className="mdi mdi-magnify"></i>
                </span>
                <div className="dropdown-menu p-0 m-0">
                  <form>
                    <input className="form-control" type="search" placeholder="Cerca..." aria-label="Cerca" />
                  </form>
                </div>
              </div>
            </div>
            <ul className="navbar-nav header-right">
              <li className="nav-item dropdown notification_dropdown">
                <Link
                  to="/supporto"
                  className="nav-link bell"
                  title="Supporto"
                >
                  <i className="fas fa-question-circle" style={{ fontSize: '20px' }} />
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
                      stroke="currentColor"
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
                      stroke="currentColor"
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
                  >
                    <svg
                      id="icon-full"
                      viewBox="0 0 24 24"
                      width={20}
                      height={20}
                      stroke="currentColor"
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
                      stroke="currentColor"
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
                  style={{ display: 'flex', alignItems: 'center' }}
                >
                  <i className="ri-notification-3-line" style={{ fontSize: '20px' }}></i>
                </Dropdown.Toggle>
                <Dropdown.Menu align="end" style={{ minWidth: '320px' }}>
                  <div className="p-4 text-center">
                    <div className="mb-3">
                      <i className="ri-microsoft-fill" style={{ fontSize: '48px', color: '#5059C9' }}></i>
                    </div>
                    <h6 className="mb-2 fw-semibold">Notifiche su Microsoft Teams</h6>
                    <p className="text-muted mb-3" style={{ fontSize: '13px', lineHeight: '1.5' }}>
                      Le notifiche verranno inviate direttamente su <strong>Microsoft Teams</strong>.
                    </p>
                    <p className="text-muted mb-0" style={{ fontSize: '12px', lineHeight: '1.5' }}>
                      Suite Clinica ti invierà messaggi su Teams per reminder, notifiche, aggiornamenti e comunicazioni importanti.
                    </p>
                  </div>
                </Dropdown.Menu>
              </Dropdown>
              <Dropdown as="li" className="nav-item dropdown header-profile">
                <Dropdown.Toggle variant="" as="a" className="nav-link i-false c-pointer dropdown-toggle-no-caret">
                  <img src={user?.avatar_path || defaultAvatar} width={20} alt="" />
                  <div className="header-info">
                    <span>Ciao, <strong>{user?.first_name || 'Utente'}</strong></span>
                    <small>{ROLE_LABELS[user?.role] || user?.role || 'Profilo'}</small>
                  </div>
                </Dropdown.Toggle>
                <Dropdown.Menu align="end" className="mt-0 dropdown-menu-end">
                  <Link to="/profilo" className="dropdown-item ai-icon">
                    <svg
                      id="icon-user1" xmlns="http://www.w3.org/2000/svg" className="text-primary"
                      width={18} height={18} viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
                    >
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx={12} cy={7} r={4} />
                    </svg>
                    <span className="ms-2">Profilo</span>
                  </Link>
                  <button onClick={logout} className="dropdown-item ai-icon">
                    <svg
                      id="icon-logout" xmlns="http://www.w3.org/2000/svg"
                      className="text-danger" width={18} height={18} viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
                    >
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                      <polyline points="16 17 21 12 16 7" />
                      <line x1={21} y1={12} x2={9} y2={12} />
                    </svg>
                    <span className="ms-2">Esci</span>
                  </button>
                </Dropdown.Menu>
              </Dropdown>
              {/* Right Sidebar Toggle Button */}
              <li className="nav-item right-sidebar">
                <Link
                  to="#"
                  className="nav-link bell i-false c-pointer ai-icon"
                  onClick={() => onNote && onNote()}
                >
                  <svg id="icon-menu" viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none"
                    strokeLinecap="round" strokeLinejoin="round" className="css-i6dzq1 hoverEffect"
                  >
                    <rect x="3" y="3" width="7" height="7" style={{strokeDasharray: "28px 48px"}}></rect>
                    <rect x="14" y="3" width="7" height="7" style={{strokeDasharray: "28px 48px"}}></rect>
                    <rect x="14" y="14" width="7" height="7" style={{strokeDasharray: "28px 48px"}}></rect>
                    <rect x="3" y="14" width="7" height="7" style={{strokeDasharray: "28px 48px"}}></rect>
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

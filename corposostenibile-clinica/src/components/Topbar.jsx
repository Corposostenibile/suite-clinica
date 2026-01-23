import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import authService from '../services/authService';

function Topbar({ user, onToggleSidebar, sidebarCollapsed }) {
  const navigate = useNavigate();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [fullScreen, setFullScreen] = useState(false);

  const notificationRef = useRef(null);
  const profileRef = useRef(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setShowProfileMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try {
      await authService.logout();
      navigate('/auth/login');
    } catch (error) {
      console.error('Logout error:', error);
      navigate('/auth/login');
    }
  };

  const onFullScreen = () => {
    const elem = document.documentElement;
    setFullScreen(true);
    if (elem.requestFullscreen) {
      elem.requestFullscreen();
    } else if (elem.webkitRequestFullscreen) {
      elem.webkitRequestFullscreen();
    } else if (elem.msRequestFullscreen) {
      elem.msRequestFullscreen();
    }
  };

  const offFullScreen = () => {
    setFullScreen(false);
    if (document.exitFullscreen) {
      document.exitFullscreen();
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen();
    } else if (document.msExitFullscreen) {
      document.msExitFullscreen();
    }
  };

  const userInitials = user
    ? `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase()
    : 'U';

  return (
    <div className="header">
      <div className="header-content">
        <nav className="navbar navbar-expand">
          <div className="collapse navbar-collapse justify-content-between">
            {/* Header Left - Search */}
            <div className="header-left">
              <div className="search_bar dropdown">
                <span className="search_icon p-3 c-pointer">
                  <i className="ri-search-line"></i>
                </span>
              </div>
            </div>

            {/* Header Right */}
            <ul className="navbar-nav header-right">

              {/* Fullscreen Toggle */}
              <li className="nav-item dropdown notification_dropdown">
                {fullScreen ? (
                  <button
                    className="nav-link c-pointer"
                    onClick={offFullScreen}
                  >
                    <svg
                      viewBox="0 0 24 24"
                      width={20}
                      height={20}
                      stroke="currentColor"
                      strokeWidth={2}
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                    </svg>
                  </button>
                ) : (
                  <button
                    className="nav-link c-pointer"
                    onClick={onFullScreen}
                  >
                    <svg
                      viewBox="0 0 24 24"
                      width={20}
                      height={20}
                      stroke="currentColor"
                      strokeWidth={2}
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                    </svg>
                  </button>
                )}
              </li>

              {/* Notifications */}
              <li className="nav-item dropdown notification_dropdown" ref={notificationRef}>
                <button
                  className="nav-link bell ai-icon i-false c-pointer icon-bell-effect"
                  onClick={() => setShowNotifications(!showNotifications)}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                    <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                  </svg>
                  <div className="pulse-css"></div>
                </button>

                {showNotifications && (
                  <div className="dropdown-menu dropdown-menu-end show">
                    <div className="widget-media dz-scroll p-3 height380" style={{ height: '300px' }}>
                      <ul className="timeline">
                        <li>
                          <div className="timeline-panel">
                            <div className="media me-2 media-success">
                              <i className="ri-checkbox-circle-line"></i>
                            </div>
                            <div className="media-body">
                              <h6 className="mb-1">Benvenuto nella Suite!</h6>
                              <small className="d-block">
                                Il tuo account e' attivo
                              </small>
                            </div>
                          </div>
                        </li>
                      </ul>
                    </div>
                    <Link className="all-notification" to="#" onClick={() => setShowNotifications(false)}>
                      Vedi tutte le notifiche <i className="ri-arrow-right-line"></i>
                    </Link>
                  </div>
                )}
              </li>

              {/* Profile Dropdown */}
              <li className="nav-item dropdown header-profile" ref={profileRef}>
                <button
                  className="nav-link i-false c-pointer"
                  onClick={() => setShowProfileMenu(!showProfileMenu)}
                >
                  {user?.avatar_path ? (
                    <img src={user.avatar_path} alt="profile" />
                  ) : (
                    <div className="avatar-initials">
                      {userInitials}
                    </div>
                  )}
                  <div className="header-info">
                    <span>Ciao, <strong>{user?.first_name || 'Utente'}</strong></span>
                    <small>{user?.is_admin ? 'Amministratore' : 'Team Member'}</small>
                  </div>
                </button>

                {showProfileMenu && (
                  <div className="dropdown-menu dropdown-menu-end show">
                    <Link
                      to="/profile"
                      className="dropdown-item ai-icon"
                      onClick={() => setShowProfileMenu(false)}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="text-primary"
                        width={18}
                        height={18}
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx={12} cy={7} r={4} />
                      </svg>
                      <span className="ms-2">Profilo</span>
                    </Link>
                    <button
                      className="dropdown-item ai-icon"
                      onClick={handleLogout}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="text-danger"
                        width={18}
                        height={18}
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                        <polyline points="16 17 21 12 16 7" />
                        <line x1={21} y1={12} x2={9} y2={12} />
                      </svg>
                      <span className="ms-2">Logout</span>
                    </button>
                  </div>
                )}
              </li>

            </ul>
          </div>
        </nav>
      </div>
    </div>
  );
}

export default Topbar;

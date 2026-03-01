import React, { useContext, useEffect, useState } from "react";

import { Link, useNavigate } from "react-router-dom";
/// Scroll

import { Dropdown } from "react-bootstrap";

/// Image
import defaultAvatar from "../../../images/profile/pic1.jpg";

import { ThemeContext } from "../../../context/ThemeContext";
import { useAuth } from "../../../context/AuthContext";
import { SVGICON } from "../../constant/theme.jsx";
import GlobalSearch from "../../../components/GlobalSearch";
import pushNotificationService from "../../../services/pushNotificationService";

// Role labels in Italian
const ROLE_LABELS = {
  admin: 'Amministrazione',
  amministratore: 'Amministrazione',
  cco: 'CCO',
  coordinatore: 'Coordinatore',
  team_leader: 'Team Leader',
  health_manager: 'Health Manager',
  professionista: 'Professionista',
  team_esterno: 'Team Esterno',
  consulente: 'Consulente',
  nutrizionista: 'Nutrizionista',
  coach: 'Coach',
  psicologo: 'Psicologo',
};

const getRoleLabel = (user) => {
  if (!user) return 'Profilo';
  if (user.role === 'team_leader' && user.is_health_manager_team_leader) {
    return 'Team Leader HM';
  }
  if (user.role === 'team_leader') {
    const specialty = String(user.specialty || '').toLowerCase();
    if (specialty === 'nutrizione' || specialty === 'nutrizionista') return 'Team Leader Nutrizione';
    if (specialty === 'coach') return 'Team Leader Coach';
    if (specialty === 'psicologia' || specialty === 'psicologo' || specialty === 'psicologa') return 'Team Leader Psicologia';
    if (specialty === 'medico') return 'Team Leader Medico';
    return 'Team Leader';
  }
  return ROLE_LABELS[user.role] || user.role || 'Profilo';
};

const Header = ({ onNote }) => {
  const { background, changeBackground } = useContext(ThemeContext);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [pushStatus, setPushStatus] = useState({
    supported: true,
    backendEnabled: true,
    permission: 'default',
    subscribed: false,
    enabled: false,
  });
  const [pushLoading, setPushLoading] = useState(true);
  const [pushBusy, setPushBusy] = useState(false);
  const [notificationItems, setNotificationItems] = useState([]);
  const [notificationCount, setNotificationCount] = useState(0);
  const [notificationLoading, setNotificationLoading] = useState(true);

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

  const loadPushStatus = async () => {
    setPushLoading(true);
    const status = await pushNotificationService.getPushStatus();
    setPushStatus(status);
    setPushLoading(false);
  };

  const loadNotifications = async () => {
    setNotificationLoading(true);
    try {
      const data = await pushNotificationService.getNotifications({ unreadOnly: true, limit: 6 });
      setNotificationCount(Number(data?.unreadCount || 0));
      setNotificationItems(Array.isArray(data?.items) ? data.items : []);
    } catch (error) {
      console.error('Error fetching notifications:', error);
      setNotificationCount(0);
      setNotificationItems([]);
    } finally {
      setNotificationLoading(false);
    }
  };

  useEffect(() => {
    if (user?.id) {
      loadPushStatus();
      loadNotifications();
    }
  }, [user?.id]);

  useEffect(() => {
    if (!user?.id) return;
    const timer = setInterval(() => {
      loadNotifications();
    }, 60000);
    return () => clearInterval(timer);
  }, [user?.id]);

  const handleEnablePush = async () => {
    setPushBusy(true);
    const result = await pushNotificationService.enablePushNotifications();
    await loadPushStatus();
    setPushBusy(false);
    if (!result?.subscribed) {
      window.alert('Notifiche non abilitate. Verifica i permessi del browser/PWA.');
    }
  };

  const handleDisablePush = async () => {
    setPushBusy(true);
    await pushNotificationService.disablePushNotifications();
    await loadPushStatus();
    setPushBusy(false);
  };

  const pushDisabledReason = !pushStatus.supported
    ? 'Il browser non supporta le notifiche push.'
    : !pushStatus.backendEnabled
      ? 'Push non configurate sul server.'
      : pushStatus.permission === 'denied'
        ? 'Permesso notifiche negato nel browser.'
        : 'Riceverai notifiche push su task e aggiornamenti futuri.';

  const formatNotificationTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' });
  };

  const getNotificationDestination = (notification) => {
    const href = notification?.url || '/task';
    const external = /^https?:\/\//i.test(href);
    return { href, external };
  };

  const handleNotificationClick = async (notification) => {
    const res = await pushNotificationService.markNotificationAsRead(notification.id);
    setNotificationItems((prev) => prev.filter((item) => item.id !== notification.id));
    if (res?.ok && Number.isFinite(res.unreadCount)) {
      setNotificationCount(res.unreadCount);
    } else {
      setNotificationCount((prev) => Math.max(0, prev - 1));
    }

    const destination = getNotificationDestination(notification);
    if (destination.external) {
      window.open(destination.href, '_blank', 'noopener,noreferrer');
      return;
    }
    navigate(destination.href);
  };

  const handleNotificationToggle = (isOpen) => {
    if (isOpen) loadNotifications();
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
              <Dropdown as="li" className="nav-item notification_dropdown" onToggle={handleNotificationToggle}>
                <Dropdown.Toggle variant="" as="a"
                  className="nav-link i-false c-pointer dropdown-toggle-no-caret"
                  role="button"
                  data-toggle="dropdown"
                  style={{ display: 'flex', alignItems: 'center', transition: 'all 0.3s ease', position: 'relative' }}
                >
                  <i className="ri-notification-3-line" style={{ fontSize: '20px', color: '#64748b' }}></i>
                  {notificationCount > 0 && (
                    <span
                      className="badge bg-danger"
                      style={{ position: 'absolute', top: '2px', right: '-4px', fontSize: '10px', minWidth: '18px', height: '18px', borderRadius: '999px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                    >
                      {notificationCount > 99 ? '99+' : notificationCount}
                    </span>
                  )}
                </Dropdown.Toggle>
                <Dropdown.Menu align="end" style={{ minWidth: '320px', border: 'none', boxShadow: '0 10px 40px rgba(0,0,0,0.1)', borderRadius: '16px' }}>
                  <div className="p-4 text-center">
                    <div className="mb-3">
                      <i className="ri-notification-3-line" style={{ fontSize: '48px', color: pushStatus.enabled ? '#25B36A' : '#64748b' }}></i>
                    </div>
                    <h6 className="mb-2 fw-bold" style={{ color: '#1e293b' }}>Notifiche Push</h6>
                    <p className="text-muted mb-3" style={{ fontSize: '13px', lineHeight: '1.5' }}>
                      {pushLoading ? 'Verifica stato notifiche...' : pushDisabledReason}
                    </p>
                    <div className="mb-3">
                      {pushStatus.enabled ? (
                        <span className="badge bg-success-subtle text-success border border-success-subtle px-3 py-2">Attive</span>
                      ) : (
                        <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-3 py-2">Disattivate</span>
                      )}
                    </div>
                    {pushStatus.enabled ? (
                      <button
                        className="btn btn-outline-danger btn-sm"
                        onClick={handleDisablePush}
                        disabled={pushBusy || pushLoading}
                      >
                        {pushBusy ? 'Disattivo...' : 'Disattiva notifiche'}
                      </button>
                    ) : (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={handleEnablePush}
                        disabled={pushBusy || pushLoading || !pushStatus.supported || !pushStatus.backendEnabled || pushStatus.permission === 'denied'}
                      >
                        {pushBusy ? 'Attivo...' : 'Attiva notifiche push'}
                      </button>
                    )}
                  </div>
                  <div className="border-top px-3 py-2 d-flex align-items-center justify-content-between">
                    <span className="fw-semibold" style={{ color: '#1e293b', fontSize: '13px' }}>Notifiche non lette</span>
                    <Link to="/task" style={{ fontSize: '12px' }}>Apri tutte</Link>
                  </div>
                  <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
                    {notificationLoading ? (
                      <div className="px-3 py-3 text-muted text-center" style={{ fontSize: '12px' }}>Caricamento notifiche...</div>
                    ) : notificationItems.length === 0 ? (
                      <div className="px-3 py-3 text-muted text-center" style={{ fontSize: '12px' }}>Nessuna notifica disponibile</div>
                    ) : (
                      notificationItems.map((notification) => {
                        const iconClass = notification.kind === 'task_assigned' ? 'ri-task-line' : 'ri-notification-3-line';
                        const iconColor = notification.kind === 'task_assigned' ? '#25B36A' : '#64748b';
                        return (
                          <button
                            key={notification.id}
                            type="button"
                            onClick={() => handleNotificationClick(notification)}
                            className="w-100 text-start border-0 bg-white px-3 py-2 border-top"
                            style={{ cursor: 'pointer' }}
                          >
                            <div className="d-flex align-items-start justify-content-between gap-2">
                              <div className="d-flex align-items-start gap-2">
                                <i className={iconClass} style={{ color: iconColor, marginTop: '2px' }}></i>
                                <div>
                                  <div className="fw-semibold" style={{ fontSize: '12px', color: '#1e293b', lineHeight: 1.3 }}>
                                    {notification.title || 'Nuova notifica'}
                                  </div>
                                  <div className="text-muted" style={{ fontSize: '11px' }}>
                                    {notification.body || 'Apri per dettagli'}
                                  </div>
                                </div>
                              </div>
                              <span className="text-muted" style={{ fontSize: '10px', whiteSpace: 'nowrap' }}>
                                {formatNotificationTime(notification.created_at)}
                              </span>
                            </div>
                          </button>
                        );
                      })
                    )}
                  </div>
                </Dropdown.Menu>
              </Dropdown>
              <Dropdown as="li" className="nav-item dropdown header-profile">
                <Dropdown.Toggle variant="" as="a" className="nav-link i-false c-pointer dropdown-toggle-no-caret" style={{ background: '#f8fafc', borderRadius: '12px', padding: '6px 12px', marginLeft: '12px', border: '1px solid #f1f5f9' }}>
                  <img src={user?.avatar_path || defaultAvatar} width={34} height={34} alt="" style={{ borderRadius: '10px' }} />
                  <div className="header-info ms-2">
                    <span style={{ fontSize: '13px' }}>Ciao, <strong style={{ color: '#1e293b' }}>{user?.first_name || 'Utente'}</strong></span>
                    <small style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 600 }}>{getRoleLabel(user)}</small>
                  </div>
                </Dropdown.Toggle>
                <Dropdown.Menu align="end" className="mt-2 dropdown-menu-end" style={{ border: 'none', boxShadow: '0 10px 40px rgba(0,0,0,0.1)', borderRadius: '16px', padding: '10px' }}>
                  <Link to="/profilo" className="dropdown-item ai-icon d-flex align-items-center p-2 rounded-3">
                    <div className="icon-wrapper-profile bg-primary-light d-flex align-items-center justify-content-center me-2" style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(80, 89, 201, 0.1)' }}>
                      <i className="ri-user-line text-primary" style={{ fontSize: '16px' }}></i>
                    </div>
                    <span className="fw-semibold" style={{ fontSize: '14px' }}>Mio Profilo</span>
                  </Link>
                  <Link to="/novita" className="dropdown-item ai-icon d-flex align-items-center p-2 rounded-3 mt-1">
                    <div className="d-flex align-items-center justify-content-center me-2" style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(37, 179, 106, 0.1)' }}>
                      <i className="mdi mdi-rocket text-success" style={{ fontSize: '16px' }}></i>
                    </div>
                    <span className="fw-semibold" style={{ fontSize: '14px' }}>Novità</span>
                  </Link>
                  <button onClick={logout} className="dropdown-item ai-icon d-flex align-items-center p-2 rounded-3 mt-1">
                    <div className="icon-wrapper-logout bg-danger-light d-flex align-items-center justify-content-center me-2" style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.1)' }}>
                      <i className="ri-logout-box-r-line text-danger" style={{ fontSize: '16px' }}></i>
                    </div>
                    <span className="fw-semibold text-danger" style={{ fontSize: '14px' }}>Esci</span>
                  </button>
                </Dropdown.Menu>
              </Dropdown>
              <li className="nav-item right-sidebar ms-2" style={{ marginRight: '1rem' }}>
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

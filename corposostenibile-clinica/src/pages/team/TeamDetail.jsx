import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import teamService, {
  ROLE_LABELS,
  SPECIALTY_LABELS,
  ROLE_COLORS,
  SPECIALTY_COLORS
} from '../../services/teamService';
import checkService from '../../services/checkService';
import trainingService from '../../services/trainingService';
import { STATO_LABELS } from '../../services/clientiService';

// Client status colors (for simple badges)
const STATO_COLORS = {
  'In prova': { bg: '#fef3c7', color: '#92400e', icon: 'ri-timer-line' },
  'Attivo': { bg: '#dcfce7', color: '#166534', icon: 'ri-checkbox-circle-line' },
  'Non attivo': { bg: '#fee2e2', color: '#991b1b', icon: 'ri-close-circle-line' },
  'In pausa': { bg: '#e0e7ff', color: '#3730a3', icon: 'ri-pause-circle-line' },
  'Freeze': { bg: '#e0f2fe', color: '#0369a1', icon: 'ri-snowflake-line' },
};

// Stili per la tabella professionale (stile ClientiList)
const tableStyles = {
  card: {
    borderRadius: '16px',
    border: 'none',
    boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
    overflow: 'hidden',
  },
  tableHeader: {
    background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
    borderBottom: '2px solid #e2e8f0',
  },
  th: {
    padding: '14px 16px',
    fontSize: '11px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: '#64748b',
    whiteSpace: 'nowrap',
    borderBottom: 'none',
  },
  td: {
    padding: '14px 16px',
    fontSize: '14px',
    color: '#334155',
    borderBottom: '1px solid #f1f5f9',
    verticalAlign: 'middle',
  },
  row: {
    transition: 'all 0.15s ease',
  },
  nameLink: {
    color: '#3b82f6',
    fontWeight: 600,
    textDecoration: 'none',
    transition: 'color 0.15s ease',
  },
  emptyCell: {
    color: '#cbd5e1',
    fontStyle: 'normal',
    fontSize: '13px',
  },
  badge: {
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'capitalize',
    letterSpacing: '0.3px',
  },
  actionBtn: {
    width: '32px',
    height: '32px',
    padding: 0,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '8px',
    border: '1px solid',
    transition: 'all 0.15s ease',
    marginLeft: '4px',
  },
  avatarTeam: {
    position: 'relative',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    marginRight: '3px',
  },
  avatarInitials: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '9px',
    fontWeight: 700,
    textTransform: 'uppercase',
    border: '2px solid #fff',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  avatarBadge: {
    position: 'absolute',
    bottom: '-2px',
    right: '-2px',
    fontSize: '6px',
    fontWeight: 700,
    color: '#fff',
    padding: '1px 3px',
    borderRadius: '3px',
    lineHeight: 1,
    boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
  },
};

// Colori per i badge di stato (gradients)
const STATO_BADGE_STYLES = {
  attivo: { background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff' },
  ghost: { background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)', color: '#fff' },
  pausa: { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: '#fff' },
  stop: { background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', color: '#fff' },
  insoluto: { background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)', color: '#fff' },
  freeze: { background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)', color: '#fff' },
};

// Colori ruoli per avatar team
const TEAM_ROLE_COLORS = {
  hm: { bg: '#f3e8ff', text: '#9333ea', badge: '#9333ea' },
  n: { bg: '#dcfce7', text: '#16a34a', badge: '#22c55e' },
  c: { bg: '#dbeafe', text: '#2563eb', badge: '#3b82f6' },
  p: { bg: '#fce7f3', text: '#db2777', badge: '#ec4899' },
  ca: { bg: '#fef3c7', text: '#d97706', badge: '#f59e0b' },
};

// Gradient colors by role (same as TeamList)
const ROLE_GRADIENTS = {
  admin: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  team_leader: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  professionista: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  team_esterno: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
};

// Stili per i rating badge (Check tab)
const getRatingStyle = (rating) => {
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: '32px',
    padding: '4px 10px',
    borderRadius: '8px',
    fontSize: '12px',
    fontWeight: 700,
  };
  if (rating === null || rating === undefined) return { ...base, background: 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)', color: '#64748b' };
  if (rating >= 8) return { ...base, background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)', color: '#166534' };
  if (rating >= 7) return { ...base, background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)', color: '#92400e' };
  return { ...base, background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)', color: '#991b1b' };
};

// KPI Badge style (Check tab)
const getKpiBadgeStyle = (rating) => {
  const base = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 14px',
    borderRadius: '20px',
    fontSize: '13px',
    fontWeight: 600,
  };
  if (rating === null || rating === undefined) return { ...base, background: 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)', color: '#64748b' };
  if (rating >= 8) return { ...base, background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)', color: '#166534' };
  if (rating >= 7) return { ...base, background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)', color: '#92400e' };
  return { ...base, background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)', color: '#991b1b' };
};

// Avatar styles for Check tab
const checkAvatarStyles = {
  confirmBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    fontSize: '9px',
    marginLeft: '4px',
  },
  confirmYes: {
    background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
    color: '#166534',
  },
  confirmNo: {
    background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
    color: '#92400e',
  },
};

// Component to render professional with read status (Check tab)
const ProfessionalCell = ({ professionals, rating }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
      {/* Rating Badge */}
      <span style={getRatingStyle(rating)}>
        {rating ?? '-'}
      </span>

      {/* Professionals */}
      {professionals && professionals.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {professionals.map((prof, idx) => (
            <div key={prof.id || idx} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <img
                src={prof.avatar_path || '/static/assets/immagini/logo_user.png'}
                alt=""
                className="rounded-circle border border-2 border-white shadow-sm"
                style={{ width: '28px', height: '28px', objectFit: 'cover', background: '#fff' }}
                onError={(e) => {
                  e.target.src = '/static/assets/immagini/logo_user.png';
                }}
              />
              <span style={{
                ...checkAvatarStyles.confirmBadge,
                ...(prof.has_read ? checkAvatarStyles.confirmYes : checkAvatarStyles.confirmNo),
              }}>
                {prof.has_read ? '✓' : '⏳'}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <small style={{ color: '#94a3b8', fontSize: '10px' }}>-</small>
      )}
    </div>
  );
};

function TeamDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [member, setMember] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('info');

  // Clienti tab state
  const [clients, setClients] = useState([]);
  const [clientsLoading, setClientsLoading] = useState(false);
  const [clientsError, setClientsError] = useState(null);
  const [clientsPage, setClientsPage] = useState(1);
  const [clientsTotal, setClientsTotal] = useState(0);
  const [clientsTotalPages, setClientsTotalPages] = useState(0);
  const [clientsSearch, setClientsSearch] = useState('');
  const [clientsStato, setClientsStato] = useState('');
  const [hoveredRow, setHoveredRow] = useState(null);
  const PER_PAGE = 10;

  // Check tab state
  const [checksResponses, setChecksResponses] = useState([]);
  const [checksLoading, setChecksLoading] = useState(false);
  const [checksError, setChecksError] = useState(null);
  const [checksStats, setChecksStats] = useState(null);
  const [checksPeriod, setChecksPeriod] = useState('month');
  const [checksPage, setChecksPage] = useState(1);
  const [checksTotal, setChecksTotal] = useState(0);
  const [checksTotalPages, setChecksTotalPages] = useState(0);
  const [checksHoveredRow, setChecksHoveredRow] = useState(null);
  const [showCustomDates, setShowCustomDates] = useState(false);
  const [checksStartDate, setChecksStartDate] = useState('');
  const [checksEndDate, setChecksEndDate] = useState('');
  // Check detail modal
  const [showCheckModal, setShowCheckModal] = useState(false);
  const [selectedCheck, setSelectedCheck] = useState(null);
  const [loadingCheckDetail, setLoadingCheckDetail] = useState(false);
  const CHECKS_PER_PAGE = 10;

  // Training tab state
  const [trainingsReceived, setTrainingsReceived] = useState([]);
  const [trainingsGiven, setTrainingsGiven] = useState([]);
  const [trainingsLoading, setTrainingsLoading] = useState(false);
  const [trainingsError, setTrainingsError] = useState(null);
  const [trainingsGivenPage, setTrainingsGivenPage] = useState(1);
  const [trainingsReceivedPage, setTrainingsReceivedPage] = useState(1);
  const TRAININGS_PER_PAGE = 10;

  useEffect(() => {
    fetchMember();
  }, [id]);

  // Fetch clients when tab changes to 'clienti' or when filters change
  useEffect(() => {
    if (activeTab === 'clienti' && id) {
      fetchClients();
    }
  }, [activeTab, id, clientsPage, clientsStato]);

  // Debounced search
  useEffect(() => {
    if (activeTab !== 'clienti') return;
    const timer = setTimeout(() => {
      setClientsPage(1);
      fetchClients();
    }, 300);
    return () => clearTimeout(timer);
  }, [clientsSearch]);

  const fetchMember = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await teamService.getTeamMember(id);
      setMember(data);
    } catch (err) {
      console.error('Error fetching team member:', err);
      setError('Errore nel caricamento dei dati');
    } finally {
      setLoading(false);
    }
  };

  const fetchClients = async () => {
    setClientsLoading(true);
    setClientsError(null);
    try {
      const params = {
        page: clientsPage,
        per_page: PER_PAGE,
      };
      if (clientsSearch) params.q = clientsSearch;
      if (clientsStato) params.stato = clientsStato;

      const data = await teamService.getMemberClients(id, params);
      if (data.success) {
        setClients(data.clients || []);
        setClientsTotal(data.total || 0);
        setClientsTotalPages(data.total_pages || 0);
      } else {
        setClientsError('Errore nel caricamento dei clienti');
      }
    } catch (err) {
      console.error('Error fetching clients:', err);
      setClientsError('Errore nel caricamento dei clienti');
    } finally {
      setClientsLoading(false);
    }
  };

  const fetchChecks = async (customStart = null, customEnd = null) => {
    setChecksLoading(true);
    setChecksError(null);
    try {
      const params = {
        period: checksPeriod,
        page: checksPage,
        per_page: CHECKS_PER_PAGE,
      };
      if (checksPeriod === 'custom' && customStart && customEnd) {
        params.start_date = customStart;
        params.end_date = customEnd;
      }

      const data = await teamService.getMemberChecks(id, params);
      if (data.success) {
        setChecksResponses(data.responses || []);
        setChecksStats(data.stats || null);
        setChecksTotal(data.total || 0);
        setChecksTotalPages(data.total_pages || 0);
      } else {
        setChecksError('Errore nel caricamento dei check');
      }
    } catch (err) {
      console.error('Error fetching checks:', err);
      setChecksError('Errore nel caricamento dei check');
    } finally {
      setChecksLoading(false);
    }
  };

  // Fetch checks when tab changes to 'check' or when period/page changes
  useEffect(() => {
    if (activeTab === 'check' && id && checksPeriod !== 'custom') {
      fetchChecks();
    }
  }, [activeTab, id, checksPeriod, checksPage]);

  // Fetch trainings when tab changes to 'training'
  useEffect(() => {
    if (activeTab === 'training' && id) {
      fetchTrainings();
    }
  }, [activeTab, id]);

  const fetchTrainings = async () => {
    setTrainingsLoading(true);
    setTrainingsError(null);
    try {
      const data = await trainingService.getAdminUserTrainings(id);
      if (data.success) {
        setTrainingsReceived(data.trainings || []);
        setTrainingsGiven(data.givenTrainings || []);
      } else {
        setTrainingsError('Errore nel caricamento dei training');
      }
    } catch (err) {
      console.error('Error fetching trainings:', err);
      setTrainingsError('Errore nel caricamento dei training');
    } finally {
      setTrainingsLoading(false);
    }
  };

  const handleCheckPeriodChange = (newPeriod) => {
    setChecksPage(1);
    if (newPeriod === 'custom') {
      setShowCustomDates(true);
      setChecksPeriod('custom');
    } else {
      setShowCustomDates(false);
      setChecksPeriod(newPeriod);
    }
  };

  const handleApplyCustomDates = () => {
    if (checksStartDate && checksEndDate) {
      fetchChecks(checksStartDate, checksEndDate);
    }
  };

  const handleViewCheckResponse = async (response) => {
    setSelectedCheck({
      ...response,
      type: response.type || 'weekly',
    });
    setShowCheckModal(true);
    setLoadingCheckDetail(true);
    try {
      const result = await checkService.getResponseDetail(response.type || 'weekly', response.id);
      if (result.success) {
        setSelectedCheck({
          ...result.response,
          type: response.type || 'weekly',
          nutrizionisti: response.nutrizionisti,
          psicologi: response.psicologi,
          coaches: response.coaches,
        });
      }
    } catch (err) {
      console.error('Error fetching response detail:', err);
    } finally {
      setLoadingCheckDetail(false);
    }
  };

  const getInitials = (name) => {
    if (!name) return '??';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  };

  const handleToggleStatus = async () => {
    try {
      await teamService.toggleTeamMemberStatus(id);
      fetchMember();
    } catch (err) {
      console.error('Error toggling status:', err);
    }
  };

  // Helper per formattare le date
  const formatDate = (dateStr) => {
    if (!dateStr) return null;
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  // Render avatar team member
  const renderTeamAvatar = (member, roleKey, roleLabel) => {
    if (!member) return null;
    const colors = TEAM_ROLE_COLORS[roleKey] || TEAM_ROLE_COLORS.n;
    const initials = `${member.first_name?.[0] || ''}${member.last_name?.[0] || ''}`;

    return (
      <span
        key={`${roleKey}-${member.id}`}
        style={tableStyles.avatarTeam}
        title={`${roleLabel}: ${member.full_name || `${member.first_name} ${member.last_name}`}`}
      >
        {member.avatar_url || member.avatar_path ? (
          <img
            src={member.avatar_url || member.avatar_path}
            alt={member.full_name}
            style={{ ...tableStyles.avatarInitials, objectFit: 'cover' }}
          />
        ) : (
          <span
            style={{
              ...tableStyles.avatarInitials,
              background: colors.bg,
              color: colors.text,
            }}
          >
            {initials}
          </span>
        )}
        <span style={{ ...tableStyles.avatarBadge, background: colors.badge }}>
          {roleKey.toUpperCase()}
        </span>
      </span>
    );
  };

  const getRole = () => member?.role || 'professionista';
  const getSpecialty = () => member?.specialty;

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Caricamento...</span>
        </div>
      </div>
    );
  }

  if (error && !member) {
    return (
      <div className="alert alert-danger d-flex align-items-center">
        <i className="ri-error-warning-line me-2 fs-4"></i>
        <div className="flex-grow-1">{error}</div>
        <Link to="/team-lista" className="btn btn-sm btn-outline-danger">
          Torna alla Lista
        </Link>
      </div>
    );
  }

  const role = getRole();
  const specialty = getSpecialty();

  return (
    <>
      {/* Page Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1">Dettaglio Membro</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/team-lista">Team</Link>
              </li>
              <li className="breadcrumb-item active">{member?.full_name}</li>
            </ol>
          </nav>
        </div>
        <div className="d-flex gap-2">
          <Link to="/team-lista" className="btn btn-outline-secondary">
            <i className="ri-arrow-left-line me-1"></i>
            Torna alla Lista
          </Link>
          <Link to={`/team-modifica/${id}`} className="btn btn-primary">
            <i className="ri-edit-line me-1"></i>
            Modifica
          </Link>
        </div>
      </div>

      <div className="row g-4">
        {/* Profile Card with Gradient Header */}
        <div className="col-lg-4">
          <div className="card shadow-sm border-0 overflow-hidden">
            {/* Gradient Header */}
            <div
              className="position-relative"
              style={{
                background: ROLE_GRADIENTS[role] || ROLE_GRADIENTS.professionista,
                height: '120px'
              }}
            >
              {/* Status badges */}
              <div className="position-absolute top-0 start-0 p-3 d-flex gap-2">
                {member?.is_active ? (
                  <span className="badge bg-success">
                    <i className="ri-checkbox-circle-line me-1"></i>Attivo
                  </span>
                ) : (
                  <span className="badge bg-dark bg-opacity-75">
                    <i className="ri-close-circle-line me-1"></i>Inattivo
                  </span>
                )}
                {member?.is_external && (
                  <span className="badge bg-white text-dark">
                    <i className="ri-external-link-line me-1"></i>Esterno
                  </span>
                )}
              </div>

              {/* Avatar positioned at bottom */}
              <div className="position-absolute start-50 translate-middle-x" style={{ bottom: '-50px' }}>
                {member?.avatar_path ? (
                  <img
                    src={member.avatar_path}
                    alt={member.full_name}
                    className="rounded-circle border border-4 border-white shadow"
                    style={{ width: '100px', height: '100px', objectFit: 'cover', background: '#fff' }}
                  />
                ) : (
                  <div
                    className="rounded-circle border border-4 border-white shadow d-flex align-items-center justify-content-center"
                    style={{ width: '100px', height: '100px', background: '#fff' }}
                  >
                    <span className="fw-bold text-primary" style={{ fontSize: '2rem' }}>
                      {member?.first_name?.[0]?.toUpperCase()}{member?.last_name?.[0]?.toUpperCase()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Card Body */}
            <div className="card-body text-center pt-5 mt-3">
              <h4 className="mb-1">{member?.full_name}</h4>
              <p className="text-muted mb-3">{member?.email}</p>

              {/* Role & Specialty Badges */}
              <div className="d-flex justify-content-center gap-2 mb-4">
                <span className={`badge bg-${ROLE_COLORS[role] || 'secondary'}`}>
                  {ROLE_LABELS[role] || role}
                </span>
                {specialty && (
                  <span className={`badge bg-${SPECIALTY_COLORS[specialty] || 'secondary'}-subtle text-${SPECIALTY_COLORS[specialty] || 'secondary'}`}>
                    {SPECIALTY_LABELS[specialty] || specialty}
                  </span>
                )}
              </div>

              {/* Quick Stats */}
              <div className="row g-3 mb-4">
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">ID Utente</div>
                    <div className="fw-semibold">#{member?.id}</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">Team Guidati</div>
                    <div className="fw-semibold">{member?.teams_led?.length || 0}</div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="d-grid">
                <button
                  className={`btn ${member?.is_active ? 'btn-outline-danger' : 'btn-outline-success'}`}
                  onClick={handleToggleStatus}
                >
                  <i className={`ri-${member?.is_active ? 'user-unfollow' : 'user-follow'}-line me-2`}></i>
                  {member?.is_active ? 'Disattiva Account' : 'Attiva Account'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Details Section */}
        <div className="col-lg-8">
          <div className="card shadow-sm border-0">
            {/* Tabs Navigation */}
            <div className="card-header bg-transparent border-bottom p-0">
              <ul className="nav nav-tabs border-0">
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'info' ? 'active' : ''}`}
                    onClick={() => setActiveTab('info')}
                  >
                    <i className="ri-user-settings-line me-2"></i>
                    Informazioni
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'teams' ? 'active' : ''}`}
                    onClick={() => setActiveTab('teams')}
                  >
                    <i className="ri-team-line me-2"></i>
                    Team Guidati
                    {member?.teams_led?.length > 0 && (
                      <span className="badge bg-primary ms-2">{member.teams_led.length}</span>
                    )}
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'clienti' ? 'active' : ''}`}
                    onClick={() => setActiveTab('clienti')}
                  >
                    <i className="ri-user-heart-line me-2"></i>
                    Clienti
                    {clientsTotal > 0 && (
                      <span className="badge bg-primary ms-2">{clientsTotal}</span>
                    )}
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'check' ? 'active' : ''}`}
                    onClick={() => setActiveTab('check')}
                  >
                    <i className="ri-checkbox-multiple-line me-2"></i>
                    Check
                    {checksTotal > 0 && (
                      <span className="badge bg-primary ms-2">{checksTotal}</span>
                    )}
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'training' ? 'active' : ''}`}
                    onClick={() => setActiveTab('training')}
                  >
                    <i className="ri-presentation-line me-2"></i>
                    Training
                  </button>
                </li>
              </ul>
            </div>

            {/* Tab Content */}
            <div className="card-body">
              {/* Info Tab */}
              {activeTab === 'info' && (
                <div className="row g-4">
                  {/* Personal Info */}
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Dati Personali
                    </h6>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-primary-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-user-line text-primary"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Nome Completo</div>
                        <div className="fw-medium">{member?.full_name}</div>
                      </div>
                    </div>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-info-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-mail-line text-info"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Email</div>
                        <div className="fw-medium">{member?.email}</div>
                      </div>
                    </div>
                  </div>

                  {/* Account Info */}
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Dettagli Account
                    </h6>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-success-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-calendar-check-line text-success"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Data Creazione</div>
                        <div className="fw-medium">
                          {member?.created_at
                            ? new Date(member.created_at).toLocaleDateString('it-IT', {
                                day: 'numeric',
                                month: 'long',
                                year: 'numeric'
                              })
                            : '-'
                          }
                        </div>
                      </div>
                    </div>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-shield-user-line text-warning"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Ruolo</div>
                        <div className="fw-medium">{ROLE_LABELS[role] || role}</div>
                      </div>
                    </div>
                    {specialty && (
                      <div className="d-flex align-items-center mb-3">
                        <div className="flex-shrink-0">
                          <div className="bg-purple-subtle rounded-circle d-flex align-items-center justify-content-center"
                               style={{ width: '40px', height: '40px', background: '#e8daff' }}>
                            <i className="ri-stethoscope-line" style={{ color: '#7c3aed' }}></i>
                          </div>
                        </div>
                        <div className="flex-grow-1 ms-3">
                          <div className="text-muted small">Specializzazione</div>
                          <div className="fw-medium">{SPECIALTY_LABELS[specialty] || specialty}</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Teams Tab */}
              {activeTab === 'teams' && (
                <>
                  {member?.teams_led && member.teams_led.length > 0 ? (
                    <div className="list-group list-group-flush">
                      {member.teams_led.map((team) => (
                        <div key={team.id} className="list-group-item px-0 py-3">
                          <div className="d-flex align-items-center">
                            <div className="flex-shrink-0">
                              <div
                                className="rounded-circle d-flex align-items-center justify-content-center text-white"
                                style={{
                                  width: '48px',
                                  height: '48px',
                                  background: ROLE_GRADIENTS.team_leader
                                }}
                              >
                                <i className="ri-team-line fs-5"></i>
                              </div>
                            </div>
                            <div className="flex-grow-1 ms-3">
                              <h6 className="mb-0">{team.name}</h6>
                              <small className="text-muted">
                                <i className="ri-shield-star-line me-1"></i>
                                Team Leader
                              </small>
                            </div>
                            <div className="d-flex gap-2">
                              <Link
                                to={`/teams-dettaglio/${team.id}`}
                                className="btn btn-sm btn-outline-primary"
                              >
                                <i className="ri-eye-line me-1"></i>
                                Dettagli
                              </Link>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-5">
                      <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                           style={{ width: '64px', height: '64px' }}>
                        <i className="ri-team-line text-muted fs-3"></i>
                      </div>
                      <p className="text-muted mb-0">Questo membro non guida nessun team</p>
                    </div>
                  )}
                </>
              )}

              {/* Clienti Tab */}
              {activeTab === 'clienti' && (
                <div>
                  {/* Filters */}
                  <div className="d-flex flex-wrap gap-3 mb-4">
                    {/* Search */}
                    <div className="flex-grow-1" style={{ maxWidth: '300px' }}>
                      <div className="position-relative">
                        <i className="ri-search-line position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}></i>
                        <input
                          type="text"
                          className="form-control bg-light border-0"
                          placeholder="Cerca paziente..."
                          value={clientsSearch}
                          onChange={(e) => setClientsSearch(e.target.value)}
                          style={{ paddingLeft: '36px' }}
                        />
                      </div>
                    </div>

                    {/* Stato Filter */}
                    <select
                      className="form-select bg-light border-0"
                      style={{ width: 'auto', minWidth: '150px' }}
                      value={clientsStato}
                      onChange={(e) => {
                        setClientsStato(e.target.value);
                        setClientsPage(1);
                      }}
                    >
                      <option value="">Tutti gli stati</option>
                      {Object.entries(STATO_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>

                    {/* Total count */}
                    <div className="d-flex align-items-center ms-auto">
                      <span className="badge bg-primary-subtle text-primary px-3 py-2">
                        {clientsTotal} pazient{clientsTotal !== 1 ? 'i' : 'e'}
                      </span>
                    </div>
                  </div>

                  {/* Loading */}
                  {clientsLoading && (
                    <div className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Caricamento...</span>
                      </div>
                    </div>
                  )}

                  {/* Error */}
                  {clientsError && !clientsLoading && (
                    <div className="alert alert-danger">
                      <i className="ri-error-warning-line me-2"></i>
                      {clientsError}
                    </div>
                  )}

                  {/* Empty State */}
                  {!clientsLoading && !clientsError && clients.length === 0 && (
                    <div className="text-center py-5">
                      <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                           style={{ width: '64px', height: '64px' }}>
                        <i className="ri-user-heart-line text-muted fs-3"></i>
                      </div>
                      <p className="text-muted mb-0">
                        {clientsSearch || clientsStato
                          ? 'Nessun paziente trovato con i filtri selezionati'
                          : 'Nessun paziente associato a questo professionista'}
                      </p>
                    </div>
                  )}

                  {/* Clients Table */}
                  {!clientsLoading && !clientsError && clients.length > 0 && (
                    <>
                      <div className="table-responsive" style={{ margin: '0 -1rem' }}>
                        <table className="table mb-0">
                          <thead style={tableStyles.tableHeader}>
                            <tr>
                              <th style={{ ...tableStyles.th, minWidth: '180px' }}>Nome Cognome</th>
                              <th style={{ ...tableStyles.th, minWidth: '100px' }}>Team</th>
                              <th style={{ ...tableStyles.th, minWidth: '100px' }}>Data Inizio</th>
                              <th style={{ ...tableStyles.th, minWidth: '100px' }}>Data Rinnovo</th>
                              <th style={{ ...tableStyles.th, minWidth: '120px' }}>Programma</th>
                              <th style={{ ...tableStyles.th, minWidth: '100px' }}>Stato</th>
                              <th style={{ ...tableStyles.th, textAlign: 'right', minWidth: '80px' }}>Azioni</th>
                            </tr>
                          </thead>
                          <tbody>
                            {clients.map((cliente, index) => {
                              const clienteId = cliente.cliente_id || cliente.clienteId || cliente.id;
                              const nomeCognome = cliente.nome_cognome || cliente.nomeCognome || cliente.full_name || 'N/D';
                              const dataInizio = cliente.data_inizio_abbonamento || cliente.dataInizioAbbonamento;
                              const dataRinnovo = cliente.data_rinnovo || cliente.dataRinnovo;
                              const programma = cliente.programma_attuale || cliente.programmaAttuale || cliente.storico_programma || cliente.storicoProgramma;
                              const statoCliente = cliente.stato_cliente || cliente.statoCliente;

                              // Team members
                              const healthManager = cliente.health_manager_user || cliente.healthManagerUser;
                              const nutrizionistiList = cliente.nutrizionisti_multipli || cliente.nutrizionistiMultipli || [];
                              const coachesList = cliente.coaches_multipli || cliente.coachesMultipli || [];
                              const psicologiList = cliente.psicologi_multipli || cliente.psicologiMultipli || [];
                              const consulentiList = cliente.consulenti_multipli || cliente.consulentiMultipli || [];

                              const hasTeam = healthManager || nutrizionistiList.length > 0 || coachesList.length > 0 || psicologiList.length > 0 || consulentiList.length > 0;

                              const isHovered = hoveredRow === index;

                              return (
                                <tr
                                  key={clienteId}
                                  style={{
                                    ...tableStyles.row,
                                    background: isHovered ? '#f8fafc' : 'transparent',
                                  }}
                                  onMouseEnter={() => setHoveredRow(index)}
                                  onMouseLeave={() => setHoveredRow(null)}
                                >
                                  {/* Nome Cognome */}
                                  <td style={tableStyles.td}>
                                    <Link
                                      to={`/clienti-dettaglio/${clienteId}`}
                                      style={tableStyles.nameLink}
                                      onMouseOver={(e) => e.currentTarget.style.color = '#2563eb'}
                                      onMouseOut={(e) => e.currentTarget.style.color = '#3b82f6'}
                                    >
                                      {nomeCognome}
                                    </Link>
                                  </td>

                                  {/* Team */}
                                  <td style={tableStyles.td}>
                                    <div className="d-flex align-items-center flex-wrap">
                                      {healthManager && renderTeamAvatar(healthManager, 'hm', 'Health Manager')}
                                      {nutrizionistiList.map(n => renderTeamAvatar(n, 'n', 'Nutrizionista'))}
                                      {coachesList.map(c => renderTeamAvatar(c, 'c', 'Coach'))}
                                      {psicologiList.map(p => renderTeamAvatar(p, 'p', 'Psicologo'))}
                                      {consulentiList.map(ca => renderTeamAvatar(ca, 'ca', 'Consulente'))}
                                      {!hasTeam && <span style={tableStyles.emptyCell}>—</span>}
                                    </div>
                                  </td>

                                  {/* Data Inizio */}
                                  <td style={tableStyles.td}>
                                    {dataInizio ? (
                                      <span style={{ fontWeight: 500 }}>{formatDate(dataInizio)}</span>
                                    ) : (
                                      <span style={tableStyles.emptyCell}>—</span>
                                    )}
                                  </td>

                                  {/* Data Rinnovo */}
                                  <td style={tableStyles.td}>
                                    {dataRinnovo ? (
                                      <span style={{ fontWeight: 500 }}>{formatDate(dataRinnovo)}</span>
                                    ) : (
                                      <span style={tableStyles.emptyCell}>—</span>
                                    )}
                                  </td>

                                  {/* Programma */}
                                  <td style={tableStyles.td}>
                                    {programma ? (
                                      <span
                                        style={{
                                          ...tableStyles.badge,
                                          background: 'linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)',
                                          color: '#0369a1',
                                        }}
                                      >
                                        {programma}
                                      </span>
                                    ) : (
                                      <span style={tableStyles.emptyCell}>—</span>
                                    )}
                                  </td>

                                  {/* Stato Cliente */}
                                  <td style={tableStyles.td}>
                                    {statoCliente ? (
                                      <span
                                        style={{
                                          ...tableStyles.badge,
                                          ...(STATO_BADGE_STYLES[statoCliente] || { background: '#94a3b8', color: '#fff' }),
                                        }}
                                      >
                                        {STATO_LABELS[statoCliente] || statoCliente}
                                      </span>
                                    ) : (
                                      <span style={tableStyles.emptyCell}>—</span>
                                    )}
                                  </td>

                                  {/* Azioni */}
                                  <td style={{ ...tableStyles.td, textAlign: 'right' }}>
                                    <Link
                                      to={`/clienti-dettaglio/${clienteId}`}
                                      style={{
                                        ...tableStyles.actionBtn,
                                        borderColor: '#22c55e',
                                        color: '#22c55e',
                                        background: isHovered ? 'rgba(34, 197, 94, 0.1)' : 'transparent',
                                      }}
                                      title="Dettaglio"
                                    >
                                      <i className="ri-eye-line" style={{ fontSize: '14px' }}></i>
                                    </Link>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>

                      {/* Pagination */}
                      {clientsTotalPages > 1 && (
                        <div className="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                          <span style={{ color: '#64748b', fontSize: '14px' }}>
                            Pagina <strong style={{ color: '#334155' }}>{clientsPage}</strong> di{' '}
                            <strong style={{ color: '#334155' }}>{clientsTotalPages}</strong>
                            <span className="ms-2" style={{ color: '#94a3b8' }}>•</span>
                            <span className="ms-2">{clientsTotal} risultati</span>
                          </span>
                          <nav>
                            <ul className="pagination mb-0" style={{ gap: '4px' }}>
                              {/* Prev */}
                              <li className={`page-item ${clientsPage === 1 ? 'disabled' : ''}`}>
                                <button
                                  className="page-link"
                                  onClick={() => setClientsPage(p => Math.max(1, p - 1))}
                                  disabled={clientsPage === 1}
                                  style={{
                                    borderRadius: '8px',
                                    border: '1px solid #e2e8f0',
                                    color: clientsPage === 1 ? '#cbd5e1' : '#64748b',
                                    padding: '8px 12px',
                                  }}
                                >
                                  <i className="ri-arrow-left-s-line"></i>
                                </button>
                              </li>
                              {/* Page numbers */}
                              {[...Array(Math.min(clientsTotalPages, 5))].map((_, i) => {
                                let pageNum;
                                if (clientsTotalPages <= 5) {
                                  pageNum = i + 1;
                                } else if (clientsPage <= 3) {
                                  pageNum = i + 1;
                                } else if (clientsPage >= clientsTotalPages - 2) {
                                  pageNum = clientsTotalPages - 4 + i;
                                } else {
                                  pageNum = clientsPage - 2 + i;
                                }
                                const isActive = clientsPage === pageNum;
                                return (
                                  <li key={pageNum} className="page-item">
                                    <button
                                      className="page-link"
                                      onClick={() => setClientsPage(pageNum)}
                                      style={{
                                        borderRadius: '8px',
                                        border: isActive ? 'none' : '1px solid #e2e8f0',
                                        background: isActive ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' : 'transparent',
                                        color: isActive ? '#fff' : '#64748b',
                                        padding: '8px 14px',
                                        fontWeight: isActive ? 600 : 400,
                                        minWidth: '40px',
                                      }}
                                    >
                                      {pageNum}
                                    </button>
                                  </li>
                                );
                              })}
                              {/* Next */}
                              <li className={`page-item ${clientsPage === clientsTotalPages ? 'disabled' : ''}`}>
                                <button
                                  className="page-link"
                                  onClick={() => setClientsPage(p => Math.min(clientsTotalPages, p + 1))}
                                  disabled={clientsPage === clientsTotalPages}
                                  style={{
                                    borderRadius: '8px',
                                    border: '1px solid #e2e8f0',
                                    color: clientsPage === clientsTotalPages ? '#cbd5e1' : '#64748b',
                                    padding: '8px 12px',
                                  }}
                                >
                                  <i className="ri-arrow-right-s-line"></i>
                                </button>
                              </li>
                            </ul>
                          </nav>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Check Tab */}
              {activeTab === 'check' && (
                <div>
                  {/* Period Filters & KPIs */}
                  <div className="mb-4">
                    <div className="d-flex flex-wrap gap-3 align-items-center justify-content-between">
                      {/* Period Buttons */}
                      <div className="d-flex gap-2 flex-wrap">
                        {[
                          { key: 'week', label: 'Settimana' },
                          { key: 'month', label: 'Mese' },
                          { key: 'trimester', label: 'Trimestre' },
                          { key: 'year', label: 'Anno' },
                          { key: 'custom', label: 'Custom', icon: 'ri-calendar-2-line' },
                        ].map((p) => (
                          <button
                            key={p.key}
                            className="btn"
                            onClick={() => handleCheckPeriodChange(p.key)}
                            disabled={checksLoading}
                            style={{
                              height: '38px',
                              borderRadius: '10px',
                              border: checksPeriod === p.key ? 'none' : '1px solid #e2e8f0',
                              background: checksPeriod === p.key
                                ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
                                : '#f8fafc',
                              color: checksPeriod === p.key ? 'white' : '#64748b',
                              fontSize: '13px',
                              fontWeight: checksPeriod === p.key ? 600 : 400,
                              padding: '0 12px',
                              transition: 'all 0.15s ease',
                            }}
                          >
                            {p.icon && <i className={`${p.icon} me-1`}></i>}
                            {p.label}
                          </button>
                        ))}
                      </div>

                      {/* KPI Averages */}
                      <div className="d-flex flex-wrap gap-2 align-items-center">
                        <div className="d-flex align-items-center gap-1">
                          <i className="ri-restaurant-line text-success" style={{ fontSize: '16px' }}></i>
                          <span style={getKpiBadgeStyle(checksStats?.avg_nutrizionista)}>
                            {checksStats?.avg_nutrizionista ?? '-'}
                          </span>
                        </div>
                        <div className="d-flex align-items-center gap-1">
                          <i className="ri-mental-health-line text-info" style={{ fontSize: '16px' }}></i>
                          <span style={getKpiBadgeStyle(checksStats?.avg_psicologo)}>
                            {checksStats?.avg_psicologo ?? '-'}
                          </span>
                        </div>
                        <div className="d-flex align-items-center gap-1">
                          <i className="ri-run-line text-primary" style={{ fontSize: '16px' }}></i>
                          <span style={getKpiBadgeStyle(checksStats?.avg_coach)}>
                            {checksStats?.avg_coach ?? '-'}
                          </span>
                        </div>
                        <div className="d-flex align-items-center gap-1">
                          <i className="ri-star-fill text-warning" style={{ fontSize: '16px' }}></i>
                          <span style={getKpiBadgeStyle(checksStats?.avg_quality)}>
                            {checksStats?.avg_quality ?? '-'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Custom Date Range */}
                    {showCustomDates && (
                      <div className="mt-3 pt-3 border-top">
                        <div className="d-flex flex-wrap gap-3 align-items-end">
                          <div>
                            <label className="form-label small text-muted mb-1">Data Inizio</label>
                            <input
                              type="date"
                              className="form-control"
                              value={checksStartDate}
                              onChange={(e) => setChecksStartDate(e.target.value)}
                              style={{
                                height: '38px',
                                borderRadius: '10px',
                                border: '1px solid #e2e8f0',
                                background: '#f8fafc',
                                fontSize: '13px',
                                minWidth: '140px',
                              }}
                            />
                          </div>
                          <div>
                            <label className="form-label small text-muted mb-1">Data Fine</label>
                            <input
                              type="date"
                              className="form-control"
                              value={checksEndDate}
                              onChange={(e) => setChecksEndDate(e.target.value)}
                              style={{
                                height: '38px',
                                borderRadius: '10px',
                                border: '1px solid #e2e8f0',
                                background: '#f8fafc',
                                fontSize: '13px',
                                minWidth: '140px',
                              }}
                            />
                          </div>
                          <button
                            className="btn"
                            onClick={handleApplyCustomDates}
                            disabled={!checksStartDate || !checksEndDate || checksLoading}
                            style={{
                              height: '38px',
                              borderRadius: '10px',
                              background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                              color: 'white',
                              fontWeight: 600,
                              padding: '0 20px',
                              border: 'none',
                            }}
                          >
                            <i className="ri-search-line me-1"></i>
                            Applica
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Loading */}
                  {checksLoading && (
                    <div className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Caricamento...</span>
                      </div>
                    </div>
                  )}

                  {/* Error */}
                  {checksError && !checksLoading && (
                    <div className="alert alert-danger">
                      <i className="ri-error-warning-line me-2"></i>
                      {checksError}
                    </div>
                  )}

                  {/* Empty State */}
                  {!checksLoading && !checksError && checksResponses.length === 0 && (
                    <div className="text-center py-5">
                      <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                           style={{ width: '64px', height: '64px' }}>
                        <i className="ri-checkbox-multiple-line text-muted fs-3"></i>
                      </div>
                      <p className="text-muted mb-0">Nessun check trovato per il periodo selezionato</p>
                    </div>
                  )}

                  {/* Checks Table */}
                  {!checksLoading && !checksError && checksResponses.length > 0 && (
                    <>
                      <div className="table-responsive" style={{ margin: '0 -1rem' }}>
                        <table className="table mb-0">
                          <thead style={tableStyles.tableHeader}>
                            <tr>
                              <th style={{ ...tableStyles.th, minWidth: '180px' }}>Cliente</th>
                              <th style={{ ...tableStyles.th, minWidth: '100px' }}>Data</th>
                              <th style={{ ...tableStyles.th, minWidth: '100px', textAlign: 'center' }}>Nutrizionista</th>
                              <th style={{ ...tableStyles.th, minWidth: '100px', textAlign: 'center' }}>Psicologo/a</th>
                              <th style={{ ...tableStyles.th, minWidth: '100px', textAlign: 'center' }}>Coach</th>
                              <th style={{ ...tableStyles.th, minWidth: '80px', textAlign: 'center' }}>Progresso</th>
                            </tr>
                          </thead>
                          <tbody>
                            {checksResponses.map((response, index) => {
                              const isHovered = checksHoveredRow === index;
                              return (
                                <tr
                                  key={`${response.type}-${response.id}`}
                                  style={{
                                    ...tableStyles.row,
                                    background: isHovered ? '#f8fafc' : 'transparent',
                                    cursor: 'pointer',
                                  }}
                                  onMouseEnter={() => setChecksHoveredRow(index)}
                                  onMouseLeave={() => setChecksHoveredRow(null)}
                                  onClick={() => handleViewCheckResponse(response)}
                                >
                                  {/* Cliente */}
                                  <td style={tableStyles.td}>
                                    <div className="d-flex align-items-center gap-2">
                                      <Link
                                        to={`/clienti-dettaglio/${response.cliente_id}`}
                                        className="text-decoration-none"
                                        onClick={(e) => e.stopPropagation()}
                                        style={{
                                          color: '#3b82f6',
                                          fontWeight: 600,
                                          fontSize: '14px',
                                        }}
                                        onMouseOver={(e) => e.currentTarget.style.color = '#2563eb'}
                                        onMouseOut={(e) => e.currentTarget.style.color = '#3b82f6'}
                                      >
                                        {response.cliente_nome || 'Cliente'}
                                      </Link>
                                      {response.type === 'dca' && (
                                        <span
                                          style={{
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '4px',
                                            padding: '2px 6px',
                                            borderRadius: '4px',
                                            fontSize: '9px',
                                            fontWeight: 600,
                                            background: 'linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)',
                                            color: '#0369a1',
                                          }}
                                        >
                                          <i className="ri-heart-pulse-line"></i> DCA
                                        </span>
                                      )}
                                    </div>
                                  </td>

                                  {/* Data */}
                                  <td style={tableStyles.td}>
                                    <span style={{ fontWeight: 500 }}>
                                      {response.submit_date || '-'}
                                    </span>
                                  </td>

                                  {/* Nutrizionista */}
                                  <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                    <ProfessionalCell
                                      professionals={response.nutrizionisti}
                                      rating={response.nutritionist_rating}
                                    />
                                  </td>

                                  {/* Psicologo */}
                                  <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                    <ProfessionalCell
                                      professionals={response.psicologi}
                                      rating={response.psychologist_rating}
                                    />
                                  </td>

                                  {/* Coach */}
                                  <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                    <ProfessionalCell
                                      professionals={response.coaches}
                                      rating={response.coach_rating}
                                    />
                                  </td>

                                  {/* Progresso */}
                                  <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                    <span style={getRatingStyle(response.progress_rating)}>
                                      {response.progress_rating ?? '-'}
                                    </span>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>

                      {/* Pagination */}
                      {checksTotalPages > 1 && (
                        <div className="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                          <span style={{ color: '#64748b', fontSize: '14px' }}>
                            Pagina <strong style={{ color: '#334155' }}>{checksPage}</strong> di{' '}
                            <strong style={{ color: '#334155' }}>{checksTotalPages}</strong>
                            <span className="ms-2" style={{ color: '#94a3b8' }}>•</span>
                            <span className="ms-2">{checksTotal} risultati</span>
                          </span>
                          <nav>
                            <ul className="pagination mb-0" style={{ gap: '4px' }}>
                              <li className={`page-item ${checksPage === 1 ? 'disabled' : ''}`}>
                                <button
                                  className="page-link"
                                  onClick={() => setChecksPage(p => Math.max(1, p - 1))}
                                  disabled={checksPage === 1}
                                  style={{
                                    borderRadius: '8px',
                                    border: '1px solid #e2e8f0',
                                    color: checksPage === 1 ? '#cbd5e1' : '#64748b',
                                    padding: '8px 12px',
                                  }}
                                >
                                  <i className="ri-arrow-left-s-line"></i>
                                </button>
                              </li>
                              {[...Array(Math.min(checksTotalPages, 5))].map((_, i) => {
                                let pageNum;
                                if (checksTotalPages <= 5) {
                                  pageNum = i + 1;
                                } else if (checksPage <= 3) {
                                  pageNum = i + 1;
                                } else if (checksPage >= checksTotalPages - 2) {
                                  pageNum = checksTotalPages - 4 + i;
                                } else {
                                  pageNum = checksPage - 2 + i;
                                }
                                const isActive = checksPage === pageNum;
                                return (
                                  <li key={pageNum} className="page-item">
                                    <button
                                      className="page-link"
                                      onClick={() => setChecksPage(pageNum)}
                                      style={{
                                        borderRadius: '8px',
                                        border: isActive ? 'none' : '1px solid #e2e8f0',
                                        background: isActive ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' : 'transparent',
                                        color: isActive ? '#fff' : '#64748b',
                                        padding: '8px 14px',
                                        fontWeight: isActive ? 600 : 400,
                                        minWidth: '40px',
                                      }}
                                    >
                                      {pageNum}
                                    </button>
                                  </li>
                                );
                              })}
                              <li className={`page-item ${checksPage === checksTotalPages ? 'disabled' : ''}`}>
                                <button
                                  className="page-link"
                                  onClick={() => setChecksPage(p => Math.min(checksTotalPages, p + 1))}
                                  disabled={checksPage === checksTotalPages}
                                  style={{
                                    borderRadius: '8px',
                                    border: '1px solid #e2e8f0',
                                    color: checksPage === checksTotalPages ? '#cbd5e1' : '#64748b',
                                    padding: '8px 12px',
                                  }}
                                >
                                  <i className="ri-arrow-right-s-line"></i>
                                </button>
                              </li>
                            </ul>
                          </nav>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Training Tab */}
              {activeTab === 'training' && (
                <div>
                  {/* Loading */}
                  {trainingsLoading && (
                    <div className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Caricamento...</span>
                      </div>
                    </div>
                  )}

                  {/* Error */}
                  {trainingsError && !trainingsLoading && (
                    <div className="alert alert-danger">
                      <i className="ri-error-warning-line me-2"></i>
                      {trainingsError}
                    </div>
                  )}

                  {!trainingsLoading && !trainingsError && (
                    <>
                      {/* Training Erogati */}
                      <div className="mb-5">
                        <div className="d-flex align-items-center justify-content-between mb-3">
                          <h6 className="text-uppercase text-muted small fw-semibold mb-0">
                            <i className="ri-slideshow-3-line me-2"></i>
                            Training Erogati
                          </h6>
                          <span className="badge bg-success-subtle text-success px-3 py-2">
                            {trainingsGiven.length} training
                          </span>
                        </div>

                        {trainingsGiven.length === 0 ? (
                          <div className="text-center py-4 rounded-3" style={{ background: '#f8fafc' }}>
                            <i className="ri-slideshow-3-line text-muted" style={{ fontSize: '28px' }}></i>
                            <p className="text-muted mb-0 mt-2 small">Nessun training erogato</p>
                          </div>
                        ) : (
                          <>
                            <div className="table-responsive" style={{ margin: '0 -1rem' }}>
                              <table className="table mb-0">
                                <thead style={tableStyles.tableHeader}>
                                  <tr>
                                    <th style={{ ...tableStyles.th, minWidth: '200px' }}>Titolo</th>
                                    <th style={{ ...tableStyles.th, minWidth: '120px' }}>Data</th>
                                    <th style={{ ...tableStyles.th, minWidth: '140px' }}>Destinatario</th>
                                    <th style={{ ...tableStyles.th, minWidth: '100px' }}>Tipo</th>
                                    <th style={{ ...tableStyles.th, minWidth: '100px' }}>Stato</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {trainingsGiven.slice((trainingsGivenPage - 1) * TRAININGS_PER_PAGE, trainingsGivenPage * TRAININGS_PER_PAGE).map((training) => (
                                    <tr key={training.id} style={tableStyles.row}>
                                      <td style={tableStyles.td}>
                                        <span style={{ fontWeight: 600, color: '#334155' }}>{training.title}</span>
                                      </td>
                                      <td style={tableStyles.td}>
                                        <span style={{ fontWeight: 500 }}>{formatDate(training.createdAt)}</span>
                                      </td>
                                      <td style={tableStyles.td}>
                                        {training.reviewee ? (
                                          <span style={{ fontWeight: 500 }}>{training.reviewee.firstName} {training.reviewee.lastName}</span>
                                        ) : (
                                          <span style={tableStyles.emptyCell}>—</span>
                                        )}
                                      </td>
                                      <td style={tableStyles.td}>
                                        <span className="badge" style={{ ...tableStyles.badge, background: '#e0f2fe', color: '#0369a1' }}>
                                          {training.reviewType || 'general'}
                                        </span>
                                      </td>
                                      <td style={tableStyles.td}>
                                        {training.isDraft ? (
                                          <span className="badge" style={{ ...tableStyles.badge, background: '#f1f5f9', color: '#64748b' }}>Bozza</span>
                                        ) : training.isAcknowledged ? (
                                          <span className="badge" style={{ ...tableStyles.badge, background: '#dcfce7', color: '#166534' }}>Confermato</span>
                                        ) : (
                                          <span className="badge" style={{ ...tableStyles.badge, background: '#fef3c7', color: '#92400e' }}>In attesa</span>
                                        )}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            {Math.ceil(trainingsGiven.length / TRAININGS_PER_PAGE) > 1 && (
                              <div className="d-flex justify-content-between align-items-center mt-3 pt-3 border-top">
                                <span style={{ color: '#64748b', fontSize: '14px' }}>
                                  Pagina <strong style={{ color: '#334155' }}>{trainingsGivenPage}</strong> di{' '}
                                  <strong style={{ color: '#334155' }}>{Math.ceil(trainingsGiven.length / TRAININGS_PER_PAGE)}</strong>
                                </span>
                                <nav>
                                  <ul className="pagination mb-0" style={{ gap: '4px' }}>
                                    <li className={`page-item ${trainingsGivenPage === 1 ? 'disabled' : ''}`}>
                                      <button className="page-link" onClick={() => setTrainingsGivenPage(p => Math.max(1, p - 1))} disabled={trainingsGivenPage === 1} style={{ borderRadius: '8px', border: '1px solid #e2e8f0', color: trainingsGivenPage === 1 ? '#cbd5e1' : '#64748b', padding: '8px 12px' }}>
                                        <i className="ri-arrow-left-s-line"></i>
                                      </button>
                                    </li>
                                    {[...Array(Math.min(Math.ceil(trainingsGiven.length / TRAININGS_PER_PAGE), 5))].map((_, i) => {
                                      const totalPages = Math.ceil(trainingsGiven.length / TRAININGS_PER_PAGE);
                                      let pageNum;
                                      if (totalPages <= 5) { pageNum = i + 1; }
                                      else if (trainingsGivenPage <= 3) { pageNum = i + 1; }
                                      else if (trainingsGivenPage >= totalPages - 2) { pageNum = totalPages - 4 + i; }
                                      else { pageNum = trainingsGivenPage - 2 + i; }
                                      const isActive = trainingsGivenPage === pageNum;
                                      return (
                                        <li key={pageNum} className="page-item">
                                          <button className="page-link" onClick={() => setTrainingsGivenPage(pageNum)} style={{ borderRadius: '8px', border: isActive ? 'none' : '1px solid #e2e8f0', background: isActive ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' : 'transparent', color: isActive ? '#fff' : '#64748b', padding: '8px 14px', fontWeight: isActive ? 600 : 400, minWidth: '40px' }}>
                                            {pageNum}
                                          </button>
                                        </li>
                                      );
                                    })}
                                    <li className={`page-item ${trainingsGivenPage >= Math.ceil(trainingsGiven.length / TRAININGS_PER_PAGE) ? 'disabled' : ''}`}>
                                      <button className="page-link" onClick={() => setTrainingsGivenPage(p => Math.min(Math.ceil(trainingsGiven.length / TRAININGS_PER_PAGE), p + 1))} disabled={trainingsGivenPage >= Math.ceil(trainingsGiven.length / TRAININGS_PER_PAGE)} style={{ borderRadius: '8px', border: '1px solid #e2e8f0', color: trainingsGivenPage >= Math.ceil(trainingsGiven.length / TRAININGS_PER_PAGE) ? '#cbd5e1' : '#64748b', padding: '8px 12px' }}>
                                        <i className="ri-arrow-right-s-line"></i>
                                      </button>
                                    </li>
                                  </ul>
                                </nav>
                              </div>
                            )}
                          </>
                        )}
                      </div>

                      {/* Training Ricevuti */}
                      <div>
                        <div className="d-flex align-items-center justify-content-between mb-3">
                          <h6 className="text-uppercase text-muted small fw-semibold mb-0">
                            <i className="ri-book-open-line me-2"></i>
                            Training Ricevuti
                          </h6>
                          <span className="badge bg-primary-subtle text-primary px-3 py-2">
                            {trainingsReceived.length} training
                          </span>
                        </div>

                        {trainingsReceived.length === 0 ? (
                          <div className="text-center py-4 rounded-3" style={{ background: '#f8fafc' }}>
                            <i className="ri-book-open-line text-muted" style={{ fontSize: '28px' }}></i>
                            <p className="text-muted mb-0 mt-2 small">Nessun training ricevuto</p>
                          </div>
                        ) : (
                          <>
                            <div className="table-responsive" style={{ margin: '0 -1rem' }}>
                              <table className="table mb-0">
                                <thead style={tableStyles.tableHeader}>
                                  <tr>
                                    <th style={{ ...tableStyles.th, minWidth: '200px' }}>Titolo</th>
                                    <th style={{ ...tableStyles.th, minWidth: '120px' }}>Data</th>
                                    <th style={{ ...tableStyles.th, minWidth: '140px' }}>Erogato da</th>
                                    <th style={{ ...tableStyles.th, minWidth: '100px' }}>Tipo</th>
                                    <th style={{ ...tableStyles.th, minWidth: '100px' }}>Stato</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {trainingsReceived.slice((trainingsReceivedPage - 1) * TRAININGS_PER_PAGE, trainingsReceivedPage * TRAININGS_PER_PAGE).map((training) => (
                                    <tr key={training.id} style={tableStyles.row}>
                                      <td style={tableStyles.td}>
                                        <span style={{ fontWeight: 600, color: '#334155' }}>{training.title}</span>
                                      </td>
                                      <td style={tableStyles.td}>
                                        <span style={{ fontWeight: 500 }}>{formatDate(training.createdAt)}</span>
                                      </td>
                                      <td style={tableStyles.td}>
                                        {training.reviewer ? (
                                          <span style={{ fontWeight: 500 }}>{training.reviewer.firstName} {training.reviewer.lastName}</span>
                                        ) : (
                                          <span style={tableStyles.emptyCell}>—</span>
                                        )}
                                      </td>
                                      <td style={tableStyles.td}>
                                        <span className="badge" style={{ ...tableStyles.badge, background: '#e0f2fe', color: '#0369a1' }}>
                                          {training.reviewType || 'general'}
                                        </span>
                                      </td>
                                      <td style={tableStyles.td}>
                                        {training.isAcknowledged ? (
                                          <span className="badge" style={{ ...tableStyles.badge, background: '#dcfce7', color: '#166534' }}>Confermato</span>
                                        ) : (
                                          <span className="badge" style={{ ...tableStyles.badge, background: '#fef3c7', color: '#92400e' }}>In attesa</span>
                                        )}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            {Math.ceil(trainingsReceived.length / TRAININGS_PER_PAGE) > 1 && (
                              <div className="d-flex justify-content-between align-items-center mt-3 pt-3 border-top">
                                <span style={{ color: '#64748b', fontSize: '14px' }}>
                                  Pagina <strong style={{ color: '#334155' }}>{trainingsReceivedPage}</strong> di{' '}
                                  <strong style={{ color: '#334155' }}>{Math.ceil(trainingsReceived.length / TRAININGS_PER_PAGE)}</strong>
                                </span>
                                <nav>
                                  <ul className="pagination mb-0" style={{ gap: '4px' }}>
                                    <li className={`page-item ${trainingsReceivedPage === 1 ? 'disabled' : ''}`}>
                                      <button className="page-link" onClick={() => setTrainingsReceivedPage(p => Math.max(1, p - 1))} disabled={trainingsReceivedPage === 1} style={{ borderRadius: '8px', border: '1px solid #e2e8f0', color: trainingsReceivedPage === 1 ? '#cbd5e1' : '#64748b', padding: '8px 12px' }}>
                                        <i className="ri-arrow-left-s-line"></i>
                                      </button>
                                    </li>
                                    {[...Array(Math.min(Math.ceil(trainingsReceived.length / TRAININGS_PER_PAGE), 5))].map((_, i) => {
                                      const totalPages = Math.ceil(trainingsReceived.length / TRAININGS_PER_PAGE);
                                      let pageNum;
                                      if (totalPages <= 5) { pageNum = i + 1; }
                                      else if (trainingsReceivedPage <= 3) { pageNum = i + 1; }
                                      else if (trainingsReceivedPage >= totalPages - 2) { pageNum = totalPages - 4 + i; }
                                      else { pageNum = trainingsReceivedPage - 2 + i; }
                                      const isActive = trainingsReceivedPage === pageNum;
                                      return (
                                        <li key={pageNum} className="page-item">
                                          <button className="page-link" onClick={() => setTrainingsReceivedPage(pageNum)} style={{ borderRadius: '8px', border: isActive ? 'none' : '1px solid #e2e8f0', background: isActive ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' : 'transparent', color: isActive ? '#fff' : '#64748b', padding: '8px 14px', fontWeight: isActive ? 600 : 400, minWidth: '40px' }}>
                                            {pageNum}
                                          </button>
                                        </li>
                                      );
                                    })}
                                    <li className={`page-item ${trainingsReceivedPage >= Math.ceil(trainingsReceived.length / TRAININGS_PER_PAGE) ? 'disabled' : ''}`}>
                                      <button className="page-link" onClick={() => setTrainingsReceivedPage(p => Math.min(Math.ceil(trainingsReceived.length / TRAININGS_PER_PAGE), p + 1))} disabled={trainingsReceivedPage >= Math.ceil(trainingsReceived.length / TRAININGS_PER_PAGE)} style={{ borderRadius: '8px', border: '1px solid #e2e8f0', color: trainingsReceivedPage >= Math.ceil(trainingsReceived.length / TRAININGS_PER_PAGE) ? '#cbd5e1' : '#64748b', padding: '8px 12px' }}>
                                        <i className="ri-arrow-right-s-line"></i>
                                      </button>
                                    </li>
                                  </ul>
                                </nav>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Check Response Detail Modal */}
      {showCheckModal && selectedCheck && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={() => setShowCheckModal(false)}>
          <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable" onClick={(e) => e.stopPropagation()}>
            <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
              <div className="modal-header" style={{
                background: selectedCheck.type === 'weekly' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' :
                           selectedCheck.type === 'dca' ? 'linear-gradient(135deg, #a855f7 0%, #9333ea 100%)' :
                           'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                color: 'white',
                border: 'none'
              }}>
                <h5 className="modal-title">
                  <i className={`me-2 ${selectedCheck.type === 'weekly' ? 'ri-calendar-check-line' : selectedCheck.type === 'dca' ? 'ri-heart-pulse-line' : 'ri-user-heart-line'}`}></i>
                  {selectedCheck.type === 'weekly' ? 'Check Settimanale' : selectedCheck.type === 'dca' ? 'Check Benessere' : 'Check Minori'}
                  {selectedCheck.cliente_nome && (
                    <span className="ms-2 opacity-75">- {selectedCheck.cliente_nome}</span>
                  )}
                </h5>
                <button className="btn-close btn-close-white" onClick={() => setShowCheckModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                {loadingCheckDetail ? (
                  <div className="text-center py-5">
                    <div className="spinner-border text-primary" role="status"></div>
                    <p className="text-muted mt-3">Caricamento dettagli...</p>
                  </div>
                ) : (
                  <div>
                    {/* Header Info */}
                    <div className="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom">
                      <div>
                        <small className="text-muted">Data compilazione</small>
                        <p className="mb-0 fw-semibold">{selectedCheck.submit_date}</p>
                      </div>
                      {selectedCheck.type === 'weekly' && (
                        <div className="text-end">
                          <small className="text-muted">Peso</small>
                          <p className="mb-0 fw-semibold">{selectedCheck.weight ? `${selectedCheck.weight} kg` : <span className="text-muted">-</span>}</p>
                        </div>
                      )}
                    </div>

                    {/* Ratings */}
                    {(selectedCheck.nutritionist_rating || selectedCheck.psychologist_rating ||
                      selectedCheck.coach_rating || selectedCheck.progress_rating) && (
                      <div className="mb-4">
                        <h6 className="text-muted mb-3"><i className="ri-star-line me-2"></i>Valutazioni Professionisti</h6>
                        <div className="row g-3">
                          {selectedCheck.nutritionist_rating && (() => {
                            const nutri = selectedCheck.nutrizionisti?.[0];
                            return (
                              <div className="col-6 col-md-3">
                                <div className="p-3 rounded text-center" style={{ background: '#dcfce7' }}>
                                  {nutri && (
                                    <div className="mb-2 d-flex justify-content-center">
                                      {nutri.avatar_path ? (
                                        <img src={nutri.avatar_path} alt="" className="rounded-circle" style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #22c55e' }} />
                                      ) : (
                                        <div className="rounded-circle bg-success text-white d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', fontSize: '0.75rem' }}>
                                          {getInitials(nutri.nome)}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                  <div className="fw-bold fs-4 text-success">{selectedCheck.nutritionist_rating}</div>
                                  <small className="text-muted">{nutri?.nome || 'Nutrizionista'}</small>
                                </div>
                              </div>
                            );
                          })()}
                          {selectedCheck.psychologist_rating && (() => {
                            const psico = selectedCheck.psicologi?.[0];
                            return (
                              <div className="col-6 col-md-3">
                                <div className="p-3 rounded text-center" style={{ background: '#fef3c7' }}>
                                  {psico && (
                                    <div className="mb-2 d-flex justify-content-center">
                                      {psico.avatar_path ? (
                                        <img src={psico.avatar_path} alt="" className="rounded-circle" style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #d97706' }} />
                                      ) : (
                                        <div className="rounded-circle text-white d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', fontSize: '0.75rem', background: '#d97706' }}>
                                          {getInitials(psico.nome)}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                  <div className="fw-bold fs-4" style={{ color: '#d97706' }}>{selectedCheck.psychologist_rating}</div>
                                  <small className="text-muted">{psico?.nome || 'Psicologo'}</small>
                                </div>
                              </div>
                            );
                          })()}
                          {selectedCheck.coach_rating && (() => {
                            const coach = selectedCheck.coaches?.[0];
                            return (
                              <div className="col-6 col-md-3">
                                <div className="p-3 rounded text-center" style={{ background: '#dbeafe' }}>
                                  {coach && (
                                    <div className="mb-2 d-flex justify-content-center">
                                      {coach.avatar_path ? (
                                        <img src={coach.avatar_path} alt="" className="rounded-circle" style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #3b82f6' }} />
                                      ) : (
                                        <div className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', fontSize: '0.75rem' }}>
                                          {getInitials(coach.nome)}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                  <div className="fw-bold fs-4 text-primary">{selectedCheck.coach_rating}</div>
                                  <small className="text-muted">{coach?.nome || 'Coach'}</small>
                                </div>
                              </div>
                            );
                          })()}
                          {selectedCheck.progress_rating && (
                            <div className="col-6 col-md-3">
                              <div className="p-3 rounded text-center" style={{ background: '#f3e8ff' }}>
                                <div className="fw-bold fs-4" style={{ color: '#9333ea' }}>{selectedCheck.progress_rating}</div>
                                <small className="text-muted">Progresso</small>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Wellness Ratings (for weekly check) */}
                    {selectedCheck.type === 'weekly' && (
                      <div className="mb-4">
                        <h6 className="text-muted mb-3"><i className="ri-heart-pulse-line me-2"></i>Benessere</h6>
                        <div className="row g-2">
                          {[
                            { key: 'digestion_rating', label: 'Digestione', icon: '🍽️' },
                            { key: 'energy_rating', label: 'Energia', icon: '⚡' },
                            { key: 'strength_rating', label: 'Forza', icon: '💪' },
                            { key: 'hunger_rating', label: 'Fame', icon: '🍴' },
                            { key: 'sleep_rating', label: 'Sonno', icon: '😴' },
                            { key: 'mood_rating', label: 'Umore', icon: '😊' },
                            { key: 'motivation_rating', label: 'Motivazione', icon: '🔥' },
                          ].map(item => (
                            <div key={item.key} className="col-6 col-md-4">
                              <div className="d-flex align-items-center p-2 rounded" style={{ background: '#f8fafc' }}>
                                <span className="me-2">{item.icon}</span>
                                <span className="small text-muted me-auto">{item.label}</span>
                                <span className={`fw-semibold ${selectedCheck[item.key] === null || selectedCheck[item.key] === undefined ? 'text-muted' : ''}`}>
                                  {selectedCheck[item.key] !== null && selectedCheck[item.key] !== undefined ? `${selectedCheck[item.key]}/10` : '-'}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Reflections */}
                    <div className="mb-4">
                      <h6 className="text-muted mb-3"><i className="ri-lightbulb-line me-2"></i>Riflessioni</h6>
                      <div className="mb-3">
                        <div className="p-3 rounded" style={{ background: '#f0fdf4' }}>
                          <small className="text-muted d-block mb-1"><i className="ri-check-line me-1 text-success"></i>Cosa ha funzionato</small>
                          <p className="mb-0">{selectedCheck.what_worked || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                      <div className="mb-3">
                        <div className="p-3 rounded" style={{ background: '#fef2f2' }}>
                          <small className="text-muted d-block mb-1"><i className="ri-close-line me-1 text-danger"></i>Cosa non ha funzionato</small>
                          <p className="mb-0">{selectedCheck.what_didnt_work || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                      <div className="mb-3">
                        <div className="p-3 rounded" style={{ background: '#fffbeb' }}>
                          <small className="text-muted d-block mb-1"><i className="ri-lightbulb-line me-1 text-warning"></i>Cosa ho imparato</small>
                          <p className="mb-0">{selectedCheck.what_learned || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                      <div className="mb-3">
                        <div className="p-3 rounded" style={{ background: '#eff6ff' }}>
                          <small className="text-muted d-block mb-1"><i className="ri-focus-line me-1 text-primary"></i>Focus prossima settimana</small>
                          <p className="mb-0">{selectedCheck.what_focus_next || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                    </div>

                    {/* Extra Comments */}
                    <div className="mb-3">
                      <h6 className="text-muted mb-2"><i className="ri-chat-1-line me-2"></i>Commenti extra</h6>
                      <div className="p-3 rounded" style={{ background: '#f8fafc' }}>
                        <p className="mb-0">{selectedCheck.extra_comments || <span className="text-muted fst-italic">Nessun commento aggiuntivo</span>}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div className="modal-footer border-0">
                <Link
                  to={`/clienti-dettaglio/${selectedCheck.cliente_id}?tab=check`}
                  className="btn btn-outline-primary"
                  onClick={() => setShowCheckModal(false)}
                >
                  <i className="ri-user-line me-1"></i>
                  Vai al Cliente
                </Link>
                <button className="btn btn-secondary" onClick={() => setShowCheckModal(false)}>
                  Chiudi
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default TeamDetail;

import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useOutletContext, useParams } from 'react-router-dom';
import {
  ROLE_LABELS,
  SPECIALTY_LABELS,
  ROLE_COLORS,
  SPECIALTY_COLORS
} from '../../services/teamService';
import teamService from '../../services/teamService';
import trainingService from '../../services/trainingService';
import taskService, { TASK_CATEGORIES } from '../../services/taskService';
import checkService from '../../services/checkService';
import qualityService, {
  getAvailableQuarters,
  getCurrentQuarter,
  getScoreStyle,
  getBandBadgeStyle,
  getSuperMalusBadgeStyle,
} from '../../services/qualityService';
import { isProfessionistaStandard } from '../../utils/rbacScope';
import './Profilo.css';
import './TeamList.css';

const ROLE_GRADIENTS = {
  admin: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  team_leader: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  professionista: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  team_esterno: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
};

const SPECIALTY_GRADIENTS = {
  nutrizione: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
  nutrizionista: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
  coach: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
  psicologia: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
  psicologo: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
  cco: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
  health_manager: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
};

const CLIENT_STATO_OPTIONS = [
  { value: '', label: 'Tutti gli stati' },
  { value: 'attivo', label: 'Attivo' },
  { value: 'in_sospeso', label: 'In sospeso' },
  { value: 'disattivato', label: 'Disattivato' },
  { value: 'prospect', label: 'Prospect' },
  { value: 'attesa_pagamento', label: 'Attesa pagamento' },
];

const CHECK_PERIOD_OPTIONS = [
  { value: 'week', label: 'Ultimi 7 giorni' },
  { value: 'month', label: 'Ultimi 30 giorni' },
  { value: 'trimester', label: 'Ultimi 90 giorni' },
  { value: 'year', label: 'Ultimi 365 giorni' },
];

const CHECK_TYPE_OPTIONS = [
  { value: 'all', label: 'Tutti i check' },
  { value: 'weekly', label: 'Weekly check' },
  { value: 'dca', label: 'DCA check' },
];

function safeDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('it-IT');
}

function Pagination({ page, totalPages, onChange }) {
  if (!totalPages || totalPages <= 1) return null;
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, page + 2);
  const pages = [];
  for (let p = start; p <= end; p += 1) pages.push(p);

  return (
    <div className="tl-pagination-buttons">
      <button className="tl-page-btn" disabled={page <= 1} onClick={() => onChange(Math.max(1, page - 1))}>
        <i className="ri-arrow-left-s-line"></i>
      </button>
      {pages.map(p => (
        <button key={p} className={`tl-page-btn${p === page ? ' active' : ''}`} onClick={() => onChange(p)}>
          {p}
        </button>
      ))}
      <button className="tl-page-btn" disabled={page >= totalPages} onClick={() => onChange(Math.min(totalPages, page + 1))}>
        <i className="ri-arrow-right-s-line"></i>
      </button>
    </div>
  );
}

function Profilo() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const outletContext = useOutletContext();
  const currentUser = outletContext?.user || null;

  const [profileUser, setProfileUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('info');
  const [capacityLoading, setCapacityLoading] = useState(false);
  const [capacityError, setCapacityError] = useState('');
  const [capacityRow, setCapacityRow] = useState(null);
  const [capacityInput, setCapacityInput] = useState('');
  const [capacitySaving, setCapacitySaving] = useState(false);

  const [clients, setClients] = useState([]);
  const [clientsLoading, setClientsLoading] = useState(false);
  const [clientsError, setClientsError] = useState('');
  const [clientPage, setClientPage] = useState(1);
  const [clientFilters, setClientFilters] = useState({ q: '', stato: '' });
  const [clientPagination, setClientPagination] = useState({ total: 0, total_pages: 0, per_page: 10, has_next: false, has_prev: false });

  const [checks, setChecks] = useState([]);
  const [checksLoading, setChecksLoading] = useState(false);
  const [checksError, setChecksError] = useState('');
  const [checkPage, setCheckPage] = useState(1);
  const [checkFilters, setCheckFilters] = useState({ q: '', period: 'month', check_type: 'all' });
  const [checkPagination, setCheckPagination] = useState({ total: 0, total_pages: 0, per_page: 10, has_next: false, has_prev: false });
  const [checkStats, setCheckStats] = useState({ avg_nutrizionista: null, avg_psicologo: null, avg_coach: null, avg_progresso: null, avg_quality: null });
  const [showCheckDetailModal, setShowCheckDetailModal] = useState(false);
  const [selectedCheckDetail, setSelectedCheckDetail] = useState(null);
  const [checkDetailLoading, setCheckDetailLoading] = useState(false);

  const [trainings, setTrainings] = useState([]);
  const [trainingsLoading, setTrainingsLoading] = useState(false);
  const [trainingsError, setTrainingsError] = useState('');
  const [trainingFilters, setTrainingFilters] = useState({ q: '', status: 'all' });
  const [trainingPage, setTrainingPage] = useState(1);
  const TRAINING_PER_PAGE = 10;

  const [tasks, setTasks] = useState([]);
  const [tasksLoading, setTasksLoading] = useState(false);
  const [tasksError, setTasksError] = useState('');
  const [taskFilters, setTaskFilters] = useState({ q: '', category: 'all', completed: 'false' });
  const [taskPage, setTaskPage] = useState(1);
  const TASK_PER_PAGE = 10;

  const [qualityLoading, setQualityLoading] = useState(false);
  const [qualityError, setQualityError] = useState('');
  const [qualityTrend, setQualityTrend] = useState({ labels: [], quality_final: [], quality_month: [], quality_trim: [] });
  const [qualityKpi, setQualityKpi] = useState(null);
  const [qualityQuarter, setQualityQuarter] = useState(getCurrentQuarter());
  const [teamDetailsById, setTeamDetailsById] = useState({});
  const [teamDetailsLoading, setTeamDetailsLoading] = useState(false);
  const [teamDetailsError, setTeamDetailsError] = useState('');

  useEffect(() => {
    if (id) {
      const fetchUserProfile = async () => {
        setLoading(true);
        try {
          const data = await teamService.getTeamMember(id);
          setProfileUser({ ...data, teams: data.teams || [], teams_led: data.teams_led || [] });
        } catch (err) {
          console.error('Error fetching user profile:', err);
          setProfileUser(null);
        } finally {
          setLoading(false);
        }
      };
      fetchUserProfile();
      return;
    }
    if (currentUser) {
      setProfileUser({ ...currentUser, teams: currentUser.teams || [], teams_led: currentUser.teams_led || [] });
    }
  }, [id, currentUser]);

  const user = profileUser;
  const isOwnProfile = !id || (currentUser && user && currentUser.id === user.id);
  const isCurrentUserCco = currentUser?.specialty === 'cco';
  const isCurrentUserAdmin = Boolean(currentUser?.is_admin || currentUser?.role === 'admin');
  const isCurrentUserProfessionista = isProfessionistaStandard(currentUser);
  const canViewCapacityTab = Boolean(isCurrentUserAdmin || currentUser?.role === 'team_leader' || isCurrentUserCco);
  const canEditCapacity = Boolean(isCurrentUserAdmin || isCurrentUserCco);
  const canViewQualityTab = Boolean(isCurrentUserAdmin || isCurrentUserCco);

  useEffect(() => {
    if (!id || !currentUser || !isCurrentUserProfessionista) return;
    if (Number(id) !== Number(currentUser.id)) navigate('/profilo', { replace: true });
  }, [id, currentUser, isCurrentUserProfessionista, navigate]);

  useEffect(() => {
    const requestedTab = new URLSearchParams(location.search).get('tab');
    if (!requestedTab) return;
    const allowedTabs = new Set(['info', 'clienti', 'check', 'formazione', 'task']);
    if (!isCurrentUserProfessionista || isOwnProfile) allowedTabs.add('teams');
    if (canViewQualityTab) allowedTabs.add('quality');
    if (canViewCapacityTab) allowedTabs.add('capienza');
    if (allowedTabs.has(requestedTab) && requestedTab !== activeTab) setActiveTab(requestedTab);
  }, [location.search, canViewCapacityTab, canViewQualityTab, isCurrentUserProfessionista, isOwnProfile, activeTab]);

  useEffect(() => {
    if (isCurrentUserProfessionista && !isOwnProfile && activeTab === 'teams') setActiveTab('info');
    if (!canViewQualityTab && activeTab === 'quality') setActiveTab('info');
  }, [isCurrentUserProfessionista, isOwnProfile, canViewQualityTab, activeTab]);

  useEffect(() => {
    const shouldLoad = activeTab === 'teams' && isCurrentUserProfessionista && isOwnProfile && Array.isArray(user?.teams) && user.teams.length > 0;
    if (!shouldLoad) return;
    const missingTeamIds = user.teams.map((t) => t?.id).filter(Boolean).filter((teamId) => !teamDetailsById[teamId]);
    if (missingTeamIds.length === 0) return;
    let cancelled = false;
    setTeamDetailsLoading(true);
    setTeamDetailsError('');
    Promise.all(missingTeamIds.map((teamId) => teamService.getTeam(teamId)))
      .then((results) => {
        if (cancelled) return;
        setTeamDetailsById((prev) => {
          const next = { ...prev };
          results.forEach((res) => { if (res?.success && res?.id) next[res.id] = res; });
          return next;
        });
      })
      .catch((err) => {
        if (cancelled) return;
        console.error('Errore caricamento dettagli team profilo:', err);
        setTeamDetailsError(err?.response?.data?.message || 'Errore nel caricamento dei membri del team');
      })
      .finally(() => { if (!cancelled) setTeamDetailsLoading(false); });
    return () => { cancelled = true; };
  }, [activeTab, isCurrentUserProfessionista, isOwnProfile, user?.teams, teamDetailsById]);

  const fetchClients = useCallback(async () => {
    if (!user?.id) return;
    setClientsLoading(true); setClientsError('');
    try {
      const response = await teamService.getMemberClients(user.id, { page: clientPage, per_page: 10, q: clientFilters.q || undefined, stato: clientFilters.stato || undefined });
      setClients(response.clients || []);
      setClientPagination({ total: response.total || 0, total_pages: response.total_pages || 0, per_page: response.per_page || 10, has_next: Boolean(response.has_next), has_prev: Boolean(response.has_prev) });
    } catch (err) {
      console.error('Errore caricamento clienti associati:', err);
      setClients([]); setClientPagination({ total: 0, total_pages: 0, per_page: 10, has_next: false, has_prev: false });
      setClientsError(err?.response?.data?.message || 'Errore nel caricamento dei clienti associati');
    } finally { setClientsLoading(false); }
  }, [user?.id, clientPage, clientFilters.q, clientFilters.stato]);

  const fetchChecks = useCallback(async () => {
    if (!user?.id) return;
    setChecksLoading(true); setChecksError('');
    try {
      const response = await teamService.getMemberChecks(user.id, { page: checkPage, per_page: 10, period: checkFilters.period, check_type: checkFilters.check_type, q: checkFilters.q || undefined });
      setChecks(response.responses || []);
      setCheckStats(response.stats || { avg_nutrizionista: null, avg_psicologo: null, avg_coach: null, avg_progresso: null, avg_quality: null });
      setCheckPagination({ total: response.total || 0, total_pages: response.total_pages || 0, per_page: response.per_page || 10, has_next: Boolean(response.has_next), has_prev: Boolean(response.has_prev) });
    } catch (err) {
      console.error('Errore caricamento check associati:', err);
      setChecks([]); setCheckPagination({ total: 0, total_pages: 0, per_page: 10, has_next: false, has_prev: false });
      setChecksError(err?.response?.data?.message || 'Errore nel caricamento dei check associati');
    } finally { setChecksLoading(false); }
  }, [user?.id, checkPage, checkFilters.period, checkFilters.check_type, checkFilters.q]);

  const fetchTrainings = useCallback(async () => {
    if (!user?.id) return;
    setTrainingsLoading(true); setTrainingsError('');
    try {
      const isOwn = currentUser?.id === user.id;
      const canReadOther = Boolean(isCurrentUserAdmin || isCurrentUserCco);
      let payload = null;
      if (isOwn) { payload = await trainingService.getMyTrainings({ page: 1, per_page: 500 }); setTrainings(payload.trainings || []); }
      else if (canReadOther) { payload = await trainingService.getAdminUserTrainings(user.id); setTrainings(payload.trainings || []); }
      else { setTrainings([]); setTrainingsError('Non autorizzato a visualizzare la formazione di questo professionista'); }
    } catch (err) {
      console.error('Errore caricamento formazione associata:', err);
      setTrainings([]); setTrainingsError(err?.response?.data?.error || 'Errore nel caricamento della formazione');
    } finally { setTrainingsLoading(false); }
  }, [user?.id, currentUser?.id, isCurrentUserAdmin, isCurrentUserCco]);

  const fetchTasks = useCallback(async () => {
    if (!user?.id) return;
    setTasksLoading(true); setTasksError('');
    try {
      const params = { assignee_id: user.id, q: taskFilters.q || undefined, category: taskFilters.category !== 'all' ? taskFilters.category : undefined, completed: taskFilters.completed !== 'all' ? taskFilters.completed : undefined };
      const response = await taskService.getAll(params);
      setTasks(Array.isArray(response) ? response : []);
    } catch (err) {
      console.error('Errore caricamento task associati:', err);
      setTasks([]); setTasksError(err?.response?.data?.message || 'Errore nel caricamento dei task');
    } finally { setTasksLoading(false); }
  }, [user?.id, taskFilters.q, taskFilters.category, taskFilters.completed]);

  const fetchQuality = useCallback(async () => {
    if (!user?.id) return;
    setQualityLoading(true); setQualityError('');
    try {
      if (!(isCurrentUserAdmin || isCurrentUserCco)) {
        setQualityKpi(null); setQualityTrend({ labels: [], quality_final: [], quality_month: [], quality_trim: [] });
        setQualityError('Quality visibile solo ad amministrazione o CCO'); return;
      }
      const [trendData, kpiData] = await Promise.all([qualityService.getProfessionistaTrend(user.id), qualityService.getProfessionistaKPIBreakdown(user.id, qualityQuarter)]);
      setQualityTrend({ labels: trendData?.labels || [], quality_final: trendData?.quality_final || [], quality_month: trendData?.quality_month || [], quality_trim: trendData?.quality_trim || [] });
      setQualityKpi(kpiData || null);
    } catch (err) {
      console.error('Errore caricamento quality:', err);
      setQualityKpi(null); setQualityTrend({ labels: [], quality_final: [], quality_month: [], quality_trim: [] });
      setQualityError(err?.response?.data?.error || 'Errore nel caricamento dati quality');
    } finally { setQualityLoading(false); }
  }, [user?.id, isCurrentUserAdmin, isCurrentUserCco, qualityQuarter]);

  const fetchCapacity = useCallback(async () => {
    if (!user?.id) return;
    setCapacityLoading(true); setCapacityError('');
    try {
      const response = await teamService.getProfessionalCapacity({ user_id: user.id });
      const row = (response.rows || [])[0] || null;
      setCapacityRow(row); setCapacityInput(row ? String(row.capienza_contrattuale ?? '') : '');
    } catch (err) {
      setCapacityRow(null); setCapacityInput('');
      if (err?.response?.status === 403) setCapacityError('Non autorizzato a visualizzare la capienza di questo professionista.');
      else setCapacityError(err?.response?.data?.message || 'Errore nel caricamento capienza.');
    } finally { setCapacityLoading(false); }
  }, [user?.id]);

  useEffect(() => { if (activeTab === 'clienti') fetchClients(); }, [activeTab, fetchClients]);
  useEffect(() => { if (activeTab === 'check') fetchChecks(); }, [activeTab, fetchChecks]);
  useEffect(() => { setShowCheckDetailModal(false); setSelectedCheckDetail(null); }, [checkPage, checkFilters.q, checkFilters.period, checkFilters.check_type]);
  useEffect(() => { if (activeTab === 'formazione') fetchTrainings(); }, [activeTab, fetchTrainings]);
  useEffect(() => { if (activeTab === 'task') fetchTasks(); }, [activeTab, fetchTasks]);
  useEffect(() => { if (activeTab === 'quality') fetchQuality(); }, [activeTab, fetchQuality]);
  useEffect(() => { if (activeTab === 'capienza') fetchCapacity(); }, [activeTab, fetchCapacity]);

  const role = user?.role || 'professionista';
  const specialty = user?.specialty;
  const bannerGradient = (specialty && SPECIALTY_GRADIENTS[specialty]) || ROLE_GRADIENTS[role] || ROLE_GRADIENTS.professionista;

  const normalizedCheckSpecialty = useMemo(() => {
    if (specialty === 'nutrizione' || specialty === 'nutrizionista') return 'nutrizione';
    if (specialty === 'psicologia' || specialty === 'psicologo') return 'psicologia';
    if (specialty === 'coach') return 'coach';
    return null;
  }, [specialty]);

  const checkRatingConfig = useMemo(() => {
    const map = {
      nutrizione: { label: 'Nutrizione', rowKey: 'nutritionist_rating', statsKey: 'avg_nutrizionista', feedbackKey: 'nutritionist_feedback', color: '#22c55e' },
      coach: { label: 'Coach', rowKey: 'coach_rating', statsKey: 'avg_coach', feedbackKey: 'coach_feedback', color: '#3b82f6' },
      psicologia: { label: 'Psicologia', rowKey: 'psychologist_rating', statsKey: 'avg_psicologo', feedbackKey: 'psychologist_feedback', color: '#d97706' },
    };
    return normalizedCheckSpecialty ? map[normalizedCheckSpecialty] : null;
  }, [normalizedCheckSpecialty]);

  const checkAvgQualityLabel = useMemo(() => checkStats.avg_quality == null ? '—' : checkStats.avg_quality.toFixed(1), [checkStats.avg_quality]);
  const checkSpecificAvgLabel = useMemo(() => {
    if (!checkRatingConfig) return null;
    const value = checkStats[checkRatingConfig.statsKey];
    return value == null ? '—' : Number(value).toFixed(1);
  }, [checkStats, checkRatingConfig]);

  const getCheckRowRatingValue = useCallback((row) => {
    if (!checkRatingConfig || !row) return null;
    return row[checkRatingConfig.rowKey];
  }, [checkRatingConfig]);

  const openCheckDetailModal = useCallback(async (row) => {
    if (!row?.id) return;
    setSelectedCheckDetail({ ...row, type: row.type || 'weekly' });
    setShowCheckDetailModal(true);
    setCheckDetailLoading(true);
    try {
      const result = await checkService.getResponseDetail(row.type || 'weekly', row.id);
      if (result?.success && result.response) {
        setSelectedCheckDetail({ ...result.response, type: row.type || 'weekly', cliente_id: row.cliente_id, cliente_nome: row.cliente_nome });
      }
    } catch (err) { console.error('Errore caricamento dettaglio check:', err); }
    finally { setCheckDetailLoading(false); }
  }, []);

  const filteredTrainings = useMemo(() => {
    const q = trainingFilters.q.trim().toLowerCase();
    return trainings.filter((t) => {
      const status = t.isAcknowledged ? 'ack' : 'pending';
      const statusMatch = trainingFilters.status === 'all' || trainingFilters.status === status;
      if (!statusMatch) return false;
      if (!q) return true;
      return (t.title || '').toLowerCase().includes(q) || (t.content || '').toLowerCase().includes(q) || (t.reviewType || '').toLowerCase().includes(q) || (`${t.reviewer?.firstName || ''} ${t.reviewer?.lastName || ''}`).toLowerCase().includes(q) || (`${t.reviewee?.firstName || ''} ${t.reviewee?.lastName || ''}`).toLowerCase().includes(q);
    });
  }, [trainings, trainingFilters.q, trainingFilters.status]);

  const trainingTotalPages = Math.max(1, Math.ceil(filteredTrainings.length / TRAINING_PER_PAGE));
  const pagedTrainings = filteredTrainings.slice((trainingPage - 1) * TRAINING_PER_PAGE, trainingPage * TRAINING_PER_PAGE);
  const taskTotalPages = Math.max(1, Math.ceil(tasks.length / TASK_PER_PAGE));
  const pagedTasks = tasks.slice((taskPage - 1) * TASK_PER_PAGE, taskPage * TASK_PER_PAGE);

  const qualityTrendRows = useMemo(() => {
    return (qualityTrend.labels || []).map((label, idx) => ({
      label, quality_final: qualityTrend.quality_final?.[idx], quality_month: qualityTrend.quality_month?.[idx], quality_trim: qualityTrend.quality_trim?.[idx],
    }));
  }, [qualityTrend]);

  // --- Helpers ---
  const paginationInfo = (page, perPage, total) => {
    if (total <= 0) return 'Nessun risultato';
    return `${Math.min((page - 1) * perPage + 1, total)}-${Math.min(page * perPage, total)} di ${total}`;
  };

  // --- Render ---
  if (loading || !user) {
    return (
      <div className="tl-loading">
        <div className="tl-spinner"></div>
        <p className="tl-loading-text">Caricamento profilo...</p>
      </div>
    );
  }

  return (
    <>
      {/* Page Header */}
      <div className="tl-profile-header">
        <div>
          <h4>{isOwnProfile ? 'Il Mio Profilo' : `Profilo di ${user.full_name}`}</h4>
          <ul className="tl-breadcrumb">
            <li><Link to="/welcome">Home</Link></li>
            <li className="tl-breadcrumb-sep">/</li>
            <li>Profilo</li>
          </ul>
        </div>
        {isOwnProfile && (
          <Link to={`/team-modifica/${user.id}`} className="tl-action-pill primary">
            <i className="ri-edit-line"></i>
            Modifica Profilo
          </Link>
        )}
      </div>

      {/* Layout */}
      <div className="tl-profile-layout">
        {/* Left: Hero Card */}
        <div className="tl-profile-hero">
          <div className="tl-profile-banner" style={{ background: bannerGradient }}>
            <div className="tl-profile-banner-badges">
              {user.is_active ? (
                <span className="tl-profile-badge active">
                  <i className="ri-checkbox-circle-line"></i>Attivo
                </span>
              ) : (
                <span className="tl-profile-badge inactive">
                  <i className="ri-close-circle-line"></i>Inattivo
                </span>
              )}
              {user.is_external && (
                <span className="tl-profile-badge external">
                  <i className="ri-external-link-line"></i>Esterno
                </span>
              )}
            </div>

            <div className="tl-profile-avatar-wrap">
              {user.avatar_path ? (
                <img src={user.avatar_path} alt={user.full_name} className="tl-profile-avatar" />
              ) : (
                <div className="tl-profile-avatar-initials">
                  {user.first_name?.[0]?.toUpperCase()}{user.last_name?.[0]?.toUpperCase()}
                </div>
              )}
            </div>
          </div>

          <div className="tl-profile-hero-body">
            <div className="tl-profile-name">{user.full_name}</div>
            <div className="tl-profile-email">{user.email}</div>

            <div className="tl-profile-pills">
              <span className={`tl-pill tl-pill-role`}>{ROLE_LABELS[role] || role}</span>
              {specialty && (
                <span className={`tl-pill tl-pill-specialty-${specialty}`}>
                  {SPECIALTY_LABELS[specialty] || specialty}
                </span>
              )}
            </div>

            <div className="tl-profile-quick-stats">
              <div className="tl-profile-quick-stat">
                <div className="tl-profile-quick-stat-label">ID Utente</div>
                <div className="tl-profile-quick-stat-value">#{user.id}</div>
              </div>
              <div className="tl-profile-quick-stat">
                <div className="tl-profile-quick-stat-label">Team Guidati</div>
                <div className="tl-profile-quick-stat-value">{user.teams_led?.length || 0}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Tabs */}
        <div className="tl-profile-main">
          {/* Tab Nav */}
          <div className="tl-tab-nav">
            <button className={`tl-tab-btn${activeTab === 'info' ? ' active' : ''}`} onClick={() => setActiveTab('info')}>
              <i className="ri-user-settings-line"></i>Info
            </button>
            {(!isCurrentUserProfessionista || isOwnProfile) && (
              <button className={`tl-tab-btn${activeTab === 'teams' ? ' active' : ''}`} onClick={() => setActiveTab('teams')}>
                <i className="ri-team-line"></i>
                {isCurrentUserProfessionista ? 'Team' : 'Team'}
                {(isCurrentUserProfessionista ? user.teams?.length : user.teams_led?.length) > 0 && (
                  <span className="tl-tab-count">{isCurrentUserProfessionista ? user.teams.length : user.teams_led.length}</span>
                )}
              </button>
            )}
            <button className={`tl-tab-btn${activeTab === 'clienti' ? ' active' : ''}`} onClick={() => setActiveTab('clienti')}>
              <i className="ri-user-heart-line"></i>Pazienti
            </button>
            <button className={`tl-tab-btn${activeTab === 'check' ? ' active' : ''}`} onClick={() => setActiveTab('check')}>
              <i className="ri-checkbox-multiple-line"></i>Check
            </button>
            <button className={`tl-tab-btn${activeTab === 'formazione' ? ' active' : ''}`} onClick={() => setActiveTab('formazione')}>
              <i className="ri-book-open-line"></i>Formazione
            </button>
            <button className={`tl-tab-btn${activeTab === 'task' ? ' active' : ''}`} onClick={() => setActiveTab('task')}>
              <i className="ri-task-line"></i>Task
            </button>
            {canViewQualityTab && (
              <button className={`tl-tab-btn${activeTab === 'quality' ? ' active' : ''}`} onClick={() => setActiveTab('quality')}>
                <i className="ri-star-line"></i>Quality
              </button>
            )}
            {canViewCapacityTab && (
              <button className={`tl-tab-btn${activeTab === 'capienza' ? ' active' : ''}`} onClick={() => setActiveTab('capienza')}>
                <i className="ri-bar-chart-box-line"></i>Capienza
              </button>
            )}
          </div>

          {/* Tab Content */}
          <div className="tl-tab-content">

            {/* INFO TAB */}
            {activeTab === 'info' && (
              <div className="tl-info-grid">
                <div>
                  <div className="tl-info-section-title">Dati Personali</div>
                  <div className="tl-info-row">
                    <div className="tl-info-icon green"><i className="ri-user-line"></i></div>
                    <div>
                      <div className="tl-info-label">Nome Completo</div>
                      <div className="tl-info-value">{user.full_name}</div>
                    </div>
                  </div>
                  <div className="tl-info-row">
                    <div className="tl-info-icon blue"><i className="ri-mail-line"></i></div>
                    <div>
                      <div className="tl-info-label">Email</div>
                      <div className="tl-info-value">{user.email}</div>
                    </div>
                  </div>
                </div>
                <div>
                  <div className="tl-info-section-title">Dettagli Account</div>
                  <div className="tl-info-row">
                    <div className="tl-info-icon amber"><i className="ri-shield-user-line"></i></div>
                    <div>
                      <div className="tl-info-label">Ruolo</div>
                      <div className="tl-info-value">{ROLE_LABELS[role] || role}</div>
                    </div>
                  </div>
                  {specialty && (
                    <div className="tl-info-row">
                      <div className="tl-info-icon purple"><i className="ri-stethoscope-line"></i></div>
                      <div>
                        <div className="tl-info-label">Specializzazione</div>
                        <div className="tl-info-value">{SPECIALTY_LABELS[specialty] || specialty}</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TEAMS TAB */}
            {activeTab === 'teams' && (
              <>
                {!isCurrentUserProfessionista && (
                  <div style={{ marginBottom: 24 }}>
                    <div className="tl-info-section-title"><i className="ri-shield-star-line" style={{ marginRight: 6 }}></i>Team Guidati</div>
                    {user.teams_led && user.teams_led.length > 0 ? (
                      <div className="tl-team-list">
                        {user.teams_led.map((team) => (
                          <Link key={team.id} to={`/teams-dettaglio/${team.id}`} className="tl-team-card">
                            <div className="tl-team-icon" style={{ background: ROLE_GRADIENTS.team_leader }}>
                              <i className="ri-team-line"></i>
                            </div>
                            <div>
                              <div className="tl-team-name">{team.name}</div>
                              <div className="tl-team-role-label"><i className="ri-shield-star-line"></i>Team Leader</div>
                            </div>
                          </Link>
                        ))}
                      </div>
                    ) : (
                      <div className="tl-team-empty">Non guida nessun team</div>
                    )}
                  </div>
                )}

                <div>
                  <div className="tl-info-section-title">
                    <i className="ri-group-line" style={{ marginRight: 6 }}></i>
                    {isCurrentUserProfessionista ? 'Il tuo Team' : 'Membro di Team'}
                  </div>
                  {isCurrentUserProfessionista && (
                    <div className="tl-team-info-alert">
                      <i className="ri-information-line"></i>
                      Puoi vedere i team di cui fai parte e i membri, incluso il Team Leader.
                    </div>
                  )}
                  {isCurrentUserProfessionista && teamDetailsLoading && (
                    <div style={{ fontSize: 13, color: '#64748b', marginBottom: 12 }}>
                      <span className="tl-spinner" style={{ width: 16, height: 16, borderWidth: 2, display: 'inline-block', marginRight: 8, verticalAlign: 'middle' }}></span>
                      Caricamento membri...
                    </div>
                  )}
                  {isCurrentUserProfessionista && teamDetailsError && (
                    <div className="tl-alert warning">{teamDetailsError}</div>
                  )}
                  {user.teams && user.teams.length > 0 ? (
                    <div className="tl-team-list">
                      {user.teams.map((team) => (
                        isCurrentUserProfessionista ? (
                          <div key={team.id} className="tl-team-card-static">
                            <div className="tl-team-card-top">
                              <div className="tl-team-icon" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
                                <i className="ri-team-line"></i>
                              </div>
                              <div>
                                <div className="tl-team-name">{team.name}</div>
                                <div className="tl-team-role-label"><i className="ri-user-line"></i>Membro</div>
                              </div>
                            </div>
                            {teamDetailsById[team.id] && (
                              <div className="tl-team-members">
                                {teamDetailsById[team.id]?.head && (
                                  <div style={{ marginBottom: 10 }}>
                                    <div className="tl-team-members-label">Team Leader</div>
                                    <span className="tl-member-chip leader">
                                      {teamDetailsById[team.id].head.full_name || `${teamDetailsById[team.id].head.first_name || ''} ${teamDetailsById[team.id].head.last_name || ''}`.trim()}
                                    </span>
                                  </div>
                                )}
                                <div>
                                  <div className="tl-team-members-label">Membri</div>
                                  <div className="tl-team-members-list">
                                    {(teamDetailsById[team.id]?.members || []).map((member) => (
                                      <span
                                        key={member.id}
                                        className={`tl-member-chip${Number(member.id) === Number(user.id) ? ' self' : ''}`}
                                        title={member.email || ''}
                                      >
                                        {member.full_name || `${member.first_name || ''} ${member.last_name || ''}`.trim() || member.email}
                                        {Number(member.id) === Number(user.id) ? ' (tu)' : ''}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        ) : (
                          <Link key={team.id} to={`/teams-dettaglio/${team.id}`} className="tl-team-card">
                            <div className="tl-team-icon" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
                              <i className="ri-user-line"></i>
                            </div>
                            <div>
                              <div className="tl-team-name">{team.name}</div>
                              <div className="tl-team-role-label"><i className="ri-user-line"></i>Membro</div>
                            </div>
                          </Link>
                        )
                      ))}
                    </div>
                  ) : (
                    <div className="tl-team-empty">Non è membro di nessun team</div>
                  )}
                </div>
              </>
            )}

            {/* CLIENTI TAB */}
            {activeTab === 'clienti' && (
              <div>
                <div className="tl-filter-row">
                  <div className="tl-search-wrap">
                    <i className="ri-search-line tl-search-icon"></i>
                    <input
                      className="tl-search-input"
                      placeholder="Cerca paziente..."
                      value={clientFilters.q}
                      onChange={(e) => { setClientPage(1); setClientFilters(prev => ({ ...prev, q: e.target.value })); }}
                    />
                  </div>
                  <select
                    className="tl-filter-select"
                    value={clientFilters.stato}
                    onChange={(e) => { setClientPage(1); setClientFilters(prev => ({ ...prev, stato: e.target.value })); }}
                  >
                    {CLIENT_STATO_OPTIONS.map(opt => <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>)}
                  </select>
                  <button className="tl-reset-btn" onClick={() => { setClientPage(1); setClientFilters({ q: '', stato: '' }); }}>
                    <i className="ri-refresh-line"></i>Reset
                  </button>
                </div>

                {clientsLoading ? (
                  <div className="tl-loading"><div className="tl-spinner"></div><p className="tl-loading-text">Caricamento pazienti...</p></div>
                ) : clientsError ? (
                  <div className="tl-alert danger">{clientsError}</div>
                ) : clients.length === 0 ? (
                  <div className="tl-empty">
                    <div className="tl-empty-icon"><i className="ri-user-search-line"></i></div>
                    <div className="tl-empty-title">Nessun paziente</div>
                    <div className="tl-empty-desc">Nessun paziente associato con i filtri correnti</div>
                  </div>
                ) : (
                  <>
                    <div className="tl-table-wrap" style={{ overflowX: 'auto' }}>
                      <table className="tl-table">
                        <thead>
                          <tr>
                            <th>Paziente</th>
                            <th>Stato</th>
                            <th>Programma</th>
                            <th>Rinnovo</th>
                            <th className="text-end">Azioni</th>
                          </tr>
                        </thead>
                        <tbody>
                          {clients.map(c => (
                            <tr key={c.cliente_id}>
                              <td>
                                <div className="tl-cell-name">{c.nome_cognome || '-'}</div>
                                <div className="tl-cell-sub">{c.email || '—'}</div>
                              </td>
                              <td><span className="tl-badge neutral">{c.stato_cliente || '—'}</span></td>
                              <td>{c.programma_attuale || '—'}</td>
                              <td>{safeDate(c.data_rinnovo)}</td>
                              <td className="text-end">
                                <button className="tl-btn-open" onClick={() => navigate(`/clienti-dettaglio/${c.cliente_id}`)}>
                                  <i className="ri-external-link-line"></i>Apri
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="tl-table-footer">
                      <span className="tl-table-footer-info">{paginationInfo(clientPage, clientPagination.per_page, clientPagination.total)}</span>
                      <Pagination page={clientPage} totalPages={clientPagination.total_pages} onChange={setClientPage} />
                    </div>
                  </>
                )}
              </div>
            )}

            {/* CHECK TAB */}
            {activeTab === 'check' && (
              <div>
                <div className="tl-filter-row">
                  <div className="tl-search-wrap">
                    <i className="ri-search-line tl-search-icon"></i>
                    <input className="tl-search-input" placeholder="Cerca per nome paziente..." value={checkFilters.q}
                      onChange={(e) => { setCheckPage(1); setCheckFilters(prev => ({ ...prev, q: e.target.value })); }} />
                  </div>
                  <select className="tl-filter-select" value={checkFilters.period}
                    onChange={(e) => { setCheckPage(1); setCheckFilters(prev => ({ ...prev, period: e.target.value })); }}>
                    {CHECK_PERIOD_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                  </select>
                  <select className="tl-filter-select" value={checkFilters.check_type}
                    onChange={(e) => { setCheckPage(1); setCheckFilters(prev => ({ ...prev, check_type: e.target.value })); }}>
                    {CHECK_TYPE_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                  </select>
                  <button className="tl-reset-btn" onClick={() => { setCheckPage(1); setCheckFilters({ q: '', period: 'month', check_type: 'all' }); }}>
                    <i className="ri-refresh-line"></i>Reset
                  </button>
                </div>

                <div className="tl-check-stats">
                  {checkRatingConfig ? (
                    <span className="tl-check-stat-badge">
                      Valutazione {checkRatingConfig.label}: <span className="tl-check-stat-value" style={{ color: checkRatingConfig.color }}>{checkSpecificAvgLabel}</span>
                    </span>
                  ) : (
                    <span className="tl-check-stat-badge">Quality media: <span className="tl-check-stat-value">{checkAvgQualityLabel}</span></span>
                  )}
                </div>

                {checksLoading ? (
                  <div className="tl-loading"><div className="tl-spinner"></div><p className="tl-loading-text">Caricamento check...</p></div>
                ) : checksError ? (
                  <div className="tl-alert danger">{checksError}</div>
                ) : checks.length === 0 ? (
                  <div className="tl-empty">
                    <div className="tl-empty-icon"><i className="ri-checkbox-multiple-blank-line"></i></div>
                    <div className="tl-empty-title">Nessun check</div>
                    <div className="tl-empty-desc">Nessun check associato con i filtri correnti</div>
                  </div>
                ) : (
                  <>
                    <div className="tl-table-wrap" style={{ overflowX: 'auto' }}>
                      <table className="tl-table tl-table-clickable">
                        <thead>
                          <tr>
                            <th>Paziente</th>
                            <th>Tipo</th>
                            <th>Data</th>
                            <th>Valutazione</th>
                            <th>Dettagli</th>
                          </tr>
                        </thead>
                        <tbody>
                          {checks.map(r => {
                            const currentRating = getCheckRowRatingValue(r);
                            return (
                              <Fragment key={`${r.type}-${r.id}`}>
                                <tr onClick={() => openCheckDetailModal(r)}>
                                  <td className="tl-cell-name">{r.cliente_nome || 'N/D'}</td>
                                  <td>
                                    <span className={`tl-badge ${r.type === 'dca' ? 'dca' : 'success'}`}>
                                      {r.type === 'dca' ? 'DCA' : 'Weekly'}
                                    </span>
                                  </td>
                                  <td>{r.submit_date || '—'}</td>
                                  <td>
                                    {checkRatingConfig ? (
                                      <span className="tl-badge" style={{ background: `${checkRatingConfig.color}15`, color: checkRatingConfig.color, border: `1px solid ${checkRatingConfig.color}33` }}>
                                        {currentRating ?? '—'}
                                      </span>
                                    ) : (
                                      <span className="tl-cell-sub">{checkAvgQualityLabel}</span>
                                    )}
                                  </td>
                                  <td><i className="ri-eye-line" style={{ color: '#94a3b8' }}></i></td>
                                </tr>
                              </Fragment>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    <div className="tl-table-footer">
                      <span className="tl-table-footer-info">{paginationInfo(checkPage, checkPagination.per_page, checkPagination.total)}</span>
                      <Pagination page={checkPage} totalPages={checkPagination.total_pages} onChange={setCheckPage} />
                    </div>
                  </>
                )}
              </div>
            )}

            {/* FORMAZIONE TAB */}
            {activeTab === 'formazione' && (
              <div>
                <div className="tl-filter-row">
                  <div className="tl-search-wrap">
                    <i className="ri-search-line tl-search-icon"></i>
                    <input className="tl-search-input" placeholder="Cerca training..." value={trainingFilters.q}
                      onChange={(e) => { setTrainingPage(1); setTrainingFilters(prev => ({ ...prev, q: e.target.value })); }} />
                  </div>
                  <select className="tl-filter-select" value={trainingFilters.status}
                    onChange={(e) => { setTrainingPage(1); setTrainingFilters(prev => ({ ...prev, status: e.target.value })); }}>
                    <option value="all">Tutti gli stati</option>
                    <option value="pending">Da confermare</option>
                    <option value="ack">Confermati</option>
                  </select>
                  <button className="tl-reset-btn" onClick={() => { setTrainingPage(1); setTrainingFilters({ q: '', status: 'all' }); }}>
                    <i className="ri-refresh-line"></i>Reset
                  </button>
                </div>

                {trainingsLoading ? (
                  <div className="tl-loading"><div className="tl-spinner"></div><p className="tl-loading-text">Caricamento formazione...</p></div>
                ) : trainingsError ? (
                  <div className="tl-alert warning">{trainingsError}</div>
                ) : filteredTrainings.length === 0 ? (
                  <div className="tl-empty">
                    <div className="tl-empty-icon"><i className="ri-book-2-line"></i></div>
                    <div className="tl-empty-title">Nessuna formazione</div>
                    <div className="tl-empty-desc">Nessuna formazione trovata</div>
                  </div>
                ) : (
                  <>
                    <div className="tl-table-wrap" style={{ overflowX: 'auto' }}>
                      <table className="tl-table">
                        <thead>
                          <tr><th>Titolo</th><th>Tipo</th><th>Data</th><th>Stato</th></tr>
                        </thead>
                        <tbody>
                          {pagedTrainings.map(t => (
                            <tr key={t.id}>
                              <td>
                                <div className="tl-cell-name">{t.title || '-'}</div>
                                <div className="tl-cell-sub">{t.reviewer?.firstName ? `${t.reviewer.firstName} ${t.reviewer.lastName || ''}`.trim() : '—'}</div>
                              </td>
                              <td>{t.reviewType || '—'}</td>
                              <td>{safeDate(t.createdAt)}</td>
                              <td>
                                {t.isAcknowledged
                                  ? <span className="tl-badge success">Confermato</span>
                                  : <span className="tl-badge warning">Da confermare</span>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="tl-table-footer">
                      <span className="tl-table-footer-info">{paginationInfo(trainingPage, TRAINING_PER_PAGE, filteredTrainings.length)}</span>
                      <Pagination page={trainingPage} totalPages={trainingTotalPages} onChange={setTrainingPage} />
                    </div>
                  </>
                )}
              </div>
            )}

            {/* TASK TAB */}
            {activeTab === 'task' && (
              <div>
                <div className="tl-filter-row">
                  <div className="tl-search-wrap">
                    <i className="ri-search-line tl-search-icon"></i>
                    <input className="tl-search-input" placeholder="Cerca task..." value={taskFilters.q}
                      onChange={(e) => { setTaskPage(1); setTaskFilters(prev => ({ ...prev, q: e.target.value })); }} />
                  </div>
                  <select className="tl-filter-select" value={taskFilters.category}
                    onChange={(e) => { setTaskPage(1); setTaskFilters(prev => ({ ...prev, category: e.target.value })); }}>
                    <option value="all">Tutte le categorie</option>
                    {Object.keys(TASK_CATEGORIES).map(cat => <option key={cat} value={cat}>{TASK_CATEGORIES[cat].label}</option>)}
                  </select>
                  <select className="tl-filter-select" value={taskFilters.completed}
                    onChange={(e) => { setTaskPage(1); setTaskFilters(prev => ({ ...prev, completed: e.target.value })); }}>
                    <option value="false">Aperti</option>
                    <option value="true">Completati</option>
                    <option value="all">Tutti</option>
                  </select>
                  <button className="tl-reset-btn" onClick={() => { setTaskPage(1); setTaskFilters({ q: '', category: 'all', completed: 'false' }); }}>
                    <i className="ri-refresh-line"></i>Reset
                  </button>
                </div>

                {tasksLoading ? (
                  <div className="tl-loading"><div className="tl-spinner"></div><p className="tl-loading-text">Caricamento task...</p></div>
                ) : tasksError ? (
                  <div className="tl-alert danger">{tasksError}</div>
                ) : tasks.length === 0 ? (
                  <div className="tl-empty">
                    <div className="tl-empty-icon"><i className="ri-task-line"></i></div>
                    <div className="tl-empty-title">Nessun task</div>
                    <div className="tl-empty-desc">Nessun task associato</div>
                  </div>
                ) : (
                  <>
                    <div className="tl-table-wrap" style={{ overflowX: 'auto' }}>
                      <table className="tl-table">
                        <thead>
                          <tr><th>Task</th><th>Categoria</th><th>Scadenza</th><th>Stato</th><th className="text-end">Azione</th></tr>
                        </thead>
                        <tbody>
                          {pagedTasks.map(t => (
                            <tr key={t.id}>
                              <td>
                                <div className="tl-cell-name">{t.title || '-'}</div>
                                <div className="tl-cell-sub">{t.description || '—'}</div>
                              </td>
                              <td>{TASK_CATEGORIES[t.category]?.label || t.category || '—'}</td>
                              <td>{safeDate(t.due_date)}</td>
                              <td>
                                {t.completed
                                  ? <span className="tl-badge success">Completato</span>
                                  : <span className="tl-badge warning">Aperto</span>}
                              </td>
                              <td className="text-end">
                                {t.client_id ? (
                                  <button className="tl-btn-open" onClick={() => navigate(`/clienti-dettaglio/${t.client_id}`)}>
                                    <i className="ri-external-link-line"></i>Apri
                                  </button>
                                ) : <span style={{ color: '#94a3b8' }}>—</span>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="tl-table-footer">
                      <span className="tl-table-footer-info">{paginationInfo(taskPage, TASK_PER_PAGE, tasks.length)}</span>
                      <Pagination page={taskPage} totalPages={taskTotalPages} onChange={setTaskPage} />
                    </div>
                  </>
                )}
              </div>
            )}

            {/* QUALITY TAB */}
            {activeTab === 'quality' && (
              <div>
                <div className="tl-quality-header">
                  <div>
                    <div className="tl-quality-title">KPI Quality</div>
                    <div className="tl-quality-sub">Dati trimestrali e trend ultime settimane</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>Trimestre</span>
                    <select className="tl-filter-select" style={{ minWidth: 130 }} value={qualityQuarter} onChange={(e) => setQualityQuarter(e.target.value)}>
                      {getAvailableQuarters().map(q => <option key={q} value={q}>{q}</option>)}
                    </select>
                  </div>
                </div>

                {qualityLoading ? (
                  <div className="tl-loading"><div className="tl-spinner"></div><p className="tl-loading-text">Caricamento quality...</p></div>
                ) : qualityError ? (
                  <div className="tl-alert warning">{qualityError}</div>
                ) : qualityKpi?.message ? (
                  <div className="tl-alert info">{qualityKpi.message}</div>
                ) : (
                  <>
                    <div className="tl-kpi-grid">
                      <div className="tl-kpi-card">
                        <div className="tl-kpi-label">Quality Trim (40%)</div>
                        <div className="tl-kpi-value" style={qualityKpi?.kpi_quality?.value != null ? getScoreStyle(qualityKpi.kpi_quality.value) : {}}>
                          {qualityKpi?.kpi_quality?.value != null ? Number(qualityKpi.kpi_quality.value).toFixed(2) : '—'}
                        </div>
                        <span className="tl-badge" style={getBandBadgeStyle(qualityKpi?.kpi_quality?.bonus_band || '0%')}>
                          {qualityKpi?.kpi_quality?.bonus_band || '0%'}
                        </span>
                      </div>
                      <div className="tl-kpi-card">
                        <div className="tl-kpi-label">Rinnovo Adj (60%)</div>
                        <div className="tl-kpi-value">
                          {qualityKpi?.kpi_rinnovo_adj?.value != null ? `${Number(qualityKpi.kpi_rinnovo_adj.value).toFixed(1)}%` : '—'}
                        </div>
                        <span className="tl-badge" style={getBandBadgeStyle(qualityKpi?.kpi_rinnovo_adj?.bonus_band || '0%')}>
                          {qualityKpi?.kpi_rinnovo_adj?.bonus_band || '0%'}
                        </span>
                      </div>
                      <div className="tl-kpi-card">
                        <div className="tl-kpi-label">Bonus Composito</div>
                        <div className="tl-kpi-value">
                          {qualityKpi?.final_bonus_percentage != null ? `${Number(qualityKpi.final_bonus_percentage).toFixed(2)}%` : '—'}
                        </div>
                      </div>
                      <div className="tl-kpi-card">
                        <div className="tl-kpi-label">Bonus Finale</div>
                        <div className="tl-kpi-value">
                          {qualityKpi?.final_bonus_after_malus != null ? `${Number(qualityKpi.final_bonus_after_malus).toFixed(2)}%` : '—'}
                        </div>
                        {qualityKpi?.super_malus?.applied && (
                          <span className="tl-badge" style={getSuperMalusBadgeStyle(qualityKpi?.super_malus?.percentage || 0)}>
                            Super Malus {qualityKpi?.super_malus?.percentage || 0}%
                          </span>
                        )}
                      </div>
                    </div>

                    {qualityKpi?.super_malus?.applied && qualityKpi?.super_malus?.reason && (
                      <div className="tl-malus-alert">
                        <i className="ri-error-warning-line"></i>
                        <strong>Motivo Super Malus:</strong> {qualityKpi.super_malus.reason}
                      </div>
                    )}

                    <div className="tl-table-wrap" style={{ overflowX: 'auto' }}>
                      <table className="tl-table">
                        <thead>
                          <tr><th>Settimana</th><th>Quality Final</th><th>Quality Mese</th><th>Quality Trim</th></tr>
                        </thead>
                        <tbody>
                          {qualityTrendRows.length === 0 ? (
                            <tr><td colSpan={4} style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>Nessun trend disponibile</td></tr>
                          ) : qualityTrendRows.map(row => (
                            <tr key={row.label}>
                              <td>{row.label}</td>
                              <td style={row.quality_final != null ? getScoreStyle(row.quality_final) : {}}>
                                {row.quality_final != null ? Number(row.quality_final).toFixed(2) : '—'}
                              </td>
                              <td>{row.quality_month != null ? Number(row.quality_month).toFixed(2) : '—'}</td>
                              <td>{row.quality_trim != null ? Number(row.quality_trim).toFixed(2) : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* CAPIENZA TAB */}
            {activeTab === 'capienza' && (
              <div>
                {capacityLoading ? (
                  <div className="tl-loading"><div className="tl-spinner"></div><p className="tl-loading-text">Caricamento capienza...</p></div>
                ) : capacityError ? (
                  <div className="tl-alert warning">{capacityError}</div>
                ) : !capacityRow ? (
                  <div className="tl-alert info">Nessun dato capienza disponibile per questo professionista.</div>
                ) : (
                  <div className="tl-table-wrap" style={{ overflowX: 'auto' }}>
                    <table className="tl-table">
                      <thead>
                        <tr><th>Professionista</th><th>Capienza contrattuale</th><th>Clienti assegnati</th><th>% Capienza</th></tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td className="tl-cell-name">{capacityRow.full_name}</td>
                          <td>
                            {canEditCapacity ? (
                              <div className="tl-capacity-edit">
                                <input type="number" min="0" className="tl-capacity-input" value={capacityInput}
                                  onChange={(e) => setCapacityInput(e.target.value)} />
                                <button className="tl-capacity-save" disabled={capacitySaving}
                                  onClick={async () => {
                                    if (capacityInput === '' || Number.isNaN(Number(capacityInput))) return;
                                    setCapacitySaving(true);
                                    try {
                                      const res = await teamService.updateProfessionalCapacity(user.id, Number(capacityInput));
                                      setCapacityRow(res.row); setCapacityInput(String(res.row.capienza_contrattuale ?? ''));
                                    } catch (err) {
                                      alert(err?.response?.data?.message || 'Errore nel salvataggio della capienza contrattuale');
                                    } finally { setCapacitySaving(false); }
                                  }}>
                                  {capacitySaving ? '...' : 'Salva'}
                                </button>
                              </div>
                            ) : <span>{capacityRow.capienza_contrattuale}</span>}
                          </td>
                          <td>
                            <span className={`tl-badge ${capacityRow.is_over_capacity ? 'danger' : 'neutral'}`}>
                              {capacityRow.clienti_assegnati}
                            </span>
                          </td>
                          <td>{(capacityRow.percentuale_capienza || 0).toFixed(1)}%</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Check Detail Modal */}
      {showCheckDetailModal && selectedCheckDetail && (
        <div className="tl-modal-overlay" onClick={() => setShowCheckDetailModal(false)}>
          <div className="tl-modal" onClick={(e) => e.stopPropagation()}>
            <div
              className="tl-modal-header"
              style={{
                background: selectedCheckDetail.type === 'dca'
                  ? 'linear-gradient(135deg, #a855f7 0%, #9333ea 100%)'
                  : 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              }}
            >
              <div className="tl-modal-title">
                <i className={selectedCheckDetail.type === 'dca' ? 'ri-heart-pulse-line' : 'ri-calendar-check-line'}></i>
                {selectedCheckDetail.type === 'dca' ? 'Check DCA' : 'Check Settimanale'}
                {selectedCheckDetail.cliente_nome ? ` - ${selectedCheckDetail.cliente_nome}` : ''}
              </div>
              <button className="tl-modal-close" onClick={() => setShowCheckDetailModal(false)}>
                <i className="ri-close-line"></i>
              </button>
            </div>

            <div className="tl-modal-body">
              {checkDetailLoading ? (
                <div className="tl-loading"><div className="tl-spinner"></div><p className="tl-loading-text">Caricamento dettagli...</p></div>
              ) : (
                <>
                  <div className="tl-detail-meta">
                    <div>
                      <div className="tl-detail-meta-label">Data compilazione</div>
                      <div className="tl-detail-meta-value">{selectedCheckDetail.submit_date || '—'}</div>
                    </div>
                    {selectedCheckDetail.type === 'weekly' && (
                      <div style={{ textAlign: 'right' }}>
                        <div className="tl-detail-meta-label">Peso</div>
                        <div className="tl-detail-meta-value">
                          {selectedCheckDetail.weight ? `${selectedCheckDetail.weight} kg` : <span className="tl-detail-text-empty">-</span>}
                        </div>
                      </div>
                    )}
                  </div>

                  {selectedCheckDetail.type === 'weekly' && (
                    <div className="tl-detail-section">
                      <div className="tl-detail-section-title"><i className="ri-camera-line"></i>Foto Progressi</div>
                      <div className="tl-detail-photo-grid">
                        {[['photo_front', 'Frontale'], ['photo_side', 'Laterale'], ['photo_back', 'Posteriore']].map(([key, label]) => (
                          <div key={key}>
                            <div className="tl-detail-photo-label">{label}</div>
                            {selectedCheckDetail[key] ? (
                              <img src={selectedCheckDetail[key]} alt={label} className="tl-detail-photo-img" onClick={() => window.open(selectedCheckDetail[key], '_blank')} />
                            ) : (
                              <div className="tl-detail-photo-empty">Non caricata</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {checkRatingConfig && (
                    <div className="tl-detail-section">
                      <div className="tl-detail-section-title"><i className="ri-star-line"></i>Valutazioni Professionisti</div>
                      <div className="tl-detail-card-grid">
                        <div className="tl-detail-card" style={{ background: `${checkRatingConfig.color}10` }}>
                          <div className="tl-detail-card-value" style={{ color: checkRatingConfig.color }}>
                            {selectedCheckDetail[checkRatingConfig.rowKey] ?? '—'}
                          </div>
                          <div className="tl-detail-card-label">{checkRatingConfig.label}</div>
                        </div>
                        {selectedCheckDetail.progress_rating != null && (
                          <div className="tl-detail-card" style={{ background: '#f3e8ff' }}>
                            <div className="tl-detail-card-value" style={{ color: '#9333ea' }}>{selectedCheckDetail.progress_rating}</div>
                            <div className="tl-detail-card-label">Progresso</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {selectedCheckDetail.type === 'weekly' && (
                    <div className="tl-detail-section">
                      <div className="tl-detail-section-title"><i className="ri-heart-pulse-line"></i>Benessere</div>
                      <div className="tl-detail-wellness-grid">
                        {[
                          { key: 'digestion_rating', label: 'Digestione', icon: 'ri-heart-pulse-line' },
                          { key: 'energy_rating', label: 'Energia', icon: 'ri-flashlight-line' },
                          { key: 'strength_rating', label: 'Forza', icon: 'ri-boxing-line' },
                          { key: 'hunger_rating', label: 'Fame', icon: 'ri-restaurant-2-line' },
                          { key: 'sleep_rating', label: 'Sonno', icon: 'ri-moon-line' },
                          { key: 'mood_rating', label: 'Umore', icon: 'ri-emotion-happy-line' },
                          { key: 'motivation_rating', label: 'Motivazione', icon: 'ri-fire-line' },
                        ].map(item => (
                          <div key={item.key} className="tl-detail-wellness-item">
                            <i className={item.icon} style={{ color: '#25B36A', fontSize: 16 }}></i>
                            <span className="tl-detail-wellness-label">{item.label}</span>
                            <span className={`tl-detail-wellness-value${selectedCheckDetail[item.key] == null ? ' tl-detail-text-empty' : ''}`}>
                              {selectedCheckDetail[item.key] != null ? `${selectedCheckDetail[item.key]}/10` : '-'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {checkRatingConfig && (
                    <div className="tl-detail-section">
                      <div className="tl-detail-section-title"><i className="ri-feedback-line"></i>Feedback Professionisti</div>
                      <div className="tl-detail-feedback-card" style={{ background: `${checkRatingConfig.color}10`, border: `1px solid ${checkRatingConfig.color}33` }}>
                        <div className="tl-detail-feedback-header">
                          <div className="tl-detail-text-label">Feedback {checkRatingConfig.label}</div>
                          <span className="tl-detail-feedback-badge">Solo professionista corrente</span>
                        </div>
                        <div className="tl-detail-text-value">
                          {selectedCheckDetail[checkRatingConfig.feedbackKey] || <span className="tl-detail-text-empty">Non compilato</span>}
                        </div>
                      </div>
                    </div>
                  )}

                  {selectedCheckDetail.type === 'weekly' && (
                    <div className="tl-detail-section">
                      <div className="tl-detail-section-title"><i className="ri-calendar-check-line"></i>Programmi</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                        <div className="tl-detail-text-block">
                          <div className="tl-detail-text-label">Aderenza programma alimentare</div>
                          <div className="tl-detail-text-value">{selectedCheckDetail.nutrition_program_adherence || <span className="tl-detail-text-empty">Non compilato</span>}</div>
                        </div>
                        <div className="tl-detail-text-block">
                          <div className="tl-detail-text-label">Aderenza programma sportivo</div>
                          <div className="tl-detail-text-value">{selectedCheckDetail.training_program_adherence || <span className="tl-detail-text-empty">Non compilato</span>}</div>
                        </div>
                      </div>
                      <div className="tl-detail-text-block">
                        <div className="tl-detail-text-label">Esercizi modificati/aggiunti</div>
                        <div className="tl-detail-text-value">{selectedCheckDetail.exercise_modifications || <span className="tl-detail-text-empty">Non compilato</span>}</div>
                      </div>
                    </div>
                  )}

                  <div className="tl-detail-section">
                    <div className="tl-detail-section-title"><i className="ri-lightbulb-line"></i>Riflessioni</div>
                    <div className="tl-detail-text-block green">
                      <div className="tl-detail-text-label"><i className="ri-check-line" style={{ color: '#22c55e' }}></i>Cosa ha funzionato</div>
                      <div className="tl-detail-text-value">{selectedCheckDetail.what_worked || <span className="tl-detail-text-empty">Non compilato</span>}</div>
                    </div>
                    <div className="tl-detail-text-block red">
                      <div className="tl-detail-text-label"><i className="ri-close-line" style={{ color: '#ef4444' }}></i>Cosa non ha funzionato</div>
                      <div className="tl-detail-text-value">{selectedCheckDetail.what_didnt_work || <span className="tl-detail-text-empty">Non compilato</span>}</div>
                    </div>
                    <div className="tl-detail-text-block amber">
                      <div className="tl-detail-text-label"><i className="ri-lightbulb-line" style={{ color: '#f59e0b' }}></i>Cosa ho imparato</div>
                      <div className="tl-detail-text-value">{selectedCheckDetail.what_learned || <span className="tl-detail-text-empty">Non compilato</span>}</div>
                    </div>
                    <div className="tl-detail-text-block blue">
                      <div className="tl-detail-text-label"><i className="ri-focus-line" style={{ color: '#3b82f6' }}></i>Focus prossima settimana</div>
                      <div className="tl-detail-text-value">{selectedCheckDetail.what_focus_next || <span className="tl-detail-text-empty">Non compilato</span>}</div>
                    </div>
                  </div>

                  {selectedCheckDetail.type === 'weekly' && (
                    <div className="tl-detail-section">
                      <div className="tl-detail-section-title"><i className="ri-user-add-line"></i>Referral</div>
                      <div className="tl-detail-text-block">
                        <div className="tl-detail-text-value">{selectedCheckDetail.referral || <span className="tl-detail-text-empty">Nessun referral indicato</span>}</div>
                      </div>
                    </div>
                  )}

                  <div className="tl-detail-section">
                    <div className="tl-detail-section-title"><i className="ri-chat-1-line"></i>Commenti extra</div>
                    <div className="tl-detail-text-block">
                      <div className="tl-detail-text-value">{selectedCheckDetail.extra_comments || <span className="tl-detail-text-empty">Nessun commento aggiuntivo</span>}</div>
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="tl-modal-footer">
              {selectedCheckDetail.cliente_id && (
                <button className="tl-btn-outline primary"
                  onClick={() => { setShowCheckDetailModal(false); navigate(`/clienti-dettaglio/${selectedCheckDetail.cliente_id}?tab=check_periodici`); }}>
                  <i className="ri-external-link-line"></i>Apri scheda check
                </button>
              )}
              <button className="tl-btn-secondary" onClick={() => setShowCheckDetailModal(false)}>Chiudi</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default Profilo;

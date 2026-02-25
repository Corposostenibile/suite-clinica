import { useCallback, useEffect, useMemo, useState } from 'react';
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
import qualityService, {
  getAvailableQuarters,
  getCurrentQuarter,
  getScoreStyle,
  getBandBadgeStyle,
  getSuperMalusBadgeStyle,
} from '../../services/qualityService';
import checkService from '../../services/checkService';
import CheckResponseDetailModal from '../../components/CheckResponseDetailModal';
import './profilo-responsive.css';

// Mapping specialty → rating per tab Check Associati (solo valutazione del professionista)
const CHECK_SPECIALTY_RATING = {
  nutrizione: { key: 'nutritionist_rating', label: 'Nutri', avgKey: 'avg_nutrizionista', role: 'nutrizionista' },
  nutrizionista: { key: 'nutritionist_rating', label: 'Nutri', avgKey: 'avg_nutrizionista', role: 'nutrizionista' },
  coach: { key: 'coach_rating', label: 'Coach', avgKey: 'avg_coach', role: 'coach' },
  psicologia: { key: 'psychologist_rating', label: 'Psico', avgKey: 'avg_psicologo', role: 'psicologo' },
  psicologo: { key: 'psychologist_rating', label: 'Psico', avgKey: 'avg_psicologo', role: 'psicologo' },
};
function getCheckRatingConfig(specialty) {
  if (!specialty) return null;
  const key = typeof specialty === 'string' ? specialty.toLowerCase() : specialty;
  return CHECK_SPECIALTY_RATING[key] ?? CHECK_SPECIALTY_RATING[specialty] ?? null;
}

const ROLE_GRADIENTS = {
  admin: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  team_leader: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  professionista: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  team_esterno: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
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

function renderPagination(page, totalPages, onChange) {
  if (!totalPages || totalPages <= 1) return null;
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, page + 2);
  const pages = [];
  for (let p = start; p <= end; p += 1) {
    pages.push(
      <li key={p} className={`page-item ${p === page ? 'active' : ''}`}>
        <button className="page-link" onClick={() => onChange(p)}>{p}</button>
      </li>
    );
  }

  return (
    <nav>
      <ul className="pagination pagination-sm mb-0">
        <li className={`page-item ${page <= 1 ? 'disabled' : ''}`}>
          <button className="page-link" onClick={() => onChange(Math.max(1, page - 1))}>
            &laquo;
          </button>
        </li>
        {pages}
        <li className={`page-item ${page >= totalPages ? 'disabled' : ''}`}>
          <button className="page-link" onClick={() => onChange(Math.min(totalPages, page + 1))}>
            &raquo;
          </button>
        </li>
      </ul>
    </nav>
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
  const [clientPagination, setClientPagination] = useState({
    total: 0,
    total_pages: 0,
    per_page: 10,
    has_next: false,
    has_prev: false,
  });

  const [checks, setChecks] = useState([]);
  const [checksLoading, setChecksLoading] = useState(false);
  const [checksError, setChecksError] = useState('');
  const [checkPage, setCheckPage] = useState(1);
  const [checkFilters, setCheckFilters] = useState({ q: '', period: 'month', check_type: 'all' });
  const [checkPagination, setCheckPagination] = useState({
    total: 0,
    total_pages: 0,
    per_page: 10,
    has_next: false,
    has_prev: false,
  });
  const [checkStats, setCheckStats] = useState({
    avg_nutrizionista: null,
    avg_psicologo: null,
    avg_coach: null,
    avg_progresso: null,
    avg_quality: null,
  });
  const [selectedCheckResponse, setSelectedCheckResponse] = useState(null);
  const [showCheckResponseModal, setShowCheckResponseModal] = useState(false);
  const [loadingCheckDetail, setLoadingCheckDetail] = useState(false);

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
  const [qualityTrend, setQualityTrend] = useState({
    labels: [],
    quality_final: [],
    quality_month: [],
    quality_trim: [],
  });
  const [qualityKpi, setQualityKpi] = useState(null);
  const [qualityQuarter, setQualityQuarter] = useState(getCurrentQuarter());

  useEffect(() => {
    if (id) {
      const fetchUserProfile = async () => {
        setLoading(true);
        try {
          const data = await teamService.getTeamMember(id);
          setProfileUser({
            ...data,
            teams: data.teams || [],
            teams_led: data.teams_led || []
          });
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
      setProfileUser({
        ...currentUser,
        teams: currentUser.teams || [],
        teams_led: currentUser.teams_led || []
      });
    }
  }, [id, currentUser]);

  const user = profileUser;
  const isOwnProfile = !id || (currentUser && user && currentUser.id === user.id);
  const isCurrentUserCco = currentUser?.specialty === 'cco';
  const isCurrentUserAdmin = Boolean(currentUser?.is_admin || currentUser?.role === 'admin');
  const canViewCapacityTab = Boolean(
    isCurrentUserAdmin || currentUser?.role === 'team_leader' || isCurrentUserCco
  );
  const canEditCapacity = Boolean(isCurrentUserAdmin || isCurrentUserCco);

  useEffect(() => {
    const requestedTab = new URLSearchParams(location.search).get('tab');
    if (!requestedTab) return;

    const allowedTabs = new Set(['info', 'teams', 'clienti', 'check', 'formazione', 'task', 'quality']);
    if (canViewCapacityTab) {
      allowedTabs.add('capienza');
    }

    if (allowedTabs.has(requestedTab) && requestedTab !== activeTab) {
      setActiveTab(requestedTab);
    }
  }, [location.search, canViewCapacityTab, activeTab]);

  const fetchClients = useCallback(async () => {
    if (!user?.id) return;
    setClientsLoading(true);
    setClientsError('');
    try {
      const response = await teamService.getMemberClients(user.id, {
        page: clientPage,
        per_page: 10,
        q: clientFilters.q || undefined,
        stato: clientFilters.stato || undefined,
      });
      setClients(response.clients || []);
      setClientPagination({
        total: response.total || 0,
        total_pages: response.total_pages || 0,
        per_page: response.per_page || 10,
        has_next: Boolean(response.has_next),
        has_prev: Boolean(response.has_prev),
      });
    } catch (err) {
      console.error('Errore caricamento clienti associati:', err);
      setClients([]);
      setClientPagination({ total: 0, total_pages: 0, per_page: 10, has_next: false, has_prev: false });
      setClientsError(err?.response?.data?.message || 'Errore nel caricamento dei clienti associati');
    } finally {
      setClientsLoading(false);
    }
  }, [user?.id, clientPage, clientFilters.q, clientFilters.stato]);

  const fetchChecks = useCallback(async () => {
    if (!user?.id) return;
    setChecksLoading(true);
    setChecksError('');
    try {
      const response = await teamService.getMemberChecks(user.id, {
        page: checkPage,
        per_page: 10,
        period: checkFilters.period,
        check_type: checkFilters.check_type,
        q: checkFilters.q || undefined,
      });
      setChecks(response.responses || []);
      setCheckStats(response.stats || {
        avg_nutrizionista: null,
        avg_psicologo: null,
        avg_coach: null,
        avg_progresso: null,
        avg_quality: null,
      });
      setCheckPagination({
        total: response.total || 0,
        total_pages: response.total_pages || 0,
        per_page: response.per_page || 10,
        has_next: Boolean(response.has_next),
        has_prev: Boolean(response.has_prev),
      });
    } catch (err) {
      console.error('Errore caricamento check associati:', err);
      setChecks([]);
      setCheckPagination({ total: 0, total_pages: 0, per_page: 10, has_next: false, has_prev: false });
      setChecksError(err?.response?.data?.message || 'Errore nel caricamento dei check associati');
    } finally {
      setChecksLoading(false);
    }
  }, [user?.id, checkPage, checkFilters.period, checkFilters.check_type, checkFilters.q]);

  const fetchTrainings = useCallback(async () => {
    if (!user?.id) return;
    setTrainingsLoading(true);
    setTrainingsError('');
    try {
      const isOwn = currentUser?.id === user.id;
      const canReadOther = Boolean(isCurrentUserAdmin || isCurrentUserCco);

      let payload = null;
      if (isOwn) {
        payload = await trainingService.getMyTrainings({ page: 1, per_page: 500 });
        setTrainings(payload.trainings || []);
      } else if (canReadOther) {
        payload = await trainingService.getAdminUserTrainings(user.id);
        setTrainings(payload.trainings || []);
      } else {
        setTrainings([]);
        setTrainingsError('Non autorizzato a visualizzare la formazione di questo professionista');
      }
    } catch (err) {
      console.error('Errore caricamento formazione associata:', err);
      setTrainings([]);
      setTrainingsError(err?.response?.data?.error || 'Errore nel caricamento della formazione');
    } finally {
      setTrainingsLoading(false);
    }
  }, [user?.id, currentUser?.id, isCurrentUserAdmin, isCurrentUserCco]);

  const fetchTasks = useCallback(async () => {
    if (!user?.id) return;
    setTasksLoading(true);
    setTasksError('');
    try {
      const params = {
        assignee_id: user.id,
        q: taskFilters.q || undefined,
        category: taskFilters.category !== 'all' ? taskFilters.category : undefined,
        completed: taskFilters.completed !== 'all' ? taskFilters.completed : undefined,
      };
      const response = await taskService.getAll(params);
      setTasks(Array.isArray(response) ? response : []);
    } catch (err) {
      console.error('Errore caricamento task associati:', err);
      setTasks([]);
      setTasksError(err?.response?.data?.message || 'Errore nel caricamento dei task');
    } finally {
      setTasksLoading(false);
    }
  }, [user?.id, taskFilters.q, taskFilters.category, taskFilters.completed]);

  const fetchQuality = useCallback(async () => {
    if (!user?.id) return;
    setQualityLoading(true);
    setQualityError('');
    try {
      if (!(isCurrentUserAdmin || isCurrentUserCco)) {
        setQualityKpi(null);
        setQualityTrend({ labels: [], quality_final: [], quality_month: [], quality_trim: [] });
        setQualityError('Quality visibile solo ad amministrazione o CCO');
        return;
      }

      const [trendData, kpiData] = await Promise.all([
        qualityService.getProfessionistaTrend(user.id),
        qualityService.getProfessionistaKPIBreakdown(user.id, qualityQuarter),
      ]);

      setQualityTrend({
        labels: trendData?.labels || [],
        quality_final: trendData?.quality_final || [],
        quality_month: trendData?.quality_month || [],
        quality_trim: trendData?.quality_trim || [],
      });
      setQualityKpi(kpiData || null);
    } catch (err) {
      console.error('Errore caricamento quality:', err);
      setQualityKpi(null);
      setQualityTrend({ labels: [], quality_final: [], quality_month: [], quality_trim: [] });
      setQualityError(err?.response?.data?.error || 'Errore nel caricamento dati quality');
    } finally {
      setQualityLoading(false);
    }
  }, [user?.id, isCurrentUserAdmin, isCurrentUserCco, qualityQuarter]);

  const fetchCapacity = useCallback(async () => {
    if (!user?.id) return;
    setCapacityLoading(true);
    setCapacityError('');
    try {
      const response = await teamService.getProfessionalCapacity({ user_id: user.id });
      const row = (response.rows || [])[0] || null;
      setCapacityRow(row);
      setCapacityInput(row ? String(row.capienza_contrattuale ?? '') : '');
    } catch (err) {
      setCapacityRow(null);
      setCapacityInput('');
      if (err?.response?.status === 403) {
        setCapacityError('Non autorizzato a visualizzare la capienza di questo professionista.');
      } else {
        setCapacityError(err?.response?.data?.message || 'Errore nel caricamento capienza.');
      }
    } finally {
      setCapacityLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    if (activeTab === 'clienti') fetchClients();
  }, [activeTab, fetchClients]);

  useEffect(() => {
    if (activeTab === 'check') fetchChecks();
  }, [activeTab, fetchChecks]);

  useEffect(() => {
    if (activeTab === 'formazione') fetchTrainings();
  }, [activeTab, fetchTrainings]);

  useEffect(() => {
    if (activeTab === 'task') fetchTasks();
  }, [activeTab, fetchTasks]);

  useEffect(() => {
    if (activeTab === 'quality') fetchQuality();
  }, [activeTab, fetchQuality]);

  useEffect(() => {
    if (activeTab === 'capienza') fetchCapacity();
  }, [activeTab, fetchCapacity]);

  const role = user?.role || 'professionista';
  const specialty = user?.specialty;

  const checkRatingConfig = useMemo(() => getCheckRatingConfig(specialty), [specialty]);

  const handleViewCheckResponse = useCallback(async (response) => {
    setSelectedCheckResponse({ ...response, type: response.type || 'weekly' });
    setShowCheckResponseModal(true);
    setLoadingCheckDetail(true);
    try {
      const result = await checkService.getResponseDetail(response.type || 'weekly', response.id);
      if (result.success) {
        setSelectedCheckResponse({
          ...result.response,
          type: response.type || 'weekly',
          nutrizionisti: response.nutrizionisti,
          psicologi: response.psicologi,
          coaches: response.coaches,
        });
      }
    } catch (err) {
      console.error('Error fetching check response detail:', err);
    } finally {
      setLoadingCheckDetail(false);
    }
  }, []);

  const checkAvgQualityLabel = useMemo(() => {
    if (checkStats.avg_quality == null) return '—';
    return checkStats.avg_quality.toFixed(1);
  }, [checkStats.avg_quality]);

  const filteredTrainings = useMemo(() => {
    const q = trainingFilters.q.trim().toLowerCase();
    return trainings.filter((t) => {
      const status = t.isAcknowledged ? 'ack' : 'pending';
      const statusMatch = trainingFilters.status === 'all' || trainingFilters.status === status;
      if (!statusMatch) return false;
      if (!q) return true;
      return (
        (t.title || '').toLowerCase().includes(q) ||
        (t.content || '').toLowerCase().includes(q) ||
        (t.reviewType || '').toLowerCase().includes(q) ||
        (`${t.reviewer?.firstName || ''} ${t.reviewer?.lastName || ''}`).toLowerCase().includes(q) ||
        (`${t.reviewee?.firstName || ''} ${t.reviewee?.lastName || ''}`).toLowerCase().includes(q)
      );
    });
  }, [trainings, trainingFilters.q, trainingFilters.status]);

  const trainingTotalPages = Math.max(1, Math.ceil(filteredTrainings.length / TRAINING_PER_PAGE));
  const pagedTrainings = filteredTrainings.slice((trainingPage - 1) * TRAINING_PER_PAGE, trainingPage * TRAINING_PER_PAGE);

  const taskTotalPages = Math.max(1, Math.ceil(tasks.length / TASK_PER_PAGE));
  const pagedTasks = tasks.slice((taskPage - 1) * TASK_PER_PAGE, taskPage * TASK_PER_PAGE);

  const qualityTrendRows = useMemo(() => {
    return (qualityTrend.labels || []).map((label, idx) => ({
      label,
      quality_final: qualityTrend.quality_final?.[idx],
      quality_month: qualityTrend.quality_month?.[idx],
      quality_trim: qualityTrend.quality_trim?.[idx],
    }));
  }, [qualityTrend]);

  if (loading || !user) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Caricamento...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="profilo-page-container">
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1">{isOwnProfile ? 'Il Mio Profilo' : `Profilo di ${user.full_name}`}</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/welcome">Home</Link>
              </li>
              <li className="breadcrumb-item active">Profilo</li>
            </ol>
          </nav>
        </div>
        {isOwnProfile && (
          <Link to={`/team-modifica/${user.id}`} className="btn btn-primary">
            <i className="ri-edit-line me-1"></i>
            Modifica Profilo
          </Link>
        )}
      </div>

      <div className="row g-4">
        <div className="col-lg-4">
          <div className="card shadow-sm border-0 overflow-hidden">
            <div
              className="position-relative"
              style={{
                background: ROLE_GRADIENTS[role] || ROLE_GRADIENTS.professionista,
                height: '120px'
              }}
            >
              <div className="position-absolute top-0 start-0 p-3 d-flex gap-2">
                {user.is_active ? (
                  <span className="badge bg-success">
                    <i className="ri-checkbox-circle-line me-1"></i>Attivo
                  </span>
                ) : (
                  <span className="badge bg-dark bg-opacity-75">
                    <i className="ri-close-circle-line me-1"></i>Inattivo
                  </span>
                )}
                {user.is_external && (
                  <span className="badge bg-white text-dark">
                    <i className="ri-external-link-line me-1"></i>Esterno
                  </span>
                )}
              </div>

              <div className="position-absolute start-50 translate-middle-x" style={{ bottom: '-50px' }}>
                {user.avatar_path ? (
                  <img
                    src={user.avatar_path}
                    alt={user.full_name}
                    className="rounded-circle border border-4 border-white shadow"
                    style={{ width: '100px', height: '100px', objectFit: 'cover', background: '#fff' }}
                  />
                ) : (
                  <div
                    className="rounded-circle border border-4 border-white shadow d-flex align-items-center justify-content-center"
                    style={{ width: '100px', height: '100px', background: '#fff' }}
                  >
                    <span className="fw-bold text-primary" style={{ fontSize: '2rem' }}>
                      {user.first_name?.[0]?.toUpperCase()}{user.last_name?.[0]?.toUpperCase()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="card-body text-center pt-5 mt-3">
              <h4 className="mb-1">{user.full_name}</h4>
              <p className="text-muted mb-3">{user.email}</p>

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

              <div className="row g-3 mb-4">
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">ID Utente</div>
                    <div className="fw-semibold">#{user.id}</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">Team Guidati</div>
                    <div className="fw-semibold">{user.teams_led?.length || 0}</div>
                  </div>
                </div>
                {role === 'health_manager' && (
                  <div className="col-12">
                    <div className="bg-primary bg-opacity-10 rounded-3 p-3 border border-primary border-opacity-25">
                      <div className="text-muted small mb-1">
                        <i className="ri-user-heart-line me-1"></i>Ruolo
                      </div>
                      <div className="fw-semibold text-primary">Health Manager</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="col-lg-8">
          <div className="card shadow-sm border-0">
            <div className="card-header bg-transparent border-bottom p-0">
              <ul className="nav nav-tabs border-0">
                <li className="nav-item">
                  <button className={`nav-link px-4 py-3 ${activeTab === 'info' ? 'active' : ''}`} onClick={() => setActiveTab('info')}>
                    <i className="ri-user-settings-line me-2"></i>
                    Informazioni
                  </button>
                </li>
                <li className="nav-item">
                  <button className={`nav-link px-4 py-3 ${activeTab === 'teams' ? 'active' : ''}`} onClick={() => setActiveTab('teams')}>
                    <i className="ri-team-line me-2"></i>
                    Team Guidati
                    {user.teams_led?.length > 0 && <span className="badge bg-primary ms-2">{user.teams_led.length}</span>}
                  </button>
                </li>
                <li className="nav-item">
                  <button className={`nav-link px-4 py-3 ${activeTab === 'clienti' ? 'active' : ''}`} onClick={() => setActiveTab('clienti')}>
                    <i className="ri-user-heart-line me-2"></i>
                    Pazienti Associati
                  </button>
                </li>
                <li className="nav-item">
                  <button className={`nav-link px-4 py-3 ${activeTab === 'check' ? 'active' : ''}`} onClick={() => setActiveTab('check')}>
                    <i className="ri-checkbox-multiple-line me-2"></i>
                    Check Associati
                  </button>
                </li>
                <li className="nav-item">
                  <button className={`nav-link px-4 py-3 ${activeTab === 'formazione' ? 'active' : ''}`} onClick={() => setActiveTab('formazione')}>
                    <i className="ri-book-open-line me-2"></i>
                    Formazione
                  </button>
                </li>
                <li className="nav-item">
                  <button className={`nav-link px-4 py-3 ${activeTab === 'task' ? 'active' : ''}`} onClick={() => setActiveTab('task')}>
                    <i className="ri-task-line me-2"></i>
                    Task
                  </button>
                </li>
                <li className="nav-item">
                  <button className={`nav-link px-4 py-3 ${activeTab === 'quality' ? 'active' : ''}`} onClick={() => setActiveTab('quality')}>
                    <i className="ri-star-line me-2"></i>
                    Quality
                  </button>
                </li>
                {canViewCapacityTab && (
                  <li className="nav-item">
                    <button className={`nav-link px-4 py-3 ${activeTab === 'capienza' ? 'active' : ''}`} onClick={() => setActiveTab('capienza')}>
                      <i className="ri-bar-chart-box-line me-2"></i>
                      Capienza
                    </button>
                  </li>
                )}
              </ul>
            </div>

            <div className="card-body">
              {activeTab === 'info' && (
                <div className="row g-4">
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">Dati Personali</h6>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-primary-subtle rounded-circle d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px' }}>
                          <i className="ri-user-line text-primary"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Nome Completo</div>
                        <div className="fw-medium">{user.full_name}</div>
                      </div>
                    </div>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-info-subtle rounded-circle d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px' }}>
                          <i className="ri-mail-line text-info"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Email</div>
                        <div className="fw-medium">{user.email}</div>
                      </div>
                    </div>
                  </div>
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">Dettagli Account</h6>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px' }}>
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
                          <div className="rounded-circle d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', background: '#e8daff' }}>
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

              {activeTab === 'teams' && (
                <>
                  <div className="mb-4">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      <i className="ri-shield-star-line me-2"></i>
                      Team Guidati
                    </h6>
                    {user.teams_led && user.teams_led.length > 0 ? (
                      <div className="row g-3">
                        {user.teams_led.map((team) => (
                          <div key={team.id} className="col-12">
                            <Link to={`/teams-dettaglio/${team.id}`} className="text-decoration-none">
                              <div className="border rounded-3 p-3 d-flex align-items-center">
                                <div className="flex-shrink-0">
                                  <div
                                    className="rounded-circle d-flex align-items-center justify-content-center text-white"
                                    style={{ width: '48px', height: '48px', background: ROLE_GRADIENTS.team_leader }}
                                  >
                                    <i className="ri-team-line fs-5"></i>
                                  </div>
                                </div>
                                <div className="flex-grow-1 ms-3">
                                  <h6 className="mb-0">{team.name}</h6>
                                  <small className="text-muted">
                                    <i className="ri-shield-star-line me-1"></i>Team Leader
                                  </small>
                                </div>
                              </div>
                            </Link>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-3 bg-light rounded-3">
                        <small className="text-muted">Non guida nessun team</small>
                      </div>
                    )}
                  </div>

                  <div>
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      <i className="ri-group-line me-2"></i>
                      Membro di Team
                    </h6>
                    {user.teams && user.teams.length > 0 ? (
                      <div className="row g-3">
                        {user.teams.map((team) => (
                          <div key={team.id} className="col-12">
                            <Link to={`/teams-dettaglio/${team.id}`} className="text-decoration-none">
                              <div className="border rounded-3 p-3 d-flex align-items-center">
                                <div className="flex-shrink-0">
                                  <div
                                    className="rounded-circle d-flex align-items-center justify-content-center text-white"
                                    style={{ width: '48px', height: '48px', background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}
                                  >
                                    <i className="ri-user-line fs-5"></i>
                                  </div>
                                </div>
                                <div className="flex-grow-1 ms-3">
                                  <h6 className="mb-0">{team.name}</h6>
                                  <small className="text-muted">
                                    <i className="ri-user-line me-1"></i>Membro
                                  </small>
                                </div>
                              </div>
                            </Link>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-3 bg-light rounded-3">
                        <small className="text-muted">Non è membro di nessun team</small>
                      </div>
                    )}
                  </div>
                </>
              )}

              {activeTab === 'clienti' && (
                <div>
                  <div className="row g-2 align-items-center mb-3">
                    <div className="col-lg-6">
                      <input
                        className="form-control"
                        placeholder="Cerca paziente..."
                        value={clientFilters.q}
                        onChange={(e) => {
                          setClientPage(1);
                          setClientFilters((prev) => ({ ...prev, q: e.target.value }));
                        }}
                      />
                    </div>
                    <div className="col-lg-4">
                      <select
                        className="form-select"
                        value={clientFilters.stato}
                        onChange={(e) => {
                          setClientPage(1);
                          setClientFilters((prev) => ({ ...prev, stato: e.target.value }));
                        }}
                      >
                        {CLIENT_STATO_OPTIONS.map((opt) => (
                          <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-lg-2">
                      <button
                        className="btn btn-outline-secondary w-100"
                        onClick={() => {
                          setClientPage(1);
                          setClientFilters({ q: '', stato: '' });
                        }}
                      >
                        Reset
                      </button>
                    </div>
                  </div>

                  {clientsLoading ? (
                    <div className="text-center py-4">
                      <div className="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                      Caricamento pazienti...
                    </div>
                  ) : clientsError ? (
                    <div className="alert alert-danger mb-0">{clientsError}</div>
                  ) : clients.length === 0 ? (
                    <div className="text-center py-5">
                      <i className="ri-user-search-line text-muted fs-1"></i>
                      <p className="text-muted mt-2 mb-0">Nessun paziente associato con i filtri correnti</p>
                    </div>
                  ) : (
                    <>
                      <div className="table-responsive border rounded">
                        <table className="table table-sm table-hover align-middle mb-0">
                          <thead className="table-light">
                            <tr>
                              <th>Paziente</th>
                              <th>Stato</th>
                              <th>Programma</th>
                              <th>Rinnovo</th>
                              <th>HM</th>
                              <th className="text-end">Azioni</th>
                            </tr>
                          </thead>
                          <tbody>
                            {clients.map((c) => (
                              <tr key={c.cliente_id}>
                                <td data-label="Paziente">
                                  <div className="fw-medium">{c.nome_cognome || '-'}</div>
                                  <small className="text-muted">{c.email || '—'}</small>
                                </td>
                                <td data-label="Stato">
                                  <span className="badge bg-light text-dark border">{c.stato_cliente || '—'}</span>
                                </td>
                                <td data-label="Programma">{c.programma_attuale || '—'}</td>
                                <td data-label="Rinnovo">{safeDate(c.data_rinnovo)}</td>
                                <td data-label="HM">
                                  {c.health_manager_user ? (
                                    <div className="d-flex align-items-center gap-2">
                                      {c.health_manager_user.avatar_path ? (
                                        <img
                                          src={c.health_manager_user.avatar_path}
                                          alt={c.health_manager_user.full_name}
                                          className="rounded-circle"
                                          style={{ width: '24px', height: '24px', objectFit: 'cover' }}
                                        />
                                      ) : (
                                        <span className="rounded-circle bg-primary bg-opacity-25 d-inline-flex align-items-center justify-content-center text-primary fw-medium" style={{ width: '24px', height: '24px', fontSize: '11px' }}>
                                          {(c.health_manager_user.full_name || ' ')[0].toUpperCase()}
                                        </span>
                                      )}
                                      <span className="small">{c.health_manager_user.full_name || '—'}</span>
                                    </div>
                                  ) : (
                                    <span className="text-muted small">—</span>
                                  )}
                                </td>
                                <td className="text-end" data-label="Azioni">
                                  <button
                                    className="btn btn-sm btn-outline-primary"
                                    onClick={() => navigate(`/clienti-dettaglio/${c.cliente_id}`)}
                                  >
                                    Apri
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <div className="d-flex justify-content-between align-items-center mt-3">
                        <small className="text-muted">
                          {clientPagination.total > 0
                            ? `Mostrando ${Math.min((clientPage - 1) * clientPagination.per_page + 1, clientPagination.total)}-${Math.min(clientPage * clientPagination.per_page, clientPagination.total)} di ${clientPagination.total}`
                            : 'Nessun risultato'}
                        </small>
                        {renderPagination(clientPage, clientPagination.total_pages, setClientPage)}
                      </div>
                    </>
                  )}
                </div>
              )}

              {activeTab === 'check' && (
                <div>
                  <div className="row g-2 align-items-center mb-3">
                    <div className="col-lg-4">
                      <input
                        className="form-control"
                        placeholder="Cerca per nome paziente..."
                        value={checkFilters.q}
                        onChange={(e) => {
                          setCheckPage(1);
                          setCheckFilters((prev) => ({ ...prev, q: e.target.value }));
                        }}
                      />
                    </div>
                    <div className="col-lg-3">
                      <select
                        className="form-select"
                        value={checkFilters.period}
                        onChange={(e) => {
                          setCheckPage(1);
                          setCheckFilters((prev) => ({ ...prev, period: e.target.value }));
                        }}
                      >
                        {CHECK_PERIOD_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-lg-3">
                      <select
                        className="form-select"
                        value={checkFilters.check_type}
                        onChange={(e) => {
                          setCheckPage(1);
                          setCheckFilters((prev) => ({ ...prev, check_type: e.target.value }));
                        }}
                      >
                        {CHECK_TYPE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-lg-2">
                      <button
                        className="btn btn-outline-secondary w-100"
                        onClick={() => {
                          setCheckPage(1);
                          setCheckFilters({ q: '', period: 'month', check_type: 'all' });
                        }}
                      >
                        Reset
                      </button>
                    </div>
                  </div>

                  {/* Un solo badge: media della valutazione del professionista (Nutri/Coach/Psico) */}
                  <div className="d-flex flex-wrap gap-3 mb-3">
                    <span className="badge bg-light text-dark border">
                      {checkRatingConfig
                        ? `${checkRatingConfig.label}: ${(checkStats[checkRatingConfig.avgKey] ?? '—').toString()}`
                        : `Quality media: ${checkAvgQualityLabel}`}
                    </span>
                  </div>

                  {checksLoading ? (
                    <div className="text-center py-4">
                      <div className="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                      Caricamento check...
                    </div>
                  ) : checksError ? (
                    <div className="alert alert-danger mb-0">{checksError}</div>
                  ) : checks.length === 0 ? (
                    <div className="text-center py-5">
                      <i className="ri-checkbox-multiple-blank-line text-muted fs-1"></i>
                      <p className="text-muted mt-2 mb-0">Nessun check associato con i filtri correnti</p>
                    </div>
                  ) : (
                    <>
                      <div className="table-responsive border rounded">
                        <table className="table table-sm table-hover align-middle mb-0">
                          <thead className="table-light">
                            <tr>
                              <th>Paziente</th>
                              <th>Tipo</th>
                              <th>Data</th>
                              <th>Valutazioni</th>
                              <th>Dettagli</th>
                            </tr>
                          </thead>
                          <tbody>
                            {checks.map((r) => {
                              const rowKey = `${r.type}-${r.id}`;
                              const ratingVal = checkRatingConfig ? (r[checkRatingConfig.key] ?? '—') : (r.progress_rating ?? '—');
                              return (
                                <tr
                                  key={rowKey}
                                  role="button"
                                  tabIndex={0}
                                  style={{ cursor: 'pointer' }}
                                  onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    handleViewCheckResponse(r);
                                  }}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                      e.preventDefault();
                                      handleViewCheckResponse(r);
                                    }
                                  }}
                                  title="Clicca per aprire il dettaglio check"
                                >
                                  <td className="fw-medium" data-label="Paziente">{r.cliente_nome || 'N/D'}</td>
                                  <td data-label="Tipo">
                                    <span className={`badge ${r.type === 'dca' ? 'bg-info' : 'bg-success'}`}>
                                      {r.type === 'dca' ? 'DCA' : 'Weekly'}
                                    </span>
                                  </td>
                                  <td data-label="Data">{r.submit_date || '—'}</td>
                                  <td data-label="Valutazioni">
                                    <small className="text-muted">
                                      {checkRatingConfig ? `${checkRatingConfig.label}: ${ratingVal}` : `Q: ${ratingVal}`}
                                    </small>
                                  </td>
                                  <td data-label="Dettaglio">
                                    <i className="ri-arrow-right-s-line" aria-hidden></i>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>

                      <div className="d-flex justify-content-between align-items-center mt-3">
                        <small className="text-muted">
                          {checkPagination.total > 0
                            ? `Mostrando ${Math.min((checkPage - 1) * checkPagination.per_page + 1, checkPagination.total)}-${Math.min(checkPage * checkPagination.per_page, checkPagination.total)} di ${checkPagination.total}`
                            : 'Nessun risultato'}
                        </small>
                        {renderPagination(checkPage, checkPagination.total_pages, setCheckPage)}
                      </div>
                    </>
                  )}
                </div>
              )}

              {activeTab === 'formazione' && (
                <div>
                  <div className="row g-2 align-items-center mb-3">
                    <div className="col-lg-6">
                      <input
                        className="form-control"
                        placeholder="Cerca training..."
                        value={trainingFilters.q}
                        onChange={(e) => {
                          setTrainingPage(1);
                          setTrainingFilters((prev) => ({ ...prev, q: e.target.value }));
                        }}
                      />
                    </div>
                    <div className="col-lg-4">
                      <select
                        className="form-select"
                        value={trainingFilters.status}
                        onChange={(e) => {
                          setTrainingPage(1);
                          setTrainingFilters((prev) => ({ ...prev, status: e.target.value }));
                        }}
                      >
                        <option value="all">Tutti gli stati</option>
                        <option value="pending">Da confermare</option>
                        <option value="ack">Confermati</option>
                      </select>
                    </div>
                    <div className="col-lg-2">
                      <button
                        className="btn btn-outline-secondary w-100"
                        onClick={() => {
                          setTrainingPage(1);
                          setTrainingFilters({ q: '', status: 'all' });
                        }}
                      >
                        Reset
                      </button>
                    </div>
                  </div>

                  {trainingsLoading ? (
                    <div className="text-center py-4">
                      <div className="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                      Caricamento formazione...
                    </div>
                  ) : trainingsError ? (
                    <div className="alert alert-warning mb-0">{trainingsError}</div>
                  ) : filteredTrainings.length === 0 ? (
                    <div className="text-center py-5">
                      <i className="ri-book-2-line text-muted fs-1"></i>
                      <p className="text-muted mt-2 mb-0">Nessuna formazione trovata</p>
                    </div>
                  ) : (
                    <>
                      <div className="table-responsive border rounded">
                        <table className="table table-sm table-hover align-middle mb-0">
                          <thead className="table-light">
                            <tr>
                              <th>Titolo</th>
                              <th>Tipo</th>
                              <th>Data</th>
                              <th>Stato</th>
                            </tr>
                          </thead>
                          <tbody>
                            {pagedTrainings.map((t) => (
                              <tr key={t.id}>
                                <td data-label="Titolo">
                                  <div className="fw-medium">{t.title || '-'}</div>
                                  <small className="text-muted">
                                    {t.reviewer?.firstName || t.reviewee?.firstName ? `${t.reviewer?.firstName || ''} ${t.reviewer?.lastName || ''}`.trim() : '—'}
                                  </small>
                                </td>
                                <td data-label="Tipo">{t.reviewType || '—'}</td>
                                <td data-label="Data">{safeDate(t.createdAt)}</td>
                                <td data-label="Stato">
                                  {t.isAcknowledged ? (
                                    <span className="badge bg-success">Confermato</span>
                                  ) : (
                                    <span className="badge bg-warning text-dark">Da confermare</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="d-flex justify-content-between align-items-center mt-3">
                        <small className="text-muted">
                          Mostrando {Math.min((trainingPage - 1) * TRAINING_PER_PAGE + 1, filteredTrainings.length)}-{Math.min(trainingPage * TRAINING_PER_PAGE, filteredTrainings.length)} di {filteredTrainings.length}
                        </small>
                        {renderPagination(trainingPage, trainingTotalPages, setTrainingPage)}
                      </div>
                    </>
                  )}
                </div>
              )}

              {activeTab === 'task' && (
                <div>
                  <div className="row g-2 align-items-center mb-3">
                    <div className="col-lg-5">
                      <input
                        className="form-control"
                        placeholder="Cerca task..."
                        value={taskFilters.q}
                        onChange={(e) => {
                          setTaskPage(1);
                          setTaskFilters((prev) => ({ ...prev, q: e.target.value }));
                        }}
                      />
                    </div>
                    <div className="col-lg-3">
                      <select
                        className="form-select"
                        value={taskFilters.category}
                        onChange={(e) => {
                          setTaskPage(1);
                          setTaskFilters((prev) => ({ ...prev, category: e.target.value }));
                        }}
                      >
                        <option value="all">Tutte le categorie</option>
                        {Object.keys(TASK_CATEGORIES).map((cat) => (
                          <option key={cat} value={cat}>{TASK_CATEGORIES[cat].label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-lg-2">
                      <select
                        className="form-select"
                        value={taskFilters.completed}
                        onChange={(e) => {
                          setTaskPage(1);
                          setTaskFilters((prev) => ({ ...prev, completed: e.target.value }));
                        }}
                      >
                        <option value="false">Aperti</option>
                        <option value="true">Completati</option>
                        <option value="all">Tutti</option>
                      </select>
                    </div>
                    <div className="col-lg-2">
                      <button
                        className="btn btn-outline-secondary w-100"
                        onClick={() => {
                          setTaskPage(1);
                          setTaskFilters({ q: '', category: 'all', completed: 'false' });
                        }}
                      >
                        Reset
                      </button>
                    </div>
                  </div>

                  {tasksLoading ? (
                    <div className="text-center py-4">
                      <div className="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                      Caricamento task...
                    </div>
                  ) : tasksError ? (
                    <div className="alert alert-danger mb-0">{tasksError}</div>
                  ) : tasks.length === 0 ? (
                    <div className="text-center py-5">
                      <i className="ri-task-line text-muted fs-1"></i>
                      <p className="text-muted mt-2 mb-0">Nessun task associato</p>
                    </div>
                  ) : (
                    <>
                      <div className="table-responsive border rounded">
                        <table className="table table-sm table-hover align-middle mb-0">
                          <thead className="table-light">
                            <tr>
                              <th>Task</th>
                              <th>Categoria</th>
                              <th>Scadenza</th>
                              <th>Stato</th>
                              <th className="text-end">Azione</th>
                            </tr>
                          </thead>
                          <tbody>
                            {pagedTasks.map((t) => (
                              <tr key={t.id}>
                                <td data-label="Task">
                                  <div className="fw-medium">{t.title || '-'}</div>
                                  <small className="text-muted">{t.description || '—'}</small>
                                </td>
                                <td data-label="Categoria">{TASK_CATEGORIES[t.category]?.label || t.category || '—'}</td>
                                <td data-label="Scadenza">{safeDate(t.due_date)}</td>
                                <td data-label="Stato">
                                  {t.completed ? (
                                    <span className="badge bg-success">Completato</span>
                                  ) : (
                                    <span className="badge bg-warning text-dark">Aperto</span>
                                  )}
                                </td>
                                <td className="text-end" data-label="Azione">
                                  {t.client_id ? (
                                    <button
                                      className="btn btn-sm btn-outline-primary"
                                      onClick={() => navigate(`/clienti-dettaglio/${t.client_id}`)}
                                    >
                                      Apri
                                    </button>
                                  ) : (
                                    <span className="text-muted">—</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="d-flex justify-content-between align-items-center mt-3">
                        <small className="text-muted">
                          Mostrando {Math.min((taskPage - 1) * TASK_PER_PAGE + 1, tasks.length)}-{Math.min(taskPage * TASK_PER_PAGE, tasks.length)} di {tasks.length}
                        </small>
                        {renderPagination(taskPage, taskTotalPages, setTaskPage)}
                      </div>
                    </>
                  )}
                </div>
              )}

              {activeTab === 'quality' && (
                <div>
                  <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                    <div>
                      <h6 className="mb-1">KPI Quality</h6>
                      <small className="text-muted">Dati trimestrali e trend ultime settimane</small>
                    </div>
                    <div className="d-flex align-items-center gap-2">
                      <span className="text-muted small">Trimestre</span>
                      <select
                        className="form-select form-select-sm"
                        style={{ minWidth: 130 }}
                        value={qualityQuarter}
                        onChange={(e) => setQualityQuarter(e.target.value)}
                      >
                        {getAvailableQuarters().map((q) => (
                          <option key={q} value={q}>{q}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {qualityLoading ? (
                    <div className="text-center py-4">
                      <div className="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                      Caricamento quality...
                    </div>
                  ) : qualityError ? (
                    <div className="alert alert-warning mb-0">{qualityError}</div>
                  ) : qualityKpi?.message ? (
                    <div className="alert alert-light border mb-0">{qualityKpi.message}</div>
                  ) : (
                    <>
                      <div className="row g-3 mb-3">
                        <div className="col-md-6 col-xl-3">
                          <div className="border rounded p-3 h-100">
                            <div className="text-muted small mb-1">Quality Trim (40%)</div>
                            <div className="fw-semibold" style={qualityKpi?.kpi_quality?.value != null ? getScoreStyle(qualityKpi.kpi_quality.value) : {}}>
                              {qualityKpi?.kpi_quality?.value != null ? Number(qualityKpi.kpi_quality.value).toFixed(2) : '—'}
                            </div>
                            <div className="mt-2">
                              <span className="badge" style={getBandBadgeStyle(qualityKpi?.kpi_quality?.bonus_band || '0%')}>
                                {qualityKpi?.kpi_quality?.bonus_band || '0%'}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="col-md-6 col-xl-3">
                          <div className="border rounded p-3 h-100">
                            <div className="text-muted small mb-1">Rinnovo Adj (60%)</div>
                            <div className="fw-semibold">
                              {qualityKpi?.kpi_rinnovo_adj?.value != null ? `${Number(qualityKpi.kpi_rinnovo_adj.value).toFixed(1)}%` : '—'}
                            </div>
                            <div className="mt-2">
                              <span className="badge" style={getBandBadgeStyle(qualityKpi?.kpi_rinnovo_adj?.bonus_band || '0%')}>
                                {qualityKpi?.kpi_rinnovo_adj?.bonus_band || '0%'}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="col-md-6 col-xl-3">
                          <div className="border rounded p-3 h-100">
                            <div className="text-muted small mb-1">Bonus Composito</div>
                            <div className="fw-semibold">
                              {qualityKpi?.final_bonus_percentage != null ? `${Number(qualityKpi.final_bonus_percentage).toFixed(2)}%` : '—'}
                            </div>
                          </div>
                        </div>
                        <div className="col-md-6 col-xl-3">
                          <div className="border rounded p-3 h-100">
                            <div className="text-muted small mb-1">Bonus Finale</div>
                            <div className="fw-semibold">
                              {qualityKpi?.final_bonus_after_malus != null ? `${Number(qualityKpi.final_bonus_after_malus).toFixed(2)}%` : '—'}
                            </div>
                            {qualityKpi?.super_malus?.applied ? (
                              <div className="mt-2">
                                <span className="badge" style={getSuperMalusBadgeStyle(qualityKpi?.super_malus?.percentage || 0)}>
                                  Super Malus {qualityKpi?.super_malus?.percentage || 0}%
                                </span>
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </div>

                      {qualityKpi?.super_malus?.applied && qualityKpi?.super_malus?.reason ? (
                        <div className="alert alert-danger py-2 mb-3">
                          <small><strong>Motivo Super Malus:</strong> {qualityKpi.super_malus.reason}</small>
                        </div>
                      ) : null}

                      <div className="table-responsive border rounded">
                        <table className="table table-sm align-middle mb-0">
                          <thead className="table-light">
                            <tr>
                              <th>Settimana</th>
                              <th>Quality Final</th>
                              <th>Quality Mese</th>
                              <th>Quality Trim</th>
                            </tr>
                          </thead>
                          <tbody>
                            {qualityTrendRows.length === 0 ? (
                              <tr>
                                <td colSpan={4} className="text-center text-muted py-4">Nessun trend disponibile</td>
                              </tr>
                            ) : (
                              qualityTrendRows.map((row) => (
                                <tr key={row.label}>
                                  <td data-label="Settimana">{row.label}</td>
                                  <td data-label="Quality Final" style={row.quality_final != null ? getScoreStyle(row.quality_final) : {}}>
                                    {row.quality_final != null ? Number(row.quality_final).toFixed(2) : '—'}
                                  </td>
                                  <td data-label="Quality Mese">{row.quality_month != null ? Number(row.quality_month).toFixed(2) : '—'}</td>
                                  <td data-label="Quality Trim">{row.quality_trim != null ? Number(row.quality_trim).toFixed(2) : '—'}</td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </div>
              )}

              {activeTab === 'capienza' && (
                <div>
                  {capacityLoading ? (
                    <div className="text-center py-4">
                      <div className="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                      Caricamento capienza...
                    </div>
                  ) : capacityError ? (
                    <div className="alert alert-warning mb-0">{capacityError}</div>
                  ) : !capacityRow ? (
                    <div className="alert alert-light border mb-0">Nessun dato capienza disponibile per questo professionista.</div>
                  ) : (
                    <div className="table-responsive border rounded">
                      <table className="table table-sm align-middle mb-0">
                        <thead className="table-light">
                          <tr>
                            <th>Professionista</th>
                            <th>Capienza contrattuale</th>
                            <th>Clienti assegnati</th>
                            <th>% Capienza</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td className="fw-medium">{capacityRow.full_name}</td>
                            <td style={{ minWidth: 220 }}>
                              {canEditCapacity ? (
                                <div className="d-flex gap-2">
                                  <input
                                    type="number"
                                    min="0"
                                    className="form-control form-control-sm"
                                    value={capacityInput}
                                    onChange={(e) => setCapacityInput(e.target.value)}
                                  />
                                  <button
                                    className="btn btn-sm btn-primary"
                                    disabled={capacitySaving}
                                    onClick={async () => {
                                      if (capacityInput === '' || Number.isNaN(Number(capacityInput))) return;
                                      setCapacitySaving(true);
                                      try {
                                        const res = await teamService.updateProfessionalCapacity(user.id, Number(capacityInput));
                                        setCapacityRow(res.row);
                                        setCapacityInput(String(res.row.capienza_contrattuale ?? ''));
                                      } catch (err) {
                                        alert(err?.response?.data?.message || 'Errore nel salvataggio della capienza contrattuale');
                                      } finally {
                                        setCapacitySaving(false);
                                      }
                                    }}
                                  >
                                    {capacitySaving ? '...' : 'Salva'}
                                  </button>
                                </div>
                              ) : (
                                <span>{capacityRow.capienza_contrattuale}</span>
                              )}
                            </td>
                            <td>
                              <span className={`badge ${capacityRow.is_over_capacity ? 'bg-danger' : 'bg-light text-dark border'}`}>
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
      </div>

      <CheckResponseDetailModal
        show={showCheckResponseModal && !!selectedCheckResponse}
        onClose={() => { setShowCheckResponseModal(false); setSelectedCheckResponse(null); }}
        response={selectedCheckResponse}
        loading={loadingCheckDetail}
        onlyProfessionalRole={checkRatingConfig?.role ?? undefined}
      />
    </div>
  );
}

export default Profilo;

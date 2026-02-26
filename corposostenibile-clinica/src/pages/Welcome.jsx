import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import dashboardService from '../services/dashboardService';
import teamService from '../services/teamService';
import trialUserService from '../services/trialUserService';
import trainingService from '../services/trainingService';
import clientiService from '../services/clientiService';
import checkService from '../services/checkService';
import taskService from '../services/taskService';
import logoFoglia from '../images/logo_foglia.png';
import { isProfessionistaStandard, isTeamLeaderRestricted, normalizeSpecialtyGroup } from '../utils/rbacScope';

// Tab configuration
const TABS = [
  { key: 'panoramica', label: 'Panoramica', icon: 'ri-dashboard-line' },
  { key: 'chat', label: 'Chat', icon: 'ri-chat-3-line' },
  { key: 'formazione', label: 'Formazione', icon: 'ri-book-open-line' },
  { key: 'pazienti', label: 'Pazienti', icon: 'ri-group-line' },
  { key: 'check', label: 'Check', icon: 'ri-checkbox-circle-line' },
  { key: 'quality', label: 'Quality', icon: 'ri-star-line' },
  { key: 'professionisti', label: 'Professionisti', icon: 'ri-user-star-line' },
];

function RoleScopedWelcome({ user, mode }) {
  const isTeamLeaderMode = mode === 'team_leader';
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [scopeData, setScopeData] = useState(null);
  const [taskStats, setTaskStats] = useState(null);
  const [recentTasks, setRecentTasks] = useState([]);
  const [trainingSummary, setTrainingSummary] = useState({
    myTrainings: 0,
    pendingMyTrainings: 0,
    myRequests: 0,
    receivedRequests: 0,
  });

  const loadScopedData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const requests = [
        teamService.getAdminDashboardStats(),
        taskService.getStats(),
        taskService.getAll({ completed: 'false' }),
        trainingService.getMyTrainings(),
        trainingService.getMyRequests(),
      ];

      if (isTeamLeaderMode) {
        requests.push(trainingService.getReceivedRequests());
      }

      const [
        dashboardRes,
        taskStatsRes,
        tasksRes,
        myTrainingsRes,
        myRequestsRes,
        receivedRequestsRes,
      ] = await Promise.all(requests);

      setScopeData(dashboardRes);
      setTaskStats(taskStatsRes || null);
      setRecentTasks(Array.isArray(tasksRes) ? tasksRes.slice(0, 6) : []);
      const myTrainings = myTrainingsRes?.trainings || [];
      const myRequests = myRequestsRes?.requests || [];
      const receivedRequests = receivedRequestsRes?.requests || [];
      setTrainingSummary({
        myTrainings: myTrainings.length,
        pendingMyTrainings: myTrainings.filter(t => !t.acknowledged_at && !t.is_acknowledged).length,
        myRequests: myRequests.length,
        receivedRequests: receivedRequests.length,
      });
    } catch (err) {
      console.error('Error loading scoped dashboard:', err);
      setError('Errore nel caricamento della dashboard');
    } finally {
      setLoading(false);
    }
  }, [isTeamLeaderMode]);

  useEffect(() => {
    loadScopedData();
  }, [loadScopedData]);

  const scopeTitle = isTeamLeaderMode ? 'Dashboard Team Leader' : 'Dashboard Professionista';
  const scopeSubtitle = isTeamLeaderMode ? 'Panoramica operativa del tuo team' : 'Panoramica personale';
  const teamSummary = scopeData?.teamsSummary || [];
  const kpi = scopeData?.kpi || {};
  const clientLoad = scopeData?.clientLoad || {};
  const tlSpecialtyGroup = normalizeSpecialtyGroup(user?.specialty);
  const tlSpecialtyLoad = tlSpecialtyGroup ? clientLoad?.[tlSpecialtyGroup] : null;
  const tlSpecialtyLabel = {
    nutrizione: 'Nutrizione',
    coach: 'Coach',
    psicologia: 'Psicologia',
    medico: 'Medico',
  }[tlSpecialtyGroup] || 'Specialità';

  const cards = isTeamLeaderMode
    ? [
        { label: 'Team gestiti', value: teamSummary.length, icon: 'ri-team-line', color: '#3b82f6' },
        { label: 'Membri team', value: kpi.totalActive ?? 0, icon: 'ri-user-star-line', color: '#22c55e' },
        { label: 'Task aperti team', value: taskStats?.total_open ?? 0, icon: 'ri-task-line', color: '#f97316' },
        { label: `Pazienti attivi (${tlSpecialtyLabel})`, value: tlSpecialtyLoad?.clients ?? 0, icon: 'ri-group-line', color: '#8b5cf6' },
      ]
    : [
        { label: 'Task aperti', value: taskStats?.total_open ?? 0, icon: 'ri-task-line', color: '#3b82f6' },
        { label: 'Training ricevuti', value: trainingSummary.myTrainings, icon: 'ri-book-open-line', color: '#22c55e' },
        { label: 'Training da leggere', value: trainingSummary.pendingMyTrainings, icon: 'ri-notification-3-line', color: '#f97316' },
        { label: 'Mie richieste formazione', value: trainingSummary.myRequests, icon: 'ri-question-answer-line', color: '#8b5cf6' },
      ];

  return (
    <>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1" style={{ fontWeight: 700, color: '#1e293b' }}>
            Ciao, {user?.first_name || 'Utente'}!
          </h4>
          <p className="text-muted mb-0">{scopeSubtitle}</p>
        </div>
        <button onClick={loadScopedData} className="btn btn-light d-flex align-items-center gap-2" style={{ borderRadius: '12px' }}>
          <i className="ri-refresh-line"></i>
          Aggiorna
        </button>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
        <div className="card-body p-4">
          <div className="d-flex align-items-start justify-content-between gap-3 flex-wrap">
            <div>
              <h5 className="mb-1" style={{ color: '#1e293b' }}>{scopeTitle}</h5>
              <p className="text-muted mb-0" style={{ fontSize: '13px' }}>
                {isTeamLeaderMode
                  ? 'Metriche e liste operative limitate ai membri del tuo team/specialità.'
                  : 'Metriche e attività limitate al tuo perimetro personale.'}
              </p>
            </div>
            <div className="d-flex gap-2 flex-wrap">
              <Link to="/task" className="btn btn-outline-primary btn-sm"><i className="ri-task-line me-1"></i>Task</Link>
              <Link to="/formazione" className="btn btn-outline-success btn-sm"><i className="ri-book-open-line me-1"></i>Formazione</Link>
              <Link to="/clienti-lista" className="btn btn-outline-secondary btn-sm"><i className="ri-group-line me-1"></i>Pazienti</Link>
              {isTeamLeaderMode && <Link to="/check-azienda" className="btn btn-outline-warning btn-sm"><i className="ri-checkbox-circle-line me-1"></i>Check</Link>}
              {!isTeamLeaderMode && <Link to="/profilo?tab=check" className="btn btn-outline-warning btn-sm"><i className="ri-checkbox-circle-line me-1"></i>Miei Check</Link>}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger">{error}</div>
      )}

      <div className="row g-3 mb-4 align-items-start">
        {cards.map((card) => (
          <div key={card.label} className="col-xl-3 col-sm-6">
            <div className="card border-0 shadow-sm" style={{ borderRadius: '14px', height: 'auto' }}>
              <div className="card-body" style={{ padding: '14px 16px' }}>
                <div className="d-flex justify-content-between align-items-center">
                  <div>
                    <div className="text-muted small">{card.label}</div>
                    <div className="fw-bold" style={{ fontSize: '1.5rem', color: '#1e293b' }}>
                      {loading ? '…' : card.value}
                    </div>
                  </div>
                  <div className="rounded-circle d-flex align-items-center justify-content-center" style={{ width: 42, height: 42, background: `${card.color}18`, color: card.color }}>
                    <i className={`${card.icon} fs-5`}></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="row g-3 align-items-start">
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 pb-0">
              <h6 className="mb-0" style={{ color: '#1e293b' }}>
                <i className="ri-task-line me-2"></i>
                Task aperti recenti
              </h6>
            </div>
            <div className="card-body">
              {loading ? (
                <div className="text-muted">Caricamento...</div>
              ) : recentTasks.length === 0 ? (
                <div className="text-muted">Nessun task aperto.</div>
              ) : (
                <div className="d-flex flex-column gap-2" style={{ maxHeight: '420px', overflowY: 'auto' }}>
                  {recentTasks.map((task) => (
                    <div key={task.id} className="d-flex align-items-center justify-content-between border rounded-3 p-2">
                      <div className="pe-3">
                        <div className="fw-medium" style={{ color: '#1e293b' }}>{task.title || 'Task'}</div>
                        <div className="text-muted small">{task.client_name || task.category || '—'}</div>
                      </div>
                      <span className="badge bg-light text-dark">{task.priority || '—'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-5">
          {isTeamLeaderMode ? (
            <>
              <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-white border-0 pb-0">
                  <h6 className="mb-0" style={{ color: '#1e293b' }}>
                    <i className="ri-team-line me-2"></i>
                    Team gestiti
                  </h6>
                </div>
                <div className="card-body">
                  {loading ? (
                    <div className="text-muted">Caricamento...</div>
                  ) : teamSummary.length === 0 ? (
                    <div className="text-muted">Nessun team associato.</div>
                  ) : (
                    <div className="d-flex flex-column gap-2">
                      {teamSummary.map((team) => (
                        <div key={team.id} className="d-flex align-items-center justify-content-between border rounded-3 p-2">
                          <div>
                            <div className="fw-medium" style={{ color: '#1e293b' }}>{team.name}</div>
                            <div className="small text-muted">
                              {team.team_type || 'team'} • {team.member_count || 0} membri
                            </div>
                          </div>
                          <Link to="/team-lista" className="btn btn-light btn-sm">Apri</Link>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-white border-0 pb-0">
                  <h6 className="mb-0" style={{ color: '#1e293b' }}>
                    <i className="ri-group-line me-2"></i>
                    Pazienti del tuo ambito ({tlSpecialtyLabel})
                  </h6>
                </div>
                <div className="card-body">
                  <div className="d-flex justify-content-between mb-2">
                    <span className="text-muted small">Pazienti attivi/in pausa</span>
                    <span className="fw-semibold">{loading ? '…' : (tlSpecialtyLoad?.clients ?? 0)}</span>
                  </div>
                  <div className="d-flex justify-content-between mb-2">
                    <span className="text-muted small">Professionisti del team</span>
                    <span className="fw-semibold">{loading ? '…' : (tlSpecialtyLoad?.professionals ?? 0)}</span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted small">Carico medio</span>
                    <span className="fw-semibold">{loading ? '…' : `${tlSpecialtyLoad?.avgLoad ?? 0} clienti/prof.`}</span>
                  </div>
                </div>
              </div>

              <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-white border-0 pb-0">
                  <h6 className="mb-0" style={{ color: '#1e293b' }}>
                    <i className="ri-book-open-line me-2"></i>
                    Formazione team
                  </h6>
                </div>
                <div className="card-body">
                  <div className="d-flex justify-content-between mb-2">
                    <span className="text-muted small">Richieste ricevute</span>
                    <span className="fw-semibold">{loading ? '…' : trainingSummary.receivedRequests}</span>
                  </div>
                  <div className="d-flex justify-content-between mb-2">
                    <span className="text-muted small">Mie richieste</span>
                    <span className="fw-semibold">{loading ? '…' : trainingSummary.myRequests}</span>
                  </div>
                  <div className="d-flex justify-content-between">
                    <span className="text-muted small">Training da leggere (miei)</span>
                    <span className="fw-semibold">{loading ? '…' : trainingSummary.pendingMyTrainings}</span>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
              <div className="card-header bg-white border-0 pb-0">
                <h6 className="mb-0" style={{ color: '#1e293b' }}>
                  <i className="ri-book-open-line me-2"></i>
                  Formazione
                </h6>
              </div>
              <div className="card-body">
                <div className="d-flex justify-content-between mb-2">
                  <span className="text-muted small">Training ricevuti</span>
                  <span className="fw-semibold">{loading ? '…' : trainingSummary.myTrainings}</span>
                </div>
                <div className="d-flex justify-content-between mb-2">
                  <span className="text-muted small">Da leggere</span>
                  <span className="fw-semibold">{loading ? '…' : trainingSummary.pendingMyTrainings}</span>
                </div>
                <div className="d-flex justify-content-between">
                  <span className="text-muted small">Mie richieste</span>
                  <span className="fw-semibold">{loading ? '…' : trainingSummary.myRequests}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function LegacyWelcomeDashboard() {
  const { user } = useOutletContext();
  const [activeTab, setActiveTab] = useState('panoramica');
  const isAdminOrCco = Boolean(user?.is_admin || user?.role === 'admin' || user?.specialty === 'cco');
  const isTeamLeader = user?.role === 'team_leader';
  const isRestrictedTeamLeaderDashboard = Boolean(isTeamLeader && !isAdminOrCco);
  const isProfessionistaDashboard = isProfessionistaStandard(user);

  // Independent loading states for progressive rendering
  const [customerStats, setCustomerStats] = useState(null);
  const [customerLoading, setCustomerLoading] = useState(true);

  const [teamStats, setTeamStats] = useState(null);
  const [teamLoading, setTeamLoading] = useState(true);

  const [trialStats, setTrialStats] = useState(null);
  const [trialLoading, setTrialLoading] = useState(true);

  const [checkStats, setCheckStats] = useState(null);
  const [negativeChecks, setNegativeChecks] = useState([]);
  const [rankings, setRankings] = useState(null);
  const [teamRatings, setTeamRatings] = useState(null);
  const [checkLoading, setCheckLoading] = useState(true);

  const [negativePage, setNegativePage] = useState(1);
  const NEGATIVE_PER_PAGE = 5;

  // Training dashboard state
  const [trainingData, setTrainingData] = useState(null);
  const [trainingLoading, setTrainingLoading] = useState(false);
  const [trainingLoaded, setTrainingLoaded] = useState(false);

  // Pazienti dashboard state
  const [pazientiData, setPazientiData] = useState(null);
  const [pazientiLoading, setPazientiLoading] = useState(false);
  const [pazientiLoaded, setPazientiLoaded] = useState(false);
  const [pazientiError, setPazientiError] = useState(null);

  // Check dashboard state
  const [checkDashData, setCheckDashData] = useState(null);
  const [checkDashLoading, setCheckDashLoading] = useState(false);
  const [checkDashLoaded, setCheckDashLoaded] = useState(false);
  const [checkDashError, setCheckDashError] = useState(null);

  // Professionisti dashboard state
  const [profData, setProfData] = useState(null);
  const [profLoading, setProfLoading] = useState(false);
  const [profLoaded, setProfLoaded] = useState(false);
  const [profError, setProfError] = useState(null);

  const loadTrainingData = useCallback(async () => {
    if (trainingLoaded) return;
    setTrainingLoading(true);
    try {
      const data = await trainingService.getDashboardStats();
      setTrainingData(data);
      setTrainingLoaded(true);
    } catch (err) {
      console.error('Error loading training stats:', err);
    } finally {
      setTrainingLoading(false);
    }
  }, [trainingLoaded]);

  const loadPazientiData = useCallback(async () => {
    if (pazientiLoaded) return;
    setPazientiLoading(true);
    setPazientiError(null);
    try {
      const data = await clientiService.getAdminDashboardStats();
      setPazientiData(data);
      setPazientiLoaded(true);
    } catch (err) {
      console.error('Error loading pazienti stats:', err);
      setPazientiError('Errore nel caricamento dei dati pazienti');
    } finally {
      setPazientiLoading(false);
    }
  }, [pazientiLoaded]);

  const loadCheckDashData = useCallback(async () => {
    if (checkDashLoaded) return;
    setCheckDashLoading(true);
    setCheckDashError(null);
    try {
      const data = await checkService.getAdminDashboardStats();
      setCheckDashData(data);
      setCheckDashLoaded(true);
    } catch (err) {
      console.error('Error loading check stats:', err);
      setCheckDashError('Errore nel caricamento dei dati check');
    } finally {
      setCheckDashLoading(false);
    }
  }, [checkDashLoaded]);

  const loadProfData = useCallback(async () => {
    if (profLoaded) return;
    setProfLoading(true);
    setProfError(null);
    try {
      const data = await teamService.getAdminDashboardStats();
      setProfData(data);
      setProfLoaded(true);
    } catch (err) {
      console.error('Error loading professionisti stats:', err);
      setProfError('Errore nel caricamento dei dati professionisti');
    } finally {
      setProfLoading(false);
    }
  }, [profLoaded]);

  // Load tab data when tab becomes active
  useEffect(() => {
    if (isRestrictedTeamLeaderDashboard) return;
    if (activeTab === 'formazione' && !trainingLoaded) {
      loadTrainingData();
    }
    if (activeTab === 'pazienti' && !pazientiLoaded) {
      loadPazientiData();
    }
    if (activeTab === 'check' && !checkDashLoaded) {
      loadCheckDashData();
    }
    if ((activeTab === 'professionisti' || activeTab === 'quality') && !profLoaded) {
      loadProfData();
    }
  }, [activeTab, trainingLoaded, loadTrainingData, pazientiLoaded, loadPazientiData, checkDashLoaded, loadCheckDashData, profLoaded, loadProfData, isRestrictedTeamLeaderDashboard]);

  // Load all data in parallel, each section independent
  useEffect(() => {
    if (isRestrictedTeamLeaderDashboard) return;
    loadCustomerStats();
    loadTeamStats();
    loadTrialStats();
    loadCheckData();
  }, [isRestrictedTeamLeaderDashboard]);

  const loadCustomerStats = async () => {
    try {
      const data = await dashboardService.getCustomerStats();
      setCustomerStats(data);
    } catch (err) {
      console.error('Error loading customer stats:', err);
    } finally {
      setCustomerLoading(false);
    }
  };

  const loadTeamStats = async () => {
    try {
      const data = await teamService.getStats();
      setTeamStats(data);
    } catch (err) {
      console.error('Error loading team stats:', err);
    } finally {
      setTeamLoading(false);
    }
  };

  const loadTrialStats = async () => {
    try {
      const data = await trialUserService.getAll();
      setTrialStats(data.stats || null);
    } catch (err) {
      console.error('Error loading trial stats:', err);
    } finally {
      setTrialLoading(false);
    }
  };

  const loadCheckData = async () => {
    try {
      const [checkData, teams] = await Promise.all([
        dashboardService.getCheckStats(),
        dashboardService.getTeamsWithMembers()
      ]);

      setCheckStats(checkData);

      if (checkData?.responses) {
        const negative = dashboardService.filterNegativeChecks(checkData.responses);
        setNegativeChecks(negative);

        const ranks = dashboardService.calculateProfessionalRankings(checkData.responses);
        setRankings(ranks);

        if (teams && teams.length > 0) {
          const teamRatingsData = dashboardService.calculateTeamRatings(checkData.responses, teams);
          setTeamRatings(teamRatingsData);
        }
      }
    } catch (err) {
      console.error('Error loading check data:', err);
    } finally {
      setCheckLoading(false);
    }
  };

  const refreshAll = () => {
    if (isRestrictedTeamLeaderDashboard) return;
    setCustomerLoading(true);
    setTeamLoading(true);
    setTrialLoading(true);
    setCheckLoading(true);
    loadCustomerStats();
    loadTeamStats();
    loadTrialStats();
    loadCheckData();
  };

  const visibleTabs = useMemo(() => {
    if (isRestrictedTeamLeaderDashboard) {
      return TABS.filter((tab) => ['panoramica', 'chat'].includes(tab.key));
    }
    return TABS;
  }, [isRestrictedTeamLeaderDashboard]);

  useEffect(() => {
    if (!visibleTabs.some((tab) => tab.key === activeTab)) {
      setActiveTab('panoramica');
    }
  }, [visibleTabs, activeTab]);

  return (
    <>
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1" style={{ fontWeight: 700, color: '#1e293b' }}>
            Ciao, {user?.first_name || 'Admin'}!
          </h4>
          <p className="text-muted mb-0">Panoramica Piattaforma</p>
        </div>
        <button
          onClick={refreshAll}
          className="btn btn-light d-flex align-items-center gap-2"
          style={{ borderRadius: '12px' }}
        >
          <i className="ri-refresh-line"></i>
          Aggiorna
        </button>
      </div>

      {/* Tabs Navigation */}
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '12px' }}>
        <div className="card-body p-2">
          <div className="d-flex flex-wrap gap-2">
            {visibleTabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className="btn"
                style={{
                  borderRadius: '8px',
                  padding: '10px 20px',
                  background: activeTab === tab.key
                    ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
                    : 'transparent',
                  color: activeTab === tab.key ? 'white' : '#64748b',
                  fontWeight: activeTab === tab.key ? 600 : 500,
                  fontSize: '14px',
                  border: 'none',
                  transition: 'all 0.2s ease',
                }}
              >
                <i className={`${tab.icon} me-2`}></i>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'panoramica' ? (
        <>
          {!isRestrictedTeamLeaderDashboard && (
            <div className="row g-3 mb-4">
              {[
                { label: 'Pazienti Totali', value: customerStats?.total_clienti, icon: 'ri-group-line', bg: 'primary' },
                { label: 'Nutrizione Attivi', value: customerStats?.nutrizione_attivo, icon: 'ri-restaurant-line', bg: 'success' },
                { label: 'Coach Attivi', value: customerStats?.coach_attivo, icon: 'ri-run-line', bg: 'warning' },
                { label: 'Psicologia Attivi', value: customerStats?.psicologia_attivo, icon: 'ri-mental-health-line', customBg: '#8b5cf6' },
                { label: 'Nuovi questo Mese', value: customerStats?.kpi?.new_month, icon: 'ri-user-add-line', customBg: '#06b6d4' },
              ].map((stat, idx) => (
                <div key={idx} className="col-xl col-sm-6">
                  <div
                    className={`card border-0 shadow-sm ${stat.bg ? `bg-${stat.bg}` : ''}`}
                    style={stat.customBg ? { backgroundColor: stat.customBg } : {}}
                  >
                    <div className="card-body py-3">
                      <div className="d-flex align-items-center justify-content-between">
                        <div>
                          <h3 className="text-white mb-0 fw-bold">
                            {customerLoading ? <SkeletonNumber /> : (stat.value ?? 0)}
                          </h3>
                          <span className="text-white opacity-75 small">{stat.label}</span>
                        </div>
                        <div
                          className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center"
                          style={{ width: '48px', height: '48px' }}
                        >
                          <i className={`${stat.icon} text-white fs-4`}></i>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* SEZIONE 2: Quick Nav + Team/Trial KPI */}
          <div className="row g-3 mb-4">
            {/* Quick Navigation */}
            <div className={isRestrictedTeamLeaderDashboard ? 'col-12' : 'col-lg-8'}>
              <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                  <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                    <i className="ri-apps-line me-2 text-primary"></i>
                    Accesso Rapido
                  </h6>
                </div>
                <div className="card-body pt-0 px-4 pb-4">
                  <div className="row g-2">
                    {QUICK_LINKS.map((link, idx) => (
                      <div key={idx} className="col-6 col-md-4 col-xl-3">
                        <Link
                          to={link.to}
                          className="d-flex align-items-center gap-2 p-3 text-decoration-none rounded-3"
                          style={{
                            background: link.bgColor,
                            transition: 'transform 0.15s, box-shadow 0.15s',
                          }}
                          onMouseOver={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)'; }}
                          onMouseOut={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}
                        >
                          <div
                            className="d-flex align-items-center justify-content-center rounded-circle"
                            style={{ width: '36px', height: '36px', background: link.iconBg, flexShrink: 0 }}
                          >
                            <i className={link.icon} style={{ color: link.color, fontSize: '16px' }}></i>
                          </div>
                          <span style={{ color: '#334155', fontWeight: 500, fontSize: '13px' }}>{link.label}</span>
                        </Link>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {!isRestrictedTeamLeaderDashboard && (
              <div className="col-lg-4">
                <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                  <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                    <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                      <i className="ri-team-line me-2 text-info"></i>
                      Team
                    </h6>
                  </div>
                  <div className="card-body pt-0 px-4 pb-3">
                    {teamLoading ? (
                      <SkeletonList count={4} />
                    ) : (
                      <div className="d-flex flex-column gap-2">
                        <StatRow label="Membri Attivi" value={teamStats?.total_active || 0} color="#3b82f6" />
                        <StatRow label="Team Leaders" value={teamStats?.total_team_leaders || 0} color="#8b5cf6" />
                        <StatRow label="In Prova" value={teamStats?.total_trial || 0} color="#f59e0b" />
                        <StatRow label="Esterni" value={teamStats?.total_external || 0} color="#64748b" />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {isRestrictedTeamLeaderDashboard && (
            <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
              <div className="card-body py-4 px-4">
                <div className="d-flex align-items-start gap-3">
                  <div
                    className="d-flex align-items-center justify-content-center rounded-circle"
                    style={{ width: '42px', height: '42px', background: '#eff6ff', color: '#2563eb', flexShrink: 0 }}
                  >
                    <i className="ri-shield-user-line fs-5"></i>
                  </div>
                  <div>
                    <h6 className="mb-1" style={{ color: '#1e293b' }}>Vista Team Leader limitata</h6>
                    <p className="text-muted mb-0" style={{ fontSize: '13px' }}>
                      Le metriche globali di dashboard (KPI cross-dipartimento, medie altri team, totali globali) sono nascoste.
                      Verranno mostrate solo sezioni coerenti con il tuo team/dipartimento nei prossimi step del refactor.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {!isRestrictedTeamLeaderDashboard && (
            <>
              <div className="row g-3 mb-4">
                <div className="col-12">
                  <h5 className="mb-3" style={{ fontWeight: 600, color: '#1e293b' }}>
                    <i className="ri-bar-chart-grouped-line me-2"></i>
                    Valutazioni Medie per Team (Ultimo Mese)
                  </h5>
                </div>
                {checkLoading ? (
                  <>
                    <div className="col-lg-4"><SkeletonCard height="120px" /></div>
                    <div className="col-lg-4"><SkeletonCard height="120px" /></div>
                    <div className="col-lg-4"><SkeletonCard height="120px" /></div>
                  </>
                ) : (
                  <>
                    <RatingCard label="Team Nutrizione" value={checkStats?.stats?.avg_nutrizionista} icon="ri-heart-pulse-line" color="#22c55e" bgColor="#dcfce7" />
                    <RatingCard label="Team Coach" value={checkStats?.stats?.avg_coach} icon="ri-run-line" color="#f97316" bgColor="#ffedd5" />
                    <RatingCard label="Team Psicologia" value={checkStats?.stats?.avg_psicologo} icon="ri-mental-health-line" color="#ec4899" bgColor="#fce7f3" />
                  </>
                )}
              </div>

              {!checkLoading && teamRatings && (teamRatings.nutrizione.length > 0 || teamRatings.coach.length > 0 || teamRatings.psicologia.length > 0) && (
                <div className="row g-3 mb-4">
                  <div className="col-12">
                    <h5 className="mb-3" style={{ fontWeight: 600, color: '#1e293b' }}>
                      <i className="ri-team-line me-2"></i>
                      Valutazioni per Singolo Team (Ultimo Mese)
                    </h5>
                  </div>
                  {teamRatings.nutrizione.length > 0 && (
                    <div className="col-lg-4">
                      <TeamRatingsList title="Team Nutrizione" teams={teamRatings.nutrizione} icon="ri-heart-pulse-line" color="#22c55e" bgColor="#dcfce7" />
                    </div>
                  )}
                  {teamRatings.coach.length > 0 && (
                    <div className="col-lg-4">
                      <TeamRatingsList title="Team Coach" teams={teamRatings.coach} icon="ri-run-line" color="#f97316" bgColor="#ffedd5" />
                    </div>
                  )}
                  {teamRatings.psicologia.length > 0 && (
                    <div className="col-lg-4">
                      <TeamRatingsList title="Team Psicologia" teams={teamRatings.psicologia} icon="ri-mental-health-line" color="#ec4899" bgColor="#fce7f3" />
                    </div>
                  )}
                </div>
              )}

              {!checkLoading && (
                <NegativeChecksTable
                  negativeChecks={negativeChecks}
                  negativePage={negativePage}
                  setNegativePage={setNegativePage}
                  perPage={NEGATIVE_PER_PAGE}
                />
              )}

              {!checkLoading && rankings && (
                <>
                  <div className="row g-3 mb-4">
                    <div className="col-12">
                      <h5 className="mb-3" style={{ fontWeight: 600, color: '#1e293b' }}>
                        <i className="ri-trophy-line me-2 text-warning"></i>
                        Top 5 Professionisti (Ultimo Mese)
                      </h5>
                    </div>
                    <div className="col-lg-4">
                      <RankingTable title="Nutrizione" professionals={rankings.nutrizione?.top || []} color="#22c55e" bgColor="#dcfce7" icon="ri-heart-pulse-line" isTop={true} />
                    </div>
                    <div className="col-lg-4">
                      <RankingTable title="Coach" professionals={rankings.coach?.top || []} color="#f97316" bgColor="#ffedd5" icon="ri-run-line" isTop={true} />
                    </div>
                    <div className="col-lg-4">
                      <RankingTable title="Psicologia" professionals={rankings.psicologia?.top || []} color="#ec4899" bgColor="#fce7f3" icon="ri-mental-health-line" isTop={true} />
                    </div>
                  </div>

                  <div className="row g-3 mb-4">
                    <div className="col-12">
                      <h5 className="mb-3" style={{ fontWeight: 600, color: '#1e293b' }}>
                        <i className="ri-arrow-down-circle-line me-2 text-danger"></i>
                        Professionisti da Migliorare (Ultimo Mese)
                      </h5>
                    </div>
                    <div className="col-lg-4">
                      <RankingTable title="Nutrizione" professionals={rankings.nutrizione?.bottom || []} color="#22c55e" bgColor="#dcfce7" icon="ri-heart-pulse-line" isTop={false} />
                    </div>
                    <div className="col-lg-4">
                      <RankingTable title="Coach" professionals={rankings.coach?.bottom || []} color="#f97316" bgColor="#ffedd5" icon="ri-run-line" isTop={false} />
                    </div>
                    <div className="col-lg-4">
                      <RankingTable title="Psicologia" professionals={rankings.psicologia?.bottom || []} color="#ec4899" bgColor="#fce7f3" icon="ri-mental-health-line" isTop={false} />
                    </div>
                  </div>
                </>
              )}
            </>
          )}
        </>
      ) : activeTab === 'pazienti' ? (
        <PazientiTab
          data={pazientiData}
          loading={pazientiLoading}
          error={pazientiError}
          onRetry={() => { setPazientiLoaded(false); loadPazientiData(); }}
        />
      ) : activeTab === 'check' ? (
        <CheckTab
          data={checkDashData}
          loading={checkDashLoading}
          error={checkDashError}
          onRetry={() => { setCheckDashLoaded(false); loadCheckDashData(); }}
        />
      ) : activeTab === 'professionisti' ? (
        <ProfessionistiTab
          data={profData}
          loading={profLoading}
          error={profError}
          onRetry={() => { setProfLoaded(false); loadProfData(); }}
        />
      ) : activeTab === 'formazione' ? (
        <FormazioneTab data={trainingData} loading={trainingLoading} />
      ) : activeTab === 'quality' ? (
        <QualityTab
          data={profData}
          loading={profLoading}
          error={profError}
          onRetry={() => { setProfLoaded(false); loadProfData(); }}
        />
      ) : (
        <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
          <div className="card-body text-center py-5">
            <h5 className="text-muted mb-3">In implementazione</h5>
          </div>
        </div>
      )}
    </>
  );
}

function Welcome() {
  const { user } = useOutletContext();

  if (isTeamLeaderRestricted(user)) {
    return <RoleScopedWelcome user={user} mode="team_leader" />;
  }

  if (isProfessionistaStandard(user)) {
    return <RoleScopedWelcome user={user} mode="professionista" />;
  }

  return <LegacyWelcomeDashboard />;
}

// ==================== FORMAZIONE TAB ====================

const REVIEW_TYPE_CONFIG = {
  settimanale: { label: 'Settimanale', color: '#3b82f6', bg: '#dbeafe', icon: 'ri-calendar-line' },
  mensile: { label: 'Mensile', color: '#8b5cf6', bg: '#ede9fe', icon: 'ri-calendar-check-line' },
  progetto: { label: 'Progetto', color: '#f59e0b', bg: '#fef3c7', icon: 'ri-folder-line' },
  miglioramento: { label: 'Miglioramento', color: '#ef4444', bg: '#fee2e2', icon: 'ri-arrow-up-circle-line' },
};

function FormazioneTab({ data, loading }) {
  const [recentPage, setRecentPage] = useState(1);
  const RECENT_PER_PAGE = 5;

  if (loading || !data) {
    return (
      <div className="row g-3">
        <div className="col-lg-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-lg-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-lg-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-lg-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-lg-8"><SkeletonCard height="300px" /></div>
        <div className="col-lg-4"><SkeletonCard height="300px" /></div>
      </div>
    );
  }

  const { kpi, byType, monthlyTrend, topReviewers, topReviewees, recentTrainings } = data;

  // Calcola il massimo per il grafico a barre
  const maxMonthly = Math.max(...(monthlyTrend || []).map(m => m.total), 1);

  // Paginazione recent trainings
  const totalRecentPages = Math.ceil((recentTrainings || []).length / RECENT_PER_PAGE);
  const recentStartIdx = (recentPage - 1) * RECENT_PER_PAGE;
  const paginatedRecent = (recentTrainings || []).slice(recentStartIdx, recentStartIdx + RECENT_PER_PAGE);

  // Month-over-month change
  const monthChange = kpi.lastMonth > 0
    ? Math.round(((kpi.thisMonth - kpi.lastMonth) / kpi.lastMonth) * 100)
    : (kpi.thisMonth > 0 ? 100 : 0);

  return (
    <>
      {/* KPI Cards */}
      <div className="row g-3 mb-4">
        {[
          { label: 'Training Totali', value: kpi.totalTrainings, icon: 'ri-book-open-line', bg: '#3b82f6' },
          { label: 'Confermati', value: kpi.totalAcknowledged, icon: 'ri-checkbox-circle-line', bg: '#22c55e', subtitle: `${kpi.ackRate}% tasso conferma` },
          { label: 'In Attesa', value: kpi.totalPending, icon: 'ri-time-line', bg: '#f59e0b' },
          { label: 'Questo Mese', value: kpi.thisMonth, icon: 'ri-calendar-line', bg: '#8b5cf6', subtitle: monthChange !== 0 ? `${monthChange > 0 ? '+' : ''}${monthChange}% vs mese scorso` : 'Uguale al mese scorso' },
        ].map((stat, idx) => (
          <div key={idx} className="col-xl-3 col-sm-6">
            <div className="card border-0 shadow-sm" style={{ backgroundColor: stat.bg, borderRadius: '16px' }}>
              <div className="card-body py-3">
                <div className="d-flex align-items-center justify-content-between">
                  <div>
                    <h3 className="text-white mb-0 fw-bold">{stat.value}</h3>
                    <span className="text-white opacity-75 small">{stat.label}</span>
                    {stat.subtitle && <div className="text-white opacity-50" style={{ fontSize: '11px', marginTop: '2px' }}>{stat.subtitle}</div>}
                  </div>
                  <div className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center" style={{ width: '48px', height: '48px' }}>
                    <i className={`${stat.icon} text-white fs-4`}></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Row 2: Trend + Tipo */}
      <div className="row g-3 mb-4">
        {/* Trend Mensile (Bar Chart) */}
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-bar-chart-line me-2 text-primary"></i>
                Trend Mensile (ultimi 6 mesi)
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <div className="d-flex align-items-end justify-content-between gap-2" style={{ height: '200px' }}>
                {(monthlyTrend || []).map((m, idx) => (
                  <div key={idx} className="d-flex flex-column align-items-center flex-fill">
                    <div className="d-flex flex-column align-items-center justify-content-end" style={{ height: '160px', width: '100%' }}>
                      {/* Acknowledged portion */}
                      <div
                        style={{
                          width: '70%',
                          maxWidth: '50px',
                          height: `${Math.max((m.acknowledged / maxMonthly) * 140, m.acknowledged > 0 ? 8 : 0)}px`,
                          background: 'linear-gradient(180deg, #22c55e 0%, #16a34a 100%)',
                          borderRadius: '6px 6px 0 0',
                          transition: 'height 0.3s ease',
                          position: 'relative',
                        }}
                        title={`Confermati: ${m.acknowledged}`}
                      ></div>
                      {/* Pending portion */}
                      <div
                        style={{
                          width: '70%',
                          maxWidth: '50px',
                          height: `${Math.max(((m.total - m.acknowledged) / maxMonthly) * 140, (m.total - m.acknowledged) > 0 ? 4 : 0)}px`,
                          background: 'linear-gradient(180deg, #f59e0b 0%, #d97706 100%)',
                          borderRadius: m.acknowledged === 0 ? '6px 6px 0 0' : '0',
                          transition: 'height 0.3s ease',
                        }}
                        title={`In attesa: ${m.total - m.acknowledged}`}
                      ></div>
                    </div>
                    <div className="text-center mt-2">
                      <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>{m.month}</span>
                      <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e293b' }}>{m.total}</div>
                    </div>
                  </div>
                ))}
              </div>
              {/* Legend */}
              <div className="d-flex gap-4 justify-content-center mt-3">
                <div className="d-flex align-items-center gap-1">
                  <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#22c55e' }}></div>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>Confermati</span>
                </div>
                <div className="d-flex align-items-center gap-1">
                  <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#f59e0b' }}></div>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>In attesa</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Breakdown per Tipo */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-pie-chart-line me-2 text-warning"></i>
                Per Tipologia
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              {(byType || []).length > 0 ? (
                <div className="d-flex flex-column gap-3">
                  {byType.map((t, idx) => {
                    const config = REVIEW_TYPE_CONFIG[t.type] || { label: t.label, color: '#64748b', bg: '#f1f5f9', icon: 'ri-file-line' };
                    const pct = kpi.totalTrainings > 0 ? Math.round((t.count / kpi.totalTrainings) * 100) : 0;
                    return (
                      <div key={idx}>
                        <div className="d-flex align-items-center justify-content-between mb-1">
                          <div className="d-flex align-items-center gap-2">
                            <div className="d-flex align-items-center justify-content-center" style={{ width: '28px', height: '28px', borderRadius: '8px', background: config.bg }}>
                              <i className={config.icon} style={{ fontSize: '14px', color: config.color }}></i>
                            </div>
                            <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{config.label}</span>
                          </div>
                          <div className="d-flex align-items-center gap-2">
                            <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>{t.count}</span>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>{pct}%</span>
                          </div>
                        </div>
                        <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: config.color, borderRadius: '3px', transition: 'width 0.3s ease' }}></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-4"><p className="text-muted mb-0" style={{ fontSize: '13px' }}>Nessun dato</p></div>
              )}

              {/* Richieste KPI */}
              <div className="mt-4 pt-3 border-top">
                <div className="d-flex align-items-center justify-content-between mb-2">
                  <span style={{ fontSize: '13px', color: '#64748b' }}>Richieste totali</span>
                  <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>{kpi.totalRequests}</span>
                </div>
                <div className="d-flex align-items-center justify-content-between">
                  <span style={{ fontSize: '13px', color: '#64748b' }}>Richieste in attesa</span>
                  <span style={{ fontSize: '14px', fontWeight: 700, color: kpi.pendingRequests > 0 ? '#f59e0b' : '#22c55e' }}>{kpi.pendingRequests}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: Top Formatori + Top Destinatari */}
      <div className="row g-3 mb-4">
        <div className="col-lg-6">
          <TopPeopleCard
            title="Top Formatori"
            subtitle="Chi ha erogato più training"
            icon="ri-user-voice-line"
            color="#3b82f6"
            bgColor="#dbeafe"
            people={topReviewers || []}
          />
        </div>
        <div className="col-lg-6">
          <TopPeopleCard
            title="Top Destinatari"
            subtitle="Chi ha ricevuto più training"
            icon="ri-user-received-line"
            color="#8b5cf6"
            bgColor="#ede9fe"
            people={topReviewees || []}
          />
        </div>
      </div>

      {/* Row 4: Ultimi Training */}
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
          <div className="d-flex align-items-center justify-content-between">
            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
              <i className="ri-file-list-3-line me-2 text-info"></i>
              Ultimi Training
            </h6>
            <Link to="/formazione" className="btn btn-sm btn-outline-primary" style={{ borderRadius: '8px' }}>
              Vai a Formazione <i className="ri-arrow-right-s-line"></i>
            </Link>
          </div>
        </div>
        <div className="card-body p-0">
          {paginatedRecent.length > 0 ? (
            <>
              <div className="table-responsive">
                <table className="table mb-0">
                  <thead>
                    <tr style={{ background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)' }}>
                      <th style={tableHeaderStyle}>Titolo</th>
                      <th style={tableHeaderStyle}>Tipo</th>
                      <th style={tableHeaderStyle}>Formatore</th>
                      <th style={tableHeaderStyle}>Destinatario</th>
                      <th style={tableHeaderStyle}>Data</th>
                      <th style={tableHeaderStyle}>Stato</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedRecent.map((t) => {
                      const typeConfig = REVIEW_TYPE_CONFIG[t.reviewType] || { label: t.reviewType || 'Altro', color: '#64748b', bg: '#f1f5f9' };
                      return (
                        <tr key={t.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={tableCellStyle}>
                            <span style={{ fontWeight: 600, color: '#334155' }}>{t.title || 'Senza titolo'}</span>
                          </td>
                          <td style={tableCellStyle}>
                            <span style={{ background: typeConfig.bg, color: typeConfig.color, padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 600 }}>
                              {typeConfig.label}
                            </span>
                          </td>
                          <td style={tableCellStyle}><span className="text-muted">{t.reviewer}</span></td>
                          <td style={tableCellStyle}><span style={{ fontWeight: 500 }}>{t.reviewee}</span></td>
                          <td style={tableCellStyle}>
                            <span className="text-muted">{t.createdAt ? new Date(t.createdAt).toLocaleDateString('it-IT') : '-'}</span>
                          </td>
                          <td style={tableCellStyle}>
                            {t.isAcknowledged ? (
                              <span style={{ background: '#dcfce7', color: '#166534', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 600 }}>
                                <i className="ri-check-line me-1"></i>Confermato
                              </span>
                            ) : (
                              <span style={{ background: '#fef3c7', color: '#92400e', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 600 }}>
                                <i className="ri-time-line me-1"></i>In attesa
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {totalRecentPages > 1 && (
                <div className="d-flex align-items-center justify-content-between px-4 py-3 border-top">
                  <span className="text-muted" style={{ fontSize: '13px' }}>
                    {recentStartIdx + 1}-{Math.min(recentStartIdx + RECENT_PER_PAGE, recentTrainings.length)} di {recentTrainings.length}
                  </span>
                  <div className="d-flex gap-2">
                    <button className="btn btn-sm btn-light" style={{ borderRadius: '8px' }} onClick={() => setRecentPage(p => Math.max(1, p - 1))} disabled={recentPage === 1}>
                      <i className="ri-arrow-left-s-line"></i> Prec
                    </button>
                    <button className="btn btn-sm btn-light" style={{ borderRadius: '8px' }} onClick={() => setRecentPage(p => Math.min(totalRecentPages, p + 1))} disabled={recentPage === totalRecentPages}>
                      Succ <i className="ri-arrow-right-s-line"></i>
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-5">
              <i className="ri-book-open-line text-muted" style={{ fontSize: '48px', opacity: 0.3 }}></i>
              <p className="text-muted mt-2 mb-0">Nessun training recente</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// ==================== PAZIENTI TAB ====================

const STATUS_CONFIG = {
  attivo: { label: 'Attivo', color: '#22c55e', bg: '#dcfce7', icon: 'ri-checkbox-circle-line' },
  ghost: { label: 'Ghost', color: '#f59e0b', bg: '#fef3c7', icon: 'ri-ghost-line' },
  pausa: { label: 'Pausa', color: '#06b6d4', bg: '#cffafe', icon: 'ri-pause-circle-line' },
  stop: { label: 'Stop', color: '#ef4444', bg: '#fee2e2', icon: 'ri-stop-circle-line' },
  insoluto: { label: 'Insoluto', color: '#dc2626', bg: '#fecaca', icon: 'ri-error-warning-line' },
  freeze: { label: 'Freeze', color: '#64748b', bg: '#f1f5f9', icon: 'ri-snowflake-line' },
  non_definito: { label: 'N/D', color: '#94a3b8', bg: '#f8fafc', icon: 'ri-question-line' },
};

const TIPOLOGIA_CONFIG = {
  a: { label: 'Tipo A', color: '#22c55e', bg: '#dcfce7' },
  b: { label: 'Tipo B', color: '#f59e0b', bg: '#fef3c7' },
  c: { label: 'Tipo C', color: '#3b82f6', bg: '#dbeafe' },
  stop: { label: 'Stop', color: '#ef4444', bg: '#fee2e2' },
  recupero: { label: 'Recupero', color: '#8b5cf6', bg: '#ede9fe' },
  pausa_gt_30: { label: 'Pausa > 30gg', color: '#64748b', bg: '#f1f5f9' },
  non_definito: { label: 'N/D', color: '#94a3b8', bg: '#f8fafc' },
};

function PazientiTab({ data, loading, error, onRetry }) {
  if (error) {
    return (
      <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
        <div className="card-body text-center py-5">
          <i className="ri-error-warning-line text-danger" style={{ fontSize: '48px', opacity: 0.6 }}></i>
          <h5 className="text-muted mt-3">{error}</h5>
          <p className="text-muted small">Assicurati che il backend sia avviato e riprova.</p>
          <button className="btn btn-primary btn-sm" style={{ borderRadius: '8px' }} onClick={onRetry}>
            <i className="ri-refresh-line me-1"></i> Riprova
          </button>
        </div>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="row g-3">
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-lg-8"><SkeletonCard height="300px" /></div>
        <div className="col-lg-4"><SkeletonCard height="300px" /></div>
        <div className="col-lg-6"><SkeletonCard height="280px" /></div>
        <div className="col-lg-6"><SkeletonCard height="280px" /></div>
      </div>
    );
  }

  const { kpi, statusDistribution, tipologiaDistribution, services, monthlyTrend, patologie, genderDistribution, programmaDistribution, paymentDistribution } = data;

  const maxMonthly = Math.max(...(monthlyTrend || []).map(m => m.count), 1);
  const totalStatus = (statusDistribution || []).reduce((s, d) => s + d.count, 0) || 1;
  const totalTipologia = (tipologiaDistribution || []).reduce((s, d) => s + d.count, 0) || 1;
  const maxPatologia = (patologie || []).length > 0 ? patologie[0].count : 1;

  // Month-over-month change
  const monthChange = kpi.newPrevMonth > 0
    ? Math.round(((kpi.newMonth - kpi.newPrevMonth) / kpi.newPrevMonth) * 100)
    : (kpi.newMonth > 0 ? 100 : 0);

  // Retention rate
  const retentionRate = kpi.total > 0 ? Math.round((kpi.active / kpi.total) * 100) : 0;

  return (
    <>
      {/* KPI Cards */}
      <div className="row g-3 mb-4">
        {[
          { label: 'Pazienti Totali', value: kpi.total, icon: 'ri-group-line', bg: '#3b82f6', subtitle: `${retentionRate}% retention` },
          { label: 'Attivi', value: kpi.active, icon: 'ri-checkbox-circle-line', bg: '#22c55e', subtitle: `${kpi.inScadenza} in scadenza` },
          { label: 'Ghost', value: kpi.ghost, icon: 'ri-ghost-line', bg: '#f59e0b', subtitle: `${kpi.pausa} in pausa` },
          { label: 'Nuovi Mese', value: kpi.newMonth, icon: 'ri-user-add-line', bg: '#8b5cf6', subtitle: monthChange !== 0 ? `${monthChange > 0 ? '+' : ''}${monthChange}% vs mese scorso` : 'Uguale al mese scorso' },
        ].map((stat, idx) => (
          <div key={idx} className="col-xl-3 col-sm-6">
            <div className="card border-0 shadow-sm" style={{ backgroundColor: stat.bg, borderRadius: '16px' }}>
              <div className="card-body py-3">
                <div className="d-flex align-items-center justify-content-between">
                  <div>
                    <h3 className="text-white mb-0 fw-bold">{stat.value}</h3>
                    <span className="text-white opacity-75 small">{stat.label}</span>
                    {stat.subtitle && <div className="text-white opacity-50" style={{ fontSize: '11px', marginTop: '2px' }}>{stat.subtitle}</div>}
                  </div>
                  <div className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center" style={{ width: '48px', height: '48px' }}>
                    <i className={`${stat.icon} text-white fs-4`}></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Row 2: Trend + Status Distribution */}
      <div className="row g-3 mb-4">
        {/* Monthly Trend (Bar Chart) */}
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-line-chart-line me-2 text-primary"></i>
                Nuovi Pazienti (ultimi 12 mesi)
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <div className="d-flex align-items-end justify-content-between gap-1" style={{ height: '200px' }}>
                {(monthlyTrend || []).map((m, idx) => (
                  <div key={idx} className="d-flex flex-column align-items-center flex-fill">
                    <div className="d-flex flex-column align-items-center justify-content-end" style={{ height: '160px', width: '100%' }}>
                      <div
                        style={{
                          width: '65%',
                          maxWidth: '40px',
                          height: `${Math.max((m.count / maxMonthly) * 140, m.count > 0 ? 8 : 0)}px`,
                          background: 'linear-gradient(180deg, #3b82f6 0%, #2563eb 100%)',
                          borderRadius: '6px 6px 0 0',
                          transition: 'height 0.3s ease',
                        }}
                        title={`${m.count} nuovi pazienti`}
                      ></div>
                    </div>
                    <div className="text-center mt-2">
                      <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 500 }}>
                        {m.month ? m.month.split('-')[1] + '/' + m.month.split('-')[0].slice(2) : ''}
                      </span>
                      <div style={{ fontSize: '11px', fontWeight: 700, color: '#1e293b' }}>{m.count}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Status Distribution */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-pie-chart-line me-2 text-success"></i>
                Distribuzione Stato
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <div className="d-flex flex-column gap-3">
                {(statusDistribution || [])
                  .sort((a, b) => b.count - a.count)
                  .map((s, idx) => {
                    const config = STATUS_CONFIG[s.status] || STATUS_CONFIG.non_definito;
                    const pct = Math.round((s.count / totalStatus) * 100);
                    return (
                      <div key={idx}>
                        <div className="d-flex align-items-center justify-content-between mb-1">
                          <div className="d-flex align-items-center gap-2">
                            <div className="d-flex align-items-center justify-content-center" style={{ width: '24px', height: '24px', borderRadius: '6px', background: config.bg }}>
                              <i className={config.icon} style={{ fontSize: '12px', color: config.color }}></i>
                            </div>
                            <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{config.label}</span>
                          </div>
                          <div className="d-flex align-items-center gap-2">
                            <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>{s.count}</span>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>{pct}%</span>
                          </div>
                        </div>
                        <div style={{ height: '5px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: config.color, borderRadius: '3px', transition: 'width 0.3s ease' }}></div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: Services + Tipologia */}
      <div className="row g-3 mb-4">
        {/* Servizi (Nutrizione, Coach, Psicologia) */}
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-stethoscope-line me-2 text-info"></i>
                Servizi Specialistici
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <div className="row g-3">
                {[
                  { key: 'nutrizione', label: 'Nutrizione', icon: 'ri-restaurant-line', color: '#22c55e', bg: '#dcfce7' },
                  { key: 'coach', label: 'Coaching', icon: 'ri-run-line', color: '#f59e0b', bg: '#fef3c7' },
                  { key: 'psicologia', label: 'Psicologia', icon: 'ri-mental-health-line', color: '#8b5cf6', bg: '#ede9fe' },
                ].map((svc) => {
                  const stats = services?.[svc.key] || {};
                  const active = stats.attivo || 0;
                  const ghost = stats.ghost || 0;
                  const pausa = stats.pausa || 0;
                  const stop = stats.stop || 0;
                  const total = active + ghost + pausa + stop + (stats.insoluto || 0) + (stats.freeze || 0) + (stats.non_definito || 0);
                  return (
                    <div key={svc.key} className="col-md-4">
                      <div style={{ background: svc.bg, borderRadius: '12px', padding: '16px' }}>
                        <div className="d-flex align-items-center gap-2 mb-3">
                          <div className="d-flex align-items-center justify-content-center" style={{ width: '32px', height: '32px', borderRadius: '8px', background: '#fff' }}>
                            <i className={svc.icon} style={{ color: svc.color, fontSize: '16px' }}></i>
                          </div>
                          <div>
                            <div style={{ fontSize: '13px', fontWeight: 600, color: svc.color }}>{svc.label}</div>
                            <div style={{ fontSize: '11px', color: '#64748b' }}>{total} totali</div>
                          </div>
                        </div>
                        <div className="d-flex flex-column gap-2">
                          <div className="d-flex justify-content-between align-items-center">
                            <span style={{ fontSize: '12px', color: '#334155' }}>Attivi</span>
                            <span style={{ fontSize: '13px', fontWeight: 700, color: '#22c55e' }}>{active}</span>
                          </div>
                          <div className="d-flex justify-content-between align-items-center">
                            <span style={{ fontSize: '12px', color: '#334155' }}>Ghost</span>
                            <span style={{ fontSize: '13px', fontWeight: 700, color: '#f59e0b' }}>{ghost}</span>
                          </div>
                          <div className="d-flex justify-content-between align-items-center">
                            <span style={{ fontSize: '12px', color: '#334155' }}>Pausa</span>
                            <span style={{ fontSize: '13px', fontWeight: 700, color: '#06b6d4' }}>{pausa}</span>
                          </div>
                          <div className="d-flex justify-content-between align-items-center">
                            <span style={{ fontSize: '12px', color: '#334155' }}>Stop</span>
                            <span style={{ fontSize: '13px', fontWeight: 700, color: '#ef4444' }}>{stop}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Tipologia Distribution */}
        <div className="col-lg-5">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-user-settings-line me-2 text-warning"></i>
                Tipologia Cliente
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <div className="d-flex flex-column gap-3">
                {(tipologiaDistribution || [])
                  .sort((a, b) => b.count - a.count)
                  .map((t, idx) => {
                    const config = TIPOLOGIA_CONFIG[t.tipologia] || TIPOLOGIA_CONFIG.non_definito;
                    const pct = Math.round((t.count / totalTipologia) * 100);
                    return (
                      <div key={idx}>
                        <div className="d-flex align-items-center justify-content-between mb-1">
                          <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{config.label}</span>
                          <div className="d-flex align-items-center gap-2">
                            <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>{t.count}</span>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>{pct}%</span>
                          </div>
                        </div>
                        <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: config.color, borderRadius: '3px', transition: 'width 0.3s ease' }}></div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 4: Patologie + Programmi */}
      <div className="row g-3 mb-4">
        {/* Top Patologie */}
        <div className="col-lg-6">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-heart-pulse-line me-2 text-danger"></i>
                Patologie Principali
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              {(patologie || []).length > 0 ? (
                <div className="d-flex flex-column gap-2">
                  {patologie.slice(0, 10).map((p, idx) => (
                    <div key={idx} className="d-flex align-items-center gap-3">
                      <div style={{ width: '24px', fontSize: '12px', fontWeight: 600, color: '#64748b', textAlign: 'right' }}>
                        {idx + 1}
                      </div>
                      <div className="flex-fill">
                        <div className="d-flex justify-content-between align-items-center mb-1">
                          <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{p.name}</span>
                          <span style={{ fontSize: '13px', fontWeight: 700, color: '#1e293b' }}>{p.count}</span>
                        </div>
                        <div style={{ height: '4px', borderRadius: '2px', background: '#f1f5f9', overflow: 'hidden' }}>
                          <div style={{
                            height: '100%',
                            width: `${Math.round((p.count / maxPatologia) * 100)}%`,
                            background: `hsl(${350 - idx * 15}, 70%, 55%)`,
                            borderRadius: '2px',
                            transition: 'width 0.3s ease',
                          }}></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-muted">
                  <i className="ri-heart-pulse-line" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                  <p className="mb-0 mt-2 small">Nessun dato patologie</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Programmi + Gender + Pagamento */}
        <div className="col-lg-6">
          <div className="d-flex flex-column gap-3">
            {/* Programmi */}
            <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
              <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                  <i className="ri-file-list-3-line me-2 text-primary"></i>
                  Programmi Attivi
                </h6>
              </div>
              <div className="card-body px-4 pb-3 pt-2">
                {(programmaDistribution || []).length > 0 ? (
                  <div className="d-flex flex-wrap gap-2">
                    {programmaDistribution.map((p, idx) => (
                      <span key={idx} style={{
                        background: `hsl(${210 + idx * 30}, 80%, 95%)`,
                        color: `hsl(${210 + idx * 30}, 60%, 35%)`,
                        padding: '6px 12px',
                        borderRadius: '20px',
                        fontSize: '12px',
                        fontWeight: 600,
                      }}>
                        {p.programma} <span style={{ opacity: 0.7 }}>({p.count})</span>
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted small mb-0">Nessun dato programmi</p>
                )}
              </div>
            </div>

            {/* Gender + Payment in a row */}
            {/* Gender */}
            <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
              <div className="card-body p-3">
                <div className="d-flex align-items-center gap-2 mb-3">
                  <i className="ri-user-heart-line text-info"></i>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>Genere</span>
                </div>
                {(genderDistribution || []).length > 0 ? (
                  <div className="d-flex flex-column gap-2">
                    {genderDistribution
                      .filter(g => g.gender !== 'non_definito')
                      .map((g, idx) => (
                        <div key={idx} className="d-flex justify-content-between align-items-center">
                          <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'capitalize' }}>{g.gender}</span>
                          <span style={{ fontSize: '13px', fontWeight: 700, color: '#1e293b' }}>{g.count}</span>
                        </div>
                      ))}
                  </div>
                ) : (
                  <p className="text-muted small mb-0">N/D</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

    </>
  );
}

// ==================== CHECK TAB ====================

function CheckTab({ data, loading, error, onRetry }) {
  const [recentPage, setRecentPage] = useState(1);
  const RECENT_PER_PAGE = 5;

  if (error) {
    return (
      <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
        <div className="card-body text-center py-5">
          <i className="ri-error-warning-line text-danger" style={{ fontSize: '48px', opacity: 0.6 }}></i>
          <h5 className="text-muted mt-3">{error}</h5>
          <p className="text-muted small">Assicurati che il backend sia avviato e riprova.</p>
          <button className="btn btn-primary btn-sm" style={{ borderRadius: '8px' }} onClick={onRetry}>
            <i className="ri-refresh-line me-1"></i> Riprova
          </button>
        </div>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="row g-3">
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-lg-8"><SkeletonCard height="300px" /></div>
        <div className="col-lg-4"><SkeletonCard height="300px" /></div>
        <div className="col-lg-6"><SkeletonCard height="280px" /></div>
        <div className="col-lg-6"><SkeletonCard height="280px" /></div>
      </div>
    );
  }

  const { kpi, ratings, typeBreakdown, ratingsDistribution, monthlyTrend, topProfessionals, recentResponses, physicalMetrics } = data;

  const maxMonthly = Math.max(...(monthlyTrend || []).map(m => m.count), 1);
  const monthChange = kpi.totalPrevMonth > 0
    ? Math.round(((kpi.totalMonth - kpi.totalPrevMonth) / kpi.totalPrevMonth) * 100)
    : (kpi.totalMonth > 0 ? 100 : 0);

  // Ratings distribution total
  const totalRatings = (ratingsDistribution?.low || 0) + (ratingsDistribution?.medium || 0) + (ratingsDistribution?.good || 0) + (ratingsDistribution?.excellent || 0) || 1;

  // Recent responses pagination
  const totalRecentPages = Math.ceil((recentResponses || []).length / RECENT_PER_PAGE);
  const recentStartIdx = (recentPage - 1) * RECENT_PER_PAGE;
  const paginatedRecent = (recentResponses || []).slice(recentStartIdx, recentStartIdx + RECENT_PER_PAGE);

  // Rating color helper
  const getRatingColor = (val) => {
    if (!val) return '#94a3b8';
    if (val >= 9) return '#22c55e';
    if (val >= 7) return '#3b82f6';
    if (val >= 5) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <>
      {/* KPI Cards */}
      <div className="row g-3 mb-4">
        {[
          { label: 'Check Totali', value: kpi.totalAll, icon: 'ri-checkbox-circle-line', bg: '#3b82f6', subtitle: `${kpi.totalMonth} questo mese` },
          { label: 'Qualità Media', value: kpi.avgQuality ? `${kpi.avgQuality}/10` : 'N/D', icon: 'ri-star-line', bg: '#22c55e', subtitle: 'Ultimi 30 giorni' },
          { label: 'Questo Mese', value: kpi.totalMonth, icon: 'ri-calendar-check-line', bg: '#8b5cf6', subtitle: monthChange !== 0 ? `${monthChange > 0 ? '+' : ''}${monthChange}% vs mese scorso` : 'Uguale al mese scorso' },
          { label: 'Da Leggere', value: kpi.unreadCount, icon: 'ri-mail-unread-line', bg: '#f59e0b', subtitle: 'Check non letti' },
        ].map((stat, idx) => (
          <div key={idx} className="col-xl-3 col-sm-6">
            <div className="card border-0 shadow-sm" style={{ backgroundColor: stat.bg, borderRadius: '16px' }}>
              <div className="card-body py-3">
                <div className="d-flex align-items-center justify-content-between">
                  <div>
                    <h3 className="text-white mb-0 fw-bold">{stat.value}</h3>
                    <span className="text-white opacity-75 small">{stat.label}</span>
                    {stat.subtitle && <div className="text-white opacity-50" style={{ fontSize: '11px', marginTop: '2px' }}>{stat.subtitle}</div>}
                  </div>
                  <div className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center" style={{ width: '48px', height: '48px' }}>
                    <i className={`${stat.icon} text-white fs-4`}></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Row 2: Trend + Ratings Professionali */}
      <div className="row g-3 mb-4">
        {/* Monthly Trend */}
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-bar-chart-line me-2 text-primary"></i>
                Trend Check Settimanali (ultimi 6 mesi)
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <div className="d-flex align-items-end justify-content-between gap-2" style={{ height: '200px' }}>
                {(monthlyTrend || []).map((m, idx) => (
                  <div key={idx} className="d-flex flex-column align-items-center flex-fill">
                    <div className="d-flex flex-column align-items-center justify-content-end" style={{ height: '160px', width: '100%' }}>
                      <div
                        style={{
                          width: '65%',
                          maxWidth: '45px',
                          height: `${Math.max((m.count / maxMonthly) * 140, m.count > 0 ? 8 : 0)}px`,
                          background: `linear-gradient(180deg, ${m.avgProgress && m.avgProgress >= 7 ? '#22c55e' : m.avgProgress && m.avgProgress >= 5 ? '#f59e0b' : '#3b82f6'} 0%, ${m.avgProgress && m.avgProgress >= 7 ? '#16a34a' : m.avgProgress && m.avgProgress >= 5 ? '#d97706' : '#2563eb'} 100%)`,
                          borderRadius: '6px 6px 0 0',
                          transition: 'height 0.3s ease',
                        }}
                        title={`${m.count} check - Media progresso: ${m.avgProgress || 'N/D'}`}
                      ></div>
                    </div>
                    <div className="text-center mt-2">
                      <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>
                        {m.month ? m.month.split('-')[1] + '/' + m.month.split('-')[0].slice(2) : ''}
                      </span>
                      <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e293b' }}>{m.count}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="d-flex gap-4 justify-content-center mt-3">
                <div className="d-flex align-items-center gap-1">
                  <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#22c55e' }}></div>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>Progresso ≥ 7</span>
                </div>
                <div className="d-flex align-items-center gap-1">
                  <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#f59e0b' }}></div>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>Progresso 5-6</span>
                </div>
                <div className="d-flex align-items-center gap-1">
                  <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#3b82f6' }}></div>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>Progresso &lt; 5</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Professional Ratings */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-star-line me-2 text-warning"></i>
                Valutazioni Medie
              </h6>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Ultimi 30 giorni</span>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <div className="d-flex flex-column gap-3">
                {[
                  { label: 'Nutrizionista', value: ratings?.nutrizionista, icon: 'ri-restaurant-line', color: '#22c55e' },
                  { label: 'Coach', value: ratings?.coach, icon: 'ri-run-line', color: '#f59e0b' },
                  { label: 'Psicologo', value: ratings?.psicologo, icon: 'ri-mental-health-line', color: '#8b5cf6' },
                  { label: 'Progresso', value: ratings?.progresso, icon: 'ri-arrow-up-circle-line', color: '#3b82f6' },
                ].map((r, idx) => (
                  <div key={idx} className="d-flex align-items-center justify-content-between">
                    <div className="d-flex align-items-center gap-2">
                      <div className="d-flex align-items-center justify-content-center" style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${r.color}15` }}>
                        <i className={r.icon} style={{ fontSize: '14px', color: r.color }}></i>
                      </div>
                      <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{r.label}</span>
                    </div>
                    <div className="d-flex align-items-center gap-2">
                      <span style={{ fontSize: '18px', fontWeight: 700, color: getRatingColor(r.value) }}>
                        {r.value || '—'}
                      </span>
                      <span style={{ fontSize: '12px', color: '#94a3b8' }}>/10</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: Type Breakdown + Ratings Distribution + Physical Metrics */}
      <div className="row g-3 mb-4">
        {/* Type Breakdown */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-pie-chart-line me-2 text-info"></i>
                Tipologia Check
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              {[
                { key: 'weekly', label: 'Settimanale', icon: 'ri-calendar-line', color: '#3b82f6', bg: '#dbeafe' },
                { key: 'dca', label: 'DCA', icon: 'ri-heart-pulse-line', color: '#ef4444', bg: '#fee2e2' },
                { key: 'minor', label: 'Minori (EDE-Q6)', icon: 'ri-user-line', color: '#8b5cf6', bg: '#ede9fe' },
              ].map((t) => {
                const info = typeBreakdown?.[t.key] || { total: 0, month: 0 };
                const pct = kpi.totalAll > 0 ? Math.round((info.total / kpi.totalAll) * 100) : 0;
                return (
                  <div key={t.key} className="mb-3">
                    <div className="d-flex align-items-center justify-content-between mb-1">
                      <div className="d-flex align-items-center gap-2">
                        <div className="d-flex align-items-center justify-content-center" style={{ width: '28px', height: '28px', borderRadius: '8px', background: t.bg }}>
                          <i className={t.icon} style={{ fontSize: '14px', color: t.color }}></i>
                        </div>
                        <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{t.label}</span>
                      </div>
                      <div className="text-end">
                        <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>{info.total}</span>
                        <span style={{ fontSize: '11px', color: '#94a3b8', marginLeft: '4px' }}>({info.month} mese)</span>
                      </div>
                    </div>
                    <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: t.color, borderRadius: '3px', transition: 'width 0.3s ease' }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Ratings Distribution */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-bar-chart-grouped-line me-2 text-success"></i>
                Distribuzione Voti
              </h6>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Ultimi 30 giorni</span>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              {[
                { label: 'Eccellente (9-10)', value: ratingsDistribution?.excellent || 0, color: '#22c55e', bg: '#dcfce7' },
                { label: 'Buono (7-8)', value: ratingsDistribution?.good || 0, color: '#3b82f6', bg: '#dbeafe' },
                { label: 'Sufficiente (5-6)', value: ratingsDistribution?.medium || 0, color: '#f59e0b', bg: '#fef3c7' },
                { label: 'Basso (1-4)', value: ratingsDistribution?.low || 0, color: '#ef4444', bg: '#fee2e2' },
              ].map((r, idx) => {
                const pct = Math.round((r.value / totalRatings) * 100);
                return (
                  <div key={idx} className="mb-3">
                    <div className="d-flex align-items-center justify-content-between mb-1">
                      <span style={{ fontSize: '12px', fontWeight: 500, color: '#334155' }}>{r.label}</span>
                      <div className="d-flex align-items-center gap-2">
                        <span style={{ fontSize: '13px', fontWeight: 700, color: r.color }}>{r.value}</span>
                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>{pct}%</span>
                      </div>
                    </div>
                    <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: r.color, borderRadius: '3px', transition: 'width 0.3s ease' }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Physical Metrics */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-heart-2-line me-2 text-danger"></i>
                Metriche Fisiche Medie
              </h6>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Ultimi 30 giorni (scala 0-10)</span>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              {physicalMetrics && Object.keys(physicalMetrics).length > 0 ? (
                <div className="d-flex flex-column gap-2">
                  {[
                    { key: 'digestione', label: 'Digestione', icon: '🫃' },
                    { key: 'energia', label: 'Energia', icon: '⚡' },
                    { key: 'forza', label: 'Forza', icon: '💪' },
                    { key: 'sonno', label: 'Sonno', icon: '😴' },
                    { key: 'umore', label: 'Umore', icon: '😊' },
                    { key: 'motivazione', label: 'Motivazione', icon: '🎯' },
                  ].map((m) => {
                    const val = physicalMetrics[m.key];
                    return (
                      <div key={m.key} className="d-flex align-items-center gap-2">
                        <span style={{ fontSize: '14px', width: '24px' }}>{m.icon}</span>
                        <span style={{ fontSize: '12px', color: '#64748b', width: '80px' }}>{m.label}</span>
                        <div className="flex-fill" style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                          <div style={{
                            height: '100%',
                            width: `${val ? (val / 10) * 100 : 0}%`,
                            background: getRatingColor(val),
                            borderRadius: '3px',
                            transition: 'width 0.3s ease',
                          }}></div>
                        </div>
                        <span style={{ fontSize: '13px', fontWeight: 700, color: getRatingColor(val), width: '30px', textAlign: 'right' }}>
                          {val || '—'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-3 text-muted">
                  <i className="ri-heart-2-line" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                  <p className="mb-0 mt-2 small">Nessun dato disponibile</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Row 4: Top Professionals */}
      <div className="row g-3 mb-4">
        {[
          { key: 'nutrizionisti', title: 'Top Nutrizionisti', icon: 'ri-restaurant-line', color: '#22c55e', bg: '#dcfce7' },
          { key: 'coaches', title: 'Top Coach', icon: 'ri-run-line', color: '#f59e0b', bg: '#fef3c7' },
          { key: 'psicologi', title: 'Top Psicologi', icon: 'ri-mental-health-line', color: '#8b5cf6', bg: '#ede9fe' },
        ].map((section) => {
          const professionals = topProfessionals?.[section.key] || [];
          return (
            <div key={section.key} className="col-lg-4">
              <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                <div className="card-header border-0 py-3 px-4" style={{ background: section.bg, borderRadius: '16px 16px 0 0' }}>
                  <h6 className="mb-0" style={{ fontWeight: 600, color: section.color }}>
                    <i className={`${section.icon} me-2`}></i>{section.title}
                  </h6>
                  <span style={{ fontSize: '11px', color: `${section.color}99` }}>Per valutazione media (min. 3 check)</span>
                </div>
                <div className="card-body px-4 pb-3 pt-3">
                  {professionals.length > 0 ? (
                    <div className="d-flex flex-column gap-2">
                      {professionals.map((p, idx) => (
                        <div key={idx} className="d-flex align-items-center justify-content-between">
                          <div className="d-flex align-items-center gap-2">
                            <div className="d-flex align-items-center justify-content-center" style={{
                              width: '24px', height: '24px', borderRadius: '50%',
                              background: idx === 0 ? section.color : '#f1f5f9',
                              color: idx === 0 ? '#fff' : '#64748b',
                              fontSize: '11px', fontWeight: 700,
                            }}>
                              {idx + 1}
                            </div>
                            <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{p.name}</span>
                          </div>
                          <div className="d-flex align-items-center gap-1">
                            <span style={{ fontSize: '14px', fontWeight: 700, color: getRatingColor(p.avg) }}>{p.avg}</span>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>({p.count})</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted small mb-0 text-center py-2">Dati insufficienti</p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Row 5: Recent Responses Table */}
      <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
          <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
            <i className="ri-file-list-3-line me-2 text-primary"></i>
            Check Recenti
          </h6>
        </div>
        {(recentResponses || []).length > 0 ? (
          <>
            <div className="table-responsive">
              <table className="table table-hover mb-0" style={{ fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #f1f5f9' }}>
                    {['Paziente', 'Data', 'Nutriz.', 'Coach', 'Psico.', 'Progr.', 'Media'].map((h) => (
                      <th key={h} style={{ padding: '12px 16px', fontWeight: 600, color: '#64748b', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {paginatedRecent.map((r) => (
                    <tr key={r.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '12px 16px', fontWeight: 600, color: '#334155' }}>{r.cliente}</td>
                      <td style={{ padding: '12px 16px', color: '#64748b' }}>{r.date || '—'}</td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontWeight: 700, color: getRatingColor(r.nutrizionista) }}>{r.nutrizionista || '—'}</span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontWeight: 700, color: getRatingColor(r.coach) }}>{r.coach || '—'}</span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontWeight: 700, color: getRatingColor(r.psicologo) }}>{r.psicologo || '—'}</span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ fontWeight: 700, color: getRatingColor(r.progresso) }}>{r.progresso || '—'}</span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        {r.avg ? (
                          <span style={{ background: `${getRatingColor(r.avg)}15`, color: getRatingColor(r.avg), padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700 }}>
                            {r.avg}
                          </span>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {totalRecentPages > 1 && (
              <div className="d-flex align-items-center justify-content-between px-4 py-3 border-top">
                <span className="text-muted" style={{ fontSize: '13px' }}>
                  {recentStartIdx + 1}-{Math.min(recentStartIdx + RECENT_PER_PAGE, recentResponses.length)} di {recentResponses.length}
                </span>
                <div className="d-flex gap-2">
                  <button className="btn btn-sm btn-light" style={{ borderRadius: '8px' }} onClick={() => setRecentPage(p => Math.max(1, p - 1))} disabled={recentPage === 1}>
                    <i className="ri-arrow-left-s-line"></i> Prec
                  </button>
                  <button className="btn btn-sm btn-light" style={{ borderRadius: '8px' }} onClick={() => setRecentPage(p => Math.min(totalRecentPages, p + 1))} disabled={recentPage === totalRecentPages}>
                    Succ <i className="ri-arrow-right-s-line"></i>
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="card-body text-center py-4">
            <i className="ri-file-list-3-line text-muted" style={{ fontSize: '32px', opacity: 0.3 }}></i>
            <p className="text-muted small mb-0 mt-2">Nessun check recente</p>
          </div>
        )}
      </div>
    </>
  );
}

// ==================== PROFESSIONISTI TAB ====================

const SPECIALTY_CONFIG = {
  nutrizione: { label: 'Nutrizione (TL)', color: '#06b6d4', bg: '#ecfeff' },
  nutrizionista: { label: 'Nutrizionisti', color: '#0891b2', bg: '#cffafe' },
  psicologia: { label: 'Psicologia (TL)', color: '#a855f7', bg: '#faf5ff' },
  psicologo: { label: 'Psicologi', color: '#9333ea', bg: '#f3e8ff' },
  coach: { label: 'Coach', color: '#22c55e', bg: '#f0fdf4' },
  amministrazione: { label: 'Amministrazione', color: '#ef4444', bg: '#fef2f2' },
  cco: { label: 'CCO', color: '#f97316', bg: '#fff7ed' },
};

const ROLE_CONFIG_TAB = {
  admin: { label: 'Admin', color: '#ef4444', bg: '#fef2f2' },
  team_leader: { label: 'Team Leader', color: '#8b5cf6', bg: '#f5f3ff' },
  professionista: { label: 'Professionista', color: '#22c55e', bg: '#f0fdf4' },
  team_esterno: { label: 'Team Esterno', color: '#64748b', bg: '#f8fafc' },
};

function ProfessionistiTab({ data, loading, error, onRetry }) {
  if (error) {
    return (
      <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
        <div className="card-body text-center py-5">
          <i className="ri-error-warning-line text-danger" style={{ fontSize: '48px', opacity: 0.6 }}></i>
          <h5 className="text-muted mt-3">{error}</h5>
          <p className="text-muted small">Assicurati che il backend sia avviato e riprova.</p>
          <button className="btn btn-primary btn-sm" style={{ borderRadius: '8px' }} onClick={onRetry}>
            <i className="ri-refresh-line me-1"></i> Riprova
          </button>
        </div>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="row g-3">
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-lg-8"><SkeletonCard height="300px" /></div>
        <div className="col-lg-4"><SkeletonCard height="300px" /></div>
        <div className="col-lg-6"><SkeletonCard height="280px" /></div>
        <div className="col-lg-6"><SkeletonCard height="280px" /></div>
      </div>
    );
  }

  const { kpi, specialtyDistribution, roleDistribution, qualitySummary, topPerformers, trialUsers, qualityTrend, teamsSummary, clientLoad } = data;

  const maxQualityTrend = Math.max(...(qualityTrend || []).map(w => w.avgQuality || 0), 1);
  const totalBonusBands = Object.values(qualitySummary?.bonusBands || {}).reduce((a, b) => a + b, 0) || 1;

  // Specialty distribution total for percentage calc
  const totalSpecialty = Object.values(specialtyDistribution || {}).reduce((a, v) => a + (v.count || 0), 0) || 1;

  const getQualityColor = (val) => {
    if (!val) return '#94a3b8';
    if (val >= 8.5) return '#22c55e';
    if (val >= 7) return '#3b82f6';
    if (val >= 5.5) return '#f59e0b';
    return '#ef4444';
  };

  const getTrendIcon = (trend) => {
    if (trend === 'up') return { icon: 'ri-arrow-up-line', color: '#22c55e' };
    if (trend === 'down') return { icon: 'ri-arrow-down-line', color: '#ef4444' };
    return { icon: 'ri-subtract-line', color: '#94a3b8' };
  };

  return (
    <>
      {/* KPI Cards */}
      <div className="row g-3 mb-4">
        {[
          { label: 'Totale Team', value: kpi.totalAll, icon: 'ri-team-line', bg: '#3b82f6', subtitle: `${kpi.totalActive} attivi` },
          { label: 'Professionisti', value: kpi.totalProfessionisti, icon: 'ri-user-star-line', bg: '#22c55e', subtitle: `${kpi.totalTeamLeaders} team leaders` },
          { label: 'In Prova', value: kpi.totalTrial, icon: 'ri-user-follow-line', bg: '#f59e0b', subtitle: 'Professionisti trial' },
          { label: 'Quality Media', value: qualitySummary.avgQuality ? qualitySummary.avgQuality.toFixed(1) : 'N/D', icon: 'ri-bar-chart-grouped-line', bg: '#8b5cf6', subtitle: qualitySummary.avgMonth ? `Mese: ${qualitySummary.avgMonth.toFixed(1)}` : 'Nessun dato' },
        ].map((stat, idx) => (
          <div key={idx} className="col-xl-3 col-sm-6">
            <div className="card border-0 shadow-sm" style={{ backgroundColor: stat.bg, borderRadius: '16px' }}>
              <div className="card-body py-3">
                <div className="d-flex align-items-center justify-content-between">
                  <div>
                    <h3 className="text-white mb-0 fw-bold">{stat.value}</h3>
                    <span className="text-white opacity-75 small">{stat.label}</span>
                    {stat.subtitle && <div className="text-white opacity-50" style={{ fontSize: '11px', marginTop: '2px' }}>{stat.subtitle}</div>}
                  </div>
                  <div className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center" style={{ width: '48px', height: '48px' }}>
                    <i className={`${stat.icon} text-white fs-4`}></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Row 2: Quality Trend + Specialty Distribution */}
      <div className="row g-3 mb-4">
        {/* Quality Weekly Trend */}
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-line-chart-line me-2 text-primary"></i>
                Quality Score Settimanale (ultime 8 settimane)
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              {(qualityTrend || []).length > 0 ? (
                <div className="d-flex align-items-end justify-content-between gap-2" style={{ height: '200px' }}>
                  {qualityTrend.map((w, idx) => (
                    <div key={idx} className="d-flex flex-column align-items-center flex-fill">
                      <div className="d-flex flex-column align-items-center justify-content-end" style={{ height: '160px', width: '100%' }}>
                        <div
                          style={{
                            width: '65%',
                            maxWidth: '45px',
                            height: `${Math.max((w.avgQuality / 10) * 140, 8)}px`,
                            background: `linear-gradient(180deg, ${getQualityColor(w.avgQuality)} 0%, ${getQualityColor(w.avgQuality)}cc 100%)`,
                            borderRadius: '6px 6px 0 0',
                            transition: 'height 0.3s ease',
                          }}
                          title={`Media: ${w.avgQuality} - ${w.count} professionisti`}
                        ></div>
                      </div>
                      <div className="text-center mt-2">
                        <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 500 }}>
                          {w.week ? new Date(w.week).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' }) : ''}
                        </span>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: getQualityColor(w.avgQuality) }}>{w.avgQuality}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4">
                  <i className="ri-bar-chart-line text-muted" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                  <p className="text-muted small mb-0 mt-2">Nessun dato quality disponibile</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Specialty Distribution */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-pie-chart-line me-2 text-info"></i>
                Per Specializzazione
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <div className="d-flex flex-column gap-2">
                {Object.entries(specialtyDistribution || {}).sort((a, b) => b[1].count - a[1].count).map(([key, val]) => {
                  const config = SPECIALTY_CONFIG[key] || { label: key, color: '#64748b', bg: '#f1f5f9' };
                  const pct = Math.round((val.count / totalSpecialty) * 100);
                  return (
                    <div key={key}>
                      <div className="d-flex align-items-center justify-content-between mb-1">
                        <span style={{ fontSize: '12px', fontWeight: 500, color: '#334155' }}>{config.label}</span>
                        <span style={{ fontSize: '12px', fontWeight: 700, color: config.color }}>{val.count}</span>
                      </div>
                      <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9' }}>
                        <div style={{ height: '100%', width: `${pct}%`, borderRadius: '3px', background: config.color, transition: 'width 0.3s ease' }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: Client Load + Bonus Bands + Role Distribution */}
      <div className="row g-3 mb-4">
        {/* Client Load per Area */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-scales-line me-2 text-warning"></i>
                Carico Clienti
              </h6>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Media clienti per professionista</span>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              {[
                { key: 'nutrizione', label: 'Nutrizione', icon: 'ri-restaurant-line', color: '#06b6d4' },
                { key: 'coach', label: 'Coach', icon: 'ri-run-line', color: '#22c55e' },
                { key: 'psicologia', label: 'Psicologia', icon: 'ri-mental-health-line', color: '#8b5cf6' },
              ].map((area) => {
                const load = clientLoad?.[area.key] || { clients: 0, professionals: 0, avgLoad: 0 };
                return (
                  <div key={area.key} className="d-flex align-items-center justify-content-between py-2 border-bottom" style={{ borderColor: '#f1f5f9 !important' }}>
                    <div className="d-flex align-items-center gap-2">
                      <div className="d-flex align-items-center justify-content-center" style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${area.color}15` }}>
                        <i className={area.icon} style={{ fontSize: '14px', color: area.color }}></i>
                      </div>
                      <div>
                        <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{area.label}</span>
                        <div style={{ fontSize: '11px', color: '#94a3b8' }}>{load.professionals} prof. / {load.clients} clienti</div>
                      </div>
                    </div>
                    <div className="text-end">
                      <span style={{ fontSize: '18px', fontWeight: 700, color: area.color }}>{load.avgLoad}</span>
                      <div style={{ fontSize: '10px', color: '#94a3b8' }}>media</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Bonus Bands Distribution */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-award-line me-2 text-success"></i>
                Bonus Bands
              </h6>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Distribuzione ultima settimana</span>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              {[
                { band: '100%', label: 'Eccellente (100%)', color: '#22c55e', bg: '#dcfce7' },
                { band: '60%', label: 'Buono (60%)', color: '#3b82f6', bg: '#dbeafe' },
                { band: '30%', label: 'Sufficiente (30%)', color: '#f59e0b', bg: '#fef3c7' },
                { band: '0%', label: 'Insufficiente (0%)', color: '#ef4444', bg: '#fee2e2' },
              ].map((b) => {
                const count = qualitySummary?.bonusBands?.[b.band] || 0;
                const pct = Math.round((count / totalBonusBands) * 100);
                return (
                  <div key={b.band} className="mb-3">
                    <div className="d-flex align-items-center justify-content-between mb-1">
                      <div className="d-flex align-items-center gap-2">
                        <span className="badge" style={{ background: b.bg, color: b.color, fontSize: '11px', padding: '3px 8px', borderRadius: '6px' }}>{b.band}</span>
                        <span style={{ fontSize: '12px', color: '#64748b' }}>{b.label}</span>
                      </div>
                      <span style={{ fontSize: '13px', fontWeight: 700, color: b.color }}>{count}</span>
                    </div>
                    <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9' }}>
                      <div style={{ height: '100%', width: `${pct}%`, borderRadius: '3px', background: b.color, transition: 'width 0.3s ease' }}></div>
                    </div>
                  </div>
                );
              })}
              <div className="d-flex gap-3 mt-3 pt-2 border-top">
                <div className="text-center flex-fill">
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#22c55e' }}>{qualitySummary?.trendUp || 0}</div>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}><i className="ri-arrow-up-line"></i> In crescita</div>
                </div>
                <div className="text-center flex-fill">
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#94a3b8' }}>{qualitySummary?.trendStable || 0}</div>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}><i className="ri-subtract-line"></i> Stabili</div>
                </div>
                <div className="text-center flex-fill">
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#ef4444' }}>{qualitySummary?.trendDown || 0}</div>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}><i className="ri-arrow-down-line"></i> In calo</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Role Distribution */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-user-settings-line me-2 text-danger"></i>
                Per Ruolo
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              <div className="d-flex flex-column gap-3">
                {Object.entries(roleDistribution || {}).sort((a, b) => b[1].count - a[1].count).map(([key, val]) => {
                  const config = ROLE_CONFIG_TAB[key] || { label: key, color: '#64748b', bg: '#f1f5f9' };
                  return (
                    <div key={key} className="d-flex align-items-center justify-content-between">
                      <div className="d-flex align-items-center gap-2">
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: config.color }}></div>
                        <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{config.label}</span>
                      </div>
                      <div className="d-flex align-items-center gap-2">
                        <span style={{ fontSize: '15px', fontWeight: 700, color: config.color }}>{val.count}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="mt-3 pt-3 border-top d-flex align-items-center justify-content-between">
                <span style={{ fontSize: '12px', color: '#94a3b8' }}>Inattivi</span>
                <span style={{ fontSize: '14px', fontWeight: 600, color: '#94a3b8' }}>{kpi.totalInactive}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row 4: Top Performers + Teams */}
      <div className="row g-3 mb-4">
        {/* Top Performers */}
        <div className="col-lg-7">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-trophy-line me-2 text-warning"></i>
                Top Performers
              </h6>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Per quality score settimana corrente</span>
            </div>
            {(topPerformers || []).length > 0 ? (
              <div className="table-responsive">
                <table className="table table-hover mb-0" style={{ fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #f1f5f9' }}>
                      <th className="border-0 py-2 px-4 text-muted" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>#</th>
                      <th className="border-0 py-2 text-muted" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Professionista</th>
                      <th className="border-0 py-2 text-muted" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Specializzazione</th>
                      <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Score</th>
                      <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Mese</th>
                      <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Banda</th>
                      <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topPerformers.slice(0, 8).map((p, idx) => {
                      const specConfig = SPECIALTY_CONFIG[p.specialty] || { label: p.specialty || '-', color: '#64748b' };
                      const trendInfo = getTrendIcon(p.trend);
                      return (
                        <tr key={p.id}>
                          <td className="py-2 px-4" style={{ fontWeight: 700, color: idx < 3 ? '#f59e0b' : '#94a3b8' }}>{idx + 1}</td>
                          <td className="py-2">
                            <span style={{ fontWeight: 500, color: '#1e293b' }}>{p.name}</span>
                          </td>
                          <td className="py-2">
                            <span className="badge" style={{ background: `${specConfig.color}15`, color: specConfig.color, fontSize: '11px', padding: '3px 8px', borderRadius: '6px' }}>
                              {specConfig.label}
                            </span>
                          </td>
                          <td className="py-2 text-center">
                            <span style={{ fontWeight: 700, color: getQualityColor(p.quality_final) }}>{p.quality_final}</span>
                          </td>
                          <td className="py-2 text-center">
                            <span style={{ fontWeight: 500, color: '#64748b' }}>{p.quality_month || '-'}</span>
                          </td>
                          <td className="py-2 text-center">
                            <span className="badge" style={{
                              background: p.bonus_band === '100%' ? '#dcfce7' : p.bonus_band === '60%' ? '#dbeafe' : p.bonus_band === '30%' ? '#fef3c7' : '#fee2e2',
                              color: p.bonus_band === '100%' ? '#166534' : p.bonus_band === '60%' ? '#1e40af' : p.bonus_band === '30%' ? '#92400e' : '#991b1b',
                              fontSize: '11px', padding: '3px 8px', borderRadius: '6px'
                            }}>
                              {p.bonus_band || '-'}
                            </span>
                          </td>
                          <td className="py-2 text-center">
                            <i className={trendInfo.icon} style={{ color: trendInfo.color, fontSize: '16px' }}></i>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="card-body text-center py-4">
                <i className="ri-trophy-line text-muted" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                <p className="text-muted small mb-0 mt-2">Nessun dato quality disponibile</p>
              </div>
            )}
          </div>
        </div>

        {/* Teams Summary */}
        <div className="col-lg-5">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-organization-chart me-2 text-info"></i>
                Teams Attivi
              </h6>
            </div>
            <div className="card-body p-0">
              {(teamsSummary || []).length > 0 ? (
                <div className="list-group list-group-flush">
                  {teamsSummary.map((team) => {
                    const typeColors = { nutrizione: '#06b6d4', coach: '#22c55e', psicologia: '#8b5cf6' };
                    const typeIcons = { nutrizione: 'ri-heart-pulse-line', coach: 'ri-run-line', psicologia: 'ri-mental-health-line' };
                    const color = typeColors[team.team_type] || '#64748b';
                    const icon = typeIcons[team.team_type] || 'ri-team-line';
                    return (
                      <div key={team.id} className="list-group-item d-flex align-items-center justify-content-between py-3 px-4" style={{ border: 'none', borderBottom: '1px solid #f1f5f9' }}>
                        <div className="d-flex align-items-center gap-3">
                          <div className="d-flex align-items-center justify-content-center" style={{ width: '36px', height: '36px', borderRadius: '10px', background: `${color}15` }}>
                            <i className={icon} style={{ fontSize: '16px', color }}></i>
                          </div>
                          <div>
                            <span style={{ fontWeight: 500, color: '#1e293b', fontSize: '14px' }}>{team.name}</span>
                            {team.head_name && <div style={{ fontSize: '11px', color: '#94a3b8' }}>Leader: {team.head_name}</div>}
                          </div>
                        </div>
                        <div className="d-flex align-items-center gap-2">
                          <span className="badge" style={{ background: `${color}15`, color, fontSize: '12px', padding: '4px 10px', borderRadius: '8px' }}>
                            {team.member_count} membri
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="card-body text-center py-4">
                  <i className="ri-team-line text-muted" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                  <p className="text-muted small mb-0 mt-2">Nessun team attivo</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Row 5: Trial Users */}
      {(trialUsers || []).length > 0 && (
        <div className="row g-3">
          <div className="col-12">
            <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
              <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                  <i className="ri-user-follow-line me-2 text-warning"></i>
                  Professionisti in Prova ({trialUsers.length})
                </h6>
              </div>
              <div className="card-body px-4 pb-4 pt-2">
                <div className="row g-2">
                  {trialUsers.map((u) => {
                    const specConfig = SPECIALTY_CONFIG[u.specialty] || { label: u.specialty || '-', color: '#64748b', bg: '#f1f5f9' };
                    const stageLabels = { 1: 'Stage 1 - Dashboard', 2: 'Stage 2 - Clienti', 3: 'Stage 3 - Completo' };
                    const stageColors = { 1: '#f59e0b', 2: '#3b82f6', 3: '#22c55e' };
                    return (
                      <div key={u.id} className="col-lg-4 col-md-6">
                        <div className="d-flex align-items-center gap-3 p-3 rounded-3" style={{ background: '#f8fafc' }}>
                          <div className="d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', borderRadius: '50%', background: `${specConfig.color}15`, flexShrink: 0 }}>
                            <span style={{ fontWeight: 700, fontSize: '14px', color: specConfig.color }}>
                              {u.name ? u.name.charAt(0).toUpperCase() : '?'}
                            </span>
                          </div>
                          <div className="flex-grow-1 min-w-0">
                            <div style={{ fontWeight: 500, color: '#1e293b', fontSize: '13px' }} className="text-truncate">{u.name}</div>
                            <div className="d-flex align-items-center gap-2">
                              <span className="badge" style={{ background: specConfig.bg, color: specConfig.color, fontSize: '10px', padding: '2px 6px', borderRadius: '4px' }}>
                                {specConfig.label}
                              </span>
                              <span style={{ fontSize: '10px', color: stageColors[u.trial_stage] || '#94a3b8', fontWeight: 600 }}>
                                {stageLabels[u.trial_stage] || `Stage ${u.trial_stage}`}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ==================== QUALITY TAB ====================

function QualityTab({ data, loading, error, onRetry }) {
  const getQualityColor = (val) => {
    if (!val) return '#94a3b8';
    if (val >= 8.5) return '#22c55e';
    if (val >= 7) return '#3b82f6';
    if (val >= 5.5) return '#f59e0b';
    return '#ef4444';
  };
  const getTrendIcon = (trend) => {
    if (trend === 'up') return { icon: 'ri-arrow-up-line', color: '#22c55e' };
    if (trend === 'down') return { icon: 'ri-arrow-down-line', color: '#ef4444' };
    return { icon: 'ri-subtract-line', color: '#94a3b8' };
  };

  if (error) {
    return (
      <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
        <div className="card-body text-center py-5">
          <i className="ri-error-warning-line text-danger" style={{ fontSize: '48px', opacity: 0.6 }}></i>
          <h5 className="text-muted mt-3">{error}</h5>
          <p className="text-muted small">Assicurati che il backend sia avviato e riprova.</p>
          <button className="btn btn-primary btn-sm" style={{ borderRadius: '8px' }} onClick={onRetry}>
            <i className="ri-refresh-line me-1"></i> Riprova
          </button>
        </div>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="row g-3">
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
        <div className="col-lg-8"><SkeletonCard height="280px" /></div>
        <div className="col-lg-4"><SkeletonCard height="280px" /></div>
        <div className="col-12"><SkeletonCard height="320px" /></div>
      </div>
    );
  }

  const { qualitySummary, qualityTrend, topPerformers } = data;
  const qs = qualitySummary || {};
  const totalBonusBands = Object.values(qs.bonusBands || {}).reduce((a, b) => a + b, 0) || 1;
  const maxTrend = Math.max(...(qualityTrend || []).map(w => w.avgQuality || 0), 1);

  return (
    <>
      {/* KPI Quality */}
      <div className="row g-3 mb-4">
        {[
          { label: 'Quality media', value: qs.avgQuality != null ? qs.avgQuality.toFixed(1) : 'N/D', icon: 'ri-star-line', bg: '#8b5cf6', subtitle: 'Settimana corrente' },
          { label: 'Media mese', value: qs.avgMonth != null ? qs.avgMonth.toFixed(1) : 'N/D', icon: 'ri-calendar-line', bg: '#3b82f6' },
          { label: 'Media trimestre', value: qs.avgTrim != null ? qs.avgTrim.toFixed(1) : 'N/D', icon: 'ri-bar-chart-grouped-line', bg: '#06b6d4' },
          {
            label: 'Trend',
            value: `${qs.trendUp || 0} ↑ / ${qs.trendStable || 0} → / ${qs.trendDown || 0} ↓`,
            icon: 'ri-trending-up-line',
            bg: '#22c55e',
            subtitle: 'In crescita / Stabili / In calo',
          },
        ].map((stat, idx) => (
          <div key={idx} className="col-xl-3 col-sm-6">
            <div className="card border-0 shadow-sm" style={{ backgroundColor: stat.bg, borderRadius: '16px' }}>
              <div className="card-body py-3">
                <div className="d-flex align-items-center justify-content-between">
                  <div>
                    <h3 className="text-white mb-0 fw-bold" style={{ fontSize: stat.value && stat.value.length > 12 ? '1rem' : undefined }}>{stat.value}</h3>
                    <span className="text-white opacity-75 small">{stat.label}</span>
                    {stat.subtitle && <div className="text-white opacity-50" style={{ fontSize: '11px', marginTop: '2px' }}>{stat.subtitle}</div>}
                  </div>
                  <div className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center" style={{ width: '48px', height: '48px' }}>
                    <i className={`${stat.icon} text-white fs-4`}></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Trend settimanale + Bonus bands */}
      <div className="row g-3 mb-4">
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-line-chart-line me-2 text-primary"></i>
                Trend Quality (ultime 8 settimane)
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              {(qualityTrend || []).length > 0 ? (
                <div className="d-flex align-items-end justify-content-between gap-1" style={{ height: '180px' }}>
                  {(qualityTrend || []).map((w, idx) => (
                    <div key={idx} className="d-flex flex-column align-items-center flex-fill">
                      <div style={{ height: '140px', width: '100%', display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
                        <div
                          style={{
                            width: '70%',
                            maxWidth: '36px',
                            height: `${Math.max((w.avgQuality / maxTrend) * 120, 4)}px`,
                            background: 'linear-gradient(180deg, #8b5cf6 0%, #6d28d9 100%)',
                            borderRadius: '6px 6px 0 0',
                          }}
                          title={`${w.week}: ${w.avgQuality}`}
                        />
                      </div>
                      <div className="text-center mt-2">
                        <div style={{ fontSize: '11px', color: '#64748b' }}>{w.week ? new Date(w.week).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' }) : '-'}</div>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e293b' }}>{w.avgQuality}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-5 text-muted">Nessun dato trend</div>
              )}
            </div>
          </div>
        </div>
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-award-line me-2 text-success"></i>
                Bonus Bands
              </h6>
            </div>
            <div className="card-body px-4 pb-4 pt-2">
              {[
                { band: '100%', color: '#22c55e', bg: '#dcfce7' },
                { band: '60%', color: '#3b82f6', bg: '#dbeafe' },
                { band: '30%', color: '#f59e0b', bg: '#fef3c7' },
                { band: '0%', color: '#ef4444', bg: '#fee2e2' },
              ].map((b) => {
                const count = qs.bonusBands?.[b.band] || 0;
                const pct = Math.round((count / totalBonusBands) * 100);
                return (
                  <div key={b.band} className="d-flex align-items-center justify-content-between mb-2">
                    <span className="badge" style={{ background: b.bg, color: b.color, fontSize: '11px' }}>{b.band}</span>
                    <span style={{ fontWeight: 700, color: b.color }}>{count}</span>
                    <div style={{ width: '60%', height: '8px', borderRadius: '4px', background: '#f1f5f9' }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: b.color, borderRadius: '4px' }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Top Performers */}
      <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
          <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
            <i className="ri-trophy-line me-2 text-warning"></i>
            Top 10 Quality
          </h6>
        </div>
        {(topPerformers || []).length > 0 ? (
          <div className="table-responsive">
            <table className="table table-hover mb-0" style={{ fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #f1f5f9' }}>
                  <th className="border-0 py-2 px-4 text-muted" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>#</th>
                  <th className="border-0 py-2 text-muted" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Professionista</th>
                  <th className="border-0 py-2 text-muted" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Specializzazione</th>
                  <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Score</th>
                  <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Banda</th>
                  <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Trend</th>
                </tr>
              </thead>
              <tbody>
                {topPerformers.map((p, idx) => {
                  const trendInfo = getTrendIcon(p.trend);
                  return (
                    <tr key={p.id}>
                      <td className="py-2 px-4" style={{ fontWeight: 700, color: idx < 3 ? '#f59e0b' : '#94a3b8' }}>{idx + 1}</td>
                      <td className="py-2"><span style={{ fontWeight: 500, color: '#1e293b' }}>{p.name}</span></td>
                      <td className="py-2"><span style={{ fontSize: '12px', color: '#64748b' }}>{p.specialty || '-'}</span></td>
                      <td className="py-2 text-center"><span style={{ fontWeight: 700, color: getQualityColor(p.quality_final) }}>{p.quality_final ?? '-'}</span></td>
                      <td className="py-2 text-center">
                        <span className="badge" style={{
                          background: p.bonus_band === '100%' ? '#dcfce7' : p.bonus_band === '60%' ? '#dbeafe' : p.bonus_band === '30%' ? '#fef3c7' : '#fee2e2',
                          color: p.bonus_band === '100%' ? '#166534' : p.bonus_band === '60%' ? '#1e40af' : p.bonus_band === '30%' ? '#92400e' : '#991b1b',
                          fontSize: '11px',
                        }}>{p.bonus_band || '-'}</span>
                      </td>
                      <td className="py-2 text-center">
                        <i className={trendInfo.icon} style={{ color: trendInfo.color, fontSize: '16px' }}></i>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-5 text-muted">Nessun dato quality disponibile</div>
        )}
      </div>
    </>
  );
}

// ==================== TOP PEOPLE CARD ====================

function TopPeopleCard({ title, subtitle, icon, color, bgColor, people }) {
  return (
    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px', overflow: 'hidden' }}>
      <div className="card-header border-0 py-3 px-4" style={{ background: bgColor }}>
        <div className="d-flex align-items-center justify-content-between">
          <div>
            <h6 className="mb-0" style={{ fontWeight: 600, color }}>
              <i className={`${icon} me-2`}></i>{title}
            </h6>
            <span style={{ fontSize: '11px', color: `${color}99` }}>{subtitle}</span>
          </div>
          {people.length > 0 && (
            <span className="badge" style={{ background: color, color: '#fff', fontSize: '11px' }}>{people.length}</span>
          )}
        </div>
      </div>
      <div className="card-body p-0">
        {people.length > 0 ? (
          <div className="list-group list-group-flush">
            {people.slice(0, 5).map((person, idx) => (
              <div key={person.id || idx} className="list-group-item d-flex align-items-center justify-content-between py-3 px-4" style={{ border: 'none', borderBottom: '1px solid #f1f5f9' }}>
                <div className="d-flex align-items-center">
                  <span className="me-3 d-flex align-items-center justify-content-center" style={{
                    width: '28px', height: '28px', borderRadius: '50%',
                    background: idx === 0 ? '#fef3c7' : idx === 1 ? '#e5e7eb' : idx === 2 ? '#fed7aa' : '#f1f5f9',
                    color: idx === 0 ? '#92400e' : idx === 1 ? '#374151' : idx === 2 ? '#c2410c' : '#64748b',
                    fontSize: '12px', fontWeight: 700
                  }}>
                    {idx + 1}
                  </span>
                  <div>
                    <span style={{ fontWeight: 500, color: '#334155', fontSize: '14px' }}>{person.name}</span>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>{person.email}</div>
                  </div>
                </div>
                <div className="d-flex align-items-center gap-1">
                  <span style={{ fontWeight: 700, fontSize: '16px', color }}>{person.count}</span>
                  <span style={{ fontSize: '11px', color: '#94a3b8' }}>training</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-4"><p className="text-muted mb-0" style={{ fontSize: '13px' }}>Nessun dato</p></div>
        )}
      </div>
    </div>
  );
}

// ==================== QUICK LINKS CONFIG ====================

const QUICK_LINKS = [
  { label: 'Pazienti', to: '/clienti-lista', icon: 'ri-group-line', color: '#3b82f6', bgColor: '#eff6ff', iconBg: '#dbeafe' },
  { label: 'Team', to: '/team-lista', icon: 'ri-team-line', color: '#8b5cf6', bgColor: '#f5f3ff', iconBg: '#ede9fe' },
  { label: 'Teams', to: '/teams', icon: 'ri-organization-chart', color: '#06b6d4', bgColor: '#ecfeff', iconBg: '#cffafe' },
  { label: 'In Prova', to: '/in-prova', icon: 'ri-user-follow-line', color: '#f59e0b', bgColor: '#fffbeb', iconBg: '#fef3c7' },
  { label: 'Check', to: '/check-azienda', icon: 'ri-checkbox-circle-line', color: '#22c55e', bgColor: '#f0fdf4', iconBg: '#dcfce7' },
  { label: 'Formazione', to: '/formazione', icon: 'ri-book-open-line', color: '#ec4899', bgColor: '#fdf2f8', iconBg: '#fce7f3' },
  { label: 'Chat', to: '/chat', icon: 'ri-chat-3-line', color: '#14b8a6', bgColor: '#f0fdfa', iconBg: '#ccfbf1' },
  { label: 'Calendario', to: '/calendario', icon: 'ri-calendar-line', color: '#ef4444', bgColor: '#fef2f2', iconBg: '#fee2e2' },
];

// ==================== SKELETON COMPONENTS ====================

function SkeletonNumber() {
  return <span className="placeholder-glow"><span className="placeholder col-4" style={{ borderRadius: '4px' }}>&nbsp;&nbsp;&nbsp;</span></span>;
}

function SkeletonList({ count = 3 }) {
  return (
    <div className="d-flex flex-column gap-2">
      {[...Array(count)].map((_, i) => (
        <div key={i} className="placeholder-glow d-flex align-items-center justify-content-between">
          <span className="placeholder col-5" style={{ borderRadius: '4px', height: '14px' }}></span>
          <span className="placeholder col-2" style={{ borderRadius: '4px', height: '14px' }}></span>
        </div>
      ))}
    </div>
  );
}

function SkeletonCard({ height = '100px' }) {
  return (
    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px', height, overflow: 'hidden' }}>
      <div className="card-body placeholder-glow d-flex align-items-center gap-3 p-4">
        <span className="placeholder rounded-circle" style={{ width: '56px', height: '56px', flexShrink: 0 }}></span>
        <div className="flex-grow-1">
          <span className="placeholder col-6 mb-2 d-block" style={{ height: '12px', borderRadius: '4px' }}></span>
          <span className="placeholder col-4" style={{ height: '24px', borderRadius: '4px' }}></span>
        </div>
      </div>
    </div>
  );
}

// ==================== STAT ROW ====================

function StatRow({ label, value, color }) {
  return (
    <div className="d-flex align-items-center justify-content-between py-1">
      <span style={{ fontSize: '13px', color: '#64748b' }}>{label}</span>
      <span style={{ fontSize: '15px', fontWeight: 700, color }}>{value}</span>
    </div>
  );
}

// ==================== RATING CARD ====================

function RatingCard({ label, value, icon, color, bgColor }) {
  const rating = value ? parseFloat(value).toFixed(1) : '-';
  const numericValue = value ? parseFloat(value) : 0;

  const getRatingStatus = () => {
    if (!value) return null;
    if (numericValue >= 8) return { label: 'Buono', bg: '#dcfce7', color: '#166534' };
    if (numericValue >= 7) return { label: 'Da migliorare', bg: '#fef3c7', color: '#92400e' };
    return { label: 'Male', bg: '#fee2e2', color: '#991b1b' };
  };

  const status = getRatingStatus();

  return (
    <div className="col-lg-4 col-sm-6">
      <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
        <div className="card-body p-4">
          <div className="d-flex align-items-center">
            <div
              className="d-flex align-items-center justify-content-center me-3"
              style={{ width: '56px', height: '56px', borderRadius: '12px', background: bgColor }}
            >
              <i className={icon} style={{ fontSize: '24px', color }}></i>
            </div>
            <div className="flex-grow-1">
              <p className="mb-1 text-muted" style={{ fontSize: '13px' }}>{label}</p>
              <div className="d-flex align-items-center gap-2">
                <h3 className="mb-0" style={{ fontWeight: 700, color: '#1e293b' }}>{rating}</h3>
                <span className="text-muted" style={{ fontSize: '14px' }}>/10</span>
                {status && (
                  <span className="badge" style={{ background: status.bg, color: status.color, fontSize: '11px', padding: '4px 8px', borderRadius: '6px' }}>
                    {status.label}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ==================== TEAM RATINGS LIST ====================

function TeamRatingsList({ title, teams, icon, color, bgColor }) {
  const getRatingStatus = (value) => {
    const n = parseFloat(value);
    if (n >= 8) return { label: 'Buono', bg: '#dcfce7', color: '#166534' };
    if (n >= 7) return { label: 'Da migliorare', bg: '#fef3c7', color: '#92400e' };
    return { label: 'Male', bg: '#fee2e2', color: '#991b1b' };
  };

  return (
    <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)', overflow: 'hidden' }}>
      <div className="card-header border-0 py-3 px-4" style={{ background: bgColor }}>
        <div className="d-flex align-items-center">
          <i className={icon} style={{ color, fontSize: '20px', marginRight: '8px' }}></i>
          <h6 className="mb-0" style={{ fontWeight: 600, color }}>{title}</h6>
        </div>
      </div>
      <div className="card-body p-0">
        {teams.length > 0 ? (
          <div className="list-group list-group-flush">
            {teams.map((team, idx) => {
              const status = getRatingStatus(team.average);
              return (
                <div key={team.id || idx} className="list-group-item d-flex align-items-center justify-content-between py-3 px-4" style={{ border: 'none', borderBottom: '1px solid #f1f5f9' }}>
                  <div className="d-flex align-items-center">
                    {team.head?.avatar_path ? (
                      <img src={team.head.avatar_path} alt="" className="rounded-circle me-3" style={{ width: '36px', height: '36px', objectFit: 'cover', border: `2px solid ${color}` }} />
                    ) : (
                      <div className="d-flex align-items-center justify-content-center me-3" style={{ width: '36px', height: '36px', borderRadius: '50%', background: bgColor, color, fontWeight: 700, fontSize: '12px' }}>
                        {team.head?.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || team.name?.substring(0, 2).toUpperCase()}
                      </div>
                    )}
                    <div>
                      <span style={{ fontWeight: 600, color: '#334155', fontSize: '14px', display: 'block' }}>{team.name}</span>
                      {team.head && <span style={{ fontSize: '11px', color: '#94a3b8' }}>{team.head.full_name}</span>}
                    </div>
                  </div>
                  <div className="d-flex align-items-center gap-2">
                    <span style={{ fontWeight: 700, fontSize: '16px', color: parseFloat(team.average) >= 7 ? '#22c55e' : '#ef4444' }}>{team.average}</span>
                    <span className="text-muted" style={{ fontSize: '12px' }}>({team.count})</span>
                    <span className="badge" style={{ background: status.bg, color: status.color, fontSize: '10px', padding: '3px 6px', borderRadius: '6px' }}>{status.label}</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-4"><p className="text-muted mb-0" style={{ fontSize: '13px' }}>Nessun team trovato</p></div>
        )}
      </div>
    </div>
  );
}

// ==================== NEGATIVE CHECKS TABLE ====================

function NegativeChecksTable({ negativeChecks, negativePage, setNegativePage, perPage }) {
  const totalPages = Math.ceil(negativeChecks.length / perPage);
  const startIdx = (negativePage - 1) * perPage;
  const paginatedChecks = negativeChecks.slice(startIdx, startIdx + perPage);

  return (
    <div className="card border-0 mb-4" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
      <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
        <h5 className="mb-0" style={{ fontWeight: 600, color: '#1e293b' }}>
          <i className="ri-alert-line me-2 text-danger"></i>
          Check Negativi Ultimo Mese
          <span className="badge bg-danger ms-2" style={{ fontSize: '12px' }}>{negativeChecks.length}</span>
        </h5>
      </div>
      <div className="card-body p-0">
        {negativeChecks.length > 0 ? (
          <>
            <div className="table-responsive">
              <table className="table mb-0">
                <thead>
                  <tr style={{ background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)' }}>
                    <th style={tableHeaderStyle}>Paziente</th>
                    <th style={tableHeaderStyle}>Data</th>
                    <th style={tableHeaderStyle}>Rating Negativi</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedChecks.map((check, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={tableCellStyle}>
                        <span style={{ fontWeight: 600, color: '#334155' }}>{check.cliente_nome}</span>
                      </td>
                      <td style={tableCellStyle}>
                        <span className="text-muted">{check.submit_date}</span>
                      </td>
                      <td style={tableCellStyle}>
                        <div className="d-flex flex-wrap gap-2">
                          {check.negativeRatings?.map((r, i) => (
                            <div key={i} className="d-flex align-items-center gap-2" style={{ background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)', padding: '6px 12px', borderRadius: '8px' }}>
                              {r.isProgress ? (
                                <img src={logoFoglia} alt="Percorso" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover' }} />
                              ) : r.professionals && r.professionals.length > 0 ? (
                                <div className="d-flex" style={{ marginLeft: '-4px' }}>
                                  {r.professionals.slice(0, 2).map((prof, pi) => (
                                    prof.avatar_path ? (
                                      <img key={pi} src={prof.avatar_path} alt="" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover', border: '2px solid #fee2e2', marginLeft: pi > 0 ? '-8px' : '0' }} onError={(e) => { e.target.style.display = 'none'; }} />
                                    ) : (
                                      <div key={pi} style={{ width: '24px', height: '24px', borderRadius: '50%', background: '#991b1b', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700, border: '2px solid #fee2e2', marginLeft: pi > 0 ? '-8px' : '0' }}>
                                        {prof.nome?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                                      </div>
                                    )
                                  ))}
                                </div>
                              ) : null}
                              <span style={{ color: '#991b1b', fontWeight: 600, fontSize: '12px' }}>{r.type}: {r.value}</span>
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div className="d-flex align-items-center justify-content-between px-4 py-3 border-top">
                <span className="text-muted" style={{ fontSize: '13px' }}>
                  {startIdx + 1}-{Math.min(startIdx + perPage, negativeChecks.length)} di {negativeChecks.length}
                </span>
                <div className="d-flex gap-2">
                  <button className="btn btn-sm btn-light" style={{ borderRadius: '8px' }} onClick={() => setNegativePage(p => Math.max(1, p - 1))} disabled={negativePage === 1}>
                    <i className="ri-arrow-left-s-line"></i> Prec
                  </button>
                  <button className="btn btn-sm btn-light" style={{ borderRadius: '8px' }} onClick={() => setNegativePage(p => Math.min(totalPages, p + 1))} disabled={negativePage === totalPages}>
                    Succ <i className="ri-arrow-right-s-line"></i>
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-5">
            <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '48px' }}></i>
            <p className="text-muted mt-2 mb-0">Nessun check negativo questo mese</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ==================== RANKING TABLE ====================

function RankingTable({ title, professionals, color, bgColor, icon, isTop }) {
  const [page, setPage] = useState(1);
  const PER_PAGE = 5;
  const totalPages = Math.ceil(professionals.length / PER_PAGE);
  const startIdx = (page - 1) * PER_PAGE;
  const paginatedProfs = professionals.slice(startIdx, startIdx + PER_PAGE);

  return (
    <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)', overflow: 'hidden' }}>
      <div className="card-header border-0 py-3 px-4" style={{ background: bgColor }}>
        <div className="d-flex align-items-center justify-content-between">
          <div className="d-flex align-items-center">
            <i className={icon} style={{ color, fontSize: '20px', marginRight: '8px' }}></i>
            <h6 className="mb-0" style={{ fontWeight: 600, color }}>{title}</h6>
          </div>
          {professionals.length > 0 && (
            <span className="badge ms-2" style={{ background: color, color: '#fff', fontSize: '11px' }}>{professionals.length}</span>
          )}
        </div>
      </div>
      <div className="card-body p-0">
        {professionals.length > 0 ? (
          <>
            <div className="list-group list-group-flush">
              {paginatedProfs.map((prof, idx) => {
                const globalIdx = startIdx + idx;
                return (
                  <div key={prof.id || idx} className="list-group-item d-flex align-items-center justify-content-between py-3 px-4" style={{ border: 'none', borderBottom: '1px solid #f1f5f9' }}>
                    <div className="d-flex align-items-center">
                      <span className="me-3 d-flex align-items-center justify-content-center" style={{
                        width: '28px', height: '28px', borderRadius: '50%',
                        background: isTop ? (globalIdx === 0 ? '#fef3c7' : globalIdx === 1 ? '#e5e7eb' : globalIdx === 2 ? '#fed7aa' : '#f1f5f9') : '#fee2e2',
                        color: isTop ? (globalIdx === 0 ? '#92400e' : globalIdx === 1 ? '#374151' : globalIdx === 2 ? '#c2410c' : '#64748b') : '#991b1b',
                        fontSize: '12px', fontWeight: 700
                      }}>
                        {globalIdx + 1}
                      </span>
                      {prof.avatar_path ? (
                        <img src={prof.avatar_path} alt="" className="rounded-circle me-3" style={{ width: '36px', height: '36px', objectFit: 'cover', border: `2px solid ${color}` }} />
                      ) : (
                        <div className="d-flex align-items-center justify-content-center me-3" style={{ width: '36px', height: '36px', borderRadius: '50%', background: bgColor, color, fontWeight: 700, fontSize: '12px' }}>
                          {prof.nome?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??'}
                        </div>
                      )}
                      <span style={{ fontWeight: 500, color: '#334155', fontSize: '14px' }}>{prof.nome || 'N/D'}</span>
                    </div>
                    <div className="d-flex align-items-center gap-2">
                      <span style={{ fontWeight: 700, fontSize: '16px', color: parseFloat(prof.average) >= 7 ? '#22c55e' : '#ef4444' }}>{prof.average}</span>
                      <span className="text-muted" style={{ fontSize: '12px' }}>({prof.count} check)</span>
                    </div>
                  </div>
                );
              })}
            </div>
            {totalPages > 1 && (
              <div className="d-flex align-items-center justify-content-between px-4 py-2 border-top">
                <span className="text-muted" style={{ fontSize: '11px' }}>{startIdx + 1}-{Math.min(startIdx + PER_PAGE, professionals.length)} di {professionals.length}</span>
                <div className="d-flex gap-1">
                  <button className="btn btn-sm btn-light" style={{ borderRadius: '6px', padding: '2px 8px', fontSize: '12px' }} onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                    <i className="ri-arrow-left-s-line"></i>
                  </button>
                  <button className="btn btn-sm btn-light" style={{ borderRadius: '6px', padding: '2px 8px', fontSize: '12px' }} onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                    <i className="ri-arrow-right-s-line"></i>
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-4"><p className="text-muted mb-0" style={{ fontSize: '13px' }}>Nessun dato disponibile</p></div>
        )}
      </div>
    </div>
  );
}

// ==================== STYLES ====================

const tableHeaderStyle = {
  padding: '16px 20px',
  fontSize: '11px',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  color: '#64748b',
  borderBottom: '2px solid #e2e8f0'
};

const tableCellStyle = {
  padding: '16px 20px',
  fontSize: '14px',
  color: '#334155',
  verticalAlign: 'middle'
};

export default Welcome;

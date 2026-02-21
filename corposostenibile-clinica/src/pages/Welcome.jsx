import { useState, useEffect, useCallback } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { Collapse } from 'react-bootstrap';
import dashboardService from '../services/dashboardService';
import teamService from '../services/teamService';
import trialUserService from '../services/trialUserService';
import trainingService from '../services/trainingService';
import clientiService from '../services/clientiService';
import checkService from '../services/checkService';
import logoFoglia from '../images/logo_foglia.png';

// Import Dashboard Components
import {
  MobileSection,
  SkeletonNumber,
  SkeletonList,
  SkeletonCard,
  StatRow,
  RatingCard,
  TeamRatingsList,
  NegativeChecksTable,
  RankingTable
} from './dashboard/DashboardShared';
import FormazioneDashboard from './dashboard/FormazioneDashboard';
import PazientiDashboard from './dashboard/PazientiDashboard';
import CheckDashboard from './dashboard/CheckDashboard';
import ProfessionistiDashboard from './dashboard/ProfessionistiDashboard';
import QualityDashboard from './dashboard/QualityDashboard';

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


function Welcome() {
  const { user } = useOutletContext();
  const [activeTab, setActiveTab] = useState('panoramica');
  const [selectedKpiMobile, setSelectedKpiMobile] = useState(0);
  const [panoramaMobileOpen, setPanoramaMobileOpen] = useState('quick');

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
  }, [activeTab, trainingLoaded, loadTrainingData, pazientiLoaded, loadPazientiData, checkDashLoaded, loadCheckDashData, profLoaded, loadProfData]);

  // Load all data in parallel, each section independent
  useEffect(() => {
    loadCustomerStats();
    loadTeamStats();
    loadTrialStats();
    loadCheckData();
  }, []);

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
    setCustomerLoading(true);
    setTeamLoading(true);
    setTrialLoading(true);
    setCheckLoading(true);
    loadCustomerStats();
    loadTeamStats();
    loadTrialStats();
    loadCheckData();
  };

  return (
    <>
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
        <div>
          <h4 className="mb-0 fw-bold text-dark mobile-text-lg">
            Ciao, {user?.first_name || 'Admin'}!
          </h4>
          <p className="text-muted mb-0 small d-none d-sm-block">Panoramica Piattaforma</p>
        </div>
        <button
          onClick={refreshAll}
          className="btn btn-light d-flex align-items-center gap-2 btn-sm"
          style={{ borderRadius: '12px' }}
        >
          <i className="ri-refresh-line"></i>
          <span className="d-none d-sm-inline">Aggiorna</span>
        </button>
      </div>

      {/* Tabs Navigation */}
      <div className="card border-0 shadow-sm mb-3 mb-md-4" style={{ borderRadius: '12px' }}>
        <div className="card-body p-2 py-md-2">
          <div className="tabs-scroll-mobile">
            <div className="d-flex gap-2" style={{ flexWrap: 'nowrap', minWidth: 'max-content' }}>
              {TABS.map((tab) => (
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
                    whiteSpace: 'nowrap',
                  }}
                >
                  <i className={`${tab.icon} me-2`}></i>
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'panoramica' ? (
        <>
          {/* SEZIONE 1: KPI Pazienti */}
          {(() => {
            const panoramaKpiStats = [
              { label: 'Pazienti Totali', value: customerStats?.total_clienti, icon: 'ri-group-line', bg: 'primary' },
              { label: 'Nutrizione Attivi', value: customerStats?.nutrizione_attivo, icon: 'ri-restaurant-line', bg: 'success' },
              { label: 'Coach Attivi', value: customerStats?.coach_attivo, icon: 'ri-run-line', bg: 'warning' },
              { label: 'Psicologia Attivi', value: customerStats?.psicologia_attivo, icon: 'ri-mental-health-line', customBg: '#8b5cf6' },
              { label: 'Nuovi questo Mese', value: customerStats?.kpi?.new_month, icon: 'ri-user-add-line', customBg: '#06b6d4' },
            ];
            const stat = panoramaKpiStats[selectedKpiMobile] || panoramaKpiStats[0];
            return (
              <>
                {/* Mobile: dropdown + una sola card */}
                <div className="d-md-none mb-3">
                  <div className="rounded-3 border bg-light bg-opacity-50 px-3 py-2 shadow-sm">
                    <label className="form-label small text-muted mb-1">KPI</label>
                    <select
                      className="form-select form-select-sm rounded-2 border"
                      value={selectedKpiMobile}
                      onChange={(e) => setSelectedKpiMobile(Number(e.target.value))}
                    >
                      {panoramaKpiStats.map((s, idx) => (
                        <option key={idx} value={idx}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                  <div
                    className={`card border-0 shadow-sm mt-2 ${stat.bg ? `bg-${stat.bg}` : ''}`}
                    style={stat.customBg ? { backgroundColor: stat.customBg } : {}}
                  >
                    <div className="card-body py-2 px-3">
                      <div className="d-flex align-items-center justify-content-between">
                        <div>
                          <h3 className="text-white mb-0 fw-bold fs-5">
                            {customerLoading ? <SkeletonNumber /> : (stat.value ?? 0)}
                          </h3>
                          <span className="text-white opacity-75 small">{stat.label}</span>
                        </div>
                        <div
                          className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
                          style={{ width: '40px', height: '40px' }}
                        >
                          <i className={`${stat.icon} text-white`} style={{ fontSize: '1.1rem' }}></i>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                {/* Desktop: griglia di card */}
                <div className="d-none d-md-block">
                  <div className="row g-3 mb-4">
                    {panoramaKpiStats.map((s, idx) => (
                      <div key={idx} className="col-xl col-sm-6">
                        <div
                          className={`card border-0 shadow-sm ${s.bg ? `bg-${s.bg}` : ''}`}
                          style={s.customBg ? { backgroundColor: s.customBg } : {}}
                        >
                          <div className="card-body py-3">
                            <div className="d-flex align-items-center justify-content-between">
                              <div>
                                <h3 className="text-white mb-0 fw-bold">
                                  {customerLoading ? <SkeletonNumber /> : (s.value ?? 0)}
                                </h3>
                                <span className="text-white opacity-75 small">{s.label}</span>
                              </div>
                              <div
                                className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center"
                                style={{ width: '48px', height: '48px' }}
                              >
                                <i className={`${s.icon} text-white fs-4`}></i>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            );
          })()}

          {/* SEZIONE 2: Quick Nav + Team/Trial KPI */}
          <MobileSection
            title="Accesso Rapido e Team"
            id="quick"
            openId={panoramaMobileOpen}
            onToggle={setPanoramaMobileOpen}
            icon="ri-apps-line"
          >
            <div className="row g-2 g-md-3 mb-0 mb-md-4">
              {/* Quick Navigation */}
              <div className="col-lg-8">
                <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                  <div className="card-header bg-white border-0 py-2 py-md-3 px-3 px-md-4" style={{ borderRadius: '16px 16px 0 0' }}>
                    <h6 className="mb-0 fw-semibold small" style={{ color: '#1e293b', fontSize: '0.95rem' }}>
                      <i className="ri-apps-line me-2 text-primary"></i>
                      Accesso Rapido
                    </h6>
                  </div>
                  <div className="card-body pt-0 px-3 px-md-4 pb-3 pb-md-4">
                    {/* Mobile: una riga a scorrimento orizzontale */}
                    <div className="d-md-none tabs-scroll-mobile">
                      <div className="d-flex gap-2" style={{ flexWrap: 'nowrap', minWidth: 'max-content' }}>
                        {QUICK_LINKS.map((link, idx) => (
                          <Link
                            key={idx}
                            to={link.to}
                            className="d-flex align-items-center gap-2 p-2 text-decoration-none rounded-3 flex-shrink-0"
                            style={{
                              background: link.bgColor,
                              transition: 'transform 0.15s, box-shadow 0.15s',
                              minWidth: '120px',
                            }}
                            onMouseOver={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)'; }}
                            onMouseOut={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}
                          >
                            <div
                              className="d-flex align-items-center justify-content-center rounded-circle"
                              style={{ width: '32px', height: '32px', background: link.iconBg, flexShrink: 0 }}
                            >
                              <i className={link.icon} style={{ color: link.color, fontSize: '14px' }}></i>
                            </div>
                            <span style={{ color: '#334155', fontWeight: 500, fontSize: '12px', whiteSpace: 'nowrap' }}>{link.label}</span>
                          </Link>
                        ))}
                      </div>
                    </div>
                    {/* Desktop: griglia */}
                    <div className="d-none d-md-block">
                      <div className="row g-2">
                        {QUICK_LINKS.map((link, idx) => (
                          <div key={idx} className="col-md-4 col-xl-3">
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
              </div>

              {/* Team + Trial Stats */}
              <div className="col-lg-4">
                <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                  <div className="card-header bg-white border-0 py-2 py-md-3 px-3 px-md-4" style={{ borderRadius: '16px 16px 0 0' }}>
                    <h6 className="mb-0 fw-semibold small" style={{ color: '#1e293b', fontSize: '0.95rem' }}>
                      <i className="ri-team-line me-2 text-info"></i>
                      Team
                    </h6>
                  </div>
                  <div className="card-body pt-0 px-3 px-md-4 pb-2 pb-md-3">
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
            </div>
          </MobileSection>

          {/* SEZIONE 3: Valutazioni Medie per Team */}
          <MobileSection
            title="Valutazioni Medie per Team"
            id="valutazioni"
            openId={panoramaMobileOpen}
            onToggle={setPanoramaMobileOpen}
            icon="ri-bar-chart-grouped-line"
          >
            <div className="row g-2 g-md-3 mb-0 mb-md-4">
              <div className="col-12">
                <h5 className="mb-2 mb-md-3 small d-none d-md-block" style={{ fontWeight: 600, color: '#1e293b', fontSize: '1rem' }}>
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
                  <RatingCard
                    label="Team Nutrizione"
                    value={checkStats?.stats?.avg_nutrizionista}
                    icon="ri-heart-pulse-line"
                    color="#22c55e"
                    bgColor="#dcfce7"
                  />
                  <RatingCard
                    label="Team Coach"
                    value={checkStats?.stats?.avg_coach}
                    icon="ri-run-line"
                    color="#f97316"
                    bgColor="#ffedd5"
                  />
                  <RatingCard
                    label="Team Psicologia"
                    value={checkStats?.stats?.avg_psicologo}
                    icon="ri-mental-health-line"
                    color="#ec4899"
                    bgColor="#fce7f3"
                  />
                </>
              )}
            </div>
          </MobileSection>

          {/* SEZIONE 3B: Valutazioni per Singolo Team */}
          {!checkLoading && teamRatings && (teamRatings.nutrizione.length > 0 || teamRatings.coach.length > 0 || teamRatings.psicologia.length > 0) && (
            <MobileSection
              title="Valutazioni per Singolo Team"
              id="valutazioni-singolo"
              openId={panoramaMobileOpen}
              onToggle={setPanoramaMobileOpen}
              icon="ri-team-line"
            >
              <div className="row g-2 g-md-3 mb-0 mb-md-4">
                <div className="col-12">
                  <h5 className="mb-2 mb-md-3 small d-none d-md-block" style={{ fontWeight: 600, color: '#1e293b', fontSize: '1rem' }}>
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
            </MobileSection>
          )}

          {/* SEZIONE 4: Check Negativi */}
          {!checkLoading && (
            <MobileSection
              title="Check Negativi"
              id="check-negativi"
              openId={panoramaMobileOpen}
              onToggle={setPanoramaMobileOpen}
              icon="ri-error-warning-line"
            >
              <NegativeChecksTable
                negativeChecks={negativeChecks}
                negativePage={negativePage}
                setNegativePage={setNegativePage}
                perPage={NEGATIVE_PER_PAGE}
                logoFoglia={logoFoglia}
              />
            </MobileSection>
          )}

          {/* SEZIONE 5: Top 5 Professionisti */}
          {!checkLoading && rankings && (
            <MobileSection
              title="Top 5 e Professionisti da Migliorare"
              id="top5"
              openId={panoramaMobileOpen}
              onToggle={setPanoramaMobileOpen}
              icon="ri-trophy-line"
            >
              <>
                <div className="row g-2 g-md-3 mb-0 mb-md-4">
                  <div className="col-12">
                    <h5 className="mb-2 mb-md-3 small d-none d-md-block" style={{ fontWeight: 600, color: '#1e293b', fontSize: '1rem' }}>
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

                <div className="row g-2 g-md-3 mb-0 mb-md-4">
                  <div className="col-12">
                    <h5 className="mb-2 mb-md-3 small d-none d-md-block" style={{ fontWeight: 600, color: '#1e293b', fontSize: '1rem' }}>
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
            </MobileSection>
          )}
        </>
      ) : activeTab === 'chat' ? (
        <div className="text-center py-5">
          <i className="ri-chat-3-line text-muted" style={{ fontSize: '48px', opacity: 0.3 }}></i>
          <p className="text-muted mt-3">Modulo Chat in arrivo</p>
        </div>
      ) : activeTab === 'formazione' ? (
        <FormazioneDashboard data={trainingData} loading={trainingLoading} />
      ) : activeTab === 'pazienti' ? (
        <PazientiDashboard data={pazientiData} loading={pazientiLoading} error={pazientiError} onRetry={() => { setPazientiLoaded(false); loadPazientiData(); }} />
      ) : activeTab === 'check' ? (
        <CheckDashboard data={checkDashData} loading={checkDashLoading} error={checkDashError} onRetry={() => { setCheckDashLoaded(false); loadCheckDashData(); }} />
      ) : activeTab === 'professionisti' ? (
        <ProfessionistiDashboard data={profData} loading={profLoading} error={profError} onRetry={() => { setProfLoaded(false); loadProfData(); }} />
      ) : activeTab === 'quality' ? (
        <QualityDashboard data={profData} loading={profLoading} error={profError} onRetry={() => { setProfLoaded(false); loadProfData(); }} />
      ) : (
        <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
          <div className="card-body text-center py-5">
            <h5 className="text-muted mb-3">Sezione in fase di implementazione</h5>
          </div>
        </div>
      )}
    </>
  );
}


export default Welcome;

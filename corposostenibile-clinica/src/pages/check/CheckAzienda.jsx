import { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate, useSearchParams, useOutletContext } from 'react-router-dom';
import checkService from '../../services/checkService';
import GuidedTour from '../../components/GuidedTour';
import SupportWidget from '../../components/SupportWidget';
import { isProfessionistaStandard, normalizeSpecialtyGroup } from '../../utils/rbacScope';
import './CheckAzienda.css';

// Professional type config
const PROF_TYPES = {
  nutrizione: { label: 'Nutrizione', icon: 'ri-restaurant-line', color: '#22c55e', activeClass: 'active-green' },
  coach:      { label: 'Coach',      icon: 'ri-run-line',        color: '#3b82f6', activeClass: 'active-blue' },
  psicologia: { label: 'Psicologia', icon: 'ri-mental-health-line', color: '#8b5cf6', activeClass: 'active-purple' },
};

// Rating helpers
const ratingClass = (v) => {
  if (v === null || v === undefined) return 'neutral';
  if (v >= 8) return 'good';
  if (v >= 7) return 'warning';
  return 'danger';
};

const getInitials = (name) => {
  if (!name) return '??';
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
};

// ── ProfessionalCell ──
const ProfessionalCell = ({ professionals, rating, progressRating }) => {
  const mps = (rating && progressRating) ? ((rating + progressRating) / 2).toFixed(1) : null;

  return (
    <div className="chk-prof-cell">
      <span className={`chk-rating ${ratingClass(rating)}`}>{rating ?? '-'}</span>

      {mps && (
        <span
          className="chk-mps"
          title={`Media: (Voto Professionista [${rating}] + Voto Progresso [${progressRating}]) / 2 = ${mps}`}
        >
          MPS: {mps}
        </span>
      )}

      {professionals && professionals.length > 0 ? (
        <div className="chk-prof-avatars">
          {professionals.map((prof, idx) => (
            <div key={prof.id || idx} className="chk-prof-avatar-row">
              <img
                src={prof.avatar_path || '/static/assets/immagini/logo_user.png'}
                alt=""
                className="chk-prof-avatar"
                onError={(e) => { e.target.src = '/static/assets/immagini/logo_user.png'; }}
              />
              <span className={`chk-read-badge ${prof.has_read ? 'read' : 'unread'}`}>
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

// ── Main Component ──
function CheckAzienda() {
  const { user } = useOutletContext();
  const navigate = useNavigate();
  const [period, setPeriod] = useState('month');
  const [loading, setLoading] = useState(true);
  const [responses, setResponses] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  // Tour
  const [mostraTour, setMostraTour] = useState(false);
  const [searchParams] = useSearchParams();
  const isProfessionista = isProfessionistaStandard(user);
  const profSpecialtyGroup = useMemo(() => normalizeSpecialtyGroup(user?.specialty), [user?.specialty]);

  useEffect(() => {
    if (searchParams.get('startTour') === 'true') {
      setMostraTour(true);
    }
  }, [searchParams]);

  const tourSteps = [
    { target: '[data-tour="header"]', title: 'Torre di Controllo', content: 'Questa pagina è la tua "torre di controllo" sulla qualità del servizio e sulla soddisfazione dei pazienti.', placement: 'bottom', icon: <i className="ri-line-chart-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #22c55e, #16a34a)' },
    { target: '[data-tour="kpi-dashboard"]', title: 'I Numeri Chiave (KPI)', content: '🟢 Verde (>= 8): Ottimo! 🟡 Giallo (7-7.9): Migliorabile. 🔴 Rosso (< 7): Attenzione.', placement: 'bottom', icon: <i className="ri-information-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #3b82f6, #2563eb)' },
    { target: '[data-tour="period-filters"]', title: 'Periodo Temporale', content: 'Scegli l\'orizzonte temporale: Settimana, Mese, Trimestre o date Custom.', placement: 'bottom', icon: <i className="ri-calendar-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #f59e0b, #d97706)' },
    { target: '[data-tour="prof-filters"]', title: 'Filtri Professionisti', content: 'Filtra per area (Nutrizione, Coach, Psicologia) o singolo professionista.', placement: 'bottom', icon: <i className="ri-group-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #8b5cf6, #7c3aed)' },
    { target: '[data-tour="status-filters"]', title: 'Filtri Rapidi (Stato)', content: 'Individua criticità con "Voto Negativo" o check non letti (⏳).', placement: 'bottom', icon: <i className="ri-filter-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #ef4444, #dc2626)' },
    { target: '[data-tour="responses-table"]', title: 'Tabella Risposte', content: 'Ogni riga è un check. ✓ = letto, ⏳ = in attesa di feedback.', placement: 'top', icon: <i className="ri-table-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #64748b, #475569)' },
    { target: '[data-tour="check-record"]', title: 'Vedi Dettagli', content: 'Cliccando su una riga si apre il dettaglio completo.', placement: 'top', icon: <i className="ri-line-chart-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #22c55e, #16a34a)', action: 'close_modal' },
    { target: '[data-tour="check-detail-modal"]', title: 'Scheda Completa', content: 'Qui puoi vedere il check nella sua interezza.', placement: 'left', icon: <i className="ri-information-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #3b82f6, #2563eb)', action: 'open_modal' },
    { target: '[data-tour="check-photos"]', title: 'Foto Progressi', content: 'Foto caricate dal paziente. Cliccaci sopra per ingrandirle.', placement: 'left', icon: <i className="ri-camera-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #8b5cf6, #7c3aed)' },
    { target: '[data-tour="check-ratings"]', title: 'Valutazioni e Feedback', content: 'Voti ai professionisti e i feedback testuali.', placement: 'top', icon: <i className="ri-star-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #f59e0b, #d97706)' },
    { target: '[data-tour="check-reflections"]', title: 'Riflessioni', content: 'Note del paziente su cosa ha funzionato e obiettivi.', placement: 'top', icon: <i className="ri-lightbulb-line" style={{ fontSize: 18, color: '#fff' }} />, iconBg: 'linear-gradient(135deg, #10b981, #059669)' },
  ];

  // Custom date range
  const [showCustomDates, setShowCustomDates] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Professional filters
  const [profType, setProfType] = useState(null);
  const [profId, setProfId] = useState(null);
  const [professionals, setProfessionals] = useState([]);
  const [loadingProfs, setLoadingProfs] = useState(false);

  // Check Response Modal
  const [showCheckResponseModal, setShowCheckResponseModal] = useState(false);
  const [selectedCheckResponse, setSelectedCheckResponse] = useState(null);
  const [loadingCheckDetail, setLoadingCheckDetail] = useState(false);

  // Pagination (server-side)
  const [currentPage, setCurrentPage] = useState(1);
  const [pagination, setPagination] = useState({ page: 1, per_page: 25, total: 0, pages: 1 });
  const ITEMS_PER_PAGE = 25;

  // Rating & Read filters
  const [ratingFilter, setRatingFilter] = useState(null);
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  const isAdminOrCco = Boolean(user?.is_admin || user?.role === 'admin' || user?.specialty === 'cco');
  const isTeamLeaderRestricted = Boolean(user?.role === 'team_leader' && !isAdminOrCco);
  const teamLeaderProfType = useMemo(() => {
    const specialty = String(user?.specialty || '').toLowerCase();
    if (specialty === 'nutrizione' || specialty === 'nutrizionista') return 'nutrizione';
    if (specialty === 'coach') return 'coach';
    if (specialty === 'psicologia' || specialty === 'psicologo') return 'psicologia';
    return null;
  }, [user?.specialty]);

  // Professionisti e team leader vedono solo la propria specialty
  const isRoleRestricted = Boolean(
    (isTeamLeaderRestricted && teamLeaderProfType) ||
    (isProfessionista && profSpecialtyGroup)
  );
  const restrictedProfType = isTeamLeaderRestricted ? teamLeaderProfType : profSpecialtyGroup;

  const visibleRatingColumns = useMemo(() => {
    if (!isRoleRestricted) return { nutrizione: true, psicologia: true, coach: true, progresso: true };
    return {
      nutrizione: restrictedProfType === 'nutrizione',
      psicologia: restrictedProfType === 'psicologia',
      coach: restrictedProfType === 'coach',
      progresso: true,
    };
  }, [isRoleRestricted, restrictedProfType]);

  const visibleKpiConfigs = useMemo(() => {
    const all = [
      { key: 'nutrizione', icon: 'ri-restaurant-line text-success', label: 'Nutrizionista', value: stats?.avg_nutrizionista },
      { key: 'psicologia', icon: 'ri-mental-health-line text-info', label: 'Psicologo', value: stats?.avg_psicologo },
      { key: 'coach', icon: 'ri-run-line text-primary', label: 'Coach', value: stats?.avg_coach },
    ];
    return all.filter((kpi) => !isRoleRestricted || visibleRatingColumns[kpi.key]);
  }, [stats, isRoleRestricted, visibleRatingColumns]);

  const showProgressKpi = !isRoleRestricted;
  const showQualityKpi = !isRoleRestricted;

  useEffect(() => {
    if (isRoleRestricted && profType !== restrictedProfType) {
      setProfType(restrictedProfType);
      setProfId(null);
      setCurrentPage(1);
    }
  }, [isRoleRestricted, restrictedProfType, profType]);

  useEffect(() => {
    if (period !== 'custom') fetchData(period, null, null, profType, profId, currentPage);
  }, [period, profType, profId, currentPage]);

  useEffect(() => {
    if (profType) { fetchProfessionals(profType); } else { setProfessionals([]); setProfId(null); }
  }, [profType]);

  const fetchData = async (periodParam, customStart = null, customEnd = null, profTypeParam = null, profIdParam = null, page = 1) => {
    setLoading(true);
    setError(null);
    try {
      const result = await checkService.getAziendaStats(periodParam, customStart, customEnd, profTypeParam, profIdParam, page, ITEMS_PER_PAGE);
      if (result.success) {
        setResponses(result.responses || []);
        setStats(result.stats || {});
        setPagination(result.pagination || { page: 1, per_page: ITEMS_PER_PAGE, total: 0, pages: 1 });
      } else {
        setError(result.error || 'Errore nel caricamento dei dati');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Errore nel caricamento dei dati');
    } finally {
      setLoading(false);
    }
  };

  const fetchProfessionals = async (type) => {
    setLoadingProfs(true);
    try {
      const result = await checkService.getProfessionistiByType(type);
      if (result.success) setProfessionals(result.professionisti || []);
    } catch (err) { console.error('Error fetching professionals:', err); }
    finally { setLoadingProfs(false); }
  };

  const handlePeriodChange = (newPeriod) => {
    if (newPeriod === 'custom') { setShowCustomDates(true); setPeriod('custom'); }
    else { setShowCustomDates(false); setCurrentPage(1); setPeriod(newPeriod); }
  };

  const handleApplyCustomDates = () => {
    if (startDate && endDate) { setCurrentPage(1); fetchData('custom', startDate, endDate, profType, profId, 1); }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.pages && newPage !== currentPage) setCurrentPage(newPage);
  };

  const handleProfTypeChange = (type) => {
    if (isRoleRestricted) return;
    setProfType(profType === type ? null : type);
    setProfId(null);
    setCurrentPage(1);
  };

  const handleProfIdChange = (id) => { setProfId(id || null); setCurrentPage(1); };

  const handleResetFilters = () => {
    setProfType(isRoleRestricted ? restrictedProfType : null);
    setProfId(null); setProfessionals([]); setRatingFilter(null); setShowUnreadOnly(false);
  };

  const getFilteredResponses = () => {
    let filtered = [...responses];
    if (ratingFilter === 'da_migliorare') {
      filtered = filtered.filter(r => {
        const ratings = [
          visibleRatingColumns.nutrizione ? r.nutritionist_rating : null,
          visibleRatingColumns.psicologia ? r.psychologist_rating : null,
          visibleRatingColumns.coach ? r.coach_rating : null,
          visibleRatingColumns.progresso ? r.progress_rating : null,
        ].filter(v => v !== null && v !== undefined);
        return ratings.some(rating => rating < 8);
      });
    } else if (ratingFilter === 'negativo') {
      filtered = filtered.filter(r => {
        const ratings = [
          visibleRatingColumns.nutrizione ? r.nutritionist_rating : null,
          visibleRatingColumns.psicologia ? r.psychologist_rating : null,
          visibleRatingColumns.coach ? r.coach_rating : null,
          visibleRatingColumns.progresso ? r.progress_rating : null,
        ].filter(v => v !== null && v !== undefined);
        return ratings.some(rating => rating < 7);
      });
    }
    if (showUnreadOnly) {
      filtered = filtered.filter(r => {
        const allProfs = [...(r.nutrizionisti || []), ...(r.psicologi || []), ...(r.coaches || [])];
        return allProfs.some(prof => !prof.has_read);
      });
    }
    return filtered;
  };

  const handleRatingFilterChange = (filter) => { setCurrentPage(1); setRatingFilter(ratingFilter === filter ? null : filter); };
  const handleUnreadFilterChange = () => { setCurrentPage(1); setShowUnreadOnly(!showUnreadOnly); };

  const handleViewCheckResponse = async (response) => {
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
    } catch (err) { console.error('Error fetching response detail:', err); }
    finally { setLoadingCheckDetail(false); }
  };

  const handleTourStepChange = (index, step) => {
    if (step.action === 'open_modal') { if (responses.length > 0) handleViewCheckResponse(responses[0]); }
    else if (step.action === 'close_modal') { setShowCheckResponseModal(false); }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    if (dateStr.includes('/')) return dateStr;
    const date = new Date(dateStr);
    return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  const periodOptions = [
    { key: 'week', label: 'Settimana' },
    { key: 'month', label: 'Mese' },
    { key: 'trimester', label: 'Trimestre' },
    { key: 'year', label: 'Anno' },
    { key: 'custom', label: 'Custom', icon: 'ri-calendar-2-line' },
  ];

  const filteredResponses = getFilteredResponses();
  const useServerPagination = !ratingFilter && !showUnreadOnly;
  const totalPages = useServerPagination ? pagination.pages : Math.ceil(filteredResponses.length / ITEMS_PER_PAGE);
  const totalItems = useServerPagination ? pagination.total : filteredResponses.length;
  const paginatedResponses = useServerPagination
    ? filteredResponses
    : filteredResponses.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  // ── Render ──
  return (
    <div className="chk-page">
      {/* Header */}
      <div className="chk-header" data-tour="header">
        <div>
          <h4>{isProfessionista ? 'I miei Check' : isTeamLeaderRestricted ? 'Check Team' : 'Check Azienda'}</h4>
          <p>
            {(ratingFilter || showUnreadOnly) ? (
              <>{filteredResponses.length} risposte filtrate <span>({pagination.total || responses.length} totali nel periodo)</span></>
            ) : (
              <>{pagination.total || responses.length} risposte nel periodo</>
            )}
          </p>
        </div>
      </div>

      {/* ── Filter Card 1: Period + KPIs ── */}
      <div className="chk-filter-card">
        <div className="chk-filter-row" style={{ justifyContent: 'space-between' }}>
          {/* Period */}
          <div className="chk-filter-group" data-tour="period-filters">
            {periodOptions.map((p) => (
              <button
                key={p.key}
                className={`chk-filter-btn ${period === p.key ? 'active' : ''}`}
                onClick={() => handlePeriodChange(p.key)}
                disabled={loading}
              >
                {p.icon && <i className={p.icon}></i>}
                {p.label}
              </button>
            ))}
          </div>

          {/* KPIs */}
          <div className="chk-kpi-row" data-tour="kpi-dashboard">
            {visibleKpiConfigs.map((kpi) => (
              <div key={kpi.key} className="chk-kpi-item">
                <i className={kpi.icon}></i>
                <span className="chk-kpi-label d-none d-xl-inline">{kpi.label}</span>
                <span className={`chk-kpi-badge ${ratingClass(kpi.value)}`}>{kpi.value ?? '-'}</span>
              </div>
            ))}
            {(showProgressKpi || showQualityKpi) && (
              <>
                <div className="chk-kpi-divider d-none d-lg-block"></div>
                {showProgressKpi && (
                  <div className="chk-kpi-item">
                    <img src="/corposostenibile.jpg" alt="Progresso" className="rounded-circle" style={{ width: '18px', height: '18px', objectFit: 'cover' }} />
                    <span className="chk-kpi-label d-none d-xl-inline">Progresso</span>
                    <span className={`chk-kpi-badge ${ratingClass(stats?.avg_progresso)}`}>{stats?.avg_progresso ?? '-'}</span>
                  </div>
                )}
                {showQualityKpi && (
                  <div className="chk-kpi-item">
                    <i className="ri-star-fill text-warning"></i>
                    <span className="chk-kpi-label d-none d-xl-inline">MPS</span>
                    <span className={`chk-kpi-badge ${ratingClass(stats?.avg_quality)}`}>{stats?.avg_quality ?? '-'}</span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Custom Date Range */}
        {showCustomDates && (
          <div className="chk-filter-row" style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid var(--chk-border-light)' }}>
            <div>
              <div className="chk-date-label">Data Inizio</div>
              <input type="date" className="chk-date-input" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div>
              <div className="chk-date-label">Data Fine</div>
              <input type="date" className="chk-date-input" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
            <button className="chk-filter-btn active" onClick={handleApplyCustomDates} disabled={!startDate || !endDate || loading}>
              <i className="ri-search-line"></i> Applica
            </button>
          </div>
        )}
      </div>

      {/* ── Filter Card 2: Prof Type + Status ── */}
      <div className="chk-filter-card">
        {/* Professional Type — solo per admin/TL, non per professionisti */}
        {!isProfessionista && (
          <div className="chk-filter-row" style={{ justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }} data-tour="prof-filters">
              <span className="chk-filter-label">Filtra per:</span>
              {isRoleRestricted ? (
                <span
                  className="chk-locked-badge"
                  style={{ background: `${PROF_TYPES[restrictedProfType]?.color || '#64748b'}15`, color: PROF_TYPES[restrictedProfType]?.color || '#64748b', border: `1px solid ${(PROF_TYPES[restrictedProfType]?.color || '#64748b')}33` }}
                >
                  <i className={PROF_TYPES[restrictedProfType]?.icon || 'ri-filter-line'}></i>
                  Solo {PROF_TYPES[restrictedProfType]?.label || 'la tua area'}
                </span>
              ) : (
                <div className="chk-filter-group">
                  {Object.entries(PROF_TYPES).map(([key, config]) => (
                    <button
                      key={key}
                      className={`chk-filter-btn ${profType === key ? config.activeClass : ''}`}
                      onClick={() => handleProfTypeChange(key)}
                      disabled={loading}
                    >
                      <i className={config.icon}></i> {config.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {profType && (
                <>
                  <select className="chk-select" value={profId || ''} onChange={(e) => handleProfIdChange(e.target.value ? parseInt(e.target.value) : null)} disabled={loading || loadingProfs}>
                    <option value="">Tutti i {PROF_TYPES[profType]?.label}</option>
                    {professionals.map((prof) => <option key={prof.id} value={prof.id}>{prof.nome}</option>)}
                  </select>
                  <button className="chk-reset-link" onClick={handleResetFilters} title="Reset filtri">
                    <i className="ri-close-circle-line" style={{ fontSize: '18px' }}></i>
                  </button>
                </>
              )}
              {!profType && !isRoleRestricted && (
                <span style={{ fontSize: '13px', color: 'var(--chk-text-light)', fontStyle: 'italic' }}>
                  Seleziona un tipo di professionista per filtrare
                </span>
              )}
            </div>
          </div>
        )}

        {/* Status Filters */}
        <div className="chk-filter-row" data-tour="status-filters">
          <span className="chk-filter-label">Stato:</span>
          <div className="chk-filter-group">
            <button className={`chk-filter-btn ${ratingFilter === 'da_migliorare' ? 'active-amber' : ''}`} onClick={() => handleRatingFilterChange('da_migliorare')} disabled={loading}>
              <i className="ri-arrow-down-line"></i> Da Migliorare (&lt;8)
            </button>
            <button className={`chk-filter-btn ${ratingFilter === 'negativo' ? 'active-red' : ''}`} onClick={() => handleRatingFilterChange('negativo')} disabled={loading}>
              <i className="ri-error-warning-line"></i> Voto Negativo (&lt;7)
            </button>
            <button className={`chk-filter-btn ${showUnreadOnly ? 'active-purple' : ''}`} onClick={handleUnreadFilterChange} disabled={loading}>
              <i className="ri-eye-off-line"></i> Non Letto
            </button>
          </div>
          {(ratingFilter || showUnreadOnly || profType) && (
            <button className="chk-reset-link" onClick={handleResetFilters} title="Reset tutti i filtri">
              <i className="ri-refresh-line"></i> Reset filtri
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="chk-error">
          <i className="ri-error-warning-line"></i> {error}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="chk-loading">
          <div className="spinner-border"></div>
          <p>Caricamento risposte...</p>
        </div>
      ) : paginatedResponses.length === 0 ? (
        <div className="chk-empty">
          <i className="ri-file-list-3-line"></i>
          <h5>Nessuna risposta trovata</h5>
          <p>
            {responses.length > 0
              ? 'Nessuna risposta corrisponde ai filtri selezionati.'
              : 'Non ci sono risposte disponibili per il periodo selezionato.'}
          </p>
          {(ratingFilter || showUnreadOnly) && (
            <button className="chk-empty-btn" onClick={() => { setRatingFilter(null); setShowUnreadOnly(false); }}>
              <i className="ri-refresh-line"></i> Rimuovi filtri stato
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="chk-table-card" data-tour="responses-table">
            <div className="table-responsive">
              <table className="chk-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '200px' }}>Cliente</th>
                    <th style={{ minWidth: '110px' }}>Data</th>
                    {visibleRatingColumns.nutrizione && <th className="text-center" style={{ minWidth: '120px' }}>Nutrizionista</th>}
                    {visibleRatingColumns.psicologia && <th className="text-center" style={{ minWidth: '120px' }}>Psicologo/a</th>}
                    {visibleRatingColumns.coach && <th className="text-center" style={{ minWidth: '120px' }}>Coach</th>}
                    {visibleRatingColumns.progresso && <th className="text-center" style={{ minWidth: '100px' }}>Progresso</th>}
                  </tr>
                </thead>
                <tbody>
                  {paginatedResponses.map((response, index) => (
                    <tr
                      key={`${response.type}-${response.id}`}
                      data-tour={index === 0 ? 'check-record' : undefined}
                      onClick={() => handleViewCheckResponse(response)}
                    >
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <Link
                            to={`/clienti-dettaglio/${response.cliente_id}`}
                            className="chk-client-link"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {response.cliente_nome || 'Cliente'}
                          </Link>
                          {response.type === 'dca' && <span className="chk-type-badge dca"><i className="ri-heart-pulse-line"></i> DCA</span>}
                          {response.type === 'minor' && <span className="chk-type-badge minor"><i className="ri-user-heart-line"></i> Minori</span>}
                        </div>
                      </td>
                      <td><span style={{ fontWeight: 500 }}>{formatDate(response.submit_date)}</span></td>
                      {visibleRatingColumns.nutrizione && (
                        <td className="text-center">
                          <ProfessionalCell professionals={response.nutrizionisti} rating={response.nutritionist_rating} progressRating={response.progress_rating} />
                        </td>
                      )}
                      {visibleRatingColumns.psicologia && (
                        <td className="text-center">
                          <ProfessionalCell professionals={response.psicologi} rating={response.psychologist_rating} progressRating={response.progress_rating} />
                        </td>
                      )}
                      {visibleRatingColumns.coach && (
                        <td className="text-center">
                          <ProfessionalCell professionals={response.coaches} rating={response.coach_rating} progressRating={response.progress_rating} />
                        </td>
                      )}
                      {visibleRatingColumns.progresso && (
                        <td className="text-center">
                          <div className="chk-prof-cell">
                            <span className={`chk-rating ${ratingClass(response.progress_rating)}`}>{response.progress_rating ?? '-'}</span>
                            <img src="/static/assets/immagini/logo_user.png" alt="" className="chk-prof-avatar" />
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="chk-pagination">
              <div className="chk-pagination-info">
                Mostrando {((currentPage - 1) * ITEMS_PER_PAGE) + 1} - {Math.min(currentPage * ITEMS_PER_PAGE, totalItems)} di {totalItems} risposte
              </div>
              <div className="chk-pagination-btns">
                <button className="chk-page-btn" onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1 || loading}>
                  <i className="ri-arrow-left-s-line"></i>
                </button>
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) pageNum = i + 1;
                  else if (currentPage <= 3) pageNum = i + 1;
                  else if (currentPage >= totalPages - 2) pageNum = totalPages - 4 + i;
                  else pageNum = currentPage - 2 + i;
                  return (
                    <button
                      key={pageNum}
                      className={`chk-page-btn ${currentPage === pageNum ? 'active' : ''}`}
                      onClick={() => handlePageChange(pageNum)}
                      disabled={loading}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                <button className="chk-page-btn" onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages || loading}>
                  <i className="ri-arrow-right-s-line"></i>
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Detail Modal ── */}
      {showCheckResponseModal && selectedCheckResponse && (
        <div className="chk-modal-backdrop" onClick={() => setShowCheckResponseModal(false)}>
          <div className="chk-modal" onClick={(e) => e.stopPropagation()} data-tour="check-detail-modal">
            <div className={`chk-modal-header ${selectedCheckResponse.type || 'weekly'}`}>
              <h5>
                <i className={selectedCheckResponse.type === 'weekly' ? 'ri-calendar-check-line' : selectedCheckResponse.type === 'dca' ? 'ri-heart-pulse-line' : 'ri-user-heart-line'}></i>
                {selectedCheckResponse.type === 'weekly' ? 'Check Settimanale' : selectedCheckResponse.type === 'dca' ? 'Check Benessere' : 'Check Minori'}
                {selectedCheckResponse.cliente_nome && <span style={{ opacity: 0.75, marginLeft: '8px' }}>- {selectedCheckResponse.cliente_nome}</span>}
              </h5>
              <button className="chk-modal-close" onClick={() => setShowCheckResponseModal(false)}>
                <i className="ri-close-line"></i>
              </button>
            </div>

            <div className="chk-modal-body">
              {loadingCheckDetail ? (
                <div className="chk-loading">
                  <div className="spinner-border"></div>
                  <p>Caricamento dettagli...</p>
                </div>
              ) : (
                <>
                  {/* Info bar */}
                  <div className="chk-modal-info-bar">
                    <div>
                      <label>Data compilazione</label>
                      <span>{selectedCheckResponse.submit_date}</span>
                    </div>
                    {selectedCheckResponse.type === 'weekly' && (
                      <div style={{ textAlign: 'right' }}>
                        <label>Peso</label>
                        <span>{selectedCheckResponse.weight ? `${selectedCheckResponse.weight} kg` : '-'}</span>
                      </div>
                    )}
                  </div>

                  {/* Photos */}
                  {selectedCheckResponse.type === 'weekly' && (
                    <div className="chk-modal-section" data-tour="check-photos">
                      <div className="chk-modal-section-title"><i className="ri-camera-line"></i> Foto Progressi</div>
                      <div className="chk-photo-grid">
                        {[
                          { key: 'photo_front', label: 'Frontale' },
                          { key: 'photo_side', label: 'Laterale' },
                          { key: 'photo_back', label: 'Posteriore' },
                        ].map((photo) => (
                          <div key={photo.key} className="chk-photo-slot">
                            <label>{photo.label}</label>
                            {selectedCheckResponse[photo.key] ? (
                              <img src={selectedCheckResponse[photo.key]} alt={photo.label} onClick={() => window.open(selectedCheckResponse[photo.key], '_blank')} />
                            ) : (
                              <div className="chk-photo-empty">Non caricata</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Ratings */}
                  {((visibleRatingColumns.nutrizione && selectedCheckResponse.nutritionist_rating) ||
                    (visibleRatingColumns.psicologia && selectedCheckResponse.psychologist_rating) ||
                    (visibleRatingColumns.coach && selectedCheckResponse.coach_rating) ||
                    (visibleRatingColumns.progresso && selectedCheckResponse.progress_rating)) && (
                    <div className="chk-modal-section" data-tour="check-ratings">
                      <div className="chk-modal-section-title"><i className="ri-star-line"></i> Valutazioni Professionisti</div>
                      <div className="chk-modal-ratings">
                        {visibleRatingColumns.nutrizione && selectedCheckResponse.nutritionist_rating && (() => {
                          const nutri = selectedCheckResponse.nutrizionisti?.[0];
                          return (
                            <div className="chk-modal-rating-card" style={{ background: 'rgba(34,197,94,0.08)' }}>
                              {nutri?.avatar_path
                                ? <img src={nutri.avatar_path} alt="" className="avatar" style={{ border: '2px solid #22c55e' }} />
                                : <div className="initials" style={{ background: '#22c55e' }}>{getInitials(nutri?.nome)}</div>}
                              <div className="value" style={{ color: '#166534' }}>{selectedCheckResponse.nutritionist_rating}</div>
                              <div className="label">{nutri?.nome || 'Nutrizionista'}</div>
                            </div>
                          );
                        })()}
                        {visibleRatingColumns.psicologia && selectedCheckResponse.psychologist_rating && (() => {
                          const psico = selectedCheckResponse.psicologi?.[0];
                          return (
                            <div className="chk-modal-rating-card" style={{ background: 'rgba(245,158,11,0.08)' }}>
                              {psico?.avatar_path
                                ? <img src={psico.avatar_path} alt="" className="avatar" style={{ border: '2px solid #d97706' }} />
                                : <div className="initials" style={{ background: '#d97706' }}>{getInitials(psico?.nome)}</div>}
                              <div className="value" style={{ color: '#92400e' }}>{selectedCheckResponse.psychologist_rating}</div>
                              <div className="label">{psico?.nome || 'Psicologo'}</div>
                            </div>
                          );
                        })()}
                        {visibleRatingColumns.coach && selectedCheckResponse.coach_rating && (() => {
                          const coach = selectedCheckResponse.coaches?.[0];
                          return (
                            <div className="chk-modal-rating-card" style={{ background: 'rgba(59,130,246,0.08)' }}>
                              {coach?.avatar_path
                                ? <img src={coach.avatar_path} alt="" className="avatar" style={{ border: '2px solid #3b82f6' }} />
                                : <div className="initials" style={{ background: '#3b82f6' }}>{getInitials(coach?.nome)}</div>}
                              <div className="value" style={{ color: '#1d4ed8' }}>{selectedCheckResponse.coach_rating}</div>
                              <div className="label">{coach?.nome || 'Coach'}</div>
                            </div>
                          );
                        })()}
                        {visibleRatingColumns.progresso && selectedCheckResponse.progress_rating && (
                          <div className="chk-modal-rating-card" style={{ background: 'rgba(139,92,246,0.08)' }}>
                            <img src="/static/assets/immagini/logo_user.png" alt="" className="avatar" style={{ border: '2px solid #9333ea' }} />
                            <div className="value" style={{ color: '#7c3aed' }}>{selectedCheckResponse.progress_rating}</div>
                            <div className="label">Progresso</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Wellness */}
                  {selectedCheckResponse.type === 'weekly' && (
                    <div className="chk-modal-section">
                      <div className="chk-modal-section-title"><i className="ri-heart-pulse-line"></i> Benessere</div>
                      <div className="chk-wellness-grid">
                        {[
                          { key: 'digestion_rating', label: 'Digestione', icon: '🍽️' },
                          { key: 'energy_rating', label: 'Energia', icon: '⚡' },
                          { key: 'strength_rating', label: 'Forza', icon: '💪' },
                          { key: 'hunger_rating', label: 'Fame', icon: '🍴' },
                          { key: 'sleep_rating', label: 'Sonno', icon: '😴' },
                          { key: 'mood_rating', label: 'Umore', icon: '😊' },
                          { key: 'motivation_rating', label: 'Motivazione', icon: '🔥' },
                        ].map(item => (
                          <div key={item.key} className="chk-wellness-item">
                            <span className="icon">{item.icon}</span>
                            <span className="label">{item.label}</span>
                            <span className="value">
                              {selectedCheckResponse[item.key] !== null && selectedCheckResponse[item.key] !== undefined
                                ? `${selectedCheckResponse[item.key]}/10` : '-'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Professional Feedback */}
                  {selectedCheckResponse.type === 'weekly' && !isRoleRestricted && (
                    <div className="chk-modal-section">
                      <div className="chk-modal-section-title"><i className="ri-feedback-line"></i> Feedback Professionisti</div>
                      <div className="chk-feedback-block green">
                        <label>Feedback Nutrizionista</label>
                        <p>{selectedCheckResponse.nutritionist_feedback || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p>
                      </div>
                      <div className="chk-feedback-block amber">
                        <label>Feedback Psicologo</label>
                        <p>{selectedCheckResponse.psychologist_feedback || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p>
                      </div>
                      <div className="chk-feedback-block blue">
                        <label>Feedback Coach</label>
                        <p>{selectedCheckResponse.coach_feedback || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p>
                      </div>
                    </div>
                  )}

                  {/* Team Leader restricted feedback */}
                  {selectedCheckResponse.type === 'weekly' && isRoleRestricted && (
                    <div className="chk-modal-section">
                      <div className="chk-modal-section-title"><i className="ri-feedback-line"></i> Feedback Professionista</div>
                      {restrictedProfType === 'nutrizione' && (
                        <div className="chk-feedback-block green"><label>Feedback Nutrizionista</label><p>{selectedCheckResponse.nutritionist_feedback || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                      )}
                      {restrictedProfType === 'psicologia' && (
                        <div className="chk-feedback-block amber"><label>Feedback Psicologo</label><p>{selectedCheckResponse.psychologist_feedback || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                      )}
                      {restrictedProfType === 'coach' && (
                        <div className="chk-feedback-block blue"><label>Feedback Coach</label><p>{selectedCheckResponse.coach_feedback || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                      )}
                    </div>
                  )}

                  {/* Programs */}
                  {selectedCheckResponse.type === 'weekly' && (
                    <div className="chk-modal-section">
                      <div className="chk-modal-section-title"><i className="ri-calendar-check-line"></i> Programmi</div>
                      <div className="chk-feedback-block neutral"><label>Aderenza programma alimentare</label><p>{selectedCheckResponse.nutrition_program_adherence || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                      <div className="chk-feedback-block neutral"><label>Aderenza programma sportivo</label><p>{selectedCheckResponse.training_program_adherence || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                      <div className="chk-feedback-block neutral"><label>Esercizi modificati/aggiunti</label><p>{selectedCheckResponse.exercise_modifications || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                      <div className="chk-stats-row" style={{ marginTop: '10px' }}>
                        <div className="chk-stat-box"><label>Passi giornalieri</label><span>{selectedCheckResponse.daily_steps || '-'}</span></div>
                        <div className="chk-stat-box"><label>Settimane completate</label><span>{selectedCheckResponse.completed_training_weeks || '-'}</span></div>
                        <div className="chk-stat-box"><label>Giorni allenamento</label><span>{selectedCheckResponse.planned_training_days || '-'}</span></div>
                      </div>
                      <div className="chk-feedback-block neutral" style={{ marginTop: '10px' }}><label>Tematiche live settimanali</label><p>{selectedCheckResponse.live_session_topics || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                    </div>
                  )}

                  {/* Reflections */}
                  <div className="chk-modal-section" data-tour="check-reflections">
                    <div className="chk-modal-section-title"><i className="ri-lightbulb-line"></i> Riflessioni</div>
                    <div className="chk-reflection success"><label><i className="ri-check-line text-success"></i> Cosa ha funzionato</label><p>{selectedCheckResponse.what_worked || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                    <div className="chk-reflection danger"><label><i className="ri-close-line text-danger"></i> Cosa non ha funzionato</label><p>{selectedCheckResponse.what_didnt_work || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                    <div className="chk-reflection warning"><label><i className="ri-lightbulb-line text-warning"></i> Cosa ho imparato</label><p>{selectedCheckResponse.what_learned || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                    <div className="chk-reflection info"><label><i className="ri-focus-line text-primary"></i> Focus prossima settimana</label><p>{selectedCheckResponse.what_focus_next || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Non compilato</span>}</p></div>
                    {selectedCheckResponse.type === 'weekly' && (
                      <div className="chk-feedback-block red" style={{ marginTop: '10px' }}><label><i className="ri-first-aid-kit-line text-danger"></i> Infortuni / Note importanti</label><p>{selectedCheckResponse.injuries_notes || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Nessun infortunio segnalato</span>}</p></div>
                    )}
                  </div>

                  {/* Referral */}
                  {selectedCheckResponse.type === 'weekly' && (
                    <div className="chk-modal-section">
                      <div className="chk-modal-section-title"><i className="ri-user-add-line"></i> Referral</div>
                      <div className="chk-feedback-block neutral"><p>{selectedCheckResponse.referral || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Nessun referral indicato</span>}</p></div>
                    </div>
                  )}

                  {/* Extra Comments */}
                  <div className="chk-modal-section">
                    <div className="chk-modal-section-title"><i className="ri-chat-1-line"></i> Commenti extra</div>
                    <div className="chk-feedback-block neutral"><p>{selectedCheckResponse.extra_comments || <span style={{ color: 'var(--chk-text-light)', fontStyle: 'italic' }}>Nessun commento aggiuntivo</span>}</p></div>
                  </div>
                </>
              )}
            </div>

            <div className="chk-modal-footer">
              <Link
                to={`/clienti-dettaglio/${selectedCheckResponse.cliente_id}?tab=check`}
                className="chk-btn-outline"
                onClick={() => setShowCheckResponseModal(false)}
              >
                <i className="ri-user-line"></i> Vai al Cliente
              </Link>
              <button className="chk-btn-secondary" onClick={() => setShowCheckResponseModal(false)}>Chiudi</button>
            </div>
          </div>
        </div>
      )}

      <SupportWidget
        pageTitle="Check Azienda"
        pageDescription="Monitora la qualità del servizio, analizza i KPI dei professionisti e gestisci le criticità in tempo reale."
        pageIcon={({ size, color }) => <i className="ri-line-chart-line" style={{ fontSize: size, color }} />}
        docsSection="check-azienda"
        onStartTour={() => setMostraTour(true)}
        brandName="Suite Clinica"
        logoSrc="/suitemind.png"
        accentColor="#22c55e"
      />

      <GuidedTour
        steps={tourSteps}
        isOpen={mostraTour}
        onClose={() => { setMostraTour(false); setShowCheckResponseModal(false); }}
        onStepChange={handleTourStepChange}
        onComplete={() => { setMostraTour(false); setShowCheckResponseModal(false); }}
      />
    </div>
  );
}

export default CheckAzienda;

import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import checkService from '../../services/checkService';
import GuidedTour from '../../components/GuidedTour';
import SupportWidget from '../../components/SupportWidget';
import CheckResponseDetailModal from '../../components/CheckResponseDetailModal';
import './check-azienda-responsive.css';
import '../clienti/clienti-table.css';
import '../clienti/clienti-responsive.css';
import {
  FaChartLine,
  FaCalendarAlt,
  FaUsers,
  FaFilter,
  FaTable,
  FaInfoCircle,
  FaLightbulb
} from 'react-icons/fa';

// Stili per la tabella (stesso stile di ClientiList)
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
    padding: '16px 20px',
    fontSize: '11px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: '#64748b',
    whiteSpace: 'nowrap',
    borderBottom: 'none',
  },
  td: {
    padding: '16px 20px',
    fontSize: '14px',
    color: '#334155',
    borderBottom: '1px solid #f1f5f9',
    verticalAlign: 'middle',
  },
  row: {
    transition: 'all 0.15s ease',
    cursor: 'pointer',
  },
};

// Stili per i rating badge
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

// KPI Badge style
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

// Professional type config
const PROF_TYPES = {
  nutrizione: {
    label: 'Nutrizione',
    icon: 'ri-restaurant-line',
    color: '#22c55e',
    bgColor: '#dcfce7'
  },
  coach: {
    label: 'Coach',
    icon: 'ri-run-line',
    color: '#3b82f6',
    bgColor: '#dbeafe'
  },
  psicologia: {
    label: 'Psicologia',
    icon: 'ri-mental-health-line',
    color: '#8b5cf6',
    bgColor: '#ede9fe'
  }
};

// Avatar styles
const avatarStyles = {
  container: {
    position: 'relative',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  img: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    objectFit: 'cover',
    border: '2px solid #fff',
    boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
  },
  initials: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '10px',
    fontWeight: 600,
    textTransform: 'uppercase',
    border: '2px solid #fff',
    boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
  },
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

// Helper to get initials from name
const getInitials = (name) => {
  if (!name) return '??';
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
};

// Component to render professional with read status
const ProfessionalCell = ({ professionals, rating, progressRating, bgColor, textColor }) => {
  // Calculate MPS if both ratings exist
  const mps = (rating && progressRating) ? ((rating + progressRating) / 2).toFixed(1) : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
      {/* Rating Badge */}
      <span style={getRatingStyle(rating)}>
        {rating ?? '-'}
      </span>

      {/* MPS Badge (New) */}
      {mps && (
        <span
          title={`Media: (Voto Professionista [${rating}] + Voto Progresso [${progressRating}]) / 2 = ${mps}`}
          style={{
            fontSize: '10px',
            fontWeight: 700,
            color: '#64748b',
            background: '#f1f5f9',
            padding: '2px 6px',
            borderRadius: '6px',
            cursor: 'help'
          }}
        >
          MPS: {mps}
        </span>
      )}

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
                ...avatarStyles.confirmBadge,
                ...(prof.has_read ? avatarStyles.confirmYes : avatarStyles.confirmNo),
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

function CheckAzienda() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState('month');
  const [hoveredRow, setHoveredRow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [responses, setResponses] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  // Tour
  const [mostraTour, setMostraTour] = useState(false);
  const [searchParams] = useSearchParams();

  // Effetto per avvio automatico tour da Hub Supporto
  useEffect(() => {
    if (searchParams.get('startTour') === 'true') {
      setMostraTour(true);
    }
  }, [searchParams]);

  const tourSteps = [
    {
      target: '[data-tour="header"]',
      title: 'Torre di Controllo',
      content: 'Questa pagina è la tua "torre di controllo" sulla qualità del servizio e sulla soddisfazione dei pazienti. Qui puoi monitorare i progressi e intervenire dove necessario.',
      placement: 'bottom',
      icon: <FaChartLine size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #22c55e, #16a34a)'
    },
    {
      target: '[data-tour="kpi-dashboard"]',
      title: 'I Numeri Chiave (KPI)',
      content: 'In alto trovi i "termometri" della qualità aziendale. 🟢 Verde (>= 8): Ottimo! 🟡 Giallo (7-7.9): Margine di miglioramento. 🔴 Rosso (< 7): Attenzione, indaga subito.',
      placement: 'bottom',
      icon: <FaInfoCircle size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #3b82f6, #2563eb)'
    },
    {
      target: '[data-tour="period-filters"]',
      title: 'Periodo Temporale',
      content: 'Scegli l\'orizzonte temporale dei dati: Settimana per il monitoraggio immediato, Mese o Trimestre per analisi di lungo periodo o date Custom.',
      placement: 'bottom',
      icon: <FaCalendarAlt size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #f59e0b, #d97706)'
    },
    {
      target: '[data-tour="prof-filters"]',
      title: 'Filtri Professionisti',
      content: 'Vuoi vedere solo l\'area Nutrizione o un singolo Coach? Usa questi filtri per "tagliare" i dati come preferisci e analizzare le performance del team.',
      placement: 'bottom',
      icon: <FaUsers size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #8b5cf6, #7c3aed)'
    },
    {
      target: '[data-tour="status-filters"]',
      title: 'Filtri Rapidi (Stato)',
      content: 'Individua subito le criticità con "Voto Negativo" o assicuratevi che tutti i check vengano gestiti filtrando per "Non Letto" (icona ⏳ sulle risposte).',
      placement: 'bottom',
      icon: <FaFilter size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #ef4444, #dc2626)'
    },
    {
      target: '[data-tour="responses-table"]',
      title: 'Tabella Risposte',
      content: 'Ogni riga è un check. La spunta verde (✓) indica che il professionista ha letto, la clessidra (⏳) indica che il check è ancora in attesa di feedback.',
      placement: 'top',
      icon: <FaTable size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #64748b, #475569)'
    },
    {
      target: '[data-tour="check-record"]',
      title: 'Vedi Dettagli',
      content: 'Cliccando su una riga si apre il dettaglio completo. Ora te lo mostro!',
      placement: 'top',
      icon: <FaChartLine size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #22c55e, #16a34a)',
      action: 'close_modal'
    },
    {
      target: '[data-tour="check-detail-modal"]',
      title: 'Scheda Completa',
      content: 'Qui puoi vedere il check nella sua interezza: data, peso e tutti i dettagli inviati dal paziente.',
      placement: 'left',
      icon: <FaInfoCircle size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #3b82f6, #2563eb)',
      action: 'open_modal'
    },
    {
      target: '[data-tour="check-photos"]',
      title: 'Foto Progressi',
      content: 'Se presenti, qui vedi le foto caricate (frontale, laterale, posteriore). Cliccandoci sopra puoi ingrandirle.',
      placement: 'left',
      icon: <FaTable size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #8b5cf6, #7c3aed)'
    },
    {
      target: '[data-tour="check-ratings"]',
      title: 'Valutazioni e Feedback',
      content: 'Qui vedi i voti dati ai professionisti e i feedback testuali che hanno lasciato in risposta.',
      placement: 'top',
      icon: <FaChartLine size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #f59e0b, #d97706)'
    },
    {
      target: '[data-tour="check-reflections"]',
      title: 'Riflessioni',
      content: 'Le note del paziente su cosa ha funzionato, cosa no e gli obiettivi per la prossima settimana.',
      placement: 'top',
      icon: <FaLightbulb size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #10b981, #059669)'
    }
  ];

  const handleTourStepChange = (index, step) => {
    if (step.action === 'open_modal') {
      // Simulate opening the first available response
      if (responses.length > 0) {
        handleViewCheckResponse(responses[0]);
      }
    } else if (step.action === 'close_modal') {
      setShowCheckResponseModal(false);
    }
  };

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

  // Rating & Read filters (client-side for now)
  const [ratingFilter, setRatingFilter] = useState(null); // 'da_migliorare', 'negativo', null
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  // Fetch data when filters or page change (except for custom period)
  useEffect(() => {
    if (period !== 'custom') {
      fetchData(period, null, null, profType, profId, currentPage);
    }
  }, [period, profType, profId, currentPage]);

  // Fetch professionals when profType changes
  useEffect(() => {
    if (profType) {
      fetchProfessionals(profType);
    } else {
      setProfessionals([]);
      setProfId(null);
    }
  }, [profType]);

  const fetchData = async (periodParam, customStart = null, customEnd = null, profTypeParam = null, profIdParam = null, page = 1) => {
    setLoading(true);
    setError(null);
    try {
      const result = await checkService.getAziendaStats(periodParam, customStart, customEnd, profTypeParam, profIdParam, page, ITEMS_PER_PAGE);
      console.log('[CheckAzienda] API Result:', result);
      if (result.success) {
        setResponses(result.responses || []);
        setStats(result.stats || {});
        setPagination(result.pagination || { page: 1, per_page: ITEMS_PER_PAGE, total: 0, pages: 1 });
      } else {
        console.error('[CheckAzienda] API returned success:false', result);
        setError(result.error || 'Errore nel caricamento dei dati');
      }
    } catch (err) {
      console.error('[CheckAzienda] Exception:', err.response?.data || err.message || err);
      setError(err.response?.data?.error || 'Errore nel caricamento dei dati');
    } finally {
      setLoading(false);
    }
  };

  const fetchProfessionals = async (type) => {
    setLoadingProfs(true);
    try {
      const result = await checkService.getProfessionistiByType(type);
      if (result.success) {
        setProfessionals(result.professionisti || []);
      }
    } catch (err) {
      console.error('Error fetching professionals:', err);
    } finally {
      setLoadingProfs(false);
    }
  };

  const handlePeriodChange = (newPeriod) => {
    if (newPeriod === 'custom') {
      setShowCustomDates(true);
      setPeriod('custom');
    } else {
      setShowCustomDates(false);
      setCurrentPage(1); // Reset page only when period changes
      setPeriod(newPeriod);
    }
  };

  const handleApplyCustomDates = () => {
    if (startDate && endDate) {
      setCurrentPage(1);
      fetchData('custom', startDate, endDate, profType, profId, 1);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.pages && newPage !== currentPage) {
      setCurrentPage(newPage);
      // fetchData will be triggered by useEffect
    }
  };

  const handleProfTypeChange = (type) => {
    if (profType === type) {
      // Deselect
      setProfType(null);
      setProfId(null);
    } else {
      setProfType(type);
      setProfId(null);
    }
    setCurrentPage(1); // Reset page when filter changes
  };

  const handleProfIdChange = (id) => {
    setProfId(id || null);
    setCurrentPage(1); // Reset page when filter changes
  };

  const handleResetFilters = () => {
    setProfType(null);
    setProfId(null);
    setProfessionals([]);
    setRatingFilter(null);
    setShowUnreadOnly(false);
  };

  // Filter responses based on rating and read status
  const getFilteredResponses = () => {
    let filtered = [...responses];

    // Filter by rating
    if (ratingFilter === 'da_migliorare') {
      // Any rating below 8
      filtered = filtered.filter(r => {
        const ratings = [r.nutritionist_rating, r.psychologist_rating, r.coach_rating, r.progress_rating].filter(v => v !== null && v !== undefined);
        return ratings.some(rating => rating < 8);
      });
    } else if (ratingFilter === 'negativo') {
      // Any rating below 7
      filtered = filtered.filter(r => {
        const ratings = [r.nutritionist_rating, r.psychologist_rating, r.coach_rating, r.progress_rating].filter(v => v !== null && v !== undefined);
        return ratings.some(rating => rating < 7);
      });
    }

    // Filter by unread status
    if (showUnreadOnly) {
      filtered = filtered.filter(r => {
        // Check if any professional hasn't read yet
        const allProfs = [...(r.nutrizionisti || []), ...(r.psicologi || []), ...(r.coaches || [])];
        return allProfs.some(prof => !prof.has_read);
      });
    }

    return filtered;
  };

  const handleRatingFilterChange = (filter) => {
    setCurrentPage(1);
    setRatingFilter(ratingFilter === filter ? null : filter);
  };

  const handleUnreadFilterChange = () => {
    setCurrentPage(1);
    setShowUnreadOnly(!showUnreadOnly);
  };

  const handleViewCheckResponse = async (response) => {
    // Set basic data and open modal
    setSelectedCheckResponse({
      ...response,
      type: response.type || 'weekly',
    });
    setShowCheckResponseModal(true);
    setLoadingCheckDetail(true);
    try {
      const result = await checkService.getResponseDetail(response.type || 'weekly', response.id);
      if (result.success) {
        setSelectedCheckResponse({
          ...result.response,
          type: response.type || 'weekly',
          // Keep professionals from original response for display
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

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    if (dateStr.includes('/')) return dateStr;
    const date = new Date(dateStr);
    return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  const handleRowClick = (response) => {
    // Open modal instead of navigating
    handleViewCheckResponse(response);
  };

  return (
    <div className="container-fluid p-0">
      {/* Header - stesso stile di ClientiList */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4" data-tour="header">
        <div>
          <h4 className="fw-bold mb-1" style={{ color: '#1e293b' }}>Check Azienda</h4>
          <p className="text-muted mb-0" style={{ fontSize: '14px' }}>
            {(ratingFilter || showUnreadOnly) ? (
              <>
                {getFilteredResponses().length} risposte filtrate
                <span className="ms-1">({pagination.total || responses.length} totali nel periodo)</span>
              </>
            ) : (
              <>{pagination.total || responses.length} risposte nel periodo</>
            )}
          </p>
        </div>
      </div>

      {/* Filters Card 1 - Period & KPIs */}
      <div
        className="card border-0 mb-3"
        style={{
          borderRadius: '16px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
        }}
      >
        <div className="card-body py-3 px-4">
          <div className="row g-3 align-items-center ca-filters-row">
            {/* Period Filters */}
            <div className="col-lg-6 ca-scroll-filters" data-tour="period-filters">
              <div className="d-flex gap-2 flex-nowrap">
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
                    onClick={() => handlePeriodChange(p.key)}
                    disabled={loading}
                    style={{
                      height: '46px',
                      borderRadius: '12px',
                      border: period === p.key ? 'none' : '1px solid #e2e8f0',
                      background: period === p.key
                        ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
                        : '#f8fafc',
                      color: period === p.key ? 'white' : '#64748b',
                      fontSize: '14px',
                      fontWeight: period === p.key ? 600 : 400,
                      padding: '0 14px',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {p.icon && <i className={`${p.icon} me-1`}></i>}
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* KPI Averages */}
            <div className="col-lg-6" data-tour="kpi-dashboard">
              <div className="d-flex flex-wrap gap-3 justify-content-lg-end align-items-center ca-kpi-container">
                {/* Nutrizionista */}
                <div className="d-flex align-items-center gap-2">
                  <i className="ri-restaurant-line text-success" style={{ fontSize: '18px' }}></i>
                  <span className="text-muted small d-none d-xl-inline">Nutrizionista</span>
                  <span style={getKpiBadgeStyle(stats?.avg_nutrizionista)}>
                    {stats?.avg_nutrizionista ?? '-'}
                  </span>
                </div>

                {/* Psicologo */}
                <div className="d-flex align-items-center gap-2">
                  <i className="ri-mental-health-line text-info" style={{ fontSize: '18px' }}></i>
                  <span className="text-muted small d-none d-xl-inline">Psicologo</span>
                  <span style={getKpiBadgeStyle(stats?.avg_psicologo)}>
                    {stats?.avg_psicologo ?? '-'}
                  </span>
                </div>

                {/* Coach */}
                <div className="d-flex align-items-center gap-2">
                  <i className="ri-run-line text-primary" style={{ fontSize: '18px' }}></i>
                  <span className="text-muted small d-none d-xl-inline">Coach</span>
                  <span style={getKpiBadgeStyle(stats?.avg_coach)}>
                    {stats?.avg_coach ?? '-'}
                  </span>
                </div>

                <div className="border-start ps-3 d-flex align-items-center gap-3">
                  {/* Progresso */}
                  <div className="d-flex align-items-center gap-2">
                    <img
                      src="/corposostenibile.jpg"
                      alt="Progresso"
                      className="rounded-circle"
                      style={{ width: '18px', height: '18px', objectFit: 'cover' }}
                    />
                    <span className="text-muted small d-none d-xl-inline">Progresso</span>
                    <span style={getKpiBadgeStyle(stats?.avg_progresso)}>
                      {stats?.avg_progresso ?? '-'}
                    </span>
                  </div>

                  {/* MPS */}
                  <div className="d-flex align-items-center gap-2">
                    <i className="ri-star-fill text-warning" style={{ fontSize: '18px' }}></i>
                    <span className="text-muted small d-none d-xl-inline">MPS</span>
                    <span style={getKpiBadgeStyle(stats?.avg_quality)}>
                      {stats?.avg_quality ?? '-'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Custom Date Range Picker */}
          {showCustomDates && (
            <div className="row mt-3 pt-3 border-top">
              <div className="col-12">
                <div className="d-flex flex-wrap gap-3 align-items-end">
                  <div>
                    <label className="form-label small text-muted mb-1">Data Inizio</label>
                    <input
                      type="date"
                      className="form-control"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      style={{
                        height: '46px',
                        borderRadius: '12px',
                        border: '1px solid #e2e8f0',
                        background: '#f8fafc',
                        fontSize: '14px',
                        minWidth: '160px',
                      }}
                    />
                  </div>
                  <div>
                    <label className="form-label small text-muted mb-1">Data Fine</label>
                    <input
                      type="date"
                      className="form-control"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      style={{
                        height: '46px',
                        borderRadius: '12px',
                        border: '1px solid #e2e8f0',
                        background: '#f8fafc',
                        fontSize: '14px',
                        minWidth: '160px',
                      }}
                    />
                  </div>
                  <button
                    className="btn"
                    onClick={handleApplyCustomDates}
                    disabled={!startDate || !endDate || loading}
                    style={{
                      height: '46px',
                      borderRadius: '12px',
                      background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                      color: 'white',
                      fontWeight: 600,
                      padding: '0 24px',
                      border: 'none',
                    }}
                  >
                    <i className="ri-search-line me-2"></i>
                    Applica
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Filters Card 2 - Professional Type & Specific Professional */}
      <div
        className="card border-0 mb-4"
        style={{
          borderRadius: '16px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
        }}
      >
        <div className="card-body py-3 px-4">
          <div className="row g-3 align-items-center">
            {/* Professional Type Filter */}
            <div className="col-lg-6 ca-scroll-filters" data-tour="prof-filters">
              <div className="d-flex align-items-center gap-3">
                <span className="text-muted small fw-semibold">Filtra per:</span>
                <div className="d-flex gap-2">
                  {Object.entries(PROF_TYPES).map(([key, config]) => (
                    <button
                      key={key}
                      className="btn"
                      onClick={() => handleProfTypeChange(key)}
                      disabled={loading}
                      style={{
                        height: '42px',
                        borderRadius: '10px',
                        border: profType === key ? 'none' : '1px solid #e2e8f0',
                        background: profType === key
                          ? `linear-gradient(135deg, ${config.color} 0%, ${config.color}dd 100%)`
                          : '#f8fafc',
                        color: profType === key ? 'white' : '#64748b',
                        fontSize: '13px',
                        fontWeight: profType === key ? 600 : 500,
                        padding: '0 16px',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <i className={`${config.icon} me-2`}></i>
                      {config.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Specific Professional Dropdown */}
            <div className="col-lg-6">
              <div className="d-flex align-items-center gap-3 justify-content-lg-end">
                {profType && (
                  <>
                    <select
                      className="form-select"
                      value={profId || ''}
                      onChange={(e) => handleProfIdChange(e.target.value ? parseInt(e.target.value) : null)}
                      disabled={loading || loadingProfs}
                      style={{
                        height: '42px',
                        borderRadius: '10px',
                        border: '1px solid #e2e8f0',
                        background: '#f8fafc',
                        fontSize: '14px',
                        maxWidth: '250px',
                      }}
                    >
                      <option value="">Tutti i {PROF_TYPES[profType]?.label}</option>
                      {professionals.map((prof) => (
                        <option key={prof.id} value={prof.id}>
                          {prof.nome}
                        </option>
                      ))}
                    </select>
                    <button
                      className="btn btn-link text-muted p-0"
                      onClick={handleResetFilters}
                      title="Reset filtri"
                      style={{ fontSize: '18px' }}
                    >
                      <i className="ri-close-circle-line"></i>
                    </button>
                  </>
                )}
                {!profType && (
                  <span className="text-muted small fst-italic">
                    Seleziona un tipo di professionista per filtrare
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Rating & Read Filters Row */}
          <div className="row g-3 align-items-center mt-2 pt-3 border-top ca-status-filters" data-tour="status-filters">
            <div className="col-12">
              <div className="d-flex align-items-center gap-3 flex-wrap">
                <span className="text-muted small fw-semibold">Stato:</span>

                {/* Voto Da Migliorare (< 8) */}
                <button
                  className="btn"
                  onClick={() => handleRatingFilterChange('da_migliorare')}
                  disabled={loading}
                  style={{
                    height: '38px',
                    borderRadius: '10px',
                    border: ratingFilter === 'da_migliorare' ? 'none' : '1px solid #e2e8f0',
                    background: ratingFilter === 'da_migliorare'
                      ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
                      : '#f8fafc',
                    color: ratingFilter === 'da_migliorare' ? 'white' : '#64748b',
                    fontSize: '13px',
                    fontWeight: ratingFilter === 'da_migliorare' ? 600 : 500,
                    padding: '0 14px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <i className="ri-arrow-down-line me-1"></i>
                  Da Migliorare (&lt;8)
                </button>

                {/* Voto Negativo (< 7) */}
                <button
                  className="btn"
                  onClick={() => handleRatingFilterChange('negativo')}
                  disabled={loading}
                  style={{
                    height: '38px',
                    borderRadius: '10px',
                    border: ratingFilter === 'negativo' ? 'none' : '1px solid #e2e8f0',
                    background: ratingFilter === 'negativo'
                      ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
                      : '#f8fafc',
                    color: ratingFilter === 'negativo' ? 'white' : '#64748b',
                    fontSize: '13px',
                    fontWeight: ratingFilter === 'negativo' ? 600 : 500,
                    padding: '0 14px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <i className="ri-error-warning-line me-1"></i>
                  Voto Negativo (&lt;7)
                </button>

                {/* Non Letto */}
                <button
                  className="btn"
                  onClick={handleUnreadFilterChange}
                  disabled={loading}
                  style={{
                    height: '38px',
                    borderRadius: '10px',
                    border: showUnreadOnly ? 'none' : '1px solid #e2e8f0',
                    background: showUnreadOnly
                      ? 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)'
                      : '#f8fafc',
                    color: showUnreadOnly ? 'white' : '#64748b',
                    fontSize: '13px',
                    fontWeight: showUnreadOnly ? 600 : 500,
                    padding: '0 14px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <i className="ri-eye-off-line me-1"></i>
                  Non Letto
                </button>

                {/* Reset all filters button */}
                {(ratingFilter || showUnreadOnly || profType) && (
                  <button
                    className="btn btn-link text-muted p-0 ms-2"
                    onClick={handleResetFilters}
                    title="Reset tutti i filtri"
                    style={{ fontSize: '14px' }}
                  >
                    <i className="ri-refresh-line me-1"></i>
                    Reset filtri
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="alert alert-danger mb-4" style={{ borderRadius: '12px' }}>
          <i className="ri-error-warning-line me-2"></i>
          {error}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}></div>
          <p className="mt-3 text-muted">Caricamento risposte...</p>
        </div>
      ) : (
        <>
          {/* Pagination calculation */}
          {(() => {
            const filteredResponses = getFilteredResponses();

            if (filteredResponses.length === 0) {
              return (
                <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
                  <div className="card-body text-center py-5">
                    <div className="mb-4">
                      <i className="ri-file-list-3-line" style={{ fontSize: '5rem', color: '#cbd5e1' }}></i>
                    </div>
                    <h5 style={{ color: '#475569' }}>Nessuna risposta trovata</h5>
                    <p className="text-muted mb-0">
                      {responses.length > 0
                        ? 'Nessuna risposta corrisponde ai filtri selezionati.'
                        : 'Non ci sono risposte disponibili per il periodo selezionato.'}
                    </p>
                    {(ratingFilter || showUnreadOnly) && (
                      <button
                        className="btn btn-outline-primary mt-3"
                        onClick={() => { setRatingFilter(null); setShowUnreadOnly(false); }}
                      >
                        <i className="ri-refresh-line me-1"></i>
                        Rimuovi filtri stato
                      </button>
                    )}
                  </div>
                </div>
              );
            }

            // Use server-side pagination when no client-side filters are active
            const useServerPagination = !ratingFilter && !showUnreadOnly;
            const totalPages = useServerPagination ? pagination.pages : Math.ceil(filteredResponses.length / ITEMS_PER_PAGE);
            const totalItems = useServerPagination ? pagination.total : filteredResponses.length;
            const paginatedResponses = useServerPagination
              ? filteredResponses // Already paginated from server
              : filteredResponses.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

            return (
              <>
                {/* Tabella Risposte */}
                <div className="card border-0 ct-card" data-tour="responses-table">
                  <div className="table-responsive">
                    <table className="table mb-0 clienti-table">
                      <thead className="ct-thead">
                        <tr>
                          <th className="ct-th" style={{ minWidth: '200px' }}>Cliente</th>
                          <th className="ct-th" style={{ minWidth: '120px' }}>Data</th>
                          <th className="ct-th" style={{ minWidth: '120px', textAlign: 'center' }}>Nutrizione</th>
                          <th className="ct-th" style={{ minWidth: '120px', textAlign: 'center' }}>Psicologia</th>
                          <th className="ct-th" style={{ minWidth: '120px', textAlign: 'center' }}>Coach</th>
                          <th className="ct-th" style={{ minWidth: '100px', textAlign: 'center' }}>Progresso</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedResponses.map((response, index) => {
                          const isHovered = hoveredRow === index;

                          return (
                            <tr
                              key={`${response.type}-${response.id}`}
                              data-tour={index === 0 ? "check-record" : undefined}
                              className="ct-row"
                              style={{
                                background: isHovered ? '#f8fafc' : 'transparent',
                              }}
                              onMouseEnter={() => setHoveredRow(index)}
                              onMouseLeave={() => setHoveredRow(null)}
                              onClick={() => handleRowClick(response)}
                            >
                              {/* Cliente */}
                              <td className="ct-td" data-label="Cliente">
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
                              <td className="ct-td" data-label="Data">
                                <span style={{ fontWeight: 500 }}>
                                  {formatDate(response.submit_date)}
                                </span>
                              </td>

                              {/* Nutrizionista */}
                              <td className="ct-td" style={{ textAlign: 'center' }} data-label="Nutrizione">
                                <ProfessionalCell
                                  professionals={response.nutrizionisti}
                                  rating={response.nutritionist_rating}
                                  progressRating={response.progress_rating}
                                  bgColor="#dcfce7"
                                  textColor="#166534"
                                />
                              </td>

                              {/* Psicologo */}
                              <td className="ct-td" style={{ textAlign: 'center' }} data-label="Psicologia">
                                <ProfessionalCell
                                  professionals={response.psicologi}
                                  rating={response.psychologist_rating}
                                  progressRating={response.progress_rating}
                                  bgColor="#e0f2fe"
                                  textColor="#0369a1"
                                />
                              </td>

                              {/* Coach */}
                              <td className="ct-td" style={{ textAlign: 'center' }} data-label="Coach">
                                <ProfessionalCell
                                  professionals={response.coaches}
                                  rating={response.coach_rating}
                                  progressRating={response.progress_rating}
                                  bgColor="#dbeafe"
                                  textColor="#1d4ed8"
                                />
                              </td>

                              {/* Progresso */}
                              <td className="ct-td" style={{ textAlign: 'center' }} data-label="Progresso">
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                                  <span style={getRatingStyle(response.progress_rating)}>
                                    {response.progress_rating ?? '-'}
                                  </span>
                                  <img
                                    src="/static/assets/immagini/logo_user.png"
                                    alt="Progresso"
                                    style={{
                                      width: '28px',
                                      height: '28px',
                                      borderRadius: '50%',
                                      objectFit: 'cover',
                                      border: '2px solid #fff',
                                      boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
                                    }}
                                  />
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="d-flex justify-content-between align-items-center mt-4">
                    <div className="text-muted small">
                      Mostrando {((currentPage - 1) * ITEMS_PER_PAGE) + 1} - {Math.min(currentPage * ITEMS_PER_PAGE, totalItems)} di {totalItems} risposte
                    </div>
                    <nav>
                      <ul className="pagination mb-0">
                        <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                          <button
                            className="page-link"
                            onClick={() => handlePageChange(currentPage - 1)}
                            disabled={currentPage === 1 || loading}
                            style={{ borderRadius: '8px 0 0 8px' }}
                          >
                            <i className="ri-arrow-left-s-line"></i>
                          </button>
                        </li>
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum;
                          if (totalPages <= 5) {
                            pageNum = i + 1;
                          } else if (currentPage <= 3) {
                            pageNum = i + 1;
                          } else if (currentPage >= totalPages - 2) {
                            pageNum = totalPages - 4 + i;
                          } else {
                            pageNum = currentPage - 2 + i;
                          }
                          return (
                            <li key={pageNum} className={`page-item ${currentPage === pageNum ? 'active' : ''}`}>
                              <button
                                className="page-link"
                                onClick={() => handlePageChange(pageNum)}
                                disabled={loading}
                                style={currentPage === pageNum ? {
                                  background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                                  borderColor: '#22c55e',
                                  color: 'white',
                                } : {}}
                              >
                                {pageNum}
                              </button>
                            </li>
                          );
                        })}
                        <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                          <button
                            className="page-link"
                            onClick={() => handlePageChange(currentPage + 1)}
                            disabled={currentPage === totalPages || loading}
                            style={{ borderRadius: '0 8px 8px 0' }}
                          >
                            <i className="ri-arrow-right-s-line"></i>
                          </button>
                        </li>
                      </ul>
                    </nav>
                  </div>
                )}
              </>
            );
          })()}
        </>
      )}

      <CheckResponseDetailModal
        show={showCheckResponseModal && !!selectedCheckResponse}
        onClose={() => setShowCheckResponseModal(false)}
        response={selectedCheckResponse}
        loading={loadingCheckDetail}
      />
      <SupportWidget
        pageTitle="Check Azienda"
        pageDescription="Monitora la qualità del servizio, analizza i KPI dei professionisti e gestisci le criticità in tempo reale."
        pageIcon={FaChartLine}
        docsSection="check-azienda"
        onStartTour={() => setMostraTour(true)}
        brandName="Suite Clinica"
        logoSrc="/suitemind.png"
        accentColor="#22c55e"
      />

      <GuidedTour
        steps={tourSteps}
        isOpen={mostraTour}
        onClose={() => {
          setMostraTour(false);
          // Close modal if open when tour closes
          setShowCheckResponseModal(false);
        }}
        onStepChange={handleTourStepChange}
        onComplete={() => {
          setMostraTour(false);
          setShowCheckResponseModal(false);
          console.log('Tour Check Azienda completato');
        }}
      />
    </div>
  );
}

export default CheckAzienda;

import { useState, useEffect, useCallback, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { createPortal } from 'react-dom';
import clientiService, {
  GIORNI_LABELS,
  STATI_PROFESSIONISTA_COLORS,
  PATOLOGIE_NUTRI,
} from '../../services/clientiService';
import teamService from '../../services/teamService';
import { useAuth } from '../../context/AuthContext';
import { isProfessionistaStandard } from '../../utils/rbacScope';
import ClientiFilters from './ClientiFilters';
import './ClientiList.css';

// Role colors for avatars
const ROLE_COLORS = {
  hm: { bg: '#f3e8ff', text: '#9333ea', badge: '#9333ea' },
  n: { bg: '#dcfce7', text: '#16a34a', badge: '#22c55e' },
  c: { bg: '#dbeafe', text: '#2563eb', badge: '#3b82f6' },
  p: { bg: '#fce7f3', text: '#db2777', badge: '#ec4899' },
  ca: { bg: '#fef3c7', text: '#d97706', badge: '#f59e0b' },
};

// Stat card icon styles
const STAT_ICON_STYLES = {
  attivo:  { bg: 'rgba(34, 197, 94, 0.1)',  color: '#22c55e' },
  ghost:   { bg: 'rgba(100, 116, 139, 0.1)', color: '#64748b' },
  pausa:   { bg: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b' },
  stop:    { bg: 'rgba(239, 68, 68, 0.1)',  color: '#ef4444' },
};

function ClientiListaNutrizione() {
  const { user } = useAuth();
  const isAdminOrCco = Boolean(user?.is_admin || user?.role === 'admin' || user?.specialty === 'cco');
  const isTeamLeaderRestricted = Boolean(user?.role === 'team_leader' && !isAdminOrCco);
  const isProfessionista = isProfessionistaStandard(user);
  const userSpecialtyGroup = (() => {
    const s = String(user?.specialty || '').toLowerCase();
    if (s === 'nutrizione' || s === 'nutrizionista') return 'nutrizione';
    if (s === 'coach') return 'coach';
    if (s === 'psicologia' || s === 'psicologo') return 'psicologia';
    return null;
  })();

  const visualButtons = [
    { key: 'generale', to: '/clienti-lista', label: 'Lista Generale', icon: 'ri-list-check' },
    { key: 'nutrizione', to: '/clienti-nutrizione', label: 'Visuale Nutrizione', icon: 'ri-restaurant-line' },
    { key: 'coach', to: '/clienti-coach', label: 'Visuale Coach', icon: 'ri-run-line' },
    { key: 'psicologia', to: '/clienti-psicologia', label: 'Visuale Psicologia', icon: 'ri-mental-health-line' },
  ].filter((btn) => {
    if (isProfessionista) return btn.key === 'generale' || btn.key === userSpecialtyGroup;
    if (!isTeamLeaderRestricted) return true;
    if (btn.key === 'generale') return true;
    return btn.key === userSpecialtyGroup;
  });

  const [searchParams, setSearchParams] = useSearchParams();
  const [clienti, setClienti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [kpi, setKpi] = useState({
    stato_attivo: 0,
    stato_ghost: 0,
    stato_pausa: 0,
    stato_stop: 0,
    chat_attivo: 0,
    chat_ghost: 0,
    chat_pausa: 0,
    chat_stop: 0,
  });
  const [nutrizionisti, setNutrizionisti] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 25,
    total: 0,
    totalPages: 0,
  });

  const [searchInput, setSearchInput] = useState(searchParams.get('q') || '');
  const [debouncedSearch, setDebouncedSearch] = useState(searchParams.get('q') || '');
  const searchTimerRef = useRef(null);

  const [filters, setFilters] = useState(() => {
    const init = {
      stato: searchParams.get('stato_cliente') || '',
      // Backward compat: leggi anche "tipologia" (legacy URL)
      tipologia: searchParams.get('tipologia_supporto_nutrizione') || searchParams.get('tipologia') || '',
      nutrizionista: searchParams.get('nutrizionista_id') || '',
      statoNutrizione: searchParams.get('stato_nutrizione') || '',
      statoChatNutrizione: searchParams.get('stato_chat_nutrizione') || '',
      checkDay: searchParams.get('check_day') || '',
      reachOut: searchParams.get('reach_out_nutrizione') || '',
      callInizialeNutrizionista: searchParams.get('call_iniziale_nutrizionista') || '',
      missing_piano_dieta: searchParams.get('missing_piano_dieta') || '0',
    };
    // Init patologie from URL params
    const patKeys = [
      'patologia_ibs','patologia_reflusso','patologia_gastrite','patologia_dca',
      'patologia_insulino_resistenza','patologia_diabete','patologia_dislipidemie',
      'patologia_steatosi_epatica','patologia_ipertensione','patologia_pcos',
      'patologia_endometriosi','patologia_obesita_sindrome','patologia_osteoporosi',
      'patologia_diverticolite','patologia_crohn','patologia_stitichezza','patologia_tiroidee',
    ];
    patKeys.forEach(k => { init[k] = searchParams.get(k) || '0'; });
    return init;
  });
  const [showFilters, setShowFilters] = useState(false);

  // Modal states
  const [showAnamnesiModal, setShowAnamnesiModal] = useState(false);
  const [showDiarioModal, setShowDiarioModal] = useState(false);
  const [showPatologieModal, setShowPatologieModal] = useState(false);
  const [showStatoModal, setShowStatoModal] = useState(false);
  const [showChatModal, setShowChatModal] = useState(false);
  const [showCheckDayModal, setShowCheckDayModal] = useState(false);
  const [showReachOutModal, setShowReachOutModal] = useState(false);
  const [selectedCliente, setSelectedCliente] = useState(null);
  const [modalValue, setModalValue] = useState('');
  const [saving, setSaving] = useState(false);

  // Anamnesi states
  const [anamnesiData, setAnamnesiData] = useState(null);
  const [anamnesiContent, setAnamnesiContent] = useState('');
  const [loadingAnamnesi, setLoadingAnamnesi] = useState(false);
  const [savingAnamnesi, setSavingAnamnesi] = useState(false);

  // Diario states
  const [diarioEntries, setDiarioEntries] = useState([]);
  const [loadingDiario, setLoadingDiario] = useState(false);
  const [newDiarioContent, setNewDiarioContent] = useState('');
  const [newDiarioDate, setNewDiarioDate] = useState('');
  const [savingDiario, setSavingDiario] = useState(false);

  // Fetch nutrizionisti on mount
  useEffect(() => {
    const fetchNutrizionisti = async () => {
      try {
        const data = await teamService.getTeamMembers({
          per_page: 100,
          active: '1',
          specialty: 'nutrizione,nutrizionista',
        });
        setNutrizionisti(data.members || []);
      } catch (err) {
        console.error('Error fetching nutrizionisti:', err);
      }
    };
    fetchNutrizionisti();
  }, []);

  const fetchClienti = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page: pagination.page,
        per_page: pagination.perPage,
        q: debouncedSearch || undefined,
        stato_cliente: filters.stato || undefined,
        tipologia_supporto_nutrizione: filters.tipologia || undefined,
        nutrizionista_id: filters.nutrizionista || undefined,
        stato_nutrizione: filters.statoNutrizione || undefined,
        stato_chat_nutrizione: filters.statoChatNutrizione || undefined,
        check_day: filters.checkDay || undefined,
        reach_out_nutrizione: filters.reachOut || undefined,
        call_iniziale_nutrizionista: filters.callInizialeNutrizionista || undefined,
        missing_piano_dieta: filters.missing_piano_dieta === '1' ? '1' : undefined,
      };
      // Add patologie filters
      PATOLOGIE_NUTRI.forEach(p => {
        if (filters[p.key] === '1') params[p.key] = '1';
      });

      const data = await clientiService.getClientiNutrizione(params);
      setClienti(data.data || []);
      setPagination(prev => ({
        ...prev,
        total: data.pagination?.total || 0,
        totalPages: data.pagination?.pages || 0,
      }));

      // Calculate KPIs from data
      if (data.kpi) {
        setKpi(data.kpi);
      } else {
        // Calculate from clienti if kpi not provided
        const clientiData = data.data || [];
        setKpi({
          stato_attivo: clientiData.filter(c => c.stato_nutrizione === 'attivo').length,
          stato_ghost: clientiData.filter(c => c.stato_nutrizione === 'ghost').length,
          stato_pausa: clientiData.filter(c => c.stato_nutrizione === 'pausa').length,
          stato_stop: clientiData.filter(c => c.stato_nutrizione === 'stop').length,
          chat_attivo: clientiData.filter(c => c.stato_cliente_chat_nutrizione === 'attivo').length,
          chat_ghost: clientiData.filter(c => c.stato_cliente_chat_nutrizione === 'ghost').length,
          chat_pausa: clientiData.filter(c => c.stato_cliente_chat_nutrizione === 'pausa').length,
          chat_stop: clientiData.filter(c => c.stato_cliente_chat_nutrizione === 'stop').length,
        });
      }
    } catch (err) {
      console.error('Error fetching clienti:', err);
      setError('Errore nel caricamento dei clienti');
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.perPage, debouncedSearch, filters]);

  useEffect(() => {
    fetchClienti();
  }, [fetchClienti]);

  // Map filter state keys to URL/backend param names
  const FILTER_KEY_MAP = {
    search: 'q',
    stato: 'stato_cliente',
    tipologia: 'tipologia_supporto_nutrizione',
    nutrizionista: 'nutrizionista_id',
    statoNutrizione: 'stato_nutrizione',
    statoChatNutrizione: 'stato_chat_nutrizione',
    checkDay: 'check_day',
    reachOut: 'reach_out_nutrizione',
    callInizialeNutrizionista: 'call_iniziale_nutrizionista',
    missing_piano_dieta: 'missing_piano_dieta',
  };

  const handleSearchInput = (value) => {
    setSearchInput(value);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(value);
      setPagination(prev => ({ ...prev, page: 1 }));
      const newParams = new URLSearchParams(searchParams);
      if (value) {
        newParams.set('q', value);
      } else {
        newParams.delete('q');
      }
      setSearchParams(newParams);
    }, 400);
  };

  useEffect(() => {
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, []);

  const handleFilterChange = (key, value) => {
    if (key === 'search') {
      handleSearchInput(value);
      return;
    }
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 }));
    const newParams = new URLSearchParams(searchParams);
    const paramKey = FILTER_KEY_MAP[key] || key;
    if (value && value !== '0') {
      newParams.set(paramKey, value);
    } else {
      newParams.delete(paramKey);
    }
    // Cleanup parametro legacy per evitare conflitti URL
    if (key === 'tipologia' && paramKey !== 'tipologia') {
      newParams.delete('tipologia');
    }
    setSearchParams(newParams);
  };

  const resetFilters = () => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    setSearchInput('');
    setDebouncedSearch('');
    const clean = {
      stato: '', tipologia: '', nutrizionista: '',
      statoNutrizione: '', statoChatNutrizione: '', checkDay: '', reachOut: '',
      callInizialeNutrizionista: '', missing_piano_dieta: '0',
    };
    PATOLOGIE_NUTRI.forEach(p => { clean[p.key] = '0'; });
    setFilters(clean);
    setSearchParams(new URLSearchParams());
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, page: newPage }));
  };

  // Get patologie for a client
  const getClientPatologie = (cliente) => {
    return PATOLOGIE_NUTRI.filter(p => cliente[p.key]).map(p => p.label);
  };

  // Handle field update
  const handleUpdateField = async (clienteId, field, value) => {
    setSaving(true);
    try {
      const result = await clientiService.updateField(clienteId, field, value || null);

      // Aggiorna immediatamente il cliente nel state locale (ottimistico)
      // senza aspettare il refetch della lista intera.
      const updatedCliente = result?.data;
      if (updatedCliente) {
        setClienti(prev =>
          prev.map(c => (c.cliente_id === clienteId ? updatedCliente : c))
        );
        // Aggiorna i KPI contatori in base al campo cambiato
        if (field === 'stato_nutrizione' || field === 'stato_cliente_chat_nutrizione') {
          // Refetch in background solo per aggiornare i contatori KPI
          fetchClienti();
        }
      } else {
        // Fallback: refetch completo se il server non ha restituito il cliente aggiornato
        fetchClienti();
      }

      setShowStatoModal(false);
      setShowChatModal(false);
      setShowCheckDayModal(false);
      setShowReachOutModal(false);
    } catch (err) {
      console.error('Error updating field:', err);
      alert('Errore nel salvataggio');
    } finally {
      setSaving(false);
    }
  };

  // Open modal helpers
  const openAnamnesiModal = async (cliente) => {
    setSelectedCliente(cliente);
    setAnamnesiData(null);
    setAnamnesiContent('');
    setShowAnamnesiModal(true);
    setLoadingAnamnesi(true);
    try {
      const res = await clientiService.getAnamnesi(cliente.cliente_id || cliente.clienteId, 'nutrizione');
      if (res?.anamnesi) {
        setAnamnesiData(res.anamnesi);
        setAnamnesiContent(res.anamnesi.content || '');
      }
    } catch (err) {
      console.error('Error loading anamnesi:', err);
    } finally {
      setLoadingAnamnesi(false);
    }
  };

  const handleSaveAnamnesi = async () => {
    if (!selectedCliente) return;
    setSavingAnamnesi(true);
    try {
      await clientiService.saveAnamnesi(selectedCliente.cliente_id || selectedCliente.clienteId, 'nutrizione', anamnesiContent);
      const res = await clientiService.getAnamnesi(selectedCliente.cliente_id || selectedCliente.clienteId, 'nutrizione');
      if (res?.anamnesi) {
        setAnamnesiData(res.anamnesi);
        setAnamnesiContent(res.anamnesi.content || '');
      }
    } catch (err) {
      console.error('Error saving anamnesi:', err);
      alert('Errore nel salvataggio anamnesi');
    } finally {
      setSavingAnamnesi(false);
    }
  };

  const openDiarioModal = async (cliente) => {
    setSelectedCliente(cliente);
    setDiarioEntries([]);
    setNewDiarioContent('');
    setNewDiarioDate(new Date().toISOString().slice(0, 10));
    setShowDiarioModal(true);
    setLoadingDiario(true);
    try {
      const res = await clientiService.getDiaryEntries(cliente.cliente_id || cliente.clienteId, 'nutrizione');
      setDiarioEntries(res?.entries || []);
    } catch (err) {
      console.error('Error loading diario:', err);
    } finally {
      setLoadingDiario(false);
    }
  };

  const handleAddDiarioEntry = async () => {
    if (!selectedCliente || !newDiarioContent.trim()) return;
    setSavingDiario(true);
    try {
      await clientiService.createDiaryEntry(
        selectedCliente.cliente_id || selectedCliente.clienteId,
        'nutrizione',
        newDiarioContent.trim(),
        newDiarioDate || null,
      );
      const res = await clientiService.getDiaryEntries(selectedCliente.cliente_id || selectedCliente.clienteId, 'nutrizione');
      setDiarioEntries(res?.entries || []);
      setNewDiarioContent('');
      setNewDiarioDate(new Date().toISOString().slice(0, 10));
    } catch (err) {
      console.error('Error adding diario entry:', err);
      alert('Errore nel salvataggio nota diario');
    } finally {
      setSavingDiario(false);
    }
  };

  const openStatoModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.stato_nutrizione || '');
    setShowStatoModal(true);
  };

  const openChatModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.stato_cliente_chat_nutrizione || '');
    setShowChatModal(true);
  };

  const openCheckDayModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.check_day || '');
    setShowCheckDayModal(true);
  };

  const openReachOutModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.reach_out_nutrizione || '');
    setShowReachOutModal(true);
  };

  // Render avatar team
  const renderTeamAvatar = (user, roleKey, roleLabel) => {
    if (!user) return null;
    const colors = ROLE_COLORS[roleKey] || ROLE_COLORS.n;
    const initials = `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase();

    return (
      <span
        key={`${roleKey}-${user.id}`}
        className="cl-avatar-wrap"
        title={`${roleLabel}: ${user.full_name || `${user.first_name} ${user.last_name}`}`}
      >
        {user.avatar_url || user.avatar_path ? (
          <img
            src={user.avatar_url || user.avatar_path}
            alt={user.full_name}
            className="cl-avatar-img"
          />
        ) : (
          <span
            className="cl-avatar-initials"
            style={{ background: colors.bg, color: colors.text }}
          >
            {initials}
          </span>
        )}
        <span className="cl-avatar-role-badge" style={{ background: colors.badge }}>
          {roleKey.toUpperCase()}
        </span>
      </span>
    );
  };

  // Render stato badge
  const renderStatoBadge = (stato) => {
    if (!stato) return <span className="cl-empty">&mdash;</span>;
    const colors = STATI_PROFESSIONISTA_COLORS[stato] || { bg: '#f1f5f9', color: '#64748b' };
    return (
      <span className="cl-badge" style={{ background: colors.bg, color: colors.color }}>
        <i className="ri-circle-fill" style={{ fontSize: '6px' }}></i>{' '}
        {stato}
      </span>
    );
  };

  // Pagination page numbers
  const getPageNumbers = () => {
    const pages = [];
    const total = pagination.totalPages;
    const current = pagination.page;
    const maxVisible = 5;

    if (total <= maxVisible) {
      for (let i = 1; i <= total; i++) pages.push(i);
    } else if (current <= 3) {
      for (let i = 1; i <= maxVisible; i++) pages.push(i);
    } else if (current >= total - 2) {
      for (let i = total - maxVisible + 1; i <= total; i++) pages.push(i);
    } else {
      for (let i = current - 2; i <= current + 2; i++) pages.push(i);
    }
    return pages;
  };

  // Count active filters (excluding search)
  const activeFilterCount = Object.entries(filters)
    .filter(([key, val]) => key !== 'search' && val && val !== '' && val !== '0')
    .length;

  // Stat cards config
  const statCards = [
    { key: 'attivo', label: 'Stato Attivo', value: kpi.stato_attivo, icon: 'ri-check-line' },
    { key: 'ghost', label: 'Stato Ghost', value: kpi.stato_ghost, icon: 'ri-ghost-line' },
    { key: 'pausa', label: 'Stato Pausa', value: kpi.stato_pausa, icon: 'ri-pause-line' },
    { key: 'stop', label: 'Stato Stop', value: kpi.stato_stop, icon: 'ri-stop-line' },
  ];

  // Render a portal-based modal
  const renderModal = (show, onClose, title, icon, children, footer) => {
    if (!show || !selectedCliente) return null;
    return createPortal(
      <div className="cl-modal-overlay" onClick={onClose}>
        <div className="cl-modal" onClick={(e) => e.stopPropagation()}>
          <div className="cl-modal-header">
            <h5 className="cl-modal-title">
              <i className={icon}></i>
              {title} - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
            </h5>
            <button className="cl-modal-close" onClick={onClose}>&times;</button>
          </div>
          <div className="cl-modal-body">
            {children}
          </div>
          <div className="cl-modal-footer">
            {footer}
          </div>
        </div>
      </div>,
      document.body
    );
  };

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="cl-header">
        <div>
          <h4>Visuale Nutrizione</h4>
          <p className="cl-header-sub">{pagination.total} pazienti in visuale nutrizione</p>
        </div>
        <div className="cl-view-pills">
          {visualButtons.map((btn) => (
            <Link
              key={btn.key}
              to={btn.to}
              className={`cl-view-pill${btn.key === 'nutrizione' ? ' active' : ''}`}
            >
              <i className={btn.icon}></i> {btn.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Stats Row */}
      <div className="cl-stats-row">
        {statCards.map((stat) => {
          const iconStyle = STAT_ICON_STYLES[stat.key] || STAT_ICON_STYLES.attivo;
          return (
            <div key={stat.key} className="cl-stat-card">
              <div>
                <div className="cl-stat-value">{stat.value}</div>
                <div className="cl-stat-label">{stat.label}</div>
              </div>
              <div
                className="cl-stat-icon"
                style={{ background: iconStyle.bg, color: iconStyle.color }}
              >
                <i className={stat.icon}></i>
              </div>
            </div>
          );
        })}
      </div>

      {/* Search Bar + Filter Button */}
      <div className="cl-search-row">
        <div className="cl-search-wrap">
          <i className="ri-search-line cl-search-icon"></i>
          <input
            type="text"
            className="cl-search-input"
            placeholder="Cerca paziente per nome..."
            value={searchInput}
            onChange={(e) => handleSearchInput(e.target.value)}
          />
        </div>
        <button className="cl-filter-open-btn" onClick={() => setShowFilters(true)}>
          <i className="ri-filter-3-line"></i> Filtra
          {activeFilterCount > 0 && (
            <span className="cl-filter-badge">{activeFilterCount}</span>
          )}
        </button>
      </div>

      {/* Filters Modal */}
      <ClientiFilters
        mode="nutrizione"
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={resetFilters}
        professionisti={nutrizionisti}
        visibleProfessionalFilters={{ nutrizione: !isProfessionista, coach: false, psicologia: false }}
        open={showFilters}
        onClose={() => setShowFilters(false)}
      />

      {/* Content */}
      {loading ? (
        <div className="cl-loading">
          <div className="cl-spinner" style={{ margin: '0 auto' }}></div>
          <p className="cl-loading-text">Caricamento pazienti...</p>
        </div>
      ) : error ? (
        <div className="cl-error">{error}</div>
      ) : clienti.length === 0 ? (
        <div className="cl-empty-state">
          <div className="cl-empty-icon">
            <i className="ri-restaurant-line"></i>
          </div>
          <h5 className="cl-empty-title">Nessun paziente trovato</h5>
          <p className="cl-empty-desc">Prova a modificare i filtri di ricerca</p>
          <button className="cl-reset-btn" onClick={resetFilters}>
            <i className="ri-refresh-line"></i> Reset Filtri
          </button>
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="cl-table-card">
            <div className="table-responsive">
              <table className="cl-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '180px' }}>Cliente</th>
                    <th style={{ minWidth: '100px' }}>Team</th>
                    <th style={{ minWidth: '110px' }}>Stato Nutri</th>
                    <th style={{ minWidth: '110px' }}>Stato Chat</th>
                    <th style={{ minWidth: '100px' }}>Check Day</th>
                    <th style={{ minWidth: '100px' }}>Reach Out</th>
                    <th style={{ textAlign: 'center', minWidth: '110px' }}>Patologie</th>
                    <th style={{ textAlign: 'center', minWidth: '100px' }}>Piano Dieta</th>
                    <th style={{ textAlign: 'center', minWidth: '90px' }}>Anamnesi</th>
                    <th style={{ textAlign: 'center', minWidth: '80px' }}>Diario</th>
                    <th style={{ textAlign: 'right', minWidth: '80px' }}>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {clienti.map((cliente) => {
                    const patologie = getClientPatologie(cliente);
                    const clienteId = cliente.cliente_id || cliente.clienteId;

                    const healthManager = cliente.health_manager_user || cliente.healthManagerUser;
                    const nutrizionistiList = cliente.nutrizionisti_multipli || cliente.nutrizionistiMultipli || [];
                    const coachesList = cliente.coaches_multipli || cliente.coachesMultipli || [];
                    const psicologiList = cliente.psicologi_multipli || cliente.psicologiMultipli || [];
                    const consulentiList = cliente.consulenti_multipli || cliente.consulentiMultipli || [];
                    const hasTeam = healthManager || nutrizionistiList.length || coachesList.length || psicologiList.length || consulentiList.length;

                    return (
                      <tr key={clienteId}>
                        <td>
                          <Link to={`/clienti-dettaglio/${clienteId}`} className="cl-name-link">
                            {cliente.nome_cognome || cliente.nomeCognome}
                          </Link>
                        </td>
                        <td>
                          <div className="cl-team-avatars">
                            {healthManager && renderTeamAvatar(healthManager, 'hm', 'Health Manager')}
                            {nutrizionistiList.map(n => renderTeamAvatar(n, 'n', 'Nutrizionista'))}
                            {coachesList.map(c => renderTeamAvatar(c, 'c', 'Coach'))}
                            {psicologiList.map(p => renderTeamAvatar(p, 'p', 'Psicologo'))}
                            {consulentiList.map(ca => renderTeamAvatar(ca, 'ca', 'Consulente'))}
                            {!hasTeam && <span className="cl-empty">&mdash;</span>}
                          </div>
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-1">
                            {renderStatoBadge(cliente.stato_nutrizione)}
                            <button className="cl-action-btn" onClick={() => openStatoModal(cliente)} title="Modifica stato" style={{ width: '28px', height: '28px', fontSize: '12px' }}>
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-1">
                            {cliente.stato_cliente_chat_nutrizione ? (
                              <span className="cl-badge" style={{
                                background: STATI_PROFESSIONISTA_COLORS[cliente.stato_cliente_chat_nutrizione]?.bg || '#f1f5f9',
                                color: STATI_PROFESSIONISTA_COLORS[cliente.stato_cliente_chat_nutrizione]?.color || '#64748b'
                              }}>
                                <i className="ri-chat-3-line" style={{ fontSize: '10px' }}></i>{' '}
                                {cliente.stato_cliente_chat_nutrizione}
                              </span>
                            ) : <span className="cl-empty">&mdash;</span>}
                            <button className="cl-action-btn" onClick={() => openChatModal(cliente)} title="Modifica stato chat" style={{ width: '28px', height: '28px', fontSize: '12px' }}>
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-1">
                            {cliente.check_day ? (
                              <span className="cl-badge" style={{ background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)', color: '#1e40af' }}>
                                <i className="ri-calendar-check-line"></i>{' '}
                                {GIORNI_LABELS[cliente.check_day] || cliente.check_day}
                              </span>
                            ) : (
                              <span className="cl-empty">&mdash;</span>
                            )}
                            <button className="cl-action-btn" onClick={() => openCheckDayModal(cliente)} title="Modifica check day" style={{ width: '28px', height: '28px', fontSize: '12px' }}>
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-1">
                            {cliente.reach_out_nutrizione ? (
                              <span className="cl-badge" style={{ background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)', color: '#92400e' }}>
                                <i className="ri-calendar-event-line"></i>{' '}
                                {GIORNI_LABELS[cliente.reach_out_nutrizione] || cliente.reach_out_nutrizione}
                              </span>
                            ) : (
                              <span className="cl-empty">&mdash;</span>
                            )}
                            <button className="cl-action-btn" onClick={() => openReachOutModal(cliente)} title="Modifica reach out" style={{ width: '28px', height: '28px', fontSize: '12px' }}>
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          {patologie.length > 0 ? (
                            <button
                              className="cl-action-btn"
                              style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', color: 'white', borderColor: 'transparent', width: 'auto', padding: '4px 10px', fontSize: '12px', fontWeight: 600 }}
                              onClick={() => { setSelectedCliente(cliente); setShowPatologieModal(true); }}
                            >
                              <i className="ri-heart-pulse-line" style={{ marginRight: '4px' }}></i>
                              {patologie.length}
                            </button>
                          ) : cliente.nessuna_patologia_nutrizionale ? (
                            <span className="cl-badge" style={{ background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)', color: '#166534', cursor: 'default' }}>
                              <i className="ri-checkbox-circle-line"></i>
                            </span>
                          ) : (
                            <button
                              className="cl-action-btn"
                              style={{ background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)', color: 'white', borderColor: 'transparent', width: 'auto', padding: '4px 10px', fontSize: '12px' }}
                              onClick={() => { setSelectedCliente(cliente); setShowPatologieModal(true); }}
                            >
                              <i className="ri-heart-pulse-line" style={{ marginRight: '4px' }}></i>-
                            </button>
                          )}
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          {cliente.active_meal_plan ? (
                            <Link
                              to={`/clienti-dettaglio/${clienteId}?tab=nutrizione&subtab=piano`}
                              className="cl-action-btn"
                              style={{
                                background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
                                color: 'white', borderColor: 'transparent', width: 'auto', padding: '4px 10px', fontSize: '12px', fontWeight: 600,
                                textDecoration: 'none', display: 'inline-flex', alignItems: 'center',
                              }}
                              title={cliente.active_meal_plan.name || 'Piano Alimentare'}
                            >
                              <i className={`ri-${cliente.active_meal_plan.has_file ? 'file-pdf-2-line' : 'file-list-line'}`} style={{ marginRight: '4px' }}></i>
                              {cliente.active_meal_plan.has_file ? 'PDF' : 'Attivo'}
                            </Link>
                          ) : (
                            <Link
                              to={`/clienti-dettaglio/${clienteId}?tab=nutrizione&subtab=piano`}
                              className="cl-action-btn"
                              style={{
                                background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                                color: 'white', borderColor: 'transparent', width: 'auto', padding: '4px 10px', fontSize: '12px', fontWeight: 600,
                                textDecoration: 'none', display: 'inline-flex', alignItems: 'center',
                              }}
                            >
                              <i className="ri-add-line" style={{ marginRight: '4px' }}></i>+
                            </Link>
                          )}
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <button
                            className="cl-action-btn"
                            style={{
                              background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                              color: 'white', borderColor: 'transparent', width: 'auto', padding: '4px 10px', fontSize: '12px', fontWeight: 600,
                            }}
                            onClick={() => openAnamnesiModal(cliente)}
                          >
                            <i className="ri-stethoscope-line" style={{ marginRight: '4px' }}></i>
                            Apri
                          </button>
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <button
                            className="cl-action-btn"
                            style={{
                              background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                              color: 'white', borderColor: 'transparent', width: 'auto', padding: '4px 10px', fontSize: '12px', fontWeight: 600,
                            }}
                            onClick={() => openDiarioModal(cliente)}
                          >
                            <i className="ri-book-open-line" style={{ marginRight: '4px' }}></i>
                            Apri
                          </button>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <Link to={`/clienti-dettaglio/${clienteId}`} className="cl-action-btn" title="Dettaglio">
                            <i className="ri-eye-line"></i>
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {pagination.totalPages > 1 && (
            <div className="cl-pagination">
              <span className="cl-pagination-info">
                Pagina <strong>{pagination.page}</strong> di <strong>{pagination.totalPages}</strong>
                {' '}&bull; {pagination.total} risultati
              </span>
              <div className="cl-pagination-buttons">
                <button className="cl-page-btn" onClick={() => handlePageChange(1)} disabled={pagination.page === 1} title="Prima pagina">&laquo;</button>
                <button className="cl-page-btn" onClick={() => handlePageChange(pagination.page - 1)} disabled={pagination.page === 1} title="Precedente">&lsaquo;</button>
                {getPageNumbers().map((pageNum) => (
                  <button
                    key={pageNum}
                    className={`cl-page-btn${pagination.page === pageNum ? ' active' : ''}`}
                    onClick={() => handlePageChange(pageNum)}
                  >
                    {pageNum}
                  </button>
                ))}
                <button className="cl-page-btn" onClick={() => handlePageChange(pagination.page + 1)} disabled={pagination.page === pagination.totalPages} title="Successiva">&rsaquo;</button>
                <button className="cl-page-btn" onClick={() => handlePageChange(pagination.totalPages)} disabled={pagination.page === pagination.totalPages} title="Ultima pagina">&raquo;</button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Modal Anamnesi Nutrizionale */}
      {renderModal(showAnamnesiModal, () => setShowAnamnesiModal(false), 'Anamnesi Nutrizionale', 'ri-stethoscope-line',
        loadingAnamnesi ? (
          <div className="text-center py-4">
            <div className="cl-spinner" style={{ margin: '0 auto' }}></div>
            <p className="cl-loading-text">Caricamento anamnesi...</p>
          </div>
        ) : (
          <>
            {anamnesiData && (
              <div className="mb-3" style={{ fontSize: '12px', color: '#64748b' }}>
                {anamnesiData.created_by && <span>Creato da <strong>{anamnesiData.created_by}</strong> il {anamnesiData.created_at}</span>}
                {anamnesiData.last_modified_by && <span> &bull; Ultima modifica da <strong>{anamnesiData.last_modified_by}</strong> il {anamnesiData.updated_at}</span>}
              </div>
            )}
            <textarea
              className="form-control"
              rows="12"
              value={anamnesiContent}
              onChange={(e) => setAnamnesiContent(e.target.value)}
              placeholder="Anamnesi patologica remota e prossima, anamnesi familiare, stile di vita e abitudini, terapie e allergie..."
            />
          </>
        ),
        <>
          <button className="cl-modal-btn-reset" onClick={() => setShowAnamnesiModal(false)}>
            <i className="ri-close-line"></i> Chiudi
          </button>
          <button
            className="cl-modal-btn-apply"
            onClick={handleSaveAnamnesi}
            disabled={savingAnamnesi || loadingAnamnesi}
          >
            {savingAnamnesi ? <><i className="ri-loader-4-line"></i> Salvando...</> : <><i className="ri-save-line"></i> Salva</>}
          </button>
        </>
      )}

      {/* Modal Diario Nutrizionale */}
      {renderModal(showDiarioModal, () => setShowDiarioModal(false), 'Diario Nutrizionale', 'ri-book-open-line',
        loadingDiario ? (
          <div className="text-center py-4">
            <div className="cl-spinner" style={{ margin: '0 auto' }}></div>
            <p className="cl-loading-text">Caricamento diario...</p>
          </div>
        ) : (
          <>
            <div className="mb-3 p-3" style={{ background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <label className="form-label" style={{ fontWeight: 600, fontSize: '13px' }}>Aggiungi nuova nota</label>
              <div className="d-flex gap-2 mb-2">
                <input
                  type="date"
                  className="form-control"
                  style={{ maxWidth: '160px' }}
                  value={newDiarioDate}
                  onChange={(e) => setNewDiarioDate(e.target.value)}
                />
              </div>
              <textarea
                className="form-control mb-2"
                rows="3"
                value={newDiarioContent}
                onChange={(e) => setNewDiarioContent(e.target.value)}
                placeholder="Scrivi una nuova nota nel diario..."
              />
              <button
                className="cl-modal-btn-apply"
                style={{ fontSize: '12px', padding: '6px 16px' }}
                onClick={handleAddDiarioEntry}
                disabled={savingDiario || !newDiarioContent.trim()}
              >
                {savingDiario ? <><i className="ri-loader-4-line"></i> Salvando...</> : <><i className="ri-add-line"></i> Aggiungi</>}
              </button>
            </div>
            {diarioEntries.length > 0 ? (
              <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
                {diarioEntries.map((entry) => (
                  <div key={entry.id} className="mb-2 p-3" style={{ background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div className="d-flex align-items-center gap-2 mb-1">
                      <span className="cl-badge" style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', color: 'white', fontSize: '11px' }}>
                        {entry.entry_date_display || entry.entry_date}
                      </span>
                      <span style={{ fontSize: '11px', color: '#64748b' }}>{entry.author}</span>
                    </div>
                    <p style={{ margin: 0, fontSize: '13px', whiteSpace: 'pre-wrap' }}>{entry.content}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-3">
                <i className="ri-book-open-line" style={{ fontSize: '36px', color: '#cbd5e1' }}></i>
                <p style={{ color: '#64748b', marginTop: '8px', marginBottom: 0, fontSize: '13px' }}>Nessuna nota nel diario</p>
              </div>
            )}
          </>
        ),
        <button className="cl-modal-btn-reset" onClick={() => setShowDiarioModal(false)}>
          <i className="ri-close-line"></i> Chiudi
        </button>
      )}

      {/* Modal Stato Nutrizione */}
      {renderModal(showStatoModal, () => setShowStatoModal(false), 'Stato Nutrizione', 'ri-circle-fill',
        <select className="form-select" value={modalValue} onChange={(e) => setModalValue(e.target.value)}>
          <option value="">-- Nessuno --</option>
          <option value="attivo">Attivo</option>
          <option value="pausa">Pausa</option>
          <option value="ghost">Ghost</option>
          <option value="stop">Stop</option>
        </select>,
        <>
          <button className="cl-modal-btn-reset" onClick={() => setShowStatoModal(false)}>
            <i className="ri-close-line"></i> Chiudi
          </button>
          <button
            className="cl-modal-btn-apply"
            onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'stato_nutrizione', modalValue)}
            disabled={saving}
          >
            {saving ? <><i className="ri-loader-4-line"></i> Salvando...</> : <><i className="ri-save-line"></i> Salva</>}
          </button>
        </>
      )}

      {/* Modal Stato Chat */}
      {renderModal(showChatModal, () => setShowChatModal(false), 'Stato Chat', 'ri-chat-3-line',
        <select className="form-select" value={modalValue} onChange={(e) => setModalValue(e.target.value)}>
          <option value="">-- Nessuno --</option>
          <option value="attivo">Attivo</option>
          <option value="pausa">Pausa</option>
          <option value="ghost">Ghost</option>
          <option value="stop">Stop</option>
        </select>,
        <>
          <button className="cl-modal-btn-reset" onClick={() => setShowChatModal(false)}>
            <i className="ri-close-line"></i> Chiudi
          </button>
          <button
            className="cl-modal-btn-apply"
            onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'stato_cliente_chat_nutrizione', modalValue)}
            disabled={saving}
          >
            {saving ? <><i className="ri-loader-4-line"></i> Salvando...</> : <><i className="ri-save-line"></i> Salva</>}
          </button>
        </>
      )}

      {/* Modal Check Day */}
      {renderModal(showCheckDayModal, () => setShowCheckDayModal(false), 'Check Day', 'ri-calendar-check-line',
        <select className="form-select" value={modalValue} onChange={(e) => setModalValue(e.target.value)}>
          <option value="">-- Nessun giorno --</option>
          <option value="lunedi">Lunedi</option>
          <option value="martedi">Martedi</option>
          <option value="mercoledi">Mercoledi</option>
          <option value="giovedi">Giovedi</option>
          <option value="venerdi">Venerdi</option>
          <option value="sabato">Sabato</option>
          <option value="domenica">Domenica</option>
        </select>,
        <>
          <button className="cl-modal-btn-reset" onClick={() => setShowCheckDayModal(false)}>
            <i className="ri-close-line"></i> Chiudi
          </button>
          <button
            className="cl-modal-btn-apply"
            onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'check_day', modalValue)}
            disabled={saving}
          >
            {saving ? <><i className="ri-loader-4-line"></i> Salvando...</> : <><i className="ri-save-line"></i> Salva</>}
          </button>
        </>
      )}

      {/* Modal Reach Out */}
      {renderModal(showReachOutModal, () => setShowReachOutModal(false), 'Reach Out', 'ri-calendar-event-line',
        <select className="form-select" value={modalValue} onChange={(e) => setModalValue(e.target.value)}>
          <option value="">-- Nessun giorno --</option>
          <option value="lunedi">Lunedi</option>
          <option value="martedi">Martedi</option>
          <option value="mercoledi">Mercoledi</option>
          <option value="giovedi">Giovedi</option>
          <option value="venerdi">Venerdi</option>
          <option value="sabato">Sabato</option>
          <option value="domenica">Domenica</option>
        </select>,
        <>
          <button className="cl-modal-btn-reset" onClick={() => setShowReachOutModal(false)}>
            <i className="ri-close-line"></i> Chiudi
          </button>
          <button
            className="cl-modal-btn-apply"
            onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'reach_out_nutrizione', modalValue)}
            disabled={saving}
          >
            {saving ? <><i className="ri-loader-4-line"></i> Salvando...</> : <><i className="ri-save-line"></i> Salva</>}
          </button>
        </>
      )}

      {/* Modal Patologie */}
      {renderModal(showPatologieModal, () => setShowPatologieModal(false), 'Patologie', 'ri-heart-pulse-line',
        selectedCliente && getClientPatologie(selectedCliente).length > 0 ? (
          <div className="d-flex flex-wrap gap-2">
            {getClientPatologie(selectedCliente).map((p, i) => (
              <span key={i} className="cl-badge" style={{ background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)', color: '#166534', padding: '6px 12px', borderRadius: '20px', fontSize: '12px' }}>
                <i className="ri-heart-pulse-fill"></i>{' '}{p}
              </span>
            ))}
          </div>
        ) : (
          <div className="text-center py-4">
            <i className="ri-heart-pulse-line" style={{ fontSize: '48px', color: '#cbd5e1' }}></i>
            <p style={{ color: '#64748b', marginTop: '8px', marginBottom: 0 }}>Nessuna patologia nutrizionale registrata</p>
          </div>
        ),
        <>
          <button className="cl-modal-btn-reset" onClick={() => setShowPatologieModal(false)}>
            <i className="ri-close-line"></i> Chiudi
          </button>
          {selectedCliente && (
            <Link
              to={`/clienti-dettaglio/${selectedCliente.cliente_id || selectedCliente.clienteId}#nutrizione`}
              className="cl-modal-btn-apply"
              style={{ textDecoration: 'none' }}
            >
              <i className="ri-external-link-line"></i> Modifica
            </Link>
          )}
        </>
      )}
    </div>
  );
}

export default ClientiListaNutrizione;

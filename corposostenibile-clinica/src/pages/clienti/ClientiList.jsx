import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import clientiService, {
  STATO_LABELS,
} from '../../services/clientiService';
import teamService from '../../services/teamService';
import GuidedTour from '../../components/GuidedTour';
import SupportWidget from '../../components/SupportWidget';
import ClientiFilters from './ClientiFilters';
import { FaUserFriends, FaChartBar, FaFilter, FaTable, FaEye, FaArrowRight } from 'react-icons/fa';
import { useAuth } from '../../context/AuthContext';
import { isProfessionistaStandard } from '../../utils/rbacScope';
import './ClientiList.css';

// Colori ruoli per avatar
const ROLE_COLORS = {
  hm: { bg: '#f3e8ff', text: '#9333ea', badge: '#9333ea' },
  n: { bg: '#dcfce7', text: '#16a34a', badge: '#22c55e' },
  c: { bg: '#dbeafe', text: '#2563eb', badge: '#3b82f6' },
  p: { bg: '#fce7f3', text: '#db2777', badge: '#ec4899' },
  ca: { bg: '#fef3c7', text: '#d97706', badge: '#f59e0b' },
};

// Icone e colori per le stat cards
const STAT_ICON_STYLES = {
  tot:        { bg: 'rgba(37, 179, 106, 0.1)', color: '#25B36A' },
  nutrizione: { bg: 'rgba(34, 197, 94, 0.1)',  color: '#22c55e' },
  coach:      { bg: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6' },
  psicologia: { bg: 'rgba(139, 92, 246, 0.1)', color: '#8b5cf6' },
  attivo:     { bg: 'rgba(34, 197, 94, 0.1)',  color: '#22c55e' },
  ghost:      { bg: 'rgba(100, 116, 139, 0.1)', color: '#64748b' },
  pausa:      { bg: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b' },
  stop:       { bg: 'rgba(239, 68, 68, 0.1)',  color: '#ef4444' },
};

function ClientiList() {
  const { user } = useAuth();
  const isAdminOrCco = Boolean(user?.is_admin || user?.role === 'admin' || user?.specialty === 'cco');
  const isTeamLeaderRestricted = Boolean(user?.role === 'team_leader' && !isAdminOrCco);
  const isProfessionista = isProfessionistaStandard(user);
  const isInfluencer = user?.role === 'influencer';
  const teamLeaderSpecialtyGroup = (() => {
    const s = String(user?.specialty || '').toLowerCase();
    if (s === 'nutrizione' || s === 'nutrizionista') return 'nutrizione';
    if (s === 'coach') return 'coach';
    if (s === 'psicologia' || s === 'psicologo') return 'psicologia';
    return null;
  })();

  // Determine specialty view for professionals and team leaders
  const professionistaView = (() => {
    if (!isProfessionista && !isTeamLeaderRestricted) return null;
    return teamLeaderSpecialtyGroup; // 'nutrizione' | 'coach' | 'psicologia' | null
  })();

  const [searchParams, setSearchParams] = useSearchParams();
  const [clienti, setClienti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [specialtyKpi, setSpecialtyKpi] = useState(null);
  const [professionisti, setProfessionisti] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 25,
    total: 0,
    totalPages: 0,
  });

  const [mostraTour, setMostraTour] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    if (searchParams.get('startTour') === 'true') {
      setMostraTour(true);
    }
  }, [searchParams]);

  const tourSteps = [
    {
      target: '[data-tour="header"]',
      title: 'Benvenuto in Lista Pazienti',
      content: 'Questa è la tua centrale operativa per la gestione dei pazienti. Da qui puoi monitorare lo stato di tutti i percorsi in corso.',
      placement: 'bottom',
      icon: <FaUserFriends size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)'
    },
    {
      target: '[data-tour="stats"]',
      title: 'Statistiche Rapide',
      content: 'Questi numeri ti danno un\'istantanea della situazione clinica attuale, suddivisa per specialità.',
      placement: 'bottom',
      icon: <FaChartBar size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
      tip: 'I numeri si aggiornano automaticamente in base ai filtri che applichi.'
    },
    {
      target: '[data-tour="filters"]',
      title: 'Ricerca e Filtri',
      content: 'Usa la barra di ricerca per trovare un paziente specifico o filtra la lista per stato, tipologia o professionista assegnato.',
      placement: 'bottom',
      icon: <FaFilter size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
      tip: 'Premi Reset per tornare alla visualizzazione completa.'
    },
    {
      target: '[data-tour="table"]',
      title: 'Tabella Pazienti',
      content: 'Ogni riga rappresenta un paziente. Qui vedi a colpo d\'occhio il team assegnato, le date chiave e lo stato attuale.',
      placement: 'top',
      icon: <FaTable size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #3B82F6, #60A5FA)'
    },
    {
      target: '[data-tour="actions-detail"]',
      title: 'Gestione Paziente',
      content: 'Clicca sul nome del paziente o sull\'icona dell\'occhio per aprire la scheda dettaglio completa e gestire il percorso.',
      placement: 'left',
      icon: <FaEye size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #8B5CF6, #D946EF)',
      tip: 'Puoi anche cliccare sulla matita per entrare direttamente in modalità modifica.'
    },
    {
      target: '[data-tour="pagination"]',
      title: 'Navigazione',
      content: 'Se hai molti pazienti, usa la paginazione per scorrere tra le diverse pagine dei risultati.',
      placement: 'top',
      icon: <FaArrowRight size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #6B7280, #9CA3AF)'
    }
  ];

  const [filters, setFilters] = useState({
    search: searchParams.get('q') || '',
    stato: searchParams.get('stato') || '',
    tipologia: searchParams.get('tipologia') || '',
    nutrizionista: searchParams.get('nutrizionista') || '',
    coach: searchParams.get('coach') || '',
    psicologa: searchParams.get('psicologa') || '',
    check_day: searchParams.get('check_day') || '',
    reach_out: searchParams.get('reach_out') || '',
    trasformazione_fisica: searchParams.get('trasformazione_fisica') || '',
    trasformazione_fisica_condivisa: searchParams.get('trasformazione_fisica_condivisa') || '',
    allenamento_dal_from: searchParams.get('allenamento_dal_from') || '',
    allenamento_dal_to: searchParams.get('allenamento_dal_to') || '',
    nuovo_allenamento_il_from: searchParams.get('nuovo_allenamento_il_from') || '',
    nuovo_allenamento_il_to: searchParams.get('nuovo_allenamento_il_to') || '',
    marketing_usabile: searchParams.get('marketing_usabile') || '',
    marketing_stories: searchParams.get('marketing_stories') || '',
    marketing_carosello: searchParams.get('marketing_carosello') || '',
    marketing_videofeedback: searchParams.get('marketing_videofeedback') || '',
    missing_check_day: searchParams.get('missing_check_day') || '',
    missing_check_saltati: searchParams.get('missing_check_saltati') || '',
    missing_reach_out: searchParams.get('missing_reach_out') || '',
    missing_stato_nutrizione: searchParams.get('missing_stato_nutrizione') || '',
    missing_stato_chat_nutrizione: searchParams.get('missing_stato_chat_nutrizione') || '',
    missing_stato_coach: searchParams.get('missing_stato_coach') || '',
    missing_stato_chat_coaching: searchParams.get('missing_stato_chat_coaching') || '',
    missing_stato_psicologia: searchParams.get('missing_stato_psicologia') || '',
    missing_stato_chat_psicologia: searchParams.get('missing_stato_chat_psicologia') || '',
    missing_piano_dieta: searchParams.get('missing_piano_dieta') || '',
    missing_piano_allenamento: searchParams.get('missing_piano_allenamento') || '',
  });

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        if (isProfessionista) {
          setStats(null);
          setProfessionisti([]);
          return;
        }
        const [statsData, profData] = await Promise.all([
          clientiService.getStats(),
          teamService.getTeamMembers({ per_page: 100, active: '1' }),
        ]);
        setStats(statsData);
        setProfessionisti(profData.members || []);
      } catch (err) {
        console.error('Error fetching initial data:', err);
      }
    };
    fetchInitialData();
  }, [isProfessionista]);

  useEffect(() => {
    if (!isTeamLeaderRestricted || !teamLeaderSpecialtyGroup) return;
    const next = {};
    if (teamLeaderSpecialtyGroup !== 'nutrizione' && filters.nutrizionista) next.nutrizionista = '';
    if (teamLeaderSpecialtyGroup !== 'coach' && filters.coach) next.coach = '';
    if (teamLeaderSpecialtyGroup !== 'psicologia' && filters.psicologa) next.psicologa = '';
    if (Object.keys(next).length > 0) {
      setFilters((prev) => ({ ...prev, ...next }));
    }
  }, [isTeamLeaderRestricted, teamLeaderSpecialtyGroup, filters.nutrizionista, filters.coach, filters.psicologa]);

  const fetchClienti = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page: pagination.page,
        per_page: pagination.perPage,
        q: filters.search || undefined,
        stato_cliente: filters.stato || undefined,
        tipologia: filters.tipologia || undefined,
        nutrizionista_id: filters.nutrizionista || undefined,
        coach_id: filters.coach || undefined,
        psicologa_id: filters.psicologa || undefined,
        check_day: filters.check_day || undefined,
        reach_out: filters.reach_out || undefined,
        trasformazione_fisica: filters.trasformazione_fisica || undefined,
        trasformazione_fisica_condivisa: filters.trasformazione_fisica_condivisa || undefined,
        allenamento_dal_from: filters.allenamento_dal_from || undefined,
        allenamento_dal_to: filters.allenamento_dal_to || undefined,
        nuovo_allenamento_il_from: filters.nuovo_allenamento_il_from || undefined,
        nuovo_allenamento_il_to: filters.nuovo_allenamento_il_to || undefined,
        marketing_usabile: filters.marketing_usabile || undefined,
        marketing_stories: filters.marketing_stories || undefined,
        marketing_carosello: filters.marketing_carosello || undefined,
        marketing_videofeedback: filters.marketing_videofeedback || undefined,
        missing_check_day: filters.missing_check_day || undefined,
        missing_check_saltati: filters.missing_check_saltati || undefined,
        missing_reach_out: filters.missing_reach_out || undefined,
        missing_stato_nutrizione: filters.missing_stato_nutrizione || undefined,
        missing_stato_chat_nutrizione: filters.missing_stato_chat_nutrizione || undefined,
        missing_stato_coach: filters.missing_stato_coach || undefined,
        missing_stato_chat_coaching: filters.missing_stato_chat_coaching || undefined,
        missing_stato_psicologia: filters.missing_stato_psicologia || undefined,
        missing_stato_chat_psicologia: filters.missing_stato_chat_psicologia || undefined,
        missing_piano_dieta: filters.missing_piano_dieta || undefined,
        missing_piano_allenamento: filters.missing_piano_allenamento || undefined,
      };

      // For professionals/TL with a specialty, pass view param so backend returns KPI aggregates
      if (professionistaView) {
        params.view = professionistaView;
      }

      const data = await clientiService.getClienti(params);
      setClienti(data.data || []);
      setPagination(prev => ({
        ...prev,
        total: data.pagination?.total || 0,
        totalPages: data.pagination?.pages || 0,
      }));

      // Use backend KPI aggregates for specialty views
      if (data.kpi) {
        setSpecialtyKpi(data.kpi);
      }
    } catch (err) {
      console.error('Error fetching clienti:', err);
      setError('Errore nel caricamento dei clienti');
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.perPage, filters, professionistaView]);

  useEffect(() => {
    fetchClienti();
  }, [fetchClienti]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 }));
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key === 'search' ? 'q' : key, value);
    } else {
      newParams.delete(key === 'search' ? 'q' : key);
    }
    setSearchParams(newParams);
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, page: newPage }));
  };

  const resetFilters = () => {
    setFilters({
      search: '', stato: '', tipologia: '', nutrizionista: '', coach: '', psicologa: '',
      check_day: '', reach_out: '', trasformazione_fisica: '', trasformazione_fisica_condivisa: '',
      allenamento_dal_from: '', allenamento_dal_to: '', nuovo_allenamento_il_from: '', nuovo_allenamento_il_to: '',
      marketing_usabile: '', marketing_stories: '', marketing_carosello: '', marketing_videofeedback: '',
      missing_check_day: '', missing_check_saltati: '', missing_reach_out: '',
      missing_stato_nutrizione: '', missing_stato_chat_nutrizione: '',
      missing_stato_coach: '', missing_stato_chat_coaching: '',
      missing_stato_psicologia: '', missing_stato_chat_psicologia: '',
      missing_piano_dieta: '', missing_piano_allenamento: ''
    });
    setSearchParams(new URLSearchParams());
  };

  const visibleProfessionalFilters = {
    nutrizione: !isProfessionista && (!isTeamLeaderRestricted || teamLeaderSpecialtyGroup === 'nutrizione'),
    coach: !isProfessionista && (!isTeamLeaderRestricted || teamLeaderSpecialtyGroup === 'coach'),
    psicologia: !isProfessionista && (!isTeamLeaderRestricted || teamLeaderSpecialtyGroup === 'psicologia'),
  };

  const visualButtons = [
    { key: 'generale', to: '/clienti-lista', label: 'Lista Generale', icon: 'ri-list-check' },
    { key: 'nutrizione', to: '/clienti-nutrizione', label: 'Visuale Nutrizione', icon: 'ri-restaurant-line' },
    { key: 'coach', to: '/clienti-coach', label: 'Visuale Coach', icon: 'ri-run-line' },
    { key: 'psicologia', to: '/clienti-psicologia', label: 'Visuale Psicologia', icon: 'ri-mental-health-line' },
  ].filter((btn) => {
    if (isInfluencer) return btn.key === 'generale';
    if (isProfessionista) return btn.key === 'generale' || btn.key === teamLeaderSpecialtyGroup;
    if (!isTeamLeaderRestricted) return true;
    if (btn.key === 'generale') return true;
    return btn.key === teamLeaderSpecialtyGroup;
  });

  // Build stat cards: professionals/TL with specialty see attivo/ghost/pausa/stop from backend KPI
  // Influencers don't see KPI cards
  const statCards = (() => {
    if (isInfluencer) return [];
    if (professionistaView && specialtyKpi) {
      return [
        { key: 'tot', label: 'Pazienti Totali', value: pagination.total, icon: 'ri-group-line' },
        { key: 'attivo', label: 'Stato Attivo', value: specialtyKpi.stato_attivo, icon: 'ri-run-line' },
        { key: 'ghost', label: 'Stato Ghost', value: specialtyKpi.stato_ghost, icon: 'ri-ghost-line' },
        { key: 'pausa', label: 'Stato Pausa', value: specialtyKpi.stato_pausa, icon: 'ri-pause-circle-line' },
        { key: 'stop', label: 'Stato Stop', value: specialtyKpi.stato_stop, icon: 'ri-stop-circle-line' },
      ];
    }
    return [
      { key: 'tot', label: 'Pazienti Totali', value: stats?.total_clienti || pagination.total, icon: 'ri-group-line' },
      { key: 'nutrizione', label: 'Nutrizionista Attivo', value: stats?.nutrizione_attivo || 0, icon: 'ri-restaurant-line' },
      { key: 'coach', label: 'Coach Attivo', value: stats?.coach_attivo || 0, icon: 'ri-run-line' },
      { key: 'psicologia', label: 'Psicologo Attivo', value: stats?.psicologia_attivo || 0, icon: 'ri-mental-health-line' },
    ].filter((stat) => {
      if (!isTeamLeaderRestricted) return true;
      if (stat.key === 'tot') return true;
      return stat.key === teamLeaderSpecialtyGroup;
    });
  })();

  const formatDate = (dateStr) => {
    if (!dateStr) return null;
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const renderTeamAvatar = (member, roleKey, roleLabel) => {
    if (!member) return null;
    const colors = ROLE_COLORS[roleKey] || ROLE_COLORS.n;
    const initials = `${member.first_name?.[0] || ''}${member.last_name?.[0] || ''}`;

    return (
      <span
        key={`${roleKey}-${member.id}`}
        className="cl-avatar-wrap"
        title={`${roleLabel}: ${member.full_name || `${member.first_name} ${member.last_name}`}`}
      >
        {member.avatar_url || member.avatar_path ? (
          <img
            src={member.avatar_url || member.avatar_path}
            alt={member.full_name}
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

  // Count active filters (excluding search)
  const activeFilterCount = Object.entries(filters)
    .filter(([key, val]) => key !== 'search' && val && val !== '' && val !== '0')
    .length;

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

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="cl-header" data-tour="header">
        <div>
          <h4>Gestione Pazienti</h4>
          <p className="cl-header-sub">{pagination.total} pazienti totali</p>
        </div>
        <div className="cl-view-pills">
          {visualButtons.map((btn) => (
            <Link
              key={btn.key}
              to={btn.to}
              className={`cl-view-pill${btn.key === 'generale' ? ' active' : ''}`}
            >
              <i className={btn.icon}></i> {btn.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Stats Row */}
      {statCards.length > 0 && (
        <div className="cl-stats-row" data-tour="stats">
          {statCards.map((stat) => {
            const iconStyle = STAT_ICON_STYLES[stat.key] || STAT_ICON_STYLES.tot;
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
      )}

      {/* Search Bar + Filter Button */}
      <div className="cl-search-row" data-tour="filters">
        <div className="cl-search-wrap">
          <i className="ri-search-line cl-search-icon"></i>
          <input
            type="text"
            className="cl-search-input"
            placeholder="Cerca paziente per nome, email, telefono..."
            value={filters.search || ''}
            onChange={(e) => handleFilterChange('search', e.target.value)}
          />
        </div>
        <button className="cl-filter-open-btn" onClick={() => setShowFilters(true)}>
          <i className="ri-filter-3-line"></i>
          Filtra
          {activeFilterCount > 0 && (
            <span className="cl-filter-badge">{activeFilterCount}</span>
          )}
        </button>
      </div>

      {/* Filters Modal */}
      <ClientiFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={resetFilters}
        professionisti={professionisti}
        visibleProfessionalFilters={visibleProfessionalFilters}
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
            <i className="ri-user-search-line"></i>
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
          <div className="cl-table-card" data-tour="table">
            <div className="table-responsive">
              <table className="cl-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '200px' }}>Nome Cognome</th>
                    <th style={{ minWidth: '120px' }}>Team</th>
                    <th style={{ minWidth: '120px' }}>Data Inizio</th>
                    <th style={{ minWidth: '120px' }}>Data Rinnovo</th>
                    <th style={{ minWidth: '140px' }}>Programma</th>
                    <th style={{ minWidth: '130px' }}>Stato</th>
                    <th style={{ textAlign: 'right', minWidth: '120px' }}>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {clienti.map((cliente, index) => {
                    const clienteId = cliente.cliente_id || cliente.clienteId;
                    const nomeCognome = cliente.nome_cognome || cliente.nomeCognome || 'N/D';
                    const dataInizio = cliente.data_inizio_abbonamento || cliente.dataInizioAbbonamento;
                    const dataRinnovo = cliente.data_rinnovo || cliente.dataRinnovo;
                    const programma = cliente.programma_attuale || cliente.programmaAttuale || cliente.storico_programma || cliente.storicoProgramma;
                    const statoCliente = cliente.stato_cliente || cliente.statoCliente;

                    const healthManager = cliente.health_manager_user || cliente.healthManagerUser;
                    const nutrizionistiList = cliente.nutrizionisti_multipli || cliente.nutrizionistiMultipli || [];
                    const coachesList = cliente.coaches_multipli || cliente.coachesMultipli || [];
                    const psicologiList = cliente.psicologi_multipli || cliente.psicologiMultipli || [];
                    const consulentiList = cliente.consulenti_multipli || cliente.consulentiMultipli || [];

                    const hasTeam = healthManager || nutrizionistiList.length > 0 || coachesList.length > 0 || psicologiList.length > 0 || consulentiList.length > 0;

                    return (
                      <tr key={clienteId}>
                        <td>
                          <Link to={`/clienti-dettaglio/${clienteId}`} className="cl-name-link">
                            {nomeCognome}
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
                          {dataInizio ? (
                            <span style={{ fontWeight: 500 }}>{formatDate(dataInizio)}</span>
                          ) : (
                            <span className="cl-empty">&mdash;</span>
                          )}
                        </td>

                        <td>
                          {dataRinnovo ? (
                            <span style={{ fontWeight: 500 }}>{formatDate(dataRinnovo)}</span>
                          ) : (
                            <span className="cl-empty">&mdash;</span>
                          )}
                        </td>

                        <td>
                          {programma ? (
                            <span className="cl-badge cl-badge-programma">{programma}</span>
                          ) : (
                            <span className="cl-empty">&mdash;</span>
                          )}
                        </td>

                        <td>
                          {statoCliente ? (
                            <span className={`cl-badge cl-badge-stato-${statoCliente}`}>
                              {STATO_LABELS[statoCliente] || statoCliente}
                            </span>
                          ) : (
                            <span className="cl-empty">&mdash;</span>
                          )}
                        </td>

                        <td style={{ textAlign: 'right' }} data-tour={index === 0 ? "actions-detail" : undefined}>
                          <Link to={`/clienti-dettaglio/${clienteId}`} className="cl-action-btn" title="Dettaglio">
                            <i className="ri-eye-line"></i>
                          </Link>
                          {!isProfessionista && (
                            <Link to={`/clienti-modifica/${clienteId}`} className="cl-action-btn" title="Modifica">
                              <i className="ri-edit-line"></i>
                            </Link>
                          )}
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
            <div className="cl-pagination" data-tour="pagination">
              <span className="cl-pagination-info">
                Pagina <strong>{pagination.page}</strong> di <strong>{pagination.totalPages}</strong>
                {' '}&bull; {pagination.total} risultati
              </span>
              <div className="cl-pagination-buttons">
                <button
                  className="cl-page-btn"
                  onClick={() => handlePageChange(1)}
                  disabled={pagination.page === 1}
                  title="Prima pagina"
                >
                  &laquo;
                </button>
                <button
                  className="cl-page-btn"
                  onClick={() => handlePageChange(pagination.page - 1)}
                  disabled={pagination.page === 1}
                  title="Precedente"
                >
                  &lsaquo;
                </button>
                {getPageNumbers().map((pageNum) => (
                  <button
                    key={pageNum}
                    className={`cl-page-btn${pagination.page === pageNum ? ' active' : ''}`}
                    onClick={() => handlePageChange(pageNum)}
                  >
                    {pageNum}
                  </button>
                ))}
                <button
                  className="cl-page-btn"
                  onClick={() => handlePageChange(pagination.page + 1)}
                  disabled={pagination.page === pagination.totalPages}
                  title="Successiva"
                >
                  &rsaquo;
                </button>
                <button
                  className="cl-page-btn"
                  onClick={() => handlePageChange(pagination.totalPages)}
                  disabled={pagination.page === pagination.totalPages}
                  title="Ultima pagina"
                >
                  &raquo;
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Support and Tour Components */}
      <SupportWidget
        pageTitle="Lista Pazienti"
        pageDescription="In questa pagina puoi gestire tutti i pazienti, filtrare per stato e specialità, e accedere alle schede dettaglio."
        pageIcon={FaUserFriends}
        docsSection="lista-pazienti"
        onStartTour={() => setMostraTour(true)}
        brandName="Suite Clinica"
        logoSrc="/suitemind.png"
        accentColor="#85FF00"
      />

      <GuidedTour
        steps={tourSteps}
        isOpen={mostraTour}
        onClose={() => setMostraTour(false)}
        onComplete={() => {
          setMostraTour(false);
          console.log('Tour Lista Pazienti completato');
        }}
      />
    </div>
  );
}

export default ClientiList;

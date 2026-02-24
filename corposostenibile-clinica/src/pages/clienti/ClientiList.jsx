import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import clientiService, {
  STATO_LABELS,
  STATO_COLORS,
  TIPOLOGIA_LABELS,
} from '../../services/clientiService';
import teamService from '../../services/teamService';
import GuidedTour from '../../components/GuidedTour';
import SupportWidget from '../../components/SupportWidget';
import ClientiFilters from './ClientiFilters';
import { FaUserFriends, FaChartBar, FaFilter, FaTable, FaEye, FaArrowRight } from 'react-icons/fa';
import './clienti-responsive.css';
import './clienti-table.css';

// Stili per la tabella professionale
// tableStyles rimosso — ora in clienti-table.css (classi ct-*)

// Colori per i badge di stato
const STATO_BADGE_STYLES = {
  attivo: { background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff' },
  ghost: { background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)', color: '#fff' },
  pausa: { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: '#fff' },
  stop: { background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', color: '#fff' },
  insoluto: { background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)', color: '#fff' },
  freeze: { background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)', color: '#fff' },
};

// Colori ruoli per avatar
const ROLE_COLORS = {
  hm: { bg: '#f3e8ff', text: '#9333ea', badge: '#9333ea' },
  n: { bg: '#dcfce7', text: '#16a34a', badge: '#22c55e' },
  c: { bg: '#dbeafe', text: '#2563eb', badge: '#3b82f6' },
  p: { bg: '#fce7f3', text: '#db2777', badge: '#ec4899' },
  ca: { bg: '#fef3c7', text: '#d97706', badge: '#f59e0b' },
};

function ClientiList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [clienti, setClienti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [professionisti, setProfessionisti] = useState([]);
  const [hoveredRow, setHoveredRow] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 25,
    total: 0,
    totalPages: 0,
  });

  const [mostraTour, setMostraTour] = useState(false);

  // Effetto per avvio automatico tour da Hub Supporto
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
    // Advanced Filters
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

  // Fetch stats and professionisti on mount
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
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
  }, []);

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
        // Advanced
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

      const data = await clientiService.getClienti(params);
      setClienti(data.data || []);
      setPagination(prev => ({
        ...prev,
        total: data.pagination?.total || 0,
        totalPages: data.pagination?.pages || 0,
      }));
    } catch (err) {
      console.error('Error fetching clienti:', err);
      setError('Errore nel caricamento dei clienti');
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.perPage, filters]);

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
    const colors = ROLE_COLORS[roleKey] || ROLE_COLORS.n;
    const initials = `${member.first_name?.[0] || ''}${member.last_name?.[0] || ''}`;

    return (
      <span
        key={`${roleKey}-${member.id}`}
        className="ct-avatar-team"
        title={`${roleLabel}: ${member.full_name || `${member.first_name} ${member.last_name}`}`}
      >
        {member.avatar_url || member.avatar_path ? (
          <img
            src={member.avatar_url || member.avatar_path}
            alt={member.full_name}
            className="ct-avatar-init"
            style={{ objectFit: 'cover' }}
          />
        ) : (
          <span
            className="ct-avatar-init"
            style={{ background: colors.bg, color: colors.text }}
          >
            {initials}
          </span>
        )}
        <span className="ct-avatar-badge" style={{ background: colors.badge }}>
          {roleKey.toUpperCase()}
        </span>
      </span>
    );
  };

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4 page-title-block" data-tour="header">
        <div>
          <h4 className="mb-1">Gestione Pazienti</h4>
          <p className="text-muted mb-0">{pagination.total} pazienti totali</p>
        </div>
        <div className="d-flex gap-2 flex-wrap clienti-header-actions">
          <Link to="/clienti-lista" className="btn btn-primary btn-sm">
            <i className="ri-list-check me-1"></i> Lista Generale
          </Link>
          <Link to="/clienti-nutrizione" className="btn btn-warning btn-sm text-white">
            <i className="ri-restaurant-line me-1"></i> Visuale Nutrizione
          </Link>
          <Link to="/clienti-coach" className="btn btn-info btn-sm text-white">
            <i className="ri-run-line me-1"></i> Visuale Coach
          </Link>
          <Link to="/clienti-psicologia" className="btn btn-danger btn-sm text-white">
            <i className="ri-mental-health-line me-1"></i> Visuale Psicologia
          </Link>
        </div>
      </div>

      {/* Stats Row */}
      <div className="mobile-swipe-indicator mb-2 d-md-none text-muted small text-center">
        <i className="ri-arrow-left-right-line me-1"></i> Scorri per vedere le altre statistiche
      </div>
      <div className="row g-3 mb-4 clienti-stats-row mobile-kpi-scroll" data-tour="stats">
        {[
          { label: 'Pazienti Totali', value: stats?.total_clienti || pagination.total, icon: 'ri-group-line', bg: 'primary' },
          { label: 'Nutrizionista Attivo', value: stats?.nutrizione_attivo || 0, icon: 'ri-restaurant-line', bg: 'success' },
          { label: 'Coach Attivo', value: stats?.coach_attivo || 0, icon: 'ri-run-line', bg: 'warning' },
          { label: 'Psicologo Attivo', value: stats?.psicologia_attivo || 0, icon: 'ri-mental-health-line', customBg: '#8b5cf6' },
        ].map((stat, idx) => (
          <div key={idx} className="col-xl-3 col-sm-6">
            <div
              className={`card border-0 shadow-sm ${stat.bg ? `bg-${stat.bg}` : ''}`}
              style={stat.customBg ? { backgroundColor: stat.customBg } : {}}
            >
              <div className="card-body py-3">
                <div className="d-flex align-items-center justify-content-between">
                  <div>
                    <h3 className="text-white mb-0 fw-bold">{stat.value}</h3>
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

      {/* Filters */}
      <ClientiFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={resetFilters}
        professionisti={professionisti}
      />

      {/* Content */}
      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}></div>
          <p className="mt-3 text-muted">Caricamento pazienti...</p>
        </div>
      ) : error ? (
        <div className="alert alert-danger" style={{ borderRadius: '12px' }}>{error}</div>
      ) : clienti.length === 0 ? (
        <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
          <div className="card-body text-center py-5">
            <div className="mb-4">
              <i className="ri-user-search-line" style={{ fontSize: '5rem', color: '#cbd5e1' }}></i>
            </div>
            <h5 style={{ color: '#475569' }}>Nessun paziente trovato</h5>
            <p className="text-muted mb-4">Prova a modificare i filtri di ricerca</p>
            <button
              className="btn btn-primary"
              onClick={resetFilters}
              style={{ borderRadius: '10px', padding: '10px 24px' }}
            >
              <i className="ri-refresh-line me-2"></i>Reset Filtri
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Tabella Pazienti */}
          <div className="card border-0 clienti-table-wrap ct-card" data-tour="table">
            <div className="table-responsive">
              <table className="table mb-0 clienti-table">
                <thead className="ct-thead">
                  <tr>
                    <th className="ct-th" style={{ minWidth: '200px' }}>Nome Cognome</th>
                    <th className="ct-th" style={{ minWidth: '120px' }}>Team</th>
                    <th className="ct-th" style={{ minWidth: '120px' }}>Data Inizio</th>
                    <th className="ct-th" style={{ minWidth: '120px' }}>Data Rinnovo</th>
                    <th className="ct-th" style={{ minWidth: '140px' }}>Programma</th>
                    <th className="ct-th" style={{ minWidth: '130px' }}>Stato</th>
                    <th className="ct-th" style={{ textAlign: 'right', minWidth: '120px' }}>Azioni</th>
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
                        className="ct-row"
                        style={{ background: isHovered ? '#f8fafc' : 'transparent' }}
                        onMouseEnter={() => setHoveredRow(index)}
                        onMouseLeave={() => setHoveredRow(null)}
                      >
                        {/* Nome Cognome */}
                        <td className="ct-td" data-label="Paziente">
                          <Link
                            to={`/clienti-dettaglio/${clienteId}`}
                            className="ct-name-link"
                          >
                            {nomeCognome}
                          </Link>
                        </td>

                        {/* Team */}
                        <td className="ct-td" data-label="Team">
                          <div className="d-flex align-items-center flex-wrap">
                            {healthManager && renderTeamAvatar(healthManager, 'hm', 'Health Manager')}
                            {nutrizionistiList.map(n => renderTeamAvatar(n, 'n', 'Nutrizionista'))}
                            {coachesList.map(c => renderTeamAvatar(c, 'c', 'Coach'))}
                            {psicologiList.map(p => renderTeamAvatar(p, 'p', 'Psicologo'))}
                            {consulentiList.map(ca => renderTeamAvatar(ca, 'ca', 'Consulente'))}
                            {!hasTeam && <span className="ct-empty">—</span>}
                          </div>
                        </td>

                        {/* Data Inizio */}
                        <td className="ct-td" data-label="Inizio">
                          {dataInizio ? (
                            <span style={{ fontWeight: 500 }}>{formatDate(dataInizio)}</span>
                          ) : (
                            <span className="ct-empty">—</span>
                          )}
                        </td>

                        {/* Data Rinnovo */}
                        <td className="ct-td" data-label="Rinnovo">
                          {dataRinnovo ? (
                            <span style={{ fontWeight: 500 }}>{formatDate(dataRinnovo)}</span>
                          ) : (
                            <span className="ct-empty">—</span>
                          )}
                        </td>

                        {/* Programma */}
                        <td className="ct-td" data-label="Programma">
                          {programma ? (
                            <span
                              className="ct-badge"
                              style={{
                                background: 'linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)',
                                color: '#0369a1',
                              }}
                            >
                              {programma}
                            </span>
                          ) : (
                            <span className="ct-empty">—</span>
                          )}
                        </td>

                        {/* Stato Cliente */}
                        <td className="ct-td" data-label="Stato">
                          {statoCliente ? (
                            <span
                              className="ct-badge"
                              style={STATO_BADGE_STYLES[statoCliente] || { background: '#94a3b8', color: '#fff' }}
                            >
                              {STATO_LABELS[statoCliente] || statoCliente}
                            </span>
                          ) : (
                            <span className="ct-empty">—</span>
                          )}
                        </td>

                        {/* Azioni */}
                        <td className="ct-td" style={{ textAlign: 'right' }} data-label="Azioni" data-tour={index === 0 ? "actions-detail" : undefined}>
                          <Link
                            to={`/clienti-dettaglio/${clienteId}`}
                            className="ct-action-btn"
                            style={{
                              borderColor: '#22c55e',
                              color: '#22c55e',
                              background: isHovered ? 'rgba(34, 197, 94, 0.1)' : 'transparent',
                            }}
                            title="Dettaglio"
                          >
                            <i className="ri-eye-line" style={{ fontSize: '16px' }}></i>
                          </Link>
                          <Link
                            to={`/clienti-modifica/${clienteId}`}
                            className="ct-action-btn"
                            style={{
                              borderColor: '#3b82f6',
                              color: '#3b82f6',
                              background: isHovered ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                            }}
                            title="Modifica"
                          >
                            <i className="ri-edit-line" style={{ fontSize: '16px' }}></i>
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
            <div
              className="d-flex flex-wrap justify-content-between align-items-center mt-4 pt-3 gap-3 clienti-pagination"
              data-tour="pagination"
            >
              <span style={{ color: '#64748b', fontSize: '14px' }}>
                Pagina <strong style={{ color: '#334155' }}>{pagination.page}</strong> di{' '}
                <strong style={{ color: '#334155' }}>{pagination.totalPages}</strong>
                <span className="ms-2" style={{ color: '#94a3b8' }}>•</span>
                <span className="ms-2">{pagination.total} risultati</span>
              </span>
              <nav>
                <ul className="pagination mb-0" style={{ gap: '4px' }}>
                  {/* First */}
                  <li className={`page-item ${pagination.page === 1 ? 'disabled' : ''}`}>
                    <button
                      className="page-link"
                      onClick={() => handlePageChange(1)}
                      disabled={pagination.page === 1}
                      style={{
                        borderRadius: '8px',
                        border: '1px solid #e2e8f0',
                        color: pagination.page === 1 ? '#cbd5e1' : '#64748b',
                        padding: '8px 12px',
                      }}
                    >
                      <i className="ri-arrow-left-double-line"></i>
                    </button>
                  </li>
                  {/* Prev */}
                  <li className={`page-item ${pagination.page === 1 ? 'disabled' : ''}`}>
                    <button
                      className="page-link"
                      onClick={() => handlePageChange(pagination.page - 1)}
                      disabled={pagination.page === 1}
                      style={{
                        borderRadius: '8px',
                        border: '1px solid #e2e8f0',
                        color: pagination.page === 1 ? '#cbd5e1' : '#64748b',
                        padding: '8px 12px',
                      }}
                    >
                      <i className="ri-arrow-left-s-line"></i>
                    </button>
                  </li>
                  {/* Page numbers */}
                  {[...Array(Math.min(pagination.totalPages, 5))].map((_, i) => {
                    let pageNum;
                    if (pagination.totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (pagination.page <= 3) {
                      pageNum = i + 1;
                    } else if (pagination.page >= pagination.totalPages - 2) {
                      pageNum = pagination.totalPages - 4 + i;
                    } else {
                      pageNum = pagination.page - 2 + i;
                    }
                    const isActive = pagination.page === pageNum;
                    return (
                      <li key={pageNum} className="page-item">
                        <button
                          className="page-link"
                          onClick={() => handlePageChange(pageNum)}
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
                  <li className={`page-item ${pagination.page === pagination.totalPages ? 'disabled' : ''}`}>
                    <button
                      className="page-link"
                      onClick={() => handlePageChange(pagination.page + 1)}
                      disabled={pagination.page === pagination.totalPages}
                      style={{
                        borderRadius: '8px',
                        border: '1px solid #e2e8f0',
                        color: pagination.page === pagination.totalPages ? '#cbd5e1' : '#64748b',
                        padding: '8px 12px',
                      }}
                    >
                      <i className="ri-arrow-right-s-line"></i>
                    </button>
                  </li>
                  {/* Last */}
                  <li className={`page-item ${pagination.page === pagination.totalPages ? 'disabled' : ''}`}>
                    <button
                      className="page-link"
                      onClick={() => handlePageChange(pagination.totalPages)}
                      disabled={pagination.page === pagination.totalPages}
                      style={{
                        borderRadius: '8px',
                        border: '1px solid #e2e8f0',
                        color: pagination.page === pagination.totalPages ? '#cbd5e1' : '#64748b',
                        padding: '8px 12px',
                      }}
                    >
                      <i className="ri-arrow-right-double-line"></i>
                    </button>
                  </li>
                </ul>
              </nav>
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

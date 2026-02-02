import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import clientiService, {
  STATO_LABELS,
  STATO_COLORS,
  TIPOLOGIA_LABELS,
} from '../../services/clientiService';
import teamService from '../../services/teamService';

// Stili per la tabella professionale
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
    width: '36px',
    height: '36px',
    padding: 0,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '8px',
    border: '1px solid',
    transition: 'all 0.15s ease',
    marginLeft: '6px',
  },
  avatarTeam: {
    position: 'relative',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    marginRight: '4px',
  },
  avatarInitials: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '10px',
    fontWeight: 700,
    textTransform: 'uppercase',
    border: '2px solid #fff',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  avatarBadge: {
    position: 'absolute',
    bottom: '-2px',
    right: '-2px',
    fontSize: '7px',
    fontWeight: 700,
    color: '#fff',
    padding: '2px 4px',
    borderRadius: '4px',
    lineHeight: 1,
    boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
  },
};

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

  const [filters, setFilters] = useState({
    search: searchParams.get('q') || '',
    stato: searchParams.get('stato') || '',
    tipologia: searchParams.get('tipologia') || '',
    nutrizionista: searchParams.get('nutrizionista') || '',
    coach: searchParams.get('coach') || '',
    psicologa: searchParams.get('psicologa') || '',
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
    setFilters({ search: '', stato: '', tipologia: '', nutrizionista: '', coach: '', psicologa: '' });
    setSearchParams(new URLSearchParams());
  };

  // Filter professionisti by role
  const nutrizionisti = professionisti.filter(p =>
    p.specialty === 'nutrizione' || p.specialty === 'nutrizionista'
  );
  const coaches = professionisti.filter(p => p.specialty === 'coach');
  const psicologi = professionisti.filter(p =>
    p.specialty === 'psicologia' || p.specialty === 'psicologo'
  );

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

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4">
        <div>
          <h4 className="mb-1">Gestione Pazienti</h4>
          <p className="text-muted mb-0">{pagination.total} pazienti totali</p>
        </div>
        <div className="d-flex gap-2">
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
      <div className="row g-3 mb-4">
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
      <div className="card shadow-sm border-0 mb-4">
        <div className="card-body py-3">
          <div className="row g-2 align-items-center">
            <div className="col-lg-3">
              <div className="position-relative">
                <i className="ri-search-line position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}></i>
                <input
                  type="text"
                  className="form-control bg-light border-0"
                  placeholder="Cerca paziente..."
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  style={{ paddingLeft: '36px' }}
                />
              </div>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.stato}
                onChange={(e) => handleFilterChange('stato', e.target.value)}
              >
                <option value="">Stato Cliente</option>
                {Object.entries(STATO_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.tipologia}
                onChange={(e) => handleFilterChange('tipologia', e.target.value)}
              >
                <option value="">Tipologia</option>
                {Object.entries(TIPOLOGIA_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.nutrizionista}
                onChange={(e) => handleFilterChange('nutrizionista', e.target.value)}
              >
                <option value="">Nutrizionista</option>
                {nutrizionisti.map(p => (
                  <option key={p.id} value={p.id}>{p.full_name}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.coach}
                onChange={(e) => handleFilterChange('coach', e.target.value)}
              >
                <option value="">Coach</option>
                {coaches.map(p => (
                  <option key={p.id} value={p.id}>{p.full_name}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-1">
              <button
                className="btn btn-outline-secondary w-100"
                onClick={resetFilters}
              >
                <i className="ri-refresh-line me-1"></i>Reset
              </button>
            </div>
          </div>
        </div>
      </div>

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
          <div className="card border-0" style={tableStyles.card}>
            <div className="table-responsive">
              <table className="table mb-0">
                <thead style={tableStyles.tableHeader}>
                  <tr>
                    <th style={{ ...tableStyles.th, minWidth: '200px' }}>Nome Cognome</th>
                    <th style={{ ...tableStyles.th, minWidth: '120px' }}>Team</th>
                    <th style={{ ...tableStyles.th, minWidth: '120px' }}>Data Inizio</th>
                    <th style={{ ...tableStyles.th, minWidth: '120px' }}>Data Rinnovo</th>
                    <th style={{ ...tableStyles.th, minWidth: '140px' }}>Programma</th>
                    <th style={{ ...tableStyles.th, minWidth: '130px' }}>Stato</th>
                    <th style={{ ...tableStyles.th, textAlign: 'right', minWidth: '120px' }}>Azioni</th>
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
                            <i className="ri-eye-line" style={{ fontSize: '16px' }}></i>
                          </Link>
                          <Link
                            to={`/clienti-modifica/${clienteId}`}
                            style={{
                              ...tableStyles.actionBtn,
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
              className="d-flex flex-wrap justify-content-between align-items-center mt-4 pt-3 gap-3"
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
    </div>
  );
}

export default ClientiList;

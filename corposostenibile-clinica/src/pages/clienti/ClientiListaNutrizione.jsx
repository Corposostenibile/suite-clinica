import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import clientiService, {
  GIORNI_LABELS,
  STATI_PROFESSIONISTA_COLORS,
  PATOLOGIE_NUTRI,
} from '../../services/clientiService';
import teamService from '../../services/teamService';
import './clienti-responsive.css';

// Stili per la tabella professionale (same as ClientiList)
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

// Additional styles specific to nutrition view
const nutriStyles = {
  statoBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    borderRadius: '20px',
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'capitalize',
  },
  btnStoria: {
    padding: '4px 10px',
    fontSize: '12px',
    borderRadius: '8px',
    color: 'white',
    border: 'none',
    transition: 'all 0.2s ease',
    cursor: 'pointer',
  },
  btnEditInline: {
    padding: '2px 6px',
    fontSize: '10px',
    borderRadius: '4px',
    background: 'rgba(0,0,0,0.05)',
    color: '#64748b',
    border: 'none',
    cursor: 'pointer',
    marginLeft: '4px',
  },
  checkDayBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    borderRadius: '8px',
    fontSize: '11px',
    fontWeight: 600,
    background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
    color: '#1e40af',
  },
  reachOutBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    borderRadius: '8px',
    fontSize: '11px',
    fontWeight: 600,
    background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
    color: '#92400e',
  },
  patologiaTag: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 500,
    background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
    color: '#166534',
  },
};

// Role colors for avatars
const ROLE_COLORS = {
  hm: { bg: '#f3e8ff', text: '#9333ea', badge: '#9333ea' },
  n: { bg: '#dcfce7', text: '#16a34a', badge: '#22c55e' },
  c: { bg: '#dbeafe', text: '#2563eb', badge: '#3b82f6' },
  p: { bg: '#fce7f3', text: '#db2777', badge: '#ec4899' },
  ca: { bg: '#fef3c7', text: '#d97706', badge: '#f59e0b' },
};

function ClientiListaNutrizione() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [clienti, setClienti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hoveredRow, setHoveredRow] = useState(null);
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

  const [filters, setFilters] = useState({
    search: searchParams.get('q') || '',
    nutrizionista: searchParams.get('nutrizionista_id') || '',
    statoNutrizione: searchParams.get('stato_nutrizione') || '',
    checkDay: searchParams.get('check_day') || '',
    reachOut: searchParams.get('reach_out_nutrizione') || '',
  });

  // Modal states
  const [showStoriaModal, setShowStoriaModal] = useState(false);
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [showPatologieModal, setShowPatologieModal] = useState(false);
  const [showStatoModal, setShowStatoModal] = useState(false);
  const [showChatModal, setShowChatModal] = useState(false);
  const [showCheckDayModal, setShowCheckDayModal] = useState(false);
  const [showReachOutModal, setShowReachOutModal] = useState(false);
  const [showPianoDietaModal, setShowPianoDietaModal] = useState(false);
  const [selectedCliente, setSelectedCliente] = useState(null);
  const [modalValue, setModalValue] = useState('');
  const [saving, setSaving] = useState(false);

  // Fetch nutrizionisti on mount
  useEffect(() => {
    const fetchNutrizionisti = async () => {
      try {
        const data = await teamService.getTeamMembers({
          per_page: 100,
          active: '1',
          specialty: 'nutrizione',
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
        q: filters.search || undefined,
        nutrizionista_id: filters.nutrizionista || undefined,
        stato_nutrizione: filters.statoNutrizione || undefined,
        check_day: filters.checkDay || undefined,
        reach_out_nutrizione: filters.reachOut || undefined,
      };

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
  }, [pagination.page, pagination.perPage, filters]);

  useEffect(() => {
    fetchClienti();
  }, [fetchClienti]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 }));
    const newParams = new URLSearchParams(searchParams);
    const paramKey = key === 'search' ? 'q' :
      key === 'nutrizionista' ? 'nutrizionista_id' :
        key === 'statoNutrizione' ? 'stato_nutrizione' :
          key === 'checkDay' ? 'check_day' :
            key === 'reachOut' ? 'reach_out_nutrizione' : key;
    if (value) {
      newParams.set(paramKey, value);
    } else {
      newParams.delete(paramKey);
    }
    setSearchParams(newParams);
  };

  const resetFilters = () => {
    setFilters({ search: '', nutrizionista: '', statoNutrizione: '', checkDay: '', reachOut: '' });
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
      await clientiService.updateField(clienteId, field, value || null);
      // Refresh the list
      fetchClienti();
      // Close modals
      setShowStoriaModal(false);
      setShowNoteModal(false);
      setShowStatoModal(false);
      setShowChatModal(false);
      setShowCheckDayModal(false);
      setShowReachOutModal(false);
      setShowPianoDietaModal(false);
    } catch (err) {
      console.error('Error updating field:', err);
      alert('Errore nel salvataggio');
    } finally {
      setSaving(false);
    }
  };

  // Open modal helpers
  const openStoriaModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.storia_nutrizionale || '');
    setShowStoriaModal(true);
  };

  const openNoteModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.note_extra_nutrizionista || '');
    setShowNoteModal(true);
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

  const openPianoDietaModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.piano_dieta || '');
    setShowPianoDietaModal(true);
  };

  // Render avatar team
  const renderTeamAvatar = (user, roleKey, roleLabel) => {
    if (!user) return null;
    const colors = ROLE_COLORS[roleKey] || ROLE_COLORS.n;
    const initials = `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase();

    return (
      <span
        key={`${roleKey}-${user.id}`}
        style={tableStyles.avatarTeam}
        title={`${roleLabel}: ${user.full_name || `${user.first_name} ${user.last_name}`}`}
      >
        {user.avatar_url || user.avatar_path ? (
          <img
            src={user.avatar_url || user.avatar_path}
            alt={user.full_name}
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

  // Render stato badge
  const renderStatoBadge = (stato) => {
    if (!stato) return <span style={tableStyles.emptyCell}>—</span>;
    const colors = STATI_PROFESSIONISTA_COLORS[stato] || { bg: '#f1f5f9', color: '#64748b' };
    return (
      <span style={{ ...nutriStyles.statoBadge, background: colors.bg, color: colors.color }}>
        <i className="ri-circle-fill" style={{ fontSize: '6px' }}></i>
        {stato}
      </span>
    );
  };

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4">
        <div>
          <h4 className="mb-1">Visuale Nutrizione</h4>
          <p className="text-muted mb-0">{pagination.total} pazienti in visuale nutrizione</p>
        </div>
        <div className="d-flex gap-2 flex-wrap clienti-header-actions">
          <Link to="/clienti-lista" className="btn btn-outline-primary btn-sm">
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
      <div className="row g-3 mb-4 clienti-stats-row">
        {[
          { label: 'Stato Attivo', value: kpi.stato_attivo, icon: 'ri-check-line', bg: 'success' },
          { label: 'Stato Ghost', value: kpi.stato_ghost, icon: 'ri-ghost-line', bg: 'secondary' },
          { label: 'Stato Pausa', value: kpi.stato_pausa, icon: 'ri-pause-line', bg: 'warning' },
          { label: 'Stato Stop', value: kpi.stato_stop, icon: 'ri-stop-line', bg: 'danger' },
        ].map((stat, idx) => (
          <div key={idx} className="col-xl-3 col-sm-6">
            <div className={`card bg-${stat.bg} border-0 shadow-sm`}>
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
                value={filters.nutrizionista}
                onChange={(e) => handleFilterChange('nutrizionista', e.target.value)}
              >
                <option value="">Nutrizionista</option>
                {nutrizionisti.map(n => (
                  <option key={n.id} value={n.id}>{n.full_name}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.statoNutrizione}
                onChange={(e) => handleFilterChange('statoNutrizione', e.target.value)}
              >
                <option value="">Stato Nutrizione</option>
                <option value="attivo">Attivo</option>
                <option value="pausa">Pausa</option>
                <option value="ghost">Ghost</option>
                <option value="stop">Stop</option>
              </select>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.checkDay}
                onChange={(e) => handleFilterChange('checkDay', e.target.value)}
              >
                <option value="">Check Day</option>
                {Object.entries(GIORNI_LABELS).filter(([k]) => !['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom'].includes(k)).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.reachOut}
                onChange={(e) => handleFilterChange('reachOut', e.target.value)}
              >
                <option value="">Reach Out</option>
                {Object.entries(GIORNI_LABELS).filter(([k]) => !['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom'].includes(k)).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
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
              <i className="ri-restaurant-line" style={{ fontSize: '5rem', color: '#cbd5e1' }}></i>
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
          <div className="card border-0 clienti-table-wrap" style={tableStyles.card}>
            <div className="table-responsive">
              <table className="table mb-0 clienti-table">
                <thead style={tableStyles.tableHeader}>
                  <tr>
                    <th style={{ ...tableStyles.th, minWidth: '180px' }}>Cliente</th>
                    <th style={{ ...tableStyles.th, minWidth: '100px' }}>Team</th>
                    <th style={{ ...tableStyles.th, minWidth: '110px' }}>Stato Nutri</th>
                    <th style={{ ...tableStyles.th, minWidth: '110px' }}>Stato Chat</th>
                    <th style={{ ...tableStyles.th, minWidth: '100px' }}>Check Day</th>
                    <th style={{ ...tableStyles.th, minWidth: '100px' }}>Reach Out</th>
                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '110px' }}>Patologie</th>
                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '100px' }}>Piano Dieta</th>
                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '80px' }}>Storia</th>
                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '90px' }}>Note Extra</th>
                    <th style={{ ...tableStyles.th, textAlign: 'right', minWidth: '80px' }}>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {clienti.map((cliente, index) => {
                    const patologie = getClientPatologie(cliente);
                    const clienteId = cliente.cliente_id || cliente.clienteId;
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
                        <td style={tableStyles.td} data-label="Paziente">
                          <Link
                            to={`/clienti-dettaglio/${clienteId}`}
                            style={tableStyles.nameLink}
                            onMouseOver={(e) => e.currentTarget.style.color = '#2563eb'}
                            onMouseOut={(e) => e.currentTarget.style.color = '#3b82f6'}
                          >
                            {cliente.nome_cognome || cliente.nomeCognome}
                          </Link>
                        </td>
                        <td style={tableStyles.td} data-label="Team">
                          <div style={{ display: 'flex', alignItems: 'center', flexDirection: 'row', flexWrap: 'nowrap' }}>
                            {renderTeamAvatar(cliente.health_manager_user, 'hm', 'Health Manager')}
                            {cliente.nutrizionisti_multipli?.map(n => renderTeamAvatar(n, 'n', 'Nutrizionista'))}
                            {cliente.coaches_multipli?.map(c => renderTeamAvatar(c, 'c', 'Coach'))}
                            {cliente.psicologi_multipli?.map(p => renderTeamAvatar(p, 'p', 'Psicologo'))}
                            {cliente.consulenti_multipli?.map(ca => renderTeamAvatar(ca, 'ca', 'Consulente'))}
                            {!cliente.health_manager_user && !cliente.nutrizionisti_multipli?.length &&
                              !cliente.coaches_multipli?.length && !cliente.psicologi_multipli?.length &&
                              !cliente.consulenti_multipli?.length && <span style={tableStyles.emptyCell}>—</span>}
                          </div>
                        </td>
                        <td style={tableStyles.td} data-label="Stato Nutri">
                          <div className="d-flex align-items-center gap-1">
                            {renderStatoBadge(cliente.stato_nutrizione)}
                            <button
                              style={nutriStyles.btnEditInline}
                              onClick={() => openStatoModal(cliente)}
                              title="Modifica stato"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td style={tableStyles.td} data-label="Stato Chat">
                          <div className="d-flex align-items-center gap-1">
                            {cliente.stato_cliente_chat_nutrizione ? (
                              <span style={{
                                ...nutriStyles.statoBadge,
                                background: STATI_PROFESSIONISTA_COLORS[cliente.stato_cliente_chat_nutrizione]?.bg || '#f1f5f9',
                                color: STATI_PROFESSIONISTA_COLORS[cliente.stato_cliente_chat_nutrizione]?.color || '#64748b'
                              }}>
                                <i className="ri-chat-3-line" style={{ fontSize: '10px' }}></i>
                                {cliente.stato_cliente_chat_nutrizione}
                              </span>
                            ) : <span style={tableStyles.emptyCell}>—</span>}
                            <button
                              style={nutriStyles.btnEditInline}
                              onClick={() => openChatModal(cliente)}
                              title="Modifica stato chat"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td style={tableStyles.td} data-label="Check Day">
                          <div className="d-flex align-items-center gap-1">
                            {cliente.check_day ? (
                              <span style={nutriStyles.checkDayBadge}>
                                <i className="ri-calendar-check-line"></i>
                                {GIORNI_LABELS[cliente.check_day] || cliente.check_day}
                              </span>
                            ) : (
                              <span style={tableStyles.emptyCell}>—</span>
                            )}
                            <button
                              style={nutriStyles.btnEditInline}
                              onClick={() => openCheckDayModal(cliente)}
                              title="Modifica check day"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td style={tableStyles.td} data-label="Reach Out">
                          <div className="d-flex align-items-center gap-1">
                            {cliente.reach_out_nutrizione ? (
                              <span style={nutriStyles.reachOutBadge}>
                                <i className="ri-calendar-event-line"></i>
                                {GIORNI_LABELS[cliente.reach_out_nutrizione] || cliente.reach_out_nutrizione}
                              </span>
                            ) : (
                              <span style={tableStyles.emptyCell}>—</span>
                            )}
                            <button
                              style={nutriStyles.btnEditInline}
                              onClick={() => openReachOutModal(cliente)}
                              title="Modifica reach out"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td style={{ ...tableStyles.td, textAlign: 'center' }} data-label="Patologie">
                          {patologie.length > 0 ? (
                            <button
                              className="btn btn-sm"
                              style={{
                                background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
                                color: 'white',
                                borderRadius: '8px',
                              }}
                              onClick={() => {
                                setSelectedCliente(cliente);
                                setShowPatologieModal(true);
                              }}
                            >
                              <i className="ri-heart-pulse-line me-1"></i>
                              {patologie.length}
                            </button>
                          ) : cliente.nessuna_patologia_nutrizionale ? (
                            <span className="btn btn-sm" style={{
                              background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
                              color: '#166534',
                              cursor: 'default',
                            }}>
                              <i className="ri-checkbox-circle-line"></i>
                            </span>
                          ) : (
                            <button
                              className="btn btn-sm"
                              style={{
                                background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                                color: 'white',
                                borderRadius: '8px',
                              }}
                              onClick={() => {
                                setSelectedCliente(cliente);
                                setShowPatologieModal(true);
                              }}
                            >
                              <i className="ri-heart-pulse-line me-1"></i>-
                            </button>
                          )}
                        </td>
                        <td style={{ ...tableStyles.td, textAlign: 'center' }} data-label="Piano Dieta">
                          <button
                            className="btn btn-sm"
                            style={{
                              ...nutriStyles.btnStoria,
                              background: cliente.piano_dieta
                                ? 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)'
                                : 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                            }}
                            onClick={() => openPianoDietaModal(cliente)}
                          >
                            <i className="ri-file-list-line me-1"></i>
                            {cliente.piano_dieta ? 'Vedi' : '+'}
                          </button>
                        </td>
                        <td style={{ ...tableStyles.td, textAlign: 'center' }} data-label="Storia">
                          <button
                            className="btn btn-sm"
                            style={{
                              ...nutriStyles.btnStoria,
                              background: cliente.storia_nutrizionale
                                ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
                                : 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                            }}
                            onClick={() => openStoriaModal(cliente)}
                          >
                            <i className="ri-file-text-line me-1"></i>
                            {cliente.storia_nutrizionale ? 'Vedi' : '+'}
                          </button>
                        </td>
                        <td style={{ ...tableStyles.td, textAlign: 'center' }} data-label="Note Extra">
                          <button
                            className="btn btn-sm"
                            style={{
                              ...nutriStyles.btnStoria,
                              background: cliente.note_extra_nutrizionista
                                ? 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)'
                                : 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                            }}
                            onClick={() => openNoteModal(cliente)}
                          >
                            <i className="ri-sticky-note-line me-1"></i>
                            {cliente.note_extra_nutrizionista ? 'Vedi' : '+'}
                          </button>
                        </td>
                        <td style={{ ...tableStyles.td, textAlign: 'right' }} data-label="Azioni">
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
                            background: isActive ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' : 'transparent',
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

      {/* Modal Storia Nutrizionale */}
      {showStoriaModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-file-text-line me-2"></i>
                  Storia Nutrizionale - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowStoriaModal(false)}></button>
              </div>
              <div className="modal-body">
                <textarea
                  className="form-control"
                  rows="12"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  placeholder="Inserisci la storia nutrizionale..."
                  style={{ border: '2px solid rgba(34, 197, 94, 0.2)', borderRadius: '12px' }}
                ></textarea>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowStoriaModal(false)} style={{ borderRadius: '10px' }}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'storia_nutrizionale', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Note Extra */}
      {showNoteModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-sticky-note-line me-2"></i>
                  Note Extra - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowNoteModal(false)}></button>
              </div>
              <div className="modal-body">
                <textarea
                  className="form-control"
                  rows="12"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  placeholder="Inserisci note extra..."
                  style={{ border: '2px solid rgba(139, 92, 246, 0.2)', borderRadius: '12px' }}
                ></textarea>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowNoteModal(false)} style={{ borderRadius: '10px' }}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'note_extra_nutrizionista', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Stato Nutrizione */}
      {showStatoModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-circle-fill me-2"></i>
                  Stato Nutrizione - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowStatoModal(false)}></button>
              </div>
              <div className="modal-body">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid rgba(34, 197, 94, 0.2)', borderRadius: '12px' }}
                >
                  <option value="">-- Nessuno --</option>
                  <option value="attivo">Attivo</option>
                  <option value="pausa">Pausa</option>
                  <option value="ghost">Ghost</option>
                  <option value="stop">Stop</option>
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowStatoModal(false)} style={{ borderRadius: '10px' }}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'stato_nutrizione', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Stato Chat */}
      {showChatModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-chat-3-line me-2"></i>
                  Stato Chat - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowChatModal(false)}></button>
              </div>
              <div className="modal-body">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid rgba(139, 92, 246, 0.2)', borderRadius: '12px' }}
                >
                  <option value="">-- Nessuno --</option>
                  <option value="attivo">Attivo</option>
                  <option value="pausa">Pausa</option>
                  <option value="ghost">Ghost</option>
                  <option value="stop">Stop</option>
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowChatModal(false)} style={{ borderRadius: '10px' }}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'stato_cliente_chat_nutrizione', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Check Day */}
      {showCheckDayModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-calendar-check-line me-2"></i>
                  Check Day - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowCheckDayModal(false)}></button>
              </div>
              <div className="modal-body">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid rgba(59, 130, 246, 0.2)', borderRadius: '12px' }}
                >
                  <option value="">-- Nessun giorno --</option>
                  <option value="lunedi">Lunedi</option>
                  <option value="martedi">Martedi</option>
                  <option value="mercoledi">Mercoledi</option>
                  <option value="giovedi">Giovedi</option>
                  <option value="venerdi">Venerdi</option>
                  <option value="sabato">Sabato</option>
                  <option value="domenica">Domenica</option>
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCheckDayModal(false)} style={{ borderRadius: '10px' }}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'check_day', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Reach Out */}
      {showReachOutModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-calendar-event-line me-2"></i>
                  Reach Out - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowReachOutModal(false)}></button>
              </div>
              <div className="modal-body">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid rgba(245, 158, 11, 0.2)', borderRadius: '12px' }}
                >
                  <option value="">-- Nessun giorno --</option>
                  <option value="lunedi">Lunedi</option>
                  <option value="martedi">Martedi</option>
                  <option value="mercoledi">Mercoledi</option>
                  <option value="giovedi">Giovedi</option>
                  <option value="venerdi">Venerdi</option>
                  <option value="sabato">Sabato</option>
                  <option value="domenica">Domenica</option>
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowReachOutModal(false)} style={{ borderRadius: '10px' }}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'reach_out_nutrizione', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Piano Dieta */}
      {showPianoDietaModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-file-list-line me-2"></i>
                  Piano Dieta - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowPianoDietaModal(false)}></button>
              </div>
              <div className="modal-body">
                <textarea
                  className="form-control"
                  rows="12"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  placeholder="Inserisci il piano dieta..."
                  style={{ border: '2px solid rgba(249, 115, 22, 0.2)', borderRadius: '12px' }}
                ></textarea>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowPianoDietaModal(false)} style={{ borderRadius: '10px' }}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'piano_dieta', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Patologie */}
      {showPatologieModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-heart-pulse-line me-2"></i>
                  Patologie - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowPatologieModal(false)}></button>
              </div>
              <div className="modal-body">
                {getClientPatologie(selectedCliente).length > 0 ? (
                  <div className="d-flex flex-wrap gap-2">
                    {getClientPatologie(selectedCliente).map((p, i) => (
                      <span key={i} style={nutriStyles.patologiaTag}>
                        <i className="ri-heart-pulse-fill"></i>
                        {p}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <i className="ri-heart-pulse-line text-muted" style={{ fontSize: '48px' }}></i>
                    <p className="text-muted mt-2 mb-0">Nessuna patologia nutrizionale registrata</p>
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowPatologieModal(false)} style={{ borderRadius: '10px' }}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <Link
                  to={`/clienti-dettaglio/${selectedCliente.cliente_id || selectedCliente.clienteId}#nutrizione`}
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', borderRadius: '10px' }}
                >
                  <i className="ri-external-link-line me-1"></i> Modifica
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ClientiListaNutrizione;

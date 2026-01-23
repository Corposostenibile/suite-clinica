import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import clientiService, {
  GIORNI_LABELS,
  STATI_PROFESSIONISTA_COLORS,
  LUOGO_LABELS,
} from '../../services/clientiService';
import teamService from '../../services/teamService';

// CSS Styles inline for the component
const styles = {
  coachHeader: {
    background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
    color: 'white',
    padding: '16px 24px',
    borderRadius: '12px',
    marginBottom: '24px',
  },
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
  avatarTeam: {
    position: 'relative',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    cursor: 'pointer',
  },
  avatarImg: {
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    objectFit: 'cover',
    border: '2px solid #fff',
    boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
  },
  avatarInitials: {
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
  avatarBadge: {
    position: 'absolute',
    bottom: '-2px',
    right: '-2px',
    fontSize: '7px',
    fontWeight: 700,
    color: '#fff',
    padding: '1px 3px',
    borderRadius: '3px',
    lineHeight: 1,
    boxShadow: '0 1px 2px rgba(0,0,0,0.15)',
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
  luogoBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    borderRadius: '8px',
    fontSize: '11px',
    fontWeight: 600,
  },
};

// Luogo colors
const LUOGO_COLORS = {
  casa: { bg: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)', color: '#92400e' },
  palestra: { bg: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)', color: '#1e40af' },
  ibrido: { bg: 'linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%)', color: '#7c3aed' },
};

// Role colors for avatars
const ROLE_COLORS = {
  hm: { bg: '#f3e8ff', text: '#9333ea', badge: '#9333ea' },
  n: { bg: '#dcfce7', text: '#16a34a', badge: '#22c55e' },
  c: { bg: '#dbeafe', text: '#2563eb', badge: '#3b82f6' },
  p: { bg: '#fce7f3', text: '#db2777', badge: '#ec4899' },
  ca: { bg: '#fef3c7', text: '#d97706', badge: '#f59e0b' },
};

function ClientiListaCoach() {
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
  const [coaches, setCoaches] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 25,
    total: 0,
    totalPages: 0,
  });

  const [filters, setFilters] = useState({
    search: searchParams.get('q') || '',
    coach: searchParams.get('coach_id') || '',
    statoCoach: searchParams.get('stato_coach') || '',
    checkDay: searchParams.get('check_day') || '',
    reachOut: searchParams.get('reach_out_coaching') || '',
  });

  // Modal states
  const [showStoriaModal, setShowStoriaModal] = useState(false);
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [showStatoModal, setShowStatoModal] = useState(false);
  const [showChatModal, setShowChatModal] = useState(false);
  const [showCheckDayModal, setShowCheckDayModal] = useState(false);
  const [showReachOutModal, setShowReachOutModal] = useState(false);
  const [showPianoAllenamentoModal, setShowPianoAllenamentoModal] = useState(false);
  const [showLuogoModal, setShowLuogoModal] = useState(false);
  const [selectedCliente, setSelectedCliente] = useState(null);
  const [modalValue, setModalValue] = useState('');
  const [saving, setSaving] = useState(false);

  // Fetch coaches on mount
  useEffect(() => {
    const fetchCoaches = async () => {
      try {
        const data = await teamService.getTeamMembers({
          per_page: 100,
          active: '1',
          specialty: 'coach',
        });
        setCoaches(data.members || []);
      } catch (err) {
        console.error('Error fetching coaches:', err);
      }
    };
    fetchCoaches();
  }, []);

  const fetchClienti = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page: pagination.page,
        per_page: pagination.perPage,
        q: filters.search || undefined,
        coach_id: filters.coach || undefined,
        stato_coach: filters.statoCoach || undefined,
        check_day: filters.checkDay || undefined,
        reach_out_coaching: filters.reachOut || undefined,
      };

      const data = await clientiService.getClientiCoach(params);
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
        const clientiData = data.data || [];
        setKpi({
          stato_attivo: clientiData.filter(c => c.stato_coach === 'attivo').length,
          stato_ghost: clientiData.filter(c => c.stato_coach === 'ghost').length,
          stato_pausa: clientiData.filter(c => c.stato_coach === 'pausa').length,
          stato_stop: clientiData.filter(c => c.stato_coach === 'stop').length,
          chat_attivo: clientiData.filter(c => c.stato_cliente_chat_coaching === 'attivo').length,
          chat_ghost: clientiData.filter(c => c.stato_cliente_chat_coaching === 'ghost').length,
          chat_pausa: clientiData.filter(c => c.stato_cliente_chat_coaching === 'pausa').length,
          chat_stop: clientiData.filter(c => c.stato_cliente_chat_coaching === 'stop').length,
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
      key === 'coach' ? 'coach_id' :
      key === 'statoCoach' ? 'stato_coach' :
      key === 'checkDay' ? 'check_day' :
      key === 'reachOut' ? 'reach_out_coaching' : key;
    if (value) {
      newParams.set(paramKey, value);
    } else {
      newParams.delete(paramKey);
    }
    setSearchParams(newParams);
  };

  const resetFilters = () => {
    setFilters({ search: '', coach: '', statoCoach: '', checkDay: '', reachOut: '' });
    setSearchParams(new URLSearchParams());
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, page: newPage }));
  };

  // Handle field update
  const handleUpdateField = async (clienteId, field, value) => {
    setSaving(true);
    try {
      await clientiService.updateField(clienteId, field, value || null);
      fetchClienti();
      setShowStoriaModal(false);
      setShowNoteModal(false);
      setShowStatoModal(false);
      setShowChatModal(false);
      setShowCheckDayModal(false);
      setShowReachOutModal(false);
      setShowPianoAllenamentoModal(false);
      setShowLuogoModal(false);
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
    setModalValue(cliente.storia_coaching || '');
    setShowStoriaModal(true);
  };

  const openNoteModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.note_extra_coach || '');
    setShowNoteModal(true);
  };

  const openStatoModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.stato_coach || '');
    setShowStatoModal(true);
  };

  const openChatModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.stato_cliente_chat_coaching || '');
    setShowChatModal(true);
  };

  const openCheckDayModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.check_day || '');
    setShowCheckDayModal(true);
  };

  const openReachOutModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.reach_out_coaching || '');
    setShowReachOutModal(true);
  };

  const openPianoAllenamentoModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.piano_allenamento || '');
    setShowPianoAllenamentoModal(true);
  };

  const openLuogoModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.luogo_di_allenamento || '');
    setShowLuogoModal(true);
  };

  // Render avatar team
  const renderAvatarTeam = (user, role, label) => {
    if (!user) return null;
    const colors = ROLE_COLORS[role] || ROLE_COLORS.c;
    const initials = `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase();

    return (
      <span
        style={styles.avatarTeam}
        title={`${label}: ${user.full_name || `${user.first_name} ${user.last_name}`}`}
      >
        {user.avatar_url ? (
          <img src={user.avatar_url} alt={user.full_name} style={styles.avatarImg} />
        ) : (
          <span style={{ ...styles.avatarInitials, background: colors.bg, color: colors.text }}>
            {initials}
          </span>
        )}
        <span style={{ ...styles.avatarBadge, background: colors.badge }}>
          {role.toUpperCase()}
        </span>
      </span>
    );
  };

  // Render stato badge
  const renderStatoBadge = (stato) => {
    if (!stato) return <em className="text-muted">-</em>;
    const colors = STATI_PROFESSIONISTA_COLORS[stato] || { bg: '#f1f5f9', color: '#64748b' };
    return (
      <span style={{ ...styles.statoBadge, background: colors.bg, color: colors.color }}>
        <i className="ri-circle-fill" style={{ fontSize: '6px' }}></i>
        {stato}
      </span>
    );
  };

  // Render luogo badge
  const renderLuogoBadge = (luogo) => {
    if (!luogo) return <em className="text-muted">-</em>;
    const colors = LUOGO_COLORS[luogo] || { bg: '#f1f5f9', color: '#64748b' };
    return (
      <span style={{ ...styles.luogoBadge, background: colors.bg, color: colors.color }}>
        <i className={luogo === 'casa' ? 'ri-home-line' : luogo === 'palestra' ? 'ri-building-line' : 'ri-exchange-line'}></i>
        {LUOGO_LABELS[luogo] || luogo}
      </span>
    );
  };

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div style={styles.coachHeader} className="d-flex flex-wrap align-items-center justify-content-between gap-3">
        <div>
          <h5 className="fw-semibold mb-1 text-white">
            <i className="ri-run-line me-2"></i>Visuale Coach
          </h5>
          <small className="opacity-75">Vista ottimizzata per il team coaching</small>
        </div>
        <Link to="/clienti-lista" className="btn btn-light btn-sm">
          <i className="ri-arrow-left-line me-1"></i> Torna alla Lista
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="row g-3 mb-4">
        <div className="col-12">
          <div className="card">
            <div className="card-body py-3">
              <div className="d-flex align-items-center gap-2 mb-2">
                <i className="ri-run-line" style={{ fontSize: '18px', color: '#f97316' }}></i>
                <span className="fw-semibold text-dark">Stato Coach</span>
              </div>
              <div className="d-flex flex-wrap gap-3">
                <div className="d-flex align-items-center gap-2">
                  {renderStatoBadge('attivo')}
                  <span className="fw-bold text-dark">{kpi.stato_attivo}</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  {renderStatoBadge('ghost')}
                  <span className="fw-bold text-dark">{kpi.stato_ghost}</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  {renderStatoBadge('pausa')}
                  <span className="fw-bold text-dark">{kpi.stato_pausa}</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  {renderStatoBadge('stop')}
                  <span className="fw-bold text-dark">{kpi.stato_stop}</span>
                </div>
                <div className="border-start ps-3 d-flex align-items-center gap-2">
                  <i className="ri-chat-3-line text-primary" style={{ fontSize: '16px' }}></i>
                  <span className="fw-semibold text-muted">Chat:</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  <span style={{ ...styles.statoBadge, ...STATI_PROFESSIONISTA_COLORS.attivo }}>
                    <i className="ri-chat-3-line" style={{ fontSize: '10px' }}></i> Attivo
                  </span>
                  <span className="fw-bold text-dark">{kpi.chat_attivo}</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  <span style={{ ...styles.statoBadge, ...STATI_PROFESSIONISTA_COLORS.ghost }}>
                    <i className="ri-chat-3-line" style={{ fontSize: '10px' }}></i> Ghost
                  </span>
                  <span className="fw-bold text-dark">{kpi.chat_ghost}</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  <span style={{ ...styles.statoBadge, ...STATI_PROFESSIONISTA_COLORS.pausa }}>
                    <i className="ri-chat-3-line" style={{ fontSize: '10px' }}></i> Pausa
                  </span>
                  <span className="fw-bold text-dark">{kpi.chat_pausa}</span>
                </div>
                <div className="d-flex align-items-center gap-2">
                  <span style={{ ...styles.statoBadge, ...STATI_PROFESSIONISTA_COLORS.stop }}>
                    <i className="ri-chat-3-line" style={{ fontSize: '10px' }}></i> Stop
                  </span>
                  <span className="fw-bold text-dark">{kpi.chat_stop}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card mb-4">
        <div className="card-body">
          <div className="row gy-3 gx-4 align-items-end">
            <div className="col-lg-4 col-md-6">
              <label className="form-label fw-semibold text-sm mb-2">Ricerca Cliente</label>
              <input
                type="text"
                className="form-control"
                placeholder="Nome cliente..."
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
              />
            </div>
            <div className="col-lg-3 col-md-4">
              <label className="form-label fw-semibold text-sm mb-2">Coach</label>
              <select
                className="form-select"
                value={filters.coach}
                onChange={(e) => handleFilterChange('coach', e.target.value)}
              >
                <option value="">Tutti</option>
                {coaches.map(c => (
                  <option key={c.id} value={c.id}>{c.full_name}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2 col-md-3">
              <label className="form-label fw-semibold text-sm mb-2">Stato Coach</label>
              <select
                className="form-select"
                value={filters.statoCoach}
                onChange={(e) => handleFilterChange('statoCoach', e.target.value)}
              >
                <option value="">Tutti</option>
                <option value="attivo">Attivo</option>
                <option value="pausa">Pausa</option>
                <option value="ghost">Ghost</option>
                <option value="stop">Stop</option>
              </select>
            </div>
            <div className="col-lg-2 col-md-3">
              <label className="form-label fw-semibold text-sm mb-2">Check Day</label>
              <select
                className="form-select"
                value={filters.checkDay}
                onChange={(e) => handleFilterChange('checkDay', e.target.value)}
              >
                <option value="">Tutti</option>
                {Object.entries(GIORNI_LABELS).filter(([k]) => !['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom'].includes(k)).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2 col-md-3">
              <label className="form-label fw-semibold text-sm mb-2">Reach Out</label>
              <select
                className="form-select"
                value={filters.reachOut}
                onChange={(e) => handleFilterChange('reachOut', e.target.value)}
              >
                <option value="">Tutti</option>
                {Object.entries(GIORNI_LABELS).filter(([k]) => !['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom'].includes(k)).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2 col-md-3">
              <div className="d-flex gap-2">
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' }}
                  onClick={fetchClienti}
                >
                  <i className="ri-filter-line me-1"></i> Filtra
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={resetFilters}
                >
                  <i className="ri-refresh-line"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border" style={{ width: '3rem', height: '3rem', color: '#f97316' }}></div>
          <p className="mt-3 text-muted">Caricamento clienti...</p>
        </div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : clienti.length === 0 ? (
        <div className="card">
          <div className="card-body text-center py-5">
            <i className="ri-run-line text-muted" style={{ fontSize: '48px' }}></i>
            <h5 className="text-secondary-light mt-3">Nessun cliente trovato</h5>
            <p className="text-muted mb-0">Non ci sono clienti che corrispondono ai criteri di ricerca.</p>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="card-header d-flex justify-content-between align-items-center">
            <h5 className="card-title mb-0">
              <i className="ri-run-line me-2" style={{ color: '#f97316' }}></i>
              Clienti ({pagination.total})
            </h5>
          </div>
          <div className="card-body p-0">
            <div className="table-responsive">
              <table className="table table-hover mb-0 align-middle">
                <thead className="table-light">
                  <tr>
                    <th>Cliente</th>
                    <th>Team</th>
                    <th>Stato Coach</th>
                    <th>Stato Chat</th>
                    <th>Check Day</th>
                    <th>Reach Out</th>
                    <th className="text-center">Piano Allenamento</th>
                    <th className="text-center">Luogo</th>
                    <th className="text-center">Storia</th>
                    <th className="text-center">Note Extra</th>
                    <th className="text-end">Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {clienti.map((cliente) => {
                    const clienteId = cliente.cliente_id || cliente.clienteId;

                    return (
                      <tr key={clienteId}>
                        <td>
                          <Link to={`/clienti-dettaglio/${clienteId}`} className="fw-semibold text-dark">
                            {cliente.nome_cognome || cliente.nomeCognome}
                          </Link>
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-1">
                            {renderAvatarTeam(cliente.health_manager_user, 'hm', 'HM')}
                            {cliente.coaches_multipli?.map((c, i) => renderAvatarTeam(c, 'c', 'Coach'))}
                            {cliente.nutrizionisti_multipli?.map((n, i) => renderAvatarTeam(n, 'n', 'Nutri'))}
                            {cliente.psicologi_multipli?.map((p, i) => renderAvatarTeam(p, 'p', 'Psico'))}
                            {cliente.consulenti_multipli?.map((ca, i) => renderAvatarTeam(ca, 'ca', 'Cons'))}
                            {!cliente.health_manager_user && !cliente.coaches_multipli?.length &&
                              !cliente.nutrizionisti_multipli?.length && !cliente.psicologi_multipli?.length &&
                              !cliente.consulenti_multipli?.length && <em className="text-muted">-</em>}
                          </div>
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-1">
                            {renderStatoBadge(cliente.stato_coach)}
                            <button
                              style={styles.btnEditInline}
                              onClick={() => openStatoModal(cliente)}
                              title="Modifica stato"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-1">
                            {cliente.stato_cliente_chat_coaching ? (
                              <span style={{
                                ...styles.statoBadge,
                                background: STATI_PROFESSIONISTA_COLORS[cliente.stato_cliente_chat_coaching]?.bg || '#f1f5f9',
                                color: STATI_PROFESSIONISTA_COLORS[cliente.stato_cliente_chat_coaching]?.color || '#64748b'
                              }}>
                                <i className="ri-chat-3-line" style={{ fontSize: '10px' }}></i>
                                {cliente.stato_cliente_chat_coaching}
                              </span>
                            ) : <em className="text-muted">-</em>}
                            <button
                              style={styles.btnEditInline}
                              onClick={() => openChatModal(cliente)}
                              title="Modifica stato chat"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-1">
                            {cliente.check_day ? (
                              <span style={styles.checkDayBadge}>
                                <i className="ri-calendar-check-line"></i>
                                {GIORNI_LABELS[cliente.check_day] || cliente.check_day}
                              </span>
                            ) : (
                              <span style={{ ...styles.checkDayBadge, background: '#f1f5f9', color: '#64748b' }}>
                                <em>-</em>
                              </span>
                            )}
                            <button
                              style={styles.btnEditInline}
                              onClick={() => openCheckDayModal(cliente)}
                              title="Modifica check day"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-1">
                            {cliente.reach_out_coaching ? (
                              <span style={styles.reachOutBadge}>
                                <i className="ri-calendar-event-line"></i>
                                {GIORNI_LABELS[cliente.reach_out_coaching] || cliente.reach_out_coaching}
                              </span>
                            ) : (
                              <span style={{ ...styles.reachOutBadge, background: '#f1f5f9', color: '#64748b' }}>
                                <em>-</em>
                              </span>
                            )}
                            <button
                              style={styles.btnEditInline}
                              onClick={() => openReachOutModal(cliente)}
                              title="Modifica reach out"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td className="text-center">
                          <button
                            className="btn btn-sm"
                            style={{
                              ...styles.btnStoria,
                              background: cliente.piano_allenamento
                                ? 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)'
                                : 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                            }}
                            onClick={() => openPianoAllenamentoModal(cliente)}
                          >
                            <i className="ri-file-list-line me-1"></i>
                            {cliente.piano_allenamento ? 'Vedi' : 'Aggiungi'}
                          </button>
                        </td>
                        <td className="text-center">
                          <div className="d-flex align-items-center justify-content-center gap-1">
                            {renderLuogoBadge(cliente.luogo_di_allenamento)}
                            <button
                              style={styles.btnEditInline}
                              onClick={() => openLuogoModal(cliente)}
                              title="Modifica luogo"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>
                        <td className="text-center">
                          <button
                            className="btn btn-sm"
                            style={{
                              ...styles.btnStoria,
                              background: cliente.storia_coaching
                                ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
                                : 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                            }}
                            onClick={() => openStoriaModal(cliente)}
                          >
                            <i className="ri-file-text-line me-1"></i>
                            {cliente.storia_coaching ? 'Vedi' : 'Aggiungi'}
                          </button>
                        </td>
                        <td className="text-center">
                          <button
                            className="btn btn-sm"
                            style={{
                              ...styles.btnStoria,
                              background: cliente.note_extra_coach
                                ? 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)'
                                : 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                            }}
                            onClick={() => openNoteModal(cliente)}
                          >
                            <i className="ri-sticky-note-line me-1"></i>
                            {cliente.note_extra_coach ? 'Vedi' : 'Aggiungi'}
                          </button>
                        </td>
                        <td className="text-end">
                          <Link
                            to={`/clienti-dettaglio/${clienteId}#coaching`}
                            className="btn btn-sm btn-outline-warning"
                            title="Vai a Tab Coaching"
                            style={{ borderColor: '#f97316', color: '#f97316' }}
                          >
                            <i className="ri-run-line"></i>
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Pagination */}
      {pagination.totalPages > 1 && (
        <nav aria-label="Paginazione clienti" className="mt-4">
          <ul className="pagination justify-content-center mb-0">
            <li className={`page-item ${pagination.page === 1 ? 'disabled' : ''}`}>
              <button className="page-link" onClick={() => handlePageChange(pagination.page - 1)}>
                &laquo;
              </button>
            </li>
            {[...Array(Math.min(pagination.totalPages, 5))].map((_, i) => {
              const pageNum = pagination.totalPages <= 5 ? i + 1 :
                pagination.page <= 3 ? i + 1 :
                pagination.page >= pagination.totalPages - 2 ? pagination.totalPages - 4 + i :
                pagination.page - 2 + i;
              return (
                <li key={pageNum} className={`page-item ${pagination.page === pageNum ? 'active' : ''}`}>
                  <button className="page-link" onClick={() => handlePageChange(pageNum)}>{pageNum}</button>
                </li>
              );
            })}
            <li className={`page-item ${pagination.page === pagination.totalPages ? 'disabled' : ''}`}>
              <button className="page-link" onClick={() => handlePageChange(pagination.page + 1)}>
                &raquo;
              </button>
            </li>
          </ul>
        </nav>
      )}

      {/* Modal Storia Coaching */}
      {showStoriaModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-file-text-line me-2"></i>
                  Storia Coaching - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowStoriaModal(false)}></button>
              </div>
              <div className="modal-body">
                <textarea
                  className="form-control"
                  rows="12"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  placeholder="Inserisci la storia coaching..."
                  style={{ border: '2px solid rgba(59, 130, 246, 0.2)', borderRadius: '12px' }}
                ></textarea>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowStoriaModal(false)}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'storia_coaching', modalValue)}
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
            <div className="modal-content">
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
                <button type="button" className="btn btn-secondary" onClick={() => setShowNoteModal(false)}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'note_extra_coach', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Stato Coach */}
      {showStatoModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-circle-fill me-2"></i>
                  Stato Coach - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowStatoModal(false)}></button>
              </div>
              <div className="modal-body">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ border: '2px solid rgba(249, 115, 22, 0.2)', borderRadius: '12px' }}
                >
                  <option value="">-- Nessuno --</option>
                  <option value="attivo">Attivo</option>
                  <option value="pausa">Pausa</option>
                  <option value="ghost">Ghost</option>
                  <option value="stop">Stop</option>
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowStatoModal(false)}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'stato_coach', modalValue)}
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
            <div className="modal-content">
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
                  style={{ border: '2px solid rgba(139, 92, 246, 0.2)', borderRadius: '12px' }}
                >
                  <option value="">-- Nessuno --</option>
                  <option value="attivo">Attivo</option>
                  <option value="pausa">Pausa</option>
                  <option value="ghost">Ghost</option>
                  <option value="stop">Stop</option>
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowChatModal(false)}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'stato_cliente_chat_coaching', modalValue)}
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
            <div className="modal-content">
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
                  style={{ border: '2px solid rgba(59, 130, 246, 0.2)', borderRadius: '12px' }}
                >
                  <option value="">-- Nessun giorno --</option>
                  <option value="lunedi">Lunedì</option>
                  <option value="martedi">Martedì</option>
                  <option value="mercoledi">Mercoledì</option>
                  <option value="giovedi">Giovedì</option>
                  <option value="venerdi">Venerdì</option>
                  <option value="sabato">Sabato</option>
                  <option value="domenica">Domenica</option>
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCheckDayModal(false)}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
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
            <div className="modal-content">
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
                  style={{ border: '2px solid rgba(245, 158, 11, 0.2)', borderRadius: '12px' }}
                >
                  <option value="">-- Nessun giorno --</option>
                  <option value="lunedi">Lunedì</option>
                  <option value="martedi">Martedì</option>
                  <option value="mercoledi">Mercoledì</option>
                  <option value="giovedi">Giovedì</option>
                  <option value="venerdi">Venerdì</option>
                  <option value="sabato">Sabato</option>
                  <option value="domenica">Domenica</option>
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowReachOutModal(false)}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'reach_out_coaching', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Piano Allenamento */}
      {showPianoAllenamentoModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-file-list-line me-2"></i>
                  Piano Allenamento - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowPianoAllenamentoModal(false)}></button>
              </div>
              <div className="modal-body">
                <textarea
                  className="form-control"
                  rows="12"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  placeholder="Inserisci il piano di allenamento..."
                  style={{ border: '2px solid rgba(249, 115, 22, 0.2)', borderRadius: '12px' }}
                ></textarea>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowPianoAllenamentoModal(false)}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'piano_allenamento', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Luogo Allenamento */}
      {showLuogoModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-map-pin-line me-2"></i>
                  Luogo Allenamento - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowLuogoModal(false)}></button>
              </div>
              <div className="modal-body">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ border: '2px solid rgba(249, 115, 22, 0.2)', borderRadius: '12px' }}
                >
                  <option value="">-- Seleziona --</option>
                  <option value="casa">Casa</option>
                  <option value="palestra">Palestra</option>
                  <option value="ibrido">Ibrido</option>
                </select>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowLuogoModal(false)}>
                  <i className="ri-close-line me-1"></i> Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'luogo_di_allenamento', modalValue)}
                  disabled={saving}
                >
                  {saving ? <><i className="ri-loader-4-line spin me-1"></i> Salvando...</> : <><i className="ri-save-line me-1"></i> Salva</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ClientiListaCoach;

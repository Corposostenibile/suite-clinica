import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import clientiService, {
  GIORNI_LABELS,
  STATI_PROFESSIONISTA_COLORS,
  LUOGO_LABELS,
} from '../../services/clientiService';
import teamService from '../../services/teamService';

// Stili per la tabella professionale (stesso stile di ClientiList)
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
  statoBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'capitalize',
  },
  btnEditInline: {
    padding: '4px 8px',
    fontSize: '12px',
    borderRadius: '6px',
    background: 'rgba(0,0,0,0.04)',
    color: '#64748b',
    border: 'none',
    cursor: 'pointer',
    marginLeft: '6px',
    transition: 'all 0.15s ease',
  },
  btnSmall: {
    padding: '6px 12px',
    fontSize: '12px',
    borderRadius: '8px',
    color: 'white',
    border: 'none',
    transition: 'all 0.2s ease',
    cursor: 'pointer',
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
  const renderTeamAvatar = (member, roleKey, roleLabel) => {
    if (!member) return null;
    const colors = ROLE_COLORS[roleKey] || ROLE_COLORS.c;
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

  // Render stato badge
  const renderStatoBadge = (stato, type = 'coach') => {
    if (!stato) return <span style={tableStyles.emptyCell}>—</span>;
    const colors = STATI_PROFESSIONISTA_COLORS[stato] || { bg: '#f1f5f9', color: '#64748b' };
    return (
      <span style={{ ...tableStyles.statoBadge, background: colors.bg, color: colors.color }}>
        <i className={type === 'chat' ? 'ri-chat-3-line' : 'ri-circle-fill'} style={{ fontSize: type === 'chat' ? '10px' : '6px' }}></i>
        {stato}
      </span>
    );
  };

  // Render luogo badge
  const renderLuogoBadge = (luogo) => {
    if (!luogo) return <span style={tableStyles.emptyCell}>—</span>;
    const colors = LUOGO_COLORS[luogo] || { bg: '#f1f5f9', color: '#64748b' };
    return (
      <span style={{ ...tableStyles.statoBadge, background: colors.bg, color: colors.color }}>
        <i className={luogo === 'casa' ? 'ri-home-line' : luogo === 'palestra' ? 'ri-building-line' : 'ri-exchange-line'}></i>
        {LUOGO_LABELS[luogo] || luogo}
      </span>
    );
  };

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4">
        <div>
          <h4 className="mb-1">Visuale Coach</h4>
          <p className="text-muted mb-0">{pagination.total} pazienti totali</p>
        </div>
        <div className="d-flex flex-wrap gap-2">
          <Link to="/clienti-lista" className="btn btn-primary px-3">
            <i className="ri-group-line me-2"></i>
            Lista Generale
          </Link>
          <Link to="/clienti-nutrizione" className="btn btn-success px-3">
            <i className="ri-restaurant-line me-2"></i>
            Visuale Nutrizione
          </Link>
          <Link to="/clienti-psicologia" className="btn px-3" style={{ backgroundColor: '#8b5cf6', color: 'white' }}>
            <i className="ri-mental-health-line me-2"></i>
            Visuale Psicologia
          </Link>
          <Link to="/clienti-nuovo" className="btn btn-primary px-4">
            <i className="ri-user-add-line me-2"></i>
            Aggiungi Paziente
          </Link>
        </div>
      </div>

      {/* Stats Row */}
      <div className="row g-3 mb-4">
        {[
          { label: 'Stato Attivo', value: kpi.stato_attivo, icon: 'ri-run-line', bg: 'success' },
          { label: 'Stato Ghost', value: kpi.stato_ghost, icon: 'ri-ghost-line', bg: 'secondary' },
          { label: 'Stato Pausa', value: kpi.stato_pausa, icon: 'ri-pause-circle-line', bg: 'warning' },
          { label: 'Stato Stop', value: kpi.stato_stop, icon: 'ri-stop-circle-line', bg: 'danger' },
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
                value={filters.coach}
                onChange={(e) => handleFilterChange('coach', e.target.value)}
              >
                <option value="">Coach</option>
                {coaches.map(c => (
                  <option key={c.id} value={c.id}>{c.full_name}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.statoCoach}
                onChange={(e) => handleFilterChange('statoCoach', e.target.value)}
              >
                <option value="">Stato Coach</option>
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
              <i className="ri-run-line" style={{ fontSize: '5rem', color: '#cbd5e1' }}></i>
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
                    <th style={{ ...tableStyles.th, minWidth: '180px' }}>Paziente</th>
                    <th style={{ ...tableStyles.th, minWidth: '100px' }}>Team</th>
                    <th style={{ ...tableStyles.th, minWidth: '130px' }}>Stato Coach</th>
                    <th style={{ ...tableStyles.th, minWidth: '130px' }}>Stato Chat</th>
                    <th style={{ ...tableStyles.th, minWidth: '120px' }}>Check Day</th>
                    <th style={{ ...tableStyles.th, minWidth: '120px' }}>Reach Out</th>
                    <th style={{ ...tableStyles.th, minWidth: '100px' }}>Luogo</th>
                    <th style={{ ...tableStyles.th, minWidth: '100px', textAlign: 'center' }}>Piano</th>
                    <th style={{ ...tableStyles.th, minWidth: '100px', textAlign: 'center' }}>Storia</th>
                    <th style={{ ...tableStyles.th, textAlign: 'right', minWidth: '100px' }}>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {clienti.map((cliente, index) => {
                    const clienteId = cliente.cliente_id || cliente.clienteId;
                    const nomeCognome = cliente.nome_cognome || cliente.nomeCognome || 'N/D';
                    const isHovered = hoveredRow === index;

                    // Team members
                    const healthManager = cliente.health_manager_user || cliente.healthManagerUser;
                    const coachesList = cliente.coaches_multipli || cliente.coachesMultipli || [];
                    const nutrizionistiList = cliente.nutrizionisti_multipli || cliente.nutrizionistiMultipli || [];
                    const psicologiList = cliente.psicologi_multipli || cliente.psicologiMultipli || [];
                    const consulentiList = cliente.consulenti_multipli || cliente.consulentiMultipli || [];
                    const hasTeam = healthManager || coachesList.length > 0 || nutrizionistiList.length > 0 || psicologiList.length > 0 || consulentiList.length > 0;

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
                        {/* Nome */}
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
                          <div style={{ display: 'flex', alignItems: 'center', flexDirection: 'row', flexWrap: 'nowrap' }}>
                            {healthManager && renderTeamAvatar(healthManager, 'hm', 'Health Manager')}
                            {coachesList.map(c => renderTeamAvatar(c, 'c', 'Coach'))}
                            {nutrizionistiList.map(n => renderTeamAvatar(n, 'n', 'Nutrizionista'))}
                            {psicologiList.map(p => renderTeamAvatar(p, 'p', 'Psicologo'))}
                            {consulentiList.map(ca => renderTeamAvatar(ca, 'ca', 'Consulente'))}
                            {!hasTeam && <span style={tableStyles.emptyCell}>—</span>}
                          </div>
                        </td>

                        {/* Stato Coach */}
                        <td style={tableStyles.td}>
                          <div className="d-flex align-items-center">
                            {renderStatoBadge(cliente.stato_coach, 'coach')}
                            <button
                              style={tableStyles.btnEditInline}
                              onClick={() => openStatoModal(cliente)}
                              title="Modifica stato"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>

                        {/* Stato Chat */}
                        <td style={tableStyles.td}>
                          <div className="d-flex align-items-center">
                            {renderStatoBadge(cliente.stato_cliente_chat_coaching, 'chat')}
                            <button
                              style={tableStyles.btnEditInline}
                              onClick={() => openChatModal(cliente)}
                              title="Modifica stato chat"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>

                        {/* Check Day */}
                        <td style={tableStyles.td}>
                          <div className="d-flex align-items-center">
                            {cliente.check_day ? (
                              <span style={{
                                ...tableStyles.badge,
                                background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
                                color: '#1e40af',
                              }}>
                                <i className="ri-calendar-check-line me-1"></i>
                                {GIORNI_LABELS[cliente.check_day] || cliente.check_day}
                              </span>
                            ) : (
                              <span style={tableStyles.emptyCell}>—</span>
                            )}
                            <button
                              style={tableStyles.btnEditInline}
                              onClick={() => openCheckDayModal(cliente)}
                              title="Modifica check day"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>

                        {/* Reach Out */}
                        <td style={tableStyles.td}>
                          <div className="d-flex align-items-center">
                            {cliente.reach_out_coaching ? (
                              <span style={{
                                ...tableStyles.badge,
                                background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
                                color: '#92400e',
                              }}>
                                <i className="ri-calendar-event-line me-1"></i>
                                {GIORNI_LABELS[cliente.reach_out_coaching] || cliente.reach_out_coaching}
                              </span>
                            ) : (
                              <span style={tableStyles.emptyCell}>—</span>
                            )}
                            <button
                              style={tableStyles.btnEditInline}
                              onClick={() => openReachOutModal(cliente)}
                              title="Modifica reach out"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>

                        {/* Luogo */}
                        <td style={tableStyles.td}>
                          <div className="d-flex align-items-center">
                            {renderLuogoBadge(cliente.luogo_di_allenamento)}
                            <button
                              style={tableStyles.btnEditInline}
                              onClick={() => openLuogoModal(cliente)}
                              title="Modifica luogo"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>

                        {/* Piano Allenamento */}
                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                          <button
                            style={{
                              ...tableStyles.btnSmall,
                              background: cliente.piano_allenamento
                                ? 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)'
                                : 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                            }}
                            onClick={() => openPianoAllenamentoModal(cliente)}
                          >
                            <i className={`ri-file-list-line ${cliente.piano_allenamento ? '' : 'me-1'}`}></i>
                            {!cliente.piano_allenamento && '+'}
                          </button>
                        </td>

                        {/* Storia */}
                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                          <button
                            style={{
                              ...tableStyles.btnSmall,
                              background: cliente.storia_coaching
                                ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
                                : 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                            }}
                            onClick={() => openStoriaModal(cliente)}
                          >
                            <i className={`ri-file-text-line ${cliente.storia_coaching ? '' : 'me-1'}`}></i>
                            {!cliente.storia_coaching && '+'}
                          </button>
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
                            to={`/clienti-dettaglio/${clienteId}#coaching`}
                            style={{
                              ...tableStyles.actionBtn,
                              borderColor: '#f97316',
                              color: '#f97316',
                              background: isHovered ? 'rgba(249, 115, 22, 0.1)' : 'transparent',
                            }}
                            title="Tab Coaching"
                          >
                            <i className="ri-run-line" style={{ fontSize: '16px' }}></i>
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
                            background: isActive ? 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' : 'transparent',
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

      {/* Modal Storia Coaching */}
      {showStoriaModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-file-text-line me-2"></i>
                  Storia Coaching - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowStoriaModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <textarea
                  className="form-control"
                  rows="12"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  placeholder="Inserisci la storia coaching..."
                  style={{ border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
                ></textarea>
              </div>
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowStoriaModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'storia_coaching', modalValue)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
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
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-sticky-note-line me-2"></i>
                  Note Extra - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowNoteModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <textarea
                  className="form-control"
                  rows="12"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  placeholder="Inserisci note extra..."
                  style={{ border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
                ></textarea>
              </div>
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowNoteModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'note_extra_coach', modalValue)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
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
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-circle-fill me-2"></i>
                  Stato Coach - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowStatoModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
                >
                  <option value="">-- Nessuno --</option>
                  <option value="attivo">Attivo</option>
                  <option value="pausa">Pausa</option>
                  <option value="ghost">Ghost</option>
                  <option value="stop">Stop</option>
                </select>
              </div>
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowStatoModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'stato_coach', modalValue)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
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
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-chat-3-line me-2"></i>
                  Stato Chat - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowChatModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
                >
                  <option value="">-- Nessuno --</option>
                  <option value="attivo">Attivo</option>
                  <option value="pausa">Pausa</option>
                  <option value="ghost">Ghost</option>
                  <option value="stop">Stop</option>
                </select>
              </div>
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowChatModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'stato_cliente_chat_coaching', modalValue)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
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
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-calendar-check-line me-2"></i>
                  Check Day - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowCheckDayModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
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
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowCheckDayModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'check_day', modalValue)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
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
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-calendar-event-line me-2"></i>
                  Reach Out - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowReachOutModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
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
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowReachOutModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'reach_out_coaching', modalValue)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
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
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-file-list-line me-2"></i>
                  Piano Allenamento - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowPianoAllenamentoModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <textarea
                  className="form-control"
                  rows="12"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  placeholder="Inserisci il piano di allenamento..."
                  style={{ border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
                ></textarea>
              </div>
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowPianoAllenamentoModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'piano_allenamento', modalValue)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
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
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-map-pin-line me-2"></i>
                  Luogo Allenamento - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowLuogoModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <select
                  className="form-select"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
                >
                  <option value="">-- Seleziona --</option>
                  <option value="casa">Casa</option>
                  <option value="palestra">Palestra</option>
                  <option value="ibrido">Ibrido</option>
                </select>
              </div>
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowLuogoModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'luogo_di_allenamento', modalValue)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
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

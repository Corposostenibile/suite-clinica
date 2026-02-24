import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import clientiService, {
  GIORNI_LABELS,
  STATI_PROFESSIONISTA_COLORS,
  PATOLOGIE_PSICO,
} from '../../services/clientiService';
import teamService from '../../services/teamService';
import './clienti-responsive.css';
import './clienti-table.css';

// Stili per la tabella professionale (stesso stile di ClientiList)
// tableStyles rimosso — ora in clienti-table.css (classi ct-*)

// Role colors for avatars
const ROLE_COLORS = {
  hm: { bg: '#f3e8ff', text: '#9333ea', badge: '#9333ea' },
  n: { bg: '#dcfce7', text: '#16a34a', badge: '#22c55e' },
  c: { bg: '#dbeafe', text: '#2563eb', badge: '#3b82f6' },
  p: { bg: '#fce7f3', text: '#db2777', badge: '#ec4899' },
  ca: { bg: '#fef3c7', text: '#d97706', badge: '#f59e0b' },
};

function ClientiListaPsicologia() {
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
  const [psicologi, setPsicologi] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 25,
    total: 0,
    totalPages: 0,
  });

  const [filters, setFilters] = useState({
    search: searchParams.get('q') || '',
    psicologo: searchParams.get('psicologa_id') || '',
    statoPsicologia: searchParams.get('stato_psicologia') || '',
    reachOut: searchParams.get('reach_out_psicologia') || '',
  });

  // Modal states
  const [showStoriaModal, setShowStoriaModal] = useState(false);
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [showPatologieModal, setShowPatologieModal] = useState(false);
  const [showStatoModal, setShowStatoModal] = useState(false);
  const [showChatModal, setShowChatModal] = useState(false);
  const [showReachOutModal, setShowReachOutModal] = useState(false);
  const [showSeduteComprateModal, setShowSeduteComprateModal] = useState(false);
  const [showSeduteSvolteModal, setShowSeduteSvolteModal] = useState(false);
  const [selectedCliente, setSelectedCliente] = useState(null);
  const [modalValue, setModalValue] = useState('');
  const [saving, setSaving] = useState(false);

  // Fetch psicologi on mount
  useEffect(() => {
    const fetchPsicologi = async () => {
      try {
        const data = await teamService.getTeamMembers({
          per_page: 100,
          active: '1',
          specialty: 'psicologia',
        });
        setPsicologi(data.members || []);
      } catch (err) {
        console.error('Error fetching psicologi:', err);
      }
    };
    fetchPsicologi();
  }, []);

  const fetchClienti = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page: pagination.page,
        per_page: pagination.perPage,
        q: filters.search || undefined,
        psicologa_id: filters.psicologo || undefined,
        stato_psicologia: filters.statoPsicologia || undefined,
        reach_out_psicologia: filters.reachOut || undefined,
      };

      const data = await clientiService.getClientiPsicologia(params);
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
          stato_attivo: clientiData.filter(c => c.stato_psicologia === 'attivo').length,
          stato_ghost: clientiData.filter(c => c.stato_psicologia === 'ghost').length,
          stato_pausa: clientiData.filter(c => c.stato_psicologia === 'pausa').length,
          stato_stop: clientiData.filter(c => c.stato_psicologia === 'stop').length,
          chat_attivo: clientiData.filter(c => c.stato_cliente_chat_psicologia === 'attivo').length,
          chat_ghost: clientiData.filter(c => c.stato_cliente_chat_psicologia === 'ghost').length,
          chat_pausa: clientiData.filter(c => c.stato_cliente_chat_psicologia === 'pausa').length,
          chat_stop: clientiData.filter(c => c.stato_cliente_chat_psicologia === 'stop').length,
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
      key === 'psicologo' ? 'psicologa_id' :
        key === 'statoPsicologia' ? 'stato_psicologia' :
          key === 'reachOut' ? 'reach_out_psicologia' : key;
    if (value) {
      newParams.set(paramKey, value);
    } else {
      newParams.delete(paramKey);
    }
    setSearchParams(newParams);
  };

  const resetFilters = () => {
    setFilters({ search: '', psicologo: '', statoPsicologia: '', reachOut: '' });
    setSearchParams(new URLSearchParams());
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, page: newPage }));
  };

  // Get patologie for a client
  const getClientPatologie = (cliente) => {
    return PATOLOGIE_PSICO.filter(p => cliente[p.key]).map(p => p.label);
  };

  // Handle field update
  const handleUpdateField = async (clienteId, field, value) => {
    setSaving(true);
    try {
      await clientiService.updateField(clienteId, field, value === '' ? null : value);
      fetchClienti();
      setShowStoriaModal(false);
      setShowNoteModal(false);
      setShowStatoModal(false);
      setShowChatModal(false);
      setShowReachOutModal(false);
      setShowSeduteComprateModal(false);
      setShowSeduteSvolteModal(false);
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
    setModalValue(cliente.storia_psicologia || '');
    setShowStoriaModal(true);
  };

  const openNoteModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.note_extra_psicologa || '');
    setShowNoteModal(true);
  };

  const openStatoModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.stato_psicologia || '');
    setShowStatoModal(true);
  };

  const openChatModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.stato_cliente_chat_psicologia || '');
    setShowChatModal(true);
  };

  const openReachOutModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.reach_out_psicologia || '');
    setShowReachOutModal(true);
  };

  const openSeduteComprateModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.sedute_psicologia_comprate?.toString() || '0');
    setShowSeduteComprateModal(true);
  };

  const openSeduteSvolteModal = (cliente) => {
    setSelectedCliente(cliente);
    setModalValue(cliente.sedute_psicologia_svolte?.toString() || '0');
    setShowSeduteSvolteModal(true);
  };

  // Render avatar team
  const renderTeamAvatar = (member, roleKey, roleLabel) => {
    if (!member) return null;
    const colors = ROLE_COLORS[roleKey] || ROLE_COLORS.p;
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

  // Render stato badge
  const renderStatoBadge = (stato, type = 'psico') => {
    if (!stato) return <span className="ct-empty">—</span>;
    const colors = STATI_PROFESSIONISTA_COLORS[stato] || { bg: '#f1f5f9', color: '#64748b' };
    return (
      <span className="ct-stato-badge" style={{ background: colors.bg, color: colors.color }}>
        <i className={type === 'chat' ? 'ri-chat-3-line' : 'ri-circle-fill'} style={{ fontSize: type === 'chat' ? '10px' : '6px' }}></i>
        {stato}
      </span>
    );
  };

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4">
        <div>
          <h4 className="mb-1">Visuale Psicologia</h4>
          <p className="text-muted mb-0">{pagination.total} pazienti totali</p>
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
          <Link to="/clienti-nuovo" className="btn btn-primary btn-sm ms-2">
            <i className="ri-user-add-line me-1"></i> Aggiungi
          </Link>
        </div>
      </div>

      {/* Stats Row */}
      <div className="d-flex align-items-center mb-2 d-md-none text-muted small bg-light p-2 rounded-3" style={{ width: 'fit-content' }}>
        <i className="ri-drag-move-fill me-2 fs-5"></i> Scorri le schede KPI
      </div>
      <div className="row g-3 mb-4 clienti-stats-row mobile-kpi-scroll">
        {[
          { label: 'Stato Attivo', value: kpi.stato_attivo, icon: 'ri-mental-health-line', bg: 'success' },
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
            <div className="col-lg-4">
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
                value={filters.psicologo}
                onChange={(e) => handleFilterChange('psicologo', e.target.value)}
              >
                <option value="">Psicologo</option>
                {psicologi.map(p => (
                  <option key={p.id} value={p.id}>{p.full_name}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.statoPsicologia}
                onChange={(e) => handleFilterChange('statoPsicologia', e.target.value)}
              >
                <option value="">Stato Psicologia</option>
                <option value="attivo">Attivo</option>
                <option value="pausa">Pausa</option>
                <option value="ghost">Ghost</option>
                <option value="stop">Stop</option>
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
            <div className="col-lg-2">
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
              <i className="ri-mental-health-line" style={{ fontSize: '5rem', color: '#cbd5e1' }}></i>
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
          <div className="card border-0 clienti-table-wrap ct-card">
            <div className="table-responsive">
              <table className="table mb-0 clienti-table">
                <thead className="ct-thead">
                  <tr>
                    <th className="ct-th" style={{ minWidth: '180px' }}>Paziente</th>
                    <th className="ct-th" style={{ minWidth: '100px' }}>Team</th>
                    <th className="ct-th" style={{ minWidth: '130px' }}>Stato Psico</th>
                    <th className="ct-th" style={{ minWidth: '130px' }}>Stato Chat</th>
                    <th className="ct-th" style={{ minWidth: '120px' }}>Reach Out</th>
                    <th className="ct-th" style={{ minWidth: '90px', textAlign: 'center' }}>Patologie</th>
                    <th className="ct-th" style={{ minWidth: '80px', textAlign: 'center' }}>Comprate</th>
                    <th className="ct-th" style={{ minWidth: '80px', textAlign: 'center' }}>Svolte</th>
                    <th className="ct-th" style={{ minWidth: '80px', textAlign: 'center' }}>Storia</th>
                    <th className="ct-th" style={{ textAlign: 'right', minWidth: '100px' }}>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {clienti.map((cliente, index) => {
                    const clienteId = cliente.cliente_id || cliente.clienteId;
                    const nomeCognome = cliente.nome_cognome || cliente.nomeCognome || 'N/D';
                    const isHovered = hoveredRow === index;
                    const patologie = getClientPatologie(cliente);
                    const seduteComprate = cliente.sedute_psicologia_comprate || 0;
                    const seduteSvolte = cliente.sedute_psicologia_svolte || 0;

                    // Team members
                    const healthManager = cliente.health_manager_user || cliente.healthManagerUser;
                    const psicologiList = cliente.psicologi_multipli || cliente.psicologiMultipli || [];
                    const nutrizionistiList = cliente.nutrizionisti_multipli || cliente.nutrizionistiMultipli || [];
                    const coachesList = cliente.coaches_multipli || cliente.coachesMultipli || [];
                    const consulentiList = cliente.consulenti_multipli || cliente.consulentiMultipli || [];
                    const hasTeam = healthManager || psicologiList.length > 0 || nutrizionistiList.length > 0 || coachesList.length > 0 || consulentiList.length > 0;

                    return (
                      <tr
                        key={clienteId}
                        className="ct-row"
                        style={{ background: isHovered ? '#f8fafc' : 'transparent' }}
                        onMouseEnter={() => setHoveredRow(index)}
                        onMouseLeave={() => setHoveredRow(null)}
                      >
                        {/* Nome */}
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
                          <div style={{ display: 'flex', alignItems: 'center', flexDirection: 'row', flexWrap: 'nowrap' }}>
                            {healthManager && renderTeamAvatar(healthManager, 'hm', 'Health Manager')}
                            {psicologiList.map(p => renderTeamAvatar(p, 'p', 'Psicologo'))}
                            {nutrizionistiList.map(n => renderTeamAvatar(n, 'n', 'Nutrizionista'))}
                            {coachesList.map(c => renderTeamAvatar(c, 'c', 'Coach'))}
                            {consulentiList.map(ca => renderTeamAvatar(ca, 'ca', 'Consulente'))}
                            {!hasTeam && <span className="ct-empty">—</span>}
                          </div>
                        </td>

                        {/* Stato Psicologia */}
                        <td className="ct-td" data-label="Stato Psico">
                          <div className="d-flex align-items-center">
                            {renderStatoBadge(cliente.stato_psicologia, 'psico')}
                            <button
                              className="ct-btn-edit"
                              onClick={() => openStatoModal(cliente)}
                              title="Modifica stato"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>

                        {/* Stato Chat */}
                        <td className="ct-td" data-label="Stato Chat">
                          <div className="d-flex align-items-center">
                            {renderStatoBadge(cliente.stato_cliente_chat_psicologia, 'chat')}
                            <button
                              className="ct-btn-edit"
                              onClick={() => openChatModal(cliente)}
                              title="Modifica stato chat"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>

                        {/* Reach Out */}
                        <td className="ct-td" data-label="Reach Out">
                          <div className="d-flex align-items-center">
                            {cliente.reach_out_psicologia ? (
                              <span className="ct-reach-out-badge">
                                <i className="ri-calendar-event-line me-1"></i>
                                {GIORNI_LABELS[cliente.reach_out_psicologia] || cliente.reach_out_psicologia}
                              </span>
                            ) : (
                              <span className="ct-empty">—</span>
                            )}
                            <button
                              className="ct-btn-edit"
                              onClick={() => openReachOutModal(cliente)}
                              title="Modifica reach out"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>

                        {/* Patologie */}
                        <td className="ct-td" style={{ textAlign: 'center' }} data-label="Patologie">
                          {patologie.length > 0 ? (
                            <button
                              className="ct-btn-sm"
                              style={{ background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)' }}
                              onClick={() => {
                                setSelectedCliente(cliente);
                                setShowPatologieModal(true);
                              }}
                            >
                              <i className="ri-brain-line me-1"></i>
                              {patologie.length}
                            </button>
                          ) : cliente.nessuna_patologia_psicologica ? (
                            <span
                              className="ct-btn-sm"
                              style={{
                                background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
                                color: '#166534',
                                cursor: 'default',
                              }}
                            >
                              <i className="ri-checkbox-circle-line"></i>
                            </span>
                          ) : (
                            <button
                              className="ct-btn-sm"
                              style={{ background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)' }}
                              onClick={() => {
                                setSelectedCliente(cliente);
                                setShowPatologieModal(true);
                              }}
                            >
                              <i className="ri-brain-line"></i>
                            </button>
                          )}
                        </td>

                        {/* Sedute Comprate */}
                        <td className="ct-td" style={{ textAlign: 'center' }} data-label="Comprate">
                          <div className="d-flex align-items-center justify-content-center gap-1">
                            <span
                              className="ct-sedute-badge"
                              style={{
                                background: seduteComprate > 0
                                  ? 'linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%)'
                                  : '#f1f5f9',
                                color: seduteComprate > 0 ? '#be185d' : '#64748b',
                              }}
                            >
                              {seduteComprate}
                            </span>
                            <button
                              className="ct-btn-edit"
                              onClick={() => openSeduteComprateModal(cliente)}
                              title="Modifica sedute comprate"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>

                        {/* Sedute Svolte */}
                        <td className="ct-td" style={{ textAlign: 'center' }} data-label="Svolte">
                          <div className="d-flex align-items-center justify-content-center gap-1">
                            <span
                              className="ct-sedute-badge"
                              style={{
                                background: seduteSvolte > 0
                                  ? 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)'
                                  : '#f1f5f9',
                                color: seduteSvolte > 0 ? '#166534' : '#64748b',
                              }}
                            >
                              {seduteSvolte}
                            </span>
                            <button
                              className="ct-btn-edit"
                              onClick={() => openSeduteSvolteModal(cliente)}
                              title="Modifica sedute svolte"
                            >
                              <i className="ri-pencil-line"></i>
                            </button>
                          </div>
                        </td>

                        {/* Storia */}
                        <td className="ct-td" style={{ textAlign: 'center' }} data-label="Storia">
                          <button
                            className="ct-btn-sm"
                            style={{
                              background: cliente.storia_psicologia
                                ? 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)'
                                : 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
                            }}
                            onClick={() => openStoriaModal(cliente)}
                          >
                            <i className={`ri-file-text-line ${cliente.storia_psicologia ? '' : 'me-1'}`}></i>
                            {!cliente.storia_psicologia && '+'}
                          </button>
                        </td>

                        {/* Azioni */}
                        <td className="ct-td" style={{ textAlign: 'right' }} data-label="Azioni">
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
                            to={`/clienti-dettaglio/${clienteId}#psicologia`}
                            className="ct-action-btn"
                            style={{
                              borderColor: '#ec4899',
                              color: '#ec4899',
                              background: isHovered ? 'rgba(236, 72, 153, 0.1)' : 'transparent',
                            }}
                            title="Tab Psicologia"
                          >
                            <i className="ri-mental-health-line" style={{ fontSize: '16px' }}></i>
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
                            background: isActive ? 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)' : 'transparent',
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

      {/* Modal Storia Psicologia */}
      {showStoriaModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-file-text-line me-2"></i>
                  Storia Psicologia - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowStoriaModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <textarea
                  className="form-control"
                  rows="12"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  placeholder="Inserisci la storia psicologia..."
                  style={{ border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
                ></textarea>
              </div>
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowStoriaModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'storia_psicologia', modalValue)}
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
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'note_extra_psicologa', modalValue)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Stato Psicologia */}
      {showStatoModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-circle-fill me-2"></i>
                  Stato Psicologia - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
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
                  style={{ background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'stato_psicologia', modalValue)}
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
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'stato_cliente_chat_psicologia', modalValue)}
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
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'reach_out_psicologia', modalValue)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Sedute Comprate */}
      {showSeduteComprateModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-shopping-cart-line me-2"></i>
                  Sedute Comprate - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowSeduteComprateModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <input
                  type="number"
                  min="0"
                  className="form-control"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
                />
              </div>
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowSeduteComprateModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'sedute_psicologia_comprate', parseInt(modalValue) || 0)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Sedute Svolte */}
      {showSeduteSvolteModal && selectedCliente && (
        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-checkbox-circle-line me-2"></i>
                  Sedute Svolte - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowSeduteSvolteModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <input
                  type="number"
                  min="0"
                  className="form-control"
                  value={modalValue}
                  onChange={(e) => setModalValue(e.target.value)}
                  style={{ height: '46px', border: '2px solid #e2e8f0', borderRadius: '12px', fontSize: '14px' }}
                />
              </div>
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowSeduteSvolteModal(false)}>
                  Chiudi
                </button>
                <button
                  type="button"
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', borderRadius: '10px' }}
                  onClick={() => handleUpdateField(selectedCliente.cliente_id || selectedCliente.clienteId, 'sedute_psicologia_svolte', parseInt(modalValue) || 0)}
                  disabled={saving}
                >
                  {saving ? 'Salvando...' : 'Salva'}
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
            <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
              <div className="modal-header" style={{ background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', borderRadius: '16px 16px 0 0' }}>
                <h5 className="modal-title text-white">
                  <i className="ri-brain-line me-2"></i>
                  Patologie - {selectedCliente.nome_cognome || selectedCliente.nomeCognome}
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowPatologieModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                {getClientPatologie(selectedCliente).length > 0 ? (
                  <div className="d-flex flex-wrap gap-2">
                    {getClientPatologie(selectedCliente).map((p, i) => (
                      <span key={i} className="ct-patologia-tag">
                        <i className="ri-brain-fill"></i>
                        {p}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4">
                    <i className="ri-brain-line text-muted" style={{ fontSize: '48px' }}></i>
                    <p className="text-muted mt-2 mb-0">Nessuna patologia psicologica registrata</p>
                  </div>
                )}
              </div>
              <div className="modal-footer" style={{ borderTop: '1px solid #f1f5f9' }}>
                <button type="button" className="btn btn-secondary" style={{ borderRadius: '10px' }} onClick={() => setShowPatologieModal(false)}>
                  Chiudi
                </button>
                <Link
                  to={`/clienti-dettaglio/${selectedCliente.cliente_id || selectedCliente.clienteId}#psicologia`}
                  className="btn text-white"
                  style={{ background: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)', borderRadius: '10px' }}
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

export default ClientiListaPsicologia;

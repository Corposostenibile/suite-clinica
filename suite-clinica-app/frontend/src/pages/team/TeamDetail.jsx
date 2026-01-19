import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import teamService, {
  ROLE_LABELS,
  SPECIALTY_LABELS,
  ROLE_COLORS,
  SPECIALTY_COLORS
} from '../../services/teamService';

// Client status colors
const STATO_COLORS = {
  'In prova': { bg: '#fef3c7', color: '#92400e', icon: 'ri-timer-line' },
  'Attivo': { bg: '#dcfce7', color: '#166534', icon: 'ri-checkbox-circle-line' },
  'Non attivo': { bg: '#fee2e2', color: '#991b1b', icon: 'ri-close-circle-line' },
  'In pausa': { bg: '#e0e7ff', color: '#3730a3', icon: 'ri-pause-circle-line' },
  'Freeze': { bg: '#e0f2fe', color: '#0369a1', icon: 'ri-snowflake-line' },
};

// Gradient colors by role (same as TeamList)
const ROLE_GRADIENTS = {
  admin: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  team_leader: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  professionista: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  team_esterno: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
};

function TeamDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [member, setMember] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('info');

  // Clienti tab state
  const [clients, setClients] = useState([]);
  const [clientsLoading, setClientsLoading] = useState(false);
  const [clientsError, setClientsError] = useState(null);
  const [clientsPage, setClientsPage] = useState(1);
  const [clientsTotal, setClientsTotal] = useState(0);
  const [clientsTotalPages, setClientsTotalPages] = useState(0);
  const [clientsSearch, setClientsSearch] = useState('');
  const [clientsStato, setClientsStato] = useState('');
  const PER_PAGE = 5;

  useEffect(() => {
    fetchMember();
  }, [id]);

  // Fetch clients when tab changes to 'clienti' or when filters change
  useEffect(() => {
    if (activeTab === 'clienti' && id) {
      fetchClients();
    }
  }, [activeTab, id, clientsPage, clientsStato]);

  // Debounced search
  useEffect(() => {
    if (activeTab !== 'clienti') return;
    const timer = setTimeout(() => {
      setClientsPage(1);
      fetchClients();
    }, 300);
    return () => clearTimeout(timer);
  }, [clientsSearch]);

  const fetchMember = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await teamService.getTeamMember(id);
      setMember(data);
    } catch (err) {
      console.error('Error fetching team member:', err);
      setError('Errore nel caricamento dei dati');
    } finally {
      setLoading(false);
    }
  };

  const fetchClients = async () => {
    setClientsLoading(true);
    setClientsError(null);
    try {
      const params = {
        page: clientsPage,
        per_page: PER_PAGE,
      };
      if (clientsSearch) params.q = clientsSearch;
      if (clientsStato) params.stato = clientsStato;

      const data = await teamService.getMemberClients(id, params);
      if (data.success) {
        setClients(data.clients || []);
        setClientsTotal(data.total || 0);
        setClientsTotalPages(data.total_pages || 0);
      } else {
        setClientsError('Errore nel caricamento dei clienti');
      }
    } catch (err) {
      console.error('Error fetching clients:', err);
      setClientsError('Errore nel caricamento dei clienti');
    } finally {
      setClientsLoading(false);
    }
  };

  const handleToggleStatus = async () => {
    try {
      await teamService.toggleTeamMemberStatus(id);
      fetchMember();
    } catch (err) {
      console.error('Error toggling status:', err);
    }
  };

  const getRole = () => member?.role || 'professionista';
  const getSpecialty = () => member?.specialty;

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Caricamento...</span>
        </div>
      </div>
    );
  }

  if (error && !member) {
    return (
      <div className="alert alert-danger d-flex align-items-center">
        <i className="ri-error-warning-line me-2 fs-4"></i>
        <div className="flex-grow-1">{error}</div>
        <Link to="/team-lista" className="btn btn-sm btn-outline-danger">
          Torna alla Lista
        </Link>
      </div>
    );
  }

  const role = getRole();
  const specialty = getSpecialty();

  return (
    <>
      {/* Page Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1">Dettaglio Membro</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/team-lista">Team</Link>
              </li>
              <li className="breadcrumb-item active">{member?.full_name}</li>
            </ol>
          </nav>
        </div>
        <div className="d-flex gap-2">
          <Link to="/team-lista" className="btn btn-outline-secondary">
            <i className="ri-arrow-left-line me-1"></i>
            Torna alla Lista
          </Link>
          <Link to={`/team-modifica/${id}`} className="btn btn-primary">
            <i className="ri-edit-line me-1"></i>
            Modifica
          </Link>
        </div>
      </div>

      <div className="row g-4">
        {/* Profile Card with Gradient Header */}
        <div className="col-lg-4">
          <div className="card shadow-sm border-0 overflow-hidden">
            {/* Gradient Header */}
            <div
              className="position-relative"
              style={{
                background: ROLE_GRADIENTS[role] || ROLE_GRADIENTS.professionista,
                height: '120px'
              }}
            >
              {/* Status badges */}
              <div className="position-absolute top-0 start-0 p-3 d-flex gap-2">
                {member?.is_active ? (
                  <span className="badge bg-success">
                    <i className="ri-checkbox-circle-line me-1"></i>Attivo
                  </span>
                ) : (
                  <span className="badge bg-dark bg-opacity-75">
                    <i className="ri-close-circle-line me-1"></i>Inattivo
                  </span>
                )}
                {member?.is_external && (
                  <span className="badge bg-white text-dark">
                    <i className="ri-external-link-line me-1"></i>Esterno
                  </span>
                )}
              </div>

              {/* Avatar positioned at bottom */}
              <div className="position-absolute start-50 translate-middle-x" style={{ bottom: '-50px' }}>
                {member?.avatar_path ? (
                  <img
                    src={member.avatar_path}
                    alt={member.full_name}
                    className="rounded-circle border border-4 border-white shadow"
                    style={{ width: '100px', height: '100px', objectFit: 'cover', background: '#fff' }}
                  />
                ) : (
                  <div
                    className="rounded-circle border border-4 border-white shadow d-flex align-items-center justify-content-center"
                    style={{ width: '100px', height: '100px', background: '#fff' }}
                  >
                    <span className="fw-bold text-primary" style={{ fontSize: '2rem' }}>
                      {member?.first_name?.[0]?.toUpperCase()}{member?.last_name?.[0]?.toUpperCase()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Card Body */}
            <div className="card-body text-center pt-5 mt-3">
              <h4 className="mb-1">{member?.full_name}</h4>
              <p className="text-muted mb-3">{member?.email}</p>

              {/* Role & Specialty Badges */}
              <div className="d-flex justify-content-center gap-2 mb-4">
                <span className={`badge bg-${ROLE_COLORS[role] || 'secondary'}`}>
                  {ROLE_LABELS[role] || role}
                </span>
                {specialty && (
                  <span className={`badge bg-${SPECIALTY_COLORS[specialty] || 'secondary'}-subtle text-${SPECIALTY_COLORS[specialty] || 'secondary'}`}>
                    {SPECIALTY_LABELS[specialty] || specialty}
                  </span>
                )}
              </div>

              {/* Quick Stats */}
              <div className="row g-3 mb-4">
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">ID Utente</div>
                    <div className="fw-semibold">#{member?.id}</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">Team Guidati</div>
                    <div className="fw-semibold">{member?.teams_led?.length || 0}</div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="d-grid">
                <button
                  className={`btn ${member?.is_active ? 'btn-outline-danger' : 'btn-outline-success'}`}
                  onClick={handleToggleStatus}
                >
                  <i className={`ri-${member?.is_active ? 'user-unfollow' : 'user-follow'}-line me-2`}></i>
                  {member?.is_active ? 'Disattiva Account' : 'Attiva Account'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Details Section */}
        <div className="col-lg-8">
          <div className="card shadow-sm border-0">
            {/* Tabs Navigation */}
            <div className="card-header bg-transparent border-bottom p-0">
              <ul className="nav nav-tabs border-0">
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'info' ? 'active' : ''}`}
                    onClick={() => setActiveTab('info')}
                  >
                    <i className="ri-user-settings-line me-2"></i>
                    Informazioni
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'teams' ? 'active' : ''}`}
                    onClick={() => setActiveTab('teams')}
                  >
                    <i className="ri-team-line me-2"></i>
                    Team Guidati
                    {member?.teams_led?.length > 0 && (
                      <span className="badge bg-primary ms-2">{member.teams_led.length}</span>
                    )}
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'clienti' ? 'active' : ''}`}
                    onClick={() => setActiveTab('clienti')}
                  >
                    <i className="ri-user-heart-line me-2"></i>
                    Clienti
                    {clientsTotal > 0 && (
                      <span className="badge bg-primary ms-2">{clientsTotal}</span>
                    )}
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'check' ? 'active' : ''}`}
                    onClick={() => setActiveTab('check')}
                  >
                    <i className="ri-checkbox-multiple-line me-2"></i>
                    Check
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'quality' ? 'active' : ''}`}
                    onClick={() => setActiveTab('quality')}
                  >
                    <i className="ri-star-line me-2"></i>
                    Quality
                  </button>
                </li>
              </ul>
            </div>

            {/* Tab Content */}
            <div className="card-body">
              {/* Info Tab */}
              {activeTab === 'info' && (
                <div className="row g-4">
                  {/* Personal Info */}
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Dati Personali
                    </h6>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-primary-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-user-line text-primary"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Nome Completo</div>
                        <div className="fw-medium">{member?.full_name}</div>
                      </div>
                    </div>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-info-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-mail-line text-info"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Email</div>
                        <div className="fw-medium">{member?.email}</div>
                      </div>
                    </div>
                  </div>

                  {/* Account Info */}
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Dettagli Account
                    </h6>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-success-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-calendar-check-line text-success"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Data Creazione</div>
                        <div className="fw-medium">
                          {member?.created_at
                            ? new Date(member.created_at).toLocaleDateString('it-IT', {
                                day: 'numeric',
                                month: 'long',
                                year: 'numeric'
                              })
                            : '-'
                          }
                        </div>
                      </div>
                    </div>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-shield-user-line text-warning"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Ruolo</div>
                        <div className="fw-medium">{ROLE_LABELS[role] || role}</div>
                      </div>
                    </div>
                    {specialty && (
                      <div className="d-flex align-items-center mb-3">
                        <div className="flex-shrink-0">
                          <div className="bg-purple-subtle rounded-circle d-flex align-items-center justify-content-center"
                               style={{ width: '40px', height: '40px', background: '#e8daff' }}>
                            <i className="ri-stethoscope-line" style={{ color: '#7c3aed' }}></i>
                          </div>
                        </div>
                        <div className="flex-grow-1 ms-3">
                          <div className="text-muted small">Specializzazione</div>
                          <div className="fw-medium">{SPECIALTY_LABELS[specialty] || specialty}</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Teams Tab */}
              {activeTab === 'teams' && (
                <>
                  {member?.teams_led && member.teams_led.length > 0 ? (
                    <div className="list-group list-group-flush">
                      {member.teams_led.map((team) => (
                        <div key={team.id} className="list-group-item px-0 py-3">
                          <div className="d-flex align-items-center">
                            <div className="flex-shrink-0">
                              <div
                                className="rounded-circle d-flex align-items-center justify-content-center text-white"
                                style={{
                                  width: '48px',
                                  height: '48px',
                                  background: ROLE_GRADIENTS.team_leader
                                }}
                              >
                                <i className="ri-team-line fs-5"></i>
                              </div>
                            </div>
                            <div className="flex-grow-1 ms-3">
                              <h6 className="mb-0">{team.name}</h6>
                              <small className="text-muted">
                                <i className="ri-shield-star-line me-1"></i>
                                Team Leader
                              </small>
                            </div>
                            <div className="d-flex gap-2">
                              <Link
                                to={`/teams-dettaglio/${team.id}`}
                                className="btn btn-sm btn-outline-primary"
                              >
                                <i className="ri-eye-line me-1"></i>
                                Dettagli
                              </Link>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-5">
                      <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                           style={{ width: '64px', height: '64px' }}>
                        <i className="ri-team-line text-muted fs-3"></i>
                      </div>
                      <p className="text-muted mb-0">Questo membro non guida nessun team</p>
                    </div>
                  )}
                </>
              )}

              {/* Clienti Tab */}
              {activeTab === 'clienti' && (
                <div>
                  {/* Filters */}
                  <div className="d-flex flex-wrap gap-3 mb-4">
                    {/* Search */}
                    <div className="flex-grow-1" style={{ maxWidth: '300px' }}>
                      <div className="input-group">
                        <span className="input-group-text bg-light border-end-0">
                          <i className="ri-search-line text-muted"></i>
                        </span>
                        <input
                          type="text"
                          className="form-control bg-light border-start-0"
                          placeholder="Cerca cliente..."
                          value={clientsSearch}
                          onChange={(e) => setClientsSearch(e.target.value)}
                        />
                      </div>
                    </div>

                    {/* Stato Filter */}
                    <select
                      className="form-select"
                      style={{ width: 'auto', minWidth: '150px' }}
                      value={clientsStato}
                      onChange={(e) => {
                        setClientsStato(e.target.value);
                        setClientsPage(1);
                      }}
                    >
                      <option value="">Tutti gli stati</option>
                      <option value="Attivo">Attivo</option>
                      <option value="In prova">In prova</option>
                      <option value="Non attivo">Non attivo</option>
                      <option value="In pausa">In pausa</option>
                      <option value="Freeze">Freeze</option>
                    </select>

                    {/* Total count */}
                    <div className="d-flex align-items-center ms-auto">
                      <span className="badge bg-primary-subtle text-primary px-3 py-2">
                        {clientsTotal} client{clientsTotal !== 1 ? 'i' : 'e'}
                      </span>
                    </div>
                  </div>

                  {/* Loading */}
                  {clientsLoading && (
                    <div className="text-center py-5">
                      <div className="spinner-border text-primary" role="status">
                        <span className="visually-hidden">Caricamento...</span>
                      </div>
                    </div>
                  )}

                  {/* Error */}
                  {clientsError && !clientsLoading && (
                    <div className="alert alert-danger">
                      <i className="ri-error-warning-line me-2"></i>
                      {clientsError}
                    </div>
                  )}

                  {/* Empty State */}
                  {!clientsLoading && !clientsError && clients.length === 0 && (
                    <div className="text-center py-5">
                      <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                           style={{ width: '64px', height: '64px' }}>
                        <i className="ri-user-heart-line text-muted fs-3"></i>
                      </div>
                      <p className="text-muted mb-0">
                        {clientsSearch || clientsStato
                          ? 'Nessun cliente trovato con i filtri selezionati'
                          : 'Nessun cliente associato a questo professionista'}
                      </p>
                    </div>
                  )}

                  {/* Clients List */}
                  {!clientsLoading && !clientsError && clients.length > 0 && (
                    <>
                      <div className="list-group list-group-flush">
                        {clients.map((client) => {
                          const statoStyle = STATO_COLORS[client.stato_cliente] || { bg: '#f1f5f9', color: '#64748b', icon: 'ri-question-line' };
                          return (
                            <Link
                              key={client.id}
                              to={`/clienti-dettaglio/${client.id}`}
                              className="list-group-item list-group-item-action px-0 py-3 border-start-0 border-end-0"
                            >
                              <div className="d-flex align-items-center">
                                {/* Avatar */}
                                <div className="flex-shrink-0">
                                  {client.foto_profilo ? (
                                    <img
                                      src={client.foto_profilo}
                                      alt={client.full_name}
                                      className="rounded-circle"
                                      style={{ width: '48px', height: '48px', objectFit: 'cover' }}
                                    />
                                  ) : (
                                    <div
                                      className="rounded-circle d-flex align-items-center justify-content-center"
                                      style={{ width: '48px', height: '48px', background: '#e2e8f0' }}
                                    >
                                      <span className="fw-semibold text-secondary">
                                        {client.nome?.[0]?.toUpperCase()}{client.cognome?.[0]?.toUpperCase()}
                                      </span>
                                    </div>
                                  )}
                                </div>

                                {/* Info */}
                                <div className="flex-grow-1 ms-3">
                                  <div className="d-flex align-items-center gap-2 mb-1">
                                    <h6 className="mb-0">{client.full_name}</h6>
                                    {/* Role badges */}
                                    {client.is_nutrizionista && (
                                      <span className="badge bg-info-subtle text-info" style={{ fontSize: '10px' }}>
                                        <i className="ri-restaurant-line me-1"></i>Nutri
                                      </span>
                                    )}
                                    {client.is_coach && (
                                      <span className="badge bg-success-subtle text-success" style={{ fontSize: '10px' }}>
                                        <i className="ri-run-line me-1"></i>Coach
                                      </span>
                                    )}
                                    {client.is_psicologo && (
                                      <span className="badge bg-warning-subtle text-warning" style={{ fontSize: '10px' }}>
                                        <i className="ri-mental-health-line me-1"></i>Psico
                                      </span>
                                    )}
                                  </div>
                                  <div className="d-flex align-items-center gap-3 text-muted small">
                                    {client.email && (
                                      <span>
                                        <i className="ri-mail-line me-1"></i>
                                        {client.email}
                                      </span>
                                    )}
                                    {client.telefono && (
                                      <span>
                                        <i className="ri-phone-line me-1"></i>
                                        {client.telefono}
                                      </span>
                                    )}
                                  </div>
                                </div>

                                {/* Status Badge */}
                                <div className="flex-shrink-0 ms-3">
                                  <span
                                    className="badge d-flex align-items-center gap-1"
                                    style={{
                                      background: statoStyle.bg,
                                      color: statoStyle.color,
                                      padding: '6px 12px',
                                      borderRadius: '8px',
                                      fontSize: '12px',
                                      fontWeight: 500,
                                    }}
                                  >
                                    <i className={statoStyle.icon}></i>
                                    {client.stato_cliente || 'N/D'}
                                  </span>
                                </div>

                                {/* Arrow */}
                                <div className="flex-shrink-0 ms-3">
                                  <i className="ri-arrow-right-s-line text-muted fs-5"></i>
                                </div>
                              </div>
                            </Link>
                          );
                        })}
                      </div>

                      {/* Pagination */}
                      {clientsTotalPages > 1 && (
                        <div className="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                          <div className="text-muted small">
                            Pagina {clientsPage} di {clientsTotalPages}
                          </div>
                          <nav>
                            <ul className="pagination pagination-sm mb-0">
                              <li className={`page-item ${clientsPage === 1 ? 'disabled' : ''}`}>
                                <button
                                  className="page-link"
                                  onClick={() => setClientsPage(p => Math.max(1, p - 1))}
                                  disabled={clientsPage === 1}
                                >
                                  <i className="ri-arrow-left-s-line"></i>
                                </button>
                              </li>
                              {[...Array(clientsTotalPages)].map((_, i) => (
                                <li key={i + 1} className={`page-item ${clientsPage === i + 1 ? 'active' : ''}`}>
                                  <button
                                    className="page-link"
                                    onClick={() => setClientsPage(i + 1)}
                                  >
                                    {i + 1}
                                  </button>
                                </li>
                              ))}
                              <li className={`page-item ${clientsPage === clientsTotalPages ? 'disabled' : ''}`}>
                                <button
                                  className="page-link"
                                  onClick={() => setClientsPage(p => Math.min(clientsTotalPages, p + 1))}
                                  disabled={clientsPage === clientsTotalPages}
                                >
                                  <i className="ri-arrow-right-s-line"></i>
                                </button>
                              </li>
                            </ul>
                          </nav>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {/* Check Tab */}
              {activeTab === 'check' && (
                <div className="text-center py-5">
                  <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                       style={{ width: '64px', height: '64px' }}>
                    <i className="ri-checkbox-multiple-line text-muted fs-3"></i>
                  </div>
                  <p className="text-muted mb-0">Qui vedrai i check ricevuti dal membro del team</p>
                </div>
              )}

              {/* Quality Tab */}
              {activeTab === 'quality' && (
                <div className="text-center py-5">
                  <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                       style={{ width: '64px', height: '64px' }}>
                    <i className="ri-star-line text-muted fs-3"></i>
                  </div>
                  <p className="text-muted mb-0">Qui vedrai il quality del membro del team</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default TeamDetail;

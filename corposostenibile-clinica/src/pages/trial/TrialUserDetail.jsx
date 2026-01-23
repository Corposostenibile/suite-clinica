import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import trialUserService, { TRIAL_STAGES } from '../../services/trialUserService';

// Gradient colors by specialty
const SPECIALTY_GRADIENTS = {
  nutrizione: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  coach: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  psicologia: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
};

const SPECIALTY_LABELS = {
  nutrizione: 'Nutrizione',
  coach: 'Coach',
  psicologia: 'Psicologia',
  nutrizionista: 'Nutrizionista',
  psicologo: 'Psicologo',
};

function TrialUserDetail() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('progress');
  const [isPromoting, setIsPromoting] = useState(false);
  const [removingClientId, setRemovingClientId] = useState(null);

  const fetchUser = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await trialUserService.get(userId);
      if (result.success) {
        setUser(result.trial_user);
      } else {
        setError(result.error || 'Errore nel caricamento');
      }
    } catch (err) {
      console.error('Error fetching trial user:', err);
      setError('Errore nel caricamento dei dati');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const handlePromote = async () => {
    const nextStage = TRIAL_STAGES[user.trial_stage + 1];
    const message = user.trial_stage === 2
      ? `Attenzione: promuovendo a Stage 3, ${user.full_name} diventerà un utente ufficiale con accesso completo. Questa azione non è reversibile. Continuare?`
      : `Promuovere ${user.full_name} a ${nextStage?.label}?`;

    if (!window.confirm(message)) return;

    setIsPromoting(true);
    try {
      const result = await trialUserService.promote(userId);
      if (result.success) {
        if (result.trial_user.trial_stage === 3) {
          navigate('/team-lista');
        } else {
          fetchUser();
        }
      } else {
        alert(result.error || 'Errore nella promozione');
      }
    } catch (err) {
      alert('Errore nella promozione');
    } finally {
      setIsPromoting(false);
    }
  };

  const handleRemoveClient = async (clienteId) => {
    if (!window.confirm('Rimuovere questo cliente dall\'assegnazione?')) return;

    setRemovingClientId(clienteId);
    try {
      const result = await trialUserService.removeClient(userId, clienteId);
      if (result.success) {
        fetchUser();
      } else {
        alert(result.error || 'Errore nella rimozione');
      }
    } catch (err) {
      alert('Errore nella rimozione');
    } finally {
      setRemovingClientId(null);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Eliminare definitivamente "${user.full_name}"? Questa azione non è reversibile.`)) return;

    try {
      const result = await trialUserService.delete(userId);
      if (result.success) {
        navigate('/in-prova');
      } else {
        alert(result.error || 'Errore nella eliminazione');
      }
    } catch (err) {
      alert('Errore nella eliminazione');
    }
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Caricamento...</span>
        </div>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="alert alert-danger d-flex align-items-center">
        <i className="ri-error-warning-line me-2 fs-4"></i>
        <div className="flex-grow-1">{error || 'Utente non trovato'}</div>
        <Link to="/in-prova" className="btn btn-sm btn-outline-danger">
          Torna alla Lista
        </Link>
      </div>
    );
  }

  const stageConfig = TRIAL_STAGES[user.trial_stage] || TRIAL_STAGES[1];
  const daysSinceStart = trialUserService.getDaysSinceStart(user.trial_started_at);
  const specialty = user.specialty;
  const gradient = SPECIALTY_GRADIENTS[specialty] || SPECIALTY_GRADIENTS.coach;

  return (
    <>
      {/* Page Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1">Dettaglio Professionista</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/in-prova">In Prova</Link>
              </li>
              <li className="breadcrumb-item active">{user.full_name}</li>
            </ol>
          </nav>
        </div>
        <div className="d-flex gap-2">
          <Link to="/in-prova" className="btn btn-outline-secondary">
            <i className="ri-arrow-left-line me-1"></i>
            Torna alla Lista
          </Link>
          <Link to={`/in-prova/${userId}/modifica`} className="btn btn-primary">
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
              style={{ background: gradient, height: '120px' }}
            >
              {/* Stage badge */}
              <div className="position-absolute top-0 start-0 p-3">
                <span
                  className="badge"
                  style={{
                    background: stageConfig.bgColor,
                    color: stageConfig.color,
                    fontWeight: 600,
                  }}
                >
                  <i className={`${stageConfig.icon} me-1`}></i>
                  {stageConfig.label}
                </span>
              </div>

              {/* Avatar positioned at bottom */}
              <div className="position-absolute start-50 translate-middle-x" style={{ bottom: '-50px' }}>
                {user.avatar_path ? (
                  <img
                    src={user.avatar_path}
                    alt={user.full_name}
                    className="rounded-circle border border-4 border-white shadow"
                    style={{ width: '100px', height: '100px', objectFit: 'cover', background: '#fff' }}
                    onError={(e) => { e.target.src = '/static/assets/immagini/logo_user.png'; }}
                  />
                ) : (
                  <div
                    className="rounded-circle border border-4 border-white shadow d-flex align-items-center justify-content-center"
                    style={{ width: '100px', height: '100px', background: '#fff' }}
                  >
                    <span className="fw-bold text-primary" style={{ fontSize: '2rem' }}>
                      {user.first_name?.[0]?.toUpperCase()}{user.last_name?.[0]?.toUpperCase()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Card Body */}
            <div className="card-body text-center pt-5 mt-3">
              <h4 className="mb-1">{user.full_name}</h4>
              <p className="text-muted mb-3">{user.email}</p>

              {/* Specialty Badge */}
              <div className="d-flex justify-content-center gap-2 mb-4">
                {specialty && (
                  <span className="badge bg-primary-subtle text-primary">
                    {SPECIALTY_LABELS[specialty] || specialty}
                  </span>
                )}
              </div>

              {/* Quick Stats */}
              <div className="row g-3 mb-4">
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">Giorni in Prova</div>
                    <div className="fw-semibold">{daysSinceStart}</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">Clienti Assegnati</div>
                    <div className="fw-semibold">{user.assigned_clients?.length || 0}</div>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="d-grid">
                <button
                  className="btn btn-outline-danger"
                  onClick={handleDelete}
                >
                  <i className="ri-delete-bin-line me-2"></i>
                  Elimina Professionista
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
                    className={`nav-link px-4 py-3 ${activeTab === 'progress' ? 'active' : ''}`}
                    onClick={() => setActiveTab('progress')}
                  >
                    <i className="ri-roadmap-line me-2"></i>
                    Progressione
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'clienti' ? 'active' : ''}`}
                    onClick={() => setActiveTab('clienti')}
                  >
                    <i className="ri-group-line me-2"></i>
                    Clienti
                    {user.assigned_clients?.length > 0 && (
                      <span className="badge bg-primary ms-2">{user.assigned_clients.length}</span>
                    )}
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'info' ? 'active' : ''}`}
                    onClick={() => setActiveTab('info')}
                  >
                    <i className="ri-user-settings-line me-2"></i>
                    Informazioni
                  </button>
                </li>
              </ul>
            </div>

            {/* Tab Content */}
            <div className="card-body">
              {/* Progress Tab */}
              {activeTab === 'progress' && (
                <div>
                  {/* Stage Progress */}
                  <div className="mb-4">
                    <div className="d-flex align-items-center justify-content-between mb-4">
                      {[1, 2, 3].map((stage, index) => {
                        const config = TRIAL_STAGES[stage];
                        const isActive = stage === user.trial_stage;
                        const isCompleted = stage < user.trial_stage;
                        const isLast = index === 2;

                        return (
                          <div key={stage} className="d-flex align-items-center flex-grow-1">
                            <div className="text-center" style={{ minWidth: '90px' }}>
                              <div
                                className="d-flex align-items-center justify-content-center mx-auto mb-2"
                                style={{
                                  width: '48px',
                                  height: '48px',
                                  borderRadius: '50%',
                                  background: isCompleted
                                    ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
                                    : isActive
                                    ? '#fff'
                                    : '#f1f5f9',
                                  border: isActive ? `3px solid ${config.color}` : 'none',
                                  boxShadow: isActive ? `0 4px 12px ${config.color}30` : 'none',
                                }}
                              >
                                {isCompleted ? (
                                  <i className="ri-check-line text-white" style={{ fontSize: '20px' }}></i>
                                ) : (
                                  <i className={config.icon} style={{ fontSize: '20px', color: isActive ? config.color : '#94a3b8' }}></i>
                                )}
                              </div>
                              <div className="fw-semibold" style={{ fontSize: '13px', color: isActive ? config.color : '#64748b' }}>
                                {config.label}
                              </div>
                              <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                                {config.description}
                              </div>
                            </div>
                            {!isLast && (
                              <div
                                style={{
                                  flex: 1,
                                  height: '3px',
                                  borderRadius: '2px',
                                  background: isCompleted
                                    ? 'linear-gradient(90deg, #22c55e, #22c55e)'
                                    : '#e2e8f0',
                                  marginTop: '-28px',
                                }}
                              ></div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Promote Button */}
                  {user.trial_stage < 3 && (
                    <div className="text-center mt-4 pt-4 border-top">
                      <button
                        className="btn btn-success px-4 py-2"
                        onClick={handlePromote}
                        disabled={isPromoting}
                      >
                        {isPromoting ? (
                          <>
                            <span className="spinner-border spinner-border-sm me-2"></span>
                            Promozione in corso...
                          </>
                        ) : (
                          <>
                            <i className="ri-arrow-up-circle-line me-2"></i>
                            Promuovi a {TRIAL_STAGES[user.trial_stage + 1]?.label || 'User Ufficiale'}
                          </>
                        )}
                      </button>
                      <p className="text-muted small mt-2 mb-0">
                        {user.trial_stage === 1
                          ? 'Sblocca accesso ai clienti assegnati'
                          : 'Il professionista diventerà un utente ufficiale'}
                      </p>
                    </div>
                  )}

                  {/* Stage 3 completed message */}
                  {user.trial_stage === 3 && (
                    <div className="text-center mt-4 pt-4 border-top">
                      <div className="bg-success-subtle rounded-3 p-4">
                        <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '32px' }}></i>
                        <p className="fw-semibold text-success mt-2 mb-0">Percorso completato - Utente ufficiale</p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Clienti Tab */}
              {activeTab === 'clienti' && (
                <div>
                  {user.trial_stage < 2 ? (
                    <div className="text-center py-5">
                      <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                           style={{ width: '64px', height: '64px' }}>
                        <i className="ri-lock-line text-muted fs-3"></i>
                      </div>
                      <p className="text-muted mb-2">L'assegnazione clienti è disponibile dallo Stage 2</p>
                      <button
                        className="btn btn-success"
                        onClick={handlePromote}
                        disabled={isPromoting}
                      >
                        <i className="ri-arrow-up-circle-line me-1"></i>
                        Promuovi a Stage 2
                      </button>
                    </div>
                  ) : (
                    <>
                      {/* Header with assign button */}
                      <div className="d-flex justify-content-between align-items-center mb-4">
                        <span className="badge bg-primary-subtle text-primary px-3 py-2">
                          {user.assigned_clients?.length || 0} client{(user.assigned_clients?.length || 0) !== 1 ? 'i' : 'e'} assegnat{(user.assigned_clients?.length || 0) !== 1 ? 'i' : 'o'}
                        </span>
                        <Link
                          to={`/in-prova/${userId}/assegna-clienti`}
                          className="btn btn-primary"
                        >
                          <i className="ri-user-add-line me-1"></i>
                          Assegna Clienti
                        </Link>
                      </div>

                      {/* Empty state */}
                      {(!user.assigned_clients || user.assigned_clients.length === 0) ? (
                        <div className="text-center py-5">
                          <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                               style={{ width: '64px', height: '64px' }}>
                            <i className="ri-user-heart-line text-muted fs-3"></i>
                          </div>
                          <p className="text-muted mb-0">Nessun cliente assegnato</p>
                        </div>
                      ) : (
                        /* Clients table */
                        <div className="table-responsive" style={{ margin: '0 -1rem' }}>
                          <table className="table mb-0">
                            <thead style={{
                              background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
                              borderBottom: '2px solid #e2e8f0',
                            }}>
                              <tr>
                                <th style={{ padding: '14px 16px', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#64748b', borderBottom: 'none' }}>
                                  Cliente
                                </th>
                                <th style={{ padding: '14px 16px', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#64748b', borderBottom: 'none' }}>
                                  Assegnato il
                                </th>
                                <th style={{ padding: '14px 16px', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#64748b', borderBottom: 'none' }}>
                                  Da
                                </th>
                                <th style={{ padding: '14px 16px', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#64748b', borderBottom: 'none' }}>
                                  Note
                                </th>
                                <th style={{ padding: '14px 16px', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#64748b', borderBottom: 'none', textAlign: 'right' }}>
                                  Azioni
                                </th>
                              </tr>
                            </thead>
                            <tbody>
                              {user.assigned_clients.map((client) => (
                                <tr key={client.cliente_id}>
                                  <td style={{ padding: '14px 16px', fontSize: '14px', color: '#334155', borderBottom: '1px solid #f1f5f9', verticalAlign: 'middle' }}>
                                    <Link
                                      to={`/clienti-dettaglio/${client.cliente_id}`}
                                      style={{ color: '#3b82f6', fontWeight: 600, textDecoration: 'none' }}
                                    >
                                      {client.nome_cognome}
                                    </Link>
                                    {client.tipologia_cliente && (
                                      <div>
                                        <span className="badge bg-light text-muted" style={{ fontSize: '10px' }}>
                                          {client.tipologia_cliente}
                                        </span>
                                      </div>
                                    )}
                                  </td>
                                  <td style={{ padding: '14px 16px', fontSize: '14px', color: '#334155', borderBottom: '1px solid #f1f5f9', verticalAlign: 'middle' }}>
                                    <span style={{ fontWeight: 500 }}>
                                      {trialUserService.formatDateTime(client.assigned_at)}
                                    </span>
                                  </td>
                                  <td style={{ padding: '14px 16px', fontSize: '14px', color: '#334155', borderBottom: '1px solid #f1f5f9', verticalAlign: 'middle' }}>
                                    {client.assigned_by || <span style={{ color: '#cbd5e1' }}>—</span>}
                                  </td>
                                  <td style={{ padding: '14px 16px', fontSize: '14px', color: '#334155', borderBottom: '1px solid #f1f5f9', verticalAlign: 'middle' }}>
                                    {client.notes || <span style={{ color: '#cbd5e1' }}>—</span>}
                                  </td>
                                  <td style={{ padding: '14px 16px', fontSize: '14px', borderBottom: '1px solid #f1f5f9', verticalAlign: 'middle', textAlign: 'right' }}>
                                    <button
                                      className="btn btn-sm btn-outline-danger"
                                      onClick={() => handleRemoveClient(client.cliente_id)}
                                      disabled={removingClientId === client.cliente_id}
                                      style={{ width: '32px', height: '32px', padding: 0, borderRadius: '8px' }}
                                      title="Rimuovi"
                                    >
                                      <i className="ri-close-line"></i>
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

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
                        <div className="fw-medium">{user.full_name}</div>
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
                        <div className="fw-medium">{user.email}</div>
                      </div>
                    </div>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px', background: '#e8daff' }}>
                          <i className="ri-stethoscope-line" style={{ color: '#7c3aed' }}></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Specializzazione</div>
                        <div className="fw-medium">{SPECIALTY_LABELS[specialty] || specialty || '-'}</div>
                      </div>
                    </div>
                  </div>

                  {/* Trial Info */}
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Dettagli Prova
                    </h6>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-success-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-calendar-check-line text-success"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Inizio Prova</div>
                        <div className="fw-medium">
                          {trialUserService.formatDate(user.trial_started_at) || '-'}
                        </div>
                      </div>
                    </div>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-time-line text-warning"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Durata</div>
                        <div className="fw-medium">{daysSinceStart} giorni</div>
                      </div>
                    </div>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-primary-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-user-star-line text-primary"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Supervisor</div>
                        <div className="fw-medium">{user.supervisor?.full_name || '-'}</div>
                      </div>
                    </div>
                    {user.department?.name && (
                      <div className="d-flex align-items-center mb-3">
                        <div className="flex-shrink-0">
                          <div className="bg-secondary-subtle rounded-circle d-flex align-items-center justify-content-center"
                               style={{ width: '40px', height: '40px' }}>
                            <i className="ri-building-line text-secondary"></i>
                          </div>
                        </div>
                        <div className="flex-grow-1 ms-3">
                          <div className="text-muted small">Dipartimento</div>
                          <div className="fw-medium">{user.department.name}</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default TrialUserDetail;

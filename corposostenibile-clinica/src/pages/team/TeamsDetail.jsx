import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import teamService, {
  TEAM_TYPE_LABELS,
  TEAM_TYPE_COLORS,
  TEAM_TYPE_ICONS,
  ROLE_LABELS,
  SPECIALTY_LABELS,
  ROLE_COLORS,
} from '../../services/teamService';

// Gradient colors by team type
const TYPE_GRADIENTS = {
  nutrizione: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  coach: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  psicologia: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
};

function TeamsDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [team, setTeam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('info');
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [availableProfessionals, setAvailableProfessionals] = useState([]);
  const [loadingProfessionals, setLoadingProfessionals] = useState(false);
  const [membersPage, setMembersPage] = useState(1);
  const membersPerPage = 5;

  useEffect(() => {
    fetchTeam();
  }, [id]);

  const fetchTeam = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await teamService.getTeam(id);
      setTeam(data);
    } catch (err) {
      console.error('Error fetching team:', err);
      setError('Errore nel caricamento del team');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Sei sicuro di voler disattivare questo team?')) return;

    try {
      await teamService.deleteTeam(id);
      navigate('/teams');
    } catch (err) {
      console.error('Error deleting team:', err);
      alert('Errore durante la disattivazione del team');
    }
  };

  const handleRemoveMember = async (userId) => {
    if (!window.confirm('Sei sicuro di voler rimuovere questo membro dal team?')) return;

    try {
      const data = await teamService.removeTeamMember(id, userId);
      setTeam(data);
    } catch (err) {
      console.error('Error removing member:', err);
      alert('Errore durante la rimozione del membro');
    }
  };

  const openAddMemberModal = async () => {
    setShowAddMemberModal(true);
    setLoadingProfessionals(true);
    try {
      const data = await teamService.getAvailableProfessionals(team.team_type);
      const existingIds = new Set((team.members || []).map(m => m.id));
      setAvailableProfessionals(
        (data.professionals || []).filter(p => !existingIds.has(p.id))
      );
    } catch (err) {
      console.error('Error fetching professionals:', err);
    } finally {
      setLoadingProfessionals(false);
    }
  };

  const handleAddMember = async (userId) => {
    try {
      const data = await teamService.addTeamMember(id, userId);
      setTeam(data);
      setAvailableProfessionals(prev => prev.filter(p => p.id !== userId));
    } catch (err) {
      console.error('Error adding member:', err);
      alert('Errore durante l\'aggiunta del membro');
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

  if (error && !team) {
    return (
      <div className="alert alert-danger d-flex align-items-center">
        <i className="ri-error-warning-line me-2 fs-4"></i>
        <div className="flex-grow-1">{error}</div>
        <Link to="/teams" className="btn btn-sm btn-outline-danger">
          Torna alla Lista
        </Link>
      </div>
    );
  }

  const type = team?.team_type;

  return (
    <>
      {/* Page Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1">Dettaglio Team</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/teams">Team</Link>
              </li>
              <li className="breadcrumb-item active">{team?.name}</li>
            </ol>
          </nav>
        </div>
        <div className="d-flex gap-2">
          <Link to="/teams" className="btn btn-outline-secondary">
            <i className="ri-arrow-left-line me-1"></i>
            Torna alla Lista
          </Link>
          <Link to={`/teams-modifica/${id}`} className="btn btn-primary">
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
                background: TYPE_GRADIENTS[type] || TYPE_GRADIENTS.nutrizione,
                height: '120px'
              }}
            >
              {/* Status badge */}
              <div className="position-absolute top-0 start-0 p-3 d-flex gap-2">
                {team?.is_active ? (
                  <span className="badge bg-success">
                    <i className="ri-checkbox-circle-line me-1"></i>Attivo
                  </span>
                ) : (
                  <span className="badge bg-dark bg-opacity-75">
                    <i className="ri-close-circle-line me-1"></i>Inattivo
                  </span>
                )}
              </div>

              {/* Icon positioned at bottom */}
              <div className="position-absolute start-50 translate-middle-x" style={{ bottom: '-50px' }}>
                <div
                  className="rounded-circle border border-4 border-white shadow d-flex align-items-center justify-content-center"
                  style={{ width: '100px', height: '100px', background: '#fff' }}
                >
                  <i className={`${TEAM_TYPE_ICONS[type]} text-${TEAM_TYPE_COLORS[type]}`} style={{ fontSize: '2.5rem' }}></i>
                </div>
              </div>
            </div>

            {/* Card Body */}
            <div className="card-body text-center pt-5 mt-3">
              <h4 className="mb-1">{team?.name}</h4>
              <span className={`badge bg-${TEAM_TYPE_COLORS[type]} mb-3`}>
                {TEAM_TYPE_LABELS[type]}
              </span>
              <p className="text-muted mb-3">
                {team?.description || 'Nessuna descrizione'}
              </p>

              {/* Quick Stats */}
              <div className="row g-3 mb-4">
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">ID Team</div>
                    <div className="fw-semibold">#{team?.id}</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">Membri</div>
                    <div className="fw-semibold">{team?.member_count || 0}</div>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="d-grid">
                <button
                  className={`btn ${team?.is_active ? 'btn-outline-danger' : 'btn-outline-success'}`}
                  onClick={handleDelete}
                >
                  <i className={`ri-${team?.is_active ? 'close-circle' : 'checkbox-circle'}-line me-2`}></i>
                  {team?.is_active ? 'Disattiva Team' : 'Attiva Team'}
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
              <ul className="nav nav-tabs border-0 flex-nowrap overflow-auto">
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'info' ? 'active' : ''}`}
                    onClick={() => setActiveTab('info')}
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    <i className="ri-information-line me-2"></i>
                    Informazioni
                  </button>
                </li>
                <li className="nav-item">
                  <button
                    className={`nav-link px-4 py-3 ${activeTab === 'members' ? 'active' : ''}`}
                    onClick={() => setActiveTab('members')}
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    <i className="ri-group-line me-2"></i>
                    Membri
                    {team?.members?.length > 0 && (
                      <span className="badge bg-primary ms-2">{team.members.length}</span>
                    )}
                  </button>
                </li>
              </ul>
            </div>

            {/* Tab Content */}
            <div className="card-body">
              {/* Info Tab */}
              {activeTab === 'info' && (
                <div className="row g-4">
                  {/* Team Info */}
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Dettagli Team
                    </h6>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className="bg-primary-subtle rounded-circle d-flex align-items-center justify-content-center"
                             style={{ width: '40px', height: '40px' }}>
                          <i className="ri-team-line text-primary"></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Nome Team</div>
                        <div className="fw-medium">{team?.name}</div>
                      </div>
                    </div>
                    <div className="d-flex align-items-center mb-3">
                      <div className="flex-shrink-0">
                        <div className={`bg-${TEAM_TYPE_COLORS[type]}-subtle rounded-circle d-flex align-items-center justify-content-center`}
                             style={{ width: '40px', height: '40px' }}>
                          <i className={`${TEAM_TYPE_ICONS[type]} text-${TEAM_TYPE_COLORS[type]}`}></i>
                        </div>
                      </div>
                      <div className="flex-grow-1 ms-3">
                        <div className="text-muted small">Tipo Team</div>
                        <div className="fw-medium">{TEAM_TYPE_LABELS[type]}</div>
                      </div>
                    </div>
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
                          {team?.created_at
                            ? new Date(team.created_at).toLocaleDateString('it-IT', {
                                day: 'numeric',
                                month: 'long',
                                year: 'numeric'
                              })
                            : '-'
                          }
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Team Leader Info */}
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Team Leader
                    </h6>
                    {team?.head ? (
                      <>
                        <div className="d-flex align-items-center mb-3">
                          <div className="flex-shrink-0">
                            {team.head.avatar_path ? (
                              <img
                                src={team.head.avatar_path}
                                alt={team.head.full_name}
                                className="rounded-circle"
                                style={{ width: '40px', height: '40px', objectFit: 'cover' }}
                              />
                            ) : (
                              <div
                                className="rounded-circle bg-warning d-flex align-items-center justify-content-center text-white"
                                style={{ width: '40px', height: '40px' }}
                              >
                                {team.head.first_name?.[0]}{team.head.last_name?.[0]}
                              </div>
                            )}
                          </div>
                          <div className="flex-grow-1 ms-3">
                            <div className="text-muted small">Nome</div>
                            <div className="fw-medium">{team.head.full_name}</div>
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
                            <div className="fw-medium">{team.head.email}</div>
                          </div>
                        </div>
                        <Link
                          to={`/team-dettaglio/${team.head.id}`}
                          className="btn btn-sm btn-outline-primary"
                        >
                          <i className="ri-eye-line me-1"></i>
                          Vedi Profilo
                        </Link>
                      </>
                    ) : (
                      <div className="text-center py-4 text-muted">
                        <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-2"
                             style={{ width: '48px', height: '48px' }}>
                          <i className="ri-user-unfollow-line fs-4"></i>
                        </div>
                        <p className="mb-0">Nessun Team Leader assegnato</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Members Tab */}
              {activeTab === 'members' && (() => {
                const allMembers = team?.members || [];
                const totalMembers = allMembers.length;
                const totalPages = Math.ceil(totalMembers / membersPerPage);
                const paginatedMembers = allMembers.slice(
                  (membersPage - 1) * membersPerPage,
                  membersPage * membersPerPage
                );

                return (
                  <>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h6 className="mb-0">
                        Membri del Team
                        <span className="badge bg-primary ms-2">{totalMembers}</span>
                      </h6>
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={openAddMemberModal}
                      >
                        <i className="ri-user-add-line me-1"></i>
                        Aggiungi Membro
                      </button>
                    </div>

                    {totalMembers > 0 ? (
                      <>
                        <div className="list-group list-group-flush">
                          {paginatedMembers.map(member => (
                            <div key={member.id} className="list-group-item px-0 py-3">
                              <div className="d-flex align-items-center">
                                <div className="flex-shrink-0">
                                  {member.avatar_path ? (
                                    <img
                                      src={member.avatar_path}
                                      alt={member.full_name}
                                      className="rounded-circle"
                                      style={{ width: '48px', height: '48px', objectFit: 'cover' }}
                                    />
                                  ) : (
                                    <div
                                      className="rounded-circle bg-secondary d-flex align-items-center justify-content-center text-white"
                                      style={{ width: '48px', height: '48px' }}
                                    >
                                      {member.first_name?.[0]}{member.last_name?.[0]}
                                    </div>
                                  )}
                                </div>
                                <div className="flex-grow-1 ms-3">
                                  <h6 className="mb-0">{member.full_name}</h6>
                                  <small className="text-muted">{member.email}</small>
                                  <div className="mt-1">
                                    <span className={`badge bg-${ROLE_COLORS[member.role] || 'secondary'} me-1`} style={{ fontSize: '10px' }}>
                                      {ROLE_LABELS[member.role] || member.role}
                                    </span>
                                    {member.specialty && (
                                      <span className="badge bg-light text-dark" style={{ fontSize: '10px' }}>
                                        {SPECIALTY_LABELS[member.specialty] || member.specialty}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="d-flex gap-2">
                                  <Link
                                    to={`/team-dettaglio/${member.id}`}
                                    className="btn btn-sm btn-outline-primary"
                                  >
                                    <i className="ri-eye-line me-1"></i>
                                    Dettagli
                                  </Link>
                                  <button
                                    className="btn btn-sm btn-outline-danger"
                                    onClick={() => handleRemoveMember(member.id)}
                                  >
                                    <i className="ri-user-unfollow-line"></i>
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                          <div className="d-flex flex-wrap justify-content-between align-items-center mt-3 pt-3 border-top gap-2">
                            <span style={{ color: '#64748b', fontSize: '14px' }}>
                              Pagina <strong style={{ color: '#334155' }}>{membersPage}</strong> di{' '}
                              <strong style={{ color: '#334155' }}>{totalPages}</strong>
                              <span className="ms-2" style={{ color: '#94a3b8' }}>•</span>
                              <span className="ms-2">{totalMembers} membri</span>
                            </span>
                            <nav>
                              <ul className="pagination mb-0" style={{ gap: '4px' }}>
                                {/* First */}
                                <li className={`page-item ${membersPage === 1 ? 'disabled' : ''}`}>
                                  <button
                                    className="page-link"
                                    onClick={() => setMembersPage(1)}
                                    disabled={membersPage === 1}
                                    style={{
                                      borderRadius: '8px',
                                      border: '1px solid #e2e8f0',
                                      color: membersPage === 1 ? '#cbd5e1' : '#64748b',
                                      padding: '8px 12px',
                                    }}
                                  >
                                    <i className="ri-arrow-left-double-line"></i>
                                  </button>
                                </li>
                                {/* Prev */}
                                <li className={`page-item ${membersPage === 1 ? 'disabled' : ''}`}>
                                  <button
                                    className="page-link"
                                    onClick={() => setMembersPage(p => p - 1)}
                                    disabled={membersPage === 1}
                                    style={{
                                      borderRadius: '8px',
                                      border: '1px solid #e2e8f0',
                                      color: membersPage === 1 ? '#cbd5e1' : '#64748b',
                                      padding: '8px 12px',
                                    }}
                                  >
                                    <i className="ri-arrow-left-s-line"></i>
                                  </button>
                                </li>
                                {/* Page numbers - max 5 visible */}
                                {[...Array(Math.min(totalPages, 5))].map((_, i) => {
                                  let pageNum;
                                  if (totalPages <= 5) {
                                    pageNum = i + 1;
                                  } else if (membersPage <= 3) {
                                    pageNum = i + 1;
                                  } else if (membersPage >= totalPages - 2) {
                                    pageNum = totalPages - 4 + i;
                                  } else {
                                    pageNum = membersPage - 2 + i;
                                  }
                                  const isActive = membersPage === pageNum;
                                  return (
                                    <li key={pageNum} className="page-item">
                                      <button
                                        className="page-link"
                                        onClick={() => setMembersPage(pageNum)}
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
                                <li className={`page-item ${membersPage === totalPages ? 'disabled' : ''}`}>
                                  <button
                                    className="page-link"
                                    onClick={() => setMembersPage(p => p + 1)}
                                    disabled={membersPage === totalPages}
                                    style={{
                                      borderRadius: '8px',
                                      border: '1px solid #e2e8f0',
                                      color: membersPage === totalPages ? '#cbd5e1' : '#64748b',
                                      padding: '8px 12px',
                                    }}
                                  >
                                    <i className="ri-arrow-right-s-line"></i>
                                  </button>
                                </li>
                                {/* Last */}
                                <li className={`page-item ${membersPage === totalPages ? 'disabled' : ''}`}>
                                  <button
                                    className="page-link"
                                    onClick={() => setMembersPage(totalPages)}
                                    disabled={membersPage === totalPages}
                                    style={{
                                      borderRadius: '8px',
                                      border: '1px solid #e2e8f0',
                                      color: membersPage === totalPages ? '#cbd5e1' : '#64748b',
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
                    ) : (
                      <div className="text-center py-5">
                        <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                             style={{ width: '64px', height: '64px' }}>
                          <i className="ri-group-line text-muted fs-3"></i>
                        </div>
                        <p className="text-muted mb-3">Nessun membro nel team</p>
                        <button
                          className="btn btn-primary"
                          onClick={openAddMemberModal}
                        >
                          <i className="ri-user-add-line me-1"></i>
                          Aggiungi il primo membro
                        </button>
                      </div>
                    )}
                  </>
                );
              })()}

                          </div>
          </div>
        </div>
      </div>

      {/* Add Member Modal */}
      {showAddMemberModal && (
        <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">
                  <i className="ri-user-add-line me-2"></i>
                  Aggiungi Membro al Team
                </h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowAddMemberModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                {loadingProfessionals ? (
                  <div className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Caricamento...</span>
                    </div>
                  </div>
                ) : availableProfessionals.length > 0 ? (
                  <div className="list-group">
                    {availableProfessionals.map(prof => (
                      <div
                        key={prof.id}
                        className="list-group-item list-group-item-action d-flex align-items-center"
                      >
                        <div className="flex-shrink-0">
                          {prof.avatar_path ? (
                            <img
                              src={prof.avatar_path}
                              alt={prof.full_name}
                              className="rounded-circle"
                              style={{ width: '40px', height: '40px', objectFit: 'cover' }}
                            />
                          ) : (
                            <div
                              className="rounded-circle bg-secondary d-flex align-items-center justify-content-center text-white"
                              style={{ width: '40px', height: '40px' }}
                            >
                              {prof.first_name?.[0]}{prof.last_name?.[0]}
                            </div>
                          )}
                        </div>
                        <div className="flex-grow-1 ms-3">
                          <div className="fw-medium">{prof.full_name}</div>
                          <small className="text-muted">{prof.email}</small>
                        </div>
                        <button
                          className="btn btn-sm btn-primary"
                          onClick={() => handleAddMember(prof.id)}
                        >
                          <i className="ri-add-line me-1"></i>
                          Aggiungi
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 text-muted">
                    <i className="ri-user-search-line fs-1 d-block mb-2"></i>
                    Nessun professionista disponibile per questo tipo di team
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowAddMemberModal(false)}
                >
                  Chiudi
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default TeamsDetail;

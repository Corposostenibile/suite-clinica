import { useState, useEffect } from 'react';
import { Link, useOutletContext, useParams } from 'react-router-dom';
import {
  ROLE_LABELS,
  SPECIALTY_LABELS,
  ROLE_COLORS,
  SPECIALTY_COLORS
} from '../../services/teamService';
import teamService from '../../services/teamService';

// Gradient colors by role
const ROLE_GRADIENTS = {
  admin: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  team_leader: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  professionista: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  team_esterno: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
};

function Profilo() {
  const { id } = useParams();
  const outletContext = useOutletContext();
  const currentUser = outletContext?.user || null;
  const [profileUser, setProfileUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('info');

  // If ID is provided in URL, fetch that user's profile
  // Otherwise, show current user's profile
  useEffect(() => {
    if (id) {
      // Fetch specific user profile
      const fetchUserProfile = async () => {
        setLoading(true);
        try {
          const data = await teamService.getTeamMember(id);
          // Ensure teams arrays are initialized
          setProfileUser({
            ...data,
            teams: data.teams || [],
            teams_led: data.teams_led || []
          });
        } catch (err) {
          console.error('Error fetching user profile:', err);
          setProfileUser(null);
        } finally {
          setLoading(false);
        }
      };
      fetchUserProfile();
    } else {
      // Use current user from context
      if (currentUser) {
        setProfileUser({
          ...currentUser,
          teams: currentUser.teams || [],
          teams_led: currentUser.teams_led || []
        });
      }
    }
  }, [id, currentUser]);

  const user = profileUser;
  const isOwnProfile = !id || (currentUser && user && currentUser.id === user.id);

  if (loading || !user) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Caricamento...</span>
        </div>
      </div>
    );
  }

  const role = user.role || 'professionista';
  const specialty = user.specialty;

  return (
    <>
      {/* Page Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1">{isOwnProfile ? 'Il Mio Profilo' : `Profilo di ${user.full_name}`}</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/welcome">Home</Link>
              </li>
              <li className="breadcrumb-item active">Profilo</li>
            </ol>
          </nav>
        </div>
        {isOwnProfile && (
          <Link to={`/team-modifica/${user.id}`} className="btn btn-primary">
            <i className="ri-edit-line me-1"></i>
            Modifica Profilo
          </Link>
        )}
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
                {user.is_active ? (
                  <span className="badge bg-success">
                    <i className="ri-checkbox-circle-line me-1"></i>Attivo
                  </span>
                ) : (
                  <span className="badge bg-dark bg-opacity-75">
                    <i className="ri-close-circle-line me-1"></i>Inattivo
                  </span>
                )}
                {user.is_external && (
                  <span className="badge bg-white text-dark">
                    <i className="ri-external-link-line me-1"></i>Esterno
                  </span>
                )}
              </div>

              {/* Avatar positioned at bottom */}
              <div className="position-absolute start-50 translate-middle-x" style={{ bottom: '-50px' }}>
                {user.avatar_path ? (
                  <img
                    src={user.avatar_path}
                    alt={user.full_name}
                    className="rounded-circle border border-4 border-white shadow"
                    style={{ width: '100px', height: '100px', objectFit: 'cover', background: '#fff' }}
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
                    <div className="fw-semibold">#{user.id}</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">Team Guidati</div>
                    <div className="fw-semibold">{user.teams_led?.length || 0}</div>
                  </div>
                </div>
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
                    {user.teams_led?.length > 0 && (
                      <span className="badge bg-primary ms-2">{user.teams_led.length}</span>
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
                  </div>

                  {/* Account Info */}
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Dettagli Account
                    </h6>
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
                          <div className="rounded-circle d-flex align-items-center justify-content-center"
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
                  {/* Teams Led */}
                  <div className="mb-4">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      <i className="ri-shield-star-line me-2"></i>
                      Team Guidati
                    </h6>
                    {user.teams_led && user.teams_led.length > 0 ? (
                      <div className="row g-3">
                        {user.teams_led.map((team) => (
                          <div key={team.id} className="col-12">
                            <Link 
                              to={`/teams-dettaglio/${team.id}`}
                              className="text-decoration-none"
                            >
                              <div className="border rounded-3 p-3 d-flex align-items-center">
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
                              </div>
                            </Link>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-3 bg-light rounded-3">
                        <small className="text-muted">Non guida nessun team</small>
                      </div>
                    )}
                  </div>

                  {/* Teams Member */}
                  <div>
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      <i className="ri-group-line me-2"></i>
                      Membro di Team
                    </h6>
                    {user.teams && user.teams.length > 0 ? (
                      <div className="row g-3">
                        {user.teams.map((team) => (
                          <div key={team.id} className="col-12">
                            <Link 
                              to={`/teams-dettaglio/${team.id}`}
                              className="text-decoration-none"
                            >
                              <div className="border rounded-3 p-3 d-flex align-items-center">
                                <div className="flex-shrink-0">
                                  <div
                                    className="rounded-circle d-flex align-items-center justify-content-center text-white"
                                    style={{
                                      width: '48px',
                                      height: '48px',
                                      background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
                                    }}
                                  >
                                    <i className="ri-user-line fs-5"></i>
                                  </div>
                                </div>
                                <div className="flex-grow-1 ms-3">
                                  <h6 className="mb-0">{team.name}</h6>
                                  <small className="text-muted">
                                    <i className="ri-user-line me-1"></i>
                                    Membro
                                  </small>
                                </div>
                              </div>
                            </Link>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-3 bg-light rounded-3">
                        <small className="text-muted">Non è membro di nessun team</small>
                      </div>
                    )}
                  </div>
                </>
              )}

              {/* Clienti Tab */}
              {activeTab === 'clienti' && (
                <div className="text-center py-5">
                  <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                       style={{ width: '64px', height: '64px' }}>
                    <i className="ri-user-heart-line text-muted fs-3"></i>
                  </div>
                  <p className="text-muted mb-0">Qui vedrai i tuoi clienti</p>
                </div>
              )}

              {/* Check Tab */}
              {activeTab === 'check' && (
                <div className="text-center py-5">
                  <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                       style={{ width: '64px', height: '64px' }}>
                    <i className="ri-checkbox-multiple-line text-muted fs-3"></i>
                  </div>
                  <p className="text-muted mb-0">Qui vedrai i check che hai ricevuto</p>
                </div>
              )}

              {/* Quality Tab */}
              {activeTab === 'quality' && (
                <div className="text-center py-5">
                  <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                       style={{ width: '64px', height: '64px' }}>
                    <i className="ri-star-line text-muted fs-3"></i>
                  </div>
                  <p className="text-muted mb-0">Qui vedrai il tuo quality</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default Profilo;

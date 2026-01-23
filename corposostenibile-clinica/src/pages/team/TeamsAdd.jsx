import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import teamService, {
  TEAM_TYPES,
  TEAM_TYPE_LABELS,
  TEAM_TYPE_COLORS,
  TEAM_TYPE_ICONS,
} from '../../services/teamService';

function TeamsAdd() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEditMode = Boolean(id);

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // Form data
  const [formData, setFormData] = useState({
    name: '',
    team_type: '',
    head_id: '',
    description: '',
    member_ids: [],
  });

  // Available options
  const [availableLeaders, setAvailableLeaders] = useState([]);
  const [availableProfessionals, setAvailableProfessionals] = useState([]);
  const [loadingLeaders, setLoadingLeaders] = useState(false);
  const [loadingProfessionals, setLoadingProfessionals] = useState(false);

  // Load team data if editing
  useEffect(() => {
    if (isEditMode) {
      fetchTeam();
    }
  }, [id]);

  // Load available leaders and professionals when team_type changes
  useEffect(() => {
    if (formData.team_type) {
      fetchAvailableOptions(formData.team_type);
    } else {
      setAvailableLeaders([]);
      setAvailableProfessionals([]);
    }
  }, [formData.team_type]);

  const fetchTeam = async () => {
    setLoading(true);
    try {
      const data = await teamService.getTeam(id);
      setFormData({
        name: data.name || '',
        team_type: data.team_type || '',
        head_id: data.head_id || '',
        description: data.description || '',
        member_ids: (data.members || []).map(m => m.id),
      });
    } catch (err) {
      console.error('Error fetching team:', err);
      setError('Errore nel caricamento del team');
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableOptions = async (teamType) => {
    setLoadingLeaders(true);
    setLoadingProfessionals(true);

    try {
      const [leadersData, professionalsData] = await Promise.all([
        teamService.getAvailableLeaders(teamType),
        teamService.getAvailableProfessionals(teamType),
      ]);

      setAvailableLeaders(leadersData.leaders || []);
      setAvailableProfessionals(professionalsData.professionals || []);
    } catch (err) {
      console.error('Error fetching options:', err);
    } finally {
      setLoadingLeaders(false);
      setLoadingProfessionals(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const newData = { ...prev, [name]: value };

      // Reset head_id and member_ids when team_type changes
      if (name === 'team_type') {
        newData.head_id = '';
        newData.member_ids = [];
      }

      return newData;
    });
  };

  const handleMemberToggle = (userId) => {
    setFormData(prev => {
      const memberIds = prev.member_ids.includes(userId)
        ? prev.member_ids.filter(id => id !== userId)
        : [...prev.member_ids, userId];
      return { ...prev, member_ids: memberIds };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!formData.name.trim()) {
      setError('Il nome del team è obbligatorio');
      return;
    }
    if (!formData.team_type) {
      setError('Il tipo di team è obbligatorio');
      return;
    }

    setSaving(true);

    try {
      const dataToSend = {
        name: formData.name.trim(),
        team_type: formData.team_type,
        head_id: formData.head_id || null,
        description: formData.description.trim() || null,
        member_ids: formData.member_ids,
      };

      if (isEditMode) {
        await teamService.updateTeam(id, dataToSend);
      } else {
        await teamService.createTeam(dataToSend);
      }

      navigate('/teams');
    } catch (err) {
      console.error('Error saving team:', err);
      setError(err.response?.data?.message || 'Errore durante il salvataggio');
    } finally {
      setSaving(false);
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

  return (
    <>
      {/* Page Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1">{isEditMode ? 'Modifica Team' : 'Nuovo Team'}</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/teams">Team</Link>
              </li>
              <li className="breadcrumb-item active">
                {isEditMode ? 'Modifica' : 'Nuovo'}
              </li>
            </ol>
          </nav>
        </div>
        <Link to="/teams" className="btn btn-outline-secondary">
          <i className="ri-arrow-left-line me-1"></i>
          Torna alla Lista
        </Link>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="alert alert-danger alert-dismissible fade show" role="alert">
          <i className="ri-error-warning-line me-2"></i>
          {error}
          <button type="button" className="btn-close" onClick={() => setError(null)}></button>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <div className="row">
          {/* Left Column - Team Preview */}
          <div className="col-lg-4">
            <div className="card shadow-sm border-0">
              <div className="card-body text-center">
                <h6 className="mb-3">Anteprima Team</h6>

                {/* Team Icon Preview */}
                <div className="mb-3">
                  <div className="d-inline-block position-relative">
                    {formData.team_type ? (
                      <div
                        className="rounded-circle d-flex align-items-center justify-content-center text-white"
                        style={{
                          width: '150px',
                          height: '150px',
                          background: `var(--bs-${TEAM_TYPE_COLORS[formData.team_type]})`
                        }}
                      >
                        <i className={`${TEAM_TYPE_ICONS[formData.team_type]}`} style={{ fontSize: '4rem' }}></i>
                      </div>
                    ) : (
                      <div
                        className="rounded-circle bg-light d-flex align-items-center justify-content-center border"
                        style={{ width: '150px', height: '150px' }}
                      >
                        <i className="ri-team-line text-muted" style={{ fontSize: '4rem' }}></i>
                      </div>
                    )}
                  </div>
                </div>

                <h5 className="mb-1">{formData.name || 'Nome Team'}</h5>
                {formData.team_type && (
                  <span className={`badge bg-${TEAM_TYPE_COLORS[formData.team_type]}`}>
                    {TEAM_TYPE_LABELS[formData.team_type]}
                  </span>
                )}
                <p className="text-muted small mt-2 mb-0">
                  {formData.description || 'Nessuna descrizione'}
                </p>

                {/* Stats */}
                <div className="d-flex justify-content-center gap-4 mt-3 pt-3 border-top">
                  <div className="text-center">
                    <div className="fw-bold text-primary">
                      {formData.head_id ? '1' : '0'}
                    </div>
                    <small className="text-muted">Leader</small>
                  </div>
                  <div className="text-center">
                    <div className="fw-bold text-primary">
                      {formData.member_ids.length}
                    </div>
                    <small className="text-muted">Membri</small>
                  </div>
                </div>
              </div>
            </div>

          </div>

          {/* Right Column - Form Fields */}
          <div className="col-lg-8">
            <div className="card shadow-sm border-0">
              <div className="card-body">
                {/* Basic Info Section */}
                <h6 className="mb-3">Informazioni Base</h6>
                <div className="row g-3 mb-4">
                  <div className="col-md-6">
                    <label className="form-label">Tipo Team *</label>
                    <select
                      className="form-select"
                      name="team_type"
                      value={formData.team_type}
                      onChange={handleChange}
                      disabled={isEditMode}
                      required
                    >
                      <option value="">Seleziona tipo...</option>
                      {Object.entries(TEAM_TYPE_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                    {isEditMode && (
                      <small className="text-muted">
                        Il tipo non può essere modificato
                      </small>
                    )}
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Nome Team *</label>
                    <input
                      type="text"
                      className="form-control"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      placeholder="Es. Team Alpha, Team Nord..."
                      required
                    />
                  </div>
                  <div className="col-12">
                    <label className="form-label">Descrizione</label>
                    <textarea
                      className="form-control"
                      name="description"
                      value={formData.description}
                      onChange={handleChange}
                      rows={2}
                      placeholder="Descrizione opzionale del team..."
                    />
                  </div>
                </div>

                <hr className="my-4" />

                {/* Team Leader Section */}
                <h6 className="mb-3">Team Leader</h6>
                <div className="row g-3 mb-4">
                  <div className="col-12">
                    {loadingLeaders ? (
                      <div className="text-center py-3">
                        <div className="spinner-border spinner-border-sm text-primary" role="status">
                          <span className="visually-hidden">Caricamento...</span>
                        </div>
                      </div>
                    ) : formData.team_type ? (
                      <>
                        <select
                          className="form-select"
                          name="head_id"
                          value={formData.head_id}
                          onChange={handleChange}
                        >
                          <option value="">Nessun Team Leader</option>
                          {availableLeaders.map(leader => (
                            <option key={leader.id} value={leader.id}>
                              {leader.full_name} ({leader.email})
                            </option>
                          ))}
                        </select>
                        {availableLeaders.length === 0 && (
                          <small className="text-warning">
                            <i className="ri-alert-line me-1"></i>
                            Nessun Team Leader disponibile per questo tipo
                          </small>
                        )}
                      </>
                    ) : (
                      <div className="form-control bg-light text-muted">
                        Seleziona prima il tipo di team
                      </div>
                    )}
                  </div>
                </div>

                <hr className="my-4" />

                {/* Members Section */}
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h6 className="mb-0">
                    Membri del Team
                    {formData.member_ids.length > 0 && (
                      <span className="badge bg-primary ms-2">{formData.member_ids.length}</span>
                    )}
                  </h6>
                  {formData.member_ids.length > 0 && (
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => setFormData(prev => ({ ...prev, member_ids: [] }))}
                    >
                      Deseleziona tutti
                    </button>
                  )}
                </div>

                {loadingProfessionals ? (
                  <div className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Caricamento...</span>
                    </div>
                  </div>
                ) : formData.team_type ? (
                  availableProfessionals.length > 0 ? (
                    <div className="row g-2" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                      {availableProfessionals.map(prof => {
                        const isSelected = formData.member_ids.includes(prof.id);
                        return (
                          <div key={prof.id} className="col-md-6">
                            <div
                              className={`border rounded p-2 cursor-pointer ${isSelected ? 'border-primary bg-primary bg-opacity-10' : ''}`}
                              style={{ cursor: 'pointer' }}
                              onClick={() => handleMemberToggle(prof.id)}
                            >
                              <div className="d-flex align-items-center">
                                <div className="form-check mb-0">
                                  <input
                                    type="checkbox"
                                    className="form-check-input"
                                    checked={isSelected}
                                    onChange={() => {}}
                                  />
                                </div>
                                <div className="flex-shrink-0 ms-2">
                                  {prof.avatar_path ? (
                                    <img
                                      src={prof.avatar_path}
                                      alt={prof.full_name}
                                      className="rounded-circle"
                                      style={{ width: '32px', height: '32px', objectFit: 'cover' }}
                                    />
                                  ) : (
                                    <div
                                      className="rounded-circle bg-secondary d-flex align-items-center justify-content-center text-white"
                                      style={{ width: '32px', height: '32px', fontSize: '0.75rem' }}
                                    >
                                      {prof.first_name?.[0]}{prof.last_name?.[0]}
                                    </div>
                                  )}
                                </div>
                                <div className="flex-grow-1 ms-2 overflow-hidden">
                                  <div className="fw-medium small text-truncate">{prof.full_name}</div>
                                  <small className="text-muted text-truncate d-block">{prof.email}</small>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-4 text-muted">
                      <i className="ri-user-search-line fs-1 d-block mb-2"></i>
                      Nessun professionista disponibile
                    </div>
                  )
                ) : (
                  <div className="text-center py-4 text-muted">
                    <i className="ri-information-line fs-1 d-block mb-2"></i>
                    Seleziona prima il tipo di team
                  </div>
                )}
              </div>

              {/* Card Footer */}
              <div className="card-footer bg-transparent border-top">
                <div className="d-flex justify-content-end gap-2">
                  <Link to="/teams" className="btn btn-outline-secondary">
                    Annulla
                  </Link>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={saving}
                  >
                    {saving ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2"></span>
                        Salvataggio...
                      </>
                    ) : (
                      <>
                        <i className="ri-check-line me-1"></i>
                        {isEditMode ? 'Salva Modifiche' : 'Crea Team'}
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </form>
    </>
  );
}

export default TeamsAdd;

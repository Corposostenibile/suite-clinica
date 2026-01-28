import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import teamService, {
  USER_ROLES,
  USER_SPECIALTIES,
  ROLE_LABELS,
} from '../../services/teamService';
import originsService from '../../services/originsService';

function TeamAdd() {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEditMode = Boolean(id);
  const fileInputRef = useRef(null);

  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(isEditMode);
  const [error, setError] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState(null);
  const [avatarFile, setAvatarFile] = useState(null);

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
    role: '',
    specialty: '',
    avatar_path: '',
  });

  const [allOrigins, setAllOrigins] = useState([]);
  const [selectedOrigins, setSelectedOrigins] = useState([]);

  // Fetch origins on component mount
  useEffect(() => {
    fetchOrigins();
  }, []);

  const fetchOrigins = async () => {
    try {
      const result = await originsService.getOrigins();
      if (result.success) {
        setAllOrigins(result.origins);
      }
    } catch (err) {
      console.error('Error fetching origins:', err);
    }
  };

  // Fetch member data in edit mode
  useEffect(() => {
    if (isEditMode) {
      fetchMemberData();
    }
  }, [id]);

  const fetchMemberData = async () => {
    setLoadingData(true);
    try {
      const data = await teamService.getTeamMember(id);
      setFormData({
        email: data.email || '',
        password: '',
        password_confirm: '',
        first_name: data.first_name || '',
        last_name: data.last_name || '',
        role: data.role || '',
        specialty: data.specialty || '',

      });
      if (data.role === 'influencer' && data.influencer_origins) {
        setSelectedOrigins(data.influencer_origins.map(o => o.id));
      }
      if (data.avatar_path) {
        setAvatarPreview(data.avatar_path);
      }
    } catch (err) {
      console.error('Error fetching member:', err);
      setError('Errore nel caricamento dei dati del membro');
    } finally {
      setLoadingData(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    if (name === 'role') {
      setFormData(prev => ({ ...prev, specialty: '' }));
    }
  };


  const handleOriginChange = (originId) => {
    setSelectedOrigins(prev => {
      if (prev.includes(originId)) {
        return prev.filter(id => id !== originId);
      } else {
        return [...prev, originId];
      }
    });
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleAvatarChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        setError('Il file deve essere inferiore a 5MB');
        return;
      }
      if (!file.type.startsWith('image/')) {
        setError('Il file deve essere un\'immagine');
        return;
      }
      setAvatarFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const removeAvatar = () => {
    setAvatarFile(null);
    setAvatarPreview(null);
    setFormData(prev => ({ ...prev, avatar_path: '' }));
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const validateForm = () => {
    if (!formData.email) {
      setError('L\'email è obbligatoria');
      return false;
    }

    // Password required only for new members
    if (!isEditMode) {
      if (!formData.password) {
        setError('La password è obbligatoria');
        return false;
      }
      if (formData.password.length < 8) {
        setError('La password deve essere di almeno 8 caratteri');
        return false;
      }
    }

    // If password is provided, check confirmation
    if (formData.password && formData.password !== formData.password_confirm) {
      setError('Le password non coincidono');
      return false;
    }

    if (!formData.first_name || !formData.last_name) {
      setError('Nome e Cognome sono obbligatori');
      return false;
    }
    if (!formData.role) {
      setError('Seleziona un ruolo');
      return false;
    }
    setError(null);
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) return;

    setLoading(true);
    setError(null);

    try {
      const dataToSend = {
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name,
        role: formData.role,

        specialty: formData.specialty || null,
        origin_ids: formData.role === 'influencer' ? selectedOrigins : [],
      };

      // Only include password if provided
      if (formData.password) {
        dataToSend.password = formData.password;
      }

      let userId;
      if (isEditMode) {
        await teamService.updateTeamMember(id, dataToSend);
        userId = id;
      } else {
        const result = await teamService.createTeamMember(dataToSend);
        userId = result.id;
      }

      // Upload avatar if a new file was selected
      if (avatarFile && userId) {
        try {
          await teamService.uploadAvatar(userId, avatarFile);
        } catch (avatarErr) {
          console.error('Error uploading avatar:', avatarErr);
          // Continue anyway, the member was saved
        }
      }

      navigate('/team-lista', {
        state: { message: isEditMode ? 'Membro aggiornato con successo!' : 'Membro aggiunto con successo!' }
      });
    } catch (err) {
      console.error('Error saving team member:', err);
      setError(err.response?.data?.message || 'Errore durante il salvataggio');
    } finally {
      setLoading(false);
    }
  };

  const getSpecialtiesForRole = () => {
    return USER_SPECIALTIES[formData.role] || [];
  };

  if (loadingData) {
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
          <h4 className="mb-1">{isEditMode ? 'Modifica Membro' : 'Nuovo Membro'}</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/team-lista">Team</Link>
              </li>
              <li className="breadcrumb-item active">
                {isEditMode ? 'Modifica' : 'Nuovo'}
              </li>
            </ol>
          </nav>
        </div>
        <Link to="/team-lista" className="btn btn-outline-secondary">
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
          {/* Left Column - Avatar */}
          <div className="col-lg-4">
            <div className="card shadow-sm border-0">
              <div className="card-body text-center">
                <h6 className="mb-3">Foto Profilo</h6>

                {/* Avatar Preview */}
                <div className="mb-3">
                  <div
                    onClick={handleAvatarClick}
                    className="d-inline-block position-relative cursor-pointer"
                    style={{ cursor: 'pointer' }}
                  >
                    {avatarPreview ? (
                      <img
                        src={avatarPreview}
                        alt="Avatar"
                        className="rounded-circle border"
                        style={{ width: '150px', height: '150px', objectFit: 'cover' }}
                      />
                    ) : (
                      <div
                        className="rounded-circle bg-light d-flex align-items-center justify-content-center border"
                        style={{ width: '150px', height: '150px' }}
                      >
                        <span className="text-primary fw-bold" style={{ fontSize: '3rem' }}>
                          {formData.first_name?.[0]?.toUpperCase() || '?'}
                          {formData.last_name?.[0]?.toUpperCase() || '?'}
                        </span>
                      </div>
                    )}
                    <div
                      className="position-absolute bottom-0 end-0 bg-primary rounded-circle d-flex align-items-center justify-content-center"
                      style={{ width: '40px', height: '40px' }}
                    >
                      <i className="ri-camera-line text-white"></i>
                    </div>
                  </div>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarChange}
                  className="d-none"
                />

                <div className="d-flex gap-2 justify-content-center">
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary"
                    onClick={handleAvatarClick}
                  >
                    <i className="ri-upload-2-line me-1"></i>
                    Carica
                  </button>
                  {avatarPreview && (
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-danger"
                      onClick={removeAvatar}
                    >
                      <i className="ri-delete-bin-line me-1"></i>
                      Rimuovi
                    </button>
                  )}
                </div>
                <small className="text-muted d-block mt-2">JPG, PNG. Max 5MB</small>
              </div>
            </div>
          </div>

          {/* Right Column - Form Fields */}
          <div className="col-lg-8">
            <div className="card shadow-sm border-0">
              <div className="card-body">
                {/* Personal Info Section */}
                <h6 className="mb-3">Dati Personali</h6>
                <div className="row g-3 mb-4">
                  <div className="col-md-6">
                    <label className="form-label">Nome *</label>
                    <input
                      type="text"
                      className="form-control"
                      name="first_name"
                      value={formData.first_name}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Cognome *</label>
                    <input
                      type="text"
                      className="form-control"
                      name="last_name"
                      value={formData.last_name}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>

                <hr className="my-4" />

                {/* Account Section */}
                <h6 className="mb-3">Credenziali di Accesso</h6>
                <div className="row g-3 mb-4">
                  <div className="col-md-12">
                    <label className="form-label">Email *</label>
                    <input
                      type="email"
                      className="form-control"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="email@esempio.com"
                      required
                    />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">
                      Password {isEditMode ? '(lascia vuoto per non modificare)' : '*'}
                    </label>
                    <input
                      type="password"
                      className="form-control"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      placeholder={isEditMode ? '••••••••' : 'Minimo 8 caratteri'}
                      required={!isEditMode}
                    />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">
                      Conferma Password {isEditMode ? '' : '*'}
                    </label>
                    <input
                      type="password"
                      className="form-control"
                      name="password_confirm"
                      value={formData.password_confirm}
                      onChange={handleChange}
                      placeholder={isEditMode ? '••••••••' : 'Ripeti la password'}
                      required={!isEditMode}
                    />
                  </div>
                </div>

                <hr className="my-4" />

                {/* Role Section */}
                <h6 className="mb-3">Ruolo e Specializzazione</h6>
                <div className="row g-3">
                  <div className="col-md-6">
                    <label className="form-label">Ruolo *</label>
                    <select
                      className="form-select"
                      name="role"
                      value={formData.role}
                      onChange={handleChange}
                      required
                    >
                      <option value="">Seleziona Ruolo</option>
                      {Object.entries(ROLE_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                    <small className="text-muted">
                      {formData.role === 'admin' && 'Accesso completo a tutte le funzionalita'}
                      {formData.role === 'team_leader' && 'Gestisce un team di professionisti'}
                      {formData.role === 'professionista' && 'Nutrizionista, Psicologo o Coach'}
                      {formData.role === 'team_esterno' && 'Collaboratore esterno'}
                    </small>
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">Specializzazione</label>
                    <select
                      className="form-select"
                      name="specialty"
                      value={formData.specialty}
                      onChange={handleChange}
                      disabled={!formData.role || getSpecialtiesForRole().length === 0}
                    >
                      <option value="">
                        {getSpecialtiesForRole().length === 0 ? 'Non applicabile' : 'Seleziona Specializzazione'}
                      </option>
                      {getSpecialtiesForRole().map(({ value, label }) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Origins Selection for Influencers */}
                {formData.role === 'influencer' && (
                  <div className="mt-4 animate__animated animate__fadeIn">
                    <h6 className="mb-3">Assegna Origini (Campagne)</h6>
                    <div className="card bg-light border-0">
                      <div className="card-body">
                        {allOrigins.length === 0 ? (
                          <p className="text-muted mb-0">Nessuna origine disponibile.</p>
                        ) : (
                          <div className="row g-2">
                             {allOrigins
                                .filter(o => o.active) // Show only active origins
                                .map(origin => (
                                <div className="col-md-6" key={origin.id}>
                                  <div className="form-check">
                                    <input
                                      className="form-check-input"
                                      type="checkbox"
                                      id={`origin-${origin.id}`}
                                      checked={selectedOrigins.includes(origin.id)}
                                      onChange={() => handleOriginChange(origin.id)}
                                    />
                                    <label className="form-check-label" htmlFor={`origin-${origin.id}`}>
                                      {origin.name}
                                    </label>
                                  </div>
                                </div>
                             ))}
                          </div>
                        )}
                        <small className="text-muted d-block mt-2">
                          Seleziona le origini dei clienti visibili a questo influencer.
                        </small>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Card Footer */}
              <div className="card-footer bg-transparent border-top">
                <div className="d-flex justify-content-end gap-2">
                  <Link to="/team-lista" className="btn btn-outline-secondary">
                    Annulla
                  </Link>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2"></span>
                        Salvataggio...
                      </>
                    ) : (
                      <>
                        <i className="ri-check-line me-1"></i>
                        {isEditMode ? 'Salva Modifiche' : 'Crea Membro'}
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

export default TeamAdd;

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import trialUserService, { TRIAL_STAGES } from '../../services/trialUserService';

function TrialUserForm() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(userId);

  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(isEdit);
  const [error, setError] = useState(null);

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    password_confirm: '',
    specialty: '',
    trial_stage: 1,
    trial_supervisor_id: '',
  });

  const [supervisors, setSupervisors] = useState([]);
  const [loadingSupervisors, setLoadingSupervisors] = useState(false);

  const specialties = [
    { value: 'nutrizione', label: 'Nutrizione' },
    { value: 'coach', label: 'Coach' },
    { value: 'psicologia', label: 'Psicologia' },
  ];

  // Fetch user data in edit mode
  useEffect(() => {
    if (isEdit) {
      fetchUserData();
    }
  }, [userId]);

  const fetchUserData = async () => {
    setLoadingData(true);
    try {
      const result = await trialUserService.get(userId);
      if (result.success) {
        const user = result.trial_user;
        setFormData({
          first_name: user.first_name || '',
          last_name: user.last_name || '',
          email: user.email || '',
          password: '',
          password_confirm: '',
          specialty: user.specialty || '',
          trial_stage: user.trial_stage || 1,
          trial_supervisor_id: user.supervisor?.id || '',
        });
      } else {
        setError('Utente non trovato');
      }
    } catch (err) {
      console.error('Error fetching user:', err);
      setError('Errore nel caricamento dei dati');
    } finally {
      setLoadingData(false);
    }
  };

  // Fetch supervisors when specialty changes
  useEffect(() => {
    if (formData.specialty) {
      fetchSupervisors(formData.specialty);
    } else {
      setSupervisors([]);
      setFormData(prev => ({ ...prev, trial_supervisor_id: '' }));
    }
  }, [formData.specialty]);

  const fetchSupervisors = async (specialty) => {
    setLoadingSupervisors(true);
    try {
      const result = await trialUserService.getSupervisors(specialty);
      if (result.success) {
        setSupervisors(result.supervisors);
      }
    } catch (err) {
      console.error('Error fetching supervisors:', err);
    } finally {
      setLoadingSupervisors(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Reset supervisor when specialty changes
    if (name === 'specialty') {
      setFormData(prev => ({ ...prev, [name]: value, trial_supervisor_id: '' }));
    }
  };

  const validateForm = () => {
    if (!formData.first_name || !formData.last_name) {
      setError('Nome e Cognome sono obbligatori');
      return false;
    }
    if (!formData.email) {
      setError("L'email è obbligatoria");
      return false;
    }
    if (!formData.specialty) {
      setError('Seleziona una specializzazione');
      return false;
    }
    if (!isEdit) {
      if (!formData.password) {
        setError('La password è obbligatoria');
        return false;
      }
      if (formData.password.length < 8) {
        setError('La password deve essere di almeno 8 caratteri');
        return false;
      }
    }
    if (formData.password && formData.password !== formData.password_confirm) {
      setError('Le password non coincidono');
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
      const data = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        email: formData.email.trim(),
        specialty: formData.specialty,
        trial_stage: parseInt(formData.trial_stage),
        trial_supervisor_id: formData.trial_supervisor_id ? parseInt(formData.trial_supervisor_id) : null,
      };

      if (formData.password) {
        data.password = formData.password;
      }

      let result;
      if (isEdit) {
        result = await trialUserService.update(userId, data);
      } else {
        result = await trialUserService.create(data);
      }

      if (result.success) {
        navigate(isEdit ? `/in-prova/${userId}` : '/in-prova');
      } else {
        setError(result.error || 'Errore nel salvataggio');
      }
    } catch (err) {
      console.error('Error saving:', err);
      setError(err.response?.data?.error || 'Errore nel salvataggio');
    } finally {
      setLoading(false);
    }
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
          <h4 className="mb-1">{isEdit ? 'Modifica Professionista' : 'Nuovo Professionista In Prova'}</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/in-prova">In Prova</Link>
              </li>
              <li className="breadcrumb-item active">
                {isEdit ? 'Modifica' : 'Nuovo'}
              </li>
            </ol>
          </nav>
        </div>
        <Link to="/in-prova" className="btn btn-outline-secondary">
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
          {/* Left Column - Specialty Selection */}
          <div className="col-lg-4">
            <div className="card shadow-sm border-0">
              <div className="card-body">
                <h6 className="mb-3">Specializzazione *</h6>

                <div className="d-flex flex-column gap-2">
                  {specialties.map((s) => (
                    <label
                      key={s.value}
                      className={`d-flex align-items-center p-3 rounded-3 ${formData.specialty === s.value ? 'border-primary' : ''}`}
                      style={{
                        cursor: 'pointer',
                        border: formData.specialty === s.value
                          ? '2px solid #0d6efd'
                          : '2px solid #e9ecef',
                        background: formData.specialty === s.value
                          ? '#e7f1ff'
                          : '#f8f9fa',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <input
                        type="radio"
                        name="specialty"
                        value={s.value}
                        checked={formData.specialty === s.value}
                        onChange={handleChange}
                        className="form-check-input me-3"
                      />
                      <div>
                        <div className="fw-semibold">{s.label}</div>
                      </div>
                    </label>
                  ))}
                </div>

                {formData.specialty && (
                  <>
                    <hr className="my-3" />
                    <h6 className="mb-3">Supervisor</h6>
                    {loadingSupervisors ? (
                      <div className="text-center py-2">
                        <span className="spinner-border spinner-border-sm text-primary"></span>
                      </div>
                    ) : (
                      <select
                        className="form-select"
                        name="trial_supervisor_id"
                        value={formData.trial_supervisor_id}
                        onChange={handleChange}
                      >
                        <option value="">Seleziona supervisor...</option>
                        {supervisors.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.full_name} {s.is_admin ? '(Admin)' : '(Team Leader)'}
                          </option>
                        ))}
                      </select>
                    )}
                    <small className="text-muted d-block mt-2">
                      Il supervisor gestisce questo professionista
                    </small>
                  </>
                )}
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
                      Password {isEdit ? '(lascia vuoto per non modificare)' : '*'}
                    </label>
                    <input
                      type="password"
                      className="form-control"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      placeholder={isEdit ? '••••••••' : 'Minimo 8 caratteri'}
                      required={!isEdit}
                    />
                  </div>
                  <div className="col-md-6">
                    <label className="form-label">
                      Conferma Password {isEdit ? '' : '*'}
                    </label>
                    <input
                      type="password"
                      className="form-control"
                      name="password_confirm"
                      value={formData.password_confirm}
                      onChange={handleChange}
                      placeholder={isEdit ? '••••••••' : 'Ripeti la password'}
                      required={!isEdit}
                    />
                  </div>
                </div>

                <hr className="my-4" />

                {/* Trial Stage Section */}
                <h6 className="mb-3">Stage Iniziale</h6>
                <div className="row g-3">
                  <div className="col-12">
                    <div className="d-flex flex-column gap-2">
                      {Object.entries(TRIAL_STAGES).filter(([key]) => key !== '3').map(([key, config]) => (
                        <label
                          key={key}
                          className="d-flex align-items-center p-3 rounded-3"
                          style={{
                            cursor: 'pointer',
                            border: formData.trial_stage === parseInt(key)
                              ? `2px solid ${config.color}`
                              : '2px solid #e9ecef',
                            background: formData.trial_stage === parseInt(key)
                              ? config.bgColor
                              : '#f8f9fa',
                            transition: 'all 0.2s ease',
                          }}
                        >
                          <input
                            type="radio"
                            name="trial_stage"
                            value={key}
                            checked={formData.trial_stage === parseInt(key)}
                            onChange={(e) => setFormData(prev => ({ ...prev, trial_stage: parseInt(e.target.value) }))}
                            className="form-check-input me-3"
                          />
                          <i className={`${config.icon} me-2`} style={{ color: config.color, fontSize: '18px' }}></i>
                          <div>
                            <span className="fw-semibold" style={{ color: config.color }}>
                              {config.label}
                            </span>
                            <small className="text-muted ms-2">{config.description}</small>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Card Footer */}
              <div className="card-footer bg-transparent border-top">
                <div className="d-flex justify-content-end gap-2">
                  <Link to={isEdit ? `/in-prova/${userId}` : '/in-prova'} className="btn btn-outline-secondary">
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
                        {isEdit ? 'Salva Modifiche' : 'Crea Professionista'}
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

export default TrialUserForm;

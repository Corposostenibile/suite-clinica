import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Modal } from 'react-bootstrap';
import { FaEnvelope, FaLock, FaEye, FaEyeSlash } from 'react-icons/fa';
import authService from '../services/authService';
import '../styles/auth.css';
import logo from '../images/logo_foglia.png';

function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(searchParams.get('message') || '');
  const [showPassword, setShowPassword] = useState(false);
  const [shake, setShake] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [showSupportModal, setShowSupportModal] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (shake) {
      const timer = setTimeout(() => setShake(false), 600);
      return () => clearTimeout(timer);
    }
  }, [shake]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await authService.login(
        formData.email,
        formData.password,
        formData.rememberMe
      );

      if (response.success) {
        const next = searchParams.get('next') || '/welcome';
        window.location.href = next;
      }
    } catch (err) {
      const message = err.response?.data?.error || 'Credenziali non valide. Riprova.';
      setError(message);
      setShake(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-account">
      <div className="row h-100">
        {/* Left Side - Decorative Panel */}
        <div className="col-lg-6 align-self-start login-panel-left">
          <div className="account-info-area">
            <video className="login-video" autoPlay loop muted playsInline>
              <source src="/login.mp4" type="video/mp4" />
            </video>
            <div className="login-content">
              <p className="sub-title">La gestione dei tuoi pazienti non è mai stata così semplice</p>
              <h1 className="title">Suite <span>Clinica</span></h1>
              <p className="text">Il nostro strumento quotidiano per prenderci cura dei pazienti in modo semplice e organizzato</p>
            </div>
          </div>
        </div>

        {/* Right Side - Login Form */}
        <div className="col-lg-6 col-md-7 col-sm-12 mx-auto align-self-center">
          <div className={`login-form${mounted ? ' login-form--visible' : ''}`}>
            <div className="login-logo">
              <img src={logo} alt="Corposostenibile" />
            </div>
            <div className="login-head">
              <h3 className="title">Pronto a fare del bene?</h3>
              <p>Inserisci le tue credenziali per accedere al tuo account.</p>
            </div>

            {/* Success Message */}
            {success && (
              <div className="alert alert-success alert--animate mb-3">
                {success}
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className={`alert alert-danger alert--animate mb-3${shake ? ' shake' : ''}`}>
                {error}
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="mb-1 text-dark">Email</label>
                <div className="input-with-icon">
                  <FaEnvelope className="input-icon" />
                  <input
                    type="email"
                    className="form-control form-control-lg has-icon"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="nome@esempio.it"
                    required
                    autoComplete="email"
                    autoFocus
                  />
                </div>
              </div>

              <div className="mb-4">
                <label className="mb-1 text-dark">Password</label>
                <div className="input-with-icon">
                  <FaLock className="input-icon" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="form-control form-control-lg has-icon has-toggle"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="••••••••"
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    className="toggle-password"
                    onClick={() => setShowPassword((v) => !v)}
                    tabIndex={-1}
                    aria-label={showPassword ? 'Nascondi password' : 'Mostra password'}
                  >
                    {showPassword ? <FaEyeSlash /> : <FaEye />}
                  </button>
                </div>
              </div>

              <div className="form-row d-flex justify-content-end mt-4 mb-2">
                <Link to="/auth/forgot-password" className="btn-link text-primary">
                  Password dimenticata?
                </Link>
              </div>

              <div className="text-center mb-4">
                <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                  {loading ? (
                    <>
                      <span className="login-spinner" />
                      Accesso in corso...
                    </>
                  ) : (
                    'Accedi'
                  )}
                </button>
              </div>

              <p className="text-center">
                Non hai un account?{' '}
                <button type="button" className="btn btn-link text-primary fw-500 contact-it-link p-0" onClick={() => setShowSupportModal(true)}>
                  Contatta il team IT
                </button>
              </p>
            </form>
          </div>
        </div>
      </div>

      <Modal show={showSupportModal} onHide={() => setShowSupportModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Supporto Suite Clinica</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>
            Per supporto ed assistenza sulla suite clinica si chiede cortesemente di aprire un ticket a <strong>Emanuele Mastronardi</strong>.
          </p>
          <p className="mb-0">
            Se non hai accesso al sistema di ticketing, invia un email a{' '}
            <a href="mailto:e.mastronardi@corposostenibile.it"><strong>e.mastronardi@corposostenibile.it</strong></a>.
          </p>
        </Modal.Body>
        <Modal.Footer>
          <button className="btn btn-primary" onClick={() => setShowSupportModal(false)}>
            Ho capito
          </button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default Login;

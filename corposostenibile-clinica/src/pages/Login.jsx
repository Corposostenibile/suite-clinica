import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
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
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-account">
      <div className="row h-100">
        {/* Left Side - Decorative Panel */}
        <div className="col-lg-6 align-self-start">
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
          <div className="login-form">
            <div className="login-logo">
              <img src={logo} alt="Corposostenibile" />
            </div>
            <div className="login-head">
              <h3 className="title">Pronto a fare del bene?</h3>
              <p>Inserisci le tue credenziali per accedere al tuo account.</p>
            </div>

            {/* Success Message */}
            {success && (
              <div className="alert alert-success mb-3">
                {success}
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="alert alert-danger mb-3">
                {error}
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="mb-1 text-dark">Email</label>
                <input
                  type="email"
                  className="form-control form-control-lg"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="nome@esempio.it"
                  required
                  autoComplete="email"
                  autoFocus
                />
              </div>

              <div className="mb-4">
                <label className="mb-1 text-dark">Password</label>
                <input
                  type="password"
                  className="form-control form-control-lg"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                />
              </div>

              <div className="form-row d-flex justify-content-between mt-4 mb-2">
                <div className="mb-4">
                  <div className="form-check custom-checkbox mb-3">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      id="rememberMe"
                      name="rememberMe"
                      checked={formData.rememberMe}
                      onChange={handleChange}
                    />
                    <label className="form-check-label" htmlFor="rememberMe">
                      Ricordami
                    </label>
                  </div>
                </div>
                <Link to="/auth/forgot-password" className="btn-link text-primary">
                  Password dimenticata?
                </Link>
              </div>

              <div className="text-center mb-4">
                <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                  {loading ? 'Accesso in corso...' : 'Accedi'}
                </button>
              </div>

              <p className="text-center">
                Non hai un account?{' '}
                <span className="text-primary fw-500">Contatta il team IT</span>
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;

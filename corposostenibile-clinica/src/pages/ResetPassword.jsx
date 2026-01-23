import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import authService from '../services/authService';
import '../styles/auth.css';
import 'remixicon/fonts/remixicon.css';

function ResetPassword() {
  const { token } = useParams();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    password: '',
    password2: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showPassword2, setShowPassword2] = useState(false);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(true);
  const [error, setError] = useState('');
  const [tokenValid, setTokenValid] = useState(false);

  // Password requirements state
  const [requirements, setRequirements] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  });

  // Verify token on mount
  useEffect(() => {
    const verifyToken = async () => {
      try {
        await authService.verifyResetToken(token);
        setTokenValid(true);
      } catch (err) {
        setTokenValid(false);
        setError('Il link di reset non è valido o è scaduto.');
      } finally {
        setValidating(false);
      }
    };

    verifyToken();
  }, [token]);

  // Check password requirements
  useEffect(() => {
    const password = formData.password;
    setRequirements({
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
    });
  }, [formData.password]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    if (error) setError('');
  };

  const getStrengthPercentage = () => {
    const metCount = Object.values(requirements).filter(Boolean).length;
    return (metCount / 5) * 100;
  };

  const getStrengthClass = () => {
    const percentage = getStrengthPercentage();
    if (percentage <= 20) return 'strength-weak';
    if (percentage <= 40) return 'strength-fair';
    if (percentage <= 80) return 'strength-good';
    return 'strength-strong';
  };

  const getStrengthLabel = () => {
    const percentage = getStrengthPercentage();
    if (percentage <= 20) return 'Debole';
    if (percentage <= 40) return 'Sufficiente';
    if (percentage <= 80) return 'Buona';
    return 'Ottima';
  };

  const isPasswordValid = () => {
    return Object.values(requirements).every(Boolean);
  };

  const passwordsMatch = () => {
    return formData.password === formData.password2 && formData.password2.length > 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!isPasswordValid()) {
      setError('La password non soddisfa tutti i requisiti di sicurezza.');
      return;
    }

    if (!passwordsMatch()) {
      setError('Le password non coincidono.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await authService.resetPassword(token, formData.password, formData.password2);
      navigate('/auth/login?message=Password aggiornata con successo! Effettua il login.');
    } catch (err) {
      const message = err.response?.data?.error || 'Errore durante il reset della password.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  // Loading state
  if (validating) {
    return (
      <div className="auth-container">
        <div className="auth-left">
          <div className="decorative-grid"></div>
          <div className="auth-left-content">
            <div style={{ marginBottom: '2rem' }}>
              <span style={{
                display: 'block',
                width: '4rem',
                height: '4rem',
                margin: '0 auto',
                border: '4px solid rgba(255,255,255,0.1)',
                borderTopColor: '#25B36A',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }}></span>
            </div>
            <h2>Verifica in corso...</h2>
            <p>Stiamo controllando il tuo link di reset</p>
          </div>
        </div>
        <div className="auth-right">
          <div className="auth-form-container">
            <div className="auth-logo">
              <img
                src="/static/assets/immagini/Suite.png"
                alt="Corposostenibile Suite"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
              <h1>Suite</h1>
            </div>
            <div className="auth-form">
              <h2>Verifica in corso...</h2>
              <p className="subtitle">Stiamo verificando il link di reset.</p>
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: '2rem' }}>
                <span style={{
                  display: 'block',
                  width: '3rem',
                  height: '3rem',
                  border: '3px solid #e2e8f0',
                  borderTopColor: '#25B36A',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }}></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Invalid token state
  if (!tokenValid) {
    return (
      <div className="auth-container">
        <div className="auth-left">
          <div className="decorative-grid"></div>
          <div className="auth-left-content">
            <div style={{
              width: '100px',
              height: '100px',
              background: 'rgba(239, 68, 68, 0.1)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 2rem'
            }}>
              <i className="ri-error-warning-line" style={{ fontSize: '3rem', color: '#ef4444' }}></i>
            </div>
            <h2>Link non valido</h2>
            <p>Il link potrebbe essere scaduto o già utilizzato</p>
          </div>
        </div>
        <div className="auth-right">
          <div className="auth-form-container">
            <div className="auth-logo">
              <img
                src="/static/assets/immagini/Suite.png"
                alt="Corposostenibile Suite"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
              <h1>Suite</h1>
            </div>
            <div className="auth-form">
              <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                <div style={{
                  width: '80px',
                  height: '80px',
                  background: 'linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%)',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 1.5rem',
                  boxShadow: '0 8px 24px rgba(239, 68, 68, 0.15)'
                }}>
                  <i className="ri-error-warning-line" style={{ fontSize: '2.5rem', color: '#ef4444' }}></i>
                </div>
              </div>
              <h2>Link non valido</h2>
              <p className="subtitle">
                Il link di reset password non è valido o è scaduto. Richiedi un nuovo link per reimpostare la password.
              </p>

              <div className="alert alert-danger">
                <i className="ri-error-warning-fill alert-icon"></i>
                <span>{error}</span>
              </div>

              <Link to="/auth/forgot-password" className="btn btn-primary" style={{ marginBottom: '1rem' }}>
                <i className="ri-mail-send-line"></i>
                Richiedi nuovo link
              </Link>

              <Link to="/auth/login" className="btn btn-outline" style={{ width: '100%' }}>
                <i className="ri-arrow-left-line"></i>
                Torna al login
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      {/* Left Panel */}
      <div className="auth-left">
        <div className="decorative-grid"></div>
        <div className="auth-left-content">
          <img
            src="/static/assets/immagini/auth/login_img.png"
            alt="Reset password illustration"
            className="auth-illustration"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
          <h2>Crea una nuova password</h2>
          <p>Scegli una password sicura e facile da ricordare</p>
        </div>
      </div>

      {/* Right Panel - Form */}
      <div className="auth-right">
        <div className="auth-form-container">
          {/* Back Link */}
          <Link to="/auth/login" className="back-link">
            <i className="ri-arrow-left-line"></i>
            Torna al login
          </Link>

          {/* Logo */}
          <div className="auth-logo">
            <img
              src="/static/assets/immagini/Suite.png"
              alt="Corposostenibile Suite"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
            <h1>Suite</h1>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            <h2>Reimposta password</h2>
            <p className="subtitle">
              Crea una nuova password sicura per il tuo account.
            </p>

            {/* Error Message */}
            {error && (
              <div className="alert alert-danger">
                <i className="ri-error-warning-fill alert-icon"></i>
                <span>{error}</span>
              </div>
            )}

            {/* New Password Field */}
            <div className="form-group">
              <label htmlFor="password">Nuova password</label>
              <div className="input-wrapper">
                <i className="ri-lock-line input-icon"></i>
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Inserisci la nuova password"
                  required
                  autoComplete="new-password"
                  autoFocus
                />
                <i
                  className={`toggle-password ${showPassword ? 'ri-eye-off-line' : 'ri-eye-line'}`}
                  onClick={() => setShowPassword(!showPassword)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Nascondi password' : 'Mostra password'}
                ></i>
              </div>

              {/* Password Strength Indicator */}
              {formData.password && (
                <div className="password-strength">
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Sicurezza password</span>
                    <span style={{ fontSize: '0.75rem', fontWeight: '600', color: getStrengthPercentage() === 100 ? '#25B36A' : '#64748b' }}>
                      {getStrengthLabel()}
                    </span>
                  </div>
                  <div className="strength-bar">
                    <div
                      className={`strength-bar-fill ${getStrengthClass()}`}
                      style={{ width: `${getStrengthPercentage()}%` }}
                    ></div>
                  </div>

                  <div className="password-requirements">
                    <div className={`requirement ${requirements.length ? 'met' : ''}`}>
                      <i className={`requirement-icon ${requirements.length ? 'ri-checkbox-circle-fill' : 'ri-close-circle-line'}`}></i>
                      <span>Almeno 8 caratteri</span>
                    </div>
                    <div className={`requirement ${requirements.uppercase ? 'met' : ''}`}>
                      <i className={`requirement-icon ${requirements.uppercase ? 'ri-checkbox-circle-fill' : 'ri-close-circle-line'}`}></i>
                      <span>Una maiuscola</span>
                    </div>
                    <div className={`requirement ${requirements.lowercase ? 'met' : ''}`}>
                      <i className={`requirement-icon ${requirements.lowercase ? 'ri-checkbox-circle-fill' : 'ri-close-circle-line'}`}></i>
                      <span>Una minuscola</span>
                    </div>
                    <div className={`requirement ${requirements.number ? 'met' : ''}`}>
                      <i className={`requirement-icon ${requirements.number ? 'ri-checkbox-circle-fill' : 'ri-close-circle-line'}`}></i>
                      <span>Un numero</span>
                    </div>
                    <div className={`requirement ${requirements.special ? 'met' : ''}`}>
                      <i className={`requirement-icon ${requirements.special ? 'ri-checkbox-circle-fill' : 'ri-close-circle-line'}`}></i>
                      <span>Un carattere speciale</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password Field */}
            <div className="form-group">
              <label htmlFor="password2">Conferma password</label>
              <div className="input-wrapper">
                <i className="ri-lock-line input-icon"></i>
                <input
                  type={showPassword2 ? 'text' : 'password'}
                  id="password2"
                  name="password2"
                  value={formData.password2}
                  onChange={handleChange}
                  placeholder="Conferma la nuova password"
                  required
                  autoComplete="new-password"
                />
                <i
                  className={`toggle-password ${showPassword2 ? 'ri-eye-off-line' : 'ri-eye-line'}`}
                  onClick={() => setShowPassword2(!showPassword2)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setShowPassword2(!showPassword2)}
                  aria-label={showPassword2 ? 'Nascondi password' : 'Mostra password'}
                ></i>
              </div>

              {/* Password Match Indicator */}
              {formData.password2 && (
                <div className={`requirement ${passwordsMatch() ? 'met' : ''}`} style={{ marginTop: '0.75rem' }}>
                  <i className={`requirement-icon ${passwordsMatch() ? 'ri-checkbox-circle-fill' : 'ri-close-circle-line'}`}></i>
                  <span>{passwordsMatch() ? 'Le password coincidono' : 'Le password non coincidono'}</span>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !isPasswordValid() || !passwordsMatch()}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Aggiornamento in corso...
                </>
              ) : (
                <>
                  <i className="ri-lock-password-line"></i>
                  Aggiorna password
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="auth-footer">
            <p>
              <Link to="/auth/login">Torna al login</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ResetPassword;

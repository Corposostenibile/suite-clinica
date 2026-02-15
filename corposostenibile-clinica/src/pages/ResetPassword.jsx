import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { FaLock, FaEye, FaEyeSlash, FaArrowLeft, FaCheckCircle, FaTimesCircle, FaExclamationTriangle } from 'react-icons/fa';
import authService from '../services/authService';
import '../styles/auth.css';
import logo from '../images/logo_foglia.png';

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
  const [shake, setShake] = useState(false);
  const [tokenValid, setTokenValid] = useState(false);
  const [mounted, setMounted] = useState(false);

  const [requirements, setRequirements] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false,
  });

  useEffect(() => {
    setMounted(true);
  }, []);

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

  useEffect(() => {
    if (shake) {
      const timer = setTimeout(() => setShake(false), 600);
      return () => clearTimeout(timer);
    }
  }, [shake]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (error) setError('');
  };

  const getStrengthPercentage = () => {
    const metCount = Object.values(requirements).filter(Boolean).length;
    return (metCount / 5) * 100;
  };

  const getStrengthClass = () => {
    const pct = getStrengthPercentage();
    if (pct <= 20) return 'strength-weak';
    if (pct <= 40) return 'strength-fair';
    if (pct <= 80) return 'strength-good';
    return 'strength-strong';
  };

  const getStrengthLabel = () => {
    const pct = getStrengthPercentage();
    if (pct <= 20) return 'Debole';
    if (pct <= 40) return 'Sufficiente';
    if (pct <= 80) return 'Buona';
    return 'Ottima';
  };

  const isPasswordValid = () => Object.values(requirements).every(Boolean);
  const passwordsMatch = () => formData.password === formData.password2 && formData.password2.length > 0;

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!isPasswordValid()) {
      setError('La password non soddisfa tutti i requisiti di sicurezza.');
      setShake(true);
      return;
    }

    if (!passwordsMatch()) {
      setError('Le password non coincidono.');
      setShake(true);
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
      setShake(true);
    } finally {
      setLoading(false);
    }
  };

  const RequirementItem = ({ met, label }) => (
    <div className={`requirement ${met ? 'met' : ''}`}>
      {met ? <FaCheckCircle size={12} /> : <FaTimesCircle size={12} />}
      <span>{label}</span>
    </div>
  );

  // Loading state - verifying token
  if (validating) {
    return (
      <div className="login-account">
        <div className="row h-100">
          <div className="col-lg-6 align-self-start login-panel-left">
            <div className="account-info-area">
              <video className="login-video" autoPlay loop muted playsInline>
                <source src="/login.mp4" type="video/mp4" />
              </video>
              <div className="login-content">
                <p className="sub-title">Verifica in corso</p>
                <h1 className="title">Un <span>momento...</span></h1>
                <p className="text">Stiamo verificando il tuo link di reset</p>
              </div>
            </div>
          </div>
          <div className="col-lg-6 col-md-7 col-sm-12 mx-auto align-self-center">
            <div className="login-form login-form--visible">
              <div className="login-logo">
                <img src={logo} alt="Corposostenibile" />
              </div>
              <div className="login-head">
                <h3 className="title">Verifica in corso...</h3>
                <p>Stiamo controllando il tuo link di reset.</p>
              </div>
              <div className="text-center">
                <span className="login-spinner" style={{ width: '40px', height: '40px', borderWidth: '3px' }} />
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
      <div className="login-account">
        <div className="row h-100">
          <div className="col-lg-6 align-self-start login-panel-left">
            <div className="account-info-area">
              <video className="login-video" autoPlay loop muted playsInline>
                <source src="/login.mp4" type="video/mp4" />
              </video>
              <div className="login-content">
                <p className="sub-title">Il link non è più valido</p>
                <h1 className="title">Link <span>scaduto</span></h1>
                <p className="text">Richiedi un nuovo link per reimpostare la password</p>
              </div>
            </div>
          </div>
          <div className="col-lg-6 col-md-7 col-sm-12 mx-auto align-self-center">
            <div className="login-form login-form--visible">
              <div className="login-logo">
                <img src={logo} alt="Corposostenibile" />
              </div>
              <div className="login-head">
                <div className="error-icon-wrapper">
                  <FaExclamationTriangle style={{ fontSize: '2.2rem', color: '#fff' }} />
                </div>
                <h3 className="title">Link non valido</h3>
                <p>Il link di reset password non è valido o è scaduto. Richiedi un nuovo link.</p>
              </div>

              <div className="alert alert-danger alert--animate mb-4">
                {error}
              </div>

              <div className="text-center mb-3">
                <Link to="/auth/forgot-password" className="btn btn-primary btn-block">
                  Richiedi nuovo link
                </Link>
              </div>
              <p className="text-center">
                <Link to="/auth/login" className="back-link">
                  <FaArrowLeft style={{ marginRight: '6px' }} />
                  Torna al login
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Main form
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
              <p className="sub-title">Scegli una password sicura per proteggere il tuo account</p>
              <h1 className="title">Nuova <span>password</span></h1>
              <p className="text">Crea una password sicura e facile da ricordare</p>
            </div>
          </div>
        </div>

        {/* Right Side - Form */}
        <div className="col-lg-6 col-md-7 col-sm-12 mx-auto align-self-center">
          <div className={`login-form${mounted ? ' login-form--visible' : ''}`}>
            <div className="login-logo">
              <img src={logo} alt="Corposostenibile" />
            </div>
            <div className="login-head">
              <h3 className="title">Reimposta password</h3>
              <p>Crea una nuova password sicura per il tuo account.</p>
            </div>

            {error && (
              <div className={`alert alert-danger alert--animate mb-3${shake ? ' shake' : ''}`}>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              {/* New Password */}
              <div className="mb-4">
                <label className="mb-1 text-dark">Nuova password</label>
                <div className="input-with-icon">
                  <FaLock className="input-icon" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="form-control form-control-lg has-icon has-toggle"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="Inserisci la nuova password"
                    required
                    autoComplete="new-password"
                    autoFocus
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

                {/* Password Strength */}
                {formData.password && (
                  <div className="password-strength">
                    <div className="strength-header">
                      <span>Sicurezza password</span>
                      <span className={`strength-label ${getStrengthPercentage() === 100 ? 'strength-label--strong' : ''}`}>
                        {getStrengthLabel()}
                      </span>
                    </div>
                    <div className="strength-bar">
                      <div
                        className={`strength-bar-fill ${getStrengthClass()}`}
                        style={{ width: `${getStrengthPercentage()}%` }}
                      />
                    </div>
                    <div className="password-requirements">
                      <RequirementItem met={requirements.length} label="Almeno 8 caratteri" />
                      <RequirementItem met={requirements.uppercase} label="Una maiuscola" />
                      <RequirementItem met={requirements.lowercase} label="Una minuscola" />
                      <RequirementItem met={requirements.number} label="Un numero" />
                      <RequirementItem met={requirements.special} label="Un carattere speciale" />
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div className="mb-4">
                <label className="mb-1 text-dark">Conferma password</label>
                <div className="input-with-icon">
                  <FaLock className="input-icon" />
                  <input
                    type={showPassword2 ? 'text' : 'password'}
                    className="form-control form-control-lg has-icon has-toggle"
                    name="password2"
                    value={formData.password2}
                    onChange={handleChange}
                    placeholder="Conferma la nuova password"
                    required
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="toggle-password"
                    onClick={() => setShowPassword2((v) => !v)}
                    tabIndex={-1}
                    aria-label={showPassword2 ? 'Nascondi password' : 'Mostra password'}
                  >
                    {showPassword2 ? <FaEyeSlash /> : <FaEye />}
                  </button>
                </div>

                {formData.password2 && (
                  <div className={`requirement match-indicator ${passwordsMatch() ? 'met' : ''}`}>
                    {passwordsMatch() ? <FaCheckCircle size={12} /> : <FaTimesCircle size={12} />}
                    <span>{passwordsMatch() ? 'Le password coincidono' : 'Le password non coincidono'}</span>
                  </div>
                )}
              </div>

              {/* Submit */}
              <div className="text-center mb-4">
                <button
                  type="submit"
                  className="btn btn-primary btn-block"
                  disabled={loading || !isPasswordValid() || !passwordsMatch()}
                >
                  {loading ? (
                    <>
                      <span className="login-spinner" />
                      Aggiornamento in corso...
                    </>
                  ) : (
                    'Aggiorna password'
                  )}
                </button>
              </div>

              <p className="text-center">
                <Link to="/auth/login" className="back-link">
                  <FaArrowLeft style={{ marginRight: '6px' }} />
                  Torna al login
                </Link>
              </p>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ResetPassword;

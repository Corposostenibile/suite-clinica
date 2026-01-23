import { useState } from 'react';
import { Link } from 'react-router-dom';
import authService from '../services/authService';
import '../styles/auth.css';
import 'remixicon/fonts/remixicon.css';

function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await authService.forgotPassword(email);
      setSuccess(true);
    } catch (err) {
      // Show success even on error for privacy (don't reveal if email exists)
      setSuccess(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      {/* Left Panel - Animated Background */}
      <div className="auth-left">
        <div className="decorative-grid"></div>
        <div className="auth-left-content">
          <img
            src="/static/assets/immagini/auth/login_img.png"
            alt="Reset password illustration"
            className="auth-illustration"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
          <h2>Recupera la tua password</h2>
          <p>Ti invieremo un link sicuro per reimpostarla</p>
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

          {success ? (
            // Success State
            <div className="auth-form">
              <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                <div style={{
                  width: '80px',
                  height: '80px',
                  background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 1.5rem',
                  boxShadow: '0 8px 24px rgba(37, 179, 106, 0.15)'
                }}>
                  <i className="ri-mail-check-line" style={{ fontSize: '2.5rem', color: '#25B36A' }}></i>
                </div>
              </div>

              <h2>Email inviata!</h2>
              <p className="subtitle">
                Se l'indirizzo email è associato a un account, riceverai un link per reimpostare la password.
              </p>

              <div className="alert alert-success">
                <i className="ri-mail-check-line alert-icon"></i>
                <span>
                  Controlla la tua casella di posta (anche la cartella spam).
                </span>
              </div>

              <Link to="/auth/login" className="btn btn-primary">
                <i className="ri-arrow-left-line"></i>
                Torna al login
              </Link>
            </div>
          ) : (
            // Form State
            <form className="auth-form" onSubmit={handleSubmit}>
              <h2>Password dimenticata?</h2>
              <p className="subtitle">
                Inserisci il tuo indirizzo email e ti invieremo le istruzioni per reimpostare la password.
              </p>

              {/* Error Message */}
              {error && (
                <div className="alert alert-danger">
                  <i className="ri-error-warning-fill alert-icon"></i>
                  <span>{error}</span>
                </div>
              )}

              {/* Email Field */}
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <div className="input-wrapper">
                  <i className="ri-mail-line input-icon"></i>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (error) setError('');
                    }}
                    placeholder="nome@esempio.com"
                    required
                    autoComplete="email"
                    autoFocus
                  />
                </div>
              </div>

              {/* Submit Button */}
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? (
                  <>
                    <span className="spinner"></span>
                    Invio in corso...
                  </>
                ) : (
                  <>
                    <i className="ri-mail-send-line"></i>
                    Invia link di reset
                  </>
                )}
              </button>
            </form>
          )}

          {/* Footer */}
          <div className="auth-footer">
            <p>
              Ricordi la password?{' '}
              <Link to="/auth/login">Accedi</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ForgotPassword;

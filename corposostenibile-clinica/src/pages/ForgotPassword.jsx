import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FaEnvelope, FaPaperPlane, FaCheckCircle, FaArrowLeft } from 'react-icons/fa';
import authService from '../services/authService';
import '../styles/auth.css';
import logo from '../images/logo_foglia.png';

function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

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
    <div className="login-account">
      <div className="row h-100">
        {/* Left Side - Decorative Panel */}
        <div className="col-lg-6 align-self-start login-panel-left">
          <div className="account-info-area">
            <video className="login-video" autoPlay loop muted playsInline>
              <source src="/login.mp4" type="video/mp4" />
            </video>
            <div className="login-content">
              <p className="sub-title">Recupera l'accesso al tuo account in pochi secondi</p>
              <h1 className="title">Password <span>dimenticata?</span></h1>
              <p className="text">Ti invieremo un link sicuro per reimpostare la tua password</p>
            </div>
          </div>
        </div>

        {/* Right Side - Form */}
        <div className="col-lg-6 col-md-7 col-sm-12 mx-auto align-self-center">
          <div className={`login-form${mounted ? ' login-form--visible' : ''}`}>
            <div className="login-logo">
              <img src={logo} alt="Corposostenibile" />
            </div>

            {success ? (
              <>
                <div className="login-head">
                  <div className="success-icon-wrapper">
                    <FaCheckCircle style={{ fontSize: '2.2rem', color: '#fff' }} />
                  </div>
                  <h3 className="title">Email inviata!</h3>
                  <p>
                    Se l'indirizzo email e' associato a un account, riceverai un link per reimpostare la password.
                  </p>
                </div>

                <div className="alert alert-success alert--animate mb-4">
                  Controlla la tua casella di posta (anche la cartella spam).
                </div>

                <div className="text-center mb-4">
                  <Link to="/auth/login" className="btn btn-primary btn-block">
                    <FaArrowLeft style={{ marginRight: '8px' }} />
                    Torna al login
                  </Link>
                </div>
              </>
            ) : (
              <>
                <div className="login-head">
                  <h3 className="title">Password dimenticata?</h3>
                  <p>Inserisci il tuo indirizzo email e ti invieremo le istruzioni per reimpostare la password.</p>
                </div>

                {error && (
                  <div className="alert alert-danger alert--animate mb-3">
                    {error}
                  </div>
                )}

                <form onSubmit={handleSubmit}>
                  <div className="mb-4">
                    <label className="mb-1 text-dark">Email</label>
                    <div className="input-with-icon">
                      <FaEnvelope className="input-icon" />
                      <input
                        type="email"
                        className="form-control form-control-lg has-icon"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          if (error) setError('');
                        }}
                        placeholder="nome@esempio.it"
                        required
                        autoComplete="email"
                        autoFocus
                      />
                    </div>
                  </div>

                  <div className="text-center mb-4">
                    <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
                      {loading ? (
                        <>
                          <span className="login-spinner" />
                          Invio in corso...
                        </>
                      ) : (
                        <>
                          <FaPaperPlane style={{ marginRight: '8px' }} />
                          Invia link di reset
                        </>
                      )}
                    </button>
                  </div>
                </form>

                <p className="text-center">
                  <Link to="/auth/login" className="back-link">
                    <FaArrowLeft style={{ marginRight: '6px' }} />
                    Torna al login
                  </Link>
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ForgotPassword;

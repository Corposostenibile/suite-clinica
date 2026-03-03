import { useState, useEffect, useCallback, lazy, Suspense, Component } from 'react';
import { useParams } from 'react-router-dom';
import videoCallService from '../../services/videoCallService';
import logoFoglia from '../../images/logo_foglia.png';
import logoFogliaWhite from '../../images/logo-foglia-white.png';
import './VideoCall.css';

// Lazy-load dTelecom components so the pre-join page works even if they fail
const LiveKitRoom = lazy(() =>
  import('@dtelecom/components-react').then((m) => ({ default: m.LiveKitRoom }))
);
const VideoConference = lazy(() =>
  import('@dtelecom/components-react').then((m) => ({ default: m.VideoConference }))
);
const RoomAudioRenderer = lazy(() =>
  import('@dtelecom/components-react').then((m) => ({ default: m.RoomAudioRenderer }))
);

// Inline styles as fallback — visible even if CSS/Bootstrap fail to load
const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #f0fdf4 0%, #e8f5e9 50%, #f5f5f5 100%)',
    padding: '1rem',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  card: {
    textAlign: 'center',
    maxWidth: 440,
    width: '100%',
    padding: '2.5rem',
    background: '#fff',
    borderRadius: '1rem',
    boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
  },
  logo: { marginBottom: '1.5rem' },
  logoImg: { borderRadius: '1rem' },
  title: { fontWeight: 700, marginBottom: '0.5rem', fontSize: '1.5rem' },
  subtitle: { color: '#6c757d', marginBottom: '1.5rem' },
  form: { marginTop: '1.5rem', textAlign: 'left' },
  label: { display: 'block', marginBottom: '0.5rem', fontWeight: 500, fontSize: '0.9rem' },
  input: {
    width: '100%',
    padding: '0.6rem 0.75rem',
    border: '1px solid #ced4da',
    borderRadius: '0.375rem',
    fontSize: '1rem',
    outline: 'none',
    boxSizing: 'border-box',
  },
  btn: {
    width: '100%',
    padding: '0.75rem 1rem',
    background: '#25B36A',
    color: '#fff',
    border: 'none',
    borderRadius: '0.375rem',
    fontSize: '1.1rem',
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: '1rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.5rem',
  },
  btnDisabled: { opacity: 0.65, cursor: 'not-allowed' },
  tips: {
    marginTop: '1.5rem',
    padding: '0.75rem',
    background: '#f8f9fa',
    borderRadius: '0.5rem',
    fontSize: '0.85rem',
    color: '#6c757d',
  },
  spinner: {
    display: 'inline-block',
    width: 32,
    height: 32,
    border: '3px solid #e9ecef',
    borderTop: '3px solid #25B36A',
    borderRadius: '50%',
    animation: 'vc-spin 0.8s linear infinite',
  },
  spinnerSm: {
    display: 'inline-block',
    width: 16,
    height: 16,
    border: '2px solid rgba(255,255,255,0.3)',
    borderTop: '2px solid #fff',
    borderRadius: '50%',
    animation: 'vc-spin 0.8s linear infinite',
  },
  icon: {
    width: 80,
    height: 80,
    borderRadius: '50%',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '1.5rem',
    fontSize: '2.2rem',
    color: '#fff',
  },
  error: { background: '#dc3545', padding: '0.5rem 1rem', borderRadius: '0.5rem', color: '#fff', marginTop: '1rem' },
  room: { display: 'flex', flexDirection: 'column', height: '100vh', background: '#111' },
  topbar: {
    display: 'flex',
    alignItems: 'center',
    padding: '0.5rem 1rem',
    background: '#1a1a2e',
    color: '#fff',
    gap: '1rem',
    flexShrink: 0,
  },
  topbarBrand: { display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700 },
  statusDot: {
    display: 'inline-block',
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#25B36A',
    marginRight: 6,
    animation: 'vc-pulse 2s infinite',
  },
};

// Keyframe animation injected once
const KEYFRAMES = `
@keyframes vc-spin { to { transform: rotate(360deg); } }
@keyframes vc-pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
`;

// Simple error boundary
class VideoCallErrorBoundary extends Component {
  state = { hasError: false, errorMsg: '' };
  static getDerivedStateFromError(error) {
    return { hasError: true, errorMsg: error?.message || 'Errore sconosciuto' };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={styles.container}>
          <div style={styles.card}>
            <div style={{ ...styles.icon, background: '#dc3545' }}>!</div>
            <h2 style={styles.title}>Errore</h2>
            <p style={styles.subtitle}>{this.state.errorMsg}</p>
            <button style={styles.btn} onClick={() => window.location.reload()}>Ricarica pagina</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function VideoCallPublicInner() {
  const { sessionToken } = useParams();

  const [sessionInfo, setSessionInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [state, setState] = useState('prejoin'); // prejoin | connecting | connected | ended | error
  const [error, setError] = useState(null);
  const [token, setToken] = useState(null);
  const [wsUrl, setWsUrl] = useState(null);
  const [dtelecomCss, setDtelecomCss] = useState(false);

  // Load session info
  useEffect(() => {
    videoCallService.getPublicInfo(sessionToken)
      .then((res) => {
        const data = res.data || res;
        setSessionInfo(data);
        if (data.cliente_name) setName(data.cliente_name);
        if (data.status === 'ended' || data.status === 'cancelled') {
          setState('ended');
        }
      })
      .catch((err) => {
        console.error('[VideoCallPublic] getPublicInfo error:', err);
        setError(err.response?.data?.error || 'Sessione non trovata');
        setState('error');
      })
      .finally(() => setLoading(false));
  }, [sessionToken]);

  // Load dtelecom CSS only when entering a call
  useEffect(() => {
    if (state === 'connected' && !dtelecomCss) {
      import('@dtelecom/components-styles').then(() => setDtelecomCss(true)).catch(() => {});
    }
  }, [state, dtelecomCss]);

  const joinCall = useCallback(async () => {
    if (!name.trim()) return;
    setState('connecting');
    setError(null);
    try {
      const res = await videoCallService.publicJoin(sessionToken, name.trim());
      const data = res.data || res;
      setToken(data.token);
      setWsUrl(data.wsUrl);
      setState('connected');
    } catch (err) {
      console.error('[VideoCallPublic] publicJoin error:', err);
      setError(err.response?.data?.error || 'Errore nella connessione');
      setState('error');
    }
  }, [sessionToken, name]);

  const handleDisconnect = useCallback(() => {
    setState('ended');
    setToken(null);
    setWsUrl(null);
  }, []);

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={styles.container}>
        <style>{KEYFRAMES}</style>
        <div style={styles.card}>
          <div style={styles.spinner} />
          <p style={{ marginTop: '1rem', color: '#6c757d' }}>Caricamento...</p>
        </div>
      </div>
    );
  }

  // ── Ended ────────────────────────────────────────────────────────────────────
  if (state === 'ended') {
    return (
      <div style={styles.container}>
        <style>{KEYFRAMES}</style>
        <div style={styles.card}>
          <div style={{ ...styles.icon, background: '#6c757d' }}>
            <i className="ri-video-off-line" style={{ fontSize: '2rem' }} />
          </div>
          <h2 style={styles.title}>Videochiamata terminata</h2>
          <p style={styles.subtitle}>Grazie per aver partecipato alla videochiamata.</p>
        </div>
      </div>
    );
  }

  // ── Error (no session info) ──────────────────────────────────────────────────
  if (state === 'error' && !sessionInfo) {
    return (
      <div style={styles.container}>
        <style>{KEYFRAMES}</style>
        <div style={styles.card}>
          <div style={{ ...styles.icon, background: '#dc3545' }}>
            <i className="ri-error-warning-line" style={{ fontSize: '2rem' }} />
          </div>
          <h2 style={styles.title}>Sessione non disponibile</h2>
          <p style={styles.subtitle}>{error}</p>
        </div>
      </div>
    );
  }

  // ── Active video call (lazy-loaded dTelecom) ─────────────────────────────────
  if (state === 'connected' && token && wsUrl) {
    return (
      <div className="videocall-room videocall-room-public" data-lk-theme="default" style={styles.room}>
        <div className="videocall-topbar">
          <div className="topbar-left">
            <div className="topbar-brand">
              <img src={logoFogliaWhite} alt="Corposostenibile" className="topbar-logo" />
              <span className="topbar-brand-text">CORPOSOSTENIBILE</span>
            </div>
            <span className="topbar-divider" />
            <span className="room-status">
              <span className="status-dot" />
              In videochiamata
            </span>
          </div>
        </div>
        <Suspense fallback={
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
            <style>{KEYFRAMES}</style>
            <div style={styles.spinner} />
            <span style={{ marginLeft: 12 }}>Connessione alla videochiamata...</span>
          </div>
        }>
          <LiveKitRoom
            token={token}
            serverUrl={wsUrl}
            connect={true}
            audio={true}
            video={true}
            onDisconnected={handleDisconnect}
            className="videocall-livekit"
            style={{ flex: 1 }}
          >
            <VideoConference />
            <RoomAudioRenderer />
          </LiveKitRoom>
        </Suspense>
      </div>
    );
  }

  // ── Pre-join screen ──────────────────────────────────────────────────────────
  return (
    <div style={styles.container} className="videocall-public-container">
      <style>{KEYFRAMES}</style>
      <div style={styles.card} className="public-card">
        <div style={styles.logo}>
          <img
            src={logoFoglia}
            alt="Corposostenibile"
            width={80}
            height={80}
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        </div>
        <h2 style={styles.title}>Corposostenibile</h2>

        {sessionInfo?.professionista_name && (
          <div style={{ margin: '1.5rem 0' }}>
            {sessionInfo.professionista_avatar ? (
              <img
                src={sessionInfo.professionista_avatar}
                alt={sessionInfo.professionista_name}
                style={{
                  width: 72, height: 72, borderRadius: '50%', objectFit: 'cover',
                  border: '3px solid #25B36A', marginBottom: '0.75rem',
                }}
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            ) : (
              <div style={{
                width: 72, height: 72, borderRadius: '50%', background: '#25B36A',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff', fontSize: '1.8rem', fontWeight: 700, marginBottom: '0.75rem',
              }}>
                {sessionInfo.professionista_name.charAt(0).toUpperCase()}
              </div>
            )}
            <p style={styles.subtitle}>
              Partecipa all'appuntamento con il tuo professionista: <strong>{sessionInfo.professionista_name}</strong>
            </p>
          </div>
        )}

        {sessionInfo?.cliente_name && (
          <p style={{ color: '#333', fontSize: '1.1rem', margin: '1rem 0' }}>
            Ciao <strong>{sessionInfo.cliente_name}</strong>, ti auguriamo una buona call
          </p>
        )}

        {error && (
          <div style={styles.error}>{error}</div>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); joinCall(); }}
          style={styles.form}
        >
          {/* Show name input only if client name is NOT known */}
          {!sessionInfo?.cliente_name && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={styles.label}>Il tuo nome</label>
              <input
                type="text"
                placeholder="Inserisci il tuo nome"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
                style={styles.input}
              />
            </div>
          )}

          {state === 'connecting' ? (
            <button type="button" disabled style={{ ...styles.btn, ...styles.btnDisabled }}>
              <span style={styles.spinnerSm} />
              Connessione...
            </button>
          ) : (
            <button
              type="submit"
              disabled={!name.trim()}
              style={!name.trim() ? { ...styles.btn, ...styles.btnDisabled } : styles.btn}
            >
              <i className="ri-video-on-line" />
              Unisciti alla videochiamata
            </button>
          )}
        </form>

        <div style={styles.tips}>
          <i className="ri-information-line" style={{ marginRight: 4 }} />
          Assicurati di permettere l'accesso a webcam e microfono quando richiesto dal browser.
        </div>
      </div>
    </div>
  );
}

export default function VideoCallPublic() {
  return (
    <VideoCallErrorBoundary>
      <VideoCallPublicInner />
    </VideoCallErrorBoundary>
  );
}

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import videoCallService from '../../services/videoCallService';
import logoFoglia from '../../images/logo-foglia-white.png';
import './VideoCall.css';

export default function VideoCallReplay() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    videoCallService.getReplayData(sessionId)
      .then((res) => setSession(res.data?.session || res.data))
      .catch((err) => {
        console.error('Error loading replay:', err);
        setError('Impossibile caricare la registrazione');
      })
      .finally(() => setLoading(false));
  }, [sessionId]);

  const formatDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleString('it-IT', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const formatDuration = (secs) => {
    if (!secs) return '—';
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}m ${s}s`;
  };

  if (loading) {
    return (
      <div className="replay-page">
        <div className="replay-loading">
          <div className="sumi-spinner" />
          <p>Caricamento...</p>
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="replay-page">
        <div className="replay-loading">
          <i className="ri-error-warning-line" style={{ fontSize: 48, opacity: 0.4 }} />
          <p>{error || 'Sessione non trovata'}</p>
          <button className="cd-btn cd-btn-primary mt-3" onClick={() => navigate(-1)}>
            Torna indietro
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="replay-page">
      {/* Topbar */}
      <div className="replay-topbar">
        <div className="topbar-left">
          <div className="topbar-brand">
            <img src={logoFoglia} alt="Corposostenibile" className="topbar-logo" />
            <span className="topbar-brand-text">CORPOSOSTENIBILE</span>
          </div>
          <span className="topbar-divider" />
          <span className="replay-topbar-title">
            <i className="ri-play-circle-line me-1" />
            Registrazione call
          </span>
        </div>
        <div className="topbar-right">
          {session.cliente_id && (
            <button
              className="cd-btn cd-btn-outline replay-btn-back"
              onClick={() => navigate(`/clienti-dettaglio/${session.cliente_id}`)}
            >
              <i className="ri-arrow-left-line me-1" />
              Torna al cliente
            </button>
          )}
        </div>
      </div>

      {/* Content: video + sidebar */}
      <div className="replay-content">
        {/* Video area */}
        <div className="replay-video-area">
          {session.recording_url ? (
            <video
              className="replay-video"
              src={session.recording_url}
              controls
              autoPlay={false}
            />
          ) : (
            <div className="replay-no-video">
              <i className="ri-video-off-line" />
              <p>Registrazione non disponibile</p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="replay-sidebar">
          <div className="replay-sidebar-section">
            <h6 className="replay-sidebar-heading">
              <i className="ri-information-line me-1" />
              Dettagli call
            </h6>
            <div className="replay-info-row">
              <span className="replay-info-label">Data</span>
              <span className="replay-info-value">{formatDate(session.scheduled_at || session.created_at)}</span>
            </div>
            <div className="replay-info-row">
              <span className="replay-info-label">Durata</span>
              <span className="replay-info-value">{formatDuration(session.duration_seconds)}</span>
            </div>
            <div className="replay-info-row">
              <span className="replay-info-label">Professionista</span>
              <span className="replay-info-value">{session.professionista_name || '—'}</span>
            </div>
            <div className="replay-info-row">
              <span className="replay-info-label">Cliente</span>
              <span className="replay-info-value">{session.cliente_name || '—'}</span>
            </div>
            {session.notes && (
              <div className="replay-notes">
                <span className="replay-info-label">Note</span>
                <p>{session.notes}</p>
              </div>
            )}
          </div>

          <div className="replay-sidebar-section">
            <h6 className="replay-sidebar-heading">
              <i className="ri-file-text-line me-1" />
              Trascrizione
            </h6>
            <div className="replay-transcription">
              {session.transcription ? (
                <p>{session.transcription}</p>
              ) : (
                <p className="replay-placeholder">Trascrizione non disponibile</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

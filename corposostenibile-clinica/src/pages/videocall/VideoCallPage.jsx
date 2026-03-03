import { useState, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Container, Button, Spinner, Alert } from 'react-bootstrap';
import videoCallService from '../../services/videoCallService';
import './VideoCall.css';

/**
 * Pre-call page (inside DashboardLayout).
 * Creates the session via API, then navigates to the fullscreen room page.
 */
export default function VideoCallPage() {
  const { clienteId } = useParams();
  const [searchParams] = useSearchParams();
  const clienteName = searchParams.get('nome') || 'Cliente';
  const navigate = useNavigate();

  const [state, setState] = useState('idle'); // idle | connecting | error
  const [error, setError] = useState(null);

  const startCall = useCallback(async () => {
    setState('connecting');
    setError(null);
    try {
      const { data } = await videoCallService.createCall(clienteId);
      // Navigate to fullscreen room page, pass data via router state
      navigate(`/video-call-room/${data.session.session_token}`, {
        state: {
          token: data.token,
          wsUrl: data.wsUrl,
          session: data.session,
          clienteName,
        },
      });
    } catch (err) {
      setError(err.response?.data?.error || 'Errore nella creazione della videochiamata');
      setState('error');
    }
  }, [clienteId, clienteName, navigate]);

  const goBack = () => {
    if (clienteId) {
      navigate(`/clienti-dettaglio/${clienteId}`);
    } else {
      navigate(-1);
    }
  };

  return (
    <Container className="videocall-precall">
      <div className="precall-card">
        <div className="precall-icon">
          <i className="ri-video-chat-line" />
        </div>
        <h2>Videochiamata</h2>
        {clienteId && (
          <p className="text-muted">
            Stai per avviare una videochiamata con <strong>{clienteName}</strong>
          </p>
        )}

        {error && (
          <Alert variant="danger" className="mt-3">
            {error}
          </Alert>
        )}

        <div className="precall-actions">
          {state === 'connecting' ? (
            <Button variant="success" size="lg" disabled>
              <Spinner size="sm" className="me-2" />
              Connessione in corso...
            </Button>
          ) : (
            <Button variant="success" size="lg" onClick={startCall}>
              <i className="ri-video-on-line me-2" />
              Avvia Videochiamata
            </Button>
          )}
          <Button variant="outline-secondary" onClick={goBack}>
            Annulla
          </Button>
        </div>

        <div className="precall-tips">
          <small className="text-muted">
            <i className="ri-information-line me-1" />
            Assicurati di avere webcam e microfono attivi.
            Il cliente riceverà un link per unirsi direttamente dal browser.
          </small>
        </div>
      </div>
    </Container>
  );
}

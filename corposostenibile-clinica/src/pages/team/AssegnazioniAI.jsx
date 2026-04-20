import { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Row, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import ghlService from '../../services/ghlService';

function formatDate(value) {
  if (!value) return 'N/D';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'N/D';
  return new Intl.DateTimeFormat('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function AssegnazioniAI() {
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showProcessed, setShowProcessed] = useState(false);

  const loadQueue = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await ghlService.getOpportunityData();
      if (response?.success) {
        setOpportunities(Array.isArray(response.data) ? response.data : []);
      } else {
        setError(response?.message || 'Impossibile caricare la queue GHL.');
      }
    } catch (err) {
      console.error('Errore caricamento opportunity data:', err);
      setError(err?.response?.data?.message || 'Errore durante il caricamento della queue.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const stats = useMemo(() => {
    const processed = opportunities.filter((item) => item.processed).length;
    const pending = opportunities.length - processed;
    return { total: opportunities.length, processed, pending };
  }, [opportunities]);

  const visibleOpportunities = useMemo(() => {
    return opportunities.filter((item) => (showProcessed ? true : !item.processed));
  }, [opportunities, showProcessed]);

  const openOpportunity = (item) => {
    navigate(`/suitemind/${item.id}`, { state: { opportunity: item } });
  };

  return (
    <div className="container-fluid py-4">
      <div className="d-flex flex-column flex-md-row align-items-md-center justify-content-between gap-3 mb-4">
        <div>
          <h2 className="mb-1">Assegnazioni AI</h2>
          <p className="text-muted mb-0">
            Queue GHL per analisi e assegnazione dei Sales.
          </p>
        </div>

        <div className="d-flex gap-2 flex-wrap">
          <Button variant="outline-secondary" onClick={() => setShowProcessed((prev) => !prev)}>
            {showProcessed ? 'Mostra solo da lavorare' : 'Mostra anche processati'}
          </Button>
          <Button variant="primary" onClick={loadQueue} disabled={loading}>
            {loading ? <Spinner size="sm" animation="border" className="me-2" /> : null}
            Ricarica
          </Button>
        </div>
      </div>

      <Row className="g-3 mb-4">
        <Col md={4}>
          <Card className="h-100 shadow-sm">
            <Card.Body>
              <div className="text-muted small">Totale record</div>
              <div className="fs-3 fw-bold">{stats.total}</div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="h-100 shadow-sm">
            <Card.Body>
              <div className="text-muted small">Da lavorare</div>
              <div className="fs-3 fw-bold text-warning">{stats.pending}</div>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="h-100 shadow-sm">
            <Card.Body>
              <div className="text-muted small">Processati</div>
              <div className="fs-3 fw-bold text-success">{stats.processed}</div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {error && (
        <Alert variant="danger" className="mb-4 d-flex align-items-center justify-content-between gap-3 flex-wrap">
          <span>{error}</span>
          <Button variant="outline-danger" size="sm" onClick={loadQueue}>
            Riprova
          </Button>
        </Alert>
      )}

      {loading ? (
        <div className="d-flex justify-content-center align-items-center py-5">
          <Spinner animation="border" role="status" className="me-2" />
          <span>Caricamento queue in corso...</span>
        </div>
      ) : visibleOpportunities.length === 0 ? (
        <Card className="shadow-sm">
          <Card.Body className="text-center py-5">
            <div className="fs-1 mb-3">📭</div>
            <h5 className="mb-2">Nessun record disponibile</h5>
            <p className="text-muted mb-0">
              {showProcessed
                ? 'Non ci sono ancora opportunity salvate da GHL.'
                : 'Non ci sono lead da lavorare in questo momento.'}
            </p>
          </Card.Body>
        </Card>
      ) : (
        <Row className="g-3">
          {visibleOpportunities.map((item) => (
            <Col key={item.id} xs={12} lg={6} xl={4}>
              <Card className="h-100 shadow-sm">
                <Card.Body className="d-flex flex-column gap-3">
                  <div className="d-flex justify-content-between align-items-start gap-3">
                    <div>
                      <h5 className="mb-1">{item.nome || 'N/D'}</h5>
                      <div className="text-muted small">ID record: {item.id}</div>
                    </div>
                    <Badge bg={item.processed ? 'success' : 'warning'}>
                      {item.processed ? 'Processato' : 'Da lavorare'}
                    </Badge>
                  </div>

                  <div className="small">
                    <div><strong>Email:</strong> {item.email || 'N/D'}</div>
                    <div><strong>Telefono:</strong> {item.lead_phone || 'N/D'}</div>
                    <div><strong>Sales:</strong> {item.sales_consultant || item.sales_person?.full_name || 'N/D'}</div>
                    <div><strong>Pacchetto:</strong> {item.pacchetto || 'N/D'}</div>
                    <div><strong>Durata:</strong> {item.durata || 'N/D'}</div>
                    <div><strong>Ricevuto:</strong> {formatDate(item.received_at)}</div>
                  </div>

                  <div className="mt-auto d-flex gap-2 flex-wrap">
                    <Button variant="primary" onClick={() => openOpportunity(item)}>
                      Apri assegnazione
                    </Button>
                    <Button variant="outline-secondary" onClick={() => navigate(`/suitemind/${item.id}`, { state: { opportunity: item } })}>
                      Dettaglio
                    </Button>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
}

export default AssegnazioniAI;

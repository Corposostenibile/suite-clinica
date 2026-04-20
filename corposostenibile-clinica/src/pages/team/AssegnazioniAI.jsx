import { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, InputGroup, Row, Spinner } from 'react-bootstrap';
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

function truncate(text, max = 140) {
  const value = String(text || '').trim();
  if (!value) return 'N/D';
  if (value.length <= max) return value;
  return `${value.slice(0, max).trim()}…`;
}

function AssegnazioniAI() {
  const navigate = useNavigate();
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('pending');
  const [showSalesOnly, setShowSalesOnly] = useState(false);
  const [lastLoadedAt, setLastLoadedAt] = useState(null);
  const [serverTotal, setServerTotal] = useState(0);

  const loadQueue = async (override = {}) => {
    setLoading(true);
    setError('');

    const effectiveStatus = override.statusFilter ?? statusFilter;
    const effectiveSearch = (override.search ?? search).trim();

    try {
      const response = await ghlService.getOpportunityData({
        processed: effectiveStatus,
        q: effectiveSearch,
        limit: 200,
      });

      if (response?.success) {
        const rows = Array.isArray(response.data) ? response.data : [];
        setOpportunities(rows);
        setServerTotal(typeof response.total === 'number' ? response.total : rows.length);
        setLastLoadedAt(new Date().toISOString());
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
    const timeout = setTimeout(() => {
      loadQueue();
    }, 250);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      loadQueue();
    }, 450);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const stats = useMemo(() => {
    const processed = opportunities.filter((item) => item.processed).length;
    const pending = opportunities.length - processed;
    const salesAssigned = opportunities.filter((item) => item.sales_person_id || item.sales_person?.id || item.sales_consultant).length;
    return {
      total: opportunities.length,
      pending,
      processed,
      salesAssigned,
    };
  }, [opportunities]);

  const visibleOpportunities = useMemo(() => {
    if (!showSalesOnly) return opportunities;
    return opportunities.filter((item) => Boolean(item.sales_person_id || item.sales_person?.id || item.sales_consultant));
  }, [opportunities, showSalesOnly]);

  const openOpportunity = (item) => {
    navigate(`/suitemind/${item.id}`, { state: { opportunity: item } });
  };

  const clearFilters = () => {
    setSearch('');
    setStatusFilter('pending');
    setShowSalesOnly(false);
  };

  const emptyCopy = useMemo(() => {
    if (search.trim() && statusFilter !== 'all') {
      return 'Nessun record trovato con questi filtri.';
    }
    if (statusFilter === 'processed') return 'Non ci sono lead processati nel range attuale.';
    return 'Non ci sono lead da lavorare in questo momento.';
  }, [search, statusFilter]);

  return (
    <div className="container-fluid py-4">
      <div className="bg-white border rounded-4 p-4 p-lg-5 shadow-sm mb-4">
        <div className="d-flex flex-column flex-xl-row align-items-xl-center justify-content-between gap-4">
          <div className="flex-grow-1">
            <div className="d-flex align-items-center gap-2 mb-2 flex-wrap">
              <Badge bg="success" className="rounded-pill px-3 py-2">GHL Queue</Badge>
              <Badge bg="light" text="dark" className="rounded-pill px-3 py-2">
                {serverTotal} record server
              </Badge>
            </div>
            <h2 className="mb-2 fw-bold">Assegnazioni AI</h2>
            <p className="text-muted mb-0" style={{ maxWidth: 760 }}>
              Queue GHL per analisi, matching e conferma assegnazioni Sales. Qui puoi filtrare i lead,
              aprire il dettaglio AI e procedere con l'assegnazione.
            </p>
          </div>

          <div className="d-flex gap-2 flex-wrap">
            <Button variant="outline-secondary" onClick={() => loadQueue()} disabled={loading}>
              {loading ? <Spinner size="sm" animation="border" className="me-2" /> : null}
              Ricarica
            </Button>
            <Button variant="outline-danger" onClick={clearFilters} disabled={loading}>
              Reset filtri
            </Button>
          </div>
        </div>

        <Row className="g-3 mt-4">
          <Col md={3} sm={6}>
            <Card className="h-100 border-0 bg-light">
              <Card.Body>
                <div className="text-muted small">Da lavorare</div>
                <div className="fs-3 fw-bold text-warning">{stats.pending}</div>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3} sm={6}>
            <Card className="h-100 border-0 bg-light">
              <Card.Body>
                <div className="text-muted small">Processati</div>
                <div className="fs-3 fw-bold text-success">{stats.processed}</div>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3} sm={6}>
            <Card className="h-100 border-0 bg-light">
              <Card.Body>
                <div className="text-muted small">Con Sales assegnato</div>
                <div className="fs-3 fw-bold text-primary">{stats.salesAssigned}</div>
              </Card.Body>
            </Card>
          </Col>
          <Col md={3} sm={6}>
            <Card className="h-100 border-0 bg-light">
              <Card.Body>
                <div className="text-muted small">Ultimo refresh</div>
                <div className="fw-semibold">{formatDate(lastLoadedAt)}</div>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        <Row className="g-3 mt-4 align-items-end">
          <Col lg={5}>
            <Form.Label className="fw-semibold">Cerca</Form.Label>
            <InputGroup>
              <InputGroup.Text>
                <i className="ri-search-line"></i>
              </InputGroup.Text>
              <Form.Control
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Nome, email, telefono, Sales o pacchetto"
              />
            </InputGroup>
          </Col>
          <Col lg={3} md={6}>
            <Form.Label className="fw-semibold">Stato record</Form.Label>
            <Form.Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="pending">Da lavorare</option>
              <option value="processed">Processati</option>
              <option value="all">Tutti</option>
            </Form.Select>
          </Col>
          <Col lg={4} md={6}>
            <div className="d-flex gap-2 flex-wrap justify-content-lg-end">
              <Button
                variant={showSalesOnly ? 'success' : 'outline-success'}
                onClick={() => setShowSalesOnly((prev) => !prev)}
              >
                {showSalesOnly ? 'Mostra tutti i lead' : 'Solo lead con Sales'}
              </Button>
              <Button variant="primary" onClick={() => loadQueue()} disabled={loading}>
                Applica filtri
              </Button>
            </div>
          </Col>
        </Row>
      </div>

      {error && (
        <Alert variant="danger" className="mb-4 d-flex align-items-center justify-content-between gap-3 flex-wrap">
          <span>{error}</span>
          <Button variant="outline-danger" size="sm" onClick={() => loadQueue()}>
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
        <Card className="shadow-sm border-0 rounded-4">
          <Card.Body className="text-center py-5">
            <div className="fs-1 mb-3">📭</div>
            <h5 className="mb-2">Nessun record disponibile</h5>
            <p className="text-muted mb-0">{emptyCopy}</p>
          </Card.Body>
        </Card>
      ) : (
        <Row className="g-3">
          {visibleOpportunities.map((item) => (
            <Col key={item.id} xs={12} xl={6}>
              <Card className="h-100 shadow-sm border-0 rounded-4 overflow-hidden">
                <Card.Body className="p-4 d-flex flex-column gap-3">
                  <div className="d-flex justify-content-between align-items-start gap-3">
                    <div className="flex-grow-1">
                      <div className="d-flex align-items-center gap-2 flex-wrap mb-2">
                        <h5 className="mb-0 fw-bold">{item.nome || 'N/D'}</h5>
                        <Badge bg={item.processed ? 'success' : 'warning'} className="rounded-pill">
                          {item.processed ? 'Processato' : 'Da lavorare'}
                        </Badge>
                        {item.sales_person?.full_name || item.sales_consultant ? (
                          <Badge bg="light" text="dark" className="rounded-pill border">
                            <i className="ri-user-star-line me-1"></i>
                            {item.sales_person?.full_name || item.sales_consultant}
                          </Badge>
                        ) : null}
                      </div>
                      <div className="text-muted small">ID record: {item.id}</div>
                    </div>
                    <Button variant="outline-primary" size="sm" onClick={() => openOpportunity(item)}>
                      Apri
                    </Button>
                  </div>

                  <div className="p-3 bg-light rounded-3 small">
                    <Row className="g-2">
                      <Col md={6}><strong>Email:</strong> {item.email || 'N/D'}</Col>
                      <Col md={6}><strong>Telefono:</strong> {item.lead_phone || 'N/D'}</Col>
                      <Col md={6}><strong>Sales:</strong> {item.sales_person?.full_name || item.sales_consultant || 'N/D'}</Col>
                      <Col md={6}><strong>Pacchetto:</strong> {item.pacchetto || 'N/D'}</Col>
                      <Col md={6}><strong>Durata:</strong> {item.durata || 'N/D'}</Col>
                      <Col md={6}><strong>HM:</strong> {item.health_manager_email || 'N/D'}</Col>
                      <Col md={6}><strong>Ricevuto:</strong> {formatDate(item.received_at)}</Col>
                    </Row>
                  </div>

                  <div>
                    <div className="text-muted small mb-1">Storia</div>
                    <div className="small">{truncate(item.storia, 160)}</div>
                  </div>

                  <div className="d-flex gap-2 flex-wrap mt-auto">
                    <Button variant="success" onClick={() => openOpportunity(item)}>
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

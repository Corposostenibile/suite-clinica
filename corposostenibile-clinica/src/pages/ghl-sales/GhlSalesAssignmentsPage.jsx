import { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, InputGroup, Row, Spinner } from 'react-bootstrap';
import { useLocation } from 'react-router-dom';
import salesGhlAssignmentsService from '../../services/salesGhlAssignmentsService';

const STATUS_OPTIONS = [
  { value: 'all', label: 'Tutti' },
  { value: 'NEW', label: 'Nuovi' },
  { value: 'PENDING_ASSIGNMENT', label: 'In attesa assegnazione' },
  { value: 'ASSIGNED', label: 'Assegnati' },
  { value: 'CONVERTED', label: 'Convertiti' },
  { value: 'LOST', label: 'Persi' },
];

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

function previewValue(value, max = 140) {
  if (value === null || value === undefined || value === '') return 'N/D';
  const normalized = typeof value === 'string' ? value.trim() : JSON.stringify(value, null, 2);
  if (!normalized) return 'N/D';
  if (normalized.length <= max) return normalized;
  return `${normalized.slice(0, max).trim()}…`;
}

function badgeVariant(status) {
  switch ((status || '').toUpperCase()) {
    case 'NEW':
      return 'warning';
    case 'PENDING_ASSIGNMENT':
      return 'info';
    case 'ASSIGNED':
      return 'success';
    case 'CONVERTED':
      return 'primary';
    case 'LOST':
      return 'danger';
    default:
      return 'secondary';
  }
}

function GhlSalesAssignmentsPage() {
  const location = useLocation();
  const [bootstrapping, setBootstrapping] = useState(true);
  const [queueLoading, setQueueLoading] = useState(false);
  const [error, setError] = useState('');
  const [assignments, setAssignments] = useState([]);
  const [serverTotal, setServerTotal] = useState(0);
  const [lastLoadedAt, setLastLoadedAt] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [salesUser, setSalesUser] = useState(salesGhlAssignmentsService.getCachedUser());
  const [emailInput, setEmailInput] = useState('');

  const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const launchEmail = queryParams.get('user_email') || queryParams.get('email') || queryParams.get('sales_user_email') || '';
  const launchName = queryParams.get('user_name') || queryParams.get('name') || '';

  const clearUrlParams = () => {
    if (!window?.history?.replaceState) return;
    window.history.replaceState({}, '', `${window.location.pathname}${window.location.hash}`);
  };

  const authenticate = async ({ user_email, user_name }) => {
    const response = await salesGhlAssignmentsService.exchangeSession({
      user_email,
      user_name,
    });

    if (response?.sales_user) {
      setSalesUser(response.sales_user);
      setEmailInput(response.sales_user.email || user_email || '');
    }

    clearUrlParams();
    return response;
  };

  const bootstrap = async () => {
    setBootstrapping(true);
    setError('');

    try {
      const cachedToken = salesGhlAssignmentsService.getToken();
      if (cachedToken) {
        const verified = await salesGhlAssignmentsService.verifySession();
        if (verified) {
          setSalesUser(salesGhlAssignmentsService.getCachedUser());
          return;
        }
      }

      if (launchEmail) {
        await authenticate({ user_email: launchEmail, user_name: launchName || undefined });
        return;
      }

      setError('Nessuna sessione sales trovata. Usa il link GHL oppure inserisci la tua email sales.');
    } catch (err) {
      const message = err?.response?.data?.description
        || err?.response?.data?.error
        || err?.response?.data?.message
        || err?.message
        || 'Impossibile avviare la sessione sales.';
      setError(message);
      salesGhlAssignmentsService.clearSession();
    } finally {
      setBootstrapping(false);
    }
  };

  useEffect(() => {
    bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadQueue = async (override = {}) => {
    setQueueLoading(true);
    setError('');

    const effectiveStatus = override.statusFilter ?? statusFilter;
    const effectiveSearch = (override.search ?? search).trim();

    try {
      const response = await salesGhlAssignmentsService.getAssignments({
        status: effectiveStatus,
        q: effectiveSearch || undefined,
        limit: 200,
      });

      const rows = Array.isArray(response?.assignments) ? response.assignments : [];
      setAssignments(rows);
      setServerTotal(typeof response?.total === 'number' ? response.total : rows.length);
      setLastLoadedAt(new Date().toISOString());
    } catch (err) {
      const message = err?.response?.data?.description
        || err?.response?.data?.error
        || err?.response?.data?.message
        || 'Errore durante il caricamento della queue Sales.';
      setError(message);
    } finally {
      setQueueLoading(false);
    }
  };

  useEffect(() => {
    if (bootstrapping || !salesGhlAssignmentsService.getToken()) return;
    const timeout = setTimeout(() => {
      loadQueue();
    }, 250);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bootstrapping, statusFilter, search]);

  const stats = useMemo(() => {
    const assigned = assignments.filter((item) => item.sales_user_id || item.sales_user?.id).length;
    const converted = assignments.filter((item) => (item.status || '').toUpperCase() === 'CONVERTED').length;
    const pendingAssignment = assignments.filter((item) => (item.status || '').toUpperCase() === 'PENDING_ASSIGNMENT').length;
    return {
      total: assignments.length,
      assigned,
      converted,
      pendingAssignment,
    };
  }, [assignments]);

  const clearFilters = () => {
    setSearch('');
    setStatusFilter('all');
  };

  const logout = () => {
    salesGhlAssignmentsService.clearSession();
    setSalesUser(null);
    setAssignments([]);
    setServerTotal(0);
    setLastLoadedAt(null);
    setError('Sessione sales rimossa.');
  };

  const handleManualLogin = async () => {
    if (!emailInput.trim()) {
      setError("Inserisci un'email sales valida.");
      return;
    }

    try {
      setBootstrapping(true);
      setError('');
      await authenticate({ user_email: emailInput.trim() });
      setSalesUser(salesGhlAssignmentsService.getCachedUser());
    } catch (err) {
      const message = err?.response?.data?.description
        || err?.response?.data?.error
        || err?.response?.data?.message
        || 'Impossibile autenticare il sales.';
      setError(message);
      salesGhlAssignmentsService.clearSession();
    } finally {
      setBootstrapping(false);
    }
  };

  const isAuthenticated = Boolean(salesGhlAssignmentsService.getToken());

  if (bootstrapping && !isAuthenticated) {
    return (
      <div className="container-fluid py-5 text-center">
        <Spinner animation="border" className="mb-3" />
        <div>Avvio sessione sales in corso...</div>
      </div>
    );
  }

  return (
    <div className="container-fluid py-4">
      <div className="bg-white border rounded-4 p-4 p-lg-5 shadow-sm mb-4">
        <div className="d-flex flex-column flex-xl-row align-items-xl-center justify-content-between gap-4">
          <div className="flex-grow-1">
            <div className="d-flex align-items-center gap-2 mb-2 flex-wrap">
              <Badge bg="success" className="rounded-pill px-3 py-2">Sales SSO</Badge>
              <Badge bg="light" text="dark" className="rounded-pill px-3 py-2">
                {serverTotal} record server
              </Badge>
              {salesUser ? (
                <Badge bg="dark" className="rounded-pill px-3 py-2">
                  {salesUser.name || salesUser.email || `Sales #${salesUser.sales_user_id}`}
                </Badge>
              ) : null}
            </div>
            <h2 className="mb-2 fw-bold">Assegnazioni Sales</h2>
            <p className="text-muted mb-0" style={{ maxWidth: 760 }}>
              Questa è la queue Sales GHL. Il link GHL apre questa pagina, fa il login automatico via email
              e poi carica le lead da assegnare.
            </p>
          </div>

          <div className="d-flex gap-2 flex-wrap">
            <Button variant="outline-secondary" onClick={() => loadQueue()} disabled={!isAuthenticated || queueLoading}>
              {queueLoading ? <Spinner size="sm" animation="border" className="me-2" /> : null}
              Ricarica
            </Button>
            <Button variant="outline-danger" onClick={clearFilters} disabled={!isAuthenticated || queueLoading}>
              Reset filtri
            </Button>
            <Button variant="outline-dark" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>

        {!isAuthenticated ? (
          <Card className="mt-4 border-warning-subtle bg-warning-subtle">
            <Card.Body>
              <div className="fw-semibold mb-2">Autenticazione sales richiesta</div>
              <div className="text-muted mb-3">
                Se sei arrivato da GHL, la pagina prova ad autenticarti automaticamente usando l'email nel link.
                In alternativa, inserisci la tua email sales e premi &quot;Entra&quot;.
              </div>
              <Row className="g-2 align-items-end">
                <Col md={8} lg={6}>
                  <Form.Label className="fw-semibold">Email sales</Form.Label>
                  <Form.Control
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    placeholder="nome.cognome@corposostenibile.com"
                  />
                </Col>
                <Col md={4} lg={3}>
                  <Button className="w-100" onClick={handleManualLogin} disabled={bootstrapping}>
                    Entra
                  </Button>
                </Col>
              </Row>
            </Card.Body>
          </Card>
        ) : (
          <Row className="g-3 mt-4">
            <Col md={3} sm={6}>
              <Card className="h-100 border-0 bg-light">
                <Card.Body>
                  <div className="text-muted small">Da lavorare</div>
                  <div className="fs-3 fw-bold text-warning">{stats.total - stats.converted}</div>
                </Card.Body>
              </Card>
            </Col>
            <Col md={3} sm={6}>
              <Card className="h-100 border-0 bg-light">
                <Card.Body>
                  <div className="text-muted small">In attesa assegnazione</div>
                  <div className="fs-3 fw-bold text-info">{stats.pendingAssignment}</div>
                </Card.Body>
              </Card>
            </Col>
            <Col md={3} sm={6}>
              <Card className="h-100 border-0 bg-light">
                <Card.Body>
                  <div className="text-muted small">Assegnati</div>
                  <div className="fs-3 fw-bold text-primary">{stats.assigned}</div>
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
        )}

        {isAuthenticated ? (
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
                  placeholder="Nome, email, telefono o codice"
                />
              </InputGroup>
            </Col>
            <Col lg={3} md={6}>
              <Form.Label className="fw-semibold">Stato lead</Form.Label>
              <Form.Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                {STATUS_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </Form.Select>
            </Col>
            <Col lg={4} md={6}>
              <div className="d-flex gap-2 flex-wrap justify-content-lg-end">
                <Button variant="primary" onClick={() => loadQueue()} disabled={queueLoading}>
                  Applica filtri
                </Button>
              </div>
            </Col>
          </Row>
        ) : null}
      </div>

      {error ? (
        <Alert variant={isAuthenticated ? 'danger' : 'warning'} className="mb-4">
          {error}
        </Alert>
      ) : null}

      {isAuthenticated && queueLoading ? (
        <div className="d-flex justify-content-center align-items-center py-5">
          <Spinner animation="border" role="status" className="me-2" />
          <span>Caricamento queue Sales in corso...</span>
        </div>
      ) : null}

      {isAuthenticated && !queueLoading && assignments.length === 0 ? (
        <Card className="shadow-sm border-0 rounded-4">
          <Card.Body className="text-center py-5">
            <div className="fs-1 mb-3">📭</div>
            <h5 className="mb-2">Nessun lead trovato</h5>
            <p className="text-muted mb-0">Prova a cambiare i filtri o a ricaricare la queue.</p>
          </Card.Body>
        </Card>
      ) : null}

      {isAuthenticated && assignments.length > 0 ? (
        <Row className="g-3">
          {assignments.map((item) => (
            <Col key={item.id} xs={12} xl={6}>
              <Card className="h-100 shadow-sm border-0 rounded-4 overflow-hidden">
                <Card.Body className="p-4 d-flex flex-column gap-3">
                  <div className="d-flex justify-content-between align-items-start gap-3">
                    <div className="flex-grow-1">
                      <div className="d-flex align-items-center gap-2 flex-wrap mb-2">
                        <h5 className="mb-0 fw-bold">{item.full_name || 'N/D'}</h5>
                        <Badge bg={badgeVariant(item.status)} className="rounded-pill">
                          {item.status || 'N/D'}
                        </Badge>
                        {item.sales_user?.full_name || item.sales_user_id ? (
                          <Badge bg="light" text="dark" className="rounded-pill border">
                            <i className="ri-user-star-line me-1"></i>
                            {item.sales_user?.full_name || `Sales #${item.sales_user_id}`}
                          </Badge>
                        ) : null}
                      </div>
                      <div className="text-muted small">Codice: {item.unique_code || 'N/D'}</div>
                    </div>
                  </div>

                  <div className="p-3 bg-light rounded-3 small">
                    <Row className="g-2">
                      <Col md={6}><strong>Email:</strong> {item.email || 'N/D'}</Col>
                      <Col md={6}><strong>Telefono:</strong> {item.phone || 'N/D'}</Col>
                      <Col md={6}><strong>Sales:</strong> {item.sales_user?.full_name || 'N/D'}</Col>
                      <Col md={6}><strong>HM:</strong> {item.health_manager_id || 'N/D'}</Col>
                      <Col md={6}><strong>Origine:</strong> {item.origin || 'N/D'}</Col>
                      <Col md={6}><strong>Pacchetto:</strong> {item.custom_package_name || 'N/D'}</Col>
                      <Col md={6}><strong>Creato:</strong> {formatDate(item.created_at)}</Col>
                      <Col md={6}><strong>Aggiornato:</strong> {formatDate(item.updated_at)}</Col>
                    </Row>
                  </div>

                  <div>
                    <div className="text-muted small mb-1">Storia cliente</div>
                    <div className="small">{previewValue(item.client_story, 180)}</div>
                  </div>

                  <div className="mt-auto">
                    <div className="text-muted small mb-1">Dettaglio assegnazione</div>
                    <div className="small text-break">{previewValue(item.ai_analysis_snapshot || item.ai_analysis, 220)}</div>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          ))}
        </Row>
      ) : null}
    </div>
  );
}

export default GhlSalesAssignmentsPage;

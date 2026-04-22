import { useCallback, useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, Col, Form, InputGroup, Modal, Row, Spinner } from 'react-bootstrap';
import salesGhlAssignmentsService from '../../services/salesGhlAssignmentsService';
import './GhlEmbedAssegnazioni.css';

const STATUS_LABELS = {
  NEW: 'Nuovo',
  CONTACTED: 'Contattato',
  QUALIFIED: 'Qualificato',
  PROPOSAL_SENT: 'Proposta inviata',
  NEGOTIATING: 'In negoziazione',
  PENDING_ASSIGNMENT: 'In attesa assegnazione',
  ASSIGNED: 'Assegnato',
  CONVERTED: 'Convertito',
  LOST: 'Perso',
};

const STATUS_FILTERS = [
  { value: 'all', label: 'Tutti' },
  { value: 'NEW', label: 'Nuovi' },
  { value: 'PENDING_ASSIGNMENT', label: 'In attesa' },
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
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function preview(value, max = 150) {
  if (value === null || value === undefined || value === '') return 'N/D';
  const text = typeof value === 'string' ? value.trim() : JSON.stringify(value, null, 2);
  if (!text) return 'N/D';
  return text.length > max ? `${text.slice(0, max).trim()}…` : text;
}

function badgeVariant(status) {
  switch ((status || '').toUpperCase()) {
    case 'NEW': return 'warning';
    case 'PENDING_ASSIGNMENT': return 'info';
    case 'ASSIGNED': return 'success';
    case 'CONVERTED': return 'primary';
    case 'LOST': return 'danger';
    default: return 'secondary';
  }
}

function GhlEmbedAssegnazioniPage() {
  const [bootstrapState, setBootstrapState] = useState('loading'); // loading|ready|error
  const [bootstrapError, setBootstrapError] = useState('');
  const [user, setUser] = useState(salesGhlAssignmentsService.getCachedUser());

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [salesOnly, setSalesOnly] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [lastLoadedAt, setLastLoadedAt] = useState(null);
  const [serverTotal, setServerTotal] = useState(0);

  const bootstrap = useCallback(async () => {
    setBootstrapState('loading');
    setBootstrapError('');

    try {
      const existingToken = salesGhlAssignmentsService.getToken();
      if (existingToken) {
        const me = await salesGhlAssignmentsService.verifySession();
        if (me) {
          setUser(salesGhlAssignmentsService.getCachedUser() || me);
          setBootstrapState('ready');
          return;
        }
      }

      const params = new URLSearchParams(window.location.search);
      const userEmail = params.get('user_email') || params.get('email') || params.get('sales_user_email') || '';
      if (!userEmail) {
        setBootstrapError('Parametri GHL mancanti. Apri la pagina dal menu sales oppure aggiungi user_email nel link.');
        setBootstrapState('error');
        return;
      }

      const data = await salesGhlAssignmentsService.exchangeSession({
        user_email: userEmail,
        user_name: params.get('user_name') || params.get('name') || '',
      });

      setUser(data?.sales_user || salesGhlAssignmentsService.getCachedUser());
      window.history.replaceState({}, '', window.location.pathname);
      setBootstrapState('ready');
    } catch (err) {
      setBootstrapError(
        err?.response?.data?.description
        || err?.response?.data?.error
        || err?.message
        || 'Impossibile avviare la sessione Sales.'
      );
      salesGhlAssignmentsService.clearSession();
      setBootstrapState('error');
    }
  }, []);

  const loadQueue = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setRefreshing(silent);
    setError('');

    try {
      const response = await salesGhlAssignmentsService.getAssignments({
        status: statusFilter,
        q: search.trim() || undefined,
        limit: 200,
      });

      const rows = Array.isArray(response?.assignments) ? response.assignments : [];
      setItems(rows);
      setServerTotal(typeof response?.total === 'number' ? response.total : rows.length);
      setLastLoadedAt(new Date().toISOString());
    } catch (err) {
      setError(
        err?.response?.data?.description
        || err?.response?.data?.error
        || err?.message
        || 'Errore nel caricamento della queue Sales.'
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [search, statusFilter]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    if (bootstrapState !== 'ready') return undefined;
    const timeout = setTimeout(() => {
      loadQueue(true);
    }, 250);
    return () => clearTimeout(timeout);
  }, [bootstrapState, loadQueue]);

  const filteredItems = useMemo(() => {
    let rows = items;
    if (salesOnly) {
      rows = rows.filter((item) => Boolean(item.sales_user_id || item.sales_user?.id));
    }
    return rows;
  }, [items, salesOnly]);

  const stats = useMemo(() => {
    const total = items.length;
    const assigned = items.filter((item) => item.sales_user_id || item.sales_user?.id).length;
    const pending = items.filter((item) => (item.status || '').toUpperCase() === 'PENDING_ASSIGNMENT' || (item.status || '').toUpperCase() === 'NEW').length;
    const converted = items.filter((item) => (item.status || '').toUpperCase() === 'CONVERTED').length;
    return { total, assigned, pending, converted };
  }, [items]);

  const openItem = (item) => {
    setSelectedItem(item);
    setShowModal(true);
  };

  const clearFilters = () => {
    setSearch('');
    setStatusFilter('all');
    setSalesOnly(false);
  };

  const logout = () => {
    salesGhlAssignmentsService.clearSession();
    setUser(null);
    setItems([]);
    setSelectedItem(null);
    setShowModal(false);
    setBootstrapState('loading');
    bootstrap();
  };

  if (bootstrapState === 'loading') {
    return (
      <div className="ghle-old-page">
        <div className="ghle-old-shell">
          <div className="ghle-old-state">
            <Spinner animation="border" role="status" className="me-2" />
            Avvio sessione sales in corso…
          </div>
        </div>
      </div>
    );
  }

  if (bootstrapState === 'error') {
    return (
      <div className="ghle-old-page">
        <div className="ghle-old-shell">
          <div className="ghle-old-state ghle-old-state-error">
            <div className="ghle-old-state-icon"><i className="ri-shield-keyhole-line"></i></div>
            <h3>Accesso non autorizzato</h3>
            <p>{bootstrapError}</p>
            <div className="d-flex gap-2 flex-wrap justify-content-center">
              <Button variant="primary" onClick={bootstrap}>Riprova</Button>
              <Button variant="outline-secondary" onClick={logout}>Pulisci sessione</Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ghle-old-page">
      <div className="ghle-old-shell">
        <div className="ghle-old-hero">
          <div className="ghle-old-hero-left">
            <div className="ghle-old-hero-icon">
              <i className="ri-cpu-line"></i>
            </div>
            <div>
              <div className="ghle-old-kicker">Sales SSO</div>
              <h1 className="ghle-old-title">Assegnazioni</h1>
              <p className="ghle-old-copy">
                Vista sales in stile old suite: lead GHL, filtri rapidi, card dettagliate e accesso diretto alla coda.
              </p>
            </div>
          </div>
          <div className="ghle-old-hero-meta">
            <span className="ghle-old-pill">{serverTotal} record server</span>
            <span className="ghle-old-pill ghle-old-pill-dark">{user?.name || user?.email || `Sales #${user?.sales_user_id || ''}`}</span>
          </div>
        </div>

        <div className="ghle-old-stats">
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">Totale</div>
            <div className="ghle-old-stat-value">{stats.total}</div>
          </div>
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">Da lavorare</div>
            <div className="ghle-old-stat-value text-warning">{stats.pending}</div>
          </div>
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">Assegnati</div>
            <div className="ghle-old-stat-value text-success">{stats.assigned}</div>
          </div>
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">Convertiti</div>
            <div className="ghle-old-stat-value text-primary">{stats.converted}</div>
          </div>
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">Ultimo refresh</div>
            <div className="ghle-old-stat-value ghle-old-stat-sm">{formatDate(lastLoadedAt)}</div>
          </div>
        </div>

        <div className="ghle-old-toolbar">
          <div className="ghle-old-filters">
            {STATUS_FILTERS.map((filter) => (
              <button
                key={filter.value}
                type="button"
                className={`ghle-old-chip ${statusFilter === filter.value ? 'active' : ''}`}
                onClick={() => setStatusFilter(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>

          <div className="ghle-old-controls">
            <InputGroup className="ghle-old-search">
              <InputGroup.Text><i className="ri-search-line"></i></InputGroup.Text>
              <Form.Control
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Nome, email, telefono o codice"
              />
            </InputGroup>

            <Button
              variant={salesOnly ? 'success' : 'outline-success'}
              className="ghle-old-action"
              onClick={() => setSalesOnly((prev) => !prev)}
            >
              {salesOnly ? 'Solo i miei lead' : 'Tutti i lead'}
            </Button>
            <Button variant="outline-secondary" className="ghle-old-action" onClick={clearFilters}>
              Reset
            </Button>
            <Button variant="outline-primary" className="ghle-old-action" onClick={() => loadQueue(false)} disabled={refreshing}>
              {refreshing ? <Spinner size="sm" animation="border" className="me-2" /> : null}
              Ricarica
            </Button>
            <Button variant="outline-dark" className="ghle-old-action" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>

        {error ? (
          <div className="ghle-old-alert">
            <i className="ri-error-warning-line"></i>
            <span>{error}</span>
            <Button variant="outline-light" size="sm" onClick={() => loadQueue(false)}>Riprova</Button>
          </div>
        ) : null}

        {loading ? (
          <div className="ghle-old-loading">
            <Spinner animation="border" role="status" className="me-2" />
            Caricamento queue in corso…
          </div>
        ) : null}

        {!loading && filteredItems.length === 0 ? (
          <Card className="ghle-old-empty shadow-sm border-0 rounded-4">
            <Card.Body className="text-center py-5">
              <div className="fs-1 mb-3">📭</div>
              <h5 className="mb-2">Nessun lead disponibile</h5>
              <p className="text-muted mb-0">Prova a cambiare filtri o ricaricare la coda.</p>
            </Card.Body>
          </Card>
        ) : null}

        {!loading && filteredItems.length > 0 ? (
          <Row className="g-3">
            {filteredItems.map((item) => (
              <Col key={item.id} xs={12} xl={6}>
                <Card className="ghle-old-card shadow-sm border-0 rounded-4 overflow-hidden h-100">
                  <Card.Body className="p-4 d-flex flex-column gap-3">
                    <div className="d-flex justify-content-between align-items-start gap-3">
                      <div className="flex-grow-1">
                        <div className="d-flex align-items-center gap-2 flex-wrap mb-2">
                          <h5 className="mb-0 fw-bold">{item.full_name || 'N/D'}</h5>
                          <Badge bg={badgeVariant(item.status)} className="rounded-pill">{STATUS_LABELS[item.status] || item.status || 'N/D'}</Badge>
                          {item.sales_user?.full_name || item.sales_user_id ? (
                            <Badge bg="light" text="dark" className="rounded-pill border">
                              <i className="ri-user-star-line me-1"></i>
                              {item.sales_user?.full_name || `Sales #${item.sales_user_id}`}
                            </Badge>
                          ) : null}
                        </div>
                        <div className="text-muted small">Codice: {item.unique_code || 'N/D'}</div>
                      </div>
                      <Button variant="outline-primary" size="sm" onClick={() => openItem(item)}>
                        Apri
                      </Button>
                    </div>

                    <div className="ghle-old-meta-grid">
                      <div><strong>Email:</strong> {item.email || 'N/D'}</div>
                      <div><strong>Telefono:</strong> {item.phone || 'N/D'}</div>
                      <div><strong>Sales:</strong> {item.sales_user?.full_name || 'N/D'}</div>
                      <div><strong>HM:</strong> {item.health_manager_id || 'N/D'}</div>
                      <div><strong>Origine:</strong> {item.origin || 'N/D'}</div>
                      <div><strong>Pacchetto:</strong> {item.custom_package_name || 'N/D'}</div>
                      <div><strong>Creato:</strong> {formatDate(item.created_at)}</div>
                      <div><strong>Aggiornato:</strong> {formatDate(item.updated_at)}</div>
                    </div>

                    <div>
                      <div className="text-muted small mb-1">Storia cliente</div>
                      <div className="small ghle-old-story">{preview(item.client_story, 220)}</div>
                    </div>

                    <div>
                      <div className="text-muted small mb-1">Snapshot AI / dettaglio</div>
                      <div className="small ghle-old-story">{preview(item.ai_analysis_snapshot || item.ai_analysis, 260)}</div>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            ))}
          </Row>
        ) : null}
      </div>

      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg" centered>
        <Modal.Header closeButton>
          <Modal.Title>Dettaglio lead</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedItem ? (
            <div className="d-flex flex-column gap-3">
              <div className="d-flex align-items-center gap-2 flex-wrap">
                <h4 className="mb-0">{selectedItem.full_name || 'N/D'}</h4>
                <Badge bg={badgeVariant(selectedItem.status)} className="rounded-pill">
                  {STATUS_LABELS[selectedItem.status] || selectedItem.status || 'N/D'}
                </Badge>
              </div>
              <div className="ghle-old-meta-grid">
                <div><strong>Codice:</strong> {selectedItem.unique_code || 'N/D'}</div>
                <div><strong>Email:</strong> {selectedItem.email || 'N/D'}</div>
                <div><strong>Telefono:</strong> {selectedItem.phone || 'N/D'}</div>
                <div><strong>Sales:</strong> {selectedItem.sales_user?.full_name || 'N/D'}</div>
                <div><strong>Origine:</strong> {selectedItem.origin || 'N/D'}</div>
                <div><strong>Pacchetto:</strong> {selectedItem.custom_package_name || 'N/D'}</div>
              </div>
              <div>
                <div className="text-muted small mb-1">Storia cliente</div>
                <div className="ghle-old-modal-box">{preview(selectedItem.client_story, 1200)}</div>
              </div>
              <div>
                <div className="text-muted small mb-1">Snapshot AI / assegnazione</div>
                <div className="ghle-old-modal-box">{preview(selectedItem.ai_analysis_snapshot || selectedItem.ai_analysis, 1200)}</div>
              </div>
            </div>
          ) : null}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="outline-secondary" onClick={() => setShowModal(false)}>Chiudi</Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default GhlEmbedAssegnazioniPage;

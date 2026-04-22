import { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, InputGroup, Row, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import ghlService from '../../services/ghlService';
import '../ghl-embed/GhlEmbedAssegnazioni.css';

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

function getLeadName(item) {
  return item?.nome || item?.full_name || [item?.first_name, item?.last_name].filter(Boolean).join(' ') || item?.email || 'N/D';
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
    <div className="ghle-old-page">
      <div className="ghle-old-shell">
        <div className="ghle-old-hero">
          <div className="ghle-old-hero-left">
            <div className="ghle-old-hero-icon">
              <i className="ri-cpu-line"></i>
            </div>
            <div>
              <div className="ghle-old-kicker">Internal AI</div>
              <h1 className="ghle-old-title">Assegnazioni AI</h1>
              <p className="ghle-old-copy">
                Dashboard interna in stile old suite per analizzare, filtrare e aprire rapidamente le opportunità.
              </p>
            </div>
          </div>
          <div className="ghle-old-hero-meta">
            <span className="ghle-old-pill">{serverTotal} record server</span>
            <span className="ghle-old-pill ghle-old-pill-dark">Suite interna</span>
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
            <div className="ghle-old-stat-label">Processati</div>
            <div className="ghle-old-stat-value text-success">{stats.processed}</div>
          </div>
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">Con Sales assegnato</div>
            <div className="ghle-old-stat-value text-primary">{stats.salesAssigned}</div>
          </div>
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">Ultimo refresh</div>
            <div className="ghle-old-stat-value ghle-old-stat-sm">{formatDate(lastLoadedAt)}</div>
          </div>
        </div>

        <div className="ghle-old-toolbar">
          <div className="ghle-old-filters">
            {[
              { key: 'pending', label: 'Da lavorare' },
              { key: 'processed', label: 'Processati' },
              { key: 'all', label: 'Tutti' },
            ].map((f) => (
              <button
                key={f.key}
                type="button"
                className={`ghle-old-chip ${statusFilter === f.key ? 'active' : ''}`}
                onClick={() => setStatusFilter(f.key)}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="ghle-old-controls">
            <InputGroup className="ghle-old-search">
              <InputGroup.Text>
                <i className="ri-search-line"></i>
              </InputGroup.Text>
              <Form.Control
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Nome, email, telefono, Sales o pacchetto"
              />
            </InputGroup>

            <Button
              variant={showSalesOnly ? 'success' : 'outline-success'}
              className="ghle-old-action"
              onClick={() => setShowSalesOnly((prev) => !prev)}
            >
              {showSalesOnly ? 'Mostra tutti i lead' : 'Solo lead con Sales'}
            </Button>
            <Button variant="outline-secondary" className="ghle-old-action" onClick={clearFilters}>
              Reset
            </Button>
            <Button variant="outline-primary" className="ghle-old-action" onClick={() => loadQueue()} disabled={loading}>
              {loading ? <Spinner size="sm" animation="border" className="me-2" /> : null}
              Ricarica
            </Button>
          </div>
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
          <div className="ghle-old-loading">
            <Spinner animation="border" role="status" className="me-2" />
            Caricamento queue in corso...
          </div>
        ) : visibleOpportunities.length === 0 ? (
          <Card className="ghle-old-empty shadow-sm border-0 rounded-4">
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
                <Card className="ghle-old-card shadow-sm border-0 rounded-4 overflow-hidden h-100">
                  <Card.Body className="p-4 d-flex flex-column gap-3">
                    <div className="d-flex justify-content-between align-items-start gap-3">
                      <div className="flex-grow-1">
                        <div className="d-flex align-items-center gap-2 flex-wrap mb-2">
                          <h5 className="mb-0 fw-bold">{getLeadName(item)}</h5>
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

                    <div className="ghle-old-meta-grid">
                      <div><strong>Email:</strong> {item.email || 'N/D'}</div>
                      <div><strong>Telefono:</strong> {item.lead_phone || item.phone || 'N/D'}</div>
                      <div><strong>Sales:</strong> {item.sales_person?.full_name || item.sales_consultant || 'N/D'}</div>
                      <div><strong>Pacchetto:</strong> {item.pacchetto || item.custom_package_name || 'N/D'}</div>
                      <div><strong>Durata:</strong> {item.durata || 'N/D'}</div>
                      <div><strong>HM:</strong> {item.health_manager_email || 'N/D'}</div>
                      <div><strong>Ricevuto:</strong> {formatDate(item.received_at || item.created_at)}</div>
                      <div><strong>Aggiornato:</strong> {formatDate(item.updated_at)}</div>
                    </div>

                    <div>
                      <div className="text-muted small mb-1">Storia</div>
                      <div className="small ghle-old-story">{truncate(item.storia || item.client_story, 160)}</div>
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
    </div>
  );
}

export default AssegnazioniAI;

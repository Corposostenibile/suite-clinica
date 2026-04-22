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

  const [dashboard, setDashboard] = useState({ sales_ghl: null, hm_legacy: null });
  const [activeSection, setActiveSection] = useState('sales_ghl');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [salesStatusFilter, setSalesStatusFilter] = useState('pending');
  const [hmStatusFilter, setHmStatusFilter] = useState('all');
  const [showSalesOnly, setShowSalesOnly] = useState(false);
  const [lastLoadedAt, setLastLoadedAt] = useState(null);

  const loadDashboard = async (override = {}) => {
    setLoading(true);
    setError('');

    const nextSection = override.activeSection ?? activeSection;
    const nextSalesStatus = override.salesStatusFilter ?? salesStatusFilter;
    const nextHmStatus = override.hmStatusFilter ?? hmStatusFilter;
    const nextSearch = (override.search ?? search).trim();
    const effectiveSearch = nextSection === 'hm_legacy' ? '' : nextSearch;

    try {
      const response = await ghlService.getAssignmentsDashboard({
        include_ai: nextSection === 'sales_ghl' ? 1 : 0,
        include_hm: nextSection === 'hm_legacy' ? 1 : 0,
        ai_processed: nextSection === 'sales_ghl' ? nextSalesStatus : 'all',
        hm_state: 'all',
        q: effectiveSearch,
        limit_ai: 200,
        limit_hm: 200,
      });

      if (response?.success) {
        setDashboard({
          sales_ghl: response.sales_ghl || response.ai_legacy || { rows: [], stats: {}, total_available: 0 },
          hm_legacy: response.hm_legacy || { rows: [], stats: {}, total_available: 0 },
        });
        setLastLoadedAt(new Date().toISOString());
      } else {
        setError(response?.message || 'Impossibile caricare la dashboard assegnazioni.');
      }
    } catch (err) {
      console.error('Errore caricamento dashboard assegnazioni:', err);
      setError(err?.response?.data?.message || 'Errore durante il caricamento della dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timeout = setTimeout(() => {
      loadDashboard();
    }, 250);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSection, salesStatusFilter, hmStatusFilter]);

  useEffect(() => {
    if (activeSection === 'hm_legacy') return undefined;
    const timeout = setTimeout(() => {
      loadDashboard();
    }, 450);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, activeSection]);

  const currentSection = useMemo(() => {
    if (activeSection === 'hm_legacy') {
      return dashboard.hm_legacy || { rows: [], stats: {}, total_available: 0 };
    }
    return dashboard.sales_ghl || { rows: [], stats: {}, total_available: 0 };
  }, [activeSection, dashboard]);

  const stats = useMemo(() => {
    const rawStats = currentSection?.stats || {};
    if (activeSection === 'hm_legacy') {
      return {
        total: rawStats.total || 0,
        pending: rawStats.complete || 0,
        processed: rawStats.partial || 0,
        salesAssigned: 0,
      };
    }
    return {
      total: rawStats.total || 0,
      pending: rawStats.pending || 0,
      processed: rawStats.processed || 0,
      salesAssigned: rawStats.sales_assigned || 0,
    };
  }, [activeSection, currentSection]);

  const visibleRows = useMemo(() => {
    const rows = Array.isArray(currentSection?.rows) ? currentSection.rows : [];
    if (activeSection !== 'sales_ghl' || !showSalesOnly) return rows;
    return rows.filter((item) => Boolean(item.sales_person_id || item.sales_person?.id || item.sales_consultant));
  }, [activeSection, currentSection, showSalesOnly]);

  const serverTotal = useMemo(() => {
    if (!currentSection) return 0;
    return typeof currentSection.total_available === 'number' ? currentSection.total_available : (currentSection.rows || []).length;
  }, [currentSection]);

  const openOpportunity = (item) => {
    if (activeSection === 'hm_legacy') {
      const legacyLeadId = item.sales_lead_id || null;
      if (legacyLeadId) {
        navigate(`/suitemind-old/${legacyLeadId}`, { state: { lead: item } });
        return;
      }
      if (item.cliente_id) {
        navigate(`/clienti-dettaglio/${item.cliente_id}?tab=health_manager`);
        return;
      }
      return;
    }
    navigate(`/suitemind/${item.id}`, { state: { opportunity: item } });
  };

  const clearFilters = () => {
    setSearch('');
    setSalesStatusFilter('pending');
    setHmStatusFilter('all');
    setShowSalesOnly(false);
  };

  const emptyCopy = useMemo(() => {
    if (search.trim()) return 'Nessun record trovato con questi filtri.';
    if (activeSection === 'hm_legacy') return 'Non ci sono lead storico HM da lavorare in questo momento.';
    return 'Non ci sono lead GHL da lavorare in questo momento.';
  }, [activeSection, search]);

  const renderStatusBadge = (item) => {
    if (activeSection === 'hm_legacy') {
      const state = item.assignment_state || 'partial';
      const map = {
        partial: { bg: 'secondary', label: 'Terminato' },
        complete: { bg: 'success', label: 'Attivo' },
      };
      const conf = map[state] || map.partial;
      return <Badge bg={conf.bg} className="rounded-pill">{conf.label}</Badge>;
    }

    return (
      <Badge bg={item.processed ? 'success' : 'warning'} className="rounded-pill">
        {item.processed ? 'Processato' : 'Da lavorare'}
      </Badge>
    );
  };

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
                Pagina madre: queue SalesLead GHL + storico HM old-suite in un unico pannello.
              </p>
            </div>
          </div>
          <div className="ghle-old-hero-meta">
            <span className="ghle-old-pill">{serverTotal} record server</span>
            <span className="ghle-old-pill ghle-old-pill-dark">Suite interna</span>
          </div>
        </div>

        <div className="ghle-old-toolbar mb-3">
          <div className="ghle-old-filters">
            <button
              type="button"
              className={`ghle-old-chip ${activeSection === 'sales_ghl' ? 'active' : ''}`}
              onClick={() => setActiveSection('sales_ghl')}
            >
              Sales GHL
            </button>
            <button
              type="button"
              className={`ghle-old-chip ${activeSection === 'hm_legacy' ? 'active' : ''}`}
              onClick={() => setActiveSection('hm_legacy')}
            >
              Storico HM (old-suite)
            </button>
          </div>
        </div>

        <div className="ghle-old-stats">
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">Totale</div>
            <div className="ghle-old-stat-value">{stats.total}</div>
          </div>
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">{activeSection === 'hm_legacy' ? 'Attivi' : 'Da lavorare'}</div>
            <div className="ghle-old-stat-value text-warning">{stats.pending}</div>
          </div>
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">{activeSection === 'hm_legacy' ? 'Terminati' : 'Completati'}</div>
            <div className="ghle-old-stat-value text-success">{stats.processed}</div>
          </div>
          {activeSection === 'sales_ghl' ? (
            <div className="ghle-old-stat-card">
              <div className="ghle-old-stat-label">Intermedi</div>
              <div className="ghle-old-stat-value text-primary">{stats.salesAssigned}</div>
            </div>
          ) : null}
          <div className="ghle-old-stat-card">
            <div className="ghle-old-stat-label">Ultimo refresh</div>
            <div className="ghle-old-stat-value ghle-old-stat-sm">{formatDate(lastLoadedAt)}</div>
          </div>
        </div>

        <div className="ghle-old-toolbar">
          <div className="ghle-old-filters">
            {activeSection === 'sales_ghl'
              ? [
                  { key: 'pending', label: 'Da lavorare' },
                  { key: 'processed', label: 'Processati' },
                  { key: 'all', label: 'Tutti' },
                ].map((f) => (
                  <button
                    key={f.key}
                    type="button"
                    className={`ghle-old-chip ${salesStatusFilter === f.key ? 'active' : ''}`}
                    onClick={() => setSalesStatusFilter(f.key)}
                  >
                    {f.label}
                  </button>
                ))
              : null}
          </div>

          <div className="ghle-old-controls">
            {activeSection === 'sales_ghl' ? (
              <>
                <InputGroup className="ghle-old-search">
                  <InputGroup.Text>
                    <i className="ri-search-line"></i>
                  </InputGroup.Text>
                  <Form.Control
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Nome, email, telefono, pacchetto o codice"
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
              </>
            ) : null}

            <Button variant="outline-primary" className="ghle-old-action" onClick={() => loadDashboard()} disabled={loading}>
              {loading ? <Spinner size="sm" animation="border" className="me-2" /> : null}
              Ricarica
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="danger" className="mb-4 d-flex align-items-center justify-content-between gap-3 flex-wrap">
            <span>{error}</span>
            <Button variant="outline-danger" size="sm" onClick={() => loadDashboard()}>
              Riprova
            </Button>
          </Alert>
        )}

        {loading ? (
          <div className="ghle-old-loading">
            <Spinner animation="border" role="status" className="me-2" />
            Caricamento dashboard in corso...
          </div>
        ) : visibleRows.length === 0 ? (
          <Card className="ghle-old-empty shadow-sm border-0 rounded-4">
            <Card.Body className="text-center py-5">
              <div className="fs-1 mb-3">📭</div>
              <h5 className="mb-2">Nessun record disponibile</h5>
              <p className="text-muted mb-0">{emptyCopy}</p>
            </Card.Body>
          </Card>
        ) : (
          <Row className="g-3">
            {visibleRows.map((item) => (
              <Col key={item.id} xs={12} xl={6}>
                <Card className="ghle-old-card shadow-sm border-0 rounded-4 overflow-hidden h-100">
                  <Card.Body className="p-4 d-flex flex-column gap-3">
                    <div className="d-flex justify-content-between align-items-start gap-3">
                      <div className="flex-grow-1">
                        <div className="d-flex align-items-center gap-2 flex-wrap mb-2">
                          <h5 className="mb-0 fw-bold">{getLeadName(item)}</h5>
                          {renderStatusBadge(item)}
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
                      <div><strong>HM:</strong> {item.health_manager_email || item.health_manager?.full_name || 'N/D'}</div>
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
                      {activeSection === 'sales_ghl' ? (
                        <Button variant="outline-secondary" onClick={() => navigate(`/suitemind/${item.id}`, { state: { opportunity: item } })}>
                          Dettaglio
                        </Button>
                      ) : (
                        <Button
                          variant="outline-secondary"
                          onClick={() => {
                            if (item.sales_lead_id) {
                              navigate(`/suitemind-old/${item.sales_lead_id}`, { state: { lead: item } });
                              return;
                            }
                            if (item.cliente_id) {
                              navigate(`/clienti-dettaglio/${item.cliente_id}?tab=health_manager`);
                            }
                          }}
                        >
                          Dettaglio
                        </Button>
                      )}
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

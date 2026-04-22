import { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Form, InputGroup, Spinner, Table } from 'react-bootstrap';
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
  const [showSalesOnly, setShowSalesOnly] = useState(false);
  const [lastLoadedAt, setLastLoadedAt] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 25;

  const loadDashboard = async (override = {}) => {
    setLoading(true);
    setError('');

    const nextSection = override.activeSection ?? activeSection;
    const nextSalesStatus = override.salesStatusFilter ?? salesStatusFilter;
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
  }, [activeSection, salesStatusFilter]);

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

  const totalPages = useMemo(() => Math.max(1, Math.ceil(visibleRows.length / pageSize)), [visibleRows.length, pageSize]);

  const paginatedRows = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return visibleRows.slice(start, start + pageSize);
  }, [currentPage, pageSize, visibleRows]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  useEffect(() => {
    setCurrentPage(1);
  }, [activeSection, search, salesStatusFilter, showSalesOnly]);

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
    setShowSalesOnly(false);
    setCurrentPage(1);
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
          <Card className="shadow-sm border-0 rounded-4 overflow-hidden">
            <Card.Body className="p-0">
              <div className="d-flex justify-content-between align-items-center px-3 py-2 border-bottom bg-light-subtle">
                <div className="small text-muted">
                  Mostrando <strong>{(currentPage - 1) * pageSize + 1}</strong>-
                  <strong>{Math.min(currentPage * pageSize, visibleRows.length)}</strong> di <strong>{visibleRows.length}</strong> record
                </div>
                <div className="d-flex align-items-center gap-2">
                  <Button variant="outline-secondary" size="sm" disabled={currentPage <= 1} onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}>
                    Precedente
                  </Button>
                  <span className="small text-muted">Pagina {currentPage} / {totalPages}</span>
                  <Button variant="outline-secondary" size="sm" disabled={currentPage >= totalPages} onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}>
                    Successiva
                  </Button>
                </div>
              </div>

              <Table responsive hover className="mb-0 align-middle">
                <thead>
                  <tr>
                    <th>Lead</th>
                    <th>Contatti</th>
                    <th>Stato</th>
                    <th>{activeSection === 'sales_ghl' ? 'Sales' : 'HM'}</th>
                    <th>Pacchetto / Storia</th>
                    <th>Date</th>
                    <th className="text-end">Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedRows.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className="fw-semibold">{getLeadName(item)}</div>
                        <div className="small text-muted">ID {item.id}</div>
                      </td>
                      <td>
                        <div>{item.email || 'N/D'}</div>
                        <div className="small text-muted">{item.lead_phone || item.phone || 'N/D'}</div>
                      </td>
                      <td>{renderStatusBadge(item)}</td>
                      <td>
                        {activeSection === 'sales_ghl'
                          ? (item.sales_person?.full_name || item.sales_consultant || 'N/D')
                          : (item.health_manager_email || item.health_manager?.full_name || 'N/D')}
                      </td>
                      <td>
                        <div>{item.pacchetto || item.custom_package_name || 'N/D'}</div>
                        <div className="small text-muted">{truncate(item.storia || item.client_story, 90)}</div>
                      </td>
                      <td>
                        <div className="small">Creato: {formatDate(item.received_at || item.created_at || item.data_dal)}</div>
                        <div className="small text-muted">Upd: {formatDate(item.updated_at || item.data_al)}</div>
                      </td>
                      <td>
                        <div className="d-flex justify-content-end gap-2 flex-wrap">
                          <Button variant="success" size="sm" onClick={() => openOpportunity(item)}>
                            Apri
                          </Button>
                          {activeSection === 'sales_ghl' ? (
                            <Button variant="outline-secondary" size="sm" onClick={() => navigate(`/suitemind/${item.id}`, { state: { opportunity: item } })}>
                              Dettaglio
                            </Button>
                          ) : (
                            <Button
                              variant="outline-secondary"
                              size="sm"
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
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        )}
      </div>
    </div>
  );
}

export default AssegnazioniAI;

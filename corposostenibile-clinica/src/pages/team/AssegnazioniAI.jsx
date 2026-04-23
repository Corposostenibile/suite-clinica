import { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Form, InputGroup, Modal, Spinner, Table } from 'react-bootstrap';
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

function toTimestamp(value) {
  if (!value) return 0;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
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

function getSalesLabel(item) {
  return item?.sales_person?.full_name || item?.sales_consultant || item?.sales_person?.email || 'Non assegnato';
}

function getLeadTimeline(item, activeSection) {
  const entries = [];

  if (activeSection === 'sales_ghl') {
    entries.push({
      key: 'created',
      label: 'Lead ricevuto',
      date: item.received_at || item.created_at,
      note: `Stato iniziale: ${item.status || 'N/D'}`,
    });

    if (item.sales_person_id || item.sales_person?.id || item.sales_consultant) {
      entries.push({
        key: 'sales',
        label: 'Sales associato',
        date: item.updated_at || item.received_at || item.created_at,
        note: getSalesLabel(item),
      });
    }

    if (item.processed) {
      entries.push({
        key: 'processed',
        label: 'Lead processato',
        date: item.updated_at || item.received_at || item.created_at,
        note: `Stato corrente: ${item.status || 'N/D'}`,
      });
    }
  } else {
    entries.push({
      key: 'hm_start',
      label: 'Assegnazione HM avviata',
      date: item.data_dal || item.created_at,
      note: item.health_manager?.full_name || item.health_manager_email || 'N/D',
    });

    if (item.data_al) {
      entries.push({
        key: 'hm_end',
        label: 'Assegnazione HM terminata',
        date: item.data_al,
        note: 'Chiusura storico HM',
      });
    }
  }

  entries.push({
    key: 'updated',
    label: 'Ultimo aggiornamento',
    date: item.updated_at || item.data_al || item.data_dal || item.created_at,
    note: `Record ID: ${item.id}`,
  });

  return entries
    .filter((entry) => entry.date)
    .sort((a, b) => toTimestamp(b.date) - toTimestamp(a.date));
}

function escapeCsvCell(value) {
  const raw = value == null ? '' : String(value);
  if (raw.includes('"') || raw.includes(',') || raw.includes('\n')) {
    return `"${raw.replace(/"/g, '""')}"`;
  }
  return raw;
}

function AssegnazioniAI() {
  const navigate = useNavigate();

  const [dashboard, setDashboard] = useState({ sales_ghl: null, hm_legacy: null });
  const [activeSection, setActiveSection] = useState('sales_ghl');
  const [viewMode, setViewMode] = useState('table');
  const [expandedSalesKey, setExpandedSalesKey] = useState(null);
  const [timelineItem, setTimelineItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [salesStatusFilter, setSalesStatusFilter] = useState('pending');
  const [salesFilterQuery, setSalesFilterQuery] = useState('');
  const [selectedSalesFilter, setSelectedSalesFilter] = useState('all');
  const [lastLoadedAt, setLastLoadedAt] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 25;

  const loadDashboard = async (override = {}) => {
    setLoading(true);
    setError('');

    const nextSection = override.activeSection ?? activeSection;
    const nextSalesStatus = override.salesStatusFilter ?? salesStatusFilter;
    const nextSearch = (override.search ?? search).trim();
    const nextSalesFilter = override.selectedSalesFilter ?? selectedSalesFilter;
    const effectiveSearch = nextSection === 'hm_legacy' ? '' : nextSearch;

    try {
      const response = await ghlService.getAssignmentsDashboard({
        include_ai: nextSection === 'sales_ghl' ? 1 : 0,
        include_hm: nextSection === 'hm_legacy' ? 1 : 0,
        ai_processed: nextSection === 'sales_ghl' ? nextSalesStatus : 'all',
        hm_state: 'all',
        q: effectiveSearch,
        sales_user_id: nextSection === 'sales_ghl' && nextSalesFilter !== 'all' ? nextSalesFilter : undefined,
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
  }, [activeSection, salesStatusFilter, selectedSalesFilter]);

  useEffect(() => {
    if (activeSection === 'hm_legacy') return undefined;
    const timeout = setTimeout(() => {
      loadDashboard();
    }, 450);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, activeSection]);

  useEffect(() => {
    if (activeSection !== 'sales_ghl') {
      setViewMode('table');
      setExpandedSalesKey(null);
    }
  }, [activeSection]);

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

  const salesFilterOptions = useMemo(() => {
    const rows = Array.isArray(dashboard.sales_ghl?.rows) ? dashboard.sales_ghl.rows : [];
    const optionsMap = new Map();

    rows.forEach((item) => {
      const salesId = item.sales_person?.id || item.sales_person_id;
      const salesEmail = item.sales_person?.email || '';
      const key = salesId ? String(salesId) : salesEmail ? `email:${salesEmail}` : 'unassigned';
      const label = getSalesLabel(item);

      if (!optionsMap.has(key)) {
        optionsMap.set(key, {
          value: key,
          label,
          email: salesEmail,
        });
      }
    });

    const options = Array.from(optionsMap.values()).sort((a, b) => a.label.localeCompare(b.label, 'it'));
    return [{ value: 'all', label: 'Tutti i sales', email: '' }, ...options];
  }, [dashboard.sales_ghl?.rows]);

  const filteredSalesOptions = useMemo(() => {
    const q = salesFilterQuery.trim().toLowerCase();
    if (!q) return salesFilterOptions;
    return salesFilterOptions.filter((opt) => {
      if (opt.value === 'all') return true;
      return `${opt.label} ${opt.email}`.toLowerCase().includes(q);
    });
  }, [salesFilterOptions, salesFilterQuery]);

  const visibleRows = useMemo(() => {
    const rows = Array.isArray(currentSection?.rows) ? currentSection.rows : [];
    if (activeSection !== 'sales_ghl' || selectedSalesFilter === 'all') return rows;

    if (selectedSalesFilter === 'unassigned') {
      return rows.filter((item) => !item.sales_person_id && !item.sales_person?.id && !item.sales_consultant);
    }

    if (selectedSalesFilter.startsWith('email:')) {
      const expectedEmail = selectedSalesFilter.slice(6).toLowerCase();
      return rows.filter((item) => (item.sales_person?.email || '').toLowerCase() === expectedEmail);
    }

    const selectedId = Number(selectedSalesFilter);
    if (!Number.isNaN(selectedId)) {
      return rows.filter((item) => Number(item.sales_person?.id || item.sales_person_id) === selectedId);
    }

    return rows;
  }, [activeSection, currentSection, selectedSalesFilter]);

  const salesGroups = useMemo(() => {
    if (activeSection !== 'sales_ghl') return [];
    const groupsMap = new Map();

    visibleRows.forEach((item) => {
      const salesId = item.sales_person?.id || item.sales_person_id;
      const salesEmail = item.sales_person?.email || null;
      const key = salesId ? `sales_${salesId}` : salesEmail ? `sales_email_${salesEmail}` : 'sales_unassigned';

      if (!groupsMap.has(key)) {
        groupsMap.set(key, {
          key,
          salesLabel: getSalesLabel(item),
          salesEmail: salesEmail || item.sales_person?.email || null,
          leads: [],
          pending: 0,
          processed: 0,
        });
      }

      const group = groupsMap.get(key);
      group.leads.push(item);
      if (item.processed) group.processed += 1;
      else group.pending += 1;
    });

    return Array.from(groupsMap.values()).sort((a, b) => b.leads.length - a.leads.length);
  }, [activeSection, visibleRows]);

  const serverTotal = useMemo(() => {
    if (!currentSection) return 0;
    return typeof currentSection.total_available === 'number' ? currentSection.total_available : (currentSection.rows || []).length;
  }, [currentSection]);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(visibleRows.length / pageSize)), [visibleRows.length, pageSize]);

  const paginatedRows = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return visibleRows.slice(start, start + pageSize);
  }, [currentPage, pageSize, visibleRows]);

  const timelineEntries = useMemo(() => {
    if (!timelineItem) return [];
    return getLeadTimeline(timelineItem, activeSection);
  }, [activeSection, timelineItem]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  useEffect(() => {
    setCurrentPage(1);
  }, [activeSection, search, salesStatusFilter, selectedSalesFilter]);

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
    setSalesFilterQuery('');
    setSelectedSalesFilter('all');
    setExpandedSalesKey(null);
    setCurrentPage(1);
  };

  const exportVisibleCsv = () => {
    if (!visibleRows.length) return;

    const headers = [
      'id',
      'nome',
      'email',
      'telefono',
      'stato',
      'processed',
      activeSection === 'sales_ghl' ? 'sales_user' : 'health_manager',
      'pacchetto',
      'storia',
      'created_at',
      'updated_at',
    ];

    const lines = [headers.join(',')];

    visibleRows.forEach((item) => {
      const values = [
        item.id,
        getLeadName(item),
        item.email || '',
        item.lead_phone || item.phone || '',
        item.status || item.assignment_state || '',
        item.processed ? '1' : '0',
        activeSection === 'sales_ghl'
          ? (item.sales_person?.full_name || item.sales_consultant || item.sales_person?.email || '')
          : (item.health_manager?.full_name || item.health_manager_email || ''),
        item.pacchetto || item.custom_package_name || '',
        item.storia || item.client_story || '',
        item.received_at || item.created_at || item.data_dal || '',
        item.updated_at || item.data_al || '',
      ];
      lines.push(values.map(escapeCsvCell).join(','));
    });

    const csvContent = `\uFEFF${lines.join('\n')}`;
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `assegnazioni_${activeSection}_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
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

            {activeSection === 'sales_ghl' ? (
              <>
                <button
                  type="button"
                  className={`ghle-old-chip ${viewMode === 'table' ? 'active' : ''}`}
                  onClick={() => setViewMode('table')}
                >
                  Vista lead
                </button>
                <button
                  type="button"
                  className={`ghle-old-chip ${viewMode === 'sales' ? 'active' : ''}`}
                  onClick={() => setViewMode('sales')}
                >
                  Drill-down Sales
                </button>
              </>
            ) : null}
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
                    placeholder="Nome lead, email lead/sales, telefono, pacchetto o codice"
                  />
                </InputGroup>

                <InputGroup className="ghle-old-search">
                  <InputGroup.Text>
                    <i className="ri-user-search-line"></i>
                  </InputGroup.Text>
                  <Form.Control
                    value={salesFilterQuery}
                    onChange={(e) => setSalesFilterQuery(e.target.value)}
                    placeholder="Cerca nome/email sales nel filtro"
                  />
                </InputGroup>

                <Form.Select
                  className="ghle-old-select"
                  value={selectedSalesFilter}
                  onChange={(e) => setSelectedSalesFilter(e.target.value)}
                >
                  {filteredSalesOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.email ? `${opt.label} (${opt.email})` : opt.label}
                    </option>
                  ))}
                </Form.Select>

                <Button variant="outline-secondary" className="ghle-old-action" onClick={clearFilters}>
                  Reset
                </Button>
              </>
            ) : null}

            <Button variant="outline-success" className="ghle-old-action" onClick={exportVisibleCsv} disabled={!visibleRows.length}>
              Export CSV
            </Button>

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
        ) : viewMode === 'sales' && activeSection === 'sales_ghl' ? (
          <div className="d-grid gap-3">
            {salesGroups.map((group) => {
              const isOpen = expandedSalesKey === group.key;
              return (
                <Card key={group.key} className="shadow-sm border-0 rounded-4">
                  <Card.Body>
                    <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                      <div>
                        <div className="fw-semibold">{group.salesLabel}</div>
                        <div className="small text-muted">{group.salesEmail || 'Email non disponibile'}</div>
                      </div>
                      <div className="d-flex align-items-center gap-2 flex-wrap">
                        <Badge bg="secondary" pill>{group.leads.length} lead</Badge>
                        <Badge bg="warning" pill>{group.pending} da lavorare</Badge>
                        <Badge bg="success" pill>{group.processed} processati</Badge>
                        <Button
                          variant={isOpen ? 'outline-secondary' : 'outline-primary'}
                          size="sm"
                          onClick={() => setExpandedSalesKey((prev) => (prev === group.key ? null : group.key))}
                        >
                          {isOpen ? 'Chiudi' : 'Apri dettaglio'}
                        </Button>
                      </div>
                    </div>

                    {isOpen ? (
                      <Table responsive hover className="mb-0 align-middle">
                        <thead>
                          <tr>
                            <th>Lead</th>
                            <th>Contatti</th>
                            <th>Stato</th>
                            <th>Date</th>
                            <th className="text-end">Azioni</th>
                          </tr>
                        </thead>
                        <tbody>
                          {group.leads.map((item) => (
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
                                <div className="small">Creato: {formatDate(item.received_at || item.created_at)}</div>
                                <div className="small text-muted">Upd: {formatDate(item.updated_at)}</div>
                              </td>
                              <td>
                                <div className="d-flex justify-content-end gap-2 flex-wrap">
                                  <Button variant="success" size="sm" onClick={() => openOpportunity(item)}>
                                    Apri
                                  </Button>
                                  <Button variant="outline-secondary" size="sm" onClick={() => setTimelineItem(item)}>
                                    Timeline
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    ) : null}
                  </Card.Body>
                </Card>
              );
            })}
          </div>
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
                          <Button variant="outline-secondary" size="sm" onClick={() => setTimelineItem(item)}>
                            Timeline
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

        <Modal show={Boolean(timelineItem)} onHide={() => setTimelineItem(null)} centered>
          <Modal.Header closeButton>
            <Modal.Title>Timeline lead</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {timelineItem ? (
              <>
                <div className="fw-semibold mb-1">{getLeadName(timelineItem)}</div>
                <div className="small text-muted mb-3">ID {timelineItem.id}</div>

                {timelineEntries.length ? (
                  <div className="d-grid gap-2">
                    {timelineEntries.map((entry) => (
                      <div key={entry.key} className="border rounded-3 p-2">
                        <div className="d-flex justify-content-between gap-2">
                          <strong>{entry.label}</strong>
                          <span className="small text-muted">{formatDate(entry.date)}</span>
                        </div>
                        <div className="small text-muted mt-1">{entry.note || '—'}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-muted">Nessun evento disponibile per questo record.</div>
                )}
              </>
            ) : null}
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setTimelineItem(null)}>
              Chiudi
            </Button>
          </Modal.Footer>
        </Modal>
      </div>
    </div>
  );
}

export default AssegnazioniAI;

import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Badge, Card, Spinner, Alert, Button, ButtonGroup, Modal, Tab, Tabs, Form } from 'react-bootstrap';
import api from '../../services/api';
import ghlService from '../../services/ghlService';
import checkService from '../../services/checkService';
import './AssegnazioniAI.css';

// Stati possibili delle assegnazioni
const STATUS_CONFIG = {
  pending_finance: { label: 'In attesa Finance', color: 'warning', icon: 'ri-time-line' },
  finance_approved: { label: 'Approvato Finance', color: 'info', icon: 'ri-checkbox-circle-line' },
  pending_assignment: { label: 'Da assegnare', color: 'primary', icon: 'ri-user-add-line' },
  in_progress: { label: 'In corso', color: 'success', icon: 'ri-loader-4-line' },
  completed: { label: 'Completato', color: 'secondary', icon: 'ri-check-double-line' },
};

// Mappa Dipartimenti e Ruoli per Criteri
const DEPT_ROLE_MAP = {
  2: 'nutrizione',
  24: 'nutrizione',
  3: 'coach',
  4: 'psicologia'
};

const LEAD_STATUS_STYLES = {
  unassigned: { label: 'Da assegnare', bg: 'secondary-subtle', text: 'secondary' },
  partial: { label: 'Parziali', bg: 'warning-subtle', text: 'warning' },
  complete: { label: 'Completate', bg: 'success-subtle', text: 'success' },
};

const PACKAGE_FALLBACK_MAP = {
  'N+C+P': 'NCP',
  'N+C': 'NC',
  'N+P': 'NP',
  'C+P': 'CP',
};

const normalizePackageCode = (raw) => {
  const code = String(raw || '').trim().toUpperCase();
  if (!code) return '';
  if (PACKAGE_FALLBACK_MAP[code]) return PACKAGE_FALLBACK_MAP[code];
  if (/^[NCP]+$/.test(code)) return code;
  return '';
};

const getPackageRequirements = (rawPackage) => {
  const normalized = normalizePackageCode(rawPackage);
  if (!normalized) {
    return { normalized: '', nutrition: true, coach: true, psychology: true };
  }

  return {
    normalized,
    nutrition: normalized.includes('N'),
    coach: normalized.includes('C'),
    psychology: normalized.includes('P'),
  };
};

function AssegnazioniAI() {
  const navigate = useNavigate();

  // Stati Generali
  const [activeTab, setActiveTab] = useState('webhook-data');
  const [error, setError] = useState(null);

  // Stati Assegnazioni
  const [assignments, setAssignments] = useState([]);
  const [initialChecksByLead, setInitialChecksByLead] = useState({});
  const [loading, setLoading] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showCheckResponseModal, setShowCheckResponseModal] = useState(false);
  const [checkResponseLoading, setCheckResponseLoading] = useState(false);
  const [checkResponseError, setCheckResponseError] = useState('');
  const [selectedCheckResponse, setSelectedCheckResponse] = useState(null);

  // Stati Webhook (Lead)
  const [opportunityData, setOpportunityData] = useState([]);
  const [loadingOpportunity, setLoadingOpportunity] = useState(false);
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);
  const [showOpportunityModal, setShowOpportunityModal] = useState(false);
  const [webhookUrls, setWebhookUrls] = useState({ opportunity_data_url: '', acconto_open_url: '' });
  const [leadFilter, setLeadFilter] = useState('unassigned'); // all | unassigned | partial | complete | assigned
  const [leadSearch, setLeadSearch] = useState('');
  const [hmFilter, setHmFilter] = useState('all'); // all | none | hm_id

  const [toastState, setToastState] = useState({ show: false, message: '', variant: 'success' });

  // --- FETCH DATA ---

  const loadInitialChecksStatus = async (clientIds) => {
    const normalizedIds = [
      ...new Set(
        (clientIds || [])
          .filter((v) => Number.isInteger(v) || (typeof v === 'string' && /^\\d+$/.test(v)))
          .map((v) => Number(v))
      )
    ];

    if (normalizedIds.length === 0) {
      setInitialChecksByLead({});
      return;
    }

    try {
      const checksResp = await checkService.getInitialAssignments({
        status: 'all',
        page: 1,
        perPage: 100,
        clientIds: normalizedIds
      });

      const map = {};
      (checksResp?.items || []).forEach((item) => {
        map[item.lead_id] = {
          check_1: item.check_1 || { assigned: false, completed: false, response_count: 0 },
          check_2: item.check_2 || { assigned: false, completed: false, response_count: 0 }
        };
      });
      setInitialChecksByLead(map);
    } catch (err) {
      console.error('Errore caricamento stato check iniziali:', err);
      setInitialChecksByLead({});
    }
  };

  const fetchAssignments = async () => {
    setLoading(true);
    try {
      const response = await api.get('/ghl/api/assignments', {
        params: selectedStatus !== 'all' ? { status: selectedStatus } : {}
      });
      if (response.data.success !== false) {
        const data = response.data.assignments || response.data || [];
        const normalized = Array.isArray(data) ? data : [];
        setAssignments(normalized);
        await loadInitialChecksStatus(normalized.map((a) => a.cliente_id));
      }
    } catch (err) {
      console.error('Errore assegnazioni:', err);
      setInitialChecksByLead({});
    } finally {
      setLoading(false);
    }
  };

  const renderInitialCheckBadge = (check) => {
    if (check?.completed) {
      return <Badge bg="success">Compilato</Badge>;
    }
    return <Badge bg="danger">Non completato</Badge>;
  };

  const handleOpenCheckResponseModal = async (leadId, checkNumber, check) => {
    if (!check?.completed || !leadId) return;
    setShowCheckResponseModal(true);
    setCheckResponseLoading(true);
    setCheckResponseError('');
    setSelectedCheckResponse(null);
    try {
      const result = await checkService.getInitialCheckResponseDetail(leadId, checkNumber);
      if (!result?.success) {
        throw new Error(result?.error || 'Dettaglio check non disponibile');
      }
      setSelectedCheckResponse(result.data);
    } catch (err) {
      setCheckResponseError(err?.message || 'Errore caricamento check compilato');
    } finally {
      setCheckResponseLoading(false);
    }
  };

  const handleCopyCheckLink = (token) => {
    if (!token) return;
    const url = `${window.location.origin}/client-checks/public/${token}`;
    const contentEl = document.querySelector('.content-body');
    const sidebarOffset = contentEl ? contentEl.getBoundingClientRect().left : 0;
    navigator.clipboard.writeText(url).then(() => {
      setToastState({ show: true, message: 'Link check copiato negli appunti!', variant: 'success', sidebarOffset });
      setTimeout(() => setToastState(prev => ({ ...prev, show: false })), 2500);
    });
  };

  const renderInitialCheckCell = (leadId, checkNumber, check) => {
    if (!check?.completed) {
      return (
        <div className="d-flex align-items-center gap-1">
          {renderInitialCheckBadge(check)}
          {check?.token && (
            <Button
              variant="link"
              className="p-0 text-muted"
              title="Copia link check"
              onClick={() => handleCopyCheckLink(check.token)}
            >
              <i className="ri-file-copy-line"></i>
            </Button>
          )}
        </div>
      );
    }
    return (
      <div className="d-flex align-items-center gap-1">
        <Button
          variant="link"
          className="p-0 text-decoration-none"
          onClick={() => handleOpenCheckResponseModal(leadId, checkNumber, check)}
        >
          {renderInitialCheckBadge(check)}
        </Button>
        {check?.token && (
          <Button
            variant="link"
            className="p-0 text-muted"
            title="Copia link check"
            onClick={() => handleCopyCheckLink(check.token)}
          >
            <i className="ri-file-copy-line"></i>
          </Button>
        )}
      </div>
    );
  };

  const fetchOpportunityData = async () => {
    setLoadingOpportunity(true);
    try {
      const result = await ghlService.getOpportunityData();
      if (result.success) {
        const rows = result.data || [];
        setOpportunityData(rows);
        await loadInitialChecksStatus(rows.map((opp) => opp.cliente_id));
        return rows;
      }
    } catch (err) {
      console.error('Errore opportunity data:', err);
    } finally {
      setLoadingOpportunity(false);
    }
    return null;
  };

  const getLeadRequirements = (opp) => {
    return getPackageRequirements(opp?.pacchetto);
  };

  const getLeadRequiredRolesCount = (opp) => {
    const req = getLeadRequirements(opp);
    return [req.nutrition, req.coach, req.psychology].filter(Boolean).length;
  };

  const getLeadAssignedCount = (opp) => {
    const flags = getLeadAssignmentFlags(opp);
    const req = getLeadRequirements(opp);
    return [req.nutrition && flags.nutrition, req.coach && flags.coach, req.psychology && flags.psychology].filter(Boolean).length;
  };

  const getLeadAssignmentFlags = (opp) => {
    const assignments = opp?.assignments || {};
    return {
      nutrition: !!assignments.nutritionist_id,
      coach: !!assignments.coach_id,
      psychology: !!assignments.psychologist_id
    };
  };

  const isLeadAssigned = (opp) => {
    return getLeadAssignedCount(opp) > 0;
  };

  const isLeadFullyAssigned = (opp) => {
    const required = getLeadRequiredRolesCount(opp);
    if (required === 0) return false;
    return getLeadAssignedCount(opp) >= required;
  };


  // --- EFFECTS ---

  useEffect(() => {
    if (activeTab === 'assignments') fetchAssignments();
    if (activeTab === 'webhook-data') fetchOpportunityData();
  }, [activeTab, selectedStatus]);

  useEffect(() => {
    ghlService.getWebhookUrls().then((result) => {
      if (result?.success) {
        setWebhookUrls({
          opportunity_data_url: result.opportunity_data_url || '',
          acconto_open_url: result.acconto_open_url || '',
        });
      }
    }).catch(() => {});
  }, []);

  // Auto-refresh webhook data
  useEffect(() => {
    const interval = setInterval(() => {
      if (activeTab === 'webhook-data') fetchOpportunityData();
    }, 10000);
    return () => clearInterval(interval);
  }, [activeTab]);

  // --- RENDER HELPERS ---

  const formatDate = (dateString, withTime = true) => {
    if (!dateString) return '-';
    const options = {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    };
    if (withTime) {
      options.hour = '2-digit';
      options.minute = '2-digit';
    }
    return new Date(dateString).toLocaleDateString('it-IT', options);
  };

  const StatusBadge = ({ status }) => {
    const config = STATUS_CONFIG[status] || { label: status, color: 'secondary', icon: 'ri-question-line' };
    return (
      <Badge bg={config.color} className="d-flex align-items-center gap-1" style={{ width: 'fit-content' }}>
        <i className={config.icon}></i>
        {config.label}
      </Badge>
    );
  };

  const uniqueHMs = useMemo(() => {
    const map = new Map();
    opportunityData.forEach((opp) => {
      if (opp.health_manager) {
        map.set(opp.health_manager.id, opp.health_manager);
      }
    });
    return Array.from(map.values()).sort((a, b) => a.full_name.localeCompare(b.full_name));
  }, [opportunityData]);

  const filteredLeads = useMemo(() => {
    let rows = opportunityData;

    if (leadSearch.trim()) {
      const q = leadSearch.trim().toLowerCase();
      rows = rows.filter((opp) => (
        (opp.nome || '').toLowerCase().includes(q) ||
        (opp.email || '').toLowerCase().includes(q) ||
        (opp.lead_phone || '').toLowerCase().includes(q) ||
        (opp.health_manager?.full_name || opp.health_manager_email || '').toLowerCase().includes(q) ||
        (opp.pacchetto || '').toLowerCase().includes(q) ||
        (opp.storia || '').toLowerCase().includes(q)
      ));
    }

    if (hmFilter === 'none') {
      rows = rows.filter((opp) => !opp.health_manager);
    } else if (hmFilter !== 'all') {
      rows = rows.filter((opp) => opp.health_manager?.id === Number(hmFilter));
    }

    if (leadFilter === 'unassigned') rows = rows.filter((opp) => !isLeadAssigned(opp));
    if (leadFilter === 'assigned') rows = rows.filter(isLeadAssigned);
    if (leadFilter === 'partial') rows = rows.filter((opp) => isLeadAssigned(opp) && !isLeadFullyAssigned(opp));
    if (leadFilter === 'complete') rows = rows.filter(isLeadFullyAssigned);

    return rows;
  }, [opportunityData, leadFilter, leadSearch, hmFilter]);

  const formatDateShort = (dateStr) => {
    if (!dateStr) return '-';
    const d = new Date(dateStr);
    return d.toLocaleDateString('it-IT', { day: '2-digit', month: 'short' });
  };

  return (
    <div className="assegnazioni-page">
      {toastState.show && (
        <div className="ai-toast-overlay" style={{ paddingLeft: toastState.sidebarOffset || 0 }}>
          <div className="ai-toast">
            <div className="ai-toast-icon">
              <i className={toastState.variant === 'success' ? 'ri-checkbox-circle-line' : 'ri-error-warning-line'}></i>
            </div>
            <span className="ai-toast-message">{toastState.message}</span>
          </div>
        </div>
      )}

      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4 gap-2">
        <div>
          <h4 className="mb-1">Assegnazione Professionisti</h4>
          <p className="text-muted mb-0">Assegnazione con SUMI dei pazienti ai professionisti del team</p>
        </div>
      </div>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)} className="mb-3">
          <i className="ri-error-warning-line me-2"></i>{error}
        </Alert>
      )}

      <Tabs activeKey={activeTab} onSelect={(k) => setActiveTab(k)}>

        {/* TAB 1: Pazienti da Assegnare */}
        <Tab eventKey="webhook-data" title={<span className="d-flex align-items-center gap-2"><i className="ri-inbox-archive-line"></i>Pazienti da Assegnare{opportunityData.length > 0 && <Badge bg="primary" pill>{opportunityData.length}</Badge>}</span>}>

          {/* Toolbar */}
          <div className="ai-toolbar">
            <div className="lead-filters">
              {[
                { key: 'all', label: 'Tutti', icon: 'ri-list-unordered' },
                { key: 'unassigned', label: 'Da assegnare', icon: 'ri-user-add-line' },
                { key: 'partial', label: 'Parziali', icon: 'ri-pie-chart-line' },
                { key: 'complete', label: 'Assegnati', icon: 'ri-check-double-line' },
              ].map(f => (
                <button key={f.key} className={`lead-filter-chip${leadFilter === f.key ? ' active' : ''}`} onClick={() => setLeadFilter(f.key)}>
                  <i className={f.icon}></i>
                  {f.label}
                </button>
              ))}
            </div>

            <Form.Select
              value={hmFilter}
              onChange={(e) => setHmFilter(e.target.value)}
              style={{ maxWidth: '180px' }}
            >
              <option value="all">Tutti gli HM</option>
              <option value="none">Senza HM</option>
              {uniqueHMs.map((hm) => (
                <option key={hm.id} value={hm.id}>{hm.full_name}</option>
              ))}
            </Form.Select>

            <Form.Control
              type="search"
              placeholder="Cerca paziente..."
              value={leadSearch}
              onChange={(e) => setLeadSearch(e.target.value)}
              style={{ maxWidth: '220px' }}
            />

            <div className="ms-auto">
              <button className="ai-refresh-btn" onClick={() => fetchOpportunityData()} disabled={loadingOpportunity}>
                <i className={`ri-refresh-line ${loadingOpportunity ? 'ai-spin' : ''}`}></i>
              </button>
            </div>
          </div>

          {/* Contenuto */}
          {loadingOpportunity && opportunityData.length === 0 ? (
            <div className="ai-empty-state">
              <Spinner animation="border" size="sm" variant="primary" />
              <p className="mt-2">Caricamento pazienti...</p>
            </div>
          ) : opportunityData.length === 0 ? (
            <div className="ai-empty-state">
              <div className="empty-icon">
                <i className="ri-inbox-archive-line"></i>
              </div>
              <p>Nessun paziente in attesa</p>
              <p style={{ fontSize: '12px', color: '#94a3b8' }}>I nuovi pazienti da GHL appariranno qui automaticamente.</p>
            </div>
          ) : filteredLeads.length === 0 ? (
            <div className="ai-empty-state">
              <p>Nessun risultato con i filtri attivi</p>
            </div>
          ) : (
            <div>
              {filteredLeads.map((opp) => {
                const flags = getLeadAssignmentFlags(opp);
                const requirements = getLeadRequirements(opp);
                const requiredCount = getLeadRequiredRolesCount(opp);
                const assignedCount = getLeadAssignedCount(opp);
                const checks = initialChecksByLead[opp.cliente_id] || {};

                return (
                  <div key={opp.id} className="patient-card">
                    <div className="d-flex align-items-center gap-3">
                      {/* Info paziente */}
                      <div className="flex-grow-1" style={{ minWidth: 0 }}>
                        <div className="d-flex align-items-center gap-2 flex-wrap">
                          <span className="patient-name">{opp.nome}</span>
                          <span className="pkg-badge">{opp.pacchetto}</span>
                          {opp.durata && opp.durata !== '0' && <span style={{ fontSize: '11px', color: '#94a3b8' }}>{opp.durata}gg</span>}
                        </div>
                        {opp.storia && (
                          <button className="btn-storia" onClick={() => { setSelectedOpportunity(opp); setShowOpportunityModal(true); }}>
                            <i className="ri-file-text-line"></i> Storia Cliente
                          </button>
                        )}

                        <div className="patient-meta">
                          {opp.email && (
                            <span><i className="ri-mail-line"></i><a href={`mailto:${opp.email}`}>{opp.email}</a></span>
                          )}
                          {opp.lead_phone && (
                            <span><i className="ri-phone-line"></i><a href={`tel:${opp.lead_phone}`}>{opp.lead_phone}</a></span>
                          )}
                        </div>
                        {opp.health_manager ? (
                          <div className="hm-chip-lg">
                            <img src={opp.health_manager.avatar_url} alt="" />
                            {opp.health_manager.full_name}
                          </div>
                        ) : opp.health_manager_email ? (
                          <div className="hm-chip-lg hm-chip-warn">
                            <i className="ri-alert-line"></i> {opp.health_manager_email}
                          </div>
                        ) : null}
                      </div>

                      {/* Right panel */}
                      <div className="patient-right">
                        {/* Checks */}
                        <div className="check-group">
                          <div className="check-item">
                            <div className="check-label">Check 1</div>
                            {renderInitialCheckCell(opp.cliente_id, 1, checks.check_1)}
                          </div>
                          <div className="check-item">
                            <div className="check-label">Check 2</div>
                            {renderInitialCheckCell(opp.cliente_id, 2, checks.check_2)}
                          </div>
                        </div>

                        <div className="divider" />

                        {/* Role indicators N C P */}
                        <div className="assignment-progress">
                          <div className="role-indicators">
                            {[
                              { key: 'nutrition', label: 'N', cls: 'role-n' },
                              { key: 'coach', label: 'C', cls: 'role-c' },
                              { key: 'psychology', label: 'P', cls: 'role-p' },
                            ].map(role => (
                              <span
                                key={role.key}
                                className={`role-dot ${role.cls} ${!requirements[role.key] ? 'inactive' : flags[role.key] ? 'assigned' : 'pending'}`}
                              >
                                {role.label}
                              </span>
                            ))}
                          </div>
                          <div className="progress-text">{assignedCount}/{requiredCount}</div>
                        </div>

                        <div className="divider" />

                        {/* Actions */}
                        <div className="patient-actions">
                          <button className="btn-action btn-ai" onClick={() => navigate(`/suitemind/${opp.id}`, { state: { opportunity: opp } })} title="SuiteMind Match">
                            <img src="/suitemind.png" alt="SuiteMind" className="btn-ai-logo" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Tab>

        {/* TAB 2: Assegnazioni Completate/Storico */}
        <Tab eventKey="assignments" title={<span className="d-flex align-items-center gap-2"><i className="ri-file-history-line"></i>Storico</span>}>
             <Card className="border-0 shadow-sm">
               {/* Filters for Assignment History */}
                <Card.Header className="bg-white border-0 py-3">
                    <div className="d-flex align-items-center gap-2 flex-wrap">
                        <span className="text-muted small me-2">Filtra per stato:</span>
                        <ButtonGroup size="sm">
                        <Button variant={selectedStatus === 'all' ? 'primary' : 'outline-primary'} onClick={() => setSelectedStatus('all')}>Tutti</Button>
                        <Button variant={selectedStatus === 'pending_finance' ? 'warning' : 'outline-warning'} onClick={() => setSelectedStatus('pending_finance')}>In attesa Finance</Button>
                        <Button variant={selectedStatus === 'pending_assignment' ? 'info' : 'outline-info'} onClick={() => setSelectedStatus('pending_assignment')}>Da assegnare</Button>
                        <Button variant={selectedStatus === 'completed' ? 'success' : 'outline-success'} onClick={() => setSelectedStatus('completed')}>Completati</Button>
                        </ButtonGroup>
                    </div>
                </Card.Header>
            <Card.Body className="p-0">
               {loading ? (
                <div className="text-center py-5"><Spinner animation="border" /></div>
              ) : assignments.length === 0 ? (
                <div className="text-center py-5 text-muted">Nessuna assegnazione trovata</div>
              ) : (
                <Table responsive hover className="mb-0">
                  <thead className="bg-light">
                    <tr>
                      <th>ID</th>
                      <th>Cliente</th>
                      <th>Stato</th>
                      <th>Check 1</th>
                      <th>Check 2</th>
                      <th>Professionisti</th>
                      <th>Data</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {assignments.map((assignment) => (
                      <tr key={assignment.id}>
                        <td>#{assignment.id}</td>
                        <td>{assignment.cliente_nome}</td>
                        <td><StatusBadge status={assignment.status} /></td>
                        <td>
                          {renderInitialCheckCell(assignment.cliente_id, 1, initialChecksByLead[assignment.cliente_id]?.check_1)}
                        </td>
                        <td>
                          {renderInitialCheckCell(assignment.cliente_id, 2, initialChecksByLead[assignment.cliente_id]?.check_2)}
                        </td>
                        <td>
                            <div className="d-flex gap-1">
                                {assignment.nutrizionista_assigned && <Badge bg="success">N</Badge>}
                                {assignment.coach_assigned && <Badge bg="success">C</Badge>}
                                {assignment.psicologa_assigned && <Badge bg="success">P</Badge>}
                            </div>
                        </td>
                        <td>{formatDate(assignment.created_at)}</td>
                        <td className="text-end">
                            <Button size="sm" variant="outline-secondary" onClick={() => { setSelectedAssignment(assignment); setShowModal(true); }}>Dettagli</Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>
        </Tab>

      </Tabs>

      {/* Storia Cliente Modal */}
      {showOpportunityModal && selectedOpportunity && (
        <div className="storia-modal-overlay" onClick={() => setShowOpportunityModal(false)}>
          <div className="storia-modal" onClick={(e) => e.stopPropagation()}>
            <div className="storia-modal-header">
              <div className="storia-modal-header-left">
                <div className="storia-modal-icon"><i className="ri-file-text-line"></i></div>
                <h5 className="storia-modal-title">{selectedOpportunity.nome}</h5>
              </div>
              <button className="storia-modal-close" onClick={() => setShowOpportunityModal(false)}>
                <i className="ri-close-line"></i>
              </button>
            </div>
            <div className="storia-modal-body">
              <span className="storia-modal-label">Storia del Cliente</span>
              <p className="storia-modal-text">
                {selectedOpportunity.storia || <em style={{ color: '#94a3b8' }}>Nessuna storia fornita</em>}
              </p>
            </div>
          </div>
        </div>
      )}

      <Modal show={showCheckResponseModal} onHide={() => setShowCheckResponseModal(false)} size="lg" dialogClassName="modal-mobile-full">
        <Modal.Header closeButton>
          <Modal.Title>Check Compilato</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {checkResponseLoading ? (
            <div className="text-center py-4">
              <Spinner animation="border" size="sm" className="me-2" />
              <span>Caricamento risposta...</span>
            </div>
          ) : checkResponseError ? (
            <Alert variant="danger" className="mb-0">{checkResponseError}</Alert>
          ) : selectedCheckResponse ? (
            <div>
              <div className="mb-3">
                <div className="fw-bold">{selectedCheckResponse.form_name}</div>
                <small className="text-muted">
                  Paziente: {selectedCheckResponse.lead_name || '-'} | Inviato: {formatDate(selectedCheckResponse.submitted_at)}
                </small>
              </div>
              <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
                {(selectedCheckResponse.responses || []).map((item) => {
                  const rawValue = item?.value;
                  let renderedValue = '-';
                  if (rawValue !== null && rawValue !== undefined && rawValue !== '') {
                    if (typeof rawValue === 'object') {
                      if (rawValue?.type === 'file' && rawValue?.path) {
                        renderedValue = (
                          <a href={rawValue.path} target="_blank" rel="noreferrer">
                            {rawValue.filename || 'Apri file'}
                          </a>
                        );
                      } else {
                        renderedValue = (
                          <code style={{ whiteSpace: 'pre-wrap' }}>
                            {JSON.stringify(rawValue)}
                          </code>
                        );
                      }
                    } else {
                      renderedValue = String(rawValue);
                    }
                  }
                  return (
                    <div key={`${item.field_id}-${item.label}`} className="mb-3">
                      <div className="small text-muted">{item.label}</div>
                      <div>{renderedValue}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="text-muted">Nessun dato disponibile.</div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowCheckResponseModal(false)}>Chiudi</Button>
        </Modal.Footer>
      </Modal>



      {/* Existing Assignment Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)} dialogClassName="modal-mobile-full">
         <Modal.Header closeButton><Modal.Title>Dettagli Assegnazione</Modal.Title></Modal.Header>
         <Modal.Body>
             {selectedAssignment && (
                 <div>
                     <p><strong>Cliente:</strong> {selectedAssignment.cliente_nome}</p>
                     <p><strong>Stato:</strong> <StatusBadge status={selectedAssignment.status} /></p>
                     <hr/>
                     <div className="d-flex gap-2 justify-content-center">
                         <div className="text-center p-2 border rounded">
                             <div className="small text-muted">Nutrizionista</div>
                             <div className="fw-bold">{selectedAssignment.nutrizionista_assigned ? 'Assegnato' : '-'}</div>
                         </div>
                         <div className="text-center p-2 border rounded">
                             <div className="small text-muted">Coach</div>
                             <div className="fw-bold">{selectedAssignment.coach_assigned ? 'Assegnato' : '-'}</div>
                         </div>
                         <div className="text-center p-2 border rounded">
                             <div className="small text-muted">Psicologa</div>
                             <div className="fw-bold">{selectedAssignment.psicologa_assigned ? 'Assegnato' : '-'}</div>
                         </div>
                     </div>
                 </div>
             )}
         </Modal.Body>
         <Modal.Footer>
             <Button variant="secondary" onClick={() => setShowModal(false)}>Chiudi</Button>
             <Button variant="primary">Gestisci</Button>
         </Modal.Footer>
      </Modal>

    </div>
  );
}

export default AssegnazioniAI;

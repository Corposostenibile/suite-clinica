import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge, Spinner, Alert, Button, Modal, Form } from 'react-bootstrap';
import oldSuiteService from '../../services/oldSuiteService';
import './AssegnazioniOldSuite.css';

/**
 * Parse package name "N/C-90gg-C" → { code, roles, duration }
 */
const parsePackageName = (name) => {
  const result = { raw: name || '', code: '', roles: { nutrition: true, coach: true, psychology: true }, duration: 0 };
  if (!name) return result;

  const parts = name.trim().split('-');
  if (parts.length > 0) {
    const rolePart = parts[0].trim().toUpperCase();
    const letters = rolePart.split('/').map(r => r.trim()).filter(Boolean);
    if (letters.length > 0) {
      const hasN = letters.includes('N');
      const hasC = letters.includes('C');
      const hasP = letters.includes('P');
      if (hasN || hasC || hasP) {
        result.roles = { nutrition: hasN, coach: hasC, psychology: hasP };
        result.code = [hasN && 'N', hasC && 'C', hasP && 'P'].filter(Boolean).join('');
      }
    }
  }
  if (parts.length > 1) {
    const match = parts[1].match(/(\d+)/);
    if (match) result.duration = parseInt(match[1], 10);
  }
  return result;
};

function AssegnazioniOldSuite() {
  const navigate = useNavigate();

  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [leadFilter, setLeadFilter] = useState('unassigned');
  const [leadSearch, setLeadSearch] = useState('');
  const [hmFilter, setHmFilter] = useState('all');

  // Modal storia
  const [selectedLead, setSelectedLead] = useState(null);
  const [showStoriaModal, setShowStoriaModal] = useState(false);

  // Modal check response
  const [showCheckModal, setShowCheckModal] = useState(false);
  const [checkLoading, setCheckLoading] = useState(false);
  const [checkError, setCheckError] = useState('');
  const [checkResponse, setCheckResponse] = useState(null);

  // Toast
  const [toastState, setToastState] = useState({ show: false, message: '' });

  // --- FETCH ---

  const fetchLeads = async () => {
    setLoading(true);
    try {
      const result = await oldSuiteService.getLeads();
      if (result.success) {
        setLeads(result.data || []);
      }
    } catch (err) {
      console.error('Errore caricamento leads:', err);
      setError('Errore nel caricamento dei pazienti');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLeads(); }, []);

  // Auto-refresh ogni 10 secondi
  useEffect(() => {
    const interval = setInterval(fetchLeads, 10000);
    return () => clearInterval(interval);
  }, []);

  // --- HELPERS ---

  const getAssignedCount = (lead) => {
    const a = lead.assignments || {};
    const r = lead.package_roles || {};
    return [
      r.nutrition && a.nutritionist_id,
      r.coach && a.coach_id,
      r.psychology && a.psychologist_id,
    ].filter(Boolean).length;
  };

  const getRequiredCount = (lead) => {
    const r = lead.package_roles || {};
    return [r.nutrition, r.coach, r.psychology].filter(Boolean).length;
  };

  const isLeadAssigned = (lead) => getAssignedCount(lead) > 0;
  const isLeadFullyAssigned = (lead) => {
    const required = getRequiredCount(lead);
    return required > 0 && getAssignedCount(lead) >= required;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('it-IT', { day: '2-digit', month: 'short' });
  };

  // --- FILTERS ---

  const uniqueHMs = useMemo(() => {
    const map = new Map();
    leads.forEach((lead) => {
      if (lead.health_manager) map.set(lead.health_manager.id, lead.health_manager);
    });
    return Array.from(map.values()).sort((a, b) => a.full_name.localeCompare(b.full_name));
  }, [leads]);

  const filteredLeads = useMemo(() => {
    let rows = leads;

    if (leadSearch.trim()) {
      const q = leadSearch.trim().toLowerCase();
      rows = rows.filter((l) =>
        (l.full_name || '').toLowerCase().includes(q) ||
        (l.email || '').toLowerCase().includes(q) ||
        (l.phone || '').toLowerCase().includes(q) ||
        (l.health_manager?.full_name || l.health_manager_name || '').toLowerCase().includes(q) ||
        (l.package_name || '').toLowerCase().includes(q) ||
        (l.client_story || '').toLowerCase().includes(q)
      );
    }

    if (hmFilter === 'none') {
      rows = rows.filter((l) => !l.health_manager);
    } else if (hmFilter !== 'all') {
      rows = rows.filter((l) => l.health_manager?.id === Number(hmFilter));
    }

    if (leadFilter === 'unassigned') rows = rows.filter((l) => !isLeadAssigned(l));
    if (leadFilter === 'assigned') rows = rows.filter(isLeadAssigned);
    if (leadFilter === 'partial') rows = rows.filter((l) => isLeadAssigned(l) && !isLeadFullyAssigned(l));
    if (leadFilter === 'complete') rows = rows.filter(isLeadFullyAssigned);

    return rows;
  }, [leads, leadFilter, leadSearch, hmFilter]);

  // --- CHECK HANDLERS ---

  const handleCopyCheckLink = (url) => {
    if (!url) return;
    navigator.clipboard.writeText(url).then(() => {
      setToastState({ show: true, message: 'Link check copiato negli appunti!' });
      setTimeout(() => setToastState(prev => ({ ...prev, show: false })), 2500);
    });
  };

  const handleOpenCheckResponse = async (leadId, checkNumber, check) => {
    if (!check?.completed || !check?.has_responses) return;
    setShowCheckModal(true);
    setCheckLoading(true);
    setCheckError('');
    setCheckResponse(null);
    try {
      const result = await oldSuiteService.getCheckDetail(leadId, checkNumber);
      if (!result?.success) throw new Error(result?.error || 'Dettaglio check non disponibile');
      setCheckResponse(result.data);
    } catch (err) {
      setCheckError(err?.message || 'Errore caricamento check');
    } finally {
      setCheckLoading(false);
    }
  };

  const renderCheckCell = (leadId, checkNumber, check) => {
    const isCompleted = check?.completed;
    const badge = isCompleted
      ? <Badge bg="success">Compilato</Badge>
      : <Badge bg="danger">Non completato</Badge>;

    return (
      <div className="d-flex align-items-center gap-1">
        {isCompleted && check?.has_responses ? (
          <Button variant="link" className="p-0 text-decoration-none" onClick={() => handleOpenCheckResponse(leadId, checkNumber, check)}>
            {badge}
          </Button>
        ) : badge}
        {checkNumber === 3 && check?.completed && (check?.type || check?.score !== null) && (
          <span className="check3-score-badge">{check.type}{check.score !== null && ` ${check.score}`}</span>
        )}
        {!isCompleted && check?.form_url && (
          <Button variant="link" className="p-0 text-muted" title="Copia link check" onClick={() => handleCopyCheckLink(check.form_url)}>
            <i className="ri-file-copy-line"></i>
          </Button>
        )}
      </div>
    );
  };

  // --- RENDER ---

  return (
    <div className="assegnazioni-page">
      {toastState.show && (
        <div className="ai-toast-overlay">
          <div className="ai-toast">
            <div className="ai-toast-icon"><i className="ri-checkbox-circle-line"></i></div>
            <span className="ai-toast-message">{toastState.message}</span>
          </div>
        </div>
      )}

      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4 gap-2">
        <div>
          <h4 className="mb-1">Assegnazione Professionisti</h4>
          <p className="text-muted mb-0">Assegnazione con SUMI dei pazienti dalla vecchia suite</p>
        </div>
      </div>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)} className="mb-3">
          <i className="ri-error-warning-line me-2"></i>{error}
        </Alert>
      )}

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

        <Form.Select value={hmFilter} onChange={(e) => setHmFilter(e.target.value)} style={{ maxWidth: '180px' }}>
          <option value="all">Tutti gli HM</option>
          <option value="none">Senza HM</option>
          {uniqueHMs.map((hm) => (
            <option key={hm.id} value={hm.id}>{hm.full_name}</option>
          ))}
        </Form.Select>

        <Form.Control type="search" placeholder="Cerca paziente..." value={leadSearch} onChange={(e) => setLeadSearch(e.target.value)} style={{ maxWidth: '220px' }} />

        <div className="ms-auto">
          <button className="ai-refresh-btn" onClick={fetchLeads} disabled={loading}>
            <i className={`ri-refresh-line ${loading ? 'ai-spin' : ''}`}></i>
          </button>
        </div>
      </div>

      {/* Content */}
      {loading && leads.length === 0 ? (
        <div className="ai-empty-state">
          <Spinner animation="border" size="sm" variant="primary" />
          <p className="mt-2">Caricamento pazienti...</p>
        </div>
      ) : leads.length === 0 ? (
        <div className="ai-empty-state">
          <div className="empty-icon"><i className="ri-inbox-archive-line"></i></div>
          <p>Nessun paziente in attesa</p>
          <p style={{ fontSize: '12px', color: '#94a3b8' }}>I nuovi pazienti dalla vecchia suite appariranno qui automaticamente.</p>
        </div>
      ) : filteredLeads.length === 0 ? (
        <div className="ai-empty-state">
          <p>Nessun risultato con i filtri attivi</p>
        </div>
      ) : (
        <div>
          {filteredLeads.map((lead) => {
            const flags = lead.assignments || {};
            const roles = lead.package_roles || {};
            const requiredCount = getRequiredCount(lead);
            const assignedCount = getAssignedCount(lead);
            const checks = lead.checks || {};

            return (
              <div key={lead.id} className="patient-card">
                <div className="d-flex align-items-center gap-3">
                  {/* Info paziente */}
                  <div className="flex-grow-1" style={{ minWidth: 0 }}>
                    <div className="d-flex align-items-center gap-2 flex-wrap">
                      <span className="patient-name">{lead.full_name}</span>
                      <span className="pkg-badge">{lead.package_code || lead.package_name}</span>
                      {lead.duration_days > 0 && <span style={{ fontSize: '11px', color: '#94a3b8' }}>{lead.duration_days}gg</span>}
                    </div>
                    {lead.client_story && (
                      <button className="btn-storia" onClick={() => { setSelectedLead(lead); setShowStoriaModal(true); }}>
                        <i className="ri-file-text-line"></i> Storia Cliente
                      </button>
                    )}
                    <div className="patient-meta">
                      {lead.email && <span><i className="ri-mail-line"></i><a href={`mailto:${lead.email}`}>{lead.email}</a></span>}
                      {lead.phone && <span><i className="ri-phone-line"></i><a href={`tel:${lead.phone}`}>{lead.phone}</a></span>}
                    </div>
                    {lead.health_manager ? (
                      <div className="hm-chip-lg">
                        <img src={lead.health_manager.avatar_url} alt="" />
                        {lead.health_manager.full_name}
                      </div>
                    ) : lead.health_manager_name ? (
                      <div className="hm-chip-lg hm-chip-warn">
                        <i className="ri-alert-line"></i> {lead.health_manager_name} <small>(non trovato)</small>
                      </div>
                    ) : null}
                    {lead.onboarding_date && (
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                        <i className="ri-calendar-check-line" style={{ marginRight: '4px' }}></i>
                        Onboarding: {formatDate(lead.onboarding_date)}
                        {lead.onboarding_time && ` alle ${lead.onboarding_time}`}
                      </div>
                    )}
                  </div>

                  {/* Right panel */}
                  <div className="patient-right">
                    {/* Checks */}
                    <div className="check-group">
                      <div className="check-item">
                        <div className="check-label">Check 1</div>
                        {renderCheckCell(lead.id, 1, checks.check_1)}
                      </div>
                      <div className="check-item">
                        <div className="check-label">Check 2</div>
                        {renderCheckCell(lead.id, 2, checks.check_2)}
                      </div>
                      <div className="check-item">
                        <div className="check-label">Check 3</div>
                        {renderCheckCell(lead.id, 3, checks.check_3)}
                      </div>
                    </div>

                    <div className="divider" />

                    {/* Role indicators N C P */}
                    <div className="assignment-progress">
                      <div className="role-indicators">
                        {[
                          { key: 'nutrition', flag: 'nutritionist_id', label: 'N', cls: 'role-n' },
                          { key: 'coach', flag: 'coach_id', label: 'C', cls: 'role-c' },
                          { key: 'psychology', flag: 'psychologist_id', label: 'P', cls: 'role-p' },
                        ].map(role => (
                          <span
                            key={role.key}
                            className={`role-dot ${role.cls} ${!roles[role.key] ? 'inactive' : flags[role.flag] ? 'assigned' : 'pending'}`}
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
                      <button className="btn-action btn-ai" onClick={() => navigate(`/suitemind-old/${lead.id}`, { state: { lead } })} title="SuiteMind Match">
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

      {/* Storia Modal */}
      {showStoriaModal && selectedLead && (
        <div className="storia-modal-overlay" onClick={() => setShowStoriaModal(false)}>
          <div className="storia-modal" onClick={(e) => e.stopPropagation()}>
            <div className="storia-modal-header">
              <div className="storia-modal-header-left">
                <div className="storia-modal-icon"><i className="ri-file-text-line"></i></div>
                <h5 className="storia-modal-title">{selectedLead.full_name}</h5>
              </div>
              <button className="storia-modal-close" onClick={() => setShowStoriaModal(false)}>
                <i className="ri-close-line"></i>
              </button>
            </div>
            <div className="storia-modal-body">
              <span className="storia-modal-label">Storia del Cliente</span>
              <p className="storia-modal-text">
                {selectedLead.client_story || <em style={{ color: '#94a3b8' }}>Nessuna storia fornita</em>}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Check Response Modal */}
      <Modal show={showCheckModal} onHide={() => setShowCheckModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Check Compilato</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {checkLoading ? (
            <div className="text-center py-4">
              <Spinner animation="border" size="sm" className="me-2" />
              <span>Caricamento risposta...</span>
            </div>
          ) : checkError ? (
            <Alert variant="danger" className="mb-0">{checkError}</Alert>
          ) : checkResponse ? (
            <div>
              <div className="mb-3">
                <div className="fw-bold">{checkResponse.form_name}</div>
                <small className="text-muted">
                  Paziente: {checkResponse.lead_name || '-'} | Inviato: {checkResponse.completed_at ? new Date(checkResponse.completed_at).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '-'}
                </small>
                {checkResponse.check_number === 3 && (checkResponse.score !== null || checkResponse.type) && (
                  <div className="mt-2">
                    {checkResponse.type && <Badge bg="info" className="me-2">Tipo: {checkResponse.type}</Badge>}
                    {checkResponse.score !== null && <Badge bg="secondary">Score: {checkResponse.score}/78</Badge>}
                  </div>
                )}
              </div>
              <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
                {(checkResponse.responses || []).map((item, idx) => (
                  <div key={idx} className="mb-3">
                    <div className="small text-muted">{item.label}</div>
                    <div>{item.value !== null && item.value !== undefined && item.value !== '' ? String(item.value) : '-'}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-muted">Nessun dato disponibile.</div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowCheckModal(false)}>Chiudi</Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default AssegnazioniOldSuite;

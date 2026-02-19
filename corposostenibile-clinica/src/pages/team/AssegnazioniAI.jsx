import { useState, useEffect, useMemo } from 'react';
import { Table, Badge, Card, Spinner, Alert, Button, ButtonGroup, Modal, Tab, Tabs, Form, Row, Col, Toast, ToastContainer } from 'react-bootstrap';
import api from '../../services/api';
import ghlService from '../../services/ghlService';
import checkService from '../../services/checkService';
import { TEAM_TYPE_COLORS } from '../../services/teamService';

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

const DEPT_LABELS = {
  2: 'Nutrizione',
  3: 'Coach',
  4: 'Psicologia',
  24: 'Nutrizione 2'
};

const LEAD_STATUS_STYLES = {
  unassigned: { label: 'Da assegnare', bg: 'secondary-subtle', text: 'secondary' },
  partial: { label: 'Parziali', bg: 'warning-subtle', text: 'warning' },
  complete: { label: 'Completate', bg: 'success-subtle', text: 'success' },
};

const ROLE_ANALYSIS_KEYS = {
  nutrition: ['nutrition', 'nutrizione', 'nutrizionista'],
  coach: ['coach'],
  psychology: ['psychology', 'psicologia', 'psicologo', 'psicologa'],
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
  const [leadFilter, setLeadFilter] = useState('all'); // all | unassigned | partial | complete | assigned
  const [leadSearch, setLeadSearch] = useState('');

  // Stati Professionisti (Criteri)
  const [professionals, setProfessionals] = useState([]);
  const [criteriaSchema, setCriteriaSchema] = useState({});
  const [loadingProfs, setLoadingProfs] = useState(false);
  const [showProfModal, setShowProfModal] = useState(false);
  const [editingProf, setEditingProf] = useState(null);
  const [tempCriteria, setTempCriteria] = useState({});
  const [profFilter, setProfFilter] = useState('all'); // 'all', 'nutrizione', 'coach', 'psicologia'
  const [searchTerm, setSearchTerm] = useState('');
  const [teamFilter, setTeamFilter] = useState('all'); // 'all' | teamId (string)
  const [criteriaStatus, setCriteriaStatus] = useState(null); // { type, message }
  const [toastState, setToastState] = useState({ show: false, message: '', variant: 'success' });

  // Stati AI Modal
  const [showAIModal, setShowAIModal] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiMatches, setAiMatches] = useState(null);
  const [selectedMatches, setSelectedMatches] = useState({ nutrition: '', coach: '', psychology: '' });
  const [assignmentNotes, setAssignmentNotes] = useState('');
  const [activeRoleFlow, setActiveRoleFlow] = useState(null); // null, 'nutrition', 'coach', 'psychology'
  const [assignmentSuccess, setAssignmentSuccess] = useState(false);
  const [lastAssignedProf, setLastAssignedProf] = useState(null);
  const [hasNewInteraction, setHasNewInteraction] = useState(false);

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
    return <Badge bg="warning" text="dark">Non completato</Badge>;
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

  const renderInitialCheckCell = (leadId, checkNumber, check) => {
    if (!check?.completed) {
      return renderInitialCheckBadge(check);
    }
    return (
      <Button
        variant="link"
        className="p-0 text-decoration-none"
        onClick={() => handleOpenCheckResponseModal(leadId, checkNumber, check)}
      >
        {renderInitialCheckBadge(check)}
      </Button>
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

  const isAlreadyAssigned = (role) => {
    const saved = selectedOpportunity?.assignments;
    if (!saved) return false;
    
    if (role === 'nutrition') return selectedMatches.nutrition == saved.nutritionist_id;
    if (role === 'coach') return selectedMatches.coach == saved.coach_id;
    if (role === 'psychology') return selectedMatches.psychology == saved.psychologist_id;
    
    return false;
  };

  const getLeadRequirements = (opp) => {
    return getPackageRequirements(opp?.pacchetto);
  };

  const isRoleRequiredForLead = (opp, role) => {
    const req = getLeadRequirements(opp);
    return !!req[role];
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

  const getStoredAnalysisForRole = (existing, role) => {
    if (!existing || !role) return null;
    const keys = ROLE_ANALYSIS_KEYS[role] || [role];
    const matchKey = keys.find((k) => existing[k]);
    if (matchKey) return existing[matchKey];
    if (existing.summary || existing.criteria) return existing; // legacy flat format
    return null;
  };

  const fetchProfessionalsAndSchema = async () => {
    setLoadingProfs(true);
    try {
      const [respProfs, respSchema] = await Promise.all([
        api.get('/team/professionals/criteria'),
        api.get('/team/criteria/schema')
      ]);

      if (respProfs.data.success) {
        setProfessionals(respProfs.data.professionals);
      }

      if (respSchema.data.success) {
        setCriteriaSchema(respSchema.data.schema);
      }
    } catch (err) {
      console.error('Errore caricamento professionisti:', err);
      setError('Impossibile caricare la lista professionisti.');
    } finally {
      setLoadingProfs(false);
    }
  };

  // --- EFFECTS ---

  useEffect(() => {
    if (activeTab === 'assignments') fetchAssignments();
    if (activeTab === 'webhook-data') fetchOpportunityData();
    if (activeTab === 'professionals') fetchProfessionalsAndSchema();
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

  // --- ACTIONS ---

  const handleOpenAIModal = (opp) => {
    setSelectedOpportunity(opp);
    setAiAnalysis(null);
    setAiMatches(null);
    setAssignmentNotes('');
    setSelectedMatches({ nutrition: '', coach: '', psychology: '' });
    setActiveRoleFlow(null); // Reset flow
    setAssignmentSuccess(false);
    setLastAssignedProf(null);
    setHasNewInteraction(false);
    setShowAIModal(true);
  };

  const handleSelectRoleFlow = (role) => {
    if (!isRoleRequiredForLead(selectedOpportunity, role)) return;

    setActiveRoleFlow(role);
    setAiAnalysis(null);
    setAiMatches(null);
    setHasNewInteraction(false);

    // Check if we already have analysis for this role
    const existing = selectedOpportunity?.ai_analysis;
    // Handle both legacy (flat) and new (keyed) structure appropriately
    // Legacy: existing has 'criteria' directly. New: existing[role] has 'criteria'.
    
    let relevantAnalysis = null;

    if (existing) {
      relevantAnalysis = getStoredAnalysisForRole(existing, role);
    }

    if (relevantAnalysis) {
        setAiAnalysis(relevantAnalysis);
        handleRunMatching(relevantAnalysis.criteria);
    } else {
        handleRunAIAnalysis(selectedOpportunity, role);
    }
  };

  const handleRunAIAnalysis = async (targetOpp = null, role = null) => {
    const opp = targetOpp || selectedOpportunity;
    const targetRole = role || activeRoleFlow;
    
    if (!opp?.storia) {
      alert("Nessuna storia disponibile per l'analisi AI.");
      return;
    }
    
    setAiLoading(true);
    
    try {
      // 1. Analyze Lead
      const resAnalyze = await api.post('/team/assignments/analyze-lead', { 
        story: opp.storia,
        opportunity_id: opp.id,
        assignment_id: opp.assignment_id,
        role: targetRole
      });
      
      if (resAnalyze.data.success) {
        const analysis = resAnalyze.data.analysis;
        setAiAnalysis(analysis);
        
        // Update local opportunity object with new analysis to avoid re-fetching immediately
        // (Optional but good for UX)
        
        // 2. Match Professionals
        await handleRunMatching(analysis.criteria);
        setHasNewInteraction(true);
      }
    } catch (err) {
      console.error("Errore AI Analysis:", err);
      alert("Errore durante l'analisi AI. Controlla la console.");
    } finally {
      setAiLoading(false);
    }
  };

  const handleRunMatching = async (criteria) => {
    try {
        const resMatch = await api.post('/team/assignments/match', { criteria });
        
        if (resMatch.data.success) {
            const matches = resMatch.data.matches;
            setAiMatches(matches);
            
            // Pre-select first best match if available
            setSelectedMatches({
                nutrition: matches.nutrizione?.[0]?.id || '',
                coach: matches.coach?.[0]?.id || '',
                psychology: matches.psicologia?.[0]?.id || ''
            });
        }
    } catch (err) {
        console.error("Errore Matching:", err);
    }
  };

  const handleConfirmAssignment = async (role) => {
    // Possiamo procedere se abbiamo un assignment_id (cliente esistente)
    // O se abbiamo un id (lead da GHLOpportunityData)
    if (!selectedOpportunity?.assignment_id && !selectedOpportunity?.id) {
        alert("ID Assegnazione o Lead mancante. Impossibile procedere.");
        return;
    }

    const nutritionist_id = role === 'nutrition' ? selectedMatches.nutrition : null;
    const coach_id = role === 'coach' ? selectedMatches.coach : null;
    const psychologist_id = role === 'psychology' ? selectedMatches.psychology : null;

    if (!nutritionist_id && !coach_id && !psychologist_id) {
        alert("Seleziona un professionista per procedere.");
        return;
    }

    try {
        setLoading(true);
        const payload = {
            assignment_id: selectedOpportunity.assignment_id,
            opportunity_data_id: !selectedOpportunity.assignment_id ? selectedOpportunity.id : null,
            nutritionist_id,
            coach_id,
            psychologist_id,
            notes: assignmentNotes,
            ai_analysis: aiAnalysis
        };
        
        const response = await api.post('/team/assignments/confirm', payload);
        if (response.data.success) {
            // Success visual feedback
            const profId = role === 'nutrition' ? selectedMatches.nutrition : (role === 'coach' ? selectedMatches.coach : selectedMatches.psychology);
            const prof = professionals.find(p => p.id == profId);
            setLastAssignedProf(prof);
            setAssignmentSuccess(true);
            setHasNewInteraction(false);
            
            // Refetch data and update selected opportunity to reflect new state
            const refreshed = await fetchOpportunityData();
            if (refreshed && Array.isArray(refreshed)) {
              const updated = refreshed.find(o => o.id === selectedOpportunity.id);
              if (updated) setSelectedOpportunity(updated);
            }
        }
    } catch (err) {
        console.error("Errore conferma:", err);
        alert("Errore durante il salvataggio dell'assegnazione.");
    } finally {
        setLoading(false);
    }
  };

  const handleEditCriteria = (prof) => {
    setEditingProf(prof);
    setTempCriteria(prof.criteria || {});
    setCriteriaStatus(null);
    setShowProfModal(true);
  };

  const handleSaveCriteria = async () => {
    if (!editingProf) return;
    try {
      await api.put(`/team/professionals/${editingProf.id}/criteria`, {
        criteria: tempCriteria
      });
      setShowProfModal(false);
      setCriteriaStatus({ type: 'success', message: 'Criteri aggiornati con successo.' });
      setToastState({ show: true, message: 'Criteri salvati', variant: 'success' });
      fetchProfessionalsAndSchema(); // Reload
    } catch (err) {
      console.error('Errore salvataggio criteri:', err);
      setCriteriaStatus({ type: 'error', message: 'Errore durante il salvataggio dei criteri.' });
      setToastState({ show: true, message: 'Errore nel salvataggio', variant: 'danger' });
    }
  };

  const toggleCriterion = (key) => {
    setTempCriteria(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const toggleAllCriteria = (keys, value) => {
    setTempCriteria(prev => {
      const updated = { ...prev };
      keys.forEach(k => {
        updated[k] = value;
      });
      return updated;
    });
  };

  const getFilteredProfessionals = () => {
    let filtered = professionals;

    // 1. Filtro per Ruolo
    if (profFilter !== 'all') {
      filtered = filtered.filter(p => {
         const mapped = DEPT_ROLE_MAP[p.department_id] || 'other';
         return mapped === profFilter;
      });
    }

    // 2. Filtro per Ricerca (Nome)
    if (searchTerm.trim() !== '') {
      const lowerTerm = searchTerm.toLowerCase();
      filtered = filtered.filter(p => p.name.toLowerCase().includes(lowerTerm));
    }

    // 3. Filtro per Team
    if (teamFilter !== 'all') {
      const teamId = Number(teamFilter);
      filtered = filtered.filter(p => (p.teams || []).some(t => t.id === teamId));
    }
    // Rimosso else che filtrava i professionisti senza team quando teamFilter era 'all'

    return filtered;
  };

  const showTeamGrouping = teamFilter === 'all';

  const teamOptions = useMemo(() => {
    const roleFiltered = profFilter === 'all'
      ? professionals
      : professionals.filter(p => (DEPT_ROLE_MAP[p.department_id] || 'other') === profFilter);

    const teamMap = new Map();
    roleFiltered.forEach(p => {
      (p.teams || []).forEach(t => {
        if (!teamMap.has(t.id)) teamMap.set(t.id, t);
      });
    });

    const options = Array.from(teamMap.values());
    options.sort((a, b) => {
      const aType = a.team_type || '';
      const bType = b.team_type || '';
      if (aType !== bType) return aType.localeCompare(bType);
      return (a.name || '').localeCompare(b.name || '');
    });

    return options;
  }, [professionals, profFilter]);

  useEffect(() => {
    if (teamFilter === 'all' || teamFilter === 'none') return;
    const teamId = Number(teamFilter);
    const exists = teamOptions.some(t => t.id === teamId);
    if (!exists) setTeamFilter('all');
  }, [teamOptions, teamFilter]);

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

  const leadStats = useMemo(() => {
    const total = opportunityData.length;
    const withAssignments = opportunityData.filter(isLeadAssigned).length;
    const fullyAssigned = opportunityData.filter(isLeadFullyAssigned).length;
    const partialAssigned = Math.max(withAssignments - fullyAssigned, 0);
    return { total, withAssignments, fullyAssigned, partialAssigned };
  }, [opportunityData]);

  const filteredLeads = useMemo(() => {
    let rows = opportunityData;

    if (leadSearch.trim()) {
      const q = leadSearch.trim().toLowerCase();
      rows = rows.filter((opp) => (
        (opp.nome || '').toLowerCase().includes(q) ||
        (opp.email || '').toLowerCase().includes(q) ||
        (opp.lead_phone || '').toLowerCase().includes(q) ||
        (opp.health_manager_email || '').toLowerCase().includes(q) ||
        (opp.pacchetto || '').toLowerCase().includes(q) ||
        (opp.storia || '').toLowerCase().includes(q)
      ));
    }

    if (leadFilter === 'unassigned') rows = rows.filter((opp) => !isLeadAssigned(opp));
    if (leadFilter === 'assigned') rows = rows.filter(isLeadAssigned);
    if (leadFilter === 'partial') rows = rows.filter((opp) => isLeadAssigned(opp) && !isLeadFullyAssigned(opp));
    if (leadFilter === 'complete') rows = rows.filter(isLeadFullyAssigned);

    return rows;
  }, [opportunityData, leadFilter, leadSearch]);

  const hasStoredAnalysis = useMemo(() => {
    if (!activeRoleFlow || !selectedOpportunity?.ai_analysis) return false;
    const existing = selectedOpportunity.ai_analysis;
    const stored = getStoredAnalysisForRole(existing, activeRoleFlow);
    return !!(stored?.summary || stored?.criteria?.length);
  }, [activeRoleFlow, selectedOpportunity]);

  return (
    <>
      <ToastContainer position="top-end" className="p-3" style={{ zIndex: 2000 }}>
        <Toast bg={toastState.variant} onClose={() => setToastState(prev => ({ ...prev, show: false }))} show={toastState.show} delay={2500} autohide>
          <Toast.Body className="text-white d-flex align-items-center gap-2">
            <i className={toastState.variant === 'success' ? 'ri-checkbox-circle-line' : 'ri-error-warning-line'}></i>
            {toastState.message}
          </Toast.Body>
        </Toast>
      </ToastContainer>

      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1">
            <i className="ri-robot-line me-2 text-primary"></i>
            Assegnazioni AI
          </h4>
          <p className="text-muted mb-0">Gestione intelligente lead e professionisti</p>
        </div>
        <Button variant="outline-primary" onClick={() => {
            if (activeTab === 'webhook-data') fetchOpportunityData();
            if (activeTab === 'assignments') fetchAssignments();
            if (activeTab === 'professionals') fetchProfessionalsAndSchema();
        }} disabled={loading || loadingOpportunity || loadingProfs}>
          <i className={`ri-refresh-line me-1 ${(loading || loadingOpportunity || loadingProfs) ? 'spin' : ''}`}></i>
          Aggiorna
        </Button>
      </div>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          <i className="ri-error-warning-line me-2"></i>{error}
        </Alert>
      )}

      <Tabs activeKey={activeTab} onSelect={(k) => setActiveTab(k)} className="mb-4">
        
        {/* TAB 1: Lead da Assegnare (Webhook) */}
        <Tab eventKey="webhook-data" title={<><i className="ri-inbox-archive-line me-2"></i>Lead da Assegnare ({opportunityData.length})</>}>
          <div className="d-flex flex-wrap align-items-center justify-content-between mb-3 gap-3">
            <ButtonGroup>
              <Button variant={leadFilter === 'all' ? 'primary' : 'outline-primary'} onClick={() => setLeadFilter('all')}>Tutte</Button>
              <Button variant={leadFilter === 'unassigned' ? 'primary' : 'outline-primary'} onClick={() => setLeadFilter('unassigned')}>Da assegnare</Button>
              <Button variant={leadFilter === 'assigned' ? 'primary' : 'outline-primary'} onClick={() => setLeadFilter('assigned')}>Con assegnazioni</Button>
              <Button variant={leadFilter === 'partial' ? 'primary' : 'outline-primary'} onClick={() => setLeadFilter('partial')}>Parziali</Button>
              <Button variant={leadFilter === 'complete' ? 'primary' : 'outline-primary'} onClick={() => setLeadFilter('complete')}>Completate</Button>
            </ButtonGroup>

            <Form.Control
              type="search"
              placeholder="Cerca lead, pacchetto o note..."
              value={leadSearch}
              onChange={(e) => setLeadSearch(e.target.value)}
              style={{ maxWidth: '420px', width: '100%' }}
            />
          </div>

          {opportunityData.length > 0 && (
            <Row className="g-3 mb-3" data-tour="stats">
              {[
                { label: 'Lead Totali', value: leadStats.total, icon: 'ri-inbox-archive-line', bg: 'primary' },
                { label: 'Con Assegnazioni', value: leadStats.withAssignments, icon: 'ri-user-follow-line', bg: 'success' },
                { label: 'Parziali', value: leadStats.partialAssigned, icon: 'ri-alert-line', bg: 'warning' },
                { label: 'Completate', value: leadStats.fullyAssigned, icon: 'ri-check-double-line', customBg: '#64748b' },
              ].map((stat, idx) => (
                <Col key={idx} md={3} sm={6}>
                  <div
                    className={`card border-0 shadow-sm ${stat.bg ? `bg-${stat.bg}` : ''}`}
                    style={stat.customBg ? { backgroundColor: stat.customBg } : {}}
                  >
                    <div className="card-body py-3">
                      <div className="d-flex align-items-center justify-content-between">
                        <div>
                          <h3 className="text-white mb-0 fw-bold">{stat.value}</h3>
                          <span className="text-white opacity-75 small">{stat.label}</span>
                        </div>
                        <div
                          className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center"
                          style={{ width: '48px', height: '48px' }}
                        >
                          <i className={`${stat.icon} text-white fs-4`}></i>
                        </div>
                      </div>
                    </div>
                  </div>
                </Col>
              ))}
            </Row>
          )}

          <Card className="border-0 shadow-sm bg-white">
            <Card.Body className="p-0">
              {loadingOpportunity && opportunityData.length === 0 ? (
                <div className="text-center py-5">
                  <Spinner animation="border" variant="primary" />
                  <p className="text-muted mt-2">Caricamento lead...</p>
                </div>
              ) : opportunityData.length === 0 ? (
                <div className="text-center py-5">
                  <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3" style={{width: '80px', height: '80px'}}>
                    <i className="ri-checkbox-circle-line text-muted" style={{fontSize: '36px'}}></i>
                  </div>
                  <h5 className="text-muted">Nessuna lead in attesa</h5>
                  <p className="text-muted">I nuovi contatti da GHL appariranno qui.</p>
                  <div className="bg-light rounded p-3 mx-auto mt-3" style={{ maxWidth: '520px' }}>
                    <p className="small mb-2"><strong>Endpoint webhook:</strong></p>
                    <code>POST {webhookUrls.opportunity_data_url || 'Caricamento...'}</code>
                    <p className="small mt-2 mb-0 text-muted">Campi attesi: nome, storia, pacchetto, durata, email, telefono, health_manager_email</p>
                  </div>
                </div>
              ) : filteredLeads.length === 0 ? (
                <div className="text-center py-5 text-muted">Nessuna lead trovata con i filtri attivi</div>
              ) : (
                (() => {
                  const renderLeadTable = (rows) => (
                    <Table responsive hover className="mb-0 bg-white">
                      <thead className="bg-light">
                        <tr>
                          <th>Cliente</th>
                          <th>Pacchetto/Info</th>
                          <th>Health Manager Email</th>
                          <th>Check 1</th>
                          <th>Check 2</th>
                          <th>Assegnazioni</th>
                          <th>Ricevuto</th>
                          <th className="text-end">Azioni</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((opp) => {
                          const flags = getLeadAssignmentFlags(opp);
                          const requirements = getLeadRequirements(opp);
                          const requiredCount = getLeadRequiredRolesCount(opp);
                          const assignedCount = getLeadAssignedCount(opp);
                          const statusKey = assignedCount === 0 ? 'unassigned' : (assignedCount === requiredCount ? 'complete' : 'partial');
                          const status = LEAD_STATUS_STYLES[statusKey];
                          const checks = initialChecksByLead[opp.cliente_id] || {};

                          return (
                            <tr key={opp.id}>
                              <td>
                                <div className="fw-bold">{opp.nome}</div>
                                {opp.storia && <small className="text-muted d-block text-truncate" style={{maxWidth: '300px'}}>{opp.storia}</small>}
                                {opp.email && (
                                  <small className="d-block">
                                    <a href={`mailto:${opp.email}`}>{opp.email}</a>
                                  </small>
                                )}
                                {opp.lead_phone && (
                                  <small className="d-block">
                                    <a href={`tel:${opp.lead_phone}`}>{opp.lead_phone}</a>
                                  </small>
                                )}
                              </td>
                              <td>
                                <Badge bg="info" className="me-1">{opp.pacchetto}</Badge>
                                <span className="small text-muted">{opp.durata} gg</span>
                              </td>
                              <td>
                                {opp.health_manager_email ? (
                                  <small><a href={`mailto:${opp.health_manager_email}`}>{opp.health_manager_email}</a></small>
                                ) : (
                                  <small className="text-muted">-</small>
                                )}
                              </td>
                              <td>{renderInitialCheckCell(opp.cliente_id, 1, checks.check_1)}</td>
                              <td>{renderInitialCheckCell(opp.cliente_id, 2, checks.check_2)}</td>
                              <td>
                                <div className="d-flex align-items-center flex-wrap gap-2">
                                  <div className="d-flex gap-1">
                                    <Badge bg={requirements.nutrition ? (flags.nutrition ? 'success' : 'light') : 'secondary'} text={requirements.nutrition ? (flags.nutrition ? 'white' : 'dark') : 'white'} className="border" title={requirements.nutrition ? 'Nutrizione richiesta' : 'Nutrizione non prevista dal pacchetto'}>N</Badge>
                                    <Badge bg={requirements.coach ? (flags.coach ? 'success' : 'light') : 'secondary'} text={requirements.coach ? (flags.coach ? 'white' : 'dark') : 'white'} className="border" title={requirements.coach ? 'Coach richiesto' : 'Coach non previsto dal pacchetto'}>C</Badge>
                                    <Badge bg={requirements.psychology ? (flags.psychology ? 'success' : 'light') : 'secondary'} text={requirements.psychology ? (flags.psychology ? 'white' : 'dark') : 'white'} className="border" title={requirements.psychology ? 'Psicologia richiesta' : 'Psicologia non prevista dal pacchetto'}>P</Badge>
                                  </div>
                                  <Badge bg={status.bg} text={status.text} className="border">{status.label}</Badge>
                                  <span className="small text-muted">{assignedCount}/{requiredCount}</span>
                                </div>
                              </td>
                              <td><small>{formatDate(opp.received_at)}</small></td>
                              <td className="text-end">
                                <Button variant="outline-primary" size="sm" onClick={() => { setSelectedOpportunity(opp); setShowOpportunityModal(true); }}>
                                  <i className="ri-eye-line me-1"></i>Dettagli
                                </Button>
                                <Button variant="gradient-ai" size="sm" className="ms-2 shadow-sm" onClick={() => handleOpenAIModal(opp)}>
                                  <i className="ri-sparkling-fill me-1"></i>AI Match
                                </Button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </Table>
                  );

                  if (leadFilter !== 'all') {
                    return renderLeadTable(filteredLeads);
                  }

                  const groups = [
                    { key: 'unassigned', title: LEAD_STATUS_STYLES.unassigned.label, badge: LEAD_STATUS_STYLES.unassigned, rows: filteredLeads.filter((opp) => !isLeadAssigned(opp)) },
                    { key: 'partial', title: LEAD_STATUS_STYLES.partial.label, badge: LEAD_STATUS_STYLES.partial, rows: filteredLeads.filter((opp) => isLeadAssigned(opp) && !isLeadFullyAssigned(opp)) },
                    { key: 'complete', title: LEAD_STATUS_STYLES.complete.label, badge: LEAD_STATUS_STYLES.complete, rows: filteredLeads.filter(isLeadFullyAssigned) },
                  ].filter(group => group.rows.length > 0);

                  return (
                    <div className="p-3">
                      {groups.map((group, index) => (
                        <div key={group.key} className={index > 0 ? 'mt-4' : ''}>
                          <div className="fw-semibold text-muted mb-2 d-flex align-items-center gap-2">
                            <span>{group.title}</span>
                            <Badge bg={group.badge.bg} text={group.badge.text} className="border">
                              {group.rows.length}
                            </Badge>
                          </div>
                          <div className="border rounded bg-white">
                            {renderLeadTable(group.rows)}
                          </div>
                        </div>
                      ))}
                    </div>
                  );
                })()
              )}
            </Card.Body>
          </Card>
        </Tab>

        {/* TAB 2: Professionisti (Criteri) */}
        <Tab eventKey="professionals" title={<><i className="ri-team-line me-2"></i>Professionisti</>}>
            <div className="d-flex flex-wrap align-items-center justify-content-between mb-3 gap-3">
                <ButtonGroup>
                    <Button variant={profFilter === 'all' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('all')}>Tutti</Button>
                    <Button variant={profFilter === 'nutrizione' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('nutrizione')}>Nutrizione</Button>
                    <Button variant={profFilter === 'coach' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('coach')}>Coach</Button>
                    <Button variant={profFilter === 'psicologia' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('psicologia')}>Psicologia</Button>
                </ButtonGroup>
                
                <div className="d-flex flex-wrap gap-2" style={{ maxWidth: '520px', width: '100%' }}>
                    <Form.Select
                        value={teamFilter}
                        onChange={(e) => setTeamFilter(e.target.value)}
                        style={{ minWidth: '200px', flex: 1 }}
                    >
                        <option value="all">Tutti i team</option>
                        {teamOptions.map(team => (
                            <option key={team.id} value={team.id}>
                                {team.team_type ? `${team.team_type.charAt(0).toUpperCase() + team.team_type.slice(1)} - ` : ''}{team.name}
                            </option>
                        ))}
                    </Form.Select>
                    <Form.Control 
                        type="search" 
                        placeholder="Cerca professionista..." 
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        style={{ minWidth: '200px', flex: 1 }}
                    />
                </div>
            </div>

            {loadingProfs ? (
                <div className="text-center py-5"><Spinner animation="border" /></div>
            ) : (
                <Card className="border-0 shadow-sm">
                    <Card.Body className="p-0">
                        {(() => {
                            const filtered = getFilteredProfessionals();

                            const renderTable = (rows) => (
                                <Table responsive hover className="mb-0 align-middle">
                                    <thead className="bg-light">
                                        <tr>
                                            <th style={{width: '30%'}}>Professionista</th>
                                            <th style={{width: '25%'}}>Team</th>
                                            <th>Stato</th>
                                            <th style={{width: '40%'}}>Criteri Specializzazione</th>
                                            <th className="text-end">Azioni</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rows.map(prof => (
                                            <tr key={prof.id}>
                                                <td>
                                                    <div className="d-flex align-items-center">
                                                        <img 
                                                            src={prof.avatar_url} 
                                                            alt={prof.name} 
                                                            className="rounded-circle me-3" 
                                                            style={{width: '40px', height: '40px', objectFit: 'cover'}} 
                                                        />
                                                        <div>
                                                            <div className="fw-bold">{prof.name}</div>
                                                            <small className="text-muted">{DEPT_LABELS[prof.department_id] || 'N/A'}</small>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td>
                                                    {prof.teams && prof.teams.length > 0 ? (
                                                        <div className="d-flex flex-wrap gap-1">
                                                            {prof.teams.map(team => (
                                                                <Badge
                                                                    key={team.id}
                                                                    bg={TEAM_TYPE_COLORS[team.team_type] || 'secondary'}
                                                                    className="text-white"
                                                                    style={{ fontSize: '11px' }}
                                                                >
                                                                    {team.name}
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        <span className="text-muted small">Senza team</span>
                                                    )}
                                                </td>
                                                <td>
                                                    {prof.is_available ? 
                                                        <Badge bg="success-subtle" text="success" className="border border-success-subtle"><i className="ri-check-line me-1"></i>Disponibile</Badge> : 
                                                        <Badge bg="secondary-subtle" text="secondary" className="border border-secondary-subtle"><i className="ri-close-line me-1"></i>Non disp.</Badge>
                                                    }
                                                </td>
                                                <td>
                                                    <div className="d-flex flex-wrap gap-1">
                                                        {Object.entries(prof.criteria || {}).filter(([, v]) => v).slice(0, 5).map(([k]) => (
                                                            <Badge bg="light" text="dark" className="border" key={k} style={{fontSize: '11px'}}>{k}</Badge>
                                                        ))}
                                                        {Object.entries(prof.criteria || {}).filter(([, v]) => v).length > 5 && (
                                                            <Badge bg="light" text="muted" className="border" style={{fontSize: '11px'}}>+{Object.entries(prof.criteria || {}).filter(([, v]) => v).length - 5} altri</Badge>
                                                        )}
                                                        {Object.values(prof.criteria || {}).filter(v => v).length === 0 && <span className="text-muted small">-</span>}
                                                    </div>
                                                </td>
                                                <td className="text-end">
                                                    <Button variant="outline-primary" size="sm" onClick={() => handleEditCriteria(prof)}>
                                                        <i className="ri-settings-3-line"></i>
                                                    </Button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </Table>
                            );

                            if (!showTeamGrouping) {
                                if (filtered.length === 0) {
                                    return (
                                        <Table responsive className="mb-0 align-middle">
                                            <tbody>
                                                <tr>
                                                    <td colSpan="5" className="text-center py-4 text-muted">
                                                        Nessun professionista trovato
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </Table>
                                    );
                                }
                                return renderTable(filtered);
                            }

                            const groups = [];
                            teamOptions.forEach(team => {
                                const members = filtered.filter(p => (p.teams || []).some(t => t.id === team.id));
                                if (members.length > 0) {
                                    groups.push({
                                        key: `team-${team.id}`,
                                        title: team.team_type ? `${team.team_type.charAt(0).toUpperCase() + team.team_type.slice(1)} - ${team.name}` : team.name,
                                        rows: members
                                    });
                                }
                            });

                            // Aggiunto: Gestione professionisti senza team
                            const noTeamMembers = filtered.filter(p => !p.teams || p.teams.length === 0);
                            if (noTeamMembers.length > 0) {
                                groups.push({
                                    key: 'no-team',
                                    title: 'Senza Team / Da assegnare',
                                    rows: noTeamMembers
                                });
                            }

                            if (groups.length === 0) {
                                return (
                                    <Table responsive className="mb-0 align-middle">
                                        <tbody>
                                            <tr>
                                                <td colSpan="5" className="text-center py-4 text-muted">
                                                    Nessun professionista trovato
                                                </td>
                                            </tr>
                                        </tbody>
                                    </Table>
                                );
                            }

                            return (
                                <div className="p-3">
                                    {groups.map((group, index) => (
                                        <div key={group.key} className={index > 0 ? 'mt-4' : ''}>
                                            <div className="fw-semibold text-muted mb-2">{group.title}</div>
                                            <div className="border rounded">
                                                {renderTable(group.rows)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            );
                        })()}
                    </Card.Body>
                </Card>
            )}
        </Tab>

        {/* TAB 3: Assegnazioni Completate/Storico */}
        <Tab eventKey="assignments" title={<><i className="ri-file-history-line me-2"></i>Storico Assegnazioni</>}>
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

      {/* MODAL EDIT CRITERIA */}
      <Modal show={showProfModal} onHide={() => setShowProfModal(false)} size="lg">
        <Modal.Header closeButton>
            <Modal.Title>Modifica Criteri: {editingProf?.name}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
            {editingProf && (
                <>
                    <div className="rounded-3 p-3 mb-3" style={{ background: 'linear-gradient(135deg, #f0f7ff 0%, #e8f5ff 100%)', border: '1px solid #d6e9ff' }}>
                        <div className="d-flex align-items-center gap-2 mb-1">
                            <div className="rounded-circle d-flex align-items-center justify-content-center" style={{ width: 36, height: 36, background: '#fff', border: '1px solid #d6e9ff' }}>
                                <i className="ri-magic-line text-primary"></i>
                            </div>
                            <div>
                                <div className="fw-semibold mb-0">Criteri per {DEPT_LABELS[editingProf.department_id]}</div>
                                <div className="text-muted small">Servono all'AI per proporre il professionista giusto.</div>
                            </div>
                        </div>
                        {criteriaStatus && criteriaStatus.type === 'error' && (
                            <div className="mt-2 d-inline-flex align-items-center gap-2 px-3 py-2 rounded" style={{ background: '#ffe8e8', border: '1px solid #ffc6c6' }}>
                                <i className="ri-error-warning-line text-danger"></i>
                                <span className="text-danger small">{criteriaStatus.message}</span>
                            </div>
                        )}
                    </div>
                    
                    {(() => {
                        const roleKey = DEPT_ROLE_MAP[editingProf.department_id];
                        const criteriaList = criteriaSchema[roleKey] || [];
                        
                        if (criteriaList.length === 0) return <Alert variant="warning">Nessuno schema criteri trovato per questo ruolo.</Alert>;

                        const selectedCount = criteriaList.filter(c => tempCriteria[c]).length;

                        return (
                            <div className="d-flex flex-column gap-3">
                                <div className="d-flex flex-wrap align-items-center justify-content-between gap-2">
                                    <div className="fw-semibold">
                                        Criteri disponibili: {criteriaList.length} · Selezionati: {selectedCount}
                                    </div>
                                    <div className="d-flex gap-2">
                                        <Button size="sm" variant="outline-secondary" onClick={() => toggleAllCriteria(criteriaList, false)}>
                                            <i className="ri-eraser-line me-1"></i>Deseleziona tutto
                                        </Button>
                                        <Button size="sm" variant="outline-primary" onClick={() => toggleAllCriteria(criteriaList, true)}>
                                            <i className="ri-check-double-line me-1"></i>Seleziona tutto
                                        </Button>
                                    </div>
                                </div>

                                <div className="d-grid" style={{gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '10px'}}>
                                    {criteriaList.map(crit => {
                                        const active = !!tempCriteria[crit];
                                        return (
                                            <Button
                                                key={crit}
                                                variant={active ? 'primary' : 'outline-secondary'}
                                                className="d-flex align-items-center justify-content-between"
                                                onClick={() => toggleCriterion(crit)}
                                            >
                                                <span className="text-start">{crit}</span>
                                                {active ? <i className="ri-check-line ms-2"></i> : <i className="ri-add-line ms-2"></i>}
                                            </Button>
                                        );
                                    })}
                                </div>
                            </div>
                        );
                    })()}
                </>
            )}
        </Modal.Body>
        <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowProfModal(false)}>Annulla</Button>
            <Button variant="primary" onClick={handleSaveCriteria}>Salva Modifiche</Button>
        </Modal.Footer>
      </Modal>
      
      {/* Existing Opportunity Modal */}
      <Modal show={showOpportunityModal} onHide={() => setShowOpportunityModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Dettagli Lead</Modal.Title>
        </Modal.Header>
        <Modal.Body>
           {selectedOpportunity && (
               <div>
                   <div className="d-flex justify-content-between align-items-start mb-3">
                       <div>
                           <h4 className="mb-1">{selectedOpportunity.nome}</h4>
                           <div className="text-muted"><i className="ri-time-line me-1"></i>{formatDate(selectedOpportunity.received_at)}</div>
                       </div>
                       <Badge bg="info" className="fs-6">{selectedOpportunity.pacchetto}</Badge>
                   </div>
                   
                   <Row className="g-3">
                       <Col md={12}>
                           <Card className="bg-light border-0">
                               <Card.Body className="py-2">
                                   <label className="text-uppercase text-muted small fw-bold mb-1">Contatti</label>
                                   <div>
                                       {selectedOpportunity.email ? (
                                           <a href={`mailto:${selectedOpportunity.email}`}>{selectedOpportunity.email}</a>
                                       ) : (
                                           <em className="text-muted">Non disponibile</em>
                                       )}
                                   </div>
                                   {selectedOpportunity.lead_phone && (
                                       <div className="mt-1">
                                           <a href={`tel:${selectedOpportunity.lead_phone}`}>{selectedOpportunity.lead_phone}</a>
                                       </div>
                                   )}
                               </Card.Body>
                           </Card>
                       </Col>
                       <Col md={12}>
                           <Card className="bg-light border-0">
                               <Card.Body>
                                   <label className="text-uppercase text-muted small fw-bold mb-2">Storia del Cliente</label>
                                   <div style={{whiteSpace: 'pre-wrap', maxHeight: '400px', overflowY: 'auto'}}>
                                       {selectedOpportunity.storia || <em className="text-muted">Nessuna storia fornita</em>}
                                   </div>
                               </Card.Body>
                           </Card>
                       </Col>
                   </Row>
               </div>
           )}
        </Modal.Body>
        <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowOpportunityModal(false)}>Chiudi</Button>
            <Button variant="success" onClick={() => {
                setShowOpportunityModal(false);
                handleOpenAIModal(selectedOpportunity);
            }}>
                <i className="ri-sparkling-fill me-1"></i> Apri Gestione AI
            </Button>
        </Modal.Footer>
      </Modal>

      <Modal show={showCheckResponseModal} onHide={() => setShowCheckResponseModal(false)} size="lg">
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
                  Lead: {selectedCheckResponse.lead_name || '-'} | Inviato: {formatDate(selectedCheckResponse.submitted_at)}
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

      {/* AI ASSIGNMENT MODAL */}
      <Modal show={showAIModal} onHide={() => setShowAIModal(false)} size="xl" centered>
        <Modal.Header closeButton className="border-bottom-0 bg-light">
            <Modal.Title className="d-flex align-items-center">
                <i className="ri-robot-2-line me-2 text-success"></i>
                <span className="fw-bold">SuiteMind Assignment</span>
                {activeRoleFlow && (
                    <Badge bg="white" text="dark" className="ms-3 border shadow-sm fw-normal">
                        {activeRoleFlow === 'nutrition' && 'Nutrizione'}
                        {activeRoleFlow === 'coach' && 'Coaching'}
                        {activeRoleFlow === 'psychology' && 'Psicologia'}
                    </Badge>
                )}
            </Modal.Title>
        </Modal.Header>
        <Modal.Body className="bg-light p-0">
            {!activeRoleFlow ? (
                // SELEZIONE RUOLO
                <div className="py-4 px-3 mx-auto" style={{ maxWidth: '900px' }}>
                    <div className="text-center mb-4">
                        <h5 className="fw-bold mb-2">Scegli il percorso di assegnazione</h5>
                        <p className="text-muted small">Seleziona il professionista da assegnare a <strong>{selectedOpportunity?.nome}</strong>.<br/>L'IA analizzerà il profilo specificamente per il ruolo richiesto.</p>
                    </div>
                    {(() => {
                      const requirement = getLeadRequirements(selectedOpportunity);
                      const analysisFor = (role) => getStoredAnalysisForRole(selectedOpportunity?.ai_analysis, role);
                      const isRoleEnabled = (role) => !!requirement[role];
                      const analysisBadge = (role) => (
                        analysisFor(role) ? (
                          <span className="badge bg-success-subtle text-success border rounded-pill px-2 py-1">Analisi pronta</span>
                        ) : null
                      );
                      const analysisBtnLabel = (role) => (analysisFor(role) ? 'Usa Analisi' : 'Avvia Analisi');
                      const disabledStyle = { opacity: 0.45, cursor: 'not-allowed', filter: 'grayscale(0.35)' };
                      return (
                    <Row className="g-3 justify-content-center">
                        <Col md={4}>
                            <Card className="border-0 shadow-sm hover-card text-center p-3 cursor-pointer" onClick={() => isRoleEnabled('nutrition') && handleSelectRoleFlow('nutrition')} style={isRoleEnabled('nutrition') ? {cursor: 'pointer', transition: 'transform 0.2s'} : disabledStyle} title={isRoleEnabled('nutrition') ? 'Nutrizione prevista nel pacchetto' : 'Nutrizione non prevista nel pacchetto'}>
                                <div className="mb-2 mx-auto bg-success-subtle rounded-circle d-flex align-items-center justify-content-center" style={{width: '60px', height: '60px'}}>
                                    <i className="ri-restaurant-line fs-3 text-success"></i>
                                </div>
                                <h6 className="fw-bold mb-2">Nutrizionista</h6>
                                <p className="text-muted extra-small mb-3" style={{fontSize: '0.8rem'}}>Abitudini alimentari, obiettivi di peso e preferenze dietetiche.</p>
                                {!isRoleEnabled('nutrition') && <span className="badge bg-secondary-subtle text-secondary border rounded-pill px-2 py-1">Non previsto</span>}
                                {analysisBadge('nutrition')}
                                <Button variant="outline-success" disabled={!isRoleEnabled('nutrition')} className="rounded-pill w-100 border-0 fw-bold py-2 shadow-none mt-2" style={{fontSize: '0.85rem'}}>
                                  {analysisBtnLabel('nutrition')} <i className="ri-arrow-right-s-line ms-1"></i>
                                </Button>
                            </Card>
                        </Col>
                        
                        <Col md={4}>
                            <Card className="border-0 shadow-sm hover-card text-center p-3 cursor-pointer" onClick={() => isRoleEnabled('coach') && handleSelectRoleFlow('coach')} style={isRoleEnabled('coach') ? {cursor: 'pointer', transition: 'transform 0.2s'} : disabledStyle} title={isRoleEnabled('coach') ? 'Coach previsto nel pacchetto' : 'Coach non previsto nel pacchetto'}>
                                <div className="mb-2 mx-auto bg-primary-subtle rounded-circle d-flex align-items-center justify-content-center" style={{width: '60px', height: '60px'}}>
                                    <i className="ri-run-line fs-3 text-primary"></i>
                                </div>
                                <h6 className="fw-bold mb-2">Coach</h6>
                                <p className="text-muted extra-small mb-3" style={{fontSize: '0.8rem'}}>Livello fitness, obiettivi di allenamento e stile di vita.</p>
                                {!isRoleEnabled('coach') && <span className="badge bg-secondary-subtle text-secondary border rounded-pill px-2 py-1">Non previsto</span>}
                                {analysisBadge('coach')}
                                <Button variant="outline-primary" disabled={!isRoleEnabled('coach')} className="rounded-pill w-100 border-0 fw-bold py-2 shadow-none mt-2" style={{fontSize: '0.85rem'}}>
                                  {analysisBtnLabel('coach')} <i className="ri-arrow-right-s-line ms-1"></i>
                                </Button>
                            </Card>
                        </Col>
                        
                        <Col md={4}>
                            <Card className="border-0 shadow-sm hover-card text-center p-3 cursor-pointer" onClick={() => isRoleEnabled('psychology') && handleSelectRoleFlow('psychology')} style={isRoleEnabled('psychology') ? {cursor: 'pointer', transition: 'transform 0.2s'} : disabledStyle} title={isRoleEnabled('psychology') ? 'Psicologia prevista nel pacchetto' : 'Psicologia non prevista nel pacchetto'}>
                                <div className="mb-2 mx-auto bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center" style={{width: '60px', height: '60px'}}>
                                    <i className="ri-mental-health-line fs-3 text-warning" style={{color: '#d97706'}}></i>
                                </div>
                                <h6 className="fw-bold mb-2">Psicologo</h6>
                                <p className="text-muted extra-small mb-3" style={{fontSize: '0.8rem'}}>Aspetti emotivi, relazione con il cibo e gestione stress.</p>
                                {!isRoleEnabled('psychology') && <span className="badge bg-secondary-subtle text-secondary border rounded-pill px-2 py-1">Non previsto</span>}
                                {analysisBadge('psychology')}
                                <Button variant="outline-warning" disabled={!isRoleEnabled('psychology')} className="rounded-pill w-100 border-0 fw-bold py-2 shadow-none text-dark mt-2" style={{fontSize: '0.85rem'}}>
                                  {analysisBtnLabel('psychology')} <i className="ri-arrow-right-s-line ms-1"></i>
                                </Button>
                            </Card>
                        </Col>
                    </Row>
                      );
                    })()}
                </div>
            ) : assignmentSuccess ? (
                // SCHERMATA DI SUCCESSO
                <div className="py-5 px-4 text-center d-flex flex-column align-items-center justify-content-center" style={{ minHeight: '500px' }}>
                    <div className="success-checkmark mb-4">
                        <div className="check-icon bg-success text-white rounded-circle d-flex align-items-center justify-content-center shadow-lg" style={{ width: '100px', height: '100px' }}>
                            <i className="ri-checkbox-circle-fill" style={{ fontSize: '60px' }}></i>
                        </div>
                    </div>
                    
                    <h2 className="fw-bold mb-2">Assegnazione Completata!</h2>
                    <p className="text-muted fs-5 mb-4">Hai assegnato correttamente <strong>{lastAssignedProf?.name}</strong> a <strong>{selectedOpportunity?.nome}</strong>.</p>
                    
                    <div className="bg-white p-3 rounded border shadow-sm mb-5 d-flex align-items-center" style={{ minWidth: '300px' }}>
                        <div className="bg-success-subtle p-2 rounded-circle me-3">
                            <i className="ri-user-follow-line text-success fs-4"></i>
                        </div>
                        <div className="text-start">
                            <div className="small text-muted text-uppercase fw-bold">Ruolo</div>
                            <div className="fw-bold fs-6">
                                {activeRoleFlow === 'nutrition' && 'Nutrizionista'}
                                {activeRoleFlow === 'coach' && 'Coach'}
                                {activeRoleFlow === 'psychology' && 'Psicologo'}
                            </div>
                        </div>
                    </div>

                    <div className="d-flex gap-3">
                        <Button 
                            variant="outline-secondary" 
                            className="px-4 rounded-pill"
                            onClick={() => {
                                setAssignmentSuccess(false);
                                setActiveRoleFlow(null);
                            }}
                        >
                            Torna ai Ruoli
                        </Button>
                        <Button 
                            variant="success" 
                            className="px-5 rounded-pill shadow-sm fw-bold"
                            onClick={() => setShowAIModal(false)}
                        >
                            Chiudi Gestione
                        </Button>
                    </div>
                </div>
            ) : (
                // FLUSSO ATTIVO (Analisi + Match)
                <div className="d-flex flex-column" style={{ minHeight: '600px', maxHeight: '80vh' }}>
                    <div className="px-4 py-2 bg-white border-bottom d-flex align-items-center sticky-top" style={{zIndex: 10}}>
                        <Button variant="link" className="text-decoration-none text-muted p-0 me-3" onClick={() => setActiveRoleFlow(null)}>
                            <i className="ri-arrow-left-line me-1"></i>Indietro
                        </Button>
                        <small className="text-muted">Analisi in corso per: <strong>{selectedOpportunity?.nome}</strong></small>
                    </div>

                    <div className="flex-grow-1 overflow-auto">
                        <Row className="g-0 m-0">
                            {/* LEFT: Analysis & Story */}
                            <Col lg={4} className="border-end bg-white custom-scrollbar p-0">
                                <div className="p-4">
                                <Card className="border-0 shadow-sm mb-4">
                                    <Card.Header className="bg-white py-3 border-bottom d-flex align-items-center">
                                        <i className="ri-file-search-line fs-5 me-2 text-success"></i>
                                        <span className="fw-bold text-uppercase small">Analisi AI</span>
                                    </Card.Header>
                                    <Card.Body className="p-4">
                                    <div className="mb-4">
                                        <h6 className="fw-bold text-muted small text-uppercase mb-2">Storia del Cliente</h6>
                                        <div className="bg-light border rounded p-3 text-muted" style={{ fontSize: '0.85rem', whiteSpace: 'pre-wrap', maxHeight: '150px', overflowY: 'auto' }}>
                                            {selectedOpportunity?.storia || <em>Nessuna storia presente</em>}
                                        </div>
                                    </div>

                                    {!aiAnalysis ? (
                                        <div className="text-center py-5">
                                            {aiLoading ? (
                                                <>
                                                    <Spinner animation="border" variant="success" className="mb-3" />
                                                    <p className="nm-0 text-muted small">Analisi in corso...</p>
                                                </>
                                            ) : hasStoredAnalysis ? (
                                                <>
                                                    <div className="bg-success-subtle rounded-circle d-inline-flex align-items-center justify-content-center mb-2" style={{width: '64px', height: '64px'}}>
                                                        <i className="ri-check-line text-success fs-3"></i>
                                                    </div>
                                                    <p className="small text-muted mb-3">Analisi già disponibile per questo ruolo.</p>
                                                    <Button
                                                        variant="outline-secondary"
                                                        size="sm"
                                                        className="w-100 rounded-pill"
                                                        onClick={() => handleRunAIAnalysis()}
                                                        disabled={aiLoading}
                                                    >
                                                        <i className="ri-refresh-line me-1"></i> Aggiorna Analisi
                                                    </Button>
                                                </>
                                            ) : (
                                                <>
                                                    <i className="ri-sparkling-line fs-1 text-success opacity-50 mb-2 d-block"></i>
                                                    <p className="small text-muted mb-3">Pronto per l'analisi</p>
                                                    <Button 
                                                        variant="success" 
                                                        size="sm" 
                                                        className="w-100 rounded-pill"
                                                        onClick={() => handleRunAIAnalysis()}
                                                        disabled={aiLoading}
                                                    >
                                                        Avvia Analisi
                                                    </Button>
                                                </>
                                            )}
                                        </div>
                                    ) : (
                                        <>
                                            <div className="mb-4">
                                                <h6 className="fw-bold text-success small text-uppercase">Sintesi</h6>
                                                <div className="text-dark bg-white p-3 rounded border border-success-subtle shadow-sm" style={{ fontSize: '0.9rem', lineHeight: '1.6' }}>
                                                    {aiAnalysis.summary}
                                                </div>
                                            </div>
                                            
                                            <div className="mb-4">
                                                <h6 className="fw-bold text-success small text-uppercase mb-2">Match Criteria</h6>
                                                <div className="d-flex flex-wrap gap-1">
                                                    {(aiAnalysis.criteria && aiAnalysis.criteria.length > 0) ? (
                                                        aiAnalysis.criteria.map(tag => (
                                                            <Badge bg="success-subtle" text="success" key={tag} className="border border-success-subtle py-2 px-3 rounded-pill" style={{fontSize: '0.75rem'}}>
                                                                {tag}
                                                            </Badge>
                                                        ))
                                                    ) : (
                                                        <span className="text-muted small fst-italic">Nessun criterio specifico estratto</span>
                                                    )}
                                                </div>
                                            </div>
                                            
                                            {aiAnalysis.suggested_focus && aiAnalysis.suggested_focus.length > 0 && (
                                            <div>
                                                <h6 className="fw-bold text-success small text-uppercase mb-2">Focus Suggerito</h6>
                                                {aiAnalysis.suggested_focus.map((focus, i) => (
                                                    <div key={i} className="d-flex align-items-start mb-2 small text-muted">
                                                        <i className="ri-check-line text-success me-2 mt-1"></i>
                                                        <span>{focus}</span>
                                                    </div>
                                                ))}
                                            </div>
                                            )}

                                            <div className="mt-4 pt-3 border-top">
                                                <Button 
                                                    variant="outline-secondary" 
                                                    size="sm" 
                                                    className="w-100"
                                                    onClick={() => handleRunAIAnalysis()}
                                                    disabled={aiLoading}
                                                >
                                                    <i className="ri-refresh-line me-1"></i> Aggiorna Analisi
                                                </Button>
                                            </div>
                                        </>
                                    )}
                                    </Card.Body>
                                </Card>
                                </div>
                            </Col>
                            
                            {/* RIGHT: Matching & Selection */}
                            <Col lg={8} className="bg-light custom-scrollbar">
                                <div className="p-4 overflow-auto">
                                {/* Contextual Matching UI based on role */}
                                
                                {/* NUTRITION SECTION */}
                                {(activeRoleFlow === 'nutrition') && (
                                <div className="p-4 rounded mb-4 shadow-sm bg-white border border-success-subtle">
                                    <div className="d-flex align-items-center justify-content-between mb-4">
                                        <h5 className="fw-bold text-success mb-0 d-flex align-items-center">
                                            <div className="bg-success-subtle rounded-circle p-2 me-3 d-flex align-items-center justify-content-center" style={{width: 40, height: 40}}>
                                                <i className="ri-restaurant-line fs-5 text-success"></i>
                                            </div>
                                            Assegnazione Nutrizionista
                                        </h5>
                                        {aiAnalysis && <Badge bg="success" className="px-3 py-2 rounded-pill shadow-sm">AI MATCHED</Badge>}
                                    </div>

                                    <Row className="g-3 align-items-end">
                                        <Col md={12} className="mb-3">
                                            <label className="small text-muted mb-2 fw-bold text-uppercase">Professionista Consigliato</label>
                                            <Form.Select 
                                                size="lg"
                                                value={selectedMatches.nutrition} 
                                                onChange={(e) => {
                                                    setSelectedMatches({...selectedMatches, nutrition: e.target.value});
                                                    setHasNewInteraction(true);
                                                }}
                                                className="border-success shadow-sm form-select-lg"
                                            >
                                                <option value="">-- Seleziona un Nutrizionista --</option>
                                                {aiMatches?.nutrizione?.map(p => (
                                                    <option key={p.id} value={p.id}>
                                                        {p.name} (Match: {p.score}%)
                                                    </option>
                                                ))}
                                                {aiMatches?.nutrizione?.length > 0 && <option disabled>──────────</option>}
                                                {professionals.filter(p => !aiMatches?.nutrizione?.find(m => m.id === p.id) && (DEPT_ROLE_MAP[p.department_id] === 'nutrizione')).map(p => (
                                                    <option key={p.id} value={p.id}>{p.name}</option>
                                                ))}
                                            </Form.Select>
                                        </Col>
                                    </Row>

                                    {selectedMatches.nutrition && (aiMatches?.nutrizione?.find(p => p.id == selectedMatches.nutrition)?.match_reasons?.length > 0) && (
                                        <Alert variant="success" className="mt-3 border-0 bg-success-subtle text-success d-flex align-items-center">
                                            <i className="ri-magic-line fs-4 me-3"></i>
                                            <div>
                                                <strong>Ottima scelta!</strong><br/>
                                                <span className="small">Questo professionista è ideale per: {aiMatches.nutrizione.find(p => p.id == selectedMatches.nutrition).match_reasons?.join(', ')}</span>
                                            </div>
                                        </Alert>
                                    )}

                                    <div className="mt-4 pt-3 border-top d-flex justify-content-end">
                                        <Button 
                                            variant="success" 
                                            size="lg"
                                            className="px-5 fw-bold shadow-sm rounded-pill"
                                            onClick={() => handleConfirmAssignment('nutrition')}
                                            disabled={loading || !selectedMatches.nutrition || (!hasNewInteraction && isAlreadyAssigned('nutrition'))}
                                        >
                                            {loading && <Spinner size="sm" animation="border" className="me-2" />}
                                            Conferma Assegnazione <i className="ri-arrow-right-line ms-2"></i>
                                        </Button>
                                    </div>
                                </div>
                                )}

                                {/* COACH SECTION */}
                                {(activeRoleFlow === 'coach') && (
                                <div className="p-4 rounded mb-4 shadow-sm bg-white border border-primary-subtle">
                                    <div className="d-flex align-items-center justify-content-between mb-4">
                                        <h5 className="fw-bold text-primary mb-0 d-flex align-items-center">
                                            <div className="bg-primary-subtle rounded-circle p-2 me-3 d-flex align-items-center justify-content-center" style={{width: 40, height: 40}}>
                                                <i className="ri-run-line fs-5 text-primary"></i>
                                            </div>
                                            Assegnazione Coach
                                        </h5>
                                        {aiAnalysis && <Badge bg="primary" className="px-3 py-2 rounded-pill shadow-sm">AI MATCHED</Badge>}
                                    </div>

                                    <Row className="g-3 align-items-end">
                                        <Col md={12} className="mb-3">
                                            <label className="small text-muted mb-2 fw-bold text-uppercase">Professionista Consigliato</label>
                                            <Form.Select 
                                                 size="lg"
                                                value={selectedMatches.coach} 
                                                onChange={(e) => {
                                                    setSelectedMatches({...selectedMatches, coach: e.target.value});
                                                    setHasNewInteraction(true);
                                                }}
                                                className="border-primary shadow-sm form-select-lg"
                                            >
                                                <option value="">-- Seleziona un Coach --</option>
                                                {aiMatches?.coach?.map(p => (
                                                    <option key={p.id} value={p.id}>
                                                        {p.name} (Match: {p.score}%)
                                                    </option>
                                                ))}
                                                {aiMatches?.coach?.length > 0 && <option disabled>──────────</option>}
                                                {professionals.filter(p => !aiMatches?.coach?.find(m => m.id === p.id) && (DEPT_ROLE_MAP[p.department_id] === 'coach')).map(p => (
                                                    <option key={p.id} value={p.id}>{p.name}</option>
                                                ))}
                                            </Form.Select>
                                        </Col>
                                    </Row>

                                    {selectedMatches.coach && (aiMatches?.coach?.find(p => p.id == selectedMatches.coach)?.match_reasons?.length > 0) && (
                                        <Alert variant="primary" className="mt-3 border-0 bg-primary-subtle text-primary d-flex align-items-center">
                                            <i className="ri-magic-line fs-4 me-3"></i>
                                            <div>
                                                <strong>Ottima scelta!</strong><br/>
                                                <span className="small">Questo professionista è ideale per: {aiMatches.coach.find(p => p.id == selectedMatches.coach).match_reasons?.join(', ')}</span>
                                            </div>
                                        </Alert>
                                    )}

                                    <div className="mt-4 pt-3 border-top d-flex justify-content-end">
                                        <Button 
                                            variant="success" 
                                            size="lg"
                                            className="px-5 fw-bold shadow-sm rounded-pill"
                                            onClick={() => handleConfirmAssignment('coach')}
                                            disabled={loading || !selectedMatches.coach || (!hasNewInteraction && isAlreadyAssigned('coach'))}
                                        >
                                            {loading && <Spinner size="sm" animation="border" className="me-2" />}
                                            Conferma Assegnazione <i className="ri-arrow-right-line ms-2"></i>
                                        </Button>
                                    </div>
                                </div>
                                )}

                                {/* PSYCHOLOGY SECTION */}
                                {(activeRoleFlow === 'psychology') && (
                                <div className="p-4 rounded mb-4 shadow-sm bg-white border border-warning-subtle">
                                    <div className="d-flex align-items-center justify-content-between mb-4">
                                        <h5 className="fw-bold text-warning mb-0 d-flex align-items-center" style={{color: '#d97706'}}>
                                            <div className="bg-warning-subtle rounded-circle p-2 me-3 d-flex align-items-center justify-content-center" style={{width: 40, height: 40}}>
                                                <i className="ri-mental-health-line fs-5 text-warning" style={{color: '#d97706'}}></i>
                                            </div>
                                            Assegnazione Psicologo
                                        </h5>
                                        {aiAnalysis && <Badge bg="warning" className="px-3 py-2 rounded-pill shadow-sm text-white">AI MATCHED</Badge>}
                                    </div>

                                    <Row className="g-3 align-items-end">
                                        <Col md={12} className="mb-3">
                                            <label className="small text-muted mb-2 fw-bold text-uppercase">Professionista Consigliato</label>
                                            <Form.Select 
                                                 size="lg"
                                                value={selectedMatches.psychology} 
                                                onChange={(e) => {
                                                    setSelectedMatches({...selectedMatches, psychology: e.target.value});
                                                    setHasNewInteraction(true);
                                                }}
                                                className="border-warning shadow-sm form-select-lg"
                                            >
                                                <option value="">-- Seleziona uno Psicologo --</option>
                                                {aiMatches?.psicologia?.map(p => (
                                                    <option key={p.id} value={p.id}>
                                                        {p.name} (Match: {p.score}%)
                                                    </option>
                                                ))}
                                                {aiMatches?.psicologia?.length > 0 && <option disabled>──────────</option>}
                                                {professionals.filter(p => !aiMatches?.psicologia?.find(m => m.id === p.id) && (DEPT_ROLE_MAP[p.department_id] === 'psicologia')).map(p => (
                                                    <option key={p.id} value={p.id}>{p.name}</option>
                                                ))}
                                            </Form.Select>
                                        </Col>
                                    </Row>

                                    {selectedMatches.psychology && (aiMatches?.psicologia?.find(p => p.id == selectedMatches.psychology)?.match_reasons?.length > 0) && (
                                        <Alert variant="warning" className="mt-3 border-0 bg-warning-subtle text-warning d-flex align-items-center" style={{color: '#d97706'}}>
                                            <i className="ri-magic-line fs-4 me-3"></i>
                                            <div>
                                                <strong>Ottima scelta!</strong><br/>
                                                <span className="small">Questo professionista è ideale per: {aiMatches.psicologia.find(p => p.id == selectedMatches.psychology).match_reasons?.join(', ')}</span>
                                            </div>
                                        </Alert>
                                    )}

                                    <div className="mt-4 pt-3 border-top d-flex justify-content-end">
                                        <Button 
                                            variant="success" 
                                            size="lg"
                                            className="px-5 fw-bold shadow-sm rounded-pill text-white"
                                            onClick={() => handleConfirmAssignment('psychology')}
                                            disabled={loading || !selectedMatches.psychology || (!hasNewInteraction && isAlreadyAssigned('psychology'))}
                                        >
                                            {loading && <Spinner size="sm" animation="border" className="me-2" />}
                                            Conferma Assegnazione <i className="ri-arrow-right-line ms-2"></i>
                                        </Button>
                                    </div>
                                </div>
                                )}
                                
                                <div className="mt-4">
                                    <label className="form-label small fw-bold text-uppercase text-muted">Note Generali Assegnazione</label>
                                    <Form.Control 
                                        as="textarea" 
                                        rows={3} 
                                        placeholder="Note opzionali visibili al professionista..."
                                        value={assignmentNotes}
                                        onChange={(e) => setAssignmentNotes(e.target.value)}
                                        className="shadow-sm border-light-subtle bg-white rounded"
                                    />
                                </div>
                                </div>
                            </Col>
                        </Row>
                    </div>
                </div>
            )}
        </Modal.Body>
        <Modal.Footer className="bg-white border-top">
            <Button variant="secondary" onClick={() => setShowAIModal(false)} className="px-4">Chiudi</Button>
        </Modal.Footer>
      </Modal>



      {/* Existing Assignment Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)}>
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

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        
        .btn-gradient-ai {
            background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
            border: none;
            color: white;
            transition: all 0.3s ease;
        }
        .btn-gradient-ai:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            color: white;
        }

        .success-checkmark {
            animation: popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        @keyframes popIn {
            0% { transform: scale(0.5); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </>
  );
}

export default AssegnazioniAI;

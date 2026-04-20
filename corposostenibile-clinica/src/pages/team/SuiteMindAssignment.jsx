import { useState, useEffect, useMemo } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Badge, Spinner, Alert, Button, Form, Row, Col, Card } from 'react-bootstrap';
import api from '../../services/api';
import ghlService from '../../services/ghlService';
import './SuiteMindAssignment.css';

const DEPT_ROLE_MAP = {
  2: 'nutrizione',
  24: 'nutrizione',
  3: 'coach',
  4: 'psicologia'
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

const getStoredAnalysisForRole = (existing, role) => {
  if (!existing || !role) return null;
  const keys = ROLE_ANALYSIS_KEYS[role] || [role];
  const matchKey = keys.find((k) => existing[k]);
  if (matchKey) return existing[matchKey];
  if (existing.summary || existing.criteria) return existing;
  return null;
};

function SuiteMindAssignment() {
  const location = useLocation();
  const navigate = useNavigate();
  const { opportunityId } = useParams();

  const [selectedOpportunity, setSelectedOpportunity] = useState(location.state?.opportunity || null);
  const [loadingOpportunity, setLoadingOpportunity] = useState(!location.state?.opportunity && !!opportunityId);
  const [opportunityError, setOpportunityError] = useState('');
  const [professionals, setProfessionals] = useState([]);
  const [loading, setLoading] = useState(false);

  // AI state
  const [aiLoading, setAiLoading] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiMatches, setAiMatches] = useState(null);
  const [selectedMatches, setSelectedMatches] = useState({ nutrition: '', coach: '', psychology: '' });
  const [assignmentNotes, setAssignmentNotes] = useState('');
  const [activeRoleFlow, setActiveRoleFlow] = useState(null);
  const [assignmentSuccess, setAssignmentSuccess] = useState(false);
  const [lastAssignedProf, setLastAssignedProf] = useState(null);
  const [hasNewInteraction, setHasNewInteraction] = useState(false);

  // Load opportunity data from route state or API (supports deep-link / refresh)
  useEffect(() => {
    let cancelled = false;

    const loadOpportunity = async () => {
      if (location.state?.opportunity) {
        setSelectedOpportunity(location.state.opportunity);
        setLoadingOpportunity(false);
        setOpportunityError('');
        return;
      }

      if (!opportunityId) {
        navigate('/assegnazioni-ai', { replace: true });
        return;
      }

      setLoadingOpportunity(true);
      setOpportunityError('');

      try {
        const response = await ghlService.getOpportunityDataById(opportunityId);
        if (cancelled) return;

        if (response?.success && response?.data) {
          setSelectedOpportunity(response.data);
        } else {
          setOpportunityError(response?.message || 'Lead non trovato.');
        }
      } catch (err) {
        if (cancelled) return;
        console.error('Errore caricamento opportunity:', err);
        setOpportunityError(err?.response?.data?.message || 'Errore durante il caricamento del lead.');
      } finally {
        if (!cancelled) {
          setLoadingOpportunity(false);
        }
      }
    };

    loadOpportunity();

    return () => {
      cancelled = true;
    };
  }, [location.state, navigate, opportunityId]);

  // Fetch professionals
  useEffect(() => {
    const fetchProfessionals = async () => {
      try {
        const resp = await api.get('/team/professionals/criteria');
        if (resp.data.success) {
          setProfessionals(resp.data.professionals);
        }
      } catch (err) {
        console.error('Errore caricamento professionisti:', err);
      }
    };
    fetchProfessionals();
  }, []);

  // --- Helpers ---

  const getLeadRequirements = (opp) => getPackageRequirements(opp?.pacchetto);

  const isRoleRequiredForLead = (opp, role) => {
    const req = getLeadRequirements(opp);
    return !!req[role];
  };

  const isAlreadyAssigned = (role) => {
    const saved = selectedOpportunity?.assignments;
    if (!saved) return false;
    if (role === 'nutrition') return selectedMatches.nutrition == saved.nutritionist_id;
    if (role === 'coach') return selectedMatches.coach == saved.coach_id;
    if (role === 'psychology') return selectedMatches.psychology == saved.psychologist_id;
    return false;
  };

  const hasStoredAnalysis = useMemo(() => {
    if (!activeRoleFlow || !selectedOpportunity?.ai_analysis) return false;
    const existing = selectedOpportunity.ai_analysis;
    const stored = getStoredAnalysisForRole(existing, activeRoleFlow);
    return !!(stored?.summary || stored?.criteria?.length);
  }, [activeRoleFlow, selectedOpportunity]);

  // --- Handlers ---

  const handleSelectRoleFlow = (role) => {
    if (!isRoleRequiredForLead(selectedOpportunity, role)) return;

    setActiveRoleFlow(role);
    setAiAnalysis(null);
    setAiMatches(null);
    setHasNewInteraction(false);

    const existing = selectedOpportunity?.ai_analysis;
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
      const resAnalyze = await api.post('/team/assignments/analyze-lead', {
        story: opp.storia,
        opportunity_id: opp.id,
        assignment_id: opp.assignment_id,
        role: targetRole
      });

      if (resAnalyze.data.success) {
        const analysis = resAnalyze.data.analysis;
        setAiAnalysis(analysis);
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
    if (!selectedOpportunity?.assignment_id && !selectedOpportunity?.id) {
      alert("ID Assegnazione o Paziente mancante. Impossibile procedere.");
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
        const profId = role === 'nutrition' ? selectedMatches.nutrition : (role === 'coach' ? selectedMatches.coach : selectedMatches.psychology);
        const prof = professionals.find(p => p.id == profId);
        setLastAssignedProf(prof);
        setAssignmentSuccess(true);
        setHasNewInteraction(false);

        // Update local opportunity to reflect assignment
        const updatedAssignments = { ...(selectedOpportunity.assignments || {}) };
        if (role === 'nutrition') updatedAssignments.nutritionist_id = nutritionist_id;
        if (role === 'coach') updatedAssignments.coach_id = coach_id;
        if (role === 'psychology') updatedAssignments.psychologist_id = psychologist_id;
        setSelectedOpportunity(prev => ({ ...prev, assignments: updatedAssignments }));
      }
    } catch (err) {
      console.error("Errore conferma:", err);
      alert("Errore durante il salvataggio dell'assegnazione.");
    } finally {
      setLoading(false);
    }
  };

  if (loadingOpportunity) {
    return (
      <div className="sm-page d-flex align-items-center justify-content-center min-vh-100">
        <div className="text-center">
          <Spinner animation="border" role="status" className="mb-3" />
          <div>Caricamento opportunità...</div>
        </div>
      </div>
    );
  }

  if (opportunityError) {
    return (
      <div className="sm-page p-4">
        <Alert variant="danger">
          <Alert.Heading>Impossibile aprire il lead</Alert.Heading>
          <p className="mb-3">{opportunityError}</p>
          <div className="d-flex gap-2 flex-wrap">
            <Button variant="primary" onClick={() => navigate('/assegnazioni-ai')}>
              Torna alla queue
            </Button>
            <Button variant="outline-danger" onClick={() => window.location.reload()}>
              Riprova
            </Button>
          </div>
        </Alert>
      </div>
    );
  }

  if (!selectedOpportunity) return null;

  const requirement = getLeadRequirements(selectedOpportunity);
  const selectedSalesDisplay = selectedOpportunity.sales_person?.full_name || selectedOpportunity.sales_consultant || 'N/D';
  const selectedStatus = selectedOpportunity.processed ? 'Processato' : 'Da lavorare';

  // --- Role selection card renderer ---
  const renderRoleCard = (role, icon, iconClass, label, description, colorVariant) => {
    const isEnabled = !!requirement[role];
    const existing = getStoredAnalysisForRole(selectedOpportunity?.ai_analysis, role);
    const hasAnalysis = !!existing;
    const btnLabel = hasAnalysis ? 'Usa Analisi' : 'Avvia Analisi';

    return (
      <div
        className={`sm-role-card ${!isEnabled ? 'sm-role-disabled' : ''}`}
        onClick={() => isEnabled && handleSelectRoleFlow(role)}
      >
        <div className={`sm-role-icon ${iconClass}`}>
          <i className={icon}></i>
        </div>
        <h6 className="sm-role-title">{label}</h6>
        {!isEnabled && <span className="sm-badge sm-badge-muted">Non previsto</span>}
        {isEnabled && hasAnalysis && <span className="sm-badge sm-badge-success">Analisi pronta</span>}
        <button className={`sm-role-btn sm-role-btn-${colorVariant}`} disabled={!isEnabled}>
          {btnLabel} <i className="ri-arrow-right-s-line"></i>
        </button>
      </div>
    );
  };

  // --- Match section renderer ---
  const renderMatchSection = (role, colorVariant, icon, label, matchKey, selectPlaceholder) => {
    const borderClass = `sm-match-section sm-match-${colorVariant}`;
    const matchList = aiMatches?.[matchKey] || [];
    const selectedValue = selectedMatches[role];
    const selectedMatch = matchList.find(p => p.id == selectedValue);
    const deptKey = role === 'nutrition' ? 'nutrizione' : (role === 'psychology' ? 'psicologia' : 'coach');

    return (
      <div className={borderClass}>
        <div className="sm-match-header">
          <div className={`sm-match-icon sm-match-icon-${colorVariant}`}>
            <i className={icon}></i>
          </div>
          <h5 className="sm-match-title">Assegnazione {label}</h5>
          {aiAnalysis && <span className="sm-ai-badge">AI MATCHED</span>}
        </div>

        <div className="sm-match-body">
          <label className="sm-select-label">Professionista Consigliato</label>
          <Form.Select
            size="lg"
            value={selectedValue}
            onChange={(e) => {
              setSelectedMatches({ ...selectedMatches, [role]: e.target.value });
              setHasNewInteraction(true);
            }}
            className={`sm-select sm-select-${colorVariant}`}
          >
            <option value="">{selectPlaceholder}</option>
            {matchList.map(p => (
              <option key={p.id} value={p.id}>
                {p.name} (Match: {p.score}%)
              </option>
            ))}
            {matchList.length > 0 && <option disabled>──────────</option>}
            {professionals.filter(p => !matchList.find(m => m.id === p.id) && (DEPT_ROLE_MAP[p.department_id] === deptKey)).map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </Form.Select>
        </div>

        {selectedMatch?.match_reasons?.length > 0 && (
          <div className={`sm-match-reason sm-match-reason-${colorVariant}`}>
            <i className="ri-magic-line"></i>
            <div>
              <strong>Ottima scelta!</strong><br />
              <span>Questo professionista è ideale per: {selectedMatch.match_reasons.join(', ')}</span>
            </div>
          </div>
        )}

        <div className="sm-match-footer">
          <Button
            variant="success"
            size="lg"
            className="sm-confirm-btn"
            onClick={() => handleConfirmAssignment(role)}
            disabled={loading || !selectedValue || (!hasNewInteraction && isAlreadyAssigned(role))}
          >
            {loading && <Spinner size="sm" animation="border" className="me-2" />}
            Conferma Assegnazione <i className="ri-arrow-right-line ms-2"></i>
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div className="sm-page">
      {!assignmentSuccess && (
        <div className="mb-4 p-4 bg-white border rounded-4 shadow-sm">
          <div className="d-flex flex-column flex-lg-row align-items-lg-center justify-content-between gap-3">
            <div>
              <div className="d-flex align-items-center gap-2 flex-wrap mb-2">
                <Badge bg={selectedOpportunity.processed ? 'success' : 'warning'} className="rounded-pill">
                  {selectedStatus}
                </Badge>
                {selectedOpportunity.sales_person?.full_name || selectedOpportunity.sales_consultant ? (
                  <Badge bg="light" text="dark" className="rounded-pill border">
                    <i className="ri-user-star-line me-1"></i>
                    Sales: {selectedSalesDisplay}
                  </Badge>
                ) : null}
              </div>
              <h4 className="mb-1">{selectedOpportunity.nome || 'Lead senza nome'}</h4>
              <div className="text-muted small">
                ID {selectedOpportunity.id} · {selectedOpportunity.email || 'N/D'} · {selectedOpportunity.lead_phone || 'N/D'}
              </div>
            </div>
            <div className="text-lg-end text-muted small">
              <div><strong>Pacchetto:</strong> {selectedOpportunity.pacchetto || 'N/D'}</div>
              <div><strong>Durata:</strong> {selectedOpportunity.durata || 'N/D'}</div>
              <div><strong>Ricevuto:</strong> {formatDate(selectedOpportunity.received_at)}</div>
            </div>
          </div>
        </div>
      )}

      {/* SCREEN: Role Selection */}
      {!activeRoleFlow && (
        <div className="sm-role-selection">
          <button className="sm-back-btn" onClick={() => navigate('/assegnazioni-ai')}>
            <i className="ri-arrow-left-line"></i>
            <span>Torna Indietro</span>
          </button>
          <div className="sm-logo-center">
            <img src="/suitemind.png" alt="SuiteMind" className="sm-logo" />
            <h5 className="sm-logo-title">Scegli il Percorso</h5>
          </div>
          <div className="sm-role-grid">
            {renderRoleCard('nutrition', 'ri-restaurant-line', 'sm-icon-nutrition', 'Nutrizionista', 'Abitudini alimentari, obiettivi di peso e preferenze dietetiche.', 'success')}
            {renderRoleCard('coach', 'ri-run-line', 'sm-icon-coach', 'Coach', 'Livello fitness, obiettivi di allenamento e stile di vita.', 'primary')}
            {renderRoleCard('psychology', 'ri-mental-health-line', 'sm-icon-psychology', 'Psicologo', 'Aspetti emotivi, relazione con il cibo e gestione stress.', 'warning')}
          </div>
        </div>
      )}

      {/* SCREEN: Success */}
      {activeRoleFlow && assignmentSuccess && (
        <div className="sm-success">
          <div className="sm-success-icon">
            <i className="ri-checkbox-circle-fill"></i>
          </div>
          <h2>Assegnazione Completata!</h2>
          <p className="sm-success-detail">
            Hai assegnato correttamente <strong>{lastAssignedProf?.name}</strong> a <strong>{selectedOpportunity.nome}</strong>.
          </p>
          <div className="sm-success-card">
            <div className="sm-success-card-icon">
              <i className="ri-user-follow-line"></i>
            </div>
            <div>
              <div className="sm-success-label">Ruolo</div>
              <div className="sm-success-role">
                {activeRoleFlow === 'nutrition' && 'Nutrizionista'}
                {activeRoleFlow === 'coach' && 'Coach'}
                {activeRoleFlow === 'psychology' && 'Psicologo'}
              </div>
            </div>
          </div>
          <div className="sm-success-actions">
            <button
              className="sm-btn-outline"
              onClick={() => { setAssignmentSuccess(false); setActiveRoleFlow(null); }}
            >
              Torna ai Ruoli
            </button>
            <button
              className="sm-btn-primary"
              onClick={() => navigate('/assegnazioni-ai')}
            >
              Torna alle Assegnazioni
            </button>
          </div>
        </div>
      )}

      {/* SCREEN: Analysis + Matching */}
      {activeRoleFlow && !assignmentSuccess && (
        <div className="sm-flow">
          <div className="sm-flow-nav">
            <Button variant="link" className="sm-flow-back" onClick={() => setActiveRoleFlow(null)}>
              <i className="ri-arrow-left-line me-1"></i>Indietro
            </Button>
            <span className="sm-flow-context">Analisi in corso per: <strong>{selectedOpportunity.nome}</strong></span>
          </div>

          <div className="sm-flow-panels">
            {/* LEFT: Analysis & Story */}
            <div className="sm-panel-left">
              <div className="sm-analysis-card">
                <div className="sm-analysis-header">
                  <i className="ri-file-search-line"></i>
                  <span>Analisi AI</span>
                </div>
                <div className="sm-analysis-body">
                  <div className="sm-story-section">
                    <h6 className="sm-section-label">Storia del Cliente</h6>
                    <div className="sm-story-text">
                      {selectedOpportunity.storia || <em>Nessuna storia presente</em>}
                    </div>
                  </div>

                  {!aiAnalysis ? (
                    <div className="sm-analysis-empty">
                      {aiLoading ? (
                        <>
                          <Spinner animation="border" variant="success" className="mb-3" />
                          <p>Analisi in corso...</p>
                        </>
                      ) : hasStoredAnalysis ? (
                        <>
                          <div className="sm-analysis-ready-icon">
                            <i className="ri-check-line"></i>
                          </div>
                          <p>Analisi già disponibile per questo ruolo.</p>
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
                          <i className="ri-sparkling-line sm-spark-icon"></i>
                          <p>Pronto per l'analisi</p>
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
                      <div className="sm-summary-section">
                        <h6 className="sm-section-label sm-section-label-success">Sintesi</h6>
                        <div className="sm-summary-box">{aiAnalysis.summary}</div>
                      </div>

                      <div className="sm-criteria-section">
                        <h6 className="sm-section-label sm-section-label-success">Match Criteria</h6>
                        <div className="sm-criteria-tags">
                          {aiAnalysis.criteria?.length > 0 ? (
                            aiAnalysis.criteria.map(tag => (
                              <span key={tag} className="sm-criteria-tag">{tag}</span>
                            ))
                          ) : (
                            <span className="sm-no-criteria">Nessun criterio specifico estratto</span>
                          )}
                        </div>
                      </div>

                      {aiAnalysis.suggested_focus?.length > 0 && (
                        <div className="sm-focus-section">
                          <h6 className="sm-section-label sm-section-label-success">Focus Suggerito</h6>
                          {aiAnalysis.suggested_focus.map((focus, i) => (
                            <div key={i} className="sm-focus-item">
                              <i className="ri-check-line"></i>
                              <span>{focus}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="sm-refresh-section">
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
                </div>
              </div>
            </div>

            {/* RIGHT: Matching & Selection */}
            <div className="sm-panel-right">
              {activeRoleFlow === 'nutrition' && renderMatchSection('nutrition', 'success', 'ri-restaurant-line', 'Nutrizionista', 'nutrizione', '-- Seleziona un Nutrizionista --')}
              {activeRoleFlow === 'coach' && renderMatchSection('coach', 'primary', 'ri-run-line', 'Coach', 'coach', '-- Seleziona un Coach --')}
              {activeRoleFlow === 'psychology' && renderMatchSection('psychology', 'warning', 'ri-mental-health-line', 'Psicologo', 'psicologia', '-- Seleziona uno Psicologo --')}

              <div className="sm-notes-section">
                <label className="sm-select-label">Note Generali Assegnazione</label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  placeholder="Note opzionali visibili al professionista..."
                  value={assignmentNotes}
                  onChange={(e) => setAssignmentNotes(e.target.value)}
                  className="sm-notes-input"
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SuiteMindAssignment;

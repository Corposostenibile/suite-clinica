import { useState, useEffect, useMemo } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Spinner, Button, Form } from 'react-bootstrap';
import api from '../../services/api';
import oldSuiteService from '../../services/oldSuiteService';
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

const getStoredAnalysisForRole = (existing, role) => {
  if (!existing || !role) return null;
  const keys = ROLE_ANALYSIS_KEYS[role] || [role];
  const matchKey = keys.find((k) => existing[k]);
  if (matchKey) return existing[matchKey];
  if (existing.summary || existing.criteria) return existing;
  return null;
};

function SuiteMindOldSuite() {
  const location = useLocation();
  const navigate = useNavigate();
  const { leadId } = useParams();

  const [selectedLead, setSelectedLead] = useState(location.state?.lead || null);
  const [professionals, setProfessionals] = useState([]);
  const [loading, setLoading] = useState(false);

  // AI state
  const [aiLoading, setAiLoading] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiMatches, setAiMatches] = useState(null);
  const [selectedMatches, setSelectedMatches] = useState({ nutrition: '', coach: '', psychology: '' });
  const [assignmentNotes, setAssignmentNotes] = useState('');
  const [onboardingNotes, setOnboardingNotes] = useState(location.state?.lead?.onboarding_notes || '');
  const [loomLink, setLoomLink] = useState(location.state?.lead?.loom_link || '');
  const [activeRoleFlow, setActiveRoleFlow] = useState(null);
  const [assignmentSuccess, setAssignmentSuccess] = useState(false);
  const [lastAssignedProf, setLastAssignedProf] = useState(null);
  const [hasNewInteraction, setHasNewInteraction] = useState(false);

  // Fetch lead if not passed via state
  useEffect(() => {
    if (!selectedLead && leadId) {
      oldSuiteService.getLeadById(leadId).then((result) => {
        if (result.success) {
          setSelectedLead(result.data);
        } else {
          navigate('/assegnazioni-old-suite', { replace: true });
        }
      }).catch(() => {
        navigate('/assegnazioni-old-suite', { replace: true });
      });
    }
  }, [selectedLead, leadId, navigate]);

  // Fetch professionals
  useEffect(() => {
    const fetchProfessionals = async () => {
      try {
        const resp = await api.get('/team/professionals/criteria');
        if (resp.data.success) setProfessionals(resp.data.professionals);
      } catch (err) {
        console.error('Errore caricamento professionisti:', err);
      }
    };
    fetchProfessionals();
  }, []);

  // --- Helpers ---

  const requirement = useMemo(() => {
    const roles = selectedLead?.package_roles || { nutrition: true, coach: true, psychology: true };
    return roles;
  }, [selectedLead]);

  const isRoleRequired = (role) => !!requirement[role];

  const isAlreadyAssigned = (role) => {
    const saved = selectedLead?.assignments;
    if (!saved) return false;
    if (role === 'nutrition') return selectedMatches.nutrition == saved.nutritionist_id;
    if (role === 'coach') return selectedMatches.coach == saved.coach_id;
    if (role === 'psychology') return selectedMatches.psychology == saved.psychologist_id;
    return false;
  };

  const hasStoredAnalysis = useMemo(() => {
    if (!activeRoleFlow || !selectedLead?.ai_analysis) return false;
    const stored = getStoredAnalysisForRole(selectedLead.ai_analysis, activeRoleFlow);
    return !!(stored?.summary || stored?.criteria?.length);
  }, [activeRoleFlow, selectedLead]);

  // --- Handlers ---

  const handleSelectRoleFlow = (role) => {
    if (!isRoleRequired(role)) return;

    setActiveRoleFlow(role);
    setAiAnalysis(null);
    setAiMatches(null);
    setHasNewInteraction(false);

    const existing = selectedLead?.ai_analysis;
    const relevantAnalysis = existing ? getStoredAnalysisForRole(existing, role) : null;

    if (relevantAnalysis) {
      setAiAnalysis(relevantAnalysis);
      handleRunMatching(relevantAnalysis.criteria);
    } else {
      handleRunAIAnalysis(selectedLead, role);
    }
  };

  const handleRunAIAnalysis = async (targetLead = null, role = null) => {
    const lead = targetLead || selectedLead;
    const targetRole = role || activeRoleFlow;

    if (!lead?.client_story) {
      alert("Nessuna storia disponibile per l'analisi AI.");
      return;
    }

    setAiLoading(true);
    try {
      const resAnalyze = await api.post('/team/assignments/analyze-lead', {
        story: lead.client_story,
        sales_lead_id: lead.id,
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
    if (!selectedLead?.id) {
      alert("ID Lead mancante. Impossibile procedere.");
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
      const result = await oldSuiteService.confirmAssignment({
        lead_id: selectedLead.id,
        nutritionist_id,
        coach_id,
        psychologist_id,
        notes: assignmentNotes,
        onboarding_notes: onboardingNotes,
        loom_link: loomLink,
        ai_analysis: aiAnalysis,
      });

      if (result.success) {
        const profId = nutritionist_id || coach_id || psychologist_id;
        const prof = professionals.find(p => p.id == profId);
        setLastAssignedProf(prof);
        setAssignmentSuccess(true);
        setHasNewInteraction(false);

        // Update local lead
        const updatedAssignments = { ...(selectedLead.assignments || {}) };
        if (role === 'nutrition') updatedAssignments.nutritionist_id = nutritionist_id;
        if (role === 'coach') updatedAssignments.coach_id = coach_id;
        if (role === 'psychology') updatedAssignments.psychologist_id = psychologist_id;
        setSelectedLead(prev => ({
          ...prev,
          assignments: updatedAssignments,
          _allAssigned: result.all_assigned,
          _assignedCount: result.assigned_count,
          _requiredCount: result.required_count,
        }));
      }
    } catch (err) {
      console.error("Errore conferma:", err);
      alert("Errore durante il salvataggio dell'assegnazione.");
    } finally {
      setLoading(false);
    }
  };

  if (!selectedLead) {
    return (
      <div className="sm-page text-center py-5">
        <Spinner animation="border" variant="primary" />
        <p className="mt-2 text-muted">Caricamento lead...</p>
      </div>
    );
  }

  // --- Role card renderer ---
  const renderRoleCard = (role, icon, iconClass, label, colorVariant) => {
    const isEnabled = isRoleRequired(role);
    const existing = getStoredAnalysisForRole(selectedLead?.ai_analysis, role);
    const hasAnalysis = !!existing;
    const btnLabel = hasAnalysis ? 'Usa Analisi' : 'Avvia Analisi';

    return (
      <div className={`sm-role-card ${!isEnabled ? 'sm-role-disabled' : ''}`} onClick={() => isEnabled && handleSelectRoleFlow(role)}>
        <div className={`sm-role-icon ${iconClass}`}><i className={icon}></i></div>
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
    const matchList = aiMatches?.[matchKey] || [];
    const selectedValue = selectedMatches[role];
    const selectedMatch = matchList.find(p => p.id == selectedValue);
    const deptKey = role === 'nutrition' ? 'nutrizione' : (role === 'psychology' ? 'psicologia' : 'coach');

    return (
      <div className={`sm-match-section sm-match-${colorVariant}`}>
        <div className="sm-match-header">
          <div className={`sm-match-icon sm-match-icon-${colorVariant}`}><i className={icon}></i></div>
          <h5 className="sm-match-title">Assegnazione {label}</h5>
          {aiAnalysis && <span className="sm-ai-badge">AI MATCHED</span>}
        </div>

        <div className="sm-match-body">
          <label className="sm-select-label">Professionista Consigliato</label>
          <Form.Select
            size="lg"
            value={selectedValue}
            onChange={(e) => { setSelectedMatches({ ...selectedMatches, [role]: e.target.value }); setHasNewInteraction(true); }}
            className={`sm-select sm-select-${colorVariant}`}
          >
            <option value="">{selectPlaceholder}</option>
            {matchList.map(p => (
              <option key={p.id} value={p.id}>{p.name} (Match: {p.score}%)</option>
            ))}
            {matchList.length > 0 && <option disabled>──────────</option>}
            {professionals.filter(p => !matchList.find(m => m.id === p.id) && (DEPT_ROLE_MAP[p.department_id] === deptKey) && p.is_available !== false).map(p => (
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
      {/* SCREEN: Role Selection */}
      {!activeRoleFlow && (
        <div className="sm-role-selection">
          <button className="sm-back-btn" onClick={() => navigate('/assegnazioni-old-suite')}>
            <i className="ri-arrow-left-line"></i>
            <span>Torna Indietro</span>
          </button>
          <div className="sm-logo-center">
            <img src="/suitemind.png" alt="SuiteMind" className="sm-logo" />
            <h5 className="sm-logo-title">Scegli il Percorso</h5>
          </div>
          <div className="sm-role-grid">
            {renderRoleCard('nutrition', 'ri-restaurant-line', 'sm-icon-nutrition', 'Nutrizionista', 'success')}
            {renderRoleCard('coach', 'ri-run-line', 'sm-icon-coach', 'Coach', 'primary')}
            {renderRoleCard('psychology', 'ri-mental-health-line', 'sm-icon-psychology', 'Psicologo', 'warning')}
          </div>
        </div>
      )}

      {/* SCREEN: Success */}
      {activeRoleFlow && assignmentSuccess && (
        <div className="sm-success">
          <div className="sm-success-icon">
            <i className={selectedLead._allAssigned ? "ri-checkbox-circle-fill" : "ri-checkbox-circle-line"}></i>
          </div>
          <h2>{selectedLead._allAssigned ? 'Paziente Creato!' : 'Professionista Assegnato!'}</h2>
          <p className="sm-success-detail">
            Hai assegnato correttamente <strong>{lastAssignedProf?.name}</strong> a <strong>{selectedLead.full_name}</strong>.
            {!selectedLead._allAssigned && (
              <><br /><span className="text-warning">Assegnazione {selectedLead._assignedCount}/{selectedLead._requiredCount} — completa gli altri ruoli per creare il paziente.</span></>
            )}
            {selectedLead._allAssigned && (
              <><br /><span className="text-success">Tutti i professionisti assegnati! Il paziente è stato creato.</span></>
            )}
          </p>
          <div className="sm-success-card">
            <div className="sm-success-card-icon"><i className="ri-user-follow-line"></i></div>
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
            {!selectedLead._allAssigned && (
              <button className="sm-btn-outline" onClick={() => { setAssignmentSuccess(false); setActiveRoleFlow(null); }}>
                Assegna prossimo ruolo
              </button>
            )}
            <button className="sm-btn-primary" onClick={() => navigate('/assegnazioni-old-suite')}>
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
            <span className="sm-flow-context">Analisi in corso per: <strong>{selectedLead.full_name}</strong></span>
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
                      {selectedLead.client_story || <em>Nessuna storia presente</em>}
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
                          <div className="sm-analysis-ready-icon"><i className="ri-check-line"></i></div>
                          <p>Analisi già disponibile per questo ruolo.</p>
                          <Button variant="outline-secondary" size="sm" className="w-100 rounded-pill" onClick={() => handleRunAIAnalysis()} disabled={aiLoading}>
                            <i className="ri-refresh-line me-1"></i> Aggiorna Analisi
                          </Button>
                        </>
                      ) : (
                        <>
                          <i className="ri-sparkling-line sm-spark-icon"></i>
                          <p>Pronto per l'analisi</p>
                          <Button variant="success" size="sm" className="w-100 rounded-pill" onClick={() => handleRunAIAnalysis()} disabled={aiLoading}>
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
                        <Button variant="outline-secondary" size="sm" className="w-100" onClick={() => handleRunAIAnalysis()} disabled={aiLoading}>
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
                <div className="mb-3">
                  <label className="sm-select-label">Note Criticità Onboarding</label>
                  <Form.Control
                    as="textarea"
                    rows={2}
                    placeholder="Note su criticità rilevate in fase di onboarding..."
                    value={onboardingNotes}
                    onChange={(e) => { setOnboardingNotes(e.target.value); setHasNewInteraction(true); }}
                    className="sm-notes-input"
                  />
                </div>

                <div className="mb-3">
                  <label className="sm-select-label">Link Loom Onboarding</label>
                  <Form.Control
                    type="url"
                    placeholder="https://www.loom.com/share/..."
                    value={loomLink}
                    onChange={(e) => { setLoomLink(e.target.value); setHasNewInteraction(true); }}
                    className="sm-notes-input"
                  />
                </div>

                <div className="mb-3">
                  <label className="sm-select-label">Note Interne Professionista</label>
                  <Form.Control
                    as="textarea"
                    rows={2}
                    placeholder="Note opzionali visibili al professionista..."
                    value={assignmentNotes}
                    onChange={(e) => { setAssignmentNotes(e.target.value); setHasNewInteraction(true); }}
                    className="sm-notes-input"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SuiteMindOldSuite;

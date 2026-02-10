import { useState, useEffect } from 'react';
import { Table, Badge, Card, Spinner, Alert, Button, ButtonGroup, Modal, Tab, Tabs, Form, Row, Col } from 'react-bootstrap';
import api from '../../services/api';
import ghlService from '../../services/ghlService';

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

function AssegnazioniAI() {
  // Stati Generali
  const [activeTab, setActiveTab] = useState('webhook-data');
  const [error, setError] = useState(null);

  // Stati Assegnazioni
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [stats, setStats] = useState({ total: 0, pending: 0, approved: 0, completed: 0 });

  // Stati Webhook (Lead)
  const [opportunityData, setOpportunityData] = useState([]);
  const [loadingOpportunity, setLoadingOpportunity] = useState(false);
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);
  const [showOpportunityModal, setShowOpportunityModal] = useState(false);

  // Stati Professionisti (Criteri)
  const [professionals, setProfessionals] = useState([]);
  const [criteriaSchema, setCriteriaSchema] = useState({});
  const [loadingProfs, setLoadingProfs] = useState(false);
  const [showProfModal, setShowProfModal] = useState(false);
  const [editingProf, setEditingProf] = useState(null);
  const [tempCriteria, setTempCriteria] = useState({});
  const [profFilter, setProfFilter] = useState('all'); // 'all', 'nutrizione', 'coach', 'psicologia'
  const [searchTerm, setSearchTerm] = useState('');

  // Stati AI Modal
  const [showAIModal, setShowAIModal] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiMatches, setAiMatches] = useState(null);
  const [selectedMatches, setSelectedMatches] = useState({ nutrition: '', coach: '', psychology: '' });
  const [assignmentNotes, setAssignmentNotes] = useState('');

  // --- FETCH DATA ---

  const fetchAssignments = async () => {
    setLoading(true);
    try {
      const response = await api.get('/ghl/api/assignments', {
        params: selectedStatus !== 'all' ? { status: selectedStatus } : {}
      });
      if (response.data.success !== false) {
        const data = response.data.assignments || response.data || [];
        setAssignments(Array.isArray(data) ? data : []);
        if (Array.isArray(data)) {
          setStats({
            total: data.length,
            pending: data.filter(a => a.status === 'pending_finance').length,
            approved: data.filter(a => a.finance_approved).length,
            completed: data.filter(a => a.status === 'completed').length,
          });
        }
      }
    } catch (err) {
      console.error('Errore assegnazioni:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchOpportunityData = async () => {
    setLoadingOpportunity(true);
    try {
      const result = await ghlService.getOpportunityData();
      if (result.success) {
        setOpportunityData(result.data || []);
      }
    } catch (err) {
      console.error('Errore opportunity data:', err);
    } finally {
      setLoadingOpportunity(false);
    }
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
    setShowAIModal(true);
  };

  const handleRunAIAnalysis = async () => {
    if (!selectedOpportunity?.storia) {
      alert("Nessuna storia disponibile per l'analisi AI.");
      return;
    }
    
    setAiLoading(true);
    setAiAnalysis(null);
    setAiMatches(null);

    try {
      // 1. Analyze Lead
      const resAnalyze = await api.post('/team/assignments/analyze-lead', { story: selectedOpportunity.storia });
      if (resAnalyze.data.success) {
        setAiAnalysis(resAnalyze.data.analysis);
        
        // 2. Match Professionals
        const criteria = resAnalyze.data.analysis.criteria || [];
        const resMatch = await api.post('/team/assignments/match', { criteria });
        
        if (resMatch.data.success) {
            setAiMatches(resMatch.data.matches);
            
            // Pre-select first best match if available
            const matches = resMatch.data.matches;
            setSelectedMatches({
                nutrition: matches.nutrizione?.[0]?.id || '',
                coach: matches.coach?.[0]?.id || '',
                psychology: matches.psicologia?.[0]?.id || ''
            });
        }
      }
    } catch (err) {
      console.error("Errore AI Analysis:", err);
      alert("Errore durante l'analisi AI. Controlla la console.");
    } finally {
      setAiLoading(false);
    }
  };

  const handleConfirmAssignment = async (role) => {
    // Possiamo procedere se abbiamo un assignment_id (cliente esistente)
    // O se abbiamo un id (lead da GHLOpportunityData)
    if (!selectedOpportunity?.assignment_id && !selectedOpportunity?.id) {
        alert("ID Assegnazione o Lead mancante. Impossibile procedere.");
        return;
    }

    const roleToIdMap = {
        'nutrition': selectedMatches.nutrition,
        'coach': selectedMatches.coach,
        'psychology': selectedMatches.psychology
    };

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
            notes: assignmentNotes
        };
        
        const response = await api.post('/team/assignments/confirm', payload);
        if (response.data.success) {
            // Update the local assignment status if possible or just refresh
            fetchOpportunityData(); // Refresh list to see if it's still pending
            alert("Professionista assegnato con successo!");
            
            // If all 3 are assigned, we could close the modal, but usually HM does it one by one
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
    setShowProfModal(true);
  };

  const handleSaveCriteria = async () => {
    if (!editingProf) return;
    try {
      await api.put(`/team/professionals/${editingProf.id}/criteria`, {
        criteria: tempCriteria
      });
      setShowProfModal(false);
      fetchProfessionalsAndSchema(); // Reload
      alert('Criteri aggiornati con successo!');
    } catch (err) {
      console.error('Errore salvataggio criteri:', err);
      alert('Errore durante il salvataggio.');
    }
  };

  const toggleCriterion = (key) => {
    setTempCriteria(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
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

    return filtered;
  };

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

  return (
    <>
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
          <Card className="border-0 shadow-sm">
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
                 </div>
               ) : (
                 <Table responsive hover className="mb-0">
                   <thead className="bg-light">
                     <tr>
                       <th>Cliente</th>
                       <th>Pacchetto/Info</th>
                       <th>Ricevuto</th>
                       <th className="text-end">Azioni</th>
                     </tr>
                   </thead>
                   <tbody>
                     {opportunityData.map((opp) => (
                       <tr key={opp.id}>
                         <td>
                           <div className="fw-bold">{opp.nome}</div>
                           {opp.storia && <small className="text-muted d-block text-truncate" style={{maxWidth: '300px'}}>{opp.storia}</small>}
                         </td>
                         <td>
                           <Badge bg="info" className="me-1">{opp.pacchetto}</Badge>
                           <span className="small text-muted">{opp.durata} gg</span>
                         </td>
                         <td><small>{formatDate(opp.received_at)}</small></td>
                         <td className="text-end">
                           <Button variant="outline-primary" size="sm" onClick={() => { setSelectedOpportunity(opp); setShowOpportunityModal(true); }}>
                             <i className="ri-eye-line me-1"></i>Dettagli
                           </Button>
                           <Button variant="gradient-primary" size="sm" className="ms-2" onClick={() => handleOpenAIModal(opp)}>
                             <i className="ri-magic-line me-1"></i>AI Match
                           </Button>
                         </td>
                       </tr>
                     ))}
                   </tbody>
                 </Table>
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
                
                <div style={{ maxWidth: '300px', width: '100%' }}>
                    <Form.Control 
                        type="search" 
                        placeholder="Cerca professionista..." 
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            {loadingProfs ? (
                <div className="text-center py-5"><Spinner animation="border" /></div>
            ) : (
                <Card className="border-0 shadow-sm">
                    <Card.Body className="p-0">
                        <Table responsive hover className="mb-0 align-middle">
                            <thead className="bg-light">
                                <tr>
                                    <th style={{width: '30%'}}>Professionista</th>
                                    <th>Stato</th>
                                    <th style={{width: '40%'}}>Criteri Specializzazione</th>
                                    <th className="text-end">Azioni</th>
                                </tr>
                            </thead>
                            <tbody>
                                {getFilteredProfessionals().map(prof => (
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
                                            {prof.is_available ? 
                                                <Badge bg="success-subtle" text="success" className="border border-success-subtle"><i className="ri-check-line me-1"></i>Disponibile</Badge> : 
                                                <Badge bg="secondary-subtle" text="secondary" className="border border-secondary-subtle"><i className="ri-close-line me-1"></i>Non disp.</Badge>
                                            }
                                        </td>
                                        <td>
                                            <div className="d-flex flex-wrap gap-1">
                                                {Object.entries(prof.criteria || {}).filter(([_, v]) => v).slice(0, 5).map(([k, _]) => (
                                                    <Badge bg="light" text="dark" className="border" key={k} style={{fontSize: '11px'}}>{k}</Badge>
                                                ))}
                                                {Object.entries(prof.criteria || {}).filter(([_, v]) => v).length > 5 && (
                                                    <Badge bg="light" text="muted" className="border" style={{fontSize: '11px'}}>+{Object.entries(prof.criteria || {}).filter(([_, v]) => v).length - 5} altri</Badge>
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
                                {getFilteredProfessionals().length === 0 && (
                                    <tr>
                                        <td colSpan="4" className="text-center py-4 text-muted">
                                            Nessun professionista trovato
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </Table>
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
                    <Alert variant="info" className="d-flex align-items-center">
                        <i className="ri-information-line fs-4 me-2"></i>
                        <div>
                            Seleziona le specializzazioni per <strong>{DEPT_LABELS[editingProf.department_id]}</strong>.
                            <br/>
                            <small>Questi tag verranno usati dall'AI per suggerire questo professionista ai pazienti con caratteristiche simili.</small>
                        </div>
                    </Alert>
                    
                    {(() => {
                        const roleKey = DEPT_ROLE_MAP[editingProf.department_id];
                        const criteriaList = criteriaSchema[roleKey] || [];
                        
                        if (criteriaList.length === 0) return <Alert variant="warning">Nessuno schema criteri trovato per questo ruolo.</Alert>;

                        return (
                            <div className="d-flex flex-wrap gap-2">
                                {criteriaList.map(crit => (
                                    <div key={crit} className="form-check form-check-inline border rounded p-2 m-0 bg-white shadow-sm" style={{minWidth: '200px'}}>
                                        <input 
                                            className="form-check-input" 
                                            type="checkbox" 
                                            id={`check-${crit}`}
                                            checked={!!tempCriteria[crit]}
                                            onChange={() => toggleCriterion(crit)}
                                            style={{cursor: 'pointer'}}
                                        />
                                        <label className="form-check-label w-100 ms-1 fw-medium" htmlFor={`check-${crit}`} style={{cursor: 'pointer'}}>
                                            {crit}
                                        </label>
                                    </div>
                                ))}
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

      {/* AI ASSIGNMENT MODAL */}
      <Modal show={showAIModal} onHide={() => setShowAIModal(false)} size="xl">
        <Modal.Header 
            closeButton 
            className="text-white border-0" 
            style={{ background: 'linear-gradient(135deg, #45CB85 0%, #239957 100%)' }}
        >
            <Modal.Title className="d-flex align-items-center">
                <i className="ri-sparkling-fill me-2"></i>
                SuiteMind - Analisi e Assegnazione AI
            </Modal.Title>
        </Modal.Header>
        <Modal.Body className="bg-light p-4">
            {aiLoading && !aiAnalysis ? (
                <div className="text-center py-5">
                    <div className="mb-4">
                       <img src="/static/assets/icone/suitemind.png" alt="SuiteMind" style={{height: '100px', width: 'auto'}} className="spin-slow" />
                    </div>
                    <h4 className="fw-bold">SuiteMind sta analizzando...</h4>
                    <p className="text-muted">Sto leggendo la storia del cliente e verificando i match migliori.</p>
                    <Spinner animation="border" variant="success" className="mt-3" />
                </div>
            ) : (
                <Row className="g-4">
                    {/* LEFT: Analysis Result */}
                    <Col lg={4}>
                        <Card className="border-0 shadow-sm overflow-hidden">
                            <Card.Header className="bg-white py-3 border-bottom d-flex align-items-center">
                                <i className="ri-file-search-line fs-4 me-2 text-success"></i>
                                <span className="fw-bold text-uppercase small">1. Storia e Analisi AI</span>
                            </Card.Header>
                            <Card.Body className="p-4" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
                                <div className="mb-4">
                                    <h6 className="fw-bold text-muted small text-uppercase mb-2">Storia del Cliente</h6>
                                    <div className="bg-white border rounded p-3" style={{ fontSize: '0.85rem', whiteSpace: 'pre-wrap', maxHeight: '250px', overflowY: 'auto' }}>
                                        {selectedOpportunity?.storia || <em>Nessuna storia presente</em>}
                                    </div>
                                </div>

                                {!aiAnalysis ? (
                                    <div className="text-center py-4 bg-white rounded border border-dashed">
                                        <i className="ri-sparkling-line fs-1 text-success opacity-50 mb-2 d-block"></i>
                                        <p className="small text-muted mb-3">L'AI non ha ancora analizzato questa lead.</p>
                                        <Button 
                                            variant="success" 
                                            size="sm" 
                                            onClick={handleRunAIAnalysis}
                                            disabled={aiLoading}
                                        >
                                            {aiLoading ? <Spinner size="sm" className="me-1" /> : <i className="ri-play-fill me-1"></i>}
                                            Avvia Analisi Smart
                                        </Button>
                                    </div>
                                ) : (
                                    <>
                                        <div className="mb-4 mt-3">
                                            <h6 className="fw-bold text-success small text-uppercase">Sintesi SuiteMind</h6>
                                            <p className="text-dark bg-white p-3 rounded border border-success-subtle" style={{ fontSize: '0.9rem', lineHeight: '1.6' }}>
                                                {aiAnalysis.summary}
                                            </p>
                                        </div>
                                        
                                        <div className="mb-4">
                                            <h6 className="fw-bold text-success small text-uppercase mb-2">Match Criteria</h6>
                                            <div className="d-flex flex-wrap gap-1">
                                                {aiAnalysis.criteria?.map(tag => (
                                                    <Badge bg="success-subtle" text="success" key={tag} className="border border-success-subtle py-2 px-3 rounded-pill" style={{fontSize: '0.75rem'}}>
                                                        {tag}
                                                    </Badge>
                                                )) || <span className="text-muted small">Nessun criterio estratto</span>}
                                            </div>
                                        </div>
                                        
                                        <div>
                                            <h6 className="fw-bold text-success small text-uppercase mb-2">Punti di Forza Match</h6>
                                            {aiAnalysis.suggested_focus?.map((focus, i) => (
                                                <div key={i} className="d-flex align-items-start mb-2 small text-muted">
                                                    <i className="ri-arrow-right-s-line text-success me-1 mt-1"></i>
                                                    <span>{focus}</span>
                                                </div>
                                            )) || <span className="text-muted small">Nessun suggerimento generato</span>}
                                        </div>

                                        <div className="mt-4 pt-3 border-top">
                                            <Button 
                                                variant="outline-success" 
                                                size="sm" 
                                                className="w-100"
                                                onClick={handleRunAIAnalysis}
                                                disabled={aiLoading}
                                            >
                                                <i className="ri-refresh-line me-1"></i> Riprova Analisi
                                            </Button>
                                        </div>
                                    </>
                                )}
                            </Card.Body>
                        </Card>
                    </Col>
                    
                    {/* RIGHT: Matching & Selection */}
                    <Col lg={8}>
                        <Card className="border-0 shadow-sm overflow-hidden">
                            <Card.Header className="bg-white py-3 border-bottom d-flex justify-content-between align-items-center">
                                <div className="d-flex align-items-center">
                                    <i className="ri-team-line fs-4 me-2 text-primary"></i>
                                    <span className="fw-bold text-uppercase small">2. Assegnazione Professionisti</span>
                                </div>
                                {aiAnalysis && <Badge bg="success" className="px-3 py-2 rounded-pill shadow-sm">AI POWERED</Badge>}
                            </Card.Header>
                            <Card.Body className="p-4" style={{ maxHeight: '65vh', overflowY: 'auto' }}>
                                
                                {/* NUTRITION SECTION */}
                                <div className="p-4 rounded mb-4 shadow-sm" style={{ background: '#F0FDF4', border: '1px solid #45CB85' }}>
                                    <div className="d-flex align-items-center justify-content-between mb-3">
                                        <h6 className="fw-bold text-success mb-0 d-flex align-items-center">
                                            <i className="ri-restaurant-line me-2 fs-4"></i>
                                            NUTRIZIONISTA
                                        </h6>
                                    </div>
                                    <Row className="g-3 align-items-end">
                                        <Col md={9}>
                                            <label className="small text-muted mb-1 fw-medium">Seleziona Professionista</label>
                                            <Form.Select 
                                                value={selectedMatches.nutrition} 
                                                onChange={(e) => setSelectedMatches({...selectedMatches, nutrition: e.target.value})}
                                                className="border-success-subtle shadow-none"
                                            >
                                                <option value="">-- Scegli Nutrizionista --</option>
                                                {aiMatches?.nutrizione?.map(p => (
                                                    <option key={p.id} value={p.id}>
                                                        {p.name} (Match: {p.score}%)
                                                    </option>
                                                ))}
                                                <option disabled>──────────</option>
                                                {professionals.filter(p => !aiMatches?.nutrizione?.find(m => m.id === p.id) && (DEPT_ROLE_MAP[p.department_id] === 'nutrizione')).map(p => (
                                                    <option key={p.id} value={p.id}>{p.name}</option>
                                                ))}
                                            </Form.Select>
                                        </Col>
                                        <Col md={3}>
                                            <Button 
                                                variant="success" 
                                                className="w-100 fw-bold shadow-sm"
                                                onClick={() => handleConfirmAssignment('nutrition')}
                                                disabled={loading || !selectedMatches.nutrition}
                                            >
                                                <i className="ri-check-line me-1"></i>Assegna
                                            </Button>
                                        </Col>
                                    </Row>
                                    {selectedMatches.nutrition && aiMatches?.nutrizione?.find(p => p.id == selectedMatches.nutrition) && (
                                        <div className="mt-2 bg-white p-2 rounded small text-success border border-success-subtle d-flex align-items-center">
                                            <i className="ri-sparkling-line me-2"></i>
                                            <span>Match ideale per: <strong>{aiMatches.nutrizione.find(p => p.id == selectedMatches.nutrition).match_reasons?.join(', ')}</strong></span>
                                        </div>
                                    )}
                                </div>

                                {/* COACH SECTION */}
                                <div className="p-4 rounded mb-4 shadow-sm" style={{ background: '#F0F9FF', border: '1px solid #487FFF' }}>
                                    <div className="d-flex align-items-center justify-content-between mb-3">
                                        <h6 className="fw-bold text-primary mb-0 d-flex align-items-center">
                                            <i className="ri-run-line me-2 fs-4"></i>
                                            COACH
                                        </h6>
                                    </div>
                                    <Row className="g-3 align-items-end">
                                        <Col md={9}>
                                            <label className="small text-muted mb-1 fw-medium">Seleziona Professionista</label>
                                            <Form.Select 
                                                value={selectedMatches.coach} 
                                                onChange={(e) => setSelectedMatches({...selectedMatches, coach: e.target.value})}
                                                className="border-primary-subtle shadow-none"
                                            >
                                                <option value="">-- Scegli Coach --</option>
                                                {aiMatches?.coach?.map(p => (
                                                    <option key={p.id} value={p.id}>
                                                        {p.name} (Match: {p.score}%)
                                                    </option>
                                                ))}
                                                <option disabled>──────────</option>
                                                {professionals.filter(p => !aiMatches?.coach?.find(m => m.id === p.id) && (DEPT_ROLE_MAP[p.department_id] === 'coach')).map(p => (
                                                    <option key={p.id} value={p.id}>{p.name}</option>
                                                ))}
                                            </Form.Select>
                                        </Col>
                                        <Col md={3}>
                                            <Button 
                                                variant="primary" 
                                                className="w-100 fw-bold shadow-sm"
                                                onClick={() => handleConfirmAssignment('coach')}
                                                disabled={loading || !selectedMatches.coach}
                                            >
                                                <i className="ri-check-line me-1"></i>Assegna
                                            </Button>
                                        </Col>
                                    </Row>
                                    {selectedMatches.coach && aiMatches?.coach?.find(p => p.id == selectedMatches.coach) && (
                                        <div className="mt-2 bg-white p-2 rounded small text-primary border border-primary-subtle d-flex align-items-center">
                                            <i className="ri-sparkling-line me-2"></i>
                                            <span>Match ideale per: <strong>{aiMatches.coach.find(p => p.id == selectedMatches.coach).match_reasons?.join(', ')}</strong></span>
                                        </div>
                                    )}
                                </div>

                                {/* PSY SECTION */}
                                <div className="p-4 rounded mb-0 shadow-sm" style={{ background: '#FFF7ED', border: '1px solid #F0AD4E' }}>
                                    <div className="d-flex align-items-center justify-content-between mb-3">
                                        <h6 className="fw-bold text-warning mb-0 d-flex align-items-center" style={{color: '#D97706 !important'}}>
                                            <i className="ri-mental-health-line me-2 fs-4"></i>
                                            PSICOLOGIA
                                        </h6>
                                    </div>
                                    <Row className="g-3 align-items-end">
                                        <Col md={9}>
                                            <label className="small text-muted mb-1 fw-medium">Seleziona Professionista</label>
                                            <Form.Select 
                                                value={selectedMatches.psychology} 
                                                onChange={(e) => setSelectedMatches({...selectedMatches, psychology: e.target.value})}
                                                className="border-warning-subtle shadow-none"
                                            >
                                                <option value="">-- Scegli Psicologo --</option>
                                                {aiMatches?.psicologia?.map(p => (
                                                    <option key={p.id} value={p.id}>
                                                        {p.name} (Match: {p.score}%)
                                                    </option>
                                                ))}
                                                <option disabled>──────────</option>
                                                {professionals.filter(p => !aiMatches?.psicologia?.find(m => m.id === p.id) && (DEPT_ROLE_MAP[p.department_id] === 'psicologia')).map(p => (
                                                    <option key={p.id} value={p.id}>{p.name}</option>
                                                ))}
                                            </Form.Select>
                                        </Col>
                                        <Col md={3}>
                                            <Button 
                                                variant="warning" 
                                                className="w-100 fw-bold shadow-sm text-white"
                                                onClick={() => handleConfirmAssignment('psychology')}
                                                disabled={loading || !selectedMatches.psychology}
                                            >
                                                <i className="ri-check-line me-1"></i>Assegna
                                            </Button>
                                        </Col>
                                    </Row>
                                    {selectedMatches.psychology && aiMatches?.psicologia?.find(p => p.id == selectedMatches.psychology) && (
                                        <div className="mt-2 bg-white p-2 rounded small text-warning border border-warning-subtle d-flex align-items-center">
                                            <i className="ri-sparkling-line me-2"></i>
                                            <span>Match ideale per: <strong>{aiMatches.psicologia.find(p => p.id == selectedMatches.psychology).match_reasons?.join(', ')}</strong></span>
                                        </div>
                                    )}
                                </div>

                                <div className="mt-4 border-top pt-3">
                                    <label className="form-label small fw-bold text-uppercase text-muted">Note Generali Assegnazione</label>
                                    <Form.Control 
                                        as="textarea" 
                                        rows={2} 
                                        placeholder="Note opzionali per tutto il team..."
                                        value={assignmentNotes}
                                        onChange={(e) => setAssignmentNotes(e.target.value)}
                                        className="shadow-none border-light-subtle bg-white"
                                        style={{fontSize: '0.85rem'}}
                                    />
                                </div>
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>
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
      `}</style>
    </>
  );
}

export default AssegnazioniAI;

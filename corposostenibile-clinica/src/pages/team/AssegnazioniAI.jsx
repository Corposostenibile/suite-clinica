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
    if (profFilter === 'all') return professionals;
    const roleKey = profFilter; // 'nutrizione', 'coach', etc
    // Devo mappare il department_id al roleKey
    return professionals.filter(p => {
       const mapped = DEPT_ROLE_MAP[p.department_id] || 'other';
       return mapped === roleKey;
    });
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
            <div className="mb-3">
                <ButtonGroup>
                    <Button variant={profFilter === 'all' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('all')}>Tutti</Button>
                    <Button variant={profFilter === 'nutrizione' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('nutrizione')}>Nutrizione</Button>
                    <Button variant={profFilter === 'coach' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('coach')}>Coach</Button>
                    <Button variant={profFilter === 'psicologia' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('psicologia')}>Psicologia</Button>
                </ButtonGroup>
            </div>

            {loadingProfs ? (
                <div className="text-center py-5"><Spinner animation="border" /></div>
            ) : (
                <Row className="g-3">
                    {getFilteredProfessionals().map(prof => (
                        <Col key={prof.id} md={6} lg={4}>
                            <Card className="h-100 border-0 shadow-sm">
                                <Card.Body>
                                    <div className="d-flex align-items-center mb-3">
                                        <div className="me-3">
                                            <img src={prof.avatar_url} alt={prof.name} className="rounded-circle" style={{width: '50px', height: '50px', objectFit: 'cover'}} />
                                        </div>
                                        <div>
                                            <h6 className="mb-0 fw-bold">{prof.name}</h6>
                                            <div className="small text-muted">{DEPT_LABELS[prof.department_id] || 'N/A'}</div>
                                        </div>
                                        <div className="ms-auto">
                                            {prof.is_available ? <Badge bg="success">Disponibile</Badge> : <Badge bg="secondary">Non disp.</Badge>}
                                        </div>
                                    </div>
                                    
                                    <div className="mb-3">
                                        <small className="text-uppercase text-muted d-block mb-2" style={{fontSize: '10px', letterSpacing: '1px'}}>Criteri Specializzazione</small>
                                        <div className="d-flex flex-wrap gap-1">
                                            {Object.entries(prof.criteria || {}).filter(([_, v]) => v).map(([k, _]) => (
                                                <Badge bg="light" text="dark" className="border" key={k}>{k}</Badge>
                                            ))}
                                            {Object.values(prof.criteria || {}).filter(v => v).length === 0 && <em className="text-muted small">Nessun criterio specificato</em>}
                                        </div>
                                    </div>
                                </Card.Body>
                                <Card.Footer className="bg-white border-top-0 pt-0">
                                    <Button variant="outline-primary" size="sm" className="w-100" onClick={() => handleEditCriteria(prof)}>
                                        <i className="ri-settings-3-line me-1"></i>Modifica Criteri
                                    </Button>
                                </Card.Footer>
                            </Card>
                        </Col>
                    ))}
                </Row>
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
             {/* Future: Add "Assign with AI" button here */}
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

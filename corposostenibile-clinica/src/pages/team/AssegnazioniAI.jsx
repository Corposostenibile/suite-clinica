import { useState, useEffect } from 'react';
import { Table, Badge, Card, Spinner, Alert, Button, ButtonGroup, Modal, Tab, Tabs } from 'react-bootstrap';
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

function AssegnazioniAI() {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [stats, setStats] = useState({ total: 0, pending: 0, approved: 0, completed: 0 });

  // Nuovi stati per opportunity data
  const [opportunityData, setOpportunityData] = useState([]);
  const [loadingOpportunity, setLoadingOpportunity] = useState(false);
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);
  const [showOpportunityModal, setShowOpportunityModal] = useState(false);
  const [activeTab, setActiveTab] = useState('webhook-data');

  // Carica le assegnazioni
  const fetchAssignments = async () => {
    setLoading(true);
    setError(null);
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
      console.error('Errore caricamento assegnazioni:', err);
      setError(err.response?.data?.message || 'Errore nel caricamento delle assegnazioni');
    } finally {
      setLoading(false);
    }
  };

  // Carica i dati opportunity dal webhook
  const fetchOpportunityData = async () => {
    setLoadingOpportunity(true);
    try {
      const result = await ghlService.getOpportunityData();
      if (result.success) {
        setOpportunityData(result.data || []);
      }
    } catch (err) {
      console.error('Errore caricamento opportunity data:', err);
    } finally {
      setLoadingOpportunity(false);
    }
  };

  useEffect(() => {
    fetchAssignments();
    fetchOpportunityData();
  }, [selectedStatus]);

  // Auto-refresh ogni 10 secondi per i dati webhook
  useEffect(() => {
    const interval = setInterval(() => {
      fetchOpportunityData();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const openDetails = (assignment) => {
    setSelectedAssignment(assignment);
    setShowModal(true);
  };

  const openOpportunityDetails = (opp) => {
    setSelectedOpportunity(opp);
    setShowOpportunityModal(true);
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

  const AssignmentBadge = ({ assigned, label }) => (
    <Badge bg={assigned ? 'success' : 'light'} text={assigned ? 'white' : 'dark'} className="me-1">
      {assigned ? <i className="ri-check-line me-1"></i> : <i className="ri-close-line me-1"></i>}
      {label}
    </Badge>
  );

  return (
    <>
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1">
            <i className="ri-robot-line me-2 text-primary"></i>
            Assegnazioni AI
          </h4>
          <p className="text-muted mb-0">Dati ricevuti da Go High Level per assegnazioni intelligenti</p>
        </div>
        <Button variant="outline-primary" onClick={() => { fetchAssignments(); fetchOpportunityData(); }} disabled={loading || loadingOpportunity}>
          <i className={`ri-refresh-line me-1 ${(loading || loadingOpportunity) ? 'spin' : ''}`}></i>
          Aggiorna
        </Button>
      </div>

      {/* Tabs */}
      <Tabs activeKey={activeTab} onSelect={(k) => setActiveTab(k)} className="mb-4">
        {/* TAB 1: Dati Webhook GHL */}
        <Tab eventKey="webhook-data" title={<><i className="ri-webhook-line me-2"></i>Dati Webhook ({opportunityData.length})</>}>
          {/* Stats Cards per Webhook */}
          <div className="row g-3 mb-4">
            <div className="col-6 col-md-3">
              <Card className="border-0 shadow-sm h-100 bg-gradient" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                <Card.Body className="text-center text-white">
                  <div className="display-6 fw-bold">{opportunityData.length}</div>
                  <div className="small opacity-75">Webhook Ricevuti</div>
                </Card.Body>
              </Card>
            </div>
            <div className="col-6 col-md-3">
              <Card className="border-0 shadow-sm h-100">
                <Card.Body className="text-center">
                  <div className="display-6 fw-bold text-success">
                    <i className="ri-check-double-line"></i>
                  </div>
                  <div className="text-muted small">Endpoint Attivo</div>
                </Card.Body>
              </Card>
            </div>
            <div className="col-6 col-md-6">
              <Card className="border-0 shadow-sm h-100">
                <Card.Body>
                  <div className="small text-muted mb-1">URL Webhook:</div>
                  <code className="bg-light p-2 rounded d-block" style={{ fontSize: '12px' }}>
                    http://161.97.116.63:5001/ghl/webhook/opportunity-data
                  </code>
                </Card.Body>
              </Card>
            </div>
          </div>

          {/* Tabella Dati Webhook */}
          <Card className="border-0 shadow-sm">
            <Card.Header className="bg-white border-0 py-3">
              <div className="d-flex align-items-center justify-content-between">
                <h5 className="mb-0">
                  <i className="ri-file-list-3-line me-2 text-primary"></i>
                  Clienti Ricevuti da GHL
                </h5>
                <small className="text-muted">
                  <i className="ri-refresh-line me-1"></i>
                  Auto-aggiornamento ogni 10s
                </small>
              </div>
            </Card.Header>
            <Card.Body className="p-0">
              {loadingOpportunity && opportunityData.length === 0 ? (
                <div className="text-center py-5">
                  <Spinner animation="border" variant="primary" />
                  <p className="text-muted mt-2">Caricamento dati webhook...</p>
                </div>
              ) : opportunityData.length === 0 ? (
                <div className="text-center py-5">
                  <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                       style={{ width: '100px', height: '100px' }}>
                    <i className="ri-webhook-line text-muted" style={{ fontSize: '48px' }}></i>
                  </div>
                  <h5 className="text-muted">Nessun dato ricevuto</h5>
                  <p className="text-muted mb-3">
                    I dati arriveranno automaticamente quando GHL invierà un webhook
                  </p>
                  <div className="bg-light rounded p-3 mx-auto" style={{ maxWidth: '500px' }}>
                    <p className="small mb-2"><strong>Configura GHL per inviare a:</strong></p>
                    <code>POST http://161.97.116.63:5001/ghl/webhook/opportunity-data</code>
                    <p className="small mt-2 mb-0 text-muted">
                      Campi: nome, storia, pacchetto, durata
                    </p>
                  </div>
                </div>
              ) : (
                <Table responsive hover className="mb-0">
                  <thead className="bg-light">
                    <tr>
                      <th style={{ width: '60px' }}>#</th>
                      <th>Nome Cliente</th>
                      <th>Pacchetto</th>
                      <th>Durata</th>
                      <th>Ricevuto</th>
                      <th className="text-end">Azioni</th>
                    </tr>
                  </thead>
                  <tbody>
                    {opportunityData.map((opp) => (
                      <tr key={opp.id}>
                        <td>
                          <Badge bg="primary" pill>{opp.id}</Badge>
                        </td>
                        <td>
                          <div className="fw-semibold">{opp.nome}</div>
                          {opp.storia && (
                            <small className="text-muted d-block" style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {opp.storia.substring(0, 50)}...
                            </small>
                          )}
                        </td>
                        <td>
                          <Badge bg="info" className="fw-normal">{opp.pacchetto}</Badge>
                        </td>
                        <td>
                          <span className="fw-semibold">{opp.durata}</span>
                          <small className="text-muted ms-1">giorni</small>
                        </td>
                        <td>
                          <small className="text-muted">{formatDate(opp.received_at)}</small>
                        </td>
                        <td className="text-end">
                          <Button
                            variant="outline-primary"
                            size="sm"
                            onClick={() => openOpportunityDetails(opp)}
                          >
                            <i className="ri-eye-line me-1"></i>
                            Dettagli
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

        {/* TAB 2: Assegnazioni Esistenti */}
        <Tab eventKey="assignments" title={<><i className="ri-user-star-line me-2"></i>Assegnazioni ({stats.total})</>}>
          {/* Stats Cards */}
          <div className="row g-3 mb-4">
            <div className="col-6 col-md-3">
              <Card className="border-0 shadow-sm h-100">
                <Card.Body className="text-center">
                  <div className="display-6 fw-bold text-primary">{stats.total}</div>
                  <div className="text-muted small">Totale</div>
                </Card.Body>
              </Card>
            </div>
            <div className="col-6 col-md-3">
              <Card className="border-0 shadow-sm h-100">
                <Card.Body className="text-center">
                  <div className="display-6 fw-bold text-warning">{stats.pending}</div>
                  <div className="text-muted small">In attesa</div>
                </Card.Body>
              </Card>
            </div>
            <div className="col-6 col-md-3">
              <Card className="border-0 shadow-sm h-100">
                <Card.Body className="text-center">
                  <div className="display-6 fw-bold text-info">{stats.approved}</div>
                  <div className="text-muted small">Approvati</div>
                </Card.Body>
              </Card>
            </div>
            <div className="col-6 col-md-3">
              <Card className="border-0 shadow-sm h-100">
                <Card.Body className="text-center">
                  <div className="display-6 fw-bold text-success">{stats.completed}</div>
                  <div className="text-muted small">Completati</div>
                </Card.Body>
              </Card>
            </div>
          </div>

          {/* Filtri */}
          <Card className="border-0 shadow-sm mb-4">
            <Card.Body className="py-2">
              <div className="d-flex align-items-center gap-2 flex-wrap">
                <span className="text-muted small me-2">Filtra per stato:</span>
                <ButtonGroup size="sm">
                  <Button variant={selectedStatus === 'all' ? 'primary' : 'outline-primary'} onClick={() => setSelectedStatus('all')}>Tutti</Button>
                  <Button variant={selectedStatus === 'pending_finance' ? 'warning' : 'outline-warning'} onClick={() => setSelectedStatus('pending_finance')}>In attesa Finance</Button>
                  <Button variant={selectedStatus === 'pending_assignment' ? 'info' : 'outline-info'} onClick={() => setSelectedStatus('pending_assignment')}>Da assegnare</Button>
                  <Button variant={selectedStatus === 'completed' ? 'success' : 'outline-success'} onClick={() => setSelectedStatus('completed')}>Completati</Button>
                </ButtonGroup>
              </div>
            </Card.Body>
          </Card>

          {error && (
            <Alert variant="danger" dismissible onClose={() => setError(null)}>
              <i className="ri-error-warning-line me-2"></i>{error}
            </Alert>
          )}

          {/* Tabella Assegnazioni */}
          <Card className="border-0 shadow-sm">
            <Card.Body className="p-0">
              {loading ? (
                <div className="text-center py-5">
                  <Spinner animation="border" variant="primary" />
                  <p className="text-muted mt-2">Caricamento assegnazioni...</p>
                </div>
              ) : assignments.length === 0 ? (
                <div className="text-center py-5">
                  <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3" style={{ width: '80px', height: '80px' }}>
                    <i className="ri-inbox-line text-muted" style={{ fontSize: '36px' }}></i>
                  </div>
                  <h5 className="text-muted">Nessuna assegnazione</h5>
                  <p className="text-muted mb-0">Le nuove assegnazioni arriveranno automaticamente da Go High Level</p>
                </div>
              ) : (
                <Table responsive hover className="mb-0">
                  <thead className="bg-light">
                    <tr>
                      <th>ID</th>
                      <th>Cliente</th>
                      <th>Stato</th>
                      <th>Finance</th>
                      <th>Professionisti</th>
                      <th>Data</th>
                      <th className="text-end">Azioni</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assignments.map((assignment) => (
                      <tr key={assignment.id}>
                        <td className="fw-medium">#{assignment.id}</td>
                        <td>
                          <div className="fw-medium">{assignment.cliente_nome || 'N/D'}</div>
                          <small className="text-muted">ID: {assignment.cliente_id}</small>
                        </td>
                        <td><StatusBadge status={assignment.status} /></td>
                        <td>
                          {assignment.finance_approved ? (
                            <Badge bg="success"><i className="ri-check-line me-1"></i>Approvato</Badge>
                          ) : (
                            <Badge bg="warning"><i className="ri-time-line me-1"></i>In attesa</Badge>
                          )}
                        </td>
                        <td>
                          <div className="d-flex gap-1 flex-wrap">
                            <AssignmentBadge assigned={assignment.nutrizionista_assigned} label="Nutri" />
                            <AssignmentBadge assigned={assignment.coach_assigned} label="Coach" />
                            <AssignmentBadge assigned={assignment.psicologa_assigned} label="Psi" />
                          </div>
                        </td>
                        <td><small>{formatDate(assignment.created_at)}</small></td>
                        <td className="text-end">
                          <Button variant="outline-primary" size="sm" onClick={() => openDetails(assignment)}>
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
      </Tabs>

      {/* Modal Dettagli Opportunity */}
      <Modal show={showOpportunityModal} onHide={() => setShowOpportunityModal(false)} size="lg">
        <Modal.Header closeButton className="bg-primary text-white">
          <Modal.Title>
            <i className="ri-user-line me-2"></i>
            Dettagli Cliente #{selectedOpportunity?.id}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedOpportunity && (
            <div className="row g-4">
              {/* Nome */}
              <div className="col-12">
                <div className="bg-light rounded p-3">
                  <h6 className="text-muted mb-2"><i className="ri-user-3-line me-2"></i>Nome Cliente</h6>
                  <h4 className="mb-0">{selectedOpportunity.nome}</h4>
                </div>
              </div>

              {/* Pacchetto e Durata */}
              <div className="col-md-6">
                <div className="border rounded p-3 h-100">
                  <h6 className="text-muted mb-2"><i className="ri-shopping-bag-line me-2"></i>Pacchetto</h6>
                  <Badge bg="info" className="fs-6">{selectedOpportunity.pacchetto}</Badge>
                </div>
              </div>
              <div className="col-md-6">
                <div className="border rounded p-3 h-100">
                  <h6 className="text-muted mb-2"><i className="ri-calendar-line me-2"></i>Durata</h6>
                  <span className="fs-4 fw-bold text-primary">{selectedOpportunity.durata}</span>
                  <span className="text-muted ms-2">giorni</span>
                </div>
              </div>

              {/* Storia */}
              <div className="col-12">
                <div className="border rounded p-3">
                  <h6 className="text-muted mb-2"><i className="ri-file-text-line me-2"></i>Storia del Cliente</h6>
                  <div className="bg-light p-3 rounded" style={{ maxHeight: '300px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                    {selectedOpportunity.storia || <em className="text-muted">Nessuna storia fornita</em>}
                  </div>
                </div>
              </div>

              {/* Metadata */}
              <div className="col-12">
                <hr />
                <div className="d-flex justify-content-between text-muted small">
                  <span><i className="ri-time-line me-1"></i>Ricevuto: {formatDate(selectedOpportunity.received_at)}</span>
                  <span><i className="ri-global-line me-1"></i>IP: {selectedOpportunity.ip_address}</span>
                </div>
              </div>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowOpportunityModal(false)}>
            Chiudi
          </Button>
          <Button variant="success">
            <i className="ri-user-add-line me-1"></i>
            Crea Cliente
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Modal Dettagli Assegnazione */}
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            <i className="ri-user-line me-2"></i>
            Dettagli Assegnazione #{selectedAssignment?.id}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedAssignment && (
            <div className="row g-3">
              <div className="col-md-6">
                <h6 className="text-muted mb-2">Cliente</h6>
                <p className="fw-medium mb-1">{selectedAssignment.cliente_nome || 'N/D'}</p>
                <small className="text-muted">ID Cliente: {selectedAssignment.cliente_id}</small>
              </div>
              <div className="col-md-6">
                <h6 className="text-muted mb-2">Stato</h6>
                <StatusBadge status={selectedAssignment.status} />
              </div>
              <div className="col-md-6">
                <h6 className="text-muted mb-2">Approvazione Finance</h6>
                {selectedAssignment.finance_approved ? (
                  <Badge bg="success" className="fs-6"><i className="ri-check-line me-1"></i>Approvato</Badge>
                ) : (
                  <Badge bg="warning" className="fs-6"><i className="ri-time-line me-1"></i>In attesa verifica</Badge>
                )}
              </div>
              <div className="col-md-6">
                <h6 className="text-muted mb-2">Checkup Iniziale</h6>
                {selectedAssignment.checkup_iniziale_fatto ? (
                  <Badge bg="success"><i className="ri-check-line me-1"></i>Completato</Badge>
                ) : (
                  <Badge bg="secondary"><i className="ri-close-line me-1"></i>Non fatto</Badge>
                )}
              </div>
              <div className="col-12">
                <hr />
                <h6 className="text-muted mb-3">Assegnazioni Professionisti</h6>
                <div className="row g-2">
                  <div className="col-md-4">
                    <Card className={`border ${selectedAssignment.nutrizionista_assigned ? 'border-success' : ''}`}>
                      <Card.Body className="text-center py-3">
                        <i className={`ri-heart-pulse-line fs-3 ${selectedAssignment.nutrizionista_assigned ? 'text-success' : 'text-muted'}`}></i>
                        <div className="fw-medium mt-2">Nutrizionista</div>
                        <small className={selectedAssignment.nutrizionista_assigned ? 'text-success' : 'text-muted'}>
                          {selectedAssignment.nutrizionista_assigned ? 'Assegnato' : 'Non assegnato'}
                        </small>
                      </Card.Body>
                    </Card>
                  </div>
                  <div className="col-md-4">
                    <Card className={`border ${selectedAssignment.coach_assigned ? 'border-success' : ''}`}>
                      <Card.Body className="text-center py-3">
                        <i className={`ri-run-line fs-3 ${selectedAssignment.coach_assigned ? 'text-success' : 'text-muted'}`}></i>
                        <div className="fw-medium mt-2">Coach</div>
                        <small className={selectedAssignment.coach_assigned ? 'text-success' : 'text-muted'}>
                          {selectedAssignment.coach_assigned ? 'Assegnato' : 'Non assegnato'}
                        </small>
                      </Card.Body>
                    </Card>
                  </div>
                  <div className="col-md-4">
                    <Card className={`border ${selectedAssignment.psicologa_assigned ? 'border-success' : ''}`}>
                      <Card.Body className="text-center py-3">
                        <i className={`ri-mental-health-line fs-3 ${selectedAssignment.psicologa_assigned ? 'text-success' : 'text-muted'}`}></i>
                        <div className="fw-medium mt-2">Psicologa</div>
                        <small className={selectedAssignment.psicologa_assigned ? 'text-success' : 'text-muted'}>
                          {selectedAssignment.psicologa_assigned ? 'Assegnata' : 'Non assegnata'}
                        </small>
                      </Card.Body>
                    </Card>
                  </div>
                </div>
              </div>
              <div className="col-12">
                <hr />
                <small className="text-muted">Creato il: {formatDate(selectedAssignment.created_at)}</small>
              </div>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>Chiudi</Button>
          <Button variant="primary"><i className="ri-edit-line me-1"></i>Gestisci Assegnazione</Button>
        </Modal.Footer>
      </Modal>

      <style>{`
        .spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </>
  );
}

export default AssegnazioniAI;

import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import trialUserService from '../../services/trialUserService';

function AssignClients() {
  const { userId } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [trialUser, setTrialUser] = useState(null);
  const [clients, setClients] = useState([]);
  const [search, setSearch] = useState('');
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 10,
    total: 0,
    pages: 1,
  });

  const [selectedClients, setSelectedClients] = useState([]);
  const [notes, setNotes] = useState('');

  const fetchUser = useCallback(async () => {
    try {
      const result = await trialUserService.get(userId);
      if (result.success) {
        setTrialUser(result.trial_user);
      } else {
        setError('Utente non trovato');
      }
    } catch (err) {
      console.error('Error fetching user:', err);
      setError('Errore nel caricamento utente');
    }
  }, [userId]);

  const fetchClients = useCallback(async () => {
    try {
      const result = await trialUserService.getAvailableClients(
        userId,
        search,
        pagination.page,
        pagination.per_page
      );
      if (result.success) {
        setClients(result.clients);
        setPagination((prev) => ({
          ...prev,
          total: result.pagination?.total || 0,
          pages: result.pagination?.pages || 1,
        }));
      }
    } catch (err) {
      console.error('Error fetching clients:', err);
    }
  }, [userId, search, pagination.page, pagination.per_page]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await fetchUser();
      await fetchClients();
      setLoading(false);
    };
    init();
  }, [fetchUser, fetchClients]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setPagination((prev) => ({ ...prev, page: 1 }));
      fetchClients();
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const toggleClient = (client) => {
    setSelectedClients((prev) => {
      const exists = prev.find((c) => c.id === client.id);
      if (exists) {
        return prev.filter((c) => c.id !== client.id);
      }
      return [...prev, client];
    });
  };

  const selectAll = () => {
    const newClients = clients.filter(
      (c) => !selectedClients.find((s) => s.id === c.id)
    );
    setSelectedClients((prev) => [...prev, ...newClients]);
  };

  const deselectAll = () => {
    setSelectedClients([]);
  };

  const handleAssign = async () => {
    if (selectedClients.length === 0) {
      setError('Seleziona almeno un cliente');
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const clientIds = selectedClients.map((c) => c.id);
      const result = await trialUserService.assignClients(userId, clientIds, notes);

      if (result.success) {
        setSuccess(`${result.assigned_count || selectedClients.length} clienti assegnati con successo!`);
        setSelectedClients([]);
        setNotes('');
        await fetchClients();
        setTimeout(() => {
          navigate(`/in-prova/${userId}`);
        }, 1500);
      } else {
        setError(result.error || 'Errore nell\'assegnazione');
      }
    } catch (err) {
      console.error('Error assigning clients:', err);
      setError('Errore nell\'assegnazione dei clienti');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Caricamento...</span>
        </div>
      </div>
    );
  }

  if (!trialUser) {
    return (
      <div className="alert alert-danger d-flex align-items-center">
        <i className="ri-error-warning-line me-2 fs-4"></i>
        <div className="flex-grow-1">Utente non trovato</div>
        <Link to="/in-prova" className="btn btn-sm btn-outline-danger">
          Torna alla Lista
        </Link>
      </div>
    );
  }

  return (
    <>
      {/* Page Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1">Assegna Clienti</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/in-prova">In Prova</Link>
              </li>
              <li className="breadcrumb-item">
                <Link to={`/in-prova/${userId}`}>{trialUser.full_name}</Link>
              </li>
              <li className="breadcrumb-item active">Assegna Clienti</li>
            </ol>
          </nav>
        </div>
        <Link to={`/in-prova/${userId}`} className="btn btn-outline-secondary">
          <i className="ri-arrow-left-line me-1"></i>
          Torna al Dettaglio
        </Link>
      </div>

      {/* Alerts */}
      {error && (
        <div className="alert alert-danger alert-dismissible fade show" role="alert">
          <i className="ri-error-warning-line me-2"></i>
          {error}
          <button type="button" className="btn-close" onClick={() => setError(null)}></button>
        </div>
      )}
      {success && (
        <div className="alert alert-success alert-dismissible fade show" role="alert">
          <i className="ri-check-line me-2"></i>
          {success}
          <button type="button" className="btn-close" onClick={() => setSuccess(null)}></button>
        </div>
      )}

      {/* Stage 1 Warning */}
      {trialUser.trial_stage === 1 && (
        <div className="alert alert-warning">
          <i className="ri-alert-line me-2"></i>
          <strong>Attenzione:</strong> Questo professionista è ancora in Stage 1 (Training).
          Promuovilo allo Stage 2 per permettergli di accedere ai clienti assegnati.
        </div>
      )}

      <div className="row g-4">
        {/* Left: Available Clients */}
        <div className="col-lg-8">
          <div className="card shadow-sm border-0">
            <div className="card-header bg-transparent border-bottom">
              <div className="d-flex align-items-center justify-content-between flex-wrap gap-3">
                <h6 className="mb-0">
                  Clienti Disponibili
                  <span className="badge bg-primary-subtle text-primary ms-2">
                    {pagination.total}
                  </span>
                </h6>
                <div className="d-flex gap-2 align-items-center">
                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={selectAll}
                  >
                    <i className="ri-checkbox-multiple-line me-1"></i>
                    Tutti
                  </button>
                  <button
                    className="btn btn-sm btn-outline-secondary"
                    onClick={deselectAll}
                  >
                    Deseleziona
                  </button>
                  <div className="position-relative" style={{ width: '220px' }}>
                    <i className="ri-search-line position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}></i>
                    <input
                      type="text"
                      className="form-control bg-light border-0"
                      placeholder="Cerca cliente..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      style={{ paddingLeft: '36px' }}
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="card-body">
              {clients.length === 0 ? (
                <div className="text-center py-5">
                  <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                       style={{ width: '64px', height: '64px' }}>
                    <i className="ri-user-search-line text-muted fs-3"></i>
                  </div>
                  <p className="text-muted mb-0">
                    {search ? 'Nessun cliente trovato' : 'Nessun cliente disponibile'}
                  </p>
                </div>
              ) : (
                <>
                  <div className="table-responsive" style={{ margin: '0 -1rem' }}>
                    <table className="table table-hover mb-0">
                      <thead style={{
                        background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
                        borderBottom: '2px solid #e2e8f0',
                      }}>
                        <tr>
                          <th style={{ padding: '12px 16px', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#64748b', borderBottom: 'none', width: '40px' }}></th>
                          <th style={{ padding: '12px 16px', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#64748b', borderBottom: 'none' }}>Nome</th>
                          <th style={{ padding: '12px 16px', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#64748b', borderBottom: 'none' }}>Email</th>
                          <th style={{ padding: '12px 16px', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: '#64748b', borderBottom: 'none' }}>Programma</th>
                        </tr>
                      </thead>
                      <tbody>
                        {clients.map((client) => {
                          const isSelected = selectedClients.find((c) => c.id === client.id);
                          return (
                            <tr
                              key={client.id}
                              onClick={() => toggleClient(client)}
                              style={{
                                cursor: 'pointer',
                                background: isSelected ? '#f0fdf4' : 'transparent',
                              }}
                            >
                              <td style={{ padding: '12px 16px', borderBottom: '1px solid #f1f5f9', verticalAlign: 'middle' }}>
                                <div className="form-check mb-0">
                                  <input
                                    type="checkbox"
                                    className="form-check-input"
                                    checked={!!isSelected}
                                    readOnly
                                    style={{ cursor: 'pointer' }}
                                  />
                                </div>
                              </td>
                              <td style={{ padding: '12px 16px', fontSize: '14px', color: '#334155', borderBottom: '1px solid #f1f5f9', verticalAlign: 'middle' }}>
                                <span style={{ fontWeight: 600, color: isSelected ? '#16a34a' : '#334155' }}>
                                  {client.nome_cognome || `${client.nome || ''} ${client.cognome || ''}`}
                                </span>
                              </td>
                              <td style={{ padding: '12px 16px', fontSize: '14px', color: '#64748b', borderBottom: '1px solid #f1f5f9', verticalAlign: 'middle' }}>
                                {client.email || <span style={{ color: '#cbd5e1' }}>—</span>}
                              </td>
                              <td style={{ padding: '12px 16px', fontSize: '14px', borderBottom: '1px solid #f1f5f9', verticalAlign: 'middle' }}>
                                {client.pacchetto ? (
                                  <span className="badge" style={{
                                    padding: '6px 12px',
                                    borderRadius: '6px',
                                    fontSize: '11px',
                                    fontWeight: 600,
                                    background: 'linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)',
                                    color: '#0369a1',
                                  }}>
                                    {client.pacchetto}
                                  </span>
                                ) : (
                                  <span style={{ color: '#cbd5e1' }}>—</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {pagination.pages > 1 && (
                    <div className="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                      <span style={{ color: '#64748b', fontSize: '14px' }}>
                        Pagina <strong style={{ color: '#334155' }}>{pagination.page}</strong> di{' '}
                        <strong style={{ color: '#334155' }}>{pagination.pages}</strong>
                        <span className="ms-2" style={{ color: '#94a3b8' }}>•</span>
                        <span className="ms-2">{pagination.total} risultati</span>
                      </span>
                      <nav>
                        <ul className="pagination mb-0" style={{ gap: '4px' }}>
                          <li className={`page-item ${pagination.page === 1 ? 'disabled' : ''}`}>
                            <button
                              className="page-link"
                              onClick={() => setPagination((prev) => ({ ...prev, page: prev.page - 1 }))}
                              disabled={pagination.page === 1}
                              style={{ borderRadius: '8px', border: '1px solid #e2e8f0', color: pagination.page === 1 ? '#cbd5e1' : '#64748b', padding: '8px 12px' }}
                            >
                              <i className="ri-arrow-left-s-line"></i>
                            </button>
                          </li>
                          {[...Array(Math.min(5, pagination.pages))].map((_, i) => {
                            let pageNum;
                            if (pagination.pages <= 5) {
                              pageNum = i + 1;
                            } else if (pagination.page <= 3) {
                              pageNum = i + 1;
                            } else if (pagination.page >= pagination.pages - 2) {
                              pageNum = pagination.pages - 4 + i;
                            } else {
                              pageNum = pagination.page - 2 + i;
                            }
                            const isActive = pagination.page === pageNum;
                            return (
                              <li key={pageNum} className="page-item">
                                <button
                                  className="page-link"
                                  onClick={() => setPagination((prev) => ({ ...prev, page: pageNum }))}
                                  style={{
                                    borderRadius: '8px',
                                    border: isActive ? 'none' : '1px solid #e2e8f0',
                                    background: isActive ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' : 'transparent',
                                    color: isActive ? '#fff' : '#64748b',
                                    padding: '8px 14px',
                                    fontWeight: isActive ? 600 : 400,
                                    minWidth: '40px',
                                  }}
                                >
                                  {pageNum}
                                </button>
                              </li>
                            );
                          })}
                          <li className={`page-item ${pagination.page === pagination.pages ? 'disabled' : ''}`}>
                            <button
                              className="page-link"
                              onClick={() => setPagination((prev) => ({ ...prev, page: prev.page + 1 }))}
                              disabled={pagination.page === pagination.pages}
                              style={{ borderRadius: '8px', border: '1px solid #e2e8f0', color: pagination.page === pagination.pages ? '#cbd5e1' : '#64748b', padding: '8px 12px' }}
                            >
                              <i className="ri-arrow-right-s-line"></i>
                            </button>
                          </li>
                        </ul>
                      </nav>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right: Selected Clients & Actions */}
        <div className="col-lg-4">
          <div className="card shadow-sm border-0" style={{ position: 'sticky', top: '20px' }}>
            <div className="card-header bg-transparent border-bottom">
              <h6 className="mb-0">
                Clienti Selezionati
                <span className="badge bg-success-subtle text-success ms-2">
                  {selectedClients.length}
                </span>
              </h6>
            </div>
            <div className="card-body">
              {selectedClients.length === 0 ? (
                <div className="text-center py-4">
                  <div className="bg-light rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                       style={{ width: '48px', height: '48px' }}>
                    <i className="ri-user-add-line text-muted"></i>
                  </div>
                  <p className="text-muted mb-0 small">
                    Seleziona i clienti dalla tabella
                  </p>
                </div>
              ) : (
                <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  {selectedClients.map((client) => (
                    <div
                      key={client.id}
                      className="d-flex align-items-center justify-content-between p-2 rounded-2 mb-2"
                      style={{ background: '#f8fafc' }}
                    >
                      <div className="d-flex align-items-center gap-2">
                        <div
                          className="rounded-circle bg-success text-white d-flex align-items-center justify-content-center"
                          style={{ width: '28px', height: '28px', fontSize: '11px', fontWeight: 700 }}
                        >
                          {(client.nome_cognome || client.nome || '?')[0]?.toUpperCase()}
                        </div>
                        <span className="fw-medium" style={{ fontSize: '13px' }}>
                          {client.nome_cognome || `${client.nome || ''} ${client.cognome || ''}`}
                        </span>
                      </div>
                      <button
                        className="btn btn-sm text-danger p-1"
                        onClick={() => toggleClient(client)}
                        title="Rimuovi"
                      >
                        <i className="ri-close-line"></i>
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Notes */}
              <div className="mt-3">
                <label className="form-label small text-muted">Note (opzionale)</label>
                <textarea
                  className="form-control"
                  rows="3"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Aggiungi note sull'assegnazione..."
                ></textarea>
              </div>
            </div>

            {/* Card Footer */}
            <div className="card-footer bg-transparent border-top">
              <button
                className="btn btn-success w-100"
                onClick={handleAssign}
                disabled={saving || selectedClients.length === 0}
              >
                {saving ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2"></span>
                    Assegnazione...
                  </>
                ) : (
                  <>
                    <i className="ri-user-add-line me-2"></i>
                    Assegna {selectedClients.length} Client{selectedClients.length !== 1 ? 'i' : 'e'}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default AssignClients;

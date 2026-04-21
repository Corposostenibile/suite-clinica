import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import clientiService, { TIPOLOGIA_CHECK_LABELS } from '../../services/clientiService';
import { useAuth } from '../../context/AuthContext';
import { isHealthManagerTeamLeader } from '../../utils/rbacScope';

function TipologiaCheckBulkAssign() {
  const { user } = useAuth();
  const canAccess = useMemo(
    () => Boolean(user?.is_admin || user?.role === 'admin' || isHealthManagerTeamLeader(user)),
    [user],
  );

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [clients, setClients] = useState([]);
  const [search, setSearch] = useState('');
  const [selectedType, setSelectedType] = useState('regolare');
  const [selectedClientIds, setSelectedClientIds] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, pages: 1, total: 0, per_page: 25 });

  const fetchCandidates = useCallback(async () => {
    try {
      const data = await clientiService.getTipologiaCheckCandidates({
        page: pagination.page,
        per_page: pagination.per_page,
        q: search || undefined,
      });
      setClients(data.data || []);
      setPagination((prev) => ({
        ...prev,
        page: data.pagination?.page || prev.page,
        pages: data.pagination?.pages || 1,
        total: data.pagination?.total || 0,
      }));
    } catch (err) {
      setError(err?.response?.data?.description || 'Errore nel caricamento candidati');
    }
  }, [pagination.page, pagination.per_page, search]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await fetchCandidates();
      setLoading(false);
    };
    init();
  }, [fetchCandidates]);

  useEffect(() => {
    const t = setTimeout(() => {
      setPagination((prev) => ({ ...prev, page: 1 }));
      fetchCandidates();
    }, 300);
    return () => clearTimeout(t);
  }, [search]);

  const toggleClient = (clienteId) => {
    setSelectedClientIds((prev) =>
      prev.includes(clienteId) ? prev.filter((id) => id !== clienteId) : [...prev, clienteId],
    );
  };

  const handleAssign = async () => {
    if (!selectedClientIds.length) {
      setError('Seleziona almeno un cliente');
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await clientiService.assignTipologiaCheckBulk(selectedClientIds, selectedType);
      setSuccess(`Aggiornati ${res.updated || 0} clienti. Saltati: ${res.skipped || 0}.`);
      setSelectedClientIds([]);
      await fetchCandidates();
    } catch (err) {
      setError(err?.response?.data?.description || 'Errore nell\'assegnazione massiva');
    } finally {
      setSaving(false);
    }
  };

  if (!canAccess) {
    return <div className="alert alert-danger">Accesso non autorizzato.</div>;
  }

  return (
    <div className="container-fluid p-0">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h4 className="mb-1">Assegnazione massiva tipologia check</h4>
          <p className="text-muted mb-0">Clienti senza tipologia check assegnata</p>
        </div>
        <Link to="/clienti-lista" className="btn btn-outline-secondary">
          <i className="ri-arrow-left-line me-1"></i>Torna lista
        </Link>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="row g-3">
        <div className="col-lg-8">
          <div className="card border-0 shadow-sm">
            <div className="card-header bg-transparent">
              <div className="d-flex justify-content-between align-items-center gap-2">
                <strong>Candidati ({pagination.total})</strong>
                <input
                  type="text"
                  className="form-control"
                  style={{ maxWidth: 260 }}
                  placeholder="Cerca cliente..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>
            <div className="card-body p-0">
              {loading ? (
                <div className="p-4 text-center">Caricamento...</div>
              ) : (
                <table className="table table-hover mb-0">
                  <thead>
                    <tr>
                      <th style={{ width: 44 }}></th>
                      <th>Nome</th>
                      <th>Email</th>
                      <th>Programma</th>
                    </tr>
                  </thead>
                  <tbody>
                    {clients.map((client) => {
                      const clienteId = client.cliente_id || client.clienteId;
                      const isSelected = selectedClientIds.includes(clienteId);
                      return (
                        <tr key={clienteId} onClick={() => toggleClient(clienteId)} style={{ cursor: 'pointer' }}>
                          <td>
                            <input type="checkbox" checked={isSelected} readOnly />
                          </td>
                          <td>{client.nome_cognome || client.nomeCognome}</td>
                          <td>{client.mail || client.email || '-'}</td>
                          <td>{client.programma_attuale || client.programmaAttuale || '-'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-4">
          <div className="card border-0 shadow-sm">
            <div className="card-header bg-transparent">
              <strong>Assegna tipologia</strong>
            </div>
            <div className="card-body">
              <div className="d-grid gap-2 mb-3">
                {Object.entries(TIPOLOGIA_CHECK_LABELS).map(([value, label]) => (
                  <label key={value} className="d-flex align-items-center gap-2">
                    <input
                      type="radio"
                      name="bulk-tipologia-check"
                      checked={selectedType === value}
                      onChange={() => setSelectedType(value)}
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
              <p className="text-muted small mb-3">Selezionati: {selectedClientIds.length}</p>
              <button className="btn btn-success w-100" onClick={handleAssign} disabled={saving || !selectedClientIds.length}>
                {saving ? 'Assegnazione...' : 'Assegna tipologia'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TipologiaCheckBulkAssign;

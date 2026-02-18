import { useEffect, useMemo, useState } from 'react';
import checkService from '../../services/checkService';

function StatusBadge({ check }) {
  if (!check?.assigned) {
    return <span className="badge bg-secondary">Non assegnato</span>;
  }
  if (check.completed) {
    return <span className="badge bg-success">Compilato ({check.response_count || 0})</span>;
  }
  return <span className="badge bg-warning text-dark">Assegnato, non compilato</span>;
}

function CheckAssegnazioniIniziali() {
  const [items, setItems] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, per_page: 20, total: 0, pages: 0 });
  const [meta, setMeta] = useState({ check_1_name: 'Check 1', check_2_name: 'Check 2' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [clientSearch, setClientSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [page, setPage] = useState(1);

  const filters = useMemo(() => ({ clientSearch, status, page, perPage: 20 }), [clientSearch, status, page]);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      setError('');
      try {
        const result = await checkService.getInitialAssignments(filters);
        if (result?.success) {
          setItems(result.items || []);
          setPagination(result.pagination || { page: 1, per_page: 20, total: 0, pages: 0 });
          setMeta(result.meta || { check_1_name: 'Check 1', check_2_name: 'Check 2' });
        } else {
          setError(result?.error || 'Errore nel caricamento');
        }
      } catch (e) {
        setError(e?.response?.data?.error || e.message || 'Errore nel caricamento');
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [filters]);

  const onSubmitFilters = (e) => {
    e.preventDefault();
    setPage(1);
    setClientSearch((prev) => prev.trim());
  };

  return (
    <div>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="fw-bold mb-1">Assegnazioni Check Iniziali</h4>
          <p className="text-muted mb-0">Stato compilazione per lead di {meta.check_1_name} e {meta.check_2_name}</p>
        </div>
        <span className="badge bg-primary">Lead totali: {pagination.total || 0}</span>
      </div>

      <form className="card border-0 mb-4" onSubmit={onSubmitFilters}>
        <div className="card-body">
          <div className="row g-3 align-items-end">
            <div className="col-md-6">
              <label className="form-label">Cerca lead</label>
              <input
                type="text"
                className="form-control"
                value={clientSearch}
                onChange={(e) => setClientSearch(e.target.value)}
                placeholder="Nome, cognome o email"
              />
            </div>
            <div className="col-md-3">
              <label className="form-label">Stato</label>
              <select
                className="form-select"
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">Tutti</option>
                <option value="completed_all">Completati entrambi</option>
                <option value="completed_any">Almeno uno compilato</option>
                <option value="pending">Nessuno compilato</option>
              </select>
            </div>
            <div className="col-md-3 d-grid">
              <button className="btn btn-primary" type="submit">Filtra</button>
            </div>
          </div>
        </div>
      </form>

      <div className="card border-0">
        <div className="table-responsive">
          <table className="table align-middle mb-0">
            <thead>
              <tr>
                <th>Lead</th>
                <th>{meta.check_1_name}</th>
                <th>{meta.check_2_name}</th>
                <th>Ultima attività</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="4" className="text-center py-5">Caricamento...</td></tr>
              ) : error ? (
                <tr><td colSpan="4" className="text-center text-danger py-5">{error}</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan="4" className="text-center text-muted py-5">Nessun lead trovato.</td></tr>
              ) : (
                items.map((item) => (
                  <tr key={item.lead_id}>
                    <td>
                      <div className="fw-semibold">{item.lead_name || '-'}</div>
                      <div className="text-muted small">{item.lead_email || '-'}</div>
                    </td>
                    <td><StatusBadge check={item.check_1} /></td>
                    <td><StatusBadge check={item.check_2} /></td>
                    <td>{item.latest_activity_at ? new Date(item.latest_activity_at).toLocaleString('it-IT') : '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {!loading && !error && pagination.pages > 1 && (
        <div className="d-flex justify-content-between align-items-center mt-3">
          <button
            className="btn btn-outline-secondary"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Precedente
          </button>
          <div className="text-muted small">Pagina {pagination.page} di {pagination.pages}</div>
          <button
            className="btn btn-outline-secondary"
            disabled={page >= pagination.pages}
            onClick={() => setPage((p) => Math.min(pagination.pages, p + 1))}
          >
            Successiva
          </button>
        </div>
      )}
    </div>
  );
}

export default CheckAssegnazioniIniziali;

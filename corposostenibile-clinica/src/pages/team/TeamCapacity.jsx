import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import teamService, { SPECIALTY_LABELS } from '../../services/teamService';

function TeamCapacity() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [canEdit, setCanEdit] = useState(false);
  const [editingValues, setEditingValues] = useState({});
  const [savingByUserId, setSavingByUserId] = useState({});

  const fetchCapacity = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await teamService.getProfessionalCapacity();
      const list = data.rows || [];
      setRows(list);
      setCanEdit(Boolean(data.can_edit));
      setEditingValues(
        list.reduce((acc, row) => {
          acc[row.user_id] = row.capienza_contrattuale;
          return acc;
        }, {})
      );
    } catch (err) {
      setRows([]);
      const status = err?.response?.status;
      if (status === 403) {
        setError('Non hai i permessi per visualizzare la tabella capienza professionisti.');
      } else {
        setError(err?.response?.data?.message || 'Errore nel caricamento della tabella capienza.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCapacity();
  }, [fetchCapacity]);

  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) => {
      const name = (row.full_name || '').toLowerCase();
      const specialty = (SPECIALTY_LABELS[row.specialty] || row.specialty || '').toLowerCase();
      return name.includes(q) || specialty.includes(q);
    });
  }, [rows, search]);

  const isCco = user?.specialty === 'cco';
  const canAccessPage = Boolean(user?.is_admin || user?.role === 'team_leader' || isCco || user?.role === 'admin');

  const handleSave = async (userId) => {
    const value = editingValues[userId];
    if (value === '' || value == null || Number.isNaN(Number(value))) return;

    setSavingByUserId((prev) => ({ ...prev, [userId]: true }));
    try {
      const data = await teamService.updateProfessionalCapacity(userId, Number(value));
      const updated = data.row;
      setRows((prev) => prev.map((r) => (r.user_id === userId ? updated : r)));
      setEditingValues((prev) => ({ ...prev, [userId]: updated.capienza_contrattuale }));
    } catch (err) {
      alert(err?.response?.data?.message || 'Errore nel salvataggio della capienza contrattuale');
    } finally {
      setSavingByUserId((prev) => ({ ...prev, [userId]: false }));
    }
  };

  if (!canAccessPage) {
    return <div className="alert alert-warning mb-0">Non autorizzato.</div>;
  }

  return (
    <div className="container-fluid p-0">
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4 gap-2">
        <div>
          <h4 className="mb-1">Capienza Professionisti</h4>
          <p className="text-muted mb-0">Nome professionista, capienza contrattuale, clienti assegnati, % capienza</p>
        </div>
        <button className="btn btn-outline-secondary" onClick={fetchCapacity}>
          <i className="ri-refresh-line me-1"></i>
          Aggiorna
        </button>
      </div>

      <div className="card shadow-sm border-0 mb-4">
        <div className="card-body">
          <div className="row g-2 align-items-center">
            <div className="col-lg-6">
              <input
                className="form-control"
                placeholder="Cerca professionista..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="col-lg-6 text-lg-end">
              <small className="text-muted">{filteredRows.length} risultati</small>
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" role="status"></div>
          <p className="text-muted mt-2 mb-0">Caricamento capienze...</p>
        </div>
      ) : error ? (
        <div className="alert alert-danger mb-0">{error}</div>
      ) : filteredRows.length === 0 ? (
        <div className="alert alert-light border mb-0">Nessuna capienza disponibile.</div>
      ) : (
        <div className="card shadow-sm border-0">
          <div className="table-responsive">
            <table className="table align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th>Professionista</th>
                  <th style={{ width: 220 }}>Capienza contrattuale</th>
                  <th>Clienti assegnati</th>
                  <th>% Capienza</th>
                  <th className="text-end">Profilo</th>
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row) => {
                  const isSaving = Boolean(savingByUserId[row.user_id]);
                  return (
                    <tr key={row.user_id}>
                      <td>
                        <div className="fw-medium">{row.full_name}</div>
                        <small className="text-muted">{SPECIALTY_LABELS[row.specialty] || row.specialty || '—'}</small>
                      </td>
                      <td>
                        {canEdit ? (
                          <div className="d-flex gap-2">
                            <input
                              type="number"
                              min="0"
                              className="form-control form-control-sm"
                              value={editingValues[row.user_id] ?? ''}
                              onChange={(e) => {
                                setEditingValues((prev) => ({ ...prev, [row.user_id]: e.target.value }));
                              }}
                            />
                            <button
                              className="btn btn-sm btn-primary"
                              disabled={isSaving}
                              onClick={() => handleSave(row.user_id)}
                            >
                              {isSaving ? '...' : 'Salva'}
                            </button>
                          </div>
                        ) : (
                          <span>{row.capienza_contrattuale}</span>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${row.is_over_capacity ? 'bg-danger' : 'bg-light text-dark border'}`}>
                          {row.clienti_assegnati}
                        </span>
                      </td>
                      <td>
                        <div className="d-flex align-items-center gap-2">
                          <div className="progress" style={{ height: 8, width: 120 }}>
                            <div
                              className={`progress-bar ${row.is_over_capacity ? 'bg-danger' : 'bg-primary'}`}
                              style={{ width: `${Math.min(row.percentuale_capienza || 0, 100)}%` }}
                            />
                          </div>
                          <span className="small fw-medium">{(row.percentuale_capienza || 0).toFixed(1)}%</span>
                        </div>
                      </td>
                      <td className="text-end">
                        <Link className="btn btn-sm btn-outline-primary" to={`/team-dettaglio/${row.user_id}`}>
                          Apri
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default TeamCapacity;

import { useCallback, useEffect, useMemo, useState } from 'react';
import teamService from '../../services/teamService';
import { useAuth } from '../../context/AuthContext';
import { canAccessHmCapacityAdmin } from '../../utils/rbacScope';
import './HmCapacityAdmin.css';

function computeRowMetrics(target, currentAssigned) {
  if (target == null) {
    return { residual: null, percent: null };
  }
  const t = Number(target);
  const current = Number(currentAssigned || 0);
  const residual = t - current;
  const percent = t <= 0 ? 0 : Math.round((current / t) * 10000) / 100;
  return { residual, percent };
}

function HmCapacityAdmin() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [savingById, setSavingById] = useState({});
  const [inputsById, setInputsById] = useState({});

  const canAccess = canAccessHmCapacityAdmin(user);

  const sortedRows = useMemo(
    () => [...rows].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''))),
    [rows],
  );

  const fetchRows = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await teamService.getHmCapacity();
      const list = Array.isArray(data?.rows) ? data.rows : [];
      setRows(list);
      setInputsById(
        list.reduce((acc, row) => {
          acc[row.hm_id] = row.target ?? '';
          return acc;
        }, {}),
      );
    } catch (err) {
      setRows([]);
      setError(err?.response?.data?.message || 'Errore nel caricamento capienza HM.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!canAccess) {
      setLoading(false);
      return;
    }
    fetchRows();
  }, [canAccess, fetchRows]);

  const handleSave = async (hmId) => {
    const raw = inputsById[hmId];
    const previous = rows.find((r) => r.hm_id === hmId);
    if (!previous) return;

    const parsed = raw === '' || raw == null ? null : Number(raw);
    if (parsed !== null && (!Number.isInteger(parsed) || parsed < 0)) {
      setError('Il target deve essere un intero >= 0 oppure vuoto.');
      return;
    }

    const optimisticMetrics = computeRowMetrics(parsed, previous.current_assigned || 0);
    const optimisticRow = {
      ...previous,
      target: parsed,
      ...optimisticMetrics,
    };

    setError('');
    setRows((prev) => prev.map((row) => (row.hm_id === hmId ? optimisticRow : row)));
    setSavingById((prev) => ({ ...prev, [hmId]: true }));

    try {
      const data = await teamService.updateHmCapacityTarget(hmId, parsed);
      const updated = data?.row || optimisticRow;
      setRows((prev) => prev.map((row) => (row.hm_id === hmId ? { ...row, ...updated } : row)));
      setInputsById((prev) => ({ ...prev, [hmId]: updated.target ?? '' }));
    } catch (err) {
      setRows((prev) => prev.map((row) => (row.hm_id === hmId ? previous : row)));
      setInputsById((prev) => ({ ...prev, [hmId]: previous.target ?? '' }));
      setError(err?.response?.data?.message || 'Errore nel salvataggio del target HM.');
    } finally {
      setSavingById((prev) => ({ ...prev, [hmId]: false }));
    }
  };

  if (!canAccess) {
    return <div className="hmc-error">Non autorizzato.</div>;
  }

  return (
    <div className="hmc-container">
      <div className="hmc-header">
        <div>
          <h4>Capienza HM</h4>
          <p className="hmc-subtitle">Gestione target e saturazione Health Manager</p>
        </div>
        <button className="hmc-refresh" onClick={fetchRows} disabled={loading}>Aggiorna</button>
      </div>

      {error && <div className="hmc-alert">{error}</div>}

      {loading ? (
        <div className="hmc-loading">Caricamento...</div>
      ) : (
        <div className="table-responsive">
          <table className="hmc-table">
            <thead>
              <tr>
                <th>HM</th>
                <th style={{ width: 220 }}>Target</th>
                <th>Attivi</th>
                <th>Residuo</th>
                <th>% Occupazione</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((row) => {
                const percent = row.percent ?? null;
                const residual = row.residual ?? null;
                const saving = Boolean(savingById[row.hm_id]);
                return (
                  <tr key={row.hm_id}>
                    <td>{row.name}</td>
                    <td>
                      <div className="hmc-edit">
                        <input
                          type="number"
                          min="0"
                          placeholder="Nessun limite"
                          value={inputsById[row.hm_id] ?? ''}
                          onChange={(e) => setInputsById((prev) => ({ ...prev, [row.hm_id]: e.target.value }))}
                          className="hmc-input"
                        />
                        <button className="hmc-save" disabled={saving} onClick={() => handleSave(row.hm_id)}>
                          {saving ? '...' : 'Salva'}
                        </button>
                      </div>
                    </td>
                    <td><span className="hmc-badge">{row.current_assigned ?? 0}</span></td>
                    <td>{residual == null ? '—' : residual}</td>
                    <td>
                      {percent == null ? (
                        <span>—</span>
                      ) : (
                        <div className="hmc-progress-wrap">
                          <div className="hmc-progress">
                            <div className={`hmc-progress-bar ${percent > 100 ? 'danger' : 'normal'}`} style={{ width: `${Math.min(percent, 100)}%` }} />
                          </div>
                          <span>{Number(percent).toFixed(2)}%</span>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
              {sortedRows.length === 0 && (
                <tr>
                  <td colSpan={5} className="hmc-empty">Nessun Health Manager trovato.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default HmCapacityAdmin;

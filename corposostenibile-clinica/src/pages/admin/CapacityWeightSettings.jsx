import { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import api from '../../services/api';
import './CapacityWeightSettings.css';

function CapacityWeightSettings() {
  const { user } = useOutletContext();
  const [weights, setWeights] = useState({ a: 1, b: 1, c: 1 });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const loadWeights = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/team/capacity-weights');
      if (res.data.success) {
        setWeights(res.data.weights);
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Errore nel caricamento dei pesi' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadWeights(); }, [loadWeights]);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const res = await api.put('/team/capacity-weights', weights);
      if (res.data.success) {
        setWeights(res.data.weights);
        setMessage({ type: 'success', text: 'Pesi aggiornati con successo' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: err?.response?.data?.message || 'Errore nel salvataggio' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="cws-container">
        <div className="cws-loading">
          <div className="cws-spinner"></div>
          <p>Caricamento...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="cws-container">
      <div className="cws-header">
        <div>
          <h4>Pesi Tipologia Capienza</h4>
          <p className="cws-header-sub">
            Configura il valore di ogni tipologia cliente (A, B, C) per il calcolo della capienza ponderata
          </p>
        </div>
      </div>

      {message && (
        <div className={`cws-message ${message.type}`}>
          <i className={message.type === 'success' ? 'ri-check-line' : 'ri-error-warning-line'}></i>
          {message.text}
        </div>
      )}

      <div className="cws-card">
        <form onSubmit={handleSave}>
          <div className="cws-weights-grid">
            {[
              { key: 'a', label: 'Tipologia A', color: '#22c55e' },
              { key: 'b', label: 'Tipologia B', color: '#f59e0b' },
              { key: 'c', label: 'Tipologia C', color: '#ef4444' },
            ].map((item) => (
              <div key={item.key} className="cws-weight-item">
                <div className="cws-weight-label">
                  <span className="cws-type-badge" style={{ background: item.color }}>
                    {item.key.toUpperCase()}
                  </span>
                  <div className="cws-weight-title">{item.label}</div>
                </div>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  className="cws-weight-input"
                  value={weights[item.key] ?? 1}
                  onChange={(e) => setWeights((prev) => ({ ...prev, [item.key]: parseFloat(e.target.value) || 0 }))}
                />
              </div>
            ))}
          </div>

          <div className="cws-info">
            <i className="ri-information-line"></i>
            <span>
              La <strong>capienza ponderata</strong> di un professionista viene calcolata come:
              (N. clienti A × peso A) + (N. clienti B × peso B) + (N. clienti C × peso C)
            </span>
          </div>

          <div className="cws-info" style={{ background: 'rgba(139, 92, 246, 0.06)', borderColor: 'rgba(139, 92, 246, 0.15)' }}>
            <i className="ri-mental-health-line" style={{ color: '#8b5cf6' }}></i>
            <span>
              Per gli <strong>psicologi</strong> il peso è sempre 1 indipendentemente dalla tipologia del cliente.
            </span>
          </div>

          <div className="cws-actions">
            <button type="submit" className="cws-save-btn" disabled={saving}>
              {saving ? 'Salvataggio...' : 'Salva pesi'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CapacityWeightSettings;

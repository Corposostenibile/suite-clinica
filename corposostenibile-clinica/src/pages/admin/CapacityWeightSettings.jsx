import { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import api from '../../services/api';
import './CapacityWeightSettings.css';

const DEFAULT_WEIGHTS = {
  nutrizione: { a: 2, b: 1.5, c: 1, secondario: 0.5 },
  coach: { a: 2, b: 1.5, c: 1, secondario: 0.5 },
};

const AREA_META = {
  nutrizione: {
    label: 'Nutrizione',
    description: 'Pesi usati per nutrizionisti e consulenti alimentari',
  },
  coach: {
    label: 'Coach',
    description: 'Pesi usati per il carico operativo coach',
  },
};

const TYPE_META = [
  { key: 'a', label: 'Tipologia A', color: '#22c55e', desc: 'Supporto piu intenso' },
  { key: 'b', label: 'Tipologia B', color: '#f59e0b', desc: 'Supporto intermedio' },
  { key: 'c', label: 'Tipologia C', color: '#ef4444', desc: 'Supporto standard' },
  { key: 'secondario', label: 'Secondario', color: '#64748b', desc: 'Figura secondaria sul percorso' },
];

function CapacityWeightSettings() {
  useOutletContext();
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [activeArea, setActiveArea] = useState('nutrizione');

  const loadWeights = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/team/capacity-weights');
      if (res.data.success && res.data.weights) {
        setWeights({
          nutrizione: { ...DEFAULT_WEIGHTS.nutrizione, ...(res.data.weights.nutrizione || {}) },
          coach: { ...DEFAULT_WEIGHTS.coach, ...(res.data.weights.coach || {}) },
        });
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
        setWeights({
          nutrizione: { ...DEFAULT_WEIGHTS.nutrizione, ...(res.data.weights.nutrizione || {}) },
          coach: { ...DEFAULT_WEIGHTS.coach, ...(res.data.weights.coach || {}) },
        });
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
            Configura i pesi per area professionale e tipologia di supporto.
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
        <div className="cws-area-tabs">
          {Object.entries(AREA_META).map(([key, area]) => (
            <button
              key={key}
              type="button"
              className={`cws-area-tab${activeArea === key ? ' active' : ''}`}
              onClick={() => setActiveArea(key)}
            >
              {area.label}
            </button>
          ))}
        </div>

        <div className="cws-area-summary">
          <div className="cws-area-title">{AREA_META[activeArea].label}</div>
          <div className="cws-area-desc">{AREA_META[activeArea].description}</div>
        </div>

        <form onSubmit={handleSave}>
          <div className="cws-weights-grid">
            {TYPE_META.map((item) => (
              <div key={`${activeArea}-${item.key}`} className="cws-weight-item">
                <div className="cws-weight-label">
                  <span className="cws-type-badge" style={{ background: item.color }}>
                    {item.key === 'secondario' ? '2nd' : item.key.toUpperCase()}
                  </span>
                  <div>
                    <div className="cws-weight-title">{item.label}</div>
                    <div className="cws-weight-desc">{item.desc}</div>
                  </div>
                </div>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  className="cws-weight-input"
                  value={weights[activeArea]?.[item.key] ?? 0}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value);
                    setWeights((prev) => ({
                      ...prev,
                      [activeArea]: {
                        ...prev[activeArea],
                        [item.key]: Number.isFinite(value) ? value : 0,
                      },
                    }));
                  }}
                />
              </div>
            ))}
          </div>

          <div className="cws-info">
            <i className="ri-information-line"></i>
            <span>
              La <strong>capienza ponderata</strong> viene calcolata per area:
              (A x peso A) + (B x peso B) + (C x peso C) + (secondario x peso secondario).
            </span>
          </div>

          <div className="cws-info cws-info-muted">
            <i className="ri-mental-health-line"></i>
            <span>
              Per gli <strong>psicologi</strong> il peso resta sempre <strong>1</strong>, indipendentemente dalla tipologia.
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

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import publicCheckService from '../../../services/publicCheckService';
import './PublicChecks.css';

const SECTIONS_CONFIG = [
  { id: 'percorso', title: 'Percorso generale', icon: 'ri-compass-3-line', color: '#6366f1' },
  { id: 'aderenza', title: 'Aderenza pratica', icon: 'ri-bar-chart-line', color: '#22c55e' },
  { id: 'corpo', title: 'Ascolto del corpo', icon: 'ri-heart-pulse-line', color: '#ec4899' },
  { id: 'cibo', title: 'Gestione quotidiana del cibo', icon: 'ri-restaurant-line', color: '#f59e0b' },
  { id: 'energia', title: 'Energia', icon: 'ri-flashlight-line', color: '#3b82f6' },
];

const RATING_LABELS = ['', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'];

function ScaleQuestion({ question, value, onChange }) {
  return (
    <div className="check-question-block">
      <p className="check-question-label">{question.label}</p>
      {question.sublabel && (
        <p className="check-question-sublabel">{question.sublabel}</p>
      )}
      <div className="wcl-scale-row">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((num) => (
          <button
            key={num}
            type="button"
            className={`wcl-scale-btn${value === num ? ' selected' : ''}`}
            onClick={() => onChange(question.key, num)}
          >
            {num}
          </button>
        ))}
      </div>
      {value != null && (
        <p className="wcl-scale-selected-label">
          {value === 1 && 'Per niente'}
          {value === 10 && 'Completamente'}
          {value > 1 && value < 10 && `${value}/10`}
        </p>
      )}
    </div>
  );
}

function WeeklyCheckLightForm() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [checkInfo, setCheckInfo] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [formData, setFormData] = useState({});

  useEffect(() => {
    loadCheckInfo();
  }, [token]);

  const loadCheckInfo = async () => {
    try {
      const result = await publicCheckService.getWeeklyLightInfo(token);
      if (result.success) {
        setCheckInfo(result);
        setQuestions(result.questions || []);
      } else {
        setError(result.error || 'Check non trovato');
      }
    } catch (err) {
      console.error('Error loading check info:', err);
      setError('Errore nel caricamento del check');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (key, value) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const missing = questions.filter(
      (q) => q.type === 'scale' && formData[q.key] == null
    );
    if (missing.length > 0) {
      setError(`Rispondi a tutte le domande prima di inviare (${missing.length} mancanti).`);
      return;
    }

    setSubmitting(true);
    try {
      const result = await publicCheckService.submitWeeklyLightCheck(token, formData);
      if (result.success) {
        navigate(`/check/weekly-light/${token}/success`);
      } else {
        setError(result.error || 'Errore nell\'invio');
      }
    } catch (err) {
      console.error('Error submitting:', err);
      setError('Errore nell\'invio del check');
    } finally {
      setSubmitting(false);
    }
  };

  const totalQuestions = questions.filter((q) => q.type === 'scale').length;
  const answered = questions.filter((q) => q.type === 'scale' && formData[q.key] != null).length;
  const progress = totalQuestions > 0 ? Math.round((answered / totalQuestions) * 100) : 0;

  // Group questions by section
  const sectionMap = {};
  questions.forEach((q) => {
    const section = q.section || 'Altro';
    if (!sectionMap[section]) sectionMap[section] = [];
    sectionMap[section].push(q);
  });

  if (loading) {
    return (
      <div className="check-loading">
        <div className="check-loading-spinner" />
        <p>Caricamento check settimanale...</p>
      </div>
    );
  }

  if (error && !checkInfo) {
    return (
      <div className="check-error-page">
        <i className="ri-error-warning-line" />
        <h2>Check non disponibile</h2>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="check-page wcl-page">
      {/* Sticky progress bar */}
      <div className="check-progress-bar-sticky">
        <div className="check-progress-bar-inner">
          <span className="check-progress-label">
            {answered}/{totalQuestions} risposte
          </span>
          <div className="check-progress-track">
            <div
              className="check-progress-fill"
              style={{ width: `${progress}%`, background: '#6366f1' }}
            />
          </div>
          <span className="check-progress-pct">{progress}%</span>
        </div>
      </div>

      <div className="check-container">
        {/* Header */}
        <div className="check-header">
          <div className="wcl-badge">Check Settimanale</div>
          <h1 className="check-title">Come è andata questa settimana?</h1>
          {checkInfo?.cliente?.nome_cognome && (
            <p className="check-subtitle">Ciao {checkInfo.cliente.nome_cognome.split(' ')[0]} 👋</p>
          )}
          <p className="check-intro">
            5 domande veloci per monitorare il tuo percorso. Rispondi con sincerità,
            ogni numero conta!
          </p>
        </div>

        <form onSubmit={handleSubmit} className="check-form">
          {Object.entries(sectionMap).map(([sectionTitle, sectionQuestions], idx) => {
            const sectionConf = SECTIONS_CONFIG[idx] || { color: '#6366f1', icon: 'ri-question-line' };
            return (
              <div key={sectionTitle} className="wcl-section">
                <div className="wcl-section-header" style={{ borderLeftColor: sectionConf.color }}>
                  <i className={sectionConf.icon} style={{ color: sectionConf.color }} />
                  <h2 className="wcl-section-title">{sectionTitle}</h2>
                </div>
                {sectionQuestions.map((q) => (
                  <ScaleQuestion
                    key={q.key}
                    question={q}
                    value={formData[q.key] ?? null}
                    onChange={handleChange}
                  />
                ))}
              </div>
            );
          })}

          {error && (
            <div className="check-error-banner">
              <i className="ri-error-warning-line" />
              {error}
            </div>
          )}

          <div className="check-submit-area">
            <button
              type="submit"
              className="check-submit-btn"
              disabled={submitting || answered < totalQuestions}
              style={{ background: '#6366f1' }}
            >
              {submitting ? (
                <>
                  <span className="check-btn-spinner" />
                  Invio in corso...
                </>
              ) : (
                <>
                  <i className="ri-send-plane-line" />
                  Invia check settimanale
                </>
              )}
            </button>
            {answered < totalQuestions && (
              <p className="check-submit-hint">
                Rispondi a tutte le {totalQuestions} domande per inviare
              </p>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

export default WeeklyCheckLightForm;

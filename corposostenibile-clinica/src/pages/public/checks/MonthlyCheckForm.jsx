import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import publicCheckService from '../../../services/publicCheckService';
import './PublicChecks.css';

const SCALE_LABELS_1_5 = ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Completamente'];
const SCALE_LABELS_0_10 = [
  'Pessima', 'Molto scarsa', 'Scarsa', 'Mediocre', 'Sotto la media',
  'Nella media', 'Discreta', 'Buona', 'Molto buona', 'Ottima', 'Eccellente',
];

const TIPOLOGIA_CONFIG = {
  regolare: { label: 'Check Mensile', color: '#22c55e', icon: 'ri-calendar-check-line' },
  dca: { label: 'Check Mensile Benessere', color: '#ec4899', icon: 'ri-heart-line' },
  minori: { label: 'Check Mensile', color: '#6366f1', icon: 'ri-user-heart-line' },
};

function ScaleQuestion5({ question, value, onChange }) {
  return (
    <div className="check-question-block">
      <p className="check-question-label">{question.label}</p>
      {question.sublabel && <p className="check-question-sublabel">{question.sublabel}</p>}
      <div className="check-rating-5">
        {SCALE_LABELS_1_5.map((label, idx) => (
          <button
            key={idx}
            type="button"
            className={`check-rating-5-btn${value === idx + 1 ? ' selected positive' : ''}`}
            onClick={() => onChange(question.key, idx + 1)}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

function ScaleQuestion10({ question, value, onChange }) {
  const selectedLabel = value != null ? SCALE_LABELS_0_10[value] : '';
  return (
    <div className="check-question-block">
      <p className="check-question-label">{question.label}</p>
      {question.sublabel && <p className="check-question-sublabel">{question.sublabel}</p>}
      <div className="check-rating-grid">
        {Array.from({ length: question.min === 0 ? 11 : 10 }, (_, i) => i + (question.min ?? 1)).map((num) => (
          <button
            key={num}
            type="button"
            className={`check-rating-btn${value === num ? ' selected' : ''}`}
            onClick={() => onChange(question.key, num)}
          >
            {num}
          </button>
        ))}
      </div>
      {selectedLabel && <p className="check-rating-selected-label">{selectedLabel}</p>}
    </div>
  );
}

function SelectQuestion({ question, value, onChange }) {
  return (
    <div className="check-question-block">
      <p className="check-question-label">{question.label}</p>
      <div className="check-select-options">
        {(question.options || []).map((opt) => (
          <button
            key={opt}
            type="button"
            className={`check-select-btn${value === opt ? ' selected' : ''}`}
            onClick={() => onChange(question.key, opt)}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}

function TextQuestion({ question, value, onChange }) {
  return (
    <div className="check-question-block">
      <p className="check-question-label">
        {question.label}
        {question.required === false && <span className="check-optional"> (facoltativo)</span>}
      </p>
      <textarea
        className="check-textarea"
        rows={3}
        value={value || ''}
        onChange={(e) => onChange(question.key, e.target.value)}
        placeholder="Scrivi qui..."
      />
    </div>
  );
}

function NumberQuestion({ question, value, onChange }) {
  return (
    <div className="check-question-block">
      <p className="check-question-label">
        {question.label}
        {question.required === false && <span className="check-optional"> (facoltativo)</span>}
      </p>
      <input
        type="number"
        className="check-number-input"
        step="0.1"
        min="0"
        max="500"
        value={value || ''}
        onChange={(e) => onChange(question.key, e.target.value ? parseFloat(e.target.value) : '')}
        placeholder="es. 72.5"
      />
    </div>
  );
}

function QuestionRenderer({ question, value, onChange }) {
  if (question.type === 'scale') {
    if (question.max === 5) return <ScaleQuestion5 question={question} value={value} onChange={onChange} />;
    return <ScaleQuestion10 question={question} value={value} onChange={onChange} />;
  }
  if (question.type === 'select') return <SelectQuestion question={question} value={value} onChange={onChange} />;
  if (question.type === 'text') return <TextQuestion question={question} value={value} onChange={onChange} />;
  if (question.type === 'number') return <NumberQuestion question={question} value={value} onChange={onChange} />;
  return null;
}

function MonthlyCheckForm() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [checkInfo, setCheckInfo] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [formData, setFormData] = useState({});
  const [collapsedSections, setCollapsedSections] = useState({});

  useEffect(() => {
    loadCheckInfo();
  }, [token]);

  const loadCheckInfo = async () => {
    try {
      const result = await publicCheckService.getMonthlyCheckInfo(token);
      if (result.success) {
        setCheckInfo(result);
        setQuestions(result.questions || []);
      } else {
        setError(result.error || 'Check non trovato');
      }
    } catch (err) {
      console.error('Error loading monthly check info:', err);
      setError('Errore nel caricamento del check');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (key, value) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const toggleSection = (section) => {
    setCollapsedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const requiredScaleKeys = questions
      .filter((q) => q.type === 'scale' && q.required !== false)
      .map((q) => q.key);
    const missing = requiredScaleKeys.filter((k) => formData[k] == null);
    if (missing.length > 0) {
      setError(`Rispondi a tutte le domande obbligatorie prima di inviare (${missing.length} mancanti).`);
      return;
    }

    setSubmitting(true);
    try {
      const result = await publicCheckService.submitMonthlyCheck(token, formData);
      if (result.success) {
        navigate(`/check/monthly/${token}/success`);
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

  const requiredScales = questions.filter((q) => q.type === 'scale' && q.required !== false);
  const answered = requiredScales.filter((q) => formData[q.key] != null).length;
  const progress = requiredScales.length > 0 ? Math.round((answered / requiredScales.length) * 100) : 0;

  // Group by section
  const sectionMap = {};
  const sectionOrder = [];
  questions.forEach((q) => {
    const sec = q.section || 'Altro';
    if (!sectionMap[sec]) {
      sectionMap[sec] = [];
      sectionOrder.push(sec);
    }
    sectionMap[sec].push(q);
  });

  const tipologia = checkInfo?.check?.tipologia || 'regolare';
  const config = TIPOLOGIA_CONFIG[tipologia] || TIPOLOGIA_CONFIG.regolare;

  const getSectionCompletion = useCallback((sectionTitle) => {
    const sqs = (sectionMap[sectionTitle] || []).filter(
      (q) => q.type === 'scale' && q.required !== false
    );
    const ans = sqs.filter((q) => formData[q.key] != null).length;
    return { answered: ans, total: sqs.length };
  }, [formData, sectionMap]);

  if (loading) {
    return (
      <div className="check-loading">
        <div className="check-loading-spinner" />
        <p>Caricamento check mensile...</p>
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
    <div className="check-page">
      {/* Sticky progress bar */}
      <div className="check-progress-bar-sticky">
        <div className="check-progress-bar-inner">
          <span className="check-progress-label">
            {answered}/{requiredScales.length} risposte
          </span>
          <div className="check-progress-track">
            <div
              className="check-progress-fill"
              style={{ width: `${progress}%`, background: config.color }}
            />
          </div>
          <span className="check-progress-pct">{progress}%</span>
        </div>
      </div>

      <div className="check-container">
        {/* Header */}
        <div className="check-header">
          <div className="wcl-badge" style={{ background: config.color }}>
            <i className={config.icon} /> {config.label}
          </div>
          <h1 className="check-title">Come è andato questo mese?</h1>
          {checkInfo?.cliente?.nome_cognome && (
            <p className="check-subtitle">Ciao {checkInfo.cliente.nome_cognome.split(' ')[0]} 👋</p>
          )}
          <p className="check-intro">
            Prenditi qualche minuto per riflettere sul tuo mese. Le tue risposte aiutano
            il team a supportarti al meglio.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="check-form">
          {sectionOrder.map((sectionTitle) => {
            const sqs = sectionMap[sectionTitle];
            const isCollapsed = collapsedSections[sectionTitle];
            const { answered: secAns, total: secTotal } = getSectionCompletion(sectionTitle);
            const secComplete = secTotal > 0 && secAns === secTotal;

            return (
              <div key={sectionTitle} className="check-section-collapsible">
                <button
                  type="button"
                  className={`check-section-toggle${secComplete ? ' complete' : ''}`}
                  onClick={() => toggleSection(sectionTitle)}
                  style={{ borderLeftColor: config.color }}
                >
                  <span className="check-section-toggle-title">{sectionTitle}</span>
                  <span className="check-section-toggle-meta">
                    {secTotal > 0 && (
                      <span className={`check-section-badge${secComplete ? ' done' : ''}`}>
                        {secAns}/{secTotal}
                      </span>
                    )}
                    <i className={`ri-arrow-${isCollapsed ? 'down' : 'up'}-s-line`} />
                  </span>
                </button>

                {!isCollapsed && (
                  <div className="check-section-body">
                    {sqs.map((q) => (
                      <QuestionRenderer
                        key={q.key}
                        question={q}
                        value={formData[q.key] ?? null}
                        onChange={handleChange}
                      />
                    ))}
                  </div>
                )}
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
              disabled={submitting}
              style={{ background: config.color }}
            >
              {submitting ? (
                <>
                  <span className="check-btn-spinner" />
                  Invio in corso...
                </>
              ) : (
                <>
                  <i className="ri-send-plane-line" />
                  Invia check mensile
                </>
              )}
            </button>
            {answered < requiredScales.length && (
              <p className="check-submit-hint">
                Puoi inviare anche con domande facoltative non compilate — assicurati
                di aver risposto a tutte le scale numeriche.
              </p>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

export default MonthlyCheckForm;

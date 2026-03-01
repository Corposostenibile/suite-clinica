/**
 * MinorCheckForm - Form pubblico per il Check Minori (EDE-Q6)
 * Questionario screening disturbi alimentari - 28 domande
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import publicCheckService from '../../../services/publicCheckService';
import './PublicChecks.css';

// Frequency scale (0-6 days)
const FREQ_LABELS = ['Mai', '1-5 gg', '6-12 gg', '13-15 gg', '16-22 gg', '23-27 gg', 'Ogni giorno'];

// Intensity scale (0-6)
const INTENSITY_LABELS = ['Per niente', 'Poco', 'Lievemente', 'Moderatam.', 'Abbastanza', 'Molto', 'Notevolm.'];

const FREQUENCY_QUESTIONS = [
  { field: 'q1', label: 'Hai deliberatamente limitato la quantità di cibo per influenzare il tuo corpo o il tuo peso?' },
  { field: 'q2', label: 'Hai passato lunghi periodi (8 ore o più) senza mangiare per influenzare il tuo corpo o il tuo peso?' },
  { field: 'q3', label: 'Hai escluso dalla tua dieta cibi che ti piacciono per influenzare il tuo corpo o il tuo peso?' },
  { field: 'q4', label: 'Hai seguito regole rigide sull\'alimentazione o sul limite di calorie?' },
  { field: 'q5', label: 'Hai avuto il desiderio di avere lo stomaco vuoto per influenzare il tuo corpo o il tuo peso?' },
  { field: 'q6', label: 'Hai avuto il desiderio di avere la pancia totalmente piatta?' },
  { field: 'q7', label: 'I pensieri sul cibo, mangiare o calorie ti hanno reso difficile concentrarti?' },
  { field: 'q8', label: 'I pensieri sul corpo o sul peso ti hanno reso difficile concentrarti?' },
  { field: 'q9', label: 'Hai avuto paura di perdere il controllo su quello che mangi?' },
  { field: 'q10', label: 'Hai avuto paura di ingrassare?' },
  { field: 'q11', label: 'Ti sei sentito/a grasso/a o in sovrappeso?' },
  { field: 'q12', label: 'Hai avuto un forte desiderio di perdere peso?' },
];

const EPISODE_QUESTIONS = [
  { field: 'q13', label: 'Quante volte hai mangiato una quantità di cibo insolitamente grande?' },
  { field: 'q14', label: 'Quante volte hai sentito di aver perso il controllo su quello che stavi mangiando?' },
  { field: 'q15', label: 'In quanti giorni ci sono stati episodi di abbuffata? (0-28 giorni)', max: 28 },
  { field: 'q16', label: 'Quante volte ti sei provocato/a il vomito per controllare peso o corpo?' },
  { field: 'q17', label: 'Quante volte hai usato lassativi per controllare peso o corpo?' },
  { field: 'q18', label: 'Quante volte ti sei allenato/a in modo eccessivo o compulsivo?' },
];

const BEHAVIOR_QUESTIONS = [
  { field: 'q19', label: 'In quanti giorni hai mangiato di nascosto?', type: 'freq' },
  { field: 'q20', label: 'In che proporzione di volte ti sei sentito/a in colpa dopo aver mangiato?', labels: ['Nessuna volta', 'Poche volte', 'Meno della metà', 'Metà', 'Più della metà', 'Quasi sempre', 'Ogni volta'] },
  { field: 'q21', label: 'Quanto ti sei preoccupato/a che altre persone ti potessero vedere mentre mangiavi?', type: 'intensity' },
];

const SELF_ASSESSMENT_QUESTIONS = [
  { field: 'q22', label: 'Quanto il tuo peso ha influenzato il modo in cui giudichi te stesso/a?' },
  { field: 'q23', label: 'Quanto la forma del tuo corpo ha influenzato il modo in cui giudichi te stesso/a?' },
  { field: 'q24', label: 'Quanto ti preoccuperesti se ti chiedessero di pesarti una volta alla settimana?' },
  { field: 'q25', label: 'Quanto sei stato/a insoddisfatto/a del tuo peso?' },
  { field: 'q26', label: 'Quanto sei stato/a insoddisfatto/a della forma del tuo corpo?' },
  { field: 'q27', label: 'Quanto ti ha dato fastidio vedere il tuo corpo (es. nello specchio)?' },
  { field: 'q28', label: 'Quanto ti ha dato fastidio che gli altri vedessero il tuo corpo?' },
];

const ALL_SECTIONS = [
  {
    id: 'frequency',
    title: 'Frequenza negli ultimi 28 giorni',
    icon: 'ri-calendar-line',
    color: '#f59e0b',
    description: 'Indica in quanti giorni hai sperimentato quanto descritto',
    questions: FREQUENCY_QUESTIONS,
    type: 'freq',
    startNum: 1,
  },
  {
    id: 'episodes',
    title: 'Episodi Specifici',
    icon: 'ri-error-warning-line',
    color: '#ef4444',
    description: 'Indica il numero di episodi negli ultimi 28 giorni',
    questions: EPISODE_QUESTIONS,
    type: 'episode',
    startNum: 13,
  },
  {
    id: 'behavior',
    title: 'Comportamenti Alimentari',
    icon: 'ri-user-heart-line',
    color: '#3b82f6',
    questions: BEHAVIOR_QUESTIONS,
    type: 'mixed',
    startNum: 19,
  },
  {
    id: 'self',
    title: 'Autovalutazione',
    icon: 'ri-mental-health-line',
    color: '#8b5cf6',
    description: 'Indica quanto ti riconosci in queste affermazioni',
    questions: SELF_ASSESSMENT_QUESTIONS,
    type: 'intensity',
    startNum: 22,
  },
];

function MinorCheckForm() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [checkInfo, setCheckInfo] = useState(null);
  const [formData, setFormData] = useState({});
  const [collapsedSections, setCollapsedSections] = useState({});
  const questionRefs = useRef({});

  useEffect(() => {
    loadCheckInfo();
  }, [token]);

  const loadCheckInfo = async () => {
    try {
      const result = await publicCheckService.getCheckInfo('minor', token);
      if (result.success) {
        setCheckInfo(result);
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

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // Auto-scroll to next unanswered question in same section after answering
  const handleFreqChange = (field, value, sectionQuestions, currentIdx) => {
    handleChange(field, value);
    // Find next unanswered in same section
    for (let i = currentIdx + 1; i < sectionQuestions.length; i++) {
      const nextField = sectionQuestions[i].field;
      if (formData[nextField] == null) {
        setTimeout(() => {
          const el = questionRefs.current[nextField];
          if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 150);
        break;
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await publicCheckService.submitMinorCheck(token, formData);
      if (result.success) {
        navigate(`/check/minor/${token}/success`);
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

  const toggleSection = (sectionId) => {
    setCollapsedSections(prev => ({ ...prev, [sectionId]: !prev[sectionId] }));
  };

  // Count all questions
  const allFields = ALL_SECTIONS.flatMap(s => s.questions.map(q => q.field));
  const totalQuestions = allFields.length;
  const answeredCount = allFields.filter(f => formData[f] != null).length;
  const overallProgress = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;

  const getSectionCompletion = useCallback((section) => {
    const answered = section.questions.filter(q => formData[q.field] != null).length;
    return { answered, total: section.questions.length };
  }, [formData]);

  // Subcomponents
  const FrequencySelector = ({ value, onChange, labels = FREQ_LABELS }) => (
    <div className="check-freq-grid">
      {labels.map((label, idx) => (
        <button
          key={idx}
          type="button"
          className={`check-freq-btn${value === idx ? ' selected' : ''}`}
          onClick={() => onChange(idx)}
        >
          {label}
        </button>
      ))}
    </div>
  );

  const EpisodeStepper = ({ value, onChange, max = 999 }) => {
    const val = value || 0;
    return (
      <div className="check-stepper">
        <button
          type="button"
          className="check-stepper-btn"
          onClick={() => onChange(Math.max(0, val - 1))}
          disabled={val <= 0}
        >
          -
        </button>
        <div className="check-stepper-value">{val}</div>
        <button
          type="button"
          className="check-stepper-btn"
          onClick={() => onChange(Math.min(max, val + 1))}
        >
          +
        </button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="check-card check-theme-minor">
        <div className="check-loading">
          <div className="check-loading-spinner"></div>
          <p className="check-loading-text">Caricamento check...</p>
        </div>
      </div>
    );
  }

  if (error && !checkInfo) {
    return (
      <div className="check-card check-theme-minor">
        <div className="check-error">
          <i className="ri-error-warning-line check-error-icon"></i>
          <h5 className="check-error-title">Errore</h5>
          <p className="check-error-text">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="check-card check-theme-minor">
      {/* Header */}
      <div className="check-header">
        <h4 className="check-header-title">Check Minori</h4>
        {checkInfo?.cliente && (
          <p className="check-header-subtitle">
            Ciao {checkInfo.cliente.nome}!
          </p>
        )}
        <p className="check-header-hint">
          Rispondi pensando agli ultimi 28 giorni
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <div className="check-body">
          {/* Sticky Progress */}
          <div className="check-sticky-progress">
            <div className="check-sticky-progress-bar">
              <div className="check-sticky-progress-fill" style={{ width: `${overallProgress}%` }}></div>
            </div>
            <div className="check-sticky-progress-text">
              <span>{answeredCount}/{totalQuestions} risposte</span>
              <span>{overallProgress}%</span>
            </div>
          </div>

          {/* Sections */}
          {ALL_SECTIONS.map(section => {
            const { answered, total } = getSectionCompletion(section);
            const isCollapsed = collapsedSections[section.id];
            const badgeClass = answered === 0 ? 'pending' : answered === total ? 'complete' : 'partial';

            return (
              <div
                key={section.id}
                className={`check-section${isCollapsed ? ' collapsed' : ''}`}
              >
                <div className="check-section-header" onClick={() => toggleSection(section.id)}>
                  <div
                    className="check-section-icon"
                    style={{ background: `${section.color}15`, color: section.color }}
                  >
                    <i className={section.icon}></i>
                  </div>
                  <span className="check-section-title">{section.title}</span>
                  <span className={`check-section-badge ${badgeClass}`}>
                    {answered === total && total > 0 ? (
                      <><i className="ri-check-line" style={{ marginRight: 2 }}></i> Fatto</>
                    ) : (
                      `${answered}/${total}`
                    )}
                  </span>
                  <i className="ri-arrow-down-s-line check-section-chevron"></i>
                </div>

                <div className="check-section-body">
                  {section.description && (
                    <p style={{ fontSize: '0.82rem', color: 'var(--check-text-muted)', marginBottom: 16 }}>
                      {section.description}
                    </p>
                  )}

                  {section.questions.map((q, idx) => {
                    const qNum = section.startNum + idx;
                    const isEpisode = section.type === 'episode';
                    const isMixed = section.type === 'mixed';

                    // Determine which selector to use
                    let selector;
                    if (isEpisode) {
                      selector = (
                        <EpisodeStepper
                          value={formData[q.field]}
                          onChange={(val) => handleChange(q.field, val)}
                          max={q.max || 999}
                        />
                      );
                    } else if (isMixed) {
                      const labels = q.labels || (q.type === 'intensity' ? INTENSITY_LABELS : FREQ_LABELS);
                      selector = (
                        <FrequencySelector
                          value={formData[q.field]}
                          onChange={(val) => handleFreqChange(q.field, val, section.questions, idx)}
                          labels={labels}
                        />
                      );
                    } else if (section.type === 'intensity') {
                      selector = (
                        <FrequencySelector
                          value={formData[q.field]}
                          onChange={(val) => handleFreqChange(q.field, val, section.questions, idx)}
                          labels={INTENSITY_LABELS}
                        />
                      );
                    } else {
                      selector = (
                        <FrequencySelector
                          value={formData[q.field]}
                          onChange={(val) => handleFreqChange(q.field, val, section.questions, idx)}
                        />
                      );
                    }

                    return (
                      <div
                        key={q.field}
                        ref={el => questionRefs.current[q.field] = el}
                        className={`check-question${formData[q.field] != null ? ' answered' : ''}`}
                      >
                        <div className="check-question-label">
                          <span className="check-question-number">{qNum}</span>
                          {q.label}
                        </div>
                        {selector}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}

          {/* Final Info Section */}
          <div className="check-section">
            <div className="check-section-header" style={{ cursor: 'default' }}>
              <div
                className="check-section-icon"
                style={{ background: '#22c55e15', color: '#22c55e' }}
              >
                <i className="ri-scales-line"></i>
              </div>
              <span className="check-section-title">Informazioni Finali</span>
            </div>

            <div className="check-section-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label className="check-textarea-label">Peso attuale (kg)</label>
                  <input
                    type="number"
                    className="check-input"
                    step="0.1"
                    min="30"
                    max="300"
                    value={formData.peso_attuale || ''}
                    onChange={(e) => handleChange('peso_attuale', parseFloat(e.target.value))}
                    placeholder="Es: 55.5"
                  />
                </div>
                <div>
                  <label className="check-textarea-label">Altezza (cm)</label>
                  <input
                    type="number"
                    className="check-input"
                    min="100"
                    max="250"
                    value={formData.altezza || ''}
                    onChange={(e) => handleChange('altezza', parseInt(e.target.value))}
                    placeholder="Es: 165"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="check-alert-danger">
              <i className="ri-error-warning-line"></i>
              {error}
            </div>
          )}

          {/* Submit */}
          <div style={{ textAlign: 'center', paddingTop: 8 }}>
            <button type="submit" className="check-submit-btn" disabled={submitting}>
              {submitting ? (
                <>
                  <span className="check-loading-spinner" style={{ width: 18, height: 18, borderWidth: 2, margin: 0 }}></span>
                  Invio in corso...
                </>
              ) : (
                <>
                  <i className="ri-send-plane-line"></i>
                  Invia Check
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

export default MinorCheckForm;

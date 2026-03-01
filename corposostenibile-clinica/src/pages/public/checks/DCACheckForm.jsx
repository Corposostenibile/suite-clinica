/**
 * DCACheckForm - Form pubblico per il Check DCA (Benessere)
 * Form a pagina singola con sezioni collapsabili e progress tracking
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import publicCheckService from '../../../services/publicCheckService';
import './PublicChecks.css';

const SECTIONS = [
  {
    id: 'emotional',
    title: 'Benessere Emotivo e Psicologico',
    icon: 'ri-heart-line',
    color: '#ec4899',
    questions: [
      { field: 'mood_balance_rating', label: 'Come ti senti? (umore, energia, equilibrio emotivo)', scale: 5, labels: ['Molto male', 'Male', 'Così così', 'Bene', 'Benissimo'] },
      { field: 'food_plan_serenity', label: 'Quanto sei sereno/a nel seguire il piano alimentare?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
      { field: 'food_weight_worry', label: 'Quanto pensi a cibo, peso o corpo durante la giornata?', scale: 5, labels: ['Mai', 'Raramente', 'A volte', 'Spesso', 'Sempre'], inverted: true },
      { field: 'emotional_eating', label: 'Mangi in risposta alle emozioni (stress, noia, tristezza)?', scale: 5, labels: ['Mai', 'Raramente', 'A volte', 'Spesso', 'Sempre'], inverted: true },
      { field: 'body_comfort', label: 'Ti senti a tuo agio nel tuo corpo?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
      { field: 'body_respect', label: 'Quanto rispetti il tuo corpo (senza giudizi negativi)?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
    ],
  },
  {
    id: 'training',
    title: 'Allenamento e Movimento',
    icon: 'ri-run-line',
    color: '#3b82f6',
    questions: [
      { field: 'exercise_wellness', label: 'Gestisci l\'allenamento come strumento di benessere?', scale: 5, labels: ['No per niente', 'Poco', 'Abbastanza', 'Molto', 'Sì completamente'] },
      { field: 'exercise_guilt', label: 'Senti senso di colpa quando salti allenamenti?', scale: 5, labels: ['Mai', 'Raramente', 'A volte', 'Spesso', 'Sempre'], inverted: true },
    ],
  },
  {
    id: 'rest',
    title: 'Riposo e Relazioni',
    icon: 'ri-moon-line',
    color: '#6366f1',
    questions: [
      { field: 'sleep_satisfaction', label: 'Sei soddisfatto/a della qualità del tuo riposo?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
      { field: 'relationship_time', label: 'Dedichi tempo a relazioni significative?', scale: 5, labels: ['Mai', 'Raramente', 'A volte', 'Spesso', 'Sempre'] },
      { field: 'personal_time', label: 'Dedichi tempo ad attività che ti piacciono?', scale: 5, labels: ['Mai', 'Raramente', 'A volte', 'Spesso', 'Sempre'] },
    ],
  },
  {
    id: 'emotions',
    title: 'Gestione Emozioni',
    icon: 'ri-emotion-line',
    color: '#f59e0b',
    questions: [
      { field: 'life_interference', label: 'Il percorso interferisce con lavoro/vita sociale?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Molto'], inverted: true },
      { field: 'unexpected_management', label: 'Gestisci gli imprevisti senza senso di colpa?', scale: 5, labels: ['Mai', 'Raramente', 'A volte', 'Spesso', 'Sempre'] },
      { field: 'self_compassion', label: 'Sei compassionevole verso te stesso/a?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
      { field: 'inner_dialogue', label: 'Il tuo dialogo interiore è gentile?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
    ],
  },
  {
    id: 'sustainability',
    title: 'Sostenibilità e Motivazione',
    icon: 'ri-seedling-line',
    color: '#22c55e',
    questions: [
      { field: 'long_term_sustainability', label: 'Questo percorso ti sembra sostenibile a lungo termine?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
      { field: 'values_alignment', label: 'Il percorso è allineato con i tuoi valori e obiettivi?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
      { field: 'motivation_level', label: 'Quanto sei motivato/a a proseguire?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
    ],
  },
  {
    id: 'meals',
    title: 'Organizzazione Pasti',
    icon: 'ri-restaurant-line',
    color: '#ef4444',
    questions: [
      { field: 'meal_organization', label: 'Ti senti organizzato/a nella gestione pasti?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
      { field: 'meal_stress', label: 'Quanto stress ti crea gestire i pasti?', scale: 5, labels: ['Nessuno', 'Poco', 'Abbastanza', 'Molto', 'Moltissimo'], inverted: true },
      { field: 'shopping_awareness', label: 'Fai la spesa in modo consapevole?', scale: 5, labels: ['Mai', 'Raramente', 'A volte', 'Spesso', 'Sempre'] },
      { field: 'shopping_impact', label: 'La spesa impatta negativamente su tempo/budget?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Moltissimo'], inverted: true },
      { field: 'meal_clarity', label: 'Hai chiaro cosa cucinare durante la settimana?', scale: 5, labels: ['Per niente', 'Poco', 'Abbastanza', 'Molto', 'Totalmente'] },
    ],
  },
];

const PHYSICAL_PARAMS = [
  { field: 'digestion_rating', label: 'Digestione', icon: 'ri-heart-pulse-line' },
  { field: 'energy_rating', label: 'Energia', icon: 'ri-flashlight-line' },
  { field: 'strength_rating', label: 'Forza', icon: 'ri-boxing-line' },
  { field: 'hunger_rating', label: 'Fame', icon: 'ri-restaurant-2-line' },
  { field: 'sleep_rating', label: 'Sonno', icon: 'ri-moon-line' },
  { field: 'mood_rating', label: 'Umore', icon: 'ri-emotion-happy-line' },
  { field: 'motivation_rating', label: 'Motivazione', icon: 'ri-fire-line' },
];

const RATING_LABELS_0_10 = [
  'Pessima', 'Molto scarsa', 'Scarsa', 'Mediocre', 'Sotto la media',
  'Nella media', 'Discreta', 'Buona', 'Molto buona', 'Ottima', 'Eccellente',
];

function DCACheckForm() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [checkInfo, setCheckInfo] = useState(null);
  const [formData, setFormData] = useState({});
  const [collapsedSections, setCollapsedSections] = useState({});
  const sectionRefs = useRef({});

  useEffect(() => {
    loadCheckInfo();
  }, [token]);

  const loadCheckInfo = async () => {
    try {
      const result = await publicCheckService.getCheckInfo('dca', token);
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

  const handleRatingChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await publicCheckService.submitDCACheck(token, formData);
      if (result.success) {
        navigate(`/check/dca/${token}/success`);
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

  // Count answered questions
  const allSectionFields = SECTIONS.flatMap(s => s.questions.map(q => q.field));
  const physicalFields = PHYSICAL_PARAMS.map(p => p.field);
  const totalQuestions = allSectionFields.length + physicalFields.length;
  const answeredCount = [...allSectionFields, ...physicalFields].filter(f => formData[f] != null).length;
  const overallProgress = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;

  const getSectionCompletion = useCallback((section) => {
    const answered = section.questions.filter(q => formData[q.field] != null).length;
    return { answered, total: section.questions.length };
  }, [formData]);

  const getPhysicalCompletion = useCallback(() => {
    const answered = PHYSICAL_PARAMS.filter(p => formData[p.field] != null).length;
    return { answered, total: PHYSICAL_PARAMS.length };
  }, [formData]);

  // Subcomponents
  const RatingSelector5 = ({ value, onChange, labels, inverted }) => (
    <div className="check-rating-5">
      {labels.map((label, idx) => (
        <button
          key={idx}
          type="button"
          className={`check-rating-5-btn${value === idx + 1 ? ` selected ${inverted ? 'negative' : 'positive'}` : ''}`}
          onClick={() => onChange(idx + 1)}
        >
          {label}
        </button>
      ))}
    </div>
  );

  const RatingGrid10 = ({ value, onChange }) => {
    const selectedLabel = value !== null && value !== undefined ? RATING_LABELS_0_10[value] : '';
    return (
      <div>
        <div className="check-rating-grid">
          {Array.from({ length: 11 }, (_, i) => i).map(num => (
            <button
              key={num}
              type="button"
              className={`check-rating-btn${value === num ? ' selected' : ''}`}
              onClick={() => onChange(num)}
            >
              {num}
            </button>
          ))}
        </div>
        <div className="check-rating-selected-label">{selectedLabel}</div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="check-card check-theme-dca">
        <div className="check-loading">
          <div className="check-loading-spinner"></div>
          <p className="check-loading-text">Caricamento check...</p>
        </div>
      </div>
    );
  }

  if (error && !checkInfo) {
    return (
      <div className="check-card check-theme-dca">
        <div className="check-error">
          <i className="ri-error-warning-line check-error-icon"></i>
          <h5 className="check-error-title">Errore</h5>
          <p className="check-error-text">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="check-card check-theme-dca">
      {/* Header */}
      <div className="check-header">
        <h4 className="check-header-title">Check Benessere</h4>
        {checkInfo?.cliente && (
          <p className="check-header-subtitle">
            Ciao {checkInfo.cliente.nome}!
          </p>
        )}
        <p className="check-header-hint">
          Prenditi qualche minuto per riflettere sul tuo benessere
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

          {/* Sections with 1-5 ratings */}
          {SECTIONS.map(section => {
            const { answered, total } = getSectionCompletion(section);
            const isCollapsed = collapsedSections[section.id];
            const badgeClass = answered === 0 ? 'pending' : answered === total ? 'complete' : 'partial';

            return (
              <div
                key={section.id}
                ref={el => sectionRefs.current[section.id] = el}
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
                  {section.questions.map(q => (
                    <div key={q.field} className={`check-question${formData[q.field] != null ? ' answered' : ''}`}>
                      <div className="check-question-label">{q.label}</div>
                      <RatingSelector5
                        value={formData[q.field]}
                        onChange={(val) => handleRatingChange(q.field, val)}
                        labels={q.labels}
                        inverted={q.inverted}
                      />
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          {/* Physical Parameters (0-10) */}
          {(() => {
            const { answered, total } = getPhysicalCompletion();
            const isCollapsed = collapsedSections['physical'];
            const badgeClass = answered === 0 ? 'pending' : answered === total ? 'complete' : 'partial';

            return (
              <div className={`check-section${isCollapsed ? ' collapsed' : ''}`}>
                <div className="check-section-header" onClick={() => toggleSection('physical')}>
                  <div
                    className="check-section-icon"
                    style={{ background: '#3b82f615', color: '#3b82f6' }}
                  >
                    <i className="ri-pulse-line"></i>
                  </div>
                  <span className="check-section-title">Parametri Fisici (0-10)</span>
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
                  {PHYSICAL_PARAMS.map(param => (
                    <div key={param.field} className={`check-question${formData[param.field] != null ? ' answered' : ''}`}>
                      <div className="check-question-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <i className={param.icon} style={{ color: 'var(--check-primary)', fontSize: 18 }}></i>
                        {param.label}
                      </div>
                      <RatingGrid10
                        value={formData[param.field]}
                        onChange={(val) => handleRatingChange(param.field, val)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Notes Section */}
          <div className="check-section">
            <div className="check-section-header" style={{ cursor: 'default' }}>
              <div
                className="check-section-icon"
                style={{ background: '#64748b15', color: '#64748b' }}
              >
                <i className="ri-edit-line"></i>
              </div>
              <span className="check-section-title">Note Aggiuntive</span>
            </div>

            <div className="check-section-body">
              <div className="check-textarea-wrap">
                <label className="check-textarea-label">
                  Vuoi segnalarci qualcuno? (opzionale)
                </label>
                <textarea
                  className="check-textarea"
                  rows="3"
                  value={formData.referral || ''}
                  onChange={(e) => handleRatingChange('referral', e.target.value)}
                  placeholder="Nome e contatto di qualcuno che potrebbe beneficiare del programma..."
                />
              </div>

              <div className="check-textarea-wrap">
                <label className="check-textarea-label">
                  Commenti extra (opzionale)
                </label>
                <textarea
                  className="check-textarea"
                  rows="3"
                  value={formData.extra_comments || ''}
                  onChange={(e) => handleRatingChange('extra_comments', e.target.value)}
                  placeholder="Qualsiasi altra cosa vorresti comunicarci..."
                />
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

export default DCACheckForm;

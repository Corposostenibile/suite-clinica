/**
 * WeeklyCheckForm - Form pubblico per il Check Settimanale
 * 7-step wizard con foto, riflessioni, valutazioni e feedback
 */

import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import publicCheckService from '../../../services/publicCheckService';
import './PublicChecks.css';

const STEPS = [
  { id: 1, title: 'Foto', icon: 'ri-camera-line' },
  { id: 2, title: 'Riflessioni', icon: 'ri-lightbulb-line' },
  { id: 3, title: 'Benessere', icon: 'ri-heart-pulse-line' },
  { id: 4, title: 'Programmi', icon: 'ri-calendar-check-line' },
  { id: 5, title: 'Valutazioni', icon: 'ri-star-line' },
  { id: 6, title: 'Referral', icon: 'ri-user-add-line' },
  { id: 7, title: 'Conferma', icon: 'ri-check-double-line' },
];

const RATING_LABELS_0_10 = [
  'Pessima', 'Molto scarsa', 'Scarsa', 'Mediocre', 'Sotto la media',
  'Nella media', 'Discreta', 'Buona', 'Molto buona', 'Ottima', 'Eccellente',
];

function WeeklyCheckForm() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [checkInfo, setCheckInfo] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);
  const stepsRef = useRef(null);

  const [formData, setFormData] = useState({
    photo_front: null,
    photo_side: null,
    photo_back: null,
    what_worked: '',
    what_didnt_work: '',
    what_learned: '',
    what_focus_next: '',
    injuries_notes: '',
    digestion_rating: null,
    energy_rating: null,
    strength_rating: null,
    hunger_rating: null,
    sleep_rating: null,
    mood_rating: null,
    motivation_rating: null,
    weight: '',
    nutrition_program_adherence: '',
    training_program_adherence: '',
    exercise_modifications: '',
    daily_steps: '',
    completed_training_weeks: '',
    planned_training_days: '',
    live_session_topics: '',
    nutritionist_rating: null,
    nutritionist_feedback: '',
    psychologist_rating: null,
    psychologist_feedback: '',
    coach_rating: null,
    coach_feedback: '',
    progress_rating: null,
    referral: '',
    extra_comments: '',
  });

  const [photoPreviews, setPhotoPreviews] = useState({
    photo_front: null,
    photo_side: null,
    photo_back: null,
  });

  const [feedbackOpen, setFeedbackOpen] = useState({});

  useEffect(() => {
    loadCheckInfo();
  }, [token]);

  // Scroll active step pill into view
  useEffect(() => {
    if (stepsRef.current) {
      const activeEl = stepsRef.current.querySelector('.check-step.active');
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
      }
    }
  }, [currentStep]);

  const loadCheckInfo = async () => {
    try {
      const result = await publicCheckService.getCheckInfo('weekly', token);
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

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handlePhotoChange = (field, file) => {
    if (file) {
      setFormData(prev => ({ ...prev, [field]: file }));
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreviews(prev => ({ ...prev, [field]: reader.result }));
      };
      reader.readAsDataURL(file);
    }
  };

  const handlePhotoRemove = (field) => {
    setFormData(prev => ({ ...prev, [field]: null }));
    setPhotoPreviews(prev => ({ ...prev, [field]: null }));
  };

  const handleNext = () => {
    if (currentStep < 7) {
      setCurrentStep(prev => prev + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const submitData = new FormData();
      Object.entries(formData).forEach(([key, value]) => {
        if (value !== null && value !== '') {
          submitData.append(key, value);
        }
      });
      const result = await publicCheckService.submitWeeklyCheck(token, submitData);
      if (result.success) {
        navigate(`/check/weekly/${token}/success`);
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

  const progress = ((currentStep - 1) / 6) * 100;

  const resolveProfessionalRoleKey = (ruolo = '') => {
    const normalized = ruolo.toLowerCase();
    if (normalized.includes('nutri')) return 'nutritionist';
    if (normalized.includes('psico')) return 'psychologist';
    if (normalized.includes('coach')) return 'coach';
    return null;
  };

  const professionalConfigs = {
    nutritionist: {
      roleLabel: 'Nutrizionista',
      description: 'Valuta il supporto nutrizionale',
      ratingField: 'nutritionist_rating',
      feedbackField: 'nutritionist_feedback',
      icon: 'ri-user-heart-line',
      avatarBg: '#22c55e',
      cardBg: '#f0fdf4',
      cardBorder: '#bbf7d0',
      feedbackPlaceholder: 'Feedback per il nutrizionista (opzionale)',
    },
    psychologist: {
      roleLabel: 'Psicologo/a',
      description: 'Valuta il supporto psicologico',
      ratingField: 'psychologist_rating',
      feedbackField: 'psychologist_feedback',
      icon: 'ri-mental-health-line',
      avatarBg: '#3b82f6',
      cardBg: '#eff6ff',
      cardBorder: '#bfdbfe',
      feedbackPlaceholder: 'Feedback per lo psicologo (opzionale)',
    },
    coach: {
      roleLabel: 'Coach',
      description: 'Valuta il supporto sportivo',
      ratingField: 'coach_rating',
      feedbackField: 'coach_feedback',
      icon: 'ri-run-line',
      avatarBg: '#8b5cf6',
      cardBg: '#faf5ff',
      cardBorder: '#e9d5ff',
      feedbackPlaceholder: 'Feedback per il coach (opzionale)',
    },
  };

  const assignedProfessionals = (checkInfo?.professionisti || [])
    .map((prof) => {
      const roleKey = resolveProfessionalRoleKey(prof.ruolo);
      if (!roleKey) return null;
      const config = professionalConfigs[roleKey];
      if (!config) return null;
      return { ...config, roleKey, nome: prof.nome || config.roleLabel };
    })
    .filter(Boolean);

  // --- Subcomponents ---

  const RatingGrid = ({ value, onChange, min = 0, max = 10, labels }) => {
    const nums = Array.from({ length: max - min + 1 }, (_, i) => i + min);
    const selectedLabel = value !== null && labels
      ? (labels[value - min] || '')
      : '';

    return (
      <div>
        <div className="check-rating-grid">
          {nums.map(num => (
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
        {labels && (
          <div className="check-rating-selected-label">
            {selectedLabel}
          </div>
        )}
        {!labels && (
          <div className="check-rating-labels">
            <span>Min</span>
            <span>Max</span>
          </div>
        )}
      </div>
    );
  };

  const PhotoUpload = ({ field, label, icon }) => (
    <div>
      <div
        className={`check-photo-card${photoPreviews[field] ? ' has-photo' : ''}`}
        onClick={() => !photoPreviews[field] && document.getElementById(field).click()}
      >
        {photoPreviews[field] ? (
          <>
            <img src={photoPreviews[field]} alt={label} className="check-photo-preview" />
            <button
              type="button"
              className="check-photo-remove"
              onClick={(e) => { e.stopPropagation(); handlePhotoRemove(field); }}
            >
              <i className="ri-close-line"></i>
            </button>
          </>
        ) : (
          <>
            <div className="check-photo-icon">
              <i className={icon || 'ri-camera-line'}></i>
            </div>
            <div className="check-photo-label">{label}</div>
            <div className="check-photo-hint">Tocca per caricare</div>
          </>
        )}
      </div>
      <input
        type="file"
        id={field}
        accept="image/*"
        style={{ display: 'none' }}
        onChange={(e) => handlePhotoChange(field, e.target.files[0])}
      />
    </div>
  );

  const TextareaField = ({ label, field, placeholder, rows = 3 }) => (
    <div className="check-textarea-wrap">
      <label className="check-textarea-label">{label}</label>
      <textarea
        className="check-textarea"
        rows={rows}
        value={formData[field]}
        onChange={(e) => handleInputChange(field, e.target.value)}
        placeholder={placeholder}
      />
      {formData[field]?.length > 0 && (
        <div className="check-textarea-counter">{formData[field].length} caratteri</div>
      )}
    </div>
  );

  // --- Renders ---

  if (loading) {
    return (
      <div className="check-card check-theme-weekly">
        <div className="check-loading">
          <div className="check-loading-spinner"></div>
          <p className="check-loading-text">Caricamento check...</p>
        </div>
      </div>
    );
  }

  if (error && !checkInfo) {
    return (
      <div className="check-card check-theme-weekly">
        <div className="check-error">
          <i className="ri-error-warning-line check-error-icon"></i>
          <h5 className="check-error-title">Errore</h5>
          <p className="check-error-text">{error}</p>
        </div>
      </div>
    );
  }

  const currentStepInfo = STEPS[currentStep - 1];

  return (
    <div className="check-card check-theme-weekly">
      {/* Header */}
      <div className="check-header">
        <h4 className="check-header-title">
          Ciao {checkInfo?.cliente?.nome || ''}!
        </h4>
        <p className="check-header-subtitle">
          È il momento del tuo check settimanale. Raccontaci come è andata!
        </p>
        <p className="check-header-hint">
          <i className="ri-time-line"></i> Compilazione: ~5 min
        </p>
      </div>

      {/* Progress */}
      <div className="check-progress-wrap">
        <div className="check-progress-bar">
          <div className="check-progress-fill" style={{ width: `${progress}%` }}></div>
        </div>
        <div className="check-steps" ref={stepsRef}>
          {STEPS.map(step => (
            <div
              key={step.id}
              className={`check-step${currentStep === step.id ? ' active' : ''}${currentStep > step.id ? ' completed' : ''}`}
            >
              <span className="check-step-number">
                {currentStep > step.id ? <i className="ri-check-line"></i> : step.id}
              </span>
              {step.title}
            </div>
          ))}
        </div>
        <div className="check-step-current-title">
          <i className={currentStepInfo.icon}></i>
          {currentStepInfo.title}
        </div>
      </div>

      {/* Form Content */}
      <div className="check-body">
        <div key={currentStep} className="check-step-content">

          {/* Step 1: Photos */}
          {currentStep === 1 && (
            <div>
              <p className="check-step-desc">
                Carica le foto per monitorare i tuoi progressi fisici
              </p>
              <div className="check-photo-grid">
                <PhotoUpload field="photo_front" label="Frontale" icon="ri-body-scan-line" />
                <PhotoUpload field="photo_side" label="Laterale" icon="ri-user-line" />
                <PhotoUpload field="photo_back" label="Posteriore" icon="ri-arrow-go-back-line" />
              </div>
            </div>
          )}

          {/* Step 2: Reflections */}
          {currentStep === 2 && (
            <div>
              <p className="check-step-desc">
                Rifletti sulla tua settimana
              </p>
              <TextareaField
                label="Cosa ha funzionato bene per te la settimana scorsa?"
                field="what_worked"
                placeholder="Racconta cosa è andato bene..."
              />
              <TextareaField
                label="Cosa NON ha funzionato bene per te?"
                field="what_didnt_work"
                placeholder="Racconta le difficoltà incontrate..."
              />
              <TextareaField
                label="Cosa hai imparato da ciò che ha funzionato e non?"
                field="what_learned"
                placeholder="Quali lezioni porti con te..."
              />
              <TextareaField
                label="Su cosa pensi sia necessario focalizzarci la prossima settimana?"
                field="what_focus_next"
                placeholder="I tuoi obiettivi per la prossima settimana..."
              />
              <TextareaField
                label="Infortuni o qualcosa di cui devo essere messo a conoscenza?"
                field="injuries_notes"
                placeholder="Segnala eventuali problemi..."
              />
            </div>
          )}

          {/* Step 3: Wellness */}
          {currentStep === 3 && (
            <div>
              <p className="check-step-desc">
                Valuta da 0 a 10 i seguenti aspetti della tua settimana
              </p>
              {[
                { field: 'digestion_rating', label: 'Digestione', icon: 'ri-heart-pulse-line' },
                { field: 'energy_rating', label: 'Energia', icon: 'ri-flashlight-line' },
                { field: 'strength_rating', label: 'Forza', icon: 'ri-boxing-line' },
                { field: 'hunger_rating', label: 'Fame', icon: 'ri-restaurant-2-line' },
                { field: 'sleep_rating', label: 'Sonno', icon: 'ri-moon-line' },
                { field: 'mood_rating', label: 'Umore', icon: 'ri-emotion-happy-line' },
                { field: 'motivation_rating', label: 'Motivazione', icon: 'ri-fire-line' },
              ].map(item => (
                <div key={item.field} className={`check-question check-question-gap${formData[item.field] !== null ? ' answered' : ''}`}>
                  <div className="check-question-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <i className={item.icon} style={{ color: 'var(--check-primary)', fontSize: 18 }}></i>
                    {item.label}
                  </div>
                  <RatingGrid
                    value={formData[item.field]}
                    onChange={(val) => handleInputChange(item.field, val)}
                    labels={RATING_LABELS_0_10}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Step 4: Programs */}
          {currentStep === 4 && (
            <div>
              <p className="check-step-desc">
                Informazioni su peso e programmi seguiti
              </p>

              <div className="check-textarea-wrap">
                <label className="check-textarea-label">Peso (Kg)</label>
                <input
                  type="number"
                  className="check-input"
                  step="0.1"
                  value={formData.weight}
                  onChange={(e) => handleInputChange('weight', e.target.value)}
                  placeholder="Es: 75.5"
                />
                <div className="check-input-hint">
                  A stomaco vuoto e dopo essere andato/a in bagno se possibile. Ma solo se vuoi!
                </div>
              </div>

              <TextareaField
                label="Stai riuscendo a rispettare il PROGRAMMA ALIMENTARE?"
                field="nutrition_program_adherence"
                placeholder="Descrivi come sta andando..."
              />
              <TextareaField
                label="Stai riuscendo a rispettare il PROGRAMMA SPORTIVO?"
                field="training_program_adherence"
                placeholder="Descrivi come sta andando..."
              />
              <TextareaField
                label="Quali esercizi non hai fatto o hai aggiunto?"
                field="exercise_modifications"
                placeholder="Variazioni al programma..."
              />

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
                <div>
                  <label className="check-textarea-label">Passi medi al giorno</label>
                  <input
                    type="text"
                    className="check-input"
                    value={formData.daily_steps}
                    onChange={(e) => handleInputChange('daily_steps', e.target.value)}
                    placeholder="Es: 8000"
                  />
                </div>
                <div>
                  <label className="check-textarea-label">Settimane 100%</label>
                  <input
                    type="text"
                    className="check-input"
                    value={formData.completed_training_weeks}
                    onChange={(e) => handleInputChange('completed_training_weeks', e.target.value)}
                    placeholder="Es: 3"
                  />
                </div>
              </div>

              <div className="check-textarea-wrap">
                <label className="check-textarea-label">Giorni di allenamento pianificati</label>
                <input
                  type="text"
                  className="check-input"
                  value={formData.planned_training_days}
                  onChange={(e) => handleInputChange('planned_training_days', e.target.value)}
                  placeholder="Es: Lunedì, Mercoledì, Venerdì"
                />
              </div>

              <TextareaField
                label="Tematiche per le LIVE Settimanali con gli Specialisti?"
                field="live_session_topics"
                placeholder="Argomenti che vorresti trattassimo..."
              />
            </div>
          )}

          {/* Step 5: Professional Ratings */}
          {currentStep === 5 && (
            <div>
              <p className="check-step-desc">
                Valuta da 1 a 10 il supporto ricevuto dai professionisti
              </p>

              {assignedProfessionals.map((prof) => (
                <div
                  key={prof.roleKey}
                  className="check-prof-card"
                  style={{ background: prof.cardBg, border: `1px solid ${prof.cardBorder}` }}
                >
                  <div className="check-prof-header">
                    <div className="check-prof-avatar" style={{ background: prof.avatarBg }}>
                      <i className={prof.icon}></i>
                    </div>
                    <div>
                      <div className="check-prof-name">{prof.nome}</div>
                      <div className="check-prof-role">{prof.description}</div>
                    </div>
                  </div>

                  <RatingGrid
                    value={formData[prof.ratingField]}
                    onChange={(val) => handleInputChange(prof.ratingField, val)}
                    min={1}
                    labels={['Scarso', 'Insufficiente', 'Mediocre', 'Sotto la media', 'Nella media', 'Discreto', 'Buono', 'Molto buono', 'Ottimo', 'Eccellente']}
                  />

                  <button
                    type="button"
                    className={`check-prof-feedback-toggle${feedbackOpen[prof.roleKey] ? ' open' : ''}`}
                    onClick={() => setFeedbackOpen(prev => ({ ...prev, [prof.roleKey]: !prev[prof.roleKey] }))}
                  >
                    <i className="ri-arrow-down-s-line"></i>
                    {feedbackOpen[prof.roleKey] ? 'Nascondi feedback' : 'Aggiungi feedback'}
                  </button>

                  {feedbackOpen[prof.roleKey] && (
                    <div style={{ marginTop: 8 }}>
                      <textarea
                        className="check-textarea"
                        rows="2"
                        placeholder={prof.feedbackPlaceholder}
                        value={formData[prof.feedbackField]}
                        onChange={(e) => handleInputChange(prof.feedbackField, e.target.value)}
                      />
                    </div>
                  )}
                </div>
              ))}

              {assignedProfessionals.length === 0 && (
                <div className="check-info-card" style={{ textAlign: 'center' }}>
                  <i className="ri-information-line" style={{ fontSize: 24, color: 'var(--check-primary)', marginBottom: 8, display: 'block' }}></i>
                  Nessun professionista assegnato al momento.
                </div>
              )}

              {/* Progress Rating */}
              <div className="check-prof-card" style={{ background: '#fefce8', border: '1px solid #fef08a', marginTop: 8 }}>
                <div className="check-prof-header">
                  <div className="check-prof-avatar" style={{ background: '#eab308' }}>
                    <i className="ri-line-chart-line"></i>
                  </div>
                  <div>
                    <div className="check-prof-name" style={{ fontSize: '0.9rem' }}>
                      Quanto consiglieresti CorpoSostenibile a una persona a cui vuoi bene?
                    </div>
                    <div className="check-prof-role">1 = Non Mi piace | 10 = Super soddisfatto</div>
                  </div>
                </div>
                <RatingGrid
                  value={formData.progress_rating}
                  onChange={(val) => handleInputChange('progress_rating', val)}
                  min={1}
                  labels={['Per niente', 'No', 'Poco', 'Forse no', 'Neutro', 'Forse sì', 'Sì', 'Volentieri', 'Certamente', 'Assolutamente sì']}
                />
              </div>
            </div>
          )}

          {/* Step 6: Referral */}
          {currentStep === 6 && (
            <div>
              <p className="check-step-desc">
                Segnalaci qualcuno e lascia eventuali note
              </p>

              <div className="check-info-card">
                <TextareaField
                  label="Chi è la persona a cui vuoi bene e che CorpoSostenibile può aiutare?"
                  field="referral"
                  placeholder={'Nome: Mario Rossi\nTelefono: 333 1234567'}
                  rows={4}
                />
                <div className="check-input-hint" style={{ marginTop: -12 }}>
                  Indica nome, cognome e numero di telefono
                </div>
              </div>

              <TextareaField
                label="Commenti extra"
                field="extra_comments"
                placeholder="Qualsiasi altra cosa vorresti comunicarci..."
                rows={4}
              />
            </div>
          )}

          {/* Step 7: Confirmation */}
          {currentStep === 7 && (() => {
            const photoCount = [formData.photo_front, formData.photo_side, formData.photo_back].filter(Boolean).length;
            const reflectionFields = ['what_worked', 'what_didnt_work', 'what_learned', 'what_focus_next', 'injuries_notes'];
            const reflectionCount = reflectionFields.filter(f => formData[f]?.trim()).length;
            const wellnessFields = ['digestion_rating', 'energy_rating', 'strength_rating', 'hunger_rating', 'sleep_rating', 'mood_rating', 'motivation_rating'];
            const wellnessCount = wellnessFields.filter(f => formData[f] !== null).length;
            const hasWeight = !!formData.weight;
            const profRatingFields = ['nutritionist_rating', 'psychologist_rating', 'coach_rating'];
            const profRatingCount = profRatingFields.filter(f => formData[f] !== null).length;

            return (
              <div style={{ textAlign: 'center', padding: '16px 0' }}>
                <div className="check-confirm-icon" style={{ background: '#dcfce7', color: '#22c55e' }}>
                  <i className="ri-check-double-line"></i>
                </div>
                <h5 className="check-confirm-title">Tutto pronto!</h5>
                <p className="check-confirm-desc">
                  Controlla il riepilogo e clicca "Invia" per confermare.
                </p>

                <div className="check-summary">
                  <div className="check-summary-title">Riepilogo</div>
                  <div className="check-summary-row">
                    <span className="check-summary-label">
                      <i className="ri-camera-line"></i> Foto caricate
                    </span>
                    <span className={`check-summary-value${photoCount === 0 ? ' empty' : ''}`}>
                      {photoCount}/3
                    </span>
                  </div>
                  <div className="check-summary-row">
                    <span className="check-summary-label">
                      <i className="ri-lightbulb-line"></i> Riflessioni compilate
                    </span>
                    <span className={`check-summary-value${reflectionCount === 0 ? ' empty' : ''}`}>
                      {reflectionCount}/5
                    </span>
                  </div>
                  <div className="check-summary-row">
                    <span className="check-summary-label">
                      <i className="ri-heart-pulse-line"></i> Valutazioni benessere
                    </span>
                    <span className={`check-summary-value${wellnessCount === 0 ? ' empty' : ''}`}>
                      {wellnessCount}/7
                    </span>
                  </div>
                  <div className="check-summary-row">
                    <span className="check-summary-label">
                      <i className="ri-scales-line"></i> Peso inserito
                    </span>
                    <span className={`check-summary-value${!hasWeight ? ' empty' : ''}`}>
                      {hasWeight ? `${formData.weight} kg` : 'No'}
                    </span>
                  </div>
                  {assignedProfessionals.length > 0 && (
                    <div className="check-summary-row">
                      <span className="check-summary-label">
                        <i className="ri-star-line"></i> Valutazioni professionisti
                      </span>
                      <span className={`check-summary-value${profRatingCount === 0 ? ' empty' : ''}`}>
                        {profRatingCount}/{assignedProfessionals.length}
                      </span>
                    </div>
                  )}
                </div>

                {error && (
                  <div className="check-alert-danger">
                    <i className="ri-error-warning-line"></i>
                    {error}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      </div>

      {/* Navigation */}
      <div className="check-nav">
        <button
          type="button"
          className="check-nav-btn secondary"
          onClick={handlePrev}
          disabled={currentStep === 1}
        >
          <i className="ri-arrow-left-s-line"></i>
          Indietro
        </button>

        <span className="check-nav-progress">{currentStep}/7</span>

        {currentStep < 7 ? (
          <button
            type="button"
            className="check-nav-btn primary"
            onClick={handleNext}
          >
            Avanti
            <i className="ri-arrow-right-s-line"></i>
          </button>
        ) : (
          <button
            type="button"
            className="check-nav-btn submit"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? (
              <>
                <span className="check-loading-spinner" style={{ width: 18, height: 18, borderWidth: 2, margin: 0 }}></span>
                Invio...
              </>
            ) : (
              <>
                <i className="ri-send-plane-line"></i>
                Invia
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

export default WeeklyCheckForm;

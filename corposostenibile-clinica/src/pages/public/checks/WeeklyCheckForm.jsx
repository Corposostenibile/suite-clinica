/**
 * WeeklyCheckForm - Form pubblico per il Check Settimanale
 * 7-step wizard con foto, riflessioni, valutazioni e feedback
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import publicCheckService from '../../../services/publicCheckService';

// Styles
const styles = {
  card: {
    borderRadius: '20px',
    border: 'none',
    boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
    overflow: 'hidden',
  },
  header: {
    background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    color: 'white',
    padding: '32px 24px',
    textAlign: 'center',
  },
  progressBar: {
    height: '8px',
    borderRadius: '4px',
    background: '#e2e8f0',
    overflow: 'hidden',
  },
  progressFill: (progress) => ({
    height: '100%',
    width: `${progress}%`,
    background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    transition: 'width 0.3s ease',
  }),
  stepIndicator: (isActive, isCompleted) => ({
    width: '36px',
    height: '36px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    fontWeight: 600,
    background: isCompleted ? '#22c55e' : isActive ? '#3b82f6' : '#e2e8f0',
    color: isCompleted || isActive ? 'white' : '#64748b',
    transition: 'all 0.3s ease',
  }),
  ratingBtn: (isSelected, color = '#3b82f6') => ({
    width: '44px',
    height: '44px',
    borderRadius: '12px',
    border: isSelected ? 'none' : '2px solid #e2e8f0',
    background: isSelected ? color : 'white',
    color: isSelected ? 'white' : '#64748b',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  }),
  photoUpload: {
    border: '2px dashed #e2e8f0',
    borderRadius: '16px',
    padding: '24px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    background: '#f8fafc',
  },
  photoPreview: {
    width: '100%',
    height: '200px',
    objectFit: 'cover',
    borderRadius: '12px',
  },
  btn: {
    padding: '12px 32px',
    borderRadius: '12px',
    fontWeight: 600,
    fontSize: '15px',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  btnPrimary: {
    background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    color: 'white',
  },
  btnSecondary: {
    background: '#f1f5f9',
    color: '#64748b',
  },
};

const STEPS = [
  { id: 1, title: 'Foto', icon: 'ri-camera-line' },
  { id: 2, title: 'Riflessioni', icon: 'ri-lightbulb-line' },
  { id: 3, title: 'Benessere', icon: 'ri-heart-pulse-line' },
  { id: 4, title: 'Programmi', icon: 'ri-calendar-check-line' },
  { id: 5, title: 'Valutazioni', icon: 'ri-star-line' },
  { id: 6, title: 'Referral', icon: 'ri-user-add-line' },
  { id: 7, title: 'Conferma', icon: 'ri-check-double-line' },
];

function WeeklyCheckForm() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [checkInfo, setCheckInfo] = useState(null);
  const [currentStep, setCurrentStep] = useState(1);

  // Form data
  const [formData, setFormData] = useState({
    // Step 1: Photos
    photo_front: null,
    photo_side: null,
    photo_back: null,
    // Step 2: Reflections
    what_worked: '',
    what_didnt_work: '',
    what_learned: '',
    what_focus_next: '',
    injuries_notes: '',
    // Step 3: Wellness ratings (0-10)
    digestion_rating: null,
    energy_rating: null,
    strength_rating: null,
    hunger_rating: null,
    sleep_rating: null,
    mood_rating: null,
    motivation_rating: null,
    // Step 4: Programs
    weight: '',
    nutrition_program_adherence: '',
    training_program_adherence: '',
    exercise_modifications: '',
    daily_steps: '',
    completed_training_weeks: '',
    planned_training_days: '',
    live_session_topics: '',
    // Step 5: Professional ratings (1-10)
    nutritionist_rating: null,
    nutritionist_feedback: '',
    psychologist_rating: null,
    psychologist_feedback: '',
    coach_rating: null,
    coach_feedback: '',
    progress_rating: null,
    // Step 6: Referral
    referral: '',
    extra_comments: '',
  });

  // Photo previews
  const [photoPreviews, setPhotoPreviews] = useState({
    photo_front: null,
    photo_side: null,
    photo_back: null,
  });

  useEffect(() => {
    loadCheckInfo();
  }, [token]);

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

  const handleNext = () => {
    if (currentStep < 7) {
      setCurrentStep(prev => prev + 1);
      window.scrollTo(0, 0);
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
      window.scrollTo(0, 0);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const submitData = new FormData();

      // Add all form fields
      Object.entries(formData).forEach(([key, value]) => {
        if (value !== null && value !== '') {
          if (value instanceof File) {
            submitData.append(key, value);
          } else {
            submitData.append(key, value);
          }
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

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status"></div>
        <p className="text-muted mt-3">Caricamento check...</p>
      </div>
    );
  }

  if (error && !checkInfo) {
    return (
      <div className="card" style={styles.card}>
        <div className="card-body text-center py-5">
          <i className="ri-error-warning-line text-danger" style={{ fontSize: '48px' }}></i>
          <h5 className="mt-3 text-danger">Errore</h5>
          <p className="text-muted">{error}</p>
        </div>
      </div>
    );
  }

  // Rating component
  const RatingSelector = ({ value, onChange, max = 10, min = 0, labels = {} }) => (
    <div className="d-flex flex-wrap gap-2 justify-content-center">
      {Array.from({ length: max - min + 1 }, (_, i) => i + min).map(num => (
        <button
          key={num}
          type="button"
          style={styles.ratingBtn(value === num)}
          onClick={() => onChange(num)}
        >
          {num}
        </button>
      ))}
      {labels.min && labels.max && (
        <div className="w-100 d-flex justify-content-between mt-2">
          <small className="text-muted">{labels.min}</small>
          <small className="text-muted">{labels.max}</small>
        </div>
      )}
    </div>
  );

  // Photo upload component
  const PhotoUpload = ({ field, label }) => (
    <div className="col-md-4 mb-3">
      <label className="d-block mb-2 fw-medium text-center">{label}</label>
      <div
        style={{
          ...styles.photoUpload,
          borderColor: photoPreviews[field] ? '#3b82f6' : '#e2e8f0',
        }}
        onClick={() => document.getElementById(field).click()}
      >
        {photoPreviews[field] ? (
          <img src={photoPreviews[field]} alt={label} style={styles.photoPreview} />
        ) : (
          <>
            <i className="ri-camera-line text-muted" style={{ fontSize: '32px' }}></i>
            <p className="text-muted small mt-2 mb-0">Clicca per caricare</p>
          </>
        )}
      </div>
      <input
        type="file"
        id={field}
        accept="image/*"
        className="d-none"
        onChange={(e) => handlePhotoChange(field, e.target.files[0])}
      />
    </div>
  );

  return (
    <div className="card" style={styles.card}>
      {/* Header */}
      <div style={styles.header}>
        <h4 className="mb-2 fw-bold">Check Settimanale</h4>
        {checkInfo?.cliente && (
          <p className="mb-0 opacity-75">
            Ciao {checkInfo.cliente.nome}!
          </p>
        )}
      </div>

      {/* Progress */}
      <div className="px-4 pt-4">
        <div style={styles.progressBar}>
          <div style={styles.progressFill(progress)}></div>
        </div>
        <div className="d-flex justify-content-between mt-3 mb-4">
          {STEPS.map(step => (
            <div key={step.id} className="text-center" style={{ flex: 1 }}>
              <div
                style={styles.stepIndicator(currentStep === step.id, currentStep > step.id)}
                className="mx-auto mb-1"
              >
                {currentStep > step.id ? (
                  <i className="ri-check-line"></i>
                ) : (
                  step.id
                )}
              </div>
              <small className={`d-none d-md-block ${currentStep === step.id ? 'text-primary fw-semibold' : 'text-muted'}`}>
                {step.title}
              </small>
            </div>
          ))}
        </div>
      </div>

      {/* Form Content */}
      <div className="card-body px-4 pb-4">
        {/* Step 1: Photos */}
        {currentStep === 1 && (
          <div>
            <h5 className="mb-4 text-center">
              <i className="ri-camera-line me-2 text-primary"></i>
              Foto del tuo fisico
            </h5>
            <p className="text-muted text-center mb-4">
              Carica le foto frontale, laterale e posteriore per monitorare i tuoi progressi
            </p>
            <div className="row">
              <PhotoUpload field="photo_front" label="Frontale" />
              <PhotoUpload field="photo_side" label="Laterale" />
              <PhotoUpload field="photo_back" label="Posteriore" />
            </div>
          </div>
        )}

        {/* Step 2: Reflections */}
        {currentStep === 2 && (
          <div>
            <h5 className="mb-4 text-center">
              <i className="ri-lightbulb-line me-2 text-primary"></i>
              Riflessioni sulla settimana
            </h5>

            <div className="mb-4">
              <label className="form-label fw-medium">
                Cosa ha funzionato bene per te la settimana scorsa?
              </label>
              <textarea
                className="form-control"
                rows="3"
                value={formData.what_worked}
                onChange={(e) => handleInputChange('what_worked', e.target.value)}
                placeholder="Racconta cosa è andato bene..."
              />
            </div>

            <div className="mb-4">
              <label className="form-label fw-medium">
                Cosa NON ha funzionato bene per te la settimana scorsa?
              </label>
              <textarea
                className="form-control"
                rows="3"
                value={formData.what_didnt_work}
                onChange={(e) => handleInputChange('what_didnt_work', e.target.value)}
                placeholder="Racconta le difficoltà incontrate..."
              />
            </div>

            <div className="mb-4">
              <label className="form-label fw-medium">
                Cosa hai imparato da ciò che ha funzionato e non ha funzionato?
              </label>
              <textarea
                className="form-control"
                rows="3"
                value={formData.what_learned}
                onChange={(e) => handleInputChange('what_learned', e.target.value)}
                placeholder="Quali lezioni porti con te..."
              />
            </div>

            <div className="mb-4">
              <label className="form-label fw-medium">
                Su cosa pensi sia necessario focalizzarci la prossima settimana?
              </label>
              <textarea
                className="form-control"
                rows="3"
                value={formData.what_focus_next}
                onChange={(e) => handleInputChange('what_focus_next', e.target.value)}
                placeholder="I tuoi obiettivi per la prossima settimana..."
              />
            </div>

            <div className="mb-4">
              <label className="form-label fw-medium">
                Infortuni o qualcosa di cui devo essere messo a conoscenza?
              </label>
              <textarea
                className="form-control"
                rows="3"
                value={formData.injuries_notes}
                onChange={(e) => handleInputChange('injuries_notes', e.target.value)}
                placeholder="Segnala eventuali problemi..."
              />
            </div>
          </div>
        )}

        {/* Step 3: Wellness */}
        {currentStep === 3 && (
          <div>
            <h5 className="mb-4 text-center">
              <i className="ri-heart-pulse-line me-2 text-primary"></i>
              Valutazione del benessere
            </h5>
            <p className="text-muted text-center mb-4">
              Valuta da 0 a 10 i seguenti aspetti della tua settimana
            </p>

            {[
              { field: 'digestion_rating', label: 'Valuta la tua digestione questa settimana:', min: 'Pessima', max: 'Eccellente' },
              { field: 'energy_rating', label: 'Valuta i tuoi livelli di energia questa settimana:', min: 'Molto bassa', max: 'Altissima' },
              { field: 'strength_rating', label: 'Valuta il tuo livello di forza questa settimana:', min: 'Molto bassa', max: 'Elevata' },
              { field: 'hunger_rating', label: 'Valuta il tuo livello di fame questa settimana:', min: 'Non ho avuto fame', max: 'Famissima' },
              { field: 'sleep_rating', label: 'Valuta la tua qualità del sonno:', min: 'Pessimo', max: 'Eccellente' },
              { field: 'mood_rating', label: 'Valuta il tuo umore questa settimana:', min: 'Pessimo', max: 'Eccellente' },
              { field: 'motivation_rating', label: 'Valuta la tua motivazione questa settimana:', min: 'Minima', max: 'Massima' },
            ].map(item => (
              <div key={item.field} className="mb-4 p-3 rounded" style={{ background: '#f8fafc' }}>
                <label className="form-label fw-medium d-block text-center mb-3">
                  {item.label}
                </label>
                <RatingSelector
                  value={formData[item.field]}
                  onChange={(val) => handleInputChange(item.field, val)}
                  labels={{ min: item.min, max: item.max }}
                />
              </div>
            ))}
          </div>
        )}

        {/* Step 4: Programs */}
        {currentStep === 4 && (
          <div>
            <h5 className="mb-4 text-center">
              <i className="ri-calendar-check-line me-2 text-primary"></i>
              Peso e Programmi
            </h5>

            <div className="mb-4">
              <label className="form-label fw-medium">Peso (Kg)</label>
              <input
                type="number"
                className="form-control"
                step="0.1"
                value={formData.weight}
                onChange={(e) => handleInputChange('weight', e.target.value)}
                placeholder="Es: 75.5"
              />
              <small className="text-muted">A stomaco vuoto e dopo essere andato/a in bagno se possibile. Ma solo se vuoi!</small>
            </div>

            <div className="mb-4">
              <label className="form-label fw-medium">
                Stai riuscendo a rispettare il PROGRAMMA ALIMENTARE?
              </label>
              <textarea
                className="form-control"
                rows="3"
                value={formData.nutrition_program_adherence}
                onChange={(e) => handleInputChange('nutrition_program_adherence', e.target.value)}
              />
            </div>

            <div className="mb-4">
              <label className="form-label fw-medium">
                Stai riuscendo a rispettare il PROGRAMMA SPORTIVO?
              </label>
              <textarea
                className="form-control"
                rows="3"
                value={formData.training_program_adherence}
                onChange={(e) => handleInputChange('training_program_adherence', e.target.value)}
              />
            </div>

            <div className="mb-4">
              <label className="form-label fw-medium">
                Quali esercizi non hai fatto o hai aggiunto?
              </label>
              <textarea
                className="form-control"
                rows="3"
                value={formData.exercise_modifications}
                onChange={(e) => handleInputChange('exercise_modifications', e.target.value)}
              />
            </div>

            <div className="row">
              <div className="col-md-6 mb-4">
                <label className="form-label fw-medium">Quanti passi in media al giorno hai fatto?</label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.daily_steps}
                  onChange={(e) => handleInputChange('daily_steps', e.target.value)}
                  placeholder="Es: 8000"
                />
              </div>
              <div className="col-md-6 mb-4">
                <label className="form-label fw-medium">Quante settimane di allenamento hai rispettato al 100%?</label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.completed_training_weeks}
                  onChange={(e) => handleInputChange('completed_training_weeks', e.target.value)}
                />
              </div>
            </div>

            <div className="mb-4">
              <label className="form-label fw-medium">
                In quali giorni hai pianificato di allenarti?
              </label>
              <input
                type="text"
                className="form-control"
                value={formData.planned_training_days}
                onChange={(e) => handleInputChange('planned_training_days', e.target.value)}
                placeholder="Es: Lunedì, Mercoledì, Venerdì"
              />
            </div>

            <div className="mb-4">
              <label className="form-label fw-medium">
                Ogni settimana ci sono delle LIVE Settimanali con gli Specialisti! Hai delle tematiche che vorresti trattassimo?
              </label>
              <textarea
                className="form-control"
                rows="3"
                value={formData.live_session_topics}
                onChange={(e) => handleInputChange('live_session_topics', e.target.value)}
                placeholder="Argomenti che vorresti trattassimo..."
              />
            </div>
          </div>
        )}

        {/* Step 5: Professional Ratings */}
        {currentStep === 5 && (
          <div>
            <h5 className="mb-4 text-center">
              <i className="ri-star-line me-2 text-primary"></i>
              Valutazione dei professionisti
            </h5>
            <p className="text-muted text-center mb-4">
              Valuta da 1 a 10 il supporto ricevuto dai professionisti
            </p>

            {/* Nutritionist */}
            <div className="mb-4 p-4 rounded" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
              <div className="d-flex align-items-center mb-3">
                <div className="rounded-circle bg-success text-white d-flex align-items-center justify-content-center me-3"
                     style={{ width: '48px', height: '48px' }}>
                  <i className="ri-user-heart-line fs-5"></i>
                </div>
                <div>
                  <h6 className="mb-0 fw-semibold">Nutrizionista</h6>
                  <small className="text-muted">Valuta il supporto nutrizionale</small>
                </div>
              </div>
              <RatingSelector
                value={formData.nutritionist_rating}
                onChange={(val) => handleInputChange('nutritionist_rating', val)}
                min={1}
                labels={{ min: 'Scarso', max: 'Eccellente' }}
              />
              <textarea
                className="form-control mt-3"
                rows="2"
                placeholder="Feedback per il nutrizionista (opzionale)"
                value={formData.nutritionist_feedback}
                onChange={(e) => handleInputChange('nutritionist_feedback', e.target.value)}
              />
            </div>

            {/* Psychologist */}
            <div className="mb-4 p-4 rounded" style={{ background: '#eff6ff', border: '1px solid #bfdbfe' }}>
              <div className="d-flex align-items-center mb-3">
                <div className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center me-3"
                     style={{ width: '48px', height: '48px' }}>
                  <i className="ri-mental-health-line fs-5"></i>
                </div>
                <div>
                  <h6 className="mb-0 fw-semibold">Psicologo/a</h6>
                  <small className="text-muted">Valuta il supporto psicologico</small>
                </div>
              </div>
              <RatingSelector
                value={formData.psychologist_rating}
                onChange={(val) => handleInputChange('psychologist_rating', val)}
                min={1}
                labels={{ min: 'Scarso', max: 'Eccellente' }}
              />
              <textarea
                className="form-control mt-3"
                rows="2"
                placeholder="Feedback per lo psicologo (opzionale)"
                value={formData.psychologist_feedback}
                onChange={(e) => handleInputChange('psychologist_feedback', e.target.value)}
              />
            </div>

            {/* Coach */}
            <div className="mb-4 p-4 rounded" style={{ background: '#faf5ff', border: '1px solid #e9d5ff' }}>
              <div className="d-flex align-items-center mb-3">
                <div className="rounded-circle text-white d-flex align-items-center justify-content-center me-3"
                     style={{ width: '48px', height: '48px', background: '#8b5cf6' }}>
                  <i className="ri-run-line fs-5"></i>
                </div>
                <div>
                  <h6 className="mb-0 fw-semibold">Coach</h6>
                  <small className="text-muted">Valuta il supporto sportivo</small>
                </div>
              </div>
              <RatingSelector
                value={formData.coach_rating}
                onChange={(val) => handleInputChange('coach_rating', val)}
                min={1}
                labels={{ min: 'Scarso', max: 'Eccellente' }}
              />
              <textarea
                className="form-control mt-3"
                rows="2"
                placeholder="Feedback per il coach (opzionale)"
                value={formData.coach_feedback}
                onChange={(e) => handleInputChange('coach_feedback', e.target.value)}
              />
            </div>

            {/* Progress Rating */}
            <div className="p-4 rounded" style={{ background: '#fefce8', border: '1px solid #fef08a' }}>
              <h6 className="mb-3 fw-semibold text-center">
                <i className="ri-line-chart-line me-2"></i>
                Quanto consiglieresti a una persona a cui vuoi bene, su una scala da 1 a 10, il programma CorpoSostenibile?
              </h6>
              <p className="text-muted text-center small mb-3">
                1 = Non Mi piace | 10 = Sono super soddisfatto
              </p>
              <RatingSelector
                value={formData.progress_rating}
                onChange={(val) => handleInputChange('progress_rating', val)}
                min={1}
                labels={{ min: 'Per niente', max: 'Assolutamente sì' }}
              />
            </div>
          </div>
        )}

        {/* Step 6: Referral */}
        {currentStep === 6 && (
          <div>
            <h5 className="mb-4 text-center">
              <i className="ri-user-add-line me-2 text-primary"></i>
              Referral e Note
            </h5>

            <div className="mb-4 p-4 rounded" style={{ background: '#f8fafc' }}>
              <label className="form-label fw-medium">
                Chi è la persona a cui vuoi bene e che sai che noi di CorpoSostenibile possiamo aiutare?
              </label>
              <p className="text-muted small mb-3">
                Indica nome, cognome e numero di telefono della persona
              </p>
              <textarea
                className="form-control"
                rows="4"
                value={formData.referral}
                onChange={(e) => handleInputChange('referral', e.target.value)}
                placeholder="Nome: Mario Rossi&#10;Telefono: 333 1234567"
              />
            </div>

            <div className="mb-4">
              <label className="form-label fw-medium">
                Commenti extra
              </label>
              <textarea
                className="form-control"
                rows="4"
                value={formData.extra_comments}
                onChange={(e) => handleInputChange('extra_comments', e.target.value)}
                placeholder="Qualsiasi altra cosa vorresti comunicarci..."
              />
            </div>
          </div>
        )}

        {/* Step 7: Confirmation */}
        {currentStep === 7 && (
          <div className="text-center">
            <div className="mb-4">
              <div className="rounded-circle bg-success bg-opacity-10 d-inline-flex align-items-center justify-content-center"
                   style={{ width: '80px', height: '80px' }}>
                <i className="ri-check-double-line text-success" style={{ fontSize: '40px' }}></i>
              </div>
            </div>
            <h5 className="mb-3">Tutto pronto!</h5>
            <p className="text-muted mb-4">
              Hai completato tutte le sezioni del check settimanale.
              Clicca su "Invia Check" per confermare.
            </p>

            {error && (
              <div className="alert alert-danger mb-4">
                <i className="ri-error-warning-line me-2"></i>
                {error}
              </div>
            )}
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="d-flex justify-content-between mt-4 pt-4 border-top">
          <button
            type="button"
            style={{ ...styles.btn, ...styles.btnSecondary }}
            onClick={handlePrev}
            disabled={currentStep === 1}
          >
            <i className="ri-arrow-left-line me-2"></i>
            Indietro
          </button>

          {currentStep < 7 ? (
            <button
              type="button"
              style={{ ...styles.btn, ...styles.btnPrimary }}
              onClick={handleNext}
            >
              Avanti
              <i className="ri-arrow-right-line ms-2"></i>
            </button>
          ) : (
            <button
              type="button"
              style={{ ...styles.btn, ...styles.btnPrimary }}
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2"></span>
                  Invio in corso...
                </>
              ) : (
                <>
                  <i className="ri-send-plane-line me-2"></i>
                  Invia Check
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default WeeklyCheckForm;

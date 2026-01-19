/**
 * DCACheckForm - Form pubblico per il Check DCA (Benessere)
 * Form a pagina singola con sezioni per valutazione benessere psicologico
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
    background: 'linear-gradient(135deg, #a855f7 0%, #9333ea 100%)',
    color: 'white',
    padding: '32px 24px',
    textAlign: 'center',
  },
  section: {
    background: '#f8fafc',
    borderRadius: '16px',
    padding: '24px',
    marginBottom: '24px',
  },
  sectionTitle: {
    fontSize: '1rem',
    fontWeight: 600,
    color: '#1e293b',
    marginBottom: '20px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  sectionIcon: {
    width: '40px',
    height: '40px',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '20px',
  },
  ratingBtn: (isSelected, color = '#a855f7') => ({
    flex: 1,
    padding: '12px 8px',
    borderRadius: '10px',
    border: isSelected ? 'none' : '2px solid #e2e8f0',
    background: isSelected ? color : 'white',
    color: isSelected ? 'white' : '#64748b',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    textAlign: 'center',
  }),
  questionRow: {
    background: 'white',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '12px',
  },
  btn: {
    padding: '14px 40px',
    borderRadius: '12px',
    fontWeight: 600,
    fontSize: '16px',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    background: 'linear-gradient(135deg, #a855f7 0%, #9333ea 100%)',
    color: 'white',
  },
};

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

function DCACheckForm() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [checkInfo, setCheckInfo] = useState(null);
  const [formData, setFormData] = useState({});

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

  // Rating selector for 1-5 scale
  const RatingSelector5 = ({ value, onChange, labels, inverted }) => (
    <div className="d-flex gap-2 mt-2">
      {labels.map((label, idx) => (
        <button
          key={idx}
          type="button"
          style={styles.ratingBtn(value === idx + 1, inverted ? '#ef4444' : '#a855f7')}
          onClick={() => onChange(idx + 1)}
        >
          {label}
        </button>
      ))}
    </div>
  );

  // Rating selector for 0-10 scale
  const RatingSelector10 = ({ value, onChange }) => (
    <div className="d-flex flex-wrap gap-2 justify-content-center mt-2">
      {Array.from({ length: 11 }, (_, i) => i).map(num => (
        <button
          key={num}
          type="button"
          style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            border: value === num ? 'none' : '2px solid #e2e8f0',
            background: value === num ? '#a855f7' : 'white',
            color: value === num ? 'white' : '#64748b',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          onClick={() => onChange(num)}
        >
          {num}
        </button>
      ))}
    </div>
  );

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border" style={{ color: '#a855f7' }} role="status"></div>
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

  return (
    <div className="card" style={styles.card}>
      {/* Header */}
      <div style={styles.header}>
        <h4 className="mb-2 fw-bold">Check Benessere</h4>
        {checkInfo?.cliente && (
          <p className="mb-0 opacity-75">
            Ciao {checkInfo.cliente.nome}!
          </p>
        )}
        <p className="mb-0 mt-2 small opacity-75">
          Prenditi qualche minuto per riflettere sul tuo benessere
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="card-body p-4">
        {/* Sections with 1-5 ratings */}
        {SECTIONS.map(section => (
          <div key={section.id} style={styles.section}>
            <div style={styles.sectionTitle}>
              <div style={{ ...styles.sectionIcon, background: `${section.color}20`, color: section.color }}>
                <i className={section.icon}></i>
              </div>
              {section.title}
            </div>

            {section.questions.map(q => (
              <div key={q.field} style={styles.questionRow}>
                <label className="form-label fw-medium mb-2">{q.label}</label>
                <RatingSelector5
                  value={formData[q.field]}
                  onChange={(val) => handleRatingChange(q.field, val)}
                  labels={q.labels}
                  inverted={q.inverted}
                />
              </div>
            ))}
          </div>
        ))}

        {/* Physical Parameters (0-10) */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <div style={{ ...styles.sectionIcon, background: '#3b82f620', color: '#3b82f6' }}>
              <i className="ri-pulse-line"></i>
            </div>
            Parametri Fisici (0-10)
          </div>

          <div className="row">
            {PHYSICAL_PARAMS.map(param => (
              <div key={param.field} className="col-md-6 mb-3">
                <div style={styles.questionRow}>
                  <label className="form-label fw-medium mb-2 d-flex align-items-center gap-2">
                    <i className={`${param.icon} text-primary`}></i>
                    {param.label}
                  </label>
                  <RatingSelector10
                    value={formData[param.field]}
                    onChange={(val) => handleRatingChange(param.field, val)}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Notes Section */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <div style={{ ...styles.sectionIcon, background: '#64748b20', color: '#64748b' }}>
              <i className="ri-edit-line"></i>
            </div>
            Note Aggiuntive
          </div>

          <div className="mb-4">
            <label className="form-label fw-medium">
              Vuoi segnalarci qualcuno? (opzionale)
            </label>
            <textarea
              className="form-control"
              rows="3"
              value={formData.referral || ''}
              onChange={(e) => handleRatingChange('referral', e.target.value)}
              placeholder="Nome e contatto di qualcuno che potrebbe beneficiare del programma..."
            />
          </div>

          <div>
            <label className="form-label fw-medium">
              Commenti extra (opzionale)
            </label>
            <textarea
              className="form-control"
              rows="3"
              value={formData.extra_comments || ''}
              onChange={(e) => handleRatingChange('extra_comments', e.target.value)}
              placeholder="Qualsiasi altra cosa vorresti comunicarci..."
            />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="alert alert-danger mb-4">
            <i className="ri-error-warning-line me-2"></i>
            {error}
          </div>
        )}

        {/* Submit */}
        <div className="text-center">
          <button type="submit" style={styles.btn} disabled={submitting}>
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
        </div>
      </form>
    </div>
  );
}

export default DCACheckForm;

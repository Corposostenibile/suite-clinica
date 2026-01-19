/**
 * MinorCheckForm - Form pubblico per il Check Minori (EDE-Q6)
 * Questionario screening disturbi alimentari - 28 domande
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
    background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
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
  questionRow: {
    background: 'white',
    borderRadius: '12px',
    padding: '16px',
    marginBottom: '12px',
  },
  questionNumber: {
    width: '28px',
    height: '28px',
    borderRadius: '8px',
    background: '#f59e0b',
    color: 'white',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    fontWeight: 700,
    marginRight: '12px',
  },
  ratingBtn: (isSelected) => ({
    flex: 1,
    padding: '10px 6px',
    borderRadius: '8px',
    border: isSelected ? 'none' : '2px solid #e2e8f0',
    background: isSelected ? '#f59e0b' : 'white',
    color: isSelected ? 'white' : '#64748b',
    fontSize: '11px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    textAlign: 'center',
    lineHeight: '1.3',
  }),
  btn: {
    padding: '14px 40px',
    borderRadius: '12px',
    fontWeight: 600,
    fontSize: '16px',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    color: 'white',
  },
};

// Frequency scale (0-6 days)
const FREQ_LABELS = ['Mai', '1-5 gg', '6-12 gg', '13-15 gg', '16-22 gg', '23-27 gg', 'Ogni giorno'];

// Intensity scale (0-6)
const INTENSITY_LABELS = ['Per niente', 'Poco', 'Lievemente', 'Moderatamente', 'Abbastanza', 'Molto', 'Notevolmente'];

// Questions configuration
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

function MinorCheckForm() {
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

  // Frequency selector (0-6)
  const FrequencySelector = ({ value, onChange, labels = FREQ_LABELS }) => (
    <div className="d-flex gap-1 mt-2 flex-wrap">
      {labels.map((label, idx) => (
        <button
          key={idx}
          type="button"
          style={styles.ratingBtn(value === idx)}
          onClick={() => onChange(idx)}
        >
          {label}
        </button>
      ))}
    </div>
  );

  // Number input for episodes
  const EpisodeInput = ({ value, onChange, max }) => (
    <input
      type="number"
      className="form-control mt-2"
      min="0"
      max={max}
      value={value || ''}
      onChange={(e) => onChange(parseInt(e.target.value) || 0)}
      placeholder="0"
      style={{ maxWidth: '120px' }}
    />
  );

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border" style={{ color: '#f59e0b' }} role="status"></div>
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
        <h4 className="mb-2 fw-bold">Check Minori</h4>
        {checkInfo?.cliente && (
          <p className="mb-0 opacity-75">
            Ciao {checkInfo.cliente.nome}!
          </p>
        )}
        <p className="mb-0 mt-2 small opacity-75">
          Rispondi pensando agli ultimi 28 giorni
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="card-body p-4">

        {/* Section 1: Frequency Questions */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <div style={{ ...styles.sectionIcon, background: '#f59e0b20', color: '#f59e0b' }}>
              <i className="ri-calendar-line"></i>
            </div>
            Frequenza negli ultimi 28 giorni
          </div>
          <p className="text-muted small mb-4">
            Indica in quanti giorni hai sperimentato quanto descritto
          </p>

          {FREQUENCY_QUESTIONS.map((q, idx) => (
            <div key={q.field} style={styles.questionRow}>
              <label className="form-label fw-medium mb-0">
                <span style={styles.questionNumber}>{idx + 1}</span>
                {q.label}
              </label>
              <FrequencySelector
                value={formData[q.field]}
                onChange={(val) => handleChange(q.field, val)}
              />
            </div>
          ))}
        </div>

        {/* Section 2: Episode Questions */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <div style={{ ...styles.sectionIcon, background: '#ef444420', color: '#ef4444' }}>
              <i className="ri-error-warning-line"></i>
            </div>
            Episodi Specifici
          </div>
          <p className="text-muted small mb-4">
            Indica il numero di episodi negli ultimi 28 giorni
          </p>

          {EPISODE_QUESTIONS.map((q, idx) => (
            <div key={q.field} style={styles.questionRow}>
              <label className="form-label fw-medium mb-0">
                <span style={styles.questionNumber}>{idx + 13}</span>
                {q.label}
              </label>
              <EpisodeInput
                value={formData[q.field]}
                onChange={(val) => handleChange(q.field, val)}
                max={q.max || 999}
              />
            </div>
          ))}
        </div>

        {/* Section 3: Behavior Questions */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <div style={{ ...styles.sectionIcon, background: '#3b82f620', color: '#3b82f6' }}>
              <i className="ri-user-heart-line"></i>
            </div>
            Comportamenti Alimentari
          </div>

          {BEHAVIOR_QUESTIONS.map((q, idx) => (
            <div key={q.field} style={styles.questionRow}>
              <label className="form-label fw-medium mb-0">
                <span style={styles.questionNumber}>{idx + 19}</span>
                {q.label}
              </label>
              <FrequencySelector
                value={formData[q.field]}
                onChange={(val) => handleChange(q.field, val)}
                labels={q.labels || (q.type === 'intensity' ? INTENSITY_LABELS : FREQ_LABELS)}
              />
            </div>
          ))}
        </div>

        {/* Section 4: Self Assessment */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <div style={{ ...styles.sectionIcon, background: '#8b5cf620', color: '#8b5cf6' }}>
              <i className="ri-mental-health-line"></i>
            </div>
            Autovalutazione
          </div>
          <p className="text-muted small mb-4">
            Indica quanto ti riconosci in queste affermazioni
          </p>

          {SELF_ASSESSMENT_QUESTIONS.map((q, idx) => (
            <div key={q.field} style={styles.questionRow}>
              <label className="form-label fw-medium mb-0">
                <span style={styles.questionNumber}>{idx + 22}</span>
                {q.label}
              </label>
              <FrequencySelector
                value={formData[q.field]}
                onChange={(val) => handleChange(q.field, val)}
                labels={INTENSITY_LABELS}
              />
            </div>
          ))}
        </div>

        {/* Final Info Section */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <div style={{ ...styles.sectionIcon, background: '#22c55e20', color: '#22c55e' }}>
              <i className="ri-scales-line"></i>
            </div>
            Informazioni Finali
          </div>

          <div className="row">
            <div className="col-md-6 mb-3">
              <label className="form-label fw-medium">Peso attuale (kg)</label>
              <input
                type="number"
                className="form-control"
                step="0.1"
                min="30"
                max="300"
                value={formData.peso_attuale || ''}
                onChange={(e) => handleChange('peso_attuale', parseFloat(e.target.value))}
                placeholder="Es: 55.5"
              />
            </div>
            <div className="col-md-6 mb-3">
              <label className="form-label fw-medium">Altezza (cm)</label>
              <input
                type="number"
                className="form-control"
                min="100"
                max="250"
                value={formData.altezza || ''}
                onChange={(e) => handleChange('altezza', parseInt(e.target.value))}
                placeholder="Es: 165"
              />
            </div>
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

export default MinorCheckForm;

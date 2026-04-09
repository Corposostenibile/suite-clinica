/**
 * MinorCheckForm - Form pubblico per il Check Minori (Adolescenti 14-18 anni)
 * Questionario percorso adolescenziale - sezioni qualitative + EDE-Q6 legacy
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import publicCheckService from '../../../services/publicCheckService';
import './PublicChecks.css';

// ─── Radio option maps ─────────────────────────────────────────────────────
const SENTIRE_OPTIONS = [
  { value: 0, label: 'Molto bene' },
  { value: 1, label: 'Bene' },
  { value: 2, label: 'Così così' },
  { value: 3, label: 'Non molto bene' },
  { value: 4, label: 'Male' },
];

const PERCORSO_OPTIONS = [
  { value: 0, label: 'Mi sta aiutando molto' },
  { value: 1, label: 'Mi trovo bene' },
  { value: 2, label: 'È ok' },
  { value: 3, label: 'Mi crea qualche difficoltà' },
  { value: 4, label: 'Non mi trovo bene' },
];

const ASCOLTO_OPTIONS = [
  { value: 0, label: 'Sì' },
  { value: 1, label: 'A volte' },
  { value: 2, label: 'No' },
];

const PRATICA_OPTIONS = [
  { value: 0, label: 'Quasi sempre' },
  { value: 1, label: 'Spesso' },
  { value: 2, label: 'A volte' },
  { value: 3, label: 'Raramente' },
];

const RICONOSCI_OPTIONS = [
  { value: 0, label: 'Sì' },
  { value: 1, label: 'A volte' },
  { value: 2, label: 'No' },
];

const MANGIARE_SENZA_FAME_OPTIONS = [
  { value: 0, label: 'Spesso' },
  { value: 1, label: 'A volte' },
  { value: 2, label: 'Raramente' },
];

const ENERGIA_OPTIONS = [
  { value: 0, label: 'Alta' },
  { value: 1, label: 'Adeguata' },
  { value: 2, label: 'Bassa' },
];

const SONNO_OPTIONS = [
  { value: 0, label: 'Bene' },
  { value: 1, label: 'Abbastanza bene' },
  { value: 2, label: 'Male' },
];

const SENTIMENTO_PESO_OPTIONS = [
  { value: 0, label: 'Sereno/a' },
  { value: 1, label: 'Indifferente' },
  { value: 2, label: 'A disagio' },
];

const FATICHE_SITUAZIONI = [
  { value: 'colazione', label: 'Colazione' },
  { value: 'pranzo', label: 'Pranzo' },
  { value: 'cena', label: 'Cena' },
  { value: 'fuori_casa', label: 'Fuori casa' },
  { value: 'scuola', label: 'A scuola' },
  { value: 'amici', label: 'Con amici' },
  { value: 'famiglia', label: 'In famiglia' },
];

const ASPETTI_DIFFICILI = [
  { value: 'troppo_impegnativi', label: 'Troppo impegnativi' },
  { value: 'ripetitivi', label: 'Poco stimolanti o ripetitivi' },
  { value: 'poco_chiari', label: 'Poco chiari' },
];

// ─── Sections definition ────────────────────────────────────────────────────
const ALL_SECTIONS = [
  {
    id: 'sentire',
    title: 'Come ti senti in questo periodo',
    icon: 'ri-emotion-line',
    color: '#f59e0b',
  },
  {
    id: 'percorso',
    title: 'Il percorso alimentare',
    icon: 'ri-restaurant-line',
    color: '#3b82f6',
  },
  {
    id: 'cibo',
    title: 'Cibo e quotidianità',
    icon: 'ri-cup-line',
    color: '#8b5cf6',
  },
  {
    id: 'fame',
    title: 'Fame, sazietà e ascolto del corpo',
    icon: 'ri-heart-pulse-line',
    color: '#ec4899',
  },
  {
    id: 'energia',
    title: 'Energia, digestione e sonno',
    icon: 'ri-flashlight-line',
    color: '#22c55e',
  },
  {
    id: 'peso',
    title: 'Peso e crescita',
    icon: 'ri-scales-3-line',
    color: '#64748b',
    subtitle: 'Solo se concordato con il professionista',
  },
  {
    id: 'migliorare',
    title: 'Cosa possiamo migliorare',
    icon: 'ri-lightbulb-line',
    color: '#f97316',
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

  useEffect(() => {
    loadCheckInfo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handleCheckboxChange = (field, value) => {
    setFormData(prev => {
      const current = prev[field] || [];
      if (current.includes(value)) {
        return { ...prev, [field]: current.filter(v => v !== value) };
      }
      return { ...prev, [field]: [...current, value] };
    });
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

  // Count answered fields
  const allFields = [
    'sentire_generale', 'difficolta',
    'percorso_vissuto', 'percorso_racconto',
    'aspetti_difficili', 'aspetti_difficili_dettaglio',
    'ascoltato', 'ascoltato_situazioni',
    'pratica_quotidiana', 'fatica_situazioni', 'alimenti_disagio',
    'riconoscere_fame', 'riconoscere_sazieta', 'mangiare_senza_fame',
    'energia', 'disturbi_fisici', 'sonno',
    'peso_attuale', 'data_misurazione', 'sentimento_peso',
    'modifiche_percorso', 'funzionamento_bene', 'approfondire',
  ];
  const totalQuestions = allFields.length;
  const answeredCount = allFields.filter(f => {
    const val = formData[f];
    if (Array.isArray(val)) return val.length > 0;
    return val != null && val !== '';
  }).length;
  const overallProgress = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;

  // Subcomponents
  const RadioSelector = ({ options, value, onChange, color }) => (
    <div className="check-radio-grid">
      {options.map(opt => (
        <button
          key={opt.value}
          type="button"
          className={`check-radio-btn${value === opt.value ? ' selected' : ''}`}
          onClick={() => onChange(opt.value)}
          style={value === opt.value ? { background: color, borderColor: color } : {}}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );

  const CheckboxGroup = ({ options, value, onChange }) => {
    const current = value || [];
    return (
      <div className="check-checkbox-grid">
        {options.map(opt => (
          <button
            key={opt.value}
            type="button"
            className={`check-checkbox-btn${current.includes(opt.value) ? ' selected' : ''}`}
            onClick={() => onChange(opt.value)}
          >
            {current.includes(opt.value) && <i className="ri-check-line"></i>}
            {opt.label}
          </button>
        ))}
      </div>
    );
  };

  const TextareaField = ({ value, onChange, placeholder }) => (
    <textarea
      className="check-textarea"
      value={value || ''}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={3}
    />
  );

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

  const f = formData;

  return (
    <div className="check-card check-theme-minor">
      {/* Header */}
      <div className="check-header">
        <h4 className="check-header-title">
          Ciao {checkInfo?.cliente?.nome || ''}!
        </h4>
        <p className="check-header-subtitle">
          È il momento del tuo check. Raccontaci come stai!
        </p>
        <p className="check-header-hint">
          <i className="ri-time-line"></i> Compilazione: ~10 min
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

          {/* ═══ SEZIONE 1: Come ti senti ═══ */}
          <div className={`check-section${collapsedSections.sentire ? ' collapsed' : ''}`}>
            <div className="check-section-header" onClick={() => toggleSection('sentire')}>
              <div className="check-section-icon" style={{ background: '#f59e0b15', color: '#f59e0b' }}>
                <i className="ri-emotion-line"></i>
              </div>
              <span className="check-section-title">Come ti senti in questo periodo</span>
              <i className="ri-arrow-down-s-line check-section-chevron"></i>
            </div>
            <div className="check-section-body">
              {/* Q1 */}
              <div className="check-question">
                <div className="check-question-label">
                  In generale, come ti senti nelle ultime settimane?
                </div>
                <RadioSelector
                  options={SENTIRE_OPTIONS}
                  value={f.sentire_generale}
                  onChange={(v) => handleChange('sentire_generale', v)}
                  color="#f59e0b"
                />
              </div>
              {/* Q2 */}
              <div className="check-question">
                <div className="check-question-label">
                  C'è qualcosa che in questo periodo ti sta mettendo in difficoltà o ti sta pesando?
                  <br /><small style={{ color: 'var(--check-text-muted)' }}>(scuola, relazioni, famiglia, sport, corpo, alimentazione, altro…)</small>
                </div>
                <TextareaField
                  value={f.difficolta}
                  onChange={(v) => handleChange('difficolta', v)}
                  placeholder="Raccontaci liberamente..."
                />
              </div>
            </div>
          </div>

          {/* ═══ SEZIONE 2: Il percorso alimentare ═══ */}
          <div className={`check-section${collapsedSections.percorso ? ' collapsed' : ''}`}>
            <div className="check-section-header" onClick={() => toggleSection('percorso')}>
              <div className="check-section-icon" style={{ background: '#3b82f615', color: '#3b82f6' }}>
                <i className="ri-restaurant-line"></i>
              </div>
              <span className="check-section-title">Il percorso alimentare</span>
              <i className="ri-arrow-down-s-line check-section-chevron"></i>
            </div>
            <div className="check-section-body">
              {/* Q3 */}
              <div className="check-question">
                <div className="check-question-label">
                  Come stai vivendo il percorso che stai facendo?
                </div>
                <RadioSelector
                  options={PERCORSO_OPTIONS}
                  value={f.percorso_vissuto}
                  onChange={(v) => handleChange('percorso_vissuto', v)}
                  color="#3b82f6"
                />
              </div>
              {/* Q4 */}
              <div className="check-question">
                <div className="check-question-label">
                  Se vuoi, racconta meglio come ti senti rispetto al percorso.
                </div>
                <TextareaField
                  value={f.percorso_racconto}
                  onChange={(v) => handleChange('percorso_racconto', v)}
                  placeholder="Scrivi qui i tuoi pensieri..."
                />
              </div>
              {/* Q5 */}
              <div className="check-question">
                <div className="check-question-label">
                  Ci sono aspetti che trovi:
                </div>
                <CheckboxGroup
                  options={ASPETTI_DIFFICILI}
                  value={f.aspetti_difficili}
                  onChange={(v) => handleCheckboxChange('aspetti_difficili', v)}
                />
              </div>
              {/* Q5b */}
              {(f.aspetti_difficili?.length > 0) && (
                <div className="check-question">
                  <div className="check-question-label">
                    Se sì, quali? Puoi spiegarlo meglio?
                  </div>
                  <TextareaField
                    value={f.aspetti_difficili_dettaglio}
                    onChange={(v) => handleChange('aspetti_difficili_dettaglio', v)}
                    placeholder="Descrivi quali aspetti trovi difficili..."
                  />
                </div>
              )}
              {/* Q6 */}
              <div className="check-question">
                <div className="check-question-label">
                  Ti senti ascoltato/a e rispettato/a nelle tue opinioni e nei tuoi tempi?
                </div>
                <RadioSelector
                  options={ASCOLTO_OPTIONS}
                  value={f.ascoltato}
                  onChange={(v) => handleChange('ascoltato', v)}
                  color="#3b82f6"
                />
              </div>
              {/* Q6b */}
              {(f.ascoltato === 1 || f.ascoltato === 2) && (
                <div className="check-question">
                  <div className="check-question-label">
                    In quali situazioni ti sei sentito/a così?
                  </div>
                  <TextareaField
                    value={f.ascoltato_situazioni}
                    onChange={(v) => handleChange('ascoltato_situazioni', v)}
                    placeholder="Raccontaci quando ti è capitato..."
                  />
                </div>
              )}
            </div>
          </div>

          {/* ═══ SEZIONE 3: Cibo e quotidianità ═══ */}
          <div className={`check-section${collapsedSections.cibo ? ' collapsed' : ''}`}>
            <div className="check-section-header" onClick={() => toggleSection('cibo')}>
              <div className="check-section-icon" style={{ background: '#8b5cf615', color: '#8b5cf6' }}>
                <i className="ri-cup-line"></i>
              </div>
              <span className="check-section-title">Cibo e quotidianità</span>
              <i className="ri-arrow-down-s-line check-section-chevron"></i>
            </div>
            <div className="check-section-body">
              {/* Q7 */}
              <div className="check-question">
                <div className="check-question-label">
                  Quanto riesci a mettere in pratica le indicazioni nella tua vita quotidiana?
                </div>
                <RadioSelector
                  options={PRATICA_OPTIONS}
                  value={f.pratica_quotidiana}
                  onChange={(v) => handleChange('pratica_quotidiana', v)}
                  color="#8b5cf6"
                />
              </div>
              {/* Q8 */}
              <div className="check-question">
                <div className="check-question-label">
                  In quali situazioni fai più fatica?
                </div>
                <CheckboxGroup
                  options={FATICHE_SITUAZIONI}
                  value={f.fatica_situazioni}
                  onChange={(v) => handleCheckboxChange('fatica_situazioni', v)}
                />
              </div>
              {/* Q9 */}
              <div className="check-question">
                <div className="check-question-label">
                  Ci sono alimenti o momenti del pasto che ti generano disagio (fisico o emotivo)?
                </div>
                <TextareaField
                  value={f.alimenti_disagio}
                  onChange={(v) => handleChange('alimenti_disagio', v)}
                  placeholder="Descrivi se ci sono situazioni che ti creano difficoltà..."
                />
              </div>
            </div>
          </div>

          {/* ═══ SEZIONE 4: Fame, sazietà e ascolto del corpo ═══ */}
          <div className={`check-section${collapsedSections.fame ? ' collapsed' : ''}`}>
            <div className="check-section-header" onClick={() => toggleSection('fame')}>
              <div className="check-section-icon" style={{ background: '#ec489915', color: '#ec4899' }}>
                <i className="ri-heart-pulse-line"></i>
              </div>
              <span className="check-section-title">Fame, sazietà e ascolto del corpo</span>
              <i className="ri-arrow-down-s-line check-section-chevron"></i>
            </div>
            <div className="check-section-body">
              {/* Q10 */}
              <div className="check-question">
                <div className="check-question-label">
                  Riesci a riconoscere quando hai realmente fame?
                </div>
                <RadioSelector
                  options={RICONOSCI_OPTIONS}
                  value={f.riconoscere_fame}
                  onChange={(v) => handleChange('riconoscere_fame', v)}
                  color="#ec4899"
                />
              </div>
              {/* Q11 */}
              <div className="check-question">
                <div className="check-question-label">
                  Riesci a riconoscere quando sei sazio/a?
                </div>
                <RadioSelector
                  options={RICONOSCI_OPTIONS}
                  value={f.riconoscere_sazieta}
                  onChange={(v) => handleChange('riconoscere_sazieta', v)}
                  color="#ec4899"
                />
              </div>
              {/* Q12 */}
              <div className="check-question">
                <div className="check-question-label">
                  Ti capita di mangiare anche in assenza di fame (per noia, stress, emozioni, abitudine)?
                </div>
                <RadioSelector
                  options={MANGIARE_SENZA_FAME_OPTIONS}
                  value={f.mangiare_senza_fame}
                  onChange={(v) => handleChange('mangiare_senza_fame', v)}
                  color="#ec4899"
                />
              </div>
            </div>
          </div>

          {/* ═══ SEZIONE 5: Energia, digestione e sonno ═══ */}
          <div className={`check-section${collapsedSections.energia ? ' collapsed' : ''}`}>
            <div className="check-section-header" onClick={() => toggleSection('energia')}>
              <div className="check-section-icon" style={{ background: '#22c55e15', color: '#22c55e' }}>
                <i className="ri-flashlight-line"></i>
              </div>
              <span className="check-section-title">Energia, digestione e sonno</span>
              <i className="ri-arrow-down-s-line check-section-chevron"></i>
            </div>
            <div className="check-section-body">
              {/* Q13 */}
              <div className="check-question">
                <div className="check-question-label">
                  Come valuti la tua energia durante la giornata?
                </div>
                <RadioSelector
                  options={ENERGIA_OPTIONS}
                  value={f.energia}
                  onChange={(v) => handleChange('energia', v)}
                  color="#22c55e"
                />
              </div>
              {/* Q14 */}
              <div className="check-question">
                <div className="check-question-label">
                  Hai avuto disturbi fisici nelle ultime settimane?
                  <br /><small style={{ color: 'var(--check-text-muted)' }}>(es. gonfiore, mal di pancia, mal di testa, nausea, irregolarità intestinale…)</small>
                </div>
                <TextareaField
                  value={f.disturbi_fisici}
                  onChange={(v) => handleChange('disturbi_fisici', v)}
                  placeholder="Descrivi eventuali disturbi..."
                />
              </div>
              {/* Q15 */}
              <div className="check-question">
                <div className="check-question-label">
                  Come stai dormendo ultimamente?
                </div>
                <RadioSelector
                  options={SONNO_OPTIONS}
                  value={f.sonno}
                  onChange={(v) => handleChange('sonno', v)}
                  color="#22c55e"
                />
              </div>
            </div>
          </div>

          {/* ═══ SEZIONE 6: Peso e crescita ═══ */}
          <div className={`check-section${collapsedSections.peso ? ' collapsed' : ''}`}>
            <div className="check-section-header" onClick={() => toggleSection('peso')}>
              <div className="check-section-icon" style={{ background: '#64748b15', color: '#64748b' }}>
                <i className="ri-scales-3-line"></i>
              </div>
              <span className="check-section-title">Peso e crescita</span>
              <i className="ri-arrow-down-s-line check-section-chevron"></i>
            </div>
            <div className="check-section-body">
              <p style={{ fontSize: '0.82rem', color: 'var(--check-text-muted)', marginBottom: 16 }}>
                <i className="ri-information-line"></i> Questa sezione viene utilizzata solo se concordata con il professionista.
              </p>
              {/* Q16 - Peso */}
              <div className="check-question">
                <div className="check-question-label">
                  Peso attuale (se richiesto)
                </div>
                <div style={{ maxWidth: 160 }}>
                  <input
                    type="number"
                    className="check-input"
                    step="0.1"
                    min="30"
                    max="300"
                    value={f.peso_attuale ?? ''}
                    onChange={(e) => handleChange('peso_attuale', e.target.value ? parseFloat(e.target.value) : null)}
                    placeholder="Es: 55.5"
                  />
                  <div className="check-input-hint">kg</div>
                </div>
              </div>
              {/* Q17 - Data misurazione */}
              <div className="check-question">
                <div className="check-question-label">
                  Data della misurazione
                </div>
                <div style={{ maxWidth: 200 }}>
                  <input
                    type="date"
                    className="check-input"
                    value={f.data_misurazione || ''}
                    onChange={(e) => handleChange('data_misurazione', e.target.value)}
                  />
                </div>
              </div>
              {/* Q18 */}
              <div className="check-question">
                <div className="check-question-label">
                  Come ti senti rispetto al peso o alle misurazioni?
                </div>
                <RadioSelector
                  options={SENTIMENTO_PESO_OPTIONS}
                  value={f.sentimento_peso}
                  onChange={(v) => handleChange('sentimento_peso', v)}
                  color="#64748b"
                />
              </div>
            </div>
          </div>

          {/* ═══ SEZIONE 9: Cosa possiamo migliorare ═══ */}
          <div className={`check-section${collapsedSections.migliorare ? ' collapsed' : ''}`}>
            <div className="check-section-header" onClick={() => toggleSection('migliorare')}>
              <div className="check-section-icon" style={{ background: '#f9731615', color: '#f97316' }}>
                <i className="ri-lightbulb-line"></i>
              </div>
              <span className="check-section-title">Cosa possiamo migliorare</span>
              <i className="ri-arrow-down-s-line check-section-chevron"></i>
            </div>
            <div className="check-section-body">
              {/* Q19 */}
              <div className="check-question">
                <div className="check-question-label">
                  C'è qualcosa che vorresti modificare nel percorso per sentirlo più adatto a te?
                </div>
                <TextareaField
                  value={f.modifiche_percorso}
                  onChange={(v) => handleChange('modifiche_percorso', v)}
                  placeholder="Scrivi le tue idee..."
                />
              </div>
              {/* Q20 */}
              <div className="check-question">
                <div className="check-question-label">
                  C'è qualcosa che senti stia funzionando particolarmente bene?
                </div>
                <TextareaField
                  value={f.funzionamento_bene}
                  onChange={(v) => handleChange('funzionamento_bene', v)}
                  placeholder="Cosa ti sta aiutando di più?"
                />
              </div>
              {/* Q21 */}
              <div className="check-question">
                <div className="check-question-label">
                  C'è un aspetto del tuo rapporto con il cibo o con il corpo che vorresti approfondire di più?
                </div>
                <TextareaField
                  value={f.approfondire}
                  onChange={(v) => handleChange('approfondire', v)}
                  placeholder="Cosa ti piacerebbe esplorare?"
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

export default MinorCheckForm;

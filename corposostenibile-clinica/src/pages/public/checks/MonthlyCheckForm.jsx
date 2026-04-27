import { useState, useEffect, useCallback, useRef } from 'react';
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

const SECTION_CONFIG = {
  // Regolare
  'Riflessioni': { icon: 'ri-quill-pen-line', color: '#22c55e' },
  'Benessere': { icon: 'ri-heart-pulse-line', color: '#3b82f6' },
  'Programmi': { icon: 'ri-calendar-check-line', color: '#8b5cf6' },
  'Note': { icon: 'ri-sticky-note-line', color: '#64748b' },
  // Minori
  'Come ti senti in questo periodo': { icon: 'ri-emotion-line', color: '#f59e0b' },
  'Il percorso alimentare': { icon: 'ri-restaurant-line', color: '#3b82f6' },
  'Cibo e quotidianità': { icon: 'ri-cup-line', color: '#8b5cf6' },
  'Fame, sazietà e ascolto del corpo': { icon: 'ri-heart-pulse-line', color: '#ec4899' },
  'Energia, digestione e sonno': { icon: 'ri-flashlight-line', color: '#22c55e' },
  'Peso e crescita': { icon: 'ri-scales-3-line', color: '#64748b' },
  'Cosa possiamo migliorare': { icon: 'ri-lightbulb-line', color: '#f97316' },
  // DCA mensile
  'Benessere emotivo e psicologico': { icon: 'ri-heart-line', color: '#ec4899' },
  'Allenamento e movimento': { icon: 'ri-run-line', color: '#3b82f6' },
  'Riposo e relazioni': { icon: 'ri-moon-line', color: '#6366f1' },
  'Gestione delle emozioni': { icon: 'ri-emotion-line', color: '#f59e0b' },
  'Sostenibilità e motivazione': { icon: 'ri-seedling-line', color: '#22c55e' },
  'Organizzazione pasti': { icon: 'ri-restaurant-line', color: '#ef4444' },
  'Parametri fisici': { icon: 'ri-activity-line', color: '#22c55e' },
};

// ─── Componenti domanda ───────────────────────────────────────────────────────

function ScaleQuestion5({ question, value, onChange }) {
  const labels = question.labels || SCALE_LABELS_1_5;
  return (
    <div className="check-question-block">
      <p className="check-question-label">{question.label}</p>
      {question.sublabel && <p className="check-question-sublabel">{question.sublabel}</p>}
      <div className="check-rating-5">
        {labels.map((label, idx) => (
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

function SelectQuestion({ question, value, onChange, color }) {
  const accent = color || '#22c55e';
  return (
    <div className="check-question-block">
      <p className="check-question-label">{question.label}</p>
      {question.sublabel && <p className="check-question-sublabel">{question.sublabel}</p>}
      <div className="check-radio-grid">
        {(question.options || []).map((opt) => (
          <button
            key={opt}
            type="button"
            className={`check-radio-btn${value === opt ? ' selected' : ''}`}
            onClick={() => onChange(question.key, opt)}
            style={value === opt ? { background: accent, borderColor: accent } : {}}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}

function MultiSelectQuestion({ question, value, onChange, color }) {
  const accent = color || '#22c55e';
  const selected = Array.isArray(value) ? value : [];
  const toggle = (opt) => {
    const next = selected.includes(opt)
      ? selected.filter((v) => v !== opt)
      : [...selected, opt];
    onChange(question.key, next.length > 0 ? next : null);
  };
  return (
    <div className="check-question-block">
      <p className="check-question-label">
        {question.label}
        {question.required === false && <span className="check-optional"> (facoltativo)</span>}
      </p>
      {question.sublabel && <p className="check-question-sublabel">{question.sublabel}</p>}
      <div className="check-checkbox-grid">
        {(question.options || []).map((opt) => (
          <button
            key={opt}
            type="button"
            className={`check-checkbox-btn${selected.includes(opt) ? ' selected' : ''}`}
            onClick={() => toggle(opt)}
            style={selected.includes(opt) ? { background: accent, borderColor: accent } : {}}
          >
            {selected.includes(opt) && <i className="ri-check-line" />}
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

function QuestionRenderer({ question, value, onChange, color }) {
  if (question.type === 'scale') {
    if (question.max === 5) return <ScaleQuestion5 question={question} value={value} onChange={onChange} />;
    return <ScaleQuestion10 question={question} value={value} onChange={onChange} />;
  }
  if (question.type === 'select') return <SelectQuestion question={question} value={value} onChange={onChange} color={color} />;
  if (question.type === 'multiselect') return <MultiSelectQuestion question={question} value={value} onChange={onChange} color={color} />;
  if (question.type === 'text') return <TextQuestion question={question} value={value} onChange={onChange} />;
  if (question.type === 'number') return <NumberQuestion question={question} value={value} onChange={onChange} />;
  return null;
}

// ─── Foto upload ──────────────────────────────────────────────────────────────

const PHOTO_FIELDS = [
  { key: 'photo_front', label: 'Frontale', icon: 'ri-user-line' },
  { key: 'photo_side', label: 'Laterale', icon: 'ri-user-follow-line' },
  { key: 'photo_back', label: 'Posteriore', icon: 'ri-user-received-2-line' },
];

function PhotoUploadSlot({ fieldKey, label, icon, file, onSelect, onRemove, accentColor }) {
  const inputRef = useRef(null);
  const previewUrl = file ? URL.createObjectURL(file) : null;

  useEffect(() => {
    return () => { if (previewUrl) URL.revokeObjectURL(previewUrl); };
  }, [previewUrl]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
      <div
        onClick={() => !file && inputRef.current?.click()}
        style={{
          width: '100%',
          aspectRatio: '3/4',
          maxHeight: 200,
          border: file ? `2px solid ${accentColor}` : '2px dashed #cbd5e1',
          borderRadius: 12,
          background: file ? '#f0fdf4' : '#f8fafc',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: file ? 'default' : 'pointer',
          overflow: 'hidden',
          position: 'relative',
          transition: 'border-color 0.2s',
        }}
      >
        {file && previewUrl ? (
          <>
            <img
              src={previewUrl}
              alt={label}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onRemove(fieldKey); }}
              style={{
                position: 'absolute', top: 6, right: 6,
                background: 'rgba(0,0,0,0.55)', color: '#fff',
                border: 'none', borderRadius: '50%', width: 26, height: 26,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', fontSize: 14,
              }}
            >
              <i className="ri-close-line" />
            </button>
          </>
        ) : (
          <div style={{ textAlign: 'center', color: '#94a3b8', padding: 8 }}>
            <i className={icon} style={{ fontSize: 28, display: 'block', marginBottom: 4 }} />
            <span style={{ fontSize: '0.7rem' }}>Tocca per aggiungere</span>
          </div>
        )}
      </div>
      <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {label}
      </span>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        style={{ display: 'none' }}
        onChange={(e) => { if (e.target.files[0]) onSelect(fieldKey, e.target.files[0]); }}
      />
    </div>
  );
}

function PhotoSection({ photos, onSelect, onRemove, accentColor }) {
  return (
    <div className="check-section-collapsible" style={{ border: '1px solid #e2e8f0' }}>
      <div
        className="check-section-toggle"
        style={{ borderLeftColor: accentColor, cursor: 'default' }}
      >
        <span className="check-section-toggle-title">
          <i className="ri-camera-line" style={{ marginRight: 6 }} />
          Foto e misure antropometriche
        </span>
        <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 500 }}>facoltativo</span>
      </div>
      <div className="check-section-body">
        <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: 16, lineHeight: 1.5 }}>
          Scatta o carica le tue foto di progressione (frontale, laterale, posteriore).
          Le foto sono riservate al tuo team di professionisti.
        </p>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          {PHOTO_FIELDS.map(({ key, label, icon }) => (
            <PhotoUploadSlot
              key={key}
              fieldKey={key}
              label={label}
              icon={icon}
              file={photos[key] || null}
              onSelect={onSelect}
              onRemove={onRemove}
              accentColor={accentColor}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Configurazione professionisti (stessa del WeeklyCheckForm) ──────────────

const PROF_CONFIGS = {
  Nutrizionista: {
    ratingField: 'nutritionist_rating',
    feedbackField: 'nutritionist_feedback',
    icon: 'ri-user-heart-line',
    avatarBg: '#22c55e',
    cardBg: '#f0fdf4',
    cardBorder: '#bbf7d0',
    feedbackPlaceholder: 'Feedback per il nutrizionista (opzionale)',
  },
  'Psicologo/a': {
    ratingField: 'psychologist_rating',
    feedbackField: 'psychologist_feedback',
    icon: 'ri-mental-health-line',
    avatarBg: '#3b82f6',
    cardBg: '#eff6ff',
    cardBorder: '#bfdbfe',
    feedbackPlaceholder: 'Feedback per lo psicologo (opzionale)',
  },
  Coach: {
    ratingField: 'coach_rating',
    feedbackField: 'coach_feedback',
    icon: 'ri-run-line',
    avatarBg: '#8b5cf6',
    cardBg: '#faf5ff',
    cardBorder: '#e9d5ff',
    feedbackPlaceholder: 'Feedback per il coach (opzionale)',
  },
};

const NPS_LABELS = ['Per niente', 'No', 'Poco', 'Forse no', 'Neutro', 'Forse sì', 'Sì', 'Volentieri', 'Certamente', 'Assolutamente sì'];

function ProfCard({ prof, formData, onChange }) {
  const cfg = PROF_CONFIGS[prof.ruolo];
  if (!cfg) return null;
  const ratingVal = formData[cfg.ratingField] ?? null;
  const feedbackVal = formData[cfg.feedbackField] ?? '';
  const [showFeedback, setShowFeedback] = useState(false);

  return (
    <div className="check-question-block" style={{ background: cfg.cardBg, border: `1px solid ${cfg.cardBorder}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
        <div style={{ width: 40, height: 40, borderRadius: '50%', background: cfg.avatarBg, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 18, flexShrink: 0 }}>
          <i className={cfg.icon} />
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: '0.92rem', color: '#1e293b' }}>{prof.nome}</div>
          <div style={{ fontSize: '0.78rem', color: '#64748b' }}>{prof.ruolo}</div>
        </div>
      </div>

      {/* Rating 1-10 */}
      <div className="check-rating-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)', marginBottom: 4 }}>
        {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
          <button
            key={n}
            type="button"
            className={`check-rating-btn${ratingVal === n ? ' selected' : ''}`}
            onClick={() => onChange(cfg.ratingField, n)}
          >
            {n}
          </button>
        ))}
      </div>
      {ratingVal != null && (
        <p style={{ fontSize: '0.78rem', color: cfg.avatarBg, fontWeight: 600, textAlign: 'center', margin: '4px 0 10px' }}>
          {NPS_LABELS[ratingVal - 1] || ''}
        </p>
      )}

      {/* Feedback toggle */}
      <button
        type="button"
        onClick={() => setShowFeedback((v) => !v)}
        style={{ background: 'none', border: 'none', color: '#64748b', fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, padding: 0 }}
      >
        <i className={`ri-arrow-${showFeedback ? 'up' : 'down'}-s-line`} />
        {showFeedback ? 'Nascondi feedback' : 'Aggiungi un commento (opzionale)'}
      </button>
      {showFeedback && (
        <textarea
          className="check-textarea"
          rows={2}
          style={{ marginTop: 8 }}
          placeholder={cfg.feedbackPlaceholder}
          value={feedbackVal}
          onChange={(e) => onChange(cfg.feedbackField, e.target.value)}
        />
      )}
    </div>
  );
}

function DcaValutazioniSection({ professionisti, formData, onChange, accentColor }) {
  const npsVal = formData['progress_rating'] ?? null;
  const referralVal = formData['referral'] ?? '';

  // Deduplica: un solo slot per tipo professionista
  const seen = new Set();
  const uniqueProfs = professionisti.filter((p) => {
    if (seen.has(p.ruolo)) return false;
    seen.add(p.ruolo);
    return true;
  });

  return (
    <>
      {/* Valutazioni professionisti */}
      <div className="check-section-collapsible">
        <div className="check-section-toggle" style={{ borderLeftColor: accentColor, cursor: 'default' }}>
          <div className="check-section-icon" style={{ background: `${accentColor}18`, color: accentColor, flexShrink: 0 }}>
            <i className="ri-star-line" />
          </div>
          <span className="check-section-toggle-title">Valutazioni</span>
          <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 500 }}>facoltativo</span>
        </div>
        <div className="check-section-body">
          <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: 14, lineHeight: 1.5 }}>
            Valuta da 1 a 10 il supporto ricevuto dai tuoi professionisti questo mese.
          </p>

          {uniqueProfs.length > 0 ? (
            uniqueProfs.map((prof) => (
              <ProfCard key={prof.ruolo} prof={prof} formData={formData} onChange={onChange} />
            ))
          ) : (
            <p style={{ fontSize: '0.82rem', color: '#94a3b8', textAlign: 'center' }}>
              Nessun professionista assegnato al momento.
            </p>
          )}

          {/* NPS CorpoSostenibile */}
          <div className="check-question-block" style={{ background: '#fefce8', border: '1px solid #fef08a', marginTop: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <div style={{ width: 40, height: 40, borderRadius: '50%', background: '#eab308', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 18, flexShrink: 0 }}>
                <i className="ri-line-chart-line" />
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.88rem', color: '#1e293b' }}>
                  Quanto consiglieresti CorpoSostenibile a una persona a cui vuoi bene?
                </div>
                <div style={{ fontSize: '0.78rem', color: '#64748b' }}>1 = Non mi piace / 10 = Super soddisfatto</div>
              </div>
            </div>
            <div className="check-rating-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
              {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  className={`check-rating-btn${npsVal === n ? ' selected' : ''}`}
                  style={npsVal === n ? { background: '#eab308', borderColor: '#eab308' } : {}}
                  onClick={() => onChange('progress_rating', n)}
                >
                  {n}
                </button>
              ))}
            </div>
            {npsVal != null && (
              <p style={{ fontSize: '0.78rem', color: '#a16207', fontWeight: 600, textAlign: 'center', marginTop: 6 }}>
                {NPS_LABELS[npsVal - 1] || ''}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Referral */}
      <div className="check-section-collapsible">
        <div className="check-section-toggle" style={{ borderLeftColor: accentColor, cursor: 'default' }}>
          <div className="check-section-icon" style={{ background: `${accentColor}18`, color: accentColor, flexShrink: 0 }}>
            <i className="ri-user-add-line" />
          </div>
          <span className="check-section-toggle-title">Conosci qualcuno che potrebbe beneficiarne?</span>
          <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 500 }}>facoltativo</span>
        </div>
        <div className="check-section-body">
          <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: 12, lineHeight: 1.5 }}>
            Chi è la persona a cui vuoi bene e che CorpoSostenibile può aiutare?
          </p>
          <textarea
            className="check-textarea"
            rows={3}
            value={referralVal}
            onChange={(e) => onChange('referral', e.target.value)}
            placeholder={'Nome: Mario Rossi\nTelefono: 333 1234567'}
          />
          <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: 6 }}>
            Indica nome, cognome e numero di telefono.
          </p>
        </div>
      </div>
    </>
  );
}

// ─── Form principale ──────────────────────────────────────────────────────────

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
  const [photos, setPhotos] = useState({});
  const draftRestoredRef = useRef(false);

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

  // Ripristina bozza dopo il caricamento del check
  useEffect(() => {
    if (!checkInfo || draftRestoredRef.current) return;
    draftRestoredRef.current = true;
    const saved = localStorage.getItem(`monthly_check_draft_${token}`);
    if (saved) {
      try {
        setFormData(JSON.parse(saved));
      } catch (_) {}
    }
  }, [checkInfo, token]);

  // Salva bozza ad ogni modifica (solo dopo il ripristino iniziale)
  useEffect(() => {
    if (!draftRestoredRef.current) return;
    localStorage.setItem(`monthly_check_draft_${token}`, JSON.stringify(formData));
  }, [formData, token]);

  const handleChange = (key, value) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const toggleSection = (section) => {
    setCollapsedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const handlePhotoSelect = (fieldKey, file) => {
    setPhotos((prev) => ({ ...prev, [fieldKey]: file }));
  };

  const handlePhotoRemove = (fieldKey) => {
    setPhotos((prev) => { const n = { ...prev }; delete n[fieldKey]; return n; });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const requiredKeys = questions
      .filter((q) => (q.type === 'scale' || q.type === 'select') && q.required !== false)
      .map((q) => q.key);
    const missing = requiredKeys.filter((k) => formData[k] == null);
    if (missing.length > 0) {
      setError(`Rispondi a tutte le domande obbligatorie prima di inviare (${missing.length} mancanti).`);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    setSubmitting(true);
    try {
      const result = await publicCheckService.submitMonthlyCheck(token, formData, photos);
      if (result.success) {
        localStorage.removeItem(`monthly_check_draft_${token}`);
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

  const tipologia = checkInfo?.check?.tipologia || 'regolare';
  const config = TIPOLOGIA_CONFIG[tipologia] || TIPOLOGIA_CONFIG.regolare;
  const isRegolare = tipologia === 'regolare';

  const requiredQuestions = questions.filter(
    (q) => (q.type === 'scale' || q.type === 'select') && q.required !== false
  );
  const answered = requiredQuestions.filter((q) => formData[q.key] != null).length;
  const progress = requiredQuestions.length > 0 ? Math.round((answered / requiredQuestions.length) * 100) : 0;

  // Raggruppa domande per sezione, escludendo "Misure e foto" (gestita separatamente)
  const sectionMap = {};
  const sectionOrder = [];
  questions.forEach((q) => {
    if (q.section === 'Misure e foto') return; // gestita sotto con il peso + foto
    const sec = q.section || 'Altro';
    if (!sectionMap[sec]) {
      sectionMap[sec] = [];
      sectionOrder.push(sec);
    }
    sectionMap[sec].push(q);
  });

  // Domanda peso (se presente)
  const weightQuestion = questions.find((q) => q.key === 'weight');

  const getSectionCompletion = useCallback((sectionTitle) => {
    const sqs = (sectionMap[sectionTitle] || []).filter(
      (q) => (q.type === 'scale' || q.type === 'select') && q.required !== false
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
            {answered}/{requiredQuestions.length} risposte
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
          {/* Sezioni domande */}
          {sectionOrder.map((sectionTitle) => {
            const sqs = sectionMap[sectionTitle];
            const isCollapsed = collapsedSections[sectionTitle];
            const { answered: secAns, total: secTotal } = getSectionCompletion(sectionTitle);
            const secComplete = secTotal > 0 && secAns === secTotal;
            const secCfg = SECTION_CONFIG[sectionTitle] || { icon: 'ri-list-check', color: config.color };

            return (
              <div key={sectionTitle} className="check-section-collapsible">
                <button
                  type="button"
                  className={`check-section-toggle${secComplete ? ' complete' : ''}`}
                  onClick={() => toggleSection(sectionTitle)}
                  style={{ borderLeftColor: secCfg.color }}
                >
                  <div
                    className="check-section-icon"
                    style={{ background: `${secCfg.color}18`, color: secCfg.color, flexShrink: 0 }}
                  >
                    <i className={secCfg.icon} />
                  </div>
                  <span className="check-section-toggle-title">{sectionTitle}</span>
                  <span className="check-section-toggle-meta">
                    {secTotal > 0 ? (
                      <span className={`check-section-badge${secComplete ? ' done' : ''}`}>
                        {secComplete
                          ? <><i className="ri-check-line" style={{ marginRight: 2 }} />Fatto</>
                          : `${secAns}/${secTotal}`}
                      </span>
                    ) : (
                      <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 500 }}>facoltativo</span>
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
                        color={secCfg.color}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {/* Sezioni DCA: valutazioni professionisti + NPS + referral */}
          {tipologia === 'dca' && (
            <DcaValutazioniSection
              professionisti={checkInfo?.professionisti || []}
              formData={formData}
              onChange={handleChange}
              accentColor={config.color}
            />
          )}

          {/* Sezione misure e foto (solo regolare, sempre visibile alla fine) */}
          {isRegolare && (
            <div className="check-section-collapsible">
              <div
                className="check-section-toggle"
                style={{ borderLeftColor: config.color, cursor: 'default' }}
              >
                <div
                  className="check-section-icon"
                  style={{ background: `${config.color}18`, color: config.color, flexShrink: 0 }}
                >
                  <i className="ri-camera-line" />
                </div>
                <span className="check-section-toggle-title">Misure e foto</span>
                <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 500 }}>facoltativo</span>
              </div>
              <div className="check-section-body">
                {/* Peso */}
                {weightQuestion && (
                  <NumberQuestion
                    question={weightQuestion}
                    value={formData['weight'] ?? null}
                    onChange={handleChange}
                  />
                )}
                {/* Foto */}
                <div style={{ marginTop: weightQuestion ? 20 : 0 }}>
                  <p style={{
                    fontSize: '0.85rem', fontWeight: 600, color: '#374151',
                    marginBottom: 4,
                  }}>
                    Foto di progressione
                    <span className="check-optional"> (facoltativo)</span>
                  </p>
                  <p style={{ fontSize: '0.78rem', color: '#64748b', marginBottom: 14, lineHeight: 1.5 }}>
                    Scatta o carica le tue foto (frontale, laterale, posteriore).
                    Sono riservate al tuo team.
                  </p>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                    {PHOTO_FIELDS.map(({ key, label, icon }) => (
                      <PhotoUploadSlot
                        key={key}
                        fieldKey={key}
                        label={label}
                        icon={icon}
                        file={photos[key] || null}
                        onSelect={handlePhotoSelect}
                        onRemove={handlePhotoRemove}
                        accentColor={config.color}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

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
            {answered < requiredQuestions.length && (
              <p className="check-submit-hint">
                Assicurati di aver risposto a tutte le scale numeriche obbligatorie prima di inviare.
              </p>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

export default MonthlyCheckForm;

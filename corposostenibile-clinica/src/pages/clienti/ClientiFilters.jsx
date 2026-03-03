import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import DatePicker from '../../components/DatePicker';
import {
    RiFilter3Line,
    RiRefreshLine,
    RiCalendarLine,
    RiUserStarLine,
    RiMegaphoneLine,
    RiErrorWarningLine,
    RiCheckDoubleLine,
    RiFileList3Line,
    RiCloseLine,
    RiCheckLine,
    RiHeartPulseLine,
    RiBrainLine,
} from 'react-icons/ri';
import {
    STATO_LABELS,
    TIPOLOGIA_LABELS,
    GIORNI_LABELS,
    PATOLOGIE_NUTRI,
    PATOLOGIE_PSICO,
    LUOGO_LABELS,
} from '../../services/clientiService';

// Full day entries only (filter out legacy short codes)
const GIORNI_FULL = Object.entries(GIORNI_LABELS).filter(([k]) =>
    !['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom'].includes(k)
);

const STATO_SERVIZIO_OPTIONS = [
    { value: 'attivo', label: 'Attivo' },
    { value: 'ghost', label: 'Ghost' },
    { value: 'pausa', label: 'Pausa' },
    { value: 'stop', label: 'Stop' },
];

const ClientiFilters = ({
    filters,
    onFilterChange,
    onReset,
    professionisti = [],
    visibleProfessionalFilters = {
        nutrizione: true,
        coach: true,
        psicologia: true,
    },
    open,
    onClose,
    mode = 'general',
}) => {
    // Local draft so changes only apply on "Applica"
    const [draft, setDraft] = useState({ ...filters });
    const isGeneral = mode === 'general';

    // Sync draft when modal opens
    useEffect(() => {
        if (open) setDraft({ ...filters });
    }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

    // In specialty modes the parent already passes a pre-filtered list, so
    // use professionisti directly for the matching dropdown.  In general mode
    // we still need to split the full list by specialty.
    const nutrizionisti = mode === 'nutrizione'
        ? professionisti
        : professionisti.filter(p => p.specialty === 'nutrizione' || p.specialty === 'nutrizionista');
    const coaches = mode === 'coach'
        ? professionisti
        : professionisti.filter(p => p.specialty === 'coach');
    const psicologi = mode === 'psicologia'
        ? professionisti
        : professionisti.filter(p => p.specialty === 'psicologia' || p.specialty === 'psicologo');

    const handleDraftChange = (key, value) => {
        setDraft(prev => ({ ...prev, [key]: value }));
    };

    const handleApply = () => {
        // Push every changed key
        Object.keys(draft).forEach(key => {
            if (key === 'search') return; // search is handled inline
            if (draft[key] !== filters[key]) {
                onFilterChange(key, draft[key]);
            }
        });
        onClose();
    };

    const handleReset = () => {
        onReset();
        onClose();
    };

    if (!open) return null;

    return createPortal(
        <div className="cl-modal-overlay" onClick={onClose}>
            <div className="cl-modal" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="cl-modal-header">
                    <h5 className="cl-modal-title">
                        <RiFilter3Line /> Filtra Pazienti
                    </h5>
                    <button className="cl-modal-close" onClick={onClose}>
                        <RiCloseLine />
                    </button>
                </div>

                {/* Body */}
                <div className="cl-modal-body">

                    {/* ── Base Filters (always visible) ── */}
                    <h6 className="cl-advanced-heading">
                        <RiFilter3Line /> Filtri Base
                    </h6>
                    <div className="row g-3 mb-4">
                        <div className="col-md-4">
                            <label className="form-label mb-1">Stato</label>
                            <select
                                className="form-select"
                                value={draft.stato || ''}
                                onChange={(e) => handleDraftChange('stato', e.target.value)}
                            >
                                <option value="">Tutti</option>
                                {Object.entries(STATO_LABELS).map(([value, label]) => (
                                    <option key={value} value={value}>{label}</option>
                                ))}
                            </select>
                        </div>
                        <div className="col-md-4">
                            <label className="form-label mb-1">Tipologia</label>
                            <select
                                className="form-select"
                                value={draft.tipologia || ''}
                                onChange={(e) => handleDraftChange('tipologia', e.target.value)}
                            >
                                <option value="">Tutte</option>
                                {Object.entries(TIPOLOGIA_LABELS).map(([value, label]) => (
                                    <option key={value} value={value}>{label}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* ── Professional Filters ── */}
                    {(visibleProfessionalFilters.nutrizione || visibleProfessionalFilters.coach || visibleProfessionalFilters.psicologia) && (
                        <>
                            <h6 className="cl-advanced-heading">
                                <RiUserStarLine /> Professionista
                            </h6>
                            <div className="row g-3 mb-4">
                                {visibleProfessionalFilters.nutrizione && (
                                    <div className="col-md-4">
                                        <label className="form-label mb-1">Nutrizionista</label>
                                        <select
                                            className="form-select"
                                            value={draft.nutrizionista || ''}
                                            onChange={(e) => handleDraftChange('nutrizionista', e.target.value)}
                                        >
                                            <option value="">Tutti</option>
                                            {nutrizionisti.map(p => (
                                                <option key={p.id} value={p.id}>{p.full_name}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                                {visibleProfessionalFilters.coach && (
                                    <div className="col-md-4">
                                        <label className="form-label mb-1">Coach</label>
                                        <select
                                            className="form-select"
                                            value={draft.coach || ''}
                                            onChange={(e) => handleDraftChange('coach', e.target.value)}
                                        >
                                            <option value="">Tutti</option>
                                            {coaches.map(p => (
                                                <option key={p.id} value={p.id}>{p.full_name}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                                {visibleProfessionalFilters.psicologia && (
                                    <div className="col-md-4">
                                        <label className="form-label mb-1">Psicologo</label>
                                        <select
                                            className="form-select"
                                            value={draft.psicologa || ''}
                                            onChange={(e) => handleDraftChange('psicologa', e.target.value)}
                                        >
                                            <option value="">Tutti</option>
                                            {psicologi.map(p => (
                                                <option key={p.id} value={p.id}>{p.full_name}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                            </div>
                        </>
                    )}

                    {/* ═══════════════════════════════════════ */}
                    {/* ── NUTRIZIONE MODE SECTIONS ────────── */}
                    {/* ═══════════════════════════════════════ */}
                    {mode === 'nutrizione' && (
                        <>
                            {/* Stato Servizio */}
                            <h6 className="cl-advanced-heading">
                                <RiCheckDoubleLine /> Stato Servizio
                            </h6>
                            <div className="row g-3 mb-4">
                                <div className="col-md-4">
                                    <label className="form-label mb-1">Stato Nutrizione</label>
                                    <select className="form-select" value={draft.statoNutrizione || ''} onChange={(e) => handleDraftChange('statoNutrizione', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {STATO_SERVIZIO_OPTIONS.map(o => (
                                            <option key={o.value} value={o.value}>{o.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label mb-1">Stato Chat Nutrizione</label>
                                    <select className="form-select" value={draft.statoChatNutrizione || ''} onChange={(e) => handleDraftChange('statoChatNutrizione', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {STATO_SERVIZIO_OPTIONS.map(o => (
                                            <option key={o.value} value={o.value}>{o.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {/* Dettagli */}
                            <h6 className="cl-advanced-heading">
                                <RiUserStarLine /> Dettagli
                            </h6>
                            <div className="row g-3 mb-4">
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Reach Out</label>
                                    <select className="form-select" value={draft.reachOut || ''} onChange={(e) => handleDraftChange('reachOut', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {GIORNI_FULL.map(([value, label]) => (
                                            <option key={value} value={value}>{label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Check Day</label>
                                    <select className="form-select" value={draft.checkDay || ''} onChange={(e) => handleDraftChange('checkDay', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {GIORNI_FULL.map(([value, label]) => (
                                            <option key={value} value={value}>{label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Call Iniziale Nutrizionista</label>
                                    <select className="form-select" value={draft.callInizialeNutrizionista || ''} onChange={(e) => handleDraftChange('callInizialeNutrizionista', e.target.value)}>
                                        <option value="">Tutti</option>
                                        <option value="1">Si</option>
                                        <option value="0">No</option>
                                    </select>
                                </div>
                            </div>

                            {/* Patologie Nutrizionali */}
                            <h6 className="cl-advanced-heading">
                                <RiHeartPulseLine /> Patologie Nutrizionali
                            </h6>
                            <div className="row g-3 mb-4">
                                {PATOLOGIE_NUTRI.map(p => (
                                    <div key={p.key} className="col-md-4">
                                        <div className="form-check form-switch">
                                            <input
                                                className="form-check-input"
                                                type="checkbox"
                                                id={`modal-${p.key}`}
                                                checked={draft[p.key] === '1'}
                                                onChange={(e) => handleDraftChange(p.key, e.target.checked ? '1' : '0')}
                                            />
                                            <label className="form-check-label" htmlFor={`modal-${p.key}`}>{p.label}</label>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Piani Mancanti */}
                            <h6 className="cl-advanced-heading info">
                                <RiFileList3Line /> Piani Mancanti
                            </h6>
                            <div className="row g-3">
                                <div className="col-md-4">
                                    <div className="form-check form-switch">
                                        <input
                                            className="form-check-input"
                                            type="checkbox"
                                            id="modal-missing_piano_dieta"
                                            checked={draft.missing_piano_dieta === '1'}
                                            onChange={(e) => handleDraftChange('missing_piano_dieta', e.target.checked ? '1' : '0')}
                                        />
                                        <label className="form-check-label" htmlFor="modal-missing_piano_dieta">No Piano Dieta</label>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}

                    {/* ═══════════════════════════════════════ */}
                    {/* ── COACH MODE SECTIONS ─────────────── */}
                    {/* ═══════════════════════════════════════ */}
                    {mode === 'coach' && (
                        <>
                            {/* Stato Servizio */}
                            <h6 className="cl-advanced-heading">
                                <RiCheckDoubleLine /> Stato Servizio
                            </h6>
                            <div className="row g-3 mb-4">
                                <div className="col-md-4">
                                    <label className="form-label mb-1">Stato Coach</label>
                                    <select className="form-select" value={draft.statoCoach || ''} onChange={(e) => handleDraftChange('statoCoach', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {STATO_SERVIZIO_OPTIONS.map(o => (
                                            <option key={o.value} value={o.value}>{o.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label mb-1">Stato Chat Coaching</label>
                                    <select className="form-select" value={draft.statoChatCoaching || ''} onChange={(e) => handleDraftChange('statoChatCoaching', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {STATO_SERVIZIO_OPTIONS.map(o => (
                                            <option key={o.value} value={o.value}>{o.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {/* Dettagli */}
                            <h6 className="cl-advanced-heading">
                                <RiUserStarLine /> Dettagli
                            </h6>
                            <div className="row g-3 mb-4">
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Reach Out</label>
                                    <select className="form-select" value={draft.reachOut || ''} onChange={(e) => handleDraftChange('reachOut', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {GIORNI_FULL.map(([value, label]) => (
                                            <option key={value} value={value}>{label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Check Day</label>
                                    <select className="form-select" value={draft.checkDay || ''} onChange={(e) => handleDraftChange('checkDay', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {GIORNI_FULL.map(([value, label]) => (
                                            <option key={value} value={value}>{label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Luogo Allenamento</label>
                                    <select className="form-select" value={draft.luogoDiAllenamento || ''} onChange={(e) => handleDraftChange('luogoDiAllenamento', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {Object.entries(LUOGO_LABELS).map(([value, label]) => (
                                            <option key={value} value={value}>{label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Call Iniziale Coach</label>
                                    <select className="form-select" value={draft.callInizialeCoach || ''} onChange={(e) => handleDraftChange('callInizialeCoach', e.target.value)}>
                                        <option value="">Tutti</option>
                                        <option value="1">Si</option>
                                        <option value="0">No</option>
                                    </select>
                                </div>
                            </div>

                            {/* Date Allenamento */}
                            <h6 className="cl-advanced-heading">
                                <RiCalendarLine /> Date Allenamento
                            </h6>
                            <div className="row g-3 mb-4">
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Allenamento Dal (Da)</label>
                                    <DatePicker className="form-control" value={draft.allenamento_dal_from || ''} onChange={(e) => handleDraftChange('allenamento_dal_from', e.target.value)} />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Allenamento Dal (A)</label>
                                    <DatePicker className="form-control" value={draft.allenamento_dal_to || ''} onChange={(e) => handleDraftChange('allenamento_dal_to', e.target.value)} />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Nuovo Allenamento (Da)</label>
                                    <DatePicker className="form-control" value={draft.nuovo_allenamento_il_from || ''} onChange={(e) => handleDraftChange('nuovo_allenamento_il_from', e.target.value)} />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Nuovo Allenamento (A)</label>
                                    <DatePicker className="form-control" value={draft.nuovo_allenamento_il_to || ''} onChange={(e) => handleDraftChange('nuovo_allenamento_il_to', e.target.value)} />
                                </div>
                            </div>

                            {/* Piani Mancanti */}
                            <h6 className="cl-advanced-heading info">
                                <RiFileList3Line /> Piani Mancanti
                            </h6>
                            <div className="row g-3">
                                <div className="col-md-4">
                                    <div className="form-check form-switch">
                                        <input
                                            className="form-check-input"
                                            type="checkbox"
                                            id="modal-missing_piano_allenamento"
                                            checked={draft.missing_piano_allenamento === '1'}
                                            onChange={(e) => handleDraftChange('missing_piano_allenamento', e.target.checked ? '1' : '0')}
                                        />
                                        <label className="form-check-label" htmlFor="modal-missing_piano_allenamento">No Piano Allenamento</label>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}

                    {/* ═══════════════════════════════════════ */}
                    {/* ── PSICOLOGIA MODE SECTIONS ────────── */}
                    {/* ═══════════════════════════════════════ */}
                    {mode === 'psicologia' && (
                        <>
                            {/* Stato Servizio */}
                            <h6 className="cl-advanced-heading">
                                <RiCheckDoubleLine /> Stato Servizio
                            </h6>
                            <div className="row g-3 mb-4">
                                <div className="col-md-4">
                                    <label className="form-label mb-1">Stato Psicologia</label>
                                    <select className="form-select" value={draft.statoPsicologia || ''} onChange={(e) => handleDraftChange('statoPsicologia', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {STATO_SERVIZIO_OPTIONS.map(o => (
                                            <option key={o.value} value={o.value}>{o.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label mb-1">Stato Chat Psicologia</label>
                                    <select className="form-select" value={draft.statoChatPsicologia || ''} onChange={(e) => handleDraftChange('statoChatPsicologia', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {STATO_SERVIZIO_OPTIONS.map(o => (
                                            <option key={o.value} value={o.value}>{o.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {/* Dettagli */}
                            <h6 className="cl-advanced-heading">
                                <RiUserStarLine /> Dettagli
                            </h6>
                            <div className="row g-3 mb-4">
                                <div className="col-md-4">
                                    <label className="form-label mb-1">Reach Out</label>
                                    <select className="form-select" value={draft.reachOut || ''} onChange={(e) => handleDraftChange('reachOut', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {GIORNI_FULL.map(([value, label]) => (
                                            <option key={value} value={value}>{label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label mb-1">Call Iniziale Psicologa</label>
                                    <select className="form-select" value={draft.callInizialePsicologa || ''} onChange={(e) => handleDraftChange('callInizialePsicologa', e.target.value)}>
                                        <option value="">Tutti</option>
                                        <option value="1">Si</option>
                                        <option value="0">No</option>
                                    </select>
                                </div>
                            </div>

                            {/* Patologie Psicologiche */}
                            <h6 className="cl-advanced-heading">
                                <RiBrainLine /> Patologie Psicologiche
                            </h6>
                            <div className="row g-3">
                                {PATOLOGIE_PSICO.map(p => (
                                    <div key={p.key} className="col-md-4">
                                        <div className="form-check form-switch">
                                            <input
                                                className="form-check-input"
                                                type="checkbox"
                                                id={`modal-${p.key}`}
                                                checked={draft[p.key] === '1'}
                                                onChange={(e) => handleDraftChange(p.key, e.target.checked ? '1' : '0')}
                                            />
                                            <label className="form-check-label" htmlFor={`modal-${p.key}`}>{p.label}</label>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}

                    {/* ═══════════════════════════════════════ */}
                    {/* ── GENERAL MODE SECTIONS (existing) ── */}
                    {/* ═══════════════════════════════════════ */}
                    {isGeneral && (
                        <>
                            {/* ── Dettagli Stato ── */}
                            <h6 className="cl-advanced-heading">
                                <RiUserStarLine /> Dettagli Stato
                            </h6>
                            <div className="row g-3 mb-4">
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Giorno Check</label>
                                    <select className="form-select" value={draft.check_day || ''} onChange={(e) => handleDraftChange('check_day', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {['lunedi','martedi','mercoledi','giovedi','venerdi','sabato','domenica'].map(d => (
                                            <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Reach Out</label>
                                    <select className="form-select" value={draft.reach_out || ''} onChange={(e) => handleDraftChange('reach_out', e.target.value)}>
                                        <option value="">Tutti</option>
                                        {['lunedi','martedi','mercoledi','giovedi','venerdi','sabato','domenica'].map(d => (
                                            <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Trasformazione Fisica</label>
                                    <select className="form-select" value={draft.trasformazione_fisica || ''} onChange={(e) => handleDraftChange('trasformazione_fisica', e.target.value)}>
                                        <option value="">Tutti</option>
                                        <option value="1">Si</option>
                                        <option value="0">No</option>
                                    </select>
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Trasf. Condivisa</label>
                                    <select className="form-select" value={draft.trasformazione_fisica_condivisa || ''} onChange={(e) => handleDraftChange('trasformazione_fisica_condivisa', e.target.value)}>
                                        <option value="">Tutti</option>
                                        <option value="1">Si</option>
                                        <option value="0">No</option>
                                    </select>
                                </div>
                            </div>

                            {/* ── Date Allenamento ── */}
                            <h6 className="cl-advanced-heading">
                                <RiCalendarLine /> Date Allenamento
                            </h6>
                            <div className="row g-3 mb-4">
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Allenamento Dal (Da)</label>
                                    <DatePicker className="form-control" value={draft.allenamento_dal_from || ''} onChange={(e) => handleDraftChange('allenamento_dal_from', e.target.value)} />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Allenamento Dal (A)</label>
                                    <DatePicker className="form-control" value={draft.allenamento_dal_to || ''} onChange={(e) => handleDraftChange('allenamento_dal_to', e.target.value)} />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Nuovo Allenamento (Da)</label>
                                    <DatePicker className="form-control" value={draft.nuovo_allenamento_il_from || ''} onChange={(e) => handleDraftChange('nuovo_allenamento_il_from', e.target.value)} />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label mb-1">Nuovo Allenamento (A)</label>
                                    <DatePicker className="form-control" value={draft.nuovo_allenamento_il_to || ''} onChange={(e) => handleDraftChange('nuovo_allenamento_il_to', e.target.value)} />
                                </div>
                            </div>

                            {/* ── Marketing ── */}
                            <h6 className="cl-advanced-heading">
                                <RiMegaphoneLine /> Marketing
                            </h6>
                            <div className="row g-3 mb-4">
                                {[
                                    { key: 'marketing_usabile', label: 'Usabile Marketing' },
                                    { key: 'marketing_stories', label: 'Stories Editate' },
                                    { key: 'marketing_carosello', label: 'Carosello Editato' },
                                    { key: 'marketing_videofeedback', label: 'Videofeedback Editato' },
                                ].map(item => (
                                    <div key={item.key} className="col-md-3">
                                        <label className="form-label mb-1">{item.label}</label>
                                        <select className="form-select" value={draft[item.key] || ''} onChange={(e) => handleDraftChange(item.key, e.target.value)}>
                                            <option value="">Tutti</option>
                                            <option value="1">Si</option>
                                            <option value="0">No</option>
                                        </select>
                                    </div>
                                ))}
                            </div>

                            {/* ── Campi NON Compilati ── */}
                            <h6 className="cl-advanced-heading danger">
                                <RiErrorWarningLine /> Campi NON Compilati
                            </h6>
                            <div className="row g-3 mb-4">
                                {[
                                    { key: 'missing_check_day', label: 'Missing Check Day' },
                                    { key: 'missing_check_saltati', label: 'Missing Check Saltati' },
                                    { key: 'missing_reach_out', label: 'Missing Reach Out' }
                                ].map(item => (
                                    <div key={item.key} className="col-md-4">
                                        <div className="form-check form-switch">
                                            <input
                                                className="form-check-input"
                                                type="checkbox"
                                                id={`modal-${item.key}`}
                                                checked={draft[item.key] === '1'}
                                                onChange={(e) => handleDraftChange(item.key, e.target.checked ? '1' : '0')}
                                            />
                                            <label className="form-check-label" htmlFor={`modal-${item.key}`}>{item.label}</label>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* ── Stati Servizio Mancanti ── */}
                            <h6 className="cl-advanced-heading warning">
                                <RiCheckDoubleLine /> Stati Servizio Mancanti
                            </h6>
                            <div className="row g-3 mb-4">
                                {[
                                    { key: 'missing_stato_nutrizione', label: 'Stato Nutrizione' },
                                    { key: 'missing_stato_chat_nutrizione', label: 'Chat Nutrizione' },
                                    { key: 'missing_stato_coach', label: 'Stato Coach' },
                                    { key: 'missing_stato_chat_coaching', label: 'Chat Coach' },
                                    { key: 'missing_stato_psicologia', label: 'Stato Psicologia' },
                                    { key: 'missing_stato_chat_psicologia', label: 'Chat Psicologia' }
                                ].map(item => (
                                    <div key={item.key} className="col-md-4">
                                        <div className="form-check form-switch">
                                            <input
                                                className="form-check-input"
                                                type="checkbox"
                                                id={`modal-${item.key}`}
                                                checked={draft[item.key] === '1'}
                                                onChange={(e) => handleDraftChange(item.key, e.target.checked ? '1' : '0')}
                                            />
                                            <label className="form-check-label" htmlFor={`modal-${item.key}`}>{item.label}</label>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* ── Piani Attivi Mancanti ── */}
                            <h6 className="cl-advanced-heading info">
                                <RiFileList3Line /> Piani Attivi Mancanti
                            </h6>
                            <div className="row g-3">
                                {[
                                    { key: 'missing_piano_dieta', label: 'No Diet Plan' },
                                    { key: 'missing_piano_allenamento', label: 'No Training Plan' },
                                ].map(item => (
                                    <div key={item.key} className="col-md-4">
                                        <div className="form-check form-switch">
                                            <input
                                                className="form-check-input"
                                                type="checkbox"
                                                id={`modal-${item.key}`}
                                                checked={draft[item.key] === '1'}
                                                onChange={(e) => handleDraftChange(item.key, e.target.checked ? '1' : '0')}
                                            />
                                            <label className="form-check-label" htmlFor={`modal-${item.key}`}>{item.label}</label>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="cl-modal-footer">
                    <button className="cl-modal-btn-reset" onClick={handleReset}>
                        <RiRefreshLine /> Reset Tutti
                    </button>
                    <button className="cl-modal-btn-apply" onClick={handleApply}>
                        <RiCheckLine /> Applica Filtri
                    </button>
                </div>
            </div>
        </div>,
        document.body
    );
};

export default ClientiFilters;

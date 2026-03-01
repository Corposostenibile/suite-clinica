import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
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
    RiCheckLine
} from 'react-icons/ri';
import { STATO_LABELS, TIPOLOGIA_LABELS } from '../../services/clientiService';

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
}) => {
    // Local draft so changes only apply on "Applica"
    const [draft, setDraft] = useState({ ...filters });

    // Sync draft when modal opens
    useEffect(() => {
        if (open) setDraft({ ...filters });
    }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

    const nutrizionisti = professionisti.filter(p =>
        p.specialty === 'nutrizione' || p.specialty === 'nutrizionista'
    );
    const coaches = professionisti.filter(p => p.specialty === 'coach');
    const psicologi = professionisti.filter(p =>
        p.specialty === 'psicologia' || p.specialty === 'psicologo'
    );

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

                    {/* ── Base Filters ── */}
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
                                <option value="1">Sì</option>
                                <option value="0">No</option>
                            </select>
                        </div>
                        <div className="col-md-3">
                            <label className="form-label mb-1">Trasf. Condivisa</label>
                            <select className="form-select" value={draft.trasformazione_fisica_condivisa || ''} onChange={(e) => handleDraftChange('trasformazione_fisica_condivisa', e.target.value)}>
                                <option value="">Tutti</option>
                                <option value="1">Sì</option>
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
                            <input type="date" className="form-control" value={draft.allenamento_dal_from || ''} onChange={(e) => handleDraftChange('allenamento_dal_from', e.target.value)} />
                        </div>
                        <div className="col-md-3">
                            <label className="form-label mb-1">Allenamento Dal (A)</label>
                            <input type="date" className="form-control" value={draft.allenamento_dal_to || ''} onChange={(e) => handleDraftChange('allenamento_dal_to', e.target.value)} />
                        </div>
                        <div className="col-md-3">
                            <label className="form-label mb-1">Nuovo Allenamento (Da)</label>
                            <input type="date" className="form-control" value={draft.nuovo_allenamento_il_from || ''} onChange={(e) => handleDraftChange('nuovo_allenamento_il_from', e.target.value)} />
                        </div>
                        <div className="col-md-3">
                            <label className="form-label mb-1">Nuovo Allenamento (A)</label>
                            <input type="date" className="form-control" value={draft.nuovo_allenamento_il_to || ''} onChange={(e) => handleDraftChange('nuovo_allenamento_il_to', e.target.value)} />
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
                                    <option value="1">Sì</option>
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

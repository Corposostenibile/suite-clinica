import { useState } from 'react';
import {
    RiSearchLine,
    RiFilter3Line,
    RiArrowDownSLine,
    RiArrowUpSLine,
    RiRefreshLine,
    RiCalendarLine,
    RiUserStarLine,
    RiMegaphoneLine,
    RiErrorWarningLine,
    RiCheckDoubleLine,
    RiFileList3Line
} from 'react-icons/ri';
import { STATO_LABELS, TIPOLOGIA_LABELS } from '../../services/clientiService';

const ClientiFilters = ({
    filters,
    onFilterChange,
    onReset,
    professionisti = []
}) => {
    const [showAdvanced, setShowAdvanced] = useState(false);

    // Filter professionals by role
    const nutrizionisti = professionisti.filter(p =>
        p.specialty === 'nutrizione' || p.specialty === 'nutrizionista'
    );
    const coaches = professionisti.filter(p => p.specialty === 'coach');
    const psicologi = professionisti.filter(p =>
        p.specialty === 'psicologia' || p.specialty === 'psicologo'
    );

    // Helper to count active advanced filters
    const activeAdvancedFiltersCount = () => {
        const advancedKeys = [
            'check_day', 'reach_out', 'trasformazione_fisica', 'trasformazione_fisica_condivisa',
            'allenamento_dal_from', 'allenamento_dal_to', 'nuovo_allenamento_il_from', 'nuovo_allenamento_il_to',
            'marketing_usabile', 'marketing_stories', 'marketing_carosello', 'marketing_videofeedback',
            'missing_check_day', 'missing_check_saltati', 'missing_reach_out',
            'missing_stato_nutrizione', 'missing_stato_chat_nutrizione',
            'missing_stato_coach', 'missing_stato_chat_coaching',
            'missing_stato_psicologia', 'missing_stato_chat_psicologia',
            'missing_piano_dieta', 'missing_piano_allenamento'
        ];
        return advancedKeys.filter(key => filters[key] && filters[key] !== '' && filters[key] !== '0').length;
    };

    const advancedCount = activeAdvancedFiltersCount();

    return (
        <div className="card shadow-sm border-0 mb-4">
            <div className="card-header bg-white border-bottom-0 py-3 d-flex justify-content-between align-items-center">
                <h5 className="mb-0 d-flex align-items-center gap-2 text-primary">
                    <RiFilter3Line /> Filtra Risultati
                </h5>
                <div className="d-flex gap-2">
                    <button
                        className={`btn btn-sm ${showAdvanced ? 'btn-primary' : 'btn-outline-primary'}`}
                        onClick={() => setShowAdvanced(!showAdvanced)}
                    >
                        {showAdvanced ? <RiArrowUpSLine className="me-1" /> : <RiArrowDownSLine className="me-1" />}
                        Filtri Avanzati
                        {advancedCount > 0 && (
                            <span className="badge bg-white text-primary ms-2 rounded-pill">
                                {advancedCount}
                            </span>
                        )}
                    </button>
                    <button
                        className="btn btn-sm btn-outline-secondary"
                        onClick={onReset}
                        title="Resetta tutti i filtri"
                    >
                        <RiRefreshLine className="me-1" /> Reset
                    </button>
                </div>
            </div>

            <div className="card-body pt-0">
                {/* --- BASIC FILTERS ROW --- */}
                <div className="row g-3 align-items-end">
                    {/* Search */}
                    <div className="col-lg-3 col-md-6">
                        <label className="form-label small text-muted fw-bold mb-1">Cerca</label>
                        <div className="position-relative">
                            <RiSearchLine className="position-absolute text-muted" style={{ left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
                            <input
                                type="text"
                                className="form-control ps-4"
                                placeholder="Nome, email, telefono..."
                                value={filters.search || ''}
                                onChange={(e) => onFilterChange('search', e.target.value)}
                            />
                        </div>
                    </div>

                    {/* Stato */}
                    <div className="col-lg-2 col-md-3">
                        <label className="form-label small text-muted fw-bold mb-1">Stato</label>
                        <select
                            className="form-select"
                            value={filters.stato || ''}
                            onChange={(e) => onFilterChange('stato', e.target.value)}
                        >
                            <option value="">Tutti</option>
                            {Object.entries(STATO_LABELS).map(([value, label]) => (
                                <option key={value} value={value}>{label}</option>
                            ))}
                        </select>
                    </div>

                    {/* Tipologia */}
                    <div className="col-lg-2 col-md-3">
                        <label className="form-label small text-muted fw-bold mb-1">Tipologia</label>
                        <select
                            className="form-select"
                            value={filters.tipologia || ''}
                            onChange={(e) => onFilterChange('tipologia', e.target.value)}
                        >
                            <option value="">Tutte</option>
                            {Object.entries(TIPOLOGIA_LABELS).map(([value, label]) => (
                                <option key={value} value={value}>{label}</option>
                            ))}
                        </select>
                    </div>

                    {/* Nutrizionista */}
                    <div className="col-lg-2 col-md-4">
                        <label className="form-label small text-muted fw-bold mb-1">Nutrizionista</label>
                        <select
                            className="form-select"
                            value={filters.nutrizionista || ''}
                            onChange={(e) => onFilterChange('nutrizionista', e.target.value)}
                        >
                            <option value="">Tutti</option>
                            {nutrizionisti.map(p => (
                                <option key={p.id} value={p.id}>{p.full_name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Coach */}
                    <div className="col-lg-2 col-md-4">
                        <label className="form-label small text-muted fw-bold mb-1">Coach</label>
                        <select
                            className="form-select"
                            value={filters.coach || ''}
                            onChange={(e) => onFilterChange('coach', e.target.value)}
                        >
                            <option value="">Tutti</option>
                            {coaches.map(p => (
                                <option key={p.id} value={p.id}>{p.full_name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Psicologo (New) */}
                    <div className="col-lg-2 col-md-4">
                        <label className="form-label small text-muted fw-bold mb-1">Psicologo</label>
                        <select
                            className="form-select"
                            value={filters.psicologa || ''}
                            onChange={(e) => onFilterChange('psicologa', e.target.value)}
                        >
                            <option value="">Tutti</option>
                            {psicologi.map(p => (
                                <option key={p.id} value={p.id}>{p.full_name}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* --- ADVANCED FILTERS SECTION --- */}
                {showAdvanced && (
                    <div className="mt-4 pt-3 border-top animate__animated animate__fadeIn">

                        {/* Status Details */}
                        <h6 className="text-secondary mb-3 d-flex align-items-center gap-2">
                            <RiUserStarLine /> Dettagli Stato
                        </h6>
                        <div className="row g-3 mb-4">
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Giorno Check</label>
                                <select
                                    className="form-select"
                                    value={filters.check_day || ''}
                                    onChange={(e) => onFilterChange('check_day', e.target.value)}
                                >
                                    <option value="">Tutti</option>
                                    <option value="lunedi">Lunedì</option>
                                    <option value="martedi">Martedì</option>
                                    <option value="mercoledi">Mercoledì</option>
                                    <option value="giovedi">Giovedì</option>
                                    <option value="venerdi">Venerdì</option>
                                    <option value="sabato">Sabato</option>
                                    <option value="domenica">Domenica</option>
                                </select>
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Reach Out</label>
                                <select
                                    className="form-select"
                                    value={filters.reach_out || ''}
                                    onChange={(e) => onFilterChange('reach_out', e.target.value)}
                                >
                                    <option value="">Tutti</option>
                                    <option value="lunedi">Lunedì</option>
                                    <option value="martedi">Martedì</option>
                                    <option value="mercoledi">Mercoledì</option>
                                    <option value="giovedi">Giovedì</option>
                                    <option value="venerdi">Venerdì</option>
                                    <option value="sabato">Sabato</option>
                                    <option value="domenica">Domenica</option>
                                </select>
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Trasformazione Fisica</label>
                                <select
                                    className="form-select"
                                    value={filters.trasformazione_fisica || ''}
                                    onChange={(e) => onFilterChange('trasformazione_fisica', e.target.value)}
                                >
                                    <option value="">Tutti</option>
                                    <option value="1">Sì</option>
                                    <option value="0">No</option>
                                </select>
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Trasf. Condivisa</label>
                                <select
                                    className="form-select"
                                    value={filters.trasformazione_fisica_condivisa || ''}
                                    onChange={(e) => onFilterChange('trasformazione_fisica_condivisa', e.target.value)}
                                >
                                    <option value="">Tutti</option>
                                    <option value="1">Sì</option>
                                    <option value="0">No</option>
                                </select>
                            </div>
                        </div>

                        {/* Date Ranges */}
                        <h6 className="text-secondary mb-3 d-flex align-items-center gap-2">
                            <RiCalendarLine /> Date Allenamento
                        </h6>
                        <div className="row g-3 mb-4">
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Allenamento Dal (Da)</label>
                                <input
                                    type="date"
                                    className="form-control"
                                    value={filters.allenamento_dal_from || ''}
                                    onChange={(e) => onFilterChange('allenamento_dal_from', e.target.value)}
                                />
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Allenamento Dal (A)</label>
                                <input
                                    type="date"
                                    className="form-control"
                                    value={filters.allenamento_dal_to || ''}
                                    onChange={(e) => onFilterChange('allenamento_dal_to', e.target.value)}
                                />
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Nuovo Allenamento Il (Da)</label>
                                <input
                                    type="date"
                                    className="form-control"
                                    value={filters.nuovo_allenamento_il_from || ''}
                                    onChange={(e) => onFilterChange('nuovo_allenamento_il_from', e.target.value)}
                                />
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Nuovo Allenamento Il (A)</label>
                                <input
                                    type="date"
                                    className="form-control"
                                    value={filters.nuovo_allenamento_il_to || ''}
                                    onChange={(e) => onFilterChange('nuovo_allenamento_il_to', e.target.value)}
                                />
                            </div>
                        </div>

                        {/* Marketing */}
                        <h6 className="text-secondary mb-3 d-flex align-items-center gap-2">
                            <RiMegaphoneLine /> Marketing
                        </h6>
                        <div className="row g-3 mb-4">
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Usabile Marketing</label>
                                <select
                                    className="form-select"
                                    value={filters.marketing_usabile || ''}
                                    onChange={(e) => onFilterChange('marketing_usabile', e.target.value)}
                                >
                                    <option value="">Tutti</option>
                                    <option value="1">Sì</option>
                                    <option value="0">No</option>
                                </select>
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Stories Editate</label>
                                <select
                                    className="form-select"
                                    value={filters.marketing_stories || ''}
                                    onChange={(e) => onFilterChange('marketing_stories', e.target.value)}
                                >
                                    <option value="">Tutti</option>
                                    <option value="1">Sì</option>
                                    <option value="0">No</option>
                                </select>
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Carosello Editato</label>
                                <select
                                    className="form-select"
                                    value={filters.marketing_carosello || ''}
                                    onChange={(e) => onFilterChange('marketing_carosello', e.target.value)}
                                >
                                    <option value="">Tutti</option>
                                    <option value="1">Sì</option>
                                    <option value="0">No</option>
                                </select>
                            </div>
                            <div className="col-md-3">
                                <label className="form-label small text-muted mb-1">Videofeedback Editato</label>
                                <select
                                    className="form-select"
                                    value={filters.marketing_videofeedback || ''}
                                    onChange={(e) => onFilterChange('marketing_videofeedback', e.target.value)}
                                >
                                    <option value="">Tutti</option>
                                    <option value="1">Sì</option>
                                    <option value="0">No</option>
                                </select>
                            </div>
                        </div>

                        {/* Missing Data */}
                        <h6 className="text-danger mb-3 d-flex align-items-center gap-2">
                            <RiErrorWarningLine /> Campi NON Compilati
                        </h6>
                        <div className="row g-3">
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
                                            id={item.key}
                                            checked={filters[item.key] === '1'}
                                            onChange={(e) => onFilterChange(item.key, e.target.checked ? '1' : '0')}
                                        />
                                        <label className="form-check-label small" htmlFor={item.key}>{item.label}</label>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <h6 className="text-warning mt-4 mb-3 d-flex align-items-center gap-2 small text-uppercase fw-bold">
                            <RiCheckDoubleLine /> Stati Servizio Mancanti
                        </h6>
                        <div className="row g-3">
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
                                            id={item.key}
                                            checked={filters[item.key] === '1'}
                                            onChange={(e) => onFilterChange(item.key, e.target.checked ? '1' : '0')}
                                        />
                                        <label className="form-check-label small" htmlFor={item.key}>{item.label}</label>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <h6 className="text-info mt-4 mb-3 d-flex align-items-center gap-2 small text-uppercase fw-bold">
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
                                            id={item.key}
                                            checked={filters[item.key] === '1'}
                                            onChange={(e) => onFilterChange(item.key, e.target.checked ? '1' : '0')}
                                        />
                                        <label className="form-check-label small" htmlFor={item.key}>{item.label}</label>
                                    </div>
                                </div>
                            ))}
                        </div>

                    </div>
                )}
            </div>
        </div>
    );
};

export default ClientiFilters;

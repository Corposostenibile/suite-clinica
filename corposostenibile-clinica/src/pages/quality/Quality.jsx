import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { createPortal } from 'react-dom';
import teamService from '../../services/teamService';
import { useAuth } from '../../context/AuthContext';
import { normalizeAvatarPath } from '../../utils/mediaUrl';
import qualityService, {
    QUALITY_SPECIALTIES,
    getWeekBounds,
    formatDateForApi,
    formatDateForDisplay,
    getScoreStyle,
    getMissRateBadgeStyle,
    getBandBadgeStyle,
    getCurrentQuarter,
    getAvailableQuarters,
    getSuperMalusBadgeStyle,
} from '../../services/qualityService';
import './Quality.css';

const BAND_BADGE_STYLES = {
    '100%': { background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff' },
    '60%':  { background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', color: '#fff' },
    '30%':  { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: '#fff' },
    '0%':   { background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)', color: '#fff' },
};

const STAT_STYLES = {
    nutrizione: { color: '#22c55e', bg: 'rgba(34, 197, 94, 0.1)' },
    coach:      { color: '#f97316', bg: 'rgba(249, 115, 22, 0.1)' },
    psicologia: { color: '#ec4899', bg: 'rgba(236, 72, 153, 0.1)' },
};

function Quality() {
    const { user } = useAuth();
    const isAdmin = Boolean(user?.is_admin || user?.role === 'admin');
    const isCco = user?.specialty === 'cco';
    const isTeamLeader = user?.role === 'team_leader';
    const canCalculateQuality = isAdmin || isCco;

    const lockedSpecialty = (() => {
        const value = String(user?.specialty || '').toLowerCase();
        if (value === 'coach') return 'coach';
        if (value === 'nutrizione' || value === 'nutrizionista') return 'nutrizione';
        if (value === 'psicologia' || value === 'psicologo') return 'psicologia';
        return null;
    })();

    // --- STATE ---
    const [viewMode, setViewMode] = useState('weekly');

    // Weekly
    const [specialty, setSpecialty] = useState('nutrizione');
    const [professionals, setProfessionals] = useState([]);
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [teams, setTeams] = useState([]);
    const [selectedTeam, setSelectedTeam] = useState('');
    const [currentWeek, setCurrentWeek] = useState(getWeekBounds());
    const [error, setError] = useState(null);
    const [brokenAvatars, setBrokenAvatars] = useState({});

    // Quarterly
    const [quarter, setQuarter] = useState(getCurrentQuarter());
    const [quarterlySummary, setQuarterlySummary] = useState(null);
    const [quarterlyLoading, setQuarterlyLoading] = useState(false);
    const [quarterlyError, setQuarterlyError] = useState(null);
    const [quarterlyCalculating, setQuarterlyCalculating] = useState(false);
    const [quarterlyCalcResult, setQuarterlyCalcResult] = useState(null);

    // Pagination
    const [pagination, setPagination] = useState({ page: 1, perPage: 25, total: 0, totalPages: 0 });

    // Calc Modal
    const [showCalcModal, setShowCalcModal] = useState(false);
    const [calcSpecialty, setCalcSpecialty] = useState('nutrizione');
    const [calcTeam, setCalcTeam] = useState('');
    const [calcWeekStart, setCalcWeekStart] = useState(getWeekBounds());
    const [calcTeams, setCalcTeams] = useState([]);
    const [calcTeamsLoading, setCalcTeamsLoading] = useState(false);
    const [calculating, setCalculating] = useState(false);
    const [calcResult, setCalcResult] = useState(null);

    useEffect(() => { if (isTeamLeader) setViewMode('weekly'); }, [isTeamLeader]);
    useEffect(() => { if (isTeamLeader && lockedSpecialty && specialty !== lockedSpecialty) setSpecialty(lockedSpecialty); }, [isTeamLeader, lockedSpecialty, specialty]);

    // --- WEEKLY ---
    const fetchQualityData = useCallback(async () => {
        if (!selectedTeam) { setLoading(false); return; }
        setLoading(true); setError(null);
        try {
            const data = await qualityService.getWeeklyScores({
                specialty, week: formatDateForApi(currentWeek.start), team_id: selectedTeam,
            });
            setProfessionals(data.professionals || []);
            setStats(data.stats || {});
            setPagination(prev => ({ ...prev, total: data.professionals?.length || 0, totalPages: Math.ceil((data.professionals?.length || 0) / prev.perPage) }));
        } catch (err) {
            console.error('Error fetching quality data:', err);
            setError('Errore nel caricamento dei dati quality');
            setProfessionals([]); setStats({});
        } finally { setLoading(false); }
    }, [specialty, currentWeek, selectedTeam]);

    const fetchTeams = useCallback(async (autoSelect = false) => {
        try {
            const data = await teamService.getTeams({ team_type: specialty, active: '1' });
            const teamList = data.teams || [];
            setTeams(teamList);
            if (autoSelect && teamList.length > 0) setSelectedTeam(String(teamList[0].id));
        } catch (err) { console.error('Error fetching teams:', err); setTeams([]); }
    }, [specialty]);

    useEffect(() => { if (viewMode === 'weekly') { setPagination(prev => ({ ...prev, page: 1 })); setSelectedTeam(''); fetchTeams(true); } }, [specialty, viewMode, fetchTeams]);
    useEffect(() => { if (viewMode === 'weekly' && selectedTeam) fetchQualityData(); }, [selectedTeam, currentWeek, viewMode, fetchQualityData]);
    useEffect(() => { setPagination(prev => ({ ...prev, page: 1 })); }, [searchTerm]);

    useEffect(() => {
        const fetchCalcTeams = async () => {
            setCalcTeamsLoading(true);
            try { const data = await teamService.getTeams({ team_type: calcSpecialty, active: '1' }); setCalcTeams(data.teams || []); setCalcTeam(''); }
            catch { setCalcTeams([]); }
            finally { setCalcTeamsLoading(false); }
        };
        if (showCalcModal) fetchCalcTeams();
    }, [calcSpecialty, showCalcModal]);

    const navigateWeek = (dir) => { const d = new Date(currentWeek.start); d.setDate(d.getDate() + dir * 7); setCurrentWeek(getWeekBounds(d)); };
    const navigateCalcWeek = (dir) => { const d = new Date(calcWeekStart.start); d.setDate(d.getDate() + dir * 7); setCalcWeekStart(getWeekBounds(d)); };

    const handleCalculateQuality = async () => {
        setCalculating(true); setCalcResult(null);
        try {
            const params = { specialty: calcSpecialty, week: formatDateForApi(calcWeekStart.start) };
            if (calcTeam) params.team_id = calcTeam;
            const result = await qualityService.calculateQuality(params);
            setCalcResult(result);
            if (calcSpecialty === specialty && formatDateForApi(calcWeekStart.start) === formatDateForApi(currentWeek.start)) fetchQualityData();
        } catch (err) {
            setCalcResult({ success: false, error: err.response?.data?.error || err.message });
        } finally { setCalculating(false); }
    };

    const closeCalcModal = () => { setShowCalcModal(false); setCalcResult(null); };

    const resetFilters = () => {
        setSearchTerm(''); setCurrentWeek(getWeekBounds());
        if (teams.length > 0) setSelectedTeam(String(teams[0].id));
    };

    const filteredProfessionals = professionals.filter(prof => {
        if (!searchTerm) return true;
        return `${prof.first_name} ${prof.last_name}`.toLowerCase().includes(searchTerm.toLowerCase());
    });

    const paginatedProfessionals = filteredProfessionals.slice((pagination.page - 1) * pagination.perPage, pagination.page * pagination.perPage);
    const totalPages = Math.ceil(filteredProfessionals.length / pagination.perPage);
    const handlePageChange = (p) => setPagination(prev => ({ ...prev, page: p }));

    const getInitials = (fn, ln) => `${fn?.[0] || ''}${ln?.[0] || ''}`.toUpperCase();

    const getPageNumbers = () => {
        const pages = [], total = totalPages, current = pagination.page;
        if (total <= 5) { for (let i = 1; i <= total; i++) pages.push(i); }
        else if (current <= 3) { for (let i = 1; i <= 5; i++) pages.push(i); }
        else if (current >= total - 2) { for (let i = total - 4; i <= total; i++) pages.push(i); }
        else { for (let i = current - 2; i <= current + 2; i++) pages.push(i); }
        return pages;
    };

    // --- QUARTERLY ---
    const fetchQuarterlySummary = useCallback(async () => {
        setQuarterlyLoading(true); setQuarterlyError(null);
        try { setQuarterlySummary(await qualityService.getQuarterlySummary(quarter)); }
        catch { setQuarterlyError('Errore nel caricamento dei dati trimestrali'); }
        finally { setQuarterlyLoading(false); }
    }, [quarter]);

    useEffect(() => { if (viewMode === 'quarterly') fetchQuarterlySummary(); }, [viewMode, fetchQuarterlySummary]);

    const handleCalculateQuarterly = async () => {
        setQuarterlyCalculating(true); setQuarterlyCalcResult(null);
        try {
            const result = await qualityService.calculateQuarterly(quarter);
            setQuarterlyCalcResult(result);
            setTimeout(fetchQuarterlySummary, 1000);
        } catch (err) {
            setQuarterlyCalcResult({ success: false, error: err.message });
        } finally { setQuarterlyCalculating(false); }
    };

    const quarters = getAvailableQuarters();
    const specConfig = QUALITY_SPECIALTIES[specialty];
    const selectedTeamName = teams.find(t => String(t.id) === selectedTeam)?.name || '';
    const specStatStyle = STAT_STYLES[specialty] || STAT_STYLES.nutrizione;

    const renderAvatar = (prof) => {
        const avatarSrc = normalizeAvatarPath(prof.avatar_path || prof.avatar_url);
        if (avatarSrc && !brokenAvatars[prof.id]) {
            return <img src={avatarSrc} alt={`${prof.first_name} ${prof.last_name}`} className="qd-avatar" onError={() => setBrokenAvatars(prev => ({ ...prev, [prof.id]: true }))} />;
        }
        return <div className="qd-avatar-initials" style={{ background: specConfig.gradient }}>{getInitials(prof.first_name, prof.last_name)}</div>;
    };

    // --- RENDER ---
    return (
        <div className="container-fluid p-0">
            {/* Header */}
            <div className="qd-header">
                <div>
                    <h2>Quality Dashboard</h2>
                    <p className="qd-header-sub">Monitoraggio performance e KPI</p>
                </div>
                {!isTeamLeader && (
                    <div className="qd-view-tabs">
                        <button className={`qd-view-tab${viewMode === 'weekly' ? ' active' : ''}`} onClick={() => setViewMode('weekly')}>
                            <i className="ri-calendar-week-line"></i> Analisi Settimanale
                        </button>
                        <button className={`qd-view-tab${viewMode === 'quarterly' ? ' active' : ''}`} onClick={() => setViewMode('quarterly')}>
                            <i className="ri-pie-chart-2-line"></i> KPI Trimestrali & Malus
                        </button>
                    </div>
                )}
            </div>

            {/* ===== WEEKLY VIEW ===== */}
            {viewMode === 'weekly' && (
                <>
                    {/* Specialty pills + action */}
                    <div className="qd-section-header">
                        <div>
                            <h4>Quality Score</h4>
                            <p className="qd-section-sub">
                                {filteredProfessionals.length} professionisti
                                {selectedTeamName && <> &middot; <strong>{selectedTeamName}</strong></>}
                            </p>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                            <div className="qd-specialty-pills">
                                {Object.entries(QUALITY_SPECIALTIES)
                                    .filter(([key]) => !isTeamLeader || !lockedSpecialty || key === lockedSpecialty)
                                    .map(([key, spec]) => (
                                        <button
                                            key={key}
                                            className={`qd-specialty-pill${specialty === key ? ` active-${key}` : ''}`}
                                            onClick={() => setSpecialty(key)}
                                        >
                                            <i className={spec.icon}></i> {spec.label}
                                        </button>
                                    ))}
                            </div>
                            {canCalculateQuality && (
                                <button className="qd-action-btn" onClick={() => setShowCalcModal(true)}>
                                    <i className="ri-calculator-line"></i> Calcola Quality
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Stats */}
                    <div className="qd-stats-row">
                        {[
                            { label: 'Media Quality', value: stats.avg_quality != null ? stats.avg_quality.toFixed(1) : '-', icon: 'ri-star-line', style: specStatStyle },
                            { label: 'Clienti Eleggibili', value: stats.total_eligible || 0, icon: 'ri-group-line', style: { color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' } },
                            { label: 'Check Effettuati', value: stats.total_checks || 0, icon: 'ri-checkbox-circle-line', style: { color: '#25B36A', bg: 'rgba(37, 179, 106, 0.1)' } },
                            { label: 'Miss Rate Medio', value: stats.avg_miss_rate != null ? `${(stats.avg_miss_rate * 100).toFixed(1)}%` : '-', icon: 'ri-percent-line', style: stats.avg_miss_rate > 0.2 ? { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' } : { color: '#22c55e', bg: 'rgba(34, 197, 94, 0.1)' } },
                        ].map((stat, i) => (
                            <div key={i} className="qd-stat-card">
                                <div>
                                    <div className="qd-stat-value" style={{ color: stat.style.color }}>{stat.value}</div>
                                    <div className="qd-stat-label">{stat.label}</div>
                                </div>
                                <div className="qd-stat-icon" style={{ background: stat.style.bg, color: stat.style.color }}>
                                    <i className={stat.icon}></i>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Filter bar */}
                    <div className="qd-filter-bar">
                        <input
                            type="text" className="qd-search-input"
                            placeholder="Cerca professionista..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                        <select className="qd-filter-select" value={selectedTeam} onChange={(e) => setSelectedTeam(e.target.value)}>
                            {teams.length === 0 ? (
                                <option value="">Caricamento...</option>
                            ) : teams.map(team => (
                                <option key={team.id} value={team.id}>{team.name}</option>
                            ))}
                        </select>
                        <div className="qd-week-nav">
                            <button className="qd-week-btn" onClick={() => navigateWeek(-1)}>
                                <i className="ri-arrow-left-s-line"></i>
                            </button>
                            <div className="qd-week-label">
                                {formatDateForDisplay(currentWeek.start)} - {formatDateForDisplay(currentWeek.end)}
                            </div>
                            <button className="qd-week-btn" onClick={() => navigateWeek(1)}>
                                <i className="ri-arrow-right-s-line"></i>
                            </button>
                        </div>
                        <button className="qd-reset-btn" onClick={resetFilters}>
                            <i className="ri-refresh-line"></i> Reset
                        </button>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="qd-error">
                            {error}
                            <button className="qd-error-retry" onClick={fetchQualityData}>Riprova</button>
                        </div>
                    )}

                    {/* Content */}
                    {loading ? (
                        <div className="qd-loading">
                            <div className="qd-spinner"></div>
                            <p className="qd-loading-text">Caricamento professionisti...</p>
                        </div>
                    ) : filteredProfessionals.length === 0 ? (
                        <div className="qd-empty-weekly">
                            <i className="ri-user-search-line"></i>
                            <h5>Nessun professionista trovato</h5>
                            <p>{stats.with_score === 0 ? 'Non ci sono dati Quality Score calcolati per questa settimana' : 'Prova a modificare i filtri di ricerca'}</p>
                            <button className="qd-empty-weekly-btn" onClick={resetFilters}>
                                <i className="ri-refresh-line"></i> Reset Filtri
                            </button>
                        </div>
                    ) : (
                        <>
                            <div className="qd-table-card">
                                <div className="qd-table-wrap">
                                    <table className="qd-table">
                                        <thead>
                                            <tr>
                                                <th style={{ minWidth: '200px' }}>Professionista</th>
                                                <th className="center" style={{ minWidth: '100px' }}>Clienti</th>
                                                <th className="center" style={{ minWidth: '100px' }}>Check</th>
                                                <th className="center" style={{ minWidth: '100px' }}>Miss Rate</th>
                                                <th className="center" style={{ minWidth: '100px' }}>Q. Raw</th>
                                                <th className="center" style={{ minWidth: '100px' }}>Q. Final</th>
                                                <th className="center" style={{ minWidth: '100px' }}>Q. Trim</th>
                                                <th className="center" style={{ minWidth: '100px' }}>Band</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {paginatedProfessionals.map((prof) => {
                                                const q = prof.quality || {};
                                                return (
                                                    <tr key={prof.id}>
                                                        <td>
                                                            <div className="qd-name-cell">
                                                                {renderAvatar(prof)}
                                                                <Link to={`/team-dettaglio/${prof.id}`} className="qd-name-link">
                                                                    {prof.first_name} {prof.last_name}
                                                                </Link>
                                                            </div>
                                                        </td>
                                                        <td className="center">
                                                            {q.n_clients_eligible ? <span className="qd-value-accent">{q.n_clients_eligible}</span> : <span className="qd-value-muted">&mdash;</span>}
                                                        </td>
                                                        <td className="center">
                                                            {q.n_checks_done ? <span className="qd-value-accent">{q.n_checks_done}</span> : <span className="qd-value-muted">&mdash;</span>}
                                                        </td>
                                                        <td className="center">
                                                            {q.miss_rate != null ? (
                                                                <span className="qd-badge" style={getMissRateBadgeStyle(q.miss_rate)}>
                                                                    {(q.miss_rate * 100).toFixed(1)}%
                                                                </span>
                                                            ) : <span className="qd-value-muted">&mdash;</span>}
                                                        </td>
                                                        <td className="center">
                                                            {q.quality_raw != null ? <span style={{ fontWeight: 500 }}>{q.quality_raw.toFixed(2)}</span> : <span className="qd-value-muted">&mdash;</span>}
                                                        </td>
                                                        <td className="center">
                                                            {q.quality_final != null ? <span style={getScoreStyle(q.quality_final)}>{q.quality_final.toFixed(2)}</span> : <span className="qd-value-muted">&mdash;</span>}
                                                        </td>
                                                        <td className="center">
                                                            {q.quality_trim != null ? <span style={{ fontWeight: 500 }}>{q.quality_trim.toFixed(2)}</span> : <span className="qd-value-muted">&mdash;</span>}
                                                        </td>
                                                        <td className="center">
                                                            {q.bonus_band ? (
                                                                <span className="qd-badge" style={BAND_BADGE_STYLES[q.bonus_band] || BAND_BADGE_STYLES['0%']}>
                                                                    {q.bonus_band}
                                                                </span>
                                                            ) : <span className="qd-value-muted">&mdash;</span>}
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div className="qd-pagination">
                                    <span className="qd-pagination-info">
                                        Mostrando {((pagination.page - 1) * pagination.perPage) + 1}-{Math.min(pagination.page * pagination.perPage, filteredProfessionals.length)} di {filteredProfessionals.length}
                                    </span>
                                    <div className="qd-pagination-buttons">
                                        <button className="qd-page-btn" onClick={() => handlePageChange(1)} disabled={pagination.page === 1}>&laquo;</button>
                                        <button className="qd-page-btn" onClick={() => handlePageChange(pagination.page - 1)} disabled={pagination.page === 1}>&lsaquo;</button>
                                        {getPageNumbers().map(p => (
                                            <button key={p} className={`qd-page-btn${pagination.page === p ? ' active' : ''}`} onClick={() => handlePageChange(p)}>{p}</button>
                                        ))}
                                        <button className="qd-page-btn" onClick={() => handlePageChange(pagination.page + 1)} disabled={pagination.page === totalPages}>&rsaquo;</button>
                                        <button className="qd-page-btn" onClick={() => handlePageChange(totalPages)} disabled={pagination.page === totalPages}>&raquo;</button>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </>
            )}

            {/* ===== QUARTERLY VIEW ===== */}
            {viewMode === 'quarterly' && (
                <>
                    {/* Quarterly header */}
                    <div className="qd-section-header">
                        <div>
                            <h4><i className="ri-pie-chart-2-line" style={{ color: '#25B36A', marginRight: '8px' }}></i>KPI Trimestrale & Super Malus</h4>
                            <p className="qd-section-sub">Bonus composito: 60% Rinnovo Adj. + 40% Quality</p>
                        </div>
                        <div className="qd-quarter-controls">
                            <select className="qd-filter-select" value={quarter} onChange={(e) => setQuarter(e.target.value)}>
                                {quarters.map(q => <option key={q} value={q}>{q}</option>)}
                            </select>
                            {canCalculateQuality && (
                                <button className="qd-action-btn" onClick={handleCalculateQuarterly} disabled={quarterlyCalculating}>
                                    {quarterlyCalculating ? <><span className="qd-spinner-sm"></span> Calcolo...</> : <><i className="ri-calculator-line"></i> Calcola Trimestre</>}
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Quarterly error */}
                    {quarterlyError && (
                        <div className="qd-error">
                            <i className="ri-alert-line"></i> {quarterlyError}
                            <button className="qd-error-retry" onClick={fetchQuarterlySummary}>Riprova</button>
                        </div>
                    )}

                    {/* Quarterly calc result */}
                    {quarterlyCalcResult && (
                        <div className={quarterlyCalcResult.success ? 'qd-alert-success' : 'qd-alert-danger'}>
                            {quarterlyCalcResult.success ? (
                                <>
                                    <i className="ri-checkbox-circle-fill"></i>
                                    Calcolo completato! Processati <strong>{quarterlyCalcResult.professionisti_processati}</strong> professionisti,
                                    <strong> {quarterlyCalcResult.super_malus_applicati}</strong> con Super Malus.
                                </>
                            ) : (
                                <><i className="ri-error-warning-fill"></i> Errore: {quarterlyCalcResult.error}</>
                            )}
                            <button className="qd-alert-close" onClick={() => setQuarterlyCalcResult(null)}>&times;</button>
                        </div>
                    )}

                    {/* Quarterly content */}
                    {quarterlyLoading ? (
                        <div className="qd-loading">
                            <div className="qd-spinner"></div>
                            <p className="qd-loading-text">Caricamento KPI trimestrali...</p>
                        </div>
                    ) : quarterlySummary ? (
                        <>
                            {/* KPI Cards */}
                            <div className="qd-kpi-row">
                                <div className="qd-kpi-card">
                                    <div className="qd-kpi-top">
                                        <span className="qd-kpi-label">Professionisti</span>
                                        <i className="ri-team-line qd-kpi-icon" style={{ color: '#3b82f6' }}></i>
                                    </div>
                                    <div className="qd-kpi-value" style={{ color: '#3b82f6' }}>{quarterlySummary.total_professionisti || 0}</div>
                                </div>
                                <div className="qd-kpi-card">
                                    <div className="qd-kpi-top">
                                        <span className="qd-kpi-label">Con Super Malus</span>
                                        <i className="ri-alert-line qd-kpi-icon" style={{ color: '#ef4444' }}></i>
                                    </div>
                                    <div className="qd-kpi-value" style={{ color: '#ef4444' }}>{quarterlySummary.professionisti_con_malus || 0}</div>
                                </div>
                                <div className="qd-kpi-card">
                                    <div className="qd-kpi-top">
                                        <span className="qd-kpi-label">Bonus Totale Prima</span>
                                        <i className="ri-money-euro-circle-line qd-kpi-icon" style={{ color: '#22c55e' }}></i>
                                    </div>
                                    <div className="qd-kpi-value" style={{ color: '#22c55e' }}>{(quarterlySummary.total_bonus_before_malus || 0).toFixed(0)}%</div>
                                </div>
                                <div className="qd-kpi-card">
                                    <div className="qd-kpi-top">
                                        <span className="qd-kpi-label">Bonus Totale Dopo</span>
                                        <i className="ri-money-euro-box-line qd-kpi-icon" style={{ color: '#f59e0b' }}></i>
                                    </div>
                                    <div className="qd-kpi-value" style={{ color: '#f59e0b' }}>{(quarterlySummary.total_bonus_after_malus || 0).toFixed(0)}%</div>
                                    {quarterlySummary.bonus_reduction_total > 0 && (
                                        <div className="qd-stat-reduction">
                                            <i className="ri-arrow-down-line"></i> -{quarterlySummary.bonus_reduction_total.toFixed(0)}%
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Malus table */}
                            {quarterlySummary.malus_details && quarterlySummary.malus_details.length > 0 ? (
                                <div className="qd-table-card">
                                    <div className="qd-malus-header">
                                        <i className="ri-error-warning-line"></i>
                                        Professionisti con Super Malus ({quarterlySummary.malus_details.length})
                                    </div>
                                    <div className="qd-table-wrap">
                                        <table className="qd-table">
                                            <thead>
                                                <tr>
                                                    <th>Professionista</th>
                                                    <th className="center">Quality</th>
                                                    <th className="center">Rinnovo Adj</th>
                                                    <th className="center">Bonus</th>
                                                    <th className="center">Malus</th>
                                                    <th className="center">Finale</th>
                                                    <th>Causa</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {quarterlySummary.malus_details.map((item, idx) => (
                                                    <tr key={idx}>
                                                        <td>
                                                            <Link to={`/team-dettaglio/${item.professionista_id}`} className="qd-name-link">
                                                                {item.professionista_name}
                                                            </Link>
                                                            <div className="qd-stat-label">{item.specialty}</div>
                                                        </td>
                                                        <td className="center">
                                                            {item.quality_trim != null ? <span style={{ fontWeight: 600 }}>{item.quality_trim?.toFixed(2)}</span> : <span className="qd-value-muted">&mdash;</span>}
                                                        </td>
                                                        <td className="center">
                                                            {item.rinnovo_adj_percentage != null ? <span style={{ fontWeight: 600 }}>{item.rinnovo_adj_percentage?.toFixed(1)}%</span> : <span className="qd-value-muted">&mdash;</span>}
                                                        </td>
                                                        <td className="center">
                                                            <span className="qd-badge" style={getBandBadgeStyle(`${item.final_bonus_percentage?.toFixed(0)}%`)}>
                                                                {item.final_bonus_percentage?.toFixed(0)}%
                                                            </span>
                                                        </td>
                                                        <td className="center">
                                                            <span className="qd-badge" style={getSuperMalusBadgeStyle(item.super_malus_percentage || 0)}>
                                                                -{item.super_malus_percentage}%
                                                            </span>
                                                        </td>
                                                        <td className="center">
                                                            <span style={{ fontWeight: 700, color: '#22c55e' }}>
                                                                {item.final_bonus_after_malus?.toFixed(0)}%
                                                            </span>
                                                        </td>
                                                        <td>
                                                            <div className="qd-cause-badges">
                                                                {item.has_negative_review && (
                                                                    <span className="qd-cause-badge danger"><i className="ri-star-line"></i> Review ≤2</span>
                                                                )}
                                                                {item.has_refund && (
                                                                    <span className="qd-cause-badge warning"><i className="ri-refund-line"></i> Rimborso</span>
                                                                )}
                                                                {item.is_primary_for_malus && (
                                                                    <span className="qd-cause-badge info" title="Professionista primario"><i className="ri-user-star-line"></i></span>
                                                                )}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ) : (
                                <div className="qd-empty-state">
                                    <div className="qd-empty-icon"><i className="ri-checkbox-circle-line"></i></div>
                                    <div className="qd-empty-title">Nessun Super Malus</div>
                                    <p className="qd-empty-desc">Nessun professionista ha ricevuto penalità Super Malus in questo trimestre.</p>
                                </div>
                            )}
                        </>
                    ) : null}
                </>
            )}

            {/* ===== CALC MODAL (portal) ===== */}
            {showCalcModal && canCalculateQuality && createPortal(
                <div className="qd-modal-overlay" onClick={calculating ? undefined : closeCalcModal}>
                    <div className="qd-modal" onClick={e => e.stopPropagation()}>
                        <div className="qd-modal-header">
                            <h5 className="qd-modal-title">
                                <i className="ri-calculator-line"></i> Calcola Quality Score
                            </h5>
                            <button className="qd-modal-close" onClick={closeCalcModal} disabled={calculating}>&times;</button>
                        </div>
                        <div className="qd-modal-body">
                            {!calcResult ? (
                                <>
                                    <div className="qd-modal-field">
                                        <label className="qd-modal-label">Specializzazione</label>
                                        <div className="qd-specialty-pills">
                                            {Object.entries(QUALITY_SPECIALTIES).map(([key, spec]) => (
                                                <button
                                                    key={key}
                                                    className={`qd-specialty-pill${calcSpecialty === key ? ` active-${key}` : ''}`}
                                                    onClick={() => setCalcSpecialty(key)}
                                                    disabled={calculating}
                                                >
                                                    <i className={spec.icon}></i> {spec.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="qd-modal-field">
                                        <label className="qd-modal-label">Team (opzionale)</label>
                                        <select className="qd-modal-select" value={calcTeam} onChange={(e) => setCalcTeam(e.target.value)} disabled={calculating || calcTeamsLoading}>
                                            <option value="">{calcTeamsLoading ? 'Caricamento...' : 'Tutti i Team'}</option>
                                            {calcTeams.map(team => <option key={team.id} value={team.id}>{team.name}</option>)}
                                        </select>
                                    </div>

                                    <div className="qd-modal-field">
                                        <label className="qd-modal-label">Settimana</label>
                                        <div className="qd-week-nav">
                                            <button className="qd-week-btn" onClick={() => navigateCalcWeek(-1)} disabled={calculating}>
                                                <i className="ri-arrow-left-s-line"></i>
                                            </button>
                                            <div className="qd-week-label" style={{ flex: 1, textAlign: 'center' }}>
                                                {formatDateForDisplay(calcWeekStart.start)}
                                            </div>
                                            <button className="qd-week-btn" onClick={() => navigateCalcWeek(1)} disabled={calculating}>
                                                <i className="ri-arrow-right-s-line"></i>
                                            </button>
                                        </div>
                                    </div>

                                    <button className="qd-modal-submit" onClick={handleCalculateQuality} disabled={calculating}>
                                        {calculating ? <><span className="qd-spinner-sm"></span> Calcolo in corso...</> : <><i className="ri-calculator-fill"></i> Avvia Calcolo</>}
                                    </button>
                                </>
                            ) : (
                                <div className="qd-modal-result">
                                    <div className={`qd-modal-result-icon ${calcResult.success ? 'success' : 'error'}`}>
                                        <i className={calcResult.success ? 'ri-checkbox-circle-fill' : 'ri-error-warning-fill'}></i>
                                    </div>
                                    <h5>{calcResult.success ? 'Calcolo Completato' : 'Errore nel Calcolo'}</h5>
                                    <p>{calcResult.success
                                        ? `Il calcolo è stato completato con successo per ${calcResult.processed_count || 0} professionisti.`
                                        : calcResult.error}</p>
                                    <button className="qd-modal-result-btn" onClick={closeCalcModal}>Chiudi</button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>,
                document.body
            )}
        </div>
    );
}

export default Quality;

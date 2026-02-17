import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import teamService from '../../services/teamService';
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

// --- STYLES ---

// Weekly Table Styles
const tableStyles = {
    card: {
        borderRadius: '16px',
        border: 'none',
        boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        overflow: 'hidden',
    },
    tableHeader: {
        background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
        borderBottom: '2px solid #e2e8f0',
    },
    th: {
        padding: '16px 20px',
        fontSize: '11px',
        fontWeight: 700,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        color: '#64748b',
        whiteSpace: 'nowrap',
        borderBottom: 'none',
    },
    td: {
        padding: '16px 20px',
        fontSize: '14px',
        color: '#334155',
        borderBottom: '1px solid #f1f5f9',
        verticalAlign: 'middle',
    },
    row: {
        transition: 'all 0.15s ease',
    },
    nameLink: {
        color: '#3b82f6',
        fontWeight: 600,
        textDecoration: 'none',
        transition: 'color 0.15s ease',
    },
    emptyCell: {
        color: '#cbd5e1',
        fontStyle: 'normal',
        fontSize: '13px',
    },
    badge: {
        padding: '6px 12px',
        borderRadius: '6px',
        fontSize: '11px',
        fontWeight: 600,
        textTransform: 'capitalize',
        letterSpacing: '0.3px',
    },
    avatarInitials: {
        width: '36px',
        height: '36px',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '12px',
        fontWeight: 700,
        textTransform: 'uppercase',
        border: '2px solid #fff',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        color: '#fff',
    },
};

// Quarterly KPI Card Styles
const kpiCardStyles = {
    card: {
        borderRadius: '16px',
        border: 'none',
        boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
        overflow: 'hidden',
        height: '100%',
    },
    kpiValue: {
        fontSize: '2.5rem',
        fontWeight: 800,
        lineHeight: 1,
    },
    kpiLabel: {
        fontSize: '0.85rem',
        color: '#64748b',
        fontWeight: 500,
    },
    badge: {
        padding: '6px 14px',
        borderRadius: '8px',
        fontSize: '12px',
        fontWeight: 600,
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
    },
};

// Bonus band badge styles
const BAND_BADGE_STYLES = {
    '100%': { background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff' },
    '60%': { background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', color: '#fff' },
    '30%': { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: '#fff' },
    '0%': { background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)', color: '#fff' },
};

function Quality() {
    // --- STATE ---
    
    // View Mode
    const [viewMode, setViewMode] = useState('weekly'); // 'weekly' | 'quarterly'

    // Weekly State
    const [specialty, setSpecialty] = useState('nutrizione');
    const [professionals, setProfessionals] = useState([]);
    const [stats, setStats] = useState({});
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [teams, setTeams] = useState([]);
    const [selectedTeam, setSelectedTeam] = useState('');
    const [currentWeek, setCurrentWeek] = useState(getWeekBounds());
    const [hoveredRow, setHoveredRow] = useState(null);
    const [error, setError] = useState(null);

    // Quarterly State
    const [quarter, setQuarter] = useState(getCurrentQuarter());
    const [quarterlySummary, setQuarterlySummary] = useState(null);
    const [quarterlyLoading, setQuarterlyLoading] = useState(false);
    const [quarterlyError, setQuarterlyError] = useState(null);
    const [quarterlyCalculating, setQuarterlyCalculating] = useState(false);
    const [quarterlyCalcResult, setQuarterlyCalcResult] = useState(null);

    // Pagination (Weekly)
    const [pagination, setPagination] = useState({
        page: 1,
        perPage: 25,
        total: 0,
        totalPages: 0,
    });

    // Modal state (Weekly Calc)
    const [showCalcModal, setShowCalcModal] = useState(false);
    const [calcSpecialty, setCalcSpecialty] = useState('nutrizione');
    const [calcTeam, setCalcTeam] = useState('');
    const [calcWeekStart, setCalcWeekStart] = useState(getWeekBounds());
    const [calcTeams, setCalcTeams] = useState([]);
    const [calcTeamsLoading, setCalcTeamsLoading] = useState(false);
    const [calculating, setCalculating] = useState(false);
    const [calcResult, setCalcResult] = useState(null);

    // --- EFFECT & LOGIC: WEEKLY ---

    // Fetch quality data based on specialty, week, and team
    const fetchQualityData = useCallback(async () => {
        if (!selectedTeam) {
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const params = {
                specialty: specialty,
                week: formatDateForApi(currentWeek.start),
                team_id: selectedTeam,
            };

            const data = await qualityService.getWeeklyScores(params);
            setProfessionals(data.professionals || []);
            setStats(data.stats || {});
            setPagination(prev => ({
                ...prev,
                total: data.professionals?.length || 0,
                totalPages: Math.ceil((data.professionals?.length || 0) / prev.perPage),
            }));
        } catch (err) {
            console.error('Error fetching quality data:', err);
            setError('Errore nel caricamento dei dati quality');
            setProfessionals([]);
            setStats({});
        } finally {
            setLoading(false);
        }
    }, [specialty, currentWeek, selectedTeam]);

    // Fetch teams for filter and auto-select first team
    const fetchTeams = useCallback(async (autoSelect = false) => {
        try {
            const data = await teamService.getTeams({ team_type: specialty, active: '1' });
            const teamList = data.teams || [];
            setTeams(teamList);
            if (autoSelect && teamList.length > 0) {
                setSelectedTeam(String(teamList[0].id));
            }
        } catch (err) {
            console.error('Error fetching teams:', err);
            setTeams([]);
        }
    }, [specialty]);

    // Initial load and when specialty changes
    useEffect(() => {
        if (viewMode === 'weekly') {
            setPagination(prev => ({ ...prev, page: 1 }));
            setSelectedTeam('');
            fetchTeams(true);
        }
    }, [specialty, viewMode, fetchTeams]);

    // Fetch quality data when team or week changes
    useEffect(() => {
        if (viewMode === 'weekly' && selectedTeam) {
            fetchQualityData();
        }
    }, [selectedTeam, currentWeek, viewMode, fetchQualityData]);

    // Reset page when search changes
    useEffect(() => {
        setPagination(prev => ({ ...prev, page: 1 }));
    }, [searchTerm]);

    // Fetch teams for calc modal when calcSpecialty changes
    useEffect(() => {
        const fetchCalcTeams = async () => {
            setCalcTeamsLoading(true);
            try {
                const data = await teamService.getTeams({ team_type: calcSpecialty, active: '1' });
                setCalcTeams(data.teams || []);
                setCalcTeam('');
            } catch (err) {
                console.error('Error fetching calc teams:', err);
                setCalcTeams([]);
            } finally {
                setCalcTeamsLoading(false);
            }
        };
        if (showCalcModal) {
            fetchCalcTeams();
        }
    }, [calcSpecialty, showCalcModal]);

    // Navigate weeks
    const navigateWeek = (direction) => {
        const newDate = new Date(currentWeek.start);
        newDate.setDate(newDate.getDate() + (direction * 7));
        setCurrentWeek(getWeekBounds(newDate));
    };

    // Navigate calc week
    const navigateCalcWeek = (direction) => {
        const newDate = new Date(calcWeekStart.start);
        newDate.setDate(newDate.getDate() + (direction * 7));
        setCalcWeekStart(getWeekBounds(newDate));
    };

    // Handle calculate quality (Weekly)
    const handleCalculateQuality = async () => {
        setCalculating(true);
        setCalcResult(null);
        try {
            const params = {
                specialty: calcSpecialty,
                week: formatDateForApi(calcWeekStart.start),
            };
            if (calcTeam) {
                params.team_id = calcTeam;
            }
            const result = await qualityService.calculateQuality(params);
            setCalcResult(result);
            if (calcSpecialty === specialty && formatDateForApi(calcWeekStart.start) === formatDateForApi(currentWeek.start)) {
                fetchQualityData();
            }
        } catch (err) {
            console.error('Error calculating quality:', err);
            setCalcResult({ success: false, error: err.response?.data?.error || err.message });
        } finally {
            setCalculating(false);
        }
    };

    // Close modal and reset
    const closeCalcModal = () => {
        setShowCalcModal(false);
        setCalcResult(null);
    };

    // Reset filters
    const resetFilters = () => {
        setSearchTerm('');
        setCurrentWeek(getWeekBounds());
        if (teams.length > 0) {
            setSelectedTeam(String(teams[0].id));
        }
    };

    // Filter professionals by search term
    const filteredProfessionals = professionals.filter(prof => {
        if (!searchTerm) return true;
        const fullName = `${prof.first_name} ${prof.last_name}`.toLowerCase();
        return fullName.includes(searchTerm.toLowerCase());
    });

    // Pagination logic
    const paginatedProfessionals = filteredProfessionals.slice(
        (pagination.page - 1) * pagination.perPage,
        pagination.page * pagination.perPage
    );
    const totalPages = Math.ceil(filteredProfessionals.length / pagination.perPage);

    const handlePageChange = (newPage) => {
        setPagination(prev => ({ ...prev, page: newPage }));
    };

    const getInitials = (firstName, lastName) => {
        return `${firstName?.[0] || ''}${lastName?.[0] || ''}`.toUpperCase();
    };

    // --- EFFECT & LOGIC: QUARTERLY ---

    const fetchQuarterlySummary = useCallback(async () => {
        setQuarterlyLoading(true);
        setQuarterlyError(null);
        try {
            const data = await qualityService.getQuarterlySummary(quarter);
            setQuarterlySummary(data);
        } catch (err) {
            console.error('Error fetching quarterly summary:', err);
            setQuarterlyError('Errore nel caricamento dei dati trimestrali');
        } finally {
            setQuarterlyLoading(false);
        }
    }, [quarter]);

    useEffect(() => {
        if (viewMode === 'quarterly') {
            fetchQuarterlySummary();
        }
    }, [viewMode, fetchQuarterlySummary]);

    const handleCalculateQuarterly = async () => {
        setQuarterlyCalculating(true);
        setQuarterlyCalcResult(null);
        try {
            const result = await qualityService.calculateQuarterly(quarter);
            setQuarterlyCalcResult(result);
            setTimeout(fetchQuarterlySummary, 1000);
        } catch (err) {
            console.error('Error calculating quarterly:', err);
            setQuarterlyCalcResult({ success: false, error: err.message });
        } finally {
            setQuarterlyCalculating(false);
        }
    };

    const quarters = getAvailableQuarters();
    const specConfig = QUALITY_SPECIALTIES[specialty];
    const selectedTeamName = teams.find(t => String(t.id) === selectedTeam)?.name || '';

    // --- RENDER ---

    return (
        <div className="container-fluid p-0">
            {/* Unified Header & Controls */}
            <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-3">
                <div>
                    <h2 className="fw-bold mb-1" style={{ color: '#1e293b' }}>Quality Dashboard</h2>
                    <p className="text-muted mb-0">Monitoraggio performance e KPI</p>
                </div>
                
                {/* View Mode Selector */}
                <div className="bg-white p-1 rounded-3 shadow-sm d-inline-flex border">
                    <button
                        className={`btn btn-sm px-3 fw-medium transition-all ${viewMode === 'weekly' ? 'btn-primary' : 'btn-light text-muted bg-transparent'}`}
                        onClick={() => setViewMode('weekly')}
                        style={{ borderRadius: '8px' }}
                    >
                        <i className="ri-calendar-week-line me-2"></i>
                        Analisi Settimanale
                    </button>
                    <div className="vr mx-1 align-self-center" style={{ height: '20px', opacity: 0.2 }}></div>
                    <button
                        className={`btn btn-sm px-3 fw-medium transition-all ${viewMode === 'quarterly' ? 'btn-primary' : 'btn-light text-muted bg-transparent'}`}
                        onClick={() => setViewMode('quarterly')}
                        style={{ borderRadius: '8px' }}
                    >
                        <i className="ri-pie-chart-2-line me-2"></i>
                        KPI Trimestrali & Malus
                    </button>
                </div>
            </div>

            {/* WEEKLY VIEW */}
            {viewMode === 'weekly' && (
                <div className="fade-in">
                    {/* Weekly Header Controls */}
                    <div className="d-flex flex-wrap align-items-center justify-content-between mb-4">
                        <div>
                            <h4 className="mb-1">Quality Score</h4>
                            <p className="text-muted mb-0">
                                {filteredProfessionals.length} professionisti
                                {selectedTeamName && <span className="fw-semibold"> · {selectedTeamName}</span>}
                            </p>
                        </div>
                        <div className="tabs-scroll-mobile">
                            <div className="d-flex gap-2" style={{ flexWrap: 'nowrap', minWidth: 'max-content' }}>
                                {Object.entries(QUALITY_SPECIALTIES).map(([key, spec]) => (
                                    <button
                                        key={key}
                                        className={`btn px-3 ${specialty === key ? '' : 'btn-outline-secondary'}`}
                                        onClick={() => setSpecialty(key)}
                                        style={{
                                            ...(specialty === key ? {
                                                backgroundColor: key === 'nutrizione' ? '#22c55e' : key === 'coach' ? '#f97316' : '#ec4899',
                                                borderColor: 'transparent',
                                                color: 'white',
                                            } : {}),
                                            whiteSpace: 'nowrap',
                                        }}
                                    >
                                        <i className={`${spec.icon} me-2`}></i>
                                        {spec.label}
                                    </button>
                                ))}
                                <button
                                    className="btn btn-primary px-4"
                                    onClick={() => setShowCalcModal(true)}
                                    style={{ whiteSpace: 'nowrap' }}
                                >
                                    <i className="ri-calculator-line me-2"></i>
                                    Calcola Quality
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Stats Row (Weekly) */}
                    <div className="row g-3 mb-4">
                        {[
                            {
                                label: 'Media Quality',
                                value: stats.avg_quality !== null && stats.avg_quality !== undefined ? stats.avg_quality.toFixed(1) : '-',
                                icon: 'ri-star-line',
                                bg: specialty === 'nutrizione' ? 'success' : specialty === 'coach' ? 'warning' : '',
                                customBg: specialty === 'psicologia' ? '#ec4899' : undefined,
                            },
                            {
                                label: 'Clienti Eleggibili',
                                value: stats.total_eligible || 0,
                                icon: 'ri-group-line',
                                bg: 'primary',
                            },
                            {
                                label: 'Check Effettuati',
                                value: stats.total_checks || 0,
                                icon: 'ri-checkbox-circle-line',
                                bg: 'info',
                            },
                            {
                                label: 'Miss Rate Medio',
                                value: stats.avg_miss_rate !== null && stats.avg_miss_rate !== undefined
                                    ? `${(stats.avg_miss_rate * 100).toFixed(1)}%`
                                    : '-',
                                icon: 'ri-percent-line',
                                bg: stats.avg_miss_rate && stats.avg_miss_rate > 0.2 ? 'danger' : 'success',
                            },
                        ].map((stat, idx) => (
                            <div key={idx} className="col-xl-3 col-sm-6">
                                <div
                                    className={`card border-0 shadow-sm ${stat.bg && !stat.customBg ? `bg-${stat.bg}` : ''}`}
                                    style={stat.customBg ? { backgroundColor: stat.customBg } : {}}
                                >
                                    <div className="card-body py-3">
                                        <div className="d-flex align-items-center justify-content-between">
                                            <div>
                                                <h3 className="text-white mb-0 fw-bold">{stat.value}</h3>
                                                <span className="text-white opacity-75 small">{stat.label}</span>
                                            </div>
                                            <div
                                                className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center"
                                                style={{ width: '48px', height: '48px' }}
                                            >
                                                <i className={`${stat.icon} text-white fs-4`}></i>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Filters (Weekly) */}
                    <div className="card shadow-sm border-0 mb-4">
                        <div className="card-body py-3">
                            <div className="row g-2 align-items-center">
                                <div className="col-lg-3">
                                    <div className="position-relative">
                                        <i className="ri-search-line position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}></i>
                                        <input
                                            type="text"
                                            className="form-control bg-light border-0"
                                            placeholder="Cerca professionista..."
                                            value={searchTerm}
                                            onChange={(e) => setSearchTerm(e.target.value)}
                                            style={{ paddingLeft: '36px' }}
                                        />
                                    </div>
                                </div>
                                <div className="col-lg-2">
                                    <select
                                        className="form-select bg-light border-0"
                                        value={selectedTeam}
                                        onChange={(e) => setSelectedTeam(e.target.value)}
                                    >
                                        {teams.length === 0 ? (
                                            <option value="">Caricamento...</option>
                                        ) : (
                                            teams.map(team => (
                                                <option key={team.id} value={team.id}>{team.name}</option>
                                            ))
                                        )}
                                    </select>
                                </div>
                                <div className="col-lg-4">
                                    <div className="d-flex align-items-center gap-2">
                                        <button
                                            className="btn btn-outline-secondary"
                                            onClick={() => navigateWeek(-1)}
                                        >
                                            <i className="ri-arrow-left-s-line"></i>
                                        </button>
                                        <div className="flex-grow-1 text-center py-2 px-3 bg-light rounded">
                                            <span className="fw-semibold">
                                                {formatDateForDisplay(currentWeek.start)} - {formatDateForDisplay(currentWeek.end)}
                                            </span>
                                        </div>
                                        <button
                                            className="btn btn-outline-secondary"
                                            onClick={() => navigateWeek(1)}
                                        >
                                            <i className="ri-arrow-right-s-line"></i>
                                        </button>
                                    </div>
                                </div>
                                <div className="col-lg-3 text-end">
                                    <button
                                        className="btn btn-outline-secondary"
                                        onClick={resetFilters}
                                    >
                                        <i className="ri-refresh-line me-1"></i>Reset
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Error Alert (Weekly) */}
                    {error && (
                        <div className="alert alert-danger mb-4" style={{ borderRadius: '12px' }}>
                            {error}
                            <button className="btn btn-link btn-sm p-0 ms-2" onClick={fetchQualityData}>
                                Riprova
                            </button>
                        </div>
                    )}

                    {/* Weekly Content */}
                    {loading ? (
                        <div className="text-center py-5">
                            <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}></div>
                            <p className="mt-3 text-muted">Caricamento professionisti...</p>
                        </div>
                    ) : filteredProfessionals.length === 0 ? (
                        <div className="card border-0" style={tableStyles.card}>
                            <div className="card-body text-center py-5">
                                <div className="mb-4">
                                    <i className="ri-user-search-line" style={{ fontSize: '5rem', color: '#cbd5e1' }}></i>
                                </div>
                                <h5 style={{ color: '#475569' }}>Nessun professionista trovato</h5>
                                <p className="text-muted mb-4">
                                    {stats.with_score === 0
                                        ? 'Non ci sono dati Quality Score calcolati per questa settimana'
                                        : 'Prova a modificare i filtri di ricerca'}
                                </p>
                                <button
                                    className="btn btn-primary"
                                    onClick={resetFilters}
                                    style={{ borderRadius: '10px', padding: '10px 24px' }}
                                >
                                    <i className="ri-refresh-line me-2"></i>Reset Filtri
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            {/* Tabella Professionisti */}
                            <div className="card border-0" style={tableStyles.card}>
                                <div className="table-responsive">
                                    <table className="table mb-0">
                                        <thead style={tableStyles.tableHeader}>
                                            <tr>
                                                <th style={{ ...tableStyles.th, minWidth: '200px' }}>Professionista</th>
                                                <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '100px' }}>Clienti</th>
                                                <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '100px' }}>Check</th>
                                                <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '100px' }}>Miss Rate</th>
                                                <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '100px' }}>Q. Raw</th>
                                                <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '100px' }}>Q. Final</th>
                                                <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '100px' }}>Q. Trim</th>
                                                <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '100px' }}>Band</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {paginatedProfessionals.map((prof, index) => {
                                                const quality = prof.quality || {};
                                                const isHovered = hoveredRow === index;

                                                return (
                                                    <tr
                                                        key={prof.id}
                                                        style={{
                                                            ...tableStyles.row,
                                                            background: isHovered ? '#f8fafc' : 'transparent',
                                                        }}
                                                        onMouseEnter={() => setHoveredRow(index)}
                                                        onMouseLeave={() => setHoveredRow(null)}
                                                    >
                                                        {/* Professionista */}
                                                        <td style={tableStyles.td}>
                                                            <div className="d-flex align-items-center gap-3">
                                                                {prof.avatar_url ? (
                                                                    <img
                                                                        src={prof.avatar_url}
                                                                        alt={`${prof.first_name} ${prof.last_name}`}
                                                                        style={{
                                                                            ...tableStyles.avatarInitials,
                                                                            objectFit: 'cover',
                                                                        }}
                                                                    />
                                                                ) : (
                                                                    <div
                                                                        style={{
                                                                            ...tableStyles.avatarInitials,
                                                                            background: specConfig.gradient,
                                                                        }}
                                                                    >
                                                                        {getInitials(prof.first_name, prof.last_name)}
                                                                    </div>
                                                                )}
                                                                <Link
                                                                    to={`/team-dettaglio/${prof.id}`}
                                                                    style={tableStyles.nameLink}
                                                                    onMouseOver={(e) => e.currentTarget.style.color = '#2563eb'}
                                                                    onMouseOut={(e) => e.currentTarget.style.color = '#3b82f6'}
                                                                >
                                                                    {prof.first_name} {prof.last_name}
                                                                </Link>
                                                            </div>
                                                        </td>

                                                        {/* Clienti */}
                                                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                            {quality.n_clients_eligible ? (
                                                                <span style={{ color: '#3b82f6', fontWeight: 600 }}>
                                                                    {quality.n_clients_eligible}
                                                                </span>
                                                            ) : (
                                                                <span style={tableStyles.emptyCell}>—</span>
                                                            )}
                                                        </td>

                                                        {/* Check */}
                                                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                            {quality.n_checks_done ? (
                                                                <span style={{ color: '#22c55e', fontWeight: 600 }}>
                                                                    {quality.n_checks_done}
                                                                </span>
                                                            ) : (
                                                                <span style={tableStyles.emptyCell}>—</span>
                                                            )}
                                                        </td>

                                                        {/* Miss Rate */}
                                                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                            {quality.miss_rate !== undefined && quality.miss_rate !== null ? (
                                                                <span
                                                                    style={{
                                                                        ...tableStyles.badge,
                                                                        ...getMissRateBadgeStyle(quality.miss_rate),
                                                                    }}
                                                                >
                                                                    {(quality.miss_rate * 100).toFixed(1)}%
                                                                </span>
                                                            ) : (
                                                                <span style={tableStyles.emptyCell}>—</span>
                                                            )}
                                                        </td>

                                                        {/* Q. Raw */}
                                                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                            {quality.quality_raw !== null && quality.quality_raw !== undefined ? (
                                                                <span style={{ fontWeight: 500 }}>{quality.quality_raw.toFixed(2)}</span>
                                                            ) : (
                                                                <span style={tableStyles.emptyCell}>—</span>
                                                            )}
                                                        </td>

                                                        {/* Q. Final */}
                                                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                            {quality.quality_final !== null && quality.quality_final !== undefined ? (
                                                                <span style={getScoreStyle(quality.quality_final)}>
                                                                    {quality.quality_final.toFixed(2)}
                                                                </span>
                                                            ) : (
                                                                <span style={tableStyles.emptyCell}>—</span>
                                                            )}
                                                        </td>

                                                        {/* Q. Trim */}
                                                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                            {quality.quality_trim !== null && quality.quality_trim !== undefined ? (
                                                                <span style={{ fontWeight: 500 }}>{quality.quality_trim.toFixed(2)}</span>
                                                            ) : (
                                                                <span style={tableStyles.emptyCell}>—</span>
                                                            )}
                                                        </td>

                                                        {/* Band */}
                                                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                            {quality.bonus_band ? (
                                                                <span
                                                                    style={{
                                                                        ...tableStyles.badge,
                                                                        ...(BAND_BADGE_STYLES[quality.bonus_band] || BAND_BADGE_STYLES['0%']),
                                                                    }}
                                                                >
                                                                    {quality.bonus_band}
                                                                </span>
                                                            ) : (
                                                                <span style={tableStyles.emptyCell}>—</span>
                                                            )}
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
                                <div className="d-flex justify-content-between align-items-center mt-4">
                                    <span className="text-muted">
                                        Mostrando {((pagination.page - 1) * pagination.perPage) + 1}-{Math.min(pagination.page * pagination.perPage, filteredProfessionals.length)} di {filteredProfessionals.length} professionisti
                                    </span>
                                    <nav>
                                        <ul className="pagination mb-0">
                                            <li className={`page-item ${pagination.page === 1 ? 'disabled' : ''}`}>
                                                <button
                                                    className="page-link"
                                                    onClick={() => handlePageChange(pagination.page - 1)}
                                                    disabled={pagination.page === 1}
                                                >
                                                    <i className="ri-arrow-left-s-line"></i>
                                                </button>
                                            </li>
                                            {[...Array(Math.min(5, totalPages))].map((_, i) => {
                                                let pageNum;
                                                if (totalPages <= 5) {
                                                    pageNum = i + 1;
                                                } else if (pagination.page <= 3) {
                                                    pageNum = i + 1;
                                                } else if (pagination.page >= totalPages - 2) {
                                                    pageNum = totalPages - 4 + i;
                                                } else {
                                                    pageNum = pagination.page - 2 + i;
                                                }
                                                return (
                                                    <li key={pageNum} className={`page-item ${pagination.page === pageNum ? 'active' : ''}`}>
                                                        <button
                                                            className="page-link"
                                                            onClick={() => handlePageChange(pageNum)}
                                                        >
                                                            {pageNum}
                                                        </button>
                                                    </li>
                                                );
                                            })}
                                            <li className={`page-item ${pagination.page === totalPages ? 'disabled' : ''}`}>
                                                <button
                                                    className="page-link"
                                                    onClick={() => handlePageChange(pagination.page + 1)}
                                                    disabled={pagination.page === totalPages}
                                                >
                                                    <i className="ri-arrow-right-s-line"></i>
                                                </button>
                                            </li>
                                        </ul>
                                    </nav>
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* QUARTERLY VIEW (Integrated) */}
            {viewMode === 'quarterly' && (
                <div className="quarterly-view fade-in">
                    {/* Quarterly Header */}
                    <div className="d-flex flex-wrap align-items-center justify-content-between mb-4">
                        <div>
                            <h5 className="mb-1">
                                <i className="ri-pie-chart-2-line me-2 text-primary"></i>
                                KPI Trimestrale & Super Malus
                            </h5>
                            <p className="text-muted mb-0 small">
                                Bonus composito: 60% Rinnovo Adj. + 40% Quality
                            </p>
                        </div>
                        <div className="d-flex gap-2 align-items-center">
                            <select
                                className="form-select form-select-sm"
                                value={quarter}
                                onChange={(e) => setQuarter(e.target.value)}
                                style={{ width: 'auto', borderRadius: '8px' }}
                            >
                                {quarters.map(q => (
                                    <option key={q} value={q}>{q}</option>
                                ))}
                            </select>
                            <button
                                className="btn btn-primary btn-sm"
                                onClick={handleCalculateQuarterly}
                                disabled={quarterlyCalculating}
                            >
                                {quarterlyCalculating ? (
                                    <>
                                        <span className="spinner-border spinner-border-sm me-1"></span>
                                        Calcolo...
                                    </>
                                ) : (
                                    <>
                                        <i className="ri-calculator-line me-1"></i>
                                        Calcola Trimestre
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Quarterly Error */}
                    {quarterlyError && (
                        <div className="alert alert-danger mb-4" style={{ borderRadius: '12px' }}>
                            <i className="ri-alert-line me-2"></i>
                            {quarterlyError}
                            <button className="btn btn-link btn-sm" onClick={fetchQuarterlySummary}>Riprova</button>
                        </div>
                    )}

                    {/* Calc Result Alert (Quarterly) */}
                    {quarterlyCalcResult && (
                        <div className={`alert ${quarterlyCalcResult.success ? 'alert-success' : 'alert-danger'} mb-4`} style={{ borderRadius: '12px' }}>
                            {quarterlyCalcResult.success ? (
                                <>
                                    <i className="ri-checkbox-circle-fill me-2"></i>
                                    Calcolo completato! Processati <strong>{quarterlyCalcResult.professionisti_processati}</strong> professionisti,
                                    <strong> {quarterlyCalcResult.super_malus_applicati}</strong> con Super Malus.
                                </>
                            ) : (
                                <>
                                    <i className="ri-error-warning-fill me-2"></i>
                                    Errore: {quarterlyCalcResult.error}
                                </>
                            )}
                            <button type="button" className="btn-close float-end" onClick={() => setQuarterlyCalcResult(null)}></button>
                        </div>
                    )}

                    {/* Quarterly Content */}
                    {quarterlyLoading ? (
                         <div className="text-center py-5">
                            <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}></div>
                            <p className="mt-3 text-muted">Caricamento KPI trimestrali...</p>
                        </div>
                    ) : quarterlySummary ? (
                        <>
                             {/* Summary Cards */}
                             <div className="row g-3 mb-4">
                                <div className="col-xl-3 col-sm-6">
                                    <div className="card" style={kpiCardStyles.card}>
                                        <div className="card-body">
                                            <div className="d-flex align-items-center justify-content-between mb-2">
                                                <span style={kpiCardStyles.kpiLabel}>Professionisti</span>
                                                <i className="ri-team-line text-primary fs-4"></i>
                                            </div>
                                            <div style={{ ...kpiCardStyles.kpiValue, color: '#3b82f6' }}>
                                                {quarterlySummary.total_professionisti || 0}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="col-xl-3 col-sm-6">
                                    <div className="card" style={kpiCardStyles.card}>
                                        <div className="card-body">
                                            <div className="d-flex align-items-center justify-content-between mb-2">
                                                <span style={kpiCardStyles.kpiLabel}>Con Super Malus</span>
                                                <i className="ri-alert-line text-danger fs-4"></i>
                                            </div>
                                            <div style={{ ...kpiCardStyles.kpiValue, color: '#ef4444' }}>
                                                {quarterlySummary.professionisti_con_malus || 0}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="col-xl-3 col-sm-6">
                                    <div className="card" style={kpiCardStyles.card}>
                                        <div className="card-body">
                                            <div className="d-flex align-items-center justify-content-between mb-2">
                                                <span style={kpiCardStyles.kpiLabel}>Bonus Totale Prima</span>
                                                <i className="ri-money-euro-circle-line text-success fs-4"></i>
                                            </div>
                                            <div style={{ ...kpiCardStyles.kpiValue, color: '#22c55e' }}>
                                                {(quarterlySummary.total_bonus_before_malus || 0).toFixed(0)}%
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="col-xl-3 col-sm-6">
                                    <div className="card" style={kpiCardStyles.card}>
                                        <div className="card-body">
                                            <div className="d-flex align-items-center justify-content-between mb-2">
                                                <span style={kpiCardStyles.kpiLabel}>Bonus Totale Dopo</span>
                                                <i className="ri-money-euro-box-line text-warning fs-4"></i>
                                            </div>
                                            <div style={{ ...kpiCardStyles.kpiValue, color: '#f59e0b' }}>
                                                {(quarterlySummary.total_bonus_after_malus || 0).toFixed(0)}%
                                            </div>
                                            {quarterlySummary.bonus_reduction_total > 0 && (
                                                <span className="text-danger small">
                                                    <i className="ri-arrow-down-line"></i>
                                                    -{quarterlySummary.bonus_reduction_total.toFixed(0)}%
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Super Malus Details Table */}
                            {quarterlySummary.malus_details && quarterlySummary.malus_details.length > 0 && (
                                <div className="card" style={{ ...kpiCardStyles.card }}>
                                    <div className="card-header bg-transparent border-0 py-3">
                                        <h6 className="mb-0">
                                            <i className="ri-error-warning-line text-danger me-2"></i>
                                            Professionisti con Super Malus ({quarterlySummary.malus_details.length})
                                        </h6>
                                    </div>
                                    <div className="table-responsive">
                                        <table className="table table-hover mb-0">
                                            <thead style={{ background: '#f8fafc' }}>
                                                <tr>
                                                    <th style={{ fontWeight: 600, fontSize: '12px', color: '#64748b' }}>Professionista</th>
                                                    <th className="text-center" style={{ fontWeight: 600, fontSize: '12px', color: '#64748b' }}>Quality</th>
                                                    <th className="text-center" style={{ fontWeight: 600, fontSize: '12px', color: '#64748b' }}>Rinnovo Adj</th>
                                                    <th className="text-center" style={{ fontWeight: 600, fontSize: '12px', color: '#64748b' }}>Bonus</th>
                                                    <th className="text-center" style={{ fontWeight: 600, fontSize: '12px', color: '#64748b' }}>Malus</th>
                                                    <th className="text-center" style={{ fontWeight: 600, fontSize: '12px', color: '#64748b' }}>Finale</th>
                                                    <th style={{ fontWeight: 600, fontSize: '12px', color: '#64748b' }}>Causa</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {quarterlySummary.malus_details.map((item, idx) => (
                                                    <tr key={idx}>
                                                        <td>
                                                            <Link 
                                                                to={`/team-dettaglio/${item.professionista_id}`}
                                                                className="text-primary fw-semibold text-decoration-none"
                                                            >
                                                                {item.professionista_name}
                                                            </Link>
                                                            <br/>
                                                            <small className="text-muted">{item.specialty}</small>
                                                        </td>
                                                        <td className="text-center">
                                                            {item.quality_trim !== null ? (
                                                                <span className="fw-semibold">{item.quality_trim?.toFixed(2)}</span>
                                                            ) : '—'}
                                                        </td>
                                                        <td className="text-center">
                                                            {item.rinnovo_adj_percentage !== null ? (
                                                                <span className="fw-semibold">{item.rinnovo_adj_percentage?.toFixed(1)}%</span>
                                                            ) : '—'}
                                                        </td>
                                                        <td className="text-center">
                                                            <span style={{ 
                                                                ...kpiCardStyles.badge,
                                                                ...getBandBadgeStyle(`${item.final_bonus_percentage?.toFixed(0)}%`)
                                                            }}>
                                                                {item.final_bonus_percentage?.toFixed(0)}%
                                                            </span>
                                                        </td>
                                                        <td className="text-center">
                                                            <span style={{ 
                                                                ...kpiCardStyles.badge,
                                                                ...getSuperMalusBadgeStyle(item.super_malus_percentage || 0)
                                                            }}>
                                                                -{item.super_malus_percentage}%
                                                            </span>
                                                        </td>
                                                        <td className="text-center">
                                                            <span className="fw-bold" style={{ color: '#22c55e' }}>
                                                                {item.final_bonus_after_malus?.toFixed(0)}%
                                                            </span>
                                                        </td>
                                                        <td>
                                                            <div className="d-flex gap-1">
                                                                {item.has_negative_review && (
                                                                    <span className="badge bg-danger-subtle text-danger">
                                                                        <i className="ri-star-line me-1"></i>Review ≤2
                                                                    </span>
                                                                )}
                                                                {item.has_refund && (
                                                                    <span className="badge bg-warning-subtle text-warning">
                                                                        <i className="ri-refund-line me-1"></i>Rimborso
                                                                    </span>
                                                                )}
                                                                {item.is_primary_for_malus && (
                                                                    <span className="badge bg-info-subtle text-info" title="Professionista primario">
                                                                        <i className="ri-user-star-line"></i>
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {/* Empty State (Quarterly) */}
                            {(!quarterlySummary.malus_details || quarterlySummary.malus_details.length === 0) && (
                                <div className="card text-center py-5" style={kpiCardStyles.card}>
                                    <div className="card-body">
                                        <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '4rem' }}></i>
                                        <h5 className="mt-3">Nessun Super Malus</h5>
                                        <p className="text-muted">
                                            Nessun professionista ha ricevuto penalità Super Malus in questo trimestre.
                                        </p>
                                    </div>
                                </div>
                            )}
                        </>
                    ) : null}
                </div>
            )}

            {/* Calculate Quality Modal (Weekly) */}
            {showCalcModal && (
                <div className="modal fade show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-dialog-centered">
                        <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
                            <div className="modal-header border-0 pb-0">
                                <h5 className="modal-title">
                                    <i className="ri-calculator-line me-2 text-primary"></i>
                                    Calcola Quality Score
                                </h5>
                                <button
                                    type="button"
                                    className="btn-close"
                                    onClick={closeCalcModal}
                                    disabled={calculating}
                                ></button>
                            </div>
                            <div className="modal-body p-4">
                                {!calcResult ? (
                                    <>
                                        {/* Specialty Selection */}
                                        <div className="mb-4">
                                            <label className="form-label fw-semibold">Specializzazione</label>
                                            <div className="d-flex gap-2 flex-wrap">
                                                {Object.entries(QUALITY_SPECIALTIES).map(([key, spec]) => (
                                                    <button
                                                        key={key}
                                                        type="button"
                                                        className={`btn ${calcSpecialty === key ? '' : 'btn-outline-secondary'}`}
                                                        onClick={() => setCalcSpecialty(key)}
                                                        disabled={calculating}
                                                        style={calcSpecialty === key ? {
                                                            backgroundColor: key === 'nutrizione' ? '#22c55e' : key === 'coach' ? '#f97316' : '#ec4899',
                                                            borderColor: 'transparent',
                                                            color: 'white',
                                                        } : {}}
                                                    >
                                                        <i className={`${spec.icon} me-1`}></i>
                                                        {spec.label}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Team Selection */}
                                        <div className="mb-4">
                                            <label className="form-label fw-semibold">Team (opzionale)</label>
                                            <select
                                                className="form-select"
                                                value={calcTeam}
                                                onChange={(e) => setCalcTeam(e.target.value)}
                                                disabled={calculating || calcTeamsLoading}
                                            >
                                                <option value="">
                                                    {calcTeamsLoading ? 'Caricamento...' : 'Tutti i Team'}
                                                </option>
                                                {calcTeams.map(team => (
                                                    <option key={team.id} value={team.id}>{team.name}</option>
                                                ))}
                                            </select>
                                        </div>

                                        {/* Week Selection */}
                                        <div className="mb-4">
                                            <label className="form-label fw-semibold">Settimana</label>
                                            <div className="d-flex align-items-center gap-2">
                                                <button
                                                    type="button"
                                                    className="btn btn-outline-secondary"
                                                    onClick={() => navigateCalcWeek(-1)}
                                                    disabled={calculating}
                                                >
                                                    <i className="ri-arrow-left-s-line"></i>
                                                </button>
                                                <div className="flex-grow-1 text-center py-2 px-3 bg-light rounded">
                                                    <span className="fw-medium">
                                                        {formatDateForDisplay(calcWeekStart.start)}
                                                    </span>
                                                </div>
                                                <button
                                                    type="button"
                                                    className="btn btn-outline-secondary"
                                                    onClick={() => navigateCalcWeek(1)}
                                                    disabled={calculating}
                                                >
                                                    <i className="ri-arrow-right-s-line"></i>
                                                </button>
                                            </div>
                                        </div>

                                        {/* Action Buttons */}
                                        <div className="d-grid gap-2">
                                            <button
                                                className="btn btn-primary py-2"
                                                onClick={handleCalculateQuality}
                                                disabled={calculating}
                                                style={{ borderRadius: '10px' }}
                                            >
                                                {calculating ? (
                                                    <>
                                                        <span className="spinner-border spinner-border-sm me-2"></span>
                                                        Calcolo in corso...
                                                    </>
                                                ) : (
                                                    <>
                                                        <i className="ri-calculator-fill me-2"></i>
                                                        Avvia Calcolo
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    </>
                                ) : (
                                    <div className="text-center py-4">
                                        <div className="mb-3">
                                            {calcResult.success ? (
                                                <i className="ri-checkbox-circle-fill text-success" style={{ fontSize: '4rem' }}></i>
                                            ) : (
                                                <i className="ri-error-warning-fill text-danger" style={{ fontSize: '4rem' }}></i>
                                            )}
                                        </div>
                                        <h5 className="mb-2">{calcResult.success ? 'Calcolo Completato' : 'Errore nel Calcolo'}</h5>
                                        <p className="text-muted mb-4">
                                            {calcResult.success
                                                ? `Il calcolo è stato completato con successo per ${calcResult.processed_count || 0} professionisti.`
                                                : calcResult.error}
                                        </p>
                                        <button
                                            className="btn btn-outline-primary"
                                            onClick={closeCalcModal}
                                            style={{ borderRadius: '10px', minWidth: '120px' }}
                                        >
                                            Chiudi
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Quality;

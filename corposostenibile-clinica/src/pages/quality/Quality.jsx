import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import teamService, {
    SPECIALTY_COLORS,
    TEAM_TYPE_LABELS,
    TEAM_TYPE_ICONS,
} from '../../services/teamService';

// Stili per la tabella professionale (come in ClientiList)
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

// Band badge styles
const BAND_BADGE_STYLES = {
    '100%': { background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff' },
    '60%': { background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', color: '#fff' },
    '30%': { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: '#fff' },
    '0%': { background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)', color: '#fff' },
};

// Miss rate badge styles
const getMissRateBadgeStyle = (rate) => {
    if (rate > 0.2) return { background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', color: '#fff' };
    if (rate > 0.1) return { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: '#fff' };
    return { background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff' };
};

// Specialty configuration
const SPECIALTIES = {
    nutrizione: {
        label: 'Nutrizione',
        icon: 'ri-leaf-line',
        color: 'success',
        gradient: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
        filterValues: 'nutrizione,nutrizionista'
    },
    coach: {
        label: 'Coach',
        icon: 'ri-run-line',
        color: 'warning',
        gradient: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
        filterValues: 'coach'
    },
    psicologia: {
        label: 'Psicologia',
        icon: 'ri-mental-health-line',
        color: 'info',
        gradient: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
        filterValues: 'psicologia,psicologo'
    }
};

// Generate mock quality data for a professional
const generateMockQualityData = (profId) => {
    const seed = profId * 7; // Use profId as seed for consistent random data
    const random = (min, max) => min + ((seed * 13 + max) % (max - min + 1));

    const nClientsEligible = random(3, 25);
    const nChecksDone = Math.min(nClientsEligible, random(1, nClientsEligible));
    const missRate = nClientsEligible > 0 ? ((nClientsEligible - nChecksDone) / nClientsEligible) : 0;

    const qualityRaw = 7 + (Math.random() * 3);
    const qualityFinal = qualityRaw - (missRate * 2);
    const qualityTrim = Math.max(0, Math.min(10, qualityFinal));

    let bonusBand = '0%';
    if (qualityTrim >= 9.5) bonusBand = '100%';
    else if (qualityTrim >= 8.5) bonusBand = '60%';
    else if (qualityTrim >= 7.5) bonusBand = '30%';

    return {
        n_clients_eligible: nClientsEligible,
        n_checks_done: nChecksDone,
        miss_rate: missRate,
        quality_raw: qualityRaw,
        quality_final: qualityFinal,
        quality_trim: qualityTrim,
        bonus_band: bonusBand
    };
};

// Get week dates
const getWeekDates = (date = new Date()) => {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(d.setDate(diff));
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    return { start: monday, end: sunday };
};

const formatDate = (date) => {
    return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

function Quality() {
    const [specialty, setSpecialty] = useState('nutrizione');
    const [professionals, setProfessionals] = useState([]);
    const [qualityData, setQualityData] = useState({});
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [teams, setTeams] = useState([]);
    const [selectedTeam, setSelectedTeam] = useState('');
    const [currentWeek, setCurrentWeek] = useState(getWeekDates());
    const [hoveredRow, setHoveredRow] = useState(null);

    // Fetch professionals based on specialty
    const fetchProfessionals = useCallback(async () => {
        setLoading(true);
        try {
            const specConfig = SPECIALTIES[specialty];
            const params = {
                specialty: specConfig.filterValues,
                active: '1',
                per_page: 100
            };

            const data = await teamService.getTeamMembers(params);
            const profs = data.members || [];
            setProfessionals(profs);

            // Generate mock quality data for each professional
            const mockData = {};
            profs.forEach(prof => {
                mockData[prof.id] = generateMockQualityData(prof.id);
            });
            setQualityData(mockData);

        } catch (err) {
            console.error('Error fetching professionals:', err);
            setProfessionals([]);
        } finally {
            setLoading(false);
        }
    }, [specialty]);

    // Fetch teams for filter
    const fetchTeams = useCallback(async () => {
        try {
            const data = await teamService.getTeams({ team_type: specialty, active: '1' });
            setTeams(data.teams || []);
        } catch (err) {
            console.error('Error fetching teams:', err);
            setTeams([]);
        }
    }, [specialty]);

    useEffect(() => {
        fetchProfessionals();
        fetchTeams();
        setSelectedTeam('');
    }, [fetchProfessionals, fetchTeams]);

    // Navigate weeks
    const navigateWeek = (direction) => {
        const newDate = new Date(currentWeek.start);
        newDate.setDate(newDate.getDate() + (direction * 7));
        setCurrentWeek(getWeekDates(newDate));
    };

    // Filter professionals
    const filteredProfessionals = professionals.filter(prof => {
        const matchesSearch = !searchTerm ||
            `${prof.first_name} ${prof.last_name}`.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesTeam = !selectedTeam ||
            prof.teams?.some(t => t.id === parseInt(selectedTeam));
        return matchesSearch && matchesTeam;
    });

    // Calculate stats
    const stats = {
        total_professionisti: filteredProfessionals.length,
        with_score: filteredProfessionals.filter(p => qualityData[p.id]?.quality_final).length,
        avg_quality: filteredProfessionals.length > 0
            ? (filteredProfessionals.reduce((sum, p) => sum + (qualityData[p.id]?.quality_final || 0), 0) / filteredProfessionals.length).toFixed(1)
            : '-',
        total_eligible: filteredProfessionals.reduce((sum, p) => sum + (qualityData[p.id]?.n_clients_eligible || 0), 0),
        total_checks: filteredProfessionals.reduce((sum, p) => sum + (qualityData[p.id]?.n_checks_done || 0), 0),
        avg_miss_rate: filteredProfessionals.length > 0
            ? (filteredProfessionals.reduce((sum, p) => sum + (qualityData[p.id]?.miss_rate || 0), 0) / filteredProfessionals.length * 100).toFixed(1)
            : '-'
    };

    const getInitials = (firstName, lastName) => {
        return `${firstName?.[0] || ''}${lastName?.[0] || ''}`.toUpperCase();
    };

    const getScoreStyle = (score) => {
        if (score >= 9) return { color: '#22c55e', fontWeight: 700 };
        if (score >= 8) return { color: '#3b82f6', fontWeight: 700 };
        return { color: '#ef4444', fontWeight: 700 };
    };

    // Get row background based on band
    const getRowBandStyle = (band, isHovered) => {
        const baseStyle = { ...tableStyles.row };
        if (isHovered) {
            baseStyle.background = '#f8fafc';
        } else {
            switch (band) {
                case '100%': baseStyle.background = '#f0fdf4'; baseStyle.borderLeft = '3px solid #22c55e'; break;
                case '60%': baseStyle.background = '#eff6ff'; baseStyle.borderLeft = '3px solid #3b82f6'; break;
                case '30%': baseStyle.background = '#fffbeb'; baseStyle.borderLeft = '3px solid #f59e0b'; break;
                default: baseStyle.borderLeft = '3px solid #94a3b8'; break;
            }
        }
        return baseStyle;
    };

    const specConfig = SPECIALTIES[specialty];

    return (
        <>
            {/* Custom Styles for filter badges */}
            <style>{`
                .filter-badge {
                    padding: 0.5rem 1rem;
                    border-radius: 20px;
                    font-size: 0.875rem;
                    font-weight: 500;
                    background: #edf2f7;
                    color: #4a5568;
                    border: 1px solid transparent;
                    cursor: pointer;
                    transition: all 0.2s;
                    text-decoration: none;
                }
                .filter-badge:hover {
                    background: #e2e8f0;
                }
                .filter-badge.active {
                    background: var(--active-color, #48bb78);
                    color: white;
                    border-color: var(--active-border, #38a169);
                }
            `}</style>

            {/* Page Header */}
            <div className="d-flex flex-wrap align-items-center justify-content-between mb-4">
                <div>
                    <h4 className="mb-1">Quality Score</h4>
                    <p className="text-muted mb-0">{filteredProfessionals.length} professionisti {specConfig.label}</p>
                </div>
            </div>

            {/* Week Navigation & Filters */}
            <div className="card mb-4">
                <div className="card-body">
                    <div className="row g-3 align-items-center">
                        <div className="col-md-6">
                            <div className="d-flex align-items-center gap-3">
                                <button
                                    className={`btn btn-outline-${specConfig.color} btn-sm`}
                                    onClick={() => navigateWeek(-1)}
                                >
                                    <i className="ri-arrow-left-s-line"></i>
                                </button>
                                <div className="text-center">
                                    <h5 className="mb-0 fw-semibold">
                                        {formatDate(currentWeek.start)} - {formatDate(currentWeek.end)}
                                    </h5>
                                    <small className="text-muted">
                                        Settimana {Math.ceil((currentWeek.start.getDate() + new Date(currentWeek.start.getFullYear(), currentWeek.start.getMonth(), 1).getDay()) / 7)}
                                    </small>
                                </div>
                                <button
                                    className={`btn btn-outline-${specConfig.color} btn-sm`}
                                    onClick={() => navigateWeek(1)}
                                >
                                    <i className="ri-arrow-right-s-line"></i>
                                </button>
                            </div>
                        </div>
                        <div className="col-md-6">
                            <div className="d-flex justify-content-end gap-2">
                                <select
                                    className="form-select form-select-sm"
                                    style={{ width: 'auto' }}
                                    value={selectedTeam}
                                    onChange={(e) => setSelectedTeam(e.target.value)}
                                >
                                    <option value="">Tutti i Team</option>
                                    {teams.map(team => (
                                        <option key={team.id} value={team.id}>{team.name}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* Quick filters */}
                    <div className="mt-3 d-flex gap-2 flex-wrap">
                        <span className="text-muted me-2 align-self-center">Specializzazione:</span>
                        {Object.entries(SPECIALTIES).map(([key, spec]) => (
                            <button
                                key={key}
                                className={`filter-badge ${specialty === key ? 'active' : ''}`}
                                onClick={() => setSpecialty(key)}
                                style={{
                                    '--active-color': key === 'nutrizione' ? '#22c55e' : key === 'coach' ? '#f97316' : '#ec4899',
                                    '--active-border': key === 'nutrizione' ? '#16a34a' : key === 'coach' ? '#ea580c' : '#db2777'
                                }}
                            >
                                <i className={`${spec.icon} me-1`}></i>
                                {spec.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="row g-3 mb-4">
                {[
                    { label: 'Media Quality', value: stats.avg_quality, icon: 'ri-star-line', gradient: specConfig.gradient },
                    { label: 'Clienti Elegg.', value: stats.total_eligible, icon: 'ri-group-line', gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' },
                    { label: 'Check Fatti', value: stats.total_checks, icon: 'ri-checkbox-circle-line', gradient: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)' },
                    { label: 'Miss Rate', value: `${stats.avg_miss_rate}%`, icon: 'ri-percent-line', gradient: parseFloat(stats.avg_miss_rate) > 20 ? 'linear-gradient(135deg, #eb3349 0%, #f45c43 100%)' : 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)' },
                ].map((stat, idx) => (
                    <div key={idx} className="col-xl-3 col-md-6 col-sm-6">
                        <div
                            className="card border-0 shadow-sm"
                            style={{ background: stat.gradient }}
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

            {/* Professionals Table */}
            <div className="card border-0" style={tableStyles.card}>
                <div
                    className="card-header d-flex justify-content-between align-items-center"
                    style={{
                        background: '#fff',
                        borderBottom: '1px solid #e2e8f0',
                        padding: '16px 20px',
                    }}
                >
                    <h6 className="mb-0" style={{ fontWeight: 600, color: '#1e293b' }}>
                        <i className="ri-list-check me-2" style={{ color: '#64748b' }}></i>
                        Professionisti {specConfig.label} ({filteredProfessionals.length})
                    </h6>
                    <div className="d-flex gap-3 align-items-center">
                        <div className="position-relative">
                            <i
                                className="ri-search-line position-absolute"
                                style={{
                                    left: '14px',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    color: '#94a3b8',
                                    fontSize: '16px',
                                }}
                            ></i>
                            <input
                                type="text"
                                className="form-control"
                                placeholder="Cerca professionista..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                style={{
                                    width: '220px',
                                    paddingLeft: '40px',
                                    height: '40px',
                                    borderRadius: '10px',
                                    border: '1px solid #e2e8f0',
                                    background: '#f8fafc',
                                    fontSize: '14px',
                                }}
                            />
                        </div>
                    </div>
                </div>

                {loading ? (
                    <div className="text-center py-5">
                        <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}></div>
                        <p className="mt-3 text-muted">Caricamento professionisti...</p>
                    </div>
                ) : filteredProfessionals.length === 0 ? (
                    <div className="card-body text-center py-5">
                        <div className="mb-4">
                            <i className="ri-user-search-line" style={{ fontSize: '5rem', color: '#cbd5e1' }}></i>
                        </div>
                        <h5 style={{ color: '#475569' }}>Nessun professionista trovato</h5>
                        <p className="text-muted mb-0">Non ci sono professionisti attivi per questa specializzazione</p>
                    </div>
                ) : (
                    <div className="table-responsive">
                        <table className="table mb-0">
                            <thead style={tableStyles.tableHeader}>
                                <tr>
                                    <th style={{ ...tableStyles.th, minWidth: '200px' }}>Professionista</th>
                                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '80px' }}>Clienti</th>
                                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '80px' }}>Check</th>
                                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '100px' }}>Miss Rate</th>
                                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '90px' }}>Q. Raw</th>
                                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '90px' }}>Q. Final</th>
                                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '90px' }}>Q. Trim</th>
                                    <th style={{ ...tableStyles.th, textAlign: 'center', minWidth: '80px' }}>Band</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredProfessionals.map((prof, index) => {
                                    const score = qualityData[prof.id] || {};
                                    const isHovered = hoveredRow === index;
                                    return (
                                        <tr
                                            key={prof.id}
                                            style={getRowBandStyle(score.bonus_band, isHovered)}
                                            onMouseEnter={() => setHoveredRow(index)}
                                            onMouseLeave={() => setHoveredRow(null)}
                                        >
                                            {/* Professionista */}
                                            <td style={tableStyles.td}>
                                                <div className="d-flex align-items-center gap-3">
                                                    {prof.avatar_url ? (
                                                        <img
                                                            src={prof.avatar_url}
                                                            alt={prof.full_name}
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
                                                {score.n_clients_eligible ? (
                                                    <span style={{ color: '#3b82f6', fontWeight: 600 }}>
                                                        {score.n_clients_eligible}
                                                    </span>
                                                ) : (
                                                    <span style={tableStyles.emptyCell}>—</span>
                                                )}
                                            </td>

                                            {/* Check */}
                                            <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                {score.n_checks_done ? (
                                                    <span style={{ color: '#22c55e', fontWeight: 600 }}>
                                                        {score.n_checks_done}
                                                    </span>
                                                ) : (
                                                    <span style={tableStyles.emptyCell}>—</span>
                                                )}
                                            </td>

                                            {/* Miss Rate */}
                                            <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                {score.miss_rate !== undefined ? (
                                                    <span
                                                        style={{
                                                            ...tableStyles.badge,
                                                            ...getMissRateBadgeStyle(score.miss_rate),
                                                        }}
                                                    >
                                                        {(score.miss_rate * 100).toFixed(1)}%
                                                    </span>
                                                ) : (
                                                    <span style={tableStyles.emptyCell}>—</span>
                                                )}
                                            </td>

                                            {/* Q. Raw */}
                                            <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                {score.quality_raw ? (
                                                    <span style={{ fontWeight: 500 }}>{score.quality_raw.toFixed(2)}</span>
                                                ) : (
                                                    <span style={tableStyles.emptyCell}>—</span>
                                                )}
                                            </td>

                                            {/* Q. Final */}
                                            <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                {score.quality_final ? (
                                                    <span style={getScoreStyle(score.quality_final)}>
                                                        {score.quality_final.toFixed(2)}
                                                    </span>
                                                ) : (
                                                    <span style={tableStyles.emptyCell}>—</span>
                                                )}
                                            </td>

                                            {/* Q. Trim */}
                                            <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                {score.quality_trim ? (
                                                    <span style={{ fontWeight: 500 }}>{score.quality_trim.toFixed(2)}</span>
                                                ) : (
                                                    <span style={tableStyles.emptyCell}>—</span>
                                                )}
                                            </td>

                                            {/* Band */}
                                            <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                                                {score.bonus_band ? (
                                                    <span
                                                        style={{
                                                            ...tableStyles.badge,
                                                            ...(BAND_BADGE_STYLES[score.bonus_band] || BAND_BADGE_STYLES['0%']),
                                                        }}
                                                    >
                                                        {score.bonus_band}
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
                )}
            </div>
        </>
    );
}

export default Quality;

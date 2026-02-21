import React from 'react';
import { SkeletonCard } from './DashboardShared';

export const SPECIALTY_CONFIG = {
    nutrizione: { label: 'Nutrizione (TL)', color: '#06b6d4', bg: '#ecfeff' },
    nutrizionista: { label: 'Nutrizionisti', color: '#0891b2', bg: '#cffafe' },
    psicologia: { label: 'Psicologia (TL)', color: '#a855f7', bg: '#faf5ff' },
    psicologo: { label: 'Psicologi', color: '#9333ea', bg: '#f3e8ff' },
    coach: { label: 'Coach', color: '#22c55e', bg: '#f0fdf4' },
    amministrazione: { label: 'Amministrazione', color: '#ef4444', bg: '#fef2f2' },
    cco: { label: 'CCO', color: '#f97316', bg: '#fff7ed' },
};

export const ROLE_CONFIG_TAB = {
    admin: { label: 'Admin', color: '#ef4444', bg: '#fef2f2' },
    team_leader: { label: 'Team Leader', color: '#8b5cf6', bg: '#f5f3ff' },
    professionista: { label: 'Professionista', color: '#22c55e', bg: '#f0fdf4' },
    team_esterno: { label: 'Team Esterno', color: '#64748b', bg: '#f8fafc' },
};

export default function ProfessionistiDashboard({ data, loading, error, onRetry }) {
    if (error) {
        return (
            <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                <div className="card-body text-center py-5">
                    <i className="ri-error-warning-line text-danger" style={{ fontSize: '48px', opacity: 0.6 }}></i>
                    <h5 className="text-muted mt-3">{error}</h5>
                    <p className="text-muted small">Assicurati che il backend sia avviato e riprova.</p>
                    <button className="btn btn-primary btn-sm" style={{ borderRadius: '8px' }} onClick={onRetry}>
                        <i className="ri-refresh-line me-1"></i> Riprova
                    </button>
                </div>
            </div>
        );
    }

    if (loading || !data) {
        return (
            <div className="row g-3">
                <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
                <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
                <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
                <div className="col-xl-3 col-sm-6"><SkeletonCard height="110px" /></div>
                <div className="col-lg-8"><SkeletonCard height="300px" /></div>
                <div className="col-lg-4"><SkeletonCard height="300px" /></div>
                <div className="col-lg-6"><SkeletonCard height="280px" /></div>
                <div className="col-lg-6"><SkeletonCard height="280px" /></div>
            </div>
        );
    }

    const { kpi, specialtyDistribution, roleDistribution, qualitySummary, topPerformers, trialUsers, qualityTrend, teamsSummary, clientLoad } = data;

    // Specialty distribution total for percentage calc
    const totalSpecialty = Object.values(specialtyDistribution || {}).reduce((a, v) => a + (v.count || 0), 0) || 1;
    const totalBonusBands = Object.values(qualitySummary?.bonusBands || {}).reduce((a, b) => a + b, 0) || 1;

    const getQualityColor = (val) => {
        if (!val) return '#94a3b8';
        if (val >= 8.5) return '#22c55e';
        if (val >= 7) return '#3b82f6';
        if (val >= 5.5) return '#f59e0b';
        return '#ef4444';
    };

    const getTrendIcon = (trend) => {
        if (trend === 'up') return { icon: 'ri-arrow-up-line', color: '#22c55e' };
        if (trend === 'down') return { icon: 'ri-arrow-down-line', color: '#ef4444' };
        return { icon: 'ri-subtract-line', color: '#94a3b8' };
    };

    return (
        <>
            {/* KPI Cards */}
            <div className="row g-3 mb-4">
                {[
                    { label: 'Totale Team', value: kpi.totalAll, icon: 'ri-team-line', bg: '#3b82f6', subtitle: `${kpi.totalActive} attivi` },
                    { label: 'Professionisti', value: kpi.totalProfessionisti, icon: 'ri-user-star-line', bg: '#22c55e', subtitle: `${kpi.totalTeamLeaders} team leaders` },
                    { label: 'In Prova', value: kpi.totalTrial, icon: 'ri-user-follow-line', bg: '#f59e0b', subtitle: 'Professionisti trial' },
                    { label: 'Quality Media', value: qualitySummary.avgQuality ? qualitySummary.avgQuality.toFixed(1) : 'N/D', icon: 'ri-bar-chart-grouped-line', bg: '#8b5cf6', subtitle: qualitySummary.avgMonth ? `Mese: ${qualitySummary.avgMonth.toFixed(1)}` : 'Nessun dato' },
                ].map((stat, idx) => (
                    <div key={idx} className="col-xl-3 col-sm-6">
                        <div className="card border-0 shadow-sm" style={{ backgroundColor: stat.bg, borderRadius: '16px' }}>
                            <div className="card-body py-3">
                                <div className="d-flex align-items-center justify-content-between">
                                    <div>
                                        <h3 className="text-white mb-0 fw-bold">{stat.value}</h3>
                                        <span className="text-white opacity-75 small">{stat.label}</span>
                                        {stat.subtitle && <div className="text-white opacity-50" style={{ fontSize: '11px', marginTop: '2px' }}>{stat.subtitle}</div>}
                                    </div>
                                    <div className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center" style={{ width: '48px', height: '48px' }}>
                                        <i className={`${stat.icon} text-white fs-4`}></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Row 2: Quality Trend + Specialty Distribution */}
            <div className="row g-3 mb-4">
                {/* Quality Weekly Trend */}
                <div className="col-lg-8">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-line-chart-line me-2 text-primary"></i>
                                Quality Score Settimanale (ultime 8 settimane)
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            {(qualityTrend || []).length > 0 ? (
                                <div className="d-flex align-items-end justify-content-between gap-2" style={{ height: '200px' }}>
                                    {qualityTrend.map((w, idx) => (
                                        <div key={idx} className="d-flex flex-column align-items-center flex-fill">
                                            <div className="d-flex flex-column align-items-center justify-content-end" style={{ height: '160px', width: '100%' }}>
                                                <div
                                                    style={{
                                                        width: '65%',
                                                        maxWidth: '45px',
                                                        height: `${Math.max((w.avgQuality / 10) * 140, 8)}px`,
                                                        background: `linear-gradient(180deg, ${getQualityColor(w.avgQuality)} 0%, ${getQualityColor(w.avgQuality)}cc 100%)`,
                                                        borderRadius: '6px 6px 0 0',
                                                        transition: 'height 0.3s ease',
                                                    }}
                                                    title={`Media: ${w.avgQuality} - ${w.count} professionisti`}
                                                ></div>
                                            </div>
                                            <div className="text-center mt-2">
                                                <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 500 }}>
                                                    {w.week ? new Date(w.week).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' }) : ''}
                                                </span>
                                                <div style={{ fontSize: '12px', fontWeight: 700, color: getQualityColor(w.avgQuality) }}>{w.avgQuality}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-4">
                                    <i className="ri-bar-chart-line text-muted" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                                    <p className="text-muted small mb-0 mt-2">Nessun dato quality disponibile</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Specialty Distribution */}
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-pie-chart-line me-2 text-info"></i>
                                Per Specializzazione
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            <div className="d-flex flex-column gap-2">
                                {Object.entries(specialtyDistribution || {}).sort((a, b) => b[1].count - a[1].count).map(([key, val]) => {
                                    const config = SPECIALTY_CONFIG[key] || { label: key, color: '#64748b', bg: '#f1f5f9' };
                                    const pct = Math.round((val.count / totalSpecialty) * 100);
                                    return (
                                        <div key={key}>
                                            <div className="d-flex align-items-center justify-content-between mb-1">
                                                <span style={{ fontSize: '12px', fontWeight: 500, color: '#334155' }}>{config.label}</span>
                                                <span style={{ fontSize: '12px', fontWeight: 700, color: config.color }}>{val.count}</span>
                                            </div>
                                            <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9' }}>
                                                <div style={{ height: '100%', width: `${pct}%`, borderRadius: '3px', background: config.color, transition: 'width 0.3s ease' }}></div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Row 3: Client Load + Bonus Bands + Role Distribution */}
            <div className="row g-3 mb-4">
                {/* Client Load per Area */}
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-scales-line me-2 text-warning"></i>
                                Carico Clienti
                            </h6>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>Media clienti per professionista</span>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            {[
                                { key: 'nutrizione', label: 'Nutrizione', icon: 'ri-restaurant-line', color: '#06b6d4' },
                                { key: 'coach', label: 'Coach', icon: 'ri-run-line', color: '#22c55e' },
                                { key: 'psicologia', label: 'Psicologia', icon: 'ri-mental-health-line', color: '#8b5cf6' },
                            ].map((area) => {
                                const load = clientLoad?.[area.key] || { clients: 0, professionals: 0, avgLoad: 0 };
                                return (
                                    <div key={area.key} className="d-flex align-items-center justify-content-between py-2 border-bottom" style={{ borderColor: '#f1f5f9 !important' }}>
                                        <div className="d-flex align-items-center gap-2">
                                            <div className="d-flex align-items-center justify-content-center" style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${area.color}15` }}>
                                                <i className={area.icon} style={{ fontSize: '14px', color: area.color }}></i>
                                            </div>
                                            <div>
                                                <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{area.label}</span>
                                                <div style={{ fontSize: '11px', color: '#94a3b8' }}>{load.professionals} prof. / {load.clients} clienti</div>
                                            </div>
                                        </div>
                                        <div className="text-end">
                                            <span style={{ fontSize: '18px', fontWeight: 700, color: area.color }}>{load.avgLoad}</span>
                                            <div style={{ fontSize: '10px', color: '#94a3b8' }}>media</div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Bonus Bands Distribution */}
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-award-line me-2 text-success"></i>
                                Bonus Bands
                            </h6>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>Distribuzione ultima settimana</span>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            {[
                                { band: '100%', label: 'Eccellente (100%)', color: '#22c55e', bg: '#dcfce7' },
                                { band: '60%', label: 'Buono (60%)', color: '#3b82f6', bg: '#dbeafe' },
                                { band: '30%', label: 'Sufficiente (30%)', color: '#f59e0b', bg: '#fef3c7' },
                                { band: '0%', label: 'Insufficiente (0%)', color: '#ef4444', bg: '#fee2e2' },
                            ].map((b) => {
                                const count = qualitySummary?.bonusBands?.[b.band] || 0;
                                const pct = Math.round((count / totalBonusBands) * 100);
                                return (
                                    <div key={b.band} className="mb-3">
                                        <div className="d-flex align-items-center justify-content-between mb-1">
                                            <div className="d-flex align-items-center gap-2">
                                                <span className="badge" style={{ background: b.bg, color: b.color, fontSize: '11px', padding: '3px 8px', borderRadius: '6px' }}>{b.band}</span>
                                                <span style={{ fontSize: '12px', color: '#64748b' }}>{b.label}</span>
                                            </div>
                                            <span style={{ fontSize: '13px', fontWeight: 700, color: b.color }}>{count}</span>
                                        </div>
                                        <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9' }}>
                                            <div style={{ height: '100%', width: `${pct}%`, borderRadius: '3px', background: b.color, transition: 'width 0.3s ease' }}></div>
                                        </div>
                                    </div>
                                );
                            })}
                            <div className="d-flex gap-3 mt-3 pt-2 border-top">
                                <div className="text-center flex-fill">
                                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#22c55e' }}>{qualitySummary?.trendUp || 0}</div>
                                    <div style={{ fontSize: '11px', color: '#94a3b8' }}><i className="ri-arrow-up-line"></i> In crescita</div>
                                </div>
                                <div className="text-center flex-fill">
                                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#94a3b8' }}>{qualitySummary?.trendStable || 0}</div>
                                    <div style={{ fontSize: '11px', color: '#94a3b8' }}><i className="ri-subtract-line"></i> Stabili</div>
                                </div>
                                <div className="text-center flex-fill">
                                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#ef4444' }}>{qualitySummary?.trendDown || 0}</div>
                                    <div style={{ fontSize: '11px', color: '#94a3b8' }}><i className="ri-arrow-down-line"></i> In calo</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Role Distribution */}
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-user-settings-line me-2 text-danger"></i>
                                Per Ruolo
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            <div className="d-flex flex-column gap-3">
                                {Object.entries(roleDistribution || {}).sort((a, b) => b[1].count - a[1].count).map(([key, val]) => {
                                    const config = ROLE_CONFIG_TAB[key] || { label: key, color: '#64748b', bg: '#f1f5f9' };
                                    return (
                                        <div key={key} className="d-flex align-items-center justify-content-between">
                                            <div className="d-flex align-items-center gap-2">
                                                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: config.color }}></div>
                                                <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{config.label}</span>
                                            </div>
                                            <div className="d-flex align-items-center gap-2">
                                                <span style={{ fontSize: '15px', fontWeight: 700, color: config.color }}>{val.count}</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                            <div className="mt-3 pt-3 border-top d-flex align-items-center justify-content-between">
                                <span style={{ fontSize: '12px', color: '#94a3b8' }}>Inattivi</span>
                                <span style={{ fontSize: '14px', fontWeight: 600, color: '#94a3b8' }}>{kpi.totalInactive}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Row 4: Top Performers + Teams */}
            <div className="row g-3 mb-4">
                {/* Top Performers */}
                <div className="col-lg-7">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-trophy-line me-2 text-warning"></i>
                                Top Performers
                            </h6>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>Per quality score settimana corrente</span>
                        </div>
                        {(topPerformers || []).length > 0 ? (
                            <div className="table-responsive">
                                <table className="table table-hover mb-0" style={{ fontSize: '13px' }}>
                                    <thead>
                                        <tr style={{ borderBottom: '2px solid #f1f5f9' }}>
                                            <th className="border-0 py-2 px-4 text-muted" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>#</th>
                                            <th className="border-0 py-2 text-muted" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Professionista</th>
                                            <th className="border-0 py-2 text-muted" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Specializzazione</th>
                                            <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Score</th>
                                            <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Mese</th>
                                            <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Banda</th>
                                            <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Trend</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {topPerformers.slice(0, 8).map((p, idx) => {
                                            const specConfig = SPECIALTY_CONFIG[p.specialty] || { label: p.specialty || '-', color: '#64748b' };
                                            const trendInfo = getTrendIcon(p.trend);
                                            return (
                                                <tr key={p.id}>
                                                    <td className="py-2 px-4" style={{ fontWeight: 700, color: idx < 3 ? '#f59e0b' : '#94a3b8' }}>{idx + 1}</td>
                                                    <td className="py-2">
                                                        <span style={{ fontWeight: 500, color: '#1e293b' }}>{p.name}</span>
                                                    </td>
                                                    <td className="py-2">
                                                        <span className="badge" style={{ background: `${specConfig.color}15`, color: specConfig.color, fontSize: '11px', padding: '3px 8px', borderRadius: '6px' }}>
                                                            {specConfig.label}
                                                        </span>
                                                    </td>
                                                    <td className="py-2 text-center">
                                                        <span style={{ fontWeight: 700, color: getQualityColor(p.quality_final) }}>{p.quality_final}</span>
                                                    </td>
                                                    <td className="py-2 text-center">
                                                        <span style={{ fontWeight: 500, color: '#64748b' }}>{p.quality_month || '-'}</span>
                                                    </td>
                                                    <td className="py-2 text-center">
                                                        <span className="badge" style={{
                                                            background: p.bonus_band === '100%' ? '#dcfce7' : p.bonus_band === '60%' ? '#dbeafe' : p.bonus_band === '30%' ? '#fef3c7' : '#fee2e2',
                                                            color: p.bonus_band === '100%' ? '#166534' : p.bonus_band === '60%' ? '#1e40af' : p.bonus_band === '30%' ? '#92400e' : '#991b1b',
                                                            fontSize: '11px', padding: '3px 8px', borderRadius: '6px'
                                                        }}>
                                                            {p.bonus_band || '-'}
                                                        </span>
                                                    </td>
                                                    <td className="py-2 text-center">
                                                        <i className={trendInfo.icon} style={{ color: trendInfo.color, fontSize: '16px' }}></i>
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <div className="card-body text-center py-4">
                                <i className="ri-trophy-line text-muted" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                                <p className="text-muted small mb-0 mt-2">Nessun dato quality disponibile</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Teams Summary */}
                <div className="col-lg-5">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-organization-chart me-2 text-info"></i>
                                Teams Attivi
                            </h6>
                        </div>
                        <div className="card-body p-0">
                            {(teamsSummary || []).length > 0 ? (
                                <div className="list-group list-group-flush">
                                    {teamsSummary.map((team) => {
                                        const typeColors = { nutrizione: '#06b6d4', coach: '#22c55e', psicologia: '#8b5cf6' };
                                        const typeIcons = { nutrizione: 'ri-heart-pulse-line', coach: 'ri-run-line', psicologia: 'ri-mental-health-line' };
                                        const color = typeColors[team.team_type] || '#64748b';
                                        const icon = typeIcons[team.team_type] || 'ri-team-line';
                                        return (
                                            <div key={team.id} className="list-group-item d-flex align-items-center justify-content-between py-3 px-4" style={{ border: 'none', borderBottom: '1px solid #f1f5f9' }}>
                                                <div className="d-flex align-items-center gap-3">
                                                    <div className="d-flex align-items-center justify-content-center" style={{ width: '36px', height: '36px', borderRadius: '10px', background: `${color}15` }}>
                                                        <i className={icon} style={{ fontSize: '16px', color }}></i>
                                                    </div>
                                                    <div>
                                                        <span style={{ fontWeight: 500, color: '#1e293b', fontSize: '14px' }}>{team.name}</span>
                                                        {team.head_name && <div style={{ fontSize: '11px', color: '#94a3b8' }}>Leader: {team.head_name}</div>}
                                                    </div>
                                                </div>
                                                <div className="d-flex align-items-center gap-2">
                                                    <span className="badge" style={{ background: `${color}15`, color, fontSize: '12px', padding: '4px 10px', borderRadius: '8px' }}>
                                                        {team.member_count} membri
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : (
                                <div className="card-body text-center py-4">
                                    <i className="ri-team-line text-muted" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                                    <p className="text-muted small mb-0 mt-2">Nessun team attivo</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Row 5: Trial Users */}
            {(trialUsers || []).length > 0 && (
                <div className="row g-3">
                    <div className="col-12">
                        <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                                <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                    <i className="ri-user-follow-line me-2 text-warning"></i>
                                    Professionisti in Prova ({trialUsers.length})
                                </h6>
                            </div>
                            <div className="card-body px-4 pb-4 pt-2">
                                <div className="row g-2">
                                    {trialUsers.map((u) => {
                                        const specConfig = SPECIALTY_CONFIG[u.specialty] || { label: u.specialty || '-', color: '#64748b', bg: '#f1f5f9' };
                                        const stageLabels = { 1: 'Stage 1 - Dashboard', 2: 'Stage 2 - Clienti', 3: 'Stage 3 - Completo' };
                                        const stageColors = { 1: '#f59e0b', 2: '#3b82f6', 3: '#22c55e' };
                                        return (
                                            <div key={u.id} className="col-lg-4 col-md-6">
                                                <div className="d-flex align-items-center gap-3 p-3 rounded-3" style={{ background: '#f8fafc' }}>
                                                    <div className="d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', borderRadius: '50%', background: `${specConfig.color}15`, flexShrink: 0 }}>
                                                        <span style={{ fontWeight: 700, fontSize: '14px', color: specConfig.color }}>
                                                            {u.name ? u.name.charAt(0).toUpperCase() : '?'}
                                                        </span>
                                                    </div>
                                                    <div className="flex-grow-1 min-w-0">
                                                        <div style={{ fontWeight: 500, color: '#1e293b', fontSize: '13px' }} className="text-truncate">{u.name}</div>
                                                        <div className="d-flex align-items-center gap-2">
                                                            <span className="badge" style={{ background: specConfig.bg, color: specConfig.color, fontSize: '10px', padding: '2px 6px', borderRadius: '4px' }}>
                                                                {specConfig.label}
                                                            </span>
                                                            <span style={{ fontSize: '10px', color: stageColors[u.trial_stage] || '#94a3b8', fontWeight: 600 }}>
                                                                {stageLabels[u.trial_stage] || `Stage ${u.trial_stage}`}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

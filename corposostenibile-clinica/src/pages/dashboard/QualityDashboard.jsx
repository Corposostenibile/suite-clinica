import React from 'react';
import { SkeletonCard } from './DashboardShared';

export default function QualityDashboard({ data, loading, error, onRetry }) {
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
                <div className="col-lg-8"><SkeletonCard height="280px" /></div>
                <div className="col-lg-4"><SkeletonCard height="280px" /></div>
                <div className="col-12"><SkeletonCard height="320px" /></div>
            </div>
        );
    }

    const { qualitySummary, qualityTrend, topPerformers } = data;
    const qs = qualitySummary || {};
    const totalBonusBands = Object.values(qs.bonusBands || {}).reduce((a, b) => a + b, 0) || 1;
    const maxTrend = Math.max(...(qualityTrend || []).map(w => w.avgQuality || 0), 1);

    return (
        <>
            {/* KPI Quality */}
            <div className="row g-3 mb-4">
                {[
                    { label: 'Quality media', value: qs.avgQuality != null ? qs.avgQuality.toFixed(1) : 'N/D', icon: 'ri-star-line', bg: '#8b5cf6', subtitle: 'Settimana corrente' },
                    { label: 'Media mese', value: qs.avgMonth != null ? qs.avgMonth.toFixed(1) : 'N/D', icon: 'ri-calendar-line', bg: '#3b82f6' },
                    { label: 'Media trimestre', value: qs.avgTrim != null ? qs.avgTrim.toFixed(1) : 'N/D', icon: 'ri-bar-chart-grouped-line', bg: '#06b6d4' },
                    {
                        label: 'Trend',
                        value: `${qs.trendUp || 0} ↑ / ${qs.trendStable || 0} → / ${qs.trendDown || 0} ↓`,
                        icon: 'ri-trending-up-line',
                        bg: '#22c55e',
                        subtitle: 'In crescita / Stabili / In calo',
                    },
                ].map((stat, idx) => (
                    <div key={idx} className="col-xl-3 col-sm-6">
                        <div className="card border-0 shadow-sm" style={{ backgroundColor: stat.bg, borderRadius: '16px' }}>
                            <div className="card-body py-3">
                                <div className="d-flex align-items-center justify-content-between">
                                    <div>
                                        <h3 className="text-white mb-0 fw-bold" style={{ fontSize: stat.value && stat.value.length > 12 ? '1rem' : undefined }}>{stat.value}</h3>
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

            {/* Trend settimanale + Bonus bands */}
            <div className="row g-3 mb-4">
                <div className="col-lg-8">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-line-chart-line me-2 text-primary"></i>
                                Trend Quality (ultime 8 settimane)
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            {(qualityTrend || []).length > 0 ? (
                                <div className="d-flex align-items-end justify-content-between gap-1" style={{ height: '180px' }}>
                                    {(qualityTrend || []).map((w, idx) => (
                                        <div key={idx} className="d-flex flex-column align-items-center flex-fill">
                                            <div style={{ height: '140px', width: '100%', display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}>
                                                <div
                                                    style={{
                                                        width: '70%',
                                                        maxWidth: '36px',
                                                        height: `${Math.max((w.avgQuality / maxTrend) * 120, 4)}px`,
                                                        background: 'linear-gradient(180deg, #8b5cf6 0%, #6d28d9 100%)',
                                                        borderRadius: '6px 6px 0 0',
                                                    }}
                                                    title={`${w.week}: ${w.avgQuality}`}
                                                />
                                            </div>
                                            <div className="text-center mt-2">
                                                <div style={{ fontSize: '11px', color: '#64748b' }}>{w.week ? new Date(w.week).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' }) : '-'}</div>
                                                <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e293b' }}>{w.avgQuality}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-5 text-muted">Nessun dato trend</div>
                            )}
                        </div>
                    </div>
                </div>
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-award-line me-2 text-success"></i>
                                Bonus Bands
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            {[
                                { band: '100%', color: '#22c55e', bg: '#dcfce7' },
                                { band: '60%', color: '#3b82f6', bg: '#dbeafe' },
                                { band: '30%', color: '#f59e0b', bg: '#fef3c7' },
                                { band: '0%', color: '#ef4444', bg: '#fee2e2' },
                            ].map((b) => {
                                const count = qs.bonusBands?.[b.band] || 0;
                                const pct = Math.round((count / totalBonusBands) * 100);
                                return (
                                    <div key={b.band} className="d-flex align-items-center justify-content-between mb-2">
                                        <span className="badge" style={{ background: b.bg, color: b.color, fontSize: '11px' }}>{b.band}</span>
                                        <span style={{ fontWeight: 700, color: b.color }}>{count}</span>
                                        <div style={{ width: '60%', height: '8px', borderRadius: '4px', background: '#f1f5f9' }}>
                                            <div style={{ width: `${pct}%`, height: '100%', background: b.color, borderRadius: '4px' }}></div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>

            {/* Top Performers */}
            <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                    <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                        <i className="ri-trophy-line me-2 text-warning"></i>
                        Top 10 Quality
                    </h6>
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
                                    <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Banda</th>
                                    <th className="border-0 py-2 text-muted text-center" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>Trend</th>
                                </tr>
                            </thead>
                            <tbody>
                                {topPerformers.map((p, idx) => {
                                    const trendInfo = getTrendIcon(p.trend);
                                    return (
                                        <tr key={p.id}>
                                            <td className="py-2 px-4" style={{ fontWeight: 700, color: idx < 3 ? '#f59e0b' : '#94a3b8' }}>{idx + 1}</td>
                                            <td className="py-2"><span style={{ fontWeight: 500, color: '#1e293b' }}>{p.name}</span></td>
                                            <td className="py-2"><span style={{ fontSize: '12px', color: '#64748b' }}>{p.specialty || '-'}</span></td>
                                            <td className="py-2 text-center"><span style={{ fontWeight: 700, color: getQualityColor(p.quality_final) }}>{p.quality_final ?? '-'}</span></td>
                                            <td className="py-2 text-center">
                                                <span className="badge" style={{
                                                    background: p.bonus_band === '100%' ? '#dcfce7' : p.bonus_band === '60%' ? '#dbeafe' : p.bonus_band === '30%' ? '#fef3c7' : '#fee2e2',
                                                    color: p.bonus_band === '100%' ? '#166534' : p.bonus_band === '60%' ? '#1e40af' : p.bonus_band === '30%' ? '#92400e' : '#991b1b',
                                                    fontSize: '11px',
                                                }}>{p.bonus_band || '-'}</span>
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
                    <div className="text-center py-5 text-muted">Nessun dato quality disponibile</div>
                )}
            </div>
        </>
    );
}

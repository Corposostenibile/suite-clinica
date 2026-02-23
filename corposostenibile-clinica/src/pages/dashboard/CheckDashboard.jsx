import React, { useState } from 'react';
import { SkeletonCard } from './DashboardShared';
import logoFoglia from '../../images/logo_foglia.png';

// Rating color helper
export const getRatingColor = (val) => {
    if (!val) return '#94a3b8';
    if (val >= 9) return '#22c55e';
    if (val >= 7) return '#3b82f6';
    if (val >= 5) return '#f59e0b';
    return '#ef4444';
};

export default function CheckDashboard({ data, loading, error, onRetry }) {
    const [recentPage, setRecentPage] = useState(1);
    const RECENT_PER_PAGE = 5;

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

    const { kpi, ratings, typeBreakdown, ratingsDistribution, monthlyTrend, topProfessionals, recentResponses, physicalMetrics } = data;

    const maxMonthly = Math.max(...(monthlyTrend || []).map(m => m.count), 1);
    const monthChange = kpi.totalPrevMonth > 0
        ? Math.round(((kpi.totalMonth - kpi.totalPrevMonth) / kpi.totalPrevMonth) * 100)
        : (kpi.totalMonth > 0 ? 100 : 0);

    // Ratings distribution total
    const totalRatings = (ratingsDistribution?.low || 0) + (ratingsDistribution?.medium || 0) + (ratingsDistribution?.good || 0) + (ratingsDistribution?.excellent || 0) || 1;

    // Recent responses pagination
    const totalRecentPages = Math.ceil((recentResponses || []).length / RECENT_PER_PAGE);
    const recentStartIdx = (recentPage - 1) * RECENT_PER_PAGE;
    const paginatedRecent = (recentResponses || []).slice(recentStartIdx, recentStartIdx + RECENT_PER_PAGE);

    return (
        <>
            {/* KPI Cards */}
            <div className="row g-3 mb-4">
                {[
                    { label: 'Check Totali', value: kpi.totalAll, icon: 'ri-checkbox-circle-line', bg: '#3b82f6', subtitle: `${kpi.totalMonth} questo mese` },
                    { label: 'Qualità Media', value: kpi.avgQuality ? `${kpi.avgQuality}/10` : 'N/D', icon: 'ri-star-line', bg: '#22c55e', subtitle: 'Ultimi 30 giorni' },
                    { label: 'Questo Mese', value: kpi.totalMonth, icon: 'ri-calendar-check-line', bg: '#8b5cf6', subtitle: monthChange !== 0 ? `${monthChange > 0 ? '+' : ''}${monthChange}% vs mese scorso` : 'Uguale al mese scorso' },
                    { label: 'Da Leggere', value: kpi.unreadCount, icon: 'ri-mail-unread-line', bg: '#f59e0b', subtitle: 'Check non letti' },
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

            {/* Row 2: Trend + Ratings Professionali */}
            <div className="row g-3 mb-4">
                {/* Monthly Trend */}
                <div className="col-lg-8">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-bar-chart-line me-2 text-primary"></i>
                                Trend Check Settimanali (ultimi 6 mesi)
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            <div className="d-flex align-items-end justify-content-between gap-2" style={{ height: '200px' }}>
                                {(monthlyTrend || []).map((m, idx) => (
                                    <div key={idx} className="d-flex flex-column align-items-center flex-fill">
                                        <div className="d-flex flex-column align-items-center justify-content-end" style={{ height: '160px', width: '100%' }}>
                                            <div
                                                style={{
                                                    width: '65%',
                                                    maxWidth: '45px',
                                                    height: `${Math.max((m.count / maxMonthly) * 140, m.count > 0 ? 8 : 0)}px`,
                                                    background: `linear-gradient(180deg, ${m.avgProgress && m.avgProgress >= 7 ? '#22c55e' : m.avgProgress && m.avgProgress >= 5 ? '#f59e0b' : '#3b82f6'} 0%, ${m.avgProgress && m.avgProgress >= 7 ? '#16a34a' : m.avgProgress && m.avgProgress >= 5 ? '#d97706' : '#2563eb'} 100%)`,
                                                    borderRadius: '6px 6px 0 0',
                                                    transition: 'height 0.3s ease',
                                                }}
                                                title={`${m.count} check - Media progresso: ${m.avgProgress || 'N/D'}`}
                                            ></div>
                                        </div>
                                        <div className="text-center mt-2">
                                            <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>
                                                {m.month ? m.month.split('-')[1] + '/' + m.month.split('-')[0].slice(2) : ''}
                                            </span>
                                            <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e293b' }}>{m.count}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <div className="d-flex gap-4 justify-content-center mt-3">
                                <div className="d-flex align-items-center gap-1">
                                    <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#22c55e' }}></div>
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>Progresso ≥ 7</span>
                                </div>
                                <div className="d-flex align-items-center gap-1">
                                    <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#f59e0b' }}></div>
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>Progresso 5-6</span>
                                </div>
                                <div className="d-flex align-items-center gap-1">
                                    <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#3b82f6' }}></div>
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>Progresso &lt; 5</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Professional Ratings */}
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-star-line me-2 text-warning"></i>
                                Valutazioni Medie
                            </h6>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>Ultimi 30 giorni</span>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            <div className="d-flex flex-column gap-3">
                                {[
                                    { label: 'Nutrizionista', value: ratings?.nutrizionista, icon: 'ri-restaurant-line', color: '#22c55e' },
                                    { label: 'Coach', value: ratings?.coach, icon: 'ri-run-line', color: '#f59e0b' },
                                    { label: 'Psicologo', value: ratings?.psicologo, icon: 'ri-mental-health-line', color: '#8b5cf6' },
                                    { label: 'Progresso', value: ratings?.progresso, icon: 'ri-arrow-up-circle-line', color: '#3b82f6' },
                                ].map((r, idx) => (
                                    <div key={idx} className="d-flex align-items-center justify-content-between">
                                        <div className="d-flex align-items-center gap-2">
                                            <div className="d-flex align-items-center justify-content-center" style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${r.color}15` }}>
                                                <i className={r.icon} style={{ fontSize: '14px', color: r.color }}></i>
                                            </div>
                                            <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{r.label}</span>
                                        </div>
                                        <div className="d-flex align-items-center gap-2">
                                            <span style={{ fontSize: '18px', fontWeight: 700, color: getRatingColor(r.value) }}>
                                                {r.value || '—'}
                                            </span>
                                            <span style={{ fontSize: '12px', color: '#94a3b8' }}>/10</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Row 3: Type Breakdown + Ratings Distribution + Physical Metrics */}
            <div className="row g-3 mb-4">
                {/* Type Breakdown */}
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-pie-chart-line me-2 text-info"></i>
                                Tipologia Check
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            {[
                                { key: 'weekly', label: 'Settimanale', icon: 'ri-calendar-line', color: '#3b82f6', bg: '#dbeafe' },
                                { key: 'dca', label: 'DCA', icon: 'ri-heart-pulse-line', color: '#ef4444', bg: '#fee2e2' },
                                { key: 'minor', label: 'Minori (EDE-Q6)', icon: 'ri-user-line', color: '#8b5cf6', bg: '#ede9fe' },
                            ].map((t) => {
                                const info = typeBreakdown?.[t.key] || { total: 0, month: 0 };
                                const pct = kpi.totalAll > 0 ? Math.round((info.total / kpi.totalAll) * 100) : 0;
                                return (
                                    <div key={t.key} className="mb-3">
                                        <div className="d-flex align-items-center justify-content-between mb-1">
                                            <div className="d-flex align-items-center gap-2">
                                                <div className="d-flex align-items-center justify-content-center" style={{ width: '28px', height: '28px', borderRadius: '8px', background: t.bg }}>
                                                    <i className={t.icon} style={{ fontSize: '14px', color: t.color }}></i>
                                                </div>
                                                <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{t.label}</span>
                                            </div>
                                            <div className="text-end">
                                                <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>{info.total}</span>
                                                <span style={{ fontSize: '11px', color: '#94a3b8', marginLeft: '4px' }}>({info.month} mese)</span>
                                            </div>
                                        </div>
                                        <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                                            <div style={{ height: '100%', width: `${pct}%`, background: t.color, borderRadius: '3px', transition: 'width 0.3s ease' }}></div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Ratings Distribution */}
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-bar-chart-grouped-line me-2 text-success"></i>
                                Distribuzione Voti
                            </h6>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>Ultimi 30 giorni</span>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            {[
                                { label: 'Eccellente (9-10)', value: ratingsDistribution?.excellent || 0, color: '#22c55e', bg: '#dcfce7' },
                                { label: 'Buono (7-8)', value: ratingsDistribution?.good || 0, color: '#3b82f6', bg: '#dbeafe' },
                                { label: 'Sufficiente (5-6)', value: ratingsDistribution?.medium || 0, color: '#f59e0b', bg: '#fef3c7' },
                                { label: 'Basso (1-4)', value: ratingsDistribution?.low || 0, color: '#ef4444', bg: '#fee2e2' },
                            ].map((r, idx) => {
                                const pct = Math.round((r.value / totalRatings) * 100);
                                return (
                                    <div key={idx} className="mb-3">
                                        <div className="d-flex align-items-center justify-content-between mb-1">
                                            <span style={{ fontSize: '12px', fontWeight: 500, color: '#334155' }}>{r.label}</span>
                                            <div className="d-flex align-items-center gap-2">
                                                <span style={{ fontSize: '13px', fontWeight: 700, color: r.color }}>{r.value}</span>
                                                <span style={{ fontSize: '11px', color: '#94a3b8' }}>{pct}%</span>
                                            </div>
                                        </div>
                                        <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                                            <div style={{ height: '100%', width: `${pct}%`, background: r.color, borderRadius: '3px', transition: 'width 0.3s ease' }}></div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Physical Metrics */}
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-heart-2-line me-2 text-danger"></i>
                                Metriche Fisiche Medie
                            </h6>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>Ultimi 30 giorni (scala 0-10)</span>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            {physicalMetrics && Object.keys(physicalMetrics).length > 0 ? (
                                <div className="d-flex flex-column gap-2">
                                    {[
                                        { key: 'digestione', label: 'Digestione', icon: '🫃' },
                                        { key: 'energia', label: 'Energia', icon: '⚡' },
                                        { key: 'forza', label: 'Forza', icon: '💪' },
                                        { key: 'sonno', label: 'Sonno', icon: '😴' },
                                        { key: 'umore', label: 'Umore', icon: '😊' },
                                        { key: 'motivazione', label: 'Motivazione', icon: '🎯' },
                                    ].map((m) => {
                                        const val = physicalMetrics[m.key];
                                        return (
                                            <div key={m.key} className="d-flex align-items-center gap-2">
                                                <span style={{ fontSize: '14px', width: '24px' }}>{m.icon}</span>
                                                <span style={{ fontSize: '12px', color: '#64748b', width: '80px' }}>{m.label}</span>
                                                <div className="flex-fill" style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                                                    <div style={{
                                                        height: '100%',
                                                        width: `${val ? (val / 10) * 100 : 0}%`,
                                                        background: getRatingColor(val),
                                                        borderRadius: '3px',
                                                        transition: 'width 0.3s ease',
                                                    }}></div>
                                                </div>
                                                <span style={{ fontSize: '13px', fontWeight: 700, color: getRatingColor(val), width: '30px', textAlign: 'right' }}>
                                                    {val || '—'}
                                                </span>
                                            </div>
                                        );
                                    })}
                                </div>
                            ) : (
                                <div className="text-center py-3 text-muted">
                                    <i className="ri-heart-2-line" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                                    <p className="mb-0 mt-2 small">Nessun dato disponibile</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Row 4: Top Professionals */}
            <div className="row g-3 mb-4">
                {[
                    { key: 'nutrizionisti', title: 'Top Nutrizionisti', icon: 'ri-restaurant-line', color: '#22c55e', bg: '#dcfce7' },
                    { key: 'coaches', title: 'Top Coach', icon: 'ri-run-line', color: '#f59e0b', bg: '#fef3c7' },
                    { key: 'psicologi', title: 'Top Psicologi', icon: 'ri-mental-health-line', color: '#8b5cf6', bg: '#ede9fe' },
                ].map((section) => {
                    const professionals = topProfessionals?.[section.key] || [];
                    return (
                        <div key={section.key} className="col-lg-4">
                            <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                                <div className="card-header border-0 py-3 px-4" style={{ background: section.bg, borderRadius: '16px 16px 0 0' }}>
                                    <h6 className="mb-0" style={{ fontWeight: 600, color: section.color }}>
                                        <i className={`${section.icon} me-2`}></i>{section.title}
                                    </h6>
                                    <span style={{ fontSize: '11px', color: `${section.color}99` }}>Per valutazione media (min. 3 check)</span>
                                </div>
                                <div className="card-body px-4 pb-3 pt-3">
                                    {professionals.length > 0 ? (
                                        <div className="d-flex flex-column gap-2">
                                            {professionals.map((p, idx) => (
                                                <div key={idx} className="d-flex align-items-center justify-content-between">
                                                    <div className="d-flex align-items-center gap-2">
                                                        <div className="d-flex align-items-center justify-content-center" style={{
                                                            width: '24px', height: '24px', borderRadius: '50%',
                                                            background: idx === 0 ? section.color : '#f1f5f9',
                                                            color: idx === 0 ? '#fff' : '#64748b',
                                                            fontSize: '11px', fontWeight: 700,
                                                        }}>
                                                            {idx + 1}
                                                        </div>
                                                        <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{p.name}</span>
                                                    </div>
                                                    <div className="d-flex align-items-center gap-1">
                                                        <span style={{ fontSize: '14px', fontWeight: 700, color: getRatingColor(p.avg) }}>{p.avg}</span>
                                                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>({p.count})</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-muted small mb-0 text-center py-2">Dati insufficienti</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Row 5: Recent Responses Table */}
            <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                    <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                        <i className="ri-file-list-3-line me-2 text-primary"></i>
                        Check Recenti
                    </h6>
                </div>
                {(recentResponses || []).length > 0 ? (
                    <>
                        <div className="table-responsive">
                            <table className="table table-hover mb-0" style={{ fontSize: '13px' }}>
                                <thead>
                                    <tr style={{ borderBottom: '2px solid #f1f5f9' }}>
                                        {['Paziente', 'Data', 'Nutriz.', 'Coach', 'Psico.', 'Progr.', 'Media'].map((h) => (
                                            <th key={h} style={{ padding: '12px 16px', fontWeight: 600, color: '#64748b', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {paginatedRecent.map((r) => (
                                        <tr key={r.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                            <td style={{ padding: '12px 16px', fontWeight: 600, color: '#334155' }} data-label="Paziente">{r.cliente}</td>
                                            <td style={{ padding: '12px 16px', color: '#64748b' }} data-label="Data">{r.date || '—'}</td>
                                            <td style={{ padding: '12px 16px' }} data-label="Nutrizionista">
                                                <span style={{ fontWeight: 700, color: getRatingColor(r.nutrizionista) }}>{r.nutrizionista || '—'}</span>
                                            </td>
                                            <td style={{ padding: '12px 16px' }} data-label="Coach">
                                                <span style={{ fontWeight: 700, color: getRatingColor(r.coach) }}>{r.coach || '—'}</span>
                                            </td>
                                            <td style={{ padding: '12px 16px' }} data-label="Psicologo">
                                                <span style={{ fontWeight: 700, color: getRatingColor(r.psicologo) }}>{r.psicologo || '—'}</span>
                                            </td>
                                            <td style={{ padding: '12px 16px' }} data-label="Progresso">
                                                <span style={{ fontWeight: 700, color: getRatingColor(r.progresso) }}>{r.progresso || '—'}</span>
                                            </td>
                                            <td style={{ padding: '12px 16px' }} data-label="Media">
                                                {r.avg ? (
                                                    <span style={{ background: `${getRatingColor(r.avg)}15`, color: getRatingColor(r.avg), padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 700 }}>
                                                        {r.avg}
                                                    </span>
                                                ) : '—'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        {totalRecentPages > 1 && (
                            <div className="d-flex align-items-center justify-content-between px-4 py-3 border-top">
                                <span className="text-muted" style={{ fontSize: '13px' }}>
                                    {recentStartIdx + 1}-{Math.min(recentStartIdx + RECENT_PER_PAGE, recentResponses.length)} di {recentResponses.length}
                                </span>
                                <div className="d-flex gap-2">
                                    <button className="btn btn-sm btn-light" style={{ borderRadius: '8px' }} onClick={() => setRecentPage(p => Math.max(1, p - 1))} disabled={recentPage === 1}>
                                        <i className="ri-arrow-left-s-line"></i> Prec
                                    </button>
                                    <button className="btn btn-sm btn-light" style={{ borderRadius: '8px' }} onClick={() => setRecentPage(p => Math.min(totalRecentPages, p + 1))} disabled={recentPage === totalRecentPages}>
                                        Succ <i className="ri-arrow-right-s-line"></i>
                                    </button>
                                </div>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="card-body text-center py-4">
                        <i className="ri-file-list-3-line text-muted" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                        <p className="text-muted small mb-0 mt-2">Nessun check recente</p>
                    </div>
                )}
            </div>
        </>
    );
}

// ==================== TEAM RATINGS LIST ====================

export function TeamRatingsList({ title, teams, icon, color, bgColor }) {
    const getRatingStatus = (value) => {
        const n = parseFloat(value);
        if (n >= 8) return { label: 'Buono', bg: '#dcfce7', color: '#166534' };
        if (n >= 7) return { label: 'Da migliorare', bg: '#fef3c7', color: '#92400e' };
        return { label: 'Male', bg: '#fee2e2', color: '#991b1b' };
    };

    return (
        <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)', overflow: 'hidden' }}>
            <div className="card-header border-0 py-3 px-4" style={{ background: bgColor }}>
                <div className="d-flex align-items-center">
                    <i className={icon} style={{ color, fontSize: '20px', marginRight: '8px' }}></i>
                    <h6 className="mb-0" style={{ fontWeight: 600, color }}>{title}</h6>
                </div>
            </div>
            <div className="card-body p-0">
                {teams.length > 0 ? (
                    <div className="list-group list-group-flush">
                        {teams.map((team, idx) => {
                            const status = getRatingStatus(team.average);
                            return (
                                <div key={team.id || idx} className="list-group-item d-flex align-items-center justify-content-between py-3 px-4" style={{ border: 'none', borderBottom: '1px solid #f1f5f9' }}>
                                    <div className="d-flex align-items-center">
                                        {team.head?.avatar_path ? (
                                            <img src={team.head.avatar_path} alt="" className="rounded-circle me-3" style={{ width: '36px', height: '36px', objectFit: 'cover', border: `2px solid ${color}` }} />
                                        ) : (
                                            <div className="d-flex align-items-center justify-content-center me-3" style={{ width: '36px', height: '36px', borderRadius: '50%', background: bgColor, color, fontWeight: 700, fontSize: '12px' }}>
                                                {team.head?.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || team.name?.substring(0, 2).toUpperCase()}
                                            </div>
                                        )}
                                        <div>
                                            <span style={{ fontWeight: 600, color: '#334155', fontSize: '14px', display: 'block' }}>{team.name}</span>
                                            {team.head && <span style={{ fontSize: '11px', color: '#94a3b8' }}>{team.head.full_name}</span>}
                                        </div>
                                    </div>
                                    <div className="d-flex align-items-center gap-2">
                                        <span style={{ fontWeight: 700, fontSize: '16px', color: parseFloat(team.average) >= 7 ? '#22c55e' : '#ef4444' }}>{team.average}</span>
                                        <span className="text-muted" style={{ fontSize: '12px' }}>({team.count})</span>
                                        <span className="badge" style={{ background: status.bg, color: status.color, fontSize: '10px', padding: '3px 6px', borderRadius: '6px' }}>{status.label}</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="text-center py-4"><p className="text-muted mb-0" style={{ fontSize: '13px' }}>Nessun team trovato</p></div>
                )}
            </div>
        </div>
    );
}

// ==================== NEGATIVE CHECKS TABLE ====================

export function NegativeChecksTable({ negativeChecks, negativePage, setNegativePage, perPage }) {
    const totalPages = Math.ceil(negativeChecks.length / perPage);
    const startIdx = (negativePage - 1) * perPage;
    const paginatedChecks = negativeChecks.slice(startIdx, startIdx + perPage);

    return (
        <div className="card border-0 mb-4" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                <h5 className="mb-0" style={{ fontWeight: 600, color: '#1e293b' }}>
                    <i className="ri-alert-line me-2 text-danger"></i>
                    Check Negativi Ultimo Mese
                    <span className="badge bg-danger ms-2" style={{ fontSize: '12px' }}>{negativeChecks.length}</span>
                </h5>
            </div>
            <div className="card-body p-0">
                {negativeChecks.length > 0 ? (
                    <>
                        <div className="table-responsive">
                            <table className="table mb-0">
                                <thead>
                                    <tr style={{ background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)' }}>
                                        <th style={tableHeaderStyle}>Paziente</th>
                                        <th style={tableHeaderStyle}>Data</th>
                                        <th style={tableHeaderStyle}>Rating Negativi</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {paginatedChecks.map((check, idx) => (
                                        <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                            <td style={tableCellStyle}>
                                                <span style={{ fontWeight: 600, color: '#334155' }}>{check.cliente_nome}</span>
                                            </td>
                                            <td style={tableCellStyle}>
                                                <span className="text-muted">{check.submit_date}</span>
                                            </td>
                                            <td style={tableCellStyle}>
                                                <div className="d-flex flex-wrap gap-2">
                                                    {check.negativeRatings?.map((r, i) => (
                                                        <div key={i} className="d-flex align-items-center gap-2" style={{ background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)', padding: '6px 12px', borderRadius: '8px' }}>
                                                            {r.isProgress ? (
                                                                <img src={logoFoglia} alt="Percorso" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover' }} />
                                                            ) : r.professionals && r.professionals.length > 0 ? (
                                                                <div className="d-flex" style={{ marginLeft: '-4px' }}>
                                                                    {r.professionals.slice(0, 2).map((prof, pi) => (
                                                                        prof.avatar_path ? (
                                                                            <img key={pi} src={prof.avatar_path} alt="" style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover', border: '2px solid #fee2e2', marginLeft: pi > 0 ? '-8px' : '0' }} onError={(e) => { e.target.style.display = 'none'; }} />
                                                                        ) : (
                                                                            <div key={pi} style={{ width: '24px', height: '24px', borderRadius: '50%', background: '#991b1b', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700, border: '2px solid #fee2e2', marginLeft: pi > 0 ? '-8px' : '0' }}>
                                                                                {prof.nome?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                                                                            </div>
                                                                        )
                                                                    ))}
                                                                </div>
                                                            ) : null}
                                                            <span style={{ color: '#991b1b', fontWeight: 600, fontSize: '12px' }}>{r.type}: {r.value}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        {totalPages > 1 && (
                            <div className="d-flex align-items-center justify-content-between px-4 py-3 border-top">
                                <span className="text-muted" style={{ fontSize: '13px' }}>
                                    {startIdx + 1}-{Math.min(startIdx + perPage, negativeChecks.length)} di {negativeChecks.length}
                                </span>
                                <div className="d-flex gap-2">
                                    <button className="btn btn-sm btn-light" style={{ borderRadius: '8px' }} onClick={() => setNegativePage(p => Math.max(1, p - 1))} disabled={negativePage === 1}>
                                        <i className="ri-arrow-left-s-line"></i> Prec
                                    </button>
                                    <button className="btn btn-sm btn-light" style={{ borderRadius: '8px' }} onClick={() => setNegativePage(p => Math.min(totalPages, p + 1))} disabled={negativePage === totalPages}>
                                        Succ <i className="ri-arrow-right-s-line"></i>
                                    </button>
                                </div>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="text-center py-5">
                        <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '48px' }}></i>
                        <p className="text-muted mt-2 mb-0">Nessun check negativo questo mese</p>
                    </div>
                )}
            </div>
        </div>
    );
}

// ==================== RANKING TABLE ====================

export function RankingTable({ title, professionals, color, bgColor, icon, isTop }) {
    const [page, setPage] = useState(1);
    const PER_PAGE = 5;
    const totalPages = Math.ceil(professionals.length / PER_PAGE);
    const startIdx = (page - 1) * PER_PAGE;
    const paginatedProfs = professionals.slice(startIdx, startIdx + PER_PAGE);

    return (
        <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)', overflow: 'hidden' }}>
            <div className="card-header border-0 py-3 px-4" style={{ background: bgColor }}>
                <div className="d-flex align-items-center justify-content-between">
                    <div className="d-flex align-items-center">
                        <i className={icon} style={{ color, fontSize: '20px', marginRight: '8px' }}></i>
                        <h6 className="mb-0" style={{ fontWeight: 600, color }}>{title}</h6>
                    </div>
                    {professionals.length > 0 && (
                        <span className="badge ms-2" style={{ background: color, color: '#fff', fontSize: '11px' }}>{professionals.length}</span>
                    )}
                </div>
            </div>
            <div className="card-body p-0">
                {professionals.length > 0 ? (
                    <>
                        <div className="list-group list-group-flush">
                            {paginatedProfs.map((prof, idx) => {
                                const globalIdx = startIdx + idx;
                                return (
                                    <div key={prof.id || idx} className="list-group-item d-flex align-items-center justify-content-between py-3 px-4" style={{ border: 'none', borderBottom: '1px solid #f1f5f9' }}>
                                        <div className="d-flex align-items-center">
                                            <span className="me-3 d-flex align-items-center justify-content-center" style={{
                                                width: '28px', height: '28px', borderRadius: '50%',
                                                background: isTop ? (globalIdx === 0 ? '#fef3c7' : globalIdx === 1 ? '#e5e7eb' : globalIdx === 2 ? '#fed7aa' : '#f1f5f9') : '#fee2e2',
                                                color: isTop ? (globalIdx === 0 ? '#92400e' : globalIdx === 1 ? '#374151' : globalIdx === 2 ? '#c2410c' : '#64748b') : '#991b1b',
                                                fontSize: '12px', fontWeight: 700
                                            }}>
                                                {globalIdx + 1}
                                            </span>
                                            {prof.avatar_path ? (
                                                <img src={prof.avatar_path} alt="" className="rounded-circle me-3" style={{ width: '36px', height: '36px', objectFit: 'cover', border: `2px solid ${color}` }} />
                                            ) : (
                                                <div className="d-flex align-items-center justify-content-center me-3" style={{ width: '36px', height: '36px', borderRadius: '50%', background: bgColor, color, fontWeight: 700, fontSize: '12px' }}>
                                                    {prof.nome?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??'}
                                                </div>
                                            )}
                                            <span style={{ fontWeight: 500, color: '#334155', fontSize: '14px' }}>{prof.nome || 'N/D'}</span>
                                        </div>
                                        <div className="d-flex align-items-center gap-2">
                                            <span style={{ fontWeight: 700, fontSize: '16px', color: parseFloat(prof.average) >= 7 ? '#22c55e' : '#ef4444' }}>{prof.average}</span>
                                            <span className="text-muted" style={{ fontSize: '12px' }}>({prof.count} check)</span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                        {totalPages > 1 && (
                            <div className="d-flex align-items-center justify-content-between px-4 py-2 border-top">
                                <span className="text-muted" style={{ fontSize: '11px' }}>{startIdx + 1}-{Math.min(startIdx + PER_PAGE, professionals.length)} di {professionals.length}</span>
                                <div className="d-flex gap-1">
                                    <button className="btn btn-sm btn-light" style={{ borderRadius: '6px', padding: '2px 8px', fontSize: '12px' }} onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                                        <i className="ri-arrow-left-s-line"></i>
                                    </button>
                                    <button className="btn btn-sm btn-light" style={{ borderRadius: '6px', padding: '2px 8px', fontSize: '12px' }} onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                                        <i className="ri-arrow-right-s-line"></i>
                                    </button>
                                </div>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="text-center py-4"><p className="text-muted mb-0" style={{ fontSize: '13px' }}>Nessun dato disponibile</p></div>
                )}
            </div>
        </div>
    );
}

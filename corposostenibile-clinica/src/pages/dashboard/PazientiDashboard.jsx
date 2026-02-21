import React from 'react';
import { SkeletonCard } from './DashboardShared';

export const STATUS_CONFIG = {
    attivo: { label: 'Attivo', color: '#22c55e', bg: '#dcfce7', icon: 'ri-checkbox-circle-line' },
    ghost: { label: 'Ghost', color: '#f59e0b', bg: '#fef3c7', icon: 'ri-ghost-line' },
    pausa: { label: 'Pausa', color: '#06b6d4', bg: '#cffafe', icon: 'ri-pause-circle-line' },
    stop: { label: 'Stop', color: '#ef4444', bg: '#fee2e2', icon: 'ri-stop-circle-line' },
    insoluto: { label: 'Insoluto', color: '#dc2626', bg: '#fecaca', icon: 'ri-error-warning-line' },
    freeze: { label: 'Freeze', color: '#64748b', bg: '#f1f5f9', icon: 'ri-snowflake-line' },
    non_definito: { label: 'N/D', color: '#94a3b8', bg: '#f8fafc', icon: 'ri-question-line' },
};

export const TIPOLOGIA_CONFIG = {
    a: { label: 'Tipo A', color: '#22c55e', bg: '#dcfce7' },
    b: { label: 'Tipo B', color: '#f59e0b', bg: '#fef3c7' },
    c: { label: 'Tipo C', color: '#3b82f6', bg: '#dbeafe' },
    stop: { label: 'Stop', color: '#ef4444', bg: '#fee2e2' },
    recupero: { label: 'Recupero', color: '#8b5cf6', bg: '#ede9fe' },
    pausa_gt_30: { label: 'Pausa > 30gg', color: '#64748b', bg: '#f1f5f9' },
    non_definito: { label: 'N/D', color: '#94a3b8', bg: '#f8fafc' },
};

export default function PazientiDashboard({ data, loading, error, onRetry }) {
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

    const { kpi, statusDistribution, tipologiaDistribution, services, monthlyTrend, patologie, genderDistribution, programmaDistribution } = data;

    const maxMonthly = Math.max(...(monthlyTrend || []).map(m => m.count), 1);
    const totalStatus = (statusDistribution || []).reduce((s, d) => s + d.count, 0) || 1;
    const totalTipologia = (tipologiaDistribution || []).reduce((s, d) => s + d.count, 0) || 1;
    const maxPatologia = (patologie || []).length > 0 ? patologie[0].count : 1;

    // Month-over-month change
    const monthChange = kpi.newPrevMonth > 0
        ? Math.round(((kpi.newMonth - kpi.newPrevMonth) / kpi.newPrevMonth) * 100)
        : (kpi.newMonth > 0 ? 100 : 0);

    // Retention rate
    const retentionRate = kpi.total > 0 ? Math.round((kpi.active / kpi.total) * 100) : 0;

    return (
        <>
            {/* KPI Cards */}
            <div className="row g-3 mb-4">
                {[
                    { label: 'Pazienti Totali', value: kpi.total, icon: 'ri-group-line', bg: '#3b82f6', subtitle: `${retentionRate}% retention` },
                    { label: 'Attivi', value: kpi.active, icon: 'ri-checkbox-circle-line', bg: '#22c55e', subtitle: `${kpi.inScadenza} in scadenza` },
                    { label: 'Ghost', value: kpi.ghost, icon: 'ri-ghost-line', bg: '#f59e0b', subtitle: `${kpi.pausa} in pausa` },
                    { label: 'Nuovi Mese', value: kpi.newMonth, icon: 'ri-user-add-line', bg: '#8b5cf6', subtitle: monthChange !== 0 ? `${monthChange > 0 ? '+' : ''}${monthChange}% vs mese scorso` : 'Uguale al mese scorso' },
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

            {/* Row 2: Trend + Status Distribution */}
            <div className="row g-3 mb-4">
                {/* Monthly Trend (Bar Chart) */}
                <div className="col-lg-8">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-line-chart-line me-2 text-primary"></i>
                                Nuovi Pazienti (ultimi 12 mesi)
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            <div className="d-flex align-items-end justify-content-between gap-1" style={{ height: '200px' }}>
                                {(monthlyTrend || []).map((m, idx) => (
                                    <div key={idx} className="d-flex flex-column align-items-center flex-fill">
                                        <div className="d-flex flex-column align-items-center justify-content-end" style={{ height: '160px', width: '100%' }}>
                                            <div
                                                style={{
                                                    width: '65%',
                                                    maxWidth: '40px',
                                                    height: `${Math.max((m.count / maxMonthly) * 140, m.count > 0 ? 8 : 0)}px`,
                                                    background: 'linear-gradient(180deg, #3b82f6 0%, #2563eb 100%)',
                                                    borderRadius: '6px 6px 0 0',
                                                    transition: 'height 0.3s ease',
                                                }}
                                                title={`${m.count} nuovi pazienti`}
                                            ></div>
                                        </div>
                                        <div className="text-center mt-2">
                                            <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 500 }}>
                                                {m.month ? m.month.split('-')[1] + '/' + m.month.split('-')[0].slice(2) : ''}
                                            </span>
                                            <div style={{ fontSize: '11px', fontWeight: 700, color: '#1e293b' }}>{m.count}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Status Distribution */}
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-pie-chart-line me-2 text-success"></i>
                                Distribuzione Stato
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            <div className="d-flex flex-column gap-3">
                                {(statusDistribution || [])
                                    .sort((a, b) => b.count - a.count)
                                    .map((s, idx) => {
                                        const config = STATUS_CONFIG[s.status] || STATUS_CONFIG.non_definito;
                                        const pct = Math.round((s.count / totalStatus) * 100);
                                        return (
                                            <div key={idx}>
                                                <div className="d-flex align-items-center justify-content-between mb-1">
                                                    <div className="d-flex align-items-center gap-2">
                                                        <div className="d-flex align-items-center justify-content-center" style={{ width: '24px', height: '24px', borderRadius: '6px', background: config.bg }}>
                                                            <i className={config.icon} style={{ fontSize: '12px', color: config.color }}></i>
                                                        </div>
                                                        <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{config.label}</span>
                                                    </div>
                                                    <div className="d-flex align-items-center gap-2">
                                                        <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>{s.count}</span>
                                                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>{pct}%</span>
                                                    </div>
                                                </div>
                                                <div style={{ height: '5px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                                                    <div style={{ height: '100%', width: `${pct}%`, background: config.color, borderRadius: '3px', transition: 'width 0.3s ease' }}></div>
                                                </div>
                                            </div>
                                        );
                                    })}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Row 3: Services + Tipologia */}
            <div className="row g-3 mb-4">
                {/* Servizi (Nutrizione, Coach, Psicologia) */}
                <div className="col-lg-7">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-stethoscope-line me-2 text-info"></i>
                                Servizi Specialistici
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            <div className="row g-3">
                                {[
                                    { key: 'nutrizione', label: 'Nutrizione', icon: 'ri-restaurant-line', color: '#22c55e', bg: '#dcfce7' },
                                    { key: 'coach', label: 'Coaching', icon: 'ri-run-line', color: '#f59e0b', bg: '#fef3c7' },
                                    { key: 'psicologia', label: 'Psicologia', icon: 'ri-mental-health-line', color: '#8b5cf6', bg: '#ede9fe' },
                                ].map((svc) => {
                                    const stats = services?.[svc.key] || {};
                                    const active = stats.attivo || 0;
                                    const ghost = stats.ghost || 0;
                                    const pausa = stats.pausa || 0;
                                    const stop = stats.stop || 0;
                                    const total = active + ghost + pausa + stop + (stats.insoluto || 0) + (stats.freeze || 0) + (stats.non_definito || 0);
                                    return (
                                        <div key={svc.key} className="col-md-4">
                                            <div style={{ background: svc.bg, borderRadius: '12px', padding: '16px' }}>
                                                <div className="d-flex align-items-center gap-2 mb-3">
                                                    <div className="d-flex align-items-center justify-content-center" style={{ width: '32px', height: '32px', borderRadius: '8px', background: '#fff' }}>
                                                        <i className={svc.icon} style={{ color: svc.color, fontSize: '16px' }}></i>
                                                    </div>
                                                    <div>
                                                        <div style={{ fontSize: '13px', fontWeight: 600, color: svc.color }}>{svc.label}</div>
                                                        <div style={{ fontSize: '11px', color: '#64748b' }}>{total} totali</div>
                                                    </div>
                                                </div>
                                                <div className="d-flex flex-column gap-2">
                                                    <div className="d-flex justify-content-between align-items-center">
                                                        <span style={{ fontSize: '12px', color: '#334155' }}>Attivi</span>
                                                        <span style={{ fontSize: '13px', fontWeight: 700, color: '#22c55e' }}>{active}</span>
                                                    </div>
                                                    <div className="d-flex justify-content-between align-items-center">
                                                        <span style={{ fontSize: '12px', color: '#334155' }}>Ghost</span>
                                                        <span style={{ fontSize: '13px', fontWeight: 700, color: '#f59e0b' }}>{ghost}</span>
                                                    </div>
                                                    <div className="d-flex justify-content-between align-items-center">
                                                        <span style={{ fontSize: '12px', color: '#334155' }}>Pausa</span>
                                                        <span style={{ fontSize: '13px', fontWeight: 700, color: '#06b6d4' }}>{pausa}</span>
                                                    </div>
                                                    <div className="d-flex justify-content-between align-items-center">
                                                        <span style={{ fontSize: '12px', color: '#334155' }}>Stop</span>
                                                        <span style={{ fontSize: '13px', fontWeight: 700, color: '#ef4444' }}>{stop}</span>
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

                {/* Tipologia Distribution */}
                <div className="col-lg-5">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-user-settings-line me-2 text-warning"></i>
                                Tipologia Cliente
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            <div className="d-flex flex-column gap-3">
                                {(tipologiaDistribution || [])
                                    .sort((a, b) => b.count - a.count)
                                    .map((t, idx) => {
                                        const config = TIPOLOGIA_CONFIG[t.tipologia] || TIPOLOGIA_CONFIG.non_definito;
                                        const pct = Math.round((t.count / totalTipologia) * 100);
                                        return (
                                            <div key={idx}>
                                                <div className="d-flex align-items-center justify-content-between mb-1">
                                                    <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{config.label}</span>
                                                    <div className="d-flex align-items-center gap-2">
                                                        <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>{t.count}</span>
                                                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>{pct}%</span>
                                                    </div>
                                                </div>
                                                <div style={{ height: '6px', borderRadius: '3px', background: '#f1f5f9', overflow: 'hidden' }}>
                                                    <div style={{ height: '100%', width: `${pct}%`, background: config.color, borderRadius: '3px', transition: 'width 0.3s ease' }}></div>
                                                </div>
                                            </div>
                                        );
                                    })}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Row 4: Patologie + Programmi */}
            <div className="row g-3 mb-4">
                {/* Top Patologie */}
                <div className="col-lg-6">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-heart-pulse-line me-2 text-danger"></i>
                                Patologie Principali
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            {(patologie || []).length > 0 ? (
                                <div className="d-flex flex-column gap-2">
                                    {patologie.slice(0, 10).map((p, idx) => (
                                        <div key={idx} className="d-flex align-items-center gap-3">
                                            <div style={{ width: '24px', fontSize: '12px', fontWeight: 600, color: '#64748b', textAlign: 'right' }}>
                                                {idx + 1}
                                            </div>
                                            <div className="flex-fill">
                                                <div className="d-flex justify-content-between align-items-center mb-1">
                                                    <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{p.name}</span>
                                                    <span style={{ fontSize: '13px', fontWeight: 700, color: '#1e293b' }}>{p.count}</span>
                                                </div>
                                                <div style={{ height: '4px', borderRadius: '2px', background: '#f1f5f9', overflow: 'hidden' }}>
                                                    <div style={{
                                                        height: '100%',
                                                        width: `${Math.round((p.count / maxPatologia) * 100)}%`,
                                                        background: `hsl(${350 - idx * 15}, 70%, 55%)`,
                                                        borderRadius: '2px',
                                                        transition: 'width 0.3s ease',
                                                    }}></div>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-4 text-muted">
                                    <i className="ri-heart-pulse-line" style={{ fontSize: '32px', opacity: 0.3 }}></i>
                                    <p className="mb-0 mt-2 small">Nessun dato patologie</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Programmi + Gender + Pagamento */}
                <div className="col-lg-6">
                    <div className="d-flex flex-column gap-3">
                        {/* Programmi */}
                        <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                                <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                    <i className="ri-file-list-3-line me-2 text-primary"></i>
                                    Programmi Attivi
                                </h6>
                            </div>
                            <div className="card-body px-4 pb-3 pt-2">
                                {(programmaDistribution || []).length > 0 ? (
                                    <div className="d-flex flex-wrap gap-2">
                                        {programmaDistribution.map((p, idx) => (
                                            <span key={idx} style={{
                                                background: `hsl(${210 + idx * 30}, 80%, 95%)`,
                                                color: `hsl(${210 + idx * 30}, 60%, 35%)`,
                                                padding: '6px 12px',
                                                borderRadius: '20px',
                                                fontSize: '12px',
                                                fontWeight: 600,
                                            }}>
                                                {p.programma} <span style={{ opacity: 0.7 }}>({p.count})</span>
                                            </span>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-muted small mb-0">Nessun dato programmi</p>
                                )}
                            </div>
                        </div>

                        {/* Gender */}
                        <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                            <div className="card-body p-3">
                                <div className="d-flex align-items-center gap-2 mb-3">
                                    <i className="ri-user-heart-line text-info"></i>
                                    <span style={{ fontSize: '13px', fontWeight: 600, color: '#334155' }}>Genere</span>
                                </div>
                                {(genderDistribution || []).length > 0 ? (
                                    <div className="d-flex flex-column gap-2">
                                        {genderDistribution
                                            .filter(g => g.gender !== 'non_definito')
                                            .map((g, idx) => (
                                                <div key={idx} className="d-flex justify-content-between align-items-center">
                                                    <span style={{ fontSize: '12px', color: '#64748b', textTransform: 'capitalize' }}>{g.gender}</span>
                                                    <span style={{ fontSize: '13px', fontWeight: 700, color: '#1e293b' }}>{g.count}</span>
                                                </div>
                                            ))}
                                    </div>
                                ) : (
                                    <p className="text-muted small mb-0">N/D</p>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { SkeletonCard, TopPeopleCard, tableHeaderStyle, tableCellStyle } from './DashboardShared';

export const REVIEW_TYPE_CONFIG = {
    settimanale: { label: 'Settimanale', color: '#3b82f6', bg: '#dbeafe', icon: 'ri-calendar-line' },
    mensile: { label: 'Mensile', color: '#8b5cf6', bg: '#ede9fe', icon: 'ri-calendar-check-line' },
    progetto: { label: 'Progetto', color: '#f59e0b', bg: '#fef3c7', icon: 'ri-folder-line' },
    miglioramento: { label: 'Miglioramento', color: '#ef4444', bg: '#fee2e2', icon: 'ri-arrow-up-circle-line' },
};

export default function FormazioneDashboard({ data, loading }) {
    const [recentPage, setRecentPage] = useState(1);
    const RECENT_PER_PAGE = 5;

    if (loading || !data) {
        return (
            <div className="row g-3">
                <div className="col-lg-3 col-sm-6"><SkeletonCard height="110px" /></div>
                <div className="col-lg-3 col-sm-6"><SkeletonCard height="110px" /></div>
                <div className="col-lg-3 col-sm-6"><SkeletonCard height="110px" /></div>
                <div className="col-lg-3 col-sm-6"><SkeletonCard height="110px" /></div>
                <div className="col-lg-8"><SkeletonCard height="300px" /></div>
                <div className="col-lg-4"><SkeletonCard height="300px" /></div>
            </div>
        );
    }

    const { kpi, byType, monthlyTrend, topReviewers, topReviewees, recentTrainings } = data;

    // Calcola il massimo per il grafico a barre
    const maxMonthly = Math.max(...(monthlyTrend || []).map(m => m.total), 1);

    // Paginazione recent trainings
    const totalRecentPages = Math.ceil((recentTrainings || []).length / RECENT_PER_PAGE);
    const recentStartIdx = (recentPage - 1) * RECENT_PER_PAGE;
    const paginatedRecent = (recentTrainings || []).slice(recentStartIdx, recentStartIdx + RECENT_PER_PAGE);

    // Month-over-month change
    const monthChange = kpi.lastMonth > 0
        ? Math.round(((kpi.thisMonth - kpi.lastMonth) / kpi.lastMonth) * 100)
        : (kpi.thisMonth > 0 ? 100 : 0);

    return (
        <>
            {/* KPI Cards */}
            <div className="row g-3 mb-4">
                {[
                    { label: 'Training Totali', value: kpi.totalTrainings, icon: 'ri-book-open-line', bg: '#3b82f6' },
                    { label: 'Confermati', value: kpi.totalAcknowledged, icon: 'ri-checkbox-circle-line', bg: '#22c55e', subtitle: `${kpi.ackRate}% tasso conferma` },
                    { label: 'In Attesa', value: kpi.totalPending, icon: 'ri-time-line', bg: '#f59e0b' },
                    { label: 'Questo Mese', value: kpi.thisMonth, icon: 'ri-calendar-line', bg: '#8b5cf6', subtitle: monthChange !== 0 ? `${monthChange > 0 ? '+' : ''}${monthChange}% vs mese scorso` : 'Uguale al mese scorso' },
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

            {/* Row 2: Trend + Tipo */}
            <div className="row g-3 mb-4">
                {/* Trend Mensile (Bar Chart) */}
                <div className="col-lg-8">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-bar-chart-line me-2 text-primary"></i>
                                Trend Mensile (ultimi 6 mesi)
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            <div className="d-flex align-items-end justify-content-between gap-2" style={{ height: '200px' }}>
                                {(monthlyTrend || []).map((m, idx) => (
                                    <div key={idx} className="d-flex flex-column align-items-center flex-fill">
                                        <div className="d-flex flex-column align-items-center justify-content-end" style={{ height: '160px', width: '100%' }}>
                                            {/* Acknowledged portion */}
                                            <div
                                                style={{
                                                    width: '70%',
                                                    maxWidth: '50px',
                                                    height: `${Math.max((m.acknowledged / maxMonthly) * 140, m.acknowledged > 0 ? 8 : 0)}px`,
                                                    background: 'linear-gradient(180deg, #22c55e 0%, #16a34a 100%)',
                                                    borderRadius: '6px 6px 0 0',
                                                    transition: 'height 0.3s ease',
                                                    position: 'relative',
                                                }}
                                                title={`Confermati: ${m.acknowledged}`}
                                            ></div>
                                            {/* Pending portion */}
                                            <div
                                                style={{
                                                    width: '70%',
                                                    maxWidth: '50px',
                                                    height: `${Math.max(((m.total - m.acknowledged) / maxMonthly) * 140, (m.total - m.acknowledged) > 0 ? 4 : 0)}px`,
                                                    background: 'linear-gradient(180deg, #f59e0b 0%, #d97706 100%)',
                                                    borderRadius: m.acknowledged === 0 ? '6px 6px 0 0' : '0',
                                                    transition: 'height 0.3s ease',
                                                }}
                                                title={`In attesa: ${m.total - m.acknowledged}`}
                                            ></div>
                                        </div>
                                        <div className="text-center mt-2">
                                            <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>{m.month}</span>
                                            <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e293b' }}>{m.total}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            {/* Legend */}
                            <div className="d-flex gap-4 justify-content-center mt-3">
                                <div className="d-flex align-items-center gap-1">
                                    <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#22c55e' }}></div>
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>Confermati</span>
                                </div>
                                <div className="d-flex align-items-center gap-1">
                                    <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: '#f59e0b' }}></div>
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>In attesa</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Breakdown per Tipo */}
                <div className="col-lg-4">
                    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
                        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                                <i className="ri-pie-chart-line me-2 text-warning"></i>
                                Per Tipologia
                            </h6>
                        </div>
                        <div className="card-body px-4 pb-4 pt-2">
                            {(byType || []).length > 0 ? (
                                <div className="d-flex flex-column gap-3">
                                    {byType.map((t, idx) => {
                                        const config = REVIEW_TYPE_CONFIG[t.type] || { label: t.label, color: '#64748b', bg: '#f1f5f9', icon: 'ri-file-line' };
                                        const pct = kpi.totalTrainings > 0 ? Math.round((t.count / kpi.totalTrainings) * 100) : 0;
                                        return (
                                            <div key={idx}>
                                                <div className="d-flex align-items-center justify-content-between mb-1">
                                                    <div className="d-flex align-items-center gap-2">
                                                        <div className="d-flex align-items-center justify-content-center" style={{ width: '28px', height: '28px', borderRadius: '8px', background: config.bg }}>
                                                            <i className={config.icon} style={{ fontSize: '14px', color: config.color }}></i>
                                                        </div>
                                                        <span style={{ fontSize: '13px', fontWeight: 500, color: '#334155' }}>{config.label}</span>
                                                    </div>
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
                            ) : (
                                <div className="text-center py-4"><p className="text-muted mb-0" style={{ fontSize: '13px' }}>Nessun dato</p></div>
                            )}

                            {/* Richieste KPI */}
                            <div className="mt-4 pt-3 border-top">
                                <div className="d-flex align-items-center justify-content-between mb-2">
                                    <span style={{ fontSize: '13px', color: '#64748b' }}>Richieste totali</span>
                                    <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e293b' }}>{kpi.totalRequests}</span>
                                </div>
                                <div className="d-flex align-items-center justify-content-between">
                                    <span style={{ fontSize: '13px', color: '#64748b' }}>Richieste in attesa</span>
                                    <span style={{ fontSize: '14px', fontWeight: 700, color: kpi.pendingRequests > 0 ? '#f59e0b' : '#22c55e' }}>{kpi.pendingRequests}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Row 3: Top Formatori + Top Destinatari */}
            <div className="row g-3 mb-4">
                <div className="col-lg-6">
                    <TopPeopleCard
                        title="Top Formatori"
                        subtitle="Chi ha erogato più training"
                        icon="ri-user-voice-line"
                        color="#3b82f6"
                        bgColor="#dbeafe"
                        people={topReviewers || []}
                    />
                </div>
                <div className="col-lg-6">
                    <TopPeopleCard
                        title="Top Destinatari"
                        subtitle="Chi ha ricevuto più training"
                        icon="ri-user-received-line"
                        color="#8b5cf6"
                        bgColor="#ede9fe"
                        people={topReviewees || []}
                    />
                </div>
            </div>

            {/* Row 4: Ultimi Training */}
            <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
                <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                    <div className="d-flex align-items-center justify-content-between">
                        <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                            <i className="ri-file-list-3-line me-2 text-info"></i>
                            Ultimi Training
                        </h6>
                        <Link to="/formazione" className="btn btn-sm btn-outline-primary" style={{ borderRadius: '8px' }}>
                            Vai a Formazione <i className="ri-arrow-right-s-line"></i>
                        </Link>
                    </div>
                </div>
                <div className="card-body p-0">
                    {paginatedRecent.length > 0 ? (
                        <>
                            <div className="table-responsive">
                                <table className="table mb-0">
                                    <thead>
                                        <tr style={{ background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)' }}>
                                            <th style={tableHeaderStyle}>Titolo</th>
                                            <th style={tableHeaderStyle}>Tipo</th>
                                            <th style={tableHeaderStyle}>Formatore</th>
                                            <th style={tableHeaderStyle}>Destinatario</th>
                                            <th style={tableHeaderStyle}>Data</th>
                                            <th style={tableHeaderStyle}>Stato</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {paginatedRecent.map((t) => {
                                            const typeConfig = REVIEW_TYPE_CONFIG[t.reviewType] || { label: t.reviewType || 'Altro', color: '#64748b', bg: '#f1f5f9' };
                                            return (
                                                <tr key={t.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                                    <td style={tableCellStyle} data-label="Titolo">
                                                        <span style={{ fontWeight: 600, color: '#334155' }}>{t.title || 'Senza titolo'}</span>
                                                    </td>
                                                    <td style={tableCellStyle} data-label="Tipo">
                                                        <span style={{ background: typeConfig.bg, color: typeConfig.color, padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 600 }}>
                                                            {typeConfig.label}
                                                        </span>
                                                    </td>
                                                    <td style={tableCellStyle} data-label="Formatore"><span className="text-muted">{t.reviewer}</span></td>
                                                    <td style={tableCellStyle} data-label="Destinatario"><span style={{ fontWeight: 500 }}>{t.reviewee}</span></td>
                                                    <td style={tableCellStyle} data-label="Data">
                                                        <span className="text-muted">{t.createdAt ? new Date(t.createdAt).toLocaleDateString('it-IT') : '-'}</span>
                                                    </td>
                                                    <td style={tableCellStyle} data-label="Stato">
                                                        {t.isAcknowledged ? (
                                                            <span style={{ background: '#dcfce7', color: '#166534', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 600 }}>
                                                                <i className="ri-check-line me-1"></i>Confermato
                                                            </span>
                                                        ) : (
                                                            <span style={{ background: '#fef3c7', color: '#92400e', padding: '4px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: 600 }}>
                                                                <i className="ri-time-line me-1"></i>In attesa
                                                            </span>
                                                        )}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                            {totalRecentPages > 1 && (
                                <div className="d-flex align-items-center justify-content-between px-4 py-3 border-top">
                                    <span className="text-muted" style={{ fontSize: '13px' }}>
                                        {recentStartIdx + 1}-{Math.min(recentStartIdx + RECENT_PER_PAGE, recentTrainings.length)} di {recentTrainings.length}
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
                        <div className="text-center py-5">
                            <i className="ri-book-open-line text-muted" style={{ fontSize: '48px', opacity: 0.3 }}></i>
                            <p className="text-muted mt-2 mb-0">Nessun training recente</p>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}

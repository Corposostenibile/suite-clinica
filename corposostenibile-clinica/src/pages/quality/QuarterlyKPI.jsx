import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import qualityService, {
    getCurrentQuarter,
    getAvailableQuarters,
    getSuperMalusBadgeStyle,
    getBandBadgeStyle,
} from '../../services/qualityService';

// Stili card KPI
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
    progressBar: {
        height: '8px',
        borderRadius: '4px',
        background: '#e2e8f0',
        overflow: 'hidden',
    },
    progressFill: {
        height: '100%',
        borderRadius: '4px',
        transition: 'width 0.5s ease',
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

function QuarterlyKPI() {
    const [quarter, setQuarter] = useState(getCurrentQuarter());
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [calculating, setCalculating] = useState(false);
    const [calcResult, setCalcResult] = useState(null);

    // Fetch quarterly summary
    const fetchSummary = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await qualityService.getQuarterlySummary(quarter);
            setSummary(data);
        } catch (err) {
            console.error('Error fetching quarterly summary:', err);
            setError('Errore nel caricamento dei dati trimestrali');
        } finally {
            setLoading(false);
        }
    }, [quarter]);

    useEffect(() => {
        fetchSummary();
    }, [fetchSummary]);

    // Calculate quarterly scores
    const handleCalculate = async () => {
        setCalculating(true);
        setCalcResult(null);
        try {
            const result = await qualityService.calculateQuarterly(quarter);
            setCalcResult(result);
            // Refresh summary after calculation
            setTimeout(fetchSummary, 1000);
        } catch (err) {
            console.error('Error calculating quarterly:', err);
            setCalcResult({ success: false, error: err.message });
        } finally {
            setCalculating(false);
        }
    };

    const quarters = getAvailableQuarters();

    if (loading) {
        return (
            <div className="text-center py-5">
                <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}></div>
                <p className="mt-3 text-muted">Caricamento KPI trimestrali...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="alert alert-warning" style={{ borderRadius: '12px' }}>
                <i className="ri-alert-line me-2"></i>
                {error}
                <button className="btn btn-link btn-sm" onClick={fetchSummary}>Riprova</button>
            </div>
        );
    }

    return (
        <div className="quarterly-kpi-section mt-5">
            {/* Header */}
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
                        onClick={handleCalculate}
                        disabled={calculating}
                    >
                        {calculating ? (
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

            {/* Calc Result Alert */}
            {calcResult && (
                <div className={`alert ${calcResult.success ? 'alert-success' : 'alert-danger'} mb-4`} style={{ borderRadius: '12px' }}>
                    {calcResult.success ? (
                        <>
                            <i className="ri-checkbox-circle-fill me-2"></i>
                            Calcolo completato! Processati <strong>{calcResult.professionisti_processati}</strong> professionisti,
                            <strong> {calcResult.super_malus_applicati}</strong> con Super Malus.
                        </>
                    ) : (
                        <>
                            <i className="ri-error-warning-fill me-2"></i>
                            Errore: {calcResult.error}
                        </>
                    )}
                    <button type="button" className="btn-close float-end" onClick={() => setCalcResult(null)}></button>
                </div>
            )}

            {summary && (
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
                                        {summary.total_professionisti || 0}
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
                                        {summary.professionisti_con_malus || 0}
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
                                        {(summary.total_bonus_before_malus || 0).toFixed(0)}%
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
                                        {(summary.total_bonus_after_malus || 0).toFixed(0)}%
                                    </div>
                                    {summary.bonus_reduction_total > 0 && (
                                        <span className="text-danger small">
                                            <i className="ri-arrow-down-line"></i>
                                            -{summary.bonus_reduction_total.toFixed(0)}%
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Super Malus Details Table */}
                    {summary.malus_details && summary.malus_details.length > 0 && (
                        <div className="card" style={{ ...kpiCardStyles.card }}>
                            <div className="card-header bg-transparent border-0 py-3">
                                <h6 className="mb-0">
                                    <i className="ri-error-warning-line text-danger me-2"></i>
                                    Professionisti con Super Malus ({summary.malus_details.length})
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
                                        {summary.malus_details.map((item, idx) => (
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

                    {/* Empty State */}
                    {(!summary.malus_details || summary.malus_details.length === 0) && (
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
            )}
        </div>
    );
}

export default QuarterlyKPI;

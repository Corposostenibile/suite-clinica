import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import checkService, { CHECK_TYPES } from '../../services/checkService';

// Styles
const styles = {
    card: {
        borderRadius: '16px',
        border: 'none',
        boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        overflow: 'hidden',
    },
    header: {
        background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
        color: 'white',
        padding: '20px 24px',
        borderRadius: '16px',
        marginBottom: '24px',
    },
    ratingBadge: (rating) => {
        if (rating === null || rating === undefined) return { background: 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%)', color: '#64748b' };
        if (rating >= 8) return { background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)', color: '#166534' };
        if (rating >= 6) return { background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)', color: '#92400e' };
        return { background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)', color: '#991b1b' };
    },
    checkTypeBadge: (type) => {
        const config = CHECK_TYPES[type] || { color: '#64748b', bgColor: '#f1f5f9' };
        return {
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '3px 8px',
            borderRadius: '6px',
            fontSize: '10px',
            fontWeight: 600,
            background: config.bgColor,
            color: config.color,
        };
    },
    tableRow: {
        cursor: 'pointer',
        transition: 'background-color 0.15s ease',
    },
    actionBtn: {
        padding: '6px 12px',
        borderRadius: '8px',
        fontSize: '12px',
        fontWeight: 500,
        border: 'none',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
    },
};

function CheckDaLeggere() {
    const navigate = useNavigate();
    const [hoveredRow, setHoveredRow] = useState(null);
    const [loading, setLoading] = useState(true);
    const [unreadChecks, setUnreadChecks] = useState([]);
    const [total, setTotal] = useState(0);
    const [error, setError] = useState(null);
    const [confirmingRead, setConfirmingRead] = useState(null);

    // Fetch data on mount
    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await checkService.getUnreadChecks();
            if (result.success) {
                setUnreadChecks(result.unread_checks || []);
                setTotal(result.total || 0);
            } else {
                setError('Errore nel caricamento dei dati');
            }
        } catch (err) {
            console.error('Error fetching unread checks:', err);
            setError('Errore nel caricamento dei dati');
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
    };

    const formatTime = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    };

    const getTimeAgo = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffDays > 0) return `${diffDays} giorn${diffDays === 1 ? 'o' : 'i'} fa`;
        if (diffHours > 0) return `${diffHours} or${diffHours === 1 ? 'a' : 'e'} fa`;
        return 'Adesso';
    };

    const RatingBadge = ({ rating }) => {
        const style = {
            ...styles.ratingBadge(rating),
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            minWidth: '32px',
            padding: '4px 10px',
            borderRadius: '8px',
            fontSize: '12px',
            fontWeight: 700,
        };
        return <span style={style}>{rating !== null && rating !== undefined ? rating : '-'}</span>;
    };

    const handleViewDetails = (check) => {
        // Navigate to client detail page with check tab active
        if (check.cliente_id) {
            navigate(`/clienti-dettaglio/${check.cliente_id}?tab=check`);
        }
    };

    const handleConfirmRead = async (check, e) => {
        e.stopPropagation();
        setConfirmingRead(check.id);
        try {
            const responseType = check.type === 'weekly' ? 'weekly_check' :
                                 check.type === 'dca' ? 'dca_check' :
                                 'minor_check';
            const result = await checkService.confirmRead(responseType, check.response_id);
            if (result.success) {
                // Remove from list
                setUnreadChecks(prev => prev.filter(c => c.id !== check.id));
                setTotal(prev => prev - 1);
            }
        } catch (err) {
            console.error('Error confirming read:', err);
        } finally {
            setConfirmingRead(null);
        }
    };

    return (
        <>
            {/* Header */}
            <div style={styles.header}>
                <div className="d-flex align-items-center justify-content-between">
                    <div>
                        <h4 className="fw-semibold mb-1">
                            <i className="ri-mail-unread-line me-2"></i>
                            Check da Leggere
                        </h4>
                        <small style={{ opacity: 0.85 }}>Check in attesa della tua conferma di lettura</small>
                    </div>
                    {total > 0 && (
                        <span className="badge bg-white text-warning" style={{ fontSize: '14px', padding: '8px 16px' }}>
                            {total} da leggere
                        </span>
                    )}
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="alert alert-danger mb-4">
                    <i className="ri-error-warning-line me-2"></i>
                    {error}
                </div>
            )}

            {/* Checks List */}
            <div className="card border-0" style={styles.card}>
                <div className="card-header bg-white d-flex justify-content-between align-items-center py-3">
                    <h6 className="mb-0 fw-semibold">
                        <i className="ri-file-list-3-line me-2 text-warning"></i>
                        Check Non Letti ({unreadChecks.length})
                    </h6>
                    <button
                        className="btn btn-sm btn-outline-secondary"
                        onClick={fetchData}
                        disabled={loading}
                    >
                        <i className="ri-refresh-line me-1"></i>
                        Aggiorna
                    </button>
                </div>
                <div className="card-body p-0">
                    {loading ? (
                        <div className="text-center py-5">
                            <div className="spinner-border text-warning" role="status">
                                <span className="visually-hidden">Caricamento...</span>
                            </div>
                            <p className="text-muted mt-2 mb-0">Caricamento check...</p>
                        </div>
                    ) : unreadChecks.length === 0 ? (
                        <div className="text-center py-5">
                            <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '48px' }}></i>
                            <h5 className="text-success mt-3 mb-1">Tutto letto!</h5>
                            <p className="text-muted mb-0">Non ci sono check in attesa di lettura</p>
                        </div>
                    ) : (
                        <div className="table-responsive">
                            <table className="table mb-0 align-middle">
                                <thead style={{ background: '#f8fafc' }}>
                                    <tr>
                                        <th style={{ padding: '12px 16px', fontWeight: 600, fontSize: '13px', color: '#475569', width: '25%' }}>Cliente</th>
                                        <th style={{ padding: '12px 16px', fontWeight: 600, fontSize: '13px', color: '#475569', width: '15%' }}>Data</th>
                                        <th style={{ padding: '12px 16px', fontWeight: 600, fontSize: '13px', color: '#475569', width: '15%' }}>Tipo Check</th>
                                        <th style={{ padding: '12px 16px', fontWeight: 600, fontSize: '13px', color: '#475569', width: '12%', textAlign: 'center' }}>Progresso</th>
                                        <th style={{ padding: '12px 16px', fontWeight: 600, fontSize: '13px', color: '#475569', width: '12%', textAlign: 'center' }}>Benessere</th>
                                        <th style={{ padding: '12px 16px', fontWeight: 600, fontSize: '13px', color: '#475569', width: '21%', textAlign: 'center' }}>Azioni</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {unreadChecks.map((check, idx) => (
                                        <tr
                                            key={check.id}
                                            style={{
                                                ...styles.tableRow,
                                                backgroundColor: hoveredRow === idx ? 'rgba(245, 158, 11, 0.08)' : 'transparent',
                                            }}
                                            onMouseEnter={() => setHoveredRow(idx)}
                                            onMouseLeave={() => setHoveredRow(null)}
                                            onClick={() => handleViewDetails(check)}
                                        >
                                            {/* Cliente */}
                                            <td style={{ padding: '12px 16px' }}>
                                                <div className="d-flex flex-column">
                                                    <span className="fw-semibold text-dark" style={{ fontSize: '14px' }}>
                                                        {check.cliente_nome || 'Cliente'}
                                                    </span>
                                                    <small className="text-muted" style={{ fontSize: '11px' }}>
                                                        {check.cliente_email || ''}
                                                    </small>
                                                </div>
                                            </td>

                                            {/* Data */}
                                            <td style={{ padding: '12px 16px' }}>
                                                <div className="d-flex flex-column">
                                                    <span className="text-dark" style={{ fontSize: '13px' }}>
                                                        {formatDate(check.submitted_at)}
                                                    </span>
                                                    <small className="text-muted" style={{ fontSize: '10px' }}>
                                                        {getTimeAgo(check.submitted_at)}
                                                    </small>
                                                </div>
                                            </td>

                                            {/* Tipo Check */}
                                            <td style={{ padding: '12px 16px' }}>
                                                <span style={styles.checkTypeBadge(check.type)}>
                                                    <i className={CHECK_TYPES[check.type]?.icon || 'ri-checkbox-circle-line'}></i>
                                                    {CHECK_TYPES[check.type]?.label || check.type}
                                                </span>
                                            </td>

                                            {/* Progresso */}
                                            <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                                                <RatingBadge rating={check.progress_rating} />
                                            </td>

                                            {/* Benessere */}
                                            <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                                                <RatingBadge rating={check.wellness_rating} />
                                            </td>

                                            {/* Azioni */}
                                            <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                                                <div className="d-flex justify-content-center gap-2">
                                                    <button
                                                        className="btn btn-sm"
                                                        style={{
                                                            ...styles.actionBtn,
                                                            background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                                                            color: 'white',
                                                        }}
                                                        onClick={(e) => handleConfirmRead(check, e)}
                                                        disabled={confirmingRead === check.id}
                                                    >
                                                        {confirmingRead === check.id ? (
                                                            <span className="spinner-border spinner-border-sm" role="status"></span>
                                                        ) : (
                                                            <>
                                                                <i className="ri-check-line me-1"></i>
                                                                Conferma
                                                            </>
                                                        )}
                                                    </button>
                                                    <button
                                                        className="btn btn-sm"
                                                        style={{
                                                            ...styles.actionBtn,
                                                            background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                                                            color: 'white',
                                                        }}
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleViewDetails(check);
                                                        }}
                                                    >
                                                        <i className="ri-eye-line me-1"></i>
                                                        Dettagli
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            {/* Info Card */}
            <div className="card border-0 mt-4" style={{ ...styles.card, background: '#fffbeb' }}>
                <div className="card-body py-3">
                    <div className="d-flex align-items-center gap-3">
                        <i className="ri-information-line text-warning" style={{ fontSize: '24px' }}></i>
                        <div>
                            <span className="fw-semibold text-dark d-block" style={{ fontSize: '14px' }}>
                                Come funziona
                            </span>
                            <small className="text-muted">
                                Qui trovi tutti i check dei tuoi clienti che non hai ancora letto.
                                Clicca su "Conferma" per segnare un check come letto, oppure vai ai "Dettagli"
                                per vedere le risposte complete del cliente.
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

export default CheckDaLeggere;

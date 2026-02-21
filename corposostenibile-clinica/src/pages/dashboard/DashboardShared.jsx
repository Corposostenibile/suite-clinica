import React from 'react';
import { Collapse } from 'react-bootstrap';

/** Su mobile: sezione collassabile (accordion). Su desktop: solo il contenuto. */
export function MobileSection({ title, id, openId, onToggle, children, icon }) {
    const isOpen = openId === id;
    return (
        <>
            <div className="d-md-none mb-2">
                <div className="card border-0 shadow-sm rounded-3">
                    <button
                        type="button"
                        className="card-header bg-white border-0 d-flex align-items-center justify-content-between w-100 py-2 px-3 text-start"
                        onClick={() => onToggle(isOpen ? null : id)}
                        style={{ borderRadius: 'inherit' }}
                    >
                        <span className="fw-semibold small" style={{ color: '#1e293b', fontSize: '0.9rem' }}>
                            {icon && <i className={`${icon} me-2`}></i>}
                            {title}
                        </span>
                        <i className={`ri-arrow-${isOpen ? 'up' : 'down'}-s-line text-muted`} style={{ fontSize: '1.1rem' }}></i>
                    </button>
                    <Collapse in={isOpen}>
                        <div>
                            <div className="card-body py-2 px-3">{children}</div>
                        </div>
                    </Collapse>
                </div>
            </div>
            <div className="d-none d-md-block">{children}</div>
        </>
    );
}

export function SkeletonNumber() {
    return <span className="placeholder-glow"><span className="placeholder col-4" style={{ borderRadius: '4px' }}>&nbsp;&nbsp;&nbsp;</span></span>;
}

export function SkeletonList({ count = 3 }) {
    return (
        <div className="d-flex flex-column gap-2">
            {[...Array(count)].map((_, i) => (
                <div key={i} className="placeholder-glow d-flex align-items-center justify-content-between">
                    <span className="placeholder col-5" style={{ borderRadius: '4px', height: '14px' }}></span>
                    <span className="placeholder col-2" style={{ borderRadius: '4px', height: '14px' }}></span>
                </div>
            ))}
        </div>
    );
}

export function SkeletonCard({ height = '100px' }) {
    return (
        <div className="card border-0 shadow-sm" style={{ borderRadius: '16px', height, overflow: 'hidden' }}>
            <div className="card-body placeholder-glow d-flex align-items-center gap-3 p-4">
                <span className="placeholder rounded-circle" style={{ width: '56px', height: '56px', flexShrink: 0 }}></span>
                <div className="flex-grow-1">
                    <span className="placeholder col-6 mb-2 d-block" style={{ height: '12px', borderRadius: '4px' }}></span>
                    <span className="placeholder col-4" style={{ height: '24px', borderRadius: '4px' }}></span>
                </div>
            </div>
        </div>
    );
}

export function StatRow({ label, value, color }) {
    return (
        <div className="d-flex align-items-center justify-content-between py-1">
            <span style={{ fontSize: '13px', color: '#64748b' }}>{label}</span>
            <span style={{ fontSize: '15px', fontWeight: 700, color }}>{value}</span>
        </div>
    );
}

export function RatingCard({ label, value, icon, color, bgColor }) {
    const rating = value ? parseFloat(value).toFixed(1) : '-';
    const numericValue = value ? parseFloat(value) : 0;

    const getRatingStatus = () => {
        if (!value) return null;
        if (numericValue >= 8) return { label: 'Buono', bg: '#dcfce7', color: '#166534' };
        if (numericValue >= 7) return { label: 'Da migliorare', bg: '#fef3c7', color: '#92400e' };
        return { label: 'Male', bg: '#fee2e2', color: '#991b1b' };
    };

    const status = getRatingStatus();

    return (
        <div className="col-lg-4 col-sm-6">
            <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
                <div className="card-body p-4">
                    <div className="d-flex align-items-center">
                        <div
                            className="d-flex align-items-center justify-content-center me-3"
                            style={{ width: '56px', height: '56px', borderRadius: '12px', background: bgColor }}
                        >
                            <i className={icon} style={{ fontSize: '24px', color }}></i>
                        </div>
                        <div className="flex-grow-1">
                            <p className="mb-1 text-muted" style={{ fontSize: '13px' }}>{label}</p>
                            <div className="d-flex align-items-center gap-2">
                                <h3 className="mb-0" style={{ fontWeight: 700, color: '#1e293b' }}>{rating}</h3>
                                <span className="text-muted" style={{ fontSize: '14px' }}>/10</span>
                                {status && (
                                    <span className="badge" style={{ background: status.bg, color: status.color, fontSize: '11px', padding: '4px 8px', borderRadius: '6px' }}>
                                        {status.label}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export function TopPeopleCard({ title, subtitle, icon, color, bgColor, people }) {
    return (
        <div className="card border-0 shadow-sm" style={{ borderRadius: '16px', overflow: 'hidden' }}>
            <div className="card-header border-0 py-3 px-4" style={{ background: bgColor }}>
                <div className="d-flex align-items-center justify-content-between">
                    <div>
                        <h6 className="mb-0" style={{ fontWeight: 600, color }}>
                            <i className={`${icon} me-2`}></i>{title}
                        </h6>
                        <span style={{ fontSize: '11px', color: `${color}99` }}>{subtitle}</span>
                    </div>
                    {people.length > 0 && (
                        <span className="badge" style={{ background: color, color: '#fff', fontSize: '11px' }}>{people.length}</span>
                    )}
                </div>
            </div>
            <div className="card-body p-0">
                {people.length > 0 ? (
                    <div className="list-group list-group-flush">
                        {people.slice(0, 5).map((person, idx) => (
                            <div key={person.id || idx} className="list-group-item d-flex align-items-center justify-content-between py-3 px-4" style={{ border: 'none', borderBottom: '1px solid #f1f5f9' }}>
                                <div className="d-flex align-items-center">
                                    <span className="me-3 d-flex align-items-center justify-content-center" style={{
                                        width: '28px', height: '28px', borderRadius: '50%',
                                        background: idx === 0 ? '#fef3c7' : idx === 1 ? '#e5e7eb' : idx === 2 ? '#fed7aa' : '#f1f5f9',
                                        color: idx === 0 ? '#92400e' : idx === 1 ? '#374151' : idx === 2 ? '#c2410c' : '#64748b',
                                        fontSize: '12px', fontWeight: 700
                                    }}>
                                        {idx + 1}
                                    </span>
                                    <div>
                                        <span style={{ fontWeight: 500, color: '#334155', fontSize: '14px' }}>{person.name}</span>
                                        <div style={{ fontSize: '11px', color: '#94a3b8' }}>{person.email}</div>
                                    </div>
                                </div>
                                <div className="d-flex align-items-center gap-1">
                                    <span style={{ fontWeight: 700, fontSize: '16px', color }}>{person.count}</span>
                                    <span style={{ fontSize: '11px', color: '#94a3b8' }}>training</span>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-4"><p className="text-muted mb-0" style={{ fontSize: '13px' }}>Nessun dato</p></div>
                )}
            </div>
        </div>
    );
}

// ==================== STYLES ====================

export const tableHeaderStyle = {
    padding: '16px 20px',
    fontSize: '11px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: '#64748b',
    borderBottom: '2px solid #e2e8f0'
};

export const tableCellStyle = {
    padding: '16px 20px',
    fontSize: '14px',
    color: '#334155',
    verticalAlign: 'middle'
};

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

export function NegativeChecksTable({ negativeChecks, negativePage, setNegativePage, perPage, logoFoglia }) {
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
    const [page, setPage] = React.useState(1);
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

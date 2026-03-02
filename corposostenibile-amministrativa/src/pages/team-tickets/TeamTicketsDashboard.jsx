import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import teamTicketsService from '../../services/teamTicketsService';

const statusConfig = {
  aperto: { label: 'Aperto', color: '#d97706', bg: '#fef3c7' },
  in_lavorazione: { label: 'In Lavorazione', color: '#6366f1', bg: '#ede9fe' },
  risolto: { label: 'Risolto', color: '#16a34a', bg: '#dcfce7' },
  chiuso: { label: 'Chiuso', color: '#64748b', bg: '#f1f5f9' },
};

const priorityConfig = {
  alta: { label: 'Alta', color: '#ef4444' },
  media: { label: 'Media', color: '#f59e0b' },
  bassa: { label: 'Bassa', color: '#06b6d4' },
};

const sourceIcon = {
  admin: 'fas fa-desktop',
  teams: 'fab fa-microsoft',
};

const AVATAR_COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];

const timeAgo = (iso) => {
  if (!iso) return '-';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'ora';
  if (mins < 60) return `${mins} min fa`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} or${hours === 1 ? 'a' : 'e'} fa`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} giorn${days === 1 ? 'o' : 'i'} fa`;
  const months = Math.floor(days / 30);
  return `${months} mes${months === 1 ? 'e' : 'i'} fa`;
};

const getInitials = (name) => name ? name.split(' ').map(n => n[0]).join('').toUpperCase() : '?';
const getAvatarColor = (name) => AVATAR_COLORS[Math.abs([...name].reduce((a, c) => a + c.charCodeAt(0), 0)) % AVATAR_COLORS.length];

export default function TeamTicketsDashboard() {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState({});
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState({});

  // Filters
  const [filters, setFilters] = useState({
    status: '', priority: '', assignee_id: '', search: '', page: 1,
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.priority) params.priority = filters.priority;
      if (filters.assignee_id) params.assignee_id = filters.assignee_id;
      if (filters.search) params.search = filters.search;
      params.page = filters.page;

      const [ticketsRes, statsRes] = await Promise.all([
        teamTicketsService.listTickets(params),
        teamTicketsService.getStats(),
      ]);
      setTickets(ticketsRes.tickets || []);
      setPagination(ticketsRes.pagination || {});
      setStats(statsRes);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { loadData(); }, [loadData]);

  useEffect(() => {
    teamTicketsService.getAssignableUsers().then((r) => setUsers(r.users || [])).catch(() => {});
  }, []);

  const statCards = [
    { label: 'Aperti', key: 'aperti', icon: 'ri-error-warning-line', iconBg: '#fef3c7', iconColor: '#d97706' },
    { label: 'In Lavorazione', key: 'in_lavorazione', icon: 'ri-loader-4-line', iconBg: '#ede9fe', iconColor: '#6366f1' },
    { label: 'Risolti', key: 'risolti', icon: 'ri-checkbox-circle-line', iconBg: '#dcfce7', iconColor: '#16a34a' },
    { label: 'Chiusi', key: 'chiusi', icon: 'ri-archive-line', iconBg: '#f1f5f9', iconColor: '#64748b' },
  ];

  return (
    <div className="container-fluid">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h4 className="mb-1 fw-bold" style={{ color: '#1e293b' }}>Team Tickets</h4>
          <p className="mb-0 text-muted small">Visualizza e monitora i ticket del team (gestione via Teams/SUMI)</p>
        </div>
        <button
          className="btn d-flex align-items-center gap-2"
          onClick={() => navigate('/team-tickets/analytics')}
          style={{
            border: '1px solid #e2e8f0',
            borderRadius: '12px',
            padding: '10px 20px',
            color: '#475569',
            fontWeight: 500,
          }}
        >
          <i className="ri-bar-chart-grouped-line" />
          Analytics
        </button>
      </div>

      {/* KPI Stat Cards */}
      <div className="row g-3 mb-4">
        {statCards.map((s) => (
          <div key={s.key} className="col-sm-6 col-xl-3">
            <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
              <div className="card-body py-3">
                <div className="d-flex align-items-center gap-3">
                  <div className="d-flex align-items-center justify-content-center rounded-circle"
                    style={{ width: '48px', height: '48px', background: s.iconBg, flexShrink: 0 }}>
                    <i className={s.icon} style={{ color: s.iconColor, fontSize: '20px' }} />
                  </div>
                  <div>
                    <h4 className="mb-0 fw-bold" style={{ color: '#1e293b' }}>{stats[s.key] ?? '-'}</h4>
                    <span className="text-muted small">{s.label}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
        <div className="card-body py-3">
          <div className="row g-2 align-items-center">
            <div className="col-md-3">
              <div className="position-relative">
                <i className="fas fa-search position-absolute" style={{ left: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8', fontSize: '14px' }} />
                <input
                  type="text"
                  className="form-control form-control-sm"
                  placeholder="Cerca ticket..."
                  value={filters.search}
                  onChange={(e) => setFilters((p) => ({ ...p, search: e.target.value, page: 1 }))}
                  style={{ borderRadius: '10px', paddingLeft: '36px', border: '1px solid #e2e8f0' }}
                />
              </div>
            </div>
            <div className="col-md-2">
              <select className="form-select form-select-sm" value={filters.status}
                onChange={(e) => setFilters((p) => ({ ...p, status: e.target.value, page: 1 }))}
                style={{ borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <option value="">Tutti gli stati</option>
                {Object.entries(statusConfig).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
            </div>
            <div className="col-md-2">
              <select className="form-select form-select-sm" value={filters.priority}
                onChange={(e) => setFilters((p) => ({ ...p, priority: e.target.value, page: 1 }))}
                style={{ borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <option value="">Tutte le priorita'</option>
                {Object.entries(priorityConfig).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
            </div>
            <div className="col-md-2">
              <select className="form-select form-select-sm" value={filters.assignee_id}
                onChange={(e) => setFilters((p) => ({ ...p, assignee_id: e.target.value, page: 1 }))}
                style={{ borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <option value="">Tutti gli assegnatari</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
            </div>
            <div className="col-md-1">
              <button
                className="btn btn-sm w-100 d-flex align-items-center justify-content-center"
                onClick={() => setFilters({ status: '', priority: '', assignee_id: '', search: '', page: 1 })}
                style={{ borderRadius: '10px', border: '1px solid #e2e8f0', height: '31px', color: '#64748b' }}
              >
                <i className="fas fa-times" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Ticket List */}
      <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
        <div className="card-body p-0">
          {loading ? (
            <div className="text-center py-5"><div className="spinner-border text-primary" /></div>
          ) : tickets.length === 0 ? (
            <div className="text-center py-5">
              <div className="d-flex align-items-center justify-content-center rounded-circle mx-auto mb-3"
                style={{ width: '80px', height: '80px', background: '#f1f5f9' }}>
                <i className="ri-inbox-line" style={{ fontSize: '32px', color: '#94a3b8' }} />
              </div>
              <h6 className="fw-semibold mb-1" style={{ color: '#64748b' }}>Nessun ticket trovato</h6>
              <p className="text-muted small mb-0">Prova a modificare i filtri</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover mb-0">
                <thead>
                  <tr style={{ background: '#f8fafc' }}>
                    {['NUMERO', 'TITOLO', 'PRIORITA\'', 'STATO', 'ASSEGNATARI', 'PAZIENTE', 'FONTE', 'DATA'].map((h) => (
                      <th key={h} style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: '#64748b',
                        borderBottom: '1px solid #e2e8f0',
                        padding: '12px 16px',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tickets.map((t) => {
                    const sc = statusConfig[t.status] || {};
                    const pc = priorityConfig[t.priority] || {};
                    return (
                      <tr key={t.id} style={{ cursor: 'pointer' }}
                        onClick={() => navigate(`/team-tickets/${t.id}`)}>
                        <td style={{ padding: '12px 16px' }}>
                          <span className="fw-semibold" style={{ color: '#6366f1', fontSize: '13px' }}>{t.ticket_number}</span>
                        </td>
                        <td style={{ maxWidth: 300, padding: '12px 16px' }}>
                          <span className="text-truncate d-inline-block fw-medium" style={{ maxWidth: 260, color: '#1e293b', fontSize: '13px' }}>
                            {t.title || t.description}
                          </span>
                          {(t.messages_count > 0 || t.attachments_count > 0) && (
                            <div className="d-flex gap-2 mt-1">
                              {t.messages_count > 0 && (
                                <span className="text-muted" style={{ fontSize: '11px' }}>
                                  <i className="fas fa-comment me-1" />{t.messages_count}
                                </span>
                              )}
                              {t.attachments_count > 0 && (
                                <span className="text-muted" style={{ fontSize: '11px' }}>
                                  <i className="fas fa-paperclip me-1" />{t.attachments_count}
                                </span>
                              )}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <div className="d-flex align-items-center gap-2">
                            <div style={{ width: 8, height: 8, borderRadius: '50%', background: pc.color, flexShrink: 0 }} />
                            <span style={{ fontSize: '12px', color: '#475569' }}>{pc.label}</span>
                          </div>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{
                            display: 'inline-block',
                            padding: '4px 12px',
                            borderRadius: '20px',
                            fontSize: '12px',
                            fontWeight: 500,
                            color: sc.color,
                            background: sc.bg,
                          }}>{sc.label}</span>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <div className="d-flex" style={{ paddingLeft: '8px' }}>
                            {(t.assigned_users || []).slice(0, 3).map((u, i) => (
                              <div key={u.id} title={u.name}
                                className="d-flex align-items-center justify-content-center rounded-circle"
                                style={{
                                  width: 28, height: 28,
                                  background: getAvatarColor(u.name),
                                  color: '#fff',
                                  fontSize: '10px',
                                  fontWeight: 600,
                                  marginLeft: i === 0 ? 0 : '-8px',
                                  border: '2px solid #fff',
                                  zIndex: 3 - i,
                                  position: 'relative',
                                }}>
                                {getInitials(u.name)}
                              </div>
                            ))}
                            {(t.assigned_users || []).length > 3 && (
                              <div className="d-flex align-items-center justify-content-center rounded-circle"
                                style={{
                                  width: 28, height: 28,
                                  background: '#e2e8f0',
                                  color: '#64748b',
                                  fontSize: '10px',
                                  fontWeight: 600,
                                  marginLeft: '-8px',
                                  border: '2px solid #fff',
                                }}>
                                +{t.assigned_users.length - 3}
                              </div>
                            )}
                            {(t.assigned_users || []).length === 0 && (
                              <span className="text-muted" style={{ fontSize: '12px' }}>-</span>
                            )}
                          </div>
                        </td>
                        <td style={{ padding: '12px 16px', fontSize: '13px', color: '#475569' }}>
                          {t.cliente_nome || '-'}
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <i className={sourceIcon[t.source] || 'fas fa-question'} title={t.source}
                            style={{ color: t.source === 'teams' ? '#6366f1' : '#94a3b8' }} />
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span className="text-muted" style={{ fontSize: '12px' }}>{timeAgo(t.created_at)}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pagination */}
        {pagination.pages > 1 && (
          <div className="card-footer bg-white d-flex justify-content-between align-items-center"
            style={{ borderTop: '1px solid #f1f5f9', borderRadius: '0 0 16px 16px' }}>
            <small className="text-muted">
              {pagination.total} ticket totali — Pagina {pagination.page} di {pagination.pages}
            </small>
            <div className="d-flex gap-1">
              <button
                className="btn btn-sm d-flex align-items-center justify-content-center"
                disabled={!pagination.has_prev}
                onClick={() => setFilters((p) => ({ ...p, page: p.page - 1 }))}
                style={{
                  width: 36, height: 36, borderRadius: '10px',
                  border: '1px solid #e2e8f0',
                  background: !pagination.has_prev ? '#f1f5f9' : '#f8fafc',
                  color: !pagination.has_prev ? '#cbd5e1' : '#475569',
                }}
              >
                <i className="fas fa-chevron-left" />
              </button>
              <button
                className="btn btn-sm d-flex align-items-center justify-content-center"
                disabled={!pagination.has_next}
                onClick={() => setFilters((p) => ({ ...p, page: p.page + 1 }))}
                style={{
                  width: 36, height: 36, borderRadius: '10px',
                  border: '1px solid #e2e8f0',
                  background: !pagination.has_next ? '#f1f5f9' : '#f8fafc',
                  color: !pagination.has_next ? '#cbd5e1' : '#475569',
                }}
              >
                <i className="fas fa-chevron-right" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

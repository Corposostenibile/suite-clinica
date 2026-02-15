import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Legend,
} from 'recharts';
import teamTicketsService from '../../services/teamTicketsService';

const STATUS_COLORS = {
  aperto: '#f59e0b',
  in_lavorazione: '#6366f1',
  risolto: '#10b981',
  chiuso: '#94a3b8',
};

const STATUS_LABELS = {
  aperto: 'Aperto',
  in_lavorazione: 'In Lavorazione',
  risolto: 'Risolto',
  chiuso: 'Chiuso',
};

const PRIORITY_COLORS = {
  alta: '#ef4444',
  media: '#f59e0b',
  bassa: '#06b6d4',
};

const PRIORITY_LABELS = {
  alta: 'Alta',
  media: 'Media',
  bassa: 'Bassa',
};

const SOURCE_COLORS = {
  admin: '#6366f1',
  teams: '#06b6d4',
};

const SOURCE_LABELS = {
  admin: 'Admin',
  teams: 'Teams',
};

const AVATAR_COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];
const getInitials = (name) => name ? name.split(' ').map(n => n[0]).join('').toUpperCase() : '?';
const getAvatarColor = (name) => AVATAR_COLORS[Math.abs([...(name || '')].reduce((a, c) => a + c.charCodeAt(0), 0)) % AVATAR_COLORS.length];

const PERIOD_OPTIONS = [
  { value: 30, label: '30 giorni' },
  { value: 60, label: '60 giorni' },
  { value: 90, label: '90 giorni' },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#fff', borderRadius: '12px', padding: '12px 16px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.12)', border: 'none',
    }}>
      <p className="fw-semibold mb-1" style={{ color: '#1e293b', fontSize: '13px' }}>{label}</p>
      {payload.map((entry, i) => (
        <p key={i} className="mb-0" style={{ color: entry.color, fontSize: '12px' }}>
          {entry.name}: <strong>{entry.value}</strong>
        </p>
      ))}
    </div>
  );
};

const PieTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div style={{
      background: '#fff', borderRadius: '12px', padding: '10px 14px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
    }}>
      <p className="mb-0 fw-medium" style={{ color: '#1e293b', fontSize: '13px' }}>
        {d.name}: <strong>{d.value}</strong>
      </p>
    </div>
  );
};

function KPICard({ icon, iconBg, iconColor, value, label }) {
  return (
    <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
      <div className="card-body py-3">
        <div className="d-flex align-items-center gap-3">
          <div className="d-flex align-items-center justify-content-center rounded-circle"
            style={{ width: '48px', height: '48px', background: iconBg, flexShrink: 0 }}>
            <i className={icon} style={{ color: iconColor, fontSize: '20px' }} />
          </div>
          <div>
            <h4 className="mb-0 fw-bold" style={{ color: '#1e293b' }}>{value}</h4>
            <span className="text-muted small">{label}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function TeamTicketsAnalytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    setLoading(true);
    teamTicketsService.getAnalytics(days)
      .then((res) => setData(res))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) {
    return (
      <div className="container-fluid text-center py-5">
        <div className="spinner-border text-primary" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="container-fluid text-center py-5">
        <div className="d-flex align-items-center justify-content-center rounded-circle mx-auto mb-3"
          style={{ width: 80, height: 80, background: '#f1f5f9' }}>
          <i className="ri-bar-chart-grouped-line" style={{ fontSize: '32px', color: '#94a3b8' }} />
        </div>
        <h6 className="fw-semibold mb-1" style={{ color: '#64748b' }}>Errore nel caricamento</h6>
        <p className="text-muted small">Impossibile caricare i dati analytics</p>
      </div>
    );
  }

  // Compute derived values
  const statusMap = {};
  (data.tickets_by_status || []).forEach(s => { statusMap[s.status] = s.count; });
  const totalTickets = Object.values(statusMap).reduce((a, b) => a + b, 0);
  const openTickets = (statusMap.aperto || 0) + (statusMap.in_lavorazione || 0);
  const resolvedTickets = (statusMap.risolto || 0) + (statusMap.chiuso || 0);
  const resolutionRate = totalTickets > 0 ? Math.round((resolvedTickets / totalTickets) * 100) : 0;

  // Format trend data for chart (short date labels)
  const trendData = (data.tickets_by_day || []).map(d => ({
    ...d,
    label: new Date(d.date).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' }),
  }));

  // Pie chart data
  const priorityData = (data.tickets_by_priority || []).map(d => ({
    name: PRIORITY_LABELS[d.priority] || d.priority,
    value: d.count,
    color: PRIORITY_COLORS[d.priority] || '#94a3b8',
  }));

  const sourceData = (data.tickets_by_source || []).map(d => ({
    name: SOURCE_LABELS[d.source] || d.source,
    value: d.count,
    color: SOURCE_COLORS[d.source] || '#94a3b8',
  }));

  const statusData = (data.tickets_by_status || []).map(d => ({
    name: STATUS_LABELS[d.status] || d.status,
    value: d.count,
    fill: STATUS_COLORS[d.status] || '#94a3b8',
  }));

  const maxAssigneeTotal = Math.max(...(data.top_assignees || []).map(a => a.total), 1);

  return (
    <div className="container-fluid">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <div className="d-flex align-items-center gap-2 mb-2">
            <Link to="/team-tickets" className="text-muted small text-decoration-none" style={{ color: '#64748b' }}>
              Team Tickets
            </Link>
            <i className="fas fa-chevron-right" style={{ fontSize: '10px', color: '#cbd5e1' }} />
            <span className="small fw-medium" style={{ color: '#6366f1' }}>Analytics</span>
          </div>
          <h4 className="mb-0 fw-bold" style={{ color: '#1e293b' }}>Analytics</h4>
        </div>
        <div className="d-flex align-items-center" style={{ background: '#f1f5f9', borderRadius: '10px', padding: '3px' }}>
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className="btn btn-sm"
              onClick={() => setDays(opt.value)}
              style={{
                borderRadius: '8px',
                padding: '6px 16px',
                border: 'none',
                background: days === opt.value ? 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)' : 'transparent',
                color: days === opt.value ? '#fff' : '#64748b',
                fontWeight: days === opt.value ? 600 : 500,
                fontSize: '13px',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Row */}
      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-xl-3">
          <KPICard icon="ri-ticket-line" iconBg="#ede9fe" iconColor="#6366f1"
            value={totalTickets} label="Ticket Totali" />
        </div>
        <div className="col-sm-6 col-xl-3">
          <KPICard icon="ri-time-line" iconBg="#fef3c7" iconColor="#d97706"
            value={data.avg_resolution_hours ? `${data.avg_resolution_hours} ore` : '-'}
            label="Tempo Medio Risoluzione" />
        </div>
        <div className="col-sm-6 col-xl-3">
          <KPICard icon="ri-error-warning-line" iconBg="#fef2f2" iconColor="#ef4444"
            value={openTickets} label="Ticket Aperti" />
        </div>
        <div className="col-sm-6 col-xl-3">
          <KPICard icon="ri-checkbox-circle-line" iconBg="#dcfce7" iconColor="#16a34a"
            value={`${resolutionRate}%`} label="Tasso Risoluzione" />
        </div>
      </div>

      {/* Trend Chart */}
      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
        <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
          <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
            <i className="ri-line-chart-line me-2" style={{ color: '#6366f1' }} />Trend Ticket
          </h6>
        </div>
        <div className="card-body px-4 pt-0">
          {trendData.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-muted small mb-0">Nessun dato disponibile per il periodo selezionato</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="gradCreated" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradResolved" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Area type="monotone" dataKey="created" name="Creati" stroke="#6366f1" fill="url(#gradCreated)" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="resolved" name="Risolti" stroke="#10b981" fill="url(#gradResolved)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* 3 Charts Row */}
      <div className="row g-3 mb-4">
        {/* Priority Pie */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm h-100" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-fire-line me-2" style={{ color: '#6366f1' }} />Per Priorità
              </h6>
            </div>
            <div className="card-body px-4 pt-0 d-flex flex-column align-items-center">
              {priorityData.length === 0 ? (
                <p className="text-muted small py-4 mb-0">Nessun dato</p>
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={priorityData} dataKey="value" nameKey="name"
                        cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3}>
                        {priorityData.map((d, i) => <Cell key={i} fill={d.color} />)}
                      </Pie>
                      <Tooltip content={<PieTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="d-flex gap-3 mt-2">
                    {priorityData.map((d, i) => (
                      <div key={i} className="d-flex align-items-center gap-1">
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: d.color }} />
                        <span className="small text-muted">{d.name} ({d.value})</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Source Pie */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm h-100" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-git-branch-line me-2" style={{ color: '#6366f1' }} />Per Sorgente
              </h6>
            </div>
            <div className="card-body px-4 pt-0 d-flex flex-column align-items-center">
              {sourceData.length === 0 ? (
                <p className="text-muted small py-4 mb-0">Nessun dato</p>
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={sourceData} dataKey="value" nameKey="name"
                        cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3}>
                        {sourceData.map((d, i) => <Cell key={i} fill={d.color} />)}
                      </Pie>
                      <Tooltip content={<PieTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="d-flex gap-3 mt-2">
                    {sourceData.map((d, i) => (
                      <div key={i} className="d-flex align-items-center gap-1">
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: d.color }} />
                        <span className="small text-muted">{d.name} ({d.value})</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Status Bar */}
        <div className="col-lg-4">
          <div className="card border-0 shadow-sm h-100" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-bar-chart-horizontal-line me-2" style={{ color: '#6366f1' }} />Per Stato
              </h6>
            </div>
            <div className="card-body px-4 pt-0">
              {statusData.length === 0 ? (
                <p className="text-muted small py-4 mb-0 text-center">Nessun dato</p>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={statusData} layout="vertical" margin={{ left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} axisLine={false} width={100} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="value" name="Ticket" radius={[0, 6, 6, 0]} barSize={20}>
                      {statusData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Performance Team */}
      {(data.top_assignees || []).length > 0 && (
        <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: '16px' }}>
          <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
            <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
              <i className="ri-team-line me-2" style={{ color: '#6366f1' }} />Performance Team
            </h6>
          </div>
          <div className="card-body p-0">
            <div className="table-responsive">
              <table className="table table-hover mb-0">
                <thead>
                  <tr style={{ background: '#f8fafc' }}>
                    {['MEMBRO', 'TOTALI', 'APERTI', 'RISOLTI', 'TEMPO MEDIO', 'PROGRESSO'].map((h) => (
                      <th key={h} style={{
                        fontSize: '11px', fontWeight: 600, textTransform: 'uppercase',
                        letterSpacing: '0.05em', color: '#64748b',
                        borderBottom: '1px solid #e2e8f0', padding: '12px 16px',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.top_assignees.map((a, i) => (
                    <tr key={i}>
                      <td style={{ padding: '12px 16px' }}>
                        <div className="d-flex align-items-center gap-2">
                          <div className="d-flex align-items-center justify-content-center rounded-circle"
                            style={{
                              width: 32, height: 32, background: getAvatarColor(a.name),
                              color: '#fff', fontSize: '11px', fontWeight: 600, flexShrink: 0,
                            }}>
                            {getInitials(a.name)}
                          </div>
                          <span className="fw-medium" style={{ color: '#1e293b', fontSize: '13px' }}>{a.name}</span>
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span className="fw-semibold" style={{ color: '#1e293b' }}>{a.total}</span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ color: '#f59e0b', fontWeight: 500 }}>{a.open}</span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ color: '#10b981', fontWeight: 500 }}>{a.resolved}</span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span className="text-muted" style={{ fontSize: '13px' }}>
                          {a.avg_resolution_hours != null ? `${a.avg_resolution_hours} ore` : '-'}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', width: '20%' }}>
                        <div className="d-flex align-items-center gap-2">
                          <div style={{ flex: 1, height: 6, borderRadius: 3, background: '#f1f5f9', overflow: 'hidden' }}>
                            <div style={{
                              width: `${(a.total / maxAssigneeTotal) * 100}%`,
                              height: '100%',
                              borderRadius: 3,
                              background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                            }} />
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Stats Extra */}
      <div className="row g-3 mb-4">
        <div className="col-md-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-body py-3 px-4">
              <div className="d-flex align-items-center gap-3">
                <div className="d-flex align-items-center justify-content-center rounded-circle"
                  style={{ width: 48, height: 48, background: '#fef3c7', flexShrink: 0 }}>
                  <i className="ri-calendar-line" style={{ color: '#d97706', fontSize: '20px' }} />
                </div>
                <div>
                  <h5 className="mb-0 fw-bold" style={{ color: '#1e293b' }}>
                    {data.busiest_day_of_week?.day_name || '-'}
                  </h5>
                  <span className="text-muted small">
                    Giorno più attivo ({data.busiest_day_of_week?.count || 0} ticket)
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-body py-3 px-4">
              <div className="d-flex align-items-center gap-3">
                <div className="d-flex align-items-center justify-content-center rounded-circle"
                  style={{ width: 48, height: 48, background: '#ede9fe', flexShrink: 0 }}>
                  <i className="ri-chat-3-line" style={{ color: '#6366f1', fontSize: '20px' }} />
                </div>
                <div>
                  <h5 className="mb-0 fw-bold" style={{ color: '#1e293b' }}>{data.recent_activity || 0}</h5>
                  <span className="text-muted small">Messaggi ultime 24h</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="col-md-4">
          <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
            <div className="card-body py-3 px-4">
              <div className="d-flex align-items-center gap-3">
                <div className="d-flex align-items-center justify-content-center rounded-circle"
                  style={{ width: 48, height: 48, background: '#dcfce7', flexShrink: 0 }}>
                  <i className="ri-attachment-2" style={{ color: '#16a34a', fontSize: '20px' }} />
                </div>
                <div>
                  <h5 className="mb-0 fw-bold" style={{ color: '#1e293b' }}>{data.total_attachments || 0}</h5>
                  <span className="text-muted small">Allegati totali</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import teamTicketsService from '../../services/teamTicketsService';

const statusConfig = {
  aperto: { label: 'Aperto', color: '#d97706', bg: '#fef3c7' },
  in_lavorazione: { label: 'In Lavorazione', color: '#6366f1', bg: '#ede9fe' },
  risolto: { label: 'Risolto', color: '#16a34a', bg: '#dcfce7' },
  chiuso: { label: 'Chiuso', color: '#64748b', bg: '#f1f5f9' },
};

const priorityConfig = {
  alta: { label: 'Alta', color: '#ef4444', bg: '#fef2f2' },
  media: { label: 'Media', color: '#f59e0b', bg: '#fef3c7' },
  bassa: { label: 'Bassa', color: '#06b6d4', bg: '#ecfeff' },
};

const AVATAR_COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];
const getInitials = (name) => name ? name.split(' ').map(n => n[0]).join('').toUpperCase() : '?';
const getAvatarColor = (name) => AVATAR_COLORS[Math.abs([...name].reduce((a, c) => a + c.charCodeAt(0), 0)) % AVATAR_COLORS.length];

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

const formatDate = (iso) => {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('it-IT', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

const formatSize = (bytes) => {
  if (!bytes) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const cardStyle = {
  height: 'auto',
  borderRadius: '14px',
  marginBottom: '16px',
};

const sectionTitle = {
  fontSize: '12px',
  fontWeight: 600,
  color: '#64748b',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  marginBottom: '8px',
};

export default function TeamTicketDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef(null);

  const loadTicket = useCallback(async () => {
    try {
      const res = await teamTicketsService.getTicket(id);
      setTicket(res.ticket);
    } catch {
      navigate('/team-tickets');
    } finally {
      setLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => { loadTicket(); }, [loadTicket]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [ticket?.messages]);

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" />
      </div>
    );
  }

  if (!ticket) return null;

  const sc = statusConfig[ticket.status] || {};
  const pc = priorityConfig[ticket.priority] || {};

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <div className="d-flex align-items-center gap-2" style={{ marginBottom: '4px' }}>
          <Link to="/team-tickets" className="text-decoration-none" style={{ color: '#64748b', fontSize: '13px' }}>
            Team Tickets
          </Link>
          <i className="fas fa-chevron-right" style={{ fontSize: '9px', color: '#cbd5e1' }} />
          <span style={{ color: '#6366f1', fontSize: '13px', fontWeight: 500 }}>{ticket.ticket_number}</span>
        </div>
        <div className="d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center gap-2 flex-wrap">
            <h5 style={{ margin: 0, fontWeight: 700, color: '#1e293b', fontSize: '18px' }}>
              {ticket.title || ticket.ticket_number}
            </h5>
            <span style={{
              padding: '2px 10px', borderRadius: '20px',
              fontSize: '11px', fontWeight: 500, color: sc.color, background: sc.bg,
            }}>{sc.label}</span>
            <span style={{
              padding: '2px 10px', borderRadius: '20px',
              fontSize: '11px', fontWeight: 500, color: pc.color, background: pc.bg,
            }}>{pc.label}</span>
            {ticket.source && (
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: '4px',
                padding: '2px 10px', borderRadius: '20px',
                fontSize: '11px', fontWeight: 500, color: '#475569', background: '#f1f5f9',
              }}>
                <i className={ticket.source === 'teams' ? 'fab fa-microsoft' : 'fas fa-desktop'} style={{ fontSize: '10px' }} />
                {ticket.source === 'teams' ? 'Teams' : 'Admin'}
              </span>
            )}
            {ticket.title && (
              <span style={{ color: '#94a3b8', fontSize: '12px' }}>{ticket.ticket_number}</span>
            )}
          </div>
          <span className="text-muted small d-flex align-items-center gap-1">
            <i className="ri-eye-line" style={{ fontSize: '14px' }} />
            Sola lettura
          </span>
        </div>
      </div>

      {/* Due colonne */}
      <div className="row" style={{ alignItems: 'flex-start' }}>
        {/* Colonna sinistra */}
        <div className="col-lg-8">
          {/* Descrizione */}
          <div className="card border-0 shadow-sm" style={cardStyle}>
            <div style={{ padding: '16px' }}>
              <div style={sectionTitle}>
                <i className="ri-file-text-line me-1" style={{ color: '#6366f1' }} />Descrizione
              </div>
              <p style={{ margin: 0, whiteSpace: 'pre-wrap', color: '#374151', lineHeight: 1.6, fontSize: '13px' }}>
                {ticket.description}
              </p>
            </div>
          </div>

          {/* Allegati */}
          {(ticket.attachments || []).length > 0 && (
            <div className="card border-0 shadow-sm" style={cardStyle}>
              <div style={{ padding: '16px' }}>
                <div style={sectionTitle}>
                  <i className="ri-attachment-2 me-1" style={{ color: '#6366f1' }} />Allegati ({ticket.attachments.length})
                </div>
                <div className="d-flex flex-wrap gap-2">
                  {ticket.attachments.map((att) => (
                    <div key={att.id}>
                      {att.is_image ? (
                        <a href={teamTicketsService.getAttachmentUrl(att.id)} target="_blank" rel="noreferrer">
                          <img
                            src={teamTicketsService.getAttachmentUrl(att.id)}
                            alt={att.filename}
                            style={{ height: 72, objectFit: 'cover', borderRadius: '8px' }}
                          />
                        </a>
                      ) : (
                        <a href={teamTicketsService.getAttachmentUrl(att.id)}
                          className="d-flex align-items-center gap-2 text-decoration-none"
                          style={{ background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', padding: '6px 12px' }}>
                          <i className="fas fa-file" style={{ color: '#6366f1', fontSize: '12px' }} />
                          <div>
                            <div className="text-truncate" style={{ color: '#1e293b', fontSize: '12px', fontWeight: 500, maxWidth: 140 }}>{att.filename}</div>
                            <div style={{ fontSize: '10px', color: '#94a3b8' }}>{formatSize(att.file_size)}</div>
                          </div>
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Messaggi (read-only) */}
          <div className="card border-0 shadow-sm" style={cardStyle}>
            <div style={{ padding: '16px 16px 0' }}>
              <div style={sectionTitle}>
                <i className="ri-chat-3-line me-1" style={{ color: '#6366f1' }} />Messaggi
              </div>
            </div>
            <div style={{ padding: '0 16px 16px', maxHeight: 400, overflowY: 'auto' }}>
              {(ticket.messages || []).length === 0 ? (
                <div style={{ textAlign: 'center', padding: '16px 0' }}>
                  <i className="ri-chat-3-line" style={{ fontSize: '20px', color: '#94a3b8', display: 'block', marginBottom: '4px' }} />
                  <span style={{ color: '#94a3b8', fontSize: '12px' }}>Nessun messaggio</span>
                </div>
              ) : (
                ticket.messages.map((msg) => {
                  const isAdmin = msg.source === 'admin';
                  return (
                    <div key={msg.id} className={`d-flex ${isAdmin ? 'justify-content-end' : 'justify-content-start'}`}
                      style={{ marginBottom: '8px' }}>
                      {!isAdmin && (
                        <div className="d-flex align-items-end" style={{ marginRight: '8px' }}>
                          <div className="d-flex align-items-center justify-content-center rounded-circle"
                            style={{ width: 26, height: 26, background: getAvatarColor(msg.sender_name || 'T'), fontSize: '9px', fontWeight: 600, color: '#fff' }}>
                            {getInitials(msg.sender_name || 'T')}
                          </div>
                        </div>
                      )}
                      <div style={{
                        maxWidth: '75%',
                        padding: '8px 12px',
                        borderRadius: isAdmin ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                        background: isAdmin ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : '#f1f5f9',
                        color: isAdmin ? '#fff' : '#1e293b',
                      }}>
                        <div className="d-flex justify-content-between align-items-center gap-3" style={{ marginBottom: '2px' }}>
                          <span style={{ fontSize: '11px', fontWeight: 600 }}>{msg.sender_name || 'Sistema'}</span>
                          <span style={{ fontSize: '9px', opacity: 0.7 }}>
                            {msg.source === 'teams' && <i className="fab fa-microsoft" style={{ marginRight: '3px' }} />}
                            {timeAgo(msg.created_at)}
                          </span>
                        </div>
                        <div style={{ whiteSpace: 'pre-wrap', fontSize: '13px', lineHeight: 1.4 }}>{msg.content}</div>
                      </div>
                      {isAdmin && (
                        <div className="d-flex align-items-end" style={{ marginLeft: '8px' }}>
                          <div className="d-flex align-items-center justify-content-center rounded-circle"
                            style={{ width: 26, height: 26, background: getAvatarColor(msg.sender_name || 'A'), fontSize: '9px', fontWeight: 600, color: '#fff' }}>
                            {getInitials(msg.sender_name || 'A')}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>

        {/* Colonna destra - sidebar (read-only) */}
        <div className="col-lg-4">
          {/* Stato + Priorita (read-only) */}
          <div className="card border-0 shadow-sm" style={cardStyle}>
            <div style={{ padding: '14px 16px' }}>
              <div className="d-flex gap-3">
                <div style={{ flex: 1 }}>
                  <label style={{ ...sectionTitle, display: 'block', marginBottom: '4px' }}>
                    <i className="ri-flag-line me-1" style={{ color: '#6366f1' }} />Stato
                  </label>
                  <span style={{
                    display: 'inline-block',
                    padding: '4px 12px',
                    borderRadius: '20px',
                    fontSize: '12px',
                    fontWeight: 500,
                    color: sc.color,
                    background: sc.bg,
                  }}>{sc.label}</span>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ ...sectionTitle, display: 'block', marginBottom: '4px' }}>
                    <i className="ri-fire-line me-1" style={{ color: '#6366f1' }} />Priorita'
                  </label>
                  <span style={{
                    display: 'inline-block',
                    padding: '4px 12px',
                    borderRadius: '20px',
                    fontSize: '12px',
                    fontWeight: 500,
                    color: pc.color,
                    background: pc.bg,
                  }}>{pc.label}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Informazioni */}
          <div className="card border-0 shadow-sm" style={cardStyle}>
            <div style={{ padding: '14px 16px' }}>
              <div style={sectionTitle}>
                <i className="ri-information-line me-1" style={{ color: '#6366f1' }} />Informazioni
              </div>
              {[
                { label: 'Creato da', value: ticket.created_by_name || '-' },
                { label: 'Paziente', value: ticket.cliente_nome || '-' },
                { label: 'Creato il', value: `${formatDate(ticket.created_at)} (${timeAgo(ticket.created_at)})` },
                ...(ticket.resolved_at ? [{ label: 'Risolto il', value: `${formatDate(ticket.resolved_at)} (${timeAgo(ticket.resolved_at)})` }] : []),
                ...(ticket.closed_at ? [{ label: 'Chiuso il', value: `${formatDate(ticket.closed_at)} (${timeAgo(ticket.closed_at)})` }] : []),
              ].map((row, i) => (
                <div key={i} className="d-flex justify-content-between align-items-center"
                  style={{ padding: '5px 0', borderBottom: '1px solid #f1f5f9' }}>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>{row.label}</span>
                  <span style={{ fontSize: '12px', fontWeight: 500, color: '#1e293b' }}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Assegnatari (read-only) */}
          <div className="card border-0 shadow-sm" style={cardStyle}>
            <div style={{ padding: '14px 16px' }}>
              <div style={sectionTitle}>
                <i className="ri-team-line me-1" style={{ color: '#6366f1' }} />Assegnatari
              </div>
              {(ticket.assigned_users || []).length === 0 ? (
                <p style={{ color: '#94a3b8', fontSize: '12px', margin: 0 }}>Nessun assegnatario</p>
              ) : (
                <div className="d-flex flex-wrap gap-1">
                  {ticket.assigned_users.map((u) => (
                    <span
                      key={u.id}
                      className="d-inline-flex align-items-center gap-1"
                      style={{
                        borderRadius: '14px',
                        padding: '3px 10px',
                        background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                        color: '#fff',
                        fontSize: '11px',
                        fontWeight: 500,
                      }}
                    >
                      <i className="fas fa-user" style={{ fontSize: '8px' }} />
                      {u.name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Timeline */}
          <div className="card border-0 shadow-sm" style={cardStyle}>
            <div style={{ padding: '14px 16px' }}>
              <div style={sectionTitle}>
                <i className="ri-history-line me-1" style={{ color: '#6366f1' }} />Timeline
              </div>
              {(ticket.status_changes || []).length === 0 ? (
                <p style={{ color: '#94a3b8', textAlign: 'center', fontSize: '12px', margin: 0 }}>Nessun cambio di stato</p>
              ) : (
                <div style={{ position: 'relative' }}>
                  <div style={{
                    position: 'absolute', left: '6px', top: '6px', bottom: '6px',
                    width: '2px', background: '#e2e8f0',
                  }} />
                  {ticket.status_changes.map((change, i) => {
                    const toConf = statusConfig[change.to_status] || { color: '#64748b', bg: '#f1f5f9' };
                    return (
                      <div key={change.id} className="d-flex gap-2" style={{ position: 'relative', paddingBottom: i < ticket.status_changes.length - 1 ? '10px' : 0 }}>
                        <div style={{
                          width: 14, height: 14, flexShrink: 0, marginTop: '2px',
                          borderRadius: '50%', background: toConf.bg, border: `2px solid ${toConf.color}`,
                          zIndex: 1,
                        }} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div className="d-flex align-items-center gap-1 flex-wrap">
                            {change.from_status && (
                              <>
                                <span style={{
                                  padding: '1px 6px', borderRadius: '10px', fontSize: '9px', fontWeight: 500,
                                  color: (statusConfig[change.from_status] || {}).color || '#64748b',
                                  background: (statusConfig[change.from_status] || {}).bg || '#f1f5f9',
                                }}>
                                  {(statusConfig[change.from_status] || {}).label || change.from_status}
                                </span>
                                <i className="fas fa-arrow-right" style={{ fontSize: '7px', color: '#cbd5e1' }} />
                              </>
                            )}
                            <span style={{
                              padding: '1px 6px', borderRadius: '10px', fontSize: '9px', fontWeight: 500,
                              color: toConf.color, background: toConf.bg,
                            }}>
                              {toConf.label || change.to_status}
                            </span>
                            {change.source && (
                              <span style={{ fontSize: '9px', color: '#94a3b8' }}>
                                <i className={change.source === 'teams' ? 'fab fa-microsoft' : 'fas fa-desktop'} style={{ fontSize: '8px' }} />
                              </span>
                            )}
                          </div>
                          <div className="d-flex align-items-center gap-1">
                            <span style={{ fontSize: '10px', color: '#94a3b8' }}>{timeAgo(change.created_at)}</span>
                            {change.changed_by_name && (
                              <span style={{ fontSize: '10px', color: '#94a3b8' }}>
                                · {change.changed_by_name}
                              </span>
                            )}
                          </div>
                          {change.message && (
                            <span style={{ fontSize: '10px', color: '#94a3b8', fontStyle: 'italic', display: 'block' }}>{change.message}</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

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

export default function TeamTicketDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [uploadFiles, setUploadFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

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
    teamTicketsService.getAssignableUsers().then((r) => setUsers(r.users || [])).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [ticket?.messages]);

  const handleStatusChange = async (newStatus) => {
    try {
      const res = await teamTicketsService.updateTicket(id, { status: newStatus });
      setTicket(res.ticket);
      loadTicket();
    } catch { /* silent */ }
  };

  const handlePriorityChange = async (newPriority) => {
    try {
      const res = await teamTicketsService.updateTicket(id, { priority: newPriority });
      setTicket(res.ticket);
    } catch { /* silent */ }
  };

  const handleAssigneeToggle = async (userId) => {
    const currentIds = (ticket.assigned_users || []).map((u) => u.id);
    const newIds = currentIds.includes(userId)
      ? currentIds.filter((i) => i !== userId)
      : [...currentIds, userId];
    try {
      const res = await teamTicketsService.updateTicket(id, { assignee_ids: newIds });
      setTicket(res.ticket);
    } catch { /* silent */ }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim()) return;
    setSending(true);
    try {
      await teamTicketsService.sendMessage(id, newMessage.trim());
      setNewMessage('');
      loadTicket();
    } catch { /* silent */ }
    finally { setSending(false); }
  };

  const handleUpload = async () => {
    if (!uploadFiles.length) return;
    setUploading(true);
    try {
      await teamTicketsService.uploadAttachments(id, uploadFiles);
      setUploadFiles([]);
      loadTicket();
    } catch { /* silent */ }
    finally { setUploading(false); }
  };

  const handleDelete = async () => {
    try {
      await teamTicketsService.deleteTicket(id);
      navigate('/team-tickets');
    } catch { /* silent */ }
  };

  if (loading) {
    return (
      <div className="container-fluid text-center py-5">
        <div className="spinner-border text-primary" />
      </div>
    );
  }

  if (!ticket) return null;

  const sc = statusConfig[ticket.status] || {};
  const pc = priorityConfig[ticket.priority] || {};

  return (
    <div className="container-fluid">
      {/* Breadcrumb + Header */}
      <div className="mb-4">
        <div className="d-flex align-items-center gap-2 mb-2">
          <Link to="/team-tickets" className="text-muted small text-decoration-none" style={{ color: '#64748b' }}>
            Team Tickets
          </Link>
          <i className="fas fa-chevron-right" style={{ fontSize: '10px', color: '#cbd5e1' }} />
          <span className="small fw-medium" style={{ color: '#6366f1' }}>{ticket.ticket_number}</span>
        </div>
        <div className="d-flex justify-content-between align-items-start">
          <div>
            <div className="d-flex align-items-center gap-3 mb-2">
              <h4 className="mb-0 fw-bold" style={{ color: '#1e293b' }}>
                {ticket.title || ticket.ticket_number}
              </h4>
              <span style={{
                display: 'inline-block', padding: '4px 12px', borderRadius: '20px',
                fontSize: '12px', fontWeight: 500, color: sc.color, background: sc.bg,
              }}>{sc.label}</span>
              <span style={{
                display: 'inline-block', padding: '4px 12px', borderRadius: '20px',
                fontSize: '12px', fontWeight: 500, color: pc.color, background: pc.bg,
              }}>{pc.label}</span>
              {ticket.source && (
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: '4px',
                  padding: '4px 12px', borderRadius: '20px',
                  fontSize: '12px', fontWeight: 500, color: '#475569', background: '#f1f5f9',
                }}>
                  <i className={ticket.source === 'teams' ? 'fab fa-microsoft' : 'fas fa-desktop'} style={{ fontSize: '11px' }} />
                  {ticket.source === 'teams' ? 'Teams' : 'Admin'}
                </span>
              )}
            </div>
            {ticket.title && (
              <p className="text-muted small mb-0">{ticket.ticket_number}</p>
            )}
          </div>
          <button
            className="btn btn-sm d-flex align-items-center gap-1"
            onClick={() => setShowDeleteConfirm(true)}
            style={{
              border: '1px solid #fecaca', borderRadius: '10px',
              color: '#ef4444', padding: '6px 14px', fontSize: '13px',
            }}
          >
            <i className="fas fa-trash" style={{ fontSize: '11px' }} />Elimina
          </button>
        </div>
      </div>

      <div className="row">
        {/* Left column: description + messages */}
        <div className="col-lg-8">
          {/* Description */}
          <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-file-text-line me-2" style={{ color: '#6366f1' }} />Descrizione
              </h6>
            </div>
            <div className="card-body px-4 pt-0">
              <p className="mb-0" style={{ whiteSpace: 'pre-wrap', color: '#374151', lineHeight: 1.7 }}>{ticket.description}</p>
            </div>
          </div>

          {/* Attachments */}
          {(ticket.attachments || []).length > 0 && (
            <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
              <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
                <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                  <i className="ri-attachment-2 me-2" style={{ color: '#6366f1' }} />Allegati
                </h6>
              </div>
              <div className="card-body px-4 pt-0">
                <div className="row g-2">
                  {ticket.attachments.map((att) => (
                    <div key={att.id} className="col-md-4">
                      {att.is_image ? (
                        <a href={teamTicketsService.getAttachmentUrl(att.id)} target="_blank" rel="noreferrer"
                          className="d-block" style={{ borderRadius: '12px', overflow: 'hidden' }}>
                          <img
                            src={teamTicketsService.getAttachmentUrl(att.id)}
                            alt={att.filename}
                            className="img-fluid"
                            style={{ maxHeight: 150, objectFit: 'cover', width: '100%', borderRadius: '12px' }}
                          />
                        </a>
                      ) : (
                        <a href={teamTicketsService.getAttachmentUrl(att.id)}
                          className="d-flex align-items-center gap-2 text-decoration-none p-3"
                          style={{ background: '#f8fafc', borderRadius: '12px', border: '1px solid #e2e8f0' }}>
                          <div className="d-flex align-items-center justify-content-center rounded"
                            style={{ width: 36, height: 36, background: '#ede9fe', flexShrink: 0 }}>
                            <i className="fas fa-file" style={{ color: '#6366f1', fontSize: '14px' }} />
                          </div>
                          <div style={{ minWidth: 0 }}>
                            <div className="text-truncate fw-medium" style={{ color: '#1e293b', fontSize: '13px' }}>{att.filename}</div>
                            <small className="text-muted">{formatSize(att.file_size)}</small>
                          </div>
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Upload new attachments */}
          <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4 d-flex justify-content-between align-items-center"
              style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-upload-2-line me-2" style={{ color: '#6366f1' }} />Carica Allegati
              </h6>
              {uploadFiles.length > 0 && (
                <button className="btn btn-sm" onClick={handleUpload} disabled={uploading}
                  style={{
                    background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                    color: '#fff', borderRadius: '8px', border: 'none', padding: '4px 14px', fontSize: '12px',
                  }}>
                  {uploading ? <span className="spinner-border spinner-border-sm" /> : 'Carica'}
                </button>
              )}
            </div>
            <div className="card-body px-4 pt-0">
              <div
                className="d-flex flex-column align-items-center justify-content-center"
                style={{
                  borderRadius: '12px', border: '2px dashed #cbd5e1',
                  padding: '20px', cursor: 'pointer', background: '#fafbfc',
                }}
                onClick={() => fileInputRef.current?.click()}
                onDrop={(e) => { e.preventDefault(); setUploadFiles((p) => [...p, ...Array.from(e.dataTransfer.files)]); }}
                onDragOver={(e) => e.preventDefault()}
              >
                <i className="fas fa-cloud-upload-alt mb-1" style={{ color: '#94a3b8', fontSize: '20px' }} />
                <span className="text-muted small">Trascina file qui o clicca</span>
                <input ref={fileInputRef} type="file" multiple className="d-none"
                  onChange={(e) => setUploadFiles((p) => [...p, ...Array.from(e.target.files)])} />
              </div>
              {uploadFiles.length > 0 && (
                <div className="d-flex flex-wrap gap-2 mt-2">
                  {uploadFiles.map((f, i) => (
                    <span key={i} className="d-flex align-items-center gap-1"
                      style={{ background: '#f1f5f9', borderRadius: '8px', padding: '4px 10px', fontSize: '12px', color: '#475569' }}>
                      <i className="fas fa-file" style={{ fontSize: '10px', color: '#94a3b8' }} />
                      {f.name}
                      <button type="button" className="btn-close" style={{ fontSize: '8px', marginLeft: '4px' }}
                        onClick={() => setUploadFiles((p) => p.filter((_, idx) => idx !== i))} />
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Messages */}
          <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-chat-3-line me-2" style={{ color: '#6366f1' }} />Messaggi
              </h6>
            </div>
            <div className="card-body px-4 pt-0" style={{ maxHeight: 450, overflowY: 'auto' }}>
              {(ticket.messages || []).length === 0 ? (
                <div className="text-center py-4">
                  <div className="d-flex align-items-center justify-content-center rounded-circle mx-auto mb-2"
                    style={{ width: 56, height: 56, background: '#f1f5f9' }}>
                    <i className="ri-chat-3-line" style={{ fontSize: '24px', color: '#94a3b8' }} />
                  </div>
                  <p className="text-muted small mb-0">Nessun messaggio</p>
                </div>
              ) : (
                ticket.messages.map((msg) => {
                  const isAdmin = msg.source === 'admin';
                  return (
                    <div key={msg.id} className={`d-flex mb-3 ${isAdmin ? 'justify-content-end' : 'justify-content-start'}`}>
                      {!isAdmin && (
                        <div className="d-flex align-items-end me-2">
                          <div className="d-flex align-items-center justify-content-center rounded-circle"
                            style={{ width: 30, height: 30, background: getAvatarColor(msg.sender_name || 'T'), fontSize: '10px', fontWeight: 600, color: '#fff' }}>
                            {getInitials(msg.sender_name || 'T')}
                          </div>
                        </div>
                      )}
                      <div style={{
                        maxWidth: '70%',
                        padding: '12px 16px',
                        borderRadius: isAdmin ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                        background: isAdmin ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : '#f1f5f9',
                        color: isAdmin ? '#fff' : '#1e293b',
                      }}>
                        <div className="d-flex justify-content-between align-items-center mb-1 gap-3">
                          <small className="fw-semibold" style={{ fontSize: '12px' }}>{msg.sender_name || 'Sistema'}</small>
                          <small style={{ fontSize: '10px', opacity: 0.7 }}>
                            {msg.source === 'teams' && <i className="fab fa-microsoft me-1" />}
                            {timeAgo(msg.created_at)}
                          </small>
                        </div>
                        <div style={{ whiteSpace: 'pre-wrap', fontSize: '14px', lineHeight: 1.5 }}>{msg.content}</div>
                      </div>
                      {isAdmin && (
                        <div className="d-flex align-items-end ms-2">
                          <div className="d-flex align-items-center justify-content-center rounded-circle"
                            style={{ width: 30, height: 30, background: getAvatarColor(msg.sender_name || 'A'), fontSize: '10px', fontWeight: 600, color: '#fff' }}>
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
            <div className="card-footer bg-white border-0 px-4 pb-3" style={{ borderRadius: '0 0 16px 16px' }}>
              <form onSubmit={handleSendMessage} className="d-flex gap-2">
                <input
                  type="text"
                  className="form-control"
                  placeholder="Scrivi un messaggio..."
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  style={{ borderRadius: '12px', border: '1px solid #e2e8f0' }}
                />
                <button type="submit" className="btn d-flex align-items-center justify-content-center"
                  disabled={sending || !newMessage.trim()}
                  style={{
                    width: 40, height: 40, borderRadius: '12px', border: 'none', flexShrink: 0,
                    background: newMessage.trim() ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : '#e2e8f0',
                    color: newMessage.trim() ? '#fff' : '#94a3b8',
                  }}>
                  {sending ? <span className="spinner-border spinner-border-sm" /> : <i className="fas fa-paper-plane" style={{ fontSize: '14px' }} />}
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Right column: sidebar */}
        <div className="col-lg-4">
          {/* Status */}
          <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-flag-line me-2" style={{ color: '#6366f1' }} />Stato
              </h6>
            </div>
            <div className="card-body px-4 pt-0">
              <select
                className="form-select"
                value={ticket.status}
                onChange={(e) => handleStatusChange(e.target.value)}
                style={{ borderRadius: '10px', border: '1px solid #e2e8f0' }}
              >
                {Object.entries(statusConfig).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Priority */}
          <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-fire-line me-2" style={{ color: '#6366f1' }} />Priorità
              </h6>
            </div>
            <div className="card-body px-4 pt-0">
              <select
                className="form-select"
                value={ticket.priority}
                onChange={(e) => handlePriorityChange(e.target.value)}
                style={{ borderRadius: '10px', border: '1px solid #e2e8f0' }}
              >
                {Object.entries(priorityConfig).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Info */}
          <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-information-line me-2" style={{ color: '#6366f1' }} />Informazioni
              </h6>
            </div>
            <div className="card-body px-4 pt-0">
              {[
                { label: 'Creato da', value: ticket.created_by_name || '-' },
                { label: 'Paziente', value: ticket.cliente_nome || '-' },
                { label: 'Creato il', value: formatDate(ticket.created_at) },
                ...(ticket.resolved_at ? [{ label: 'Risolto il', value: formatDate(ticket.resolved_at) }] : []),
                ...(ticket.closed_at ? [{ label: 'Chiuso il', value: formatDate(ticket.closed_at) }] : []),
              ].map((row, i) => (
                <div key={i} className="d-flex justify-content-between align-items-center py-2"
                  style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <span className="text-muted small">{row.label}</span>
                  <span className="fw-medium small" style={{ color: '#1e293b' }}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Assignees */}
          <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-team-line me-2" style={{ color: '#6366f1' }} />Assegnatari
              </h6>
            </div>
            <div className="card-body px-4 pt-0">
              <div className="d-flex flex-wrap gap-2">
                {users.map((u) => {
                  const isAssigned = (ticket.assigned_users || []).some((a) => a.id === u.id);
                  return (
                    <button
                      key={u.id}
                      className="btn btn-sm d-flex align-items-center gap-1"
                      onClick={() => handleAssigneeToggle(u.id)}
                      style={{
                        borderRadius: '20px',
                        padding: '5px 14px',
                        border: isAssigned ? 'none' : '1px solid #e2e8f0',
                        background: isAssigned ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : '#fff',
                        color: isAssigned ? '#fff' : '#475569',
                        fontSize: '12px',
                        fontWeight: 500,
                      }}
                    >
                      {isAssigned && <i className="fas fa-check" style={{ fontSize: '10px' }} />}
                      {u.name}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Status Timeline */}
          <div className="card border-0 shadow-sm mb-3" style={{ borderRadius: '16px' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h6 className="mb-0 fw-semibold" style={{ color: '#1e293b' }}>
                <i className="ri-history-line me-2" style={{ color: '#6366f1' }} />Timeline
              </h6>
            </div>
            <div className="card-body px-4 pt-0">
              {(ticket.status_changes || []).length === 0 ? (
                <p className="text-muted text-center small py-3 mb-0">Nessun cambio di stato</p>
              ) : (
                <div style={{ position: 'relative' }}>
                  {/* Vertical line */}
                  <div style={{
                    position: 'absolute', left: '8px', top: '8px', bottom: '8px',
                    width: '2px', background: '#e2e8f0',
                  }} />
                  {ticket.status_changes.map((change, i) => {
                    const toConf = statusConfig[change.to_status] || { color: '#64748b', bg: '#f1f5f9' };
                    return (
                      <div key={change.id} className="d-flex gap-3 position-relative" style={{ paddingBottom: i < ticket.status_changes.length - 1 ? '16px' : 0 }}>
                        {/* Dot */}
                        <div className="d-flex align-items-center justify-content-center rounded-circle"
                          style={{
                            width: 18, height: 18, flexShrink: 0,
                            background: toConf.bg, border: `2px solid ${toConf.color}`,
                            zIndex: 1,
                          }} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div className="d-flex align-items-center gap-2 flex-wrap">
                            {change.from_status && (
                              <>
                                <span style={{
                                  padding: '2px 8px', borderRadius: '12px', fontSize: '10px', fontWeight: 500,
                                  color: (statusConfig[change.from_status] || {}).color || '#64748b',
                                  background: (statusConfig[change.from_status] || {}).bg || '#f1f5f9',
                                }}>
                                  {(statusConfig[change.from_status] || {}).label || change.from_status}
                                </span>
                                <i className="fas fa-arrow-right" style={{ fontSize: '8px', color: '#cbd5e1' }} />
                              </>
                            )}
                            <span style={{
                              padding: '2px 8px', borderRadius: '12px', fontSize: '10px', fontWeight: 500,
                              color: toConf.color, background: toConf.bg,
                            }}>
                              {toConf.label || change.to_status}
                            </span>
                          </div>
                          <div className="d-flex align-items-center gap-2 mt-1">
                            <small className="text-muted" style={{ fontSize: '11px' }}>{timeAgo(change.created_at)}</small>
                            {change.changed_by_name && (
                              <small className="text-muted" style={{ fontSize: '11px' }}>
                                da <span className="fw-medium">{change.changed_by_name}</span>
                              </small>
                            )}
                          </div>
                          {change.message && (
                            <small className="text-muted fst-italic d-block mt-1" style={{ fontSize: '11px' }}>{change.message}</small>
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

      {/* Delete Confirm Modal */}
      {showDeleteConfirm && (
        <>
          <div className="modal-backdrop fade show" style={{ zIndex: 1050 }} onClick={() => setShowDeleteConfirm(false)} />
          <div className="modal fade show d-block" style={{ zIndex: 1055 }} tabIndex="-1" onClick={() => setShowDeleteConfirm(false)}>
            <div className="modal-dialog modal-dialog-centered" onClick={(e) => e.stopPropagation()}>
              <div className="modal-content border-0" style={{ borderRadius: '16px', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
                <div className="modal-header border-0 px-4 pt-4 pb-0">
                  <h5 className="modal-title fw-bold" style={{ color: '#1e293b' }}>Conferma eliminazione</h5>
                  <button className="btn-close" onClick={() => setShowDeleteConfirm(false)} />
                </div>
                <div className="modal-body px-4 py-3">
                  <p className="mb-0" style={{ color: '#475569' }}>
                    Sei sicuro di voler eliminare il ticket <strong>{ticket.ticket_number}</strong>?
                    Questa azione non può essere annullata.
                  </p>
                </div>
                <div className="modal-footer border-0 px-4 pb-4 pt-0">
                  <button className="btn" onClick={() => setShowDeleteConfirm(false)}
                    style={{ borderRadius: '10px', border: '1px solid #e2e8f0', color: '#475569', padding: '8px 20px' }}>
                    Annulla
                  </button>
                  <button className="btn" onClick={handleDelete}
                    style={{
                      background: '#ef4444', color: '#fff',
                      borderRadius: '10px', border: 'none', padding: '8px 20px', fontWeight: 500,
                    }}>
                    Elimina
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

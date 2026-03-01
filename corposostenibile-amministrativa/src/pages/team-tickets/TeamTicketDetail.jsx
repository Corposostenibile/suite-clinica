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

// Stile card che resetta height: calc(100% - 30px) del template
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
          <button
            onClick={() => setShowDeleteConfirm(true)}
            style={{
              border: '1px solid #fecaca', borderRadius: '8px',
              color: '#ef4444', padding: '4px 12px', fontSize: '12px',
              background: 'transparent', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px',
            }}
          >
            <i className="fas fa-trash" style={{ fontSize: '10px' }} />Elimina
          </button>
        </div>
      </div>

      {/* Due colonne - align-items: flex-start impedisce lo stretch delle colonne */}
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
                  <i className="ri-attachment-2 me-1" style={{ color: '#6366f1' }} />Allegati
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

          {/* Upload */}
          <div className="card border-0 shadow-sm" style={cardStyle}>
            <div style={{ padding: '16px' }}>
              <div className="d-flex justify-content-between align-items-center" style={{ marginBottom: '8px' }}>
                <div style={sectionTitle}>
                  <i className="ri-upload-2-line me-1" style={{ color: '#6366f1' }} />Carica Allegati
                </div>
                {uploadFiles.length > 0 && (
                  <button onClick={handleUpload} disabled={uploading}
                    style={{
                      background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
                      color: '#fff', borderRadius: '6px', border: 'none', padding: '3px 12px', fontSize: '11px', cursor: 'pointer',
                    }}>
                    {uploading ? <span className="spinner-border spinner-border-sm" /> : 'Carica'}
                  </button>
                )}
              </div>
              <div
                className="d-flex align-items-center justify-content-center gap-2"
                style={{
                  borderRadius: '8px', border: '2px dashed #cbd5e1',
                  padding: '10px', cursor: 'pointer', background: '#fafbfc',
                }}
                onClick={() => fileInputRef.current?.click()}
                onDrop={(e) => { e.preventDefault(); setUploadFiles((p) => [...p, ...Array.from(e.dataTransfer.files)]); }}
                onDragOver={(e) => e.preventDefault()}
              >
                <i className="fas fa-cloud-upload-alt" style={{ color: '#94a3b8', fontSize: '14px' }} />
                <span style={{ color: '#94a3b8', fontSize: '12px' }}>Trascina file qui o clicca</span>
                <input ref={fileInputRef} type="file" multiple style={{ display: 'none' }}
                  onChange={(e) => setUploadFiles((p) => [...p, ...Array.from(e.target.files)])} />
              </div>
              {uploadFiles.length > 0 && (
                <div className="d-flex flex-wrap gap-2" style={{ marginTop: '8px' }}>
                  {uploadFiles.map((f, i) => (
                    <span key={i} className="d-flex align-items-center gap-1"
                      style={{ background: '#f1f5f9', borderRadius: '6px', padding: '2px 8px', fontSize: '11px', color: '#475569' }}>
                      <i className="fas fa-file" style={{ fontSize: '9px', color: '#94a3b8' }} />
                      {f.name}
                      <button type="button" className="btn-close" style={{ fontSize: '7px', marginLeft: '4px' }}
                        onClick={() => setUploadFiles((p) => p.filter((_, idx) => idx !== i))} />
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Messaggi */}
          <div className="card border-0 shadow-sm" style={cardStyle}>
            <div style={{ padding: '16px 16px 0' }}>
              <div style={sectionTitle}>
                <i className="ri-chat-3-line me-1" style={{ color: '#6366f1' }} />Messaggi
              </div>
            </div>
            <div style={{ padding: '0 16px', maxHeight: 350, overflowY: 'auto' }}>
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
            <div style={{ padding: '10px 16px 16px', borderTop: '1px solid #f1f5f9' }}>
              <form onSubmit={handleSendMessage} className="d-flex gap-2">
                <input
                  type="text"
                  className="form-control form-control-sm"
                  placeholder="Scrivi un messaggio..."
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  style={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '13px' }}
                />
                <button type="submit"
                  disabled={sending || !newMessage.trim()}
                  style={{
                    width: 34, height: 34, borderRadius: '8px', border: 'none', flexShrink: 0,
                    background: newMessage.trim() ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : '#e2e8f0',
                    color: newMessage.trim() ? '#fff' : '#94a3b8',
                    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                  {sending ? <span className="spinner-border spinner-border-sm" /> : <i className="fas fa-paper-plane" style={{ fontSize: '12px' }} />}
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Colonna destra - sidebar */}
        <div className="col-lg-4">
          {/* Stato + Priorita */}
          <div className="card border-0 shadow-sm" style={cardStyle}>
            <div style={{ padding: '14px 16px' }}>
              <div className="d-flex gap-3">
                <div style={{ flex: 1 }}>
                  <label style={{ ...sectionTitle, display: 'block', marginBottom: '4px' }}>
                    <i className="ri-flag-line me-1" style={{ color: '#6366f1' }} />Stato
                  </label>
                  <select
                    className="form-select form-select-sm"
                    value={ticket.status}
                    onChange={(e) => handleStatusChange(e.target.value)}
                    style={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                  >
                    {Object.entries(statusConfig).map(([k, v]) => (
                      <option key={k} value={k}>{v.label}</option>
                    ))}
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ ...sectionTitle, display: 'block', marginBottom: '4px' }}>
                    <i className="ri-fire-line me-1" style={{ color: '#6366f1' }} />Priorità
                  </label>
                  <select
                    className="form-select form-select-sm"
                    value={ticket.priority}
                    onChange={(e) => handlePriorityChange(e.target.value)}
                    style={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                  >
                    {Object.entries(priorityConfig).map(([k, v]) => (
                      <option key={k} value={k}>{v.label}</option>
                    ))}
                  </select>
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
                { label: 'Creato il', value: formatDate(ticket.created_at) },
                ...(ticket.resolved_at ? [{ label: 'Risolto il', value: formatDate(ticket.resolved_at) }] : []),
                ...(ticket.closed_at ? [{ label: 'Chiuso il', value: formatDate(ticket.closed_at) }] : []),
              ].map((row, i) => (
                <div key={i} className="d-flex justify-content-between align-items-center"
                  style={{ padding: '5px 0', borderBottom: '1px solid #f1f5f9' }}>
                  <span style={{ fontSize: '12px', color: '#64748b' }}>{row.label}</span>
                  <span style={{ fontSize: '12px', fontWeight: 500, color: '#1e293b' }}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Assegnatari */}
          <div className="card border-0 shadow-sm" style={cardStyle}>
            <div style={{ padding: '14px 16px' }}>
              <div style={sectionTitle}>
                <i className="ri-team-line me-1" style={{ color: '#6366f1' }} />Assegnatari
              </div>
              <div className="d-flex flex-wrap gap-1">
                {users.map((u) => {
                  const isAssigned = (ticket.assigned_users || []).some((a) => a.id === u.id);
                  return (
                    <button
                      key={u.id}
                      onClick={() => handleAssigneeToggle(u.id)}
                      style={{
                        borderRadius: '14px',
                        padding: '3px 10px',
                        border: isAssigned ? 'none' : '1px solid #e2e8f0',
                        background: isAssigned ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : '#fff',
                        color: isAssigned ? '#fff' : '#475569',
                        fontSize: '11px',
                        fontWeight: 500,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      {isAssigned && <i className="fas fa-check" style={{ fontSize: '8px' }} />}
                      {u.name}
                    </button>
                  );
                })}
              </div>
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

      {/* Delete Confirm Modal */}
      {showDeleteConfirm && (
        <>
          <div className="modal-backdrop fade show" style={{ zIndex: 1050 }} onClick={() => setShowDeleteConfirm(false)} />
          <div className="modal fade show d-block" style={{ zIndex: 1055 }} tabIndex="-1" onClick={() => setShowDeleteConfirm(false)}>
            <div className="modal-dialog modal-dialog-centered" onClick={(e) => e.stopPropagation()}>
              <div className="modal-content border-0" style={{ borderRadius: '14px', boxShadow: '0 20px 60px rgba(0,0,0,0.15)', height: 'auto' }}>
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

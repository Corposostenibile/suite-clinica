import React, { useState, useEffect, useRef, useCallback } from 'react'
import { kanbanService } from '../services/kanbanService'

const STATUS_LABELS = {
  aperto: 'Aperto',
  in_lavorazione: 'In Lavorazione',
  risolto: 'Risolto',
  chiuso: 'Chiuso',
}

const STATUS_COLORS = {
  aperto: '#3b82f6',
  in_lavorazione: '#f59e0b',
  risolto: '#10b981',
  chiuso: '#6b7280',
}

const PRIORITY_LABELS = { alta: 'Alta', media: 'Media', bassa: 'Bassa' }
const PRIORITY_COLORS = { alta: '#ef4444', media: '#f59e0b', bassa: '#10b981' }

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'ora'
  if (mins < 60) return `${mins} min fa`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h fa`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}g fa`
  return new Date(dateStr).toLocaleDateString('it-IT')
}

export default function TicketDetailPanel({ ticket, token, currentUserId, onClose, onUpdated }) {
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [replyText, setReplyText] = useState('')
  const [sending, setSending] = useState(false)
  const [uploading, setUploading] = useState(false)
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  // Fetch full ticket detail
  const fetchDetail = useCallback(async () => {
    try {
      setLoading(true)
      const data = await kanbanService.getTicket(token, ticket.id)
      setDetail(data)
    } catch (err) {
      console.error('Failed to load ticket detail:', err)
    } finally {
      setLoading(false)
    }
  }, [token, ticket.id])

  useEffect(() => {
    fetchDetail()
  }, [fetchDetail])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [detail?.messages])

  // Status action
  const changeStatus = async (newStatus) => {
    try {
      const updated = await kanbanService.updateStatus(token, ticket.id, newStatus)
      onUpdated(updated)
      fetchDetail()
    } catch (err) {
      console.error('Status change failed:', err)
    }
  }

  // Send reply
  const handleReply = async (e) => {
    e.preventDefault()
    if (!replyText.trim()) return
    setSending(true)
    try {
      await kanbanService.addMessage(token, ticket.id, replyText.trim())
      setReplyText('')
      fetchDetail()
    } catch (err) {
      console.error('Reply failed:', err)
    } finally {
      setSending(false)
    }
  }

  // Upload file
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await kanbanService.uploadAttachment(token, ticket.id, file)
      fetchDetail()
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  // Status action buttons
  const statusActions = () => {
    const s = ticket.status
    const actions = []
    if (s === 'aperto') {
      actions.push({ status: 'in_lavorazione', label: 'Prendi in Carico', icon: 'ri-play-line' })
    }
    if (s === 'in_lavorazione') {
      actions.push({ status: 'risolto', label: 'Segna Risolto', icon: 'ri-checkbox-circle-line' })
    }
    if (s === 'risolto') {
      actions.push({ status: 'chiuso', label: 'Chiudi', icon: 'ri-lock-line' })
    }
    if (s === 'risolto' || s === 'chiuso') {
      actions.push({ status: 'aperto', label: 'Riapri', icon: 'ri-refresh-line' })
    }
    return actions
  }

  return (
    <>
      <div className="kb-overlay" onClick={onClose} />
      <div className="kb-detail-panel">
        {/* Header */}
        <div className="kb-detail-header">
          <div className="kb-detail-header-left">
            <span className="kb-detail-number">{ticket.ticket_number}</span>
            <span
              className="kb-badge"
              style={{ backgroundColor: STATUS_COLORS[ticket.status] }}
            >
              {STATUS_LABELS[ticket.status]}
            </span>
            <span
              className="kb-badge kb-badge--outline"
              style={{ borderColor: PRIORITY_COLORS[ticket.priority], color: PRIORITY_COLORS[ticket.priority] }}
            >
              {PRIORITY_LABELS[ticket.priority]}
            </span>
          </div>
          <button className="kb-detail-close" onClick={onClose}>
            <i className="ri-close-line" />
          </button>
        </div>

        {loading ? (
          <div className="kb-detail-loading">
            <div className="kb-spinner" />
          </div>
        ) : detail ? (
          <div className="kb-detail-content">
            {/* Title + description */}
            <div className="kb-detail-section">
              <h2 className="kb-detail-title">
                {detail.title || 'Senza titolo'}
              </h2>
              <p className="kb-detail-desc">{detail.description}</p>
            </div>

            {/* Patient */}
            {detail.cliente_nome && (
              <div className="kb-detail-meta">
                <i className="ri-heart-pulse-line" />
                <span>Paziente: <strong>{detail.cliente_nome}</strong></span>
              </div>
            )}

            {/* Assignees */}
            <div className="kb-detail-section">
              <h3 className="kb-detail-label">Assegnatari</h3>
              <div className="kb-detail-assignees">
                {(detail.assigned_users || []).map(u => (
                  <span key={u.id} className="kb-detail-assignee">
                    <span className="kb-card-avatar">
                      {u.avatar
                        ? <img src={u.avatar} alt="" />
                        : u.name?.charAt(0).toUpperCase()
                      }
                    </span>
                    {u.name}
                  </span>
                ))}
                {(!detail.assigned_users || detail.assigned_users.length === 0) && (
                  <span className="kb-detail-empty">Nessun assegnatario</span>
                )}
              </div>
            </div>

            {/* Status actions */}
            <div className="kb-detail-actions">
              {statusActions().map(action => (
                <button
                  key={action.status}
                  className="kb-btn kb-btn--sm"
                  onClick={() => changeStatus(action.status)}
                >
                  <i className={action.icon} />
                  {action.label}
                </button>
              ))}
            </div>

            {/* Messages thread */}
            <div className="kb-detail-section">
              <h3 className="kb-detail-label">
                Messaggi ({detail.messages?.length || 0})
              </h3>
              <div className="kb-messages">
                {(detail.messages || []).map(msg => (
                  <div
                    key={msg.id}
                    className={`kb-message ${
                      msg.sender_id === currentUserId ? 'kb-message--mine' : ''
                    } ${msg.source === 'teams' ? 'kb-message--teams' : ''}`}
                  >
                    <div className="kb-message-header">
                      <strong>{msg.sender_name || 'Utente'}</strong>
                      <span className="kb-message-source">
                        {msg.source === 'teams' ? 'Teams' : 'Admin'}
                      </span>
                      <span className="kb-message-time">{timeAgo(msg.created_at)}</span>
                    </div>
                    <div className="kb-message-body">{msg.content}</div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              {/* Reply input */}
              <form className="kb-reply" onSubmit={handleReply}>
                <input
                  className="kb-reply-input"
                  placeholder="Scrivi una risposta..."
                  value={replyText}
                  onChange={e => setReplyText(e.target.value)}
                  disabled={sending}
                />
                <button
                  className="kb-btn kb-btn--primary kb-btn--sm"
                  type="submit"
                  disabled={!replyText.trim() || sending}
                >
                  <i className="ri-send-plane-line" />
                </button>
              </form>
            </div>

            {/* Attachments */}
            <div className="kb-detail-section">
              <h3 className="kb-detail-label">
                Allegati ({detail.attachments?.length || 0})
              </h3>
              <div className="kb-attachments">
                {(detail.attachments || []).map(att => (
                  <a
                    key={att.id}
                    className="kb-attachment"
                    href={`/api/team-tickets/tab/attachments/${att.id}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <i className={att.is_image ? 'ri-image-line' : 'ri-file-line'} />
                    <span>{att.filename}</span>
                  </a>
                ))}
              </div>
              <div className="kb-attachment-upload">
                <input
                  ref={fileInputRef}
                  type="file"
                  id="attachment-upload"
                  className="kb-file-input"
                  onChange={handleFileUpload}
                  disabled={uploading}
                />
                <label htmlFor="attachment-upload" className="kb-btn kb-btn--sm">
                  <i className={uploading ? 'ri-loader-4-line kb-spin' : 'ri-upload-line'} />
                  {uploading ? 'Upload...' : 'Carica file'}
                </label>
              </div>
            </div>

            {/* Status changes timeline */}
            {detail.status_changes && detail.status_changes.length > 0 && (
              <div className="kb-detail-section">
                <h3 className="kb-detail-label">Timeline</h3>
                <div className="kb-timeline">
                  {detail.status_changes.map(sc => (
                    <div key={sc.id} className="kb-timeline-item">
                      <div className="kb-timeline-dot" />
                      <div className="kb-timeline-content">
                        <span>
                          {sc.from_status
                            ? `${STATUS_LABELS[sc.from_status] || sc.from_status} → ${STATUS_LABELS[sc.to_status] || sc.to_status}`
                            : `Creato come ${STATUS_LABELS[sc.to_status] || sc.to_status}`
                          }
                        </span>
                        <span className="kb-timeline-meta">
                          {sc.changed_by_name || 'Sistema'} · {timeAgo(sc.created_at)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="kb-detail-error">Errore nel caricamento</div>
        )}
      </div>
    </>
  )
}

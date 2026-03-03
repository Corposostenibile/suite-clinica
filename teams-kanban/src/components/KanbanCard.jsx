import React from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

const PRIORITY_COLORS = {
  alta: '#ef4444',
  media: '#f59e0b',
  bassa: '#10b981',
}

const RELATIONSHIP_STYLES = {
  creator: { color: '#6366f1', label: 'Creato da te' },
  assignee: { color: '#f97316', label: 'Assegnato a te' },
  participant: { color: '#9ca3af', label: 'Partecipante' },
}

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

function Avatar({ name, avatar, className = '' }) {
  return (
    <span className={`kb-card-avatar ${className}`} title={name}>
      {avatar
        ? <img src={avatar} alt="" />
        : name?.charAt(0).toUpperCase()
      }
    </span>
  )
}

export default function KanbanCard({ ticket, onClick, isDragging }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortDragging,
  } = useSortable({ id: String(ticket.id) })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isSortDragging ? 0.4 : 1,
  }

  const rel = RELATIONSHIP_STYLES[ticket.relationship_to_user] || RELATIONSHIP_STYLES.participant
  const priorityColor = PRIORITY_COLORS[ticket.priority] || PRIORITY_COLORS.media

  const assignees = ticket.assigned_users || []

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`kb-card ${isDragging ? 'kb-card--dragging' : ''}`}
      onClick={onClick}
    >
      <div className="kb-card-border" style={{ backgroundColor: rel.color }} />

      <div className="kb-card-body">
        <div className="kb-card-top">
          <span
            className="kb-card-priority"
            style={{ backgroundColor: priorityColor }}
            title={ticket.priority}
          />
          <span className="kb-card-title">
            {ticket.title || ticket.description?.slice(0, 60)}
          </span>
        </div>

        {ticket.cliente_nome && (
          <div className="kb-card-patient">
            <i className="ri-heart-pulse-line" />
            {ticket.cliente_nome}
          </div>
        )}

        <div className="kb-card-footer">
          {/* Creator → Assignees flow */}
          <div className="kb-card-people">
            <Avatar
              name={ticket.created_by_name}
              avatar={ticket.created_by_avatar}
              className="kb-card-avatar--creator"
            />
            {assignees.length > 0 && (
              <>
                <i className="ri-arrow-right-s-line kb-card-arrow" />
                <div className="kb-card-avatars">
                  {assignees.slice(0, 3).map(u => (
                    <Avatar key={u.id} name={u.name} avatar={u.avatar} />
                  ))}
                  {assignees.length > 3 && (
                    <span className="kb-card-avatar kb-card-avatar--more">
                      +{assignees.length - 3}
                    </span>
                  )}
                </div>
              </>
            )}
          </div>

          <span className="kb-card-relation">{rel.label}</span>
          <span className="kb-card-time">{timeAgo(ticket.updated_at || ticket.created_at)}</span>
        </div>
      </div>
    </div>
  )
}

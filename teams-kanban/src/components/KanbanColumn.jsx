import React from 'react'
import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import KanbanCard from './KanbanCard'

export default function KanbanColumn({ status, config, tickets, onCardClick }) {
  const { setNodeRef, isOver } = useDroppable({ id: status })

  const ticketIds = tickets.map(t => String(t.id))

  return (
    <div
      className={`kb-column ${isOver ? 'kb-column--over' : ''}`}
      ref={setNodeRef}
    >
      <div className="kb-column-header" style={{ '--col-color': config.color }}>
        <div className="kb-column-title">
          <i className={config.icon} />
          <span>{config.label}</span>
        </div>
        <span className="kb-column-count">{tickets.length}</span>
      </div>

      <div className="kb-column-body">
        <SortableContext items={ticketIds} strategy={verticalListSortingStrategy}>
          {tickets.map(ticket => (
            <KanbanCard
              key={ticket.id}
              ticket={ticket}
              onClick={() => onCardClick(ticket)}
            />
          ))}
        </SortableContext>

        {tickets.length === 0 && (
          <div className="kb-column-empty">
            <i className="ri-inbox-line" />
            <span>Nessun ticket</span>
          </div>
        )}
      </div>
    </div>
  )
}

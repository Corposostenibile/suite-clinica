import React, { useState, useCallback } from 'react'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
} from '@dnd-kit/core'
import KanbanColumn from './KanbanColumn'
import KanbanCard from './KanbanCard'

const STATUS_CONFIG = {
  aperto: { label: 'Aperto', color: '#3b82f6', icon: 'ri-radio-button-line' },
  in_lavorazione: { label: 'In Lavorazione', color: '#f59e0b', icon: 'ri-loader-4-line' },
  standby: { label: 'Standby', color: '#8b5cf6', icon: 'ri-pause-circle-line' },
  risolto: { label: 'Risolto', color: '#10b981', icon: 'ri-checkbox-circle-line' },
  chiuso: { label: 'Chiuso', color: '#6b7280', icon: 'ri-lock-line' },
}

export default function KanbanBoard({ columns, loading, onStatusChange, onCardClick, statuses }) {
  const [activeTicket, setActiveTicket] = useState(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  )

  const handleDragStart = useCallback((event) => {
    const { active } = event
    // Find the ticket across all columns
    for (const tickets of Object.values(columns)) {
      const found = tickets.find(t => String(t.id) === String(active.id))
      if (found) {
        setActiveTicket(found)
        break
      }
    }
  }, [columns])

  const handleDragEnd = useCallback((event) => {
    const { active, over } = event
    setActiveTicket(null)

    if (!over) return

    // The droppable ID is the status name
    const newStatus = over.id
    const ticketId = Number(active.id)

    // Find current status
    let currentStatus = null
    for (const [status, tickets] of Object.entries(columns)) {
      if (tickets.some(t => t.id === ticketId)) {
        currentStatus = status
        break
      }
    }

    if (currentStatus && currentStatus !== newStatus) {
      onStatusChange(ticketId, newStatus)
    }
  }, [columns, onStatusChange])

  if (loading) {
    return (
      <div className="kb-board-loading">
        <div className="kb-spinner" />
        <p>Caricamento ticket...</p>
      </div>
    )
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="kb-board">
        {(statuses || Object.keys(STATUS_CONFIG)).map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            config={STATUS_CONFIG[status] || { label: status, color: '#6b7280', icon: 'ri-question-line' }}
            tickets={columns[status] || []}
            onCardClick={onCardClick}
          />
        ))}
        {(!statuses || statuses.length === 0) && Object.entries(STATUS_CONFIG).map(([status, config]) => (
          <KanbanColumn
            key={status}
            status={status}
            config={config}
            tickets={columns[status] || []}
            onCardClick={onCardClick}
          />
        ))}
      </div>

      <DragOverlay dropAnimation={null}>
        {activeTicket ? (
          <KanbanCard ticket={activeTicket} isDragging />
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}

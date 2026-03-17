import React, { useState, useEffect, useCallback, useRef, memo } from 'react'
import { useTeamsAuth } from './hooks/useTeamsAuth'
import { useTicketSocket } from './hooks/useTicketSocket'
import KanbanBoard from './components/KanbanBoard'
import TicketDetailPanel from './components/TicketDetailPanel'
import CreateTicketModal from './components/CreateTicketModal'
import FilterBar from './components/FilterBar'
import { kanbanService } from './services/kanbanService'

function getBoardKey() {
  try {
    const params = new URLSearchParams(window.location.search)
    return (params.get('board') || 'general').trim() || 'general'
  } catch {
    return 'general'
  }
}

const BOARD_CONFIG = {
  general: {
    title: 'Ticket Board',
    statuses: ['aperto', 'in_lavorazione', 'risolto', 'chiuso'],
    priorityOptions: [
      { value: '', label: 'Tutte' },
      { value: 'alta', label: 'Alta' },
      { value: 'media', label: 'Media' },
      { value: 'bassa', label: 'Bassa' },
    ],
  },
  it: {
    title: 'Ticket IT',
    statuses: ['aperto', 'in_lavorazione', 'standby', 'risolto'],
    priorityOptions: [
      { value: '', label: 'Tutte' },
      { value: 'bloccante', label: 'Bloccante' },
      { value: 'non_bloccante', label: 'Non bloccante' },
    ],
  },
}

export default function App() {
  const { user, token, loading: authLoading, error: authError, devLogin } = useTeamsAuth()
  const board = getBoardKey()
  const boardCfg = BOARD_CONFIG[board] || BOARD_CONFIG.general

  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // UI state
  const [selectedTicket, setSelectedTicket] = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  // Filters
  const [filters, setFilters] = useState({
    scope: 'all',       // all | created | assigned
    search: '',
    priority: '',       // '' | <board-specific>
  })

  // Ref to keep tickets current in socket callbacks
  const ticketsRef = useRef(tickets)
  ticketsRef.current = tickets

  // Fetch tickets
  const fetchTickets = useCallback(async () => {
    if (!token) return
    try {
      setLoading(true)
      const data = await kanbanService.listTickets(token, { board })
      setTickets(data)
      setError(null)
    } catch (err) {
      setError('Errore nel caricamento dei ticket')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [token, board])

  useEffect(() => {
    if (token) fetchTickets()
  }, [token, fetchTickets])

  // Socket handlers
  const handleTicketEvent = useCallback((event, data) => {
    const ticket = data.ticket
    if (!ticket) return

    if (event === 'ticket_created') {
      setTickets(prev => {
        if (prev.some(t => t.id === ticket.id)) return prev
        return [ticket, ...prev]
      })
    } else if (event === 'ticket_updated' || event === 'ticket_status_changed') {
      setTickets(prev => prev.map(t => t.id === ticket.id ? ticket : t))
      // Update detail panel if open
      setSelectedTicket(prev => prev?.id === ticket.id ? ticket : prev)
    }
  }, [])

  useTicketSocket(token, handleTicketEvent)

  // Status change (drag-and-drop)
  const handleStatusChange = useCallback(async (ticketId, newStatus) => {
    const prev = ticketsRef.current
    // Optimistic update
    setTickets(tickets =>
      tickets.map(t => t.id === ticketId ? { ...t, status: newStatus } : t)
    )
    try {
      const updated = await kanbanService.updateStatus(token, ticketId, newStatus)
      setTickets(tickets =>
        tickets.map(t => t.id === ticketId ? updated : t)
      )
    } catch (err) {
      // Rollback
      setTickets(prev)
      console.error('Status change failed:', err)
    }
  }, [token])

  // Ticket created
  const handleTicketCreated = useCallback((ticket) => {
    setTickets(prev => [ticket, ...prev])
    setShowCreate(false)
  }, [])

  // Ticket updated from detail panel
  const handleTicketUpdated = useCallback((ticket) => {
    setTickets(prev => prev.map(t => t.id === ticket.id ? ticket : t))
    setSelectedTicket(ticket)
  }, [])

  // Apply client-side filters
  const filteredTickets = tickets.filter(t => {
    // Scope filter
    if (filters.scope === 'created' && t.relationship_to_user !== 'creator') return false
    if (filters.scope === 'assigned' && t.relationship_to_user !== 'assignee') return false

    // Priority filter
    if (filters.priority && t.priority !== filters.priority) return false

    // Search filter
    if (filters.search) {
      const q = filters.search.toLowerCase()
      const matchTitle = t.title?.toLowerCase().includes(q)
      const matchDesc = t.description?.toLowerCase().includes(q)
      const matchNumber = t.ticket_number?.toLowerCase().includes(q)
      const matchPatient = t.cliente_nome?.toLowerCase().includes(q)
      if (!matchTitle && !matchDesc && !matchNumber && !matchPatient) return false
    }

    return true
  })

  const sortedTickets = [...filteredTickets].sort((a, b) => {
    if (board === 'it') {
      const ap = a.priority === 'bloccante' ? 0 : 1
      const bp = b.priority === 'bloccante' ? 0 : 1
      if (ap !== bp) return ap - bp
    }
    const at = new Date(a.updated_at || a.created_at || 0).getTime()
    const bt = new Date(b.updated_at || b.created_at || 0).getTime()
    return bt - at
  })

  // Group by status
  const columns = boardCfg.statuses.reduce((acc, status) => {
    acc[status] = sortedTickets.filter(t => t.status === status)
    return acc
  }, {})

  // Auth loading
  if (authLoading) {
    return (
      <div className="kb-loading">
        <div className="kb-spinner" />
        <p>Accesso in corso...</p>
      </div>
    )
  }

  // Dev login fallback
  if (authError === 'DEV_LOGIN') {
    return <DevLogin onLogin={devLogin} />
  }

  // Auth error
  if (authError) {
    return (
      <div className="kb-error">
        <i className="ri-error-warning-line" />
        <h2>Errore di autenticazione</h2>
        <p>{authError}</p>
      </div>
    )
  }

  return (
    <div className="kb-app">
      <header className="kb-header">
        <div className="kb-header-left">
          <h1 className="kb-title">{boardCfg.title}</h1>
          <span className="kb-ticket-count">{tickets.length} ticket</span>
        </div>
        <div className="kb-header-right">
          {user && (
            <span className="kb-user-name">
              <i className="ri-user-line" />
              {user.name}
            </span>
          )}
        </div>
      </header>

      <FilterBar
        filters={filters}
        onChange={setFilters}
        onCreateClick={() => setShowCreate(true)}
        board={board}
        priorityOptions={boardCfg.priorityOptions}
      />

      {error && (
        <div className="kb-error-bar">
          <i className="ri-error-warning-line" />
          {error}
          <button onClick={fetchTickets}>Riprova</button>
        </div>
      )}

      <KanbanBoard
        columns={columns}
        loading={loading}
        onStatusChange={handleStatusChange}
        onCardClick={setSelectedTicket}
        statuses={boardCfg.statuses}
      />

      {selectedTicket && (
        <TicketDetailPanel
          ticket={selectedTicket}
          token={token}
          currentUserId={user?.id}
          onClose={() => setSelectedTicket(null)}
          onUpdated={handleTicketUpdated}
          board={board}
        />
      )}

      {showCreate && (
        <CreateTicketModal
          token={token}
          onClose={() => setShowCreate(false)}
          onCreated={handleTicketCreated}
          board={board}
        />
      )}
    </div>
  )
}

/** Dev-only login form (when not inside Teams) */
function DevLogin({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    onLogin(username, password)
  }

  return (
    <div className="kb-dev-login">
      <h2>Ticket Board — Dev Login</h2>
      <p>Teams SSO non disponibile. Login con credenziali Suite.</p>
      <form onSubmit={handleSubmit}>
        <input
          className="kb-form-input"
          placeholder="Username o email"
          value={username}
          onChange={e => setUsername(e.target.value)}
          autoFocus
        />
        <input
          className="kb-form-input"
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
        />
        <button className="kb-btn kb-btn--primary" type="submit">
          Accedi
        </button>
      </form>
    </div>
  )
}

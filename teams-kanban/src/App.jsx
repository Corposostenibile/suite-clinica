import React, { useState, useEffect, useCallback, useRef, memo } from 'react'
import { useTeamsAuth } from './hooks/useTeamsAuth'
import { useTicketSocket } from './hooks/useTicketSocket'
import KanbanBoard from './components/KanbanBoard'
import TicketDetailPanel from './components/TicketDetailPanel'
import CreateTicketModal from './components/CreateTicketModal'
import FilterBar from './components/FilterBar'
import { kanbanService } from './services/kanbanService'

const STATUSES = ['aperto', 'in_lavorazione', 'risolto', 'chiuso']

export default function App() {
  const { user, token, loading: authLoading, error: authError, devLogin } = useTeamsAuth()

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
    priority: '',       // '' | alta | media | bassa
  })

  // Ref to keep tickets current in socket callbacks
  const ticketsRef = useRef(tickets)
  ticketsRef.current = tickets

  // Fetch tickets
  const fetchTickets = useCallback(async () => {
    if (!token) return
    try {
      setLoading(true)
      const data = await kanbanService.listTickets(token)
      setTickets(data)
      setError(null)
    } catch (err) {
      setError('Errore nel caricamento dei ticket')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [token])

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

  // Group by status
  const columns = STATUSES.reduce((acc, status) => {
    acc[status] = filteredTickets.filter(t => t.status === status)
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
          <h1 className="kb-title">Ticket Board</h1>
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
      />

      {selectedTicket && (
        <TicketDetailPanel
          ticket={selectedTicket}
          token={token}
          currentUserId={user?.id}
          onClose={() => setSelectedTicket(null)}
          onUpdated={handleTicketUpdated}
        />
      )}

      {showCreate && (
        <CreateTicketModal
          token={token}
          onClose={() => setShowCreate(false)}
          onCreated={handleTicketCreated}
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

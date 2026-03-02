import React, { useState, useEffect, useRef, useCallback } from 'react'
import { kanbanService } from '../services/kanbanService'

export default function CreateTicketModal({ token, onClose, onCreated }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('media')
  const [assigneeId, setAssigneeId] = useState('')
  const [clienteId, setClienteId] = useState('')
  const [clienteSearch, setClienteSearch] = useState('')
  const [clienteResults, setClienteResults] = useState([])

  const [users, setUsers] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const searchTimeout = useRef(null)

  // Load assignable users
  useEffect(() => {
    kanbanService.getUsers(token).then(setUsers).catch(() => {})
  }, [token])

  // Patient typeahead
  const searchPatients = useCallback((q) => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    if (q.length < 2) {
      setClienteResults([])
      return
    }
    searchTimeout.current = setTimeout(async () => {
      try {
        const results = await kanbanService.searchPatients(token, q)
        setClienteResults(results)
      } catch {
        setClienteResults([])
      }
    }, 300)
  }, [token])

  const handleClienteSearch = (value) => {
    setClienteSearch(value)
    setClienteId('')
    searchPatients(value)
  }

  const selectPatient = (patient) => {
    setClienteId(patient.id)
    setClienteSearch(patient.nome)
    setClienteResults([])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!title.trim() || !description.trim()) {
      setError('Titolo e descrizione sono obbligatori')
      return
    }

    setSubmitting(true)
    setError('')
    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        priority,
      }
      if (assigneeId) payload.assignee_ids = [Number(assigneeId)]
      if (clienteId) payload.cliente_id = Number(clienteId)

      const ticket = await kanbanService.createTicket(token, payload)
      onCreated(ticket)
    } catch (err) {
      setError(err.response?.data?.error || 'Errore nella creazione')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="kb-overlay" onClick={onClose} />
      <div className="kb-modal">
        <div className="kb-modal-header">
          <h2>Nuovo Ticket</h2>
          <button className="kb-detail-close" onClick={onClose}>
            <i className="ri-close-line" />
          </button>
        </div>

        <form className="kb-modal-body" onSubmit={handleSubmit}>
          {error && (
            <div className="kb-form-error">
              <i className="ri-error-warning-line" />
              {error}
            </div>
          )}

          {/* Title */}
          <div className="kb-form-group">
            <label className="kb-form-label">Titolo *</label>
            <input
              className="kb-form-input"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Breve descrizione del problema"
              autoFocus
            />
          </div>

          {/* Description */}
          <div className="kb-form-group">
            <label className="kb-form-label">Descrizione *</label>
            <textarea
              className="kb-form-textarea"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Descrivi il problema in dettaglio..."
              rows={4}
            />
          </div>

          {/* Priority */}
          <div className="kb-form-group">
            <label className="kb-form-label">Priorita'</label>
            <div className="kb-priority-group">
              {[
                { value: 'alta', label: 'Alta', color: '#ef4444' },
                { value: 'media', label: 'Media', color: '#f59e0b' },
                { value: 'bassa', label: 'Bassa', color: '#10b981' },
              ].map(p => (
                <button
                  key={p.value}
                  type="button"
                  className={`kb-priority-btn ${priority === p.value ? 'kb-priority-btn--active' : ''}`}
                  style={{ '--pri-color': p.color }}
                  onClick={() => setPriority(p.value)}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Assignee */}
          <div className="kb-form-group">
            <label className="kb-form-label">Assegnatario</label>
            <select
              className="kb-form-input"
              value={assigneeId}
              onChange={e => setAssigneeId(e.target.value)}
            >
              <option value="">Nessuno</option>
              {users.map(u => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          </div>

          {/* Patient typeahead */}
          <div className="kb-form-group">
            <label className="kb-form-label">Paziente</label>
            <div className="kb-typeahead">
              <input
                className="kb-form-input"
                value={clienteSearch}
                onChange={e => handleClienteSearch(e.target.value)}
                placeholder="Cerca paziente..."
              />
              {clienteResults.length > 0 && (
                <div className="kb-typeahead-results">
                  {clienteResults.map(p => (
                    <button
                      key={p.id}
                      type="button"
                      className="kb-typeahead-item"
                      onClick={() => selectPatient(p)}
                    >
                      <strong>{p.nome}</strong>
                      {p.email && <span>{p.email}</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="kb-modal-footer">
            <button
              type="button"
              className="kb-btn"
              onClick={onClose}
              disabled={submitting}
            >
              Annulla
            </button>
            <button
              type="submit"
              className="kb-btn kb-btn--primary"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <i className="ri-loader-4-line kb-spin" />
                  Creazione...
                </>
              ) : (
                <>
                  <i className="ri-add-line" />
                  Crea Ticket
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

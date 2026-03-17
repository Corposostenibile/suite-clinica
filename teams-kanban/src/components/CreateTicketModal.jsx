import React, { useState, useRef, useCallback } from 'react'
import { kanbanService } from '../services/kanbanService'

const IT_SYSTEM_OPTIONS = [
  { value: 'suite_clinica', label: 'Suite Clinica' },
  { value: 'ghl', label: 'GHL' },
  { value: 'respondio', label: 'Respond.io' },
  { value: 'teams', label: 'Teams' },
  { value: 'manychat', label: 'Manychat' },
]

export default function CreateTicketModal({ token, onClose, onCreated, board = 'general' }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState(board === 'it' ? 'non_bloccante' : 'media')
  const [system, setSystem] = useState('suite_clinica')
  const [file, setFile] = useState(null)

  // Assignee typeahead
  const [assigneeId, setAssigneeId] = useState('')
  const [assigneeSearch, setAssigneeSearch] = useState('')
  const [assigneeResults, setAssigneeResults] = useState([])

  // Patient typeahead
  const [clienteId, setClienteId] = useState('')
  const [clienteSearch, setClienteSearch] = useState('')
  const [clienteResults, setClienteResults] = useState([])

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const assigneeTimeout = useRef(null)
  const clienteTimeout = useRef(null)

  // Assignee typeahead search
  const searchAssignees = useCallback((q) => {
    if (assigneeTimeout.current) clearTimeout(assigneeTimeout.current)
    if (q.length < 2) {
      setAssigneeResults([])
      return
    }
    assigneeTimeout.current = setTimeout(async () => {
      try {
        const results = await kanbanService.searchUsers(token, q)
        setAssigneeResults(results)
      } catch {
        setAssigneeResults([])
      }
    }, 300)
  }, [token])

  const handleAssigneeSearch = (value) => {
    setAssigneeSearch(value)
    setAssigneeId('')
    searchAssignees(value)
  }

  const selectAssignee = (user) => {
    setAssigneeId(user.id)
    setAssigneeSearch(user.name)
    setAssigneeResults([])
  }

  // Patient typeahead search
  const searchPatients = useCallback((q) => {
    if (clienteTimeout.current) clearTimeout(clienteTimeout.current)
    if (q.length < 2) {
      setClienteResults([])
      return
    }
    clienteTimeout.current = setTimeout(async () => {
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
    if (board === 'it' && !system) {
      setError('Sistema obbligatorio')
      return
    }

    setSubmitting(true)
    setError('')
    try {
      const payload = {
        title: title.trim(),
        description: description.trim(),
        priority,
        board,
      }
      if (board === 'it') {
        payload.system = system
      } else {
        if (assigneeId) payload.assignee_ids = [Number(assigneeId)]
        if (clienteId) payload.cliente_id = Number(clienteId)
      }

      const ticket = await kanbanService.createTicket(token, payload)
      if (file) {
        try {
          await kanbanService.uploadAttachment(token, ticket.id, file)
        } catch (err) {
          console.error('Upload failed:', err)
        }
      }
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
              {(board === 'it'
                ? [
                  { value: 'bloccante', label: 'Bloccante', color: '#ef4444' },
                  { value: 'non_bloccante', label: 'Non bloccante', color: '#10b981' },
                ]
                : [
                  { value: 'alta', label: 'Alta', color: '#ef4444' },
                  { value: 'media', label: 'Media', color: '#f59e0b' },
                  { value: 'bassa', label: 'Bassa', color: '#10b981' },
                ]
              ).map(p => (
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

          {board === 'it' ? (
            <>
              <div className="kb-form-group">
                <label className="kb-form-label">Sistema *</label>
                <select
                  className="kb-select"
                  value={system}
                  onChange={e => setSystem(e.target.value)}
                >
                  {IT_SYSTEM_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div className="kb-form-group">
                <label className="kb-form-label">Allegato</label>
                <input
                  type="file"
                  className="kb-form-input"
                  onChange={e => setFile(e.target.files?.[0] || null)}
                />
              </div>
            </>
          ) : (
            <>
              {/* Assignee typeahead */}
              <div className="kb-form-group">
                <label className="kb-form-label">Assegnatario</label>
                <div className="kb-typeahead">
                  <input
                    className="kb-form-input"
                    value={assigneeSearch}
                    onChange={e => handleAssigneeSearch(e.target.value)}
                    placeholder="Cerca per nome o email..."
                  />
                  {assigneeResults.length > 0 && (
                    <div className="kb-typeahead-results">
                      {assigneeResults.map(u => (
                        <button
                          key={u.id}
                          type="button"
                          className="kb-typeahead-item"
                          onClick={() => selectAssignee(u)}
                        >
                          <strong>{u.name}</strong>
                          <span>{u.email}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
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
            </>
          )}

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

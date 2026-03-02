import React from 'react'

const SCOPE_OPTIONS = [
  { value: 'all', label: 'Tutti' },
  { value: 'created', label: 'Creati da me' },
  { value: 'assigned', label: 'Assegnati a me' },
]

const PRIORITY_OPTIONS = [
  { value: '', label: 'Tutte' },
  { value: 'alta', label: 'Alta' },
  { value: 'media', label: 'Media' },
  { value: 'bassa', label: 'Bassa' },
]

export default function FilterBar({ filters, onChange, onCreateClick }) {
  const setField = (field, value) => {
    onChange({ ...filters, [field]: value })
  }

  return (
    <div className="kb-filters">
      <div className="kb-filters-left">
        {/* Scope toggle */}
        <div className="kb-toggle-group">
          {SCOPE_OPTIONS.map(opt => (
            <button
              key={opt.value}
              className={`kb-toggle ${filters.scope === opt.value ? 'kb-toggle--active' : ''}`}
              onClick={() => setField('scope', opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="kb-search">
          <i className="ri-search-line" />
          <input
            type="text"
            placeholder="Cerca ticket..."
            value={filters.search}
            onChange={e => setField('search', e.target.value)}
          />
          {filters.search && (
            <button
              className="kb-search-clear"
              onClick={() => setField('search', '')}
            >
              <i className="ri-close-line" />
            </button>
          )}
        </div>

        {/* Priority filter */}
        <select
          className="kb-select"
          value={filters.priority}
          onChange={e => setField('priority', e.target.value)}
        >
          {PRIORITY_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>
              {opt.value ? `${opt.label} priorita'` : opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="kb-filters-right">
        <button className="kb-btn kb-btn--primary" onClick={onCreateClick}>
          <i className="ri-add-line" />
          Nuovo Ticket
        </button>
      </div>
    </div>
  )
}

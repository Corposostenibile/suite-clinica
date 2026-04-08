import { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useOutletContext } from 'react-router-dom';
import ghlService from '../../services/ghlService';
import './Calendario.css';

function Calendario() {
  const { user } = useOutletContext();
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creatingEvent, setCreatingEvent] = useState(false);
  const [createEventError, setCreateEventError] = useState('');
  const [createEventSuccess, setCreateEventSuccess] = useState('');
  const [customerSearch, setCustomerSearch] = useState('');
  const [customerSearchResults, setCustomerSearchResults] = useState([]);
  const [searchingCustomers, setSearchingCustomers] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [newEventForm, setNewEventForm] = useState(() => {
    const now = new Date();
    return {
      title: '',
      date: now.toISOString().slice(0, 10),
      time: '09:00',
      duration_minutes: 30,
      notes: '',
      timezone: 'Europe/Rome',
    };
  });
  const [teamMembers, setTeamMembers] = useState([]);
  const [selectedMemberId, setSelectedMemberId] = useState(null);
  const [memberSearch, setMemberSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef(null);
  const [currentWeekStart, setCurrentWeekStart] = useState(() => {
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(now.getFullYear(), now.getMonth(), diff);
  });

  const isAdmin = user?.is_admin || user?.role === 'admin';
  const isTeamLeader = user?.role === 'team_leader' && !isAdmin;
  const canFilter = isAdmin || isTeamLeader;

  const formatDate = (d) => d.toISOString().split('T')[0];

  const getDefaultEventForm = useCallback(() => {
    const now = new Date();
    const minutes = now.getMinutes() < 30 ? '30' : '00';
    const hours = minutes === '30' ? now.getHours() : now.getHours() + 1;
    const paddedHours = String(hours).padStart(2, '0');
    return {
      title: '',
      date: now.toISOString().slice(0, 10),
      time: `${paddedHours}:${minutes}`,
      duration_minutes: 30,
      notes: '',
      timezone: 'Europe/Rome',
    };
  }, []);

  const getWeekEnd = (start) => {
    const end = new Date(start);
    end.setDate(end.getDate() + 6);
    return end;
  };

  // Fetch team members for filter (admin/team_leader only)
  useEffect(() => {
    if (!canFilter) return;
    ghlService.getCalendarTeamMembers().then((res) => {
      if (res.success && res.members?.length > 0) {
        setTeamMembers(res.members);
      }
    }).catch(() => {});
  }, [canFilter]);

  // Close search dropdown on click outside
  useEffect(() => {
    const handler = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const checkConnection = useCallback(async () => {
    try {
      const status = await ghlService.getConnectionStatus();
      setConnected(status.is_connected);
      return status.is_connected;
    } catch {
      setConnected(false);
      return false;
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (selectedMemberId) {
        // Viewing another member's calendar - skip own connection check
        setConnected(true);
      } else if (canFilter) {
        // Admin/TL without a member selected - show empty grid with filter
        setConnected(true);
        setEvents([]);
        setLoading(false);
        return;
      } else {
        // Normal user - check own connection
        const isConnected = await checkConnection();
        if (!isConnected) {
          setLoading(false);
          return;
        }
      }
      const start = formatDate(currentWeekStart);
      const end = formatDate(getWeekEnd(currentWeekStart));
      const response = await ghlService.getEvents(start, end, selectedMemberId);
      const sorted = (response.events || []).sort(
        (a, b) => new Date(a.start) - new Date(b.start)
      );
      setEvents(sorted);
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.message || 'Errore nel caricamento eventi');
    } finally {
      setLoading(false);
    }
  }, [currentWeekStart, checkConnection, selectedMemberId, canFilter]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  useEffect(() => {
    if (!showCreateModal) return;
    const query = customerSearch.trim();
    if (query.length < 2) {
      setCustomerSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setSearchingCustomers(true);
      try {
        const res = await ghlService.searchCustomers(query, 8);
        setCustomerSearchResults(Array.isArray(res.customers) ? res.customers : []);
      } catch {
        setCustomerSearchResults([]);
      } finally {
        setSearchingCustomers(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [customerSearch, showCreateModal]);

  const openCreateModal = () => {
    setCreateEventError('');
    setCreateEventSuccess('');
    setSelectedCustomer(null);
    setCustomerSearch('');
    setCustomerSearchResults([]);
    setNewEventForm(getDefaultEventForm());
    setShowCreateModal(true);
  };

  const handleCreateCalendarEvent = async () => {
    setCreateEventError('');
    setCreateEventSuccess('');

    if (!newEventForm.date || !newEventForm.time) {
      setCreateEventError('Data e orario sono obbligatori.');
      return;
    }

    const start = new Date(`${newEventForm.date}T${newEventForm.time}`);
    if (Number.isNaN(start.getTime())) {
      setCreateEventError('Formato data/ora non valido.');
      return;
    }

    setCreatingEvent(true);
    try {
      const payload = {
        title: newEventForm.title,
        start_time: start.toISOString(),
        duration_minutes: Number(newEventForm.duration_minutes) || 30,
        notes: newEventForm.notes,
        timezone: newEventForm.timezone || 'Europe/Rome',
        user_id: selectedMemberId || undefined,
        cliente_id: selectedCustomer?.cliente_id || undefined,
      };

      const res = await ghlService.createCalendarEvent(payload);
      if (!res?.success) {
        setCreateEventError(res?.message || 'Errore durante la creazione evento.');
        return;
      }

      setCreateEventSuccess(res.mocked
        ? 'Mock mode attivo: evento simulato (nessuna creazione reale su GHL).'
        : 'Evento creato con successo.');
      await fetchEvents();
      setTimeout(() => setShowCreateModal(false), 700);
    } catch (err) {
      setCreateEventError(err.response?.data?.message || 'Errore durante la creazione evento.');
    } finally {
      setCreatingEvent(false);
    }
  };

  const prevWeek = () => {
    setCurrentWeekStart((prev) => {
      const d = new Date(prev);
      d.setDate(d.getDate() - 7);
      return d;
    });
  };

  const nextWeek = () => {
    setCurrentWeekStart((prev) => {
      const d = new Date(prev);
      d.setDate(d.getDate() + 7);
      return d;
    });
  };

  const goToday = () => {
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    setCurrentWeekStart(new Date(now.getFullYear(), now.getMonth(), diff));
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
  };

  const formatFullDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('it-IT', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
    });
  };

  const getDuration = (start, end) => {
    if (!start || !end) return null;
    const diff = Math.round((new Date(end) - new Date(start)) / 60000);
    if (diff < 60) return `${diff} min`;
    const h = Math.floor(diff / 60);
    const m = diff % 60;
    return m > 0 ? `${h}h ${m}min` : `${h}h`;
  };

  const weekLabel = () => {
    const start = currentWeekStart;
    const end = getWeekEnd(start);
    const opts = { day: 'numeric', month: 'long' };
    return `${start.toLocaleDateString('it-IT', opts)} - ${end.toLocaleDateString('it-IT', opts)} ${end.getFullYear()}`;
  };

  // Group events by day
  const eventsByDay = events.reduce((acc, ev) => {
    const day = new Date(ev.start).toDateString();
    if (!acc[day]) acc[day] = [];
    acc[day].push(ev);
    return acc;
  }, {});

  // Build all 7 days
  const weekDays = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(currentWeekStart);
    d.setDate(d.getDate() + i);
    weekDays.push(d);
  }

  const statusConfig = {
    scheduled:  { color: '#3b82f6', label: 'Programmato', bg: 'rgba(59, 130, 246, 0.08)' },
    confirmed:  { color: '#3b82f6', label: 'Confermato', bg: 'rgba(59, 130, 246, 0.08)' },
    completed:  { color: '#25B36A', label: 'Completato', bg: 'rgba(37, 179, 106, 0.08)' },
    cancelled:  { color: '#94a3b8', label: 'Cancellato', bg: 'rgba(148, 163, 184, 0.08)' },
    no_show:    { color: '#ef4444', label: 'No Show', bg: 'rgba(239, 68, 68, 0.08)' },
    noshow:     { color: '#ef4444', label: 'No Show', bg: 'rgba(239, 68, 68, 0.08)' },
  };

  const getStatus = (status) => statusConfig[(status || '').toLowerCase()] || { color: '#3b82f6', label: status || 'Programmato', bg: 'rgba(59, 130, 246, 0.08)' };

  const calendarColors = {
    'call 1to1 iniziale': '#f59e0b',
    'call 1to1':          '#3b82f6',
  };

  const getEventColor = (ev) => {
    const calName = (ev.ghl_calendar_name || '').toLowerCase().trim();
    for (const [key, color] of Object.entries(calendarColors)) {
      if (calName.includes(key)) return color;
    }
    return '#25B36A';
  };

  // Get the viewed member info (for avatar in modal when viewing another user)
  const viewedMember = selectedMemberId
    ? teamMembers.find((m) => m.id === selectedMemberId)
    : null;
  const avatarUser = viewedMember || user;

  // Not connected - only show for non-admin/non-TL users
  if (!loading && !connected && !selectedMemberId && !canFilter) {
    return (
      <div className="cal-page">
        <div className="cal-empty-state">
          <div className="cal-empty-icon">
            <i className="ri-calendar-close-line"></i>
          </div>
          <h3 className="cal-empty-title">Calendario non collegato</h3>
          <p className="cal-empty-desc">
            Il tuo account non e' ancora associato al Calendario.
            <br />
            Ti chiediamo cortesemente di aprire un ticket a <strong>Emanuele Mastronardi</strong>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="cal-page">
      {/* Header */}
      <div className="cal-header">
        <div className="cal-header-left">
          <h4 className="cal-header-title">Calendario</h4>
          <span className="cal-week-label">{weekLabel()}</span>
        </div>
        <div className="cal-header-actions">
          {/* Admin: search bar */}
          {isAdmin && teamMembers.length > 0 && (
            <div className="cal-search-wrap" ref={searchRef}>
              <div className="cal-search-input-wrap">
                <i className="ri-search-line cal-search-icon"></i>
                <input
                  type="text"
                  className="cal-search-input"
                  placeholder="Cerca membro del team..."
                  value={memberSearch}
                  autoComplete="off"
                  name="cal-member-search"
                  data-lpignore="true"
                  data-1p-ignore="true"
                  onChange={(e) => {
                    setMemberSearch(e.target.value);
                    setSearchOpen(true);
                  }}
                  onFocus={() => setSearchOpen(true)}
                />
                {selectedMemberId && (
                  <button
                    className="cal-search-clear"
                    onClick={() => {
                      setSelectedMemberId(null);
                      setMemberSearch('');
                      setSearchOpen(false);
                    }}
                    title="Torna al mio calendario"
                  >
                    <i className="ri-close-line"></i>
                  </button>
                )}
              </div>
              {searchOpen && memberSearch.trim().length > 0 && (() => {
                const q = memberSearch.toLowerCase();
                const filtered = teamMembers.filter((m) =>
                  m.full_name.toLowerCase().includes(q)
                );
                return filtered.length > 0 ? (
                  <div className="cal-search-dropdown">
                    {filtered.map((m) => (
                      <div
                        key={m.id}
                        className={`cal-search-item ${m.id === selectedMemberId ? 'active' : ''}`}
                        onClick={() => {
                          setSelectedMemberId(m.id);
                          setMemberSearch(m.full_name);
                          setSearchOpen(false);
                        }}
                      >
                        {m.avatar_path ? (
                          <img src={m.avatar_path} alt="" className="cal-search-item-avatar cal-search-item-avatar-img" />
                        ) : (
                          <span className="cal-search-item-avatar">
                            {m.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                          </span>
                        )}
                        <span className="cal-search-item-name">{m.full_name}</span>
                        {m.specialty && (
                          <span className="cal-search-item-spec">{m.specialty}</span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : null;
              })()}
            </div>
          )}

          {/* Team leader: dropdown */}
          {isTeamLeader && teamMembers.length > 0 && (
            <select
              className="cal-member-select"
              value={selectedMemberId || ''}
              onChange={(e) => {
                const val = e.target.value ? Number(e.target.value) : null;
                setSelectedMemberId(val);
              }}
            >
              <option value="">Il mio calendario</option>
              {teamMembers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name}
                </option>
              ))}
            </select>
          )}
          <button className="cal-nav-btn" onClick={prevWeek}>
            <i className="ri-arrow-left-s-line"></i>
          </button>
          <button className="cal-nav-btn cal-nav-today" onClick={goToday}>
            Oggi
          </button>
          <button className="cal-nav-btn" onClick={nextWeek}>
            <i className="ri-arrow-right-s-line"></i>
          </button>
          <button className="cal-nav-btn" onClick={fetchEvents} title="Aggiorna">
            <i className="ri-refresh-line"></i>
          </button>
          <button className="cal-nav-btn cal-nav-today" onClick={openCreateModal} title="Crea evento">
            <i className="ri-add-line"></i>
            Nuovo evento
          </button>
        </div>
      </div>

      {/* Viewing indicator */}
      {viewedMember && (
        <div className="cal-viewing-badge">
          {viewedMember.avatar_path ? (
            <img src={viewedMember.avatar_path} alt="" className="cal-viewing-avatar cal-viewing-avatar-img" />
          ) : (
            <span className="cal-viewing-avatar">
              {viewedMember.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
            </span>
          )}
          <span>Stai visualizzando il calendario di <strong>{viewedMember.full_name}</strong></span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="cal-alert cal-alert-danger">
          <i className="ri-error-warning-line"></i> {error}
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="cal-loading-wrap">
          <div className="cal-spinner"></div>
          <p className="cal-loading-text">Caricamento eventi...</p>
        </div>
      ) : (
        <>
          {/* Week Grid */}
          <div className="cal-week-card">
            <div className="cal-week-grid">
              {weekDays.map((day) => {
                const dayKey = day.toDateString();
                const dayEvents = eventsByDay[dayKey] || [];
                const isToday = new Date().toDateString() === dayKey;

                return (
                  <div key={dayKey} className={`cal-day-col ${isToday ? 'cal-day-today' : ''}`}>
                    <div className="cal-day-header">
                      <span className="cal-day-name">
                        {day.toLocaleDateString('it-IT', { weekday: 'short' })}
                      </span>
                      <span className={`cal-day-num ${isToday ? 'cal-today-num' : ''}`}>
                        {day.getDate()}
                      </span>
                    </div>
                    <div className="cal-day-body">
                      {dayEvents.length === 0 ? (
                        <div className="cal-day-empty">&mdash;</div>
                      ) : (
                        dayEvents.map((ev) => {
                          const evColor = getEventColor(ev);
                          return (
                            <div
                              key={ev.id}
                              className="cal-event"
                              onClick={() => setSelectedEvent(ev)}
                            >
                              <div className="cal-ev-row">
                                <span className="cal-ev-dot" style={{ background: evColor }}></span>
                                <span className="cal-ev-time">{formatTime(ev.start)}</span>
                                {ev.meetingLink && (
                                  <span className="cal-ev-meet" title="Ha link meeting">
                                    <i className="ri-video-chat-line"></i>
                                  </span>
                                )}
                              </div>
                              <div className="cal-ev-title">{ev.title || 'Senza titolo'}</div>
                              {ev.cliente && ev.cliente_matched && (
                                <div className="cal-ev-cliente">
                                  <i className="ri-user-heart-line"></i> {ev.cliente.nome_cognome}
                                </div>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* ===== Event Detail Modal ===== */}
      {selectedEvent && createPortal((() => {
        const ev = selectedEvent;
        const st = getStatus(ev.status);
        const duration = getDuration(ev.start, ev.end);

        return (
          <div className="cal-modal-backdrop" onClick={() => setSelectedEvent(null)}>
            <div className="cal-modal" onClick={(e) => e.stopPropagation()}>
              {/* Header */}
              <div className="cal-modal-header" style={{ background: st.bg }}>
                <h5>
                  <span className="cal-modal-dot" style={{ background: st.color }}></span>
                  Dettagli Appuntamento
                </h5>
                <button className="cal-modal-close" onClick={() => setSelectedEvent(null)}>
                  <i className="ri-close-line"></i>
                </button>
              </div>

              {/* Body */}
              <div className="cal-modal-body">
                {/* Title with avatar */}
                <div className="cal-modal-title-row">
                  {avatarUser?.avatar_path ? (
                    <img src={avatarUser.avatar_path} alt="" className="cal-modal-avatar cal-modal-avatar-img" />
                  ) : (
                    <div className="cal-modal-avatar">
                      {(avatarUser?.full_name || '?')?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                    </div>
                  )}
                  <div className="cal-modal-title">{ev.title || 'Senza titolo'}</div>
                </div>

                {/* Status badge */}
                <div className="cal-modal-status" style={{ color: st.color, background: st.bg }}>
                  {st.label}
                </div>

                {/* Info rows */}
                <div className="cal-modal-info">
                  <div className="cal-modal-row">
                    <i className="ri-calendar-line"></i>
                    <div>
                      <div className="cal-modal-row-label">Data</div>
                      <div className="cal-modal-row-value">{formatFullDate(ev.start)}</div>
                    </div>
                  </div>

                  <div className="cal-modal-row">
                    <i className="ri-time-line"></i>
                    <div>
                      <div className="cal-modal-row-label">Orario</div>
                      <div className="cal-modal-row-value">
                        {formatTime(ev.start)} - {formatTime(ev.end)}
                        {duration && <span className="cal-modal-duration">{duration}</span>}
                      </div>
                    </div>
                  </div>

                  {ev.ghl_calendar_name && (
                    <div className="cal-modal-row">
                      <i className="ri-calendar-2-line"></i>
                      <div>
                        <div className="cal-modal-row-label">Calendario</div>
                        <div className="cal-modal-row-value">{ev.ghl_calendar_name}</div>
                      </div>
                    </div>
                  )}

                  {ev.location && (
                    <div className="cal-modal-row">
                      <i className="ri-map-pin-line"></i>
                      <div>
                        <div className="cal-modal-row-label">Luogo</div>
                        <div className="cal-modal-row-value">{ev.location}</div>
                      </div>
                    </div>
                  )}

                  {ev.meetingLink && (
                    <div className="cal-modal-row">
                      <i className="ri-video-chat-line"></i>
                      <div>
                        <div className="cal-modal-row-label">Link Meeting</div>
                        <a href={ev.meetingLink} target="_blank" rel="noopener noreferrer" className="cal-modal-row-link">
                          {ev.meetingLink}
                        </a>
                      </div>
                    </div>
                  )}
                </div>

                {/* Cliente */}
                {ev.cliente && ev.cliente_matched && (
                  <div className="cal-modal-section">
                    <div className="cal-modal-section-title">Cliente associato</div>
                    <div className="cal-modal-cliente">
                      <div className="cal-modal-cliente-avatar">
                        {ev.cliente.nome_cognome?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="cal-modal-cliente-name">{ev.cliente.nome_cognome}</div>
                        {ev.cliente.email && (
                          <div className="cal-modal-cliente-email">{ev.cliente.email}</div>
                        )}
                        {ev.cliente.telefono && (
                          <div className="cal-modal-cliente-email">{ev.cliente.telefono}</div>
                        )}
                        {ev.cliente.stato_cliente && (
                          <span className={`cal-modal-stato cal-stato-${ev.cliente.stato_cliente}`}>
                            {ev.cliente.stato_cliente}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Notes */}
                {ev.notes && (
                  <div className="cal-modal-section">
                    <div className="cal-modal-section-title">Note</div>
                    <div className="cal-modal-notes">{ev.notes}</div>
                  </div>
                )}

                {/* Loom */}
                {ev.loomLink && (
                  <div className="cal-modal-section">
                    <div className="cal-modal-section-title">Registrazione</div>
                    <a href={ev.loomLink} target="_blank" rel="noopener noreferrer" className="cal-modal-link">
                      <i className="ri-video-line"></i> Apri registrazione Loom
                    </a>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="cal-modal-footer">
                {ev.meetingLink && (
                  <a
                    href={ev.meetingLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="cal-modal-btn cal-modal-btn-primary"
                  >
                    <i className="ri-video-chat-line"></i> Entra nel meeting
                  </a>
                )}
                <button className="cal-modal-btn cal-modal-btn-outline" onClick={() => setSelectedEvent(null)}>
                  Chiudi
                </button>
              </div>
            </div>
          </div>
        );
      })(), document.body)}

      {showCreateModal && createPortal(
        <div className="cal-modal-backdrop" onClick={() => setShowCreateModal(false)}>
          <div className="cal-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cal-modal-header" style={{ background: 'rgba(37,179,106,0.12)' }}>
              <h5><i className="ri-calendar-event-line" style={{ marginRight: 8 }}></i>Nuovo evento calendario</h5>
              <button className="cal-modal-close" onClick={() => setShowCreateModal(false)}>
                <i className="ri-close-line"></i>
              </button>
            </div>

            <div className="cal-modal-body">
              <div className="mb-3">
                <label className="form-label">Titolo</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Titolo evento"
                  value={newEventForm.title}
                  onChange={(e) => setNewEventForm((p) => ({ ...p, title: e.target.value }))}
                />
              </div>

              <div className="row g-2 mb-3">
                <div className="col-6">
                  <label className="form-label">Data</label>
                  <input
                    type="date"
                    className="form-control"
                    value={newEventForm.date}
                    onChange={(e) => setNewEventForm((p) => ({ ...p, date: e.target.value }))}
                  />
                </div>
                <div className="col-6">
                  <label className="form-label">Ora</label>
                  <input
                    type="time"
                    className="form-control"
                    value={newEventForm.time}
                    onChange={(e) => setNewEventForm((p) => ({ ...p, time: e.target.value }))}
                  />
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label">Durata (minuti)</label>
                <input
                  type="number"
                  min="5"
                  step="5"
                  className="form-control"
                  value={newEventForm.duration_minutes}
                  onChange={(e) => setNewEventForm((p) => ({ ...p, duration_minutes: e.target.value }))}
                />
              </div>

              <div className="mb-3">
                <label className="form-label">Cliente (opzionale)</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Cerca cliente per nome (min 2 caratteri)"
                  value={customerSearch}
                  onChange={(e) => {
                    setCustomerSearch(e.target.value);
                    setSelectedCustomer(null);
                  }}
                />
                {searchingCustomers && <small className="text-muted">Ricerca clienti...</small>}
                {!searchingCustomers && customerSearchResults.length > 0 && (
                  <div className="border rounded mt-2" style={{ maxHeight: 180, overflowY: 'auto' }}>
                    {customerSearchResults.map((c) => (
                      <button
                        key={c.cliente_id}
                        type="button"
                        className="btn btn-link text-start w-100"
                        onClick={() => {
                          setSelectedCustomer(c);
                          setCustomerSearch(c.nome_cognome || '');
                          setCustomerSearchResults([]);
                        }}
                      >
                        <strong>{c.nome_cognome}</strong>
                        {c.email ? <span className="text-muted"> · {c.email}</span> : null}
                      </button>
                    ))}
                  </div>
                )}
                {selectedCustomer && (
                  <small className="text-success d-block mt-1">Cliente selezionato: {selectedCustomer.nome_cognome}</small>
                )}
              </div>

              <div className="mb-3">
                <label className="form-label">Note (opzionale)</label>
                <textarea
                  className="form-control"
                  rows="3"
                  value={newEventForm.notes}
                  onChange={(e) => setNewEventForm((p) => ({ ...p, notes: e.target.value }))}
                />
              </div>

              {createEventError && <div className="alert alert-danger py-2">{createEventError}</div>}
              {createEventSuccess && <div className="alert alert-success py-2">{createEventSuccess}</div>}
            </div>

            <div className="cal-modal-footer">
              <button className="cal-modal-btn cal-modal-btn-outline" onClick={() => setShowCreateModal(false)}>
                Annulla
              </button>
              <button className="cal-modal-btn cal-modal-btn-primary" onClick={handleCreateCalendarEvent} disabled={creatingEvent}>
                {creatingEvent ? 'Creazione...' : 'Crea evento'}
              </button>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}

export default Calendario;

import { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useOutletContext } from 'react-router-dom';
import ghlService from '../../services/ghlService';
import calendarService from '../../services/calendarService';
import './Calendario.css';

function Calendario() {
  const { user } = useOutletContext();
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [teamMembers, setTeamMembers] = useState([]);
  const [selectedMemberId, setSelectedMemberId] = useState(null);
  const [memberSearch, setMemberSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef(null);
  const [bookingOpen, setBookingOpen] = useState(false);
  const [bookingSubmitting, setBookingSubmitting] = useState(false);
  const [bookingError, setBookingError] = useState(null);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [slotError, setSlotError] = useState(null);
  const [bookingForm, setBookingForm] = useState(() => {
    const now = new Date();
    const rounded = new Date(now);
    rounded.setMinutes(Math.ceil(now.getMinutes() / 30) * 30, 0, 0);
    return {
      clienteQuery: '',
      clienteId: null,
      title: '',
      notes: '',
      date: rounded.toISOString().split('T')[0],
      time: `${String(rounded.getHours()).padStart(2, '0')}:${String(rounded.getMinutes()).padStart(2, '0')}`,
      duration: 30,
    };
  });
  const [customerResults, setCustomerResults] = useState([]);
  const [customerSearching, setCustomerSearching] = useState(false);
  const [customerDropdownOpen, setCustomerDropdownOpen] = useState(false);
  const customerSearchRef = useRef(null);
  const customerSearchTimerRef = useRef(null);
  const [currentWeekStart, setCurrentWeekStart] = useState(() => {
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(now.getFullYear(), now.getMonth(), diff);
  });

  const isAdmin = user?.is_admin || user?.role === 'admin';
  const isTeamLeader = user?.role === 'team_leader' && !isAdmin;
  const canFilter = isAdmin || isTeamLeader;
  const canBookOnViewedCalendar = !selectedMemberId || Number(selectedMemberId) === Number(user?.id) || isAdmin;

  const formatDate = (d) => d.toISOString().split('T')[0];
  const parseDateString = (dateStr) => {
    const [year, month, day] = (dateStr || '').split('-').map(Number);
    return new Date(year, (month || 1) - 1, day || 1);
  };
  const parseTimeToMinutes = (timeStr) => {
    const [hour, minute] = (timeStr || '00:00').split(':').map(Number);
    return (hour * 60) + minute;
  };
  const formatMinutesToTime = (minutes) => {
    const normalized = Math.max(0, Math.min(23 * 60 + 59, minutes));
    const hour = String(Math.floor(normalized / 60)).padStart(2, '0');
    const minute = String(normalized % 60).padStart(2, '0');
    return `${hour}:${minute}`;
  };
  const getWeekStartForDate = (dateValue) => {
    const d = new Date(dateValue);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.getFullYear(), d.getMonth(), diff);
  };

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
      if (customerSearchRef.current && !customerSearchRef.current.contains(e.target)) {
        setCustomerDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => () => {
    if (customerSearchTimerRef.current) {
      clearTimeout(customerSearchTimerRef.current);
    }
  }, []);

  useEffect(() => {
    if (!bookingOpen || !bookingForm.date) return;
    
    const fetchSlots = async () => {
      setLoadingSlots(true);
      setSlotError(null);
      setAvailableSlots([]);
      try {
        const slotsRes = await ghlService.getFreeSlots(bookingForm.date, bookingForm.date, selectedMemberId);
        if (!slotsRes?.success) {
          throw new Error(slotsRes?.message || 'Errore nel recupero degli slot');
        }
        
        const flattenedIsoSlots = [];
        const walk = (node) => {
          if (!node) return;
          if (Array.isArray(node)) {
            node.forEach(walk);
            return;
          }
          if (typeof node === 'object') {
            Object.values(node).forEach(walk);
            return;
          }
          if (typeof node === 'string' && node.includes('T') && node.includes(':')) {
            const dt = new Date(node);
            if (!Number.isNaN(dt.getTime())) {
              flattenedIsoSlots.push(dt);
            }
          }
        };
        walk(slotsRes.slots);
        
        const timeSlots = flattenedIsoSlots.map(d => ({
          time: `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`,
          date: d
        })).sort((a, b) => a.date - b.date);
        
        const uniqueTimes = [];
        const uniqueSlots = timeSlots.filter(s => {
          if (uniqueTimes.includes(s.time)) return false;
          uniqueTimes.push(s.time);
          return true;
        });
        
        setAvailableSlots(uniqueSlots);
      } catch (err) {
        setSlotError(err.message || 'Impossibile caricare le disponibilità');
      } finally {
        setLoadingSlots(false);
      }
    };
    
    fetchSlots();
  }, [bookingOpen, bookingForm.date, selectedMemberId]);

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

  const buildLocalIso = (dateStr, timeStr) => {
    const [year, month, day] = dateStr.split('-').map(Number);
    const [hour, minute] = timeStr.split(':').map(Number);
    const localDate = new Date(year, month - 1, day, hour, minute, 0, 0);
    const tzMinutes = -localDate.getTimezoneOffset();
    const sign = tzMinutes >= 0 ? '+' : '-';
    const abs = Math.abs(tzMinutes);
    const tzH = String(Math.floor(abs / 60)).padStart(2, '0');
    const tzM = String(abs % 60).padStart(2, '0');
    return `${dateStr}T${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:00${sign}${tzH}:${tzM}`;
  };

  const toLocalIsoFromDate = (dateObj) => {
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, '0');
    const d = String(dateObj.getDate()).padStart(2, '0');
    const hh = String(dateObj.getHours()).padStart(2, '0');
    const mm = String(dateObj.getMinutes()).padStart(2, '0');
    const tzMinutes = -dateObj.getTimezoneOffset();
    const sign = tzMinutes >= 0 ? '+' : '-';
    const abs = Math.abs(tzMinutes);
    const tzH = String(Math.floor(abs / 60)).padStart(2, '0');
    const tzM = String(abs % 60).padStart(2, '0');
    return `${y}-${m}-${d}T${hh}:${mm}:00${sign}${tzH}:${tzM}`;
  };

  const handleCustomerQueryChange = (value) => {
    setBookingForm((prev) => ({
      ...prev,
      clienteQuery: value,
      clienteId: null,
    }));
    setBookingError(null);
    if (customerSearchTimerRef.current) clearTimeout(customerSearchTimerRef.current);

    if (!value || value.trim().length < 3) {
      setCustomerResults([]);
      setCustomerDropdownOpen(false);
      setCustomerSearching(false);
      return;
    }

    setCustomerSearching(true);
    setCustomerDropdownOpen(true);
    customerSearchTimerRef.current = setTimeout(async () => {
      try {
        const result = await calendarService.searchCustomers(value.trim(), 15);
        setCustomerResults(result.customers || []);
      } catch {
        setCustomerResults([]);
      } finally {
        setCustomerSearching(false);
      }
    }, 250);
  };

  const handleCreateAppointment = async (e) => {
    e.preventDefault();
    setBookingError(null);
    setSuccessMessage(null);

    if (!bookingForm.clienteId) {
      setBookingError('Seleziona un cliente dalla ricerca.');
      return;
    }
    if (!bookingForm.date || !bookingForm.time) {
      setBookingError('Data e orario sono obbligatori.');
      return;
    }

    const startIso = buildLocalIso(bookingForm.date, bookingForm.time);
    const startDate = new Date(startIso);
    const endDate = new Date(startDate.getTime() + Number(bookingForm.duration || 30) * 60000);
    const endIso = toLocalIsoFromDate(endDate);

    try {
      setBookingSubmitting(true);

      // Pre-check disponibilità: se rileviamo slot e l'orario non è libero, blocchiamo.
      const slotsRes = await ghlService.getFreeSlots(bookingForm.date, bookingForm.date, selectedMemberId);
      if (!slotsRes?.success) {
        throw new Error(slotsRes?.message || 'Impossibile verificare disponibilità slot');
      }
      const flattenedIsoSlots = [];
      const walk = (node) => {
        if (!node) return;
        if (Array.isArray(node)) {
          node.forEach(walk);
          return;
        }
        if (typeof node === 'object') {
          Object.values(node).forEach(walk);
          return;
        }
        if (typeof node === 'string' && node.includes('T') && node.includes(':')) {
          const dt = new Date(node);
          if (!Number.isNaN(dt.getTime())) {
            flattenedIsoSlots.push(dt);
          }
        }
      };
      walk(slotsRes.slots);
      if (flattenedIsoSlots.length > 0) {
        const hasMatch = flattenedIsoSlots.some((d) => Math.abs(d.getTime() - startDate.getTime()) <= 60000);
        if (!hasMatch) {
          throw new Error('Lo slot selezionato non risulta disponibile. Aggiorna e scegli un altro orario.');
        }
      }

      const payload = {
        cliente_id: bookingForm.clienteId,
        start_time: startIso,
        end_time: endIso,
        duration_minutes: Number(bookingForm.duration || 30),
        title: bookingForm.title || 'Appuntamento professionista',
        notes: bookingForm.notes || '',
        timezone: 'Europe/Rome',
      };
      if (selectedMemberId) {
        payload.user_id = selectedMemberId;
      }
      const res = await ghlService.createAppointment(payload);
      if (!res?.success) {
        throw new Error(res?.message || 'Errore creazione appuntamento');
      }
      setBookingOpen(false);
      setSuccessMessage('Appuntamento creato con successo.');
      await fetchEvents();
      setBookingForm((prev) => ({
        ...prev,
        clienteQuery: '',
        clienteId: null,
        title: '',
        notes: '',
      }));
    } catch (err) {
      setBookingError(err?.response?.data?.message || err?.message || 'Errore creazione appuntamento');
    } finally {
      setBookingSubmitting(false);
    }
  };

  const openBookingForDay = (dayDate) => {
    const day = new Date(dayDate);
    const today = new Date();
    let hour = 9;
    let minute = 0;
    if (day.toDateString() === today.toDateString()) {
      const rounded = new Date(today);
      rounded.setMinutes(Math.ceil(today.getMinutes() / 30) * 30, 0, 0);
      hour = rounded.getHours();
      minute = rounded.getMinutes();
    }
    setBookingForm((prev) => ({
      ...prev,
      date: `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`,
      time: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`,
    }));
    setBookingError(null);
    setBookingOpen(true);
  };

  const weekLabel = () => {
    const start = currentWeekStart;
    const end = getWeekEnd(start);
    const opts = { day: 'numeric', month: 'long' };
    return `${start.toLocaleDateString('it-IT', opts)} - ${end.toLocaleDateString('it-IT', opts)} ${end.getFullYear()}`;
  };

  const bookingSelectedDate = parseDateString(bookingForm.date);
  const bookingWeekStart = getWeekStartForDate(bookingSelectedDate);
  const bookingWeekDays = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(bookingWeekStart);
    d.setDate(d.getDate() + i);
    bookingWeekDays.push(d);
  }

  const bookingDayEvents = events
    .filter((ev) => formatDate(new Date(ev.start)) === bookingForm.date)
    .sort((a, b) => new Date(a.start) - new Date(b.start));

  const timelineStep = [...availableSlots, ...bookingDayEvents].some((item) => {
    const date = item?.date || item?.start;
    if (!date) return false;
    const d = new Date(date);
    return d.getMinutes() % 30 !== 0;
  }) ? 15 : 30;

  const bookedRanges = bookingDayEvents.map((ev) => {
    const start = new Date(ev.start);
    const end = ev.end ? new Date(ev.end) : new Date(start.getTime() + Number(bookingForm.duration || 30) * 60000);
    return {
      event: ev,
      startMinutes: (start.getHours() * 60) + start.getMinutes(),
      endMinutes: (end.getHours() * 60) + end.getMinutes(),
    };
  });

  const visibleMinutes = [
    ...availableSlots.map((slot) => parseTimeToMinutes(slot.time)),
    ...bookedRanges.flatMap((range) => [range.startMinutes, range.endMinutes]),
  ];
  const timelineStart = visibleMinutes.length > 0
    ? Math.max(7 * 60, Math.floor((Math.min(...visibleMinutes) - 60) / timelineStep) * timelineStep)
    : 8 * 60;
  const timelineEnd = visibleMinutes.length > 0
    ? Math.min(21 * 60, Math.ceil((Math.max(...visibleMinutes) + 60) / timelineStep) * timelineStep)
    : 20 * 60;
  const availableTimeSet = new Set(availableSlots.map((slot) => slot.time));
  const dayTimelineSlots = [];

  for (let minute = timelineStart; minute <= timelineEnd; minute += timelineStep) {
    const time = formatMinutesToTime(minute);
    const bookedRange = bookedRanges.find((range) => minute >= range.startMinutes && minute < range.endMinutes);
    const isAvailable = availableTimeSet.has(time);

    dayTimelineSlots.push({
      time,
      status: bookedRange ? 'busy' : isAvailable ? 'available' : 'unavailable',
      event: bookedRange?.event || null,
      isSelected: bookingForm.time === time,
    });
  }

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
          {canBookOnViewedCalendar && (
            <button
              className="cal-nav-btn cal-booking-btn"
              onClick={() => {
                setBookingError(null);
                setBookingOpen(true);
              }}
              title="Nuova prenotazione"
            >
              <i className="ri-calendar-check-line"></i>
              Prenota
            </button>
          )}
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
      {successMessage && (
        <div className="cal-alert cal-alert-success">
          <i className="ri-checkbox-circle-line"></i> {successMessage}
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
                      <div className="cal-day-header-actions">
                        <span className={`cal-day-num ${isToday ? 'cal-today-num' : ''}`}>
                          {day.getDate()}
                        </span>
                        {canBookOnViewedCalendar && (
                          <button
                            className="cal-day-add-btn"
                            title="Prenota in questo giorno"
                            onClick={() => openBookingForDay(day)}
                          >
                            <i className="ri-add-line"></i>
                          </button>
                        )}
                      </div>
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
      {bookingOpen && createPortal(
        <div className="cal-modal-backdrop" onClick={() => setBookingOpen(false)}>
          <div className="cal-modal cal-booking-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cal-modal-header">
              <h5>
                <span className="cal-modal-dot" style={{ background: '#25B36A' }}></span>
                Nuova prenotazione
              </h5>
              <button className="cal-modal-close" onClick={() => setBookingOpen(false)}>
                <i className="ri-close-line"></i>
              </button>
            </div>

            <form className="cal-modal-body" onSubmit={handleCreateAppointment}>
              <div className="cal-booking-grid">
                <div className="cal-book-field cal-book-field-full" ref={customerSearchRef}>
                  <label>Cliente</label>
                  <input
                    type="text"
                    value={bookingForm.clienteQuery}
                    onChange={(e) => handleCustomerQueryChange(e.target.value)}
                    placeholder="Cerca cliente (min 3 caratteri)"
                    onFocus={() => {
                      if (customerResults.length > 0) setCustomerDropdownOpen(true);
                    }}
                  />
                  {customerDropdownOpen && (
                    <div className="cal-book-customer-dropdown">
                      {customerSearching ? (
                        <div className="cal-book-customer-item muted">Ricerca in corso...</div>
                      ) : customerResults.length === 0 ? (
                        <div className="cal-book-customer-item muted">Nessun cliente trovato</div>
                      ) : (
                        customerResults.map((c) => (
                          <button
                            type="button"
                            key={c.cliente_id}
                            className="cal-book-customer-item"
                            onClick={() => {
                              setBookingForm((prev) => ({
                                ...prev,
                                clienteId: c.cliente_id,
                                clienteQuery: c.nome_cognome,
                              }));
                              setCustomerDropdownOpen(false);
                            }}
                          >
                            <span>{c.nome_cognome}</span>
                            {c.stato_cliente && <small>{c.stato_cliente}</small>}
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>

                <div className="cal-book-field cal-book-field-full">
                  <label>Giorno</label>
                  <div className="cal-book-day-strip">
                    {bookingWeekDays.map((day) => {
                      const dayValue = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
                      const isActive = bookingForm.date === dayValue;
                      const dayEventsCount = events.filter((ev) => formatDate(new Date(ev.start)) === dayValue).length;
                      return (
                        <button
                          key={dayValue}
                          type="button"
                          className={`cal-book-day-card ${isActive ? 'active' : ''}`}
                          onClick={() => setBookingForm((prev) => ({ ...prev, date: dayValue, time: '' }))}
                        >
                          <span className="cal-book-day-name">{day.toLocaleDateString('it-IT', { weekday: 'short' })}</span>
                          <strong className="cal-book-day-number">{day.getDate()}</strong>
                          <span className="cal-book-day-meta">
                            {dayEventsCount > 0 ? `${dayEventsCount} impegn.` : 'Nessun evento'}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="cal-book-field cal-book-field-full">
                  <label>Agenda del giorno</label>
                  {loadingSlots ? (
                    <div className="cal-slots-loading">
                      <div className="cal-spinner" style={{width: 16, height: 16, display: 'inline-block', marginRight: 8, borderWidth: 2}}></div>
                      Ricerca disponibilità in corso...
                    </div>
                  ) : slotError ? (
                    <div className="cal-slots-error">{slotError}</div>
                  ) : dayTimelineSlots.length === 0 ? (
                    <div className="cal-slots-empty">Nessuna fascia oraria disponibile per questa data.</div>
                  ) : (
                    <>
                      <div className="cal-slot-legend">
                        <span className="available"><i className="ri-checkbox-blank-circle-fill"></i> Libero</span>
                        <span className="busy"><i className="ri-checkbox-blank-circle-fill"></i> Occupato</span>
                        <span className="unavailable"><i className="ri-checkbox-blank-circle-fill"></i> Non prenotabile</span>
                      </div>
                      <div className="cal-slot-timeline">
                        {dayTimelineSlots.map((slot) => (
                          <button
                            key={slot.time}
                            type="button"
                            className={`cal-slot-card ${slot.status} ${slot.isSelected ? 'selected' : ''}`}
                            onClick={() => {
                              if (slot.status !== 'available') return;
                              setBookingForm((prev) => ({ ...prev, time: slot.time }));
                            }}
                            disabled={slot.status !== 'available'}
                          >
                            <div className="cal-slot-card-time">{slot.time}</div>
                            <div className="cal-slot-card-state">
                              {slot.status === 'available' && 'Disponibile'}
                              {slot.status === 'busy' && 'Occupato'}
                              {slot.status === 'unavailable' && 'Non prenotabile'}
                            </div>
                            <div className="cal-slot-card-detail">
                              {slot.status === 'busy'
                                ? (slot.event?.title || slot.event?.cliente?.nome_cognome || 'Appuntamento')
                                : slot.status === 'available'
                                  ? 'Prenota questo orario'
                                  : 'Fuori dagli slot GHL'}
                            </div>
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                  {/* Hidden input to maintain HTML form validation if time is missing */}
                  <input 
                    type="text" 
                    value={bookingForm.time} 
                    required 
                    style={{opacity: 0, position: 'absolute', height: 0, width: 0, padding: 0, margin: 0, border: 'none'}} 
                    onChange={() => {}}
                  />
                </div>

                <div className="cal-book-field">
                  <label>Durata (min)</label>
                  <select
                    value={bookingForm.duration}
                    onChange={(e) => setBookingForm((prev) => ({ ...prev, duration: Number(e.target.value) }))}
                  >
                    <option value={15}>15</option>
                    <option value={30}>30</option>
                    <option value={45}>45</option>
                    <option value={60}>60</option>
                  </select>
                </div>

                <div className="cal-book-field cal-book-field-full">
                  <label>Titolo</label>
                  <input
                    type="text"
                    value={bookingForm.title}
                    onChange={(e) => setBookingForm((prev) => ({ ...prev, title: e.target.value }))}
                    placeholder="Es. Call 1to1 Iniziale"
                  />
                </div>

                <div className="cal-book-field cal-book-field-full">
                  <label>Note</label>
                  <textarea
                    value={bookingForm.notes}
                    onChange={(e) => setBookingForm((prev) => ({ ...prev, notes: e.target.value }))}
                    placeholder="Note opzionali"
                    rows={3}
                  />
                </div>
              </div>

              {bookingError && (
                <div className="cal-alert cal-alert-danger" style={{ marginTop: 12 }}>
                  <i className="ri-error-warning-line"></i> {bookingError}
                </div>
              )}

              <div className="cal-modal-footer" style={{ marginTop: 16 }}>
                <button
                  type="submit"
                  className="cal-modal-btn cal-modal-btn-primary"
                  disabled={bookingSubmitting}
                >
                  {bookingSubmitting ? 'Creazione...' : 'Conferma prenotazione'}
                </button>
                <button
                  type="button"
                  className="cal-modal-btn cal-modal-btn-outline"
                  onClick={() => setBookingOpen(false)}
                  disabled={bookingSubmitting}
                >
                  Annulla
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

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
    </div>
  );
}

export default Calendario;

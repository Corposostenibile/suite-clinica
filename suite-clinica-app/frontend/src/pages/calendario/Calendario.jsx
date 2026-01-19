import { useState, useEffect, useCallback } from 'react';
import { useOutletContext, Link } from 'react-router-dom';
import calendarService, { EVENT_CATEGORIES, MEETING_STATUSES } from '../../services/calendarService';
import ghlService from '../../services/ghlService';

// Styles
const styles = {
    card: {
        borderRadius: '16px',
        border: 'none',
        boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        overflow: 'hidden',
    },
    dayHeader: {
        padding: '12px 8px',
        textAlign: 'center',
        fontWeight: 600,
        fontSize: '12px',
        textTransform: 'uppercase',
        color: '#64748b',
        background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
    },
    dayCell: {
        minHeight: '110px',
        padding: '8px',
        borderRight: '1px solid #f1f5f9',
        borderBottom: '1px solid #f1f5f9',
        verticalAlign: 'top',
        cursor: 'pointer',
        transition: 'background 0.2s',
    },
    eventPill: {
        padding: '3px 8px',
        borderRadius: '6px',
        fontSize: '11px',
        fontWeight: 500,
        marginBottom: '3px',
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
    }
};

function Calendario() {
    const { user } = useOutletContext();
    const [currentDate, setCurrentDate] = useState(new Date());
    const [selectedDate, setSelectedDate] = useState(new Date());
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isConnected, setIsConnected] = useState(null); // null = checking, true/false = result
    const [connectUrl, setConnectUrl] = useState('/oauth/google');
    const [selectedEvent, setSelectedEvent] = useState(null);
    const [showEventModal, setShowEventModal] = useState(false);
    const [connectionChecked, setConnectionChecked] = useState(false);
    const [useGHL, setUseGHL] = useState(false); // true = use GHL, false = use Google

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const firstDayOfMonth = new Date(year, month, 1).getDay();
    const startDay = firstDayOfMonth === 0 ? 6 : firstDayOfMonth - 1;

    const monthNames = [
        'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
    ];

    const dayNames = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'];

    // Check connection status on mount - Try GHL first, then Google
    const checkConnectionStatus = useCallback(async () => {
        try {
            // First check GHL connection
            const ghlStatus = await ghlService.getConnectionStatus();

            if (ghlStatus.is_connected) {
                // GHL is configured and user has calendar linked
                setIsConnected(true);
                setUseGHL(true);
                setConnectionChecked(true);
                return true;
            }

            // If GHL not configured or user not linked, fallback to Google
            const googleStatus = await calendarService.getConnectionStatus();
            setIsConnected(googleStatus.is_connected);
            setUseGHL(false);
            if (googleStatus.connect_url) {
                setConnectUrl(googleStatus.connect_url);
            }
            setConnectionChecked(true);
            return googleStatus.is_connected;
        } catch (err) {
            console.error('Error checking connection status:', err);
            setIsConnected(false);
            setConnectionChecked(true);
            return false;
        }
    }, []);

    // Fetch events when month changes
    const fetchEvents = useCallback(async (forceUseGHL = null) => {
        // First check connection if not done yet
        let shouldUseGHL = forceUseGHL !== null ? forceUseGHL : useGHL;

        if (!connectionChecked) {
            // Check GHL connection first
            try {
                const ghlStatus = await ghlService.getConnectionStatus();

                if (ghlStatus.is_connected) {
                    setIsConnected(true);
                    setUseGHL(true);
                    setConnectionChecked(true);
                    shouldUseGHL = true;
                } else {
                    // GHL not configured for this user
                    setIsConnected(false);
                    setUseGHL(false);
                    setConnectionChecked(true);
                    setLoading(false);
                    return;
                }
            } catch (err) {
                console.error('[Calendario] Error checking GHL connection:', err);
                setIsConnected(false);
                setConnectionChecked(true);
                setLoading(false);
                return;
            }
        } else if (!isConnected) {
            setLoading(false);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            // Calculate date range for current month view (with some padding)
            const startDate = new Date(year, month, 1);
            startDate.setDate(startDate.getDate() - 7); // Start a week before
            const endDate = new Date(year, month + 1, 0);
            endDate.setDate(endDate.getDate() + 7); // End a week after

            const startStr = startDate.toISOString().split('T')[0];
            const endStr = endDate.toISOString().split('T')[0];

            let formattedEvents = [];

            // Always use GHL now (Google Calendar removed)
            if (shouldUseGHL) {
                // Fetch from GHL
                const ghlData = await ghlService.getEvents(startStr, endStr);

                if (!ghlData.success) {
                    if (ghlData.message?.includes('non configurato')) {
                        setIsConnected(false);
                        setUseGHL(false);
                    } else {
                        setError(ghlData.message || 'Errore nel caricamento eventi GHL');
                    }
                    setEvents([]);
                    return;
                }

                // Format GHL events
                formattedEvents = (ghlData.events || []).map(event => {
                    const eventStart = new Date(event.start);
                    const eventEnd = event.end ? new Date(event.end) : eventStart;

                    // Determina colore in base al tipo di calendario
                    const calName = (event.ghl_calendar_name || '').toLowerCase();
                    const isIniziale = calName.includes('iniziale');
                    const eventColor = isIniziale ? '#22c55e' : '#8b5cf6'; // Verde per Iniziale, Viola per Periodica

                    return {
                        id: event.id,
                        googleEventId: event.id, // Keep for compatibility
                        title: event.title,
                        date: eventStart,
                        endDate: eventEnd,
                        time: eventStart.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }),
                        allDay: false,
                        color: eventColor,
                        isCallIniziale: isIniziale,
                        // GHL data
                        meetingId: null,
                        userId: null,
                        userName: null,
                        clienteId: event.cliente?.cliente_id,
                        clienteName: event.cliente?.nome_cognome || event.title,
                        category: null,
                        status: event.status || 'scheduled',
                        meetingLink: event.meetingLink,
                        meetingOutcome: null,
                        meetingNotes: event.notes,
                        loomLink: null,
                        location: event.location,
                        description: event.notes,
                        // GHL specific
                        ghlContactId: event.ghl_contact_id,
                        ghlCalendarId: event.ghl_calendar_id,
                        ghlCalendarName: event.ghl_calendar_name,
                        clienteMatched: event.cliente_matched,
                    };
                });
            } else {
                // GHL not configured - show empty
                setIsConnected(false);
                setEvents([]);
                return;
            }

            setEvents(formattedEvents);
        } catch (err) {
            console.error('Error fetching events:', err);
            if (err.response?.status === 401) {
                setIsConnected(false);
            } else {
                setError('Errore nel caricamento degli eventi');
            }
        } finally {
            setLoading(false);
        }
    }, [year, month, connectionChecked, isConnected, useGHL]);

    // Single useEffect for fetching events
    useEffect(() => {
        fetchEvents();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [year, month]);

    const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
    const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));
    const goToToday = () => {
        const today = new Date();
        setCurrentDate(today);
        setSelectedDate(today);
    };

    const getEventsForDay = (day) => {
        return events.filter(event => {
            const eventDate = event.date;
            return eventDate.getDate() === day &&
                   eventDate.getMonth() === month &&
                   eventDate.getFullYear() === year;
        }).sort((a, b) => a.date - b.date);
    };

    const selectedDateEvents = events.filter(event => {
        const eventDate = event.date;
        return eventDate.getDate() === selectedDate.getDate() &&
               eventDate.getMonth() === selectedDate.getMonth() &&
               eventDate.getFullYear() === selectedDate.getFullYear();
    }).sort((a, b) => a.date - b.date);

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Today's events
    const todayEvents = events.filter(event => {
        const eventDate = new Date(event.date);
        eventDate.setHours(0, 0, 0, 0);
        return eventDate.getTime() === today.getTime();
    });

    // This week stats
    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - today.getDay() + 1);
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);

    const weekEvents = events.filter(event => {
        const eventDate = new Date(event.date);
        eventDate.setHours(0, 0, 0, 0);
        return eventDate >= startOfWeek && eventDate <= endOfWeek;
    });

    // Raggruppa eventi per tipo: "Call Iniziale" vs "Call Periodica"
    const callStats = weekEvents.reduce((acc, event) => {
        const calName = (event.ghlCalendarName || '').toLowerCase();
        // Se contiene "iniziale" → Call Iniziale, altrimenti → Call Periodica
        const type = calName.includes('iniziale') ? 'Call Iniziale' : 'Call Periodica';
        acc[type] = (acc[type] || 0) + 1;
        return acc;
    }, {});

    const callIniziali = callStats['Call Iniziale'] || 0;
    const callPeriodiche = callStats['Call Periodica'] || 0;

    const isToday = (day) => {
        const now = new Date();
        return day === now.getDate() && month === now.getMonth() && year === now.getFullYear();
    };

    const isSelected = (day) => {
        return day === selectedDate.getDate() &&
               month === selectedDate.getMonth() &&
               year === selectedDate.getFullYear();
    };

    const isWeekend = (dayOfWeek) => dayOfWeek === 5 || dayOfWeek === 6; // Sat, Sun

    const formatDate = (date) => {
        return date.toLocaleDateString('it-IT', {
            weekday: 'long',
            day: 'numeric',
            month: 'long'
        });
    };

    const getEventConfig = (event) => {
        if (event.category && EVENT_CATEGORIES[event.category]) {
            return EVENT_CATEGORIES[event.category];
        }
        // Default based on color or fallback
        return {
            label: 'Evento',
            color: event.color || '#6b7280',
            bgColor: `${event.color || '#6b7280'}20`,
            icon: 'ri-calendar-event-line',
            duration: 30
        };
    };

    const handleEventClick = (event) => {
        setSelectedEvent(event);
        setShowEventModal(true);
    };

    const handleStartCall = (meetingLink) => {
        if (meetingLink) {
            window.open(meetingLink, '_blank');
        }
    };

    const renderCalendarGrid = () => {
        const cells = [];
        let day = 1;

        for (let week = 0; week < 6; week++) {
            const weekCells = [];

            for (let dayOfWeek = 0; dayOfWeek < 7; dayOfWeek++) {
                if ((week === 0 && dayOfWeek < startDay) || day > daysInMonth) {
                    weekCells.push(
                        <td key={`${week}-${dayOfWeek}`} style={{ ...styles.dayCell, background: '#fafafa' }}></td>
                    );
                } else {
                    const currentDay = day;
                    const dayEvents = getEventsForDay(currentDay);
                    const todayClass = isToday(currentDay);
                    const selectedClass = isSelected(currentDay);
                    const weekend = isWeekend(dayOfWeek);

                    weekCells.push(
                        <td
                            key={`${week}-${dayOfWeek}`}
                            style={{
                                ...styles.dayCell,
                                background: selectedClass ? '#f0fdf4' : todayClass ? '#fef3c7' : weekend ? '#fafafa' : '#fff',
                            }}
                            onClick={() => setSelectedDate(new Date(year, month, currentDay))}
                        >
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                marginBottom: '6px',
                            }}>
                                <span style={{
                                    fontSize: '14px',
                                    fontWeight: todayClass || selectedClass ? 700 : 500,
                                    color: todayClass ? '#f59e0b' : selectedClass ? '#22c55e' : weekend ? '#94a3b8' : '#1e293b',
                                }}>
                                    {currentDay}
                                </span>
                                {todayClass && (
                                    <span style={{
                                        fontSize: '9px',
                                        background: '#fef3c7',
                                        color: '#f59e0b',
                                        padding: '2px 6px',
                                        borderRadius: '10px',
                                        fontWeight: 600,
                                    }}>
                                        OGGI
                                    </span>
                                )}
                            </div>
                            <div>
                                {dayEvents.slice(0, 3).map((event, idx) => {
                                    const config = getEventConfig(event);
                                    return (
                                        <div
                                            key={idx}
                                            style={{
                                                ...styles.eventPill,
                                                background: config.bgColor,
                                                color: config.color,
                                            }}
                                            title={`${event.time} - ${event.title}${event.clienteName ? ` - ${event.clienteName}` : ''}`}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleEventClick(event);
                                            }}
                                        >
                                            <span style={{ fontWeight: 600 }}>{event.time}</span>
                                            <span style={{
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap',
                                                flex: 1,
                                            }}>
                                                {event.clienteName || event.title}
                                            </span>
                                        </div>
                                    );
                                })}
                                {dayEvents.length > 3 && (
                                    <div style={{ fontSize: '10px', color: '#64748b', textAlign: 'center', marginTop: '2px' }}>
                                        +{dayEvents.length - 3} altre
                                    </div>
                                )}
                            </div>
                        </td>
                    );
                    day++;
                }
            }

            // Aggiungi la riga se contiene almeno un giorno del mese
            // (day > 1 significa che abbiamo processato almeno un giorno in questa settimana)
            if (week === 0 || day <= daysInMonth + 1) {
                cells.push(<tr key={week}>{weekCells}</tr>);
            }

            // Esci se abbiamo finito i giorni
            if (day > daysInMonth) {
                break;
            }
        }

        return cells;
    };

    const userName = user?.first_name || 'Professionista';

    // Loading connection status
    if (isConnected === null || !connectionChecked) {
        return (
            <div className="d-flex align-items-center justify-content-center" style={{ minHeight: '400px' }}>
                <div className="text-center">
                    <div className="spinner-border text-primary mb-3" role="status">
                        <span className="visually-hidden">Caricamento...</span>
                    </div>
                    <p className="text-muted">Verifica connessione calendario...</p>
                </div>
            </div>
        );
    }

    // Not connected to any calendar
    if (!isConnected) {
        return (
            <>
                <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                    <div>
                        <h4 className="fw-bold mb-1" style={{ color: '#1e293b' }}>Il tuo Calendario</h4>
                        <p className="text-muted mb-0" style={{ fontSize: '14px' }}>
                            Configura il calendario per visualizzare i tuoi appuntamenti
                        </p>
                    </div>
                </div>

                <div className="card border-0" style={styles.card}>
                    <div className="card-body text-center py-5">
                        {/* Calendar Icon */}
                        <div style={{
                            width: '80px',
                            height: '80px',
                            background: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
                            borderRadius: '20px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto 20px',
                            boxShadow: '0 4px 12px rgba(249, 115, 22, 0.3)',
                        }}>
                            <i className="ri-calendar-schedule-line text-white" style={{ fontSize: '40px' }}></i>
                        </div>
                        <h5 className="fw-bold mb-2">Calendario non configurato</h5>
                        <p className="text-muted mb-0" style={{ maxWidth: '450px', margin: '0 auto' }}>
                            Il tuo calendario non è ancora stato associato al tuo profilo.
                        </p>
                        <p className="mt-3 mb-0">
                            <strong>Contatta il Team IT di CorpoSostenibile</strong>
                            <br />
                            <span className="text-muted" style={{ fontSize: '14px' }}>
                                per configurare l'associazione del tuo calendario.
                            </span>
                        </p>
                    </div>
                </div>
            </>
        );
    }

    return (
        <>
            {/* Page Header */}
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                <div>
                    <h4 className="fw-bold mb-1" style={{ color: '#1e293b' }}>Il tuo Calendario</h4>
                    <p className="text-muted mb-0" style={{ fontSize: '14px' }}>
                        Ciao {userName}, hai {todayEvents.length} appuntamenti oggi
                    </p>
                </div>
                <div className="d-flex gap-2">
                    <button
                        className="btn"
                        onClick={() => fetchEvents()}
                        disabled={loading}
                        style={{
                            background: '#fff',
                            border: '1px solid #e2e8f0',
                            color: '#64748b',
                            fontWeight: 500,
                            padding: '10px 16px',
                            borderRadius: '10px',
                        }}
                    >
                        <i className={`ri-refresh-line ${loading ? 'ri-spin' : ''}`}></i>
                    </button>
                    <button
                        className="btn"
                        onClick={goToToday}
                        style={{
                            background: '#fff',
                            border: '1px solid #e2e8f0',
                            color: '#64748b',
                            fontWeight: 500,
                            padding: '10px 20px',
                            borderRadius: '10px',
                        }}
                    >
                        <i className="ri-focus-line me-2"></i>
                        Oggi
                    </button>
                    <a
                        href={calendarService.getDashboardUrl()}
                        className="btn"
                        style={{
                            background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                            color: 'white',
                            fontWeight: 600,
                            padding: '10px 20px',
                            borderRadius: '10px',
                            border: 'none',
                            boxShadow: '0 2px 8px rgba(34, 197, 94, 0.3)',
                        }}
                    >
                        <i className="ri-add-line me-2"></i>
                        Nuova Call
                    </a>
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="alert alert-danger d-flex align-items-center mb-4" role="alert">
                    <i className="ri-error-warning-line me-2"></i>
                    {error}
                    <button
                        type="button"
                        className="btn-close ms-auto"
                        onClick={() => setError(null)}
                    ></button>
                </div>
            )}

            {/* Stats Cards */}
            <div className="row g-3 mb-4">
                <div className="col-xl-3 col-sm-6">
                    <div className="card border-0" style={{ ...styles.card, background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' }}>
                        <div className="card-body py-3">
                            <div className="d-flex align-items-center justify-content-between">
                                <div>
                                    <h3 className="text-white mb-0 fw-bold">{loading ? '-' : todayEvents.length}</h3>
                                    <span className="text-white" style={{ opacity: 0.85, fontSize: '13px' }}>Call Oggi</span>
                                </div>
                                <div style={{ width: '48px', height: '48px', background: 'rgba(255,255,255,0.2)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className="ri-calendar-todo-line text-white" style={{ fontSize: '22px' }}></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-xl-3 col-sm-6">
                    <div className="card border-0" style={{ ...styles.card, background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' }}>
                        <div className="card-body py-3">
                            <div className="d-flex align-items-center justify-content-between">
                                <div>
                                    <h3 className="text-white mb-0 fw-bold">{loading ? '-' : weekEvents.length}</h3>
                                    <span className="text-white" style={{ opacity: 0.85, fontSize: '13px' }}>Call Settimana</span>
                                </div>
                                <div style={{ width: '48px', height: '48px', background: 'rgba(255,255,255,0.2)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className="ri-calendar-check-line text-white" style={{ fontSize: '22px' }}></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                {/* Call Iniziale */}
                <div className="col-xl-3 col-sm-6">
                    <div className="card border-0" style={{ ...styles.card, background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' }}>
                        <div className="card-body py-3">
                            <div className="d-flex align-items-center justify-content-between">
                                <div>
                                    <h3 className="text-white mb-0 fw-bold">
                                        {loading ? '-' : callIniziali}
                                    </h3>
                                    <span className="text-white" style={{ opacity: 0.85, fontSize: '13px' }}>Call Iniziale</span>
                                </div>
                                <div style={{ width: '48px', height: '48px', background: 'rgba(255,255,255,0.2)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className="ri-user-add-line text-white" style={{ fontSize: '22px' }}></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                {/* Call Periodica */}
                <div className="col-xl-3 col-sm-6">
                    <div className="card border-0" style={{ ...styles.card, background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' }}>
                        <div className="card-body py-3">
                            <div className="d-flex align-items-center justify-content-between">
                                <div>
                                    <h3 className="text-white mb-0 fw-bold">
                                        {loading ? '-' : callPeriodiche}
                                    </h3>
                                    <span className="text-white" style={{ opacity: 0.85, fontSize: '13px' }}>Call Periodica</span>
                                </div>
                                <div style={{ width: '48px', height: '48px', background: 'rgba(255,255,255,0.2)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <i className="ri-refresh-line text-white" style={{ fontSize: '22px' }}></i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="row g-4">
                {/* Calendar */}
                <div className="col-xl-8">
                    <div className="card border-0" style={styles.card}>
                        <div className="card-header bg-white border-0 py-3">
                            <div className="d-flex align-items-center justify-content-center gap-4">
                                <button className="btn btn-sm" onClick={prevMonth} style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '8px 12px' }}>
                                    <i className="ri-arrow-left-s-line"></i>
                                </button>
                                <h5 className="mb-0 fw-bold" style={{ color: '#1e293b', minWidth: '180px', textAlign: 'center' }}>
                                    {monthNames[month]} {year}
                                </h5>
                                <button className="btn btn-sm" onClick={nextMonth} style={{ border: '1px solid #e2e8f0', borderRadius: '8px', padding: '8px 12px' }}>
                                    <i className="ri-arrow-right-s-line"></i>
                                </button>
                            </div>
                        </div>

                        <div className="card-body p-0" style={{ position: 'relative' }}>
                            {loading && (
                                <div style={{
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    bottom: 0,
                                    background: 'rgba(255,255,255,0.8)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    zIndex: 10,
                                }}>
                                    <div className="spinner-border text-primary" role="status">
                                        <span className="visually-hidden">Caricamento...</span>
                                    </div>
                                </div>
                            )}
                            <table className="table table-bordered mb-0" style={{ tableLayout: 'fixed' }}>
                                <thead>
                                    <tr>
                                        {dayNames.map((day, idx) => (
                                            <th key={day} style={{
                                                ...styles.dayHeader,
                                                color: idx >= 5 ? '#94a3b8' : '#64748b'
                                            }}>{day}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {renderCalendarGrid()}
                                </tbody>
                            </table>
                        </div>

                        <div className="card-footer bg-white border-0 py-3">
                            <div className="d-flex flex-wrap gap-4 justify-content-center">
                                <div className="d-flex align-items-center gap-2">
                                    <div style={{
                                        width: '12px',
                                        height: '12px',
                                        borderRadius: '3px',
                                        background: '#22c55e'
                                    }}></div>
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>Call Iniziale</span>
                                </div>
                                <div className="d-flex align-items-center gap-2">
                                    <div style={{
                                        width: '12px',
                                        height: '12px',
                                        borderRadius: '3px',
                                        background: '#8b5cf6'
                                    }}></div>
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>Call Periodica</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Sidebar - Selected Day */}
                <div className="col-xl-4">
                    <div className="card border-0" style={{ ...styles.card, maxHeight: '600px', display: 'flex', flexDirection: 'column' }}>
                        <div className="card-header bg-white border-0 py-3" style={{ borderBottom: '1px solid #f1f5f9', flexShrink: 0 }}>
                            <h6 className="mb-0 fw-semibold text-capitalize" style={{ color: '#1e293b' }}>
                                <i className="ri-calendar-event-line me-2" style={{ color: '#22c55e' }}></i>
                                {formatDate(selectedDate)}
                            </h6>
                        </div>
                        <div className="card-body p-0" style={{ overflowY: 'auto', flex: 1 }}>
                            {loading ? (
                                <div className="text-center py-5">
                                    <div className="spinner-border spinner-border-sm text-primary" role="status">
                                        <span className="visually-hidden">Caricamento...</span>
                                    </div>
                                </div>
                            ) : selectedDateEvents.length === 0 ? (
                                <div className="text-center py-5">
                                    <i className="ri-calendar-line" style={{ fontSize: '48px', color: '#e2e8f0' }}></i>
                                    <p className="text-muted mt-3 mb-0">Nessun appuntamento</p>
                                    <a
                                        href={calendarService.getDashboardUrl()}
                                        className="btn btn-sm btn-outline-success mt-3"
                                        style={{ borderRadius: '20px' }}
                                    >
                                        <i className="ri-add-line me-1"></i> Aggiungi Call
                                    </a>
                                </div>
                            ) : (
                                <div>
                                    {selectedDateEvents.map((event, idx) => {
                                        const config = getEventConfig(event);
                                        const statusConfig = MEETING_STATUSES[event.status] || MEETING_STATUSES.scheduled;
                                        return (
                                            <div
                                                key={idx}
                                                className="p-3"
                                                style={{
                                                    borderLeft: `4px solid ${config.color}`,
                                                    borderBottom: '1px solid #f1f5f9',
                                                    background: idx % 2 === 0 ? '#fff' : '#fafafa',
                                                    cursor: 'pointer',
                                                }}
                                                onClick={() => handleEventClick(event)}
                                            >
                                                <div className="d-flex align-items-start gap-3">
                                                    <div
                                                        style={{
                                                            width: '44px',
                                                            height: '44px',
                                                            borderRadius: '12px',
                                                            background: config.bgColor,
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                            flexShrink: 0,
                                                        }}
                                                    >
                                                        <i className={config.icon} style={{ color: config.color, fontSize: '20px' }}></i>
                                                    </div>
                                                    <div className="flex-grow-1" style={{ minWidth: 0 }}>
                                                        <div className="d-flex align-items-center justify-content-between mb-1">
                                                            <h6 className="mb-0 text-truncate" style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b' }}>
                                                                {event.clienteName || event.title}
                                                            </h6>
                                                            <span
                                                                style={{
                                                                    fontSize: '10px',
                                                                    background: statusConfig.bgColor,
                                                                    color: statusConfig.color,
                                                                    padding: '3px 8px',
                                                                    borderRadius: '12px',
                                                                    fontWeight: 600,
                                                                    flexShrink: 0,
                                                                    marginLeft: '8px',
                                                                }}
                                                            >
                                                                {statusConfig.label}
                                                            </span>
                                                        </div>
                                                        {event.category && (
                                                            <p className="mb-1" style={{ fontSize: '12px', color: '#64748b' }}>
                                                                <i className="ri-price-tag-3-line me-1"></i>
                                                                {config.label}
                                                            </p>
                                                        )}
                                                        <div className="d-flex align-items-center gap-3" style={{ fontSize: '12px', color: '#94a3b8' }}>
                                                            <span>
                                                                <i className="ri-time-line me-1"></i>
                                                                {event.time}
                                                            </span>
                                                            {event.location && (
                                                                <span>
                                                                    <i className="ri-map-pin-line me-1"></i>
                                                                    {event.location}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="mt-2 d-flex gap-2">
                                                    {event.meetingLink && (
                                                        <button
                                                            className="btn btn-sm"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleStartCall(event.meetingLink);
                                                            }}
                                                            style={{
                                                                background: '#22c55e',
                                                                color: '#fff',
                                                                borderRadius: '8px',
                                                                fontSize: '11px',
                                                                padding: '5px 12px',
                                                            }}
                                                        >
                                                            <i className="ri-video-chat-line me-1"></i> Avvia Call
                                                        </button>
                                                    )}
                                                    {event.clienteId && (
                                                        <Link
                                                            to={`/clienti-dettaglio/${event.clienteId}`}
                                                            className="btn btn-sm"
                                                            onClick={(e) => e.stopPropagation()}
                                                            style={{
                                                                background: '#f1f5f9',
                                                                color: '#64748b',
                                                                borderRadius: '8px',
                                                                fontSize: '11px',
                                                                padding: '5px 12px',
                                                            }}
                                                        >
                                                            <i className="ri-user-line me-1"></i> Scheda Cliente
                                                        </Link>
                                                    )}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Event Detail Modal */}
            {showEventModal && selectedEvent && (
                <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={() => setShowEventModal(false)}>
                    <div className="modal-dialog modal-dialog-centered" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-content" style={{ borderRadius: '16px', border: 'none' }}>
                            <div className="modal-header border-0 pb-0">
                                <h5 className="modal-title fw-bold">{selectedEvent.title}</h5>
                                <button type="button" className="btn-close" onClick={() => setShowEventModal(false)}></button>
                            </div>
                            <div className="modal-body">
                                <div className="mb-3">
                                    <div className="d-flex align-items-center gap-2 mb-2">
                                        <i className="ri-time-line text-muted"></i>
                                        <span>{selectedEvent.time}</span>
                                        {selectedEvent.endDate && (
                                            <span className="text-muted">
                                                - {selectedEvent.endDate.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        )}
                                    </div>
                                    <div className="d-flex align-items-center gap-2 mb-2">
                                        <i className="ri-calendar-line text-muted"></i>
                                        <span>{formatDate(selectedEvent.date)}</span>
                                    </div>
                                    {selectedEvent.clienteName && (
                                        <div className="d-flex align-items-center gap-2 mb-2">
                                            <i className="ri-user-line text-muted"></i>
                                            <span>{selectedEvent.clienteName}</span>
                                        </div>
                                    )}
                                    {selectedEvent.category && (
                                        <div className="d-flex align-items-center gap-2 mb-2">
                                            <i className="ri-price-tag-3-line text-muted"></i>
                                            <span>{getEventConfig(selectedEvent).label}</span>
                                        </div>
                                    )}
                                    {selectedEvent.location && (
                                        <div className="d-flex align-items-center gap-2 mb-2">
                                            <i className="ri-map-pin-line text-muted"></i>
                                            <span>{selectedEvent.location}</span>
                                        </div>
                                    )}
                                    {selectedEvent.description && (
                                        <div className="mt-3 p-3 bg-light rounded">
                                            <small className="text-muted">{selectedEvent.description}</small>
                                        </div>
                                    )}
                                    {selectedEvent.meetingNotes && (
                                        <div className="mt-3">
                                            <strong className="small">Note:</strong>
                                            <p className="mb-0 mt-1 text-muted small">{selectedEvent.meetingNotes}</p>
                                        </div>
                                    )}
                                    {selectedEvent.loomLink && (
                                        <div className="mt-3">
                                            <a href={selectedEvent.loomLink} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-outline-primary">
                                                <i className="ri-video-line me-1"></i> Guarda Registrazione Loom
                                            </a>
                                        </div>
                                    )}
                                </div>
                            </div>
                            <div className="modal-footer border-0 pt-0">
                                {selectedEvent.meetingLink && (
                                    <button
                                        className="btn btn-success"
                                        onClick={() => handleStartCall(selectedEvent.meetingLink)}
                                    >
                                        <i className="ri-video-chat-line me-2"></i>
                                        Avvia Call
                                    </button>
                                )}
                                {selectedEvent.clienteId && (
                                    <Link
                                        to={`/clienti-dettaglio/${selectedEvent.clienteId}`}
                                        className="btn btn-outline-secondary"
                                        onClick={() => setShowEventModal(false)}
                                    >
                                        <i className="ri-user-line me-2"></i>
                                        Vai al Cliente
                                    </Link>
                                )}
                                <button className="btn btn-light" onClick={() => setShowEventModal(false)}>
                                    Chiudi
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

export default Calendario;

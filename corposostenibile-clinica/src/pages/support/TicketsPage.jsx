import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import itSupportService from '../../services/itSupportService';
import OpenTicketModal from '../../components/support/OpenTicketModal';
import TicketStatusBadge from '../../components/support/TicketStatusBadge';
import './TicketsPage.css';

const TIPO_ICONS = {
    bug: 'ri-bug-line',
    dato_errato: 'ri-error-warning-line',
    accesso: 'ri-lock-2-line',
    lentezza: 'ri-dashboard-line',
};

const TIPO_LABELS = {
    bug: 'Bug',
    dato_errato: 'Dato errato',
    accesso: 'Accesso',
    lentezza: 'Lentezza',
};

const MODULO_LABELS = {
    assegnazioni: 'Assegnazioni',
    calendario: 'Calendario',
    check: 'Check',
    clienti: 'Clienti',
    dashboard: 'Dashboard',
    formazione: 'Formazione',
    generico: 'Generico',
    profilo: 'Profilo',
    quality: 'Quality',
    supporto: 'Supporto',
    task: 'Task',
    team: 'Team',
};

const STAT_CARDS = [
    { key: 'total',   label: 'Totale',     icon: 'ri-inbox-line',          color: '#25B36A', bg: 'rgba(37, 179, 106, 0.08)' },
    { key: 'nuovi',   label: 'Nuovi',      icon: 'ri-mail-line',           color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.08)' },
    { key: 'in_corso', label: 'In corso',  icon: 'ri-loader-4-line',       color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.08)' },
    { key: 'chiusi',  label: 'Chiusi',     icon: 'ri-check-double-line',   color: '#64748b', bg: 'rgba(100, 116, 139, 0.08)' },
];

const STATUS_FILTER_OPTIONS = [
    { value: '',                 label: 'Tutti gli stati' },
    { value: 'nuovo',            label: 'Nuovo' },
    { value: 'in_triage',        label: 'In triage' },
    { value: 'in_lavorazione',   label: 'In lavorazione' },
    { value: 'in_attesa_utente', label: 'In attesa utente' },
    { value: 'da_testare',       label: 'Da testare' },
    { value: 'risolto',          label: 'Risolto' },
    { value: 'non_valido',       label: 'Non valido' },
];

export default function TicketsPage() {
    const navigate = useNavigate();
    const [tickets, setTickets] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [statusFilter, setStatusFilter] = useState('');
    const [activeStatCard, setActiveStatCard] = useState('total');

    const fetchTickets = useCallback(async (silent = false) => {
        if (!silent) setIsLoading(true);
        setIsRefreshing(silent);
        setError(null);
        try {
            const data = await itSupportService.listMyTickets();
            setTickets(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error('[TicketsPage] fetch error', err);
            setError(
                err?.response?.data?.description
                || err?.message
                || 'Impossibile caricare i ticket'
            );
        } finally {
            setIsLoading(false);
            setIsRefreshing(false);
        }
    }, []);

    useEffect(() => {
        fetchTickets();
    }, [fetchTickets]);

    const counters = useMemo(() => {
        const c = { total: tickets.length, nuovi: 0, in_corso: 0, chiusi: 0 };
        tickets.forEach((t) => {
            if (t.status === 'nuovo') c.nuovi += 1;
            if (['risolto', 'non_valido'].includes(t.status)) c.chiusi += 1;
            else c.in_corso += 1;
        });
        // correct: in_corso non include i nuovi? li includiamo
        c.in_corso = tickets.filter(t => !['risolto', 'non_valido', 'nuovo'].includes(t.status)).length;
        return c;
    }, [tickets]);

    const filteredTickets = useMemo(() => {
        let list = tickets;
        // Stat card quick filter
        if (activeStatCard === 'nuovi') {
            list = list.filter(t => t.status === 'nuovo');
        } else if (activeStatCard === 'in_corso') {
            list = list.filter(t => !['risolto', 'non_valido', 'nuovo'].includes(t.status));
        } else if (activeStatCard === 'chiusi') {
            list = list.filter(t => ['risolto', 'non_valido'].includes(t.status));
        }
        // Dropdown status filter
        if (statusFilter) {
            list = list.filter(t => t.status === statusFilter);
        }
        return list;
    }, [tickets, activeStatCard, statusFilter]);

    const handleStatCardClick = (key) => {
        setActiveStatCard(key);
        setStatusFilter('');
    };

    const handleCreated = (newTicket) => {
        setIsModalOpen(false);
        setTickets((prev) => [newTicket, ...prev]);
    };

    return (
        <div className="its-page">
            {/* Header */}
            <div className="its-header">
                <div className="its-header-left">
                    <img src="/suitemind.png" alt="Suite" className="its-header-logo" />
                    <div>
                        <h4>I miei ticket IT</h4>
                        <p>
                            {counters.total === 0
                                ? 'Nessun ticket aperto al momento'
                                : `${counters.total} ticket${counters.total !== 1 ? '' : ''} — ${counters.in_corso + counters.nuovi} attiv${(counters.in_corso + counters.nuovi) !== 1 ? 'i' : 'o'}`}
                        </p>
                    </div>
                </div>
                <div className="its-header-actions">
                    <button
                        className="its-refresh-btn"
                        onClick={() => fetchTickets(true)}
                        disabled={isRefreshing}
                        title="Aggiorna"
                    >
                        <i className={`ri-refresh-line ${isRefreshing ? 'spin' : ''}`}></i>
                    </button>
                    <button
                        className="its-btn-primary"
                        onClick={() => setIsModalOpen(true)}
                    >
                        <i className="ri-add-line"></i>
                        <span>Apri nuovo ticket</span>
                    </button>
                </div>
            </div>

            {/* Scope notice */}
            <div className="its-scope-notice" role="note">
                <i className="ri-information-line"></i>
                <span>
                    <strong>Quest'area è solo per problemi tecnici della piattaforma.</strong>
                    {' '}Per richieste su clienti, team o questioni organizzative, rivolgiti al tuo responsabile.
                </span>
            </div>

            {/* Stats */}
            <div className="its-stats-row">
                {STAT_CARDS.map((stat) => (
                    <div
                        key={stat.key}
                        className={`its-stat-card ${activeStatCard === stat.key ? 'active' : ''}`}
                        onClick={() => handleStatCardClick(stat.key)}
                        style={{ '--stat-color': stat.color, '--stat-icon-bg': stat.bg }}
                    >
                        <div className="its-stat-content">
                            <div>
                                <div className="its-stat-value">{counters[stat.key]}</div>
                                <div className="its-stat-label">{stat.label}</div>
                            </div>
                            <div className="its-stat-icon">
                                <i className={stat.icon}></i>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Filter */}
            <div className="its-filter-card">
                <span className="its-filter-label">
                    <i className="ri-filter-line"></i> Filtra per stato:
                </span>
                <select
                    className="its-filter-select"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                >
                    {STATUS_FILTER_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                </select>
                {(statusFilter || activeStatCard !== 'total') && (
                    <button
                        className="its-btn-ghost"
                        onClick={() => { setStatusFilter(''); setActiveStatCard('total'); }}
                    >
                        <i className="ri-close-line"></i> Reset filtri
                    </button>
                )}
            </div>

            {/* Body */}
            {isLoading && (
                <div className="its-state its-state-loading">
                    <i className="ri-loader-4-line"></i>
                    Caricamento ticket…
                </div>
            )}

            {!isLoading && error && (
                <div className="its-state its-state-error">
                    <div>⚠️ {error}</div>
                    <button className="its-btn-ghost" onClick={() => fetchTickets()}>
                        <i className="ri-refresh-line"></i> Riprova
                    </button>
                </div>
            )}

            {!isLoading && !error && filteredTickets.length === 0 && (
                <div className="its-state its-state-empty">
                    <div className="its-state-empty-icon">
                        <i className="ri-inbox-line"></i>
                    </div>
                    <h5>
                        {tickets.length === 0
                            ? 'Nessun ticket aperto'
                            : 'Nessun ticket con questi filtri'}
                    </h5>
                    <p>
                        {tickets.length === 0
                            ? 'Quando apri un ticket IT, lo vedrai qui.'
                            : 'Prova a modificare i filtri per vedere altri ticket.'}
                    </p>
                    {tickets.length === 0 && (
                        <button className="its-btn-primary" onClick={() => setIsModalOpen(true)}>
                            <i className="ri-add-line"></i>
                            <span>Apri il tuo primo ticket</span>
                        </button>
                    )}
                </div>
            )}

            {!isLoading && !error && filteredTickets.length > 0 && (
                <div className="its-list">
                    {filteredTickets.map((ticket, idx) => (
                        <div
                            key={ticket.id}
                            className="its-list-item"
                            style={{ animationDelay: `${Math.min(idx * 0.03, 0.3)}s` }}
                        >
                            <Link
                                to={`/supporto/ticket/${ticket.id}`}
                                className="its-list-link"
                                onClick={() => window.scrollTo(0, 0)}
                            >
                                <div className={`its-list-icon tipo-${ticket.tipo}`}>
                                    <i className={TIPO_ICONS[ticket.tipo] || 'ri-ticket-2-line'}></i>
                                </div>
                                <div className="its-list-main">
                                    <div className="its-list-row-top">
                                        <span className="its-list-number">{ticket.ticket_number}</span>
                                        <TicketStatusBadge status={ticket.status} />
                                    </div>
                                    <h3 className="its-list-title">{ticket.title}</h3>
                                    <div className="its-list-meta">
                                        <span className="its-chip">
                                            {TIPO_LABELS[ticket.tipo] || ticket.tipo}
                                        </span>
                                        <span className="its-chip">
                                            <i className="ri-folder-2-line"></i>
                                            {MODULO_LABELS[ticket.modulo] || ticket.modulo}
                                        </span>
                                        {ticket.criticita === 'bloccante' && (
                                            <span className="its-chip chip-danger">
                                                <i className="ri-alarm-warning-line"></i>
                                                Bloccante
                                            </span>
                                        )}
                                        {ticket.comments_count > 0 && (
                                            <span className="its-chip chip-muted">
                                                <i className="ri-chat-3-line"></i>
                                                {ticket.comments_count}
                                            </span>
                                        )}
                                        {ticket.attachments_count > 0 && (
                                            <span className="its-chip">
                                                <i className="ri-attachment-line"></i>
                                                {ticket.attachments_count}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="its-list-date">
                                    <span className="its-date-relative">{formatRelative(ticket.created_at)}</span>
                                    <span>{formatDate(ticket.created_at)}</span>
                                </div>
                            </Link>
                        </div>
                    ))}
                </div>
            )}

            {isModalOpen && (
                <OpenTicketModal
                    onClose={() => setIsModalOpen(false)}
                    onCreated={handleCreated}
                />
            )}
        </div>
    );
}

function formatDate(iso) {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        return d.toLocaleDateString('it-IT', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
        });
    } catch { return iso; }
}

function formatRelative(iso) {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        const diff = (Date.now() - d.getTime()) / 1000;
        if (diff < 60) return 'ora';
        if (diff < 3600) return `${Math.floor(diff / 60)} min fa`;
        if (diff < 86400) return `${Math.floor(diff / 3600)} h fa`;
        if (diff < 604800) return `${Math.floor(diff / 86400)} g fa`;
        return d.toLocaleDateString('it-IT', { day: '2-digit', month: 'short' });
    } catch { return ''; }
}

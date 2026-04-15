import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ghlSupportService from '../../services/ghlSupportService';
import './GhlEmbed.css';

const STATUS_LABELS = {
    nuovo: 'Nuovo',
    in_analisi: 'In analisi',
    in_lavorazione: 'In lavorazione',
    in_attesa_highlevel: 'In attesa HighLevel',
    in_attesa_utente: 'In attesa tua',
    risolto: 'Risolto',
    non_valido: 'Non valido',
};

const STAT_CARDS = [
    { key: 'total', label: 'Totale' },
    { key: 'nuovi', label: 'Nuovi' },
    { key: 'in_corso', label: 'In corso' },
    { key: 'chiusi', label: 'Chiusi' },
];

// ───────────────────────────────────────────────────────────────────────────

export default function GhlEmbedTicketsPage() {
    const navigate = useNavigate();
    const [bootstrapState, setBootstrapState] = useState('loading'); // loading|ready|error
    const [bootstrapError, setBootstrapError] = useState(null);
    const [user, setUser] = useState(null);

    const [tickets, setTickets] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [loadError, setLoadError] = useState(null);

    const [isModalOpen, setIsModalOpen] = useState(false);
    const [activeStatCard, setActiveStatCard] = useState('total');

    // ── Bootstrap SSO al primo mount ────────────────────────────────────────
    useEffect(() => {
        let cancelled = false;

        async function bootstrap() {
            // 1) Se c'è already un token, verifica validità
            const existingToken = ghlSupportService.getToken();
            if (existingToken) {
                try {
                    const me = await ghlSupportService.verifySession();
                    if (me && !cancelled) {
                        setUser(me);
                        setBootstrapState('ready');
                        return;
                    }
                } catch (err) {
                    console.warn('[GhlEmbed] verifica sessione fallita', err);
                }
            }

            // 2) Altrimenti prova exchange dai placeholder GHL in query string
            const params = new URLSearchParams(window.location.search);
            const userId = params.get('user_id');
            if (!userId) {
                if (!cancelled) {
                    setBootstrapError('Parametri GHL mancanti. Accedi dal menu "Ticket IT" dentro GoHighLevel.');
                    setBootstrapState('error');
                }
                return;
            }

            try {
                const data = await ghlSupportService.exchangeSession({
                    user_id: userId,
                    user_email: params.get('user_email') || '',
                    user_name: params.get('user_name') || '',
                    role: params.get('role') || '',
                    location_id: params.get('location_id') || '',
                    location_name: params.get('location_name') || '',
                });
                if (cancelled) return;

                setUser(data.user);
                setBootstrapState('ready');

                // Pulisci URL (rimuovi query string per privacy)
                window.history.replaceState({}, '', window.location.pathname);
            } catch (err) {
                if (cancelled) return;
                console.error('[GhlEmbed] SSO exchange failed', err);
                setBootstrapError(
                    err?.response?.data?.description
                    || err?.message
                    || 'Impossibile stabilire la sessione'
                );
                setBootstrapState('error');
            }
        }

        bootstrap();
        return () => { cancelled = true; };
    }, []);

    // ── Fetch tickets ───────────────────────────────────────────────────────
    const fetchTickets = useCallback(async (silent = false) => {
        if (!silent) setIsLoading(true);
        setIsRefreshing(silent);
        setLoadError(null);
        try {
            const data = await ghlSupportService.listMyTickets();
            setTickets(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error('[GhlEmbed] fetch error', err);
            setLoadError(
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
        if (bootstrapState === 'ready') fetchTickets();
    }, [bootstrapState, fetchTickets]);

    // ── Counters + filters ──────────────────────────────────────────────────

    const counters = useMemo(() => {
        const c = { total: tickets.length, nuovi: 0, in_corso: 0, chiusi: 0 };
        tickets.forEach(t => {
            if (t.status === 'nuovo') c.nuovi += 1;
            else if (['risolto', 'non_valido'].includes(t.status)) c.chiusi += 1;
            else c.in_corso += 1;
        });
        return c;
    }, [tickets]);

    const filteredTickets = useMemo(() => {
        switch (activeStatCard) {
            case 'nuovi': return tickets.filter(t => t.status === 'nuovo');
            case 'in_corso': return tickets.filter(t => !['nuovo', 'risolto', 'non_valido'].includes(t.status));
            case 'chiusi': return tickets.filter(t => ['risolto', 'non_valido'].includes(t.status));
            default: return tickets;
        }
    }, [tickets, activeStatCard]);

    const handleTicketCreated = (newTicket) => {
        setIsModalOpen(false);
        setTickets(prev => [newTicket, ...prev]);
    };

    // ── Bootstrap state rendering ───────────────────────────────────────────

    if (bootstrapState === 'loading') {
        return (
            <div className="ghle-page">
                <div className="ghle-container">
                    <div className="ghle-state ghle-state-loading">
                        <i className="ri-loader-4-line"></i>
                        Autenticazione con GoHighLevel…
                    </div>
                </div>
            </div>
        );
    }

    if (bootstrapState === 'error') {
        return (
            <div className="ghle-page">
                <div className="ghle-container">
                    <div className="ghle-state ghle-state-error">
                        <i className="ri-alert-line" style={{ fontSize: 32, marginBottom: 8 }}></i>
                        <h3>Accesso non autorizzato</h3>
                        <p>{bootstrapError}</p>
                    </div>
                </div>
            </div>
        );
    }

    // ── Main render ─────────────────────────────────────────────────────────

    return (
        <div className="ghle-page">
            <div className="ghle-container">
                {/* Header */}
                <div className="ghle-header">
                    <div className="ghle-header-left">
                        <div className="ghle-header-icon">
                            <i className="ri-customer-service-2-line"></i>
                        </div>
                        <div className="ghle-header-title">
                            <h1>Ticket IT — GoHighLevel</h1>
                            <p>
                                {user?.name || user?.email || 'Utente GHL'} ·{' '}
                                {counters.total === 0
                                    ? 'Nessun ticket aperto'
                                    : `${counters.total} ticket`}
                            </p>
                        </div>
                    </div>
                    <div className="ghle-header-actions">
                        <button
                            className="ghle-refresh-btn"
                            onClick={() => fetchTickets(true)}
                            disabled={isRefreshing}
                            title="Aggiorna"
                        >
                            <i className={`ri-refresh-line ${isRefreshing ? 'spin' : ''}`}></i>
                        </button>
                        <button
                            className="ghle-btn ghle-btn-primary"
                            onClick={() => setIsModalOpen(true)}
                        >
                            <i className="ri-add-line"></i>
                            Nuovo ticket
                        </button>
                    </div>
                </div>

                {/* Stats */}
                <div className="ghle-stats">
                    {STAT_CARDS.map(stat => (
                        <div
                            key={stat.key}
                            className={`ghle-stat-card ${activeStatCard === stat.key ? 'active' : ''}`}
                            onClick={() => setActiveStatCard(stat.key)}
                        >
                            <div className="ghle-stat-value">{counters[stat.key]}</div>
                            <div className="ghle-stat-label">{stat.label}</div>
                        </div>
                    ))}
                </div>

                {/* Body */}
                {isLoading && (
                    <div className="ghle-state-loading">
                        <i className="ri-loader-4-line"></i>
                        Caricamento ticket…
                    </div>
                )}

                {!isLoading && loadError && (
                    <div className="ghle-state ghle-state-error">
                        <div>{loadError}</div>
                        <button className="ghle-btn ghle-btn-ghost" onClick={() => fetchTickets()}
                                style={{ marginTop: 12 }}>
                            <i className="ri-refresh-line"></i> Riprova
                        </button>
                    </div>
                )}

                {!isLoading && !loadError && filteredTickets.length === 0 && (
                    <div className="ghle-state">
                        <div className="ghle-state-empty-icon">
                            <i className="ri-inbox-line"></i>
                        </div>
                        <h3>
                            {tickets.length === 0
                                ? 'Nessun ticket aperto'
                                : 'Nessun ticket con questo filtro'}
                        </h3>
                        <p>
                            {tickets.length === 0
                                ? 'Apri il tuo primo ticket per un problema con GoHighLevel.'
                                : 'Cambia filtro per vedere altri ticket.'}
                        </p>
                        {tickets.length === 0 && (
                            <button className="ghle-btn ghle-btn-primary"
                                    onClick={() => setIsModalOpen(true)}>
                                <i className="ri-add-line"></i> Apri il primo ticket
                            </button>
                        )}
                    </div>
                )}

                {!isLoading && !loadError && filteredTickets.length > 0 && (
                    <div className="ghle-list">
                        {filteredTickets.map(ticket => (
                            <div
                                key={ticket.id}
                                className="ghle-list-item"
                                onClick={() => navigate(`/ghl-embed/tickets/${ticket.id}`)}
                            >
                                <div className="ghle-list-main">
                                    <div className="ghle-list-top">
                                        <span className="ghle-list-number">{ticket.ticket_number}</span>
                                        <StatusBadge status={ticket.status} />
                                    </div>
                                    <h3 className="ghle-list-title">{ticket.title}</h3>
                                    <div className="ghle-list-meta">
                                        {ticket.comments_count > 0 && (
                                            <span>
                                                <i className="ri-chat-3-line"></i> {ticket.comments_count}
                                            </span>
                                        )}
                                        {ticket.attachments_count > 0 && (
                                            <span>
                                                <i className="ri-attachment-line"></i> {ticket.attachments_count}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="ghle-list-date">
                                    {formatRelative(ticket.created_at)}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {isModalOpen && (
                    <OpenTicketModal
                        onClose={() => setIsModalOpen(false)}
                        onCreated={handleTicketCreated}
                    />
                )}
            </div>
        </div>
    );
}

// ───────────────────────────────────────────────────────────────────────────
// MODAL apertura ticket — 3 campi: titolo, descrizione, allegati
// ───────────────────────────────────────────────────────────────────────────

function OpenTicketModal({ onClose, onCreated }) {
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [attachments, setAttachments] = useState([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);
    const titleRef = useRef(null);

    useEffect(() => {
        if (titleRef.current) titleRef.current.focus();
    }, []);

    useEffect(() => {
        const onKey = (e) => { if (e.key === 'Escape' && !isSubmitting) onClose?.(); };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [onClose, isSubmitting]);

    const handleFiles = (files) => {
        const arr = Array.from(files || []);
        const MAX_MB = 10;
        const filtered = arr.filter(f => {
            if (f.size > MAX_MB * 1024 * 1024) {
                setError(`"${f.name}" supera ${MAX_MB}MB`);
                return false;
            }
            return true;
        });
        setAttachments(prev => [...prev, ...filtered].slice(0, 5));
    };

    const removeAttachment = (idx) => {
        setAttachments(prev => prev.filter((_, i) => i !== idx));
    };

    const isValid = title.trim().length > 0 && description.trim().length >= 10;

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!isValid || isSubmitting) return;
        setIsSubmitting(true);
        setError(null);
        try {
            const ticket = await ghlSupportService.createTicket({
                title: title.trim(),
                description: description.trim(),
            });
            for (const file of attachments) {
                try {
                    await ghlSupportService.uploadAttachment(ticket.id, file);
                } catch (attErr) {
                    console.error('[GhlEmbed] upload attachment failed', attErr);
                }
            }
            onCreated?.(ticket);
        } catch (err) {
            console.error('[GhlEmbed] create error', err);
            setError(
                err?.response?.data?.description
                || err?.message
                || 'Impossibile creare il ticket'
            );
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="ghle-modal-backdrop" onClick={() => !isSubmitting && onClose?.()}>
            <div className="ghle-modal" onClick={e => e.stopPropagation()}
                 role="dialog" aria-modal="true">
                <form onSubmit={handleSubmit}>
                    <header className="ghle-modal-header">
                        <h2>
                            <i className="ri-ticket-2-line"></i> Apri un ticket IT
                        </h2>
                        <button type="button" className="ghle-modal-close"
                                onClick={onClose} disabled={isSubmitting}
                                aria-label="Chiudi">
                            <i className="ri-close-line"></i>
                        </button>
                    </header>

                    <div className="ghle-modal-body">
                        {error && (
                            <div className="ghle-alert-error">
                                <i className="ri-error-warning-line"></i>
                                {error}
                            </div>
                        )}

                        <div className="ghle-field">
                            <label>
                                Titolo<span className="ghle-required">*</span>
                            </label>
                            <input
                                ref={titleRef}
                                type="text"
                                className="ghle-input"
                                value={title}
                                onChange={e => setTitle(e.target.value)}
                                placeholder="Riassumi il problema in una frase"
                                maxLength={120}
                                required
                                disabled={isSubmitting}
                            />
                        </div>

                        <div className="ghle-field">
                            <label>
                                Descrizione<span className="ghle-required">*</span>
                            </label>
                            <textarea
                                className="ghle-textarea"
                                value={description}
                                onChange={e => setDescription(e.target.value)}
                                placeholder="Cosa stavi facendo, cosa è successo, cosa ti aspettavi…"
                                rows={6}
                                required
                                disabled={isSubmitting}
                            />
                        </div>

                        <div className="ghle-field">
                            <label>
                                Allegati <span style={{ color: 'var(--ghle-text-muted)', fontWeight: 400 }}>
                                    (max 5 file, 10MB ciascuno)
                                </span>
                            </label>
                            <div
                                className="ghle-dropzone"
                                onClick={() => fileInputRef.current?.click()}
                                onDragOver={e => {
                                    e.preventDefault();
                                    e.currentTarget.classList.add('is-dragging');
                                }}
                                onDragLeave={e => e.currentTarget.classList.remove('is-dragging')}
                                onDrop={e => {
                                    e.preventDefault();
                                    e.currentTarget.classList.remove('is-dragging');
                                    handleFiles(e.dataTransfer.files);
                                }}
                            >
                                <i className="ri-upload-cloud-2-line" style={{ fontSize: 24 }}></i>
                                <div style={{ marginTop: 4 }}>
                                    Trascina file o clicca per selezionarli
                                </div>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    hidden
                                    multiple
                                    accept="image/*,application/pdf,video/*,.log,.txt,.json,.csv,.zip"
                                    onChange={e => handleFiles(e.target.files)}
                                    disabled={isSubmitting}
                                />
                            </div>
                            {attachments.length > 0 && (
                                <ul className="ghle-attachments-list">
                                    {attachments.map((file, idx) => (
                                        <li key={`${file.name}-${idx}`}>
                                            <i className="ri-attachment-line"></i>
                                            <span className="ghle-att-name">{file.name}</span>
                                            <span style={{ color: 'var(--ghle-text-muted)' }}>
                                                {(file.size / 1024 / 1024).toFixed(2)} MB
                                            </span>
                                            <button type="button" className="ghle-att-remove"
                                                    onClick={() => removeAttachment(idx)}
                                                    disabled={isSubmitting}
                                                    aria-label="Rimuovi">
                                                <i className="ri-close-line"></i>
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </div>

                    <div className="ghle-version-tag" title="Versione applicazione corrente">
                        <i className="ri-git-commit-line"></i>
                        <span>versione {import.meta.env.VITE_APP_VERSION || 'dev'}</span>
                    </div>

                    <footer className="ghle-modal-footer">
                        <button type="button" className="ghle-btn ghle-btn-ghost"
                                onClick={onClose} disabled={isSubmitting}>
                            Annulla
                        </button>
                        <button type="submit" className="ghle-btn ghle-btn-primary"
                                disabled={!isValid || isSubmitting}>
                            {isSubmitting ? (
                                <>
                                    <i className="ri-loader-4-line spin"></i> Invio…
                                </>
                            ) : (
                                <>
                                    <i className="ri-send-plane-line"></i> Invia ticket
                                </>
                            )}
                        </button>
                    </footer>
                </form>
            </div>
        </div>
    );
}

// ── Status Badge ──────────────────────────────────────────────────────────

function StatusBadge({ status }) {
    const label = STATUS_LABELS[status] || status;
    return (
        <span className={`ghle-status-badge ghle-status-${status}`}>
            {label}
        </span>
    );
}

// ── Helpers ──────────────────────────────────────────────────────────────

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

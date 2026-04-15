import { useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import AuthContext from '../../context/AuthContext';
import itSupportService from '../../services/itSupportService';
import TicketStatusBadge from '../../components/support/TicketStatusBadge';
import './TicketsPage.css';
import './TicketDetail.css';

const POLL_INTERVAL_MS = 20000;

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

export default function TicketDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const auth = useContext(AuthContext);
    const currentUser = auth?.user;

    const [ticket, setTicket] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [newComment, setNewComment] = useState('');
    const [isPosting, setIsPosting] = useState(false);
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef(null);
    const pollRef = useRef(null);
    const commentsEndRef = useRef(null);

    const fetchTicket = useCallback(async () => {
        try {
            const data = await itSupportService.getTicket(id);
            setTicket(data);
            setError(null);
        } catch (err) {
            console.error('[TicketDetail] fetch error', err);
            setError(
                err?.response?.data?.description
                || err?.message
                || 'Impossibile caricare il ticket'
            );
        } finally {
            setIsLoading(false);
        }
    }, [id]);

    useEffect(() => {
        fetchTicket();
    }, [fetchTicket]);

    useEffect(() => {
        if (!id) return undefined;
        pollRef.current = window.setInterval(fetchTicket, POLL_INTERVAL_MS);
        return () => {
            if (pollRef.current) window.clearInterval(pollRef.current);
        };
    }, [fetchTicket, id]);

    useEffect(() => {
        commentsEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }, [ticket?.comments?.length]);

    const handlePostComment = async (e) => {
        e.preventDefault();
        const content = newComment.trim();
        if (!content || isPosting) return;
        setIsPosting(true);
        try {
            await itSupportService.addComment(id, content);
            setNewComment('');
            fetchTicket();
        } catch (err) {
            console.error('[TicketDetail] post comment error', err);
            alert(err?.response?.data?.description || 'Impossibile inviare il commento');
        } finally {
            setIsPosting(false);
        }
    };

    const handleFileSelected = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);
        try {
            await itSupportService.uploadAttachment(id, file);
            fetchTicket();
        } catch (err) {
            console.error('[TicketDetail] upload error', err);
            alert(err?.response?.data?.description || 'Impossibile caricare l\'allegato');
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    if (isLoading) {
        return (
            <div className="its-page">
                <div className="its-state its-state-loading">
                    <i className="ri-loader-4-line"></i>
                    Caricamento ticket…
                </div>
            </div>
        );
    }

    if (error || !ticket) {
        return (
            <div className="its-page">
                <div className="its-state its-state-error">
                    <div>⚠️ {error || 'Ticket non trovato'}</div>
                    <button className="its-btn-ghost" onClick={() => navigate('/supporto/ticket')}>
                        <i className="ri-arrow-left-line"></i> Torna alla lista
                    </button>
                </div>
            </div>
        );
    }

    const canInteract = !['risolto', 'non_valido'].includes(ticket.status);

    return (
        <div className="its-page">
            <button
                type="button"
                className="itd-back"
                onClick={() => navigate('/supporto/ticket')}
            >
                <i className="ri-arrow-left-line"></i>
                <span>Tutti i miei ticket</span>
            </button>

            {/* Header card */}
            <div className="itd-header-card">
                <div className="itd-header-top">
                    <div className="itd-header-title-block">
                        <span className="itd-number">{ticket.ticket_number}</span>
                        <h4 className="itd-title">{ticket.title}</h4>
                    </div>
                    <TicketStatusBadge status={ticket.status} />
                </div>

                <div className="itd-chips">
                    <span className="its-chip">
                        <i className="ri-price-tag-3-line"></i>
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
                    <span className="its-chip">
                        <i className="ri-time-line"></i>
                        {formatDate(ticket.created_at)}
                    </span>
                </div>
            </div>

            {/* Descrizione */}
            <section className="itd-section">
                <div className="itd-section-header">
                    <h5 className="itd-section-title">
                        <i className="ri-file-text-line"></i>
                        Descrizione
                    </h5>
                </div>
                <pre className="itd-description">{ticket.description}</pre>
            </section>

            {/* Link registrazione */}
            {ticket.link_registrazione && (
                <section className="itd-section">
                    <div className="itd-section-header">
                        <h5 className="itd-section-title">
                            <i className="ri-video-line"></i>
                            Video / Registrazione
                        </h5>
                    </div>
                    <a
                        href={ticket.link_registrazione}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="itd-link-external"
                    >
                        <i className="ri-external-link-line"></i>
                        {ticket.link_registrazione}
                    </a>
                </section>
            )}

            {/* Allegati */}
            {ticket.attachments && ticket.attachments.length > 0 && (
                <section className="itd-section">
                    <div className="itd-section-header">
                        <h5 className="itd-section-title">
                            <i className="ri-attachment-line"></i>
                            Allegati
                            <span className="itd-section-count">{ticket.attachments.length}</span>
                        </h5>
                    </div>
                    <ul className="itd-attachments">
                        {ticket.attachments.map((att) => (
                            <li key={att.id}>
                                <a
                                    href={itSupportService.getAttachmentDownloadUrl(att.id)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    <i className="ri-download-2-line"></i>
                                    <span className="itd-att-name">{att.filename}</span>
                                    <span className="itd-att-size">
                                        {(att.file_size / 1024 / 1024).toFixed(2)} MB
                                    </span>
                                </a>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            {/* Commenti */}
            <section className="itd-section">
                <div className="itd-section-header">
                    <h5 className="itd-section-title">
                        <i className="ri-chat-3-line"></i>
                        Commenti
                        <span className="itd-section-count">
                            {ticket.comments?.length || 0}
                        </span>
                    </h5>
                </div>

                <div className="itd-thread">
                    {(!ticket.comments || ticket.comments.length === 0) && (
                        <div className="itd-thread-empty">
                            Nessun commento per ora. Il team IT ti risponderà qui.
                        </div>
                    )}
                    {(ticket.comments || []).map((c) => (
                        <CommentBubble
                            key={c.id}
                            comment={c}
                            isMine={c.author_user_id === currentUser?.id}
                        />
                    ))}
                    <div ref={commentsEndRef} />
                </div>

                {canInteract ? (
                    <form onSubmit={handlePostComment} className="itd-composer">
                        <textarea
                            placeholder="Scrivi un messaggio al team IT…"
                            value={newComment}
                            onChange={(e) => setNewComment(e.target.value)}
                            rows={3}
                            disabled={isPosting}
                            maxLength={10000}
                        />
                        <div className="itd-composer-actions">
                            <span className="itd-composer-info">
                                <i className="ri-information-line"></i>
                                Gli aggiornamenti dal team IT appaiono in automatico ogni 20s
                            </span>
                            <div className="itd-composer-right">
                                <button
                                    type="button"
                                    className="its-btn-ghost"
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={uploading}
                                >
                                    <i className="ri-attachment-line"></i>
                                    {uploading ? 'Upload…' : 'Allega file'}
                                </button>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    hidden
                                    onChange={handleFileSelected}
                                    accept="image/*,application/pdf,video/*,.log,.txt,.json,.csv,.zip"
                                />
                                <button
                                    type="submit"
                                    className="its-btn-primary"
                                    disabled={!newComment.trim() || isPosting}
                                >
                                    <i className="ri-send-plane-line"></i>
                                    {isPosting ? 'Invio…' : 'Invia'}
                                </button>
                            </div>
                        </div>
                    </form>
                ) : (
                    <div className="itd-closed-banner">
                        <i className="ri-lock-2-line"></i>
                        Ticket chiuso. Per ulteriori segnalazioni apri un nuovo ticket.
                    </div>
                )}
            </section>
        </div>
    );
}

function CommentBubble({ comment, isMine }) {
    const isFromClickUp = comment.direction === 'from_clickup';
    return (
        <div className={`itd-bubble ${isMine ? 'itd-bubble-mine' : ''} ${isFromClickUp ? 'itd-bubble-team' : ''}`}>
            <div className="itd-bubble-avatar">
                <i className={isFromClickUp ? 'ri-customer-service-2-line' : 'ri-user-line'}></i>
            </div>
            <div className="itd-bubble-body">
                <div className="itd-bubble-head">
                    <span className="itd-bubble-author">{comment.author_name}</span>
                    {isFromClickUp && <span className="itd-bubble-tag">Team IT</span>}
                    <span className="itd-bubble-time">{formatDateTime(comment.created_at)}</span>
                </div>
                <pre className="itd-bubble-content">{comment.content}</pre>
            </div>
        </div>
    );
}

function formatDate(iso) {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        return d.toLocaleDateString('it-IT', {
            day: '2-digit',
            month: 'long',
            year: 'numeric',
        });
    } catch { return iso; }
}

function formatDateTime(iso) {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        return d.toLocaleString('it-IT', {
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit',
        });
    } catch { return iso; }
}

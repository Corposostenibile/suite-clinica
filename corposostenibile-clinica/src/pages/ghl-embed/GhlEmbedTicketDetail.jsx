import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ghlSupportService from '../../services/ghlSupportService';
import './GhlEmbed.css';

const POLL_INTERVAL_MS = 20000;

const STATUS_LABELS = {
    nuovo: 'Nuovo',
    in_analisi: 'In analisi',
    in_lavorazione: 'In lavorazione',
    in_attesa_highlevel: 'In attesa HighLevel',
    in_attesa_utente: 'In attesa tua',
    risolto: 'Risolto',
    non_valido: 'Non valido',
};

export default function GhlEmbedTicketDetail() {
    const { id } = useParams();
    const navigate = useNavigate();

    const [currentUser, setCurrentUser] = useState(null);
    const [ticket, setTicket] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [newComment, setNewComment] = useState('');
    const [isPosting, setIsPosting] = useState(false);
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef(null);
    const pollRef = useRef(null);
    const commentsEndRef = useRef(null);

    // Bootstrap: verifica sessione
    useEffect(() => {
        const cached = ghlSupportService.getCachedUser();
        if (cached) {
            setCurrentUser(cached);
            return;
        }
        // Se non c'è cache, prova verifySession
        (async () => {
            try {
                const me = await ghlSupportService.verifySession();
                if (me) setCurrentUser(me);
                else navigate('/ghl-embed/tickets', { replace: true });
            } catch {
                navigate('/ghl-embed/tickets', { replace: true });
            }
        })();
    }, [navigate]);

    const fetchTicket = useCallback(async () => {
        try {
            const data = await ghlSupportService.getTicket(id);
            setTicket(data);
            setError(null);
        } catch (err) {
            console.error('[GhlEmbed/detail] fetch', err);
            setError(
                err?.response?.data?.description
                || err?.message
                || 'Impossibile caricare il ticket'
            );
        } finally {
            setIsLoading(false);
        }
    }, [id]);

    useEffect(() => { fetchTicket(); }, [fetchTicket]);

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
            await ghlSupportService.addComment(id, content);
            setNewComment('');
            fetchTicket();
        } catch (err) {
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
            await ghlSupportService.uploadAttachment(id, file);
            fetchTicket();
        } catch (err) {
            alert(err?.response?.data?.description || 'Impossibile caricare l\'allegato');
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleDownload = async (att) => {
        try {
            await ghlSupportService.downloadAttachment(att.id, att.filename);
        } catch (err) {
            alert('Impossibile scaricare l\'allegato');
        }
    };

    if (isLoading) {
        return (
            <div className="ghle-page">
                <div className="ghle-container">
                    <div className="ghle-state-loading">
                        <i className="ri-loader-4-line"></i>
                        Caricamento ticket…
                    </div>
                </div>
            </div>
        );
    }

    if (error || !ticket) {
        return (
            <div className="ghle-page">
                <div className="ghle-container">
                    <div className="ghle-state ghle-state-error">
                        <div>{error || 'Ticket non trovato'}</div>
                        <button className="ghle-btn ghle-btn-ghost"
                                onClick={() => navigate('/ghl-embed/tickets')}
                                style={{ marginTop: 12 }}>
                            <i className="ri-arrow-left-line"></i> Torna alla lista
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    const canInteract = !['risolto', 'non_valido'].includes(ticket.status);
    const statusLabel = STATUS_LABELS[ticket.status] || ticket.status;

    return (
        <div className="ghle-page">
            <div className="ghle-container">
                <button type="button" className="ghle-back"
                        onClick={() => navigate('/ghl-embed/tickets')}>
                    <i className="ri-arrow-left-line"></i> Tutti i miei ticket
                </button>

                {/* Header */}
                <div className="ghle-detail-header">
                    <div className="ghle-detail-top">
                        <div>
                            <span className="ghle-detail-number">{ticket.ticket_number}</span>
                            <h1 className="ghle-detail-title">{ticket.title}</h1>
                        </div>
                        <span className={`ghle-status-badge ghle-status-${ticket.status}`}>
                            {statusLabel}
                        </span>
                    </div>
                </div>

                {/* Descrizione */}
                <section className="ghle-section">
                    <div className="ghle-section-title">
                        <i className="ri-file-text-line"></i> Descrizione
                    </div>
                    <pre className="ghle-description">{ticket.description}</pre>
                </section>

                {/* Allegati */}
                {ticket.attachments && ticket.attachments.length > 0 && (
                    <section className="ghle-section">
                        <div className="ghle-section-title">
                            <i className="ri-attachment-line"></i>
                            Allegati ({ticket.attachments.length})
                        </div>
                        <ul className="ghle-attachments-download">
                            {ticket.attachments.map(att => (
                                <li key={att.id}>
                                    <button type="button" onClick={() => handleDownload(att)}>
                                        <i className="ri-download-2-line"></i>
                                        <span>{att.filename}</span>
                                        <span className="ghle-att-size">
                                            {(att.file_size / 1024 / 1024).toFixed(2)} MB
                                        </span>
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </section>
                )}

                {/* Commenti */}
                <section className="ghle-section">
                    <div className="ghle-section-title">
                        <i className="ri-chat-3-line"></i>
                        Commenti ({ticket.comments?.length || 0})
                    </div>

                    <div className="ghle-thread">
                        {(!ticket.comments || ticket.comments.length === 0) && (
                            <div className="ghle-thread-empty">
                                Nessun commento per ora. Il team IT risponderà qui.
                            </div>
                        )}
                        {(ticket.comments || []).map(c => (
                            <CommentBubble
                                key={c.id}
                                comment={c}
                                isMine={c.author_ghl_user_id === currentUser?.user_id}
                            />
                        ))}
                        <div ref={commentsEndRef} />
                    </div>

                    {canInteract ? (
                        <form onSubmit={handlePostComment} className="ghle-composer">
                            <textarea
                                className="ghle-textarea"
                                placeholder="Scrivi un messaggio al team IT…"
                                value={newComment}
                                onChange={e => setNewComment(e.target.value)}
                                rows={3}
                                disabled={isPosting}
                                maxLength={10000}
                            />
                            <div className="ghle-composer-actions">
                                <span className="ghle-composer-info">
                                    <i className="ri-information-line"></i>
                                    Gli aggiornamenti appaiono automaticamente ogni 20s
                                </span>
                                <div className="ghle-composer-right">
                                    <button type="button" className="ghle-btn ghle-btn-ghost"
                                            onClick={() => fileInputRef.current?.click()}
                                            disabled={uploading}>
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
                                    <button type="submit" className="ghle-btn ghle-btn-primary"
                                            disabled={!newComment.trim() || isPosting}>
                                        <i className="ri-send-plane-line"></i>
                                        {isPosting ? 'Invio…' : 'Invia'}
                                    </button>
                                </div>
                            </div>
                        </form>
                    ) : (
                        <div className="ghle-closed-banner">
                            <i className="ri-lock-2-line"></i>
                            Ticket chiuso. Per ulteriori segnalazioni apri un nuovo ticket.
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
}

function CommentBubble({ comment, isMine }) {
    const isFromTeamIT = comment.direction === 'from_clickup';
    return (
        <div className={`ghle-bubble ${isMine ? 'ghle-bubble-mine' : ''} ${isFromTeamIT ? 'ghle-bubble-team' : ''}`}>
            <div className="ghle-bubble-avatar">
                <i className={isFromTeamIT ? 'ri-customer-service-2-line' : 'ri-user-line'}></i>
            </div>
            <div className="ghle-bubble-body">
                <div className="ghle-bubble-head">
                    <span className="ghle-bubble-author">{comment.author_name}</span>
                    {isFromTeamIT && <span className="ghle-bubble-tag">Team IT</span>}
                    <span className="ghle-bubble-time">{formatDateTime(comment.created_at)}</span>
                </div>
                <pre className="ghle-bubble-content">{comment.content}</pre>
            </div>
        </div>
    );
}

function formatDateTime(iso) {
    if (!iso) return '';
    try {
        const d = new Date(iso);
        return d.toLocaleString('it-IT', {
            day: '2-digit', month: 'short',
            hour: '2-digit', minute: '2-digit',
        });
    } catch { return ''; }
}

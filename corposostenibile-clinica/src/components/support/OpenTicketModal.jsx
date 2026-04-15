import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import itSupportService from '../../services/itSupportService';
import loomService from '../../services/loomService';
import '../../pages/support/TicketsPage.css';
import './OpenTicketModal.css';

const DESCRIPTION_TEMPLATES = {
    bug: `🔴 Cosa è successo:

🟢 Cosa mi aspettavo che succedesse:

🧭 Passi per riprodurre:
1.
2.
3.`,
    dato_errato: `📍 Dove l'ho visto:

🔢 Valore sbagliato:

✅ Valore corretto (se lo sai):`,
    accesso: `🔐 Cosa stavo cercando di fare:

❌ Cosa non riesco a fare:

📍 Dove succede:`,
    lentezza: `🐢 Cosa è lento:

⏱️ Quanto tempo ci mette (stima):

📍 Pagine / azioni interessate:`,
};

const DEFAULT_MODULE_FROM_PATH = () => {
    const path = window.location.pathname.toLowerCase();
    if (path.includes('/clienti')) return 'clienti';
    if (path.includes('/calendario')) return 'calendario';
    if (path.includes('/check')) return 'check';
    if (path.includes('/chat')) return 'generico';
    if (path.includes('/task')) return 'task';
    if (path.includes('/team')) return 'team';
    if (path.includes('/assegna') || path.includes('/suitemind')) return 'assegnazioni';
    if (path.includes('/formazione')) return 'formazione';
    if (path.includes('/quality')) return 'quality';
    if (path.includes('/profilo')) return 'profilo';
    if (path.includes('/supporto') || path.includes('/documentazione')) return 'supporto';
    if (path.includes('/welcome') || path === '/' || path.includes('/dashboard')) return 'dashboard';
    return 'generico';
};

const DEFAULT_FORM = () => ({
    tipo: 'bug',
    modulo: DEFAULT_MODULE_FROM_PATH(),
    criticita: 'non_bloccante',
    title: '',
    description: DESCRIPTION_TEMPLATES.bug,
    cliente_coinvolto: '',
    link_registrazione: '',
});

const DEFAULT_ENUMS = {
    tipo: [
        { value: 'bug', label: 'Bug' },
        { value: 'dato_errato', label: 'Dato errato' },
        { value: 'accesso', label: 'Accesso / Permessi' },
        { value: 'lentezza', label: 'Lentezza' },
    ],
    modulo: [
        { value: 'assegnazioni', label: 'Assegnazioni' },
        { value: 'calendario', label: 'Calendario' },
        { value: 'check', label: 'Check' },
        { value: 'clienti', label: 'Clienti' },
        { value: 'dashboard', label: 'Dashboard' },
        { value: 'formazione', label: 'Formazione' },
        { value: 'generico', label: 'Generico' },
        { value: 'profilo', label: 'Profilo' },
        { value: 'quality', label: 'Quality' },
        { value: 'supporto', label: 'Supporto' },
        { value: 'task', label: 'Task' },
        { value: 'team', label: 'Team' },
    ],
    criticita: [
        { value: 'bloccante', label: 'Bloccante' },
        { value: 'non_bloccante', label: 'Non bloccante' },
    ],
};

export default function OpenTicketModal({ onClose, onCreated }) {
    const [form, setForm] = useState(DEFAULT_FORM);
    const [enums, setEnums] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const [attachments, setAttachments] = useState([]);
    const [descriptionTouched, setDescriptionTouched] = useState(false);
    const [patientSuggestions, setPatientSuggestions] = useState([]);
    const [isSearchingPatients, setIsSearchingPatients] = useState(false);
    const [showPatientDropdown, setShowPatientDropdown] = useState(false);
    const fileInputRef = useRef(null);
    const titleRef = useRef(null);
    const patientInputRef = useRef(null);

    useEffect(() => {
        (async () => {
            try {
                const data = await itSupportService.getEnums();
                setEnums(data);
            } catch (err) {
                console.error('[OpenTicketModal] fetch enums', err);
            }
        })();
    }, []);

    useEffect(() => {
        if (titleRef.current) titleRef.current.focus();
    }, []);

    useEffect(() => {
        const onKey = (e) => {
            if (e.key === 'Escape' && !isSubmitting) onClose?.();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [onClose, isSubmitting]);

    // Debounced patient autocomplete
    useEffect(() => {
        const query = form.cliente_coinvolto.trim();
        // Non cercare se il campo contiene già il marker "(ID ...)" = già selezionato
        if (!showPatientDropdown || query.length < 2 || /\(ID\s+\d+\)\s*$/i.test(query)) {
            setPatientSuggestions([]);
            setIsSearchingPatients(false);
            return undefined;
        }

        let active = true;
        setIsSearchingPatients(true);
        const timer = window.setTimeout(async () => {
            try {
                const items = await loomService.searchPatients(query, 8);
                if (active) setPatientSuggestions(items);
            } catch (err) {
                console.error('[OpenTicketModal] patient search', err);
                if (active) setPatientSuggestions([]);
            } finally {
                if (active) setIsSearchingPatients(false);
            }
        }, 300);

        return () => {
            active = false;
            window.clearTimeout(timer);
        };
    }, [form.cliente_coinvolto, showPatientDropdown]);

    // Click outside patient dropdown
    useEffect(() => {
        const handler = (e) => {
            if (patientInputRef.current && !patientInputRef.current.contains(e.target)) {
                setShowPatientDropdown(false);
            }
        };
        if (showPatientDropdown) {
            document.addEventListener('mousedown', handler);
            return () => document.removeEventListener('mousedown', handler);
        }
        return undefined;
    }, [showPatientDropdown]);

    const handlePatientSelect = (patient) => {
        const display = `${patient.nome_cognome} (ID ${patient.cliente_id})`;
        setForm((prev) => ({ ...prev, cliente_coinvolto: display }));
        setShowPatientDropdown(false);
        setPatientSuggestions([]);
    };

    const handleClearPatient = () => {
        setForm((prev) => ({ ...prev, cliente_coinvolto: '' }));
        setShowPatientDropdown(false);
        setPatientSuggestions([]);
    };

    const handleChange = (field) => (e) => {
        const value = e.target.value;
        setForm((prev) => {
            const next = { ...prev, [field]: value };
            if (field === 'tipo' && !descriptionTouched) {
                next.description = DESCRIPTION_TEMPLATES[value] || '';
            }
            return next;
        });
    };

    const handleDescriptionChange = (e) => {
        setDescriptionTouched(true);
        setForm((prev) => ({ ...prev, description: e.target.value }));
    };

    const handleFiles = (files) => {
        const arr = Array.from(files || []);
        const MAX_MB = 10;
        const filtered = arr.filter((f) => {
            if (f.size > MAX_MB * 1024 * 1024) {
                setError(`"${f.name}" supera ${MAX_MB}MB e verrà ignorato`);
                return false;
            }
            return true;
        });
        setAttachments((prev) => [...prev, ...filtered].slice(0, 5));
    };

    const removeAttachment = (idx) => {
        setAttachments((prev) => prev.filter((_, i) => i !== idx));
    };

    const isFormValid = useMemo(() => {
        return (
            form.title.trim().length > 0
            && form.description.trim().length > 10
            && form.tipo
            && form.modulo
            && form.criticita
        );
    }, [form]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!isFormValid || isSubmitting) return;
        setIsSubmitting(true);
        setError(null);

        try {
            const ticket = await itSupportService.createTicket({
                title: form.title.trim(),
                description: form.description.trim(),
                tipo: form.tipo,
                modulo: form.modulo,
                criticita: form.criticita,
                cliente_coinvolto: form.cliente_coinvolto.trim() || undefined,
                link_registrazione: form.link_registrazione.trim() || undefined,
            });

            for (const file of attachments) {
                try {
                    await itSupportService.uploadAttachment(ticket.id, file);
                } catch (attErr) {
                    console.error('[OpenTicketModal] upload attachment failed', attErr);
                }
            }

            onCreated?.(ticket);
        } catch (err) {
            console.error('[OpenTicketModal] create error', err);
            const message =
                err?.response?.data?.description
                || err?.message
                || 'Impossibile creare il ticket';
            setError(message);
        } finally {
            setIsSubmitting(false);
        }
    };

    return createPortal(
        <div className="otm-backdrop" onClick={() => !isSubmitting && onClose?.()}>
            <div
                className="otm-dialog"
                onClick={(e) => e.stopPropagation()}
                role="dialog"
                aria-modal="true"
            >
                <header className="otm-header">
                    <div className="otm-header-content">
                        <h4>
                            <i className="ri-ticket-2-line"></i>
                            Apri un ticket IT
                        </h4>
                        <p>Descrivi il problema, il team IT ti risponderà il prima possibile.</p>
                    </div>
                    <button
                        type="button"
                        className="otm-close"
                        onClick={onClose}
                        disabled={isSubmitting}
                        aria-label="Chiudi"
                    >
                        <i className="ri-close-line"></i>
                    </button>
                </header>

                <form onSubmit={handleSubmit} className="otm-form">
                    <div className="otm-scope-notice" role="note">
                        <i className="ri-information-line otm-scope-notice-icon"></i>
                        <div className="otm-scope-notice-body">
                            <strong>Quest'area è solo per problemi tecnici della Suite Clinica.</strong>
                            <span> Per richieste su clienti, gestione del team o questioni organizzative, rivolgiti al tuo responsabile.</span>
                        </div>
                    </div>

                    <div className="otm-row otm-row-3">
                        <div className="otm-field">
                            <label className="otm-field-label">
                                <i className="ri-price-tag-3-line"></i>
                                Tipo<span className="otm-field-required">*</span>
                            </label>
                            <select
                                className="otm-select"
                                value={form.tipo}
                                onChange={handleChange('tipo')}
                                required
                                disabled={isSubmitting}
                            >
                                {(enums?.tipo || DEFAULT_ENUMS.tipo).map((o) => (
                                    <option key={o.value} value={o.value}>{o.label}</option>
                                ))}
                            </select>
                        </div>

                        <div className="otm-field">
                            <label className="otm-field-label">
                                <i className="ri-folder-2-line"></i>
                                Modulo<span className="otm-field-required">*</span>
                            </label>
                            <select
                                className="otm-select"
                                value={form.modulo}
                                onChange={handleChange('modulo')}
                                required
                                disabled={isSubmitting}
                            >
                                {(enums?.modulo || DEFAULT_ENUMS.modulo).map((o) => (
                                    <option key={o.value} value={o.value}>{o.label}</option>
                                ))}
                            </select>
                        </div>

                        <div className="otm-field">
                            <label className="otm-field-label">
                                <i className="ri-alarm-warning-line"></i>
                                Criticità<span className="otm-field-required">*</span>
                            </label>
                            <select
                                className="otm-select"
                                value={form.criticita}
                                onChange={handleChange('criticita')}
                                required
                                disabled={isSubmitting}
                            >
                                {(enums?.criticita || DEFAULT_ENUMS.criticita).map((o) => (
                                    <option key={o.value} value={o.value}>{o.label}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div className="otm-field">
                        <label className="otm-field-label">
                            <i className="ri-pencil-line"></i>
                            Titolo<span className="otm-field-required">*</span>
                        </label>
                        <input
                            ref={titleRef}
                            type="text"
                            className="otm-input"
                            value={form.title}
                            onChange={handleChange('title')}
                            placeholder="Riassumi il problema in una frase"
                            maxLength={120}
                            required
                            disabled={isSubmitting}
                        />
                    </div>

                    <div className="otm-field">
                        <label className="otm-field-label">
                            <i className="ri-file-text-line"></i>
                            Descrizione<span className="otm-field-required">*</span>
                            <span className="otm-field-hint">template automatico in base al Tipo</span>
                        </label>
                        <textarea
                            className="otm-textarea"
                            value={form.description}
                            onChange={handleDescriptionChange}
                            placeholder="Descrivi cosa è successo, cosa ti aspettavi e come riprodurre"
                            rows={8}
                            required
                            disabled={isSubmitting}
                        />
                        <div className="otm-hint">
                            <i className="ri-information-line"></i>
                            Sovrascrivi pure il template come preferisci.
                        </div>
                    </div>

                    <div className="otm-field otm-field-patient" ref={patientInputRef}>
                        <label className="otm-field-label">
                            <i className="ri-user-heart-line"></i>
                            Paziente coinvolto
                            <span className="otm-field-hint">opzionale — cerca per nome</span>
                        </label>
                        <div className="otm-autocomplete">
                            <input
                                type="text"
                                className="otm-input"
                                value={form.cliente_coinvolto}
                                onChange={(e) => {
                                    handleChange('cliente_coinvolto')(e);
                                    setShowPatientDropdown(true);
                                }}
                                onFocus={() => setShowPatientDropdown(true)}
                                placeholder="Inizia a scrivere per cercare un paziente…"
                                disabled={isSubmitting}
                                autoComplete="off"
                            />
                            {form.cliente_coinvolto && (
                                <button
                                    type="button"
                                    className="otm-autocomplete-clear"
                                    onClick={handleClearPatient}
                                    aria-label="Svuota"
                                    disabled={isSubmitting}
                                >
                                    <i className="ri-close-line"></i>
                                </button>
                            )}

                            {showPatientDropdown && (isSearchingPatients || patientSuggestions.length > 0) && (
                                <ul className="otm-autocomplete-list">
                                    {isSearchingPatients && (
                                        <li className="otm-autocomplete-empty">
                                            <i className="ri-loader-4-line" style={{ animation: 'itsSpin 1s linear infinite' }}></i>
                                            Ricerca in corso…
                                        </li>
                                    )}
                                    {!isSearchingPatients && patientSuggestions.length === 0 && form.cliente_coinvolto.trim().length >= 2 && (
                                        <li className="otm-autocomplete-empty">
                                            Nessun paziente trovato. Puoi digitare un testo libero.
                                        </li>
                                    )}
                                    {!isSearchingPatients && patientSuggestions.map((p) => (
                                        <li
                                            key={p.cliente_id}
                                            className="otm-autocomplete-item"
                                            onClick={() => handlePatientSelect(p)}
                                        >
                                            <i className="ri-user-3-line"></i>
                                            <div className="otm-autocomplete-item-body">
                                                <div className="otm-autocomplete-item-name">{p.nome_cognome}</div>
                                                <div className="otm-autocomplete-item-meta">ID {p.cliente_id}</div>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </div>

                    <div className="otm-field">
                        <label className="otm-field-label">
                            <i className="ri-video-line"></i>
                            Link video / registrazione Loom
                            <span className="otm-field-hint">opzionale</span>
                        </label>
                        <input
                            type="url"
                            className="otm-input"
                            value={form.link_registrazione}
                            onChange={handleChange('link_registrazione')}
                            placeholder="https://www.loom.com/share/..."
                            disabled={isSubmitting}
                        />
                    </div>

                    <div className="otm-field">
                        <label className="otm-field-label">
                            <i className="ri-attachment-line"></i>
                            Allegati
                            <span className="otm-field-hint">max 5 file, 10MB ciascuno</span>
                        </label>
                        <div
                            className="otm-dropzone"
                            onDragOver={(e) => {
                                e.preventDefault();
                                e.currentTarget.classList.add('is-dragging');
                            }}
                            onDragLeave={(e) => {
                                e.currentTarget.classList.remove('is-dragging');
                            }}
                            onDrop={(e) => {
                                e.preventDefault();
                                e.currentTarget.classList.remove('is-dragging');
                                handleFiles(e.dataTransfer.files);
                            }}
                            onClick={() => fileInputRef.current?.click()}
                            role="button"
                            tabIndex={0}
                        >
                            <i className="ri-upload-cloud-2-line"></i>
                            <span className="otm-dropzone-label">
                                Trascina qui i file o clicca per selezionarli
                            </span>
                            <span className="otm-dropzone-hint">
                                Screenshot, video, log, pdf…
                            </span>
                            <input
                                ref={fileInputRef}
                                type="file"
                                hidden
                                multiple
                                accept="image/*,application/pdf,video/*,.log,.txt,.json,.csv,.zip"
                                onChange={(e) => handleFiles(e.target.files)}
                                disabled={isSubmitting}
                            />
                        </div>
                        {attachments.length > 0 && (
                            <ul className="otm-attachments">
                                {attachments.map((file, idx) => (
                                    <li key={`${file.name}-${idx}`}>
                                        <i className="ri-attachment-line"></i>
                                        <span className="otm-att-name">{file.name}</span>
                                        <span className="otm-att-size">
                                            {(file.size / 1024 / 1024).toFixed(2)} MB
                                        </span>
                                        <button
                                            type="button"
                                            className="otm-att-remove"
                                            onClick={() => removeAttachment(idx)}
                                            disabled={isSubmitting}
                                            aria-label="Rimuovi"
                                        >
                                            <i className="ri-close-line"></i>
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    {error && (
                        <div className="otm-error">
                            <i className="ri-error-warning-line"></i>
                            {error}
                        </div>
                    )}

                    <div className="otm-version-tag" title="Versione applicazione corrente">
                        <i className="ri-git-commit-line"></i>
                        <span>versione {import.meta.env.VITE_APP_VERSION || 'dev'}</span>
                    </div>

                    <div className="otm-actions">
                        <button
                            type="button"
                            className="otm-btn otm-btn-ghost"
                            onClick={onClose}
                            disabled={isSubmitting}
                        >
                            Annulla
                        </button>
                        <button
                            type="submit"
                            className="otm-btn otm-btn-primary"
                            disabled={!isFormValid || isSubmitting}
                        >
                            {isSubmitting ? (
                                <>
                                    <i className="ri-loader-4-line" style={{ animation: 'itsSpin 1s linear infinite' }}></i>
                                    Invio in corso…
                                </>
                            ) : (
                                <>
                                    <i className="ri-send-plane-line"></i>
                                    Invia ticket
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>,
        document.body
    );
}

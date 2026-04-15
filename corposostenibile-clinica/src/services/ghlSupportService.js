import axios from 'axios';

/**
 * Service per il sistema GHL Support Tickets embedded in GoHighLevel.
 * Backend: backend/corposostenibile/blueprints/ghl_support
 *
 * Auth: JWT di sessione ottenuto via POST /sso/exchange al primo mount
 * (scambiando i placeholder GHL in query string). Salvato in sessionStorage
 * scoped al tab iframe. Tutte le API successive usano Bearer header.
 */

const API_BASE = '/api/ghl-support';
const SESSION_KEY = 'ghl_support_session_token';
const USER_CACHE_KEY = 'ghl_support_session_user';

// ── Session storage ────────────────────────────────────────────────────────

function getToken() {
    return sessionStorage.getItem(SESSION_KEY);
}

function setToken(token) {
    sessionStorage.setItem(SESSION_KEY, token);
}

function clearSession() {
    sessionStorage.removeItem(SESSION_KEY);
    sessionStorage.removeItem(USER_CACHE_KEY);
}

function getCachedUser() {
    const raw = sessionStorage.getItem(USER_CACHE_KEY);
    try {
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
}

function setCachedUser(user) {
    sessionStorage.setItem(USER_CACHE_KEY, JSON.stringify(user));
}

// ── HTTP helpers ───────────────────────────────────────────────────────────

function authHeaders() {
    const token = getToken();
    if (!token) {
        throw new Error('GHL session mancante');
    }
    return { Authorization: `Bearer ${token}` };
}

// ── Client helpers browser / OS detection ──────────────────────────────────

function detectBrowser() {
    const ua = navigator.userAgent || '';
    if (/Edg\//.test(ua)) return `Edge ${versionFrom(ua, /Edg\/([\d.]+)/)}`;
    if (/OPR\/|Opera\//.test(ua)) return `Opera ${versionFrom(ua, /(?:OPR|Opera)\/([\d.]+)/)}`;
    if (/Firefox\//.test(ua)) return `Firefox ${versionFrom(ua, /Firefox\/([\d.]+)/)}`;
    if (/Chrome\//.test(ua) && /Safari\//.test(ua))
        return `Chrome ${versionFrom(ua, /Chrome\/([\d.]+)/)}`;
    if (/Safari\//.test(ua) && /Version\//.test(ua))
        return `Safari ${versionFrom(ua, /Version\/([\d.]+)/)}`;
    return 'Sconosciuto';
}

function detectOS() {
    const ua = navigator.userAgent || '';
    const platform = navigator.platform || '';
    if (/Windows NT 10/.test(ua)) return 'Windows 10/11';
    if (/Windows NT/.test(ua)) return 'Windows';
    if (/Mac OS X/.test(ua) || /Macintosh/.test(platform)) return 'macOS';
    if (/iPhone/.test(ua)) return 'iOS (iPhone)';
    if (/iPad/.test(ua)) return 'iPadOS';
    if (/Android/.test(ua)) return 'Android';
    if (/Linux/.test(ua)) return 'Linux';
    return platform || 'Sconosciuto';
}

function versionFrom(ua, regex) {
    const m = ua.match(regex);
    return m ? m[1].split('.').slice(0, 2).join('.') : '';
}

// ── Service ────────────────────────────────────────────────────────────────

const ghlSupportService = {
    // ── Session lifecycle ──────────────────────────────────────────────────

    getToken,
    getCachedUser,
    clearSession,

    /**
     * Scambia i placeholder GHL (da query string) con un JWT di sessione.
     * @param {Object} params - {user_id, user_email, user_name, role, location_id, location_name}
     */
    async exchangeSession(params) {
        const response = await axios.post(`${API_BASE}/sso/exchange`, params);
        const { session_token, user } = response.data;
        setToken(session_token);
        setCachedUser(user);
        return response.data;
    },

    /**
     * Verifica che il JWT in sessionStorage sia ancora valido chiamando /session/me.
     * Se 401 → ritorna null (la pagina dovrà mostrare errore).
     */
    async verifySession() {
        try {
            const response = await axios.get(`${API_BASE}/session/me`, {
                headers: authHeaders(),
            });
            setCachedUser(response.data);
            return response.data;
        } catch (err) {
            if (err?.response?.status === 401) {
                clearSession();
                return null;
            }
            throw err;
        }
    },

    // ── Tickets ────────────────────────────────────────────────────────────

    async listMyTickets(params = {}) {
        const response = await axios.get(`${API_BASE}/tickets/mine`, {
            headers: authHeaders(),
            params,
        });
        return response.data;
    },

    async getTicket(ticketId) {
        const response = await axios.get(`${API_BASE}/tickets/${ticketId}`, {
            headers: authHeaders(),
        });
        return response.data;
    },

    async createTicket({ title, description }) {
        const payload = {
            title,
            description,
            pagina_origine: document.referrer || window.location.href,
            browser: detectBrowser(),
            os: detectOS(),
            user_agent: navigator.userAgent,
        };
        const response = await axios.post(`${API_BASE}/tickets`, payload, {
            headers: authHeaders(),
        });
        return response.data;
    },

    async addComment(ticketId, content) {
        const response = await axios.post(
            `${API_BASE}/tickets/${ticketId}/comments`,
            { content },
            { headers: authHeaders() }
        );
        return response.data;
    },

    async uploadAttachment(ticketId, file) {
        const formData = new FormData();
        formData.append('file', file);
        const response = await axios.post(
            `${API_BASE}/tickets/${ticketId}/attachments`,
            formData,
            {
                headers: {
                    ...authHeaders(),
                    'Content-Type': 'multipart/form-data',
                },
            }
        );
        return response.data;
    },

    /**
     * Download di un allegato via fetch+blob+anchor (serve JWT in header,
     * non si può fare con <a href> semplice).
     */
    async downloadAttachment(attachmentId, filename) {
        const response = await axios.get(
            `${API_BASE}/attachments/${attachmentId}/download`,
            {
                headers: authHeaders(),
                responseType: 'blob',
            }
        );
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || `attachment-${attachmentId}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    },
};

export default ghlSupportService;

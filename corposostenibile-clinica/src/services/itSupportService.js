import api from './api';

/**
 * Service per il sistema IT Support Tickets con integrazione ClickUp.
 * Backend: backend/corposostenibile/blueprints/it_support
 */

const itSupportService = {
  /**
   * Ritorna gli enum validi per il form (tipo / modulo / criticità).
   */
  async getEnums() {
    const response = await api.get('/it-support/enums');
    return response.data;
  },

  /**
   * Crea un nuovo ticket IT.
   * @param {Object} payload
   * @param {string} payload.title
   * @param {string} payload.description
   * @param {string} payload.tipo
   * @param {string} payload.modulo
   * @param {string} payload.criticita
   * @param {string} [payload.cliente_coinvolto]
   * @param {string} [payload.link_registrazione]
   */
  async createTicket(payload) {
    const enriched = {
      ...payload,
      pagina_origine: window.location.href,
      browser: _detectBrowser(),
      os: _detectOS(),
      // SemVer e Git SHA separati: due custom field distinti su ClickUp
      versione_app: import.meta.env.VITE_APP_SEMVER || 'dev',
      commit_sha: import.meta.env.VITE_GIT_COMMIT || 'unknown',
      user_agent: navigator.userAgent,
    };
    const response = await api.post('/it-support/tickets', enriched);
    return response.data;
  },

  /**
   * Lista ticket dell'utente corrente.
   */
  async listMyTickets(params = {}) {
    const response = await api.get('/it-support/tickets/mine', { params });
    return response.data;
  },

  /**
   * Dettaglio di un ticket (include commenti e allegati).
   */
  async getTicket(ticketId) {
    const response = await api.get(`/it-support/tickets/${ticketId}`);
    return response.data;
  },

  /**
   * Aggiunge un commento al ticket. Verrà replicato su ClickUp.
   */
  async addComment(ticketId, content) {
    const response = await api.post(
      `/it-support/tickets/${ticketId}/comments`,
      { content }
    );
    return response.data;
  },

  /**
   * Upload allegato (screenshot, video, log).
   */
  async uploadAttachment(ticketId, file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(
      `/it-support/tickets/${ticketId}/attachments`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return response.data;
  },

  /**
   * URL diretto per scaricare un allegato.
   */
  getAttachmentDownloadUrl(attachmentId) {
    return `/api/it-support/attachments/${attachmentId}/download`;
  },
};

// ── Helpers di rilevamento client-side ────────────────────────────────────

function _detectBrowser() {
  const ua = navigator.userAgent || '';
  if (/Edg\//.test(ua)) return `Edge ${_versionFrom(ua, /Edg\/([\d.]+)/)}`;
  if (/OPR\/|Opera\//.test(ua))
    return `Opera ${_versionFrom(ua, /(?:OPR|Opera)\/([\d.]+)/)}`;
  if (/Firefox\//.test(ua))
    return `Firefox ${_versionFrom(ua, /Firefox\/([\d.]+)/)}`;
  if (/Chrome\//.test(ua) && /Safari\//.test(ua))
    return `Chrome ${_versionFrom(ua, /Chrome\/([\d.]+)/)}`;
  if (/Safari\//.test(ua) && /Version\//.test(ua))
    return `Safari ${_versionFrom(ua, /Version\/([\d.]+)/)}`;
  return 'Sconosciuto';
}

function _detectOS() {
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

function _versionFrom(ua, regex) {
  const match = ua.match(regex);
  return match ? match[1].split('.').slice(0, 2).join('.') : '';
}

export default itSupportService;

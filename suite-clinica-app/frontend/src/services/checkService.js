/**
 * Check Service - API per la gestione dei check settimanali
 *
 * Supporta 3 tipi di check hardcoded:
 * - weekly: Check Settimanale (completo con foto e valutazioni)
 * - dca: Check DCA (disturbi alimentari psicologici)
 * - minor: Check Minori (EDE-Q6 per screening)
 */

import axios from 'axios';

const api = axios.create({
  baseURL: '/client-checks',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Check types configuration
export const CHECK_TYPES = {
  weekly: {
    key: 'weekly',
    label: 'Check Settimanale',
    description: 'Check completo con foto, valutazioni benessere e feedback professionisti',
    icon: 'ri-calendar-check-line',
    color: '#3b82f6',
    bgColor: '#dbeafe'
  },
  dca: {
    key: 'dca',
    label: 'Check DCA',
    description: 'Check psicologico per disturbi del comportamento alimentare',
    icon: 'ri-heart-pulse-line',
    color: '#a855f7',
    bgColor: '#f3e8ff'
  },
  minor: {
    key: 'minor',
    label: 'Check Minori',
    description: 'Questionario screening disturbi alimentari - 28 domande',
    icon: 'ri-mental-health-line',
    color: '#f59e0b',
    bgColor: '#fef3c7'
  }
};

const checkService = {
  // ==================== CLIENTE CHECKS ====================

  /**
   * Get all checks and responses for a client
   * @param {number} clienteId - Client ID
   * @returns {Promise} - { success, checks: { weekly, dca, minor }, responses: [] }
   */
  async getClienteChecks(clienteId) {
    const response = await api.get(`/api/cliente/${clienteId}/checks`);
    return response.data;
  },

  /**
   * Generate or retrieve check link for a client
   * @param {string} checkType - 'weekly', 'dca', or 'minor'
   * @param {number} clienteId - Client ID
   * @returns {Promise} - { success, is_new, check_id, token, url, response_count }
   */
  async generateCheckLink(checkType, clienteId) {
    const response = await api.post(`/api/generate/${checkType}/${clienteId}`);
    return response.data;
  },

  // ==================== DA LEGGERE ====================

  /**
   * Get unread checks for the current professional
   * @returns {Promise} - { success, unread_checks: [], total: number }
   */
  async getUnreadChecks() {
    const response = await api.get('/api/da-leggere');
    return response.data;
  },

  /**
   * Confirm that a check has been read
   * @param {string} responseType - 'weekly_check' or 'dca_check'
   * @param {number} responseId - Response ID
   * @returns {Promise} - { success, message, read_at }
   */
  async confirmRead(responseType, responseId) {
    const response = await api.post(`/api/conferma-lettura/${responseType}/${responseId}`);
    return response.data;
  },

  // ==================== RESPONSE DETAILS ====================

  /**
   * Get detailed response data
   * @param {string} responseType - 'weekly', 'dca', or 'minor'
   * @param {number} responseId - Response ID
   * @returns {Promise} - { success, response: {...} }
   */
  async getResponseDetail(responseType, responseId) {
    const response = await api.get(`/api/response/${responseType}/${responseId}`);
    return response.data;
  },

  // ==================== AZIENDA STATS ====================

  /**
   * Get company-wide check statistics
   * @param {string} period - 'week', 'month', 'trimester', 'year', or 'custom'
   * @param {string} startDate - Start date for custom period (YYYY-MM-DD)
   * @param {string} endDate - End date for custom period (YYYY-MM-DD)
   * @param {string} profType - Professional type filter: 'nutrizione', 'coach', 'psicologia'
   * @param {number} profId - Specific professional ID
   * @returns {Promise} - { success, period, stats: {...}, responses: [] }
   */
  async getAziendaStats(period = 'month', startDate = null, endDate = null, profType = null, profId = null) {
    let url = `/api/azienda/stats?period=${period}`;
    if (period === 'custom' && startDate && endDate) {
      url += `&start_date=${startDate}&end_date=${endDate}`;
    }
    if (profType) {
      url += `&prof_type=${profType}`;
    }
    if (profId) {
      url += `&prof_id=${profId}`;
    }
    const response = await api.get(url);
    return response.data;
  },

  /**
   * Get list of professionals by type
   * @param {string} profType - 'nutrizione', 'coach', 'psicologia'
   * @returns {Promise} - { success, professionisti: [{id, nome, avatar_url}] }
   */
  async getProfessionistiByType(profType) {
    const response = await api.get(`/api/professionisti/${profType}`);
    return response.data;
  },



  // ==================== UTILITIES ====================

  /**
   * Copy check link to clipboard
   * @param {string} url - URL to copy
   * @returns {Promise<boolean>} - Success status
   */
  async copyLinkToClipboard(url) {
    try {
      await navigator.clipboard.writeText(url);
      return true;
    } catch (err) {
      console.error('Failed to copy link:', err);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = url;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      return true;
    }
  },

  /**
   * Get badge color based on rating value
   * @param {number} rating - Rating value (1-10)
   * @returns {string} - CSS color
   */
  getRatingColor(rating) {
    if (!rating) return '#9ca3af';
    if (rating >= 8) return '#22c55e';
    if (rating >= 6) return '#f59e0b';
    if (rating >= 4) return '#f97316';
    return '#ef4444';
  },

  /**
   * Format rating as badge style
   * @param {number} rating - Rating value
   * @returns {object} - Style object for badge
   */
  getRatingBadgeStyle(rating) {
    const color = this.getRatingColor(rating);
    return {
      background: `${color}15`,
      color: color,
      padding: '4px 10px',
      borderRadius: '12px',
      fontWeight: 600,
      fontSize: '0.85rem'
    };
  }
};

export default checkService;

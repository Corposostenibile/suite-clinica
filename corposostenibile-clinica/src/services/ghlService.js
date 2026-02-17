/**
 * GHL Service - API per l'integrazione Go High Level
 *
 * Gestisce configurazione, mapping calendari e eventi.
 * NOTA: Le route GHL sono sotto /ghl/api/... (non sotto /api/)
 */

import axios from 'axios';

// Helper to get CSRF token
const getCsrfToken = () => {
  let token = document.querySelector('meta[name="csrf-token"]')?.content;
  if (!token) {
    const value = `; ${document.cookie}`;
    const parts = value.split('; csrf_token=');
    if (parts.length === 2) token = parts.pop().split(';').shift();
  }
  return token;
};

// Create separate axios instance for GHL routes (they're not under /api/)
const ghlApi = axios.create({
  baseURL: '/ghl/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Add CSRF token to requests
ghlApi.interceptors.request.use((config) => {
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

// Handle 401 responses
ghlApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = `${import.meta.env.BASE_URL}auth/login`;
    }
    return Promise.reject(error);
  }
);

const ghlService = {
  // =========================================================================
  // CONFIGURATION
  // =========================================================================

  /**
   * Get GHL configuration (admin only)
   */
  async getConfig() {
    const response = await ghlApi.get('/config');
    return response.data;
  },

  /**
   * Update GHL configuration (admin only)
   * @param {Object} config - { api_key, location_id, is_active }
   */
  async updateConfig(config) {
    const response = await ghlApi.post('/config', config);
    return response.data;
  },

  /**
   * Test GHL connection (admin only)
   */
  async testConnection() {
    const response = await ghlApi.post('/config/test');
    return response.data;
  },

  // =========================================================================
  // CALENDARS & USERS
  // =========================================================================

  /**
   * Get all GHL calendars
   */
  async getCalendars() {
    const response = await ghlApi.get('/calendars');
    return response.data;
  },

  /**
   * Get all GHL users
   */
  async getGHLUsers() {
    const response = await ghlApi.get('/users');
    return response.data;
  },

  // =========================================================================
  // MAPPING
  // =========================================================================

  /**
   * Get user-calendar mapping
   */
  async getMapping() {
    const response = await ghlApi.get('/mapping');
    return response.data;
  },

  /**
   * Update single user mapping
   * @param {number} userId - Suite Clinica user ID
   * @param {string} ghlCalendarId - GHL calendar ID
   * @param {string} ghlUserId - GHL user ID
   */
  async updateMapping(userId, ghlCalendarId, ghlUserId = null) {
    const response = await ghlApi.post('/mapping', {
      user_id: userId,
      ghl_calendar_id: ghlCalendarId,
      ghl_user_id: ghlUserId
    });
    return response.data;
  },

  /**
   * Update multiple user mappings at once
   * @param {Array} mappings - [{ user_id, ghl_calendar_id, ghl_user_id }, ...]
   */
  async updateMappingBulk(mappings) {
    const response = await ghlApi.post('/mapping/bulk', { mappings });
    return response.data;
  },

  // =========================================================================
  // CALENDAR EVENTS
  // =========================================================================

  /**
   * Get calendar events for current user
   * @param {string} start - Start date (YYYY-MM-DD)
   * @param {string} end - End date (YYYY-MM-DD)
   */
  async getEvents(start, end) {
    const response = await ghlApi.get('/calendar/events', {
      params: { start, end }
    });
    return response.data;
  },

  /**
   * Get free slots for current user's calendar
   * @param {string} start - Start date
   * @param {string} end - End date
   */
  async getFreeSlots(start, end) {
    const response = await ghlApi.get('/calendar/free-slots', {
      params: { start, end }
    });
    return response.data;
  },

  /**
   * Get GHL connection status for current user
   */
  async getConnectionStatus() {
    const response = await ghlApi.get('/calendar/connection-status');
    return response.data;
  },

  // =========================================================================
  // WEBHOOK URLS (dinamici per sviluppatore)
  // =========================================================================

  /**
   * Ottiene gli URL webhook per questo backend (porta corretta per ogni dev)
   */
  async getWebhookUrls() {
    const response = await ghlApi.get('/webhook-urls');
    return response.data;
  },

  // =========================================================================
  // OPPORTUNITY DATA (Webhook)
  // =========================================================================

  /**
   * Get all opportunity data received from webhooks
   */
  async getOpportunityData() {
    // Usa endpoint debug temporaneamente (non richiede login)
    const response = await ghlApi.get('/opportunity-data-debug');
    return response.data;
  },

  /**
   * Get single opportunity data by ID
   */
  async getOpportunityDataById(id) {
    const response = await ghlApi.get(`/opportunity-data/${id}`);
    return response.data;
  },

  /**
   * Clear all opportunity data (admin only)
   */
  async clearOpportunityData() {
    const response = await ghlApi.post('/opportunity-data/clear');
    return response.data;
  }
};

export default ghlService;

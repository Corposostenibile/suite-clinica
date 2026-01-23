/**
 * Calendar Service - API per la gestione del calendario e meeting
 *
 * Integrazione con Google Calendar tramite backend Flask
 */

import axios from 'axios';

const api = axios.create({
  baseURL: '/calendar',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Event categories configuration
export const EVENT_CATEGORIES = {
  call_iniziale: {
    key: 'call_iniziale',
    label: 'Call Iniziale',
    color: '#22c55e',
    bgColor: '#dcfce7',
    icon: 'ri-user-add-line',
    duration: 60
  },
  call_periodica: {
    key: 'call_periodica',
    label: 'Call Periodica',
    color: '#3b82f6',
    bgColor: '#dbeafe',
    icon: 'ri-refresh-line',
    duration: 30
  },
  call_1_sales: {
    key: 'call_1_sales',
    label: 'Call 1 Sales',
    color: '#dc3545',
    bgColor: '#fee2e2',
    icon: 'ri-money-dollar-circle-line',
    duration: 45
  },
  call_2_sales: {
    key: 'call_2_sales',
    label: 'Call 2 Sales',
    color: '#fd7e14',
    bgColor: '#fed7aa',
    icon: 'ri-money-dollar-circle-line',
    duration: 30
  },
  call_interna: {
    key: 'call_interna',
    label: 'Call Interna',
    color: '#8b5cf6',
    bgColor: '#ede9fe',
    icon: 'ri-team-line',
    duration: 45
  },
  call_customer_care: {
    key: 'call_customer_care',
    label: 'Call Customer Care',
    color: '#ec4899',
    bgColor: '#fce7f3',
    icon: 'ri-customer-service-2-line',
    duration: 30
  },
  call_onboarding: {
    key: 'call_onboarding',
    label: 'Call Onboarding',
    color: '#14b8a6',
    bgColor: '#ccfbf1',
    icon: 'ri-rocket-line',
    duration: 60
  },
  call_followup: {
    key: 'call_followup',
    label: 'Call Follow-up',
    color: '#f59e0b',
    bgColor: '#fef3c7',
    icon: 'ri-phone-line',
    duration: 15
  }
};

// Meeting statuses
export const MEETING_STATUSES = {
  scheduled: { label: 'Programmato', color: '#3b82f6', bgColor: '#dbeafe' },
  completed: { label: 'Completato', color: '#22c55e', bgColor: '#dcfce7' },
  cancelled: { label: 'Cancellato', color: '#6b7280', bgColor: '#f3f4f6' },
  no_show: { label: 'No Show', color: '#ef4444', bgColor: '#fee2e2' },
};

const calendarService = {
  // ==================== CONNECTION STATUS ====================

  /**
   * Check if user is connected to Google Calendar
   * @returns {Promise} - { is_connected, connect_url, expires_at, ... }
   */
  async getConnectionStatus() {
    const response = await api.get('/api/connection-status');
    return response.data;
  },

  /**
   * Disconnect from Google Calendar
   * @returns {Promise}
   */
  async disconnect() {
    const response = await api.get('/disconnect', {
      headers: { 'Accept': 'application/json' }
    });
    return response.data;
  },

  // ==================== EVENTS ====================

  /**
   * Get events from Google Calendar
   * @param {string} start - Start date (ISO string or YYYY-MM-DD)
   * @param {string} end - End date (ISO string or YYYY-MM-DD)
   * @returns {Promise} - Array of events formatted for calendar display
   */
  async getEvents(start, end) {
    const params = {};
    if (start) params.start = start;
    if (end) params.end = end;

    const response = await api.get('/api/events', { params });
    return response.data;
  },

  /**
   * Create a new event in Google Calendar
   * @param {Object} eventData - Event data
   * @returns {Promise} - Created event with meeting info
   */
  async createEvent(eventData) {
    const response = await api.post('/api/events', eventData);
    return response.data;
  },

  /**
   * Delete an event by Google event ID
   * @param {string} googleEventId - Google Calendar event ID
   * @returns {Promise}
   */
  async deleteEventByGoogleId(googleEventId) {
    const response = await api.delete(`/api/event/${googleEventId}`);
    return response.data;
  },

  // ==================== MEETINGS ====================

  /**
   * Get meeting details by ID
   * @param {number} meetingId - Meeting ID
   * @returns {Promise} - Meeting details
   */
  async getMeeting(meetingId) {
    const response = await api.get(`/api/meeting/${meetingId}`);
    return response.data;
  },

  /**
   * Update meeting details
   * @param {number} meetingId - Meeting ID
   * @param {Object} data - Fields to update
   * @returns {Promise}
   */
  async updateMeeting(meetingId, data) {
    const response = await api.put(`/api/meeting/${meetingId}`, data);
    return response.data;
  },

  /**
   * Delete a meeting
   * @param {number} meetingId - Meeting ID
   * @returns {Promise}
   */
  async deleteMeeting(meetingId) {
    const response = await api.delete(`/api/meeting/${meetingId}`);
    return response.data;
  },

  /**
   * Get meetings for a specific client
   * @param {number} clienteId - Client ID
   * @param {number} userId - Optional user ID filter (admin only)
   * @returns {Promise}
   */
  async getClienteMeetings(clienteId, userId = null) {
    let url = `/api/meetings/${clienteId}`;
    if (userId) url += `?user_id=${userId}`;
    const response = await api.get(url);
    return response.data;
  },

  /**
   * Sync a single event to the database
   * @param {Object} eventData - Event data including google_event_id
   * @returns {Promise}
   */
  async syncSingleEvent(eventData) {
    const response = await api.post('/api/sync-single-event', eventData);
    return response.data;
  },

  // ==================== TEAM & CUSTOMERS ====================

  /**
   * Get list of team users
   * @returns {Promise} - { users: [{id, full_name, email, department}] }
   */
  async getTeamUsers() {
    const response = await api.get('/api/team/users');
    return response.data;
  },

  /**
   * Search customers by name
   * @param {string} query - Search query (min 3 chars)
   * @param {number} limit - Max results (default 20)
   * @returns {Promise} - { customers: [{cliente_id, nome_cognome, ...}] }
   */
  async searchCustomers(query, limit = 20) {
    if (!query || query.length < 3) {
      return { customers: [] };
    }
    const response = await api.get('/api/customers/search', {
      params: { q: query, limit }
    });
    return response.data;
  },

  /**
   * Get all customers list
   * @returns {Promise} - { customers: [{cliente_id, nome_cognome, email}] }
   */
  async getCustomersList() {
    const response = await api.get('/api/customers/list');
    return response.data;
  },

  /**
   * Get minimal customer info by ID
   * @param {number} clienteId - Customer ID
   * @returns {Promise}
   */
  async getCustomerMinimal(clienteId) {
    const response = await api.get(`/api/customers/${clienteId}/minimal`);
    return response.data;
  },

  // ==================== SYNC ====================

  /**
   * Trigger full sync from Google Calendar
   * Note: This redirects, use with window.location for full page refresh
   * @returns {string} - Sync URL
   */
  getSyncUrl() {
    return '/calendar/sync';
  },

  // ==================== ADMIN (Token Management) ====================

  /**
   * Get status of all OAuth tokens (Admin only)
   * @returns {Promise}
   */
  async getTokensStatus() {
    const response = await api.get('/api/admin/tokens/status');
    return response.data;
  },

  /**
   * Force refresh all expiring tokens (Admin only)
   * @returns {Promise}
   */
  async forceRefreshTokens() {
    const response = await api.post('/api/admin/tokens/refresh');
    return response.data;
  },

  /**
   * Cleanup expired tokens (Admin only)
   * @returns {Promise}
   */
  async cleanupTokens() {
    const response = await api.post('/api/admin/tokens/cleanup');
    return response.data;
  },

  /**
   * Refresh specific user's token (Admin only)
   * @param {number} userId - User ID
   * @returns {Promise}
   */
  async refreshUserToken(userId) {
    const response = await api.post(`/api/admin/tokens/${userId}/refresh`);
    return response.data;
  },

  // ==================== UTILITIES ====================

  /**
   * Get category config by key
   * @param {string} categoryKey - Category key
   * @returns {Object} - Category config or default
   */
  getCategoryConfig(categoryKey) {
    return EVENT_CATEGORIES[categoryKey] || {
      key: categoryKey || 'default',
      label: categoryKey || 'Evento',
      color: '#6b7280',
      bgColor: '#f3f4f6',
      icon: 'ri-calendar-event-line',
      duration: 30
    };
  },

  /**
   * Get status config by key
   * @param {string} statusKey - Status key
   * @returns {Object} - Status config or default
   */
  getStatusConfig(statusKey) {
    return MEETING_STATUSES[statusKey] || MEETING_STATUSES.scheduled;
  },

  /**
   * Format event for display
   * @param {Object} event - Raw event from API
   * @returns {Object} - Formatted event
   */
  formatEvent(event) {
    const categoryConfig = this.getCategoryConfig(event.extendedProps?.event_category);
    const statusConfig = this.getStatusConfig(event.extendedProps?.status);

    return {
      id: event.id,
      title: event.title,
      start: event.start,
      end: event.end,
      allDay: event.allDay || false,
      color: event.color || categoryConfig.color,
      ...event.extendedProps,
      categoryConfig,
      statusConfig,
    };
  },

  /**
   * Parse ISO date to local date object
   * @param {string} isoString - ISO date string
   * @returns {Date}
   */
  parseDate(isoString) {
    if (!isoString) return null;
    return new Date(isoString);
  },

  /**
   * Format date for display
   * @param {Date|string} date - Date to format
   * @param {Object} options - Intl.DateTimeFormat options
   * @returns {string}
   */
  formatDate(date, options = {}) {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (!d || isNaN(d.getTime())) return '';

    const defaultOptions = {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      ...options
    };

    return d.toLocaleDateString('it-IT', defaultOptions);
  },

  /**
   * Format time for display
   * @param {Date|string} date - Date to format
   * @returns {string} - Time in HH:MM format
   */
  formatTime(date) {
    const d = typeof date === 'string' ? new Date(date) : date;
    if (!d || isNaN(d.getTime())) return '';

    return d.toLocaleTimeString('it-IT', {
      hour: '2-digit',
      minute: '2-digit'
    });
  },

  /**
   * Get Google Calendar connection URL
   * @returns {string}
   */
  getConnectUrl() {
    return '/google/authorize';
  },

  /**
   * Get dashboard URL (old frontend)
   * @returns {string}
   */
  getDashboardUrl() {
    return '/calendar/dashboard';
  }
};

export default calendarService;

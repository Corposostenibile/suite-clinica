/**
 * Trial User Service
 *
 * Servizio per la gestione degli utenti in prova (professionisti in trial).
 * Gestisce le operazioni CRUD e l'assegnazione clienti.
 */

import axios from 'axios';

const api = axios.create({
  baseURL: '/api/team',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Response interceptor for auth errors
api.interceptors.response.use(
  (response) => {
    const contentType = response?.headers?.['content-type'] || '';
    if (typeof response?.data === 'string' && contentType.includes('text/html')) {
      return Promise.reject(new Error('Endpoint /api/team non raggiungibile: risposta HTML ricevuta (proxy non configurato).'));
    }
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = `${import.meta.env.BASE_URL}auth/login`;
    }
    return Promise.reject(error);
  }
);

// Trial stages configuration
export const TRIAL_STAGES = {
  1: {
    value: 1,
    label: 'Stage 1',
    description: 'Dashboard + Training',
    color: '#f59e0b',
    bgColor: '#fef3c7',
    icon: 'ri-book-read-line',
    features: ['Dashboard', 'Formazione', 'Training']
  },
  2: {
    value: 2,
    label: 'Stage 2',
    description: 'Clienti Selezionati',
    color: '#3b82f6',
    bgColor: '#dbeafe',
    icon: 'ri-user-follow-line',
    features: ['Dashboard', 'Formazione', 'Clienti Assegnati']
  },
  3: {
    value: 3,
    label: 'Stage 3',
    description: 'User Ufficiale',
    color: '#22c55e',
    bgColor: '#dcfce7',
    icon: 'ri-verified-badge-line',
    features: ['Accesso Completo']
  }
};

const trialUserService = {
  // ==================== CRUD OPERATIONS ====================

  /**
   * Get all trial users
   * @returns {Promise<Object>} - { success, trial_users: [], stats: {} }
   */
  async getAll() {
    const response = await api.get('/trial-users');
    return response.data;
  },

  /**
   * Get single trial user with assigned clients
   * @param {number} userId - User ID
   * @returns {Promise<Object>} - { success, trial_user: {...} }
   */
  async get(userId) {
    const response = await api.get(`/trial-users/${userId}`);
    return response.data;
  },

  /**
   * Create new trial user
   * @param {Object} data - { email, first_name, last_name, password, ... }
   * @returns {Promise<Object>} - { success, trial_user }
   */
  async create(data) {
    const response = await api.post('/trial-users', data);
    return response.data;
  },

  /**
   * Update trial user
   * @param {number} userId - User ID
   * @param {Object} data - Fields to update
   * @returns {Promise<Object>} - { success, trial_user }
   */
  async update(userId, data) {
    const response = await api.put(`/trial-users/${userId}`, data);
    return response.data;
  },

  /**
   * Delete trial user
   * @param {number} userId - User ID
   * @returns {Promise<Object>} - { success, message }
   */
  async delete(userId) {
    const response = await api.delete(`/trial-users/${userId}`);
    return response.data;
  },

  // ==================== PROMOTION ====================

  /**
   * Promote trial user to next stage
   * @param {number} userId - User ID
   * @returns {Promise<Object>} - { success, message, trial_user }
   */
  async promote(userId) {
    const response = await api.post(`/trial-users/${userId}/promote`);
    return response.data;
  },

  // ==================== CLIENT ASSIGNMENT ====================

  /**
   * Assign clients to trial user
   * @param {number} userId - User ID
   * @param {number[]} clienteIds - Array of cliente IDs
   * @param {string} notes - Optional notes
   * @returns {Promise<Object>} - { success, message, assigned_count }
   */
  async assignClients(userId, clienteIds, notes = '') {
    const response = await api.post(`/trial-users/${userId}/assign-clients`, {
      cliente_ids: clienteIds,
      notes
    });
    return response.data;
  },

  /**
   * Remove client from trial user
   * @param {number} userId - User ID
   * @param {number} clienteId - Cliente ID
   * @returns {Promise<Object>} - { success, message }
   */
  async removeClient(userId, clienteId) {
    const response = await api.delete(`/trial-users/${userId}/remove-client/${clienteId}`);
    return response.data;
  },

  /**
   * Get available clients for assignment
   * @param {number} userId - Exclude clients already assigned to this user
   * @param {string} search - Search query
   * @param {number} page - Page number
   * @param {number} perPage - Items per page
   * @returns {Promise<Object>} - { success, clients: [], pagination: {} }
   */
  async getAvailableClients(userId, search = '', page = 1, perPage = 50) {
    let url = `/trial-users/available-clients?page=${page}&per_page=${perPage}`;
    if (userId) url += `&user_id=${userId}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    const response = await api.get(url);
    return response.data;
  },

  // ==================== HELPERS ====================

  /**
   * Get list of potential supervisors
   * @returns {Promise<Object>} - { success, supervisors: [] }
   */
  async getSupervisors(specialty) {
    const params = specialty ? { specialty } : {};
    const response = await api.get('/trial-users/supervisors', { params });
    return response.data;
  },

  /**
   * Get stage configuration
   * @param {number} stage - Stage number (1, 2, or 3)
   * @returns {Object} - Stage config
   */
  getStageConfig(stage) {
    return TRIAL_STAGES[stage] || TRIAL_STAGES[1];
  },

  /**
   * Get stage badge style
   * @param {number} stage - Stage number
   * @returns {Object} - CSS style object
   */
  getStageBadgeStyle(stage) {
    const config = this.getStageConfig(stage);
    return {
      background: config.bgColor,
      color: config.color,
      padding: '4px 12px',
      borderRadius: '12px',
      fontWeight: 600,
      fontSize: '12px',
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px'
    };
  },

  /**
   * Calculate days since trial started
   * @param {string} startedAt - ISO date string
   * @returns {number} - Days count
   */
  getDaysSinceStart(startedAt) {
    if (!startedAt) return 0;
    const start = new Date(startedAt);
    const now = new Date();
    return Math.floor((now - start) / (1000 * 60 * 60 * 24));
  },

  /**
   * Format date for display
   * @param {string} dateStr - ISO date string
   * @returns {string} - Formatted date
   */
  formatDate(dateStr) {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  },

  /**
   * Format datetime for display
   * @param {string} dateStr - ISO datetime string
   * @returns {string} - Formatted datetime
   */
  formatDateTime(dateStr) {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
};

export default trialUserService;

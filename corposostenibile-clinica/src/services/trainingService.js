/**
 * Training Service
 *
 * Servizio per la gestione dei training/formazione.
 * Comunica con il backend per ottenere training, richieste e gestire le conferme.
 *
 * Nota: Usa axios direttamente invece di 'api' perché il blueprint review
 * non segue il pattern /api/... ma usa /review/api/...
 */

import axios from 'axios';

// Helper to get cookie by name
const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
};

// Create axios instance for review API
const reviewApi = axios.create({
  baseURL: '/review/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor to add CSRF token
reviewApi.interceptors.request.use((config) => {
  let csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

  if (!csrfToken) {
    csrfToken = getCookie('csrf_token') || getCookie('csrftoken') || getCookie('XSRF-TOKEN');
  }

  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
    config.headers['X-CSRF-Token'] = csrfToken;
  }

  return config;
});

// Response interceptor for error handling
reviewApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = '/auth/login';
    }
    return Promise.reject(error);
  }
);

const trainingService = {
  /**
   * Ottiene i training ricevuti dall'utente corrente
   * @returns {Promise<Object>} - { trainings, stats }
   */
  getMyTrainings: async () => {
    const response = await reviewApi.get('/my-trainings');
    return response.data;
  },

  /**
   * Ottiene le richieste di training inviate dall'utente
   * @returns {Promise<Object>} - { requests, stats }
   */
  getMyRequests: async () => {
    const response = await reviewApi.get('/my-requests');
    return response.data;
  },

  /**
   * Ottiene le richieste di training ricevute (dove altri chiedono training a me)
   * @returns {Promise<Object>} - { requests, stats }
   */
  getReceivedRequests: async () => {
    const response = await reviewApi.get('/received-requests');
    return response.data;
  },

  /**
   * Ottiene i training erogati dall'utente (dove sono il reviewer/formatore)
   * @returns {Promise<Object>} - { trainings, stats }
   */
  getGivenTrainings: async () => {
    const response = await reviewApi.get('/given-trainings');
    return response.data;
  },

  /**
   * Ottiene i possibili destinatari per una richiesta di training
   * @returns {Promise<Object>} - { recipients: [{ id, name, role, department }] }
   */
  getRequestRecipients: async () => {
    const response = await reviewApi.get('/request-recipients');
    return response.data;
  },

  /**
   * Crea una nuova richiesta di training
   * @param {Object} data - { subject, description, priority, recipient_id }
   * @returns {Promise<Object>} - { success, request_id, message }
   */
  createRequest: async (data) => {
    const response = await reviewApi.post('/request', data);
    return response.data;
  },

  /**
   * Cancella una richiesta di training pending
   * @param {number} requestId - ID della richiesta
   * @returns {Promise<Object>} - { success, message }
   */
  cancelRequest: async (requestId) => {
    const response = await reviewApi.post(`/request/${requestId}/cancel`);
    return response.data;
  },

  /**
   * Conferma la lettura di un training
   * @param {number} reviewId - ID del training
   * @param {string} notes - Note opzionali
   * @returns {Promise<Object>} - { success, message }
   */
  acknowledgeTraining: async (reviewId, notes = '') => {
    const response = await reviewApi.post(`/${reviewId}/acknowledge`, { notes });
    return response.data;
  },

  /**
   * Invia un messaggio nella chat di un training
   * @param {number} reviewId - ID del training
   * @param {string} content - Contenuto del messaggio
   * @returns {Promise<Object>} - { success, message: { id, content, sender_id, sender_name, created_at, is_own } }
   */
  sendMessage: async (reviewId, content) => {
    const response = await reviewApi.post(`/${reviewId}/message`, { content });
    return response.data;
  },

  /**
   * Marca tutti i messaggi di un training come letti
   * @param {number} reviewId - ID del training
   * @returns {Promise<Object>} - { success, count }
   */
  markAllMessagesRead: async (reviewId) => {
    const response = await reviewApi.post(`/${reviewId}/mark-all-read`);
    return response.data;
  },

  // ===================== ADMIN METHODS =====================

  /**
   * [ADMIN] Ottiene lista di tutti i professionisti attivi
   * @returns {Promise<Object>} - { professionals: [...] }
   */
  getAdminProfessionals: async () => {
    const response = await reviewApi.get('/admin/professionals');
    return response.data;
  },

  /**
   * [ADMIN] Ottiene i training di un utente specifico
   * @param {number} userId - ID dell'utente
   * @returns {Promise<Object>} - { user, trainings, stats }
   */
  getAdminUserTrainings: async (userId) => {
    const response = await reviewApi.get(`/admin/trainings/${userId}`);
    return response.data;
  },

  /**
   * [ADMIN] Crea un nuovo training per un utente specifico
   * @param {number} userId - ID dell'utente destinatario
   * @param {Object} data - { title, content, review_type, strengths, improvements, goals, period_start, period_end, is_private }
   * @returns {Promise<Object>} - { success, message, training }
   */
  createTrainingForUser: async (userId, data) => {
    const response = await reviewApi.post(`/admin/trainings/${userId}`, data);
    return response.data;
  },

  /**
   * [ADMIN] Ottiene statistiche globali training per la dashboard
   * @returns {Promise<Object>} - { kpi, byType, monthlyTrend, topReviewers, topReviewees, recentTrainings }
   */
  getDashboardStats: async () => {
    const response = await reviewApi.get('/admin/dashboard-stats');
    return response.data;
  },
};

export default trainingService;

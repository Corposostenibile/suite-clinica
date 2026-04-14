/**
 * Old Suite Service - API per integrazione temporanea con vecchia suite CRM
 *
 * Gestisce lead ricevute via webhook da suite.corposostenibile.com
 * NOTA: Le route sono sotto /old-suite/api/... (non sotto /api/)
 */

import axios from 'axios';

const getCsrfToken = () => {
  let token = document.querySelector('meta[name="csrf-token"]')?.content;
  if (!token) {
    const value = `; ${document.cookie}`;
    const parts = value.split('; csrf_token=');
    if (parts.length === 2) token = parts.pop().split(';').shift();
  }
  return token;
};

const oldSuiteApi = axios.create({
  baseURL: '/old-suite/api',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

oldSuiteApi.interceptors.request.use((config) => {
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

oldSuiteApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = `${import.meta.env.BASE_URL}auth/login`;
    }
    return Promise.reject(error);
  }
);

const oldSuiteService = {
  /**
   * Get all leads from old suite webhooks
   */
  async getLeads() {
    const response = await oldSuiteApi.get('/leads');
    return response.data;
  },

  /**
   * Get single lead by ID
   */
  async getLeadById(id) {
    const response = await oldSuiteApi.get(`/leads/${id}`);
    return response.data;
  },

  /**
   * Get check response detail for a lead
   */
  async getCheckDetail(leadId, checkNumber) {
    const response = await oldSuiteApi.get(`/leads/${leadId}/check/${checkNumber}`);
    return response.data;
  },

  /**
   * Confirm assignment for a lead (converts to Cliente)
   */
  async confirmAssignment(payload) {
    const response = await oldSuiteApi.post('/confirm-assignment', payload);
    return response.data;
  },

  /**
   * Crea una lead manualmente (Team Leader HM o Admin)
   * @param {{ first_name, last_name, email, phone?, roles?, duration_days?, client_story? }} data
   */
  async createLead(data) {
    const response = await oldSuiteApi.post('/leads/create', data);
    return response.data;
  },
};

export default oldSuiteService;

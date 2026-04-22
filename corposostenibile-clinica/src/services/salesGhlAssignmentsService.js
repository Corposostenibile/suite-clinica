import axios from 'axios';

/**
 * Service per il launcher Sales GHL / queue assegnazioni.
 *
 * Backend:
 * - POST /api/ghl-assignments/sso/exchange
 * - GET /api/ghl-assignments
 *
 * Il token viene salvato in sessionStorage per mantenere la sessione del tab.
 */

const API_BASE = '/api/ghl-assignments';
const TOKEN_KEY = 'sales_ghl_assignments_token';
const USER_KEY = 'sales_ghl_assignments_user';

const salesApi = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

function getCachedUser() {
  const raw = sessionStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function setCachedUser(user) {
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

function authHeaders() {
  const token = getToken();
  if (!token) {
    throw new Error('Sessione sales mancante');
  }
  return { Authorization: `Bearer ${token}` };
}

const salesGhlAssignmentsService = {
  getToken,
  getCachedUser,
  clearSession,

  async exchangeSession(params) {
    const response = await salesApi.post('/sso/exchange', params);
    const { token, sales_user } = response.data || {};
    if (token) setToken(token);
    if (sales_user) setCachedUser(sales_user);
    return response.data;
  },

  async verifySession() {
    try {
      const response = await salesApi.get('', {
        headers: authHeaders(),
        params: { limit: 1, status: 'all' },
      });
      return response.data;
    } catch (error) {
      if (error?.response?.status === 401) {
        clearSession();
        return null;
      }
      throw error;
    }
  },

  async getAssignments(params = {}) {
    const response = await salesApi.get('', {
      headers: authHeaders(),
      params,
    });
    return response.data;
  },
};

export default salesGhlAssignmentsService;

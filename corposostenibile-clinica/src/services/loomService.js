/**
 * Loom Service
 *
 * Servizio per la gestione dei link Loom associati agli eventi GHL.
 * Comunica con il backend per salvare/recuperare i link delle registrazioni.
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

// Create axios instance for GHL/Loom routes
const loomApi = axios.create({
  baseURL: '/ghl/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Add CSRF token to requests
loomApi.interceptors.request.use((config) => {
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

// Handle 401 responses
loomApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = `${import.meta.env.BASE_URL}auth/login`;
    }
    return Promise.reject(error);
  }
);

const loomService = {
  /**
   * Salva una registrazione Loom creata dal widget di supporto.
   *
   * @param {Object} payload
   * @param {string} payload.loomLink - URL share Loom
   * @param {string} [payload.title] - Titolo opzionale
   * @param {string} [payload.note] - Nota opzionale
   * @param {number|null} [payload.clienteId] - Paziente opzionale
   * @returns {Promise<Object>}
   */
  saveSupportRecording: async (payload) => {
    const csrfToken = getCsrfToken() || '';
    const response = await axios.post(
      '/loom/api/recordings',
      {
        loom_link: payload.loomLink,
        title: payload.title,
        note: payload.note,
        cliente_id: payload.clienteId ?? null,
      },
      {
        withCredentials: true,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
          'X-CSRF-Token': csrfToken,
        },
      }
    );
    return response.data;
  },

  /**
   * Ricerca pazienti per associazione registrazione Loom.
   *
   * @param {string} query
   * @param {number} [limit=20]
   * @returns {Promise<Array<{cliente_id:number,nome_cognome:string}>>}
   */
  searchPatients: async (query, limit = 20) => {
    const response = await axios.get('/loom/api/patients/search', {
      params: {
        q: query || '',
        limit,
      },
      withCredentials: true,
    });
    return response?.data?.items || [];
  },

  /**
   * Salva link Loom per un evento GHL
   * Crea o aggiorna il record Meeting locale associato
   *
   * @param {Object} eventData - Dati dell'evento
   * @param {string} eventData.ghlEventId - ID dell'evento GHL
   * @param {string} eventData.loomLink - URL del video Loom
   * @param {string} [eventData.title] - Titolo dell'evento
   * @param {string} [eventData.startTime] - Data/ora inizio (ISO string)
   * @param {string} [eventData.endTime] - Data/ora fine (ISO string)
   * @param {number} [eventData.clienteId] - ID del cliente associato
   * @param {string} [eventData.ghlCalendarId] - ID del calendario GHL
   * @returns {Promise<Object>} - Risposta del server con meeting_id
   */
  saveLoomLink: async (eventData) => {
    const response = await loomApi.post('/meeting/loom', {
      ghl_event_id: eventData.ghlEventId,
      loom_link: eventData.loomLink,
      title: eventData.title,
      start_time: eventData.startTime,
      end_time: eventData.endTime,
      cliente_id: eventData.clienteId,
      ghl_calendar_id: eventData.ghlCalendarId,
    });
    return response.data;
  },

  /**
   * Ottiene il link Loom per un evento GHL
   *
   * @param {string} ghlEventId - ID dell'evento GHL
   * @returns {Promise<Object>} - { success, meeting_id, loom_link, has_loom }
   */
  getLoomLink: async (ghlEventId) => {
    const response = await loomApi.get(`/meeting/loom/${ghlEventId}`);
    return response.data;
  },
};

export default loomService;

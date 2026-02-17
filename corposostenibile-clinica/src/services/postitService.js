/**
 * Post-it Service
 *
 * Servizio per la gestione dei post-it / promemoria personali.
 * Comunica con il backend Flask per le operazioni CRUD.
 */

import axios from 'axios';

// Helper to get cookie by name
const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
};

// Create axios instance for postit API
const postitApi = axios.create({
    baseURL: '/postit/api',
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,
});

const isHtmlLikePayload = (payload) => {
    if (typeof payload !== 'string') return false;
    const trimmed = payload.trim().toLowerCase();
    return trimmed.startsWith('<!doctype html') || trimmed.startsWith('<html');
};

const isHtmlContentType = (headers = {}) => {
    const contentType = headers['content-type'] || headers['Content-Type'] || '';
    return typeof contentType === 'string' && contentType.toLowerCase().includes('text/html');
};

const isWrongEntrypointResponse = (response) => (
    isHtmlContentType(response?.headers || {}) || isHtmlLikePayload(response?.data)
);

// Request interceptor to add CSRF token
postitApi.interceptors.request.use((config) => {
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
postitApi.interceptors.response.use(
    (response) => {
        if (isWrongEntrypointResponse(response)) {
            const err = new Error('POSTIT_WRONG_ENTRYPOINT');
            err.code = 'POSTIT_WRONG_ENTRYPOINT';
            err.response = response;
            throw err;
        }
        return response;
    },
    (error) => {
        if (isWrongEntrypointResponse(error?.response)) {
            error.code = 'POSTIT_WRONG_ENTRYPOINT';
        }
        if (error.response?.status === 401) {
            window.location.href = `${import.meta.env.BASE_URL}auth/login`;
        }
        return Promise.reject(error);
    }
);

const postitService = {
    /**
     * Ottiene tutti i post-it dell'utente corrente
     * @returns {Promise<Object>} - { success, postits: [...], count }
     */
    getAll: async () => {
        const response = await postitApi.get('/list', {
            headers: {
                'Cache-Control': 'no-cache',
                Pragma: 'no-cache',
            },
            params: {
                _t: Date.now(),
            },
        });
        return response.data;
    },

    /**
     * Crea un nuovo post-it
     * @param {Object} data - { content, color?, reminderAt? }
     * @returns {Promise<Object>} - { success, message, postit }
     */
    create: async (data) => {
        const response = await postitApi.post('/create', data);
        return response.data;
    },

    /**
     * Ottiene un singolo post-it
     * @param {number} id - ID del post-it
     * @returns {Promise<Object>} - { success, postit }
     */
    get: async (id) => {
        const response = await postitApi.get(`/${id}`);
        return response.data;
    },

    /**
     * Aggiorna un post-it
     * @param {number} id - ID del post-it
     * @param {Object} data - { content?, color?, reminderAt?, position? }
     * @returns {Promise<Object>} - { success, message, postit }
     */
    update: async (id, data) => {
        const response = await postitApi.put(`/${id}`, data);
        return response.data;
    },

    /**
     * Elimina un post-it
     * @param {number} id - ID del post-it
     * @returns {Promise<Object>} - { success, message }
     */
    delete: async (id) => {
        const response = await postitApi.delete(`/${id}`);
        return response.data;
    },

    /**
     * Riordina i post-it
     * @param {number[]} order - Array di ID nell'ordine desiderato
     * @returns {Promise<Object>} - { success, message }
     */
    reorder: async (order) => {
        const response = await postitApi.post('/reorder', { order });
        return response.data;
    },
};

export default postitService;

export const isPostitWrongEntrypointError = (error) => (
    error?.code === 'POSTIT_WRONG_ENTRYPOINT' ||
    isWrongEntrypointResponse(error?.response)
);

// Colori disponibili per i post-it
export const POSTIT_COLORS = {
    yellow: { bg: '#fff9c4', border: '#fdd835', label: 'Giallo' },
    green: { bg: '#c8e6c9', border: '#66bb6a', label: 'Verde' },
    blue: { bg: '#bbdefb', border: '#42a5f5', label: 'Blu' },
    pink: { bg: '#f8bbd9', border: '#ec407a', label: 'Rosa' },
    orange: { bg: '#ffe0b2', border: '#ffa726', label: 'Arancione' },
    purple: { bg: '#e1bee7', border: '#ab47bc', label: 'Viola' },
};

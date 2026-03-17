import api from './api';

const taskService = {
    /**
     * Recupera la lista dei task con filtri opzionali
     * @param {Object} params - { category, completed, priority, ... }
     */
    getAll: async (params = {}) => {
        const response = await api.get('/tasks/', { params });
        return response.data;
    },

    /**
     * Recupera le statistiche dei task
     */
    getStats: async () => {
        const response = await api.get('/tasks/stats');
        return response.data;
    },

    getFilterOptions: async () => {
        const response = await api.get('/tasks/filter-options');
        return response.data;
    },

    /**
     * Crea un nuovo task (manuale)
     * @param {Object} data 
     */
    create: async (data) => {
        const response = await api.post('/tasks/', data);
        return response.data;
    },

    /**
     * Aggiorna un task esistente
     * @param {number} id 
     * @param {Object} data 
     */
    update: async (id, data) => {
        const response = await api.put(`/tasks/${id}`, data);
        return response.data;
    },

    /**
     * Elimina un task
     * @param {number} id 
     */
    delete: async (id) => {
        const response = await api.delete(`/tasks/${id}`);
        return response.data;
    },

    /**
     * Segna un task come completato/da fare
     * @param {number} id 
     * @param {boolean} completed 
     */
    toggleComplete: async (id, completed) => {
        const response = await api.put(`/tasks/${id}`, { completed });
        return response.data;
    }
};

export const TASK_CATEGORIES = {
    onboarding: { label: 'Onboarding', icon: 'ri-user-add-line', color: '#17a2b8', bg: 'info' },
    check: { label: 'Check', icon: 'ri-file-list-3-line', color: '#28a745', bg: 'success' },
    reminder: { label: 'Reminder', icon: 'ri-alarm-warning-line', color: '#dc8c14', bg: 'warning' },
    formazione: { label: 'Formazione', icon: 'ri-book-open-line', color: '#6f42c1', bg: 'primary' },
    sollecito: { label: 'Solleciti', icon: 'ri-time-line', color: '#dc3545', bg: 'danger' },
    generico: { label: 'Generico', icon: 'ri-task-line', color: '#6c757d', bg: 'secondary' }
};

export const TASK_PRIORITIES = {
    low: { label: 'Bassa', color: '#28a745' },
    medium: { label: 'Media', color: '#ffc107' },
    high: { label: 'Alta', color: '#dc3545' },
    urgent: { label: 'Urgente', color: '#dc3545' } 
};

export default taskService;

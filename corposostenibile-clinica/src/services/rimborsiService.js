import api from './api';
import axios from 'axios';

const API_BASE = '/rimborsi';

const rimborsiService = {
  async list(params = {}) {
    const response = await api.get(`${API_BASE}/list`, { params });
    return response.data;
  },

  async get(id) {
    const response = await api.get(`${API_BASE}/${id}`);
    return response.data;
  },

  async create(data) {
    const response = await api.post(`${API_BASE}/create`, data);
    return response.data;
  },

  async delete(id) {
    const response = await api.delete(`${API_BASE}/${id}`);
    return response.data;
  },

  /**
   * Ricerca clienti - usa l'endpoint esistente /customers/api/search
   */
  async searchClienti(q) {
    const response = await axios.get('/customers/api/search', {
      params: { q },
      withCredentials: true,
    });
    return response.data;
  },
};

export default rimborsiService;

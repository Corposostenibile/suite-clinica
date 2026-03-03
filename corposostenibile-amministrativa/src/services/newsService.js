import api from './api';

const newsService = {
  async listAll(params = {}) {
    const response = await api.get('/news/list-all', { params });
    return response.data;
  },

  async getDetail(id) {
    const response = await api.get(`/news/${id}`);
    return response.data;
  },

  async create(data) {
    const response = await api.post('/news/create', data);
    return response.data;
  },

  async update(id, data) {
    const response = await api.put(`/news/${id}`, data);
    return response.data;
  },

  async remove(id) {
    const response = await api.delete(`/news/${id}`);
    return response.data;
  },
};

export default newsService;

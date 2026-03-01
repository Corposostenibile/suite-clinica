import api from './api';

const newsService = {
  async list(params = {}) {
    const response = await api.get('/news/list', { params });
    return response.data;
  },

  async getDetail(id) {
    const response = await api.get(`/news/${id}`);
    return response.data;
  },
};

export default newsService;

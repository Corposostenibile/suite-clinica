import api from './api';

const searchService = {
  globalSearch: async (query) => {
    const response = await api.get('/search/global', { params: { q: query } });
    return response.data;
  },
};

export default searchService;

import api from './api';

const searchService = {
  globalSearch: async (query, category = '', page = 1) => {
    const response = await api.get('/search/global', { 
      params: { 
        q: query,
        category: category !== 'all' ? category : '',
        page: page,
        per_page: 10
      } 
    });
    return response.data;
  },
};

export default searchService;

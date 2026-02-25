import api from './api';

const adminPushService = {
  listProfessionisti: async () => {
    const response = await api.get('/push/admin/professionisti');
    return response.data?.items || [];
  },

  sendPush: async ({ userId, title, body, url }) => {
    const response = await api.post('/push/admin/send', {
      user_id: userId,
      title,
      body,
      url,
    });
    return response.data;
  },
};

export default adminPushService;

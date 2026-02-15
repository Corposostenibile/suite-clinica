import api from './api';

const teamTicketsService = {
  async listByPatient(clienteId, params = {}) {
    const response = await api.get('/team-tickets/', {
      params: { cliente_id: clienteId, ...params },
    });
    return response.data;
  },

  async getTicket(id) {
    const response = await api.get(`/team-tickets/${id}`);
    return response.data;
  },

  async getMessages(ticketId) {
    const response = await api.get(`/team-tickets/${ticketId}/messages`);
    return response.data;
  },

  getAttachmentUrl(attId) {
    return `/api/team-tickets/attachments/${attId}`;
  },
};

export default teamTicketsService;

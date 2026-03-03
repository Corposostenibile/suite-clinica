import api from './api';

const teamTicketsService = {
  // ─── Tickets (read-only) ───
  async listTickets(params = {}) {
    const response = await api.get('/team-tickets/', { params });
    return response.data;
  },

  async getTicket(id) {
    const response = await api.get(`/team-tickets/${id}`);
    return response.data;
  },

  // ─── Messages (read-only) ───
  async getMessages(ticketId) {
    const response = await api.get(`/team-tickets/${ticketId}/messages`);
    return response.data;
  },

  // ─── Attachments (download only) ───
  getAttachmentUrl(attId) {
    return `/api/team-tickets/attachments/${attId}`;
  },

  // ─── Stats & Support ───
  async getStats() {
    const response = await api.get('/team-tickets/stats');
    return response.data;
  },

  async getAnalytics(days = 30) {
    const response = await api.get('/team-tickets/analytics', { params: { days } });
    return response.data;
  },

  async getAssignableUsers() {
    const response = await api.get('/team-tickets/users');
    return response.data;
  },

  async searchPatients(q) {
    const response = await api.get('/team-tickets/patients/search', { params: { q } });
    return response.data;
  },
};

export default teamTicketsService;

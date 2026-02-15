import api from './api';

const teamTicketsService = {
  // ─── Tickets ───
  async listTickets(params = {}) {
    const response = await api.get('/team-tickets/', { params });
    return response.data;
  },

  async getTicket(id) {
    const response = await api.get(`/team-tickets/${id}`);
    return response.data;
  },

  async createTicket(formData) {
    const response = await api.post('/team-tickets/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async updateTicket(id, data) {
    const response = await api.patch(`/team-tickets/${id}`, data);
    return response.data;
  },

  async deleteTicket(id) {
    const response = await api.delete(`/team-tickets/${id}`);
    return response.data;
  },

  // ─── Messages ───
  async getMessages(ticketId) {
    const response = await api.get(`/team-tickets/${ticketId}/messages`);
    return response.data;
  },

  async sendMessage(ticketId, content) {
    const response = await api.post(`/team-tickets/${ticketId}/messages`, { content });
    return response.data;
  },

  // ─── Attachments ───
  async uploadAttachments(ticketId, files) {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const response = await api.post(`/team-tickets/${ticketId}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

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

import api from './api';

const sopService = {
  async getDocuments() {
    const response = await api.get('/sop/documents');
    return response.data;
  },

  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/sop/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async deleteDocument(docId) {
    const response = await api.delete(`/sop/documents/${docId}`);
    return response.data;
  },

  async chat(query, sessionId) {
    const response = await api.post('/sop/chat', { query, session_id: sessionId });
    return response.data;
  },

  async clearChat(sessionId) {
    const response = await api.post('/sop/chat/clear', { session_id: sessionId });
    return response.data;
  },

  async getStats() {
    const response = await api.get('/sop/stats');
    return response.data;
  },
};

export default sopService;

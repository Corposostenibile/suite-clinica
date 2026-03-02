import api, { setAuthToken } from './api'

export const kanbanService = {
  /** Exchange AAD token for JWT */
  async authenticate(aadToken) {
    const { data } = await api.post('/tab-auth', { aad_token: aadToken })
    return data // { token, user_id, name }
  },

  /** Dev-mode login (no Teams) */
  async devLogin(username, password) {
    const { data } = await api.post('/tab-auth/dev', { username, password })
    return data
  },

  /** List tickets (scope=mine) */
  async listTickets(token) {
    setAuthToken(token)
    const { data } = await api.get('/tab/tickets', {
      params: { per_page: 200 },
    })
    return data.tickets
  },

  /** Get ticket detail with messages and attachments */
  async getTicket(token, ticketId) {
    setAuthToken(token)
    const { data } = await api.get(`/tab/tickets/${ticketId}`)
    return data
  },

  /** Update ticket status (drag-and-drop) */
  async updateStatus(token, ticketId, status) {
    setAuthToken(token)
    const { data } = await api.patch(`/tab/tickets/${ticketId}/status`, { status })
    return data.ticket
  },

  /** Create ticket */
  async createTicket(token, payload) {
    setAuthToken(token)
    const { data } = await api.post('/tab/tickets', payload)
    return data.ticket
  },

  /** Update ticket (priority, assignees, description) */
  async updateTicket(token, ticketId, payload) {
    setAuthToken(token)
    const { data } = await api.patch(`/tab/tickets/${ticketId}`, payload)
    return data.ticket
  },

  /** Add message to ticket */
  async addMessage(token, ticketId, content) {
    setAuthToken(token)
    const { data } = await api.post(`/tab/tickets/${ticketId}/messages`, { content })
    return data.message
  },

  /** Upload attachment */
  async uploadAttachment(token, ticketId, file) {
    setAuthToken(token)
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post(`/tab/tickets/${ticketId}/attachments`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data.attachment
  },

  /** Search patients */
  async searchPatients(token, query) {
    setAuthToken(token)
    const { data } = await api.get('/tab/patients/search', { params: { q: query } })
    return data.patients
  },

  /** Search assignable users */
  async searchUsers(token, query) {
    setAuthToken(token)
    const { data } = await api.get('/tab/users', { params: { q: query } })
    return data.users
  },
}

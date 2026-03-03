import api from './api';

const videoCallService = {
  /** Create a new video call session (immediate or scheduled) */
  createCall: (clienteId, { scheduledAt, notes } = {}) =>
    api.post('/video-calls/create', {
      cliente_id: clienteId || null,
      scheduled_at: scheduledAt || null,
      notes: notes || null,
    }),

  /** End a video call session */
  endCall: (sessionId, notes) =>
    api.post(`/video-calls/${sessionId}/end`, { notes }),

  /** Get call history (optionally filtered by client) */
  getHistory: (clienteId) =>
    api.get('/video-calls/history', { params: clienteId ? { cliente_id: clienteId } : {} }),

  /** Get all video calls for a specific client (for Appuntamenti tab) */
  getClientCalls: (clienteId, cacheBust) =>
    api.get(`/video-calls/client/${clienteId}`, { params: { _t: cacheBust } }),

  /** Professional joins a scheduled/waiting call (gets token) */
  joinCall: (sessionId) =>
    api.post(`/video-calls/${sessionId}/join`),

  /** Get public session info (no auth) */
  getPublicInfo: (sessionToken) =>
    api.get(`/video-calls/public/info/${sessionToken}`),

  /** Join as client (public, no auth) */
  publicJoin: (sessionToken, name) =>
    api.post(`/video-calls/public/join/${sessionToken}`, { name }),

  /** Upload a call recording blob */
  uploadRecording: (sessionId, blob, onProgress) => {
    const formData = new FormData();
    formData.append('recording', blob, 'recording.webm');
    return api.post(`/video-calls/${sessionId}/upload-recording`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    });
  },

  /** Get replay data for a session */
  getReplayData: (sessionId) =>
    api.get(`/video-calls/${sessionId}/replay`),
};

export default videoCallService;

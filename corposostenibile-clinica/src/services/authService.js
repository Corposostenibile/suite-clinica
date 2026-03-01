import api from './api';

const authService = {
  /**
   * Login with email and password
   */
  async login(email, password, rememberMe = false) {
    const response = await api.post('/auth/login', {
      email,
      password,
      remember_me: rememberMe,
    });
    return response.data;
  },

  /**
   * Logout current user
   */
  async logout() {
    const response = await api.post('/auth/logout');
    return response.data;
  },

  /**
   * Request password reset email
   */
  async forgotPassword(email) {
    const response = await api.post('/auth/forgot-password', { email });
    return response.data;
  },

  /**
   * Reset password with token
   */
  async resetPassword(token, password, password2) {
    const response = await api.post(`/auth/reset-password/${token}`, {
      password,
      password2,
    });
    return response.data;
  },

  /**
   * Verify reset token is valid
   */
  async verifyResetToken(token) {
    const response = await api.get(`/auth/verify-reset-token/${token}`);
    return response.data;
  },

  /**
   * Get current user info
   */
  async getCurrentUser() {
    const response = await api.get('/auth/me');
    return response.data;
  },

  /**
   * Get list of users available for impersonation (admin only)
   */
  async getImpersonateUsers() {
    const response = await api.get('/auth/impersonate/users');
    return response.data;
  },

  /**
   * Start impersonation as another user (admin only)
   */
  async impersonateUser(userId) {
    const response = await api.post(`/auth/impersonate/${userId}`);
    return response.data;
  },

  /**
   * Stop impersonation and return to admin account
   */
  async stopImpersonation() {
    const response = await api.post('/auth/stop-impersonation');
    return response.data;
  },
};

export default authService;

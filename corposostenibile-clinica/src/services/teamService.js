import api from './api';

// User role types
export const USER_ROLES = {
  ADMIN: 'admin',
  TEAM_LEADER: 'team_leader',
  PROFESSIONISTA: 'professionista',
  TEAM_ESTERNO: 'team_esterno',
  INFLUENCER: 'influencer',
  HEALTH_MANAGER: 'health_manager',
};

// User specialties by role
export const USER_SPECIALTIES = {
  admin: [
    { value: 'amministrazione', label: 'Amministrazione' },
    { value: 'cco', label: 'CCO' },
  ],
  team_leader: [
    { value: 'nutrizione', label: 'Nutrizione' },
    { value: 'psicologia', label: 'Psicologia' },
    { value: 'coach', label: 'Coach' },
  ],
  professionista: [
    { value: 'nutrizionista', label: 'Nutrizione' },
    { value: 'psicologo', label: 'Psicologia' },
    { value: 'coach', label: 'Coach' },
  ],
  team_esterno: [],
  influencer: [],
  health_manager: [],
};

// Role labels for display
export const ROLE_LABELS = {
  admin: 'Admin',
  team_leader: 'Team Leader',
  professionista: 'Professionista',
  team_esterno: 'Team Esterno',
  influencer: 'Influencer',
  health_manager: 'Health Manager',
};

// Specialty labels for display (unificati per categoria)
export const SPECIALTY_LABELS = {
  amministrazione: 'Amministrazione',
  cco: 'CCO',
  nutrizione: 'Nutrizione',
  psicologia: 'Psicologia',
  coach: 'Coach',
  nutrizionista: 'Nutrizione',   // Unificato con nutrizione
  psicologo: 'Psicologia',       // Unificato con psicologia
};

// Opzioni filtro specializzazione (solo valori unici per i filtri)
export const SPECIALTY_FILTER_OPTIONS = [
  { value: 'nutrizione,nutrizionista', label: 'Nutrizione' },
  { value: 'psicologia,psicologo', label: 'Psicologia' },
  { value: 'coach', label: 'Coach' },
  { value: 'amministrazione', label: 'Amministrazione' },
  { value: 'cco', label: 'CCO' },
];

// Badge colors by role
export const ROLE_COLORS = {
  admin: 'danger',
  team_leader: 'primary',
  professionista: 'success',
  team_esterno: 'secondary',
  influencer: 'info',
  health_manager: 'primary',
};

// Badge colors by specialty
export const SPECIALTY_COLORS = {
  amministrazione: 'danger',
  cco: 'danger',
  nutrizione: 'info',
  psicologia: 'warning',
  coach: 'success',
  nutrizionista: 'info',
  psicologo: 'warning',
};

// ==================== TEAM ENTITY CONSTANTS ====================

// Team types
export const TEAM_TYPES = {
  NUTRIZIONE: 'nutrizione',
  COACH: 'coach',
  PSICOLOGIA: 'psicologia',
};

// Team type labels for display
export const TEAM_TYPE_LABELS = {
  nutrizione: 'Nutrizione',
  coach: 'Coach',
  psicologia: 'Psicologia',
};

// Team type colors (for badges and gradients)
export const TEAM_TYPE_COLORS = {
  nutrizione: 'info',
  coach: 'success',
  psicologia: 'warning',
};

// Team type gradients (for card headers)
export const TEAM_TYPE_GRADIENTS = {
  nutrizione: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  coach: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  psicologia: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
};

// Team type icons
export const TEAM_TYPE_ICONS = {
  nutrizione: 'ri-heart-pulse-line',
  coach: 'ri-run-line',
  psicologia: 'ri-mental-health-line',
};

const teamService = {
  /**
   * Get list of team members with filters and pagination
   */
  async getTeamMembers(params = {}) {
    const response = await api.get('/team/members', { params });
    return response.data;
  },

  /**
   * Get single team member by ID
   */
  async getTeamMember(id) {
    const response = await api.get(`/team/members/${id}`);
    return response.data;
  },

  /**
   * Create new team member
   */
  async createTeamMember(data) {
    const response = await api.post('/team/members', data);
    return response.data;
  },

  /**
   * Update team member
   */
  async updateTeamMember(id, data) {
    const response = await api.put(`/team/members/${id}`, data);
    return response.data;
  },

  /**
   * Delete team member
   */
  async deleteTeamMember(id) {
    const response = await api.delete(`/team/members/${id}`);
    return response.data;
  },

  /**
   * Toggle team member active status
   */
  async toggleTeamMemberStatus(id) {
    const response = await api.post(`/team/members/${id}/toggle`);
    return response.data;
  },

  /**
   * Upload avatar for team member
   */
  async uploadAvatar(id, file) {
    const formData = new FormData();
    formData.append('avatar', file);
    const response = await api.post(`/team/members/${id}/avatar`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  /**
   * Get departments list
   */
  async getDepartments() {
    const response = await api.get('/team/departments');
    return response.data;
  },

  /**
   * Get team stats (admin only)
   */
  async getStats() {
    const response = await api.get('/team/stats');
    return response.data;
  },

  /**
   * Get comprehensive admin dashboard stats for professionals overview
   */
  async getAdminDashboardStats() {
    const response = await api.get('/team/admin-dashboard-stats');
    return response.data;
  },

  // ==================== TEAM ENTITY MANAGEMENT ====================

  /**
   * Get list of teams with optional filters
   * @param {Object} params - { team_type, active, q }
   */
  async getTeams(params = {}) {
    const response = await api.get('/team/teams', { params });
    return response.data;
  },

  /**
   * Get single team by ID with members
   */
  async getTeam(id) {
    const response = await api.get(`/team/teams/${id}`);
    return response.data;
  },

  /**
   * Create new team
   * @param {Object} data - { name, team_type, head_id, description, member_ids }
   */
  async createTeam(data) {
    const response = await api.post('/team/teams', data);
    return response.data;
  },

  /**
   * Update team
   * @param {number} id - Team ID
   * @param {Object} data - { name, head_id, description, is_active, member_ids }
   */
  async updateTeam(id, data) {
    const response = await api.put(`/team/teams/${id}`, data);
    return response.data;
  },

  /**
   * Delete team (soft delete)
   */
  async deleteTeam(id) {
    const response = await api.delete(`/team/teams/${id}`);
    return response.data;
  },

  /**
   * Add member to team
   */
  async addTeamMember(teamId, userId) {
    const response = await api.post(`/team/teams/${teamId}/members`, { user_id: userId });
    return response.data;
  },

  /**
   * Remove member from team
   */
  async removeTeamMember(teamId, userId) {
    const response = await api.delete(`/team/teams/${teamId}/members/${userId}`);
    return response.data;
  },

  /**
   * Get available team leaders for a team type
   */
  async getAvailableLeaders(teamType) {
    const response = await api.get(`/team/available-leaders/${teamType}`);
    return response.data;
  },

  /**
   * Get available professionals for a team type
   */
  async getAvailableProfessionals(teamType) {
    const response = await api.get(`/team/available-professionals/${teamType}`);
    return response.data;
  },

  /**
   * Get clients associated with a team member (professional)
   * @param {number} memberId - User ID
   * @param {Object} params - { page, per_page, q, stato }
   */
  async getMemberClients(memberId, params = {}) {
    const response = await api.get(`/team/members/${memberId}/clients`, { params });
    return response.data;
  },

  /**
   * Get check responses from clients associated with a team member (professional)
   * @param {number} memberId - User ID
   * @param {Object} params - { period, start_date, end_date, page, per_page }
   */
  async getMemberChecks(memberId, params = {}) {
    const response = await api.get(`/team/members/${memberId}/checks`, { params });
    return response.data;
  },

  /**
   * Helper function to determine user role from backend data
   */
  getUserRole(user) {
    if (user.is_admin) {
      return USER_ROLES.ADMIN;
    }
    if (user.is_team_leader || user.teams_led?.length > 0) {
      return USER_ROLES.TEAM_LEADER;
    }
    if (user.is_external) {
      return USER_ROLES.TEAM_ESTERNO;
    }
    return USER_ROLES.PROFESSIONISTA;
  },

  /**
   * Helper function to determine user specialty from backend data
   */
  getUserSpecialty(user) {
    if (user.specialty) {
      return user.specialty;
    }

    // Derive from department if not explicitly set
    const deptName = user.department?.name?.toLowerCase();
    if (!deptName) return null;

    if (deptName.includes('nutri')) return 'nutrizione';
    if (deptName.includes('psico')) return 'psicologia';
    if (deptName.includes('coach')) return 'coach';
    if (deptName === 'cco') return 'cco';
    if (deptName.includes('admin') || deptName.includes('hr')) return 'amministrazione';

    return null;
  },

  /**
   * Get role badge color
   */
  getRoleBadgeColor(role) {
    return ROLE_COLORS[role] || 'secondary';
  },

  /**
   * Get specialty badge color
   */
  getSpecialtyBadgeColor(specialty) {
    return SPECIALTY_COLORS[specialty] || 'secondary';
  },

  // ==================== ASSEGNAZIONI AI ====================

  /**
   * Get all professionals for AI assignments
   * Returns professionals with their assignment_ai_notes and client KPIs
   */
  async getAssegnazioni(params = {}) {
    const response = await api.get('/team/api/assegnazioni', { params });
    return response.data;
  },

  /**
   * Get single professional's assignment data
   */
  async getAssegnazione(userId) {
    const response = await api.get(`/team/api/assegnazioni/${userId}`);
    return response.data;
  },

  /**
   * Update professional's assignment AI notes
   * @param {number} userId - Professional user ID
   * @param {Object} data - { specializzazione, target_ideale, problematiche_efficaci, target_non_ideale, link_calendario, note_aggiuntive }
   */
  async updateAssegnazione(userId, data) {
    const response = await api.post(`/team/api/assegnazioni/${userId}`, data);
    return response.data;
  },

  /**
   * Toggle professional's availability for assignments
   */
  async toggleDisponibile(userId) {
    const response = await api.post(`/team/api/assegnazioni/${userId}/toggle-disponibile`);
    return response.data;
  },
};

export default teamService;

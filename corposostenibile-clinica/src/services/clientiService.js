import api from './api';
import axios from 'axios';

// ==================== ENUM CONSTANTS ====================

// Stati cliente
export const STATO_CLIENTE = {
  ATTIVO: 'attivo',
  GHOST: 'ghost',
  PAUSA: 'pausa',
  STOP: 'stop',
};

export const STATO_LABELS = {
  attivo: 'Attivo',
  ghost: 'Ghost',
  pausa: 'Pausa',
  stop: 'Ex-Cliente',
};

export const STATO_COLORS = {
  attivo: 'success',
  ghost: 'warning',
  pausa: 'info',
  stop: 'danger',
};

// Tipologia cliente
export const TIPOLOGIA_CLIENTE = {
  A: 'a',
  B: 'b',
  C: 'c',
  STOP: 'stop',
  RECUPERO: 'recupero',
  PAUSA_GT_30: 'pausa_gt_30',
};

export const TIPOLOGIA_LABELS = {
  a: 'Tipo A',
  b: 'Tipo B',
  c: 'Tipo C',
  secondario: 'Secondario',
  stop: 'Ex-Cliente',
  recupero: 'Recupero',
  pausa_gt_30: 'Pausa > 30gg',
};

export const TIPOLOGIA_COLORS = {
  a: 'success',
  b: 'warning',
  c: 'info',
  secondario: 'secondary',
  stop: 'danger',
  recupero: 'secondary',
  pausa_gt_30: 'dark',
};

// Genere
export const GENERE = {
  UOMO: 'uomo',
  DONNA: 'donna',
};

export const GENERE_LABELS = {
  uomo: 'Uomo',
  donna: 'Donna',
};

// Modalità pagamento
export const PAGAMENTO = {
  BONIFICO: 'bonifico',
  KLARNA: 'klarna',
  STRIPE: 'stripe',
  PAYPAL: 'paypal',
  CARTA: 'carta',
  CONTANTI: 'contanti',
};

export const PAGAMENTO_LABELS = {
  bonifico: 'Bonifico',
  klarna: 'Klarna',
  stripe: 'Stripe',
  paypal: 'PayPal',
  carta: 'Carta',
  contanti: 'Contanti',
};

// Giorni check (formato lungo usato nell'API)
export const GIORNI = {
  LUNEDI: 'lunedi',
  MARTEDI: 'martedi',
  MERCOLEDI: 'mercoledi',
  GIOVEDI: 'giovedi',
  VENERDI: 'venerdi',
  SABATO: 'sabato',
  DOMENICA: 'domenica',
};

export const GIORNI_LABELS = {
  lunedi: 'Lunedì',
  martedi: 'Martedì',
  mercoledi: 'Mercoledì',
  giovedi: 'Giovedì',
  venerdi: 'Venerdì',
  sabato: 'Sabato',
  domenica: 'Domenica',
  // Supporto formato corto legacy
  lun: 'Lunedì',
  mar: 'Martedì',
  mer: 'Mercoledì',
  gio: 'Giovedì',
  ven: 'Venerdì',
  sab: 'Sabato',
  dom: 'Domenica',
};

// Stati professionisti (nutrizione, coach, psicologia)
export const STATI_PROFESSIONISTA = {
  ATTIVO: 'attivo',
  GHOST: 'ghost',
  PAUSA: 'pausa',
  STOP: 'stop',
};

export const STATI_PROFESSIONISTA_LABELS = {
  attivo: 'Attivo',
  ghost: 'Ghost',
  pausa: 'Pausa',
  stop: 'Ex-Cliente',
};

export const STATI_PROFESSIONISTA_COLORS = {
  attivo: { bg: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)', color: '#166534' },
  ghost: { bg: 'linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%)', color: '#3730a3' },
  pausa: { bg: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)', color: '#92400e' },
  stop: { bg: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)', color: '#991b1b' },
};

// Patologie psicologiche
export const PATOLOGIE_PSICO = [
  { key: 'patologia_psico_dca', label: 'DCA' },
  { key: 'patologia_psico_obesita_psicoemotiva', label: 'Obesità Psicoemotiva' },
  { key: 'patologia_psico_ansia_umore_cibo', label: 'Ansia/Umore/Cibo' },
  { key: 'patologia_psico_comportamenti_disfunzionali', label: 'Comportamenti Disfunzionali' },
  { key: 'patologia_psico_immagine_corporea', label: 'Immagine Corporea' },
  { key: 'patologia_psico_psicosomatiche', label: 'Psicosomatiche' },
  { key: 'patologia_psico_relazionali_altro', label: 'Relazionali/Altro' },
];

// Tipi professionista (per assegnazioni)
export const TIPO_PROFESSIONISTA = {
  NUTRIZIONISTA: 'nutrizionista',
  COACH: 'coach',
  PSICOLOGA: 'psicologa',
  MEDICO: 'medico',
  HEALTH_MANAGER: 'health_manager',
  CONSULENTE: 'consulente',
};

export const TIPO_PROFESSIONISTA_LABELS = {
  nutrizionista: 'Nutrizionista',
  coach: 'Coach',
  psicologa: 'Psicologo/a',
  medico: 'Medico',
  health_manager: 'Health Manager',
  consulente: 'Consulente',
};

export const TIPO_PROFESSIONISTA_ICONS = {
  nutrizionista: 'ri-heart-pulse-line',
  coach: 'ri-run-line',
  psicologa: 'ri-mental-health-line',
  medico: 'ri-stethoscope-line',
  health_manager: 'ri-user-star-line',
  consulente: 'ri-money-dollar-circle-line',
};

export const TIPO_PROFESSIONISTA_COLORS = {
  nutrizionista: { bg: 'success', icon: 'text-success', bgSubtle: 'bg-success-subtle' },
  coach: { bg: 'warning', icon: 'text-warning', bgSubtle: 'bg-warning-subtle' },
  psicologa: { bg: 'info', icon: 'text-info', bgSubtle: 'bg-info-subtle' },
  medico: { bg: 'danger', icon: 'text-danger', bgSubtle: 'bg-danger-subtle' },
  health_manager: { bg: 'primary', icon: 'text-primary', bgSubtle: 'bg-primary-subtle' },
  consulente: { bg: 'purple', icon: 'text-purple', bgSubtle: 'bg-purple-subtle' },
};

// Patologie nutrizionali
export const PATOLOGIE_NUTRI = [
  { key: 'patologia_ibs', label: 'IBS' },
  { key: 'patologia_reflusso', label: 'Reflusso' },
  { key: 'patologia_gastrite', label: 'Gastrite' },
  { key: 'patologia_dca', label: 'DCA' },
  { key: 'patologia_insulino_resistenza', label: 'Insulino-Resistenza' },
  { key: 'patologia_diabete', label: 'Diabete' },
  { key: 'patologia_dislipidemie', label: 'Dislipidemie' },
  { key: 'patologia_steatosi_epatica', label: 'Steatosi Epatica' },
  { key: 'patologia_ipertensione', label: 'Ipertensione' },
  { key: 'patologia_pcos', label: 'PCOS' },
  { key: 'patologia_endometriosi', label: 'Endometriosi' },
  { key: 'patologia_obesita_sindrome', label: 'Obesità Sindrome' },
  { key: 'patologia_osteoporosi', label: 'Osteoporosi' },
  { key: 'patologia_diverticolite', label: 'Diverticolite' },
  { key: 'patologia_crohn', label: 'Crohn' },
  { key: 'patologia_stitichezza', label: 'Stitichezza' },
  { key: 'patologia_tiroidee', label: 'Tiroidee' },
];

// Luogo allenamento
export const LUOGO_ALLENAMENTO = {
  CASA: 'casa',
  PALESTRA: 'palestra',
  IBRIDO: 'ibrido',
};

export const LUOGO_LABELS = {
  casa: 'Casa',
  palestra: 'Palestra',
  ibrido: 'Ibrido',
};

// Team di vendita
export const TEAM = {
  INTERNO: 'interno',
  SALES_TEAM: 'sales_team',
  SETTER_TEAM: 'setter_team',
  SITO: 'sito',
  VA_TEAM: 'va_team',
};

export const TEAM_LABELS = {
  interno: 'Interno',
  sales_team: 'Sales Team',
  setter_team: 'Setter Team',
  sito: 'Sito',
  va_team: 'VA Team',
};

// Check saltati
export const CHECK_SALTATI_LABELS = {
  '1': '1 check',
  '2': '2 check',
  '3': '3 check',
  '3_plus': '3+ check',
};

// ==================== SERVICE FUNCTIONS ====================

// Base API path (relative to api.js baseURL '/api')
const API_BASE = '/v1/customers';

const clientiService = {
  /**
   * Get list of clients with filters and pagination
   * @param {Object} params - Query parameters
   * @returns {Promise} - API response with clients array and pagination
   */
  async getClienti(params = {}) {
    const response = await api.get(`${API_BASE}/`, { params });
    return response.data;
  },

  /**
   * Get single client by ID
   * @param {number} id - Client ID
   * @returns {Promise} - Client object
   */
  async getCliente(id) {
    const response = await api.get(`${API_BASE}/${id}`);
    return response.data;
  },

  /**
   * Create new client
   * @param {Object} data - Client data
   * @returns {Promise} - Created client object
   */
  async createCliente(data) {
    const response = await api.post(`${API_BASE}/`, data);
    return response.data;
  },

  /**
   * Update client
   * @param {number} id - Client ID
   * @param {Object} data - Updated data
   * @returns {Promise} - Updated client object
   */
  async updateCliente(id, data) {
    const response = await api.patch(`${API_BASE}/${id}`, data);
    return response.data;
  },

  /**
   * Update single field (convenience wrapper)
   * @param {number} id - Client ID
   * @param {string} field - Field name
   * @param {any} value - Field value
   * @returns {Promise} - Updated client object
   */
  async updateField(id, field, value) {
    const response = await api.patch(`${API_BASE}/${id}`, { [field]: value });
    return response.data;
  },

  /**
   * Delete client
   * @param {number} id - Client ID
   * @returns {Promise} - Success response
   */
  async deleteCliente(id) {
    const response = await api.delete(`${API_BASE}/${id}`);
    return response.data;
  },

  /**
   * Get client history
   * @param {number} id - Client ID
   * @param {number} limit - Max results
   * @returns {Promise} - History array
   */
  async getHistory(id, limit = 20) {
    const response = await api.get(`${API_BASE}/${id}/history`, { params: { limit } });
    return response.data;
  },

  /**
   * Get dashboard stats
   * @returns {Promise} - Stats object
   */
  async getStats() {
    const response = await api.get(`${API_BASE}/stats`);
    return response.data;
  },

  /**
   * Get comprehensive admin dashboard stats for patients overview
   * @returns {Promise} - Full stats with KPIs, distributions, trends
   */
  async getAdminDashboardStats() {
    const response = await api.get(`${API_BASE}/admin-dashboard-stats`);
    return response.data;
  },

  // ==================== SPECIALTY VIEWS ====================

  /**
   * Get clients for Nutrizione view (list_nutrizionista)
   * @param {Object} params - Query parameters
   * @returns {Promise} - API response with clients and KPIs
   */
  async getClientiNutrizione(params = {}) {
    const response = await api.get(`${API_BASE}/`, {
      params: {
        ...params,
        view: 'nutrizione',
      },
    });
    return response.data;
  },

  /**
   * Get clients for Coach view (list_coach)
   * @param {Object} params - Query parameters
   * @returns {Promise} - API response with clients and KPIs
   */
  async getClientiCoach(params = {}) {
    const response = await api.get(`${API_BASE}/`, {
      params: {
        ...params,
        view: 'coach',
      },
    });
    return response.data;
  },

  /**
   * Get clients for Psicologia view (list_psicologo)
   * @param {Object} params - Query parameters
   * @returns {Promise} - API response with clients and KPIs
   */
  async getClientiPsicologia(params = {}) {
    const response = await api.get(`${API_BASE}/`, {
      params: {
        ...params,
        view: 'psicologia',
      },
    });
    return response.data;
  },

  async getClientiExpiring(params = {}) {
    const response = await api.get(`${API_BASE}/expiring`, { params });
    return response.data;
  },

  async getClientiUnsatisfied(params = {}) {
    const response = await api.get(`${API_BASE}/unsatisfied`, { params });
    return response.data;
  },

  /**
   * Get KPI stats for specialty views
   * @param {string} specialty - 'nutrizione' | 'coach' | 'psicologia'
   * @param {number} professionalId - Optional professional ID to filter
   * @returns {Promise} - KPI stats
   */
  async getSpecialtyKpi(specialty, professionalId = null) {
    const params = { specialty };
    if (professionalId) {
      params.professional_id = professionalId;
    }
    const response = await api.get(`${API_BASE}/specialty-kpi`, { params });
    return response.data;
  },

  /**
   * Get feedback metrics for a client
   * @param {number} id - Client ID
   * @returns {Promise} - Feedback metrics data
   */
  async getFeedbackMetrics(id) {
    const response = await api.get(`${API_BASE}/${id}/feedback-metrics`);
    return response.data;
  },

  /**
   * Get initial checks (Check 1, 2) from original lead/assignment
   * @param {number} id - Client ID
   * @returns {Promise} - { has_data, checks: { check_1, check_2 } }
   */
  async getInitialChecks(id) {
    const response = await api.get(`${API_BASE}/${id}/initial-checks`);
    return response.data;
  },

  /**
   * Get weekly checks metrics for a client
   * @param {number} id - Client ID
   * @returns {Promise} - Weekly checks metrics data
   */
  async getWeeklyChecksMetrics(id) {
    const response = await api.get(`${API_BASE}/${id}/weekly-checks-metrics`);
    return response.data;
  },

  // ==================== CUSTOMER CARE INTERVENTIONS ====================

  /**
   * Get customer care interventions
   * @param {number} id - Client ID
   * @returns {Promise} - Interventions array
   */
  async getCustomerCareInterventions(id) {
    const response = await api.get(`${API_BASE}/${id}/customer-care-interventions`);
    return response.data;
  },

  /**
   * Create customer care intervention
   * @param {number} id - Client ID
   * @param {Object} data - Intervention data
   * @returns {Promise} - Created intervention
   */
  async createCustomerCareIntervention(id, data) {
    const response = await api.post(`${API_BASE}/${id}/customer-care-interventions`, data);
    return response.data;
  },

  /**
   * Update customer care intervention
   * @param {number} interventionId - Intervention ID
   * @param {Object} data - Updated data
   * @returns {Promise} - Updated intervention
   */
  async updateCustomerCareIntervention(interventionId, data) {
    const response = await api.put(`${API_BASE}/customer-care-interventions/${interventionId}`, data);
    return response.data;
  },

  /**
   * Delete customer care intervention
   * @param {number} interventionId - Intervention ID
   * @returns {Promise} - Success response
   */
  async deleteCustomerCareIntervention(interventionId) {
    const response = await api.delete(`${API_BASE}/customer-care-interventions/${interventionId}`);
    return response.data;
  },

  // ==================== CHECK IN INTERVENTIONS ====================

  async getCheckInInterventions(id) {
    const response = await api.get(`${API_BASE}/${id}/check-in-interventions`);
    return response.data;
  },

  async createCheckInIntervention(id, data) {
    const response = await api.post(`${API_BASE}/${id}/check-in-interventions`, data);
    return response.data;
  },

  async updateCheckInIntervention(interventionId, data) {
    const response = await api.put(`${API_BASE}/check-in-interventions/${interventionId}`, data);
    return response.data;
  },

  async deleteCheckInIntervention(interventionId) {
    const response = await api.delete(`${API_BASE}/check-in-interventions/${interventionId}`);
    return response.data;
  },

  // ==================== TRUSTPILOT ====================

  async getTrustpilotOverview(params = {}) {
    const response = await api.get(`${API_BASE}/trustpilot-overview`, { params });
    return response.data;
  },

  async getTrustpilotStatus(id) {
    const response = await api.get(`${API_BASE}/${id}/trustpilot`);
    return response.data;
  },

  async generateTrustpilotLink(id, data = {}) {
    const response = await api.post(`${API_BASE}/${id}/trustpilot/link`, data);
    return response.data;
  },

  async sendTrustpilotInvite(id, data = {}) {
    const response = await api.post(`${API_BASE}/${id}/trustpilot/invite`, data);
    return response.data;
  },

  // ==================== VIDEO REVIEW (MARKETING) ====================

  async getVideoReviewRequests(id) {
    const response = await api.get(`${API_BASE}/${id}/video-review-requests`);
    return response.data;
  },

  async createVideoReviewBooked(id, data = {}) {
    const response = await api.post(`${API_BASE}/${id}/video-review-requests/booked`, data);
    return response.data;
  },

  async confirmVideoReviewByHm(requestId, data) {
    const response = await api.post(`${API_BASE}/video-review-requests/${requestId}/hm-confirm`, data);
    return response.data;
  },

  // ==================== PROFESSIONAL ASSIGNMENT ====================

  /**
   * Get professional assignment history for a client
   * @param {number} clienteId - Client ID
   * @returns {Promise} - History array
   */
  async getProfessionistiHistory(clienteId) {
    const response = await api.get(`${API_BASE}/${clienteId}/professionisti/history`);
    return response.data;
  },

  /**
   * Assign a professional to a client
   * @param {number} clienteId - Client ID
   * @param {Object} data - Assignment data (tipo_professionista, user_id, data_dal, motivazione_aggiunta)
   * @returns {Promise} - Response with history_id
   */
  async assignProfessionista(clienteId, data) {
    const response = await api.post(`${API_BASE}/${clienteId}/professionisti/assign`, data);
    return response.data;
  },

  /**
   * Interrupt a professional assignment
   * @param {number} clienteId - Client ID
   * @param {number} historyId - History record ID
   * @param {Object} data - Interruption data (motivazione_interruzione, data_al optional)
   * @returns {Promise} - Success response
   */
  async interruptProfessionista(clienteId, historyId, data) {
    const response = await api.post(`${API_BASE}/${clienteId}/professionisti/${historyId}/interrupt`, data);
    return response.data;
  },

  /**
   * Interrupt a legacy professional assignment (without history record)
   * @param {number} clienteId - Client ID
   * @param {Object} data - Interruption data (user_id, tipo_professionista, motivazione_interruzione)
   * @returns {Promise} - Success response
   */
  async interruptLegacyProfessionista(clienteId, data) {
    const response = await api.post(`${API_BASE}/${clienteId}/professionisti/legacy/interrupt`, data);
    return response.data;
  },

  // ==================== SEARCH ====================

  /**
   * Search clients
   * Note: Uses the HTML blueprint endpoint, not the REST API
   * @param {string} query - Search query
   * @returns {Promise} - Search results
   */
  async searchClienti(query) {
    // This endpoint is on the HTML blueprint, not the API
    const response = await axios.get('/customers/api/search', {
      params: { q: query },
      withCredentials: true,
    });
    return response.data;
  },

  // ==================== HELPER FUNCTIONS ====================

  /**
   * Get badge color for stato
   * @param {string} stato - State value
   * @returns {string} - Bootstrap color class
   */
  getStatoBadgeColor(stato) {
    return STATO_COLORS[stato] || 'secondary';
  },

  /**
   * Get badge color for tipologia
   * @param {string} tipologia - Type value
   * @returns {string} - Bootstrap color class
   */
  getTipologiaBadgeColor(tipologia) {
    return TIPOLOGIA_COLORS[tipologia] || 'secondary';
  },

  /**
   * Format date for display
   * @param {string} dateStr - ISO date string
   * @returns {string} - Formatted date (dd/mm/yyyy)
   */
  formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('it-IT');
  },

  /**
   * Format currency
   * @param {number} amount - Amount
   * @returns {string} - Formatted currency
   */
  formatCurrency(amount) {
    if (amount == null) return '-';
    return new Intl.NumberFormat('it-IT', {
      style: 'currency',
      currency: 'EUR',
    }).format(amount);
  },

  /**
   * Get client initials
   * @param {string} name - Full name
   * @returns {string} - Initials
   */
  getInitials(name) {
    if (!name) return '??';
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  },

  /**
   * Calculate age from birth date
   * @param {string} birthDate - Birth date string
   * @returns {number|null} - Age in years
   */
  calculateAge(birthDate) {
    if (!birthDate) return null;
    const today = new Date();
    const birth = new Date(birthDate);
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  },

  /**
   * Check if subscription is expiring soon
   * @param {string} renewalDate - Renewal date
   * @param {number} days - Days threshold
   * @returns {boolean} - Is expiring
   */
  isExpiringSoon(renewalDate, days = 30) {
    if (!renewalDate) return false;
    const renewal = new Date(renewalDate);
    const today = new Date();
    const diffTime = renewal - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays >= 0 && diffDays <= days;
  },

  // ==================== STORICO STATI ====================

  /**
   * Get state history for a specific service
   * Note: Uses axios directly because this endpoint is at /customers/... not /api/customers/...
   * @param {number} clienteId - Client ID
   * @param {string} servizio - Service type: 'nutrizione', 'chat_nutrizione', 'coach', 'chat_coaching', 'psicologia', 'chat_psicologia'
   * @returns {Promise} - History data { ok, servizio, storico: [] }
   */
  async getStoricoStati(clienteId, servizio) {
    const response = await axios.get(`/customers/${clienteId}/stati/${servizio}/storico`, { withCredentials: true });
    return response.data;
  },

  /**
   * Get pathology history for a client
   * Note: Uses axios directly because this endpoint is at /customers/... not /api/customers/...
   * @param {number} clienteId - Client ID
   * @returns {Promise} - History data { ok, storico: [] }
   */
  async getStoricoPatologie(clienteId) {
    const response = await axios.get(`/customers/${clienteId}/patologie/storico`, { withCredentials: true });
    return response.data;
  },

  // ==================== PIANI ALIMENTARI ====================

  /**
   * Get meal plans history for a client
   * Note: Uses axios directly because this endpoint is at /customers/... not /api/customers/...
   * @param {number} clienteId - Client ID
   * @returns {Promise} - { ok, plans: [] }
   */
  async getMealPlans(clienteId) {
    const response = await axios.get(`/customers/${clienteId}/nutrition/history`, { withCredentials: true });
    return response.data;
  },

  /**
   * Get meal plan versions
   * @param {number} clienteId - Client ID
   * @param {number} planId - Plan ID
   * @returns {Promise} - { ok, plan, versions: [] }
   */
  async getMealPlanVersions(clienteId, planId) {
    const response = await axios.get(`/customers/${clienteId}/nutrition/${planId}/versions`, { withCredentials: true });
    return response.data;
  },

  /**
   * Download meal plan PDF URL
   * @param {number} clienteId - Client ID
   * @param {number} planId - Plan ID
   * @returns {string} - Download URL
   */
  getMealPlanDownloadUrl(clienteId, planId) {
    return `/customers/${clienteId}/nutrition/${planId}/download`;
  },

  /**
   * Update an existing meal plan
   * Note: Uses axios directly because this endpoint is at /customers/... not /api/customers/...
   * @param {number} clienteId - Client ID
   * @param {FormData} formData - Form data with plan_id, start_date, end_date, notes, change_reason, and optional file
   * @returns {Promise} - { ok, message }
   */
  async updateMealPlan(clienteId, formData) {
    const response = await axios.post(`/customers/${clienteId}/nutrition/change`, formData, {
      withCredentials: true,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // ==================== ANAMNESI ====================

  /**
   * Get anamnesi for a specific service
   * @param {number} clienteId - Client ID
   * @param {string} serviceType - 'nutrizione', 'coaching', or 'psicologia'
   * @returns {Promise} - { success, anamnesi: { id, content, created_at, updated_at, created_by, last_modified_by } | null }
   */
  async getAnamnesi(clienteId, serviceType) {
    const response = await api.get(`${API_BASE}/${clienteId}/anamnesi/${serviceType}`);
    return response.data;
  },

  /**
   * Create or update anamnesi for a specific service
   * @param {number} clienteId - Client ID
   * @param {string} serviceType - 'nutrizione', 'coaching', or 'psicologia'
   * @param {string} content - Anamnesi content
   * @returns {Promise} - { success, message, anamnesi_id }
   */
  async saveAnamnesi(clienteId, serviceType, content) {
    const response = await api.post(`${API_BASE}/${clienteId}/anamnesi/${serviceType}`, { content });
    return response.data;
  },

  // ==================== DIARIO ====================

  /**
   * Get all diary entries for a specific service
   * @param {number} clienteId - Client ID
   * @param {string} serviceType - 'nutrizione', 'coaching', or 'psicologia'
   * @returns {Promise} - { success, entries: [{ id, entry_date, entry_date_display, content, author, created_at }] }
   */
  async getDiaryEntries(clienteId, serviceType) {
    const response = await api.get(`${API_BASE}/${clienteId}/diary/${serviceType}`);
    return response.data;
  },

  /**
   * Create a new diary entry
   * @param {number} clienteId - Client ID
   * @param {string} serviceType - 'nutrizione', 'coaching', or 'psicologia'
   * @param {string} content - Diary entry content
   * @param {string} entryDate - Date in YYYY-MM-DD format (optional, defaults to today)
   * @returns {Promise} - { success, message, entry }
   */
  async createDiaryEntry(clienteId, serviceType, content, entryDate = null) {
    const data = { content };
    if (entryDate) data.entry_date = entryDate;
    const response = await api.post(`${API_BASE}/${clienteId}/diary/${serviceType}`, data);
    return response.data;
  },

  /**
   * Update an existing diary entry
   * @param {number} clienteId - Client ID
   * @param {string} serviceType - 'nutrizione', 'coaching', or 'psicologia'
   * @param {number} entryId - Entry ID
   * @param {string} content - Updated content
   * @param {string} entryDate - Updated date in YYYY-MM-DD format (optional)
   * @returns {Promise} - { success, message, entry }
   */
  async updateDiaryEntry(clienteId, serviceType, entryId, content, entryDate = null) {
    const data = { content };
    if (entryDate) data.entry_date = entryDate;
    const response = await api.put(`${API_BASE}/${clienteId}/diary/${serviceType}/${entryId}`, data);
    return response.data;
  },

  /**
   * Delete a diary entry
   * @param {number} clienteId - Client ID
   * @param {string} serviceType - 'nutrizione', 'coaching', or 'psicologia'
   * @param {number} entryId - Entry ID
   * @returns {Promise} - { success, message }
   */
  async deleteDiaryEntry(clienteId, serviceType, entryId) {
    const response = await api.delete(`${API_BASE}/${clienteId}/diary/${serviceType}/${entryId}`);
    return response.data;
  },

  /**
   * Get diary entry history
   * @param {number} clienteId
   * @param {string} serviceType
   * @param {number} entryId
   * @returns {Promise} - { success, history: [] }
   */
  async getDiaryHistory(clienteId, serviceType, entryId) {
    const response = await api.get(`${API_BASE}/${clienteId}/diary/${serviceType}/${entryId}/history`);
    return response.data;
  },

  // ==================== TRAINING PLANS ====================

  /**
   * Get training plans history for a client
   * @param {number} clienteId - Client ID
   * @returns {Promise} - { ok, plans: [] }
   */
  async getTrainingPlans(clienteId) {
    const response = await axios.get(`/customers/${clienteId}/training/history`, { withCredentials: true });
    return response.data;
  },

  /**
   * Add a new training plan
   * @param {number} clienteId - Client ID
   * @param {FormData} formData - Form data with name, start_date, end_date, notes, piano_allenamento_file
   * @returns {Promise} - { ok, plan_id, message }
   */
  async addTrainingPlan(clienteId, formData) {
    const response = await axios.post(`/customers/${clienteId}/training/add`, formData, {
      withCredentials: true,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  /**
   * Get training plan versions
   * @param {number} clienteId - Client ID
   * @param {number} planId - Plan ID
   * @returns {Promise} - { ok, versions: [] }
   */
  async getTrainingPlanVersions(clienteId, planId) {
    const response = await axios.get(`/customers/${clienteId}/training/${planId}/versions`, { withCredentials: true });
    return response.data;
  },

  /**
   * Download training plan PDF URL
   * @param {number} clienteId - Client ID
   * @param {number} planId - Plan ID
   * @returns {string} - Download URL
   */
  getTrainingPlanDownloadUrl(clienteId, planId) {
    return `/customers/${clienteId}/training/${planId}/download`;
  },

  /**
   * Update an existing training plan
   * @param {number} clienteId - Client ID
   * @param {FormData} formData - Form data
   * @returns {Promise} - { ok, message }
   */
  async updateTrainingPlan(clienteId, formData) {
    const response = await axios.post(`/customers/${clienteId}/training/change`, formData, {
      withCredentials: true,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // ==================== TRAINING LOCATIONS ====================

  /**
   * Get training locations history for a client
   * @param {number} clienteId - Client ID
   * @returns {Promise} - { ok, locations: [] }
   */
  async getTrainingLocations(clienteId) {
    const response = await axios.get(`/customers/${clienteId}/location/history`, { withCredentials: true });
    return response.data;
  },

  /**
   * Add a new training location
   * @param {number} clienteId - Client ID
   * @param {Object} data - { location, start_date, end_date?, notes? }
   * @returns {Promise} - { ok, location_id }
   */
  async addTrainingLocation(clienteId, data) {
    const response = await axios.post(`/customers/${clienteId}/location/add`, data, { withCredentials: true });
    return response.data;
  },

  /**
   * Update a training location
   * @param {number} clienteId - Client ID
   * @param {number} locationId - Location ID
   * @param {Object} data - { location?, start_date?, end_date?, notes?, change_reason? }
   * @returns {Promise} - { ok, message }
   */
  async updateTrainingLocation(clienteId, locationId, data) {
    const response = await axios.post(`/customers/${clienteId}/location/change/${locationId}`, data, { withCredentials: true });
    return response.data;
  },

  // ==================== CALL BONUS ====================

  /**
   * Get call bonus history for a client
   * @param {number} clienteId - Client ID
   * @returns {Promise} - { data: [...] }
   */
  async getCallBonusHistory(clienteId) {
    const response = await api.get(`${API_BASE}/${clienteId}/call-bonus-history`);
    return response.data;
  },

  /**
   * Create a call bonus request with AI analysis
   * @param {number} clienteId - Client ID
   * @param {Object} data - { tipo_professionista, note_richiesta }
   * @returns {Promise} - { success, call_bonus_id, analysis, matches }
   */
  async createCallBonusRequest(clienteId, data) {
    const response = await api.post(`${API_BASE}/${clienteId}/call-bonus-request`, data);
    return response.data;
  },

  /**
   * Select a professional for a call bonus
   * @param {number} callBonusId - Call Bonus ID
   * @param {number} professionalId - Professional ID
   * @returns {Promise} - { success, call_bonus_id, professional_name, link_call_bonus }
   */
  async selectCallBonusProfessional(callBonusId, professionalId) {
    const response = await api.post(`${API_BASE}/call-bonus-select/${callBonusId}`, {
      professional_id: professionalId,
    });
    return response.data;
  },

  /**
   * Confirm booking for a call bonus
   * @param {number} callBonusId - Call Bonus ID
   * @returns {Promise} - { success, call_bonus_id, message }
   */
  async confirmCallBonusBooking(callBonusId) {
    const response = await api.post(`${API_BASE}/call-bonus-confirm/${callBonusId}`);
    return response.data;
  },

  /**
   * Decline a call bonus (professionista rifiuta)
   * @param {number} callBonusId - Call Bonus ID
   * @returns {Promise} - { success, call_bonus_id, message }
   */
  async declineCallBonus(callBonusId) {
    const response = await api.post(`${API_BASE}/call-bonus-decline/${callBonusId}`);
    return response.data;
  },

  /**
   * Respond to call bonus interest (professionista assegnato conferma/rifiuta interesse paziente)
   * @param {number} callBonusId - Call Bonus ID
   * @param {boolean} interested - true if patient is interested, false otherwise
   * @param {string} motivazione - Optional motivation (for non-interested)
   * @returns {Promise} - { success, call_bonus_id, status, message }
   */
  async respondCallBonusInterest(callBonusId, interested, motivazione = '') {
    const response = await api.post(`${API_BASE}/call-bonus-interest/${callBonusId}`, {
      interested,
      motivazione,
    });
    return response.data;
  },
};

export default clientiService;

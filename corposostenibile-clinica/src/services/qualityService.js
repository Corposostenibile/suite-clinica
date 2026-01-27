import axios from 'axios';

/**
 * Quality Service
 * Service for fetching Quality Score data from the backend API.
 *
 * Note: Uses axios directly because quality routes are at /quality/api/...
 * instead of /api/quality/... like other services.
 */

// Create axios instance for quality routes
const qualityApi = axios.create({
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Bonus band thresholds (for display)
export const BONUS_BANDS = {
    '100%': { minScore: 9.0, color: '#22c55e', gradient: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' },
    '60%': { minScore: 8.5, color: '#3b82f6', gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' },
    '30%': { minScore: 8.0, color: '#f59e0b', gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' },
    '0%': { minScore: 0, color: '#94a3b8', gradient: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)' },
};

// Miss rate penalty tiers
export const MISS_RATE_PENALTIES = [
    { maxRate: 0.05, penalty: 0, label: '0-5%' },
    { maxRate: 0.10, penalty: 0.5, label: '5-10%' },
    { maxRate: 0.20, penalty: 1.0, label: '10-20%' },
    { maxRate: 0.30, penalty: 2.0, label: '20-30%' },
    { maxRate: 0.40, penalty: 3.0, label: '30-40%' },
    { maxRate: 0.50, penalty: 4.0, label: '40-50%' },
    { maxRate: 1.00, penalty: 5.0, label: '>50%' },
];

// Specialty configuration
export const QUALITY_SPECIALTIES = {
    nutrizione: {
        label: 'Nutrizione',
        icon: 'ri-leaf-line',
        color: 'success',
        gradient: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
        filterValues: 'nutrizione,nutrizionista'
    },
    coach: {
        label: 'Coach',
        icon: 'ri-run-line',
        color: 'warning',
        gradient: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
        filterValues: 'coach'
    },
    psicologia: {
        label: 'Psicologia',
        icon: 'ri-mental-health-line',
        color: 'info',
        gradient: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
        filterValues: 'psicologia,psicologo'
    }
};

/**
 * Get week bounds (Monday to Sunday) for a given date
 * @param {Date} date - Target date
 * @returns {{start: Date, end: Date}} Week start and end dates
 */
export const getWeekBounds = (date = new Date()) => {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust for Monday
    const monday = new Date(d.setDate(diff));
    monday.setHours(0, 0, 0, 0);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    sunday.setHours(23, 59, 59, 999);
    return { start: monday, end: sunday };
};

/**
 * Format date as YYYY-MM-DD for API calls
 * @param {Date} date - Date to format
 * @returns {string} Formatted date string
 */
export const formatDateForApi = (date) => {
    return date.toISOString().split('T')[0];
};

/**
 * Format date as DD/MM/YYYY for display
 * @param {Date} date - Date to format
 * @returns {string} Formatted date string
 */
export const formatDateForDisplay = (date) => {
    return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

/**
 * Get quality score style based on value
 * @param {number} score - Quality score
 * @returns {Object} Style object with color and fontWeight
 */
export const getScoreStyle = (score) => {
    if (score >= 9) return { color: '#22c55e', fontWeight: 700 };
    if (score >= 8) return { color: '#3b82f6', fontWeight: 700 };
    if (score >= 7) return { color: '#f59e0b', fontWeight: 700 };
    return { color: '#ef4444', fontWeight: 700 };
};

/**
 * Get miss rate badge style based on rate
 * @param {number} rate - Miss rate (0-1)
 * @returns {Object} Style object for badge
 */
export const getMissRateBadgeStyle = (rate) => {
    if (rate > 0.2) return { background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', color: '#fff' };
    if (rate > 0.1) return { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: '#fff' };
    return { background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff' };
};

/**
 * Get bonus band badge style
 * @param {string} band - Bonus band ('100%', '60%', '30%', '0%')
 * @returns {Object} Style object for badge
 */
export const getBandBadgeStyle = (band) => {
    const styles = {
        '100%': { background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff' },
        '60%': { background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', color: '#fff' },
        '30%': { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: '#fff' },
        '0%': { background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)', color: '#fff' },
    };
    return styles[band] || styles['0%'];
};

/**
 * Get row background style based on bonus band
 * @param {string} band - Bonus band
 * @param {boolean} isHovered - Whether row is hovered
 * @returns {Object} Style object for row
 */
export const getRowBandStyle = (band, isHovered = false) => {
    const baseStyle = { transition: 'all 0.15s ease' };
    if (isHovered) {
        return { ...baseStyle, background: '#f8fafc' };
    }
    switch (band) {
        case '100%':
            return { ...baseStyle, background: '#f0fdf4', borderLeft: '3px solid #22c55e' };
        case '60%':
            return { ...baseStyle, background: '#eff6ff', borderLeft: '3px solid #3b82f6' };
        case '30%':
            return { ...baseStyle, background: '#fffbeb', borderLeft: '3px solid #f59e0b' };
        default:
            return { ...baseStyle, borderLeft: '3px solid #94a3b8' };
    }
};

/**
 * Quality Service object with API methods
 */
const qualityService = {
    /**
     * Get weekly quality scores for a specialty
     * @param {Object} params - Query parameters
     * @param {string} params.specialty - Specialty name ('nutrizione', 'coach', 'psicologia')
     * @param {string} [params.week] - Week start date (YYYY-MM-DD)
     * @param {number} [params.team_id] - Team ID filter
     * @returns {Promise<Object>} Quality data with professionals and stats
     */
    async getWeeklyScores(params = {}) {
        const response = await qualityApi.get('/quality/api/weekly-scores', { params });
        return response.data;
    },

    /**
     * Get quality trend for a professional (last 12 weeks)
     * @param {number} professionistaId - Professional ID
     * @returns {Promise<Object>} Trend data with labels and values
     */
    async getProfessionistaTrend(professionistaId) {
        const response = await qualityApi.get(`/quality/api/professionista/${professionistaId}/trend`);
        return response.data;
    },

    /**
     * Get eligible clients for a professional in a week
     * @param {number} professionistaId - Professional ID
     * @param {string} week - Week start date (YYYY-MM-DD)
     * @returns {Promise<Object>} Eligible clients data
     */
    async getEligibleClients(professionistaId, week) {
        const response = await qualityApi.get(`/quality/api/clienti-eleggibili/${professionistaId}`, {
            params: { week }
        });
        return response.data;
    },

    /**
     * Get check responses for a professional in a week
     * @param {number} professionistaId - Professional ID
     * @param {string} week - Week start date (YYYY-MM-DD)
     * @param {string} [dept] - Department type
     * @returns {Promise<Object>} Check responses data
     */
    async getCheckResponses(professionistaId, week, dept = 'nutrizione') {
        const response = await qualityApi.get(`/quality/api/check-responses/${professionistaId}`, {
            params: { week, dept }
        });
        return response.data;
    },

    /**
     * Calculate quality scores for a specialty and week
     * @param {Object} params - Calculation parameters
     * @param {string} params.specialty - Specialty ('nutrizione', 'coach', 'psicologia')
     * @param {string} params.week - Week start date (YYYY-MM-DD)
     * @param {number} [params.team_id] - Optional team ID filter
     * @returns {Promise<Object>} Calculation result with scores
     */
    async calculateQuality(params) {
        const response = await qualityApi.post('/quality/api/calculate', params);
        return response.data;
    },

    /**
     * Get dashboard stats for current week
     * @returns {Promise<Object>} Dashboard stats
     */
    async getDashboardStats() {
        const response = await qualityApi.get('/quality/api/dashboard/stats');
        return response.data;
    },

    /**
     * Calculate quarterly composite KPI with Super Malus for all professionals
     * @param {string} [quarter] - Quarter string (e.g. '2025-Q4'), defaults to current
     * @returns {Promise<Object>} Calculation result with stats and per-professional results
     */
    async calculateQuarterly(quarter) {
        const response = await qualityApi.post('/quality/api/calcola-trimestrale', { quarter });
        return response.data;
    },

    /**
     * Get quarterly summary with Super Malus details
     * @param {string} [quarter] - Quarter string (e.g. '2025-Q4'), defaults to current
     * @returns {Promise<Object>} Summary with aggregate stats and malus details
     */
    async getQuarterlySummary(quarter) {
        const response = await qualityApi.get('/quality/api/quarterly-summary', {
            params: quarter ? { quarter } : {}
        });
        return response.data;
    },

    /**
     * Get KPI breakdown for a specific professional in a quarter
     * @param {number} professionistaId - Professional ID
     * @param {string} [quarter] - Quarter string (e.g. '2025-Q4'), defaults to current
     * @returns {Promise<Object>} Detailed KPI breakdown with Super Malus info
     */
    async getProfessionistaKPIBreakdown(professionistaId, quarter) {
        const response = await qualityApi.get(`/quality/api/professionista/${professionistaId}/kpi-breakdown`, {
            params: quarter ? { quarter } : {}
        });
        return response.data;
    },
};

// Super Malus badge style helper
export const getSuperMalusBadgeStyle = (percentage) => {
    if (percentage >= 100) return { background: 'linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)', color: '#fff' };
    if (percentage >= 50) return { background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)', color: '#fff' };
    if (percentage >= 25) return { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: '#fff' };
    return { background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff' };
};

// Get current quarter string (e.g. '2025-Q1')
export const getCurrentQuarter = () => {
    const now = new Date();
    const year = now.getFullYear();
    const quarter = Math.floor(now.getMonth() / 3) + 1;
    return `${year}-Q${quarter}`;
};

// Get available quarters (last 4)
export const getAvailableQuarters = () => {
    const quarters = [];
    const now = new Date();
    let year = now.getFullYear();
    let quarter = Math.floor(now.getMonth() / 3) + 1;

    for (let i = 0; i < 4; i++) {
        quarters.push(`${year}-Q${quarter}`);
        quarter--;
        if (quarter === 0) {
            quarter = 4;
            year--;
        }
    }
    return quarters;
};

export default qualityService;

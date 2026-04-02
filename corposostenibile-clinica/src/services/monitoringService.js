import api from './api';

const monitoringService = {
  /**
   * Recupera metriche monitoring dal backend.
   * @param {Object} params - { days: number, include_static: 0|1, limit: number }
   * @returns {Promise<Object>} - { endpoints, errors, period_days, total_requests, ... }
   */
  async getMetrics(params = {}) {
    const { days = 7, include_static = 0, per_day_limit = 300 } = params;
    const response = await api.get('/monitoring/metrics', {
      params: { days, include_static, per_day_limit },
      timeout: 55000, // 55s — sotto il timeout nginx di 60s
    });
    return response.data;
  },

  /**
   * Recupera metriche infrastrutturali live (kubectl + gcloud).
   * @returns {Promise<Object>} - { pods_metrics, nodes_metrics, hpa, deployment, pods_status, cloud_sql }
   */
  async getInfrastructure() {
    const response = await api.get('/monitoring/infrastructure');
    return response.data;
  },
};

export default monitoringService;

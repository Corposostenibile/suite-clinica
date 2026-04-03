import api from './api';

const monitoringService = {
  /**
   * Recupera overview da Cloud Monitoring API (metriche pre-aggregate GCP).
   * Istantaneo (~1-2s), nessun log grezzo.
   */
  async getOverview(params = {}) {
    const { days = 7 } = params;
    const response = await api.get('/monitoring/overview', {
      params: { days },
      timeout: 15000, // 15s max
    });
    return response.data;
  },

  /**
   * Recupera dettaglio per endpoint da Cloud Logging (campione log).
   * Più lento (~5-10s), usato solo per tab "Dettaglio API".
   */
  async getMetrics(params = {}) {
    const { days = 7, include_static = 0 } = params;
    const response = await api.get('/monitoring/metrics', {
      params: { days, include_static },
      timeout: 30000, // 30s
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

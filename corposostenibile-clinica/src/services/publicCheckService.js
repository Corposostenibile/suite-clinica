/**
 * Public Check Service - API per la compilazione dei check pubblici
 * Questi endpoint non richiedono autenticazione
 */

import axios from 'axios';

const api = axios.create({
  baseURL: '/client-checks',
  headers: {
    'Content-Type': 'application/json',
  }
});

const publicCheckService = {
  /**
   * Get check info and client data by token
   * @param {string} checkType - 'weekly', 'dca', or 'minor'
   * @param {string} token - Unique check token
   * @returns {Promise} - { success, check, cliente, professionisti }
   */
  async getCheckInfo(checkType, token) {
    const response = await api.get(`/api/public/${checkType}/${token}`);
    return response.data;
  },

  /**
   * Submit weekly check response
   * @param {string} token - Check token
   * @param {FormData} formData - Form data with all fields and photos
   * @returns {Promise} - { success, message }
   */
  async submitWeeklyCheck(token, formData) {
    const response = await api.post(`/api/public/weekly/${token}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      }
    });
    return response.data;
  },

  /**
   * Submit DCA check response
   * @param {string} token - Check token
   * @param {object} data - Form data
   * @returns {Promise} - { success, message }
   */
  async submitDCACheck(token, data) {
    const response = await api.post(`/api/public/dca/${token}`, data);
    return response.data;
  },

  /**
   * Submit Minor check response
   * @param {string} token - Check token
   * @param {object} data - Form data
   * @returns {Promise} - { success, message }
   */
  async submitMinorCheck(token, data) {
    const response = await api.post(`/api/public/minor/${token}`, data);
    return response.data;
  },
};

export default publicCheckService;

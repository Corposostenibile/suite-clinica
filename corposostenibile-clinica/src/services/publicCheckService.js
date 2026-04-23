/**
 * Public Check Service - API per la compilazione dei check pubblici
 * Questi endpoint non richiedono autenticazione
 */

import axios from 'axios';
import { normalizeMediaUrlsDeep } from '../utils/mediaUrl';

const api = axios.create({
  baseURL: '/api/client-checks',
  headers: {
    'Content-Type': 'application/json',
  }
});

api.interceptors.response.use(
  (response) => {
    if (response?.data) {
      normalizeMediaUrlsDeep(response.data);
    }
    return response;
  },
  (error) => Promise.reject(error)
);

const publicCheckService = {
  /**
   * Get check info and client data by token
   * @param {string} checkType - 'weekly', 'dca', or 'minor'
   * @param {string} token - Unique check token
   * @returns {Promise} - { success, check, cliente, professionisti }
   */
  async getCheckInfo(checkType, token) {
    const endpoint = `/public/${checkType}/${token}`;
    const requestConfig = {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
      },
      validateStatus: (status) => (status >= 200 && status < 300) || status === 304,
    };

    const response = await api.get(endpoint, {
      ...requestConfig,
      params: { _ts: Date.now() },
    });

    if (response.status === 304 || !response.data) {
      const retryResponse = await api.get(endpoint, {
        ...requestConfig,
        params: { _ts: Date.now(), _retry: 1 },
      });
      return retryResponse.data;
    }

    return response.data;
  },

  /**
   * Submit weekly check response
   * @param {string} token - Check token
   * @param {FormData} formData - Form data with all fields and photos
   * @returns {Promise} - { success, message }
   */
  async submitWeeklyCheck(token, formData) {
    const response = await api.post(`/public/weekly/${token}`, formData, {
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
    const response = await api.post(`/public/dca/${token}`, data);
    return response.data;
  },

  /**
   * Submit Minor check response
   * @param {string} token - Check token
   * @param {object} data - Form data
   * @returns {Promise} - { success, message }
   */
  async submitMinorCheck(token, data) {
    const response = await api.post(`/public/minor/${token}`, data);
    return response.data;
  },

  async getWeeklyLightInfo(token) {
    const response = await api.get(`/public/weekly-light/${token}`, {
      params: { _ts: Date.now() },
    });
    return response.data;
  },

  async submitWeeklyLightCheck(token, data) {
    const response = await api.post(`/public/weekly-light/${token}`, data);
    return response.data;
  },

  async getMonthlyCheckInfo(token) {
    const response = await api.get(`/public/monthly/${token}`, {
      params: { _ts: Date.now() },
    });
    return response.data;
  },

  async submitMonthlyCheck(token, data, photos = {}) {
    const hasPhotos = Object.values(photos).some(Boolean);
    if (hasPhotos) {
      const formData = new FormData();
      formData.append('responses', JSON.stringify(data));
      if (photos.photo_front) formData.append('photo_front', photos.photo_front);
      if (photos.photo_side) formData.append('photo_side', photos.photo_side);
      if (photos.photo_back) formData.append('photo_back', photos.photo_back);
      const response = await api.post(`/public/monthly/${token}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    }
    const response = await api.post(`/public/monthly/${token}`, data);
    return response.data;
  },
};

export default publicCheckService;

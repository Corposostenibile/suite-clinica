import axios from 'axios';
import { normalizeMediaUrlsDeep } from '../utils/mediaUrl';

// Helper to get cookie by name
const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
};

// Base API configuration
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for session cookies
});

// Request interceptor to add CSRF token
api.interceptors.request.use((config) => {
  // Try meta tag first, then cookie
  let csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

  if (!csrfToken) {
    // Flask-WTF cookie names
    csrfToken = getCookie('csrf_token') || getCookie('csrftoken') || getCookie('XSRF-TOKEN');
  }

  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
    config.headers['X-CSRF-Token'] = csrfToken; // Some backends use this header
  }

  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    if (response?.data) {
      normalizeMediaUrlsDeep(response.data);
    }
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login if unauthorized
      window.location.href = `${import.meta.env.BASE_URL}auth/login`;
    }
    return Promise.reject(error);
  }
);

export default api;

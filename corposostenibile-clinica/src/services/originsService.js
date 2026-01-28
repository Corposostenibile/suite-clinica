
import api from './api';

const ORIGINS_API_BASE = '/v1/customers/origins';

const originsService = {
  /**
   * Ottiene la lista di tutte le origini
   */
  getOrigins: async () => {
    try {
      const response = await api.get(ORIGINS_API_BASE);
      // Il backend restituisce direttamente l'array, non un oggetto con mapping
      return { success: true, origins: response.data || [] };
    } catch (error) {
      console.error('Error fetching origins:', error);
      return { 
        success: false, 
        message: error.response?.data?.error || 'Errore nel caricamento delle origini' 
      };
    }
  },

  /**
   * Crea una nuova origine
   * @param {Object} data { name: string, active: boolean }
   */
  createOrigin: async (data) => {
    try {
      const response = await api.post(ORIGINS_API_BASE, data);
      return { success: true, origin: response.data };
    } catch (error) {
      console.error('Error creating origin:', error);
      return { 
        success: false, 
        message: error.response?.data?.error || 'Errore nella creazione dell\'origine' 
      };
    }
  },

  /**
   * Aggiorna un'origine esistente
   * @param {number} id 
   * @param {Object} data 
   */
  updateOrigin: async (id, data) => {
    try {
      const response = await api.put(`${ORIGINS_API_BASE}/${id}`, data);
      return { success: true, origin: response.data };
    } catch (error) {
      console.error('Error updating origin:', error);
      return { 
        success: false, 
        message: error.response?.data?.error || 'Errore nell\'aggiornamento dell\'origine' 
      };
    }
  },

  /**
   * Elimina un'origine
   * @param {number} id 
   */
  deleteOrigin: async (id) => {
    try {
      await api.delete(`${ORIGINS_API_BASE}/${id}`);
      return { success: true };
    } catch (error) {
      console.error('Error deleting origin:', error);
      return { 
        success: false, 
        message: error.response?.data?.error || 'Errore nell\'eliminazione dell\'origine' 
      };
    }
  }
};

export default originsService;

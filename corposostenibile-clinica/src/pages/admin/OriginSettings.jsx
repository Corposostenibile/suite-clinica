import React, { useState, useEffect } from "react";
import originsService from "../../services/originsService";
import Swal from "sweetalert2";
import './OriginSettings.css';

const OriginSettings = () => {
  const [origins, setOrigins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingOrigin, setEditingOrigin] = useState(null);
  const [formData, setFormData] = useState({ name: "", active: true });

  useEffect(() => {
    loadOrigins();
  }, []);

  const loadOrigins = async () => {
    setLoading(true);
    const result = await originsService.getOrigins();
    if (result.success) {
      setOrigins(result.origins);
    }
    setLoading(false);
  };

  const handleShowModal = (origin = null) => {
    if (origin) {
      setEditingOrigin(origin);
      setFormData({ name: origin.name, active: origin.active });
    } else {
      setEditingOrigin(null);
      setFormData({ name: "", active: true });
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingOrigin(null);
  };

  const handleSave = async () => {
    if (!formData.name) {
      Swal.fire("Errore", "Il nome è obbligatorio", "error");
      return;
    }

    let result;
    if (editingOrigin) {
      result = await originsService.updateOrigin(editingOrigin.id, formData);
    } else {
      result = await originsService.createOrigin(formData);
    }

    if (result.success) {
      Swal.fire("Successo", "Salvataggio completato", "success");
      loadOrigins();
      handleCloseModal();
    } else {
      Swal.fire("Errore", result.message, "error");
    }
  };

  const handleDelete = async (id) => {
    const confirm = await Swal.fire({
      title: "Sei sicuro?",
      text: "Questa azione è irreversibile.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Sì, elimina",
      cancelButtonText: "Annulla",
    });

    if (confirm.isConfirmed) {
      const result = await originsService.deleteOrigin(id);
      if (result.success) {
        Swal.fire("Eliminato", "Origine eliminata", "success");
        loadOrigins();
      } else {
        Swal.fire("Errore", result.message, "error");
      }
    }
  };

  return (
    <div className="org-page">
      {/* Header */}
      <div className="org-header">
        <div>
          <h4>Gestione Origini</h4>
          <p>Configura le origini di provenienza dei clienti</p>
        </div>
        <div className="org-header-actions">
          <button className="org-add-btn" onClick={() => handleShowModal(null)}>
            <i className="ri-add-line"></i> Nuova Origine
          </button>
        </div>
      </div>

      {/* Table Card */}
      <div className="org-card">
        {loading ? (
          <div className="org-loading">
            <div className="org-spinner"></div>
            <p>Caricamento origini...</p>
          </div>
        ) : origins.length === 0 ? (
          <div className="org-empty">
            <div className="org-empty-icon">
              <i className="ri-compass-3-line"></i>
            </div>
            <h5>Nessuna origine trovata</h5>
            <p>Crea la prima origine per iniziare a tracciare la provenienza dei clienti.</p>
          </div>
        ) : (
          <div className="org-table-wrap">
            <table className="org-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nome</th>
                  <th>Stato</th>
                  <th style={{ textAlign: 'right' }}>Azioni</th>
                </tr>
              </thead>
              <tbody>
                {origins.map((origin) => (
                  <tr key={origin.id}>
                    <td>
                      <span className="org-id-badge">#{origin.id}</span>
                    </td>
                    <td>
                      <div className="org-name-cell">
                        <div className="org-name-icon">
                          <i className="ri-compass-3-line"></i>
                        </div>
                        <span className="org-name-text">{origin.name}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`org-status-badge ${origin.active ? 'active' : 'inactive'}`}>
                        <i className={origin.active ? 'ri-checkbox-circle-fill' : 'ri-close-circle-fill'}></i>
                        {origin.active ? "Attivo" : "Inattivo"}
                      </span>
                    </td>
                    <td>
                      <div className="org-actions" style={{ justifyContent: 'flex-end' }}>
                        <button
                          className="org-action-btn edit"
                          title="Modifica"
                          onClick={() => handleShowModal(origin)}
                        >
                          <i className="ri-pencil-line"></i>
                        </button>
                        <button
                          className="org-action-btn delete"
                          title="Elimina"
                          onClick={() => handleDelete(origin.id)}
                        >
                          <i className="ri-delete-bin-line"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="org-modal-overlay" onClick={handleCloseModal}>
          <div className="org-modal" onClick={(e) => e.stopPropagation()}>
            <div className="org-modal-header">
              <h5 className="org-modal-title">
                {editingOrigin ? "Modifica Origine" : "Nuova Origine"}
              </h5>
              <button className="org-modal-close" onClick={handleCloseModal}>
                <i className="ri-close-line"></i>
              </button>
            </div>
            <div className="org-modal-body">
              <div className="org-field">
                <label className="org-label">Nome Identificativo</label>
                <input
                  type="text"
                  className="org-input"
                  placeholder="Es. influencer_chiara"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
                <div className="org-hint">Nome univoco usato per filtrare (es. nei link)</div>
              </div>
              <div className="org-toggle-wrap">
                <label className="org-toggle">
                  <input
                    type="checkbox"
                    checked={formData.active}
                    onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                  />
                  <span className="org-toggle-slider"></span>
                </label>
                <span className="org-toggle-label">Attivo</span>
              </div>
            </div>
            <div className="org-modal-footer">
              <button className="org-btn-cancel" onClick={handleCloseModal}>
                Annulla
              </button>
              <button className="org-btn-save" onClick={handleSave}>
                <i className="ri-save-line"></i> Salva
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OriginSettings;

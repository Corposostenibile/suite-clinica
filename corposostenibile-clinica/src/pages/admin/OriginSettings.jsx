import React, { useState, useEffect } from "react";
import { Modal, Button, Form } from "react-bootstrap";
import originsService from "../../services/originsService";
import Swal from "sweetalert2";

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

  const handlSave = async () => {
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
    <div className="card">
        <div className="card-header d-flex justify-content-between align-items-center">
            <h4 className="card-title">Gestione Origini</h4>
            <Button variant="primary" onClick={() => handleShowModal(null)}>
                <i className="fa fa-plus me-2"></i> Nuova Origine
            </Button>
        </div>
        <div className="card-body">
            {loading ? (
                <div className="text-center">Caricamento...</div>
            ) : (
                <div className="table-responsive">
                    <table className="table table-responsive-md">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Nome</th>
                                <th>Stato</th>
                                <th>Azioni</th>
                            </tr>
                        </thead>
                        <tbody>
                            {origins.map((origin) => (
                                <tr key={origin.id}>
                                    <td>{origin.id}</td>
                                    <td>{origin.name}</td>
                                    <td>
                                        <span className={`badge badge-${origin.active ? "success" : "danger"}`}>
                                            {origin.active ? "Attivo" : "Inattivo"}
                                        </span>
                                    </td>
                                    <td>
                                        <div className="d-flex action-button">
                                            <Button variant="info" size="sm" className="me-2" onClick={() => handleShowModal(origin)}>
                                                <i className="fa fa-pencil"></i>
                                            </Button>
                                            <Button variant="danger" size="sm" onClick={() => handleDelete(origin.id)}>
                                                <i className="fa fa-trash"></i>
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {origins.length === 0 && (
                                <tr>
                                    <td colSpan="4" className="text-center">Nessuna origine trovata.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            )}
        </div>

        <Modal show={showModal} onHide={handleCloseModal}>
            <Modal.Header closeButton>
                <Modal.Title>{editingOrigin ? "Modifica Origine" : "Nuova Origine"}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form>
                    <Form.Group className="mb-3">
                        <Form.Label>Nome Identificativo</Form.Label>
                        <Form.Control 
                            type="text" 
                            placeholder="Es. influencer_chiara" 
                            value={formData.name}
                            onChange={(e) => setFormData({...formData, name: e.target.value})}
                        />
                         <Form.Text className="text-muted">
                            Nome univoco usato per filtrare (es. nei link)
                        </Form.Text>
                    </Form.Group>
                    <Form.Group className="mb-3">
                        <Form.Check 
                            type="checkbox" 
                            label="Attivo" 
                            checked={formData.active}
                            onChange={(e) => setFormData({...formData, active: e.target.checked})}
                        />
                    </Form.Group>
                </Form>
            </Modal.Body>
            <Modal.Footer>
                <Button variant="secondary" onClick={handleCloseModal}>
                    Annulla
                </Button>
                <Button variant="primary" onClick={handlSave}>
                    Salva
                </Button>
            </Modal.Footer>
        </Modal>
    </div>
  );
};

export default OriginSettings;

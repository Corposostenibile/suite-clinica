import { useState, useEffect, useCallback, useRef } from 'react';
import sopService from '../../services/sopService';

const statusBadge = (status) => {
  switch (status) {
    case 'ready':
      return <span className="badge bg-success">Pronto</span>;
    case 'processing':
      return <span className="badge bg-warning text-dark">Elaborazione...</span>;
    case 'error':
      return <span className="badge bg-danger">Errore</span>;
    default:
      return <span className="badge bg-secondary">{status}</span>;
  }
};

const formatFileSize = (bytes) => {
  if (!bytes) return '-';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDate = (isoString) => {
  if (!isoString) return '-';
  const d = new Date(isoString);
  return d.toLocaleDateString('it-IT', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

export default function SOPDocuments() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const fileInputRef = useRef(null);

  const loadDocuments = useCallback(async () => {
    try {
      const data = await sopService.getDocuments();
      setDocuments(data.documents || []);
    } catch {
      setError('Errore nel caricamento dei documenti');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
    // Poll for status updates every 5 seconds
    const interval = setInterval(loadDocuments, 5000);
    return () => clearInterval(interval);
  }, [loadDocuments]);

  const handleUpload = async (files) => {
    if (!files || files.length === 0) return;

    setUploading(true);
    setError('');
    setSuccess('');

    for (const file of files) {
      try {
        await sopService.uploadDocument(file);
        setSuccess(`"${file.name}" caricato con successo. Elaborazione in corso...`);
      } catch (err) {
        setError(err.response?.data?.error || `Errore nel caricamento di "${file.name}"`);
      }
    }
    setUploading(false);
    loadDocuments();
  };

  const handleDelete = async (docId) => {
    try {
      await sopService.deleteDocument(docId);
      setSuccess('Documento eliminato');
      setDeleteConfirm(null);
      loadDocuments();
    } catch {
      setError('Errore nell\'eliminazione del documento');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleUpload(e.dataTransfer.files);
  };

  return (
    <div className="container-fluid">
      <div className="row page-titles">
        <ol className="breadcrumb">
          <li className="breadcrumb-item"><a href="#">SOP Chatbot</a></li>
          <li className="breadcrumb-item active">Documenti</li>
        </ol>
      </div>

      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-header d-flex justify-content-between align-items-center">
              <h4 className="card-title mb-0">Documenti SOP</h4>
              <button
                className="btn btn-primary"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                <i className="fas fa-upload me-2"></i>
                {uploading ? 'Caricamento...' : 'Carica documento'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc"
                multiple
                style={{ display: 'none' }}
                onChange={(e) => handleUpload(e.target.files)}
              />
            </div>
            <div className="card-body">
              {error && (
                <div className="alert alert-danger alert-dismissible fade show" role="alert">
                  {error}
                  <button type="button" className="btn-close" onClick={() => setError('')}></button>
                </div>
              )}
              {success && (
                <div className="alert alert-success alert-dismissible fade show" role="alert">
                  {success}
                  <button type="button" className="btn-close" onClick={() => setSuccess('')}></button>
                </div>
              )}

              {/* Drop zone */}
              <div
                className={`border border-2 border-dashed rounded p-4 text-center mb-4 ${dragOver ? 'border-primary bg-light' : 'border-secondary'}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                style={{ cursor: 'pointer', transition: 'all 0.2s' }}
                onClick={() => fileInputRef.current?.click()}
              >
                <i className="fas fa-cloud-upload-alt fa-2x mb-2 text-muted"></i>
                <p className="mb-0 text-muted">
                  Trascina qui i file PDF o DOCX, oppure clicca per selezionarli
                </p>
              </div>

              {/* Documents table */}
              {loading ? (
                <div className="text-center py-4">
                  <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Caricamento...</span>
                  </div>
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center py-4 text-muted">
                  <i className="fas fa-folder-open fa-3x mb-3"></i>
                  <p>Nessun documento SOP caricato</p>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover">
                    <thead>
                      <tr>
                        <th>Nome file</th>
                        <th>Dimensione</th>
                        <th>Data caricamento</th>
                        <th>Status</th>
                        <th>Chunks</th>
                        <th>Azioni</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((doc) => (
                        <tr key={doc.id}>
                          <td>
                            <i className={`fas ${doc.mime_type?.includes('pdf') ? 'fa-file-pdf text-danger' : 'fa-file-word text-primary'} me-2`}></i>
                            {doc.filename}
                          </td>
                          <td>{formatFileSize(doc.file_size)}</td>
                          <td>{formatDate(doc.created_at)}</td>
                          <td>
                            {statusBadge(doc.status)}
                            {doc.error_message && (
                              <small className="d-block text-danger mt-1">{doc.error_message}</small>
                            )}
                          </td>
                          <td>{doc.chunks_count || '-'}</td>
                          <td>
                            {deleteConfirm === doc.id ? (
                              <div className="btn-group btn-group-sm">
                                <button
                                  className="btn btn-danger"
                                  onClick={() => handleDelete(doc.id)}
                                >
                                  Conferma
                                </button>
                                <button
                                  className="btn btn-secondary"
                                  onClick={() => setDeleteConfirm(null)}
                                >
                                  Annulla
                                </button>
                              </div>
                            ) : (
                              <button
                                className="btn btn-outline-danger btn-sm"
                                onClick={() => setDeleteConfirm(doc.id)}
                                title="Elimina documento"
                              >
                                <i className="fas fa-trash"></i>
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

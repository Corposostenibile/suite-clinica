import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import clientiService from '../../services/clientiService';

function DiarioModal({ show, onClose, cliente, serviceType }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newContent, setNewContent] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (show && cliente) {
      fetchDiario();
    } else {
      setEntries([]);
      setNewContent('');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [show, cliente]);

  const fetchDiario = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await clientiService.getDiaryEntries(cliente.cliente_id || cliente.clienteId, serviceType);
      setEntries(data.entries || []);
    } catch (err) {
      console.error('Error fetching diary:', err);
      setError('Errore nel caricamento del diario. Riprova.');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!newContent.trim()) return;
    setSaving(true);
    try {
      await clientiService.createDiaryEntry(cliente.cliente_id || cliente.clienteId, serviceType, newContent);
      setNewContent('');
      await fetchDiario();
    } catch (err) {
      console.error('Error adding entry:', err);
      alert('Errore nel salvataggio della nota');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (entryId) => {
    if (!window.confirm('Sei sicuro di voler eliminare questa nota?')) return;
    try {
      await clientiService.deleteDiaryEntry(cliente.cliente_id || cliente.clienteId, serviceType, entryId);
      await fetchDiario();
    } catch (err) {
      console.error('Error deleting entry:', err);
      alert('Errore eliminazione nota');
    }
  };

  if (!show || !cliente) return null;

  return createPortal(
    <div className="cl-modal-overlay" onClick={onClose}>
      <div className="cl-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px', width: '100%' }}>
        <div className="cl-modal-header">
          <h5 className="cl-modal-title">
            <i className="ri-book-2-line align-middle me-2"></i>
            Diario - {cliente.nome_cognome || cliente.nomeCognome}
          </h5>
          <button className="cl-modal-close" onClick={onClose}>&times;</button>
        </div>
        <div className="cl-modal-body" style={{ maxHeight: '60vh', overflowY: 'auto', background: '#f8fafc', padding: '16px' }}>
          
          <div style={{ marginBottom: '20px', background: 'white', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <textarea
              className="form-control"
              rows="3"
              placeholder="Aggiungi una nuova nota al diario..."
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              style={{ fontSize: '14px', resize: 'vertical' }}
            />
            <div style={{ marginTop: '8px', textAlign: 'right' }}>
              <button 
                className="cl-modal-btn-apply"
                style={{ padding: '6px 12px', fontSize: '13px', width: 'auto' }}
                onClick={handleAdd}
                disabled={saving || !newContent.trim()}
              >
                {saving ? <><i className="ri-loader-4-line"></i> Salvando...</> : <><i className="ri-add-line"></i> Aggiungi Nota</>}
              </button>
            </div>
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <div className="spinner-border text-primary" role="status"></div>
            </div>
          ) : error ? (
            <div className="alert alert-danger">{error}</div>
          ) : entries.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#64748b', padding: '20px' }}>
              Nessuna nota nel diario.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {entries.map(entry => (
                <div key={entry.id} style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '12px', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
                    <div style={{ fontSize: '12px', color: '#64748b', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ background: '#eff6ff', color: '#3b82f6', padding: '2px 6px', borderRadius: '4px', fontWeight: 500 }}>
                        <i className="ri-calendar-line me-1"></i>
                        {entry.entry_date_display || entry.entry_date}
                        {entry.created_at && (
                          <span className="ms-1 opacity-75">
                            ({entry.created_at.split(' ')[1]})
                          </span>
                        )}
                      </span>
                      <span>
                        <i className="ri-user-line me-1"></i>
                        {entry.author}
                      </span>
                    </div>
                    <button 
                      onClick={() => handleDelete(entry.id)}
                      style={{ background: 'none', border: 'none', color: '#ef4444', fontSize: '16px', padding: '4px', cursor: 'pointer', opacity: 0.8 }}
                      title="Elimina nota"
                    >
                      <i className="ri-delete-bin-line"></i>
                    </button>
                  </div>
                  <div style={{ fontSize: '14px', color: '#334155', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
                    {entry.content}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}

export default DiarioModal;

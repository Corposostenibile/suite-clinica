import { useState, useEffect, useCallback } from 'react';
import newsService from '../../services/newsService';

const formatDate = (iso) => {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('it-IT', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
};

const emptyForm = {
  title: '',
  summary: '',
  content: '',
  is_published: true,
  is_pinned: false,
  published_at: new Date().toISOString().slice(0, 16),
};

export default function NewsManager() {
  const [newsList, setNewsList] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  // Delete confirm
  const [deleteId, setDeleteId] = useState(null);

  const loadNews = useCallback(async () => {
    setLoading(true);
    try {
      const data = await newsService.listAll();
      if (data.success) setNewsList(data.news);
    } catch (err) {
      console.error('Errore caricamento news:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNews();
  }, [loadNews]);

  const openCreate = () => {
    setEditingId(null);
    setForm({ ...emptyForm, published_at: new Date().toISOString().slice(0, 16) });
    setShowModal(true);
  };

  const openEdit = (item) => {
    setEditingId(item.id);
    setForm({
      title: item.title || '',
      summary: item.summary || '',
      content: item.content || '',
      is_published: item.is_published ?? true,
      is_pinned: item.is_pinned ?? false,
      published_at: item.published_at ? item.published_at.slice(0, 16) : '',
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.title.trim() || !form.content.trim()) return;
    setSaving(true);
    try {
      if (editingId) {
        await newsService.update(editingId, form);
      } else {
        await newsService.create(form);
      }
      setShowModal(false);
      loadNews();
    } catch (err) {
      console.error('Errore salvataggio:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await newsService.remove(deleteId);
      setDeleteId(null);
      loadNews();
    } catch (err) {
      console.error('Errore eliminazione:', err);
    }
  };

  // ─── Styles ──────────────────────────────────────────────────────
  const pageStyle = { padding: '1.5rem' };
  const headerStyle = {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem',
  };
  const titleStyle = { margin: 0, fontWeight: 700, fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' };
  const btnPrimary = {
    background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8,
    padding: '0.6rem 1.25rem', fontWeight: 600, cursor: 'pointer', fontSize: '0.9rem',
    display: 'flex', alignItems: 'center', gap: '0.5rem',
  };
  const tableStyle = {
    width: '100%', borderCollapse: 'separate', borderSpacing: 0,
    background: '#fff', borderRadius: 12, overflow: 'hidden',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  };
  const thStyle = {
    padding: '0.75rem 1rem', textAlign: 'left', fontWeight: 600, fontSize: '0.8rem',
    color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px',
    borderBottom: '2px solid #e2e8f0', background: '#f8fafc',
  };
  const tdStyle = {
    padding: '0.75rem 1rem', borderBottom: '1px solid #f1f5f9', fontSize: '0.9rem',
  };
  const badgeStyle = (bg, color) => ({
    display: 'inline-block', padding: '2px 8px', borderRadius: 999,
    fontSize: '0.75rem', fontWeight: 600, background: bg, color,
  });
  const actionBtn = {
    background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem 0.5rem',
    borderRadius: 6, fontSize: '1rem',
  };

  // ─── Modal overlay ───────────────────────────────────────────────
  const overlayStyle = {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 1050,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  };
  const modalStyle = {
    background: '#fff', borderRadius: 16, width: '100%', maxWidth: 640,
    maxHeight: '90vh', overflow: 'auto', padding: '2rem', position: 'relative',
  };
  const labelStyle = { display: 'block', fontWeight: 600, marginBottom: '0.25rem', fontSize: '0.85rem', color: '#334155' };
  const inputStyle = {
    width: '100%', padding: '0.5rem 0.75rem', border: '1px solid #d1d5db',
    borderRadius: 8, fontSize: '0.9rem', marginBottom: '1rem',
  };
  const textareaStyle = { ...inputStyle, minHeight: 120, resize: 'vertical', fontFamily: 'inherit' };
  const checkRow = { display: 'flex', gap: '2rem', marginBottom: '1rem' };
  const checkLabel = { display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.9rem' };

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <h2 style={titleStyle}>📰 Gestione Novità</h2>
        <button style={btnPrimary} onClick={openCreate}>
          <i className="fas fa-plus" /> Nuova Novità
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <div className="spinner-border text-primary" role="status" />
        </div>
      ) : newsList.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
          <p>Nessuna novità creata.</p>
        </div>
      ) : (
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Titolo</th>
              <th style={thStyle}>Stato</th>
              <th style={thStyle}>Data</th>
              <th style={thStyle}>Pinned</th>
              <th style={thStyle}>Views</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Azioni</th>
            </tr>
          </thead>
          <tbody>
            {newsList.map((item) => (
              <tr key={item.id} style={{ transition: 'background 0.15s' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#f8fafc')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = '')}
              >
                <td style={tdStyle}>
                  <span style={{ fontWeight: 600 }}>{item.title}</span>
                  {item.summary && (
                    <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: 2 }}>{item.summary}</div>
                  )}
                </td>
                <td style={tdStyle}>
                  {item.is_published
                    ? <span style={badgeStyle('#dcfce7', '#16a34a')}>Pubblicata</span>
                    : <span style={badgeStyle('#f1f5f9', '#64748b')}>Bozza</span>
                  }
                </td>
                <td style={tdStyle}>{formatDate(item.published_at)}</td>
                <td style={tdStyle}>
                  {item.is_pinned && <span style={badgeStyle('#fef3c7', '#b45309')}>📌 Pinned</span>}
                </td>
                <td style={tdStyle}>{item.total_views ?? 0}</td>
                <td style={{ ...tdStyle, textAlign: 'right', whiteSpace: 'nowrap' }}>
                  <button style={actionBtn} title="Modifica" onClick={() => openEdit(item)}>
                    ✏️
                  </button>
                  <button style={actionBtn} title="Elimina" onClick={() => setDeleteId(item.id)}>
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* ─── Create / Edit Modal ─────────────────────────────────── */}
      {showModal && (
        <div style={overlayStyle} onClick={() => setShowModal(false)}>
          <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 1.5rem', fontWeight: 700 }}>
              {editingId ? '✏️ Modifica Novità' : '📝 Nuova Novità'}
            </h3>

            <label style={labelStyle}>Titolo *</label>
            <input
              style={inputStyle}
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="Es: Lancio ufficiale della Suite Clinica!"
            />

            <label style={labelStyle}>Sommario</label>
            <input
              style={inputStyle}
              value={form.summary}
              onChange={(e) => setForm({ ...form, summary: e.target.value })}
              placeholder="Breve descrizione (opzionale)"
            />

            <label style={labelStyle}>Contenuto *</label>
            <textarea
              style={textareaStyle}
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
              placeholder="Testo completo della novità (supporta HTML)"
            />

            <label style={labelStyle}>Data pubblicazione</label>
            <input
              type="datetime-local"
              style={inputStyle}
              value={form.published_at}
              onChange={(e) => setForm({ ...form, published_at: e.target.value })}
            />

            <div style={checkRow}>
              <label style={checkLabel}>
                <input
                  type="checkbox"
                  checked={form.is_published}
                  onChange={(e) => setForm({ ...form, is_published: e.target.checked })}
                />
                Pubblicata
              </label>
              <label style={checkLabel}>
                <input
                  type="checkbox"
                  checked={form.is_pinned}
                  onChange={(e) => setForm({ ...form, is_pinned: e.target.checked })}
                />
                📌 In evidenza
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
              <button
                style={{ ...btnPrimary, background: '#e2e8f0', color: '#334155' }}
                onClick={() => setShowModal(false)}
              >
                Annulla
              </button>
              <button
                style={{ ...btnPrimary, opacity: saving ? 0.6 : 1 }}
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Salvataggio...' : editingId ? 'Salva Modifiche' : 'Crea Novità'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Delete Confirm Modal ────────────────────────────────── */}
      {deleteId && (
        <div style={overlayStyle} onClick={() => setDeleteId(null)}>
          <div style={{ ...modalStyle, maxWidth: 420, textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 1rem', fontWeight: 700 }}>🗑️ Conferma eliminazione</h3>
            <p style={{ color: '#64748b', marginBottom: '1.5rem' }}>
              Sei sicuro di voler eliminare questa novità? L'azione non è reversibile.
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem' }}>
              <button
                style={{ ...btnPrimary, background: '#e2e8f0', color: '#334155' }}
                onClick={() => setDeleteId(null)}
              >
                Annulla
              </button>
              <button
                style={{ ...btnPrimary, background: '#ef4444' }}
                onClick={handleDelete}
              >
                Elimina
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

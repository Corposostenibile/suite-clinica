import { useEffect, useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import adminPushService from '../../services/adminPushService';

function AdminPushNotifications() {
  const { user } = useAuth();
  const isAdmin = Boolean(user?.is_admin || user?.role === 'admin');

  const [professionisti, setProfessionisti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [feedback, setFeedback] = useState({ type: '', message: '' });
  const [form, setForm] = useState({
    userId: '',
    title: '',
    body: '',
    url: '/appointment-setting',
  });

  const selectedUser = useMemo(
    () => professionisti.find((item) => String(item.id) === String(form.userId)),
    [professionisti, form.userId],
  );

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setFeedback({ type: '', message: '' });
      try {
        const items = await adminPushService.listProfessionisti();
        setProfessionisti(items);
      } catch (error) {
        setFeedback({ type: 'danger', message: error?.response?.data?.message || 'Errore caricamento professionisti.' });
      } finally {
        setLoading(false);
      }
    };

    if (isAdmin) {
      loadData();
    }
  }, [isAdmin]);

  if (!isAdmin) {
    return <Navigate to="/appointment-setting" replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSending(true);
    setFeedback({ type: '', message: '' });
    try {
      const result = await adminPushService.sendPush({
        userId: Number(form.userId),
        title: form.title.trim(),
        body: form.body.trim(),
        url: form.url.trim() || '/',
      });
      const sent = Number(result?.sent || 0);
      if (sent > 0) {
        setFeedback({ type: 'success', message: `Notifica inviata con successo (${sent} device).` });
      } else {
        setFeedback({ type: 'warning', message: 'Nessuna subscription attiva per questo professionista.' });
      }
      setForm((prev) => ({ ...prev, title: '', body: '' }));
    } catch (error) {
      setFeedback({ type: 'danger', message: error?.response?.data?.message || error?.response?.data || 'Invio notifica fallito.' });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="row">
      <div className="col-xl-8 col-lg-10">
        <div className="card">
          <div className="card-header border-0 pb-0">
            <h4 className="card-title mb-0">Invia Notifica Push Manuale</h4>
          </div>
          <div className="card-body">
            {feedback.message && (
              <div className={`alert alert-${feedback.type} py-2`} role="alert">
                {feedback.message}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label">Professionista</label>
                <select
                  className="form-select"
                  value={form.userId}
                  onChange={(e) => setForm((prev) => ({ ...prev, userId: e.target.value }))}
                  required
                  disabled={loading || sending}
                >
                  <option value="">{loading ? 'Caricamento...' : 'Seleziona professionista'}</option>
                  {professionisti.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.full_name} ({item.email})
                    </option>
                  ))}
                </select>
              </div>

              <div className="mb-3">
                <label className="form-label">Titolo</label>
                <input
                  className="form-control"
                  value={form.title}
                  onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                  maxLength={120}
                  required
                  disabled={sending}
                />
              </div>

              <div className="mb-3">
                <label className="form-label">Messaggio</label>
                <textarea
                  className="form-control"
                  rows={4}
                  value={form.body}
                  onChange={(e) => setForm((prev) => ({ ...prev, body: e.target.value }))}
                  maxLength={300}
                  required
                  disabled={sending}
                />
              </div>

              <div className="mb-4">
                <label className="form-label">URL apertura (opzionale)</label>
                <input
                  className="form-control"
                  value={form.url}
                  onChange={(e) => setForm((prev) => ({ ...prev, url: e.target.value }))}
                  placeholder="/task oppure https://..."
                  disabled={sending}
                />
                {selectedUser && (
                  <small className="text-muted d-block mt-2">
                    Destinatario: {selectedUser.full_name} - {selectedUser.role}
                  </small>
                )}
              </div>

              <button type="submit" className="btn btn-primary" disabled={sending || loading || !form.userId}>
                {sending ? 'Invio in corso...' : 'Invia Notifica'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AdminPushNotifications;

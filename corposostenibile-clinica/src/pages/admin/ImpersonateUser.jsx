import { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import authService from '../../services/authService';
import defaultAvatar from '../../images/profile/pic1.jpg';
import './ImpersonateUser.css';

const ROLE_LABELS = {
  admin: 'Admin',
  cco: 'CCO',
  coordinatore: 'Coordinatore',
  team_leader: 'Team Leader',
  health_manager: 'Health Manager',
  professionista: 'Professionista',
  team_esterno: 'Team Esterno',
  consulente: 'Consulente',
  influencer: 'Influencer',
};

function ImpersonateUser() {
  const { user } = useOutletContext();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [busyId, setBusyId] = useState(null);

  const isAdmin = user?.is_admin || user?.role === 'admin';

  useEffect(() => {
    if (isAdmin) loadUsers();
  }, [isAdmin]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError('');
      const result = await authService.getImpersonateUsers();
      if (result.success) {
        setUsers(result.users);
      } else {
        setError(result.error || 'Errore nel caricamento utenti.');
      }
    } catch (err) {
      console.error('Impersonate loadUsers error:', err?.response?.status, err?.response?.data || err.message);
      setError(err?.response?.data?.error || 'Errore nel caricamento utenti.');
    } finally {
      setLoading(false);
    }
  };

  if (!isAdmin) {
    return (
      <div className="imp-unauthorized">
        <i className="ri-lock-line"></i>
        Accesso non autorizzato. Solo gli admin possono accedere a questa pagina.
      </div>
    );
  }

  const handleImpersonate = async (userId) => {
    try {
      setBusyId(userId);
      setError('');
      const result = await authService.impersonateUser(userId);
      if (result.success) {
        window.location.href = '/welcome';
      } else {
        setError(result.error || 'Errore durante l\'impersonazione.');
        setBusyId(null);
      }
    } catch (err) {
      setError('Errore durante l\'impersonazione.');
      setBusyId(null);
    }
  };

  const term = search.toLowerCase().trim();
  const filtered = term
    ? users.filter(u =>
        (u.full_name || '').toLowerCase().includes(term) ||
        (u.email || '').toLowerCase().includes(term)
      )
    : users;

  return (
    <div className="container-fluid">
      <div className="imp-header">
        <div>
          <h4><i className="ri-user-shared-line"></i> Accedi come</h4>
          <div className="imp-header-sub">
            Accedi alla piattaforma come un altro utente per vedere la loro visualizzazione.
          </div>
        </div>
      </div>

      {error && <div className="imp-error">{error}</div>}

      <div className="card" style={{ border: 'none', borderRadius: '16px', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
        <div className="card-body" style={{ padding: '24px' }}>
          <div className="imp-search">
            <i className="ri-search-line"></i>
            <input
              type="text"
              placeholder="Cerca per nome o email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {loading ? (
            <div className="imp-loading">Caricamento utenti...</div>
          ) : filtered.length === 0 ? (
            <div className="imp-empty">
              <i className="ri-user-search-line"></i>
              {term ? 'Nessun utente trovato per la ricerca.' : 'Nessun utente disponibile.'}
            </div>
          ) : (
            <>
              <div className="imp-count">{filtered.length} utent{filtered.length === 1 ? 'e' : 'i'}</div>
              <div className="imp-list">
                {filtered.map((u) => (
                  <div className="imp-user-card" key={u.id}>
                    <div className="imp-user-info">
                      <img
                        src={u.avatar_path || defaultAvatar}
                        alt=""
                        className="imp-user-avatar"
                      />
                      <div>
                        <div className="imp-user-name">{u.full_name}</div>
                        <div className="imp-user-meta">
                          <span className="imp-role-badge">
                            {ROLE_LABELS[u.role] || u.role || '—'}
                          </span>
                          {u.specialty && <span>{u.specialty}</span>}
                          {u.specialty && u.email && <span> · </span>}
                          <span>{u.email}</span>
                        </div>
                      </div>
                    </div>
                    <button
                      className="imp-btn"
                      onClick={() => handleImpersonate(u.id)}
                      disabled={busyId !== null}
                    >
                      {busyId === u.id ? 'Accesso...' : 'Accedi come'}
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ImpersonateUser;

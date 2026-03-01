import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import trialUserService from '../../services/trialUserService';
import './TrialUsersList.css';

const STAGE_BADGE_CLASS = {
  1: 'tu-badge-stage1',
  2: 'tu-badge-stage2',
  3: 'tu-badge-stage3',
};

const STAT_STYLES = {
  total:   { color: '#25B36A', bg: 'rgba(37, 179, 106, 0.1)' },
  stage_1: { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' },
  stage_2: { color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' },
  stage_3: { color: '#22c55e', bg: 'rgba(34, 197, 94, 0.1)' },
};

function TrialUsersList() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [trialUsers, setTrialUsers] = useState([]);
  const [stats, setStats] = useState({ total: 0, stage_1: 0, stage_2: 0, stage_3: 0 });
  const [error, setError] = useState(null);

  const [filters, setFilters] = useState({ search: '', stage: '' });

  const fetchData = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const result = await trialUserService.getAll();
      if (result.success) {
        setTrialUsers(result.trial_users || []);
        setStats(result.stats || { total: 0, stage_1: 0, stage_2: 0, stage_3: 0 });
      } else {
        setError(result.error || 'Errore nel caricamento dei dati');
      }
    } catch (err) {
      console.error('Error fetching trial users:', err);
      setError(err?.response?.data?.error || err?.message || 'Errore nel caricamento dei dati');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleFilterChange = (key, value) => setFilters(prev => ({ ...prev, [key]: value }));
  const resetFilters = () => setFilters({ search: '', stage: '' });

  const filteredUsers = trialUsers.filter(user => {
    if (filters.stage && user.trial_stage !== parseInt(filters.stage)) return false;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      return user.full_name?.toLowerCase().includes(q) || user.email?.toLowerCase().includes(q) || user.specialty?.toLowerCase().includes(q);
    }
    return true;
  });

  const handlePromote = async (e, userId) => {
    e.stopPropagation();
    if (!window.confirm('Promuovere questo utente allo stage successivo?')) return;
    try {
      const result = await trialUserService.promote(userId);
      if (result.success) fetchData();
      else alert(result.error || 'Errore nella promozione');
    } catch { alert('Errore nella promozione'); }
  };

  const handleDelete = async (e, userId, userName) => {
    e.stopPropagation();
    if (!window.confirm(`Eliminare definitivamente "${userName}"?`)) return;
    try {
      const result = await trialUserService.delete(userId);
      if (result.success) fetchData();
      else alert(result.error || 'Errore nella eliminazione');
    } catch { alert('Errore nella eliminazione'); }
  };

  const statCards = [
    { key: 'total', label: 'Totale In Prova', value: stats.total, icon: 'ri-user-star-line' },
    { key: 'stage_1', label: 'Stage 1 - Training', value: stats.stage_1, icon: 'ri-book-read-line' },
    { key: 'stage_2', label: 'Stage 2 - Clienti', value: stats.stage_2, icon: 'ri-user-follow-line' },
    { key: 'stage_3', label: 'Promossi', value: stats.stage_3, icon: 'ri-verified-badge-line' },
  ];

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="tu-header">
        <div>
          <h4>Professionisti In Prova</h4>
          <p className="tu-header-sub">{stats.total} professionisti in onboarding</p>
        </div>
        <Link to="/in-prova/nuovo" className="tu-add-btn">
          <i className="ri-user-add-line"></i> Nuovo Professionista
        </Link>
      </div>

      {/* Stats */}
      <div className="tu-stats-row">
        {statCards.map(stat => {
          const s = STAT_STYLES[stat.key];
          return (
            <div key={stat.key} className="tu-stat-card">
              <div>
                <div className="tu-stat-value" style={{ color: s.color }}>{stat.value}</div>
                <div className="tu-stat-label">{stat.label}</div>
              </div>
              <div className="tu-stat-icon" style={{ background: s.bg, color: s.color }}>
                <i className={stat.icon}></i>
              </div>
            </div>
          );
        })}
      </div>

      {/* Filters */}
      <div className="tu-filter-bar">
        <input
          type="text" className="tu-search-input"
          placeholder="Cerca professionista..."
          value={filters.search}
          onChange={(e) => handleFilterChange('search', e.target.value)}
        />
        <select className="tu-filter-select" value={filters.stage} onChange={(e) => handleFilterChange('stage', e.target.value)}>
          <option value="">Tutti gli Stage</option>
          <option value="1">Stage 1 - Training</option>
          <option value="2">Stage 2 - Clienti Selezionati</option>
          <option value="3">Stage 3 - Promosso</option>
        </select>
        <button className="tu-reset-btn" onClick={resetFilters}>
          <i className="ri-refresh-line"></i> Reset
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="tu-loading">
          <div className="tu-spinner"></div>
          <p className="tu-loading-text">Caricamento professionisti...</p>
        </div>
      ) : error ? (
        <div className="tu-error">
          {error}
          <button className="tu-error-retry" onClick={fetchData}>Riprova</button>
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="tu-empty">
          <div className="tu-empty-icon"><i className="ri-user-star-line"></i></div>
          <div className="tu-empty-title">Nessun professionista in prova</div>
          <p className="tu-empty-desc">
            {filters.stage || filters.search
              ? 'Prova a modificare i filtri di ricerca'
              : 'Inizia aggiungendo un nuovo professionista'}
          </p>
          {!filters.stage && !filters.search ? (
            <Link to="/in-prova/nuovo" className="tu-empty-btn">
              <i className="ri-user-add-line"></i> Nuovo Professionista
            </Link>
          ) : (
            <button className="tu-empty-btn" onClick={resetFilters}>
              <i className="ri-refresh-line"></i> Reset Filtri
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="tu-table-card">
            <div className="tu-table-wrap">
              <table className="tu-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '220px' }}>Professionista</th>
                    <th style={{ minWidth: '120px' }}>Stage</th>
                    <th style={{ minWidth: '130px' }}>Specialità</th>
                    <th style={{ minWidth: '150px' }}>Supervisor</th>
                    <th style={{ minWidth: '100px', textAlign: 'center' }}>Clienti</th>
                    <th style={{ minWidth: '120px' }}>Inizio Prova</th>
                    <th style={{ textAlign: 'right', minWidth: '160px' }}>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user) => {
                    const daysSinceStart = trialUserService.getDaysSinceStart(user.trial_started_at);
                    return (
                      <tr key={user.id} onClick={() => navigate(`/in-prova/${user.id}`)}>
                        <td>
                          <Link to={`/in-prova/${user.id}`} className="tu-name-link" onClick={(e) => e.stopPropagation()}>
                            {user.full_name}
                          </Link>
                          <div className="tu-email">{user.email}</div>
                        </td>
                        <td>
                          <span className={`tu-badge ${STAGE_BADGE_CLASS[user.trial_stage] || 'tu-badge-default'}`}>
                            Stage {user.trial_stage}
                          </span>
                        </td>
                        <td>
                          {user.specialty
                            ? <span className="tu-specialty">{user.specialty}</span>
                            : <span className="tu-value-muted">&mdash;</span>}
                        </td>
                        <td>
                          {user.supervisor
                            ? <span className="tu-supervisor">{user.supervisor.full_name}</span>
                            : <span className="tu-value-muted">&mdash;</span>}
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          {user.trial_stage >= 2 ? (
                            <span className={`tu-clients-badge ${user.assigned_clients_count > 0 ? 'has-clients' : 'no-clients'}`}>
                              {user.assigned_clients_count}
                            </span>
                          ) : (
                            <span className="tu-value-muted">&mdash;</span>
                          )}
                        </td>
                        <td>
                          {user.trial_started_at ? (
                            <>
                              <div className="tu-date">{trialUserService.formatDate(user.trial_started_at)}</div>
                              <div className="tu-days-ago">{daysSinceStart}g fa</div>
                            </>
                          ) : (
                            <span className="tu-value-muted">&mdash;</span>
                          )}
                        </td>
                        <td onClick={(e) => e.stopPropagation()}>
                          <div className="tu-actions">
                            {user.is_trial && user.trial_stage < 3 && (
                              <button className="tu-action-btn promote" onClick={(e) => handlePromote(e, user.id)} title="Promuovi">
                                <i className="ri-arrow-up-line"></i>
                              </button>
                            )}
                            {user.trial_stage >= 2 && (
                              <Link to={`/in-prova/${user.id}/assegna-clienti`} className="tu-action-btn assign" title="Assegna Clienti">
                                <i className="ri-user-add-line"></i>
                              </Link>
                            )}
                            <Link to={`/in-prova/${user.id}/modifica`} className="tu-action-btn edit" title="Modifica">
                              <i className="ri-edit-line"></i>
                            </Link>
                            <button className="tu-action-btn delete" onClick={(e) => handleDelete(e, user.id, user.full_name)} title="Elimina">
                              <i className="ri-delete-bin-line"></i>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Results count */}
          <div className="tu-results-count">
            <strong>{filteredUsers.length}</strong> professionisti
            {(filters.stage || filters.search) ? ' (filtrati)' : ''}
          </div>
        </>
      )}
    </div>
  );
}

export default TrialUsersList;

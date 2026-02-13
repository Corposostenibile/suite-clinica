import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import trialUserService, { TRIAL_STAGES } from '../../services/trialUserService';

// Stili per la tabella professionale (stesso stile di ClientiList)
const tableStyles = {
  card: {
    borderRadius: '16px',
    border: 'none',
    boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
    overflow: 'hidden',
  },
  tableHeader: {
    background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
    borderBottom: '2px solid #e2e8f0',
  },
  th: {
    padding: '16px 20px',
    fontSize: '11px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    color: '#64748b',
    whiteSpace: 'nowrap',
    borderBottom: 'none',
  },
  td: {
    padding: '16px 20px',
    fontSize: '14px',
    color: '#334155',
    borderBottom: '1px solid #f1f5f9',
    verticalAlign: 'middle',
  },
  row: {
    transition: 'all 0.15s ease',
    cursor: 'pointer',
  },
  nameLink: {
    color: '#3b82f6',
    fontWeight: 600,
    textDecoration: 'none',
    transition: 'color 0.15s ease',
  },
  emptyCell: {
    color: '#cbd5e1',
    fontStyle: 'normal',
    fontSize: '13px',
  },
  badge: {
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: 600,
    letterSpacing: '0.3px',
  },
  actionBtn: {
    width: '36px',
    height: '36px',
    padding: 0,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '8px',
    border: '1px solid',
    transition: 'all 0.15s ease',
    marginLeft: '6px',
  },
};

// Badge stili per stage
const STAGE_BADGE_STYLES = {
  1: { background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', color: '#fff' },
  2: { background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)', color: '#fff' },
  3: { background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff' },
};

function TrialUsersList() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [trialUsers, setTrialUsers] = useState([]);
  const [stats, setStats] = useState({ total: 0, stage_1: 0, stage_2: 0, stage_3: 0 });
  const [error, setError] = useState(null);
  const [hoveredRow, setHoveredRow] = useState(null);

  const [filters, setFilters] = useState({
    search: '',
    stage: '',
  });

  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
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
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const resetFilters = () => {
    setFilters({ search: '', stage: '' });
  };

  // Filter users
  const filteredUsers = trialUsers.filter(user => {
    if (filters.stage && user.trial_stage !== parseInt(filters.stage)) {
      return false;
    }
    if (filters.search) {
      const query = filters.search.toLowerCase();
      return (
        user.full_name?.toLowerCase().includes(query) ||
        user.email?.toLowerCase().includes(query) ||
        user.specialty?.toLowerCase().includes(query)
      );
    }
    return true;
  });

  // Handle promote
  const handlePromote = async (e, userId) => {
    e.stopPropagation();
    if (!window.confirm('Promuovere questo utente allo stage successivo?')) return;
    try {
      const result = await trialUserService.promote(userId);
      if (result.success) {
        fetchData();
      } else {
        alert(result.error || 'Errore nella promozione');
      }
    } catch (err) {
      alert('Errore nella promozione');
    }
  };

  // Handle delete
  const handleDelete = async (e, userId, userName) => {
    e.stopPropagation();
    if (!window.confirm(`Eliminare definitivamente "${userName}"?`)) return;
    try {
      const result = await trialUserService.delete(userId);
      if (result.success) {
        fetchData();
      } else {
        alert(result.error || 'Errore nella eliminazione');
      }
    } catch (err) {
      alert('Errore nella eliminazione');
    }
  };

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4">
        <div>
          <h4 className="mb-1">Professionisti In Prova</h4>
          <p className="text-muted mb-0">{stats.total} professionisti in onboarding</p>
        </div>
        <div className="d-flex flex-wrap gap-2">
          <Link to="/in-prova/nuovo" className="btn btn-primary px-4">
            <i className="ri-user-add-line me-2"></i>
            Nuovo Professionista
          </Link>
        </div>
      </div>

      {/* Stats Row */}
      <div className="row g-3 mb-4">
        {[
          { label: 'Totale In Prova', value: stats.total, icon: 'ri-user-star-line', bg: 'primary' },
          { label: 'Stage 1 - Training', value: stats.stage_1, icon: 'ri-book-read-line', bg: 'warning' },
          { label: 'Stage 2 - Clienti', value: stats.stage_2, icon: 'ri-user-follow-line', customBg: '#3b82f6' },
          { label: 'Promossi', value: stats.stage_3, icon: 'ri-verified-badge-line', bg: 'success' },
        ].map((stat, idx) => (
          <div key={idx} className="col-xl-3 col-sm-6">
            <div
              className={`card border-0 shadow-sm ${stat.bg ? `bg-${stat.bg}` : ''}`}
              style={stat.customBg ? { backgroundColor: stat.customBg } : {}}
            >
              <div className="card-body py-3">
                <div className="d-flex align-items-center justify-content-between">
                  <div>
                    <h3 className="text-white mb-0 fw-bold">{stat.value}</h3>
                    <span className="text-white opacity-75 small">{stat.label}</span>
                  </div>
                  <div
                    className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center"
                    style={{ width: '48px', height: '48px' }}
                  >
                    <i className={`${stat.icon} text-white fs-4`}></i>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="card shadow-sm border-0 mb-4">
        <div className="card-body py-3">
          <div className="row g-2 align-items-center">
            <div className="col-lg-5">
              <div className="position-relative">
                <i className="ri-search-line position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}></i>
                <input
                  type="text"
                  className="form-control bg-light border-0"
                  placeholder="Cerca professionista..."
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  style={{ paddingLeft: '36px' }}
                />
              </div>
            </div>
            <div className="col-lg-3">
              <select
                className="form-select bg-light border-0"
                value={filters.stage}
                onChange={(e) => handleFilterChange('stage', e.target.value)}
              >
                <option value="">Tutti gli Stage</option>
                <option value="1">Stage 1 - Training</option>
                <option value="2">Stage 2 - Clienti Selezionati</option>
                <option value="3">Stage 3 - Promosso</option>
              </select>
            </div>
            <div className="col-lg-2">
              <button
                className="btn btn-outline-secondary w-100"
                onClick={resetFilters}
              >
                <i className="ri-refresh-line me-1"></i>Reset
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-5">
          <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}></div>
          <p className="mt-3 text-muted">Caricamento professionisti...</p>
        </div>
      ) : error ? (
        <div className="alert alert-danger" style={{ borderRadius: '12px' }}>
          {error}
          <button className="btn btn-sm btn-outline-danger ms-3" onClick={fetchData}>
            Riprova
          </button>
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
          <div className="card-body text-center py-5">
            <div className="mb-4">
              <i className="ri-user-star-line" style={{ fontSize: '5rem', color: '#cbd5e1' }}></i>
            </div>
            <h5 style={{ color: '#475569' }}>Nessun professionista in prova</h5>
            <p className="text-muted mb-4">
              {filters.stage || filters.search
                ? 'Prova a modificare i filtri di ricerca'
                : 'Inizia aggiungendo un nuovo professionista'}
            </p>
            {!filters.stage && !filters.search ? (
              <Link
                to="/in-prova/nuovo"
                className="btn btn-primary"
                style={{ borderRadius: '10px', padding: '10px 24px' }}
              >
                <i className="ri-user-add-line me-2"></i>Nuovo Professionista
              </Link>
            ) : (
              <button
                className="btn btn-primary"
                onClick={resetFilters}
                style={{ borderRadius: '10px', padding: '10px 24px' }}
              >
                <i className="ri-refresh-line me-2"></i>Reset Filtri
              </button>
            )}
          </div>
        </div>
      ) : (
        <>
          {/* Tabella Professionisti In Prova */}
          <div className="card border-0" style={tableStyles.card}>
            <div className="table-responsive">
              <table className="table mb-0">
                <thead style={tableStyles.tableHeader}>
                  <tr>
                    <th style={{ ...tableStyles.th, minWidth: '220px' }}>Professionista</th>
                    <th style={{ ...tableStyles.th, minWidth: '120px' }}>Stage</th>
                    <th style={{ ...tableStyles.th, minWidth: '130px' }}>Specialità</th>
                    <th style={{ ...tableStyles.th, minWidth: '150px' }}>Supervisor</th>
                    <th style={{ ...tableStyles.th, minWidth: '100px', textAlign: 'center' }}>Clienti</th>
                    <th style={{ ...tableStyles.th, minWidth: '120px' }}>Inizio Prova</th>
                    <th style={{ ...tableStyles.th, textAlign: 'right', minWidth: '160px' }}>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user, index) => {
                    const isHovered = hoveredRow === index;
                    const daysSinceStart = trialUserService.getDaysSinceStart(user.trial_started_at);

                    return (
                      <tr
                        key={user.id}
                        style={{
                          ...tableStyles.row,
                          background: isHovered ? '#f8fafc' : 'transparent',
                        }}
                        onMouseEnter={() => setHoveredRow(index)}
                        onMouseLeave={() => setHoveredRow(null)}
                        onClick={() => navigate(`/in-prova/${user.id}`)}
                      >
                        {/* Professionista */}
                        <td style={tableStyles.td}>
                          <Link
                            to={`/in-prova/${user.id}`}
                            style={tableStyles.nameLink}
                            onClick={(e) => e.stopPropagation()}
                            onMouseOver={(e) => e.currentTarget.style.color = '#2563eb'}
                            onMouseOut={(e) => e.currentTarget.style.color = '#3b82f6'}
                          >
                            {user.full_name}
                          </Link>
                          <div>
                            <small className="text-muted">{user.email}</small>
                          </div>
                        </td>

                        {/* Stage */}
                        <td style={tableStyles.td}>
                          <span
                            style={{
                              ...tableStyles.badge,
                              ...(STAGE_BADGE_STYLES[user.trial_stage] || { background: '#94a3b8', color: '#fff' }),
                            }}
                          >
                            Stage {user.trial_stage}
                          </span>
                        </td>

                        {/* Specialità */}
                        <td style={tableStyles.td}>
                          {user.specialty ? (
                            <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>
                              {user.specialty}
                            </span>
                          ) : (
                            <span style={tableStyles.emptyCell}>—</span>
                          )}
                        </td>

                        {/* Supervisor */}
                        <td style={tableStyles.td}>
                          {user.supervisor ? (
                            <span style={{ fontSize: '13px', fontWeight: 500 }}>
                              {user.supervisor.full_name}
                            </span>
                          ) : (
                            <span style={tableStyles.emptyCell}>—</span>
                          )}
                        </td>

                        {/* Clienti */}
                        <td style={{ ...tableStyles.td, textAlign: 'center' }}>
                          {user.trial_stage >= 2 ? (
                            <span
                              style={{
                                ...tableStyles.badge,
                                background: user.assigned_clients_count > 0
                                  ? 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)'
                                  : '#f1f5f9',
                                color: user.assigned_clients_count > 0 ? '#166534' : '#94a3b8',
                              }}
                            >
                              {user.assigned_clients_count}
                            </span>
                          ) : (
                            <span style={tableStyles.emptyCell}>—</span>
                          )}
                        </td>

                        {/* Inizio Prova */}
                        <td style={tableStyles.td}>
                          {user.trial_started_at ? (
                            <>
                              <span style={{ fontWeight: 500 }}>
                                {trialUserService.formatDate(user.trial_started_at)}
                              </span>
                              <div>
                                <small className="text-muted">{daysSinceStart}g fa</small>
                              </div>
                            </>
                          ) : (
                            <span style={tableStyles.emptyCell}>—</span>
                          )}
                        </td>

                        {/* Azioni */}
                        <td style={{ ...tableStyles.td, textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                          {/* Promote */}
                          {user.is_trial && user.trial_stage < 3 && (
                            <button
                              onClick={(e) => handlePromote(e, user.id)}
                              title="Promuovi"
                              style={{
                                ...tableStyles.actionBtn,
                                borderColor: '#22c55e',
                                color: '#22c55e',
                                background: isHovered ? 'rgba(34, 197, 94, 0.1)' : 'transparent',
                              }}
                            >
                              <i className="ri-arrow-up-line" style={{ fontSize: '16px' }}></i>
                            </button>
                          )}

                          {/* Assign Clients */}
                          {user.trial_stage >= 2 && (
                            <Link
                              to={`/in-prova/${user.id}/assegna-clienti`}
                              title="Assegna Clienti"
                              style={{
                                ...tableStyles.actionBtn,
                                borderColor: '#3b82f6',
                                color: '#3b82f6',
                                background: isHovered ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                              }}
                            >
                              <i className="ri-user-add-line" style={{ fontSize: '16px' }}></i>
                            </Link>
                          )}

                          {/* Edit */}
                          <Link
                            to={`/in-prova/${user.id}/modifica`}
                            title="Modifica"
                            style={{
                              ...tableStyles.actionBtn,
                              borderColor: '#64748b',
                              color: '#64748b',
                              background: isHovered ? 'rgba(100, 116, 139, 0.1)' : 'transparent',
                            }}
                          >
                            <i className="ri-edit-line" style={{ fontSize: '16px' }}></i>
                          </Link>

                          {/* Delete */}
                          <button
                            onClick={(e) => handleDelete(e, user.id, user.full_name)}
                            title="Elimina"
                            style={{
                              ...tableStyles.actionBtn,
                              borderColor: '#ef4444',
                              color: '#ef4444',
                              background: isHovered ? 'rgba(239, 68, 68, 0.1)' : 'transparent',
                            }}
                          >
                            <i className="ri-delete-bin-line" style={{ fontSize: '16px' }}></i>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Results count */}
          <div className="d-flex justify-content-between align-items-center mt-4 pt-3">
            <span style={{ color: '#64748b', fontSize: '14px' }}>
              <strong style={{ color: '#334155' }}>{filteredUsers.length}</strong> professionisti
              {filters.stage || filters.search ? ' (filtrati)' : ''}
            </span>
          </div>
        </>
      )}
    </div>
  );
}

export default TrialUsersList;

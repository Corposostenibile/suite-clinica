import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import teamService, {
  TEAM_TYPE_LABELS,
  TEAM_TYPE_COLORS,
  TEAM_TYPE_ICONS,
  TEAM_TYPES,
} from '../../services/teamService';

// Colori sfondo header card in base al tipo team (coerenti con i KPI pazienti)
const TYPE_GRADIENTS = {
  nutrizione: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
  coach: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
  psicologia: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
};

function TeamsList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [filters, setFilters] = useState({
    search: searchParams.get('q') || '',
    teamType: searchParams.get('team_type') || '',
    status: searchParams.get('status') || 'active',
  });

  const fetchTeams = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        q: filters.search || undefined,
        team_type: filters.teamType || undefined,
        active: filters.status === 'active' ? '1' : filters.status === 'inactive' ? '0' : undefined,
      };

      const data = await teamService.getTeams(params);
      setTeams(data.teams || []);
    } catch (err) {
      console.error('Error fetching teams:', err);
      setError('Errore nel caricamento dei team');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchTeams();
  }, [fetchTeams]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key === 'search' ? 'q' : key === 'teamType' ? 'team_type' : key, value);
    } else {
      newParams.delete(key === 'search' ? 'q' : key === 'teamType' ? 'team_type' : key);
    }
    setSearchParams(newParams);
  };

  const resetFilters = () => {
    setFilters({ search: '', teamType: '', status: '' });
    setSearchParams(new URLSearchParams());
  };

  // Stats
  const totalTeams = teams.length;
  const nutrizioneTeams = teams.filter(t => t.team_type === 'nutrizione').length;
  const coachTeams = teams.filter(t => t.team_type === 'coach').length;
  const psicologiaTeams = teams.filter(t => t.team_type === 'psicologia').length;

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4">
        <div>
          <h4 className="mb-1">Gestione Team</h4>
          <p className="text-muted mb-0">{totalTeams} team totali</p>
        </div>
        <Link to="/teams-nuovo" className="btn btn-primary btn-lg px-4">
          <i className="ri-add-line me-2"></i>
          Nuovo Team
        </Link>
      </div>

      {/* Stats Row */}
      <div className="row g-3 mb-4">
        {[
          { label: 'Team Totali', value: totalTeams, icon: 'ri-team-line', bg: 'primary', gradient: null },
          { label: 'Nutrizione', value: nutrizioneTeams, icon: TEAM_TYPE_ICONS.nutrizione, bg: null, gradient: TYPE_GRADIENTS.nutrizione },
          { label: 'Coach', value: coachTeams, icon: TEAM_TYPE_ICONS.coach, bg: null, gradient: TYPE_GRADIENTS.coach },
          { label: 'Psicologia', value: psicologiaTeams, icon: TEAM_TYPE_ICONS.psicologia, bg: null, gradient: TYPE_GRADIENTS.psicologia },
        ].map((stat, idx) => (
          <div key={idx} className="col-xl-3 col-sm-6">
            <div
              className={`card border-0 shadow-sm ${stat.bg ? `bg-${stat.bg}` : ''}`}
              style={stat.gradient ? { background: stat.gradient } : {}}
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
            <div className="col-lg-4">
              <div className="position-relative">
                <i className="ri-search-line position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}></i>
                <input
                  type="text"
                  className="form-control bg-light border-0"
                  placeholder="Cerca per nome..."
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  style={{ paddingLeft: '36px' }}
                />
              </div>
            </div>
            <div className="col-lg-3">
              <select
                className="form-select bg-light border-0"
                value={filters.teamType}
                onChange={(e) => handleFilterChange('teamType', e.target.value)}
              >
                <option value="">Tutti i Tipi</option>
                {Object.entries(TEAM_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-3">
              <select
                className="form-select bg-light border-0"
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
              >
                <option value="">Tutti</option>
                <option value="active">Attivi</option>
                <option value="inactive">Inattivi</option>
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
          <p className="mt-3 text-muted">Caricamento team...</p>
        </div>
      ) : error ? (
        <div className="alert alert-danger">{error}</div>
      ) : teams.length === 0 ? (
        <div className="card shadow-sm border-0">
          <div className="card-body text-center py-5">
            <div className="mb-4">
              <i className="ri-team-line text-muted" style={{ fontSize: '5rem' }}></i>
            </div>
            <h5>Nessun team trovato</h5>
            <p className="text-muted mb-4">Prova a modificare i filtri di ricerca</p>
            <button className="btn btn-primary" onClick={resetFilters}>
              <i className="ri-refresh-line me-2"></i>Reset Filtri
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Teams Grid */}
          <div className="row g-4">
            {teams.map((team) => (
              <div key={team.id} className="col-xxl-3 col-xl-4 col-lg-4 col-md-6 mb-4">
                <div className="card border-0 shadow-sm overflow-hidden" style={{ borderRadius: '12px' }}>
                  {/* Gradient Header */}
                  <div
                    className="position-relative"
                    style={{
                      background: TYPE_GRADIENTS[team.team_type] || TYPE_GRADIENTS.nutrizione,
                      height: '70px',
                    }}
                  >
                    {/* Status Badge */}
                    <div className="position-absolute top-0 start-0 m-2 d-flex gap-1">
                      {!team.is_active && (
                        <span className="badge bg-dark bg-opacity-75 small">
                          <i className="ri-close-circle-line me-1"></i>Inattivo
                        </span>
                      )}
                    </div>

                    {/* Type Badge */}
                    <div className="position-absolute top-0 end-0 m-2">
                      <span className="badge bg-white text-dark small">
                        {TEAM_TYPE_LABELS[team.team_type]}
                      </span>
                    </div>

                    {/* Icon */}
                    <div className="position-absolute start-50 translate-middle" style={{ top: '100%' }}>
                      <div
                        className="rounded-circle border border-3 border-white shadow-sm d-flex align-items-center justify-content-center"
                        style={{
                          width: '64px',
                          height: '64px',
                          background: '#fff'
                        }}
                      >
                        <i className={`${TEAM_TYPE_ICONS[team.team_type]} fs-3 text-${TEAM_TYPE_COLORS[team.team_type]}`}></i>
                      </div>
                    </div>
                  </div>

                  {/* Card Body */}
                  <div className="card-body text-center pt-5 pb-3">
                    {/* Name */}
                    <h5 className="fw-semibold mb-1">
                      <Link
                        to={`/teams-dettaglio/${team.id}`}
                        className="text-dark text-decoration-none"
                        style={{ transition: 'color 0.2s' }}
                        onMouseOver={(e) => e.target.style.color = '#667eea'}
                        onMouseOut={(e) => e.target.style.color = ''}
                      >
                        {team.name}
                      </Link>
                    </h5>

                    {/* Description */}
                    <p className="text-muted small mb-3" style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: '100%'
                    }}>
                      {team.description || 'Nessuna descrizione'}
                    </p>

                    {/* Team Leader */}
                    {team.head && (
                      <div className="d-flex align-items-center justify-content-center mb-2">
                        <div className="flex-shrink-0">
                          {team.head.avatar_path ? (
                            <img
                              src={team.head.avatar_path}
                              alt={team.head.full_name}
                              className="rounded-circle"
                              style={{ width: '24px', height: '24px', objectFit: 'cover' }}
                            />
                          ) : (
                            <div
                              className="rounded-circle bg-primary d-flex align-items-center justify-content-center text-white"
                              style={{ width: '24px', height: '24px', fontSize: '10px' }}
                            >
                              {team.head.first_name?.[0]}{team.head.last_name?.[0]}
                            </div>
                          )}
                        </div>
                        <small className="ms-2 text-muted">
                          <i className="ri-user-star-line me-1"></i>
                          {team.head.full_name}
                        </small>
                      </div>
                    )}

                    {/* Members Count */}
                    <div className="text-muted small">
                      <i className="ri-group-line me-1"></i>
                      {team.member_count || 0} membri
                    </div>
                  </div>

                  {/* Card Footer */}
                  <div className="card-footer bg-light border-0 py-2">
                    <div className="d-flex gap-2 justify-content-center">
                      <Link
                        to={`/teams-dettaglio/${team.id}`}
                        className="btn btn-sm btn-outline-primary flex-fill"
                      >
                        <i className="ri-eye-line me-1"></i>Dettagli
                      </Link>
                      <Link
                        to={`/teams-modifica/${team.id}`}
                        className="btn btn-sm btn-outline-secondary flex-fill"
                      >
                        <i className="ri-edit-line me-1"></i>Modifica
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default TeamsList;

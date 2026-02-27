import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import teamService, {
  ROLE_LABELS,
  SPECIALTY_LABELS,
  SPECIALTY_FILTER_OPTIONS,
  ROLE_COLORS,
  getUserRoleDisplayLabel,
  SPECIALTY_COLORS,
  getUserDisplaySpecialty,
} from '../../services/teamService';
import { useAuth } from '../../context/AuthContext';
import { normalizeAvatarPath } from '../../utils/mediaUrl';
import { isProfessionistaStandard } from '../../utils/rbacScope';

// Colori sfondo header card in base alla specializzazione (coerenti con i KPI pazienti)
const SPECIALTY_GRADIENTS = {
  nutrizione: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
  nutrizionista: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
  coach: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
  psicologia: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
  psicologo: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
};

// Fallback gradient per membri senza specializzazione
const DEFAULT_GRADIENT = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';

function TeamList() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isAdminOrCco = Boolean(user?.is_admin || user?.role === 'admin' || user?.specialty === 'cco');
  const isTeamLeaderRestricted = Boolean(user?.role === 'team_leader' && !isAdminOrCco);
  const isProfessionista = isProfessionistaStandard(user);
  const [searchParams, setSearchParams] = useSearchParams();
  const [members, setMembers] = useState([]);
  const [brokenAvatars, setBrokenAvatars] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [globalStats, setGlobalStats] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 12,
    total: 0,
    totalPages: 0,
  });

  const [filters, setFilters] = useState({
    search: searchParams.get('q') || '',
    role: searchParams.get('role') || '',
    specialty: searchParams.get('specialty') || '',
    status: searchParams.get('status') || 'active',
  });

  // Keep filter state aligned with URL query params (e.g. /team-lista?role=health_manager).
  useEffect(() => {
    setFilters({
      search: searchParams.get('q') || '',
      role: searchParams.get('role') || '',
      specialty: searchParams.get('specialty') || '',
      status: searchParams.get('status') || 'active',
    });
  }, [searchParams]);

  // Fetch global stats on mount
  useEffect(() => {
    if (isProfessionista) {
      navigate('/profilo', { replace: true });
      return;
    }
    const fetchStats = async () => {
      if (!isAdminOrCco) return;
      try {
        const stats = await teamService.getStats();
        setGlobalStats(stats);
      } catch (err) {
        console.error('Error fetching stats:', err);
      }
    };
    fetchStats();
  }, [isAdminOrCco, isProfessionista, navigate]);

  const fetchMembers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page: pagination.page,
        per_page: pagination.perPage,
        q: filters.search || undefined,
        role: filters.role || undefined,
        specialty: filters.specialty || undefined,
        active: filters.status === 'active' ? '1' : filters.status === 'inactive' ? '0' : undefined,
      };

      const data = await teamService.getTeamMembers(params);
      setMembers(data.members || []);
      setPagination(prev => ({
        ...prev,
        total: data.total || 0,
        totalPages: data.total_pages || 0,
      }));
    } catch (err) {
      console.error('Error fetching team members:', err);
      setError('Errore nel caricamento del team');
    } finally {
      setLoading(false);
    }
  }, [pagination.page, pagination.perPage, filters]);

  useEffect(() => {
    if (isProfessionista) return;
    fetchMembers();
  }, [fetchMembers, isProfessionista]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 }));
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key === 'search' ? 'q' : key, value);
    } else {
      newParams.delete(key === 'search' ? 'q' : key);
    }
    setSearchParams(newParams);
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, page: newPage }));
  };

  const resetFilters = () => {
    setFilters({ search: '', role: '', specialty: '', status: '' });
    setSearchParams(new URLSearchParams());
  };

  // Check if any filter is active (exclude default status='active')
  const hasActiveFilters = filters.search || filters.role || filters.specialty || (filters.status && filters.status !== 'active');

  // Stats - use global stats when no filters, otherwise use filtered results
  const totalMembers = isAdminOrCco && !hasActiveFilters ? (globalStats?.total_members || pagination.total) : pagination.total;
  const totalActive = isAdminOrCco && !hasActiveFilters ? (globalStats?.total_active || pagination.total) : members.filter(m => m.is_active).length;
  const totalLeaders = isAdminOrCco && !hasActiveFilters
    ? (globalStats?.total_team_leaders || 0)
    : members.filter(m => m.role === 'team_leader' || (m.teams_led?.length || 0) > 0).length;
  const totalExternal = isAdminOrCco && !hasActiveFilters ? (globalStats?.total_external || 0) : members.filter(m => m.is_external).length;

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4">
        <div>
          <h4 className="mb-1">Gestione Team</h4>
          <p className="text-muted mb-0">{pagination.total} membri totali</p>
        </div>
        {isAdminOrCco && (
          <Link to="/team-nuovo" className="btn btn-primary">
            <i className="ri-user-add-line me-1"></i>
            Nuovo Professionista
          </Link>
        )}
      </div>

      {!isTeamLeaderRestricted && (
        <div className="row g-3 mb-4">
          {[
            { label: 'Membri Totali', value: totalMembers, icon: 'ri-team-line', bg: 'primary' },
            { label: 'Attivi', value: totalActive, icon: 'ri-checkbox-circle-line', bg: 'success' },
            { label: 'Team Leaders', value: totalLeaders, icon: 'ri-user-star-line', bg: 'info' },
            { label: 'Esterni', value: totalExternal, icon: 'ri-external-link-line', bg: 'warning' },
          ].map((stat, idx) => (
            <div key={idx} className="col-xl-3 col-sm-6">
              <div className={`card bg-${stat.bg} border-0 shadow-sm`}>
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
      )}

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
                  placeholder="Cerca per nome o email..."
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  style={{ paddingLeft: '36px' }}
                />
              </div>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.role}
                onChange={(e) => handleFilterChange('role', e.target.value)}
              >
                <option value="">Tutti i Ruoli</option>
                {Object.entries(ROLE_LABELS)
                  .filter(([value]) => value !== 'team_leader' && value !== 'team_esterno')
                  .map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2">
              <select
                className="form-select bg-light border-0"
                value={filters.specialty}
                onChange={(e) => handleFilterChange('specialty', e.target.value)}
              >
                <option value="">Specializzazione</option>
                {SPECIALTY_FILTER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div className="col-lg-2">
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
      ) : members.length === 0 ? (
        <div className="card shadow-sm border-0">
          <div className="card-body text-center py-5">
            <div className="mb-4">
              <i className="ri-user-search-line text-muted" style={{ fontSize: '5rem' }}></i>
            </div>
            <h5>Nessun membro trovato</h5>
            <p className="text-muted mb-4">Prova a modificare i filtri di ricerca</p>
            <button className="btn btn-primary" onClick={resetFilters}>
              <i className="ri-refresh-line me-2"></i>Reset Filtri
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Team Grid */}
          <div className="row g-4">
            {members.map((member) => {
              const avatarSrc = normalizeAvatarPath(member.avatar_path);
              const showAvatar = avatarSrc && !brokenAvatars[member.id];
              const displaySpecialty = getUserDisplaySpecialty(member);

              return (
              <div key={member.id} className="col-xxl-3 col-xl-4 col-lg-4 col-md-6 mb-4">
                <div className="card border-0 shadow-sm overflow-hidden" style={{ borderRadius: '12px' }}>
                  {/* Gradient Header - colore basato su specializzazione */}
                  <div
                    className="position-relative"
                    style={{
                      background: SPECIALTY_GRADIENTS[member.specialty] || DEFAULT_GRADIENT,
                      height: '70px',
                    }}
                  >
                    {/* Status Badges */}
                    <div className="position-absolute top-0 start-0 m-2 d-flex gap-1">
                      {!member.is_active && (
                        <span className="badge bg-dark bg-opacity-75 small">
                          <i className="ri-close-circle-line me-1"></i>Inattivo
                        </span>
                      )}
                      {member.is_external && (
                        <span className="badge bg-white text-dark small">
                          <i className="ri-external-link-line me-1"></i>Esterno
                        </span>
                      )}
                    </div>

                    {/* Avatar */}
                    <div className="position-absolute start-50 translate-middle" style={{ top: '100%' }}>
                      {showAvatar ? (
                        <img
                          src={avatarSrc}
                          alt={member.full_name}
                          className="rounded-circle border border-3 border-white shadow-sm"
                          style={{ width: '64px', height: '64px', objectFit: 'cover', background: '#fff' }}
                          onError={() => setBrokenAvatars(prev => ({ ...prev, [member.id]: true }))}
                        />
                      ) : (
                        <div
                          className="rounded-circle border border-3 border-white shadow-sm d-flex align-items-center justify-content-center"
                          style={{
                            width: '64px',
                            height: '64px',
                            background: '#fff'
                          }}
                        >
                          <span className="fw-bold fs-5 text-primary">
                            {member.first_name?.[0]?.toUpperCase()}{member.last_name?.[0]?.toUpperCase()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Body */}
                  <div className="card-body text-center pt-5 pb-3">
                    {/* Name */}
                    <h5 className="fw-semibold mb-1">
                      <Link
                        to={`/team-dettaglio/${member.id}`}
                        className="text-dark text-decoration-none"
                        style={{ transition: 'color 0.2s' }}
                        onMouseOver={(e) => e.target.style.color = '#667eea'}
                        onMouseOut={(e) => e.target.style.color = ''}
                      >
                        {member.full_name || `${member.first_name} ${member.last_name}`}
                      </Link>
                    </h5>

                    {/* Email */}
                    <p className="text-muted small mb-3" style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: '100%'
                    }}>
                      {member.email}
                    </p>

                    {/* Role & Specialty Badges */}
                    <div className="d-flex flex-wrap justify-content-center gap-1 mb-2">
                      <span className={`badge rounded-pill px-2 py-1 bg-${ROLE_COLORS[member.role] || 'secondary'}`} style={{ fontSize: '11px' }}>
                        {getUserRoleDisplayLabel(member)}
                      </span>
                      {displaySpecialty && (
                        <span className={`badge rounded-pill px-2 py-1 bg-${SPECIALTY_COLORS[displaySpecialty] || 'secondary'}-subtle text-${SPECIALTY_COLORS[displaySpecialty] || 'secondary'}`} style={{ fontSize: '11px' }}>
                          {SPECIALTY_LABELS[displaySpecialty] || displaySpecialty}
                        </span>
                      )}
                    </div>

                    {/* Teams Led */}
                    {member.teams_led?.length > 0 && (
                      <div className="text-muted small">
                        <i className="ri-team-line me-1"></i>
                        Leader di {member.teams_led.length} team
                      </div>
                    )}
                  </div>

                  {/* Card Footer */}
                  <div className="card-footer bg-light border-0 py-2">
                    <div className="d-flex gap-2 justify-content-center">
                      <Link
                        to={`/team-dettaglio/${member.id}`}
                        className="btn btn-sm btn-outline-primary flex-fill"
                      >
                        <i className="ri-eye-line me-1"></i>Dettagli
                      </Link>
                      {isAdminOrCco && (
                        <Link
                          to={`/team-modifica/${member.id}`}
                          className="btn btn-sm btn-outline-secondary flex-fill"
                        >
                          <i className="ri-edit-line me-1"></i>Modifica
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              );
            })}
          </div>

          {/* Pagination */}
          {pagination.totalPages > 1 && (
            <div className="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
              <span className="text-muted">
                Pagina <strong>{pagination.page}</strong> di <strong>{pagination.totalPages}</strong>
              </span>
              <nav>
                <ul className="pagination pagination-sm mb-0">
                  <li className={`page-item ${pagination.page === 1 ? 'disabled' : ''}`}>
                    <button className="page-link rounded-start" onClick={() => handlePageChange(pagination.page - 1)}>
                      <i className="ri-arrow-left-s-line"></i>
                    </button>
                  </li>
                  {[...Array(Math.min(pagination.totalPages, 5))].map((_, i) => {
                    const pageNum = pagination.totalPages <= 5 ? i + 1 :
                      pagination.page <= 3 ? i + 1 :
                      pagination.page >= pagination.totalPages - 2 ? pagination.totalPages - 4 + i :
                      pagination.page - 2 + i;
                    return (
                      <li key={pageNum} className={`page-item ${pagination.page === pageNum ? 'active' : ''}`}>
                        <button className="page-link" onClick={() => handlePageChange(pageNum)}>{pageNum}</button>
                      </li>
                    );
                  })}
                  <li className={`page-item ${pagination.page === pagination.totalPages ? 'disabled' : ''}`}>
                    <button className="page-link rounded-end" onClick={() => handlePageChange(pagination.page + 1)}>
                      <i className="ri-arrow-right-s-line"></i>
                    </button>
                  </li>
                </ul>
              </nav>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default TeamList;

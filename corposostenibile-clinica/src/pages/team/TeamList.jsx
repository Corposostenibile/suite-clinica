import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import teamService, {
  ROLE_LABELS,
  SPECIALTY_LABELS,
  SPECIALTY_FILTER_OPTIONS,
  getUserRoleDisplayLabel,
  getUserDisplaySpecialty,
} from '../../services/teamService';
import { useAuth } from '../../context/AuthContext';
import { normalizeAvatarPath } from '../../utils/mediaUrl';
import { isProfessionistaStandard } from '../../utils/rbacScope';
import './TeamList.css';

const SPECIALTY_GRADIENTS = {
  nutrizione: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
  nutrizionista: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
  coach: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
  psicologia: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
  psicologo: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
  health_manager: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
  cco: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
};
const DEFAULT_GRADIENT = 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)';

const STAT_ICON_STYLES = {
  total:   { bg: 'rgba(37, 179, 106, 0.1)',  color: '#25B36A' },
  active:  { bg: 'rgba(34, 197, 94, 0.1)',   color: '#22c55e' },
  leaders: { bg: 'rgba(249, 115, 22, 0.1)',  color: '#f97316' },
  external:{ bg: 'rgba(139, 92, 246, 0.1)',  color: '#8b5cf6' },
};

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
    page: 1, perPage: 12, total: 0, totalPages: 0,
  });

  const [filters, setFilters] = useState({
    search: searchParams.get('q') || '',
    role: searchParams.get('role') || '',
    specialty: searchParams.get('specialty') || '',
    status: searchParams.get('status') || 'active',
  });

  useEffect(() => {
    setFilters({
      search: searchParams.get('q') || '',
      role: searchParams.get('role') || '',
      specialty: searchParams.get('specialty') || '',
      status: searchParams.get('status') || 'active',
    });
  }, [searchParams]);

  useEffect(() => {
    if (isProfessionista) { navigate('/profilo', { replace: true }); return; }
    const fetchStats = async () => {
      if (!isAdminOrCco) return;
      try {
        const stats = await teamService.getStats();
        setGlobalStats(stats);
      } catch (err) { console.error('Error fetching stats:', err); }
    };
    fetchStats();
  }, [isAdminOrCco, isProfessionista, navigate]);

  const fetchMembers = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = {
        page: pagination.page, per_page: pagination.perPage,
        q: filters.search || undefined, role: filters.role || undefined,
        specialty: filters.specialty || undefined,
        active: filters.status === 'active' ? '1' : filters.status === 'inactive' ? '0' : undefined,
      };
      const data = await teamService.getTeamMembers(params);
      setMembers(data.members || []);
      setPagination(prev => ({ ...prev, total: data.total || 0, totalPages: data.total_pages || 0 }));
    } catch (err) {
      console.error('Error fetching team members:', err);
      setError('Errore nel caricamento del team');
    } finally { setLoading(false); }
  }, [pagination.page, pagination.perPage, filters]);

  useEffect(() => { if (!isProfessionista) fetchMembers(); }, [fetchMembers, isProfessionista]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 }));
    const newParams = new URLSearchParams(searchParams);
    if (value) newParams.set(key === 'search' ? 'q' : key, value);
    else newParams.delete(key === 'search' ? 'q' : key);
    setSearchParams(newParams);
  };

  const handlePageChange = (p) => setPagination(prev => ({ ...prev, page: p }));

  const resetFilters = () => {
    setFilters({ search: '', role: '', specialty: '', status: '' });
    setSearchParams(new URLSearchParams());
  };

  const hasActiveFilters = filters.search || filters.role || filters.specialty || (filters.status && filters.status !== 'active');
  const totalMembers = isAdminOrCco && !hasActiveFilters ? (globalStats?.total_members || pagination.total) : pagination.total;
  const totalActive = isAdminOrCco && !hasActiveFilters ? (globalStats?.total_active || pagination.total) : members.filter(m => m.is_active).length;
  const totalLeaders = isAdminOrCco && !hasActiveFilters ? (globalStats?.total_team_leaders || 0) : members.filter(m => m.role === 'team_leader' || (m.teams_led?.length || 0) > 0).length;
  const totalExternal = isAdminOrCco && !hasActiveFilters ? (globalStats?.total_external || 0) : members.filter(m => m.is_external).length;

  const getPageNumbers = () => {
    const pages = [], total = pagination.totalPages, current = pagination.page;
    if (total <= 5) { for (let i = 1; i <= total; i++) pages.push(i); }
    else if (current <= 3) { for (let i = 1; i <= 5; i++) pages.push(i); }
    else if (current >= total - 2) { for (let i = total - 4; i <= total; i++) pages.push(i); }
    else { for (let i = current - 2; i <= current + 2; i++) pages.push(i); }
    return pages;
  };

  const statCards = [
    { key: 'total', label: 'Membri Totali', value: totalMembers, icon: 'ri-team-line' },
    { key: 'active', label: 'Attivi', value: totalActive, icon: 'ri-checkbox-circle-line' },
    { key: 'leaders', label: 'Team Leaders', value: totalLeaders, icon: 'ri-user-star-line' },
    { key: 'external', label: 'Esterni', value: totalExternal, icon: 'ri-external-link-line' },
  ];

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="tl-header">
        <div>
          <h4>Gestione Team</h4>
          <p className="tl-header-sub">{pagination.total} membri totali</p>
        </div>
        <div className="tl-header-actions">
          <Link to="/team-capienza" className="tl-action-pill">
            <i className="ri-bar-chart-box-line"></i> Capienza
          </Link>
          <Link to="/criteri-professionisti" className="tl-action-pill">
            <i className="ri-settings-3-line"></i> Specializzazione
          </Link>
          {isAdminOrCco && (
            <Link to="/team-nuovo" className="tl-action-pill primary">
              <i className="ri-user-add-line"></i> Nuovo Professionista
            </Link>
          )}
        </div>
      </div>

      {/* Stats */}
      {!isTeamLeaderRestricted && (
        <div className="tl-stats-row">
          {statCards.map((stat) => {
            const s = STAT_ICON_STYLES[stat.key];
            return (
              <div key={stat.key} className="tl-stat-card">
                <div>
                  <div className="tl-stat-value">{stat.value}</div>
                  <div className="tl-stat-label">{stat.label}</div>
                </div>
                <div className="tl-stat-icon" style={{ background: s.bg, color: s.color }}>
                  <i className={stat.icon}></i>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Search + Filters */}
      <div className="tl-search-row">
        <div className="tl-search-wrap">
          <i className="ri-search-line tl-search-icon"></i>
          <input
            type="text" className="tl-search-input"
            placeholder="Cerca per nome o email..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
          />
        </div>
        <select className="tl-filter-select" value={filters.role} onChange={(e) => handleFilterChange('role', e.target.value)}>
          <option value="">Tutti i Ruoli</option>
          {Object.entries(ROLE_LABELS).filter(([v]) => v !== 'team_leader' && v !== 'team_esterno').map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <select className="tl-filter-select" value={filters.specialty} onChange={(e) => handleFilterChange('specialty', e.target.value)}>
          <option value="">Specializzazione</option>
          {SPECIALTY_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <select className="tl-filter-select" value={filters.status} onChange={(e) => handleFilterChange('status', e.target.value)}>
          <option value="">Tutti</option>
          <option value="active">Attivi</option>
          <option value="inactive">Inattivi</option>
        </select>
        <button className="tl-reset-btn" onClick={resetFilters}>
          <i className="ri-refresh-line"></i> Reset
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="tl-loading">
          <div className="tl-spinner"></div>
          <p className="tl-loading-text">Caricamento team...</p>
        </div>
      ) : error ? (
        <div className="tl-error">{error}</div>
      ) : members.length === 0 ? (
        <div className="tl-empty">
          <div className="tl-empty-icon"><i className="ri-user-search-line"></i></div>
          <h5 className="tl-empty-title">Nessun membro trovato</h5>
          <p className="tl-empty-desc">Prova a modificare i filtri di ricerca</p>
          <button className="tl-empty-btn" onClick={resetFilters}>
            <i className="ri-refresh-line"></i> Reset Filtri
          </button>
        </div>
      ) : (
        <>
          <div className="tl-grid">
            {members.map((member) => {
              const avatarSrc = normalizeAvatarPath(member.avatar_path);
              const showAvatar = avatarSrc && !brokenAvatars[member.id];
              const displaySpecialty = getUserDisplaySpecialty(member);

              return (
                <div key={member.id} className="tl-card">
                  <div className="tl-card-header" style={{ background: SPECIALTY_GRADIENTS[member.specialty] || SPECIALTY_GRADIENTS[member.role] || DEFAULT_GRADIENT }}>
                    <div className="tl-card-badges">
                      {!member.is_active && (
                        <span className="tl-mini-badge dark"><i className="ri-close-circle-line"></i> Inattivo</span>
                      )}
                      {member.is_external && (
                        <span className="tl-mini-badge light"><i className="ri-external-link-line"></i> Esterno</span>
                      )}
                    </div>
                    <div className="tl-avatar-wrap">
                      {showAvatar ? (
                        <img src={avatarSrc} alt={member.full_name} className="tl-avatar"
                          onError={() => setBrokenAvatars(prev => ({ ...prev, [member.id]: true }))} />
                      ) : (
                        <div className="tl-avatar-initials">
                          {member.first_name?.[0]?.toUpperCase()}{member.last_name?.[0]?.toUpperCase()}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="tl-card-body">
                    <div className="tl-card-name">
                      <Link to={`/team-dettaglio/${member.id}`}>
                        {member.full_name || `${member.first_name} ${member.last_name}`}
                      </Link>
                    </div>
                    <div className="tl-card-email">{member.email}</div>
                    <div className="tl-card-pills">
                      <span className="tl-pill tl-pill-role">{getUserRoleDisplayLabel(member)}</span>
                      {displaySpecialty && (
                        <span className={`tl-pill tl-pill-specialty-${displaySpecialty}`}>
                          {SPECIALTY_LABELS[displaySpecialty] || displaySpecialty}
                        </span>
                      )}
                    </div>
                    {member.teams_led?.length > 0 && (
                      <div className="tl-card-teams-led">
                        <i className="ri-team-line"></i> Leader di {member.teams_led.length} team
                      </div>
                    )}
                  </div>

                  <div className="tl-card-footer">
                    <Link to={`/team-dettaglio/${member.id}`} className="tl-card-action">
                      <i className="ri-eye-line"></i> Dettagli
                    </Link>
                    {isAdminOrCco && (
                      <Link to={`/team-modifica/${member.id}`} className="tl-card-action">
                        <i className="ri-edit-line"></i> Modifica
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          {pagination.totalPages > 1 && (
            <div className="tl-pagination">
              <span className="tl-pagination-info">
                Pagina <strong>{pagination.page}</strong> di <strong>{pagination.totalPages}</strong>
                {' '}&bull; {pagination.total} risultati
              </span>
              <div className="tl-pagination-buttons">
                <button className="tl-page-btn" onClick={() => handlePageChange(1)} disabled={pagination.page === 1}>&laquo;</button>
                <button className="tl-page-btn" onClick={() => handlePageChange(pagination.page - 1)} disabled={pagination.page === 1}>&lsaquo;</button>
                {getPageNumbers().map(p => (
                  <button key={p} className={`tl-page-btn${pagination.page === p ? ' active' : ''}`} onClick={() => handlePageChange(p)}>{p}</button>
                ))}
                <button className="tl-page-btn" onClick={() => handlePageChange(pagination.page + 1)} disabled={pagination.page === pagination.totalPages}>&rsaquo;</button>
                <button className="tl-page-btn" onClick={() => handlePageChange(pagination.totalPages)} disabled={pagination.page === pagination.totalPages}>&raquo;</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default TeamList;

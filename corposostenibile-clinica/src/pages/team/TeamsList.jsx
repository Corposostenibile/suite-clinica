import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import teamService, {
  TEAM_TYPE_LABELS,
  TEAM_TYPE_ICONS,
} from '../../services/teamService';
import { normalizeAvatarPath } from '../../utils/mediaUrl';
import { useAuth } from '../../context/AuthContext';
import './TeamList.css';

const TYPE_GRADIENTS = {
  nutrizione: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
  coach: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
  psicologia: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
};

const STAT_ICON_STYLES = {
  total:      { bg: 'rgba(37, 179, 106, 0.1)',  color: '#25B36A' },
  nutrizione: { bg: 'rgba(34, 197, 94, 0.1)',   color: '#22c55e' },
  coach:      { bg: 'rgba(249, 115, 22, 0.1)',  color: '#f97316' },
  psicologia: { bg: 'rgba(139, 92, 246, 0.1)',  color: '#8b5cf6' },
};

function TeamsList() {
  const { user } = useAuth();
  const isAdminOrCco = Boolean(user?.is_admin || user?.role === 'admin' || user?.specialty === 'cco');
  const [searchParams, setSearchParams] = useSearchParams();
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1, perPage: 12, total: 0, totalPages: 0,
  });

  const [filters, setFilters] = useState({
    search: searchParams.get('q') || '',
    teamType: searchParams.get('team_type') || '',
    status: searchParams.get('status') || 'active',
  });

  const fetchTeams = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params = {
        page: pagination.page, per_page: pagination.perPage,
        q: filters.search || undefined,
        team_type: filters.teamType || undefined,
        active: filters.status === 'active' ? '1' : filters.status === 'inactive' ? '0' : undefined,
      };
      const data = await teamService.getTeams(params);
      setTeams(data.teams || []);
      setPagination(prev => ({ ...prev, total: data.total || 0, totalPages: data.total_pages || 0 }));
    } catch (err) {
      console.error('Error fetching teams:', err);
      setError('Errore nel caricamento dei team');
    } finally { setLoading(false); }
  }, [pagination.page, pagination.perPage, filters]);

  useEffect(() => { fetchTeams(); }, [fetchTeams]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, page: 1 }));
    const newParams = new URLSearchParams(searchParams);
    if (value) newParams.set(key === 'search' ? 'q' : key === 'teamType' ? 'team_type' : key, value);
    else newParams.delete(key === 'search' ? 'q' : key === 'teamType' ? 'team_type' : key);
    setSearchParams(newParams);
  };

  const handlePageChange = (p) => setPagination(prev => ({ ...prev, page: p }));

  const resetFilters = () => {
    setFilters({ search: '', teamType: '', status: '' });
    setSearchParams(new URLSearchParams());
  };

  const getPageNumbers = () => {
    const pages = [], total = pagination.totalPages, current = pagination.page;
    if (total <= 5) { for (let i = 1; i <= total; i++) pages.push(i); }
    else if (current <= 3) { for (let i = 1; i <= 5; i++) pages.push(i); }
    else if (current >= total - 2) { for (let i = total - 4; i <= total; i++) pages.push(i); }
    else { for (let i = current - 2; i <= current + 2; i++) pages.push(i); }
    return pages;
  };

  const statCards = [
    { key: 'total', label: 'Team Totali', value: pagination.total, icon: 'ri-team-line' },
    { key: 'nutrizione', label: 'Nutrizione', value: teams.filter(t => t.team_type === 'nutrizione').length, icon: TEAM_TYPE_ICONS.nutrizione },
    { key: 'coach', label: 'Coach', value: teams.filter(t => t.team_type === 'coach').length, icon: TEAM_TYPE_ICONS.coach },
    { key: 'psicologia', label: 'Psicologia', value: teams.filter(t => t.team_type === 'psicologia').length, icon: TEAM_TYPE_ICONS.psicologia },
  ];

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="tl-header">
        <div>
          <h4>Gestione Team</h4>
          <p className="tl-header-sub">{pagination.total} team totali</p>
        </div>
        {isAdminOrCco && (
          <Link to="/teams-nuovo" className="tl-action-pill primary">
            <i className="ri-add-line"></i> Nuovo Team
          </Link>
        )}
      </div>

      {/* Stats */}
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

      {/* Search + Filters */}
      <div className="tl-search-row">
        <div className="tl-search-wrap">
          <i className="ri-search-line tl-search-icon"></i>
          <input
            type="text" className="tl-search-input"
            placeholder="Cerca per nome..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
          />
        </div>
        <select className="tl-filter-select" value={filters.teamType} onChange={(e) => handleFilterChange('teamType', e.target.value)}>
          <option value="">Tutti i Tipi</option>
          {Object.entries(TEAM_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
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
      ) : teams.length === 0 ? (
        <div className="tl-empty">
          <div className="tl-empty-icon"><i className="ri-team-line"></i></div>
          <h5 className="tl-empty-title">Nessun team trovato</h5>
          <p className="tl-empty-desc">Prova a modificare i filtri di ricerca</p>
          <button className="tl-empty-btn" onClick={resetFilters}>
            <i className="ri-refresh-line"></i> Reset Filtri
          </button>
        </div>
      ) : (
        <>
          <div className="tl-grid">
            {teams.map((team) => {
              const leaderAvatar = normalizeAvatarPath(team.head?.avatar_path || team.head?.avatar_url);
              const leaderInitials = `${team.head?.first_name?.[0] || ''}${team.head?.last_name?.[0] || ''}`.toUpperCase();
              const leaderDisplayName = team.head?.full_name || 'Nessun leader';

              return (
                <div key={team.id} className="tl-card">
                  <div className="tl-card-header" style={{ background: TYPE_GRADIENTS[team.team_type] || TYPE_GRADIENTS.nutrizione }}>
                    <div className="tl-card-badges">
                      {!team.is_active && (
                        <span className="tl-mini-badge dark"><i className="ri-close-circle-line"></i> Inattivo</span>
                      )}
                    </div>
                    <div className="tl-card-badge-right">
                      <span className="tl-mini-badge light">{TEAM_TYPE_LABELS[team.team_type]}</span>
                    </div>
                    <div className="tl-avatar-wrap">
                      {leaderAvatar ? (
                        <img src={leaderAvatar} alt={team.head?.full_name || 'Team leader'} className="tl-avatar" />
                      ) : leaderInitials ? (
                        <div className="tl-avatar-initials">{leaderInitials}</div>
                      ) : (
                        <div className="tl-avatar-initials">
                          <i className={`${TEAM_TYPE_ICONS[team.team_type]}`} style={{ fontSize: '22px' }}></i>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="tl-card-body">
                    <div className="tl-card-name">
                      <Link to={`/teams-dettaglio/${team.id}`}>{leaderDisplayName}</Link>
                    </div>
                    <div className="tl-card-sub">{team.name || 'Team senza nome'}</div>
                    <div className="tl-card-sub" style={{ marginTop: '-4px' }}>
                      {TEAM_TYPE_LABELS[team.team_type]} &bull; {team.member_count || 0} membri
                    </div>
                  </div>

                  <div className="tl-card-footer">
                    <Link to={`/teams-dettaglio/${team.id}`} className="tl-card-action">
                      <i className="ri-eye-line"></i> Dettagli
                    </Link>
                    {isAdminOrCco && (
                      <Link to={`/teams-modifica/${team.id}`} className="tl-card-action">
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

export default TeamsList;

import { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import teamService, {
  ROLE_LABELS,
  SPECIALTY_LABELS,
  SPECIALTY_FILTER_OPTIONS,
  ROLE_COLORS,

  SPECIALTY_COLORS
} from '../../services/teamService';
import { useAuth } from '../../context/AuthContext';
import GuidedTour from '../../components/GuidedTour';
import SupportWidget from '../../components/SupportWidget';
import { FaUserShield, FaUsers, FaUserTie, FaUserCog, FaFilter, FaTable, FaEye, FaArrowRight } from 'react-icons/fa';
import '../clienti/clienti-responsive.css';
import '../clienti/clienti-table.css';

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

const normalizeAvatarPath = (avatarPath) => {
  if (!avatarPath) return null;
  const rawPath = String(avatarPath).trim();
  if (!rawPath) return null;

  // Keep data/blob URLs as is.
  if (/^(data:|blob:)/i.test(rawPath)) return rawPath;

  // Normalize legacy absolute URLs to same-origin upload paths.
  if (/^https?:\/\//i.test(rawPath) || rawPath.startsWith('//')) {
    try {
      const parsed = new URL(rawPath, window.location.origin);
      const pathname = parsed.pathname || '';
      if (pathname.startsWith('/uploads/')) return `${pathname}${parsed.search || ''}`;
      if (pathname.startsWith('/avatars/')) return `/uploads${pathname}${parsed.search || ''}`;
      if (pathname.startsWith('/')) return `${pathname}${parsed.search || ''}`;
      return `/uploads/avatars/${pathname}${parsed.search || ''}`;
    } catch {
      return rawPath;
    }
  }

  if (rawPath.startsWith('/uploads/')) return rawPath;
  if (rawPath.startsWith('uploads/')) return `/${rawPath}`;
  if (rawPath.startsWith('/avatars/')) return `/uploads${rawPath}`;
  if (rawPath.startsWith('avatars/')) return `/uploads/${rawPath}`;
  if (rawPath.startsWith('/')) return rawPath;

  return `/uploads/avatars/${rawPath}`;
};

function TeamList() {
  const { user } = useAuth();
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

  const [mostraTour, setMostraTour] = useState(false);

  // Effetto per avvio automatico tour da Hub Supporto
  useEffect(() => {
    if (searchParams.get('startTour') === 'true') {
      setMostraTour(true);
    }
  }, [searchParams]);

  const tourSteps = [
    {
      target: '[data-tour="header"]',
      title: 'Gestione Team',
      content: 'In questa sezione puoi gestire tutti i professionisti della clinica, monitorare il loro stato e i ruoli assegnati.',
      placement: 'bottom',
      icon: <FaUsers size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)'
    },
    {
      target: '[data-tour="stats"]',
      title: 'Statistiche Team',
      content: 'Visualizza rapidamente il numero totale di membri, quanti sono attivi, i team leader e i collaboratori esterni.',
      placement: 'bottom',
      icon: <FaUsers size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #10B981, #34D399)'
    },
    {
      target: '[data-tour="filters"]',
      title: 'Filtri Avanzati',
      content: 'Cerca per nome, email o filtra per ruolo, specializzazione e stato per trovare rapidamente chi cerchi.',
      placement: 'bottom',
      icon: <FaFilter size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)'
    },
    {
      target: '[data-tour="table"]',
      title: 'Lista Professionisti',
      content: 'La tabella mostra tutti i dettagli chiave. Puoi vedere a colpo d\'occhio chi è leader di un team, il ruolo e la specializzazione.',
      placement: 'top',
      icon: <FaTable size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #3B82F6, #60A5FA)'
    },
    {
      target: '[data-tour="actions"]',
      title: 'Azioni Rapide',
      content: 'Accedi al profilo completo per visualizzare il carico clienti e le performance, oppure modifica i dati del professionista.',
      placement: 'left',
      icon: <FaEye size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #8B5CF6, #D946EF)'
    }
  ];

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
    const fetchStats = async () => {
      try {
        const stats = await teamService.getStats();
        setGlobalStats(stats);
      } catch (err) {
        console.error('Error fetching stats:', err);
      }
    };
    fetchStats();
  }, []);

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
    fetchMembers();
  }, [fetchMembers]);

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
  const totalMembers = hasActiveFilters ? pagination.total : (globalStats?.total_members || pagination.total);
  const totalActive = hasActiveFilters ? members.filter(m => m.is_active).length : (globalStats?.total_active || pagination.total);
  const totalLeaders = hasActiveFilters ? members.filter(m => m.role === 'team_leader').length : (globalStats?.total_team_leaders || 0);
  const totalExternal = hasActiveFilters ? members.filter(m => m.is_external).length : (globalStats?.total_external || 0);

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4" data-tour="header">
        <div>
          <h4 className="mb-1">Gestione Team</h4>
          <p className="text-muted mb-0">{pagination.total} membri totali</p>
        </div>
        {(user?.is_admin || user?.role === 'admin') && (
          <Link to="/team-nuovo" className="btn btn-primary">
            <i className="ri-user-add-line me-1"></i>
            Nuovo Professionista
          </Link>
        )}
      </div>

      {/* Stats Row */}
      <div className="row g-3 mb-4 clienti-stats-row" data-tour="stats">
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

      {/* Filters */}
      <div className="card shadow-sm border-0 mb-4" data-tour="filters">
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
                {Object.entries(ROLE_LABELS).map(([value, label]) => (
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
          {/* Tabella Team */}
          <div className="card border-0 clienti-table-wrap ct-card" data-tour="table">
            <div className="table-responsive">
              <table className="table mb-0 clienti-table">
                <thead className="ct-thead">
                  <tr>
                    <th className="ct-th" style={{ minWidth: '200px' }}>Professionista</th>
                    <th className="ct-th" style={{ minWidth: '150px' }}>Ruolo</th>
                    <th className="ct-th" style={{ minWidth: '150px' }}>Specializzazione</th>
                    <th className="ct-th" style={{ minWidth: '150px' }}>Info Team</th>
                    <th className="ct-th" style={{ minWidth: '120px' }}>Stato</th>
                    <th className="ct-th" style={{ textAlign: 'right', minWidth: '120px' }}>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((member, index) => {
                    const avatarSrc = normalizeAvatarPath(member.avatar_path);
                    const showAvatar = avatarSrc && !brokenAvatars[member.id];
                    const initials = `${member.first_name?.[0] || ''}${member.last_name?.[0] || ''}`.toUpperCase();
                    const specGradient = SPECIALTY_GRADIENTS[member.specialty] || DEFAULT_GRADIENT;

                    return (
                      <tr key={member.id} className="ct-row">
                        {/* Professionista */}
                        <td className="ct-td" data-label="Professionista">
                          <div className="d-flex align-items-center gap-3">
                            {showAvatar ? (
                              <img
                                src={avatarSrc}
                                alt={member.full_name}
                                className="ct-avatar-init"
                                style={{ objectFit: 'cover' }}
                                onError={() => setBrokenAvatars(prev => ({ ...prev, [member.id]: true }))}
                              />
                            ) : (
                              <div
                                className="ct-avatar-init"
                                style={{ background: specGradient, color: '#fff' }}
                              >
                                {initials}
                              </div>
                            )}
                            <Link to={`/team-dettaglio/${member.id}`} className="ct-name-link">
                              {member.full_name || `${member.first_name} ${member.last_name}`}
                            </Link>
                          </div>
                        </td>

                        {/* Ruolo */}
                        <td className="ct-td" data-label="Ruolo">
                          <span className={`badge rounded-pill px-2 py-1 bg-${ROLE_COLORS[member.role] || 'secondary'}`} style={{ fontSize: '11px' }}>
                            {ROLE_LABELS[member.role] || member.role || 'N/D'}
                          </span>
                        </td>

                        {/* Specializzazione */}
                        <td className="ct-td" data-label="Specializzazione">
                          {member.specialty ? (
                            <span className={`badge rounded-pill px-2 py-1 bg-${SPECIALTY_COLORS[member.specialty] || 'secondary'}-subtle text-${SPECIALTY_COLORS[member.specialty] || 'secondary'}`} style={{ fontSize: '11px' }}>
                              {SPECIALTY_LABELS[member.specialty] || member.specialty}
                            </span>
                          ) : (
                            <span className="ct-empty">—</span>
                          )}
                        </td>

                        {/* Info Team (Leader di...) */}
                        <td className="ct-td" data-label="Info Team">
                          {member.teams_led?.length > 0 ? (
                            <span className="text-primary small fw-semibold">
                              <i className="ri-team-line me-1"></i>
                              Leader di {member.teams_led.length} team
                            </span>
                          ) : member.is_external ? (
                            <span className="badge bg-light text-dark small">
                              <i className="ri-external-link-line me-1"></i>Esterno
                            </span>
                          ) : (
                            <span className="ct-empty">—</span>
                          )}
                        </td>

                        {/* Stato */}
                        <td className="ct-td" data-label="Stato">
                          {member.is_active ? (
                            <span className="badge bg-success-subtle text-success px-2 py-1" style={{ fontSize: '11px' }}>
                              <i className="ri-checkbox-circle-line me-1"></i>Attivo
                            </span>
                          ) : (
                            <span className="badge bg-dark bg-opacity-75 text-white px-2 py-1" style={{ fontSize: '11px' }}>
                              <i className="ri-close-circle-line me-1"></i>Inattivo
                            </span>
                          )}
                        </td>

                        {/* Azioni */}
                        <td className="ct-td" style={{ textAlign: 'right' }} data-label="Azioni" data-tour={index === 0 ? "actions" : undefined}>
                          <Link
                            to={`/team-dettaglio/${member.id}`}
                            className="ct-action-btn"
                            style={{ borderColor: '#22c55e', color: '#22c55e' }}
                            title="Dettaglio"
                          >
                            <i className="ri-eye-line" style={{ fontSize: '16px' }}></i>
                          </Link>
                          <Link
                            to={`/team-modifica/${member.id}`}
                            className="ct-action-btn"
                            style={{ borderColor: '#3b82f6', color: '#3b82f6' }}
                            title="Modifica"
                          >
                            <i className="ri-edit-line" style={{ fontSize: '16px' }}></i>
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {pagination.totalPages > 1 && (
            <div className="d-flex justify-content-between align-items-center mt-4 pt-3 border-top clienti-pagination">
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

      {/* Support and Tour Components */}
      <SupportWidget
        pageTitle="Gestione Team"
        pageDescription="In questa pagina puoi gestire tutti i membri del team, filtrare per ruolo e specialità, e accedere ai profili completi."
        pageIcon={FaUsers}
        docsSection="gestione-team"
        onStartTour={() => setMostraTour(true)}
        brandName="Suite Clinica"
        logoSrc="/suitemind.png"
        accentColor="#85FF00"
      />

      <GuidedTour
        steps={tourSteps}
        isOpen={mostraTour}
        onClose={() => setMostraTour(false)}
        onComplete={() => {
          setMostraTour(false);
          console.log('Tour Gestione Team completato');
        }}
      />
    </div>
  );
}

export default TeamList;

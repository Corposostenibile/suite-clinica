import { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import dashboardService from '../services/dashboardService';
import logoFoglia from '../images/logo_foglia.png';

function Welcome() {
  const { user } = useOutletContext();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [checkStats, setCheckStats] = useState(null);
  const [negativeChecks, setNegativeChecks] = useState([]);
  const [rankings, setRankings] = useState(null);
  const [teamRatings, setTeamRatings] = useState(null);
  const [negativePage, setNegativePage] = useState(1);
  const NEGATIVE_PER_PAGE = 5;

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      // Fetch dashboard data and teams in parallel
      const [data, teams] = await Promise.all([
        dashboardService.getDashboardData(),
        dashboardService.getTeamsWithMembers()
      ]);

      setStats(data.customers);
      setCheckStats(data.checks);

      // Filter negative checks
      if (data.checks?.responses) {
        const negative = dashboardService.filterNegativeChecks(data.checks.responses);
        setNegativeChecks(negative); // All negative checks
        setNegativePage(1); // Reset to first page

        // Calculate rankings
        const ranks = dashboardService.calculateProfessionalRankings(data.checks.responses);
        setRankings(ranks);

        // Calculate per-team ratings
        if (teams && teams.length > 0) {
          const teamRatingsData = dashboardService.calculateTeamRatings(data.checks.responses, teams);
          setTeamRatings(teamRatingsData);
        }
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="d-flex align-items-center justify-content-center" style={{ minHeight: '400px' }}>
        <div className="text-center">
          <div className="spinner-border text-success mb-3" role="status">
            <span className="visually-hidden">Caricamento...</span>
          </div>
          <p className="text-muted">Caricamento dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Page Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1" style={{ fontWeight: 700, color: '#1e293b' }}>
            Ciao, {user?.first_name || 'Admin'}!
          </h4>
          <p className="text-muted mb-0">Panoramica Dashboard Amministrativa</p>
        </div>
        <div className="d-flex gap-2">
          <button
            onClick={loadDashboardData}
            className="btn btn-light d-flex align-items-center gap-2"
            style={{ borderRadius: '12px' }}
          >
            <i className="ri-refresh-line"></i>
            Aggiorna
          </button>
        </div>
      </div>

      {/* SEZIONE 1: KPI Cards */}
      <div className="row g-3 mb-4">
        <KPICard
          label="Pazienti Totali"
          value={stats?.total_clienti || 0}
          icon="ri-group-line"
          gradient="linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)"
          shadow="rgba(59, 130, 246, 0.3)"
        />
        <KPICard
          label="Nutrizione Attivi"
          value={stats?.nutrizione_attivo || 0}
          icon="ri-heart-pulse-line"
          gradient="linear-gradient(135deg, #22c55e 0%, #16a34a 100%)"
          shadow="rgba(34, 197, 94, 0.3)"
        />
        <KPICard
          label="Coach Attivi"
          value={stats?.coach_attivo || 0}
          icon="ri-run-line"
          gradient="linear-gradient(135deg, #f97316 0%, #ea580c 100%)"
          shadow="rgba(249, 115, 22, 0.3)"
        />
        <KPICard
          label="Psicologia Attivi"
          value={stats?.psicologia_attivo || 0}
          icon="ri-mental-health-line"
          gradient="linear-gradient(135deg, #ec4899 0%, #db2777 100%)"
          shadow="rgba(236, 72, 153, 0.3)"
        />
        <KPICard
          label="Nuovi questo Mese"
          value={stats?.kpi?.new_month || 0}
          icon="ri-user-add-line"
          gradient="linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)"
          shadow="rgba(139, 92, 246, 0.3)"
        />
      </div>

      {/* SEZIONE 2: Valutazioni Medie per Team */}
      <div className="row g-3 mb-4">
        <div className="col-12">
          <h5 className="mb-3" style={{ fontWeight: 600, color: '#1e293b' }}>
            <i className="ri-bar-chart-grouped-line me-2"></i>
            Valutazioni Medie per Team (Ultimo Mese)
          </h5>
        </div>
        <RatingCard
          label="Team Nutrizione"
          value={checkStats?.stats?.avg_nutrizionista}
          icon="ri-heart-pulse-line"
          color="#22c55e"
          bgColor="#dcfce7"
        />
        <RatingCard
          label="Team Coach"
          value={checkStats?.stats?.avg_coach}
          icon="ri-run-line"
          color="#f97316"
          bgColor="#ffedd5"
        />
        <RatingCard
          label="Team Psicologia"
          value={checkStats?.stats?.avg_psicologo}
          icon="ri-mental-health-line"
          color="#ec4899"
          bgColor="#fce7f3"
        />
      </div>

      {/* SEZIONE 2B: Valutazioni per Singolo Team */}
      {teamRatings && (teamRatings.nutrizione.length > 0 || teamRatings.coach.length > 0 || teamRatings.psicologia.length > 0) && (
        <div className="row g-3 mb-4">
          <div className="col-12">
            <h5 className="mb-3" style={{ fontWeight: 600, color: '#1e293b' }}>
              <i className="ri-team-line me-2"></i>
              Valutazioni per Singolo Team (Ultimo Mese)
            </h5>
          </div>

          {/* Nutrizione Teams */}
          {teamRatings.nutrizione.length > 0 && (
            <div className="col-lg-4">
              <TeamRatingsList
                title="Team Nutrizione"
                teams={teamRatings.nutrizione}
                icon="ri-heart-pulse-line"
                color="#22c55e"
                bgColor="#dcfce7"
              />
            </div>
          )}

          {/* Coach Teams */}
          {teamRatings.coach.length > 0 && (
            <div className="col-lg-4">
              <TeamRatingsList
                title="Team Coach"
                teams={teamRatings.coach}
                icon="ri-run-line"
                color="#f97316"
                bgColor="#ffedd5"
              />
            </div>
          )}

          {/* Psicologia Teams */}
          {teamRatings.psicologia.length > 0 && (
            <div className="col-lg-4">
              <TeamRatingsList
                title="Team Psicologia"
                teams={teamRatings.psicologia}
                icon="ri-mental-health-line"
                color="#ec4899"
                bgColor="#fce7f3"
              />
            </div>
          )}
        </div>
      )}

      {/* SEZIONE 3: Check Negativi */}
      {(() => {
        const totalPages = Math.ceil(negativeChecks.length / NEGATIVE_PER_PAGE);
        const startIdx = (negativePage - 1) * NEGATIVE_PER_PAGE;
        const paginatedChecks = negativeChecks.slice(startIdx, startIdx + NEGATIVE_PER_PAGE);

        return (
          <div className="card border-0 mb-4" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
            <div className="card-header bg-white border-0 py-3 px-4" style={{ borderRadius: '16px 16px 0 0' }}>
              <h5 className="mb-0" style={{ fontWeight: 600, color: '#1e293b' }}>
                <i className="ri-alert-line me-2 text-danger"></i>
                Check Negativi Ultimo Mese
                <span className="badge bg-danger ms-2" style={{ fontSize: '12px' }}>{negativeChecks.length}</span>
              </h5>
            </div>
            <div className="card-body p-0">
              {negativeChecks.length > 0 ? (
                <>
                  <div className="table-responsive">
                    <table className="table mb-0">
                      <thead>
                        <tr style={{ background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)' }}>
                          <th style={tableHeaderStyle}>Paziente</th>
                          <th style={tableHeaderStyle}>Data</th>
                          <th style={tableHeaderStyle}>Rating Negativi</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedChecks.map((check, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                            <td style={tableCellStyle}>
                              <span style={{ fontWeight: 600, color: '#334155' }}>{check.cliente_nome}</span>
                            </td>
                            <td style={tableCellStyle}>
                              <span className="text-muted">{check.submit_date}</span>
                            </td>
                            <td style={tableCellStyle}>
                              <div className="d-flex flex-wrap gap-2">
                                {check.negativeRatings?.map((r, i) => (
                                  <div
                                    key={i}
                                    className="d-flex align-items-center gap-2"
                                    style={{
                                      background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',
                                      padding: '6px 12px',
                                      borderRadius: '8px',
                                    }}
                                  >
                                    {/* Avatar o Logo */}
                                    {r.isProgress ? (
                                      <img
                                        src={logoFoglia}
                                        alt="Percorso"
                                        style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover' }}
                                      />
                                    ) : r.professionals && r.professionals.length > 0 ? (
                                      <div className="d-flex" style={{ marginLeft: '-4px' }}>
                                        {r.professionals.slice(0, 2).map((prof, pi) => (
                                          prof.avatar_path ? (
                                            <img
                                              key={pi}
                                              src={prof.avatar_path}
                                              alt=""
                                              style={{
                                                width: '24px',
                                                height: '24px',
                                                borderRadius: '50%',
                                                objectFit: 'cover',
                                                border: '2px solid #fee2e2',
                                                marginLeft: pi > 0 ? '-8px' : '0'
                                              }}
                                              onError={(e) => { e.target.style.display = 'none'; }}
                                            />
                                          ) : (
                                            <div
                                              key={pi}
                                              style={{
                                                width: '24px',
                                                height: '24px',
                                                borderRadius: '50%',
                                                background: '#991b1b',
                                                color: '#fff',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                fontSize: '10px',
                                                fontWeight: 700,
                                                border: '2px solid #fee2e2',
                                                marginLeft: pi > 0 ? '-8px' : '0'
                                              }}
                                            >
                                              {prof.nome?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                                            </div>
                                          )
                                        ))}
                                      </div>
                                    ) : null}
                                    <span style={{ color: '#991b1b', fontWeight: 600, fontSize: '12px' }}>
                                      {r.type}: {r.value}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {/* Paginazione */}
                  {totalPages > 1 && (
                    <div className="d-flex align-items-center justify-content-between px-4 py-3 border-top">
                      <span className="text-muted" style={{ fontSize: '13px' }}>
                        {startIdx + 1}-{Math.min(startIdx + NEGATIVE_PER_PAGE, negativeChecks.length)} di {negativeChecks.length}
                      </span>
                      <div className="d-flex gap-2">
                        <button
                          className="btn btn-sm btn-light"
                          style={{ borderRadius: '8px' }}
                          onClick={() => setNegativePage(p => Math.max(1, p - 1))}
                          disabled={negativePage === 1}
                        >
                          <i className="ri-arrow-left-s-line"></i> Prec
                        </button>
                        <button
                          className="btn btn-sm btn-light"
                          style={{ borderRadius: '8px' }}
                          onClick={() => setNegativePage(p => Math.min(totalPages, p + 1))}
                          disabled={negativePage === totalPages}
                        >
                          Succ <i className="ri-arrow-right-s-line"></i>
                        </button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-5">
                  <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '48px' }}></i>
                  <p className="text-muted mt-2 mb-0">Nessun check negativo questo mese</p>
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* SEZIONE 4: Top 5 Professionisti */}
      <div className="row g-3 mb-4">
        <div className="col-12">
          <h5 className="mb-3" style={{ fontWeight: 600, color: '#1e293b' }}>
            <i className="ri-trophy-line me-2 text-warning"></i>
            Top 5 Professionisti (Ultimo Mese)
          </h5>
        </div>
        <div className="col-lg-4">
          <RankingTable
            title="Nutrizione"
            professionals={rankings?.nutrizione?.top || []}
            color="#22c55e"
            bgColor="#dcfce7"
            icon="ri-heart-pulse-line"
            isTop={true}
          />
        </div>
        <div className="col-lg-4">
          <RankingTable
            title="Coach"
            professionals={rankings?.coach?.top || []}
            color="#f97316"
            bgColor="#ffedd5"
            icon="ri-run-line"
            isTop={true}
          />
        </div>
        <div className="col-lg-4">
          <RankingTable
            title="Psicologia"
            professionals={rankings?.psicologia?.top || []}
            color="#ec4899"
            bgColor="#fce7f3"
            icon="ri-mental-health-line"
            isTop={true}
          />
        </div>
      </div>

      {/* SEZIONE 5: Peggiori 5 Professionisti */}
      <div className="row g-3 mb-4">
        <div className="col-12">
          <h5 className="mb-3" style={{ fontWeight: 600, color: '#1e293b' }}>
            <i className="ri-arrow-down-circle-line me-2 text-danger"></i>
            Professionisti da Migliorare (Ultimo Mese)
          </h5>
        </div>
        <div className="col-lg-4">
          <RankingTable
            title="Nutrizione"
            professionals={rankings?.nutrizione?.bottom || []}
            color="#22c55e"
            bgColor="#dcfce7"
            icon="ri-heart-pulse-line"
            isTop={false}
          />
        </div>
        <div className="col-lg-4">
          <RankingTable
            title="Coach"
            professionals={rankings?.coach?.bottom || []}
            color="#f97316"
            bgColor="#ffedd5"
            icon="ri-run-line"
            isTop={false}
          />
        </div>
        <div className="col-lg-4">
          <RankingTable
            title="Psicologia"
            professionals={rankings?.psicologia?.bottom || []}
            color="#ec4899"
            bgColor="#fce7f3"
            icon="ri-mental-health-line"
            isTop={false}
          />
        </div>
      </div>
    </>
  );
}

// ==================== COMPONENTI ====================

function KPICard({ label, value, icon, gradient, shadow }) {
  return (
    <div className="col-xl col-sm-6">
      <div
        className="card border-0"
        style={{
          borderRadius: '16px',
          background: gradient,
          boxShadow: `0 4px 15px ${shadow}`,
          overflow: 'hidden'
        }}
      >
        <div className="card-body p-4">
          <div className="d-flex align-items-center justify-content-between">
            <div>
              <h2 className="mb-1 text-white" style={{ fontWeight: 700, fontSize: '2rem' }}>
                {value}
              </h2>
              <p className="mb-0 text-white" style={{ opacity: 0.85, fontSize: '13px', fontWeight: 500 }}>
                {label}
              </p>
            </div>
            <div
              className="d-flex align-items-center justify-content-center"
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '12px',
                background: 'rgba(255,255,255,0.2)'
              }}
            >
              <i className={`${icon} text-white`} style={{ fontSize: '24px' }}></i>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function RatingCard({ label, value, icon, color, bgColor }) {
  const rating = value ? parseFloat(value).toFixed(1) : '-';
  const numericValue = value ? parseFloat(value) : 0;

  // Determina stato: >= 8 buono, 7-8 da migliorare, < 7 male
  const getRatingStatus = () => {
    if (!value) return null;
    if (numericValue >= 8) {
      return { label: 'Buono', bg: '#dcfce7', color: '#166534' };
    } else if (numericValue >= 7) {
      return { label: 'Da migliorare', bg: '#fef3c7', color: '#92400e' };
    } else {
      return { label: 'Male', bg: '#fee2e2', color: '#991b1b' };
    }
  };

  const status = getRatingStatus();

  return (
    <div className="col-lg-4 col-sm-6">
      <div
        className="card border-0"
        style={{
          borderRadius: '16px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.08)'
        }}
      >
        <div className="card-body p-4">
          <div className="d-flex align-items-center">
            <div
              className="d-flex align-items-center justify-content-center me-3"
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '12px',
                background: bgColor
              }}
            >
              <i className={icon} style={{ fontSize: '24px', color: color }}></i>
            </div>
            <div className="flex-grow-1">
              <p className="mb-1 text-muted" style={{ fontSize: '13px' }}>{label}</p>
              <div className="d-flex align-items-center gap-2">
                <h3 className="mb-0" style={{ fontWeight: 700, color: '#1e293b' }}>{rating}</h3>
                <span className="text-muted" style={{ fontSize: '14px' }}>/10</span>
                {status && (
                  <span
                    className="badge"
                    style={{
                      background: status.bg,
                      color: status.color,
                      fontSize: '11px',
                      padding: '4px 8px',
                      borderRadius: '6px'
                    }}
                  >
                    {status.label}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TeamRatingsList({ title, teams, icon, color, bgColor }) {
  // Determina stato: >= 8 buono, 7-8 da migliorare, < 7 male
  const getRatingStatus = (value) => {
    const numericValue = parseFloat(value);
    if (numericValue >= 8) {
      return { label: 'Buono', bg: '#dcfce7', color: '#166534' };
    } else if (numericValue >= 7) {
      return { label: 'Da migliorare', bg: '#fef3c7', color: '#92400e' };
    } else {
      return { label: 'Male', bg: '#fee2e2', color: '#991b1b' };
    }
  };

  return (
    <div
      className="card border-0"
      style={{
        borderRadius: '16px',
        boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        overflow: 'hidden'
      }}
    >
      <div
        className="card-header border-0 py-3 px-4"
        style={{ background: bgColor }}
      >
        <div className="d-flex align-items-center">
          <i className={icon} style={{ color: color, fontSize: '20px', marginRight: '8px' }}></i>
          <h6 className="mb-0" style={{ fontWeight: 600, color: color }}>{title}</h6>
        </div>
      </div>
      <div className="card-body p-0">
        {teams.length > 0 ? (
          <div className="list-group list-group-flush">
            {teams.map((team, idx) => {
              const status = getRatingStatus(team.average);
              return (
                <div
                  key={team.id || idx}
                  className="list-group-item d-flex align-items-center justify-content-between py-3 px-4"
                  style={{ border: 'none', borderBottom: '1px solid #f1f5f9' }}
                >
                  <div className="d-flex align-items-center">
                    {/* Team head avatar or initials */}
                    {team.head?.avatar_path ? (
                      <img
                        src={team.head.avatar_path}
                        alt=""
                        className="rounded-circle me-3"
                        style={{
                          width: '36px',
                          height: '36px',
                          objectFit: 'cover',
                          border: `2px solid ${color}`
                        }}
                      />
                    ) : (
                      <div
                        className="d-flex align-items-center justify-content-center me-3"
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: '50%',
                          background: bgColor,
                          color: color,
                          fontWeight: 700,
                          fontSize: '12px'
                        }}
                      >
                        {team.head?.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || team.name?.substring(0, 2).toUpperCase()}
                      </div>
                    )}
                    <div>
                      <span style={{ fontWeight: 600, color: '#334155', fontSize: '14px', display: 'block' }}>
                        {team.name}
                      </span>
                      {team.head && (
                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                          {team.head.full_name}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="d-flex align-items-center gap-2">
                    <span
                      style={{
                        fontWeight: 700,
                        fontSize: '16px',
                        color: parseFloat(team.average) >= 7 ? '#22c55e' : '#ef4444'
                      }}
                    >
                      {team.average}
                    </span>
                    <span className="text-muted" style={{ fontSize: '12px' }}>
                      ({team.count})
                    </span>
                    <span
                      className="badge"
                      style={{
                        background: status.bg,
                        color: status.color,
                        fontSize: '10px',
                        padding: '3px 6px',
                        borderRadius: '6px'
                      }}
                    >
                      {status.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-4">
            <p className="text-muted mb-0" style={{ fontSize: '13px' }}>
              Nessun team trovato
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function RankingTable({ title, professionals, color, bgColor, icon, isTop }) {
  const [page, setPage] = useState(1);
  const PER_PAGE = 5;
  const totalPages = Math.ceil(professionals.length / PER_PAGE);
  const startIdx = (page - 1) * PER_PAGE;
  const paginatedProfs = professionals.slice(startIdx, startIdx + PER_PAGE);

  return (
    <div
      className="card border-0"
      style={{
        borderRadius: '16px',
        boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
        overflow: 'hidden'
      }}
    >
      <div
        className="card-header border-0 py-3 px-4"
        style={{ background: bgColor }}
      >
        <div className="d-flex align-items-center justify-content-between">
          <div className="d-flex align-items-center">
            <i className={icon} style={{ color: color, fontSize: '20px', marginRight: '8px' }}></i>
            <h6 className="mb-0" style={{ fontWeight: 600, color: color }}>{title}</h6>
          </div>
          {professionals.length > 0 && (
            <span className="badge ms-2" style={{ background: color, color: '#fff', fontSize: '11px' }}>
              {professionals.length}
            </span>
          )}
        </div>
      </div>
      <div className="card-body p-0">
        {professionals.length > 0 ? (
          <>
            <div className="list-group list-group-flush">
              {paginatedProfs.map((prof, idx) => {
                const globalIdx = startIdx + idx;
                return (
                  <div
                    key={prof.id || idx}
                    className="list-group-item d-flex align-items-center justify-content-between py-3 px-4"
                    style={{ border: 'none', borderBottom: '1px solid #f1f5f9' }}
                  >
                    <div className="d-flex align-items-center">
                      <span
                        className="me-3 d-flex align-items-center justify-content-center"
                        style={{
                          width: '28px',
                          height: '28px',
                          borderRadius: '50%',
                          background: isTop
                            ? (globalIdx === 0 ? '#fef3c7' : globalIdx === 1 ? '#e5e7eb' : globalIdx === 2 ? '#fed7aa' : '#f1f5f9')
                            : '#fee2e2',
                          color: isTop
                            ? (globalIdx === 0 ? '#92400e' : globalIdx === 1 ? '#374151' : globalIdx === 2 ? '#c2410c' : '#64748b')
                            : '#991b1b',
                          fontSize: '12px',
                          fontWeight: 700
                        }}
                      >
                        {globalIdx + 1}
                      </span>
                      {prof.avatar_path ? (
                        <img
                          src={prof.avatar_path}
                          alt=""
                          className="rounded-circle me-3"
                          style={{
                            width: '36px',
                            height: '36px',
                            objectFit: 'cover',
                            border: `2px solid ${color}`
                          }}
                        />
                      ) : (
                        <div
                          className="d-flex align-items-center justify-content-center me-3"
                          style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '50%',
                            background: bgColor,
                            color: color,
                            fontWeight: 700,
                            fontSize: '12px'
                          }}
                        >
                          {prof.nome?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || '??'}
                        </div>
                      )}
                      <span style={{ fontWeight: 500, color: '#334155', fontSize: '14px' }}>
                        {prof.nome || 'N/D'}
                      </span>
                    </div>
                    <div className="d-flex align-items-center gap-2">
                      <span
                        style={{
                          fontWeight: 700,
                          fontSize: '16px',
                          color: parseFloat(prof.average) >= 7 ? '#22c55e' : '#ef4444'
                        }}
                      >
                        {prof.average}
                      </span>
                      <span className="text-muted" style={{ fontSize: '12px' }}>
                        ({prof.count} check)
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
            {/* Paginazione */}
            {totalPages > 1 && (
              <div className="d-flex align-items-center justify-content-between px-4 py-2 border-top">
                <span className="text-muted" style={{ fontSize: '11px' }}>
                  {startIdx + 1}-{Math.min(startIdx + PER_PAGE, professionals.length)} di {professionals.length}
                </span>
                <div className="d-flex gap-1">
                  <button
                    className="btn btn-sm btn-light"
                    style={{ borderRadius: '6px', padding: '2px 8px', fontSize: '12px' }}
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <i className="ri-arrow-left-s-line"></i>
                  </button>
                  <button
                    className="btn btn-sm btn-light"
                    style={{ borderRadius: '6px', padding: '2px 8px', fontSize: '12px' }}
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    <i className="ri-arrow-right-s-line"></i>
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-4">
            <p className="text-muted mb-0" style={{ fontSize: '13px' }}>
              Nessun dato disponibile
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ==================== STILI ====================

const tableHeaderStyle = {
  padding: '16px 20px',
  fontSize: '11px',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  color: '#64748b',
  borderBottom: '2px solid #e2e8f0'
};

const tableCellStyle = {
  padding: '16px 20px',
  fontSize: '14px',
  color: '#334155',
  verticalAlign: 'middle'
};

export default Welcome;

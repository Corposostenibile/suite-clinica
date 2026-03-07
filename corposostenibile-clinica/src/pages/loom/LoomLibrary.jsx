import React, { useEffect, useMemo, useState } from 'react';
import Swal from 'sweetalert2';
import { useAuth } from '../../context/AuthContext';
import loomService from '../../services/loomService';
import teamService from '../../services/teamService';
import './LoomLibrary.css';

const formatDateTime = (isoValue) => {
  if (!isoValue) return '-';
  const date = new Date(isoValue);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('it-IT');
};

const getDisplayTitle = (recording) => {
  if (recording?.title?.trim()) return recording.title.trim();
  return 'Registrazione Loom';
};

const getLoomEmbedUrl = (loomLink) => {
  const value = String(loomLink || '').trim();
  if (!value) return '';
  if (value.includes('/embed/')) return value;
  return value.replace('/share/', '/embed/');
};

const LoomLibrary = () => {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [isReloading, setIsReloading] = useState(false);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [associationFilter, setAssociationFilter] = useState('all');
  const [specialtyFilter, setSpecialtyFilter] = useState('all');
  const [teamFilter, setTeamFilter] = useState('all');
  const [sortOrder, setSortOrder] = useState('newest');
  const [page, setPage] = useState(1);
  const [previewLink, setPreviewLink] = useState('');
  const [recordings, setRecordings] = useState([]);
  const [capacityRows, setCapacityRows] = useState([]);
  const pageSize = 12;

  const role = String(user?.role || '');
  const isAdmin = Boolean(user?.is_admin || role === 'admin');
  const isAdminOrTeamLeader = Boolean(isAdmin || role === 'team_leader');
  const canUseCapienzaStyleFilters = isAdmin;

  const specialtyGroups = useMemo(() => ({
    nutrizione: ['nutrizione', 'nutrizionista'],
    coach: ['coach'],
    psicologia: ['psicologia', 'psicologo'],
  }), []);

  const loadRecordings = async ({ silent = false } = {}) => {
    try {
      if (silent) {
        setIsReloading(true);
      } else {
        setIsLoading(true);
      }
      setError(null);
      const requests = [loomService.getRecordings()];
      if (canUseCapienzaStyleFilters) {
        requests.push(teamService.getProfessionalCapacity());
      }
      const [recordingsData, capacityData] = await Promise.all(requests);
      setRecordings(Array.isArray(recordingsData) ? recordingsData : []);
      if (canUseCapienzaStyleFilters) {
        setCapacityRows(Array.isArray(capacityData?.rows) ? capacityData.rows : []);
      } else {
        setCapacityRows([]);
      }
    } catch (err) {
      console.error('[LoomLibrary] load error', err);
      setError('Non riesco a caricare la libreria Loom. Riprova tra poco.');
    } finally {
      setIsLoading(false);
      setIsReloading(false);
    }
  };

  useEffect(() => {
    loadRecordings();
  }, [canUseCapienzaStyleFilters]);

  const submitterMeta = useMemo(() => {
    const map = new Map();
    capacityRows.forEach((row) => {
      map.set(Number(row.user_id), row);
    });
    return map;
  }, [capacityRows]);

  const teamOptions = useMemo(() => {
    if (!canUseCapienzaStyleFilters) return [];
    const base = capacityRows.filter((row) => row.role_type !== 'health_manager');
    const teamMap = new Map();
    base.forEach((row) => {
      (row.teams || []).forEach((team) => {
        if (!teamMap.has(team.id)) teamMap.set(team.id, team);
      });
    });
    return Array.from(teamMap.values()).sort((a, b) => {
      if ((a.team_type || '') !== (b.team_type || '')) return (a.team_type || '').localeCompare(b.team_type || '');
      return (a.name || '').localeCompare(b.name || '');
    });
  }, [canUseCapienzaStyleFilters, capacityRows]);

  const filteredRecordings = useMemo(() => {
    const q = query.trim().toLowerCase();
    return recordings.filter((item) => {
      if (associationFilter === 'associated' && !item?.cliente_id) return false;
      if (associationFilter === 'unassociated' && item?.cliente_id) return false;
      if (canUseCapienzaStyleFilters) {
        const meta = submitterMeta.get(Number(item?.submitter_user_id));
        const specialty = String(meta?.specialty || '').toLowerCase();
        const teams = meta?.teams || [];
        if (specialtyFilter !== 'all') {
          const allowed = specialtyGroups[specialtyFilter] || [];
          if (!allowed.includes(specialty)) return false;
        }
        if (teamFilter !== 'all') {
          if (!teams.some((team) => Number(team.id) === Number(teamFilter))) return false;
        }
      }
      if (!q) return true;
      const fields = [
        item?.title,
        item?.note,
        item?.cliente_name,
        item?.submitter_user_name,
        item?.loom_link,
      ];
      return fields.some((value) => String(value || '').toLowerCase().includes(q));
    });
  }, [query, associationFilter, canUseCapienzaStyleFilters, specialtyFilter, teamFilter, submitterMeta, specialtyGroups, recordings]);

  const sortedRecordings = useMemo(() => {
    const rows = [...filteredRecordings];
    rows.sort((a, b) => {
      const aTs = new Date(a?.created_at || 0).getTime();
      const bTs = new Date(b?.created_at || 0).getTime();
      if (sortOrder === 'oldest') return aTs - bTs;
      return bTs - aTs;
    });
    return rows;
  }, [filteredRecordings, sortOrder]);

  const totalPages = Math.max(1, Math.ceil(sortedRecordings.length / pageSize));
  const pagedRecordings = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedRecordings.slice(start, start + pageSize);
  }, [sortedRecordings, page]);

  useEffect(() => {
    setPage(1);
  }, [query, associationFilter, specialtyFilter, teamFilter, sortOrder]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const stats = useMemo(() => {
    const associated = recordings.filter((r) => Boolean(r?.cliente_id)).length;
    return {
      total: recordings.length,
      associated,
      unassociated: recordings.length - associated,
    };
  }, [recordings]);

  const showTeamGrouping = canUseCapienzaStyleFilters && teamFilter === 'all';
  const groupedRecordings = useMemo(() => {
    if (!showTeamGrouping) {
      return [{ key: 'filtered', title: 'Registrazioni Filtrate', rows: pagedRecordings }];
    }
    const groups = [];
    teamOptions.forEach((team) => {
      const teamRows = pagedRecordings.filter((recording) => {
        const meta = submitterMeta.get(Number(recording?.submitter_user_id));
        return (meta?.teams || []).some((memberTeam) => Number(memberTeam.id) === Number(team.id));
      });
      if (teamRows.length > 0) {
        groups.push({
          key: `team-${team.id}`,
          title: team.team_type ? `${team.team_type.charAt(0).toUpperCase() + team.team_type.slice(1)} - ${team.name}` : team.name,
          rows: teamRows,
        });
      }
    });
    const noTeamRows = pagedRecordings.filter((recording) => {
      const meta = submitterMeta.get(Number(recording?.submitter_user_id));
      return !meta?.teams || meta.teams.length === 0;
    });
    if (noTeamRows.length > 0) {
      groups.push({ key: 'no-team', title: 'Senza Team', rows: noTeamRows });
    }
    return groups;
  }, [showTeamGrouping, teamOptions, pagedRecordings, submitterMeta]);

  const handleCopyLink = async (loomLink) => {
    if (!loomLink) return;
    try {
      await navigator.clipboard.writeText(loomLink);
      Swal.fire({
        toast: true,
        position: 'top-end',
        icon: 'success',
        title: 'Link copiato',
        timer: 1800,
        showConfirmButton: false,
      });
    } catch (err) {
      console.error('[LoomLibrary] copy error', err);
      Swal.fire({
        toast: true,
        position: 'top-end',
        icon: 'error',
        title: 'Copia link non riuscita',
        timer: 2200,
        showConfirmButton: false,
      });
    }
  };

  return (
    <div className="container-fluid p-0">
      <div className="loomlib-header">
        <div>
          <h4>Libreria Loom</h4>
          <p className="loomlib-header-sub">Video registrati dalla suite, visibili in base ai tuoi permessi.</p>
        </div>
        <button
          type="button"
          className="loomlib-refresh-btn"
          onClick={() => loadRecordings({ silent: true })}
          disabled={isLoading || isReloading}
        >
          <i className="ri-refresh-line me-1"></i>
          {isReloading ? 'Aggiorno...' : 'Aggiorna'}
        </button>
      </div>

      <div className="loomlib-view-tabs">
        <button
          className={`loomlib-view-tab${associationFilter === 'all' ? ' active' : ''}`}
          onClick={() => setAssociationFilter('all')}
        >
          <i className="ri-folder-video-line"></i>
          Tutti
          <span className="loomlib-view-count">{stats.total}</span>
        </button>
        <button
          className={`loomlib-view-tab${associationFilter === 'associated' ? ' active' : ''}`}
          onClick={() => setAssociationFilter('associated')}
        >
          <i className="ri-user-heart-line"></i>
          Associati a paziente
          <span className="loomlib-view-count">{stats.associated}</span>
        </button>
        <button
          className={`loomlib-view-tab${associationFilter === 'unassociated' ? ' active' : ''}`}
          onClick={() => setAssociationFilter('unassociated')}
        >
          <i className="ri-user-unfollow-line"></i>
          Senza paziente
          <span className="loomlib-view-count">{stats.unassociated}</span>
        </button>
      </div>

      <div className="loomlib-filter-bar">
        {canUseCapienzaStyleFilters ? (
          <div className="loomlib-specialty-pills">
            {[
              { key: 'all', label: 'Tutti' },
              { key: 'nutrizione', label: 'Nutrizione' },
              { key: 'coach', label: 'Coach' },
              { key: 'psicologia', label: 'Psicologia' },
            ].map((opt) => (
              <button
                key={opt.key}
                className={`loomlib-specialty-pill${specialtyFilter === opt.key ? ' active' : ''}`}
                onClick={() => setSpecialtyFilter(opt.key)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        ) : <div />}

        <div className="loomlib-filter-controls">
          {canUseCapienzaStyleFilters && (
            <select
              className="loomlib-filter-select"
              value={teamFilter}
              onChange={(e) => setTeamFilter(e.target.value)}
            >
              <option value="all">Tutti i team</option>
              {teamOptions.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.team_type ? `${team.team_type.charAt(0).toUpperCase() + team.team_type.slice(1)} - ` : ''}{team.name}
                </option>
              ))}
            </select>
          )}
          <input
            className="loomlib-search-input"
            type="text"
            value={query}
            placeholder="Cerca per titolo, paziente, autore o link"
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            className="loomlib-filter-select"
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
          >
            <option value="newest">Più recenti</option>
            <option value="oldest">Meno recenti</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="loomlib-state">Caricamento libreria Loom in corso...</div>
      ) : error ? (
        <div className="loomlib-state loomlib-state-error">{error}</div>
      ) : sortedRecordings.length === 0 ? (
        <div className="loomlib-state">Nessun video Loom trovato.</div>
      ) : (
        <div className="loomlib-table-card">
          <div className="loomlib-groups">
            {groupedRecordings.map((group) => (
              <div key={group.key} className="loomlib-group">
                {showTeamGrouping && (
                  <div className="loomlib-group-header">
                    <span>{group.title}</span>
                    <span className="loomlib-group-count">{group.rows.length}</span>
                  </div>
                )}
                <div className="table-responsive">
                  <table className="loomlib-table">
                    <thead>
                      <tr>
                        <th>Titolo</th>
                        <th>Paziente</th>
                        {isAdminOrTeamLeader && <th>Autore</th>}
                        <th>Data</th>
                        <th style={{ textAlign: 'right' }}>Azioni</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.rows.map((recording) => (
                        <tr key={recording.id}>
                          <td>
                            <div className="loomlib-title">{getDisplayTitle(recording)}</div>
                            <div className={`loomlib-note-inline${recording.note ? '' : ' empty'}`}>
                              {recording.note || 'Nessuna nota'}
                            </div>
                          </td>
                          <td>
                            <span className={`loomlib-badge${recording.cliente_name ? '' : ' muted'}`}>
                              {recording.cliente_name || 'Non associato'}
                            </span>
                          </td>
                          {isAdminOrTeamLeader && (
                            <td>{recording.submitter_user_name || '-'}</td>
                          )}
                          <td>{formatDateTime(recording.created_at)}</td>
                          <td style={{ textAlign: 'right' }}>
                            <div className="loomlib-actions">
                              <a
                                href={recording.loom_link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="loomlib-open-link"
                              >
                                <i className="ri-external-link-line"></i> Apri
                              </a>
                              <button
                                type="button"
                                className="loomlib-copy-btn"
                                onClick={() => handleCopyLink(recording.loom_link)}
                              >
                                <i className="ri-file-copy-line"></i> Copia
                              </button>
                              <button
                                type="button"
                                className="loomlib-copy-btn"
                                onClick={() => setPreviewLink(recording.loom_link)}
                              >
                                <i className="ri-play-circle-line"></i> Anteprima
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {sortedRecordings.length > 0 && (
        <div className="loomlib-pagination">
          <button
            type="button"
            className="loomlib-page-btn"
            onClick={() => setPage((prev) => Math.max(1, prev - 1))}
            disabled={page <= 1}
          >
            <i className="ri-arrow-left-s-line"></i> Precedente
          </button>
          <span>Pagina {page} / {totalPages}</span>
          <button
            type="button"
            className="loomlib-page-btn"
            onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
            disabled={page >= totalPages}
          >
            Successiva <i className="ri-arrow-right-s-line"></i>
          </button>
        </div>
      )}

      {previewLink && (
        <>
          <div className="loomlib-preview-backdrop" onClick={() => setPreviewLink('')}></div>
          <div className="loomlib-preview-modal">
            <div className="loomlib-preview-header">
              <span>Anteprima Loom</span>
              <button type="button" className="loomlib-preview-close" onClick={() => setPreviewLink('')}>
                <i className="ri-close-line"></i>
              </button>
            </div>
            <div className="loomlib-preview-body">
              <iframe
                src={getLoomEmbedUrl(previewLink)}
                title="Loom preview"
                allowFullScreen
                loading="lazy"
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default LoomLibrary;

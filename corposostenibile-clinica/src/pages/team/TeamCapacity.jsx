import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import teamService, { SPECIALTY_LABELS } from '../../services/teamService';
import { normalizeAvatarPath } from '../../utils/mediaUrl';
import './TeamCapacity.css';

const SPECIALTY_GROUPS = {
  nutrizione: ['nutrizione', 'nutrizionista'],
  coach: ['coach'],
  psicologia: ['psicologia', 'psicologo'],
};

function TeamCapacity() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [viewTab, setViewTab] = useState('professionisti');
  const [profFilter, setProfFilter] = useState('all');
  const [teamFilter, setTeamFilter] = useState('all');
  const [canEdit, setCanEdit] = useState(false);
  const [editingValues, setEditingValues] = useState({});
  const [savingByUserId, setSavingByUserId] = useState({});

  const fetchCapacity = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const data = await teamService.getProfessionalCapacity();
      const list = data.rows || [];
      setRows(list);
      setCanEdit(Boolean(data.can_edit));
      setEditingValues(list.reduce((acc, row) => { acc[row.user_id] = row.capienza_contrattuale; return acc; }, {}));
    } catch (err) {
      setRows([]);
      const status = err?.response?.status;
      setError(status === 403
        ? 'Non hai i permessi per visualizzare la tabella capienza professionisti.'
        : (err?.response?.data?.message || 'Errore nel caricamento della tabella capienza.'));
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchCapacity(); }, [fetchCapacity]);

  const profRows = useMemo(() => rows.filter((r) => r.role_type !== 'health_manager'), [rows]);
  const hmRows = useMemo(() => rows.filter((r) => r.role_type === 'health_manager'), [rows]);
  const activeRows = viewTab === 'health_manager' ? hmRows : profRows;

  const filteredRows = useMemo(() => {
    let filtered = activeRows;
    if (viewTab === 'professionisti' && profFilter !== 'all') {
      filtered = filtered.filter((row) => (SPECIALTY_GROUPS[profFilter] || []).includes(String(row.specialty || '').toLowerCase()));
    }
    if (teamFilter !== 'all') {
      const teamId = Number(teamFilter);
      filtered = filtered.filter((row) => (row.teams || []).some((t) => t.id === teamId));
    }
    const q = search.trim().toLowerCase();
    if (!q) return filtered;
    return filtered.filter((row) => {
      const name = (row.full_name || '').toLowerCase();
      const specialty = (SPECIALTY_LABELS[row.specialty] || row.specialty || '').toLowerCase();
      return name.includes(q) || specialty.includes(q);
    });
  }, [activeRows, viewTab, profFilter, teamFilter, search]);

  const showTeamGrouping = teamFilter === 'all';

  const teamOptions = useMemo(() => {
    const base = viewTab === 'professionisti'
      ? (profFilter === 'all' ? profRows : profRows.filter((row) => (SPECIALTY_GROUPS[profFilter] || []).includes(String(row.specialty || '').toLowerCase())))
      : hmRows;
    const teamMap = new Map();
    base.forEach((row) => { (row.teams || []).forEach((team) => { if (!teamMap.has(team.id)) teamMap.set(team.id, team); }); });
    return Array.from(teamMap.values()).sort((a, b) => {
      if ((a.team_type || '') !== (b.team_type || '')) return (a.team_type || '').localeCompare(b.team_type || '');
      return (a.name || '').localeCompare(b.name || '');
    });
  }, [profRows, hmRows, viewTab, profFilter]);

  const groupedRows = useMemo(() => {
    if (!showTeamGrouping) {
      return [{ key: 'filtered', title: viewTab === 'health_manager' ? 'Health Manager Filtrati' : 'Professionisti Filtrati', teamType: null, rows: filteredRows }];
    }
    const teamMap = new Map();
    filteredRows.forEach((row) => { (row.teams || []).forEach((team) => { if (!teamMap.has(team.id)) teamMap.set(team.id, team); }); });
    const opts = Array.from(teamMap.values()).sort((a, b) => {
      if ((a.team_type || '') !== (b.team_type || '')) return (a.team_type || '').localeCompare(b.team_type || '');
      return (a.name || '').localeCompare(b.name || '');
    });
    const groups = [];
    opts.forEach((team) => {
      const members = filteredRows.filter((row) => (row.teams || []).some((t) => t.id === team.id));
      if (members.length > 0) {
        groups.push({
          key: `team-${team.id}`,
          title: team.team_type ? `${team.team_type.charAt(0).toUpperCase() + team.team_type.slice(1)} - ${team.name}` : team.name,
          teamType: team.team_type, rows: members,
        });
      }
    });
    const noTeam = filteredRows.filter((row) => !row.teams || row.teams.length === 0);
    if (noTeam.length > 0) groups.push({ key: 'no-team', title: 'Senza Team', teamType: null, rows: noTeam });
    return groups;
  }, [filteredRows, showTeamGrouping, viewTab]);

  useEffect(() => {
    if (teamFilter === 'all') return;
    if (!teamOptions.some((t) => t.id === Number(teamFilter))) setTeamFilter('all');
  }, [teamFilter, teamOptions]);

  const isCco = user?.specialty === 'cco';
  const isAdminOrCco = Boolean(user?.is_admin || user?.role === 'admin' || isCco);
  const canUseSpecialtyFilters = isAdminOrCco;
  const canAccessPage = Boolean(user?.is_admin || user?.role === 'team_leader' || isCco || user?.role === 'admin');

  useEffect(() => { if (!canUseSpecialtyFilters && profFilter !== 'all') setProfFilter('all'); }, [canUseSpecialtyFilters, profFilter]);
  useEffect(() => { if (!canUseSpecialtyFilters && teamFilter !== 'all') setTeamFilter('all'); }, [canUseSpecialtyFilters, teamFilter]);
  useEffect(() => { if (viewTab === 'health_manager') setProfFilter('all'); }, [viewTab]);

  const handleSave = async (userId) => {
    const value = editingValues[userId];
    if (value === '' || value == null || Number.isNaN(Number(value))) return;
    setSavingByUserId((prev) => ({ ...prev, [userId]: true }));
    try {
      const data = await teamService.updateProfessionalCapacity(userId, Number(value));
      const updated = data.row;
      setRows((prev) => prev.map((r) => (r.user_id === userId ? { ...r, ...updated } : r)));
      setEditingValues((prev) => ({ ...prev, [userId]: updated.capienza_contrattuale }));
    } catch (err) {
      alert(err?.response?.data?.message || 'Errore nel salvataggio della capienza contrattuale');
    } finally { setSavingByUserId((prev) => ({ ...prev, [userId]: false })); }
  };

  if (!canAccessPage) return <div className="tc-error">Non autorizzato.</div>;

  const renderAvatar = (row) => {
    const src = normalizeAvatarPath(row.avatar_path);
    const initials = `${row.first_name?.[0] || ''}${row.last_name?.[0] || ''}`.toUpperCase();
    if (src) {
      return <img src={src} alt={row.full_name} className="tc-avatar" />;
    }
    return <span className="tc-avatar-initials">{initials}</span>;
  };

  const renderCapacityRow = (row, keyPrefix) => {
    const isSaving = Boolean(savingByUserId[row.user_id]);
    return (
      <tr key={`${keyPrefix}-${row.user_id}`}>
        <td>
          <div className="tc-name-cell">
            {renderAvatar(row)}
            <div>
              <div className="tc-name">{row.full_name}</div>
              <div className="tc-specialty">{SPECIALTY_LABELS[row.specialty] || row.specialty || '—'}</div>
            </div>
          </div>
        </td>
        <td>
          {canEdit ? (
            <div className="tc-edit-wrap">
              <input
                type="number" min="0" className="tc-edit-input"
                value={editingValues[row.user_id] ?? ''}
                onChange={(e) => setEditingValues((prev) => ({ ...prev, [row.user_id]: e.target.value }))}
              />
              <button className="tc-save-btn" disabled={isSaving} onClick={() => handleSave(row.user_id)}>
                {isSaving ? '...' : 'Salva'}
              </button>
            </div>
          ) : (
            <span>{row.capienza_contrattuale}</span>
          )}
        </td>
        <td>
          <span className={`tc-badge ${row.is_over_capacity ? 'tc-badge-danger' : 'tc-badge-default'}`}>
            {row.clienti_assegnati}
          </span>
        </td>
        <td>
          <div className="tc-progress-wrap">
            <div className="tc-progress">
              <div className={`tc-progress-bar ${row.is_over_capacity ? 'danger' : 'normal'}`}
                style={{ width: `${Math.min(row.percentuale_capienza || 0, 100)}%` }} />
            </div>
            <span className="tc-progress-value">{(row.percentuale_capienza || 0).toFixed(1)}%</span>
          </div>
        </td>
        <td style={{ textAlign: 'right' }}>
          <Link className="tc-profile-link" to={`/team-dettaglio/${row.user_id}?tab=capienza`}>
            <i className="ri-eye-line"></i> Apri
          </Link>
        </td>
      </tr>
    );
  };

  const renderHMRow = (row, keyPrefix) => {
    const isSaving = Boolean(savingByUserId[row.user_id]);
    const convertiti = row.clienti_convertiti ?? 0;
    const inAttesa = row.lead_in_attesa ?? 0;
    return (
      <tr key={`${keyPrefix}-${row.user_id}`}>
        <td>
          <div className="tc-name-cell">
            {renderAvatar(row)}
            <div className="tc-name">{row.full_name}</div>
          </div>
        </td>
        <td>
          {canEdit ? (
            <div className="tc-edit-wrap">
              <input
                type="number" min="0" className="tc-edit-input"
                value={editingValues[row.user_id] ?? ''}
                onChange={(e) => setEditingValues((prev) => ({ ...prev, [row.user_id]: e.target.value }))}
              />
              <button className="tc-save-btn" disabled={isSaving} onClick={() => handleSave(row.user_id)}>
                {isSaving ? '...' : 'Salva'}
              </button>
            </div>
          ) : (
            <span>{row.capienza_contrattuale}</span>
          )}
        </td>
        <td><span className="tc-badge tc-badge-success">{convertiti}</span></td>
        <td><span className={`tc-badge ${inAttesa > 0 ? 'tc-badge-warning' : 'tc-badge-muted'}`}>{inAttesa}</span></td>
        <td><span className={`tc-badge ${row.is_over_capacity ? 'tc-badge-danger' : 'tc-badge-default'}`}>{row.clienti_assegnati}</span></td>
        <td>
          <div className="tc-progress-wrap">
            <div className="tc-progress">
              <div className={`tc-progress-bar ${row.is_over_capacity ? 'danger' : 'normal'}`}
                style={{ width: `${Math.min(row.percentuale_capienza || 0, 100)}%` }} />
            </div>
            <span className="tc-progress-value">{(row.percentuale_capienza || 0).toFixed(1)}%</span>
          </div>
        </td>
        <td style={{ textAlign: 'right' }}>
          <Link className="tc-profile-link" to={`/team-dettaglio/${row.user_id}?tab=capienza`}>
            <i className="ri-eye-line"></i> Apri
          </Link>
        </td>
      </tr>
    );
  };

  const renderProfTable = (tableRows, keyPrefix) => (
    <div className="table-responsive">
      <table className="tc-table">
        <thead>
          <tr>
            <th>Professionista</th>
            <th style={{ width: 220 }}>Capienza contrattuale</th>
            <th>Clienti assegnati</th>
            <th>% Capienza</th>
            <th style={{ textAlign: 'right' }}>Profilo</th>
          </tr>
        </thead>
        <tbody>
          {tableRows.map((row) => renderCapacityRow(row, keyPrefix))}
        </tbody>
      </table>
    </div>
  );

  const renderHMTable = (tableRows, keyPrefix) => (
    <div className="table-responsive">
      <table className="tc-table">
        <thead>
          <tr>
            <th>Health Manager</th>
            <th style={{ width: 220 }}>Capienza contrattuale</th>
            <th>Clienti convertiti</th>
            <th>Lead in attesa</th>
            <th>Totale</th>
            <th>% Capienza</th>
            <th style={{ textAlign: 'right' }}>Profilo</th>
          </tr>
        </thead>
        <tbody>
          {tableRows.map((row) => renderHMRow(row, keyPrefix))}
        </tbody>
      </table>
    </div>
  );

  const renderTable = viewTab === 'health_manager' ? renderHMTable : renderProfTable;

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="tc-header">
        <div>
          <h4>Capienza</h4>
          <p className="tc-header-sub">Capienza contrattuale, clienti assegnati, % capienza</p>
        </div>
        <button className="tc-refresh-btn" onClick={fetchCapacity}>
          <i className="ri-refresh-line"></i> Aggiorna
        </button>
      </div>

      {/* View Tabs */}
      <div className="tc-view-tabs">
        <button className={`tc-view-tab${viewTab === 'professionisti' ? ' active' : ''}`} onClick={() => setViewTab('professionisti')}>
          <i className="ri-stethoscope-line"></i> Professionisti
          <span className="tc-view-count">{profRows.length}</span>
        </button>
        <button className={`tc-view-tab${viewTab === 'health_manager' ? ' active' : ''}`} onClick={() => setViewTab('health_manager')}>
          <i className="ri-heart-pulse-line"></i> Health Manager
          <span className="tc-view-count">{hmRows.length}</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="tc-filter-bar">
        {viewTab === 'professionisti' && canUseSpecialtyFilters ? (
          <div className="tc-specialty-pills">
            {[
              { key: 'all', label: 'Tutti' },
              { key: 'nutrizione', label: 'Nutrizione' },
              { key: 'coach', label: 'Coach' },
              { key: 'psicologia', label: 'Psicologia' },
            ].map((opt) => (
              <button key={opt.key} className={`tc-specialty-pill${profFilter === opt.key ? ' active' : ''}`} onClick={() => setProfFilter(opt.key)}>
                {opt.label}
              </button>
            ))}
          </div>
        ) : <div />}

        <div className="tc-filter-controls">
          {canUseSpecialtyFilters && (
            <select className="tc-filter-select" value={teamFilter} onChange={(e) => setTeamFilter(e.target.value)}>
              <option value="all">Tutti i team</option>
              {teamOptions.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.team_type ? `${team.team_type.charAt(0).toUpperCase() + team.team_type.slice(1)} - ` : ''}{team.name}
                </option>
              ))}
            </select>
          )}
          <input
            type="search" className="tc-search-input"
            placeholder={viewTab === 'health_manager' ? 'Cerca health manager...' : 'Cerca professionista...'}
            value={search} onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="tc-loading">
          <div className="tc-spinner"></div>
          <p className="tc-loading-text">Caricamento capienza...</p>
        </div>
      ) : error ? (
        <div className="tc-error">{error}</div>
      ) : filteredRows.length === 0 ? (
        <div className="tc-table-card">
          <div className="tc-empty-row">
            {viewTab === 'health_manager' ? 'Nessun Health Manager trovato.' : 'Nessuna capienza disponibile.'}
          </div>
        </div>
      ) : (
        <div className="tc-table-card">
          {!showTeamGrouping ? (
            renderTable(filteredRows, 'filtered')
          ) : (
            <div className="tc-groups">
              {groupedRows.map((group) => (
                <div key={group.key} className="tc-group">
                  <div className="tc-group-header">
                    <span>{group.title}</span>
                    <span className={`tc-group-count ${group.teamType || 'default'}`}>
                      {group.rows.length}
                    </span>
                  </div>
                  <div className="tc-group-table-wrap">
                    {renderTable(group.rows, group.key)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default TeamCapacity;

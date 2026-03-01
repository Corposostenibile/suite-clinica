import { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { normalizeAvatarPath } from '../../utils/mediaUrl';
import './CriteriProfessionisti.css';

const DEPT_ROLE_MAP = {
  2: 'nutrizione',
  24: 'nutrizione',
  3: 'coach',
  4: 'psicologia'
};

const DEPT_LABELS = {
  2: 'Nutrizione',
  3: 'Coach',
  4: 'Psicologia',
  24: 'Nutrizione 2'
};

const TEAM_TYPE_CSS = {
  nutrizione: 'nutrizione',
  coach: 'coach',
  psicologia: 'psicologia',
};

function CriteriProfessionisti() {
  const { user } = useAuth();
  const isTeamLeader = user?.role === 'team_leader';
  const isAdminOrCco = Boolean(user?.is_admin || user?.role === 'admin' || user?.specialty === 'cco');
  const canUseSpecialtyFilters = isAdminOrCco;

  const [professionals, setProfessionals] = useState([]);
  const [criteriaSchema, setCriteriaSchema] = useState({});
  const [loadingProfs, setLoadingProfs] = useState(false);
  const [error, setError] = useState(null);
  const [showProfModal, setShowProfModal] = useState(false);
  const [editingProf, setEditingProf] = useState(null);
  const [tempCriteria, setTempCriteria] = useState({});
  const [profFilter, setProfFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [teamFilter, setTeamFilter] = useState('all');
  const [criteriaStatus, setCriteriaStatus] = useState(null);
  const [toastState, setToastState] = useState({ show: false, message: '', variant: 'success' });
  const [brokenAvatars, setBrokenAvatars] = useState({});

  const fetchProfessionalsAndSchema = async () => {
    setLoadingProfs(true);
    try {
      const [respProfs, respSchema] = await Promise.all([
        api.get('/team/professionals/criteria'),
        api.get('/team/criteria/schema')
      ]);
      if (respProfs.data.success) setProfessionals(respProfs.data.professionals);
      if (respSchema.data.success) setCriteriaSchema(respSchema.data.schema);
    } catch (err) {
      console.error('Errore caricamento professionisti:', err);
      setError('Impossibile caricare la lista professionisti.');
    } finally {
      setLoadingProfs(false);
    }
  };

  useEffect(() => { fetchProfessionalsAndSchema(); }, []);

  useEffect(() => {
    if (!canUseSpecialtyFilters && profFilter !== 'all') setProfFilter('all');
  }, [canUseSpecialtyFilters, profFilter]);

  // Toast auto-hide
  useEffect(() => {
    if (!toastState.show) return;
    const t = setTimeout(() => setToastState(prev => ({ ...prev, show: false })), 2500);
    return () => clearTimeout(t);
  }, [toastState.show]);

  const handleEditCriteria = (prof) => {
    setEditingProf(prof);
    setTempCriteria(prof.criteria || {});
    setCriteriaStatus(null);
    setShowProfModal(true);
  };

  const handleSaveCriteria = async () => {
    if (!editingProf) return;
    try {
      await api.put(`/team/professionals/${editingProf.id}/criteria`, { criteria: tempCriteria });
      setShowProfModal(false);
      setCriteriaStatus({ type: 'success', message: 'Criteri aggiornati con successo.' });
      setToastState({ show: true, message: 'Criteri salvati', variant: 'success' });
      fetchProfessionalsAndSchema();
    } catch (err) {
      console.error('Errore salvataggio criteri:', err);
      setCriteriaStatus({ type: 'error', message: 'Errore durante il salvataggio dei criteri.' });
      setToastState({ show: true, message: 'Errore nel salvataggio', variant: 'danger' });
    }
  };

  const toggleCriterion = (key) => {
    setTempCriteria(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleAllCriteria = (keys, value) => {
    setTempCriteria(prev => {
      const updated = { ...prev };
      keys.forEach(k => { updated[k] = value; });
      return updated;
    });
  };

  const getFilteredProfessionals = () => {
    let filtered = professionals;
    if (profFilter !== 'all') {
      filtered = filtered.filter(p => (DEPT_ROLE_MAP[p.department_id] || 'other') === profFilter);
    }
    if (searchTerm.trim() !== '') {
      const lowerTerm = searchTerm.toLowerCase();
      filtered = filtered.filter(p => p.name.toLowerCase().includes(lowerTerm));
    }
    if (teamFilter !== 'all') {
      const teamId = Number(teamFilter);
      filtered = filtered.filter(p => (p.teams || []).some(t => t.id === teamId));
    }
    return filtered;
  };

  const showTeamGrouping = teamFilter === 'all';

  const teamOptions = useMemo(() => {
    const roleFiltered = profFilter === 'all'
      ? professionals
      : professionals.filter(p => (DEPT_ROLE_MAP[p.department_id] || 'other') === profFilter);

    const teamMap = new Map();
    roleFiltered.forEach(p => {
      (p.teams || []).forEach(t => { if (!teamMap.has(t.id)) teamMap.set(t.id, t); });
    });

    const options = Array.from(teamMap.values());
    options.sort((a, b) => {
      const aType = a.team_type || '';
      const bType = b.team_type || '';
      if (aType !== bType) return aType.localeCompare(bType);
      return (a.name || '').localeCompare(b.name || '');
    });
    return options;
  }, [professionals, profFilter]);

  useEffect(() => {
    if (teamFilter === 'all' || teamFilter === 'none') return;
    const teamId = Number(teamFilter);
    if (!teamOptions.some(t => t.id === teamId)) setTeamFilter('all');
  }, [teamOptions, teamFilter]);

  const renderAvatar = (prof) => {
    const avatarSrc = normalizeAvatarPath(prof.avatar_path);
    if (avatarSrc && !brokenAvatars[prof.id]) {
      return (
        <img
          src={avatarSrc} alt={prof.name} className="cp-avatar"
          onError={() => setBrokenAvatars(prev => ({ ...prev, [prof.id]: true }))}
        />
      );
    }
    const initials = (prof.name || '').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    return <div className="cp-avatar-initials">{initials}</div>;
  };

  const renderTable = (rows) => (
    <table className="cp-table">
      <thead>
        <tr>
          <th style={{ width: '30%' }}>Professionista</th>
          <th style={{ width: '20%' }}>Team</th>
          <th>Stato</th>
          <th style={{ width: '30%' }}>Criteri Specializzazione</th>
          <th style={{ textAlign: 'right' }}>Azioni</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(prof => (
          <tr key={prof.id}>
            <td>
              <div className="cp-name-cell">
                {renderAvatar(prof)}
                <div>
                  <div className="cp-name">{prof.name}</div>
                  <div className="cp-dept">{DEPT_LABELS[prof.department_id] || 'N/A'}</div>
                </div>
              </div>
            </td>
            <td>
              {prof.teams && prof.teams.length > 0 ? (
                <div className="cp-team-badges">
                  {prof.teams.map(team => (
                    <span key={team.id} className={`cp-team-badge ${TEAM_TYPE_CSS[team.team_type] || 'default'}`}>
                      {team.name}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="cp-criteria-none">Senza team</span>
              )}
            </td>
            <td>
              {prof.is_available ? (
                <span className="cp-status available"><i className="ri-check-line"></i> Disponibile</span>
              ) : (
                <span className="cp-status unavailable"><i className="ri-close-line"></i> Non disp.</span>
              )}
            </td>
            <td>
              <div className="cp-criteria-wrap">
                {Object.entries(prof.criteria || {}).filter(([, v]) => v).slice(0, 5).map(([k]) => (
                  <span className="cp-criteria-pill" key={k}>{k}</span>
                ))}
                {Object.entries(prof.criteria || {}).filter(([, v]) => v).length > 5 && (
                  <span className="cp-criteria-more">+{Object.entries(prof.criteria || {}).filter(([, v]) => v).length - 5} altri</span>
                )}
                {Object.values(prof.criteria || {}).filter(v => v).length === 0 && (
                  <span className="cp-criteria-none">-</span>
                )}
              </div>
            </td>
            <td style={{ textAlign: 'right' }}>
              <button className="cp-edit-btn" onClick={() => handleEditCriteria(prof)} title="Modifica criteri">
                <i className="ri-settings-3-line"></i>
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  const renderContent = () => {
    const filtered = getFilteredProfessionals();

    if (!showTeamGrouping) {
      if (filtered.length === 0) {
        return <div className="cp-empty-row">Nessun professionista trovato</div>;
      }
      return renderTable(filtered);
    }

    const groups = [];
    teamOptions.forEach(team => {
      const members = filtered.filter(p => (p.teams || []).some(t => t.id === team.id));
      if (members.length > 0) {
        groups.push({
          key: `team-${team.id}`,
          title: team.team_type ? `${team.team_type.charAt(0).toUpperCase() + team.team_type.slice(1)} - ${team.name}` : team.name,
          rows: members
        });
      }
    });

    const noTeamMembers = filtered.filter(p => !p.teams || p.teams.length === 0);
    if (noTeamMembers.length > 0) {
      groups.push({ key: 'no-team', title: 'Senza Team / Da assegnare', rows: noTeamMembers });
    }

    if (groups.length === 0) {
      return <div className="cp-empty-row">Nessun professionista trovato</div>;
    }

    return (
      <div className="cp-groups">
        {groups.map((group) => (
          <div key={group.key} className="cp-group">
            <div className="cp-group-header">{group.title}</div>
            <div className="cp-group-table-wrap">
              {renderTable(group.rows)}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderModal = () => {
    if (!showProfModal || !editingProf) return null;

    const roleKey = DEPT_ROLE_MAP[editingProf.department_id];
    const criteriaList = criteriaSchema[roleKey] || [];
    const selectedCount = criteriaList.filter(c => tempCriteria[c]).length;

    return createPortal(
      <div className="cp-modal-overlay" onClick={() => setShowProfModal(false)}>
        <div className="cp-modal" onClick={e => e.stopPropagation()}>
          <div className="cp-modal-header">
            <h5 className="cp-modal-title">Modifica Criteri: {editingProf.name}</h5>
            <button className="cp-modal-close" onClick={() => setShowProfModal(false)}>&times;</button>
          </div>

          <div className="cp-modal-body">
            <div className="cp-modal-info">
              <div className="cp-modal-info-icon">
                <i className="ri-magic-line"></i>
              </div>
              <div>
                <div className="cp-modal-info-title">Criteri per {DEPT_LABELS[editingProf.department_id]}</div>
                <div className="cp-modal-info-desc">Servono all'AI per proporre il professionista giusto.</div>
                {criteriaStatus && criteriaStatus.type === 'error' && (
                  <div className="cp-modal-error">
                    <i className="ri-error-warning-line"></i>
                    {criteriaStatus.message}
                  </div>
                )}
              </div>
            </div>

            {criteriaList.length === 0 ? (
              <div className="cp-no-schema">Nessuno schema criteri trovato per questo ruolo.</div>
            ) : (
              <>
                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
                  <div className="cp-criteria-counter">
                    Criteri disponibili: {criteriaList.length} &middot; Selezionati: {selectedCount}
                  </div>
                  <div className="cp-criteria-actions">
                    <button className="cp-criteria-bulk-btn" onClick={() => toggleAllCriteria(criteriaList, false)}>
                      <i className="ri-eraser-line"></i> Deseleziona tutto
                    </button>
                    <button className="cp-criteria-bulk-btn" onClick={() => toggleAllCriteria(criteriaList, true)}>
                      <i className="ri-check-double-line"></i> Seleziona tutto
                    </button>
                  </div>
                </div>

                <div className="cp-criteria-grid">
                  {criteriaList.map(crit => {
                    const active = !!tempCriteria[crit];
                    return (
                      <button
                        key={crit}
                        className={`cp-criteria-toggle${active ? ' active' : ''}`}
                        onClick={() => toggleCriterion(crit)}
                      >
                        <span>{crit}</span>
                        <i className={active ? 'ri-check-line' : 'ri-add-line'}></i>
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>

          <div className="cp-modal-footer">
            <button className="cp-btn-cancel" onClick={() => setShowProfModal(false)}>Annulla</button>
            <button className="cp-btn-save" onClick={handleSaveCriteria}>Salva Modifiche</button>
          </div>
        </div>
      </div>,
      document.body
    );
  };

  return (
    <div className="container-fluid p-0">
      {/* Toast */}
      {toastState.show && (
        <div className={`cp-toast ${toastState.variant}`}>
          <i className={toastState.variant === 'success' ? 'ri-checkbox-circle-line' : 'ri-error-warning-line'}></i>
          {toastState.message}
        </div>
      )}

      {/* Header */}
      <div className="cp-header">
        <div>
          <h4>Criteri Professionisti</h4>
          <p className="cp-header-sub">Gestione dei criteri di specializzazione per il matching AI</p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="cp-error">
          <i className="ri-error-warning-line"></i>
          {error}
          <button className="cp-error-close" onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      {/* Filters */}
      <div className="cp-filter-bar">
        {canUseSpecialtyFilters ? (
          <div className="cp-specialty-pills">
            {[
              { key: 'all', label: 'Tutti' },
              { key: 'nutrizione', label: 'Nutrizione' },
              { key: 'coach', label: 'Coach' },
              { key: 'psicologia', label: 'Psicologia' },
            ].map(opt => (
              <button
                key={opt.key}
                className={`cp-specialty-pill${profFilter === opt.key ? ' active' : ''}`}
                onClick={() => setProfFilter(opt.key)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        ) : <div />}

        <div className="cp-filter-controls">
          <select
            className="cp-filter-select"
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
          >
            <option value="all">{isTeamLeader ? 'I miei team' : 'Tutti i team'}</option>
            {teamOptions.map(team => (
              <option key={team.id} value={team.id}>
                {team.team_type ? `${team.team_type.charAt(0).toUpperCase() + team.team_type.slice(1)} - ` : ''}{team.name}
              </option>
            ))}
          </select>
          <input
            type="search"
            className="cp-search-input"
            placeholder="Cerca professionista..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Content */}
      {loadingProfs ? (
        <div className="cp-loading">
          <div className="cp-spinner"></div>
          <p className="cp-loading-text">Caricamento professionisti...</p>
        </div>
      ) : (
        <div className="cp-table-card">
          {renderContent()}
        </div>
      )}

      {/* Edit Modal (portal) */}
      {renderModal()}
    </div>
  );
}

export default CriteriProfessionisti;

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Button, ButtonGroup, Card, Form, Spinner, Table } from 'react-bootstrap';
import { useAuth } from '../../context/AuthContext';
import teamService, { SPECIALTY_LABELS, TEAM_TYPE_COLORS } from '../../services/teamService';

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
  const [profFilter, setProfFilter] = useState('all');
  const [teamFilter, setTeamFilter] = useState('all');
  const [canEdit, setCanEdit] = useState(false);
  const [editingValues, setEditingValues] = useState({});
  const [savingByUserId, setSavingByUserId] = useState({});

  const fetchCapacity = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await teamService.getProfessionalCapacity();
      const list = data.rows || [];
      setRows(list);
      setCanEdit(Boolean(data.can_edit));
      setEditingValues(
        list.reduce((acc, row) => {
          acc[row.user_id] = row.capienza_contrattuale;
          return acc;
        }, {})
      );
    } catch (err) {
      setRows([]);
      const status = err?.response?.status;
      if (status === 403) {
        setError('Non hai i permessi per visualizzare la tabella capienza professionisti.');
      } else {
        setError(err?.response?.data?.message || 'Errore nel caricamento della tabella capienza.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCapacity();
  }, [fetchCapacity]);

  const filteredRows = useMemo(() => {
    let filtered = rows;

    if (profFilter !== 'all') {
      filtered = filtered.filter((row) => {
        const specialty = String(row.specialty || '').toLowerCase();
        return (SPECIALTY_GROUPS[profFilter] || []).includes(specialty);
      });
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
  }, [rows, profFilter, teamFilter, search]);

  const showTeamGrouping = teamFilter === 'all';

  const teamOptions = useMemo(() => {
    const roleFilteredRows = profFilter === 'all'
      ? rows
      : rows.filter((row) => {
          const specialty = String(row.specialty || '').toLowerCase();
          return (SPECIALTY_GROUPS[profFilter] || []).includes(specialty);
        });

    const teamMap = new Map();
    roleFilteredRows.forEach((row) => {
      (row.teams || []).forEach((team) => {
        if (!teamMap.has(team.id)) teamMap.set(team.id, team);
      });
    });

    return Array.from(teamMap.values()).sort((a, b) => {
      const aType = a.team_type || '';
      const bType = b.team_type || '';
      if (aType !== bType) return aType.localeCompare(bType);
      return (a.name || '').localeCompare(b.name || '');
    });
  }, [rows, profFilter]);

  const groupedRows = useMemo(() => {
    if (!showTeamGrouping) {
      return [{
        key: 'filtered',
        title: 'Professionisti Filtrati',
        teamType: null,
        rows: filteredRows,
      }];
    }

    const teamMap = new Map();

    filteredRows.forEach((row) => {
      (row.teams || []).forEach((team) => {
        if (!teamMap.has(team.id)) teamMap.set(team.id, team);
      });
    });

    const teamOptions = Array.from(teamMap.values()).sort((a, b) => {
      const aType = a.team_type || '';
      const bType = b.team_type || '';
      if (aType !== bType) return aType.localeCompare(bType);
      return (a.name || '').localeCompare(b.name || '');
    });

    const groups = [];
    teamOptions.forEach((team) => {
      const members = filteredRows.filter((row) => (row.teams || []).some((t) => t.id === team.id));
      if (members.length > 0) {
        groups.push({
          key: `team-${team.id}`,
          title: team.team_type
            ? `${team.team_type.charAt(0).toUpperCase() + team.team_type.slice(1)} - ${team.name}`
            : team.name,
          teamType: team.team_type,
          rows: members,
        });
      }
    });

    return groups;
  }, [filteredRows, showTeamGrouping]);

  useEffect(() => {
    if (teamFilter === 'all') return;
    const teamId = Number(teamFilter);
    if (!teamOptions.some((t) => t.id === teamId)) {
      setTeamFilter('all');
    }
  }, [teamFilter, teamOptions]);

  const isCco = user?.specialty === 'cco';
  const isAdminOrCco = Boolean(user?.is_admin || user?.role === 'admin' || isCco);
  const canUseSpecialtyFilters = isAdminOrCco;
  const canAccessPage = Boolean(user?.is_admin || user?.role === 'team_leader' || isCco || user?.role === 'admin');

  useEffect(() => {
    if (!canUseSpecialtyFilters && profFilter !== 'all') {
      setProfFilter('all');
    }
  }, [canUseSpecialtyFilters, profFilter]);

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
    } finally {
      setSavingByUserId((prev) => ({ ...prev, [userId]: false }));
    }
  };

  if (!canAccessPage) return <Alert variant="warning" className="mb-0">Non autorizzato.</Alert>;

  const renderCapacityTable = (tableRows, keyPrefix = 'tbl') => (
    <Table responsive hover className="mb-0 align-middle">
      <thead className="bg-light">
        <tr>
          <th>Professionista</th>
          <th style={{ width: 220 }}>Capienza contrattuale</th>
          <th>Clienti assegnati</th>
          <th>% Capienza</th>
          <th className="text-end">Profilo</th>
        </tr>
      </thead>
      <tbody>
        {tableRows.map((row) => {
          const isSaving = Boolean(savingByUserId[row.user_id]);
          return (
            <tr key={`${keyPrefix}-${row.user_id}`}>
              <td>
                <div className="fw-medium">{row.full_name}</div>
                <small className="text-muted">{SPECIALTY_LABELS[row.specialty] || row.specialty || '—'}</small>
              </td>
              <td>
                {canEdit ? (
                  <div className="d-flex gap-2 align-items-center">
                    <Form.Control
                      type="number"
                      min="0"
                      size="sm"
                      value={editingValues[row.user_id] ?? ''}
                      onChange={(e) => {
                        setEditingValues((prev) => ({ ...prev, [row.user_id]: e.target.value }));
                      }}
                    />
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={isSaving}
                      onClick={() => handleSave(row.user_id)}
                    >
                      {isSaving ? '...' : 'Salva'}
                    </Button>
                  </div>
                ) : (
                  <span>{row.capienza_contrattuale}</span>
                )}
              </td>
              <td>
                <span className={`badge ${row.is_over_capacity ? 'bg-danger' : 'bg-light text-dark border'}`}>
                  {row.clienti_assegnati}
                </span>
              </td>
              <td>
                <div className="d-flex align-items-center gap-2">
                  <div className="progress" style={{ height: 8, width: 120 }}>
                    <div
                      className={`progress-bar ${row.is_over_capacity ? 'bg-danger' : 'bg-primary'}`}
                      style={{ width: `${Math.min(row.percentuale_capienza || 0, 100)}%` }}
                    />
                  </div>
                  <span className="small fw-medium">{(row.percentuale_capienza || 0).toFixed(1)}%</span>
                </div>
              </td>
              <td className="text-end">
                <Link className="btn btn-sm btn-outline-primary" to={`/team-dettaglio/${row.user_id}?tab=capienza`}>
                  Apri
                </Link>
              </td>
            </tr>
          );
        })}
      </tbody>
    </Table>
  );

  return (
    <div className="container-fluid p-0">
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4 gap-2">
        <div>
          <h4 className="mb-1">Capienza Professionisti</h4>
          <p className="text-muted mb-0">Nome professionista, capienza contrattuale, clienti assegnati, % capienza</p>
        </div>
        <Button variant="outline-secondary" onClick={fetchCapacity}>
          <i className="ri-refresh-line me-1"></i>
          Aggiorna
        </Button>
      </div>

      <div className="d-flex flex-wrap align-items-center justify-content-between mb-3 gap-3">
        {canUseSpecialtyFilters ? (
          <ButtonGroup>
            <Button variant={profFilter === 'all' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('all')}>Tutti</Button>
            <Button variant={profFilter === 'nutrizione' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('nutrizione')}>Nutrizione</Button>
            <Button variant={profFilter === 'coach' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('coach')}>Coach</Button>
            <Button variant={profFilter === 'psicologia' ? 'primary' : 'outline-primary'} onClick={() => setProfFilter('psicologia')}>Psicologia</Button>
          </ButtonGroup>
        ) : (
          <div />
        )}

        <div className="d-flex flex-wrap gap-2" style={{ maxWidth: '520px', width: '100%' }}>
          <Form.Select
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
            style={{ minWidth: '200px', flex: 1 }}
          >
            <option value="all">Tutti i team</option>
            {teamOptions.map((team) => (
              <option key={team.id} value={team.id}>
                {team.team_type ? `${team.team_type.charAt(0).toUpperCase() + team.team_type.slice(1)} - ` : ''}{team.name}
              </option>
            ))}
          </Form.Select>
          <Form.Control
            type="search"
            placeholder="Cerca professionista..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ minWidth: '200px', flex: 1 }}
          />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-5"><Spinner animation="border" /></div>
      ) : error ? (
        <Alert variant="danger" className="mb-0">{error}</Alert>
      ) : filteredRows.length === 0 ? (
        <Card className="border-0 shadow-sm">
          <Card.Body className="p-0">
            <Table responsive className="mb-0 align-middle">
              <tbody>
                <tr>
                  <td colSpan="5" className="text-center py-4 text-muted">
                    Nessuna capienza disponibile.
                  </td>
                </tr>
              </tbody>
            </Table>
          </Card.Body>
        </Card>
      ) : (
        <Card className="border-0 shadow-sm">
          <Card.Body className="p-0">
            {!showTeamGrouping ? (
              renderCapacityTable(filteredRows, 'filtered')
            ) : (
              <div className="p-3">
                {groupedRows.map((group, index) => (
                  <div key={group.key} className={index > 0 ? 'mt-4' : ''}>
                    <div className="fw-semibold text-muted mb-2 d-flex align-items-center gap-2">
                      <span>{group.title}</span>
                      {group.teamType ? (
                        <span className={`badge bg-${TEAM_TYPE_COLORS[group.teamType] || 'secondary'}`}>
                          {group.rows.length}
                        </span>
                      ) : (
                        <span className="badge bg-secondary">{group.rows.length}</span>
                      )}
                    </div>
                    <div className="border rounded">
                      {renderCapacityTable(group.rows, group.key)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card.Body>
        </Card>
      )}
    </div>
  );
}

export default TeamCapacity;

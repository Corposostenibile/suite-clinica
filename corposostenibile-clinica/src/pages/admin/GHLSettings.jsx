import { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import ghlService from '../../services/ghlService';

function GHLSettings() {
  const { user } = useOutletContext();

  // Config state
  const [config, setConfig] = useState({
    api_key: '',
    location_id: '',
    is_active: false,
    has_api_key: false
  });
  const [configLoading, setConfigLoading] = useState(true);
  const [configSaving, setConfigSaving] = useState(false);
  const [testResult, setTestResult] = useState(null);

  // Mapping state
  const [mapping, setMapping] = useState([]);
  const [ghlCalendars, setGhlCalendars] = useState([]);
  const [ghlUsers, setGhlUsers] = useState([]);
  const [mappingLoading, setMappingLoading] = useState(false);
  const [mappingSaving, setMappingSaving] = useState(false);

  // Tab state
  const [activeTab, setActiveTab] = useState('config');

  // Calendar search state (per user)
  const [calendarSearch, setCalendarSearch] = useState({});
  // User filter
  const [userFilter, setUserFilter] = useState('');

  // Check if admin
  if (!user?.is_admin) {
    return (
      <div className="alert alert-danger">
        <i className="ri-lock-line me-2"></i>
        Accesso non autorizzato. Solo gli admin possono accedere a questa pagina.
      </div>
    );
  }

  useEffect(() => {
    loadConfig();
  }, []);

  useEffect(() => {
    if (activeTab === 'mapping' && config.is_active) {
      loadMappingData();
    }
  }, [activeTab, config.is_active]);

  const loadConfig = async () => {
    try {
      setConfigLoading(true);
      const result = await ghlService.getConfig();
      if (result.success) {
        setConfig({
          api_key: '',
          location_id: result.config.location_id || '',
          is_active: result.config.is_active,
          has_api_key: result.config.has_api_key,
          last_sync_at: result.config.last_sync_at,
          last_error: result.config.last_error
        });
      }
    } catch (error) {
      console.error('Error loading config:', error);
    } finally {
      setConfigLoading(false);
    }
  };

  const loadMappingData = async () => {
    try {
      setMappingLoading(true);

      // Load in parallel
      const [mappingResult, calendarsResult, usersResult] = await Promise.all([
        ghlService.getMapping(),
        ghlService.getCalendars(),
        ghlService.getGHLUsers()
      ]);

      if (mappingResult.success) {
        setMapping(mappingResult.mapping);
      }
      if (calendarsResult.success) {
        setGhlCalendars(calendarsResult.calendars);
      }
      if (usersResult.success) {
        setGhlUsers(usersResult.users);
      }
    } catch (error) {
      console.error('Error loading mapping data:', error);
    } finally {
      setMappingLoading(false);
    }
  };

  const saveConfig = async () => {
    try {
      setConfigSaving(true);
      setTestResult(null);

      const dataToSave = {
        location_id: config.location_id,
        is_active: config.is_active
      };

      // Only include api_key if it was changed
      if (config.api_key) {
        dataToSave.api_key = config.api_key;
      }

      const result = await ghlService.updateConfig(dataToSave);

      if (result.success) {
        setTestResult({ success: true, message: 'Configurazione salvata!' });
        // Reload config to get updated state
        loadConfig();
      } else {
        setTestResult({ success: false, message: result.message });
      }
    } catch (error) {
      setTestResult({ success: false, message: error.message });
    } finally {
      setConfigSaving(false);
    }
  };

  const testConnection = async () => {
    try {
      setConfigSaving(true);
      setTestResult(null);

      const result = await ghlService.testConnection();
      setTestResult(result);

      if (result.success) {
        loadConfig();
      }
    } catch (error) {
      setTestResult({ success: false, message: error.message });
    } finally {
      setConfigSaving(false);
    }
  };

  const updateUserMapping = async (userId, ghlUserId) => {
    try {
      // Map by GHL user ID (will show all their calendars)
      await ghlService.updateMapping(userId, null, ghlUserId);

      // Update local state
      setMapping(prev => prev.map(m =>
        m.user_id === userId
          ? { ...m, ghl_calendar_id: null, ghl_user_id: ghlUserId }
          : m
      ));
    } catch (error) {
      console.error('Error updating mapping:', error);
    }
  };

  return (
    <>
      {/* Page Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1" style={{ fontWeight: 700, color: '#1e293b' }}>
            <i className="ri-settings-3-line me-2"></i>
            Impostazioni Go High Level
          </h4>
          <p className="text-muted mb-0">Configura l'integrazione calendario con GHL</p>
        </div>
      </div>

      {/* Tabs */}
      <ul className="nav nav-tabs mb-4">
        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === 'config' ? 'active' : ''}`}
            onClick={() => setActiveTab('config')}
          >
            <i className="ri-key-line me-2"></i>
            Configurazione API
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link ${activeTab === 'mapping' ? 'active' : ''}`}
            onClick={() => setActiveTab('mapping')}
            disabled={!config.is_active}
          >
            <i className="ri-links-line me-2"></i>
            Mapping Calendari
          </button>
        </li>
      </ul>

      {/* Config Tab */}
      {activeTab === 'config' && (
        <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
          <div className="card-body p-4">
            {configLoading ? (
              <div className="text-center py-5">
                <div className="spinner-border text-success" role="status"></div>
                <p className="mt-2 text-muted">Caricamento configurazione...</p>
              </div>
            ) : (
              <>
                <h5 className="mb-4">
                  <i className="ri-key-2-line me-2 text-warning"></i>
                  Credenziali Go High Level
                </h5>

                {/* API Key */}
                <div className="mb-4">
                  <label className="form-label fw-semibold">API Key / Access Token</label>
                  <input
                    type="password"
                    className="form-control"
                    placeholder={config.has_api_key ? '••••••••••••••••••••' : 'Inserisci API Key'}
                    value={config.api_key}
                    onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                    style={{ borderRadius: '10px' }}
                  />
                  <small className="text-muted">
                    Trova la API Key in GHL: Settings → API Keys
                    {config.has_api_key && (
                      <span className="ms-2 text-success">
                        <i className="ri-checkbox-circle-fill"></i> API Key configurata
                      </span>
                    )}
                  </small>
                </div>

                {/* Location ID */}
                <div className="mb-4">
                  <label className="form-label fw-semibold">Location ID</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="es. abc123XYZ"
                    value={config.location_id}
                    onChange={(e) => setConfig({ ...config, location_id: e.target.value })}
                    style={{ borderRadius: '10px' }}
                  />
                  <small className="text-muted">
                    Trova il Location ID nell'URL di GHL: app.gohighlevel.com/location/<strong>XXXXX</strong>
                  </small>
                </div>

                {/* Active Toggle */}
                <div className="mb-4">
                  <div className="form-check form-switch">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="ghlActive"
                      checked={config.is_active}
                      onChange={(e) => setConfig({ ...config, is_active: e.target.checked })}
                      style={{ width: '3em', height: '1.5em' }}
                    />
                    <label className="form-check-label fw-semibold ms-2" htmlFor="ghlActive">
                      Integrazione Attiva
                    </label>
                  </div>
                </div>

                {/* Last Sync Info */}
                {config.last_sync_at && (
                  <div className="alert alert-info py-2 mb-4">
                    <i className="ri-time-line me-2"></i>
                    Ultima sincronizzazione: {new Date(config.last_sync_at).toLocaleString('it-IT')}
                  </div>
                )}

                {/* Last Error */}
                {config.last_error && (
                  <div className="alert alert-danger py-2 mb-4">
                    <i className="ri-error-warning-line me-2"></i>
                    Ultimo errore: {config.last_error}
                  </div>
                )}

                {/* Test Result */}
                {testResult && (
                  <div className={`alert ${testResult.success ? 'alert-success' : 'alert-danger'} py-2 mb-4`}>
                    <i className={`${testResult.success ? 'ri-checkbox-circle-line' : 'ri-close-circle-line'} me-2`}></i>
                    {testResult.message}
                  </div>
                )}

                {/* Buttons */}
                <div className="d-flex gap-2">
                  <button
                    className="btn btn-success"
                    onClick={saveConfig}
                    disabled={configSaving}
                    style={{ borderRadius: '10px' }}
                  >
                    {configSaving ? (
                      <span className="spinner-border spinner-border-sm me-2"></span>
                    ) : (
                      <i className="ri-save-line me-2"></i>
                    )}
                    Salva Configurazione
                  </button>
                  <button
                    className="btn btn-outline-primary"
                    onClick={testConnection}
                    disabled={configSaving || !config.location_id}
                    style={{ borderRadius: '10px' }}
                  >
                    <i className="ri-wifi-line me-2"></i>
                    Testa Connessione
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Mapping Tab */}
      {activeTab === 'mapping' && (
        <div className="card border-0" style={{ borderRadius: '16px', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
          <div className="card-body p-4">
            {mappingLoading ? (
              <div className="text-center py-5">
                <div className="spinner-border text-success" role="status"></div>
                <p className="mt-2 text-muted">Caricamento dati...</p>
              </div>
            ) : (
              <>
                <div className="d-flex align-items-center justify-content-between mb-4">
                  <h5 className="mb-0">
                    <i className="ri-calendar-line me-2 text-primary"></i>
                    Associa Calendari GHL agli Utenti
                  </h5>
                  <button
                    className="btn btn-sm btn-outline-secondary"
                    onClick={loadMappingData}
                    style={{ borderRadius: '8px' }}
                  >
                    <i className="ri-refresh-line me-1"></i>
                    Aggiorna
                  </button>
                </div>

                {ghlUsers.length === 0 ? (
                  <div className="alert alert-warning">
                    <i className="ri-information-line me-2"></i>
                    Nessun utente (team member) trovato in GHL. Verifica la configurazione.
                  </div>
                ) : (
                  <>
                    {/* Info */}
                    <div className="alert alert-info py-2 mb-4">
                      <i className="ri-lightbulb-line me-2"></i>
                      <strong>Utenti GHL (team members):</strong> {ghlUsers.length} |
                      <strong className="ms-2">Utenti Suite:</strong> {mapping.length}
                      <br />
                      <small className="text-muted">
                        Seleziona l'utente GHL corrispondente per ogni professionista.
                        Verranno mostrati tutti i calendari di quell'utente.
                      </small>
                    </div>

                    {/* User Filter */}
                    <div className="mb-3">
                      <div className="input-group" style={{ maxWidth: '400px' }}>
                        <span className="input-group-text" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                          <i className="ri-search-line text-muted"></i>
                        </span>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="Filtra utenti per nome o email..."
                          value={userFilter}
                          onChange={(e) => setUserFilter(e.target.value)}
                          style={{ border: '1px solid #e2e8f0', borderLeft: 'none' }}
                        />
                        {userFilter && (
                          <button
                            className="btn btn-outline-secondary"
                            type="button"
                            onClick={() => setUserFilter('')}
                            style={{ border: '1px solid #e2e8f0', borderLeft: 'none' }}
                          >
                            <i className="ri-close-line"></i>
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Mapping Table */}
                    <div className="table-responsive">
                      <table className="table">
                        <thead>
                          <tr style={{ background: '#f8fafc' }}>
                            <th style={{ fontWeight: 600, color: '#64748b', fontSize: '12px', textTransform: 'uppercase' }}>
                              Utente Suite Clinica
                            </th>
                            <th style={{ fontWeight: 600, color: '#64748b', fontSize: '12px', textTransform: 'uppercase' }}>
                              Ruolo
                            </th>
                            <th style={{ fontWeight: 600, color: '#64748b', fontSize: '12px', textTransform: 'uppercase' }}>
                              Utente GHL
                              <small className="d-block text-muted fw-normal" style={{ textTransform: 'none', fontSize: '10px' }}>
                                (tutti i calendari)
                              </small>
                            </th>
                            <th style={{ fontWeight: 600, color: '#64748b', fontSize: '12px', textTransform: 'uppercase' }}>
                              Stato
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {mapping
                            .filter(u => {
                              if (!userFilter) return true;
                              const search = userFilter.toLowerCase();
                              return (
                                u.full_name?.toLowerCase().includes(search) ||
                                u.email?.toLowerCase().includes(search)
                              );
                            })
                            .map((user) => (
                            <tr key={user.user_id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                              <td className="py-3">
                                <div className="d-flex align-items-center">
                                  <div
                                    className="d-flex align-items-center justify-content-center me-3"
                                    style={{
                                      width: '36px',
                                      height: '36px',
                                      borderRadius: '50%',
                                      background: '#e0f2fe',
                                      color: '#0284c7',
                                      fontWeight: 700,
                                      fontSize: '12px'
                                    }}
                                  >
                                    {user.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                                  </div>
                                  <div>
                                    <div style={{ fontWeight: 600, color: '#334155' }}>{user.full_name}</div>
                                    <div style={{ fontSize: '12px', color: '#94a3b8' }}>{user.email}</div>
                                  </div>
                                </div>
                              </td>
                              <td className="py-3">
                                <span
                                  className="badge"
                                  style={{
                                    background: user.specialty === 'nutrizionista' ? '#dcfce7' :
                                               user.specialty === 'coach' ? '#ffedd5' :
                                               user.specialty === 'psicologo' ? '#fce7f3' : '#f1f5f9',
                                    color: user.specialty === 'nutrizionista' ? '#166534' :
                                           user.specialty === 'coach' ? '#c2410c' :
                                           user.specialty === 'psicologo' ? '#9d174d' : '#64748b',
                                    padding: '4px 8px',
                                    borderRadius: '6px',
                                    fontSize: '11px'
                                  }}
                                >
                                  {user.specialty || user.role || '-'}
                                </span>
                              </td>
                              <td className="py-3" style={{ minWidth: '300px' }}>
                                <div style={{ position: 'relative' }}>
                                  {/* Search Input */}
                                  <input
                                    type="text"
                                    className="form-control form-control-sm mb-1"
                                    placeholder="Cerca utente GHL..."
                                    value={calendarSearch[user.user_id] || ''}
                                    onChange={(e) => setCalendarSearch({
                                      ...calendarSearch,
                                      [user.user_id]: e.target.value
                                    })}
                                    style={{ borderRadius: '8px', fontSize: '12px' }}
                                  />
                                  {/* Filtered Select - GHL Users */}
                                  <select
                                    className="form-select form-select-sm"
                                    value={user.ghl_user_id || ''}
                                    onChange={(e) => updateUserMapping(user.user_id, e.target.value || null)}
                                    style={{ borderRadius: '8px' }}
                                    size={calendarSearch[user.user_id] ? 5 : 1}
                                  >
                                    <option value="">-- Nessun utente GHL --</option>
                                    {ghlUsers
                                      .filter(ghlUser => {
                                        const search = (calendarSearch[user.user_id] || '').toLowerCase();
                                        if (!search) return true;
                                        // Cerca in tutti i campi nome possibili
                                        const fullName = ghlUser.name || `${ghlUser.firstName || ''} ${ghlUser.lastName || ''}`;
                                        const email = ghlUser.email || '';
                                        const calName = ghlUser.calendarName || '';
                                        return fullName.toLowerCase().includes(search) ||
                                               email.toLowerCase().includes(search) ||
                                               calName.toLowerCase().includes(search);
                                      })
                                      .map((ghlUser) => {
                                        // Costruisci il nome da mostrare
                                        const displayName = ghlUser.name ||
                                          `${ghlUser.firstName || ''} ${ghlUser.lastName || ''}`.trim() ||
                                          ghlUser.calendarName ||
                                          ghlUser.id;
                                        const emailPart = ghlUser.email ? ` (${ghlUser.email})` : '';
                                        return (
                                          <option key={ghlUser.id} value={ghlUser.id}>
                                            {displayName}{emailPart}
                                          </option>
                                        );
                                      })}
                                  </select>
                                  {/* Show current selection */}
                                  {user.ghl_user_id && (
                                    <div style={{ fontSize: '11px', color: '#22c55e', marginTop: '4px' }}>
                                      <i className="ri-check-line me-1"></i>
                                      {(() => {
                                        const ghlUser = ghlUsers.find(u => u.id === user.ghl_user_id);
                                        if (!ghlUser) return user.ghl_user_id;
                                        return ghlUser.name ||
                                          `${ghlUser.firstName || ''} ${ghlUser.lastName || ''}`.trim() ||
                                          ghlUser.calendarName ||
                                          user.ghl_user_id;
                                      })()}
                                    </div>
                                  )}
                                </div>
                              </td>
                              <td className="py-3">
                                {user.ghl_user_id ? (
                                  <span className="badge bg-success" style={{ padding: '4px 8px', borderRadius: '6px' }}>
                                    <i className="ri-check-line me-1"></i>
                                    Collegato
                                  </span>
                                ) : (
                                  <span className="badge bg-secondary" style={{ padding: '4px 8px', borderRadius: '6px' }}>
                                    Non collegato
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

export default GHLSettings;

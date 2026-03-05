import { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import ghlService from '../../services/ghlService';
import './GHLSettings.css';

function GHLSettings() {
  const { user } = useOutletContext();

  const [config, setConfig] = useState({
    api_key: '', location_id: '', is_active: false, has_api_key: false
  });
  const [configLoading, setConfigLoading] = useState(true);
  const [configSaving, setConfigSaving] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const [mapping, setMapping] = useState([]);
  const [ghlUsers, setGhlUsers] = useState([]);
  const [mappingLoading, setMappingLoading] = useState(false);

  const [activeTab, setActiveTab] = useState('config');
  const [calendarSearch, setCalendarSearch] = useState({});
  const [userFilter, setUserFilter] = useState('');

  const loadConfig = useCallback(async () => {
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
  }, []);

  const loadMappingData = useCallback(async () => {
    try {
      setMappingLoading(true);
      const [mappingResult, usersResult] = await Promise.all([
        ghlService.getMapping(),
        ghlService.getGHLUsers()
      ]);
      if (mappingResult.success) setMapping(mappingResult.mapping);
      if (usersResult.success) setGhlUsers(usersResult.users);
    } catch (error) {
      console.error('Error loading mapping data:', error);
    } finally {
      setMappingLoading(false);
    }
  }, []);

  useEffect(() => { loadConfig(); }, [loadConfig]);

  useEffect(() => {
    if (activeTab === 'mapping' && config.is_active) loadMappingData();
  }, [activeTab, config.is_active, loadMappingData]);

  if (!user?.is_admin) {
    return (
      <div className="gs-unauthorized">
        <i className="ri-lock-line"></i>
        Accesso non autorizzato. Solo gli admin possono accedere a questa pagina.
      </div>
    );
  }

  const saveConfig = async () => {
    try {
      setConfigSaving(true);
      setTestResult(null);
      const dataToSave = { location_id: config.location_id, is_active: config.is_active };
      if (config.api_key) dataToSave.api_key = config.api_key;
      const result = await ghlService.updateConfig(dataToSave);
      if (result.success) {
        setTestResult({ success: true, message: 'Configurazione salvata!' });
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
      if (result.success) loadConfig();
    } catch (error) {
      setTestResult({ success: false, message: error.message });
    } finally {
      setConfigSaving(false);
    }
  };

  const updateUserMapping = async (userId, ghlUserId) => {
    try {
      await ghlService.updateMapping(userId, null, ghlUserId);
      setMapping(prev => prev.map(m =>
        m.user_id === userId ? { ...m, ghl_calendar_id: null, ghl_user_id: ghlUserId } : m
      ));
    } catch (error) {
      console.error('Error updating mapping:', error);
    }
  };

  const getRoleBadgeClass = (specialty) => {
    if (specialty === 'nutrizionista' || specialty === 'nutrizione') return 'nutrizionista';
    if (specialty === 'coach') return 'coach';
    if (specialty === 'psicologo' || specialty === 'psicologia') return 'psicologo';
    if (specialty === 'health_manager') return 'hm';
    return 'default';
  };

  const connectedCount = mapping.filter(m => m.ghl_user_id).length;

  return (
    <div className="gs-page">
      {/* Header */}
      <div className="gs-header">
        <div className="gs-header-left">
          <h4 className="gs-header-title">
            <i className="ri-settings-4-line"></i>
            Impostazioni Go High Level
          </h4>
          <p className="gs-header-sub">Configura l'integrazione calendario con GHL</p>
        </div>
        {config.is_active && config.has_api_key && (
          <div className="gs-header-badge">
            <i className="ri-checkbox-circle-fill"></i> Integrazione attiva
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="gs-tabs">
        <button
          className={`gs-tab ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          <i className="ri-key-line"></i> Configurazione API
        </button>
        <button
          className={`gs-tab ${activeTab === 'mapping' ? 'active' : ''}`}
          onClick={() => setActiveTab('mapping')}
          disabled={!config.is_active}
        >
          <i className="ri-links-line"></i> Mapping Calendari
          {connectedCount > 0 && (
            <span className="gs-tab-count">{connectedCount}</span>
          )}
        </button>
      </div>

      {/* ===== Config Tab ===== */}
      {activeTab === 'config' && (
        <div className="gs-card">
          {configLoading ? (
            <div className="gs-loading">
              <div className="gs-spinner"></div>
              <p className="gs-loading-text">Caricamento configurazione...</p>
            </div>
          ) : (
            <>
              <div className="gs-section-title">
                <i className="ri-key-2-line"></i> Credenziali Go High Level
              </div>

              <div className="gs-form-grid">
                {/* API Key */}
                <div className="gs-field">
                  <label className="gs-label">API Key / Access Token</label>
                  <input
                    type="password"
                    className="gs-input"
                    placeholder={config.has_api_key ? '••••••••••••••••••••' : 'Inserisci API Key'}
                    value={config.api_key}
                    onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                  />
                  <div className="gs-hint">
                    Trova la API Key in GHL: Settings &rarr; API Keys
                    {config.has_api_key && (
                      <span className="gs-hint-success">
                        <i className="ri-checkbox-circle-fill"></i> Configurata
                      </span>
                    )}
                  </div>
                </div>

                {/* Location ID */}
                <div className="gs-field">
                  <label className="gs-label">Location ID</label>
                  <input
                    type="text"
                    className="gs-input"
                    placeholder="es. abc123XYZ"
                    value={config.location_id}
                    onChange={(e) => setConfig({ ...config, location_id: e.target.value })}
                  />
                  <div className="gs-hint">
                    Trova il Location ID nell'URL: app.gohighlevel.com/location/<strong>XXXXX</strong>
                  </div>
                </div>
              </div>

              {/* Active Toggle */}
              <div className="gs-toggle-wrap">
                <label className="gs-toggle">
                  <input
                    type="checkbox"
                    checked={config.is_active}
                    onChange={(e) => setConfig({ ...config, is_active: e.target.checked })}
                  />
                  <span className="gs-toggle-slider"></span>
                </label>
                <span className="gs-toggle-label">Integrazione Attiva</span>
              </div>

              {/* Alerts */}
              {config.last_sync_at && (
                <div className="gs-alert gs-alert-info">
                  <i className="ri-time-line"></i>
                  Ultima sincronizzazione: {new Date(config.last_sync_at).toLocaleString('it-IT')}
                </div>
              )}

              {config.last_error && (
                <div className="gs-alert gs-alert-danger">
                  <i className="ri-error-warning-line"></i>
                  Ultimo errore: {config.last_error}
                </div>
              )}

              {testResult && (
                <div className={`gs-alert ${testResult.success ? 'gs-alert-success' : 'gs-alert-danger'}`}>
                  <i className={testResult.success ? 'ri-checkbox-circle-line' : 'ri-close-circle-line'}></i>
                  {testResult.message}
                  {testResult.calendars_count !== undefined && (
                    <span className="gs-alert-detail"> — {testResult.calendars_count} calendari trovati</span>
                  )}
                </div>
              )}

              {/* Buttons */}
              <div className="gs-btn-group">
                <button className="gs-btn gs-btn-primary" onClick={saveConfig} disabled={configSaving}>
                  {configSaving ? <span className="gs-spinner-sm"></span> : <i className="ri-save-line"></i>}
                  Salva Configurazione
                </button>
                <button
                  className="gs-btn gs-btn-outline"
                  onClick={testConnection}
                  disabled={configSaving || !config.location_id}
                >
                  <i className="ri-wifi-line"></i> Testa Connessione
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ===== Mapping Tab ===== */}
      {activeTab === 'mapping' && (
        <div className="gs-card">
          {mappingLoading ? (
            <div className="gs-loading">
              <div className="gs-spinner"></div>
              <p className="gs-loading-text">Caricamento dati...</p>
            </div>
          ) : (
            <>
              <div className="gs-mapping-header">
                <div>
                  <h5 className="gs-section-title" style={{ marginBottom: 4 }}>
                    <i className="ri-calendar-line"></i> Associa Utenti GHL ai Professionisti
                  </h5>
                  <p className="gs-header-sub">
                    Seleziona l'utente GHL corrispondente per ogni professionista
                  </p>
                </div>
                <button className="gs-btn gs-btn-outline gs-btn-sm" onClick={loadMappingData}>
                  <i className="ri-refresh-line"></i> Aggiorna
                </button>
              </div>

              {/* Stats */}
              <div className="gs-mapping-stats">
                <div className="gs-stat-item">
                  <span className="gs-stat-value">{ghlUsers.length}</span>
                  <span className="gs-stat-label">Utenti GHL</span>
                </div>
                <div className="gs-stat-item">
                  <span className="gs-stat-value">{mapping.length}</span>
                  <span className="gs-stat-label">Utenti Suite</span>
                </div>
                <div className="gs-stat-item">
                  <span className="gs-stat-value gs-stat-green">{connectedCount}</span>
                  <span className="gs-stat-label">Collegati</span>
                </div>
                <div className="gs-stat-item">
                  <span className="gs-stat-value gs-stat-gray">{mapping.length - connectedCount}</span>
                  <span className="gs-stat-label">Da collegare</span>
                </div>
              </div>

              {ghlUsers.length === 0 ? (
                <div className="gs-alert gs-alert-warning">
                  <i className="ri-information-line"></i>
                  Nessun utente (team member) trovato in GHL. Verifica la configurazione.
                </div>
              ) : (
                <>
                  {/* Filter */}
                  <div className="gs-filter-wrap">
                    <i className="ri-search-line"></i>
                    <input
                      type="text"
                      className="gs-filter-input"
                      placeholder="Filtra utenti per nome o email..."
                      value={userFilter}
                      onChange={(e) => setUserFilter(e.target.value)}
                    />
                  </div>

                  {/* Table */}
                  <div className="gs-table-wrap">
                    <table className="gs-table">
                      <thead>
                        <tr>
                          <th>Utente Suite Clinica</th>
                          <th>Ruolo</th>
                          <th>Utente GHL</th>
                          <th>Stato</th>
                        </tr>
                      </thead>
                      <tbody>
                        {mapping
                          .filter(u => {
                            if (!userFilter) return true;
                            const s = userFilter.toLowerCase();
                            return u.full_name?.toLowerCase().includes(s) || u.email?.toLowerCase().includes(s);
                          })
                          .map((u) => (
                            <tr key={u.user_id}>
                              <td>
                                <div className="gs-user-cell">
                                  <div className="gs-user-avatar">
                                    {u.full_name?.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                                  </div>
                                  <div>
                                    <div className="gs-user-name">{u.full_name}</div>
                                    <div className="gs-user-email">{u.email}</div>
                                  </div>
                                </div>
                              </td>
                              <td>
                                <span className={`gs-role-badge ${getRoleBadgeClass(u.specialty)}`}>
                                  {u.specialty || u.role || '-'}
                                </span>
                              </td>
                              <td className="gs-ghl-cell">
                                <div className="gs-ghl-select-wrap">
                                  <input
                                    type="text"
                                    className="gs-ghl-search"
                                    placeholder="Cerca utente GHL..."
                                    value={calendarSearch[u.user_id] || ''}
                                    onChange={(e) => setCalendarSearch({ ...calendarSearch, [u.user_id]: e.target.value })}
                                  />
                                  <select
                                    className="gs-ghl-select"
                                    value={u.ghl_user_id || ''}
                                    onChange={(e) => updateUserMapping(u.user_id, e.target.value || null)}
                                    size={calendarSearch[u.user_id] ? 5 : 1}
                                  >
                                    <option value="">-- Nessun utente GHL --</option>
                                    {ghlUsers
                                      .filter(ghlUser => {
                                        const search = (calendarSearch[u.user_id] || '').toLowerCase();
                                        if (!search) return true;
                                        const fullName = ghlUser.name || `${ghlUser.firstName || ''} ${ghlUser.lastName || ''}`;
                                        return fullName.toLowerCase().includes(search) ||
                                          (ghlUser.email || '').toLowerCase().includes(search);
                                      })
                                      .map((ghlUser) => {
                                        const displayName = ghlUser.name || `${ghlUser.firstName || ''} ${ghlUser.lastName || ''}`.trim() || ghlUser.id;
                                        const emailPart = ghlUser.email ? ` (${ghlUser.email})` : '';
                                        return <option key={ghlUser.id} value={ghlUser.id}>{displayName}{emailPart}</option>;
                                      })}
                                  </select>
                                  {u.ghl_user_id && (
                                    <div className="gs-ghl-linked">
                                      <i className="ri-check-line"></i>
                                      {(() => {
                                        const ghlUser = ghlUsers.find(x => x.id === u.ghl_user_id);
                                        if (!ghlUser) return u.ghl_user_id;
                                        return ghlUser.name || `${ghlUser.firstName || ''} ${ghlUser.lastName || ''}`.trim() || u.ghl_user_id;
                                      })()}
                                    </div>
                                  )}
                                </div>
                              </td>
                              <td>
                                {u.ghl_user_id ? (
                                  <span className="gs-status-badge linked">
                                    <i className="ri-check-line"></i> Collegato
                                  </span>
                                ) : (
                                  <span className="gs-status-badge unlinked">Non collegato</span>
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
      )}
    </div>
  );
}

export default GHLSettings;

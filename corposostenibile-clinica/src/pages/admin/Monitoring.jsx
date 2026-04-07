import React, { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell, PieChart, Pie,
} from 'recharts';
import monitoringService from '../../services/monitoringService';
import './Monitoring.css';

const COLORS = {
  internal: '#4CAF50',
  external_call: '#FF9800',
  static: '#9E9E9E',
};

const CLASSIFICATION_LABELS = {
  internal: 'Interna',
  external_call: 'Verso servizi esterni',
  static: 'File statico',
};

function Monitoring() {
  const { user } = useOutletContext();
  // Overview (Cloud Monitoring - veloce)
  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState(null);
  // Dettaglio endpoint (Cloud Logging - più lento, lazy)
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [days, setDays] = useState(7);
  const [includeStatic, setIncludeStatic] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedEndpoint, setSelectedEndpoint] = useState(null);
  const [sortField, setSortField] = useState('avg_latency_ms');
  const [sortAsc, setSortAsc] = useState(false);
  const [filterClassification, setFilterClassification] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [infraData, setInfraData] = useState(null);
  const [infraLoading, setInfraLoading] = useState(false);
  const [infraError, setInfraError] = useState(null);
  // Errori
  const [errorFilter, setErrorFilter] = useState('all'); // 'all', '4xx', '5xx'
  const [selectedError, setSelectedError] = useState(null);

  // Carica overview all'avvio (veloce, Cloud Monitoring)
  const fetchOverview = useCallback(async () => {
    try {
      setOverviewLoading(true);
      setOverviewError(null);
      const result = await monitoringService.getOverview({ days });
      setOverview(result);
    } catch (err) {
      setOverviewError(err.response?.data?.message || 'Errore nel caricamento overview');
      console.error('Overview fetch error:', err);
    } finally {
      setOverviewLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  // Quando cambia il periodo, invalida i dati dettaglio (verranno ricaricati lazy)
  useEffect(() => {
    setData(null);
  }, [days]);

  // Carica dettaglio endpoint solo quando serve (lazy)
  const fetchData = useCallback(async () => {
    if (data) return; // già caricato
    try {
      setLoading(true);
      setError(null);
      const result = await monitoringService.getMetrics({
        days,
        include_static: includeStatic ? 1 : 0,
      });
      setData(result);
    } catch (err) {
      setError(err.response?.data?.message || 'Errore nel caricamento dettaglio endpoint');
      console.error('Monitoring fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [days, includeStatic, data]);

  const forceRefreshData = useCallback(async () => {
    setData(null);
    try {
      setLoading(true);
      setError(null);
      const result = await monitoringService.getMetrics({
        days,
        include_static: includeStatic ? 1 : 0,
      });
      setData(result);
    } catch (err) {
      setError(err.response?.data?.message || 'Errore nel caricamento dettaglio endpoint');
    } finally {
      setLoading(false);
    }
  }, [days, includeStatic]);

  // Carica dati endpoint/errori quando si clicca sul tab
  useEffect(() => {
    if ((activeTab === 'endpoints' || activeTab === 'errors') && !data && !loading) {
      fetchData();
    }
  }, [activeTab, data, loading, fetchData]);

  const fetchInfraData = useCallback(async () => {
    try {
      setInfraLoading(true);
      setInfraError(null);
      const result = await monitoringService.getInfrastructure();
      setInfraData(result);
    } catch (err) {
      setInfraError(err.response?.data?.message || 'Errore nel caricamento dati infrastruttura');
      console.error('Infrastructure fetch error:', err);
    } finally {
      setInfraLoading(false);
    }
  }, []);

  // Fetch infra data when switching to the infrastructure tab
  useEffect(() => {
    if (activeTab === 'infrastructure' && !infraData && !infraLoading) {
      fetchInfraData();
    }
  }, [activeTab, infraData, infraLoading, fetchInfraData]);

  if (!user?.is_admin && user?.role !== 'admin') {
    return (
      <div className="monitoring-page">
        <div className="alert alert-danger">Accesso riservato agli amministratori.</div>
      </div>
    );
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const sortIndicator = (field) => {
    if (sortField !== field) return '';
    return sortAsc ? ' \u25B2' : ' \u25BC';
  };

  const getFilteredEndpoints = () => {
    if (!data?.endpoints) return [];
    let eps = [...data.endpoints];

    if (filterClassification !== 'all') {
      eps = eps.filter(e => e.classification === filterClassification);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      eps = eps.filter(e =>
        e.url.toLowerCase().includes(q) ||
        e.method.toLowerCase().includes(q)
      );
    }

    eps.sort((a, b) => {
      const va = a[sortField];
      const vb = b[sortField];
      if (typeof va === 'number') return sortAsc ? va - vb : vb - va;
      return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });

    return eps;
  };

  const renderLoading = (msg = 'Caricamento dati...', submsg = '') => (
    <div className="monitoring-loading">
      <div className="spinner-border text-primary" role="status">
        <span className="visually-hidden">Caricamento...</span>
      </div>
      <p className="mt-3">{msg}</p>
      {submsg && <p className="text-muted small">{submsg}</p>}
    </div>
  );

  const renderControls = () => (
    <div className="monitoring-controls">
      <div className="control-group">
        <label>Periodo:</label>
        <select value={days} onChange={e => setDays(Number(e.target.value))} className="form-select form-select-sm">
          <option value={1}>Ultimo giorno</option>
          <option value={3}>Ultimi 3 giorni</option>
          <option value={7}>Ultimi 7 giorni</option>
          <option value={14}>Ultimi 14 giorni</option>
          <option value={30}>Ultimi 30 giorni</option>
        </select>
      </div>
      <button
        className="btn btn-sm btn-outline-primary"
        onClick={() => { setOverview(null); setData(null); fetchOverview(); }}
        disabled={overviewLoading || loading}
      >
        Aggiorna
      </button>
    </div>
  );

  const renderSummaryCards = () => {
    if (!overview) return null;
    return (
      <div className="summary-cards">
        <div className="summary-card" title="Numero totale di richieste HTTP ricevute dal Load Balancer nel periodo selezionato">
          <div className="summary-value">{overview.total_requests?.toLocaleString() || 0}</div>
          <div className="summary-label">Richieste totali ({overview.period_days}gg)</div>
        </div>
        <div className="summary-card" title="Media aritmetica delle richieste giornaliere nel periodo">
          <div className="summary-value">{overview.avg_requests_per_day || 0}</div>
          <div className="summary-label">Media richieste/giorno</div>
        </div>
        <div className="summary-card" title="Tempo medio di risposta di tutte le richieste. Può essere alzato da poche richieste molto lente (es. chiamate a servizi esterni)">
          <div className="summary-value">{overview.avg_latency_ms || 0}ms</div>
          <div className="summary-label">Latenza media</div>
        </div>
        <div className="summary-card" title="Il 95% delle richieste risponde entro questo tempo. È l'indicatore più utile per capire l'esperienza reale degli utenti">
          <div className="summary-value">{overview.p95_latency_ms || 0}ms</div>
          <div className="summary-label">Latenza P95</div>
        </div>
        <div className="summary-card" title="Percentuale di risposte con errore. 4xx = errori client (es. 404 non trovato, 401 non autorizzato). 5xx = errori server (bug, timeout)">
          <div className="summary-value">{overview.error_rate_pct || 0}%</div>
          <div className="summary-label">Errori ({overview.errors_4xx || 0} 4xx + {overview.errors_5xx || 0} 5xx)</div>
        </div>
      </div>
    );
  };

  const renderOverview = () => {
    if (overviewLoading) return renderLoading('Caricamento panoramica...', '~1-2 secondi (Cloud Monitoring)');
    if (overviewError) return <div className="alert alert-danger">{overviewError}</div>;
    if (!overview) return null;

    return (
      <div className="monitoring-overview">
        {renderSummaryCards()}

        <div className="charts-row">
          <div className="chart-container">
            <h5>Distribuzione oraria (tutte le richieste)</h5>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={overview.hourly_distribution || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip formatter={(val) => [val.toLocaleString(), 'Richieste']} />
                <Bar dataKey="count" fill="#4CAF50" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-container">
            <h5>Distribuzione settimanale (tutte le richieste)</h5>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={overview.weekday_distribution || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip formatter={(val) => [val.toLocaleString(), 'Media/giorno']} />
                <Bar dataKey="avg_per_day" fill="#FF9800" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="charts-row">
          <div className="chart-container">
            <h5>Latenza (ms)</h5>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={[
                { name: 'Media', value: overview.avg_latency_ms || 0, desc: 'Tempo medio di risposta' },
                { name: 'P50', value: overview.p50_latency_ms || 0, desc: 'Il 50% delle richieste risponde entro questo tempo (mediana)' },
                { name: 'P95', value: overview.p95_latency_ms || 0, desc: 'Il 95% delle richieste risponde entro questo tempo' },
                { name: 'P99', value: overview.p99_latency_ms || 0, desc: 'Il 99% delle richieste risponde entro questo tempo' },
                { name: 'Max', value: overview.max_latency_ms || 0, desc: 'Tempo della richiesta più lenta (stima dal bucket)' },
              ]}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip
                  formatter={(val, _name, props) => [`${val.toLocaleString()}ms`, props.payload.desc]}
                />
                <Bar dataKey="value" name="Latenza (ms)">
                  {[
                    { name: 'Media', value: overview.avg_latency_ms || 0 },
                    { name: 'P50', value: overview.p50_latency_ms || 0 },
                    { name: 'P95', value: overview.p95_latency_ms || 0 },
                    { name: 'P99', value: overview.p99_latency_ms || 0 },
                    { name: 'Max', value: overview.max_latency_ms || 0 },
                  ].map((entry, i) => (
                    <Cell key={i} fill={entry.value > 5000 ? '#f44336' : entry.value > 2000 ? '#FF9800' : '#4CAF50'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-container">
            <h5>Errori</h5>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={[
                    { name: 'OK (2xx/3xx)', value: Math.max(0, (overview.total_requests || 0) - (overview.errors_4xx || 0) - (overview.errors_5xx || 0)) },
                    { name: 'Client (4xx)', value: overview.errors_4xx || 0 },
                    { name: 'Server (5xx)', value: overview.errors_5xx || 0 },
                  ].filter(d => d.value > 0)}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={70}
                  label={({ name, percent }) => `${name} (${(percent * 100).toFixed(1)}%)`}
                >
                  <Cell fill="#4CAF50" />
                  <Cell fill="#FF9800" />
                  <Cell fill="#f44336" />
                </Pie>
                <Tooltip formatter={(val) => [val.toLocaleString(), 'Richieste']} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top endpoint per latenza (dai log, se disponibili) */}
        {data?.endpoints && data.endpoints.length > 0 && (
          <div className="charts-row">
            <div className="chart-container">
              <h5>Top 10 per latenza media (ms) — da log</h5>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={[...data.endpoints].sort((a, b) => b.avg_latency_ms - a.avg_latency_ms).slice(0, 10)} layout="vertical" margin={{ left: 200 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis
                    type="category"
                    dataKey="url"
                    width={190}
                    tick={{ fontSize: 11 }}
                    tickFormatter={v => v.length > 30 ? v.slice(0, 30) + '...' : v}
                  />
                  <Tooltip formatter={(val) => [`${val}ms`, 'Latenza media']} />
                  <Bar dataKey="avg_latency_ms" name="Latenza media (ms)">
                    {[...data.endpoints].sort((a, b) => b.avg_latency_ms - a.avg_latency_ms).slice(0, 10).map((entry, i) => (
                      <Cell key={i} fill={entry.avg_latency_ms > 5000 ? '#f44336' : entry.avg_latency_ms > 2000 ? '#FF9800' : '#4CAF50'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {!data && !loading && (
          <div className="text-center mt-3">
            <button className="btn btn-sm btn-outline-secondary" onClick={forceRefreshData}>
              Carica dettaglio per endpoint (da Cloud Logging)
            </button>
          </div>
        )}
        {loading && <p className="text-muted text-center mt-3">Caricamento dettaglio endpoint...</p>}
      </div>
    );
  };

  const renderEndpointTable = () => {
    const endpoints = getFilteredEndpoints();

    return (
      <div className="monitoring-endpoints">
        <div className="filter-bar">
          <input
            type="text"
            className="form-control form-control-sm"
            placeholder="Cerca endpoint..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ maxWidth: 300 }}
          />
          <select
            className="form-select form-select-sm"
            value={filterClassification}
            onChange={e => setFilterClassification(e.target.value)}
            style={{ maxWidth: 200 }}
          >
            <option value="all">Tutti i tipi</option>
            <option value="internal">Solo interni</option>
            <option value="external_call">Solo verso esterni</option>
          </select>
          <span className="text-muted small">{endpoints.length} endpoint</span>
        </div>

        <div className="table-responsive">
          <table className="table table-hover table-sm monitoring-table">
            <thead>
              <tr>
                <th>Tipo</th>
                <th onClick={() => handleSort('method')} className="sortable">
                  Metodo{sortIndicator('method')}
                </th>
                <th onClick={() => handleSort('url')} className="sortable">
                  Endpoint{sortIndicator('url')}
                </th>
                <th onClick={() => handleSort('avg_latency_ms')} className="sortable text-end" title="Tempo medio di risposta per questo endpoint">
                  Latenza media{sortIndicator('avg_latency_ms')}
                </th>
                <th onClick={() => handleSort('p95_latency_ms')} className="sortable text-end" title="Il 95% delle richieste a questo endpoint risponde entro questo tempo">
                  P95{sortIndicator('p95_latency_ms')}
                </th>
                <th onClick={() => handleSort('max_latency_ms')} className="sortable text-end" title="Tempo della richiesta più lenta registrata per questo endpoint">
                  Max{sortIndicator('max_latency_ms')}
                </th>
                <th onClick={() => handleSort('error_rate_pct')} className="sortable text-end" title="Percentuale di risposte con errore (status HTTP >= 400)">
                  Errori{sortIndicator('error_rate_pct')}
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {endpoints.map((ep) => {
                const epKey = `${ep.method}:${ep.url}`;
                const isSelected = selectedEndpoint === epKey;
                return (
                  <React.Fragment key={epKey}>
                    <tr
                      className={`${ep.avg_latency_ms > 5000 ? 'row-critical' : ep.avg_latency_ms > 2000 ? 'row-warning' : ''}`}
                    >
                      <td>
                        <span className={`badge-classification badge-${ep.classification}`}>
                          {ep.classification === 'internal' ? 'INT' : 'EXT'}
                        </span>
                      </td>
                      <td><span className={`method-badge method-${ep.method.toLowerCase()}`}>{ep.method}</span></td>
                      <td className="endpoint-url" title={ep.url}>{ep.url}</td>
                      <td className="text-end">
                        <span className={`latency-value ${ep.avg_latency_ms > 5000 ? 'latency-critical' : ep.avg_latency_ms > 2000 ? 'latency-warning' : 'latency-ok'}`}>
                          {ep.avg_latency_ms.toLocaleString()}ms
                        </span>
                      </td>
                      <td className="text-end">{ep.p95_latency_ms.toLocaleString()}ms</td>
                      <td className="text-end">{ep.max_latency_ms.toLocaleString()}ms</td>
                      <td className="text-end">
                        {ep.error_rate_pct > 0 && (
                          <span className="badge bg-danger">{ep.error_rate_pct}%</span>
                        )}
                      </td>
                      <td>
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => setSelectedEndpoint(isSelected ? null : epKey)}
                          title="Dettaglio"
                        >
                          {isSelected ? '\u25B2' : '\u25BC'}
                        </button>
                      </td>
                    </tr>
                    {isSelected && (
                      <tr className="endpoint-detail-row">
                        <td colSpan={8} style={{ padding: 0 }}>
                          {renderEndpointDetail(ep)}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
              {endpoints.length === 0 && (
                <tr><td colSpan={8} className="text-center text-muted">Nessun endpoint trovato</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderEndpointDetail = (ep) => {
    // Cerca gli errori HTTP (dal LB) relativi a questo endpoint
    const endpointKey = `${ep.method} ${ep.url}`;
    const endpointErrors = (data?.errors || []).filter(
      err => err.endpoint === endpointKey
    );

    // Cerca gli errori applicativi (dal backend) che potrebbero corrispondere
    // Matching per URL nell'errore app (il messaggio spesso contiene l'URL)
    const relatedAppErrors = (data?.app_errors || []).filter(appErr => {
      const fp = (appErr.fingerprint || '').toLowerCase();
      const urlPart = ep.url.replace(/\{[^}]+\}/g, '').toLowerCase();
      // Match se il fingerprint contiene parte dell'URL o il metodo
      return fp.includes(urlPart) || 
        (appErr.samples || []).some(s => 
          (s.message || '').toLowerCase().includes(urlPart)
        );
    });

    return (
      <div className="endpoint-detail">
        <h5>{ep.method} {ep.url}</h5>
        <div className="detail-badges">
          <span className={`badge-classification badge-${ep.classification}`}>
            {CLASSIFICATION_LABELS[ep.classification]}
          </span>
          <span className="badge bg-secondary">{ep.total_requests} campioni</span>
          {ep.error_count > 0 && (
            <span className="badge bg-danger">{ep.error_count} errori ({ep.error_rate_pct}%)</span>
          )}
        </div>

        <div className="charts-row">
          <div className="chart-container">
            <h6>Distribuzione oraria</h6>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={ep.hourly_distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip formatter={(val) => [val, 'Chiamate']} />
                <Bar dataKey="count" fill={COLORS[ep.classification] || '#8884d8'} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="chart-container">
            <h6>Distribuzione settimanale (media/giorno)</h6>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={ep.weekday_distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip formatter={(val) => [val, 'Media chiamate/giorno']} />
                <Bar dataKey="avg_per_day" fill={COLORS[ep.classification] || '#8884d8'} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Dettaglio errori per questo endpoint */}
        {endpointErrors.length > 0 && (
          <div className="endpoint-errors-detail">
            <h6>Errori HTTP per questo endpoint</h6>
            <div className="table-responsive">
              <table className="table table-sm table-bordered mb-0">
                <thead>
                  <tr>
                    <th className="text-center">Status</th>
                    <th className="text-end">Occorrenze</th>
                    <th>Ultimo</th>
                    <th>Campioni</th>
                  </tr>
                </thead>
                <tbody>
                  {endpointErrors.map((err, j) => (
                    <tr key={j}>
                      <td className="text-center">
                        <span className={`badge ${err.status >= 500 ? 'bg-danger' : 'bg-warning'}`}>
                          {err.status}
                        </span>
                      </td>
                      <td className="text-end fw-bold">{err.count}</td>
                      <td className="small text-muted">
                        {err.last_seen ? new Date(err.last_seen).toLocaleString('it-IT') : '-'}
                      </td>
                      <td className="small">
                        {err.samples?.slice(0, 3).map((s, k) => (
                          <div key={k}>
                            {new Date(s.timestamp).toLocaleString('it-IT')} — {s.latency_ms}ms
                            {s.status_message && <> — <code>{s.status_message}</code></>}
                          </div>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Errori applicativi correlati (dal backend) */}
        {relatedAppErrors.length > 0 && (
          <div className="endpoint-app-errors-detail">
            <h6>
              <span className="badge bg-danger me-2">{relatedAppErrors.length}</span>
              Errori applicativi correlati (dal backend)
            </h6>
            {relatedAppErrors.map((appErr, j) => (
              <div key={j} className={`app-error-item severity-${(appErr.severity || 'error').toLowerCase()}`}>
                <div className="app-error-header">
                  <div className="app-error-meta">
                    <span className={`badge ${appErr.severity === 'ERROR' || appErr.severity === 'CRITICAL' ? 'bg-danger' : 'bg-warning'}`}>
                      {appErr.severity}
                    </span>
                    <span className="badge bg-secondary">{appErr.count}x</span>
                  </div>
                  <div className="app-error-fingerprint"><code>{appErr.fingerprint}</code></div>
                </div>
                {appErr.samples?.slice(0, 1).map((sample, k) => (
                  <div key={k} className="app-error-samples">
                    <pre className="app-error-message">{sample.message}</pre>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {ep.error_count > 0 && endpointErrors.length === 0 && relatedAppErrors.length === 0 && (
          <div className="text-muted small mt-2">
            <em>{ep.error_count} errori registrati ma dettagli non disponibili nel campione corrente</em>
          </div>
        )}
      </div>
    );
  };

  const renderErrors = () => {
    if (!data?.errors?.length) {
      return <div className="text-muted text-center p-4">Nessun errore nel periodo selezionato.</div>;
    }

    // Filtra errori per tipo
    const filteredErrors = data.errors.filter(err => {
      if (errorFilter === '4xx') return err.status >= 400 && err.status < 500;
      if (errorFilter === '5xx') return err.status >= 500;
      return true;
    });

    // Calcola statistiche per il grafico a torta
    const errorStats = data.error_stats || {};
    const topErrorCodes = errorStats.top_error_codes || {};
    const pieData = Object.entries(topErrorCodes).map(([code, count]) => ({
      name: `${code}`,
      value: count,
    }));

    return (
      <div className="monitoring-errors">
        {/* Statistiche errori */}
        <div className="error-stats-section">
          <div className="charts-row">
            {/* Riepilogo errori */}
            <div className="chart-container">
              <h5>Riepilogo Errori</h5>
              <div className="error-summary-cards">
                <div className="error-summary-card">
                  <div className="error-summary-value text-danger">{errorStats.total_errors || 0}</div>
                  <div className="error-summary-label">Errori totali</div>
                </div>
                <div className="error-summary-card">
                  <div className="error-summary-value text-warning">{errorStats.errors_4xx || 0}</div>
                  <div className="error-summary-label">Errori 4xx (Client)</div>
                </div>
                <div className="error-summary-card">
                  <div className="error-summary-value text-danger">{errorStats.errors_5xx || 0}</div>
                  <div className="error-summary-label">Errori 5xx (Server)</div>
                </div>
                <div className="error-summary-card">
                  <div className="error-summary-value">{errorStats.error_rate_pct || 0}%</div>
                  <div className="error-summary-label">Tasso errore</div>
                </div>
              </div>
            </div>

            {/* Grafico errori per codice */}
            <div className="chart-container">
              <h5>Errori per Codice di Stato</h5>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={70}
                      label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={entry.name.startsWith('5') ? '#f44336' : '#FF9800'} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(val) => [val.toLocaleString(), 'Occorrenze']} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-muted text-center p-3">Nessun dato disponibile</div>
              )}
            </div>
          </div>

          {/* Grafico temporale errori */}
          {errorStats.hourly_error_distribution && (
            <div className="chart-container full-width">
              <h5>Distribuzione Oraria Errori</h5>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={errorStats.hourly_error_distribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" tick={{ fontSize: 11 }} />
                  <YAxis />
                  <Tooltip formatter={(val) => [val.toLocaleString(), 'Errori']} />
                  <Bar dataKey="count" fill="#f44336" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Filtri */}
        <div className="filter-bar mt-3">
          <label>Filtra per tipo:</label>
          <select
            className="form-select form-select-sm"
            value={errorFilter}
            onChange={e => setErrorFilter(e.target.value)}
            style={{ maxWidth: 150 }}
          >
            <option value="all">Tutti</option>
            <option value="4xx">Solo 4xx</option>
            <option value="5xx">Solo 5xx</option>
          </select>
          <span className="text-muted small">{filteredErrors.length} endpoint con errori</span>
        </div>

        {/* Tabella dettaglio errori */}
        <div className="table-responsive mt-3">
          <table className="table table-hover table-sm">
            <thead>
              <tr>
                <th>Endpoint</th>
                <th className="text-center">Status</th>
                <th className="text-end">Occorrenze</th>
                <th>Messaggio Errore</th>
                <th>Ultimo errore</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredErrors.map((err, i) => (
                <React.Fragment key={i}>
                  <tr 
                    className={selectedError === i ? 'row-selected' : ''}
                    onClick={() => setSelectedError(selectedError === i ? null : i)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td className="endpoint-url">{err.endpoint}</td>
                    <td className="text-center">
                      <span className={`badge ${err.status >= 500 ? 'bg-danger' : 'bg-warning'}`}>
                        {err.status}
                      </span>
                    </td>
                    <td className="text-end fw-bold">{err.count}</td>
                    <td className="small error-message-cell">
                      {err.error_message ? (
                        <span title={err.error_message}>
                          {err.error_message.length > 60 
                            ? err.error_message.substring(0, 60) + '...' 
                            : err.error_message}
                        </span>
                      ) : (
                        <span className="text-muted">-</span>
                      )}
                    </td>
                    <td className="small text-muted">
                      {err.last_seen ? new Date(err.last_seen).toLocaleString('it-IT') : '-'}
                    </td>
                    <td>
                      <button className="btn btn-sm btn-outline-secondary">
                        {selectedError === i ? '▲' : '▼'}
                      </button>
                    </td>
                  </tr>
                  {/* Dettaglio espanso */}
                  {selectedError === i && (
                    <tr>
                      <td colSpan={6} className="error-detail-cell">
                        <div className="error-detail-content">
                          <div className="error-detail-section">
                            <h6>Messaggi di Errore</h6>
                            {err.error_variants && Object.keys(err.error_variants).length > 0 ? (
                              <ul className="error-variants-list">
                                {Object.entries(err.error_variants).map(([msg, count], j) => (
                                  <li key={j}>
                                    <span className="badge bg-secondary me-2">{count}x</span>
                                    <code>{msg}</code>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="text-muted">Nessun messaggio disponibile</p>
                            )}
                          </div>
                          
                          <div className="error-detail-section">
                            <h6>Campioni Recenti</h6>
                            <div className="table-responsive">
                              <table className="table table-sm table-bordered mb-0">
                                <thead>
                                  <tr>
                                    <th>Timestamp</th>
                                    <th>Latenza</th>
                                    <th>Messaggio</th>
                                    <th>User Agent</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {err.samples?.map((s, j) => (
                                    <tr key={j}>
                                      <td className="small">{new Date(s.timestamp).toLocaleString('it-IT')}</td>
                                      <td className="small">{s.latency_ms}ms</td>
                                      <td className="small">{s.status_message || '-'}</td>
                                      <td className="small text-truncate" style={{maxWidth: '200px'}}>{s.user_agent || '-'}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>

                          {err.top_user_agents && err.top_user_agents.length > 0 && (
                            <div className="error-detail-section">
                              <h6>User Agent più frequenti</h6>
                              <div className="d-flex gap-3 flex-wrap">
                                {err.top_user_agents.map((ua, j) => (
                                  <span key={j} className="badge bg-light text-dark">
                                    {ua.agent}: {ua.count}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
              {filteredErrors.length === 0 && (
                <tr><td colSpan={6} className="text-center text-muted">Nessun errore trovato per il filtro selezionato</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Log Errori Applicativi Reali (dal backend k8s_container) */}
        {data.app_errors && data.app_errors.length > 0 && (
          <div className="app-errors-section mt-4">
            <h5 className="section-title">
              <span className="badge bg-danger me-2">{data.app_errors.length}</span>
              Log Errori Applicativi
              <span className="text-muted small ms-2">(dal backend)</span>
            </h5>
            <p className="text-muted small mb-3">
              Messaggi di errore reali dal processo backend (stack trace, eccezioni Python, timeout DB, ecc.)
            </p>
            <div className="app-errors-list">
              {data.app_errors.map((appErr, i) => (
                <div key={i} className={`app-error-item severity-${(appErr.severity || 'ERROR').toLowerCase()}`}>
                  <div className="app-error-header" onClick={() => setSelectedError(selectedError === `app-${i}` ? null : `app-${i}`)} style={{ cursor: 'pointer' }}>
                    <div className="app-error-meta">
                      <span className={`badge ${appErr.severity === 'ERROR' || appErr.severity === 'CRITICAL' ? 'bg-danger' : 'bg-warning'}`}>
                        {appErr.severity}
                      </span>
                      <span className="badge bg-secondary">{appErr.count}x</span>
                      {appErr.container && <span className="badge bg-light text-dark">{appErr.container}</span>}
                    </div>
                    <div className="app-error-fingerprint">
                      <code>{appErr.fingerprint}</code>
                    </div>
                    <div className="app-error-times">
                      <span className="small text-muted">
                        {appErr.last_seen ? new Date(appErr.last_seen).toLocaleString('it-IT') : '-'}
                        {appErr.first_seen && appErr.first_seen !== appErr.last_seen && (
                          <> &mdash; da {new Date(appErr.first_seen).toLocaleString('it-IT')}</>
                        )}
                      </span>
                      <button className="btn btn-sm btn-outline-secondary ms-2">
                        {selectedError === `app-${i}` ? '\u25B2' : '\u25BC'}
                      </button>
                    </div>
                  </div>
                  {selectedError === `app-${i}` && appErr.samples && (
                    <div className="app-error-samples">
                      {appErr.samples.map((sample, j) => (
                        <div key={j} className="app-error-sample">
                          <div className="sample-meta">
                            <span className="small text-muted">{new Date(sample.timestamp).toLocaleString('it-IT')}</span>
                            {sample.pod && <span className="badge bg-light text-dark small">{sample.pod}</span>}
                          </div>
                          <pre className="app-error-message">{sample.message}</pre>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {(!data.app_errors || data.app_errors.length === 0) && (
          <div className="text-muted text-center p-3 mt-3">
            <small>Nessun log di errore applicativo trovato nel periodo (k8s_container severity &ge; WARNING)</small>
          </div>
        )}

      </div>
    );
  };

  const renderInfrastructure = () => {
    if (infraLoading) {
      return (
        <div className="monitoring-loading">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Caricamento...</span>
          </div>
          <p className="mt-3">Caricamento dati infrastruttura (kubectl / gcloud)...</p>
          <p className="text-muted small">5-10 secondi</p>
        </div>
      );
    }

    if (infraError) {
      return <div className="alert alert-danger">{infraError}</div>;
    }

    if (!infraData) {
      return <div className="text-muted text-center p-4">Nessun dato disponibile.</div>;
    }

    const { pods_metrics, nodes_metrics, hpa, deployment, pods_status, cloud_sql } = infraData;

    return (
      <div className="infra-section">
        {/* -- Deployment overview cards -- */}
        {deployment && Object.keys(deployment).length > 0 && (
          <div className="infra-block">
            <h5>Deployment Backend</h5>
            <div className="infra-cards">
              <div className="infra-card">
                <div className="infra-card-label">Repliche</div>
                <div className="infra-card-value">
                  {deployment.ready_replicas}/{deployment.replicas}
                  <span className={`infra-status-dot ${deployment.ready_replicas === deployment.replicas ? 'dot-ok' : 'dot-warning'}`} />
                </div>
              </div>
              <div className="infra-card">
                <div className="infra-card-label">Strategia</div>
                <div className="infra-card-value">{deployment.strategy}</div>
              </div>
              <div className="infra-card">
                <div className="infra-card-label">CPU Req / Limit</div>
                <div className="infra-card-value">{deployment.requests_cpu || '-'} / {deployment.limits_cpu || '-'}</div>
              </div>
              <div className="infra-card">
                <div className="infra-card-label">Mem Req / Limit</div>
                <div className="infra-card-value">{deployment.requests_memory || '-'} / {deployment.limits_memory || '-'}</div>
              </div>
            </div>
            {deployment.image && (
              <div className="infra-detail-row">
                <span className="infra-detail-label">Immagine:</span>
                <code className="infra-detail-code">{deployment.image}</code>
              </div>
            )}
            {deployment.command && (
              <div className="infra-detail-row">
                <span className="infra-detail-label">Comando:</span>
                <code className="infra-detail-code">{deployment.command}</code>
              </div>
            )}
          </div>
        )}

        {/* -- HPA -- */}
        {hpa && hpa.length > 0 && (
          <div className="infra-block">
            <h5>Horizontal Pod Autoscaler</h5>
            <div className="table-responsive">
              <table className="table table-sm table-hover">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Target</th>
                    <th className="text-center">Repliche (min/cur/max)</th>
                    <th className="text-center">CPU (current/target)</th>
                    <th className="text-center">Memoria (current/target)</th>
                  </tr>
                </thead>
                <tbody>
                  {hpa.map((h, i) => (
                    <tr key={i}>
                      <td className="fw-medium">{h.name}</td>
                      <td>{h.reference}</td>
                      <td className="text-center">
                        {h.min_replicas} / <strong>{h.current_replicas}</strong> / {h.max_replicas}
                      </td>
                      <td className="text-center">
                        {h.cpu_current_pct != null ? (
                          <span className={h.cpu_current_pct > (h.cpu_target_pct || 80) ? 'text-danger fw-bold' : ''}>
                            {h.cpu_current_pct}%
                          </span>
                        ) : '-'} / {h.cpu_target_pct != null ? `${h.cpu_target_pct}%` : '-'}
                      </td>
                      <td className="text-center">
                        {h.memory_current_pct != null ? (
                          <span className={h.memory_current_pct > (h.memory_target_pct || 80) ? 'text-danger fw-bold' : ''}>
                            {h.memory_current_pct}%
                          </span>
                        ) : '-'} / {h.memory_target_pct != null ? `${h.memory_target_pct}%` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* -- Pod Metrics (CPU/Memory usage) -- */}
        {pods_metrics && pods_metrics.length > 0 && (
          <div className="infra-block">
            <h5>Utilizzo Risorse Pod</h5>
            <div className="charts-row">
              <div className="chart-container">
                <h6>CPU (millicores)</h6>
                <ResponsiveContainer width="100%" height={Math.max(200, pods_metrics.length * 50)}>
                  <BarChart data={pods_metrics} layout="vertical" margin={{ left: 180 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={170}
                      tick={{ fontSize: 10 }}
                      tickFormatter={v => v.length > 28 ? v.slice(0, 28) + '...' : v}
                    />
                    <Tooltip formatter={(val) => [`${val}m`, 'CPU']} />
                    <Bar dataKey="cpu_millicores" name="CPU (m)" fill="#42A5F5" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="chart-container">
                <h6>Memoria (MiB)</h6>
                <ResponsiveContainer width="100%" height={Math.max(200, pods_metrics.length * 50)}>
                  <BarChart data={pods_metrics} layout="vertical" margin={{ left: 180 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={170}
                      tick={{ fontSize: 10 }}
                      tickFormatter={v => v.length > 28 ? v.slice(0, 28) + '...' : v}
                    />
                    <Tooltip formatter={(val) => [`${val} MiB`, 'Memoria']} />
                    <Bar dataKey="memory_mib" name="Memoria (MiB)" fill="#66BB6A" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* -- Node Metrics -- */}
        {nodes_metrics && nodes_metrics.length > 0 && (
          <div className="infra-block">
            <h5>Nodi Cluster</h5>
            <div className="table-responsive">
              <table className="table table-sm table-hover">
                <thead>
                  <tr>
                    <th>Nodo</th>
                    <th className="text-end">CPU (m)</th>
                    <th className="text-center">CPU %</th>
                    <th className="text-end">Memoria (MiB)</th>
                    <th className="text-center">Memoria %</th>
                  </tr>
                </thead>
                <tbody>
                  {nodes_metrics.map((n, i) => (
                    <tr key={i}>
                      <td className="fw-medium" style={{ fontFamily: 'monospace', fontSize: '0.82rem' }}>{n.name}</td>
                      <td className="text-end">{n.cpu_millicores}m</td>
                      <td className="text-center">
                        <div className="infra-pct-bar-wrap">
                          <div
                            className={`infra-pct-bar ${Number(n.cpu_pct) > 85 ? 'bar-danger' : Number(n.cpu_pct) > 60 ? 'bar-warning' : 'bar-ok'}`}
                            style={{ width: `${Math.min(Number(n.cpu_pct), 100)}%` }}
                          />
                          <span className="infra-pct-label">{n.cpu_pct}%</span>
                        </div>
                      </td>
                      <td className="text-end">{n.memory_mib} MiB</td>
                      <td className="text-center">
                        <div className="infra-pct-bar-wrap">
                          <div
                            className={`infra-pct-bar ${Number(n.memory_pct) > 85 ? 'bar-danger' : Number(n.memory_pct) > 60 ? 'bar-warning' : 'bar-ok'}`}
                            style={{ width: `${Math.min(Number(n.memory_pct), 100)}%` }}
                          />
                          <span className="infra-pct-label">{n.memory_pct}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* -- Pods Status -- */}
        {pods_status && pods_status.length > 0 && (
          <div className="infra-block">
            <h5>Stato Pod</h5>
            <div className="table-responsive">
              <table className="table table-sm table-hover">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th className="text-center">Stato</th>
                    <th className="text-center">Ready</th>
                    <th className="text-center">Restarts</th>
                    <th>Nodo</th>
                    <th>IP</th>
                    <th>Creato</th>
                  </tr>
                </thead>
                <tbody>
                  {pods_status.map((p, i) => (
                    <tr key={i}>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.82rem' }}>{p.name}</td>
                      <td className="text-center">
                        <span className={`badge ${p.status === 'Running' ? 'bg-success' : p.status === 'Pending' ? 'bg-warning' : 'bg-danger'}`}>
                          {p.status}
                        </span>
                      </td>
                      <td className="text-center">{p.ready}</td>
                      <td className="text-center">
                        <span className={p.restarts > 5 ? 'text-danger fw-bold' : p.restarts > 0 ? 'text-warning' : ''}>
                          {p.restarts}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{p.node}</td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{p.ip}</td>
                      <td className="small text-muted">
                        {p.age ? new Date(p.age).toLocaleString('it-IT') : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* -- Cloud SQL -- */}
        {cloud_sql && Object.keys(cloud_sql).length > 0 && (
          <div className="infra-block">
            <h5>Cloud SQL</h5>
            <div className="infra-cards">
              <div className="infra-card">
                <div className="infra-card-label">Stato</div>
                <div className="infra-card-value">
                  {cloud_sql.state}
                  <span className={`infra-status-dot ${cloud_sql.state === 'RUNNABLE' ? 'dot-ok' : 'dot-warning'}`} />
                </div>
              </div>
              <div className="infra-card">
                <div className="infra-card-label">Tier</div>
                <div className="infra-card-value">{cloud_sql.tier}</div>
              </div>
              <div className="infra-card">
                <div className="infra-card-label">Versione</div>
                <div className="infra-card-value">{cloud_sql.database_version}</div>
              </div>
              <div className="infra-card">
                <div className="infra-card-label">Disco</div>
                <div className="infra-card-value">{cloud_sql.disk_size_gb} GB ({cloud_sql.disk_type})</div>
              </div>
              <div className="infra-card">
                <div className="infra-card-label">Regione</div>
                <div className="infra-card-value">{cloud_sql.region}</div>
              </div>
              <div className="infra-card">
                <div className="infra-card-label">Disponibilita'</div>
                <div className="infra-card-value">{cloud_sql.availability_type}</div>
              </div>
            </div>
          </div>
        )}

        <div className="infra-actions">
          <button
            className="btn btn-sm btn-outline-primary"
            onClick={fetchInfraData}
            disabled={infraLoading}
          >
            Aggiorna dati infrastruttura
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="monitoring-page">
      <div className="monitoring-header">
        <h3>API Monitoring</h3>
        <span className="text-muted">Dati da Google Cloud Load Balancer</span>
      </div>

      {renderControls()}

      {overviewLoading && activeTab === 'overview' && renderLoading('Caricamento panoramica...', '~1-2 secondi (Cloud Monitoring)')}
      {overviewError && activeTab === 'overview' && <div className="alert alert-danger">{overviewError}</div>}

      {(overview || data) && (
        <>
          <div className="monitoring-tabs">
            <button
              className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              Panoramica
            </button>
            <button
              className={`tab-btn ${activeTab === 'endpoints' ? 'active' : ''}`}
              onClick={() => setActiveTab('endpoints')}
            >
              Dettaglio API {data ? `(${data.endpoints?.length || 0})` : ''}
            </button>
            <button
              className={`tab-btn ${activeTab === 'errors' ? 'active' : ''}`}
              onClick={() => setActiveTab('errors')}
            >
              Errori {data ? `(${data.errors?.length || 0})` : ''}
            </button>
            <button
              className={`tab-btn ${activeTab === 'infrastructure' ? 'active' : ''}`}
              onClick={() => setActiveTab('infrastructure')}
            >
              Infrastruttura
            </button>
          </div>

          {activeTab === 'overview' && renderOverview()}
          {activeTab === 'endpoints' && (loading ? renderLoading('Caricamento dettaglio endpoint...', '~5-10 secondi (Cloud Logging)') : error ? <div className="alert alert-danger">{error}</div> : data ? renderEndpointTable() : null)}
          {activeTab === 'errors' && (loading ? renderLoading('Caricamento errori...', '~5-10 secondi (Cloud Logging)') : error ? <div className="alert alert-danger">{error}</div> : data ? renderErrors() : null)}
          {activeTab === 'infrastructure' && renderInfrastructure()}

          <div className="monitoring-footer text-muted small">
            {overview && <>Periodo: {overview.period_days} giorni | Richieste totali: {overview.total_requests?.toLocaleString()}</>}
            {data && <> | Endpoint unici: {data.endpoints?.length}</>}
            {' '}| Fonte overview: Cloud Monitoring (pre-aggregato)
          </div>
        </>
      )}
    </div>
  );
}

export default Monitoring;

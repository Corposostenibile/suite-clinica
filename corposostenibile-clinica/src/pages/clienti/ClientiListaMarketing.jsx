import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { createPortal } from 'react-dom';
import clientiService from '../../services/clientiService';
import { useAuth } from '../../context/AuthContext';
import { isAdminOrCco, canAccessMarketingView } from '../../utils/rbacScope';
import './ClientiList.css';

// Peso perso e Media Soddisfazione sono ora calcolati server-side
// (vedi customers/services.py::get_marketing_metrics_for_clienti).
// Il backend espone c.peso_perso_kg (float | null) e c.media_soddisfazione (float 0-10 | null).

function CheckboxCell({ value, onToggle, state }) {
  const isSaving = state === 'saving';
  const isError = state === 'error';
  const borderColor = isError
    ? '#dc2626'
    : isSaving
      ? '#f59e0b'
      : value
        ? '#10b981'
        : '#d1d5db';
  const title = isError
    ? 'Errore nel salvataggio — riprova'
    : isSaving
      ? 'Salvataggio in corso...'
      : value
        ? 'Attivo — click per disattivare'
        : 'Inattivo — click per attivare';

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={isSaving}
      className="btn btn-sm p-0 border-0 bg-transparent"
      title={title}
      style={{ lineHeight: 1 }}
    >
      <span
        className="d-inline-flex align-items-center justify-content-center rounded"
        style={{
          width: 28,
          height: 28,
          background: value ? 'linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%)' : '#f3f4f6',
          border: `1.5px solid ${borderColor}`,
          transition: 'all 0.15s ease',
          opacity: isSaving ? 0.6 : 1,
        }}
      >
        {isSaving ? (
          <span
            className="spinner-border spinner-border-sm"
            style={{ width: 12, height: 12, borderWidth: 2, color: '#f59e0b' }}
            role="status"
          />
        ) : value ? (
          <i className="ri-check-line" style={{ color: '#059669', fontSize: 18, fontWeight: 'bold' }}></i>
        ) : null}
      </span>
    </button>
  );
}

function SoddisfazioneBadge({ value }) {
  if (value == null || Number.isNaN(Number(value))) {
    return <span className="cl-empty">&mdash;</span>;
  }
  // Scala 0-10 (nutri+coach+psico+percorso con NULL-aware count)
  const v = Number(value);
  const grad = v >= 9
    ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)'
    : v >= 8
      ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
      : v >= 7
        ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)'
        : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
  return (
    <span className="cl-badge" style={{ background: grad, color: '#fff' }} title="Media voti settimanali (nutri + coach + psico + percorso)">
      <i className="ri-star-fill" style={{ marginRight: 4 }}></i>
      {v.toFixed(1)}
    </span>
  );
}

function PesoPersoBadge({ value }) {
  if (value == null || Number.isNaN(Number(value))) {
    return <span className="cl-empty">&mdash;</span>;
  }
  const v = Number(value);
  const isLoss = v > 0;
  const isGain = v < 0;
  const grad = isLoss
    ? 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)'
    : isGain
      ? 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)'
      : '#f1f5f9';
  const color = isLoss ? '#1e40af' : isGain ? '#991b1b' : '#64748b';
  const sign = isLoss ? '-' : isGain ? '+' : '';
  return (
    <span className="cl-badge" style={{ background: grad, color }} title="Peso iniziale - Peso attuale (da check iniziali e settimanali)">
      <i className="ri-scales-3-line" style={{ fontSize: 10 }}></i>
      {sign}{Math.abs(v).toFixed(1)} kg
    </span>
  );
}

// Chiavi allineate alle colonne reali del modello Cliente (marketing_*)
const BOOL_COLUMNS = [
  { key: 'marketing_videofeedback', label: 'Videofeedback', group: 'videofeedback' },
  { key: 'marketing_videofeedback_richiesto', label: 'VF Richiesto', group: 'videofeedback' },
  { key: 'marketing_videofeedback_svolto', label: 'VF Svolto', group: 'videofeedback' },
  { key: 'marketing_videofeedback_condiviso', label: 'VF Condiviso', group: 'videofeedback' },
  { key: 'marketing_trasformazione_fisica', label: 'Trasf. Fisica', group: 'trasformazione' },
  { key: 'marketing_trasformazione_fisica_condivisa', label: 'Trasf. Fis. Condiv.', group: 'trasformazione' },
  { key: 'marketing_trasformazione', label: 'Trasformazione', group: 'trasformazione' },
  { key: 'marketing_exit_call_richiesta', label: 'Exit Call Rich.', group: 'exit_call' },
  { key: 'marketing_exit_call_svolta', label: 'Exit Call Svolta', group: 'exit_call' },
  { key: 'marketing_exit_call_condivisa', label: 'Exit Call Cond.', group: 'exit_call' },
];

const BOOL_GROUPS = [
  { key: 'videofeedback', label: 'Videofeedback', icon: 'ri-video-chat-line', color: '#8b5cf6' },
  { key: 'trasformazione', label: 'Trasformazione', icon: 'ri-sparkling-2-line', color: '#ec4899' },
  { key: 'exit_call', label: 'Exit Call', icon: 'ri-phone-line', color: '#f59e0b' },
];

const INITIAL_FILTERS = {
  origine: '',
  pesoPersoMin: '',
  pesoPersoMax: '',
  mediaMin: '',
  mediaMax: '',
  ...Object.fromEntries(BOOL_COLUMNS.map((c) => [c.key, 'all'])),
};

function getOrigineName(c) {
  // Allineato alla tab "Anagrafica" del dettaglio cliente (ClientiDetail.jsx):
  // usa il campo stringa `cliente.origine` (models.py::Cliente.origine).
  return c?.origine || '';
}

function getClientName(c) {
  return c?.nome_cognome || `${c?.nome || ''} ${c?.cognome || ''}`.trim() || '-';
}

function ClientiListaMarketing() {
  const { user } = useAuth();
  const hasAccess = canAccessMarketingView(user);
  const showOtherPills = isAdminOrCco(user);

  const visualButtons = [
    { key: 'generale', to: '/clienti-lista', label: 'Lista Generale', icon: 'ri-list-check' },
    { key: 'nutrizione', to: '/clienti-nutrizione', label: 'Visuale Nutrizione', icon: 'ri-restaurant-line' },
    { key: 'coach', to: '/clienti-coach', label: 'Visuale Coach', icon: 'ri-run-line' },
    { key: 'psicologia', to: '/clienti-psicologia', label: 'Visuale Psicologia', icon: 'ri-mental-health-line' },
    { key: 'health_manager', to: '/clienti-health-manager', label: 'Health Manager', icon: 'ri-heart-pulse-line' },
    { key: 'marketing', to: '/clienti-marketing', label: 'Visuale Marketing', icon: 'ri-megaphone-line' },
  ].filter((btn) => {
    if (btn.key === 'marketing') return true;
    return showOtherPills;
  });

  const [searchParams, setSearchParams] = useSearchParams();
  const [clienti, setClienti] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    perPage: 10,
    total: 0,
    totalPages: 0,
  });

  const [searchInput, setSearchInput] = useState(searchParams.get('q') || '');
  const [debouncedSearch, setDebouncedSearch] = useState(searchParams.get('q') || '');
  const searchTimerRef = useRef(null);

  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [showFiltersModal, setShowFiltersModal] = useState(false);

  // Feedback di salvataggio per singolo checkbox (cliente_id:field -> 'saving' | 'error')
  const [savingFlags, setSavingFlags] = useState({});

  // Scroll orizzontale tabella
  const tableScrollRef = useRef(null);
  const [scrollState, setScrollState] = useState({
    canLeft: false,
    canRight: false,
    hasOverflow: false,
  });

  const updateScrollMetrics = useCallback(() => {
    const el = tableScrollRef.current;
    if (!el) return;
    const hasOverflow = el.scrollWidth > el.clientWidth + 1;
    setScrollState({
      canLeft: el.scrollLeft > 0,
      canRight: el.scrollLeft + el.clientWidth < el.scrollWidth - 1,
      hasOverflow,
    });
  }, []);

  const scrollTable = (dir) => {
    const el = tableScrollRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 260, behavior: 'smooth' });
  };

  const handleSearchInput = (val) => {
    setSearchInput(val);
  };

  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(searchInput);
      setPagination((p) => ({ ...p, page: 1 }));
    }, 350);
    return () => {
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    };
  }, [searchInput]);

  const fetchClienti = useCallback(async () => {
    if (!hasAccess) return;
    setLoading(true);
    setError(null);
    try {
      const params = {
        page: pagination.page,
        per_page: pagination.perPage,
        q: debouncedSearch || undefined,
        // Filtro origine applicato server-side (Cliente.origine LIKE case-insensitive)
        origine: filters.origine || undefined,
      };
      const data = await clientiService.getClientiMarketing(params);
      setClienti(data.data || []);
      setPagination((p) => ({
        ...p,
        total: data.pagination?.total || 0,
        totalPages: data.pagination?.total_pages || 0,
      }));
    } catch (err) {
      console.error('Error fetching marketing clienti:', err);
      setError('Errore nel caricamento della lista clienti.');
    } finally {
      setLoading(false);
    }
  }, [hasAccess, pagination.page, pagination.perPage, debouncedSearch, filters.origine]);

  useEffect(() => {
    fetchClienti();
  }, [fetchClienti]);

  useEffect(() => {
    const params = {};
    if (debouncedSearch) params.q = debouncedSearch;
    setSearchParams(params, { replace: true });
  }, [debouncedSearch, setSearchParams]);

  // Reset pagina quando cambia l'origine (filtro server-side)
  useEffect(() => {
    setPagination((p) => (p.page === 1 ? p : { ...p, page: 1 }));
  }, [filters.origine]);

  useEffect(() => {
    updateScrollMetrics();
    const onResize = () => updateScrollMetrics();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [clienti, updateScrollMetrics]);

  const toggleBool = useCallback(async (clienteId, field, currentValue) => {
    const newValue = !currentValue;
    const flagKey = `${clienteId}:${field}`;
    setSavingFlags((prev) => ({ ...prev, [flagKey]: 'saving' }));
    setClienti((prev) => prev.map((c) =>
      c.cliente_id === clienteId ? { ...c, [field]: newValue } : c
    ));
    try {
      await clientiService.updateField(clienteId, field, newValue);
      setSavingFlags((prev) => {
        const next = { ...prev };
        delete next[flagKey];
        return next;
      });
    } catch (err) {
      console.error('Error updating marketing flag:', err);
      setClienti((prev) => prev.map((c) =>
        c.cliente_id === clienteId ? { ...c, [field]: currentValue } : c
      ));
      setSavingFlags((prev) => ({ ...prev, [flagKey]: 'error' }));
      window.setTimeout(() => {
        setSavingFlags((prev) => {
          const next = { ...prev };
          delete next[flagKey];
          return next;
        });
      }, 2500);
    }
  }, []);

  const origineOptions = useMemo(() => {
    const set = new Set();
    clienti.forEach((c) => {
      const o = getOrigineName(c);
      if (o) set.add(o);
    });
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'it'));
  }, [clienti]);

  const filteredRows = useMemo(() => {
    const pmin = filters.pesoPersoMin === '' ? null : Number(filters.pesoPersoMin);
    const pmax = filters.pesoPersoMax === '' ? null : Number(filters.pesoPersoMax);
    const smin = filters.mediaMin === '' ? null : Number(filters.mediaMin);
    const smax = filters.mediaMax === '' ? null : Number(filters.mediaMax);

    return clienti.filter((c) => {
      // NB: filters.origine è applicato server-side (vedi fetchClienti)

      if (pmin !== null || pmax !== null) {
        // Filtro attivo sul peso: escludi clienti senza dato
        if (c.peso_perso_kg == null) return false;
        const peso = Number(c.peso_perso_kg);
        if (pmin !== null && peso < pmin) return false;
        if (pmax !== null && peso > pmax) return false;
      }

      if (smin !== null || smax !== null) {
        if (c.media_soddisfazione == null) return false;
        const media = Number(c.media_soddisfazione);
        if (smin !== null && media < smin) return false;
        if (smax !== null && media > smax) return false;
      }

      for (const col of BOOL_COLUMNS) {
        const want = filters[col.key];
        if (want === 'all') continue;
        const actual = Boolean(c[col.key]);
        if (want === 'true' && !actual) return false;
        if (want === 'false' && actual) return false;
      }
      return true;
    });
  }, [clienti, filters]);

  const activeFilterCount = useMemo(() => {
    let n = 0;
    if (filters.origine) n += 1;
    if (filters.pesoPersoMin !== '' || filters.pesoPersoMax !== '') n += 1;
    if (filters.mediaMin !== '' || filters.mediaMax !== '') n += 1;
    BOOL_COLUMNS.forEach((col) => {
      if (filters[col.key] !== 'all') n += 1;
    });
    return n;
  }, [filters]);

  const resetFilters = () => setFilters(INITIAL_FILTERS);

  const handlePageChange = (newPage) => {
    setPagination((p) => ({ ...p, page: newPage }));
  };

  const getPageNumbers = () => {
    const current = pagination.page;
    const total = pagination.totalPages;
    const delta = 2;
    const pages = [];
    const rangeStart = Math.max(1, current - delta);
    const rangeEnd = Math.min(total, current + delta);
    for (let i = rangeStart; i <= rangeEnd; i++) pages.push(i);
    return pages;
  };

  if (!hasAccess) {
    return (
      <div className="container-fluid p-0">
        <div className="alert alert-warning mt-4">
          Non hai i permessi per accedere alla Visuale Marketing.
        </div>
      </div>
    );
  }

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="cl-header">
        <div>
          <h4>Visuale Marketing</h4>
          <p className="cl-header-sub">{pagination.total} pazienti in visuale marketing</p>
        </div>
        <div className="cl-view-pills">
          {visualButtons.map((btn) => (
            <Link
              key={btn.key}
              to={btn.to}
              className={`cl-view-pill${btn.key === 'marketing' ? ' active' : ''}`}
            >
              <i className={btn.icon}></i> {btn.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Search Bar + Filter Button */}
      <div className="cl-search-row">
        <div className="cl-search-wrap">
          <i className="ri-search-line cl-search-icon"></i>
          <input
            type="text"
            className="cl-search-input"
            placeholder="Cerca paziente per nome..."
            value={searchInput}
            onChange={(e) => handleSearchInput(e.target.value)}
          />
        </div>
        <button className="cl-filter-open-btn" onClick={() => setShowFiltersModal(true)}>
          <i className="ri-filter-3-line"></i> Filtra
          {activeFilterCount > 0 && (
            <span className="cl-filter-badge">{activeFilterCount}</span>
          )}
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="cl-loading">
          <div className="cl-spinner" style={{ margin: '0 auto' }}></div>
          <p className="cl-loading-text">Caricamento pazienti...</p>
        </div>
      ) : error ? (
        <div className="cl-error">{error}</div>
      ) : filteredRows.length === 0 ? (
        <div className="cl-empty-state">
          <div className="cl-empty-icon">
            <i className="ri-megaphone-line"></i>
          </div>
          <h5 className="cl-empty-title">
            {clienti.length === 0
              ? 'Nessun paziente trovato'
              : 'Nessun paziente corrisponde ai filtri'}
          </h5>
          <p className="cl-empty-desc">Prova a modificare i filtri di ricerca</p>
          {activeFilterCount > 0 && (
            <button className="cl-reset-btn" onClick={resetFilters}>
              <i className="ri-refresh-line"></i> Reset Filtri
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="cl-table-card cl-mk-table-wrap">
            {scrollState.hasOverflow && scrollState.canLeft && (
              <>
                <div className="cl-mk-fade cl-mk-fade-left" aria-hidden="true"></div>
                <button
                  type="button"
                  className="cl-mk-scroll-btn cl-mk-scroll-btn-left"
                  onClick={() => scrollTable(-1)}
                  aria-label="Scorri a sinistra"
                >
                  <i className="ri-arrow-left-s-line"></i>
                </button>
              </>
            )}
            {scrollState.hasOverflow && scrollState.canRight && (
              <>
                <div className="cl-mk-fade cl-mk-fade-right" aria-hidden="true"></div>
                <button
                  type="button"
                  className="cl-mk-scroll-btn cl-mk-scroll-btn-right"
                  onClick={() => scrollTable(1)}
                  aria-label="Scorri a destra"
                >
                  <i className="ri-arrow-right-s-line"></i>
                </button>
              </>
            )}
            <div
              className="table-responsive"
              ref={tableScrollRef}
              onScroll={updateScrollMetrics}
            >
              <table className="cl-table" style={{ minWidth: 1600 }}>
                <thead>
                  <tr>
                    <th style={{ minWidth: 200, position: 'sticky', left: 0, background: 'white', zIndex: 3 }}>Cliente</th>
                    <th style={{ minWidth: 150 }}>Origine</th>
                    <th style={{ minWidth: 110 }} title="Peso perso in kg (mock)">Peso Perso</th>
                    <th style={{ minWidth: 130 }} title="Media voto check + voto percorso (mock)">Soddisfazione</th>
                    {BOOL_COLUMNS.map((col) => (
                      <th key={col.key} style={{ textAlign: 'center', minWidth: 100 }}>{col.label}</th>
                    ))}
                    <th style={{ textAlign: 'right', minWidth: 80 }}>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((c) => (
                    <tr key={c.cliente_id}>
                      <td style={{ position: 'sticky', left: 0, background: 'white', zIndex: 1 }}>
                        <Link
                          to={`/clienti-dettaglio/${c.cliente_id}`}
                          className="cl-name-link"
                          title="Apri cartella clinica"
                        >
                          {getClientName(c)}
                        </Link>
                      </td>
                      <td>
                        {getOrigineName(c) ? (
                          <span className="cl-badge" style={{ background: 'linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%)', color: '#6d28d9' }}>
                            <i className="ri-hashtag" style={{ fontSize: 10 }}></i>
                            {getOrigineName(c)}
                          </span>
                        ) : (
                          <span className="cl-empty">&mdash;</span>
                        )}
                      </td>
                      <td>
                        <PesoPersoBadge value={c.peso_perso_kg} />
                      </td>
                      <td>
                        <SoddisfazioneBadge value={c.media_soddisfazione} />
                      </td>
                      {BOOL_COLUMNS.map((col) => {
                        const current = Boolean(c[col.key]);
                        const flagState = savingFlags[`${c.cliente_id}:${col.key}`];
                        return (
                          <td key={col.key} style={{ textAlign: 'center' }}>
                            <CheckboxCell
                              value={current}
                              onToggle={() => toggleBool(c.cliente_id, col.key, current)}
                              state={flagState}
                            />
                          </td>
                        );
                      })}
                      <td style={{ textAlign: 'right' }}>
                        <Link
                          to={`/clienti-dettaglio/${c.cliente_id}`}
                          className="cl-action-btn"
                          title="Apri cartella clinica"
                        >
                          <i className="ri-folder-open-line"></i>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination */}
          {pagination.totalPages > 1 && (
            <div className="cl-pagination">
              <span className="cl-pagination-info">
                Pagina <strong>{pagination.page}</strong> di <strong>{pagination.totalPages}</strong>
                {' '}&bull; {pagination.total} risultati
              </span>
              <div className="cl-pagination-buttons">
                <button className="cl-page-btn" onClick={() => handlePageChange(1)} disabled={pagination.page === 1} title="Prima pagina">&laquo;</button>
                <button className="cl-page-btn" onClick={() => handlePageChange(pagination.page - 1)} disabled={pagination.page === 1} title="Precedente">&lsaquo;</button>
                {getPageNumbers().map((pageNum) => (
                  <button
                    key={pageNum}
                    className={`cl-page-btn${pagination.page === pageNum ? ' active' : ''}`}
                    onClick={() => handlePageChange(pageNum)}
                  >
                    {pageNum}
                  </button>
                ))}
                <button className="cl-page-btn" onClick={() => handlePageChange(pagination.page + 1)} disabled={pagination.page === pagination.totalPages} title="Successiva">&rsaquo;</button>
                <button className="cl-page-btn" onClick={() => handlePageChange(pagination.totalPages)} disabled={pagination.page === pagination.totalPages} title="Ultima pagina">&raquo;</button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ============ MODAL FILTRI (pattern cl-modal-*, createPortal) ============ */}
      <MarketingFiltersModal
        open={showFiltersModal}
        onClose={() => setShowFiltersModal(false)}
        filters={filters}
        onApply={(next) => setFilters(next)}
        onReset={resetFilters}
        origineOptions={origineOptions}
      />
    </div>
  );
}

function MarketingFiltersModal({ open, onClose, filters, onApply, onReset, origineOptions }) {
  const [draft, setDraft] = useState({ ...filters });

  // eslint-disable-next-line react-hooks/exhaustive-deps, react-hooks/set-state-in-effect
  useEffect(() => { if (open) setDraft({ ...filters }); }, [open]);

  if (!open) return null;

  const updateDraft = (key, value) =>
    setDraft((prev) => ({ ...prev, [key]: value }));

  const handleApply = () => {
    onApply(draft);
    onClose();
  };

  const handleReset = () => {
    setDraft({ ...INITIAL_FILTERS });
    onReset();
    onClose();
  };

  const activeCount = (() => {
    let n = 0;
    if (draft.origine) n += 1;
    if (draft.pesoPersoMin !== '' || draft.pesoPersoMax !== '') n += 1;
    if (draft.mediaMin !== '' || draft.mediaMax !== '') n += 1;
    BOOL_COLUMNS.forEach((col) => {
      if (draft[col.key] !== 'all') n += 1;
    });
    return n;
  })();

  return createPortal(
    <div className="cl-modal-overlay" onClick={onClose}>
      <div className="cl-modal" onClick={(e) => e.stopPropagation()}>
        <div className="cl-modal-header">
          <h5 className="cl-modal-title">
            <i className="ri-filter-3-line"></i> Filtra Pazienti
          </h5>
          <button className="cl-modal-close" onClick={onClose}>
            <i className="ri-close-line"></i>
          </button>
        </div>

        <div className="cl-modal-body">
          {/* ── Info Cliente ── */}
          <h6 className="cl-advanced-heading">
            <i className="ri-user-line"></i> Info Cliente
          </h6>
          <div className="row g-3 mb-4">
            <div className="col-md-12">
              <label className="form-label mb-1">Origine</label>
              <select
                className="form-select"
                value={draft.origine}
                onChange={(e) => updateDraft('origine', e.target.value)}
              >
                <option value="">Tutte le origini</option>
                {origineOptions.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
              <div className="form-text small text-muted">
                Filtro applicato al backend (match case-insensitive).
              </div>
            </div>

            <div className="col-md-6">
              <label className="form-label mb-1">Peso perso (kg)</label>
              <div className="input-group">
                <input
                  type="number"
                  className="form-control"
                  placeholder="Min"
                  step="0.1"
                  value={draft.pesoPersoMin}
                  onChange={(e) => updateDraft('pesoPersoMin', e.target.value)}
                />
                <span className="input-group-text">—</span>
                <input
                  type="number"
                  className="form-control"
                  placeholder="Max"
                  step="0.1"
                  value={draft.pesoPersoMax}
                  onChange={(e) => updateDraft('pesoPersoMax', e.target.value)}
                />
              </div>
            </div>

            <div className="col-md-6">
              <label className="form-label mb-1">Soddisfazione (0-10)</label>
              <div className="input-group">
                <input
                  type="number"
                  className="form-control"
                  placeholder="Min"
                  min="0"
                  max="10"
                  step="0.1"
                  value={draft.mediaMin}
                  onChange={(e) => updateDraft('mediaMin', e.target.value)}
                />
                <span className="input-group-text">—</span>
                <input
                  type="number"
                  className="form-control"
                  placeholder="Max"
                  min="0"
                  max="10"
                  step="0.1"
                  value={draft.mediaMax}
                  onChange={(e) => updateDraft('mediaMax', e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* ── Gruppi bool Marketing ── */}
          {BOOL_GROUPS.map((group) => {
            const cols = BOOL_COLUMNS.filter((c) => c.group === group.key);
            return (
              <div className="mb-4" key={group.key}>
                <h6 className="cl-advanced-heading" style={{ color: group.color }}>
                  <i className={group.icon}></i> {group.label}
                </h6>
                <div className="row g-3">
                  {cols.map((col) => (
                    <div className="col-md-6" key={col.key}>
                      <label className="form-label mb-1">{col.label}</label>
                      <div className="btn-group w-100" role="group">
                        {[
                          { v: 'all', label: 'Tutti', icon: 'ri-subtract-line' },
                          { v: 'true', label: 'Sì', icon: 'ri-check-line' },
                          { v: 'false', label: 'No', icon: 'ri-close-line' },
                        ].map((opt) => {
                          const active = draft[col.key] === opt.v;
                          return (
                            <button
                              key={opt.v}
                              type="button"
                              className={`btn btn-sm ${
                                active
                                  ? opt.v === 'true'
                                    ? 'btn-success'
                                    : opt.v === 'false'
                                      ? 'btn-secondary'
                                      : 'btn-primary'
                                  : 'btn-outline-secondary'
                              }`}
                              onClick={() => updateDraft(col.key, opt.v)}
                            >
                              <i className={`${opt.icon} me-1`}></i>
                              {opt.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          <div className="alert alert-info small mb-0" style={{ background: '#eff6ff', borderColor: '#bfdbfe', color: '#1e40af' }}>
            <i className="ri-information-line me-1"></i>
            <strong>Nota:</strong> Origine e ricerca testuale sono applicate al backend (paginazione completa).
            I flag marketing, peso perso e soddisfazione filtrano la pagina corrente.
          </div>
        </div>

        <div className="cl-modal-footer">
          <span className="badge bg-primary-subtle text-primary me-auto">
            {activeCount} filtri attivi
          </span>
          <button className="cl-modal-btn-reset" onClick={handleReset}>
            <i className="ri-refresh-line"></i> Reset Tutti
          </button>
          <button className="cl-modal-btn-apply" onClick={handleApply}>
            <i className="ri-check-line"></i> Applica Filtri
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}

export default ClientiListaMarketing;

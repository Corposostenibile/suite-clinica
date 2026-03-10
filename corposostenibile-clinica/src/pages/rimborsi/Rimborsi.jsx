import { useState, useEffect, useCallback, useRef } from 'react';
import { useOutletContext } from 'react-router-dom';
import rimborsiService from '../../services/rimborsiService';
import './Rimborsi.css';

const TIPOLOGIA_LABELS = {
  entro_14_giorni: 'Entro 14 giorni',
  dopo_14_giorni: 'Dopo 14 giorni',
};

function Rimborsi() {
  const { user } = useOutletContext();

  // Lista rimborsi
  const [rimborsi, setRimborsi] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchList, setSearchList] = useState('');

  // Form nuovo rimborso
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [alert, setAlert] = useState(null);

  // Form fields
  const [clienteSearch, setClienteSearch] = useState('');
  const [clienteResults, setClienteResults] = useState([]);
  const [selectedCliente, setSelectedCliente] = useState(null);
  const [tipologia, setTipologia] = useState('');
  const [motivato, setMotivato] = useState(null);
  const [motivazione, setMotivazione] = useState('');
  const [dataFinePercorso, setDataFinePercorso] = useState('');
  const [searchingClienti, setSearchingClienti] = useState(false);

  const searchTimeout = useRef(null);

  // Admin check
  if (!user?.is_admin && user?.role !== 'admin') {
    return (
      <div className="rmb-unauthorized">
        <i className="ri-lock-line"></i>
        <p>Accesso non autorizzato. Solo gli admin possono accedere a questa pagina.</p>
      </div>
    );
  }

  const fetchRimborsi = useCallback(async () => {
    setLoading(true);
    try {
      const res = await rimborsiService.list({
        page,
        per_page: 20,
        search: searchList,
      });
      if (res.success) {
        setRimborsi(res.rimborsi);
        setTotalPages(res.pages);
      }
    } catch {
      setAlert({ type: 'danger', message: 'Errore nel caricamento dei rimborsi' });
    } finally {
      setLoading(false);
    }
  }, [page, searchList]);

  useEffect(() => {
    fetchRimborsi();
  }, [fetchRimborsi]);

  // Ricerca clienti con debounce
  useEffect(() => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current);

    if (clienteSearch.length < 2) {
      setClienteResults([]);
      return;
    }

    searchTimeout.current = setTimeout(async () => {
      setSearchingClienti(true);
      try {
        const res = await rimborsiService.searchClienti(clienteSearch);
        if (res.success) {
          setClienteResults(res.clienti);
        }
      } catch {
        // silent
      } finally {
        setSearchingClienti(false);
      }
    }, 300);

    return () => {
      if (searchTimeout.current) clearTimeout(searchTimeout.current);
    };
  }, [clienteSearch]);

  const resetForm = () => {
    setClienteSearch('');
    setClienteResults([]);
    setSelectedCliente(null);
    setTipologia('');
    setMotivato(null);
    setMotivazione('');
    setDataFinePercorso('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedCliente || !tipologia || motivato === null || !dataFinePercorso) {
      setAlert({ type: 'warning', message: 'Compila tutti i campi obbligatori' });
      return;
    }
    if (motivato && !motivazione.trim()) {
      setAlert({ type: 'warning', message: 'La motivazione è obbligatoria per rimborsi motivati' });
      return;
    }

    setSubmitting(true);
    try {
      const res = await rimborsiService.create({
        cliente_id: selectedCliente.id,
        tipologia,
        motivato,
        motivazione: motivato ? motivazione : '',
        data_fine_percorso: dataFinePercorso,
      });
      if (res.success) {
        setAlert({ type: 'success', message: 'Rimborso registrato con successo' });
        resetForm();
        setShowForm(false);
        fetchRimborsi();
      }
    } catch (err) {
      const msg = err.response?.data?.error || 'Errore nella registrazione del rimborso';
      setAlert({ type: 'danger', message: msg });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Sei sicuro di voler eliminare questo rimborso?')) return;
    try {
      const res = await rimborsiService.delete(id);
      if (res.success) {
        setAlert({ type: 'success', message: 'Rimborso eliminato' });
        fetchRimborsi();
      }
    } catch {
      setAlert({ type: 'danger', message: 'Errore nella cancellazione' });
    }
  };

  return (
    <div className="rmb-page">

      {/* Header */}
      <div className="rmb-header">
        <div>
          <h4>Gestione Rimborsi</h4>
          <p>Registra e monitora i rimborsi dei clienti</p>
        </div>
        <button
          className="rmb-btn-new"
          onClick={() => { setShowForm(!showForm); if (showForm) resetForm(); }}
        >
          <i className={`ri-${showForm ? 'close' : 'add'}-line`}></i>
          {showForm ? 'Chiudi' : 'Nuovo Rimborso'}
        </button>
      </div>

      {/* Alert */}
      {alert && (
        <div className={`rmb-alert ${alert.type}`}>
          <i className={`ri-${alert.type === 'success' ? 'check' : alert.type === 'warning' ? 'alert' : 'error-warning'}-line`}></i>
          {alert.message}
          <button className="rmb-alert-close" onClick={() => setAlert(null)}>
            <i className="ri-close-line"></i>
          </button>
        </div>
      )}

      {/* Form Nuovo Rimborso */}
      {showForm && (
        <div className="rmb-form-card">
          <h5>Registra Nuovo Rimborso</h5>
          <form onSubmit={handleSubmit}>

            {/* 1. Ricerca Cliente */}
            <div className="rmb-form-section">
              <label className="rmb-form-label">1. Seleziona Cliente</label>
              {selectedCliente ? (
                <div className="rmb-selected-cliente">
                  <span>
                    <i className="ri-user-heart-line" style={{ marginRight: 8, color: '#15803d' }}></i>
                    <strong>{selectedCliente.nome}</strong>
                    {selectedCliente.stato && (
                      <span style={{ color: 'var(--rmb-text-muted)', marginLeft: 8 }}>
                        {selectedCliente.stato}
                      </span>
                    )}
                  </span>
                  <button
                    type="button"
                    className="rmb-btn-change"
                    onClick={() => { setSelectedCliente(null); setClienteSearch(''); }}
                  >
                    Cambia
                  </button>
                </div>
              ) : (
                <div className="position-relative">
                  <input
                    type="text"
                    className="rmb-search-input"
                    placeholder="Cerca per nome e cognome..."
                    value={clienteSearch}
                    onChange={(e) => setClienteSearch(e.target.value)}
                    autoFocus
                  />
                  {searchingClienti && (
                    <div className="rmb-search-spinner">
                      <div className="spinner-border spinner-border-sm" style={{ color: 'var(--rmb-primary)' }}></div>
                    </div>
                  )}
                  {clienteResults.length > 0 && (
                    <div className="rmb-search-dropdown">
                      {clienteResults.map((c) => (
                        <div
                          key={c.id}
                          className="rmb-search-item"
                          onClick={() => {
                            setSelectedCliente(c);
                            setClienteSearch('');
                            setClienteResults([]);
                          }}
                        >
                          <i className="ri-user-line" style={{ color: 'var(--rmb-text-light)' }}></i>
                          <span>{c.nome}</span>
                          {c.stato && (
                            <span style={{ color: 'var(--rmb-text-light)', fontSize: 12, marginLeft: 'auto' }}>
                              {c.stato}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                  {clienteSearch.length >= 2 && clienteResults.length === 0 && !searchingClienti && (
                    <div className="rmb-search-dropdown">
                      <div className="rmb-search-item empty">Nessun cliente trovato</div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 2. Tipologia */}
            <div className="rmb-form-section">
              <label className="rmb-form-label">2. Tipologia di Rimborso</label>
              <div className="rmb-options-row">
                <div
                  className={`rmb-option-card ${tipologia === 'entro_14_giorni' ? 'selected' : ''}`}
                  onClick={() => setTipologia('entro_14_giorni')}
                >
                  <i className="ri-time-line"></i>
                  <span>Entro 14 giorni</span>
                </div>
                <div
                  className={`rmb-option-card ${tipologia === 'dopo_14_giorni' ? 'selected' : ''}`}
                  onClick={() => setTipologia('dopo_14_giorni')}
                >
                  <i className="ri-calendar-check-line"></i>
                  <span>Dopo 14 giorni</span>
                </div>
              </div>
            </div>

            {/* 3. Motivato / Immotivato */}
            <div className="rmb-form-section">
              <label className="rmb-form-label">3. Il rimborso è motivato?</label>
              <div className="rmb-options-row">
                <div
                  className={`rmb-option-card ${motivato === true ? 'selected' : ''}`}
                  onClick={() => setMotivato(true)}
                >
                  <i className="ri-chat-check-line"></i>
                  <span>Motivato</span>
                </div>
                <div
                  className={`rmb-option-card ${motivato === false ? 'selected' : ''}`}
                  onClick={() => setMotivato(false)}
                >
                  <i className="ri-chat-delete-line"></i>
                  <span>Immotivato</span>
                </div>
              </div>
            </div>

            {/* 4. Motivazione (solo se motivato) */}
            {motivato === true && (
              <div className="rmb-form-section">
                <label className="rmb-form-label">4. Motivazione</label>
                <textarea
                  className="rmb-textarea"
                  rows={3}
                  placeholder="Descrivi la motivazione del rimborso..."
                  value={motivazione}
                  onChange={(e) => setMotivazione(e.target.value)}
                />
              </div>
            )}

            {/* 5. Data Fine Percorso */}
            <div className="rmb-form-section">
              <label className="rmb-form-label">
                {motivato === true ? '5' : '4'}. Data Fine Percorso
              </label>
              <input
                type="date"
                className="rmb-date-input"
                value={dataFinePercorso}
                onChange={(e) => setDataFinePercorso(e.target.value)}
              />
              <span className="rmb-form-sublabel">
                Questa data verrà aggiornata anche nel dettaglio del paziente.
              </span>
            </div>

            {/* Submit */}
            <div className="rmb-form-actions">
              <button type="submit" className="rmb-btn-submit" disabled={submitting}>
                {submitting ? (
                  <>
                    <span className="spinner-border spinner-border-sm"></span>
                    Salvataggio...
                  </>
                ) : (
                  <>
                    <i className="ri-save-line"></i>
                    Registra Rimborso
                  </>
                )}
              </button>
              <button
                type="button"
                className="rmb-btn-cancel"
                onClick={() => { setShowForm(false); resetForm(); }}
              >
                Annulla
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Lista Rimborsi */}
      <div className="rmb-list-card">
        <div className="rmb-list-header">
          <h5>Rimborsi Registrati</h5>
          <div className="rmb-search-bar">
            <i className="ri-search-line"></i>
            <input
              type="text"
              placeholder="Cerca per nome..."
              value={searchList}
              onChange={(e) => { setSearchList(e.target.value); setPage(1); }}
            />
          </div>
        </div>

        {loading ? (
          <div className="rmb-loading">
            <div className="spinner-border" style={{ color: 'var(--rmb-primary)' }}></div>
          </div>
        ) : rimborsi.length === 0 ? (
          <div className="rmb-empty">
            <i className="ri-refund-2-line"></i>
            <p>Nessun rimborso registrato</p>
          </div>
        ) : (
          <>
            <div style={{ overflowX: 'auto' }}>
              <table className="rmb-table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Professionisti</th>
                    <th>Tipologia</th>
                    <th>Motivato</th>
                    <th>Data Fine Percorso</th>
                    <th>Registrato il</th>
                    <th>Da</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {rimborsi.map((r) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600 }}>{r.cliente_nome}</td>
                      <td>
                        {r.professionisti_snapshot && r.professionisti_snapshot.length > 0 ? (
                          <div className="rmb-prof-list">
                            {r.professionisti_snapshot.map((p, idx) => (
                              <div key={idx} className="rmb-prof-chip">
                                <i className={`ri-${p.ruolo === 'nutrizionista' ? 'restaurant' : p.ruolo === 'coach' ? 'run' : 'mental-health'}-line`}></i>
                                <span>{p.nome}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <span style={{ color: 'var(--rmb-text-light)', fontSize: 13 }}>Nessuno</span>
                        )}
                      </td>
                      <td>
                        <span className={`rmb-badge ${r.tipologia === 'entro_14_giorni' ? 'info' : 'warning'}`}>
                          {TIPOLOGIA_LABELS[r.tipologia]}
                        </span>
                      </td>
                      <td>
                        {r.motivato ? (
                          <div>
                            <span className="rmb-badge success">
                              <i className="ri-chat-check-line"></i> Sì
                            </span>
                            {r.motivazione && (
                              <p className="rmb-motivazione">{r.motivazione}</p>
                            )}
                          </div>
                        ) : (
                          <span className="rmb-badge neutral">
                            <i className="ri-chat-delete-line"></i> No
                          </span>
                        )}
                      </td>
                      <td>{r.data_fine_percorso ? new Date(r.data_fine_percorso).toLocaleDateString('it-IT') : '-'}</td>
                      <td>{r.created_at ? new Date(r.created_at).toLocaleDateString('it-IT') : '-'}</td>
                      <td style={{ color: 'var(--rmb-text-muted)' }}>{r.created_by_name || '-'}</td>
                      <td>
                        <button
                          className="rmb-btn-delete"
                          onClick={() => handleDelete(r.id)}
                          title="Elimina rimborso"
                        >
                          <i className="ri-delete-bin-line"></i>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="rmb-pagination">
                <button
                  className="rmb-page-btn"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  <i className="ri-arrow-left-s-line"></i>
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    className={`rmb-page-btn ${p === page ? 'active' : ''}`}
                    onClick={() => setPage(p)}
                  >
                    {p}
                  </button>
                ))}
                <button
                  className="rmb-page-btn"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                >
                  <i className="ri-arrow-right-s-line"></i>
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default Rimborsi;

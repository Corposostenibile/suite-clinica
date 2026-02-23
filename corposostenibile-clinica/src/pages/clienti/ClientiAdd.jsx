import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import clientiService, {
  STATO_CLIENTE,
  STATO_LABELS,
  TIPOLOGIA_CLIENTE,
  TIPOLOGIA_LABELS,
  GENERE,
  GENERE_LABELS,
  PAGAMENTO,
  PAGAMENTO_LABELS,
  GIORNI,
  GIORNI_LABELS,
  LUOGO_ALLENAMENTO,
  LUOGO_LABELS,
  TEAM,
  TEAM_LABELS,
} from '../../services/clientiService';
import teamService from '../../services/teamService';
import originsService from '../../services/originsService';
import './clienti-add-responsive.css';

function ClientiAdd() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [professionisti, setProfessionisti] = useState([]);
  const [origins, setOrigins] = useState([]);
  const [activeTab, setActiveTab] = useState('anagrafica');

  // Form data
  const [formData, setFormData] = useState({
    // Anagrafica
    nome_cognome: '',
    data_di_nascita: '',
    genere: '',
    mail: '',
    numero_telefono: '',
    indirizzo: '',
    paese: '',
    professione: '',
    professione_note: '',
    // Abbonamento
    data_inizio_abbonamento: '',
    durata_programma_giorni: '',
    deposito_iniziale: '',
    modalita_pagamento: '',
    rate_cliente_sales: '',
    note_rinnovo: '',
    // Programma
    programma_attuale: '',
    programma_attuale_dettaglio: '',
    macrocategoria: '',
    tipologia_cliente: '',
    categoria: '',
    di_team: '',
    // Stati
    stato_cliente: 'attivo',
    stato_nutrizione: '',
    stato_coach: '',
    stato_psicologia: '',
    // Professionisti
    nutrizionista_id: '',
    coach_id: '',
    psicologa_id: '',
    health_manager_id: '',
    // Planning
    check_day: '',
    luogo_di_allenamento: '',
    // Psicologia
    sedute_psicologia_comprate: '',
    sedute_psicologia_svolte: '',
    // Origine
    origine_id: '',
  });

  // Fetch professionisti
  useEffect(() => {
    const fetchProfessionisti = async () => {
      try {
        const data = await teamService.getTeamMembers({ per_page: 100, active: '1' });
        setProfessionisti(data.members || []);
      } catch (err) {
        console.error('Error fetching professionisti:', err);
      }
    };
    fetchProfessionisti();
  }, []);

  // Fetch origins
  useEffect(() => {
    const fetchOrigins = async () => {
      try {
        const result = await originsService.getOrigins();
        if (result.success) {
          setOrigins(result.origins || []);
        }
      } catch (err) {
        console.error('Error fetching origins:', err);
      }
    };
    fetchOrigins();
  }, []);

  // Fetch client data if editing
  useEffect(() => {
    if (isEdit) {
      const fetchCliente = async () => {
        setLoading(true);
        try {
          const data = await clientiService.getCliente(id);
          const cliente = data.data || data;
          // Map API response to form fields
          setFormData({
            nome_cognome: cliente.nome_cognome || cliente.nomeCognome || '',
            data_di_nascita: cliente.data_di_nascita || cliente.dataDiNascita || '',
            genere: cliente.genere || '',
            mail: cliente.mail || cliente.email || '',
            numero_telefono: cliente.numero_telefono || cliente.numeroTelefono || '',
            indirizzo: cliente.indirizzo || '',
            paese: cliente.paese || '',
            professione: cliente.professione || '',
            professione_note: cliente.professione_note || cliente.professioneNote || '',
            data_inizio_abbonamento: cliente.data_inizio_abbonamento || cliente.dataInizioAbbonamento || '',
            durata_programma_giorni: cliente.durata_programma_giorni || cliente.durataProgrmmGiorni || '',
            deposito_iniziale: cliente.deposito_iniziale || cliente.depositoIniziale || '',
            modalita_pagamento: cliente.modalita_pagamento || cliente.modalitaPagamento || '',
            rate_cliente_sales: cliente.rate_cliente_sales || cliente.rateClienteSales || '',
            note_rinnovo: cliente.note_rinnovo || cliente.noteRinnovo || '',
            programma_attuale: cliente.programma_attuale || cliente.programmaAttuale || '',
            programma_attuale_dettaglio: cliente.programma_attuale_dettaglio || cliente.programmaAttualeDettaglio || '',
            macrocategoria: cliente.macrocategoria || '',
            tipologia_cliente: cliente.tipologia_cliente || cliente.tipologiaCliente || '',
            categoria: cliente.categoria || '',
            di_team: cliente.di_team || cliente.diTeam || '',
            stato_cliente: cliente.stato_cliente || cliente.statoCliente || 'attivo',
            stato_nutrizione: cliente.stato_nutrizione || cliente.statoNutrizione || '',
            stato_coach: cliente.stato_coach || cliente.statoCoach || '',
            stato_psicologia: cliente.stato_psicologia || cliente.statoPsicologia || '',
            nutrizionista_id: cliente.nutrizionista_id || cliente.nutrizionistaId || '',
            coach_id: cliente.coach_id || cliente.coachId || '',
            psicologa_id: cliente.psicologa_id || cliente.psicologaId || '',
            health_manager_id: cliente.health_manager_id || cliente.healthManagerId || '',
            check_day: cliente.check_day || cliente.checkDay || '',
            luogo_di_allenamento: cliente.luogo_di_allenamento || cliente.luogoDiAllenamento || '',
            sedute_psicologia_comprate: cliente.sedute_psicologia_comprate || cliente.sedutePsicologiaComprate || '',
            sedute_psicologia_svolte: cliente.sedute_psicologia_svolte || cliente.sedutePsicologiaSvolte || '',
            origine_id: cliente.origine_id || cliente.origineId || '',
          });
        } catch (err) {
          console.error('Error fetching cliente:', err);
          setError('Errore nel caricamento del cliente');
        } finally {
          setLoading(false);
        }
      };
      fetchCliente();
    }
  }, [id, isEdit]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      // Clean empty values
      const cleanData = Object.fromEntries(
        Object.entries(formData).filter(([_, v]) => v !== '' && v !== null)
      );

      if (isEdit) {
        await clientiService.updateCliente(id, cleanData);
      } else {
        await clientiService.createCliente(cleanData);
      }
      navigate('/clienti-lista');
    } catch (err) {
      console.error('Error saving cliente:', err);
      setError(err.response?.data?.message || 'Errore nel salvataggio');
    } finally {
      setSaving(false);
    }
  };

  // Filter professionisti by specialty
  const nutrizionisti = professionisti.filter(p =>
    p.specialty === 'nutrizione' || p.specialty === 'nutrizionista'
  );
  const coaches = professionisti.filter(p => p.specialty === 'coach');
  const psicologi = professionisti.filter(p =>
    p.specialty === 'psicologia' || p.specialty === 'psicologo'
  );

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" style={{ width: '3rem', height: '3rem' }}></div>
        <p className="mt-3 text-muted">Caricamento...</p>
      </div>
    );
  }

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between mb-4 ca-header">
        <div>
          <h4 className="mb-1">{isEdit ? 'Modifica Cliente' : 'Nuovo Cliente'}</h4>
          <p className="text-muted mb-0">
            {isEdit ? `Modifica i dati di ${formData.nome_cognome}` : 'Inserisci i dati del nuovo cliente'}
          </p>
        </div>
        <Link to="/clienti-lista" className="btn btn-outline-secondary">
          <i className="ri-arrow-left-line me-2"></i>
          Torna alla Lista
        </Link>
      </div>

      {error && (
        <div className="alert alert-danger alert-dismissible fade show" role="alert">
          {error}
          <button type="button" className="btn-close" onClick={() => setError(null)}></button>
        </div>
      )}

      <div className="row">
        {/* Main Form */}
        <div className="col-xl-8">
          <div className="card shadow-sm border-0" style={{ borderRadius: '12px' }}>
            {/* Tabs */}
            <div className="card-header bg-white border-0 pt-4 pb-0 ca-tabs-container">
              <ul className="nav nav-tabs border-0">
                {[
                  { id: 'anagrafica', label: 'Anagrafica', icon: 'ri-user-line' },
                  { id: 'abbonamento', label: 'Abbonamento', icon: 'ri-vip-crown-line' },
                  { id: 'programma', label: 'Programma', icon: 'ri-file-list-3-line' },
                  { id: 'team', label: 'Team', icon: 'ri-team-line' },
                ].map(tab => (
                  <li key={tab.id} className="nav-item">
                    <button
                      className={`nav-link ${activeTab === tab.id ? 'active' : ''}`}
                      onClick={() => setActiveTab(tab.id)}
                      type="button"
                    >
                      <i className={`${tab.icon} me-2`}></i>
                      {tab.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="card-body p-4 ca-form">
                {/* Tab: Anagrafica */}
                {activeTab === 'anagrafica' && (
                  <div className="row g-3">
                    <div className="col-12">
                      <label className="form-label fw-semibold">Nome e Cognome *</label>
                      <input
                        type="text"
                        className="form-control"
                        name="nome_cognome"
                        value={formData.nome_cognome}
                        onChange={handleChange}
                        required
                        placeholder="es. Mario Rossi"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Data di Nascita</label>
                      <input
                        type="date"
                        className="form-control"
                        name="data_di_nascita"
                        value={formData.data_di_nascita}
                        onChange={handleChange}
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Genere</label>
                      <select
                        className="form-select"
                        name="genere"
                        value={formData.genere}
                        onChange={handleChange}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(GENERE_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Email</label>
                      <input
                        type="email"
                        className="form-control"
                        name="mail"
                        value={formData.mail}
                        onChange={handleChange}
                        placeholder="email@esempio.com"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Telefono</label>
                      <input
                        type="tel"
                        className="form-control"
                        name="numero_telefono"
                        value={formData.numero_telefono}
                        onChange={handleChange}
                        placeholder="+39 123 456 7890"
                      />
                    </div>
                    <div className="col-12">
                      <label className="form-label fw-semibold">Indirizzo</label>
                      <input
                        type="text"
                        className="form-control"
                        name="indirizzo"
                        value={formData.indirizzo}
                        onChange={handleChange}
                        placeholder="Via, Numero, CAP, Città"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Paese</label>
                      <input
                        type="text"
                        className="form-control"
                        name="paese"
                        value={formData.paese}
                        onChange={handleChange}
                        placeholder="Italia"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Professione</label>
                      <input
                        type="text"
                        className="form-control"
                        name="professione"
                        value={formData.professione}
                        onChange={handleChange}
                      />
                    </div>
                    <div className="col-12">
                      <label className="form-label fw-semibold">Note Professione</label>
                      <textarea
                        className="form-control"
                        name="professione_note"
                        value={formData.professione_note}
                        onChange={handleChange}
                        rows="2"
                      ></textarea>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">
                        <i className="ri-global-line me-2 text-primary"></i>
                        Origine
                      </label>
                      <select
                        className="form-select"
                        name="origine_id"
                        value={formData.origine_id}
                        onChange={handleChange}
                      >
                        <option value="">Nessuna origine</option>
                        {origins
                          .filter(o => o.active)
                          .map(origin => (
                            <option key={origin.id} value={origin.id}>
                              {origin.name}
                            </option>
                          ))}
                      </select>
                      <small className="text-muted d-block mt-1">Seleziona l'origine/campagna del cliente</small>
                    </div>
                  </div>
                )}

                {/* Tab: Abbonamento */}
                {activeTab === 'abbonamento' && (
                  <div className="row g-3">
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Data Inizio Abbonamento</label>
                      <input
                        type="date"
                        className="form-control"
                        name="data_inizio_abbonamento"
                        value={formData.data_inizio_abbonamento}
                        onChange={handleChange}
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Durata Programma (giorni)</label>
                      <input
                        type="number"
                        className="form-control"
                        name="durata_programma_giorni"
                        value={formData.durata_programma_giorni}
                        onChange={handleChange}
                        min="1"
                        placeholder="90"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Deposito Iniziale</label>
                      <div className="input-group">
                        <span className="input-group-text">€</span>
                        <input
                          type="number"
                          className="form-control"
                          name="deposito_iniziale"
                          value={formData.deposito_iniziale}
                          onChange={handleChange}
                          step="0.01"
                          min="0"
                        />
                      </div>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Modalità Pagamento</label>
                      <select
                        className="form-select"
                        name="modalita_pagamento"
                        value={formData.modalita_pagamento}
                        onChange={handleChange}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(PAGAMENTO_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">LTV (Rate Cliente Sales)</label>
                      <div className="input-group">
                        <span className="input-group-text">€</span>
                        <input
                          type="number"
                          className="form-control"
                          name="rate_cliente_sales"
                          value={formData.rate_cliente_sales}
                          onChange={handleChange}
                          step="0.01"
                          min="0"
                        />
                      </div>
                    </div>
                    <div className="col-12">
                      <label className="form-label fw-semibold">Note Rinnovo</label>
                      <textarea
                        className="form-control"
                        name="note_rinnovo"
                        value={formData.note_rinnovo}
                        onChange={handleChange}
                        rows="3"
                      ></textarea>
                    </div>
                  </div>
                )}

                {/* Tab: Programma */}
                {activeTab === 'programma' && (
                  <div className="row g-3">
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Stato Cliente</label>
                      <select
                        className="form-select"
                        name="stato_cliente"
                        value={formData.stato_cliente}
                        onChange={handleChange}
                      >
                        {Object.entries(STATO_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Tipologia Cliente</label>
                      <select
                        className="form-select"
                        name="tipologia_cliente"
                        value={formData.tipologia_cliente}
                        onChange={handleChange}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(TIPOLOGIA_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Team di Vendita</label>
                      <select
                        className="form-select"
                        name="di_team"
                        value={formData.di_team}
                        onChange={handleChange}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(TEAM_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Check Day</label>
                      <select
                        className="form-select"
                        name="check_day"
                        value={formData.check_day}
                        onChange={handleChange}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(GIORNI_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Luogo di Allenamento</label>
                      <select
                        className="form-select"
                        name="luogo_di_allenamento"
                        value={formData.luogo_di_allenamento}
                        onChange={handleChange}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(LUOGO_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Programma Attuale</label>
                      <input
                        type="text"
                        className="form-control"
                        name="programma_attuale"
                        value={formData.programma_attuale}
                        onChange={handleChange}
                      />
                    </div>
                  </div>
                )}

                {/* Tab: Team */}
                {activeTab === 'team' && (
                  <div className="row g-3">
                    <div className="col-12 mb-3">
                      <div className="alert alert-info">
                        <i className="ri-information-line me-2"></i>
                        Assegna i professionisti che seguiranno questo cliente.
                      </div>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">
                        <i className="ri-heart-pulse-line me-2 text-info"></i>
                        Nutrizionista
                      </label>
                      <select
                        className="form-select"
                        name="nutrizionista_id"
                        value={formData.nutrizionista_id}
                        onChange={handleChange}
                      >
                        <option value="">Nessuno</option>
                        {nutrizionisti.map(p => (
                          <option key={p.id} value={p.id}>{p.full_name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Stato Nutrizione</label>
                      <select
                        className="form-select"
                        name="stato_nutrizione"
                        value={formData.stato_nutrizione}
                        onChange={handleChange}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(STATO_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">
                        <i className="ri-run-line me-2 text-success"></i>
                        Coach
                      </label>
                      <select
                        className="form-select"
                        name="coach_id"
                        value={formData.coach_id}
                        onChange={handleChange}
                      >
                        <option value="">Nessuno</option>
                        {coaches.map(p => (
                          <option key={p.id} value={p.id}>{p.full_name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Stato Coach</label>
                      <select
                        className="form-select"
                        name="stato_coach"
                        value={formData.stato_coach}
                        onChange={handleChange}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(STATO_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">
                        <i className="ri-mental-health-line me-2 text-warning"></i>
                        Psicologo/a
                      </label>
                      <select
                        className="form-select"
                        name="psicologa_id"
                        value={formData.psicologa_id}
                        onChange={handleChange}
                      >
                        <option value="">Nessuno</option>
                        {psicologi.map(p => (
                          <option key={p.id} value={p.id}>{p.full_name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Stato Psicologia</label>
                      <select
                        className="form-select"
                        name="stato_psicologia"
                        value={formData.stato_psicologia}
                        onChange={handleChange}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(STATO_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Sedute Psicologia Comprate</label>
                      <input
                        type="number"
                        className="form-control"
                        name="sedute_psicologia_comprate"
                        value={formData.sedute_psicologia_comprate}
                        onChange={handleChange}
                        min="0"
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Sedute Psicologia Svolte</label>
                      <input
                        type="number"
                        className="form-control"
                        name="sedute_psicologia_svolte"
                        value={formData.sedute_psicologia_svolte}
                        onChange={handleChange}
                        min="0"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Form Actions */}
              <div className="card-footer bg-light border-0 py-3 ca-footer">
                <div className="d-flex justify-content-end gap-2">
                  <Link to="/clienti-lista" className="btn btn-outline-secondary">
                    Annulla
                  </Link>
                  <button type="submit" className="btn btn-primary" disabled={saving}>
                    {saving ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-2"></span>
                        Salvataggio...
                      </>
                    ) : (
                      <>
                        <i className="ri-save-line me-2"></i>
                        {isEdit ? 'Salva Modifiche' : 'Crea Cliente'}
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

        {/* Preview Card */}
        <div className="col-xl-4">
          <div className="card shadow-sm border-0 sticky-top ca-preview-card" style={{ borderRadius: '12px', top: '100px' }}>
            {/* Header Gradient */}
            <div
              style={{
                background: 'linear-gradient(135deg, #1B5E20 0%, #4CAF50 100%)',
                height: '80px',
                borderRadius: '12px 12px 0 0',
                position: 'relative'
              }}
            >
              <div className="position-absolute start-50 translate-middle" style={{ top: '100%' }}>
                <div
                  className="rounded-circle border border-4 border-white shadow d-flex align-items-center justify-content-center bg-white"
                  style={{ width: '80px', height: '80px' }}
                >
                  <span className="fw-bold fs-3 text-success">
                    {clientiService.getInitials(formData.nome_cognome || 'NC')}
                  </span>
                </div>
              </div>
            </div>

            <div className="card-body text-center pt-5 mt-3">
              <h5 className="fw-bold mb-1">{formData.nome_cognome || 'Nuovo Cliente'}</h5>
              <p className="text-muted small mb-3">{formData.mail || 'email@esempio.com'}</p>

              <div className="d-flex justify-content-center gap-2 mb-3">
                {formData.stato_cliente && (
                  <span className={`badge bg-${clientiService.getStatoBadgeColor(formData.stato_cliente)}`}>
                    {STATO_LABELS[formData.stato_cliente]}
                  </span>
                )}
                {formData.tipologia_cliente && (
                  <span className={`badge bg-${clientiService.getTipologiaBadgeColor(formData.tipologia_cliente)}`}>
                    {TIPOLOGIA_LABELS[formData.tipologia_cliente]}
                  </span>
                )}
              </div>

              <hr />

              <div className="text-start">
                <p className="small mb-2">
                  <i className="ri-phone-line me-2 text-muted"></i>
                  {formData.numero_telefono || '-'}
                </p>
                <p className="small mb-2">
                  <i className="ri-map-pin-line me-2 text-muted"></i>
                  {formData.paese || '-'}
                </p>
                <p className="small mb-2">
                  <i className="ri-calendar-line me-2 text-muted"></i>
                  Check: {formData.check_day ? GIORNI_LABELS[formData.check_day] : '-'}
                </p>
                {formData.data_inizio_abbonamento && (
                  <p className="small mb-2">
                    <i className="ri-vip-crown-line me-2 text-muted"></i>
                    Inizio: {clientiService.formatDate(formData.data_inizio_abbonamento)}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ClientiAdd;

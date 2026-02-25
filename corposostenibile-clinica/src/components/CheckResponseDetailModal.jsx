import { Link } from 'react-router-dom';

const getInitials = (name) => {
  if (!name) return '??';
  return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
};

/**
 * Modal dettaglio risposta check (weekly/dca).
 * Props:
 * - show: boolean
 * - onClose: () => void
 * - response: object (selectedCheckResponse)
 * - loading: boolean
 * - onlyProfessionalRole: optional 'nutrizionista' | 'coach' | 'psicologo' — quando valorizzato mostra solo quella valutazione e quel feedback
 */
function CheckResponseDetailModal({ show, onClose, response, loading, onlyProfessionalRole }) {
  if (!show || !response) return null;

  const showRating = (role) => !onlyProfessionalRole || onlyProfessionalRole === role;
  const showFeedback = (role) => !onlyProfessionalRole || onlyProfessionalRole === role;

  return (
    <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={onClose}>
      <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable" onClick={(e) => e.stopPropagation()} data-tour="check-detail-modal">
        <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
          <div className="modal-header" style={{
            background: response.type === 'weekly' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' :
              response.type === 'dca' ? 'linear-gradient(135deg, #a855f7 0%, #9333ea 100%)' :
                'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            color: 'white',
            border: 'none'
          }}>
            <h5 className="modal-title">
              <i className={`me-2 ${response.type === 'weekly' ? 'ri-calendar-check-line' : response.type === 'dca' ? 'ri-heart-pulse-line' : 'ri-user-heart-line'}`}></i>
              {response.type === 'weekly' ? 'Check Settimanale' : response.type === 'dca' ? 'Check Benessere' : 'Check Minori'}
              {response.cliente_nome && (
                <span className="ms-2 opacity-75">- {response.cliente_nome}</span>
              )}
            </h5>
            <button className="btn-close btn-close-white" onClick={onClose}></button>
          </div>
          <div className="modal-body p-4">
            {loading ? (
              <div className="text-center py-5">
                <div className="spinner-border text-primary" role="status"></div>
                <p className="text-muted mt-3">Caricamento dettagli...</p>
              </div>
            ) : (
              <div>
                <div className="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom">
                  <div>
                    <small className="text-muted">Data compilazione</small>
                    <p className="mb-0 fw-semibold">{response.submit_date}</p>
                  </div>
                  {response.type === 'weekly' && (
                    <div className="text-end">
                      <small className="text-muted">Peso</small>
                      <p className="mb-0 fw-semibold">{response.weight ? `${response.weight} kg` : <span className="text-muted">-</span>}</p>
                    </div>
                  )}
                </div>

                {response.type === 'weekly' && (
                  <div className="mb-4" data-tour="check-photos">
                    <h6 className="text-muted mb-3"><i className="ri-camera-line me-2"></i>Foto Progressi</h6>
                    <div className="row g-3">
                      {['photo_front', 'photo_side', 'photo_back'].map((key, idx) => {
                        const labels = ['Frontale', 'Laterale', 'Posteriore'];
                        const url = response[key];
                        return (
                          <div key={key} className="col-4">
                            <div className="text-center">
                              <small className="text-muted d-block mb-2">{labels[idx]}</small>
                              {url ? (
                                <img src={url} alt={labels[idx]} className="img-fluid rounded" style={{ maxHeight: '150px', objectFit: 'cover', cursor: 'pointer' }} onClick={() => window.open(url, '_blank')} />
                              ) : (
                                <div className="p-4 rounded d-flex align-items-center justify-content-center" style={{ background: '#f8fafc', minHeight: '100px' }}>
                                  <span className="text-muted small">Non caricata</span>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {(response.nutritionist_rating || response.psychologist_rating || response.coach_rating || response.progress_rating) && (
                  <div className="mb-4" data-tour="check-ratings">
                    <h6 className="text-muted mb-3"><i className="ri-star-line me-2"></i>Valutazioni Professionisti</h6>
                    <div className="row g-3">
                      {showRating('nutrizionista') && response.nutritionist_rating != null && (() => {
                        const nutri = response.nutrizionisti?.[0];
                        return (
                          <div key="nutri" className="col-6 col-md-3">
                            <div className="p-3 rounded text-center" style={{ background: '#dcfce7' }}>
                              {nutri && (
                                <div className="mb-2 d-flex justify-content-center">
                                  {nutri.avatar_path ? (
                                    <img src={nutri.avatar_path} alt="" className="rounded-circle" style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #22c55e' }} />
                                  ) : (
                                    <div className="rounded-circle bg-success text-white d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', fontSize: '0.75rem' }}>
                                      {getInitials(nutri.nome)}
                                    </div>
                                  )}
                                </div>
                              )}
                              <div className="fw-bold fs-4 text-success">{response.nutritionist_rating}</div>
                              <small className="text-muted">{nutri?.nome || 'Nutrizionista'}</small>
                            </div>
                          </div>
                        );
                      })()}
                      {showRating('psicologo') && response.psychologist_rating != null && (() => {
                        const psico = response.psicologi?.[0];
                        return (
                          <div key="psico" className="col-6 col-md-3">
                            <div className="p-3 rounded text-center" style={{ background: '#fef3c7' }}>
                              {psico && (
                                <div className="mb-2 d-flex justify-content-center">
                                  {psico.avatar_path ? (
                                    <img src={psico.avatar_path} alt="" className="rounded-circle" style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #d97706' }} />
                                  ) : (
                                    <div className="rounded-circle text-white d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', fontSize: '0.75rem', background: '#d97706' }}>
                                      {getInitials(psico.nome)}
                                    </div>
                                  )}
                                </div>
                              )}
                              <div className="fw-bold fs-4" style={{ color: '#d97706' }}>{response.psychologist_rating}</div>
                              <small className="text-muted">{psico?.nome || 'Psicologo'}</small>
                            </div>
                          </div>
                        );
                      })()}
                      {showRating('coach') && response.coach_rating != null && (() => {
                        const coach = response.coaches?.[0];
                        return (
                          <div key="coach" className="col-6 col-md-3">
                            <div className="p-3 rounded text-center" style={{ background: '#dbeafe' }}>
                              {coach && (
                                <div className="mb-2 d-flex justify-content-center">
                                  {coach.avatar_path ? (
                                    <img src={coach.avatar_path} alt="" className="rounded-circle" style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #3b82f6' }} />
                                  ) : (
                                    <div className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', fontSize: '0.75rem' }}>
                                      {getInitials(coach.nome)}
                                    </div>
                                  )}
                                </div>
                              )}
                              <div className="fw-bold fs-4 text-primary">{response.coach_rating}</div>
                              <small className="text-muted">{coach?.nome || 'Coach'}</small>
                            </div>
                          </div>
                        );
                      })()}
                      {!onlyProfessionalRole && response.progress_rating != null && (
                        <div className="col-6 col-md-3">
                          <div className="p-3 rounded text-center" style={{ background: '#f3e8ff' }}>
                            <div className="mb-2 d-flex justify-content-center">
                              <img src="/static/assets/immagini/logo_user.png" alt="Progresso" className="rounded-circle" style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #9333ea' }} />
                            </div>
                            <div className="fw-bold fs-4" style={{ color: '#9333ea' }}>{response.progress_rating}</div>
                            <small className="text-muted">Progresso</small>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {response.type === 'weekly' && (
                  <div className="mb-4">
                    <h6 className="text-muted mb-3"><i className="ri-heart-pulse-line me-2"></i>Benessere</h6>
                    <div className="row g-2">
                      {[
                        { key: 'digestion_rating', label: 'Digestione', icon: '🍽️' },
                        { key: 'energy_rating', label: 'Energia', icon: '⚡' },
                        { key: 'strength_rating', label: 'Forza', icon: '💪' },
                        { key: 'hunger_rating', label: 'Fame', icon: '🍴' },
                        { key: 'sleep_rating', label: 'Sonno', icon: '😴' },
                        { key: 'mood_rating', label: 'Umore', icon: '😊' },
                        { key: 'motivation_rating', label: 'Motivazione', icon: '🔥' },
                      ].map(item => (
                        <div key={item.key} className="col-6 col-md-4">
                          <div className="d-flex align-items-center p-2 rounded" style={{ background: '#f8fafc' }}>
                            <span className="me-2">{item.icon}</span>
                            <span className="small text-muted me-auto">{item.label}</span>
                            <span className={`fw-semibold ${response[item.key] === null || response[item.key] === undefined ? 'text-muted' : ''}`}>
                              {response[item.key] != null && response[item.key] !== undefined ? `${response[item.key]}/10` : '-'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {response.type === 'weekly' && (
                  <div className="mb-4">
                    <h6 className="text-muted mb-3"><i className="ri-feedback-line me-2"></i>Feedback Professionisti</h6>
                    <div className="row g-2">
                      {showFeedback('nutrizionista') && (
                        <div className="col-12">
                          <div className="p-3 rounded" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                            <small className="text-muted d-block mb-1">Feedback Nutrizionista</small>
                            <p className="mb-0 small">{response.nutritionist_feedback || <span className="text-muted fst-italic">Non compilato</span>}</p>
                          </div>
                        </div>
                      )}
                      {showFeedback('psicologo') && (
                        <div className="col-12">
                          <div className="p-3 rounded" style={{ background: '#fef3c7', border: '1px solid #fde68a' }}>
                            <small className="text-muted d-block mb-1">Feedback Psicologo</small>
                            <p className="mb-0 small">{response.psychologist_feedback || <span className="text-muted fst-italic">Non compilato</span>}</p>
                          </div>
                        </div>
                      )}
                      {showFeedback('coach') && (
                        <div className="col-12">
                          <div className="p-3 rounded" style={{ background: '#dbeafe', border: '1px solid #bfdbfe' }}>
                            <small className="text-muted d-block mb-1">Feedback Coach</small>
                            <p className="mb-0 small">{response.coach_feedback || <span className="text-muted fst-italic">Non compilato</span>}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {response.type === 'weekly' && (
                  <div className="mb-4">
                    <h6 className="text-muted mb-3"><i className="ri-calendar-check-line me-2"></i>Programmi</h6>
                    <div className="row g-2 align-items-start">
                      <div className="col-md-6 d-flex">
                        <div className="p-3 rounded flex-fill" style={{ background: '#f8fafc' }}>
                          <small className="text-muted d-block mb-1">Aderenza programma alimentare</small>
                          <p className="mb-0 small">{response.nutrition_program_adherence || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                      <div className="col-md-6 d-flex">
                        <div className="p-3 rounded flex-fill" style={{ background: '#f8fafc' }}>
                          <small className="text-muted d-block mb-1">Aderenza programma sportivo</small>
                          <p className="mb-0 small">{response.training_program_adherence || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                      <div className="col-12">
                        <div className="p-3 rounded" style={{ background: '#f8fafc' }}>
                          <small className="text-muted d-block mb-1">Esercizi modificati/aggiunti</small>
                          <p className="mb-0 small">{response.exercise_modifications || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                      <div className="col-md-4">
                        <div className="p-3 rounded text-center" style={{ background: '#f8fafc' }}>
                          <small className="text-muted d-block mb-1">Passi giornalieri</small>
                          <span className="fw-semibold">{response.daily_steps ?? <span className="text-muted">-</span>}</span>
                        </div>
                      </div>
                      <div className="col-md-4">
                        <div className="p-3 rounded text-center" style={{ background: '#f8fafc' }}>
                          <small className="text-muted d-block mb-1">Settimane completate</small>
                          <span className="fw-semibold">{response.completed_training_weeks ?? <span className="text-muted">-</span>}</span>
                        </div>
                      </div>
                      <div className="col-md-4">
                        <div className="p-3 rounded text-center" style={{ background: '#f8fafc' }}>
                          <small className="text-muted d-block mb-1">Giorni allenamento</small>
                          <span className="fw-semibold">{response.planned_training_days ?? <span className="text-muted">-</span>}</span>
                        </div>
                      </div>
                      <div className="col-12">
                        <div className="p-3 rounded" style={{ background: '#f8fafc' }}>
                          <small className="text-muted d-block mb-1">Tematiche live settimanali</small>
                          <p className="mb-0 small">{response.live_session_topics || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="mb-4" data-tour="check-reflections">
                  <h6 className="text-muted mb-3"><i className="ri-lightbulb-line me-2"></i>Riflessioni</h6>
                  <div className="mb-3">
                    <div className="p-3 rounded" style={{ background: '#f0fdf4' }}>
                      <small className="text-muted d-block mb-1"><i className="ri-check-line me-1 text-success"></i>Cosa ha funzionato</small>
                      <p className="mb-0">{response.what_worked || <span className="text-muted fst-italic">Non compilato</span>}</p>
                    </div>
                  </div>
                  <div className="mb-3">
                    <div className="p-3 rounded" style={{ background: '#fef2f2' }}>
                      <small className="text-muted d-block mb-1"><i className="ri-close-line me-1 text-danger"></i>Cosa non ha funzionato</small>
                      <p className="mb-0">{response.what_didnt_work || <span className="text-muted fst-italic">Non compilato</span>}</p>
                    </div>
                  </div>
                  <div className="mb-3">
                    <div className="p-3 rounded" style={{ background: '#fffbeb' }}>
                      <small className="text-muted d-block mb-1"><i className="ri-lightbulb-line me-1 text-warning"></i>Cosa ho imparato</small>
                      <p className="mb-0">{response.what_learned || <span className="text-muted fst-italic">Non compilato</span>}</p>
                    </div>
                  </div>
                  <div className="mb-3">
                    <div className="p-3 rounded" style={{ background: '#eff6ff' }}>
                      <small className="text-muted d-block mb-1"><i className="ri-focus-line me-1 text-primary"></i>Focus prossima settimana</small>
                      <p className="mb-0">{response.what_focus_next || <span className="text-muted fst-italic">Non compilato</span>}</p>
                    </div>
                  </div>
                  {response.type === 'weekly' && (
                    <div className="mb-3">
                      <div className="p-3 rounded" style={{ background: '#fef2f2', border: '1px solid #fecaca' }}>
                        <small className="text-muted d-block mb-1"><i className="ri-first-aid-kit-line me-1 text-danger"></i>Infortuni / Note importanti</small>
                        <p className="mb-0">{response.injuries_notes || <span className="text-muted fst-italic">Nessun infortunio segnalato</span>}</p>
                      </div>
                    </div>
                  )}
                </div>

                {response.type === 'weekly' && (
                  <div className="mb-4">
                    <h6 className="text-muted mb-3"><i className="ri-user-add-line me-2"></i>Referral</h6>
                    <div className="p-3 rounded" style={{ background: '#f8fafc' }}>
                      <p className="mb-0">{response.referral || <span className="text-muted fst-italic">Nessun referral indicato</span>}</p>
                    </div>
                  </div>
                )}

                <div className="mb-3">
                  <h6 className="text-muted mb-2"><i className="ri-chat-1-line me-2"></i>Commenti extra</h6>
                  <div className="p-3 rounded" style={{ background: '#f8fafc' }}>
                    <p className="mb-0">{response.extra_comments || <span className="text-muted fst-italic">Nessun commento aggiuntivo</span>}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
          <div className="modal-footer border-0">
            {response.cliente_id && (
              <Link to={`/clienti-dettaglio/${response.cliente_id}?tab=check_periodici`} className="btn btn-outline-primary" onClick={onClose}>
                <i className="ri-user-line me-1"></i>
                Vai al Cliente
              </Link>
            )}
            <button className="btn btn-secondary" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CheckResponseDetailModal;

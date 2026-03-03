import { useState, useCallback, useEffect, useRef } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Button } from 'react-bootstrap';
import { LiveKitRoom, VideoConference, RoomAudioRenderer } from '@dtelecom/components-react';
import '@dtelecom/components-styles';
import videoCallService from '../../services/videoCallService';
import clientiService from '../../services/clientiService';
import logoFoglia from '../../images/logo-foglia-white.png';
import './VideoCall.css';

// Patologie labels map
const PATOLOGIE_LABELS = {
  patologia_ibs: 'IBS', patologia_reflusso: 'Reflusso', patologia_gastrite: 'Gastrite',
  patologia_dca: 'DCA', patologia_insulino_resistenza: 'Insulino-resistenza',
  patologia_diabete: 'Diabete', patologia_dislipidemie: 'Dislipidemie',
  patologia_steatosi_epatica: 'Steatosi epatica', patologia_ipertensione: 'Ipertensione',
  patologia_pcos: 'PCOS', patologia_endometriosi: 'Endometriosi',
  patologia_obesita_sindrome: 'Obesità/Sindrome met.', patologia_osteoporosi: 'Osteoporosi',
  patologia_diverticolite: 'Diverticolite', patologia_crohn: 'Crohn',
  patologia_stitichezza: 'Stitichezza', patologia_tiroidee: 'Tiroidee',
};

const PATOLOGIE_PSICO_LABELS = {
  patologia_psico_dca: 'DCA', patologia_psico_obesita_psicoemotiva: 'Obesità psicoemotiva',
  patologia_psico_ansia_umore_cibo: 'Ansia/Umore/Cibo',
  patologia_psico_comportamenti_disfunzionali: 'Comportamenti disfunzionali',
  patologia_psico_immagine_corporea: 'Immagine corporea',
  patologia_psico_psicosomatiche: 'Psicosomatiche',
  patologia_psico_relazionali_altro: 'Relazionali/Altro',
};

const SIDEBAR_TABS = [
  { id: 'anagrafica', label: 'Anagrafica', icon: 'ri-user-line' },
  { id: 'programma', label: 'Programma', icon: 'ri-file-list-3-line' },
  { id: 'team', label: 'Team', icon: 'ri-team-line' },
  { id: 'nutrizione', label: 'Nutrizione', icon: 'ri-heart-pulse-line' },
  { id: 'coaching', label: 'Coaching', icon: 'ri-run-line' },
  { id: 'psicologia', label: 'Psicologia', icon: 'ri-mental-health-line' },
  { id: 'medico', label: 'Medico', icon: 'ri-stethoscope-line' },
];

function SumiField({ label, value }) {
  if (!value && value !== 0) return null;
  return (
    <div className="sumi-field">
      <span className="sumi-field-label">{label}</span>
      <span className="sumi-field-value">{value}</span>
    </div>
  );
}

function SumiSection({ title, icon, children }) {
  // Filter out null/false children
  const validChildren = Array.isArray(children)
    ? children.filter(Boolean)
    : children ? [children] : [];
  if (validChildren.length === 0) return null;
  return (
    <div className="sumi-section">
      <h6 className="sumi-section-title">
        <i className={`${icon} me-1`} />{title}
      </h6>
      {validChildren}
    </div>
  );
}

function formatDate(d) {
  if (!d) return null;
  return new Date(d).toLocaleDateString('it-IT');
}

function SumiSidebarContent({ data: c }) {
  const [tab, setTab] = useState('anagrafica');
  const tabsRef = useRef(null);
  const [canLeft, setCanLeft] = useState(false);
  const [canRight, setCanRight] = useState(false);

  const updateArrows = useCallback(() => {
    const el = tabsRef.current;
    if (!el) return;
    setCanLeft(el.scrollLeft > 0);
    setCanRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
  }, []);

  useEffect(() => {
    const el = tabsRef.current;
    if (!el) return;
    updateArrows();
    el.addEventListener('scroll', updateArrows, { passive: true });
    const ro = new ResizeObserver(updateArrows);
    ro.observe(el);
    return () => { el.removeEventListener('scroll', updateArrows); ro.disconnect(); };
  }, [updateArrows]);

  const scrollTabs = useCallback((dir) => {
    tabsRef.current?.scrollBy({ left: dir * 150, behavior: 'smooth' });
  }, []);

  const activePatologie = Object.entries(PATOLOGIE_LABELS)
    .filter(([k]) => c[k]).map(([, v]) => v);
  if (c.patologia_altro) activePatologie.push(c.patologia_altro);

  const activePsico = Object.entries(PATOLOGIE_PSICO_LABELS)
    .filter(([k]) => c[k]).map(([, v]) => v);
  if (c.patologia_psico_altro) activePsico.push(c.patologia_psico_altro);

  return (
    <>
      {/* Tab navigation with scroll arrows */}
      <div className="sumi-tabs-wrapper">
        {canLeft && (
          <button className="sumi-tabs-arrow sumi-tabs-arrow-left" onClick={() => scrollTabs(-1)}>
            <i className="ri-arrow-left-s-line" />
          </button>
        )}
        <div className="sumi-tabs" ref={tabsRef}>
          {SIDEBAR_TABS.map((t) => (
            <button
              key={t.id}
              className={`sumi-tab ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
              title={t.label}
            >
              <i className={t.icon} />
              <span className="sumi-tab-label">{t.label}</span>
            </button>
          ))}
        </div>
        {canRight && (
          <button className="sumi-tabs-arrow sumi-tabs-arrow-right" onClick={() => scrollTabs(1)}>
            <i className="ri-arrow-right-s-line" />
          </button>
        )}
      </div>

      {/* Tab content */}
      <div className="sumi-tab-content">

        {/* ── ANAGRAFICA ── */}
        {tab === 'anagrafica' && (
          <>
            <SumiSection title="Dati Personali" icon="ri-user-3-line">
              <SumiField label="Nome" value={c.nome_cognome} />
              <SumiField label="Data di nascita" value={formatDate(c.data_di_nascita)} />
              <SumiField label="Genere" value={c.genere} />
              <SumiField label="Professione" value={c.professione} />
              <SumiField label="Paese" value={c.paese} />
            </SumiSection>
            <SumiSection title="Contatti" icon="ri-phone-line">
              <SumiField label="Email" value={c.mail} />
              <SumiField label="Telefono" value={c.numero_telefono} />
              <SumiField label="Indirizzo" value={c.indirizzo} />
            </SumiSection>
            <SumiSection title="Stato" icon="ri-pulse-line">
              <SumiField label="Stato cliente" value={c.stato_cliente} />
              <SumiField label="Tipologia" value={c.tipologia_cliente} />
              <SumiField label="Origine" value={c.origine} />
              <SumiField label="Team" value={c.di_team} />
            </SumiSection>
            {c.alert && c.alert_storia && (
              <SumiSection title="Alert" icon="ri-alarm-warning-line">
                <p className="sumi-text sumi-alert-text">{c.alert_storia}</p>
              </SumiSection>
            )}
          </>
        )}

        {/* ── PROGRAMMA ── */}
        {tab === 'programma' && (
          <>
            <SumiSection title="Programma Attuale" icon="ri-file-list-3-line">
              <SumiField label="Programma" value={c.programma_attuale} />
              <SumiField label="Dettaglio" value={c.programma_attuale_dettaglio} />
              <SumiField label="Macrocategoria" value={c.macrocategoria} />
              <SumiField label="Storico" value={c.storico_programma} />
            </SumiSection>
            <SumiSection title="Abbonamento" icon="ri-calendar-line">
              <SumiField label="Inizio" value={formatDate(c.data_inizio_abbonamento)} />
              <SumiField label="Durata (giorni)" value={c.durata_programma_giorni} />
              <SumiField label="Rinnovo" value={formatDate(c.data_rinnovo)} />
              <SumiField label="In scadenza" value={c.in_scadenza} />
              <SumiField label="Pagamento" value={c.modalita_pagamento} />
              <SumiField label="Note rinnovo" value={c.note_rinnovo} />
            </SumiSection>
            <SumiSection title="Obiettivi" icon="ri-focus-3-line">
              <SumiField label="Obiettivo" value={c.obiettivo_semplicato} />
              {c.obiettivo_cliente && (
                <div className="sumi-note">
                  <span className="sumi-note-label">Obiettivo dettagliato</span>
                  <p>{c.obiettivo_cliente}</p>
                </div>
              )}
              {c.problema && (
                <div className="sumi-note">
                  <span className="sumi-note-label">Problema</span>
                  <p>{c.problema}</p>
                </div>
              )}
              {c.paure && (
                <div className="sumi-note">
                  <span className="sumi-note-label">Paure</span>
                  <p>{c.paure}</p>
                </div>
              )}
              {c.conseguenze && (
                <div className="sumi-note">
                  <span className="sumi-note-label">Conseguenze</span>
                  <p>{c.conseguenze}</p>
                </div>
              )}
            </SumiSection>
          </>
        )}

        {/* ── TEAM ── */}
        {tab === 'team' && (
          <>
            <SumiSection title="Team Assegnato" icon="ri-team-line">
              <SumiField label="Nutrizionista" value={c.nutrizionista} />
              <SumiField label="Coach" value={c.coach} />
              <SumiField label="Psicologa" value={c.psicologa} />
              <SumiField label="Consulente" value={c.consulente_alimentare} />
            </SumiSection>
            <SumiSection title="Date Call Iniziali" icon="ri-calendar-check-line">
              <SumiField label="Nutrizionista" value={formatDate(c.data_call_iniziale_nutrizionista)} />
              <SumiField label="Coach" value={formatDate(c.data_call_iniziale_coach)} />
              <SumiField label="Psicologia" value={formatDate(c.data_call_iniziale_psicologia)} />
            </SumiSection>
          </>
        )}

        {/* ── NUTRIZIONE ── */}
        {tab === 'nutrizione' && (
          <>
            <SumiSection title="Piano Nutrizione" icon="ri-heart-pulse-line">
              <SumiField label="Inizio" value={formatDate(c.data_inizio_nutrizione)} />
              <SumiField label="Durata (giorni)" value={c.durata_nutrizione_giorni} />
              <SumiField label="Scadenza" value={formatDate(c.data_scadenza_nutrizione)} />
              <SumiField label="Stato" value={c.stato_nutrizione} />
            </SumiSection>
            {activePatologie.length > 0 && (
              <SumiSection title="Patologie" icon="ri-heart-add-line">
                <div className="sumi-tags">
                  {activePatologie.map((p) => (
                    <span key={p} className="sumi-tag">{p}</span>
                  ))}
                </div>
              </SumiSection>
            )}
            {c.storia_cliente && (
              <SumiSection title="Storia Clinica" icon="ri-file-text-line">
                <p className="sumi-text">{c.storia_cliente}</p>
              </SumiSection>
            )}
          </>
        )}

        {/* ── COACHING ── */}
        {tab === 'coaching' && (
          <>
            <SumiSection title="Piano Coaching" icon="ri-run-line">
              <SumiField label="Inizio" value={formatDate(c.data_inizio_coach)} />
              <SumiField label="Durata (giorni)" value={c.durata_coach_giorni} />
              <SumiField label="Scadenza" value={formatDate(c.data_scadenza_coach)} />
            </SumiSection>
            {c.obiettivo_semplicato && (
              <SumiSection title="Obiettivo" icon="ri-focus-3-line">
                <p className="sumi-text">{c.obiettivo_semplicato}</p>
              </SumiSection>
            )}
          </>
        )}

        {/* ── PSICOLOGIA ── */}
        {tab === 'psicologia' && (
          <>
            <SumiSection title="Piano Psicologia" icon="ri-mental-health-line">
              <SumiField label="Inizio" value={formatDate(c.data_inizio_psicologia)} />
              <SumiField label="Durata (giorni)" value={c.durata_psicologia_giorni} />
              <SumiField label="Scadenza" value={formatDate(c.data_scadenza_psicologia)} />
              <SumiField label="Stato" value={c.stato_psicologia} />
            </SumiSection>
            {activePsico.length > 0 && (
              <SumiSection title="Patologie Psicologiche" icon="ri-brain-line">
                <div className="sumi-tags">
                  {activePsico.map((p) => (
                    <span key={p} className="sumi-tag">{p}</span>
                  ))}
                </div>
              </SumiSection>
            )}
          </>
        )}

        {/* ── MEDICO ── */}
        {tab === 'medico' && (
          <>
            <SumiSection title="Informazioni Mediche" icon="ri-stethoscope-line">
              {activePatologie.length > 0 && (
                <>
                  <span className="sumi-note-label">Patologie</span>
                  <div className="sumi-tags" style={{ marginBottom: 12 }}>
                    {activePatologie.map((p) => (
                      <span key={p} className="sumi-tag">{p}</span>
                    ))}
                  </div>
                </>
              )}
              {activePsico.length > 0 && (
                <>
                  <span className="sumi-note-label">Patologie Psicologiche</span>
                  <div className="sumi-tags" style={{ marginBottom: 12 }}>
                    {activePsico.map((p) => (
                      <span key={p} className="sumi-tag sumi-tag-psico">{p}</span>
                    ))}
                  </div>
                </>
              )}
            </SumiSection>
            {c.storia_cliente && (
              <SumiSection title="Storia Clinica" icon="ri-file-text-line">
                <p className="sumi-text">{c.storia_cliente}</p>
              </SumiSection>
            )}
            {c.alert && c.alert_storia && (
              <SumiSection title="Alert" icon="ri-alarm-warning-line">
                <p className="sumi-text sumi-alert-text">{c.alert_storia}</p>
              </SumiSection>
            )}
          </>
        )}

      </div>
    </>
  );
}

/**
 * Fullscreen video call room (outside DashboardLayout).
 * Receives token/wsUrl/session via router state from VideoCallPage.
 */
export default function VideoCallRoom() {
  const { sessionToken } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const { token, wsUrl, session, clienteName } = location.state || {};
  const [linkCopied, setLinkCopied] = useState(false);

  // SUMI sidebar
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [clienteData, setClienteData] = useState(null);
  const [loadingCliente, setLoadingCliente] = useState(false);
  const hasCliente = !!session?.cliente_id;

  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [uploadProgress, setUploadProgress] = useState(null); // null = not uploading, 0-100
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    if (sidebarOpen && hasCliente && !clienteData) {
      setLoadingCliente(true);
      clientiService.getCliente(session.cliente_id)
        .then((res) => setClienteData(res.data || res))
        .catch((err) => console.error('Error fetching client data:', err))
        .finally(() => setLoadingCliente(false));
    }
  }, [sidebarOpen, hasCliente, clienteData, session?.cliente_id]);

  // ── Recording helpers ──
  const startRecording = useCallback(() => {
    try {
      // Capture all audio+video from the page
      const videoEl = document.querySelector('.videocall-livekit video');
      const stream = videoEl?.captureStream?.() || videoEl?.mozCaptureStream?.();
      if (!stream) {
        console.warn('Cannot capture stream');
        return;
      }
      recordedChunksRef.current = [];
      const mr = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp8,opus' });
      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) recordedChunksRef.current.push(e.data);
      };
      mr.start(1000); // 1s chunks
      mediaRecorderRef.current = mr;
      setIsRecording(true);
      setRecordingSeconds(0);
      timerRef.current = setInterval(() => setRecordingSeconds((s) => s + 1), 1000);
    } catch (err) {
      console.error('Error starting recording:', err);
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    clearInterval(timerRef.current);
    setIsRecording(false);
  }, []);

  const uploadRecording = useCallback(async () => {
    if (!recordedChunksRef.current.length || !session?.id) return;
    const blob = new Blob(recordedChunksRef.current, { type: 'video/webm' });
    recordedChunksRef.current = [];
    setUploadProgress(0);
    try {
      await videoCallService.uploadRecording(session.id, blob, (pct) => setUploadProgress(pct));
    } catch (err) {
      console.error('Error uploading recording:', err);
    } finally {
      setUploadProgress(null);
    }
  }, [session?.id]);

  // Cleanup timer on unmount
  useEffect(() => () => clearInterval(timerRef.current), []);

  const formatTimer = (s) => {
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  };

  const handleDisconnect = useCallback(async () => {
    // Stop recording if active
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      clearInterval(timerRef.current);
      setIsRecording(false);
    }

    if (session?.id) {
      try {
        await videoCallService.endCall(session.id);
      } catch { /* ignore */ }
    }

    // Upload recording if we have chunks
    if (recordedChunksRef.current.length > 0 && session?.id) {
      const blob = new Blob(recordedChunksRef.current, { type: 'video/webm' });
      recordedChunksRef.current = [];
      setUploadProgress(0);
      try {
        await videoCallService.uploadRecording(session.id, blob, (pct) => setUploadProgress(pct));
      } catch (err) {
        console.error('Error uploading recording:', err);
      }
      setUploadProgress(null);
    }

    if (session?.cliente_id) {
      navigate(`/clienti-dettaglio/${session.cliente_id}`);
    } else {
      navigate('/welcome');
    }
  }, [session, navigate]);

  const copyPublicLink = useCallback(() => {
    const link = `${window.location.origin}/video-call/join/${sessionToken}`;
    navigator.clipboard.writeText(link).then(() => {
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 3000);
    });
  }, [sessionToken]);

  if (!token || !wsUrl) {
    return (
      <div className="videocall-room" data-lk-theme="default">
        <div className="videocall-no-session">
          <h3>Sessione non valida</h3>
          <p>Torna alla pagina precedente e avvia una nuova videochiamata.</p>
          <Button variant="outline-light" onClick={() => navigate('/video-call')}>
            Torna indietro
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="videocall-room" data-lk-theme="default">
      {/* Floating action bar */}
      <div className="videocall-topbar">
        <div className="topbar-left">
          <div className="topbar-brand">
            <img src={logoFoglia} alt="Corposostenibile" className="topbar-logo" />
            <span className="topbar-brand-text">CORPOSOSTENIBILE</span>
          </div>
          <span className="topbar-divider" />
          <span className="room-status">
            <span className="status-dot" />
            In videochiamata
          </span>
          {clienteName && clienteName !== 'Cliente' && (
            <span className="client-name">{clienteName}</span>
          )}
        </div>
        <div className="topbar-right">
          {/* Record button */}
          {!isRecording ? (
            <Button
              size="sm"
              onClick={startRecording}
              className="topbar-btn-record"
              title="Avvia registrazione"
            >
              <span className="rec-dot" />
              Registra
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={stopRecording}
              className="topbar-btn-record recording"
              title="Ferma registrazione"
            >
              <span className="rec-dot blink" />
              <span className="rec-timer">{formatTimer(recordingSeconds)}</span>
              Stop
            </Button>
          )}
          {hasCliente && (
            <Button
              size="sm"
              onClick={() => setSidebarOpen((v) => !v)}
              className={`topbar-btn-suitemind ${sidebarOpen ? 'active' : ''}`}
              title="Apri SUMI"
            >
              <img src="/suitemind.png" alt="SUMI" className="suitemind-btn-icon" />
            </Button>
          )}
          <Button
            size="sm"
            onClick={copyPublicLink}
            className="topbar-btn-copy"
          >
            <i className={`ri-${linkCopied ? 'check-line' : 'link'} me-1`} />
            {linkCopied ? 'Link copiato!' : 'Copia link cliente'}
          </Button>
          <Button variant="outline-danger" size="sm" onClick={handleDisconnect}>
            <i className="ri-phone-line me-1" />
            Termina
          </Button>
        </div>
      </div>

      <div className="videocall-main-area">
        <LiveKitRoom
          token={token}
          serverUrl={wsUrl}
          connect={true}
          audio={true}
          video={true}
          onDisconnected={handleDisconnect}
          className="videocall-livekit"
        >
          <VideoConference />
          <RoomAudioRenderer />
        </LiveKitRoom>

        {/* Upload progress overlay */}
        {uploadProgress !== null && (
          <div className="rec-upload-overlay">
            <div className="rec-upload-card">
              <div className="rec-upload-spinner" />
              <p>Salvataggio registrazione... {uploadProgress}%</p>
              <div className="rec-upload-bar">
                <div className="rec-upload-fill" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          </div>
        )}

        {/* SUMI Sidebar */}
        {sidebarOpen && hasCliente && (
          <div className="sumi-sidebar">
            <div className="sumi-sidebar-header">
              <div className="sumi-sidebar-title">
                <img src="/suitemind.png" alt="SUMI" className="sumi-sidebar-icon" />
                <span>SUMI</span>
              </div>
              <button className="sumi-sidebar-close" onClick={() => setSidebarOpen(false)}>
                <i className="ri-close-line" />
              </button>
            </div>

            {loadingCliente ? (
              <div className="sumi-loading">
                <div className="sumi-spinner" />
                <p>Caricamento dati...</p>
              </div>
            ) : clienteData ? (
              <SumiSidebarContent data={clienteData} />
            ) : (
              <div className="sumi-loading">
                <p>Dati non disponibili</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

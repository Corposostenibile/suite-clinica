/**
 * =============================================================================
 * SUPPORT WIDGET - BOTTONE DI ASSISTENZA FLOTTANTE
 * =============================================================================
 *
 * Questo componente crea un bottone flottante (FAB - Floating Action Button)
 * che apre un pannello di assistenza contestuale.
 *
 * Offre accesso rapido a:
 * - Tour Guidato
 * - Pagina Supporto
 * - Documentazione
 * - Contatto Supporto
 *
 * AUTORE: Pitch Partner Team
 * VERSIONE: 1.0.0
 * LICENZA: MIT
 *
 * =============================================================================
 *
 * DIPENDENZE RICHIESTE:
 * ---------------------
 * npm install react-icons react-router-dom
 *
 * Icone utilizzate da react-icons/fa:
 * - FaTimes (chiudi)
 * - FaRoute (tour)
 * - FaLifeRing (pagina supporto)
 * - FaBook (documentazione)
 * - FaHeadset (supporto)
 * - FaBoxOpen (icona pagina default)
 * - FaChevronRight (freccia)
 *
 * =============================================================================
 *
 * COME USARE QUESTO COMPONENTE:
 * -----------------------------
 *
 * 1. Copia questo file nella tua cartella components:
 *    /src/components/SupportWidget.js
 *
 * 2. Importa il componente nella tua pagina:
 *    import SupportWidget from './components/SupportWidget';
 *
 * 3. Aggiungi il componente alla tua pagina:
 *    <SupportWidget
 *      pageTitle="Titolo della Pagina"
 *      pageDescription="Descrizione di cosa fa questa pagina"
 *      onStartTour={() => setMostraTour(true)}
 *      onContactSupport={() => window.open('mailto:support@tuaapp.com')}
 *    />
 *
 * =============================================================================
 *
 * PROPS DEL COMPONENTE:
 * ---------------------
 *
 * | Prop             | Tipo         | Obbligatorio | Descrizione                           |
 * |------------------|--------------|--------------|---------------------------------------|
 * | pageTitle        | string       | NO           | Titolo della pagina corrente          |
 * | pageDescription  | string       | NO           | Descrizione della pagina              |
 * | pageIcon         | ReactElement | NO           | Icona della pagina (default: FaBoxOpen)|
 * | docsSection      | string       | NO           | Ancora per link documentazione        |
 * | onStartTour      | function     | NO           | Callback click "Tour Guidato"         |
 * | onOpenDocs       | function     | NO           | Callback click "Documentazione"       |
 * | onContactSupport | function     | NO           | Callback click "Supporto"             |
 * | logoSrc          | string       | NO           | URL logo personalizzato               |
 * | brandName        | string       | NO           | Nome brand (default: 'Pitch Partner') |
 * | accentColor      | string       | NO           | Colore accento (default: '#85FF00')   |
 *
 * =============================================================================
 *
 * ESEMPIO COMPLETO DI UTILIZZO:
 * -----------------------------
 *
 * import React, { useState } from 'react';
 * import SupportWidget from './components/SupportWidget';
 * import GuidedTour from './components/GuidedTour';
 * import { FaBoxOpen } from 'react-icons/fa';
 *
 * function MiaPagina() {
 *   const [mostraTour, setMostraTour] = useState(false);
 *
 *   const stepDelTour = [
 *     // ... definisci i tuoi step qui
 *   ];
 *
 *   return (
 *     <div>
 *       <h1>La Mia Pagina</h1>
 *
 *       {/* Il widget apparirà in basso a destra *\/}
 *       <SupportWidget
 *         pageTitle="Gestione Inventario"
 *         pageDescription="In questa pagina puoi gestire tutti gli elementi del tuo inventario. Filtra, cerca e modifica i tuoi asset."
 *         pageIcon={FaBoxOpen}
 *         docsSection="inventario"
 *         onStartTour={() => setMostraTour(true)}
 *         onOpenDocs={() => window.open('/docs#inventario', '_blank')}
 *         onContactSupport={() => window.open('mailto:supporto@miaapp.com')}
 *         brandName="La Mia App"
 *         accentColor="#3B82F6"
 *       />
 *
 *       {/* Integra con GuidedTour *\/}
 *       <GuidedTour
 *         steps={stepDelTour}
 *         isOpen={mostraTour}
 *         onClose={() => setMostraTour(false)}
 *         onComplete={() => setMostraTour(false)}
 *       />
 *     </div>
 *   );
 * }
 *
 * =============================================================================
 *
 * PERSONALIZZAZIONE COLORI:
 * -------------------------
 *
 * Il colore principale del widget può essere cambiato tramite la prop accentColor:
 *
 * - Verde (default): accentColor="#85FF00"
 * - Blu:             accentColor="#3B82F6"
 * - Viola:           accentColor="#8B5CF6"
 * - Rosa:            accentColor="#EC4899"
 *
 * Questo colore viene usato per:
 * - Bordo del bottone flottante
 * - Glow effect
 * - Hover sui pulsanti del menu
 *
 * =============================================================================
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaTimes, FaRoute, FaBook, FaHeadset, FaBoxOpen, FaChevronRight, FaLifeRing, FaVideo } from 'react-icons/fa';
import Swal from 'sweetalert2';
import useLoom from '../hooks/useLoom';
import loomService from '../services/loomService';

let pageWidgetInstances = 0;
const pageWidgetListeners = new Set();

const emitPageWidgetInstances = () => {
  pageWidgetListeners.forEach((listener) => listener(pageWidgetInstances));
};

function SupportWidget({
  pageTitle,
  pageDescription,
  pageIcon,
  docsSection,
  onStartTour,
  onOpenDocs,
  onContactSupport,
  logoSrc,
  brandName = 'Pitch Partner',
  accentColor = '#85FF00',
  variant = 'page',
  minimal = false,
}) {
  // =========================================================================
  // STATO DEL COMPONENTE
  // =========================================================================
  const [isOpen, setIsOpen] = useState(false);  // Controlla apertura pannello
  const [isSavingLoom, setIsSavingLoom] = useState(false);
  const [isLoomDecisionOpen, setIsLoomDecisionOpen] = useState(false);
  const [loomDraftVideo, setLoomDraftVideo] = useState(null);
  const [associatePatient, setAssociatePatient] = useState(false);
  const [patientQuery, setPatientQuery] = useState('');
  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const [patientOptions, setPatientOptions] = useState([]);
  const [isLoadingPatients, setIsLoadingPatients] = useState(false);
  const [hasPageScopedWidget, setHasPageScopedWidget] = useState(pageWidgetInstances > 0);
  const navigate = useNavigate();
  const {
    startRecording,
    isRecording,
    error: loomError,
    isReady: isLoomReady,
    isInitialized: isLoomInitialized,
    isSupported: isLoomSupported,
  } = useLoom();

  const showToast = (icon, title) => {
    Swal.fire({
      toast: true,
      position: 'top-end',
      icon,
      title,
      showConfirmButton: false,
      timer: 2600,
      timerProgressBar: true,
    });
  };

  useEffect(() => {
    const listener = (count) => {
      setHasPageScopedWidget(count > 0);
    };
    pageWidgetListeners.add(listener);
    listener(pageWidgetInstances);
    return () => {
      pageWidgetListeners.delete(listener);
    };
  }, []);

  useEffect(() => {
    if (variant !== 'page') return undefined;
    pageWidgetInstances += 1;
    emitPageWidgetInstances();
    return () => {
      pageWidgetInstances = Math.max(0, pageWidgetInstances - 1);
      emitPageWidgetInstances();
    };
  }, [variant]);

  useEffect(() => {
    console.info('[LoomWidget] state changed', {
      isLoomSupported,
      isLoomInitialized,
      isLoomReady,
      isRecording,
      isSavingLoom,
      isLoomDecisionOpen,
      loomError,
    });
  }, [isLoomSupported, isLoomInitialized, isLoomReady, isRecording, isSavingLoom, isLoomDecisionOpen, loomError]);

  useEffect(() => {
    if (!isLoomDecisionOpen || !associatePatient) {
      setPatientOptions([]);
      setIsLoadingPatients(false);
      return;
    }

    let isActive = true;
    const timerId = window.setTimeout(async () => {
      try {
        setIsLoadingPatients(true);
        const items = await loomService.searchPatients(patientQuery, 20);
        if (isActive) {
          setPatientOptions(items);
        }
      } catch (err) {
        if (isActive) {
          console.error('[LoomWidget] patients search error', err);
          setPatientOptions([]);
        }
      } finally {
        if (isActive) {
          setIsLoadingPatients(false);
        }
      }
    }, 300);

    return () => {
      isActive = false;
      window.clearTimeout(timerId);
    };
  }, [isLoomDecisionOpen, associatePatient, patientQuery]);


  // =========================================================================
  // HANDLERS
  // =========================================================================

  // Avvia il tour guidato
  const handleStartTour = () => {
    setIsOpen(false);
    if (onStartTour) {
      // Piccolo delay per permettere la chiusura del pannello
      setTimeout(() => onStartTour(), 300);
    }
  };

  // Apri documentazione
  const handleOpenDocs = () => {
    setIsOpen(false);
    if (onOpenDocs) {
      onOpenDocs();
    } else {
      // Comportamento default: naviga alla pagina docs
      const docsUrl = docsSection ? `/documentazione#${docsSection}` : '/documentazione';
      navigate(docsUrl);
    }
  };

  // Contatta supporto
  const handleContactSupport = () => {
    setIsOpen(false);
    if (onContactSupport) {
      onContactSupport();
    }
  };

  // Vai alla pagina supporto
  const handleGoToSupport = () => {
    setIsOpen(false);
    navigate('/supporto');
  };

  const resetLoomDecisionState = () => {
    setIsLoomDecisionOpen(false);
    setLoomDraftVideo(null);
    setAssociatePatient(false);
    setPatientQuery('');
    setSelectedPatientId(null);
    setPatientOptions([]);
    setIsLoadingPatients(false);
  };

  const handleSaveLoomDecision = async () => {
    if (!loomDraftVideo?.sharedUrl) {
      showToast('error', 'Link Loom non disponibile');
      return;
    }

    if (associatePatient && !selectedPatientId) {
      showToast('warning', 'Seleziona un paziente o disattiva l\'associazione');
      return;
    }

    try {
      setIsSavingLoom(true);
      console.info('[LoomWidget] saving recording to backend...', {
        associatePatient,
        selectedPatientId,
      });
      await loomService.saveSupportRecording({
        loomLink: loomDraftVideo.sharedUrl,
        title: loomDraftVideo.title || pageTitle || 'Registrazione supporto',
        clienteId: associatePatient ? selectedPatientId : null,
      });
      console.info('[LoomWidget] recording saved successfully');
      showToast('success', 'Loom salvato nella tua libreria');
      resetLoomDecisionState();
    } catch (err) {
      console.error('[LoomWidget] save error', err);
      const message = err?.response?.data?.message || err?.message || 'Errore salvataggio Loom';
      showToast('error', message);
    } finally {
      setIsSavingLoom(false);
    }
  };

  // Registra Loom dal widget e apre modale suite per conferma salvataggio
  const handleRecordLoom = () => {
    console.info('[LoomWidget] click Registra Loom', {
      isRecording,
      isSavingLoom,
      isLoomReady,
      isLoomInitialized,
      isLoomSupported,
      loomError,
      pageTitle,
    });
    if (!isLoomReady) {
      console.warn('[LoomWidget] Loom non pronto al click', {
        isLoomReady,
        isLoomInitialized,
        isLoomSupported,
        loomError,
        origin: window.location.origin,
      });
      showToast('error', loomError || 'Loom non pronto. Verifica APP_ID e ricarica la pagina.');
      return;
    }
    setIsOpen(false);
    startRecording(async (video) => {
      console.info('[LoomWidget] recording callback received', video);
      if (!video?.sharedUrl) {
        console.warn('[LoomWidget] missing sharedUrl in callback payload');
        showToast('error', 'Registrazione completata ma link Loom non disponibile');
        return;
      }
      setLoomDraftVideo(video);
      setIsLoomDecisionOpen(true);
    });
  };

  // Icona della pagina (usa quella passata o quella default)
  const PageIcon = pageIcon || FaBoxOpen;

  // =========================================================================
  // RENDER COMPONENTE
  // =========================================================================
  if (variant === 'global' && hasPageScopedWidget) {
    return null;
  }

  return (
    <>
      {/* =====================================================================
          BOTTONE FLOTTANTE (FAB)
          Posizionato in basso a destra, sempre visibile
          ===================================================================== */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #1A1A1A, #2D2D2D)',
          border: `3px solid ${accentColor}`,
          boxShadow: `0 4px 20px ${accentColor}4D, 0 8px 32px rgba(0,0,0,0.3)`,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          transition: 'all 0.3s ease',
          transform: isOpen ? 'scale(0.9) rotate(90deg)' : 'scale(1)',
          overflow: 'hidden'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = isOpen ? 'scale(0.95) rotate(90deg)' : 'scale(1.1)';
          e.currentTarget.style.boxShadow = `0 6px 28px ${accentColor}66, 0 12px 40px rgba(0,0,0,0.4)`;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = isOpen ? 'scale(0.9) rotate(90deg)' : 'scale(1)';
          e.currentTarget.style.boxShadow = `0 4px 20px ${accentColor}4D, 0 8px 32px rgba(0,0,0,0.3)`;
        }}
      >
        {isOpen ? (
          // Icona X quando aperto
          <FaTimes size={24} color={accentColor} />
        ) : logoSrc ? (
          // Logo personalizzato se fornito
          <img
            src={logoSrc}
            alt="Supporto"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover'
            }}
          />
        ) : (
          // Icona ? di default
          <span style={{ color: accentColor, fontSize: '28px', fontWeight: 'bold' }}>?</span>
        )}
      </button>

      {/* =====================================================================
          OVERLAY SFONDO
          Sfondo scuro con blur quando il pannello è aperto
          ===================================================================== */}
      {isOpen && (
        <div
          onClick={() => setIsOpen(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            backdropFilter: 'blur(4px)',
            zIndex: 9997,
            animation: 'fadeIn 0.2s ease'
          }}
        />
      )}

      {/* =====================================================================
          PANNELLO ASSISTENZA
          Pannello che si apre sopra il bottone flottante
          ===================================================================== */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '100px',
            right: '24px',
            width: '380px',
            maxWidth: 'calc(100vw - 48px)',
            background: 'white',
            borderRadius: '20px',
            boxShadow: '0 10px 60px rgba(0,0,0,0.2)',
            zIndex: 9998,
            overflow: 'hidden',
            animation: 'slideUp 0.3s ease'
          }}
        >
          {/* Header del Pannello */}
          <div
            style={{
              background: 'linear-gradient(135deg, #1A1A1A, #2D2D2D)',
              padding: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px'
            }}
          >
            {/* Logo/Icona Brand */}
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                background: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              {logoSrc ? (
                <img
                  src={logoSrc}
                  alt={brandName}
                  style={{ width: '32px', height: '32px' }}
                />
              ) : (
                <span style={{ fontSize: '20px', fontWeight: 'bold', color: '#1A1A1A' }}>?</span>
              )}
            </div>
            {/* Titolo */}
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: '16px', color: 'white' }}>
                {brandName}
              </div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>
                Centro Assistenza
              </div>
            </div>
            {/* Bottone Chiudi */}
            <button
              onClick={() => setIsOpen(false)}
              style={{
                background: 'rgba(255,255,255,0.1)',
                border: 'none',
                borderRadius: '10px',
                width: '36px',
                height: '36px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
            >
              <FaTimes size={16} color="white" />
            </button>
          </div>

          {!minimal && (
            <>
              {/* Informazioni Pagina Corrente */}
              <div style={{ padding: '24px' }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '14px',
                  marginBottom: '20px'
                }}>
                  {/* Icona Pagina */}
                  <div style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}>
                    <PageIcon size={20} color="#6366F1" />
                  </div>
                  {/* Titolo Pagina */}
                  <div>
                    <div style={{
                      fontSize: '13px',
                      color: '#6B7280',
                      marginBottom: '4px'
                    }}>
                      Ti trovi nella pagina
                    </div>
                    <div style={{
                      fontSize: '17px',
                      fontWeight: 700,
                      color: '#1A1A1A',
                      lineHeight: '1.3'
                    }}>
                      {pageTitle || 'Pagina Corrente'}
                    </div>
                  </div>
                </div>

                {/* Descrizione Pagina */}
                {pageDescription && (
                  <div style={{
                    background: '#F9FAFB',
                    borderRadius: '12px',
                    padding: '16px',
                    fontSize: '14px',
                    lineHeight: '1.6',
                    color: '#4B5563'
                  }}>
                    {pageDescription}
                  </div>
                )}
              </div>

              {/* Linea Separatore */}
              <div style={{
                height: '1px',
                background: '#E5E7EB',
                margin: '0 24px'
              }} />
            </>
          )}

          {/* Opzioni di Aiuto */}
          <div style={{ padding: '24px' }}>
            {!minimal && (
              <div style={{
                fontSize: '14px',
                fontWeight: 600,
                color: '#1A1A1A',
                marginBottom: '16px'
              }}>
                Hai bisogno?
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {/* Opzione: Registra Loom */}
              <OpzioneAiuto
                icon={<FaVideo size={18} color="#DC2626" />}
                iconBg="linear-gradient(135deg, #FEE2E2, #FECACA)"
                titolo={isRecording || isSavingLoom ? 'Registrazione in corso...' : isLoomDecisionOpen ? 'Conferma salvataggio...' : 'Registra Loom'}
                descrizione="Registra e salva un Loom nella tua libreria"
                onClick={handleRecordLoom}
                accentColor={accentColor}
                disabled={isRecording || isSavingLoom || isLoomDecisionOpen}
              />

              {!minimal && (
                <>
                  {/* Opzione 1: Tour Guidato */}
                  {onStartTour && (
                    <OpzioneAiuto
                      icon={<FaRoute size={18} color="#059669" />}
                      iconBg="linear-gradient(135deg, #ECFDF5, #D1FAE5)"
                      titolo="Tour Guidato"
                      descrizione="Scopri le funzionalità passo dopo passo"
                      onClick={handleStartTour}
                      accentColor={accentColor}
                    />
                  )}

                  {/* Opzione 2: Pagina Supporto */}
                  <OpzioneAiuto
                    icon={<FaLifeRing size={18} color="#8B5CF6" />}
                    iconBg="linear-gradient(135deg, #F3E8FF, #E9D5FF)"
                    titolo="Pagina Supporto"
                    descrizione="Accedi al centro assistenza completo"
                    onClick={handleGoToSupport}
                    accentColor={accentColor}
                  />

                  {/* Opzione 3: Documentazione */}
                  <OpzioneAiuto
                    icon={<FaBook size={18} color="#6366F1" />}
                    iconBg="linear-gradient(135deg, #EEF2FF, #E0E7FF)"
                    titolo="Documentazione Ufficiale"
                    descrizione="Guide e manuali dettagliati"
                    onClick={handleOpenDocs}
                    accentColor={accentColor}
                  />

                  {/* Opzione 4: Contatta Supporto */}
                  {onContactSupport && (
                    <OpzioneAiuto
                      icon={<FaHeadset size={18} color="#D97706" />}
                      iconBg="linear-gradient(135deg, #FEF3C7, #FDE68A)"
                      titolo="Hai Bisogno di Assistenza?"
                      descrizione="Contatta il nostro team di supporto"
                      onClick={handleContactSupport}
                      accentColor={accentColor}
                    />
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =====================================================================
          MODALE DECISIONE SALVATAGGIO LOOM
          ===================================================================== */}
      {isLoomDecisionOpen && (
        <>
          <div
            onClick={() => {
              if (!isSavingLoom) resetLoomDecisionState();
            }}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0, 0, 0, 0.5)',
              backdropFilter: 'blur(4px)',
              zIndex: 10000,
              animation: 'fadeIn 0.2s ease'
            }}
          />
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '560px',
              maxWidth: 'calc(100vw - 32px)',
              background: 'white',
              borderRadius: '16px',
              boxShadow: '0 18px 80px rgba(0,0,0,0.35)',
              zIndex: 10001,
              overflow: 'hidden'
            }}
          >
            <div style={{ padding: '20px 24px', borderBottom: '1px solid #E5E7EB', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#111827' }}>Salva registrazione Loom</div>
              <button
                onClick={() => {
                  if (!isSavingLoom) resetLoomDecisionState();
                }}
                disabled={isSavingLoom}
                style={{ border: 'none', background: 'transparent', cursor: isSavingLoom ? 'not-allowed' : 'pointer', color: '#6B7280' }}
              >
                <FaTimes size={18} />
              </button>
            </div>

            <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ background: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px', padding: '14px' }}>
                <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '6px' }}>Video registrato</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#111827', marginBottom: '8px' }}>
                  {loomDraftVideo?.title || 'Registrazione supporto'}
                </div>
                <a
                  href={loomDraftVideo?.sharedUrl || '#'}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: '13px', color: '#2563EB', wordBreak: 'break-all' }}
                >
                  {loomDraftVideo?.sharedUrl}
                </a>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '14px', color: '#111827' }}>
                <input
                  type="checkbox"
                  checked={associatePatient}
                  disabled={isSavingLoom}
                  onChange={(e) => {
                    const nextValue = e.target.checked;
                    setAssociatePatient(nextValue);
                    if (!nextValue) {
                      setPatientQuery('');
                      setSelectedPatientId(null);
                      setPatientOptions([]);
                    }
                  }}
                />
                Associa a un paziente
              </label>

              {associatePatient && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <input
                    type="text"
                    placeholder="Cerca paziente..."
                    value={patientQuery}
                    disabled={isSavingLoom}
                    onChange={(e) => setPatientQuery(e.target.value)}
                    style={{
                      width: '100%',
                      border: '1px solid #D1D5DB',
                      borderRadius: '10px',
                      padding: '10px 12px',
                      fontSize: '14px'
                    }}
                  />
                  <select
                    value={selectedPatientId || ''}
                    disabled={isSavingLoom || isLoadingPatients || patientOptions.length === 0}
                    onChange={(e) => setSelectedPatientId(e.target.value ? Number(e.target.value) : null)}
                    style={{
                      width: '100%',
                      border: '1px solid #D1D5DB',
                      borderRadius: '10px',
                      padding: '10px 12px',
                      fontSize: '14px',
                      background: 'white'
                    }}
                  >
                    <option value="">
                      {isLoadingPatients ? 'Ricerca in corso...' : patientOptions.length ? 'Seleziona un paziente' : 'Nessun paziente trovato'}
                    </option>
                    {patientOptions.map((patient) => (
                      <option key={patient.cliente_id} value={patient.cliente_id}>
                        {patient.nome_cognome}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            <div style={{ padding: '16px 24px', borderTop: '1px solid #E5E7EB', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={resetLoomDecisionState}
                disabled={isSavingLoom}
                style={{
                  border: '1px solid #D1D5DB',
                  background: 'white',
                  color: '#111827',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  cursor: isSavingLoom ? 'not-allowed' : 'pointer'
                }}
              >
                Annulla
              </button>
              <button
                onClick={handleSaveLoomDecision}
                disabled={isSavingLoom || !loomDraftVideo?.sharedUrl || (associatePatient && !selectedPatientId)}
                style={{
                  border: 'none',
                  background: '#2563EB',
                  color: 'white',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  fontWeight: 600,
                  cursor: isSavingLoom ? 'not-allowed' : 'pointer',
                  opacity: (isSavingLoom || !loomDraftVideo?.sharedUrl || (associatePatient && !selectedPatientId)) ? 0.6 : 1
                }}
              >
                {isSavingLoom ? 'Salvataggio...' : 'Salva'}
              </button>
            </div>
          </div>
        </>
      )}

      {/* =====================================================================
          ANIMAZIONI CSS
          Definisce le animazioni di apertura
          ===================================================================== */}
      <style>{`
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
}

/**
 * =============================================================================
 * COMPONENTE INTERNO: OpzioneAiuto
 * =============================================================================
 *
 * Renderizza una singola opzione nel menu di aiuto.
 * Usato internamente da SupportWidget.
 */
function OpzioneAiuto({ icon, iconBg, titolo, descrizione, onClick, accentColor, disabled = false }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        padding: '14px 16px',
        background: 'white',
        border: '2px solid #E5E7EB',
        borderRadius: '12px',
        cursor: 'pointer',
        transition: 'all 0.2s',
        textAlign: 'left',
        width: '100%',
        opacity: disabled ? 0.6 : 1
      }}
      onMouseEnter={(e) => {
        if (disabled) return;
        e.currentTarget.style.borderColor = accentColor;
        e.currentTarget.style.background = `${accentColor}0D`; // 5% opacità
      }}
      onMouseLeave={(e) => {
        if (disabled) return;
        e.currentTarget.style.borderColor = '#E5E7EB';
        e.currentTarget.style.background = 'white';
      }}
    >
      {/* Icona */}
      <div style={{
        width: '40px',
        height: '40px',
        borderRadius: '10px',
        background: iconBg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }}>
        {icon}
      </div>
      {/* Testo */}
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, fontSize: '14px', color: '#1A1A1A' }}>
          {titolo}
        </div>
        <div style={{ fontSize: '12px', color: '#6B7280', marginTop: '2px' }}>
          {descrizione}
        </div>
      </div>
      {/* Freccia */}
      <FaChevronRight size={14} color="#9CA3AF" />
    </button>
  );
}

export default SupportWidget;

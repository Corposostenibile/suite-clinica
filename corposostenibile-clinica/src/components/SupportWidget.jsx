/**
 * =============================================================================
 * SUPPORT WIDGET - BOTTONE DI ASSISTENZA FLOTTANTE
 * =============================================================================
 */

import { useContext, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import {
  FaBook,
  FaBoxOpen,
  FaChevronRight,
  FaHeadset,
  FaLifeRing,
  FaRoute,
  FaTicketAlt,
  FaTimes,
  FaVideo,
} from 'react-icons/fa';
import Swal from 'sweetalert2';
import AuthContext from '../context/AuthContext';
import useLoom from '../hooks/useLoom';
import loomService from '../services/loomService';
import { getTourContext, normalizeTourSpecialtyKey } from '../utils/tourScope';

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
  docsAudience,
  docsSpecialty,
  tourOptions,
  onStartTour,
  onOpenDocs,
  onContactSupport,
  logoSrc,
  brandName = 'Pitch Partner',
  accentColor = '#85FF00',
  variant = 'page',
  minimal = false,
}) {
  const [isOpen, setIsOpen] = useState(false);
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
  const auth = useContext(AuthContext);
  const currentUser = auth?.user || null;
  const {
    isAdminOrCco,
    audience: inferredDocsAudience,
    specialtyKey: inferredSpecialtyKey,
  } = getTourContext(currentUser);
  const guideAudience = docsAudience || inferredDocsAudience;
  const guideSpecialty = normalizeTourSpecialtyKey(docsSpecialty)
    || (isAdminOrCco ? 'all' : inferredSpecialtyKey || 'all');
  const resolvedTourOptions = Array.isArray(tourOptions) && tourOptions.length > 0
    ? tourOptions
    : isAdminOrCco
      ? [
          {
            title: 'Tour Team Leader',
            description: 'Apri il percorso di coordinamento e supervisione del team',
            audience: 'team_leader',
            iconColor: '#059669',
            iconBg: 'linear-gradient(135deg, #ECFDF5, #D1FAE5)',
          },
          {
            title: 'Tour Professionista',
            description: 'Apri il percorso operativo pensato per il professionista',
            audience: 'professionista',
            iconColor: '#0F766E',
            iconBg: 'linear-gradient(135deg, #CCFBF1, #99F6E4)',
          },
        ]
      : [
          {
            title: guideAudience === 'team_leader' ? 'Tour Team Leader' : 'Tour Guidato',
            description: guideAudience === 'team_leader'
              ? 'Scopri il percorso di coordinamento del team passo dopo passo'
              : 'Scopri le funzionalità passo dopo passo',
            audience: guideAudience,
            iconColor: '#059669',
            iconBg: 'linear-gradient(135deg, #ECFDF5, #D1FAE5)',
          },
        ];

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

  const handleStartTour = (audience = guideAudience, tourType = 'general') => {
    setIsOpen(false);
    if (onStartTour) {
      setTimeout(() => onStartTour(audience, tourType), 300);
    }
  };

  const handleOpenDocs = () => {
    setIsOpen(false);
    if (onOpenDocs) {
      onOpenDocs();
      return;
    }

    const params = new URLSearchParams();
    params.set('audience', guideAudience);
    params.set('specialty', guideSpecialty || 'all');
    const docsUrl = docsSection
      ? `/documentazione?${params.toString()}#${docsSection}`
      : `/documentazione?${params.toString()}`;
    navigate(docsUrl);
  };

  const handleContactSupport = () => {
    setIsOpen(false);
    if (onContactSupport) {
      onContactSupport();
    }
  };

  const handleGoToSupport = () => {
    setIsOpen(false);
    navigate('/supporto');
  };

  const handleOpenTickets = () => {
    setIsOpen(false);
    navigate('/supporto/ticket');
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
      await loomService.saveSupportRecording({
        loomLink: loomDraftVideo.sharedUrl,
        title: loomDraftVideo.title || pageTitle || 'Registrazione supporto',
        clienteId: associatePatient ? selectedPatientId : null,
      });
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

  const handleRecordLoom = () => {
    if (!isLoomReady) {
      showToast('error', loomError || 'Loom non pronto. Verifica APP_ID e ricarica la pagina.');
      return;
    }

    setIsOpen(false);
    startRecording((video) => {
      if (!video?.sharedUrl) {
        showToast('error', 'Registrazione completata ma link Loom non disponibile');
        return;
      }
      setLoomDraftVideo(video);
      setIsLoomDecisionOpen(true);
    });
  };

  const PageIcon = pageIcon || FaBoxOpen;

  if (variant === 'global' && hasPageScopedWidget) {
    return null;
  }

  return createPortal(
    <>
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
          zIndex: 2147483004,
          transition: 'all 0.3s ease',
          transform: isOpen ? 'scale(0.9) rotate(90deg)' : 'scale(1)',
          overflow: 'hidden',
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
          <FaTimes size={24} color={accentColor} />
        ) : logoSrc ? (
          <img
            src={logoSrc}
            alt="Supporto"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />
        ) : (
          <span style={{ color: accentColor, fontSize: '28px', fontWeight: 'bold' }}>?</span>
        )}
      </button>

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
            zIndex: 2147483002,
            animation: 'fadeIn 0.2s ease',
          }}
        />
      )}

      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '100px',
            right: '24px',
            width: '380px',
            maxWidth: 'calc(100vw - 48px)',
            maxHeight: 'calc(100vh - 140px)',
            background: 'white',
            borderRadius: '20px',
            boxShadow: '0 10px 60px rgba(0,0,0,0.2)',
            zIndex: 2147483003,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            animation: 'slideUp 0.3s ease',
          }}
        >
          <div
            style={{
              background: 'linear-gradient(135deg, #1A1A1A, #2D2D2D)',
              padding: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              flexShrink: 0,
            }}
          >
            <div
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                background: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
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
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: '16px', color: 'white' }}>
                {brandName}
              </div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>
                Centro Assistenza
              </div>
            </div>
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
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.1)';
              }}
            >
              <FaTimes size={16} color="white" />
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
          {pageTitle && (
            <>
              <div style={{ padding: '24px' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '14px',
                    marginBottom: '20px',
                  }}
                >
                  <div
                    style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '12px',
                      background: 'linear-gradient(135deg, #EEF2FF, #E0E7FF)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <PageIcon size={20} color="#6366F1" />
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: '13px',
                        color: '#6B7280',
                        marginBottom: '4px',
                      }}
                    >
                      Ti trovi nella pagina
                    </div>
                    <div
                      style={{
                        fontSize: '17px',
                        fontWeight: 700,
                        color: '#1A1A1A',
                        lineHeight: '1.3',
                      }}
                    >
                      {pageTitle}
                    </div>
                  </div>
                </div>

                {pageDescription && (
                  <div
                    style={{
                      background: '#F9FAFB',
                      borderRadius: '12px',
                      padding: '16px',
                      fontSize: '14px',
                      lineHeight: '1.6',
                      color: '#4B5563',
                    }}
                  >
                    {pageDescription}
                  </div>
                )}
              </div>

              <div
                style={{
                  height: '1px',
                  background: '#E5E7EB',
                  margin: '0 24px',
                }}
              />
            </>
          )}

          <div style={{ padding: '24px' }}>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <OpzioneAiuto
                icon={<FaTicketAlt size={18} color="#DC2626" />}
                iconBg="linear-gradient(135deg, #FEE2E2, #FECACA)"
                titolo="Apri Ticket IT"
                descrizione="Segnala un bug, un rallentamento o richiedi supporto tecnico"
                onClick={handleOpenTickets}
                accentColor={accentColor}
              />

              <OpzioneAiuto
                icon={<FaBook size={18} color="#6366F1" />}
                iconBg="linear-gradient(135deg, #EEF2FF, #E0E7FF)"
                titolo="Documentazione"
                descrizione="Guide e manuali dettagliati"
                onClick={handleOpenDocs}
                accentColor={accentColor}
              />

              {/* Loom recording - nascosto temporaneamente
              <OpzioneAiuto
                icon={<FaVideo size={18} color="#DC2626" />}
                iconBg="linear-gradient(135deg, #FEE2E2, #FECACA)"
                titolo={isRecording || isSavingLoom ? 'Registrazione in corso...' : isLoomDecisionOpen ? 'Conferma salvataggio...' : 'Registra Loom'}
                descrizione="Registra e salva un Loom nella tua libreria"
                onClick={handleRecordLoom}
                accentColor={accentColor}
                disabled={isRecording || isSavingLoom || isLoomDecisionOpen}
              />
              */}

              {onStartTour && resolvedTourOptions.map((option, index) => (
                <OpzioneAiuto
                  key={`${option.title}-${option.audience || guideAudience}-${option.tourType || 'general'}-${index}`}
                  icon={<FaRoute size={18} color={option.iconColor || '#059669'} />}
                  iconBg={option.iconBg || 'linear-gradient(135deg, #ECFDF5, #D1FAE5)'}
                  titolo={option.title}
                  descrizione={option.description}
                  onClick={() => handleStartTour(option.audience || guideAudience, option.tourType || 'general')}
                  accentColor={accentColor}
                />
              ))}

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
            </div>
          </div>
          </div>
        </div>
      )}

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
              zIndex: 2147483005,
              animation: 'fadeIn 0.2s ease',
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
              zIndex: 2147483006,
              overflow: 'hidden',
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
                      fontSize: '14px',
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
                      background: 'white',
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
                  cursor: isSavingLoom ? 'not-allowed' : 'pointer',
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
                  opacity: (isSavingLoom || !loomDraftVideo?.sharedUrl || (associatePatient && !selectedPatientId)) ? 0.6 : 1,
                }}
              >
                {isSavingLoom ? 'Salvataggio...' : 'Salva'}
              </button>
            </div>
          </div>
        </>
      )}

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
    </>,
    document.body
  );
}

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
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'all 0.2s',
        textAlign: 'left',
        width: '100%',
        opacity: disabled ? 0.6 : 1,
      }}
      onMouseEnter={(e) => {
        if (disabled) return;
        e.currentTarget.style.borderColor = accentColor;
        e.currentTarget.style.background = `${accentColor}0D`;
      }}
      onMouseLeave={(e) => {
        if (disabled) return;
        e.currentTarget.style.borderColor = '#E5E7EB';
        e.currentTarget.style.background = 'white';
      }}
    >
      <div
        style={{
          width: '40px',
          height: '40px',
          borderRadius: '10px',
          background: iconBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, fontSize: '14px', color: '#1A1A1A' }}>
          {titolo}
        </div>
        <div style={{ fontSize: '12px', color: '#6B7280', marginTop: '2px' }}>
          {descrizione}
        </div>
      </div>
      <FaChevronRight size={14} color="#9CA3AF" />
    </button>
  );
}

export default SupportWidget;

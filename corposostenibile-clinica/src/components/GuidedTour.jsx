/**
 * =============================================================================
 * GUIDED TOUR - COMPONENTE REACT PER TOUR GUIDATI INTERATTIVI
 * =============================================================================
 *
 * Questo componente crea tour guidati step-by-step con effetto spotlight.
 * Evidenzia elementi della pagina e mostra tooltip informativi.
 *
 * AUTORE: Pitch Partner Team
 * VERSIONE: 1.0.0
 * LICENZA: MIT
 *
 * =============================================================================
 *
 * DIPENDENZE RICHIESTE:
 * ---------------------
 * npm install react-icons
 *
 * Icone utilizzate da react-icons/fa:
 * - FaTimes (chiudi)
 * - FaChevronLeft (indietro)
 * - FaChevronRight (avanti)
 * - FaCheck (completa)
 * - FaLightbulb (suggerimento)
 *
 * =============================================================================
 *
 * COME USARE QUESTO COMPONENTE:
 * -----------------------------
 *
 * 1. Copia questo file nella tua cartella components:
 *    /src/components/GuidedTour.js
 *
 * 2. Importa il componente nella tua pagina:
 *    import GuidedTour from './components/GuidedTour';
 *
 * 3. Definisci gli step del tour (vedi sezione STRUTTURA STEP sotto)
 *
 * 4. Aggiungi il componente alla tua pagina:
 *    <GuidedTour
 *      steps={tuoArrayDiStep}
 *      isOpen={statoDiVisibilita}
 *      onClose={() => setStatoDiVisibilita(false)}
 *      onComplete={() => console.log('Tour completato!')}
 *    />
 *
 * 5. Aggiungi l'attributo data-tour agli elementi che vuoi evidenziare:
 *    <button data-tour="crea-elemento">Crea Nuovo</button>
 *
 * =============================================================================
 *
 * PROPS DEL COMPONENTE:
 * ---------------------
 *
 * | Prop         | Tipo     | Obbligatorio | Descrizione                        |
 * |--------------|----------|--------------|-------------------------------------|
 * | steps        | Array    | SI           | Array di oggetti step (vedi sotto) |
 * | isOpen       | boolean  | SI           | Controlla se il tour è visibile    |
 * | onClose      | function | SI           | Chiamata quando si chiude il tour  |
 * | onComplete   | function | NO           | Chiamata al completamento del tour |
 * | onStepChange | function | NO           | Chiamata ad ogni cambio step       |
 *
 * =============================================================================
 *
 * STRUTTURA DI OGNI STEP:
 * -----------------------
 *
 * {
 *   // CAMPI OBBLIGATORI:
 *   target: '[data-tour="nome-elemento"]',  // Selettore CSS dell'elemento da evidenziare
 *   title: 'Titolo dello Step',              // Titolo mostrato nel tooltip
 *   content: 'Descrizione dettagliata...',   // Testo descrittivo
 *
 *   // CAMPI OPZIONALI:
 *   placement: 'bottom',                     // Posizione tooltip: 'top', 'bottom', 'left', 'right'
 *   icon: <FaIcona size={18} color="white" />,  // Icona personalizzata
 *   iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)',  // Sfondo icona
 *   tip: 'Suggerimento extra mostrato in box verde'       // Tip aggiuntivo
 * }
 *
 * =============================================================================
 *
 * ESEMPIO COMPLETO DI UTILIZZO:
 * -----------------------------
 *
 * import React, { useState } from 'react';
 * import GuidedTour from './components/GuidedTour';
 * import { FaPlus, FaFilter } from 'react-icons/fa';
 *
 * function MiaPagina() {
 *   const [mostraTour, setMostraTour] = useState(false);
 *
 *   const stepDelTour = [
 *     {
 *       target: '[data-tour="bottone-crea"]',
 *       title: 'Crea Nuovo Elemento',
 *       content: 'Clicca qui per creare un nuovo elemento nel sistema.',
 *       placement: 'bottom',
 *       icon: <FaPlus size={18} color="white" />,
 *       iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
 *       tip: 'Puoi anche usare la scorciatoia Ctrl+N'
 *     },
 *     {
 *       target: '[data-tour="filtri"]',
 *       title: 'Filtra i Risultati',
 *       content: 'Usa questi filtri per trovare velocemente quello che cerchi.',
 *       placement: 'bottom',
 *       icon: <FaFilter size={18} color="white" />
 *     }
 *   ];
 *
 *   return (
 *     <div>
 *       <button onClick={() => setMostraTour(true)}>
 *         Avvia Tour Guidato
 *       </button>
 *
 *       <button data-tour="bottone-crea">Crea Nuovo</button>
 *       <div data-tour="filtri">...filtri...</div>
 *
 *       <GuidedTour
 *         steps={stepDelTour}
 *         isOpen={mostraTour}
 *         onClose={() => setMostraTour(false)}
 *         onComplete={() => {
 *           setMostraTour(false);
 *           localStorage.setItem('tourCompletato', 'true');
 *         }}
 *         onStepChange={(indice, step) => {
 *           console.log(`Passato allo step ${indice + 1}: ${step.title}`);
 *         }}
 *       />
 *     </div>
 *   );
 * }
 *
 * =============================================================================
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { FaTimes, FaChevronLeft, FaChevronRight, FaCheck, FaLightbulb } from 'react-icons/fa';

function GuidedTour({ steps, isOpen, onClose, onComplete, onStepChange }) {
  // =========================================================================
  // STATO DEL COMPONENTE
  // =========================================================================
  const [currentStep, setCurrentStep] = useState(0);           // Indice step corrente
  const [targetElement, setTargetElement] = useState(null);    // Elemento DOM evidenziato
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 }); // Posizione tooltip
  const [highlightStyle, setHighlightStyle] = useState({});    // Stile spotlight
  const [isAnimating, setIsAnimating] = useState(false);       // Stato animazione
  const tooltipRef = useRef(null);                             // Riferimento al tooltip

  // =========================================================================
  // CALCOLO POSIZIONE TOOLTIP E SPOTLIGHT
  // =========================================================================
  // Questa funzione calcola dove posizionare il tooltip e lo spotlight
  // in base all'elemento target e allo spazio disponibile nel viewport
  const calculatePosition = useCallback(() => {
    if (!steps[currentStep]) return;

    // Trova l'elemento nel DOM usando il selettore CSS
    const selector = steps[currentStep].target;
    const element = document.querySelector(selector);

    if (element) {
      setTargetElement(element);
      const rect = element.getBoundingClientRect();
      const padding = 12; // Padding attorno all'elemento evidenziato

      // Calcola posizione e dimensioni dello spotlight
      setHighlightStyle({
        top: rect.top - padding,
        left: rect.left - padding,
        width: rect.width + padding * 2,
        height: rect.height + padding * 2,
      });

      // Dimensioni del tooltip
      const tooltipWidth = 400;
      const tooltipEl = tooltipRef.current;
      const tooltipHeight = tooltipEl ? tooltipEl.offsetHeight : 350;

      // Dimensioni viewport
      const viewportHeight = window.innerHeight;
      const viewportWidth = window.innerWidth;
      const margin = 20;

      // Calcola spazio disponibile in ogni direzione
      const spaceAbove = rect.top - margin;
      const spaceBelow = viewportHeight - rect.bottom - margin;
      const spaceLeft = rect.left - margin;
      const spaceRight = viewportWidth - rect.right - margin;

      // Determina posizionamento migliore
      let placement = steps[currentStep].placement || 'bottom';
      let top, left;

      // Verifica se il posizionamento preferito è possibile
      const canFitBottom = spaceBelow >= tooltipHeight;
      const canFitTop = spaceAbove >= tooltipHeight;
      const canFitRight = spaceRight >= tooltipWidth;
      const canFitLeft = spaceLeft >= tooltipWidth;

      // Auto-aggiusta il posizionamento se necessario
      if (placement === 'bottom' && !canFitBottom && canFitTop) {
        placement = 'top';
      } else if (placement === 'top' && !canFitTop && canFitBottom) {
        placement = 'bottom';
      } else if (placement === 'left' && !canFitLeft && canFitRight) {
        placement = 'right';
      } else if (placement === 'right' && !canFitRight && canFitLeft) {
        placement = 'left';
      }

      // Calcola posizione in base al placement
      switch (placement) {
        case 'top':
          top = rect.top - tooltipHeight - margin;
          left = rect.left + rect.width / 2 - tooltipWidth / 2;
          break;
        case 'bottom':
          top = rect.bottom + margin;
          left = rect.left + rect.width / 2 - tooltipWidth / 2;
          break;
        case 'left':
          top = rect.top + rect.height / 2 - tooltipHeight / 2;
          left = rect.left - tooltipWidth - margin;
          break;
        case 'right':
          top = rect.top + rect.height / 2 - tooltipHeight / 2;
          left = rect.right + margin;
          break;
        case 'bottom-left':
          top = rect.bottom + margin;
          left = rect.left;
          break;
        case 'bottom-right':
          top = rect.bottom + margin;
          left = rect.right - tooltipWidth;
          break;
        default:
          top = rect.bottom + margin;
          left = rect.left + rect.width / 2 - tooltipWidth / 2;
      }

      // Mantieni il tooltip dentro il viewport
      left = Math.max(margin, Math.min(left, viewportWidth - tooltipWidth - margin));
      top = Math.max(margin, Math.min(top, viewportHeight - tooltipHeight - margin));

      setTooltipPosition({ top, left });

      // Scrolla l'elemento in vista se necessario
      const isInViewport = rect.top >= 0 && rect.bottom <= viewportHeight;
      if (!isInViewport) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [currentStep, steps]);

  // =========================================================================
  // EFFETTI
  // =========================================================================

  // Ricalcola posizione quando si apre il tour o cambia step
  useEffect(() => {
    if (isOpen && steps.length > 0) {
      setIsAnimating(true);

      // Notifica il cambio step iniziale
      if (currentStep === 0) {
        onStepChange?.(0, steps[0]);
      }

      // Prima calcolazione
      const timer1 = setTimeout(() => {
        calculatePosition();
      }, 100);

      // Seconda calcolazione dopo render del tooltip
      const timer2 = setTimeout(() => {
        calculatePosition();
        setIsAnimating(false);
      }, 350);

      return () => {
        clearTimeout(timer1);
        clearTimeout(timer2);
      };
    }
  }, [isOpen, currentStep, calculatePosition, steps.length, onStepChange]);

  // Ascolta resize e scroll per ricalcolare posizione
  useEffect(() => {
    if (isOpen) {
      window.addEventListener('resize', calculatePosition);
      window.addEventListener('scroll', calculatePosition);
      return () => {
        window.removeEventListener('resize', calculatePosition);
        window.removeEventListener('scroll', calculatePosition);
      };
    }
  }, [isOpen, calculatePosition]);

  // =========================================================================
  // HANDLERS NAVIGAZIONE
  // =========================================================================

  // Vai allo step successivo
  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      onStepChange?.(nextStep, steps[nextStep]);
    } else {
      handleComplete();
    }
  };

  // Vai allo step precedente
  const handlePrev = () => {
    if (currentStep > 0) {
      const prevStep = currentStep - 1;
      setCurrentStep(prevStep);
      onStepChange?.(prevStep, steps[prevStep]);
    }
  };

  // Completa il tour
  const handleComplete = () => {
    setCurrentStep(0);
    onComplete?.();
    onClose();
  };

  // Salta/chiudi il tour
  const handleSkip = () => {
    setCurrentStep(0);
    onClose();
  };

  // =========================================================================
  // RENDER CONDIZIONALE
  // =========================================================================

  // Non renderizzare se il tour è chiuso o non ci sono step
  if (!isOpen || steps.length === 0) return null;

  // Dati step corrente
  const step = steps[currentStep];
  const progress = ((currentStep + 1) / steps.length) * 100;
  const isLastStep = currentStep === steps.length - 1;

  // =========================================================================
  // RENDER COMPONENTE
  // =========================================================================
  return (
    <>
      {/* =====================================================================
          OVERLAY SPOTLIGHT
          Crea l'effetto di oscuramento con un buco trasparente sull'elemento
          ===================================================================== */}
      <div
        style={{
          position: 'fixed',
          ...highlightStyle,
          background: 'transparent',
          boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.75)', // Oscura tutto tranne questo rettangolo
          borderRadius: '12px',
          zIndex: 10000,
          transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          pointerEvents: 'none',
        }}
      />

      {/* =====================================================================
          BORDO VERDE EVIDENZIATORE
          Crea il bordo verde brillante attorno all'elemento
          ===================================================================== */}
      <div
        style={{
          position: 'fixed',
          ...highlightStyle,
          border: '3px solid #85FF00',
          borderRadius: '12px',
          zIndex: 10001,
          transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          pointerEvents: 'none',
          boxShadow: '0 0 20px rgba(133, 255, 0, 0.4), inset 0 0 20px rgba(133, 255, 0, 0.1)',
        }}
      />

      {/* =====================================================================
          ANIMAZIONE PULSE
          Crea l'effetto di pulsazione attorno all'elemento
          ===================================================================== */}
      <div
        style={{
          position: 'fixed',
          ...highlightStyle,
          border: '3px solid #85FF00',
          borderRadius: '12px',
          zIndex: 10001,
          animation: 'tourPulse 2s infinite',
          pointerEvents: 'none',
        }}
      />

      {/* =====================================================================
          TOOLTIP CON CONTENUTO
          Il pannello informativo che mostra titolo, descrizione e navigazione
          ===================================================================== */}
      <div
        ref={tooltipRef}
        style={{
          position: 'fixed',
          top: tooltipPosition.top,
          left: tooltipPosition.left,
          width: '400px',
          maxWidth: 'calc(100vw - 40px)',
          maxHeight: 'calc(100vh - 40px)',
          background: 'white',
          borderRadius: '16px',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
          zIndex: 10003,
          overflow: 'hidden',
          transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          opacity: isAnimating ? 0 : 1,
          transform: isAnimating ? 'translateY(10px)' : 'translateY(0)',
        }}
      >
        {/* Header del Tooltip */}
        <div
          style={{
            background: 'linear-gradient(135deg, #1A1A1A, #2D2D2D)',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {/* Icona Step */}
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: step.iconBg || 'linear-gradient(135deg, #85FF00, #65A30D)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {step.icon || <FaLightbulb size={18} color="white" />}
            </div>
            {/* Titolo e Numerazione */}
            <div>
              <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Step {currentStep + 1} di {steps.length}
              </div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: 'white' }}>
                {step.title}
              </div>
            </div>
          </div>
          {/* Bottone Chiudi */}
          <button
            onClick={handleSkip}
            style={{
              background: 'rgba(255,255,255,0.1)',
              border: 'none',
              borderRadius: '8px',
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'background 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
          >
            <FaTimes size={14} color="white" />
          </button>
        </div>

        {/* Barra di Progresso */}
        <div style={{ height: '4px', background: '#E5E7EB' }}>
          <div
            style={{
              height: '100%',
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #85FF00, #65A30D)',
              transition: 'width 0.4s ease',
            }}
          />
        </div>

        {/* Contenuto Principale */}
        <div style={{ padding: '20px' }}>
          <p style={{
            fontSize: '15px',
            lineHeight: '1.7',
            color: '#4B5563',
            margin: 0,
          }}>
            {step.content}
          </p>

          {/* Box Suggerimento (opzionale) */}
          {step.tip && (
            <div
              style={{
                marginTop: '16px',
                padding: '12px 16px',
                background: 'linear-gradient(135deg, #F0FDF4, #DCFCE7)',
                borderRadius: '10px',
                border: '1px solid #86EFAC',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
              }}
            >
              <FaLightbulb size={14} color="#16A34A" style={{ marginTop: '2px', flexShrink: 0 }} />
              <span style={{ fontSize: '13px', color: '#166534', lineHeight: '1.5' }}>
                {step.tip}
              </span>
            </div>
          )}
        </div>

        {/* Footer con Navigazione */}
        <div
          style={{
            padding: '16px 20px',
            borderTop: '1px solid #E5E7EB',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#F9FAFB',
          }}
        >
          {/* Link Salta Tour */}
          <button
            onClick={handleSkip}
            style={{
              padding: '8px 16px',
              background: 'transparent',
              border: 'none',
              fontSize: '14px',
              color: '#6B7280',
              cursor: 'pointer',
              transition: 'color 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = '#1F2937'}
            onMouseLeave={(e) => e.currentTarget.style.color = '#6B7280'}
          >
            Salta tour
          </button>

          {/* Bottoni Navigazione */}
          <div style={{ display: 'flex', gap: '10px' }}>
            {/* Bottone Indietro (solo se non siamo al primo step) */}
            {currentStep > 0 && (
              <button
                onClick={handlePrev}
                style={{
                  padding: '10px 18px',
                  background: 'white',
                  border: '2px solid #E5E7EB',
                  borderRadius: '10px',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: '#374151',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#D1D5DB';
                  e.currentTarget.style.background = '#F9FAFB';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#E5E7EB';
                  e.currentTarget.style.background = 'white';
                }}
              >
                <FaChevronLeft size={12} /> Indietro
              </button>
            )}

            {/* Bottone Avanti / Completa */}
            <button
              onClick={handleNext}
              style={{
                padding: '10px 20px',
                background: isLastStep
                  ? 'linear-gradient(135deg, #10B981, #059669)'
                  : 'linear-gradient(135deg, #1A1A1A, #2D2D2D)',
                border: 'none',
                borderRadius: '10px',
                fontSize: '14px',
                fontWeight: 600,
                color: 'white',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 6px 16px rgba(0,0,0,0.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
              }}
            >
              {isLastStep ? (
                <>
                  <FaCheck size={14} /> Completa
                </>
              ) : (
                <>
                  Avanti <FaChevronRight size={12} />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Indicatori Step (pallini) */}
        <div
          style={{
            padding: '12px 20px',
            display: 'flex',
            justifyContent: 'center',
            gap: '6px',
            background: '#F9FAFB',
            borderTop: '1px solid #E5E7EB',
          }}
        >
          {steps.map((_, index) => (
            <button
              key={index}
              onClick={() => {
                setCurrentStep(index);
                onStepChange?.(index, steps[index]);
              }}
              style={{
                width: index === currentStep ? '24px' : '8px',
                height: '8px',
                borderRadius: '4px',
                border: 'none',
                background: index === currentStep
                  ? '#85FF00'           // Step corrente: verde
                  : index < currentStep
                    ? '#10B981'          // Step completati: verde scuro
                    : '#D1D5DB',         // Step futuri: grigio
                cursor: 'pointer',
                transition: 'all 0.3s ease',
              }}
            />
          ))}
        </div>
      </div>

      {/* =====================================================================
          ANIMAZIONI CSS
          Definisce l'animazione di pulsazione per lo spotlight
          ===================================================================== */}
      <style>{`
        @keyframes tourPulse {
          0% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0;
            transform: scale(1.05);
          }
          100% {
            opacity: 0;
            transform: scale(1.1);
          }
        }
      `}</style>
    </>
  );
}

export default GuidedTour;

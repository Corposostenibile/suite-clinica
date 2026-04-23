/**
 * CheckSuccess - Pagina di conferma dopo invio check
 * Versione con animazione celebrativa, checkmark animato e confetti
 */

import { useParams } from 'react-router-dom';
import { useMemo } from 'react';
import './PublicChecks.css';

const CHECK_CONFIG = {
  weekly: {
    title: 'Check Settimanale',
    message: 'Il tuo check settimanale è stato inviato con successo!',
    theme: 'check-theme-weekly',
  },
  'weekly-light': {
    title: 'Check Settimanale',
    message: 'Il tuo check settimanale è stato inviato con successo!',
    theme: 'check-theme-weekly',
  },
  monthly: {
    title: 'Check Mensile',
    message: 'Il tuo check mensile è stato inviato con successo!',
    theme: 'check-theme-weekly',
  },
  dca: {
    title: 'Check Benessere',
    message: 'Il tuo check benessere è stato inviato con successo!',
    theme: 'check-theme-dca',
  },
  minor: {
    title: 'Check Minori',
    message: 'Il questionario è stato inviato con successo!',
    theme: 'check-theme-minor',
  },
};

const CONFETTI_COLORS = ['#22c55e', '#3b82f6', '#a855f7', '#f59e0b', '#ec4899', '#14b8a6'];

function CheckSuccess() {
  const { checkType } = useParams();
  const config = CHECK_CONFIG[checkType] || CHECK_CONFIG.weekly;

  const confettiPieces = useMemo(() => {
    return Array.from({ length: 24 }, (_, i) => ({
      id: i,
      left: `${Math.random() * 100}%`,
      color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
      delay: `${Math.random() * 1.5}s`,
      duration: `${2 + Math.random() * 2}s`,
      size: 6 + Math.random() * 6,
      rotation: Math.random() * 360,
    }));
  }, []);

  return (
    <div className={`check-card ${config.theme} check-success`}>
      {/* Animated Header */}
      <div className="check-success-header">
        {/* Confetti */}
        <div className="check-confetti">
          {confettiPieces.map(p => (
            <div
              key={p.id}
              className="check-confetti-piece"
              style={{
                left: p.left,
                top: '-10px',
                width: p.size,
                height: p.size,
                background: p.color,
                animationDelay: p.delay,
                animationDuration: p.duration,
                borderRadius: p.id % 3 === 0 ? '50%' : '2px',
                transform: `rotate(${p.rotation}deg)`,
              }}
            />
          ))}
        </div>

        {/* Animated Checkmark */}
        <div className="check-success-checkmark">
          <svg viewBox="0 0 56 56">
            <circle className="circle" cx="28" cy="28" r="26" />
            <path className="check" d="M16 28 L24 36 L40 20" />
          </svg>
        </div>

        <h3 className="check-success-title">Grazie!</h3>
      </div>

      {/* Body */}
      <div className="check-success-body">
        <p className="check-success-message">
          {config.title} Completato
        </p>
        <p className="check-success-detail">
          {config.message}
        </p>

        <div className="check-success-info">
          <i className="ri-team-line check-success-info-icon"></i>
          <span className="check-success-info-text">
            I tuoi professionisti riceveranno le tue risposte e le analizzeranno per supportarti al meglio nel tuo percorso.
          </span>
        </div>

        <div className="check-success-close">
          <i className="ri-close-circle-line"></i>
          Puoi chiudere questa pagina in sicurezza
        </div>
      </div>
    </div>
  );
}

export default CheckSuccess;

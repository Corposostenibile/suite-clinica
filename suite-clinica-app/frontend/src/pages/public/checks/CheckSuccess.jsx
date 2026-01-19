/**
 * CheckSuccess - Pagina di conferma dopo invio check
 * Versione generica per tutti i tipi di check
 */

import { useParams } from 'react-router-dom';

const styles = {
  card: {
    borderRadius: '20px',
    border: 'none',
    boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
    overflow: 'hidden',
    textAlign: 'center',
  },
  successIcon: {
    width: '80px',
    height: '80px',
    borderRadius: '50%',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '40px',
    marginBottom: '24px',
  },
};

const CHECK_CONFIG = {
  weekly: {
    title: 'Check Settimanale',
    color: '#10b981',
    gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    message: 'Il tuo check settimanale è stato inviato con successo!',
  },
  dca: {
    title: 'Check Benessere',
    color: '#3b82f6',
    gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    message: 'Il tuo check benessere è stato inviato con successo!',
  },
  minor: {
    title: 'Check Minori',
    color: '#f59e0b',
    gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    message: 'Il questionario è stato inviato con successo!',
  },
};

function CheckSuccess() {
  const { checkType } = useParams();
  const config = CHECK_CONFIG[checkType] || CHECK_CONFIG.weekly;

  return (
    <div className="card" style={styles.card}>
      {/* Header */}
      <div style={{ background: config.gradient, color: 'white', padding: '40px 24px' }}>
        <div
          style={{
            ...styles.successIcon,
            background: 'rgba(255,255,255,0.2)',
            color: 'white'
          }}
        >
          <i className="ri-check-line"></i>
        </div>
        <h3 className="mb-0 fw-bold">Grazie!</h3>
      </div>

      {/* Body */}
      <div className="card-body p-5">
        <div
          style={{
            ...styles.successIcon,
            background: `${config.color}15`,
            color: config.color
          }}
        >
          <i className="ri-checkbox-circle-line"></i>
        </div>

        <h4 className="mb-3 fw-semibold">{config.title} Completato</h4>

        <p className="text-muted mb-4" style={{ fontSize: '1.1rem' }}>
          {config.message}
        </p>

        <div
          style={{
            background: '#f8fafc',
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '24px'
          }}
        >
          <p className="mb-0 text-muted">
            <i className="ri-information-line me-2" style={{ color: config.color }}></i>
            I tuoi professionisti riceveranno le tue risposte e le analizzeranno per supportarti al meglio nel tuo percorso.
          </p>
        </div>

        <p className="text-muted small mb-0">
          Puoi chiudere questa pagina in sicurezza.
        </p>
      </div>
    </div>
  );
}

export default CheckSuccess;

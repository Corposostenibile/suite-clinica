import '../chat/Chat.css';

function AssegnazioniAI() {
  return (
    <div className="chat-coming-soon">
      <div className="chat-hero">
        <div className="chat-hero-icon">
          <i className="ri-user-add-line"></i>
        </div>

        <h3 className="chat-hero-title">Assegnazione Professionisti</h3>

        <p className="chat-hero-desc">
          Qui potrai assegnare i professionisti ai pazienti con l'aiuto di SUMI.
          <br />
          <strong>Questa funzionalità sarà disponibile con l'uscita della nuova versione del CRM per i sales.</strong>
        </p>

        <div className="chat-soon-badge">
          <i className="ri-time-line"></i>
          Prossimamente
        </div>
      </div>
    </div>
  );
}

export default AssegnazioniAI;

import './Chat.css';

function Chat() {
  return (
    <div className="chat-coming-soon">
      <div className="chat-hero">
        <div className="chat-hero-icon">
          <i className="ri-chat-3-line"></i>
        </div>

        <h3 className="chat-hero-title">Chat con i Pazienti</h3>

        <p className="chat-hero-desc">
          Qui potrai comunicare direttamente con i tuoi pazienti in tempo reale.
          <br />
          <strong>Questa funzionalità sarà disponibile con l'uscita dell'applicazione per i pazienti.</strong>
        </p>

        <div className="chat-soon-badge">
          <i className="ri-time-line"></i>
          Prossimamente
        </div>
      </div>
    </div>
  );
}

export default Chat;

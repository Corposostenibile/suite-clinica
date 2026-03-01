import './Calendario.css';

function Calendario() {
  return (
    <div className="cal-coming-soon">
      <div className="cal-hero">
        <div className="cal-hero-icon">
          <i className="ri-calendar-line"></i>
        </div>

        <h3 className="cal-hero-title">Calendario</h3>

        <p className="cal-hero-desc">
          Qui potrai gestire i tuoi appuntamenti, visualizzare la tua agenda e
          sincronizzare il calendario con i tuoi pazienti.
          <br />
          <strong>Disponibile da lunedì 9 marzo con la versione 1.1 della Suite Clinica.</strong>
        </p>

        <div className="cal-soon-badge">
          <i className="ri-rocket-2-line"></i>
          In arrivo — v1.1 · 9 Marzo
        </div>
      </div>
    </div>
  );
}

export default Calendario;

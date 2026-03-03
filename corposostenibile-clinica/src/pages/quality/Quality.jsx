import '../calendario/Calendario.css';
import './quality-responsive.css';

function Quality() {
  return (
    <div className="cal-coming-soon">
      <div className="cal-hero">
        <div className="cal-hero-icon">
          <i className="ri-bar-chart-grouped-line"></i>
        </div>

        <h3 className="cal-hero-title">Quality Dashboard</h3>

        <p className="cal-hero-desc">
          Qui potrai monitorare le performance del team e visualizzare i KPI
          settimanali e trimestrali.
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

export default Quality;

import { useOutletContext } from 'react-router-dom';

function Welcome() {
  const { user } = useOutletContext();

  return (
    <div className="container-fluid p-0">
      {/* Header */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h4 className="mb-1" style={{ fontWeight: 700, color: '#1e293b' }}>
            Ciao, {user?.first_name || 'Admin'}!
          </h4>
          <p className="text-muted mb-0">Dashboard Amministrativa</p>
        </div>
      </div>

      {/* Coming Soon Card */}
      <div className="card border-0 shadow-sm" style={{ borderRadius: '16px' }}>
        <div className="card-body text-center py-5">
          <div className="mb-4">
            <i className="ri-time-line text-primary" style={{ fontSize: '5rem', opacity: 0.3 }}></i>
          </div>
          <h4 className="text-muted mb-2">In Arrivo</h4>
          <p className="text-muted mb-0">
            La sezione <strong>Dashboard</strong> sarà disponibile presto.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Welcome;

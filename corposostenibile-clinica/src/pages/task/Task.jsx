function Task() {
    return (
        <>
            {/* Page Header */}
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                <div>
                    <h4 className="mb-1">Le tue Task</h4>
                    <p className="text-muted mb-0">Gestisci le tue attività quotidiane</p>
                </div>
            </div>

            {/* Coming Soon Card */}
            <div className="card" style={{ borderRadius: '16px', border: 'none', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
                <div className="card-body p-0">
                    <div
                        className="d-flex flex-column align-items-center justify-content-center text-center"
                        style={{
                            minHeight: '500px',
                            background: 'linear-gradient(180deg, #f8f9fc 0%, #ffffff 100%)',
                            borderRadius: '16px',
                            padding: '60px 40px'
                        }}
                    >
                        {/* Icon Container */}
                        <div
                            className="mb-4"
                            style={{
                                width: '120px',
                                height: '120px',
                                borderRadius: '50%',
                                background: 'linear-gradient(135deg, rgba(23, 162, 184, 0.15) 0%, rgba(23, 162, 184, 0.05) 100%)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}
                        >
                            <i
                                className="ri-task-line"
                                style={{
                                    fontSize: '56px',
                                    color: '#17a2b8'
                                }}
                            ></i>
                        </div>

                        {/* Title */}
                        <h3
                            className="mb-3"
                            style={{
                                fontWeight: '600',
                                color: '#333',
                                fontSize: '28px'
                            }}
                        >
                            Gestione Task
                        </h3>

                        {/* Description */}
                        <p
                            className="mb-4"
                            style={{
                                color: '#6c757d',
                                maxWidth: '450px',
                                fontSize: '16px',
                                lineHeight: '1.6'
                            }}
                        >
                            Qui potrai gestire tutte le tue attività: onboarding clienti, check da leggere, reminder e formazione.
                            <br />
                            <strong style={{ color: '#555' }}>
                                Questa funzionalità sarà disponibile a breve.
                            </strong>
                        </p>

                        {/* Feature Pills */}
                        <div className="d-flex flex-wrap justify-content-center gap-2 mb-4">
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(23, 162, 184, 0.1)',
                                    color: '#17a2b8',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-user-add-line me-1"></i>
                                Onboarding
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(40, 167, 69, 0.1)',
                                    color: '#28a745',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-file-list-3-line me-1"></i>
                                Check da leggere
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(220, 140, 20, 0.1)',
                                    color: '#dc8c14',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-alarm-warning-line me-1"></i>
                                Reminder
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(111, 66, 193, 0.1)',
                                    color: '#6f42c1',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-book-open-line me-1"></i>
                                Formazione
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(220, 53, 69, 0.1)',
                                    color: '#dc3545',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-notification-badge-line me-1"></i>
                                Notifiche
                            </span>
                        </div>

                        {/* Coming Soon Badge */}
                        <div
                            className="d-inline-flex align-items-center"
                            style={{
                                background: 'linear-gradient(135deg, #17a2b8 0%, #138496 100%)',
                                color: '#fff',
                                padding: '12px 28px',
                                borderRadius: '30px',
                                fontWeight: '600',
                                fontSize: '14px',
                                boxShadow: '0 4px 15px rgba(23, 162, 184, 0.3)'
                            }}
                        >
                            <i className="ri-time-line me-2" style={{ fontSize: '18px' }}></i>
                            Prossimamente
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

export default Task;

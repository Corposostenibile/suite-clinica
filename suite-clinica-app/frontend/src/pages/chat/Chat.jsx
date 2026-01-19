function Chat() {
    return (
        <>
            {/* Page Header */}
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                <div>
                    <h4 className="mb-1">Chat Pazienti</h4>
                    <p className="text-muted mb-0">Messaggi con i tuoi pazienti</p>
                </div>
            </div>

            {/* Coming Soon Card */}
            <div className="card" style={{ borderRadius: '16px', border: 'none', boxShadow: '0 2px 12px rgba(0,0,0,0.08)' }}>
                <div className="card-body p-0">
                    <div
                        className="d-flex flex-column align-items-center justify-content-center text-center"
                        style={{
                            minHeight: '500px',
                            background: 'linear-gradient(180deg, #f8faf9 0%, #ffffff 100%)',
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
                                background: 'linear-gradient(135deg, rgba(40, 199, 111, 0.15) 0%, rgba(40, 199, 111, 0.05) 100%)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}
                        >
                            <i
                                className="ri-chat-3-line"
                                style={{
                                    fontSize: '56px',
                                    color: '#28c76f'
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
                            Chat con i Pazienti
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
                            Qui potrai comunicare direttamente con i tuoi pazienti in tempo reale.
                            <br />
                            <strong style={{ color: '#555' }}>
                                Questa funzionalità sarà disponibile con l'uscita dell'applicazione per i pazienti.
                            </strong>
                        </p>

                        {/* Feature Pills */}
                        <div className="d-flex flex-wrap justify-content-center gap-2 mb-4">
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(40, 199, 111, 0.1)',
                                    color: '#28c76f',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-message-3-line me-1"></i>
                                Messaggi in tempo reale
                            </span>
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
                                <i className="ri-notification-3-line me-1"></i>
                                Notifiche push
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(255, 159, 67, 0.1)',
                                    color: '#ff9f43',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-attachment-2 me-1"></i>
                                Condivisione file
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(156, 39, 176, 0.1)',
                                    color: '#9c27b0',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-bar-chart-line me-1"></i>
                                Analisi chat
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(103, 58, 183, 0.1)',
                                    color: '#673ab7',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-robot-line me-1"></i>
                                AI integrata
                            </span>
                        </div>

                        {/* Coming Soon Badge */}
                        <div
                            className="d-inline-flex align-items-center"
                            style={{
                                background: 'linear-gradient(135deg, #28c76f 0%, #24b662 100%)',
                                color: '#fff',
                                padding: '12px 28px',
                                borderRadius: '30px',
                                fontWeight: '600',
                                fontSize: '14px',
                                boxShadow: '0 4px 15px rgba(40, 199, 111, 0.3)'
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

export default Chat;

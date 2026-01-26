function Support() {
    return (
        <>
            {/* Page Header */}
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                <div>
                    <h4 className="mb-1">Supporto SUMI</h4>
                    <p className="text-muted mb-0">Assistenza e aiuto</p>
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
                        {/* SuiteMind Logo */}
                        <div className="mb-4">
                            <img
                                src="/suitemind.png"
                                alt="SUMI"
                                style={{
                                    width: '120px',
                                    height: '120px',
                                    objectFit: 'contain'
                                }}
                            />
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
                            Supporto SUMI
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
                            SUMI è l'assistente virtuale di Suite Clinica, pronto ad aiutarti in ogni momento.
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
                                    background: 'rgba(99, 102, 241, 0.1)',
                                    color: '#6366f1',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-chat-1-line me-1"></i>
                                Chat con supporto
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(16, 185, 129, 0.1)',
                                    color: '#10b981',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-book-open-line me-1"></i>
                                Guide e tutorial
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(245, 158, 11, 0.1)',
                                    color: '#f59e0b',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-question-answer-line me-1"></i>
                                FAQ
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(239, 68, 68, 0.1)',
                                    color: '#ef4444',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-bug-line me-1"></i>
                                Segnala un problema
                            </span>
                            <span
                                className="badge"
                                style={{
                                    background: 'rgba(14, 165, 233, 0.1)',
                                    color: '#0ea5e9',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-compass-3-line me-1"></i>
                                Tour guidato
                            </span>
                        </div>

                        {/* Coming Soon Badge */}
                        <div
                            style={{
                                background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                                color: 'white',
                                padding: '12px 32px',
                                borderRadius: '30px',
                                fontWeight: '600',
                                fontSize: '14px',
                                boxShadow: '0 4px 15px rgba(99, 102, 241, 0.3)',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '8px'
                            }}
                        >
                            <i className="ri-time-line"></i>
                            In Arrivo
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

export default Support;

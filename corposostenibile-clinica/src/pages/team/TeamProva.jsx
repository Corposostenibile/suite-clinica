function TeamProva() {
    return (
        <>
            {/* Page Header */}
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                <div>
                    <h4 className="mb-1">Professionisti In Prova</h4>
                    <p className="text-muted mb-0">Gestisci i professionisti in periodo di prova</p>
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
                                background: 'linear-gradient(135deg, rgba(253, 126, 20, 0.15) 0%, rgba(253, 126, 20, 0.05) 100%)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}
                        >
                            <i
                                className="ri-time-line"
                                style={{
                                    fontSize: '56px',
                                    color: '#fd7e14'
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
                            Professionisti In Prova
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
                            Qui potrai gestire i professionisti in periodo di prova: monitorare il loro progresso, valutazioni e feedback.
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
                                    background: 'rgba(253, 126, 20, 0.1)',
                                    color: '#fd7e14',
                                    padding: '8px 16px',
                                    borderRadius: '20px',
                                    fontWeight: '500',
                                    fontSize: '13px'
                                }}
                            >
                                <i className="ri-user-follow-line me-1"></i>
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
                                <i className="ri-checkbox-circle-line me-1"></i>
                                Valutazioni
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
                                <i className="ri-feedback-line me-1"></i>
                                Feedback
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
                                <i className="ri-line-chart-line me-1"></i>
                                Progresso
                            </span>
                        </div>

                        {/* Coming Soon Badge */}
                        <div
                            className="d-inline-flex align-items-center"
                            style={{
                                background: 'linear-gradient(135deg, #fd7e14 0%, #e66a00 100%)',
                                color: '#fff',
                                padding: '12px 28px',
                                borderRadius: '30px',
                                fontWeight: '600',
                                fontSize: '14px',
                                boxShadow: '0 4px 15px rgba(253, 126, 20, 0.3)'
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

export default TeamProva;

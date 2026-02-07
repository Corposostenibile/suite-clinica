import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import clientiService from '../../services/clientiService';
import { 
    FaUserFriends, 
    FaTasks, 
    FaGraduationCap, 
    FaChartBar, 
    FaBookOpen, 
    FaPlayCircle, 
    FaSearch,
    FaQuestionCircle,
    FaArrowRight,
    FaUserCircle,
    FaClipboardList
} from 'react-icons/fa';

const SUPPORT_CARDS = [
    {
        id: 'lista-pazienti',
        title: 'Lista Pazienti',
        description: 'Dashboard operativa per gestire pazienti, filtri avanzati, statistiche e monitoraggio rinnovi.',
        icon: <FaUserFriends size={32} />,
        color: '#4CAF50',
        gradient: 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)',
        docHash: 'lista-pazienti',
        tourPage: '/clienti-lista',
        tourAvailable: true
    },
    {
        id: 'dettaglio-paziente',
        title: 'Scheda Paziente',
        description: 'Visione completa a 360° del paziente: anagrafica, piani, allenamenti e diario clinico.',
        icon: <FaUserCircle size={32} />,
        color: '#2196F3',
        gradient: 'linear-gradient(135deg, #2196F3 0%, #1565C0 100%)',
        docHash: 'la-scheda-completa_del_paziente',
        tourPage: '/clienti-dettaglio/10101', // ID demo valido
        tourAvailable: true
    },
    {
        id: 'task',
        title: 'Sistema Task',
        description: 'Organizza la giornata con task automatici, scadenze e solleciti intelligenti.',
        icon: <FaTasks size={32} />,
        color: '#FF9800',
        gradient: 'linear-gradient(135deg, #FF9800 0%, #EF6C00 100%)',
        docHash: 'task',
        tourPage: '/task',
        tourAvailable: true
    },
    {
        id: 'formazione',
        title: 'Formazione',
        description: 'Accedi ai materiali formativi, protocolli ufficiali e richiedi training specifici.',
        icon: <FaGraduationCap size={32} />,
        color: '#9C27B0',
        gradient: 'linear-gradient(135deg, #9C27B0 0%, #6A1B9A 100%)',
        docHash: 'formazione',
        tourPage: '/formazione',
        tourAvailable: true
    },
    {
        id: 'check-azienda',
        title: 'Check Azienda (KPI)',
        description: 'Analizza qualità del servizio, soddisfazione pazienti e performance del team.',
        icon: <FaChartBar size={32} />,
        color: '#F44336',
        gradient: 'linear-gradient(135deg, #F44336 0%, #C62828 100%)',
        docHash: 'check-azienda',
        tourPage: '/check-azienda',
        tourAvailable: true
    }
];

const Support = () => {
    const navigate = useNavigate();
    const [searchQuery, setSearchQuery] = useState('');
    const [firstClientId, setFirstClientId] = useState(null);

    useEffect(() => {
        const fetchFirstClient = async () => {
            try {
                const response = await clientiService.getClienti({ per_page: 1 });
                const clients = response.data || response.clienti || (Array.isArray(response) ? response : []);
                if (clients.length > 0) {
                    const id = clients[0].cliente_id || clients[0].id;
                    setFirstClientId(id);
                }
            } catch (error) {
                console.error("Errore nel recupero del primo cliente per il tour:", error);
            }
        };
        fetchFirstClient();
    }, []);

    const filteredCards = SUPPORT_CARDS.filter(card => 
        card.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        card.description.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleOpenDocs = (hash) => {
        navigate(`/documentazione#${hash}`);
    };

    const handleStartTour = (card) => {
        if (card.id === 'dettaglio-paziente' && firstClientId) {
            navigate(`/clienti-dettaglio/${firstClientId}?startTour=true`);
        } else if (card.tourPage) {
            navigate(`${card.tourPage}?startTour=true`);
        } else if (card.id === 'dettaglio-paziente') {
            // Fallback se non abbiamo ancora l'ID o se c'è stato un errore
            navigate(`/clienti-lista?startTour=true`);
        }
    };

    return (
        <div className="support-container" style={{ padding: '0 10px' }}>
            <style>
                {`
                    .search-input::placeholder {
                        color: rgba(255, 255, 255, 0.85) !important;
                        opacity: 1 !important;
                    }
                `}
            </style>
            {/* Header Hero Section */}
            <div style={{ 
                background: 'linear-gradient(135deg, #1B5E20 0%, #0D3B12 100%)',
                padding: '40px 30px',
                borderRadius: '24px',
                marginBottom: '30px',
                color: 'white',
                position: 'relative',
                overflow: 'hidden',
                boxShadow: '0 15px 35px rgba(0,0,0,0.2)'
            }}>
                <div style={{ position: 'relative', zIndex: 2 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '20px' }}>
                        <img 
                            src="/suitemind.png" 
                            alt="SUMI" 
                            style={{ 
                                width: '80px', 
                                height: '80px', 
                                objectFit: 'contain',
                                filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.2))'
                            }} 
                        />
                        <div>
                            <h1 style={{ fontSize: '38px', fontWeight: '800', marginBottom: '8px', margin: 0, color: '#ffffff', textShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
                                Centro Supporto
                            </h1>
                            <p style={{ fontSize: '18px', opacity: 1, fontWeight: '500', margin: 0 }}>
                                Guide, Tour e Assistenza per Suite Clinica
                            </p>
                        </div>
                    </div>
                    
                    {/* Search Bar */}
                    <div style={{ 
                        background: 'rgba(255,255,255,0.15)',
                        backdropFilter: 'blur(10px)',
                        borderRadius: '16px',
                        padding: '10px 20px',
                        display: 'flex',
                        alignItems: 'center',
                        maxWidth: '600px',
                        border: '1px solid rgba(255,255,255,0.2)',
                        boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
                        marginTop: '24px'
                    }}>
                        <FaSearch style={{ marginRight: '15px', color: 'rgba(255,255,255,0.9)', fontSize: '18px' }} />
                        <input 
                            type="text" 
                            className="search-input"
                            placeholder="Cerca una funzionalità (es. come creare un task...)"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            style={{ 
                                background: 'transparent',
                                border: 'none',
                                color: 'white',
                                width: '100%',
                                fontSize: '16px',
                                outline: 'none'
                            }}
                        />
                    </div>
                </div>
                
                {/* Decorative Pattern */}
                <div style={{ 
                    position: 'absolute',
                    top: '-50px',
                    right: '-50px',
                    width: '300px',
                    height: '300px',
                    background: 'rgba(255,255,255,0.05)',
                    borderRadius: '50%',
                    zIndex: 1
                }} />
                <div style={{ 
                    position: 'absolute',
                    bottom: '-30px',
                    right: '100px',
                    width: '150px',
                    height: '150px',
                    background: 'rgba(255,255,255,0.03)',
                    borderRadius: '50%',
                    zIndex: 1
                }} />
            </div>

            {/* Section Title */}
            <div style={{ marginBottom: '24px' }}>
                <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#1e293b', marginBottom: '8px' }}>
                    📚 Guide Operative
                </h2>
                <p style={{ color: '#64748b', fontSize: '15px', margin: 0 }}>
                    Seleziona un'area per leggere la guida completa o avviare il tour guidato interattivo
                </p>
            </div>

            {/* Support Hub Grid */}
            <div className="row g-4 mb-5">
                {filteredCards.map((card) => (
                    <div key={card.id} className="col-xl-4 col-lg-6">
                        <div className="card border-0" style={{ 
                            borderRadius: '20px', 
                            overflow: 'hidden',
                            boxShadow: '0 8px 25px rgba(0,0,0,0.08)',
                            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                            cursor: 'default',
                            position: 'relative'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateY(-8px)';
                            e.currentTarget.style.boxShadow = '0 20px 40px rgba(0,0,0,0.15)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = '0 8px 25px rgba(0,0,0,0.08)';
                        }}
                        >
                            {/* Header con gradiente */}
                            <div style={{ 
                                background: card.gradient, 
                                padding: '20px 20px', 
                                color: 'white',
                                position: 'relative',
                                overflow: 'hidden'
                            }}>
                                <div style={{ 
                                    position: 'absolute',
                                    top: '-20px',
                                    right: '-20px',
                                    width: '100px',
                                    height: '100px',
                                    background: 'rgba(255,255,255,0.1)',
                                    borderRadius: '50%'
                                }} />
                                <div style={{ 
                                    background: 'rgba(255,255,255,0.2)', 
                                    padding: '20px', 
                                    borderRadius: '16px',
                                    backdropFilter: 'blur(5px)',
                                    display: 'inline-flex',
                                    boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
                                    position: 'relative',
                                    zIndex: 2
                                }}>
                                    {card.icon}
                                </div>
                            </div>

                            {/* Body */}
                            <div className="card-body p-3 d-flex flex-column">
                                <h5 style={{ 
                                    fontWeight: '700', 
                                    marginBottom: '8px', 
                                    color: '#1e293b',
                                    fontSize: '17px'
                                }}>
                                    {card.title}
                                </h5>
                                <p style={{ 
                                    color: '#64748b', 
                                    fontSize: '13px', 
                                    lineHeight: '1.5',
                                    marginBottom: '16px', 
                                }}>
                                    {card.description}
                                </p>
                                
                                {/* Action Buttons */}
                                <div className="d-grid gap-2">
                                    <button 
                                        className="btn"
                                        onClick={() => handleOpenDocs(card.docHash)}
                                        style={{ 
                                            borderRadius: '12px', 
                                            padding: '12px', 
                                            fontWeight: '600',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            gap: '8px',
                                            border: `2px solid ${card.color}`,
                                            background: 'white',
                                            color: card.color,
                                            transition: 'all 0.2s ease'
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.background = card.color;
                                            e.currentTarget.style.color = 'white';
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.background = 'white';
                                            e.currentTarget.style.color = card.color;
                                        }}
                                    >
                                        <FaBookOpen size={14} /> Leggi Guida
                                    </button>
                                    {card.tourAvailable && (
                                        <button 
                                            className="btn"
                                            onClick={() => handleStartTour(card)}
                                            style={{ 
                                                borderRadius: '12px', 
                                                padding: '12px', 
                                                fontWeight: '600',
                                                border: 'none',
                                                background: card.gradient,
                                                color: 'white',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                gap: '8px',
                                                boxShadow: `0 4px 15px ${card.color}40`,
                                                transition: 'all 0.2s ease'
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.transform = 'translateY(-2px)';
                                                e.currentTarget.style.boxShadow = `0 6px 20px ${card.color}60`;
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.transform = 'translateY(0)';
                                                e.currentTarget.style.boxShadow = `0 4px 15px ${card.color}40`;
                                            }}
                                        >
                                            <FaPlayCircle size={14} /> Avvia Tour Guidato
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Additional Help Sections */}
            <div style={{ marginBottom: '24px', marginTop: '48px' }}>
                <h2 style={{ fontSize: '24px', fontWeight: '700', color: '#1e293b', marginBottom: '8px' }}>
                    💡 Altre Risorse
                </h2>
                <p style={{ color: '#64748b', fontSize: '15px', margin: 0 }}>
                    Strumenti aggiuntivi per risolvere dubbi e ottenere assistenza
                </p>
            </div>

            <div className="row g-4">
                <div className="col-lg-6">
                    <div className="card border-0" style={{ 
                        borderRadius: '20px', 
                        background: 'linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%)', 
                        border: '1px solid #E5E7EB',
                        transition: 'all 0.3s ease',
                        cursor: 'pointer'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-4px)';
                        e.currentTarget.style.boxShadow = '0 12px 24px rgba(0,0,0,0.1)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                    }}
                    >
                        <div className="card-body p-4 d-flex align-items-center gap-4">
                            <div style={{ 
                                background: 'linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%)', 
                                padding: '18px', 
                                borderRadius: '16px', 
                                boxShadow: '0 4px 15px rgba(76, 175, 80, 0.3)' 
                            }}>
                                <FaQuestionCircle size={32} color="white" />
                            </div>
                            <div style={{ flex: 1 }}>
                                <h5 className="mb-1" style={{ fontWeight: '700', color: '#1e293b' }}>FAQ & Troubleshooting</h5>
                                <p className="text-muted mb-0 small">Risolvi velocemente i dubbi più comuni</p>
                            </div>
                            <FaArrowRight size={20} style={{ color: '#4CAF50' }} />
                        </div>
                    </div>
                </div>
                <div className="col-lg-6">
                    <div className="card border-0" style={{ 
                        borderRadius: '20px', 
                        background: 'linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%)', 
                        border: '1px solid #E5E7EB',
                        transition: 'all 0.3s ease',
                        cursor: 'pointer'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-4px)';
                        e.currentTarget.style.boxShadow = '0 12px 24px rgba(0,0,0,0.1)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'none';
                    }}
                    >
                        <div className="card-body p-4 d-flex align-items-center gap-4">
                            <div style={{ 
                                background: 'linear-gradient(135deg, #2196F3 0%, #1565C0 100%)', 
                                padding: '18px', 
                                borderRadius: '16px', 
                                boxShadow: '0 4px 15px rgba(33, 150, 243, 0.3)' 
                            }}>
                                <img src="/suitemind.png" alt="SUMI" style={{ width: '32px', height: '32px', objectFit: 'contain' }} />
                            </div>
                            <div style={{ flex: 1 }}>
                                <h5 className="mb-1" style={{ fontWeight: '700', color: '#1e293b' }}>Chiedi a SUMI</h5>
                                <p className="text-muted mb-0 small">Assistente AI per supporto immediato</p>
                            </div>
                            <FaArrowRight size={20} style={{ color: '#2196F3' }} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Support;

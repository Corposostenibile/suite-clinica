import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Support.css';

const SUPPORT_SECTIONS = [
    {
        id: 'dashboard',
        title: 'Dashboard',
        description: 'Panoramica generale, statistiche rapide e riepilogo giornaliero della tua attività.',
        icon: 'ri-dashboard-line',
        gradient: 'linear-gradient(135deg, #25B36A, #1a8a50)',
    },
    {
        id: 'calendario',
        title: 'Calendario',
        description: 'Gestione appuntamenti, sincronizzazione Google Calendar e vista settimanale.',
        icon: 'ri-calendar-line',
        gradient: 'linear-gradient(135deg, #3b82f6, #2563eb)',
    },
    {
        id: 'chat',
        title: 'Chat',
        description: 'Comunicazione diretta con i pazienti in tempo reale. Funzionalità in arrivo.',
        icon: 'ri-chat-3-line',
        gradient: 'linear-gradient(135deg, #06b6d4, #0891b2)',
        comingSoon: true,
    },
    {
        id: 'task',
        title: 'Task',
        description: 'Gestione attività, scadenze, solleciti automatici e organizzazione del lavoro.',
        icon: 'ri-task-line',
        gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
        docsGuideKey: 'task',
    },
    {
        id: 'post-it',
        title: 'Post-it',
        description: 'Promemoria rapidi nella sidebar, note personali e appunti veloci.',
        icon: 'ri-sticky-note-line',
        gradient: 'linear-gradient(135deg, #eab308, #ca8a04)',
    },
    {
        id: 'formazione',
        title: 'Formazione',
        description: 'Training assegnati, formazione erogata e richieste di crescita professionale tra colleghi.',
        icon: 'ri-graduation-cap-line',
        gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
        docsGuideKey: 'formazione',
    },
    {
        id: 'pazienti',
        title: 'Pazienti',
        description: 'Lista pazienti, scheda dettagliata, filtri avanzati e monitoraggio percorsi.',
        icon: 'ri-group-line',
        gradient: 'linear-gradient(135deg, #10b981, #059669)',
        docsGuideKey: 'lista-pazienti',
    },
    {
        id: 'assegnazioni',
        title: 'Assegnazioni',
        description: 'Assegnazione pazienti ai professionisti, criteri automatici e gestione carico.',
        icon: 'ri-user-settings-line',
        gradient: 'linear-gradient(135deg, #ec4899, #db2777)',
    },
    {
        id: 'check',
        title: 'Check',
        description: 'Compilazione check, monitoraggio progressi e storico dei pazienti.',
        icon: 'ri-checkbox-circle-line',
        gradient: 'linear-gradient(135deg, #14b8a6, #0d9488)',
        docsGuideKey: 'check-azienda',
    },
    {
        id: 'team',
        title: 'Team',
        description: 'Gestione team, composizione gruppi, ruoli e coordinamento tra professionisti.',
        icon: 'ri-team-line',
        gradient: 'linear-gradient(135deg, #6366f1, #4f46e5)',
    },
    {
        id: 'professionisti',
        title: 'Professionisti',
        description: 'Elenco professionisti, specialità, capacità operativa e dettagli profilo.',
        icon: 'ri-user-star-line',
        gradient: 'linear-gradient(135deg, #f97316, #ea580c)',
    },
    {
        id: 'quality',
        title: 'Quality',
        description: 'Analisi qualità del servizio, KPI, soddisfazione pazienti e performance.',
        icon: 'ri-bar-chart-box-line',
        gradient: 'linear-gradient(135deg, #ef4444, #dc2626)',
    },
    {
        id: 'in-prova',
        title: 'In Prova',
        description: 'Gestione utenti in prova, monitoraggio trial e conversione a professionisti attivi.',
        icon: 'ri-user-follow-line',
        gradient: 'linear-gradient(135deg, #a855f7, #9333ea)',
    },
];

const Support = () => {
    const navigate = useNavigate();
    const [searchQuery, setSearchQuery] = useState('');

    const filteredSections = SUPPORT_SECTIONS.filter(section =>
        section.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        section.description.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="sup-page">
            {/* Header */}
            <div className="sup-header">
                <div className="sup-header-left">
                    <img src="/suitemind.png" alt="SUMI" className="sup-header-logo" />
                    <div>
                        <h4>Centro Supporto</h4>
                        <p>Guide e documentazione per ogni sezione di Suite Clinica</p>
                    </div>
                </div>
            </div>

            {/* Search */}
            <div className="sup-search-row">
                <div className="sup-search-wrap">
                    <input
                        type="text"
                        className="sup-search-input"
                        placeholder="Cerca una sezione"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                    <i className="ri-search-line sup-search-icon"></i>
                </div>
            </div>

            {/* Cards grid */}
            {filteredSections.length === 0 ? (
                <div className="sup-empty">
                    <div className="sup-empty-icon">
                        <i className="ri-search-line"></i>
                    </div>
                    <h5>Nessun risultato</h5>
                    <p>Nessuna sezione trovata per "{searchQuery}". Prova con un altro termine.</p>
                </div>
            ) : (
                <div className="sup-cards-grid">
                    {filteredSections.map((section) => (
                        <div key={section.id} className="sup-card">
                            <div className="sup-card-icon-area">
                                <div className="sup-card-icon" style={{ background: section.gradient }}>
                                    <i className={section.icon}></i>
                                </div>
                            </div>
                            <div className="sup-card-body">
                                <div className="sup-card-title">{section.title}</div>
                                <div className="sup-card-desc">{section.description}</div>
                                {section.comingSoon ? (
                                    <button className="sup-btn-go disabled" disabled>
                                        <i className="ri-time-line"></i>
                                        In Arrivo
                                    </button>
                                ) : section.docsGuideKey ? (
                                    <button
                                        className="sup-btn-go"
                                        onClick={() => navigate(`/documentazione#${section.docsGuideKey}`)}
                                    >
                                        Vai alla Documentazione
                                        <i className="ri-arrow-right-line"></i>
                                    </button>
                                ) : (
                                    <button
                                        className="sup-btn-go"
                                        onClick={() => navigate(`/supporto/${section.id}`)}
                                    >
                                        Vai al Supporto Dedicato
                                        <i className="ri-arrow-right-line"></i>
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default Support;

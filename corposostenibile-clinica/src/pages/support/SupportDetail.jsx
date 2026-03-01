import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './SupportDetail.css';

const SECTIONS = {
    dashboard: {
        title: 'Dashboard',
        subtitle: 'Guida alla panoramica generale',
        icon: 'ri-dashboard-line',
        gradient: 'linear-gradient(135deg, #25B36A, #1a8a50)',
    },
    calendario: {
        title: 'Calendario',
        subtitle: 'Guida alla gestione appuntamenti',
        icon: 'ri-calendar-line',
        gradient: 'linear-gradient(135deg, #3b82f6, #2563eb)',
    },
    chat: {
        title: 'Chat',
        subtitle: 'Guida alla messaggistica interna',
        icon: 'ri-chat-3-line',
        gradient: 'linear-gradient(135deg, #06b6d4, #0891b2)',
    },
    task: {
        title: 'Task',
        subtitle: 'Guida alla gestione attività',
        icon: 'ri-task-line',
        gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
    },
    'post-it': {
        title: 'Post-it',
        subtitle: 'Guida ai promemoria rapidi',
        icon: 'ri-sticky-note-line',
        gradient: 'linear-gradient(135deg, #eab308, #ca8a04)',
    },
    formazione: {
        title: 'Formazione',
        subtitle: 'Guida ai materiali formativi',
        icon: 'ri-graduation-cap-line',
        gradient: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
    },
    pazienti: {
        title: 'Pazienti',
        subtitle: 'Guida alla gestione pazienti',
        icon: 'ri-group-line',
        gradient: 'linear-gradient(135deg, #10b981, #059669)',
    },
    assegnazioni: {
        title: 'Assegnazioni',
        subtitle: 'Guida alle assegnazioni professionisti',
        icon: 'ri-user-settings-line',
        gradient: 'linear-gradient(135deg, #ec4899, #db2777)',
    },
    check: {
        title: 'Check',
        subtitle: 'Guida ai check settimanali',
        icon: 'ri-checkbox-circle-line',
        gradient: 'linear-gradient(135deg, #14b8a6, #0d9488)',
    },
    team: {
        title: 'Team',
        subtitle: 'Guida alla gestione team',
        icon: 'ri-team-line',
        gradient: 'linear-gradient(135deg, #6366f1, #4f46e5)',
    },
    professionisti: {
        title: 'Professionisti',
        subtitle: 'Guida all\'elenco professionisti',
        icon: 'ri-user-star-line',
        gradient: 'linear-gradient(135deg, #f97316, #ea580c)',
    },
    quality: {
        title: 'Quality',
        subtitle: 'Guida all\'analisi qualità',
        icon: 'ri-bar-chart-box-line',
        gradient: 'linear-gradient(135deg, #ef4444, #dc2626)',
    },
    'in-prova': {
        title: 'In Prova',
        subtitle: 'Guida alla gestione utenti in prova',
        icon: 'ri-user-follow-line',
        gradient: 'linear-gradient(135deg, #a855f7, #9333ea)',
    },
};

const SupportDetail = () => {
    const { section } = useParams();
    const navigate = useNavigate();
    const info = SECTIONS[section];

    if (!info) {
        return (
            <div className="sd-page">
                <div className="sd-header">
                    <div className="sd-header-left">
                        <button className="sd-back-btn" onClick={() => navigate('/supporto')}>
                            <i className="ri-arrow-left-line"></i>
                        </button>
                        <div>
                            <h4>Sezione non trovata</h4>
                            <p>La sezione richiesta non esiste</p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="sd-page">
            {/* Header */}
            <div className="sd-header">
                <div className="sd-header-left">
                    <button className="sd-back-btn" onClick={() => navigate('/supporto')}>
                        <i className="ri-arrow-left-line"></i>
                    </button>
                    <div className="sd-header-icon" style={{ background: info.gradient }}>
                        <i className={info.icon}></i>
                    </div>
                    <div>
                        <h4>Supporto {info.title}</h4>
                        <p>{info.subtitle}</p>
                    </div>
                </div>
            </div>

            {/* Content placeholder — da popolare sezione per sezione */}
            <div className="sd-content-card">
                <div className="sd-placeholder">
                    <div className="sd-placeholder-icon">
                        <i className={info.icon}></i>
                    </div>
                    <h5>Documentazione {info.title}</h5>
                    <p>
                        La documentazione per questa sezione è in fase di preparazione.
                        Qui troverai guide dettagliate, tutorial e FAQ.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default SupportDetail;

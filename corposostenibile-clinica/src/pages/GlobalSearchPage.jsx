import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Modal, Button } from 'react-bootstrap';
import searchService from '../services/searchService';
import './GlobalSearchPage.css';

const GlobalSearchPage = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const queryParams = new URLSearchParams(location.search);
    const initialQuery = queryParams.get('q') || '';
    
    // State
    const [query, setQuery] = useState(initialQuery);
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('all'); // all, paziente, check, professional, training
    const [page, setPage] = useState(1);
    const [pagination, setPagination] = useState({ total: 0, pages: 0 });
    const [resultCounts, setResultCounts] = useState({ all: 0, paziente: 0, check: 0, professional: 0, training: 0 });
    const [selectedResult, setSelectedResult] = useState(null);
    
    // Effect: Perform search when URL query changes
    useEffect(() => {
        const q = queryParams.get('q');
        if (q && q.length >= 2) {
            setQuery(q);
            setPage(1); // Reset page on new query
            performSearch(q, activeTab, 1);
        } else {
            setResults([]);
            setResultCounts({ all: 0, paziente: 0, check: 0, professional: 0, training: 0 });
        }
    }, [location.search]);

    // Effect: Perform search on tab or page change
    useEffect(() => {
        if (query && query.length >= 2) {
            // Se cambiamo tab da 'all' a una categoria specifica, o tra categorie, resettiamo inizialmente la pagina?
            // In realtà il reset della pagina viene già gestito nell'onClick del tab
            performSearch(query, activeTab, page);
        }
    }, [activeTab, page]);

    const performSearch = async (searchQuery, category, searchPage) => {
        setLoading(true);
        try {
            const data = await searchService.globalSearch(searchQuery, category, searchPage);
            setResults(data.results || []);
            setResultCounts(data.counts || { all: 0, paziente: 0, check: 0, professional: 0, training: 0 });
            setPagination(data.pagination || { total: 0, pages: 0 });
        } catch (error) {
            console.error('Search error:', error);
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const handleSearchSubmit = (e) => {
        e.preventDefault();
        if (query.trim().length >= 2) {
            setPage(1);
            navigate(`/ricerca-globale?q=${encodeURIComponent(query.trim())}`);
        }
    };

    const handleClear = () => {
        setQuery('');
        setResults([]);
        setPage(1);
        setPagination({ total: 0, pages: 0 });
        setResultCounts({ all: 0, paziente: 0, check: 0, professional: 0, training: 0 });
        navigate('/ricerca-globale');
    };

    const handleTabChange = (tab) => {
        setActiveTab(tab);
        setPage(1);
    };

    const handlePageChange = (newPage) => {
        setPage(newPage);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    // Grouping for "All" view (if we are in 'all' tab)
    const groupedResults = {
        paziente: results.filter(r => r.category === 'paziente'),
        check: results.filter(r => r.category === 'check'),
        professional: results.filter(r => r.category === 'professional'),
        training: results.filter(r => r.category === 'training')
    };

    const ROLE_LABELS = {
        admin: 'Admin',
        amministratore: 'Admin',
        cco: 'CCO',
        coordinatore: 'Coordinatore',
        team_leader: 'Team Leader',
        health_manager: 'Health Manager',
        professionista: 'Professionista',
        team_esterno: 'Team Esterno',
        consulente: 'Consulente',
        nutrizionista: 'Nutrizionista',
        coach: 'Coach',
        psicologo: 'Psicologo',
    };

    // Render Helpers
    const renderCard = (result) => {
        let iconClass = 'mdi mdi-magnify';
        let avatarClass = '';
        let badgeClass = '';
        let label = '';

        switch (result.type) {
            case 'paziente':
                iconClass = 'mdi mdi-account';
                avatarClass = 'avatar-paziente';
                badgeClass = 'badge-paziente';
                label = 'Paziente';
                break;
            case 'check':
                iconClass = 'mdi mdi-file-document-check';
                avatarClass = 'avatar-check';
                badgeClass = 'badge-check';
                label = 'Check';
                break;
            case 'professional': {
                iconClass = 'mdi mdi-doctor';
                avatarClass = 'avatar-professional';
                badgeClass = 'badge-professional';
                const role = result.metadata?.role;
                label = ROLE_LABELS[role] || 'Professionista';
                break;
            }
            case 'training':
                iconClass = 'mdi mdi-school';
                avatarClass = 'avatar-training';
                badgeClass = 'badge-training';
                label = 'Training';
                break;
            default:
                break;
        }

        return (
            <div
                key={`${result.type}-${result.id}`}
                className="result-card-clean"
                onClick={() => setSelectedResult(result)}
            >
                {result.avatar ? (
                    <div
                        className="result-avatar"
                        style={{ backgroundImage: `url(${result.avatar})` }}
                    />
                ) : (
                    <div className={`result-avatar ${avatarClass}`}>
                        <i className={iconClass}></i>
                    </div>
                )}

                <div className="result-info">
                    <div className="result-info-header">
                        <h4 className="result-name">{result.title}</h4>
                    </div>
                    <div className="result-meta">
                        <span>{result.subtitle}</span>
                    </div>
                </div>

                <div className="result-card-right">
                    <span className={`result-role-badge ${badgeClass}`}>{label}</span>
                    <i className="mdi mdi-chevron-right result-arrow"></i>
                </div>
            </div>
        );
    };

    const STATO_COLORS = {
        attivo: '#059669',
        ghost: '#94a3b8',
        pausa: '#f59e0b',
        stop: '#ef4444',
    };

    const renderPreviewBody = (result) => {
        if (!result) return null;
        const meta = result.metadata || {};

        switch (result.type) {
            case 'paziente':
                return (
                    <div className="preview-info-grid">
                        {meta.stato && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Stato</span>
                                <span
                                    className="preview-stato-badge"
                                    style={{
                                        background: `${STATO_COLORS[meta.stato] || '#94a3b8'}18`,
                                        color: STATO_COLORS[meta.stato] || '#94a3b8',
                                        borderColor: `${STATO_COLORS[meta.stato] || '#94a3b8'}30`,
                                    }}
                                >
                                    {meta.stato.charAt(0).toUpperCase() + meta.stato.slice(1)}
                                </span>
                            </div>
                        )}
                        {meta.tipologia && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Tipologia</span>
                                <span className="preview-info-value">{meta.tipologia}</span>
                            </div>
                        )}
                        {result.subtitle && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Contatto</span>
                                <span className="preview-info-value">{result.subtitle}</span>
                            </div>
                        )}
                    </div>
                );
            case 'professional':
                return (
                    <div className="preview-info-grid">
                        {meta.role && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Ruolo</span>
                                <span className="preview-info-value">{ROLE_LABELS[meta.role] || meta.role}</span>
                            </div>
                        )}
                        {meta.specialty && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Specialità</span>
                                <span className="preview-info-value">{meta.specialty}</span>
                            </div>
                        )}
                        {meta.email && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Email</span>
                                <span className="preview-info-value">{meta.email}</span>
                            </div>
                        )}
                    </div>
                );
            case 'check':
                return (
                    <div className="preview-info-grid">
                        {meta.patient_name && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Paziente</span>
                                <span className="preview-info-value">{meta.patient_name}</span>
                            </div>
                        )}
                        {meta.date && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Data</span>
                                <span className="preview-info-value">{meta.date}</span>
                            </div>
                        )}
                        {meta.avg_rating != null && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Voto medio</span>
                                <span className="preview-info-value preview-rating">
                                    <i className="mdi mdi-star"></i> {Number(meta.avg_rating).toFixed(1)}
                                </span>
                            </div>
                        )}
                    </div>
                );
            case 'training':
                return (
                    <div className="preview-info-grid">
                        {result.subtitle && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Dettaglio</span>
                                <span className="preview-info-value">{result.subtitle}</span>
                            </div>
                        )}
                        {meta.review_type && (
                            <div className="preview-info-row">
                                <span className="preview-info-label">Tipo review</span>
                                <span className="preview-info-value">{meta.review_type}</span>
                            </div>
                        )}
                    </div>
                );
            default:
                return result.subtitle ? (
                    <div className="preview-info-grid">
                        <div className="preview-info-row">
                            <span className="preview-info-label">Info</span>
                            <span className="preview-info-value">{result.subtitle}</span>
                        </div>
                    </div>
                ) : null;
        }
    };

    const getModalTypeInfo = (result) => {
        if (!result) return { iconClass: '', avatarClass: '', badgeClass: '', label: '' };
        switch (result.type) {
            case 'paziente':
                return { iconClass: 'mdi mdi-account', avatarClass: 'avatar-paziente', badgeClass: 'badge-paziente', label: 'Paziente' };
            case 'check':
                return { iconClass: 'mdi mdi-file-document-check', avatarClass: 'avatar-check', badgeClass: 'badge-check', label: 'Check' };
            case 'professional': {
                const role = result.metadata?.role;
                return { iconClass: 'mdi mdi-doctor', avatarClass: 'avatar-professional', badgeClass: 'badge-professional', label: ROLE_LABELS[role] || 'Professionista' };
            }
            case 'training':
                return { iconClass: 'mdi mdi-school', avatarClass: 'avatar-training', badgeClass: 'badge-training', label: 'Training' };
            default:
                return { iconClass: 'mdi mdi-magnify', avatarClass: '', badgeClass: '', label: '' };
        }
    };

    const renderSection = (title, items, icon, categoryKey) => {
        if (!items || items.length === 0) return null;
        return (
            <div className="results-section">
                <div className="section-label d-flex justify-content-between align-items-center">
                    <span>
                        <i className={icon}></i>
                        {title} ({resultCounts[categoryKey]})
                    </span>
                    {resultCounts[categoryKey] > 10 && (
                        <button 
                            className="btn btn-sm btn-link text-primary" 
                            onClick={() => handleTabChange(categoryKey)}
                        >
                            Vedi tutti <i className="mdi mdi-arrow-right"></i>
                        </button>
                    )}
                </div>
                <div className="results-grid-clean">
                    {items.map(renderCard)}
                </div>
            </div>
        );
    };

    return (
        <div className="global-search-page">
            <div className="search-header-container">
                <div className="container">
                    <div className="row justify-content-center">
                        <div className="col-lg-8">
                            <div className="search-header-title text-center">
                                <img src="/suitemind.png" alt="SUMI" className="search-header-logo" />
                                <h1>Ricerca Globale</h1>
                                <p>Cerca pazienti, check aziendali, professionisti e formazione in un unico posto</p>
                            </div>

                            <div className="search-input-area mx-auto">
                                <form onSubmit={handleSearchSubmit} className="search-input-wrapper">
                                    <i className="mdi mdi-magnify search-input-icon"></i>
                                    <input 
                                        type="text" 
                                        className="search-input-field" 
                                        placeholder="Cerca qualcuno o qualcosa..."
                                        value={query}
                                        onChange={(e) => setQuery(e.target.value)}
                                        autoFocus
                                    />
                                    {query && (
                                        <button type="button" className="search-clear-btn" onClick={handleClear}>
                                            <i className="mdi mdi-close"></i>
                                        </button>
                                    )}
                                </form>
                            </div>

                            {resultCounts.all > 0 && (
                                <div className="d-flex justify-content-center">
                                    <div className="search-nav-tabs">
                                        <button 
                                            className={`search-tab ${activeTab === 'all' ? 'active' : ''}`}
                                            onClick={() => handleTabChange('all')}
                                        >
                                            Tutti <span className="search-tab-count">{resultCounts.all}</span>
                                        </button>
                                        <button 
                                            className={`search-tab ${activeTab === 'paziente' ? 'active' : ''}`}
                                            onClick={() => handleTabChange('paziente')}
                                        >
                                            Pazienti <span className="search-tab-count">{resultCounts.paziente}</span>
                                        </button>
                                        <button 
                                            className={`search-tab ${activeTab === 'check' ? 'active' : ''}`}
                                            onClick={() => handleTabChange('check')}
                                        >
                                            Check <span className="search-tab-count">{resultCounts.check}</span>
                                        </button>
                                        <button 
                                            className={`search-tab ${activeTab === 'professional' ? 'active' : ''}`}
                                            onClick={() => handleTabChange('professional')}
                                        >
                                            Professionisti <span className="search-tab-count">{resultCounts.professional}</span>
                                        </button>
                                        <button 
                                            className={`search-tab ${activeTab === 'training' ? 'active' : ''}`}
                                            onClick={() => handleTabChange('training')}
                                        >
                                            Training <span className="search-tab-count">{resultCounts.training}</span>
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <div className="container pb-5">
                <div className="row justify-content-center">
                    <div className="col-lg-10">
                        {loading && page === 1 ? (
                            <div className="search-loading-clean">
                                <div className="spinner-clean"></div>
                                <p>Ricerca in corso...</p>
                            </div>
                        ) : results.length > 0 ? (
                            activeTab === 'all' ? (
                                <>
                                    {renderSection('Pazienti', groupedResults.paziente, 'mdi mdi-account', 'paziente')}
                                    {renderSection('Check', groupedResults.check, 'mdi mdi-file-document-check', 'check')}
                                    {renderSection('Professionisti', groupedResults.professional, 'mdi mdi-doctor', 'professional')}
                                    {renderSection('Training', groupedResults.training, 'mdi mdi-school', 'training')}
                                </>
                            ) : (
                                <>
                                    <div className="results-grid-clean">
                                        {results.map(renderCard)}
                                    </div>
                                    
                                    {/* Paginazione */}
                                    {pagination.pages > 1 && (
                                        <div className="search-pagination">
                                            <span className="search-pagination-info">
                                                Pagina <strong>{page}</strong> di <strong>{pagination.pages}</strong> — {pagination.total} risultati
                                            </span>
                                            <div className="search-pagination-buttons">
                                                <button
                                                    className="search-page-btn"
                                                    onClick={() => handlePageChange(page - 1)}
                                                    disabled={page === 1}
                                                >
                                                    <i className="mdi mdi-chevron-left"></i>
                                                </button>

                                                {[...Array(Math.min(pagination.pages, 5))].map((_, i) => {
                                                    let pageNum;
                                                    if (pagination.pages <= 5) pageNum = i + 1;
                                                    else if (page <= 3) pageNum = i + 1;
                                                    else if (page >= pagination.pages - 2) pageNum = pagination.pages - 4 + i;
                                                    else pageNum = page - 2 + i;

                                                    return (
                                                        <button
                                                            key={pageNum}
                                                            className={`search-page-btn ${page === pageNum ? 'active' : ''}`}
                                                            onClick={() => handlePageChange(pageNum)}
                                                        >
                                                            {pageNum}
                                                        </button>
                                                    );
                                                })}

                                                <button
                                                    className="search-page-btn"
                                                    onClick={() => handlePageChange(page + 1)}
                                                    disabled={page === pagination.pages}
                                                >
                                                    <i className="mdi mdi-chevron-right"></i>
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </>
                            )
                        ) : query.length >= 2 ? (
                            <div className="search-empty-clean">
                                <div className="empty-logo-wrapper">
                                    <img src="/suitemind.png" alt="SUMI" />
                                </div>
                                <h3>Nessun risultato trovato</h3>
                                <p>Non abbiamo trovato nulla che corrisponda a "{query}". Prova con un'altra parola chiave.</p>
                            </div>
                        ) : null}
                    </div>
                </div>
            </div>

            {/* Preview Modal */}
            <Modal
                show={!!selectedResult}
                onHide={() => setSelectedResult(null)}
                centered
                className="preview-modal"
            >
                {selectedResult && (() => {
                    const typeInfo = getModalTypeInfo(selectedResult);
                    return (
                        <>
                            <Modal.Header closeButton className="preview-modal-header">
                                <div className="preview-modal-title-row">
                                    {selectedResult.avatar ? (
                                        <div
                                            className="preview-avatar"
                                            style={{ backgroundImage: `url(${selectedResult.avatar})` }}
                                        />
                                    ) : (
                                        <div className={`preview-avatar ${typeInfo.avatarClass}`}>
                                            <i className={typeInfo.iconClass}></i>
                                        </div>
                                    )}
                                    <div className="preview-title-info">
                                        <h5 className="preview-title">{selectedResult.title}</h5>
                                        <span className={`result-role-badge ${typeInfo.badgeClass}`}>{typeInfo.label}</span>
                                    </div>
                                </div>
                            </Modal.Header>
                            <Modal.Body className="preview-modal-body">
                                {renderPreviewBody(selectedResult)}
                            </Modal.Body>
                            <Modal.Footer className="preview-modal-footer">
                                <Button variant="light" onClick={() => setSelectedResult(null)}>
                                    Chiudi
                                </Button>
                                <Button
                                    variant="primary"
                                    className="preview-go-btn"
                                    onClick={() => {
                                        setSelectedResult(null);
                                        navigate(selectedResult.link);
                                    }}
                                >
                                    Vai ai dettagli <i className="mdi mdi-arrow-right"></i>
                                </Button>
                            </Modal.Footer>
                        </>
                    );
                })()}
            </Modal>
        </div>
    );
};

export default GlobalSearchPage;

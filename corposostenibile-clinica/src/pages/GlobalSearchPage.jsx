import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
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
                label = 'Pazienti';
                break;
            case 'check':
                iconClass = 'mdi mdi-file-document-check';
                avatarClass = 'avatar-check';
                badgeClass = 'badge-check';
                label = 'Check';
                break;
            case 'professional':
                iconClass = 'mdi mdi-doctor';
                avatarClass = 'avatar-professional';
                badgeClass = 'badge-professional';
                label = 'Professionisti';
                break;
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
                onClick={() => navigate(result.link)}
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
                        <span className={`result-role-badge ${badgeClass}`}>{label}</span>
                    </div>
                    
                    <div className="result-meta">
                         <div className="result-meta-item">
                            <i className="mdi mdi-information-outline"></i>
                            <span>{result.subtitle}</span>
                        </div>
                    </div>
                </div>
            </div>
        );
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
                                        <div className="d-flex flex-wrap justify-content-between align-items-center mt-5 pt-3 gap-3 border-top">
                                            <span className="text-muted small">
                                                Pagina <strong>{page}</strong> di <strong>{pagination.pages}</strong>
                                                <span className="mx-2">•</span>
                                                {pagination.total} risultati
                                            </span>
                                            <nav>
                                                <ul className="pagination mb-0" style={{ gap: '4px' }}>
                                                    <li className={`page-item ${page === 1 ? 'disabled' : ''}`}>
                                                        <button 
                                                            className="page-link border-0 shadow-sm rounded-3" 
                                                            onClick={() => handlePageChange(page - 1)}
                                                            disabled={page === 1}
                                                        >
                                                            <i className="mdi mdi-chevron-left"></i>
                                                        </button>
                                                    </li>
                                                    
                                                    {[...Array(Math.min(pagination.pages, 5))].map((_, i) => {
                                                        let pageNum;
                                                        if (pagination.pages <= 5) pageNum = i + 1;
                                                        else if (page <= 3) pageNum = i + 1;
                                                        else if (page >= pagination.pages - 2) pageNum = pagination.pages - 4 + i;
                                                        else pageNum = page - 2 + i;
                                                        
                                                        const isActive = page === pageNum;
                                                        return (
                                                            <li key={pageNum} className="page-item">
                                                                <button 
                                                                    className={`page-link border-0 shadow-sm rounded-3 ${isActive ? 'bg-primary text-white' : 'bg-white text-dark'}`}
                                                                    onClick={() => handlePageChange(pageNum)}
                                                                >
                                                                    {pageNum}
                                                                </button>
                                                            </li>
                                                        );
                                                    })}

                                                    <li className={`page-item ${page === pagination.pages ? 'disabled' : ''}`}>
                                                        <button 
                                                            className="page-link border-0 shadow-sm rounded-3" 
                                                            onClick={() => handlePageChange(page + 1)}
                                                            disabled={page === pagination.pages}
                                                        >
                                                            <i className="mdi mdi-chevron-right"></i>
                                                        </button>
                                                    </li>
                                                </ul>
                                            </nav>
                                        </div>
                                    )}
                                </>
                            )
                        ) : query.length >= 2 ? (
                            <div className="search-empty-clean">
                                <div className="empty-icon-clean">
                                    <i className="mdi mdi-magnify-remove-outline"></i>
                                </div>
                                <h3>Nessun risultato trovato</h3>
                                <p>Non abbiamo trovato nulla che corrisponda a "{query}". Prova con un'altra parola chiave.</p>
                            </div>
                        ) : (
                             <div className="search-empty-clean">
                                <div className="empty-icon-clean">
                                    <i className="mdi mdi-magnify"></i>
                                </div>
                                <h3>Inizia la ricerca</h3>
                                <p>Digita il nome di un paziente, un check, un professionista o una formazione per iniziare.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default GlobalSearchPage;

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
    const [activeTab, setActiveTab] = useState('all'); // all, paziente, check, professional
    
    // Effect: Perform search when URL query changes
    useEffect(() => {
        const q = queryParams.get('q');
        if (q && q.length >= 2) {
            setQuery(q);
            performSearch(q);
        } else {
            setResults([]);
        }
    }, [location.search]);

    const performSearch = async (searchQuery) => {
        setLoading(true);
        try {
            const data = await searchService.globalSearch(searchQuery);
            setResults(data);
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
            navigate(`/ricerca-globale?q=${encodeURIComponent(query.trim())}`);
        }
    };

    const handleClear = () => {
        setQuery('');
        setResults([]);
        navigate('/ricerca-globale');
    };

    // Filtering logic based on active tab
    const filteredResults = activeTab === 'all' 
        ? results 
        : results.filter(r => r.category === activeTab);

    // Grouping for "All" view
    const groupedResults = {
        paziente: results.filter(r => r.category === 'paziente'),
        check: results.filter(r => r.category === 'check'),
        professional: results.filter(r => r.category === 'professional')
    };

    const resultCounts = {
        all: results.length,
        paziente: results.filter(r => r.category === 'paziente').length,
        check: results.filter(r => r.category === 'check').length,
        professional: results.filter(r => r.category === 'professional').length
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

    const renderSection = (title, items, icon) => {
        if (!items || items.length === 0) return null;
        return (
            <div className="results-section">
                <div className="section-label">
                    <i className={icon}></i>
                    {title} ({items.length})
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
                                <p>Cerca pazienti, check aziendali e professionisti in un unico posto</p>
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

                            {results.length > 0 && (
                                <div className="d-flex justify-content-center">
                                    <div className="search-nav-tabs">
                                        <button 
                                            className={`search-tab ${activeTab === 'all' ? 'active' : ''}`}
                                            onClick={() => setActiveTab('all')}
                                        >
                                            Tutti <span className="search-tab-count">{resultCounts.all}</span>
                                        </button>
                                        <button 
                                            className={`search-tab ${activeTab === 'paziente' ? 'active' : ''}`}
                                            onClick={() => setActiveTab('paziente')}
                                        >
                                            Pazienti <span className="search-tab-count">{resultCounts.paziente}</span>
                                        </button>
                                        <button 
                                            className={`search-tab ${activeTab === 'check' ? 'active' : ''}`}
                                            onClick={() => setActiveTab('check')}
                                        >
                                            Check <span className="search-tab-count">{resultCounts.check}</span>
                                        </button>
                                        <button 
                                            className={`search-tab ${activeTab === 'professional' ? 'active' : ''}`}
                                            onClick={() => setActiveTab('professional')}
                                        >
                                            Professionisti <span className="search-tab-count">{resultCounts.professional}</span>
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
                        {loading ? (
                            <div className="search-loading-clean">
                                <div className="spinner-clean"></div>
                                <p>Ricerca in corso...</p>
                            </div>
                        ) : results.length > 0 ? (
                            activeTab === 'all' ? (
                                <>
                                    {renderSection('Pazienti', groupedResults.paziente, 'mdi mdi-account')}
                                    {renderSection('Check', groupedResults.check, 'mdi mdi-file-document-check')}
                                    {renderSection('Professionisti', groupedResults.professional, 'mdi mdi-doctor')}
                                </>
                            ) : (
                                <div className="results-grid-clean">
                                    {filteredResults.map(renderCard)}
                                </div>
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
                                <p>Digita il nome di un paziente, un check o un professionista per iniziare.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default GlobalSearchPage;

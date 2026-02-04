import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import searchService from '../services/searchService';

import './GlobalSearch.css'; // We'll create this for specific styles

const GlobalSearch = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [showDropdown, setShowDropdown] = useState(false);
    const searchRef = useRef(null);
    const navigate = useNavigate();

    // Debounce search
    useEffect(() => {
        const delayDebounceFn = setTimeout(async () => {
            if (query.length >= 2) {
                setIsLoading(true);
                try {
                    const data = await searchService.globalSearch(query);
                    setResults(data);
                    setShowDropdown(true);
                } catch (error) {
                    console.error("Search error:", error);
                    setResults([]);
                } finally {
                    setIsLoading(false);
                }
            } else {
                setResults([]);
                setShowDropdown(false);
            }
        }, 300);

        return () => clearTimeout(delayDebounceFn);
    }, [query]);

    // Click outside to close
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (searchRef.current && !searchRef.current.contains(event.target)) {
                setShowDropdown(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelectResult = (result) => {
        setShowDropdown(false);
        setQuery(''); // Optional: clear query on selection
        if (result.link) {
            navigate(result.link);
        }
    };

    return (
        <div ref={searchRef} style={{ position: 'relative' }}>
            <div className="search_bar dropdown">
                <span className="search_icon p-3 c-pointer">
                    <i className="mdi mdi-magnify"></i>
                </span>
                <input 
                    type="text" 
                    className="form-control" 
                    placeholder="Cerca pazienti..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => {
                        if (query.length >= 2 && results.length > 0) setShowDropdown(true);
                    }}
                />
            </div>

            {showDropdown && (
                <div className="search-dropdown-menu dropdown-menu show" style={{ 
                    position: 'absolute', 
                    top: '100%', 
                    left: '0', 
                    width: '100%', 
                    minWidth: '300px',
                    maxHeight: '400px',
                    overflowY: 'auto',
                    zIndex: 1000
                }}>
                    <div className="dropdown-header">Risultati</div>
                    {isLoading ? (
                        <div className="dropdown-item text-center">Loading...</div>
                    ) : results.length > 0 ? (
                        results.map((result) => (
                            <div 
                                key={`${result.type}-${result.id}`} 
                                className="dropdown-item d-flex align-items-center c-pointer"
                                onClick={() => handleSelectResult(result)}
                            >
                                <div className="avatar-sm me-3">
                                    <div className="avatar-initials rounded-circle bg-primary text-white d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px' }}>
                                        {result.title.substring(0, 2).toUpperCase()}
                                    </div>
                                </div>
                                <div>
                                    <h6 className="mb-0">{result.title}</h6>
                                    <small className="text-muted">{result.subtitle}</small>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="dropdown-item text-muted">Nessun risultato trovato</div>
                    )}
                </div>
            )}
        </div>
    );
};

export default GlobalSearch;

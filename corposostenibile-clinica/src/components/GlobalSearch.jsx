import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../pages/GlobalSearchPage.css'; // Import shared styles

const GlobalSearch = () => {
    const [query, setQuery] = useState('');
    const navigate = useNavigate();

    const handleSearch = (e) => {
        e.preventDefault();
        if (query.trim().length >= 2) {
            navigate(`/ricerca-globale?q=${encodeURIComponent(query.trim())}`);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            handleSearch(e);
        }
    };

    return (
        <form onSubmit={handleSearch} className="header-search-bar">
            <i className="mdi mdi-magnify header-search-icon"></i>
            <input 
                type="text" 
                className="header-search-input" 
                placeholder="Ricerca globale..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
            />
        </form>
    );
};

export default GlobalSearch;

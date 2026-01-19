// Documentation Search Functionality
console.log('🚀 LOADING SEARCH SCRIPT...');
(function() {
    'use strict';
    
    // Search index
    const searchIndex = [
        { title: 'Sistema Ticket', url: '/help/doc/ticket', keywords: 'ticket supporto richieste workflow sla dashboard creazione gestione' },
        { title: 'Comunicazioni', url: '/help/doc/communications', keywords: 'comunicazioni email notifiche priorità template invio ricezione tracciamento lettura' },
        { title: 'Training e Review', url: '/help/doc/training', keywords: 'training formazione review peer feedback materiali percorsi certificazioni valutazioni' },
        { title: 'Gestione Clienti', url: '/help/doc/clienti', keywords: 'clienti gestione database programmi tracking progressi comunicazione scheda storico' },
        { title: 'Check e Feedback', url: '/help/doc/check', keywords: 'check feedback monitoraggio progressi settimanali metriche analisi alert sistema' }
    ];
    
    function performSearch(query) {
        if (!query || query.length < 2) return [];
        
        const lowerQuery = query.toLowerCase();
        const results = [];
        
        searchIndex.forEach(function(item) {
            let score = 0;
            const title = item.title.toLowerCase();
            const keywords = item.keywords.toLowerCase();
            
            // Exact match in title
            if (title.includes(lowerQuery)) score += 100;
            
            // Match in keywords
            const words = lowerQuery.split(' ');
            words.forEach(function(word) {
                if (word.length > 1) {
                    if (title.includes(word)) score += 50;
                    if (keywords.includes(word)) score += 25;
                }
            });
            
            if (score > 0) {
                results.push({
                    title: item.title,
                    url: item.url,
                    score: score
                });
            }
        });
        
        return results.sort(function(a, b) { return b.score - a.score; });
    }
    
    function showSearchResults(results, inputElement) {
        // Remove existing results
        const existing = document.querySelector('.search-results');
        if (existing) existing.remove();
        
        if (results.length === 0) return;
        
        // Create results container
        const container = document.createElement('div');
        container.className = 'search-results';
        container.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
        `;
        
        results.slice(0, 5).forEach(function(result) {
            const item = document.createElement('a');
            item.href = result.url;
            item.style.cssText = `
                display: block;
                padding: 12px;
                border-bottom: 1px solid #eee;
                text-decoration: none;
                color: #333;
                transition: background-color 0.2s;
            `;
            item.innerHTML = '<strong>' + result.title + '</strong>';
            
            item.addEventListener('mouseenter', function() {
                this.style.backgroundColor = '#f8f9fa';
            });
            item.addEventListener('mouseleave', function() {
                this.style.backgroundColor = 'white';
            });
            
            container.appendChild(item);
        });
        
        // Position container
        const parent = inputElement.closest('.search-input') || inputElement.closest('.input-group');
        if (parent) {
            parent.style.position = 'relative';
            parent.appendChild(container);
        }
    }
    
    function initializeSearch() {
        console.log('🔍 Initializing search functionality...');
        
        // Setup banner search
        const bannerSearch = document.getElementById('banner-search');
        console.log('🔍 Banner search:', bannerSearch ? 'FOUND' : 'NOT FOUND');
        if (bannerSearch) {
            console.log('Banner search found');
            let timeout;
            
            bannerSearch.addEventListener('input', function() {
                clearTimeout(timeout);
                const query = this.value;
                
                timeout = setTimeout(function() {
                    const results = performSearch(query);
                    showSearchResults(results, bannerSearch);
                }, 300);
            });
            
            bannerSearch.addEventListener('blur', function() {
                setTimeout(function() {
                    const results = document.querySelector('.search-results');
                    if (results) results.remove();
                }, 200);
            });
        } else {
            console.log('Banner search not found');
        }
        
        // Handle form submission
        const bannerForm = document.getElementById('banner-search-form');
        if (bannerForm) {
            bannerForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const query = bannerSearch.value;
                const results = performSearch(query);
                if (results.length > 0) {
                    window.location.href = results[0].url;
                }
            });
        }
        
        // Removed "/" shortcut as it was not working properly
        
        console.log('Search initialized successfully');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeSearch);
    } else {
        initializeSearch();
    }
    
    // Also initialize on window load as fallback
    window.addEventListener('load', initializeSearch);
    
})();
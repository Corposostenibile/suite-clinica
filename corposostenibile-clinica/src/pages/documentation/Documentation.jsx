import React, { useMemo } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Mapping tra le ancore logiche (docsSection) e i percorsi fisici della documentazione
 */
const SECTION_MAP = {
    'lista-pazienti': 'pazienti/lista/',
    'la-scheda-completa-del-paziente': 'pazienti/dettaglio/',
    'check-azienda': 'azienda/check_azienda/',
    'task': 'professionisti/task/',
    'formazione': 'professionisti/formazione/',
};

const Documentation = () => {
    const location = useLocation();
    
    // Calcola l'URL dell'iframe in base all'hash nell'URL del browser
    const docUrl = useMemo(() => {
        const hash = location.hash.replace('#', '');
        const baseUrl = "/documentation/static/";
        
        if (hash && SECTION_MAP[hash]) {
            return `${baseUrl}${SECTION_MAP[hash]}`;
        }
        
        // Se non c'è corrispondenza o non c'è hash, carica la root
        return baseUrl;
    }, [location.hash]);

    return (
        <div style={{ 
            width: '100%',
            height: 'calc(100vh - 210px)',
            backgroundColor: '#fff',
            borderRadius: '16px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
            overflow: 'hidden',
            border: '1px solid #f0f0f0',
            position: 'relative'
        }}>
            <iframe 
                src={docUrl} 
                title="Corposostenibile Documentation"
                style={{
                    width: '100%',
                    height: '100%',
                    border: 'none',
                    display: 'block'
                }}
            />
        </div>
    );
};

export default Documentation;

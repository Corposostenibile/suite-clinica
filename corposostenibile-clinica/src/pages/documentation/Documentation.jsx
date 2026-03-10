import React, { useContext, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import AuthContext from '../../context/AuthContext';

/**
 * Mapping tra le ancore logiche (docsSection) e i percorsi fisici della documentazione
 */
const SECTION_MAP = {
    'lista-pazienti': { path: 'pazienti/lista/', roleAnchors: { team_leader: 'team-leader', professionista: 'professionista' } },
    'la-scheda-completa-del-paziente': { path: 'pazienti/dettaglio/', roleAnchors: { team_leader: 'team-leader', professionista: 'professionista' } },
    'check-azienda': { path: 'azienda/check_azienda/', roleAnchors: { team_leader: 'team-leader', professionista: 'professionista' } },
    'task': { path: 'professionisti/task/', roleAnchors: { team_leader: 'team-leader', professionista: 'professionista' } },
    'formazione': { path: 'professionisti/formazione/', roleAnchors: { team_leader: 'team-leader', professionista: 'professionista' } },
};

const Documentation = () => {
    const location = useLocation();
    const auth = useContext(AuthContext);
    const currentUser = auth?.user || null;
    
    // Calcola l'URL dell'iframe in base all'hash nell'URL del browser
    const docUrl = useMemo(() => {
        const hash = location.hash.replace('#', '');
        const params = new URLSearchParams(location.search || '');
        const explicitAudience = params.get('audience');
        const isAdminOrCco = Boolean(
            currentUser?.is_admin === true ||
            currentUser?.role === 'admin' ||
            String(currentUser?.specialty || '').toLowerCase() === 'cco'
        );
        const inferredAudience = (currentUser?.role === 'team_leader' && !isAdminOrCco)
            ? 'team_leader'
            : 'professionista';
        const audience = explicitAudience === 'team_leader' || explicitAudience === 'professionista'
            ? explicitAudience
            : inferredAudience;
        // Passiamo da /api così il reverse proxy inoltra sempre al backend (evita iframe con SPA dentro).
        const baseUrl = "/api/documentation/static/";
        
        if (hash && SECTION_MAP[hash]) {
            const entry = SECTION_MAP[hash];
            const anchor = entry.roleAnchors?.[audience];
            return `${baseUrl}${entry.path}${anchor ? `#${anchor}` : ''}`;
        }
        
        // Se non c'è corrispondenza o non c'è hash, carica la root
        return baseUrl;
    }, [location.hash, location.search, currentUser]);

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

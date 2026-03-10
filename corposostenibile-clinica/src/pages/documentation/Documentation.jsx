import React, { useContext, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import AuthContext from '../../context/AuthContext';
import './Documentation.css';

const GUIDE_GROUPS = [
    {
        id: 'pazienti',
        label: 'Pazienti',
        items: [
            {
                key: 'lista-pazienti',
                label: 'Lista Pazienti',
                path: 'pazienti/lista/',
                roleAnchors: { team_leader: 'team-leader', professionista: 'professionista' },
                descriptions: {
                    team_leader: 'Monitora carico, scadenze e pazienti che richiedono coordinamento del team.',
                    professionista: 'Gestisci il tuo portafoglio pazienti, i filtri e le azioni operative rapide.',
                },
            },
            {
                key: 'la-scheda-completa-del-paziente',
                label: 'Scheda Completa Paziente',
                path: 'pazienti/dettaglio/',
                roleAnchors: { team_leader: 'team-leader', professionista: 'professionista' },
                descriptions: {
                    team_leader: 'Usa la scheda per sbloccare decisioni, pause, rinnovi e priorita del paziente.',
                    professionista: 'Aggiorna stato, prossime azioni, diario e materiali del paziente senza perdere contesto.',
                },
            },
        ],
    },
    {
        id: 'operativita',
        label: 'Operativita',
        items: [
            {
                key: 'task',
                label: 'Task',
                path: 'professionisti/task/',
                roleAnchors: { team_leader: 'team-leader', professionista: 'professionista' },
                descriptions: {
                    team_leader: 'Controlla task in stallo, carico team e attivita scadute prima di intervenire.',
                    professionista: 'Completa, filtra e apri subito le attivita collegate ai pazienti.',
                },
            },
            {
                key: 'formazione',
                label: 'Formazione',
                path: 'professionisti/formazione/',
                roleAnchors: { team_leader: 'team-leader', professionista: 'professionista' },
                descriptions: {
                    team_leader: 'Usa training e richieste per distribuire competenze e allineare il team.',
                    professionista: 'Consulta training ricevuti e richiedi supporto formativo su casi reali.',
                },
            },
            {
                key: 'check-azienda',
                label: 'Check Azienda',
                path: 'azienda/check_azienda/',
                roleAnchors: { team_leader: 'team-leader', professionista: 'professionista' },
                descriptions: {
                    team_leader: 'Leggi KPI, feedback e qualita del team per identificare dove intervenire.',
                    professionista: 'Consulta risultati, feedback e aree di miglioramento del tuo lavoro.',
                },
            },
        ],
    },
];

const DEFAULT_GUIDE_BY_AUDIENCE = {
    team_leader: 'lista-pazienti',
    professionista: 'task',
};

function Documentation() {
    const location = useLocation();
    const navigate = useNavigate();
    const auth = useContext(AuthContext);
    const currentUser = auth?.user || null;

    const isAdminOrCco = Boolean(
        currentUser?.is_admin === true ||
        currentUser?.role === 'admin' ||
        String(currentUser?.specialty || '').toLowerCase() === 'cco'
    );

    const inferredAudience = (currentUser?.role === 'team_leader' && !isAdminOrCco)
        ? 'team_leader'
        : 'professionista';

    const searchParams = useMemo(() => new URLSearchParams(location.search || ''), [location.search]);
    const requestedAudience = searchParams.get('audience');
    const audience = (requestedAudience === 'team_leader' || requestedAudience === 'professionista')
        ? requestedAudience
        : inferredAudience;

    const allGuides = useMemo(
        () => GUIDE_GROUPS.flatMap((group) => group.items.map((item) => ({ ...item, groupId: group.id, groupLabel: group.label }))),
        []
    );

    const activeGuideKey = useMemo(() => {
        const hashKey = location.hash.replace('#', '');
        if (allGuides.some((guide) => guide.key === hashKey)) {
            return hashKey;
        }
        return DEFAULT_GUIDE_BY_AUDIENCE[audience];
    }, [location.hash, allGuides, audience]);

    const activeGuide = allGuides.find((guide) => guide.key === activeGuideKey) || allGuides[0];
    const iframeUrl = `/api/documentation/static/${activeGuide.path}${activeGuide.roleAnchors?.[audience] ? `#${activeGuide.roleAnchors[audience]}` : ''}`;

    const roleCopy = audience === 'team_leader'
        ? {
            eyebrow: 'Percorso Team Leader',
            title: 'Guide per coordinare il team e sbloccare i casi in stallo.',
            body: 'La selezione privilegia monitoraggio, priorita operative, qualita e supporto ai professionisti.',
        }
        : {
            eyebrow: 'Percorso Professionista',
            title: 'Guide operative per lavorare veloce sui tuoi pazienti.',
            body: 'La selezione privilegia esecuzione quotidiana, aggiornamento stati, task e richieste di formazione.',
        };

    const setAudience = (nextAudience) => {
        const params = new URLSearchParams(location.search || '');
        params.set('audience', nextAudience);
        navigate({
            pathname: location.pathname,
            search: `?${params.toString()}`,
            hash: `#${activeGuideKey}`,
        });
    };

    const openGuide = (guideKey) => {
        navigate({
            pathname: location.pathname,
            search: `?${searchParams.toString()}`,
            hash: `#${guideKey}`,
        });
    };

    return (
        <div className="docs-shell">
            <aside className="docs-sidebar">
                <div className="docs-hero">
                    <span className="docs-eyebrow">{roleCopy.eyebrow}</span>
                    <h1>{roleCopy.title}</h1>
                    <p>{roleCopy.body}</p>
                </div>

                {isAdminOrCco && (
                    <div className="docs-audience-switch">
                        <button
                            type="button"
                            className={audience === 'team_leader' ? 'active' : ''}
                            onClick={() => setAudience('team_leader')}
                        >
                            Team Leader
                        </button>
                        <button
                            type="button"
                            className={audience === 'professionista' ? 'active' : ''}
                            onClick={() => setAudience('professionista')}
                        >
                            Professionista
                        </button>
                    </div>
                )}

                <div className="docs-groups">
                    {GUIDE_GROUPS.map((group) => (
                        <section key={group.id} className="docs-group">
                            <div className="docs-group-label">{group.label}</div>
                            <div className="docs-guide-list">
                                {group.items.map((guide) => (
                                    <button
                                        key={guide.key}
                                        type="button"
                                        className={`docs-guide-card${activeGuideKey === guide.key ? ' active' : ''}`}
                                        onClick={() => openGuide(guide.key)}
                                    >
                                        <span className="docs-guide-title">{guide.label}</span>
                                        <span className="docs-guide-description">
                                            {guide.descriptions[audience]}
                                        </span>
                                    </button>
                                ))}
                            </div>
                        </section>
                    ))}
                </div>
            </aside>

            <section className="docs-viewer">
                <div className="docs-viewer-header">
                    <div>
                        <span className="docs-viewer-kicker">{activeGuide.groupLabel}</span>
                        <h2>{activeGuide.label}</h2>
                    </div>
                    <p>{activeGuide.descriptions[audience]}</p>
                </div>

                <div className="docs-iframe-frame">
                    <iframe
                        src={iframeUrl}
                        title={`Documentazione ${activeGuide.label}`}
                        className="docs-iframe"
                    />
                </div>
            </section>
        </div>
    );
}

export default Documentation;

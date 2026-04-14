import React, { useMemo, useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '../../context/AuthContext';
import logoFoglia from '../../images/logo_mini.png';
import {
  DOCUMENTATION_SPECIALTY_OPTIONS,
  getRequestedSpecialty,
  getTourContext,
} from '../../utils/tourScope';
import './Documentation.css';

/* ─── Icons mapping ──────────────────────────────────────────────── */

const ICON_MAP = {
  'ri-book-3-line': 'ri-book-3-line',
  'ri-group-line': 'ri-group-line',
  'ri-settings-4-line': 'ri-settings-4-line',
  'ri-book-open-line': 'ri-book-open-line',
  'ri-org-chart': 'ri-org-chart',
  'ri-user-heart-line': 'ri-user-heart-line',
  'ri-tools-line': 'ri-tools-line',
  'ri-message-3-line': 'ri-message-3-line',
  'ri-user-guide-line': 'ri-user-guide-line',
  'ri-server-line': 'ri-server-line',
  'ri-admin-line': 'ri-admin-line',
  'ri-code-s-slash-line': 'ri-code-s-slash-line',
};

/* ─── API ──────────────────────────────────────────────────────── */

async function fetchDocNavigation() {
  const res = await fetch('/api/documentation/nav');
  if (!res.ok) throw new Error('Failed to fetch navigation');
  const json = await res.json();
  return json.data;
}

/* ─── Variants resolver per guide legacy (pazienti, professionisti) ─── */

const VARIANT_GUIDES = {
  'lista-pazienti': {
    variants: {
      team_leader: {
        all: 'pazienti/lista_team_leader/',
        nutrizione: 'pazienti/lista_team_leader_nutrizione/',
        coaching: 'pazienti/lista_team_leader_coaching/',
        psicologia: 'pazienti/lista_team_leader_psicologia/',
      },
      professionista: {
        all: 'pazienti/lista_professionista/',
        nutrizione: 'pazienti/lista_professionista_nutrizione/',
        coaching: 'pazienti/lista_professionista_coaching/',
        psicologia: 'pazienti/lista_professionista_psicologia/',
      },
    },
    descriptions: {
      team_leader: {
        all: 'Monitora carico, scadenze e pazienti che richiedono coordinamento del team.',
        nutrizione: 'Monitora il carico pazienti e i segnali di criticita nella nutrizione.',
        coaching: 'Monitora il carico pazienti e i segnali di criticita nel coaching.',
        psicologia: 'Monitora il carico pazienti e i segnali di criticita nella psicologia.',
      },
      professionista: {
        all: 'Gestisci il tuo portafoglio pazienti, i filtri e le azioni rapide.',
        nutrizione: 'Organizza i pazienti seguiti in nutrizione.',
        coaching: 'Organizza i pazienti seguiti nel coaching.',
        psicologia: 'Organizza i pazienti seguiti in psicologia.',
      },
    },
  },
  'la-scheda-completa-del-paziente': {
    variants: {
      team_leader: {
        all: 'pazienti/dettaglio_team_leader/',
        nutrizione: 'pazienti/dettaglio_team_leader_nutrizione/',
        coaching: 'pazienti/dettaglio_team_leader_coaching/',
        psicologia: 'pazienti/dettaglio_team_leader_psicologia/',
      },
      professionista: {
        all: 'pazienti/dettaglio_professionista/',
        nutrizione: 'pazienti/dettaglio_professionista_nutrizione/',
        coaching: 'pazienti/dettaglio_professionista_coaching/',
        psicologia: 'pazienti/dettaglio_professionista_psicologia/',
      },
    },
    descriptions: {
      team_leader: {
        all: 'Usa la scheda per sbloccare decisioni, pause, rinnovi e priorita.',
        nutrizione: 'Supervisiona stato, materiali e continuita operativa nutrizione.',
        coaching: 'Supervisiona stato, materiali e continuita operativa coaching.',
        psicologia: 'Supervisiona stato, alert e continuita operativa psicologia.',
      },
      professionista: {
        all: 'Aggiorna stato, prossime azioni, diario e materiali.',
        nutrizione: 'Lavora la scheda con focus nutrizione.',
        coaching: 'Lavora la scheda con focus coaching.',
        psicologia: 'Lavora la scheda con focus psicologia.',
      },
    },
  },
  task: {
    variants: {
      team_leader: {
        all: 'professionisti/task_team_leader/',
        nutrizione: 'professionisti/task_team_leader_nutrizione/',
        coaching: 'professionisti/task_team_leader_coaching/',
        psicologia: 'professionisti/task_team_leader_psicologia/',
      },
      professionista: {
        all: 'professionisti/task_professionista/',
        nutrizione: 'professionisti/task_professionista_nutrizione/',
        coaching: 'professionisti/task_professionista_coaching/',
        psicologia: 'professionisti/task_professionista_psicologia/',
      },
    },
    descriptions: {
      team_leader: {
        all: 'Controlla task in stallo, carico team e attivita scadute.',
        nutrizione: 'Controlla il backlog della nutrizione.',
        coaching: 'Controlla il backlog del coaching.',
        psicologia: 'Controlla il backlog della psicologia.',
      },
      professionista: {
        all: 'Completa, filtra e apri subito le attivita collegate ai pazienti.',
        nutrizione: 'Completa e filtra i task in nutrizione.',
        coaching: 'Completa e filtra i task nel coaching.',
        psicologia: 'Completa e filtra i task in psicologia.',
      },
    },
  },
  formazione: {
    variants: {
      team_leader: {
        all: 'professionisti/formazione_team_leader/',
        nutrizione: 'professionisti/formazione_team_leader_nutrizione/',
        coaching: 'professionisti/formazione_team_leader_coaching/',
        psicologia: 'professionisti/formazione_team_leader_psicologia/',
      },
      professionista: {
        all: 'professionisti/formazione_professionista/',
        nutrizione: 'professionisti/formazione_professionista_nutrizione/',
        coaching: 'professionisti/formazione_professionista_coaching/',
        psicologia: 'professionisti/formazione_professionista_psicologia/',
      },
    },
    descriptions: {
      team_leader: {
        all: 'Usa training e richieste per distribuire competenze.',
        nutrizione: 'Allinea la nutrizione su casi e standard.',
        coaching: 'Allinea il coaching su casi e standard.',
        psicologia: 'Allinea la psicologia su casi e standard.',
      },
      professionista: {
        all: 'Consulta training ricevuti e richiedi supporto.',
        nutrizione: 'Training utili al lavoro nutrizionale.',
        coaching: 'Training utili al lavoro di coaching.',
        psicologia: 'Training utili al lavoro psicologico.',
      },
    },
  },
  'check-azienda': {
    variants: {
      team_leader: {
        all: 'azienda/check_azienda_team_leader/',
        nutrizione: 'azienda/check_azienda_team_leader_nutrizione/',
        coaching: 'azienda/check_azienda_team_leader_coaching/',
        psicologia: 'azienda/check_azienda_team_leader_psicologia/',
      },
      professionista: {
        all: 'azienda/check_azienda_professionista/',
        nutrizione: 'azienda/check_azienda_professionista_nutrizione/',
        coaching: 'azienda/check_azienda_professionista_coaching/',
        psicologia: 'azienda/check_azienda_professionista_psicologia/',
      },
    },
    descriptions: {
      team_leader: {
        all: 'Leggi KPI, feedback e qualita del team.',
        nutrizione: 'Leggi KPI e feedback della nutrizione.',
        coaching: 'Leggi KPI e feedback del coaching.',
        psicologia: 'Leggi KPI e feedback della psicologia.',
      },
      professionista: {
        all: 'Consulta risultati, feedback e aree di miglioramento.',
        nutrizione: 'KPI e feedback per il lavoro in nutrizione.',
        coaching: 'KPI e feedback per il lavoro nel coaching.',
        psicologia: 'KPI e feedback per il lavoro in psicologia.',
      },
    },
  },
};

const DEFAULT_GUIDE_BY_AUDIENCE = {
  team_leader: 'lista-pazienti',
  professionista: 'task',
};

const SPECIALTY_OPTIONS = DOCUMENTATION_SPECIALTY_OPTIONS.filter((option) =>
  ['all', 'nutrizione', 'coaching', 'psicologia'].includes(option.key)
);

/* ─── Inner component ───────────────────────────────────────────────── */

function DocumentationInner() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user: currentUser, loading } = useAuth();
  const [navConfig, setNavConfig] = useState([]);
  const [navLoading, setNavLoading] = useState(true);
  const [navError, setNavError] = useState(null);

  // Carica navigazione da API
  useEffect(() => {
    let mounted = true;
    async function loadNav() {
      try {
        const data = await fetchDocNavigation();
        if (mounted) {
          setNavConfig(data);
          setNavError(null);
        }
      } catch (err) {
        if (mounted) {
          setNavError(err.message);
          console.error('[Docs] Failed to load navigation:', err);
        }
      } finally {
        if (mounted) setNavLoading(false);
      }
    }
    loadNav();
    return () => { mounted = false; };
  }, []);

  const searchParams = useMemo(() => new URLSearchParams(location.search || ''), [location.search]);
  const requestedAudience = searchParams.get('audience');
  const requestedSpecialty = getRequestedSpecialty(searchParams);

  const {
    isAdminOrCco,
    isRestrictedTeamLeader,
    isProfessionista,
    specialtyKey: userSpecialtyKey,
    audience,
  } = getTourContext(currentUser, requestedAudience);

  const canSwitchAudience = isAdminOrCco;
  const specialtyLocked = Boolean(!isAdminOrCco && (isRestrictedTeamLeader || isProfessionista) && userSpecialtyKey);
  const specialty = specialtyLocked
    ? userSpecialtyKey
    : (requestedSpecialty || 'all');

  // Costruisci lista guide dalla config API
  const allGuides = useMemo(() => {
    const guides = [];
    
    for (const group of navConfig) {
      if (!group.items) continue;
      
      for (const item of group.items) {
        const variantData = VARIANT_GUIDES[item.key];
        
        guides.push({
          key: item.key,
          label: item.label,
          icon: item.icon || 'ri-file-text-line',
          groupId: group.key,
          groupLabel: group.label,
          // Static path (dalla API)
          staticPath: item.path,
          // Variant data (se presente)
          hasVariants: !!variantData,
          variantConfig: variantData,
        });
      }
    }
    return guides;
  }, [navConfig]);

  const hashKey = location.hash.replace('#', '');
  const activeGuideKey = allGuides.some((guide) => guide.key === hashKey)
    ? hashKey
    : DEFAULT_GUIDE_BY_AUDIENCE[audience];

  const activeGuide = allGuides.find((guide) => guide.key === activeGuideKey) || allGuides[0];
  const activeSpecialtyOption = SPECIALTY_OPTIONS.find((option) => option.key === specialty) || SPECIALTY_OPTIONS[0];

  const resolveVariantPath = (guide, guideAudience, guideSpecialty) => {
    if (!guide.variantConfig) return '';
    const audienceVariants = guide.variantConfig.variants?.[guideAudience] 
      || guide.variantConfig.variants?.professionista || {};
    return audienceVariants[guideSpecialty] || audienceVariants.all || '';
  };

  const resolveGuideDescription = (guide, guideAudience, guideSpecialty) => {
    if (!guide.variantConfig) return guide.label;
    const audienceDescriptions = guide.variantConfig.descriptions?.[guideAudience] 
      || guide.variantConfig.descriptions?.professionista || {};
    return audienceDescriptions[guideSpecialty] || audienceDescriptions.all || guide.label;
  };

  const iframeUrl = useMemo(() => {
    if (!activeGuide) return '';
    if (activeGuide.staticPath) {
      return `/api/documentation/static/${activeGuide.staticPath}`;
    }
    return `/api/documentation/static/${resolveVariantPath(activeGuide, audience, specialty)}`;
  }, [activeGuide, audience, specialty]);

  const updateRoute = (nextAudience, nextSpecialty, nextGuideKey = activeGuideKey) => {
    const params = new URLSearchParams(location.search || '');
    params.set('audience', nextAudience);
    params.set('specialty', nextSpecialty);
    navigate({
      pathname: location.pathname,
      search: `?${params.toString()}`,
      hash: `#${nextGuideKey}`,
    });
  };

  const setAudience = (nextAudience) => {
    const nextSpecialty = specialtyLocked ? (userSpecialtyKey || 'all') : specialty;
    updateRoute(nextAudience, nextSpecialty);
  };

  const setSpecialty = (nextSpecialty) => {
    updateRoute(audience, nextSpecialty);
  };

  const openGuide = (guideKey) => {
    updateRoute(audience, specialty, guideKey);
  };

  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleGuideClick = (guideKey) => {
    openGuide(guideKey);
    setDrawerOpen(false);
  };

  if (loading || navLoading) {
    return (
      <div className="dc-loading">
        <div className="dc-loading-ring"><div /><div /><div /></div>
      </div>
    );
  }

  if (navError) {
    return (
      <div className="dc-loading">
        <div style={{ color: '#dc2626', textAlign: 'center', padding: '2rem' }}>
          <p>Errore caricamento navigazione: {navError}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dc">
      {/* ═══ Sidebar ═══ */}
      <aside className={`dc-side${drawerOpen ? ' dc-side--open' : ''}`}>
        {/* Brand header */}
        <div className="dc-side-brand">
          <img src={logoFoglia} alt="Corposostenibile" className="dc-brand-leaf" />
          <div className="dc-brand-info">
            <span className="dc-brand-title">Suite Clinica</span>
            <span className="dc-brand-subtitle">Documentazione</span>
          </div>
        </div>

        {/* Back to app */}
        <div className="dc-side-back-wrap">
          <button className="dc-back" onClick={() => navigate('/welcome')}>
            <i className="ri-arrow-left-s-line" />
            <span>Torna alla Suite</span>
          </button>
        </div>

        {/* Controls */}
        <div className="dc-side-controls">
          {canSwitchAudience && (
            <div className="dc-field">
              <label className="dc-label">Visualizza come</label>
              <div className="dc-seg">
                <button
                  type="button"
                  className={audience === 'team_leader' ? 'on' : ''}
                  onClick={() => setAudience('team_leader')}
                >
                  <i className="ri-shield-user-line" />
                  Team Leader
                </button>
                <button
                  type="button"
                  className={audience === 'professionista' ? 'on' : ''}
                  onClick={() => setAudience('professionista')}
                >
                  <i className="ri-user-heart-line" />
                  Professionista
                </button>
              </div>
            </div>
          )}

          <div className="dc-field">
            <label className="dc-label">Specializzazione</label>
            {specialtyLocked ? (
              <div className="dc-lock">
                <i className="ri-lock-2-line" />
                <span>{activeSpecialtyOption.label}</span>
              </div>
            ) : (
              <div className="dc-chips">
                {SPECIALTY_OPTIONS.map((opt) => (
                  <button
                    key={opt.key}
                    type="button"
                    className={specialty === opt.key ? 'on' : ''}
                    onClick={() => setSpecialty(opt.key)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Guide navigation */}
        <nav className="dc-nav">
          {navConfig.map((group) => (
            <div key={group.key} className="dc-nav-section">
              <div className="dc-nav-heading">
                <i className={group.icon || 'ri-file-text-line'} />
                <span>{group.label}</span>
                <span className="dc-nav-heading-count">{group.items?.length || 0}</span>
              </div>

              {group.items?.map((guide) => {
                const active = activeGuideKey === guide.key;
                return (
                  <button
                    key={guide.key}
                    type="button"
                    className={`dc-nav-link${active ? ' dc-nav-link--on' : ''}`}
                    onClick={() => handleGuideClick(guide.key)}
                  >
                    {active && <div className="dc-nav-link-bar" />}
                    <i className={guide.icon || 'ri-file-text-line'} />
                    <div className="dc-nav-link-text">
                      <strong>{guide.label}</strong>
                      <span>{resolveGuideDescription(
                        { key: guide.key, variantConfig: VARIANT_GUIDES[guide.key] },
                        audience,
                        specialty
                      )}</span>
                    </div>
                    {active && <i className="ri-arrow-right-s-line dc-nav-link-arrow" />}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="dc-side-footer">
          <span>Suite Clinica v2.0</span>
        </div>
      </aside>

      {/* ═══ Mobile bar ═══ */}
      <div className="dc-mbar">
        <button className="dc-mbar-btn" onClick={() => navigate('/welcome')}>
          <i className="ri-arrow-left-line" />
        </button>
        <div className="dc-mbar-center">
          <div className="dc-mbar-mark"><i className="ri-book-3-line" /></div>
          <span>{activeGuide?.label || 'Documentazione'}</span>
        </div>
        <button className="dc-mbar-btn" onClick={() => setDrawerOpen(!drawerOpen)}>
          <i className={drawerOpen ? 'ri-close-line' : 'ri-menu-3-line'} />
        </button>
      </div>

      {/* ═══ Overlay ═══ */}
      {drawerOpen && <div className="dc-overlay" onClick={() => setDrawerOpen(false)} />}

      {/* ═══ Main ═══ */}
      <main className="dc-main">
        <header className="dc-header">
          <div className="dc-header-left">
            <div className="dc-header-breadcrumb">
              <span className="dc-header-crumb">{activeGuide?.groupLabel || ''}</span>
              <i className="ri-arrow-right-s-line" />
              <span className="dc-header-crumb">{activeGuide?.label || ''}</span>
            </div>
            <div className="dc-header-meta">
              <span className="dc-header-badge">
                <i className={audience === 'team_leader' ? 'ri-shield-user-line' : 'ri-user-heart-line'} />
                {audience === 'team_leader' ? 'Team Leader' : 'Professionista'}
              </span>
              {specialty !== 'all' && (
                <span className="dc-header-badge dc-header-badge--spec">
                  {activeSpecialtyOption.label}
                </span>
              )}
            </div>
          </div>
          <p className="dc-header-desc">
            {activeGuide ? resolveGuideDescription(
              { key: activeGuide.key, variantConfig: VARIANT_GUIDES[activeGuide.key] },
              audience,
              specialty
            ) : ''}
          </p>
        </header>

        <div className="dc-frame">
          <iframe
            src={iframeUrl}
            title={`Documentazione ${activeGuide?.label || ''}`}
          />
        </div>
      </main>
    </div>
  );
}

/* ─── Wrapper ───────────────────────────────────────────────────────── */

function Documentation() {
  return (
    <AuthProvider>
      <DocumentationInner />
    </AuthProvider>
  );
}

export default Documentation;

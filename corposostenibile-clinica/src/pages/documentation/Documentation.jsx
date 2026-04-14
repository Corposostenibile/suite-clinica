import React, { useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '../../context/AuthContext';
import logoFoglia from '../../images/logo_mini.png';
import {
  DOCUMENTATION_SPECIALTY_OPTIONS,
  getRequestedSpecialty,
  getTourContext,
} from '../../utils/tourScope';
import './Documentation.css';

/* ─── Data ───────────────────────────────────────────────────────── */

// Guide con path fisso (senza varianti ruolo/specialty)
const STATIC_GUIDES = {
  panoramica: {
    label: 'Panoramica',
    icon: 'ri-book-open-line',
    path: 'panoramica/overview/',
    description: 'Panoramica generale del progetto e template documentazione.',
  },
  team: {
    label: 'Team e Organizzazione',
    icon: 'ri-org-chart',
    path: 'team/team-professionisti/',
    description: 'Autenticazione, team professionisti, KPI e performance.',
  },
  'clienti-core': {
    label: 'Clienti Core',
    icon: 'ri-user-heart-line',
    path: 'clienti-core/gestione-clienti/',
    description: 'Gestione clienti, check periodici, nutrizione, diario.',
  },
  strumenti: {
    label: 'Strumenti Operativi',
    icon: 'ri-tools-line',
    path: 'strumenti/task-calendario/',
    description: 'Task, calendario, ticket, chat, ricerca.',
  },
  comunicazione: {
    label: 'Comunicazione',
    icon: 'ri-message-3-line',
    path: 'comunicazione/README/',
    description: 'GHL, respond.io, notifiche, chatbot.',
  },
  'guide-ruoli': {
    label: 'Guide Ruoli',
    icon: 'ri-user-guide-line',
    path: 'guide-ruoli/overview/',
    description: 'Guide operative per Coach, Nutrizionista, Psicologo.',
  },
  infrastruttura: {
    label: 'Infrastruttura',
    icon: 'ri-server-line',
    path: 'infrastruttura/ci_cd_analysis/',
    description: 'CI/CD, GCP, migrazione. Solo admin.',
    adminOnly: true,
  },
  sviluppo: {
    label: 'Sviluppo',
    icon: 'ri-code-s-slash-line',
    path: 'sviluppo/refactor_status_report/',
    description: 'Refactor, piani sviluppo. Solo admin.',
    adminOnly: true,
  },
};

// Guide con varianti ruolo/specialty
const createGuideVariants = (basePath) => ({
  team_leader: {
    all: `${basePath}_team_leader/`,
    nutrizione: `${basePath}_team_leader_nutrizione/`,
    coaching: `${basePath}_team_leader_coaching/`,
    psicologia: `${basePath}_team_leader_psicologia/`,
  },
  professionista: {
    all: `${basePath}_professionista/`,
    nutrizione: `${basePath}_professionista_nutrizione/`,
    coaching: `${basePath}_professionista_coaching/`,
    psicologia: `${basePath}_professionista_psicologia/`,
  },
});

const GUIDE_GROUPS = [
  {
    id: 'pazienti',
    label: 'Pazienti',
    icon: 'ri-group-line',
    items: [
      {
        key: 'lista-pazienti',
        label: 'Lista Pazienti',
        icon: 'ri-list-check-2',
        variants: createGuideVariants('pazienti/lista'),
        descriptions: {
          team_leader: {
            all: 'Monitora carico, scadenze e pazienti che richiedono coordinamento del team.',
            nutrizione: 'Monitora il carico pazienti e i segnali di criticita nella nutrizione.',
            coaching: 'Monitora il carico pazienti e i segnali di criticita nel coaching.',
            psicologia: 'Monitora il carico pazienti e i segnali di criticita nella psicologia.',
          },
          professionista: {
            all: 'Gestisci il tuo portafoglio pazienti, i filtri e le azioni operative rapide.',
            nutrizione: 'Organizza i pazienti seguiti in nutrizione e arriva subito ai casi da lavorare.',
            coaching: 'Organizza i pazienti seguiti nel coaching e arriva subito ai casi da lavorare.',
            psicologia: 'Organizza i pazienti seguiti in psicologia e arriva subito ai casi da lavorare.',
          },
        },
      },
      {
        key: 'la-scheda-completa-del-paziente',
        label: 'Scheda Completa Paziente',
        icon: 'ri-file-user-line',
        variants: createGuideVariants('pazienti/dettaglio'),
        descriptions: {
          team_leader: {
            all: 'Usa la scheda per sbloccare decisioni, pause, rinnovi e priorita del paziente.',
            nutrizione: 'Supervisiona stato, materiali e continuita operativa della nutrizione.',
            coaching: 'Supervisiona stato, materiali e continuita operativa del coaching.',
            psicologia: 'Supervisiona stato, alert e continuita operativa della psicologia.',
          },
          professionista: {
            all: 'Aggiorna stato, prossime azioni, diario e materiali del paziente senza perdere contesto.',
            nutrizione: 'Lavora la scheda paziente con focus su setup, piano, diario e alert nutrizione.',
            coaching: 'Lavora la scheda paziente con focus su setup, schede, diario e alert coaching.',
            psicologia: 'Lavora la scheda paziente con focus su setup, diario e alert psicologia.',
          },
        },
      },
    ],
  },
  {
    id: 'operativita',
    label: 'Operativita',
    icon: 'ri-settings-4-line',
    items: [
      {
        key: 'task',
        label: 'Task',
        icon: 'ri-task-line',
        variants: createGuideVariants('professionisti/task'),
        descriptions: {
          team_leader: {
            all: 'Controlla task in stallo, carico team e attivita scadute prima di intervenire.',
            nutrizione: 'Controlla il backlog della nutrizione e i task che stanno rallentando il reparto.',
            coaching: 'Controlla il backlog del coaching e i task che stanno rallentando il reparto.',
            psicologia: 'Controlla il backlog della psicologia e i task che stanno rallentando il reparto.',
          },
          professionista: {
            all: 'Completa, filtra e apri subito le attivita collegate ai pazienti.',
            nutrizione: 'Completa e filtra i task collegati al tuo lavoro in nutrizione.',
            coaching: 'Completa e filtra i task collegati al tuo lavoro nel coaching.',
            psicologia: 'Completa e filtra i task collegati al tuo lavoro in psicologia.',
          },
        },
      },
      {
        key: 'formazione',
        label: 'Formazione',
        icon: 'ri-graduation-cap-line',
        variants: createGuideVariants('professionisti/formazione'),
        descriptions: {
          team_leader: {
            all: 'Usa training e richieste per distribuire competenze e allineare il team.',
            nutrizione: 'Usa training e richieste per allineare la nutrizione su casi, standard e feedback.',
            coaching: 'Usa training e richieste per allineare il coaching su casi, standard e feedback.',
            psicologia: 'Usa training e richieste per allineare la psicologia su casi, standard e feedback.',
          },
          professionista: {
            all: 'Consulta training ricevuti e richiedi supporto formativo su casi reali.',
            nutrizione: 'Consulta training utili al lavoro nutrizionale e richiedi supporto mirato.',
            coaching: 'Consulta training utili al lavoro di coaching e richiedi supporto mirato.',
            psicologia: 'Consulta training utili al lavoro psicologico e richiedi supporto mirato.',
          },
        },
      },
      {
        key: 'check-azienda',
        label: 'Check Azienda',
        icon: 'ri-checkbox-circle-line',
        variants: createGuideVariants('azienda/check_azienda'),
        descriptions: {
          team_leader: {
            all: 'Leggi KPI, feedback e qualita del team per identificare dove intervenire.',
            nutrizione: 'Leggi KPI e feedback della nutrizione per capire dove intervenire come TL.',
            coaching: 'Leggi KPI e feedback del coaching per capire dove intervenire come TL.',
            psicologia: 'Leggi KPI e feedback della psicologia per capire dove intervenire come TL.',
          },
          professionista: {
            all: 'Consulta risultati, feedback e aree di miglioramento del tuo lavoro.',
            nutrizione: 'Consulta KPI e feedback rilevanti per il tuo lavoro in nutrizione.',
            coaching: 'Consulta KPI e feedback rilevanti per il tuo lavoro nel coaching.',
            psicologia: 'Consulta KPI e feedback rilevanti per il tuo lavoro in psicologia.',
          },
        },
      },
    ],
  },
  {
    id: 'generale',
    label: 'Generale',
    icon: 'ri-book-3-line',
    items: [
      {
        key: 'panoramica',
        label: 'Panoramica',
        icon: 'ri-book-open-line',
        staticPath: 'panoramica/overview/',
        description: 'Panoramica generale del progetto e template documentazione.',
      },
      {
        key: 'team',
        label: 'Team e Organizzazione',
        icon: 'ri-org-chart',
        staticPath: 'team/team-professionisti/',
        description: 'Autenticazione, team professionisti, KPI e performance.',
      },
      {
        key: 'clienti-core',
        label: 'Clienti Core',
        icon: 'ri-user-heart-line',
        staticPath: 'clienti-core/gestione-clienti/',
        description: 'Gestione clienti, check periodici, nutrizione, diario.',
      },
      {
        key: 'strumenti',
        label: 'Strumenti Operativi',
        icon: 'ri-tools-line',
        staticPath: 'strumenti/task-calendario/',
        description: 'Task, calendario, ticket, chat, ricerca.',
      },
      {
        key: 'comunicazione',
        label: 'Comunicazione',
        icon: 'ri-message-3-line',
        staticPath: 'comunicazione/README/',
        description: 'GHL, respond.io, notifiche, chatbot.',
      },
      {
        key: 'guide-ruoli',
        label: 'Guide Ruoli',
        icon: 'ri-user-guide-line',
        staticPath: 'guide-ruoli/overview/',
        description: 'Guide operative per Coach, Nutrizionista, Psicologo.',
      },
    ],
  },
  {
    id: 'amministrazione',
    label: 'Amministrazione',
    icon: 'ri-admin-line',
    adminOnly: true,
    items: [
      {
        key: 'infrastruttura',
        label: 'Infrastruttura',
        icon: 'ri-server-line',
        staticPath: 'infrastruttura/ci_cd_analysis/',
        description: 'CI/CD, GCP, migrazione.',
      },
      {
        key: 'sviluppo',
        label: 'Sviluppo',
        icon: 'ri-code-s-slash-line',
        staticPath: 'sviluppo/refactor_status_report/',
        description: 'Refactor, piani sviluppo.',
      },
    ],
  },
];

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

  const allGuides = useMemo(
    () => GUIDE_GROUPS
      .filter((group) => !group.adminOnly || isAdminOrCco)
      .flatMap((group) => group.items.map((item) => ({ ...item, groupId: group.id, groupLabel: group.label }))),
    [isAdminOrCco]
  );

  const hashKey = location.hash.replace('#', '');
  const activeGuideKey = allGuides.some((guide) => guide.key === hashKey)
    ? hashKey
    : DEFAULT_GUIDE_BY_AUDIENCE[audience];

  const activeGuide = allGuides.find((guide) => guide.key === activeGuideKey) || allGuides[0];
  const activeSpecialtyOption = SPECIALTY_OPTIONS.find((option) => option.key === specialty) || SPECIALTY_OPTIONS[0];

  const resolveVariantPath = (guide, guideAudience, guideSpecialty) => {
    const audienceVariants = guide.variants?.[guideAudience] || guide.variants?.professionista || {};
    return audienceVariants[guideSpecialty] || audienceVariants.all || '';
  };

  const resolveGuideDescription = (guide, guideAudience, guideSpecialty) => {
    // Se ha description statica, usala
    if (guide.description) {
      return guide.description;
    }
    // Altrimenti cerca nelle varianti
    const audienceDescriptions = guide.descriptions?.[guideAudience] || guide.descriptions?.professionista || {};
    return audienceDescriptions[guideSpecialty] || audienceDescriptions.all || '';
  };

  const iframeUrl = useMemo(() => {
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

  if (loading) {
    return (
      <div className="dc-loading">
        <div className="dc-loading-ring"><div /><div /><div /></div>
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
          {GUIDE_GROUPS.map((group) => (
            <div key={group.id} className="dc-nav-section">
              <div className="dc-nav-heading">
                <i className={group.icon} />
                <span>{group.label}</span>
                <span className="dc-nav-heading-count">{group.items.length}</span>
              </div>

              {group.items.map((guide) => {
                const active = activeGuideKey === guide.key;
                return (
                  <button
                    key={guide.key}
                    type="button"
                    className={`dc-nav-link${active ? ' dc-nav-link--on' : ''}`}
                    onClick={() => handleGuideClick(guide.key)}
                  >
                    {active && <div className="dc-nav-link-bar" />}
                    <i className={guide.icon} />
                    <div className="dc-nav-link-text">
                      <strong>{guide.label}</strong>
                      <span>{resolveGuideDescription(guide, audience, specialty)}</span>
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
          <span>{activeGuide.label}</span>
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
              <span className="dc-header-crumb">{activeGuide.groupLabel}</span>
              <i className="ri-arrow-right-s-line" />
              <span className="dc-header-crumb">{activeGuide.label}</span>
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
          <p className="dc-header-desc">{resolveGuideDescription(activeGuide, audience, specialty)}</p>
        </header>

        <div className="dc-frame">
          <iframe
            src={iframeUrl}
            title={`Documentazione ${activeGuide.label}`}
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

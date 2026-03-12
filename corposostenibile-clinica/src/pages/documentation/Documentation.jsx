import React, { useContext, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import AuthContext from '../../context/AuthContext';
import {
  DOCUMENTATION_SPECIALTY_OPTIONS,
  getRequestedSpecialty,
  getTourContext,
} from '../../utils/tourScope';
import './Documentation.css';

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
    items: [
      {
        key: 'lista-pazienti',
        label: 'Lista Pazienti',
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
    items: [
      {
        key: 'task',
        label: 'Task',
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
];

const DEFAULT_GUIDE_BY_AUDIENCE = {
  team_leader: 'lista-pazienti',
  professionista: 'task',
};

const SPECIALTY_OPTIONS = DOCUMENTATION_SPECIALTY_OPTIONS.filter((option) =>
  ['all', 'nutrizione', 'coaching', 'psicologia'].includes(option.key)
);

function Documentation() {
  const location = useLocation();
  const navigate = useNavigate();
  const auth = useContext(AuthContext);
  const currentUser = auth?.user || null;
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
    () => GUIDE_GROUPS.flatMap((group) => group.items.map((item) => ({ ...item, groupId: group.id, groupLabel: group.label }))),
    []
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
    const audienceDescriptions = guide.descriptions?.[guideAudience] || guide.descriptions?.professionista || {};
    return audienceDescriptions[guideSpecialty] || audienceDescriptions.all || '';
  };

  const iframeUrl = `/api/documentation/static/${resolveVariantPath(activeGuide, audience, specialty)}`;

  const roleCopy = audience === 'team_leader'
    ? {
        eyebrow: specialty === 'all' ? 'Percorso Team Leader' : `Team Leader • ${activeSpecialtyOption.label}`,
        title: specialty === 'all'
          ? 'Guide per coordinare il team e sbloccare i casi in stallo.'
          : `Guide Team Leader per supervisionare ${activeSpecialtyOption.label.toLowerCase()}.`,
        body: specialty === 'all'
          ? 'La selezione privilegia monitoraggio, priorita operative, qualita e supporto ai professionisti.'
          : `La selezione privilegia KPI, supervisione e decisioni operative nella tua area ${activeSpecialtyOption.label.toLowerCase()}.`,
      }
    : {
        eyebrow: specialty === 'all' ? 'Percorso Professionista' : `Professionista • ${activeSpecialtyOption.label}`,
        title: specialty === 'all'
          ? 'Guide operative per lavorare veloce sui tuoi pazienti.'
          : `Guide operative per lavorare sui pazienti in ${activeSpecialtyOption.label.toLowerCase()}.`,
        body: specialty === 'all'
          ? 'La selezione privilegia esecuzione quotidiana, aggiornamento stati, task e richieste di formazione.'
          : `La selezione privilegia il lavoro quotidiano nella tua area ${activeSpecialtyOption.label.toLowerCase()}, senza rumore sulle altre specialita.`,
      };

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

  return (
    <div className="docs-shell">
      <aside className="docs-sidebar">
        <div className="docs-hero">
          <span className="docs-eyebrow">{roleCopy.eyebrow}</span>
          <h1>{roleCopy.title}</h1>
          <p>{roleCopy.body}</p>
        </div>

        {canSwitchAudience && (
          <div className="docs-control-block">
            <div className="docs-control-label">Audience</div>
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
          </div>
        )}

        <div className="docs-control-block">
          <div className="docs-control-label">Specializzazione</div>
          {specialtyLocked ? (
            <div className="docs-specialty-lock">
              <span>{activeSpecialtyOption.label}</span>
              <small>Vista bloccata sul tuo perimetro operativo</small>
            </div>
          ) : (
            <div className="docs-specialty-switch">
              {SPECIALTY_OPTIONS.map((option) => (
                <button
                  key={option.key}
                  type="button"
                  className={specialty === option.key ? 'active' : ''}
                  onClick={() => setSpecialty(option.key)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          )}
        </div>

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
                      {resolveGuideDescription(guide, audience, specialty)}
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
            <span className="docs-viewer-kicker">
              {activeGuide.groupLabel} • {activeSpecialtyOption.label}
            </span>
            <h2>{activeGuide.label}</h2>
          </div>
          <p>{resolveGuideDescription(activeGuide, audience, specialty)}</p>
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

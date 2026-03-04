import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import clientiService, {
  STATO_LABELS,
  STATO_CLIENTE,
  TIPOLOGIA_LABELS,
  TIPOLOGIA_CLIENTE,
  GENERE_LABELS,
  PAGAMENTO_LABELS,
  PAGAMENTO,
  GIORNI_LABELS,
  LUOGO_LABELS,
  TEAM_LABELS,
  STATI_PROFESSIONISTA_LABELS,
  STATI_PROFESSIONISTA_COLORS,
  TIPO_PROFESSIONISTA,
  TIPO_PROFESSIONISTA_LABELS,
  TIPO_PROFESSIONISTA_ICONS,
  TIPO_PROFESSIONISTA_COLORS,
  PATOLOGIE_PSICO,
} from '../../services/clientiService';
import teamService from '../../services/teamService';
import checkService, { CHECK_TYPES } from '../../services/checkService';
import teamTicketsService from '../../services/teamTicketsService';
import { useAuth } from '../../context/AuthContext';
import GuidedTour from '../../components/GuidedTour';
import SupportWidget from '../../components/SupportWidget';
import ScrollableSubtabs from '../../components/ScrollableSubtabs';
import DatePicker from '../../components/DatePicker';
import api from '../../services/api';
import { FaUserCircle, FaIdCard, FaLayerGroup, FaSave, FaAppleAlt, FaClipboardCheck, FaBrain, FaRunning, FaCheck } from 'react-icons/fa';
import { isHealthManagerUser, isProfessionistaStandard, isTeamLeaderRestricted, normalizeSpecialtyGroup } from '../../utils/rbacScope';
import { createPortal } from 'react-dom';
import './ClientiDetail.css';
import '../calendario/Calendario.css';
import '../check/CheckAzienda.css';

// Authenticated image loader for check iniziali attachments
const CheckPhoto = ({ url, label, onClickFullscreen }) => {
  const [blobUrl, setBlobUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  useEffect(() => {
    let cancelled = false;
    api.get(url, { responseType: 'blob' })
      .then(resp => { if (!cancelled) setBlobUrl(URL.createObjectURL(resp.data)); })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [url]);
  useEffect(() => { return () => { if (blobUrl) URL.revokeObjectURL(blobUrl); }; }, [blobUrl]);
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', marginBottom: '6px', textTransform: 'uppercase' }}>{label}</div>
      {loading ? (
        <div style={{ width: '100%', height: '200px', background: '#f1f5f9', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="spinner-border spinner-border-sm text-secondary"></div>
        </div>
      ) : error ? (
        <div style={{ width: '100%', height: '120px', background: '#fef2f2', borderRadius: '10px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', fontSize: '0.75rem' }}>
          <i className="ri-image-line" style={{ fontSize: '1.5rem', marginBottom: 4 }}></i>Non disponibile
        </div>
      ) : (
        <img src={blobUrl} alt={label}
          style={{ width: '100%', maxHeight: '280px', objectFit: 'cover', borderRadius: '10px', border: '1px solid #e2e8f0', cursor: 'pointer', transition: 'transform 0.2s' }}
          onClick={() => onClickFullscreen(blobUrl)}
          onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.02)'}
          onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
        />
      )}
    </div>
  );
};

// Status gradient colors (same pattern as TeamDetail)
const STATUS_GRADIENTS = {
  attivo: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  pausa: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  ghost: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  stop: 'linear-gradient(135deg, #ed213a 0%, #93291e 100%)',
};

const STATUS_COLORS = {
  attivo: 'success',
  pausa: 'warning',
  ghost: 'secondary',
  stop: 'danger',
};

// Figura di riferimento labels
const FIGURA_RIF_LABELS = {
  coach: 'Coach',
  nutrizionista: 'Nutrizionista',
  psicologa: 'Psicologa',
};

// Lista professioni
const PROFESSIONI_OPTIONS = [
  { group: 'Sanità e Benessere', options: ['Medico', 'Infermiere/a', 'Farmacista', 'Fisioterapista', 'Odontoiatra (Dentista)', 'Psicologo/a', 'Veterinario/a', 'Operatore Socio-Sanitario (OSS)', 'Tecnico di laboratorio', 'Nutrizionista'] },
  { group: 'Tecnologia e Informatica', options: ['Sviluppatore/trice software', 'Sviluppatore/trice web', 'Sistemista / Amministratore di sistema', 'Analista dati (Data Analyst)', 'Project Manager IT', 'Tecnico informatico', 'Specialista Cyber Security'] },
  { group: 'Istruzione e Formazione', options: ['Insegnante (scuola primaria/secondaria)', 'Professore/essa universitario/a', 'Ricercatore/trice', 'Formatore/trice aziendale', 'Educatore/trice'] },
  { group: 'Finanza e Contabilità', options: ['Commercialista', 'Consulente finanziario', 'Ragioniere/a', 'Analista finanziario', 'Bancario/a'] },
  { group: 'Legale', options: ['Avvocato/essa', 'Notaio/a', 'Consulente legale'] },
  { group: 'Ingegneria e Architettura', options: ['Ingegnere civile', 'Ingegnere meccanico', 'Ingegnere elettrico/elettronico', 'Architetto/a', 'Geometra'] },
  { group: 'Arte, Design e Creatività', options: ['Grafico/a / Designer', 'Fotografo/a', 'Artista', 'Musicista', 'Attore/rice', 'Giornalista', 'Scrittore/trice'] },
  { group: 'Vendite, Marketing e Comunicazione', options: ['Agente di commercio / Rappresentante', 'Commesso/a / Addetto/a alle vendite', 'Specialista marketing', 'Social Media Manager', 'Addetto/a stampa / Specialista PR', 'Responsabile vendite'] },
  { group: 'Edilizia, Artigianato e Lavori Manuali', options: ['Muratore/a', 'Elettricista', 'Idraulico/a', 'Falegname', 'Meccanico/a', 'Parrucchiere/a / Estetista'] },
  { group: 'Trasporti e Logistica', options: ['Autista / Conducente', 'Corriere', 'Responsabile logistica', 'Operatore di magazzino'] },
  { group: 'Ristorazione e Turismo', options: ['Cuoco/a / Chef', 'Cameriere/a', 'Barista', 'Guida turistica', 'Receptionist'] },
  { group: 'Sicurezza e Forze dell\'Ordine', options: ['Poliziotto/a', 'Carabiniere', 'Vigile del fuoco', 'Guardia giurata / Addetto/a sicurezza'] },
  { group: 'Pubblica Amministrazione', options: ['Impiegato/a pubblico/a', 'Funzionario pubblico'] },
  { group: 'Sport e Fitness', options: ['Personal trainer', 'Istruttore/trice fitness', 'Atleta professionista'] },
  { group: 'Servizi e Consulenza', options: ['Consulente (generico)', 'Imprenditore/trice'] },
  { group: 'Altre Opzioni', options: ['Studente/ssa', 'Pensionato/a', 'Disoccupato/a o in cerca di occupazione', 'Casalingo/a', '__ALTRO__'] },
];

function ClientiDetail() {
  const { id } = useParams();

  const navigate = useNavigate();
  const { user } = useAuth();
  const isProfessionista = isProfessionistaStandard(user);
  const isHealthManager = isHealthManagerUser(user);
  const isRestrictedTeamLeader = isTeamLeaderRestricted(user);
  const specialtyGroup = normalizeSpecialtyGroup(user?.specialty);
  const isSpecialtyRestrictedRole = isProfessionista || isRestrictedTeamLeader;
  const canSaveGlobalClientCard = true;
  const canManageTeamAssignments = !isProfessionista && !isHealthManager;
  // La generazione dei check periodici è consentita anche al professionista:
  // il backend applica il vero controllo RBAC sul paziente.
  const canGenerateCheckLinks = true;
  const canCreateCallBonus = true;
  const canDeleteClientRecord = Boolean(user?.is_admin || user?.role === 'admin');
  const canManageNutritionSection = !isSpecialtyRestrictedRole || specialtyGroup === 'nutrizione';
  const canManageCoachingSection = !isSpecialtyRestrictedRole || specialtyGroup === 'coach';
  const canManagePsychologySection = !isSpecialtyRestrictedRole || specialtyGroup === 'psicologia';
  const canViewExternalTeamTab = !isRestrictedTeamLeader;
  const canManageAssignmentType = useCallback((tipo) => {
    if (!canManageTeamAssignments) return false;
    if (!isRestrictedTeamLeader) return true;
    if (tipo === 'health_manager') return false;

    const allowedBySpecialty = {
      nutrizione: new Set(['nutrizionista']),
      coach: new Set(['coach']),
      psicologia: new Set(['psicologa']),
      medico: new Set(['medico']),
    };
    return allowedBySpecialty[specialtyGroup]?.has(tipo) ?? false;
  }, [canManageTeamAssignments, isRestrictedTeamLeader, specialtyGroup]);

  const getAllowedMainTabsForUser = useCallback(() => {
    if (!isSpecialtyRestrictedRole) {
      return new Set([
        'anagrafica', 'programma', 'team', 'nutrizione', 'coaching', 'psicologia', 'medico',
        'check_periodici', 'check_iniziali', 'tickets', 'call_bonus'
      ]);
    }

    const allowed = new Set(['anagrafica', 'programma', 'check_periodici', 'check_iniziali', 'tickets', 'call_bonus']);
    if (isRestrictedTeamLeader) {
      allowed.add('team');
    }
    if (specialtyGroup === 'nutrizione') allowed.add('nutrizione');
    if (specialtyGroup === 'coach') allowed.add('coaching');
    if (specialtyGroup === 'psicologia') allowed.add('psicologia');
    if (specialtyGroup === 'medico') allowed.add('medico');
    return allowed;
  }, [isSpecialtyRestrictedRole, isRestrictedTeamLeader, specialtyGroup]);

  // State
  const [cliente, setCliente] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('anagrafica');

  // Tab scroll arrows
  const tabsRef = useRef(null);
  const [tabScroll, setTabScroll] = useState({ canLeft: false, canRight: false });

  const updateTabArrows = useCallback(() => {
    const el = tabsRef.current;
    if (!el) return;
    setTabScroll({
      canLeft: el.scrollLeft > 0,
      canRight: el.scrollLeft + el.clientWidth < el.scrollWidth - 1,
    });
  }, []);

  useEffect(() => {
    const el = tabsRef.current;
    if (!el) return;
    updateTabArrows();
    el.addEventListener('scroll', updateTabArrows, { passive: true });
    const ro = new ResizeObserver(updateTabArrows);
    ro.observe(el);
    return () => {
      el.removeEventListener('scroll', updateTabArrows);
      ro.disconnect();
    };
  }, [updateTabArrows, loading]);

  const scrollTabs = useCallback((dir) => {
    const el = tabsRef.current;
    if (!el) return;
    el.scrollBy({ left: dir * 200, behavior: 'smooth' });
  }, []);

  // Tour Steps Definitions
  const commonSteps = [
    {
      target: '[data-tour="header-dettaglio"]',
      title: 'Scheda Paziente',
      content: 'Benvenuto nella scheda completa del paziente. Qui puoi gestire ogni aspetto del suo percorso nutrizionale, sportivo e psicologico.',
      placement: 'bottom',
      icon: <FaUserCircle size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)'
    },
    {
      target: '[data-tour="profilo-rapido"]',
      title: 'Profilo Rapido',
      content: 'In questa colonna trovi le informazioni essenziali: stato del paziente, giorni al rinnovo e i professionisti assegnati.',
      placement: 'right',
      icon: <FaIdCard size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #10B981, #34D399)'
    },
    {
      target: '[data-tour="nav-tabs-dettaglio"]',
      title: 'Navigazione Sezioni',
      content: 'Usa questi tab per spostarti tra le diverse aree del percorso cliente.',
      placement: 'bottom',
      icon: <FaLayerGroup size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)'
    },
    {
      target: '[data-tour="salva-modifiche"]',
      title: 'Salvataggio rapido',
      content: 'Ricordati di salvare sempre dopo aver apportato modifiche importanti.',
      placement: 'bottom',
      icon: <FaSave size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #EF4444, #F87171)'
    }
  ];

  const tabSpecificSteps = {
    anagrafica: [
      {
        target: '[data-tour="anagrafica-dati"]',
        title: 'Dati Personali',
        content: 'Gestisci qui i dati anagrafici, la professione e le note base.',
        placement: 'right',
        icon: <FaUserCircle size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
        tabId: 'anagrafica'
      },
      {
        target: '[data-tour="anagrafica-contatti"]',
        title: 'Contatti',
        content: 'Tutti i recapiti e l\'indirizzo del cliente sempre a portata di mano.',
        placement: 'left',
        icon: <FaIdCard size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
        tabId: 'anagrafica'
      },
      {
        target: '[data-tour="anagrafica-storia"]',
        title: 'Storia e Obiettivi',
        content: 'Annota il passato del cliente, le sue paure e gli obiettivi che vuole raggiungere.',
        placement: 'top',
        icon: <FaLayerGroup size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
        tabId: 'anagrafica'
      }
    ],
    programma: [
      {
        target: '[data-tour="programma-stato"]',
        title: 'Stato Operativo',
        content: 'Controlla se il cliente è attivo, in pausa o in stop, e aggiorna i dettagli del suo programma.',
        placement: 'right',
        icon: <FaLayerGroup size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
        tabId: 'programma'
      },
      {
        target: '[data-tour="programma-date"]',
        title: 'Controllo Scadenze',
        content: 'Monitora la data di inizio e soprattutto la data di rinnovo per prevenire abbandoni.',
        placement: 'top',
        icon: <FaSave size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
        tabId: 'programma'
      }
    ],
    team: [
      {
        target: '[data-tour="team-subtabs"]',
        title: 'Gestione Team',
        content: 'Visualizza e assegna i professionisti (Nutrizionista, Coach, Psicologo) che seguono il cliente.',
        placement: 'bottom',
        icon: <FaUserCircle size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
        tabId: 'team'
      },
      {
        target: '[data-tour="team-timeline"]',
        title: 'Storico Assegnazioni',
        content: 'Una timeline completa di chi ha seguito il cliente nel tempo.',
        placement: 'top',
        icon: <FaLayerGroup size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
        tabId: 'team'
      }
    ],
    nutrizione: [
      {
        target: '[data-tour="nutrizione-subtabs"]',
        title: 'Area Nutrizione',
        content: 'Naviga tra le diverse sezioni dedicate alla nutrizione.',
        placement: 'bottom',
        icon: <FaAppleAlt size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
        tabId: 'nutrizione'
      },
      {
        target: '[data-tour="nutrizione-panoramica"]',
        title: 'Panoramica Nutrizione',
        content: 'Vedi i professionisti attivi e lo storico degli stati del servizio nutrizionale.',
        placement: 'top',
        icon: <FaAppleAlt size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
        tabId: 'nutrizione',
        onEnter: () => setNutrizioneSubTab('panoramica')
      },
      {
        target: '[data-tour="nutrizione-setup"]',
        title: 'Setup Nutrizione',
        content: 'Configura la call iniziale e i giorni di reach-out settimanale.',
        placement: 'top',
        icon: <FaAppleAlt size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
        tabId: 'nutrizione',
        onEnter: () => setNutrizioneSubTab('setup')
      },
      {
        target: '[data-tour="nutrizione-patologie"]',
        title: 'Patologie e Anamnesi',
        content: 'Documenta la situazione clinica e le abitudini alimentari del cliente.',
        placement: 'top',
        icon: <FaAppleAlt size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
        tabId: 'nutrizione',
        onEnter: () => setNutrizioneSubTab('patologie')
      },
      {
        target: '[data-tour="nutrizione-diario"]',
        title: 'Diario Nutrizionale',
        content: 'Annota i progressi e le osservazioni durante il percorso nutrizionale.',
        placement: 'top',
        icon: <FaAppleAlt size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
        tabId: 'nutrizione',
        onEnter: () => setNutrizioneSubTab('diario')
      },
      {
        target: '[data-tour="nutrizione-alert"]',
        title: 'Alert Nutrizione',
        content: 'Segnala allergie o criticità fondamentali che devono essere sempre visibili.',
        placement: 'top',
        icon: <FaAppleAlt size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #EF4444, #F87171)',
        tabId: 'nutrizione',
        onEnter: () => setNutrizioneSubTab('alert')
      }
    ],
    coaching: [
      {
        target: '[data-tour="coaching-subtabs"]',
        title: 'Area Coaching',
        content: 'Gestisci allenamenti, luoghi e setup sportivo del cliente.',
        placement: 'bottom',
        icon: <FaRunning size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
        tabId: 'coaching'
      },
      {
        target: '[data-tour="coaching-panoramica"]',
        title: 'Panoramica Coaching',
        content: 'Monitora i coach assegnati e lo storico degli stati sportivi.',
        placement: 'top',
        icon: <FaRunning size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
        tabId: 'coaching',
        onEnter: () => setCoachingSubTab('panoramica')
      },
      {
        target: '[data-tour="coaching-setup"]',
        title: 'Setup Coaching',
        content: 'Gestisci la call iniziale sportiva e la frequenza dei contatti.',
        placement: 'top',
        icon: <FaRunning size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
        tabId: 'coaching',
        onEnter: () => setCoachingSubTab('setup')
      },
      {
        target: '[data-tour="coaching-schede"]',
        title: 'Schede Allenamento',
        content: 'Pianifica le schede, carica i file e consulta lo storico degli allenamenti.',
        placement: 'top',
        icon: <FaRunning size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
        tabId: 'coaching',
        onEnter: () => setCoachingSubTab('piano')
      },
      {
        target: '[data-tour="coaching-luoghi"]',
        title: 'Luoghi di Allenamento',
        content: 'Indica dove si allena il cliente (casa, palestra, ecc.).',
        placement: 'top',
        icon: <FaRunning size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
        tabId: 'coaching',
        onEnter: () => setCoachingSubTab('luoghi')
      },
      {
        target: '[data-tour="coaching-patologie"]',
        title: 'Patologie e Anamnesi Sportiva',
        content: 'Annota infortuni, condizioni fisiche o patologie rilevanti per l\'allenamento.',
        placement: 'top',
        icon: <FaRunning size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
        tabId: 'coaching',
        onEnter: () => setCoachingSubTab('patologie')
      },
      {
        target: '[data-tour="coaching-diario"]',
        title: 'Diario Coaching',
        content: 'Traccia i feedback sugli allenamenti e l\'evoluzione atletica.',
        placement: 'top',
        icon: <FaRunning size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)',
        tabId: 'coaching',
        onEnter: () => setCoachingSubTab('diario')
      },
      {
        target: '[data-tour="coaching-alert"]',
        title: 'Alert Coaching',
        content: 'Inserisci alert critici per la sicurezza durante l\'esercizio fisico.',
        placement: 'top',
        icon: <FaRunning size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #EF4444, #F87171)',
        tabId: 'coaching',
        onEnter: () => setCoachingSubTab('alert')
      }
    ],
    psicologia: [
      {
        target: '[data-tour="psicologia-subtabs"]',
        title: 'Area Psicologia',
        content: 'Approfondisci il benessere mentale e comportamentale del cliente.',
        placement: 'bottom',
        icon: <FaBrain size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #8B5CF6, #A78BFA)',
        tabId: 'psicologia'
      },
      {
        target: '[data-tour="psicologia-panoramica"]',
        title: 'Panoramica Psicologia',
        content: 'Vedi gli psicologi assegnati e lo storico del supporto psicologico.',
        placement: 'top',
        icon: <FaBrain size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #8B5CF6, #A78BFA)',
        tabId: 'psicologia',
        onEnter: () => setPsicologiaSubTab('panoramica')
      },
      {
        target: '[data-tour="psicologia-setup"]',
        title: 'Setup Psicologia',
        content: 'Gestisci la call iniziale psicologica e le modalità di supporto.',
        placement: 'top',
        icon: <FaBrain size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #8B5CF6, #A78BFA)',
        tabId: 'psicologia',
        onEnter: () => setPsicologiaSubTab('setup')
      },
      {
        target: '[data-tour="psicologia-patologie"]',
        title: 'Patologie Psicologiche',
        content: 'Documenta eventuali disturbi o condizioni psicologiche certificate.',
        placement: 'top',
        icon: <FaBrain size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #8B5CF6, #A78BFA)',
        tabId: 'psicologia',
        onEnter: () => setPsicologiaSubTab('patologie')
      },
      {
        target: '[data-tour="psicologia-diario"]',
        title: 'Diario Psicologia',
        content: 'Note del percorso psicologico e annotazioni comportamentali.',
        placement: 'top',
        icon: <FaBrain size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #8B5CF6, #A78BFA)',
        tabId: 'psicologia',
        onEnter: () => setPsicologiaSubTab('diario')
      },
      {
        target: '[data-tour="psicologia-alert"]',
        title: 'Alert Psicologia',
        content: 'Inserisci alert critici per la gestione psicologica o rischi per il cliente.',
        placement: 'top',
        icon: <FaBrain size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #EF4444, #F87171)',
        tabId: 'psicologia',
        onEnter: () => setPsicologiaSubTab('alert')
      }
    ],
    check_periodici: [
      {
        target: '[data-tour="check-periodici-tabs"]',
        title: 'Check Periodici',
        content: 'Scegli la tipologia di check: Settimanale, DCA o Minori.',
        placement: 'bottom',
        icon: <FaClipboardCheck size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #EF4444, #F87171)',
        tabId: 'check_periodici'
      },
      {
        target: '[data-tour="check-periodici-link"]',
        title: 'Invio Check',
        content: 'Genera e copia i link da inviare al cliente per la compilazione.',
        placement: 'bottom',
        icon: <FaIdCard size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #EF4444, #F87171)',
        tabId: 'check_periodici'
      },
      {
        target: '[data-tour="check-periodici-risposte"]',
        title: 'Storico Risposte',
        content: 'Consulta tutte le compilazioni passate e i punteggi ottenuti.',
        placement: 'top',
        icon: <FaLayerGroup size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #EF4444, #F87171)',
        tabId: 'check_periodici'
      }
    ],
    check_iniziali: [
      {
        target: '[data-tour="check-iniziali-tabs"]',
        title: 'Check Iniziali',
        content: 'Accedi ai check storici (Check 1, 2 e 3) compilati all\'inizio del percorso.',
        placement: 'bottom',
        icon: <FaLayerGroup size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
        tabId: 'check_iniziali'
      },
      {
        target: '[data-tour="check-iniziali-contenuto"]',
        title: 'Dettagli Check Iniziali',
        content: 'Visualizza tutte le risposte dettagliate e i punteggi dei check di ingresso.',
        placement: 'top',
        icon: <FaLayerGroup size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
        tabId: 'check_iniziali'
      }
    ]
  };
  const [mostraTour, setMostraTour] = useState(false);
  const [activeTourSteps, setActiveTourSteps] = useState([]);
  const [tourKey, setTourKey] = useState(0);

  const handleTourStart = () => {
    // Definizione step di scelta iniziale
    const selectionStep = {
      target: '[data-tour="header-dettaglio"]', // Target a generic element
      title: (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Guida Interattiva</span>
        </div>
      ),
      content: (
        <div>
          <p className="mb-3">
            Ti trovi nella pagina <strong>Dettaglio Paziente</strong>.
            <br />
            Tab selezionata: <strong>{activeTab.charAt(0).toUpperCase() + activeTab.slice(1).replace('_', ' ')}</strong>
          </p>
          <p className="mb-3 small text-muted">
             Che tipo di tour vuoi seguire oggi?
          </p>
          <div className="d-flex flex-column gap-2">
            <button
              className="btn btn-sm btn-outline-primary d-flex align-items-center justify-content-center gap-2"
              onClick={() => handleTourSelection('general')}
            >
              <FaLayerGroup /> Panoramica Generale
            </button>
            <button
              className="btn btn-sm btn-outline-success d-flex align-items-center justify-content-center gap-2"
              onClick={() => handleTourSelection('specific')}
            >
              <FaCheck /> Specifico Tab: {activeTab.charAt(0).toUpperCase() + activeTab.slice(1).replace('_', ' ')}
            </button>
          </div>
        </div>
      ),
      placement: 'bottom', // 'center' if supported by library, else bottom of header
      icon: <FaBrain size={18} color="white" />,
      iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
      // Note: We might need to block "Next" button on this step via library props if possible,
      // or just trust users to click the custom buttons.
    };

    setActiveTourSteps([selectionStep]);
    setTourKey(prev => prev + 1);
    setActiveTourSteps([selectionStep]);
    setTourKey(prev => prev + 1);
    setMostraTour(true);
  };

  // Support Hub Integration: Auto-start tour if query param is set
  const [searchParams] = useSearchParams();
  useEffect(() => {
    if (searchParams.get('startTour') === 'true' && !loading) {
        // Avvia il tour con un leggero ritardo per assicurare il rendering
        setTimeout(() => {
            handleTourStart();
        }, 800);
    }
  }, [searchParams, loading]);

  useEffect(() => {
    const requestedTab = (searchParams.get('tab') || '').trim().toLowerCase();
    if (!requestedTab) return;

    const tabAliases = {
      check: 'check_periodici',
      checks: 'check_periodici',
      check_periodici: 'check_periodici',
      check_settimanali: 'check_periodici',
      check_settimanale: 'check_periodici',
      check_iniziali: 'check_iniziali',
    };

    const mapped = tabAliases[requestedTab] || requestedTab;
    const validTabs = getAllowedMainTabsForUser();

    if (validTabs.has(mapped)) {
      setActiveTab(mapped);
    }
  }, [searchParams, getAllowedMainTabsForUser]);

  const handleTourSelection = (type) => {
    let steps = [];
    if (type === 'general') {
       steps = commonSteps;
    } else {
       const specific = tabSpecificSteps[activeTab] || [];
       if (specific.length === 0) {
         // Fallback if no specific steps
         steps = commonSteps;
         alert('Nessun tour specifico per questa tab. Avvio tour generale.');
       } else {
         steps = specific;
       }
    }
    setActiveTourSteps(steps);
    setTourKey(prev => prev + 1);
  };

  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [teamSubTab, setTeamSubTab] = useState('clinico'); // 'clinico' or 'esterno'
  useEffect(() => {
    if (!canViewExternalTeamTab && teamSubTab === 'esterno') {
      setTeamSubTab('clinico');
    }
  }, [canViewExternalTeamTab, teamSubTab]);

  // Professional assignment state
  const [professionistiHistory, setProfessionistiHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [availableProfessionals, setAvailableProfessionals] = useState({});

  // Nutrizione sub-tab state
  const [nutrizioneSubTab, setNutrizioneSubTab] = useState('panoramica');
  const [storicoStatoNutrizione, setStoricoStatoNutrizione] = useState([]);
  const [storicoChatNutrizione, setStoricoChatNutrizione] = useState([]);
  const [loadingStoricoNutrizione, setLoadingStoricoNutrizione] = useState(false);
  const [mealPlans, setMealPlans] = useState([]);
  const [loadingMealPlans, setLoadingMealPlans] = useState(false);
  const [showAddMealPlanModal, setShowAddMealPlanModal] = useState(false);
  const [mealPlanForm, setMealPlanForm] = useState({ name: '', start_date: '', end_date: '', notes: '' });
  const [mealPlanFile, setMealPlanFile] = useState(null);
  const [savingMealPlan, setSavingMealPlan] = useState(false);
  // Preview, Edit, History modals for meal plans
  const [showPreviewPlanModal, setShowPreviewPlanModal] = useState(false);
  const [showEditPlanModal, setShowEditPlanModal] = useState(false);
  const [showVersionsModal, setShowVersionsModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [editPlanForm, setEditPlanForm] = useState({ start_date: '', end_date: '', notes: '', change_reason: '' });
  const [editPlanFile, setEditPlanFile] = useState(null);
  const [planVersions, setPlanVersions] = useState([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  // Anamnesi state (campo unico)
  const [anamnesiNutrizione, setAnamnesiNutrizione] = useState(null);
  const [anamnesiContent, setAnamnesiContent] = useState('');
  const [loadingAnamnesi, setLoadingAnamnesi] = useState(false);
  const [savingAnamnesi, setSavingAnamnesi] = useState(false);
  // Diario state (Nutrizione)
  const [diarioEntries, setDiarioEntries] = useState([]);
  const [loadingDiario, setLoadingDiario] = useState(false);
  const [showDiarioModal, setShowDiarioModal] = useState(false);
  const [diarioForm, setDiarioForm] = useState({ id: null, entry_date: '', content: '' });
  const [savingDiario, setSavingDiario] = useState(false);
  // Diario History
  const [showDiaryHistoryModal, setShowDiaryHistoryModal] = useState(false);
  const [diaryHistory, setDiaryHistory] = useState([]);
  const [loadingDiaryHistory, setLoadingDiaryHistory] = useState(false);

  // ==================== COACHING STATE ====================
  const [coachingSubTab, setCoachingSubTab] = useState('panoramica');
  // Training Plans
  const [trainingPlans, setTrainingPlans] = useState([]);
  const [loadingTrainingPlans, setLoadingTrainingPlans] = useState(false);
  const [showAddTrainingPlanModal, setShowAddTrainingPlanModal] = useState(false);
  const [trainingPlanForm, setTrainingPlanForm] = useState({ name: '', start_date: '', end_date: '', notes: '' });
  const [trainingPlanFile, setTrainingPlanFile] = useState(null);
  const [savingTrainingPlan, setSavingTrainingPlan] = useState(false);
  const [showPreviewTrainingModal, setShowPreviewTrainingModal] = useState(false);
  const [showEditTrainingModal, setShowEditTrainingModal] = useState(false);
  const [showTrainingVersionsModal, setShowTrainingVersionsModal] = useState(false);
  const [selectedTrainingPlan, setSelectedTrainingPlan] = useState(null);
  const [editTrainingForm, setEditTrainingForm] = useState({ start_date: '', end_date: '', notes: '', change_reason: '' });
  const [editTrainingFile, setEditTrainingFile] = useState(null);
  const [trainingVersions, setTrainingVersions] = useState([]);
  const [loadingTrainingVersions, setLoadingTrainingVersions] = useState(false);
  // Training Locations
  const [trainingLocations, setTrainingLocations] = useState([]);
  const [loadingLocations, setLoadingLocations] = useState(false);
  const [showLocationModal, setShowLocationModal] = useState(false);
  const [locationForm, setLocationForm] = useState({ id: null, location: '', start_date: '', end_date: '', notes: '', change_reason: '' });
  const [savingLocation, setSavingLocation] = useState(false);
  // Coaching Anamnesi & Diario
  const [anamnesiCoaching, setAnamnesiCoaching] = useState(null);
  const [anamnesiCoachingContent, setAnamnesiCoachingContent] = useState('');
  const [loadingAnamnesiCoaching, setLoadingAnamnesiCoaching] = useState(false);
  const [savingAnamnesiCoaching, setSavingAnamnesiCoaching] = useState(false);
  const [diarioCoachingEntries, setDiarioCoachingEntries] = useState([]);
  const [loadingDiarioCoaching, setLoadingDiarioCoaching] = useState(false);
  const [showDiarioCoachingModal, setShowDiarioCoachingModal] = useState(false);
  const [diarioCoachingForm, setDiarioCoachingForm] = useState({ id: null, entry_date: '', content: '' });
  const [savingDiarioCoaching, setSavingDiarioCoaching] = useState(false);
  // Coaching State History
  const [storicoStatoCoaching, setStoricoStatoCoaching] = useState([]);
  const [storicoChatCoaching, setStoricoChatCoaching] = useState([]);
  const [loadingStoricoCoaching, setLoadingStoricoCoaching] = useState(false);

  // ==================== PSICOLOGIA STATE ====================
  const [psicologiaSubTab, setPsicologiaSubTab] = useState('panoramica');
  // Psicologia State History
  const [storicoStatoPsicologia, setStoricoStatoPsicologia] = useState([]);
  const [storicoChatPsicologia, setStoricoChatPsicologia] = useState([]);
  const [loadingStoricoPsicologia, setLoadingStoricoPsicologia] = useState(false);
  // Psicologia Anamnesi (service_anamnesi)
  const [anamnesiPsicologia, setAnamnesiPsicologia] = useState(null);
  const [anamnesiPsicologiaContent, setAnamnesiPsicologiaContent] = useState('');
  const [loadingAnamnesiPsicologia, setLoadingAnamnesiPsicologia] = useState(false);
  const [savingAnamnesiPsicologia, setSavingAnamnesiPsicologia] = useState(false);
  // Psicologia Diario
  const [diarioPsicologiaEntries, setDiarioPsicologiaEntries] = useState([]);
  const [loadingDiarioPsicologia, setLoadingDiarioPsicologia] = useState(false);
  const [showDiarioPsicologiaModal, setShowDiarioPsicologiaModal] = useState(false);
  const [diarioPsicologiaForm, setDiarioPsicologiaForm] = useState({ id: null, entry_date: '', content: '' });
  const [savingDiarioPsicologia, setSavingDiarioPsicologia] = useState(false);

  // ==================== CHECK STATE ====================
  const [checkData, setCheckData] = useState({ checks: { weekly: null, dca: null, minor: null }, responses: [] });
  const [loadingChecks, setLoadingChecks] = useState(false);
  const [generatingLink, setGeneratingLink] = useState(null); // 'weekly' | 'dca' | 'minor' | null
  const [showCheckResponseModal, setShowCheckResponseModal] = useState(false);
  const [selectedCheckResponse, setSelectedCheckResponse] = useState(null);

  const [loadingCheckDetail, setLoadingCheckDetail] = useState(false);
  const [lightboxUrl, setLightboxUrl] = useState(null);

  // Check Sub-tabs states
  const [activePeriodiciTab, setActivePeriodiciTab] = useState('weekly');
  const [activeInizialiTab, setActiveInizialiTab] = useState('check_1');
  const [initialChecksData, setInitialChecksData] = useState(null);
  const [loadingInitialChecks, setLoadingInitialChecks] = useState(false);

  // ==================== TICKETS STATE ====================
  const [patientTickets, setPatientTickets] = useState([]);
  const [loadingTickets, setLoadingTickets] = useState(false);
  const [ticketDetailModal, setTicketDetailModal] = useState(null);
  const [ticketMessages, setTicketMessages] = useState([]);
  const [loadingTicketDetail, setLoadingTicketDetail] = useState(false);

  // Call Bonus state
  const [callBonusHistory, setCallBonusHistory] = useState([]);
  const [loadingCallBonus, setLoadingCallBonus] = useState(false);
  const [showCallBonusModal, setShowCallBonusModal] = useState(false);
  const [callBonusStep, setCallBonusStep] = useState(1);
  const [callBonusForm, setCallBonusForm] = useState({ tipo_professionista: '', note_richiesta: '' });
  const [callBonusAiLoading, setCallBonusAiLoading] = useState(false);
  const [callBonusAnalysis, setCallBonusAnalysis] = useState(null);
  const [callBonusMatches, setCallBonusMatches] = useState([]);
  const [callBonusId, setCallBonusId] = useState(null);
  const [selectedCallBonusProfessional, setSelectedCallBonusProfessional] = useState(null);
  const [callBonusCalendarLink, setCallBonusCalendarLink] = useState('');
  const [callBonusResponseModal, setCallBonusResponseModal] = useState(null); // cb record for modal
  const [callBonusInterestStep, setCallBonusInterestStep] = useState('ask'); // 'ask' | 'book_hm'
  const [confirmingBooking, setConfirmingBooking] = useState(false);
  const [decliningCallBonus, setDecliningCallBonus] = useState(false);

  const [showAssignModal, setShowAssignModal] = useState(false);
  const [showInterruptModal, setShowInterruptModal] = useState(false);
  const [assigningType, setAssigningType] = useState(null);
  const [interruptingAssignment, setInterruptingAssignment] = useState(null);
  const [assignForm, setAssignForm] = useState({ user_id: '', data_dal: '', motivazione_aggiunta: '' });
  const [interruptForm, setInterruptForm] = useState({ motivazione_interruzione: '' });
  const [assignLoading, setAssignLoading] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    // Anagrafica
    nome_cognome: '',
    data_di_nascita: '',
    genere: '',
    indirizzo: '',
    paese: '',
    professione: '',
    professione_note: '',
    origine: '',
    mail: '',
    numero_telefono: '',
    storia_cliente: '',
    problema: '',
    paure: '',
    conseguenze: '',
    // Programma e Stato
    stato_cliente: '',
    stato_cliente_data: '',
    programma_attuale: '',
    tipologia_cliente: '',
    data_inizio_abbonamento: '',
    durata_programma_giorni: '',
    data_rinnovo: '',
    data_inizio_nutrizione: '',
    durata_nutrizione_giorni: '',
    data_scadenza_nutrizione: '',
    data_inizio_coach: '',
    durata_coach_giorni: '',
    data_scadenza_coach: '',
    data_inizio_psicologia: '',
    durata_psicologia_giorni: '',
    data_scadenza_psicologia: '',
    modalita_pagamento: '',
    rate_cliente_sales: '',
    note_rinnovo: '',
    // Team
    stato_nutrizione: '',
    stato_nutrizione_data: '',
    stato_coach: '',
    stato_coach_data: '',
    stato_psicologia: '',
    stato_psicologia_data: '',
    check_day: '',
    di_team: '',
    figura_di_riferimento: '',
    alert: false,
    // Nutrizione
    call_iniziale_nutrizionista: false,
    data_call_iniziale_nutrizionista: '',
    reach_out_nutrizione: '',
    stato_cliente_chat_nutrizione: '',
    nessuna_patologia: false,
    patologia_ibs: false,
    patologia_reflusso: false,
    patologia_gastrite: false,
    patologia_dca: false,
    patologia_insulino_resistenza: false,
    patologia_diabete: false,
    patologia_dislipidemie: false,
    patologia_steatosi_epatica: false,
    patologia_ipertensione: false,
    patologia_pcos: false,
    patologia_endometriosi: false,
    patologia_obesita_sindrome: false,
    patologia_osteoporosi: false,
    patologia_diverticolite: false,
    patologia_crohn: false,
    patologia_stitichezza: false,
    patologia_tiroidee: false,
    patologia_altro_check: false,
    patologia_altro: '',
    storia_nutrizione: '',
    note_extra_nutrizione: '',
    alert_nutrizione: '',
    // Coaching
    call_iniziale_coach: false,
    data_call_iniziale_coach: '',
    reach_out_coaching: '',
    stato_cliente_chat_coaching: '',
    luogo_di_allenamento: '',
    storia_coach: '',
    note_extra_coach: '',
    alert_coaching: '',
    // Psicologia
    call_iniziale_psicologa: false,
    data_call_iniziale_psicologia: '',
    reach_out_psicologia: '',
    stato_cliente_chat_psicologia: '',
    storia_psicologica: '',
    note_extra_psicologa: '',
    alert_psicologia: '',
    nessuna_patologia_psico: false,
    patologia_psico_dca: false,
    patologia_psico_obesita_psicoemotiva: false,
    patologia_psico_ansia_umore_cibo: false,
    patologia_psico_comportamenti_disfunzionali: false,
    patologia_psico_immagine_corporea: false,
    patologia_psico_psicosomatiche: false,
    patologia_psico_relazionali_altro: false,
    patologia_psico_altro_check: false,
    patologia_psico_altro: '',
    sedute_psicologia_comprate: 0,
    sedute_psicologia_svolte: 0,
  });

  const [showProfessioneAltro, setShowProfessioneAltro] = useState(false);
  const [professioneAltro, setProfessioneAltro] = useState('');

  // Fetch cliente
  useEffect(() => {
    const fetchCliente = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await clientiService.getCliente(id);
        const c = data.data || data;
        setCliente(c);
        populateForm(c);
      } catch (err) {
        console.error('Error fetching cliente:', err);
        setError('Errore nel caricamento del cliente');
      } finally {
        setLoading(false);
      }
    };
    fetchCliente();
  }, [id]);

  // Preload professionisti history once so HM/team badges are available immediately
  useEffect(() => {
    if (!id || professionistiHistory.length > 0) return;
    fetchProfessionistiHistory();
  }, [id, professionistiHistory.length]);

  // Fetch professional history when Team tab is active
  useEffect(() => {
    if (activeTab === 'team' && id) {
      fetchProfessionistiHistory();
      fetchAvailableProfessionals();
    }
  }, [activeTab, id]);

  // Fetch state history and meal plans when Nutrizione tab is active
  useEffect(() => {
    if (activeTab === 'nutrizione' && id) {
      fetchStoricoNutrizione();
      fetchMealPlans();
      // Also fetch professionisti history for the timeline
      if (professionistiHistory.length === 0) {
        fetchProfessionistiHistory();
      }
    }
  }, [activeTab, id]);

  // Fetch anamnesi/diario when sub-tab changes
  useEffect(() => {
    if (activeTab === 'nutrizione' && id) {
      if (nutrizioneSubTab === 'patologie') {
        fetchAnamnesi();
      } else if (nutrizioneSubTab === 'diario') {
        fetchDiarioEntries();
      }
    }
  }, [activeTab, nutrizioneSubTab, id]);

  // Fetch coaching data when Coaching tab is active
  useEffect(() => {
    if (activeTab === 'coaching' && id) {
      fetchTrainingPlans();
      fetchTrainingLocations();
      if (professionistiHistory.length === 0) {
        fetchProfessionistiHistory();
      }
    }
  }, [activeTab, id]);

  // Fetch coaching sub-tab data
  useEffect(() => {
    if (activeTab === 'coaching' && id) {
      if (coachingSubTab === 'panoramica') {
        fetchStoricoCoaching();
      } else if (coachingSubTab === 'anamnesi') {
        fetchAnamnesiCoaching();
      } else if (coachingSubTab === 'diario') {
        fetchDiarioCoaching();
      }
    }
  }, [activeTab, coachingSubTab, id]);

  // Fetch psicologia data when Psicologia tab is active
  useEffect(() => {
    if (activeTab === 'psicologia' && id) {
      if (professionistiHistory.length === 0) {
        fetchProfessionistiHistory();
      }
    }
  }, [activeTab, id]);

  // Fetch psicologia sub-tab data
  useEffect(() => {
    if (activeTab === 'psicologia' && id) {
      if (psicologiaSubTab === 'panoramica') {
        fetchStoricoPsicologia();
      } else if (psicologiaSubTab === 'patologie') {
        fetchAnamnesiPsicologia();
      } else if (psicologiaSubTab === 'diario') {
        fetchDiarioPsicologia();
      }
    }
  }, [activeTab, psicologiaSubTab, id]);

  // Fetch medico data when Medico tab is active
  useEffect(() => {
    if (activeTab === 'medico' && id) {
      if (professionistiHistory.length === 0) {
        fetchProfessionistiHistory();
      }
      fetchAvailableProfessionals();
    }
  }, [activeTab, id]);

  // Fetch check data when check tab is active
  useEffect(() => {
    // Fetch check data when check tab is active
    if ((activeTab === 'check_periodici' || activeTab === 'check_iniziali') && id) {
      fetchCheckData();
      // Also fetch professionisti history for showing avatars in check responses
      if (professionistiHistory.length === 0) {
        fetchProfessionistiHistory();
      }
    }
  }, [activeTab, id]);

  // ==================== CHECK FUNCTIONS ====================
  const fetchCheckData = async () => {
    setLoadingChecks(true);
    try {
      const data = await checkService.getClienteChecks(id);
      if (data.success) {
        setCheckData({ checks: data.checks, responses: data.responses });
      }
    } catch (err) {
      console.error('Error fetching check data:', err);
    } finally {
      setLoadingChecks(false);
    }
  };

  const handleGenerateCheckLink = async (checkType) => {
    if (!canGenerateCheckLinks) {
      setError('Generazione link check non consentita.');
      return;
    }
    setGeneratingLink(checkType);
    try {
      const result = await checkService.generateCheckLink(checkType, id);
      if (result.success) {
        // Copy to clipboard
        await checkService.copyLinkToClipboard(result.url);
        alert('Link copiato negli appunti!');
        // Refresh check data
        fetchCheckData();
      }
    } catch (err) {
      console.error('Error generating check link:', err);
      alert('Errore nella generazione del link');
    } finally {
      setGeneratingLink(null);
    }
  };

  const handleOpenCheckForm = (url) => {
    window.open(url, '_blank');
  };

  const handleViewCheckResponse = async (response) => {
    setSelectedCheckResponse(response);
    setShowCheckResponseModal(true);
    setLoadingCheckDetail(true);
    try {
      const result = await checkService.getResponseDetail(response.source || response.type, response.id);
      if (result.success) {
        setSelectedCheckResponse(result.response);
      }
    } catch (err) {
      console.error('Error fetching response detail:', err);
    } finally {
      setLoadingCheckDetail(false);
    }
  };

  const handleConfirmReadCheck = async (responseType, responseId) => {
    try {
      const result = await checkService.confirmRead(responseType, responseId);
      if (result.success) {
        // Refresh check data
        fetchCheckData();
      }
    } catch (err) {
      console.error('Error confirming read:', err);
    }
  };

  const fetchInitialChecks = useCallback(async () => {
    if (!id) return;
    setLoadingInitialChecks(true);
    try {
      const result = await clientiService.getInitialChecks(id);
      if (result.has_data) {
        setInitialChecksData(result.checks);
      } else {
        setInitialChecksData(null);
      }
    } catch (err) {
      console.error('Error fetching initial checks:', err);
    } finally {
      setLoadingInitialChecks(false);
    }
  }, [id]);

  useEffect(() => {
    if (activeTab === 'check_iniziali') {
      fetchInitialChecks();
    }
  }, [activeTab, fetchInitialChecks]);

  // ── Fetch Tickets ──
  const fetchPatientTickets = useCallback(async () => {
    if (!id) return;
    setLoadingTickets(true);
    try {
      const data = await teamTicketsService.listByPatient(id, { per_page: 50 });
      setPatientTickets(data.tickets || []);
    } catch (err) {
      console.error('Error fetching patient tickets:', err);
    } finally {
      setLoadingTickets(false);
    }
  }, [id]);

  useEffect(() => {
    if (activeTab === 'tickets') {
      fetchPatientTickets();
    }
  }, [activeTab, fetchPatientTickets]);

  const openTicketDetail = async (ticketId) => {
    setLoadingTicketDetail(true);
    setTicketDetailModal(null);
    setTicketMessages([]);
    try {
      const [ticketData, messagesData] = await Promise.all([
        teamTicketsService.getTicket(ticketId),
        teamTicketsService.getMessages(ticketId),
      ]);
      setTicketDetailModal(ticketData.ticket || ticketData);
      setTicketMessages(messagesData.messages || []);
    } catch (err) {
      console.error('Error fetching ticket detail:', err);
    } finally {
      setLoadingTicketDetail(false);
    }
  };

  // ── Fetch Call Bonus History ──
  const fetchCallBonusHistory = useCallback(async () => {
    if (!id) return;
    setLoadingCallBonus(true);
    try {
      const data = await clientiService.getCallBonusHistory(id);
      setCallBonusHistory(data.data || []);
    } catch (err) {
      console.error('Error fetching call bonus history:', err);
    } finally {
      setLoadingCallBonus(false);
    }
  }, [id]);

  useEffect(() => {
    if (activeTab === 'call_bonus') {
      fetchCallBonusHistory();
    }
  }, [activeTab, fetchCallBonusHistory]);

  // ── Call Bonus Handlers ──
  const handleOpenCallBonusModal = () => {
    setCallBonusStep(1);
    setCallBonusForm({ tipo_professionista: '', note_richiesta: '' });
    setCallBonusAnalysis(null);
    setCallBonusMatches([]);
    setCallBonusId(null);
    setSelectedCallBonusProfessional(null);
    setCallBonusCalendarLink('');
    setShowCallBonusModal(true);
  };

  const handleCallBonusAnalyze = async () => {
    if (!callBonusForm.tipo_professionista) return;
    setCallBonusAiLoading(true);
    try {
      const result = await clientiService.createCallBonusRequest(id, callBonusForm);
      setCallBonusId(result.call_bonus_id);
      setCallBonusAnalysis(result.analysis);
      setCallBonusMatches(result.matches || []);
      setCallBonusStep(2);
    } catch (err) {
      console.error('Error creating call bonus request:', err);
      alert('Errore nella creazione della richiesta. Riprova.');
    } finally {
      setCallBonusAiLoading(false);
    }
  };

  const handleSelectCallBonusProfessional = async (prof) => {
    try {
      const result = await clientiService.selectCallBonusProfessional(callBonusId, prof.id);
      setSelectedCallBonusProfessional(prof);
      setCallBonusCalendarLink(result.link_call_bonus || '');
      setCallBonusStep(3);
    } catch (err) {
      console.error('Error selecting professional:', err);
      alert('Errore nella selezione del professionista. Riprova.');
    }
  };

  const handleConfirmCallBonusBooking = async () => {
    const targetId = callBonusResponseModal ? callBonusResponseModal.id : callBonusId;
    if (!targetId) return;
    setConfirmingBooking(true);
    try {
      await clientiService.confirmCallBonusBooking(targetId);
      if (callBonusResponseModal) {
        setCallBonusResponseModal(null);
      } else {
        setShowCallBonusModal(false);
      }
      fetchCallBonusHistory();
    } catch (err) {
      console.error('Error confirming booking:', err);
      alert('Errore nella conferma. Riprova.');
    } finally {
      setConfirmingBooking(false);
    }
  };

  const handleDeclineCallBonus = async () => {
    if (!callBonusResponseModal) return;
    setDecliningCallBonus(true);
    try {
      await clientiService.respondCallBonusInterest(callBonusResponseModal.id, false);
      setCallBonusResponseModal(null);
      setCallBonusInterestStep('ask');
      fetchCallBonusHistory();
    } catch (err) {
      console.error('Error declining call bonus:', err);
      alert('Errore nel rifiuto. Riprova.');
    } finally {
      setDecliningCallBonus(false);
    }
  };

  const handleConfirmCallBonusInterest = async () => {
    if (!callBonusResponseModal) return;
    setConfirmingBooking(true);
    try {
      await clientiService.respondCallBonusInterest(callBonusResponseModal.id, true);
      setCallBonusResponseModal(null);
      setCallBonusInterestStep('ask');
      fetchCallBonusHistory();
    } catch (err) {
      console.error('Error confirming interest:', err);
      alert('Errore nella conferma interesse. Riprova.');
    } finally {
      setConfirmingBooking(false);
    }
  };

  const fetchStoricoNutrizione = async () => {
    setLoadingStoricoNutrizione(true);
    try {
      const [statoRes, chatRes] = await Promise.all([
        clientiService.getStoricoStati(id, 'nutrizione'),
        clientiService.getStoricoStati(id, 'chat_nutrizione'),
      ]);
      setStoricoStatoNutrizione(statoRes.storico || []);
      setStoricoChatNutrizione(chatRes.storico || []);
    } catch (err) {
      console.error('Error fetching nutrition state history:', err);
    } finally {
      setLoadingStoricoNutrizione(false);
    }
  };

  const fetchStoricoCoaching = async () => {
    setLoadingStoricoCoaching(true);
    try {
      const [statoRes, chatRes] = await Promise.all([
        clientiService.getStoricoStati(id, 'coach'),
        clientiService.getStoricoStati(id, 'chat_coaching'),
      ]);
      setStoricoStatoCoaching(statoRes.storico || []);
      setStoricoChatCoaching(chatRes.storico || []);
    } catch (err) {
      console.error('Error fetching coaching state history:', err);
    } finally {
      setLoadingStoricoCoaching(false);
    }
  };

  const fetchStoricoPsicologia = async () => {
    setLoadingStoricoPsicologia(true);
    try {
      const [statoRes, chatRes] = await Promise.all([
        clientiService.getStoricoStati(id, 'psicologia'),
        clientiService.getStoricoStati(id, 'chat_psicologia'),
      ]);
      setStoricoStatoPsicologia(statoRes.storico || []);
      setStoricoChatPsicologia(chatRes.storico || []);
    } catch (err) {
      console.error('Error fetching psicologia state history:', err);
    } finally {
      setLoadingStoricoPsicologia(false);
    }
  };

  // ==================== PSICOLOGIA FUNCTIONS ====================

  const fetchAnamnesiPsicologia = async () => {
    setLoadingAnamnesiPsicologia(true);
    try {
      const response = await clientiService.getAnamnesi(id, 'psicologia');
      if (response.success && response.anamnesi) {
        setAnamnesiPsicologia(response.anamnesi);
        setAnamnesiPsicologiaContent(response.anamnesi.content || '');
      } else {
        setAnamnesiPsicologia(null);
        setAnamnesiPsicologiaContent('');
      }
    } catch (err) {
      console.error('Error fetching psicologia anamnesi:', err);
      setAnamnesiPsicologia(null);
      setAnamnesiPsicologiaContent('');
    } finally {
      setLoadingAnamnesiPsicologia(false);
    }
  };

  const handleSaveAnamnesiPsicologia = async () => {
    if (!canManagePsychologySection) {
      setError('Salvataggio anamnesi psicologia non consentito per il ruolo corrente.');
      return;
    }
    if (!anamnesiPsicologiaContent.trim()) {
      alert('Inserisci il contenuto dell\'anamnesi');
      return;
    }
    setSavingAnamnesiPsicologia(true);
    try {
      await clientiService.saveAnamnesi(id, 'psicologia', anamnesiPsicologiaContent);
      fetchAnamnesiPsicologia();
    } catch (err) {
      console.error('Error saving psicologia anamnesi:', err);
      alert('Errore durante il salvataggio dell\'anamnesi');
    } finally {
      setSavingAnamnesiPsicologia(false);
    }
  };

  const fetchDiarioPsicologia = async () => {
    setLoadingDiarioPsicologia(true);
    try {
      const response = await clientiService.getDiaryEntries(id, 'psicologia');
      setDiarioPsicologiaEntries(response.entries || []);
    } catch (err) {
      console.error('Error fetching psicologia diary:', err);
      setDiarioPsicologiaEntries([]);
    } finally {
      setLoadingDiarioPsicologia(false);
    }
  };

  const handleOpenDiarioPsicologiaModal = (entry = null) => {
    if (!canManagePsychologySection) {
      setError('Modifica diario psicologia non consentita per il ruolo corrente.');
      return;
    }
    if (entry) {
      setDiarioPsicologiaForm({
        id: entry.id,
        entry_date: entry.entry_date || '',
        content: entry.content || ''
      });
    } else {
      setDiarioPsicologiaForm({
        id: null,
        entry_date: new Date().toISOString().split('T')[0],
        content: ''
      });
    }
    setShowDiarioPsicologiaModal(true);
  };

  const handleSaveDiarioPsicologia = async () => {
    if (!canManagePsychologySection) {
      setError('Salvataggio diario psicologia non consentito per il ruolo corrente.');
      return;
    }
    if (!diarioPsicologiaForm.entry_date || !diarioPsicologiaForm.content.trim()) {
      alert('Compila data e contenuto');
      return;
    }
    setSavingDiarioPsicologia(true);
    try {
      if (diarioPsicologiaForm.id) {
        await clientiService.updateDiaryEntry(
          id,
          'psicologia',
          diarioPsicologiaForm.id,
          diarioPsicologiaForm.content,
          diarioPsicologiaForm.entry_date
        );
      } else {
        await clientiService.createDiaryEntry(
          id,
          'psicologia',
          diarioPsicologiaForm.content,
          diarioPsicologiaForm.entry_date
        );
      }
      setShowDiarioPsicologiaModal(false);
      setDiarioPsicologiaForm({ id: null, entry_date: '', content: '' });
      fetchDiarioPsicologia();
    } catch (err) {
      console.error('Error saving psicologia diary entry:', err);
      alert('Errore durante il salvataggio');
    } finally {
      setSavingDiarioPsicologia(false);
    }
  };

  const handleDeleteDiarioPsicologia = async (entryId) => {
    if (!canManagePsychologySection) {
      setError('Eliminazione diario psicologia non consentita per il ruolo corrente.');
      return;
    }
    if (!confirm('Sei sicuro di voler eliminare questa nota?')) return;
    try {
      await clientiService.deleteDiaryEntry(id, 'psicologia', entryId);
      fetchDiarioPsicologia();
    } catch (err) {
      console.error('Error deleting psicologia diary entry:', err);
      alert('Errore durante l\'eliminazione');
    }
  };

  const fetchMealPlans = async () => {
    setLoadingMealPlans(true);
    try {
      const response = await clientiService.getMealPlans(id);
      setMealPlans(response.plans || []);
    } catch (err) {
      console.error('Error fetching meal plans:', err);
    } finally {
      setLoadingMealPlans(false);
    }
  };

  const handleAddMealPlan = async () => {
    if (!canManageNutritionSection) {
      setError('Gestione piano alimentare non consentita per il ruolo corrente.');
      return;
    }
    if (!mealPlanForm.start_date || !mealPlanForm.end_date) {
      alert('Inserisci le date di inizio e fine');
      return;
    }
    if (!mealPlanFile) {
      alert('Seleziona un file PDF per il piano alimentare');
      return;
    }

    setSavingMealPlan(true);
    try {
      const formData = new FormData();
      formData.append('name', mealPlanForm.name || '');
      formData.append('start_date', mealPlanForm.start_date);
      formData.append('end_date', mealPlanForm.end_date);
      formData.append('notes', mealPlanForm.notes || '');
      formData.append('piano_alimentare_file', mealPlanFile);

      // Get CSRF token from cookie
      const csrfToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_access_token=') || row.startsWith('csrf_token='))
        ?.split('=')[1];

      const headers = {};
      if (csrfToken) {
        headers['X-CSRF-TOKEN'] = csrfToken;
      }

      const response = await fetch(`/customers/${id}/nutrition/add`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
        headers,
      });

      if (!response.ok) {
        const text = await response.text();
        console.error('Server response:', response.status, text);
        try {
          const errData = JSON.parse(text);
          alert(errData.error || `Errore ${response.status}: ${text}`);
        } catch {
          alert(`Errore ${response.status}: ${text.substring(0, 200)}`);
        }
        return;
      }

      const data = await response.json();
      if (data.ok || data.plan_id) {
        setShowAddMealPlanModal(false);
        setMealPlanForm({ name: '', start_date: '', end_date: '', notes: '' });
        setMealPlanFile(null);
        fetchMealPlans();
      } else {
        alert(data.error || 'Errore durante il salvataggio');
      }
    } catch (err) {
      console.error('Error adding meal plan:', err);
      alert('Errore durante il salvataggio del piano alimentare: ' + err.message);
    } finally {
      setSavingMealPlan(false);
    }
  };

  // Preview meal plan PDF
  const handlePreviewPlan = (plan) => {
    setSelectedPlan(plan);
    setShowPreviewPlanModal(true);
  };

  // Open edit modal for a meal plan
  const handleOpenEditPlan = (plan) => {
    if (!canManageNutritionSection) {
      setError('Modifica piano alimentare non consentita per il ruolo corrente.');
      return;
    }
    setSelectedPlan(plan);
    setEditPlanForm({
      start_date: plan.start_date || '',
      end_date: plan.end_date || '',
      notes: plan.notes || '',
      change_reason: '',
    });
    setEditPlanFile(null);
    setShowEditPlanModal(true);
  };

  // Update existing meal plan
  const handleUpdateMealPlan = async () => {
    if (!canManageNutritionSection) {
      setError('Aggiornamento piano alimentare non consentito per il ruolo corrente.');
      return;
    }
    if (!selectedPlan) return;

    if (!editPlanForm.start_date || !editPlanForm.end_date) {
      alert('Inserisci le date di inizio e fine');
      return;
    }

    setSavingMealPlan(true);
    try {
      const formData = new FormData();
      formData.append('plan_id', selectedPlan.id);
      formData.append('start_date', editPlanForm.start_date);
      formData.append('end_date', editPlanForm.end_date);
      formData.append('notes', editPlanForm.notes || '');
      formData.append('change_reason', editPlanForm.change_reason || '');
      if (editPlanFile) {
        formData.append('piano_alimentare_file', editPlanFile);
      }

      await clientiService.updateMealPlan(id, formData);
      setShowEditPlanModal(false);
      setSelectedPlan(null);
      setEditPlanForm({ start_date: '', end_date: '', notes: '', change_reason: '' });
      setEditPlanFile(null);
      fetchMealPlans();
    } catch (err) {
      console.error('Error updating meal plan:', err);
      alert('Errore durante l\'aggiornamento del piano alimentare: ' + (err.response?.data?.error || err.message));
    } finally {
      setSavingMealPlan(false);
    }
  };

  // Fetch meal plan version history
  const fetchMealPlanVersions = async (planId) => {
    setLoadingVersions(true);
    try {
      const response = await clientiService.getMealPlanVersions(id, planId);
      setPlanVersions(response.versions || []);
    } catch (err) {
      console.error('Error fetching meal plan versions:', err);
      setPlanVersions([]);
    } finally {
      setLoadingVersions(false);
    }
  };

  // Open version history modal
  const handleViewVersions = (plan) => {
    setSelectedPlan(plan);
    setShowVersionsModal(true);
    fetchMealPlanVersions(plan.id);
  };

  // ==================== ANAMNESI FUNCTIONS ====================

  const fetchAnamnesi = async () => {
    setLoadingAnamnesi(true);
    try {
      const response = await clientiService.getAnamnesi(id, 'nutrizione');
      if (response.success && response.anamnesi) {
        setAnamnesiNutrizione(response.anamnesi);
        const raw = response.anamnesi.content || '';
        // If content was saved as JSON (old 5-section format), merge into single text
        try {
          const parsed = JSON.parse(raw);
          if (parsed && typeof parsed === 'object') {
            const parts = [];
            if (parsed.remota) parts.push(parsed.remota);
            if (parsed.prossima) parts.push(parsed.prossima);
            if (parsed.familiare) parts.push(parsed.familiare);
            if (parsed.stileVita) parts.push(parsed.stileVita);
            if (parsed.terapie) parts.push(parsed.terapie);
            setAnamnesiContent(parts.join('\n\n'));
          } else {
            setAnamnesiContent(raw);
          }
        } catch (_) {
          setAnamnesiContent(raw);
        }
      } else {
        setAnamnesiNutrizione(null);
        setAnamnesiContent('');
      }
    } catch (err) {
      console.error('Error fetching anamnesi:', err);
      setAnamnesiNutrizione(null);
      setAnamnesiContent('');
    } finally {
      setLoadingAnamnesi(false);
    }
  };

  const handleSaveAnamnesi = async () => {
    if (!canManageNutritionSection) {
      setError('Salvataggio anamnesi nutrizione non consentito per il ruolo corrente.');
      return;
    }
    if (!anamnesiContent.trim()) {
      alert('Inserisci il contenuto dell\'anamnesi');
      return;
    }
    setSavingAnamnesi(true);
    try {
      await clientiService.saveAnamnesi(id, 'nutrizione', anamnesiContent);
      fetchAnamnesi();
    } catch (err) {
      console.error('Error saving anamnesi:', err);
      alert('Errore durante il salvataggio dell\'anamnesi');
    } finally {
      setSavingAnamnesi(false);
    }
  };

  // ==================== DIARIO FUNCTIONS ====================

  const fetchDiarioEntries = async () => {
    setLoadingDiario(true);
    try {
      const response = await clientiService.getDiaryEntries(id, 'nutrizione');
      if (response.success) {
        setDiarioEntries(response.entries || []);
      }
    } catch (err) {
      console.error('Error fetching diary entries:', err);
      setDiarioEntries([]);
    } finally {
      setLoadingDiario(false);
    }
  };

  const handleOpenDiarioModal = (entry = null) => {
    if (!canManageNutritionSection) {
      setError('Modifica diario nutrizione non consentita per il ruolo corrente.');
      return;
    }
    if (entry) {
      setDiarioForm({
        id: entry.id,
        entry_date: entry.entry_date,
        content: entry.content,
      });
    } else {
      setDiarioForm({
        id: null,
        entry_date: new Date().toISOString().split('T')[0],
        content: '',
      });
    }
    setShowDiarioModal(true);
  };

  const handleSaveDiarioEntry = async () => {
    if (!canManageNutritionSection) {
      setError('Salvataggio diario nutrizione non consentito per il ruolo corrente.');
      return;
    }
    if (!diarioForm.content.trim()) {
      alert('Inserisci il contenuto della nota');
      return;
    }

    setSavingDiario(true);
    try {
      if (diarioForm.id) {
        await clientiService.updateDiaryEntry(id, 'nutrizione', diarioForm.id, diarioForm.content, diarioForm.entry_date);
      } else {
        await clientiService.createDiaryEntry(id, 'nutrizione', diarioForm.content, diarioForm.entry_date);
      }
      setShowDiarioModal(false);
      setDiarioForm({ id: null, entry_date: '', content: '' });
      fetchDiarioEntries();
    } catch (err) {
      console.error('Error saving diary entry:', err);
      alert('Errore durante il salvataggio della nota');
    } finally {
      setSavingDiario(false);
    }
  };

  const handleDeleteDiarioEntry = async (entryId) => {
    if (!canManageNutritionSection) {
      setError('Eliminazione diario nutrizione non consentita per il ruolo corrente.');
      return;
    }
    if (!confirm('Sei sicuro di voler eliminare questa nota?')) return;

    try {
      await clientiService.deleteDiaryEntry(id, 'nutrizione', entryId);
      fetchDiarioEntries();
    } catch (err) {
      console.error('Error deleting diary entry:', err);
      alert('Errore durante l\'eliminazione della nota');
    }
  };

  const handleOpenHistoryModal = async (entry, type) => {
    setLoadingDiaryHistory(true);
    setShowDiaryHistoryModal(true);
    setDiaryHistory([]);
    try {
      const data = await clientiService.getDiaryHistory(id, type, entry.id);
      if (data.success) {
        setDiaryHistory(data.history);
      }
    } catch (err) {
      console.error('Error fetching diary history:', err);
    } finally {
      setLoadingDiaryHistory(false);
    }
  };

  // ==================== COACHING FUNCTIONS ====================

  // Training Plans
  const fetchTrainingPlans = async () => {
    setLoadingTrainingPlans(true);
    try {
      const response = await clientiService.getTrainingPlans(id);
      setTrainingPlans(response.plans || []);
    } catch (err) {
      console.error('Error fetching training plans:', err);
      setTrainingPlans([]);
    } finally {
      setLoadingTrainingPlans(false);
    }
  };

  const handleAddTrainingPlan = async () => {
    if (!canManageCoachingSection) {
      setError('Gestione piano allenamento non consentita per il ruolo corrente.');
      return;
    }
    if (!trainingPlanForm.start_date || !trainingPlanForm.end_date) {
      alert('Inserisci le date di inizio e fine');
      return;
    }
    if (!trainingPlanFile) {
      alert('Seleziona un file PDF per il piano di allenamento');
      return;
    }

    setSavingTrainingPlan(true);
    try {
      const formData = new FormData();
      formData.append('name', trainingPlanForm.name || '');
      formData.append('start_date', trainingPlanForm.start_date);
      formData.append('end_date', trainingPlanForm.end_date);
      formData.append('notes', trainingPlanForm.notes || '');
      formData.append('piano_allenamento_file', trainingPlanFile);

      const data = await clientiService.addTrainingPlan(id, formData);
      if (data.ok || data.plan_id) {
        setShowAddTrainingPlanModal(false);
        setTrainingPlanForm({ name: '', start_date: '', end_date: '', notes: '' });
        setTrainingPlanFile(null);
        fetchTrainingPlans();
      } else {
        alert(data.error || 'Errore durante il salvataggio');
      }
    } catch (err) {
      console.error('Error adding training plan:', err);
      if (err?.response?.data?.error) {
        alert(err.response.data.error);
        return;
      }
      if (err?.response?.status) {
        alert(`Errore ${err.response.status} durante il salvataggio del piano`);
        return;
      }
      const fileSizeMb = trainingPlanFile ? (trainingPlanFile.size / (1024 * 1024)).toFixed(2) : null;
      const isNetworkReset = err?.message?.toLowerCase().includes('failed to fetch');
      if (isNetworkReset) {
        alert(
          `Connessione interrotta dal server durante l'upload (${fileSizeMb ? `${fileSizeMb} MB` : 'dimensione file non disponibile'}). ` +
          'Verifica limite upload lato server/reverse proxy e riprova con un PDF più piccolo.'
        );
      } else {
        alert('Errore durante il salvataggio del piano: ' + err.message);
      }
    } finally {
      setSavingTrainingPlan(false);
    }
  };

  const handlePreviewTrainingPlan = (plan) => {
    setSelectedTrainingPlan(plan);
    setShowPreviewTrainingModal(true);
  };

  const handleOpenEditTrainingPlan = (plan) => {
    if (!canManageCoachingSection) {
      setError('Modifica piano allenamento non consentita per il ruolo corrente.');
      return;
    }
    setSelectedTrainingPlan(plan);
    setEditTrainingForm({
      start_date: plan.start_date || '',
      end_date: plan.end_date || '',
      notes: plan.notes || '',
      change_reason: '',
    });
    setEditTrainingFile(null);
    setShowEditTrainingModal(true);
  };

  const handleUpdateTrainingPlan = async () => {
    if (!canManageCoachingSection) {
      setError('Aggiornamento piano allenamento non consentito per il ruolo corrente.');
      return;
    }
    if (!selectedTrainingPlan) return;

    if (!editTrainingForm.start_date || !editTrainingForm.end_date) {
      alert('Inserisci le date di inizio e fine');
      return;
    }

    setSavingTrainingPlan(true);
    try {
      const formData = new FormData();
      formData.append('plan_id', selectedTrainingPlan.id);
      formData.append('start_date', editTrainingForm.start_date);
      formData.append('end_date', editTrainingForm.end_date);
      formData.append('notes', editTrainingForm.notes || '');
      formData.append('change_reason', editTrainingForm.change_reason || '');
      if (editTrainingFile) {
        formData.append('piano_allenamento_file', editTrainingFile);
      }

      await clientiService.updateTrainingPlan(id, formData);
      setShowEditTrainingModal(false);
      setSelectedTrainingPlan(null);
      setEditTrainingForm({ start_date: '', end_date: '', notes: '', change_reason: '' });
      setEditTrainingFile(null);
      fetchTrainingPlans();
    } catch (err) {
      console.error('Error updating training plan:', err);
      alert('Errore durante l\'aggiornamento del piano');
    } finally {
      setSavingTrainingPlan(false);
    }
  };

  const fetchTrainingPlanVersions = async (planId) => {
    setLoadingTrainingVersions(true);
    try {
      const response = await clientiService.getTrainingPlanVersions(id, planId);
      setTrainingVersions(response.versions || []);
    } catch (err) {
      console.error('Error fetching training plan versions:', err);
      setTrainingVersions([]);
    } finally {
      setLoadingTrainingVersions(false);
    }
  };

  const handleViewTrainingVersions = (plan) => {
    setSelectedTrainingPlan(plan);
    setShowTrainingVersionsModal(true);
    fetchTrainingPlanVersions(plan.id);
  };

  // Training Locations
  const fetchTrainingLocations = async () => {
    setLoadingLocations(true);
    try {
      const response = await clientiService.getTrainingLocations(id);
      setTrainingLocations(response.history || []);
    } catch (err) {
      console.error('Error fetching training locations:', err);
      setTrainingLocations([]);
    } finally {
      setLoadingLocations(false);
    }
  };

  const handleOpenLocationModal = (location = null) => {
    if (!canManageCoachingSection) {
      setError('Gestione luoghi allenamento non consentita per il ruolo corrente.');
      return;
    }
    if (location) {
      setLocationForm({
        id: location.id,
        location: location.location,
        start_date: location.start_date || '',
        end_date: location.end_date || '',
        notes: location.notes || '',
        change_reason: '',
      });
    } else {
      setLocationForm({
        id: null,
        location: '',
        start_date: new Date().toISOString().split('T')[0],
        end_date: '',
        notes: '',
        change_reason: '',
      });
    }
    setShowLocationModal(true);
  };

  const handleSaveLocation = async () => {
    if (!canManageCoachingSection) {
      setError('Salvataggio luogo allenamento non consentito per il ruolo corrente.');
      return;
    }
    if (!locationForm.location) {
      alert('Seleziona un luogo di allenamento');
      return;
    }
    if (!locationForm.start_date) {
      alert('Inserisci la data di inizio');
      return;
    }

    setSavingLocation(true);
    try {
      if (locationForm.id) {
        await clientiService.updateTrainingLocation(id, locationForm.id, {
          location: locationForm.location,
          start_date: locationForm.start_date,
          end_date: locationForm.end_date || null,
          notes: locationForm.notes,
          change_reason: locationForm.change_reason,
        });
      } else {
        await clientiService.addTrainingLocation(id, {
          location: locationForm.location,
          start_date: locationForm.start_date,
          end_date: locationForm.end_date || null,
          notes: locationForm.notes,
        });
      }
      setShowLocationModal(false);
      setLocationForm({ id: null, location: '', start_date: '', end_date: '', notes: '', change_reason: '' });
      fetchTrainingLocations();
    } catch (err) {
      console.error('Error saving location:', err);
      alert('Errore durante il salvataggio del luogo');
    } finally {
      setSavingLocation(false);
    }
  };

  // Coaching Anamnesi
  const fetchAnamnesiCoaching = async () => {
    setLoadingAnamnesiCoaching(true);
    try {
      const response = await clientiService.getAnamnesi(id, 'coaching');
      if (response.success && response.anamnesi) {
        setAnamnesiCoaching(response.anamnesi);
        setAnamnesiCoachingContent(response.anamnesi.content || '');
      } else {
        setAnamnesiCoaching(null);
        setAnamnesiCoachingContent('');
      }
    } catch (err) {
      console.error('Error fetching coaching anamnesi:', err);
      setAnamnesiCoaching(null);
      setAnamnesiCoachingContent('');
    } finally {
      setLoadingAnamnesiCoaching(false);
    }
  };

  const handleSaveAnamnesiCoaching = async () => {
    if (!canManageCoachingSection) {
      setError('Salvataggio anamnesi coaching non consentito per il ruolo corrente.');
      return;
    }
    if (!anamnesiCoachingContent.trim()) {
      alert('Inserisci il contenuto dell\'anamnesi');
      return;
    }

    setSavingAnamnesiCoaching(true);
    try {
      await clientiService.saveAnamnesi(id, 'coaching', anamnesiCoachingContent);
      fetchAnamnesiCoaching();
    } catch (err) {
      console.error('Error saving coaching anamnesi:', err);
      alert('Errore durante il salvataggio dell\'anamnesi');
    } finally {
      setSavingAnamnesiCoaching(false);
    }
  };

  // Coaching Diario
  const fetchDiarioCoaching = async () => {
    setLoadingDiarioCoaching(true);
    try {
      const response = await clientiService.getDiaryEntries(id, 'coaching');
      if (response.success) {
        setDiarioCoachingEntries(response.entries || []);
      }
    } catch (err) {
      console.error('Error fetching coaching diary:', err);
      setDiarioCoachingEntries([]);
    } finally {
      setLoadingDiarioCoaching(false);
    }
  };

  const handleOpenDiarioCoachingModal = (entry = null) => {
    if (!canManageCoachingSection) {
      setError('Modifica diario coaching non consentita per il ruolo corrente.');
      return;
    }
    if (entry) {
      setDiarioCoachingForm({
        id: entry.id,
        entry_date: entry.entry_date,
        content: entry.content,
      });
    } else {
      setDiarioCoachingForm({
        id: null,
        entry_date: new Date().toISOString().split('T')[0],
        content: '',
      });
    }
    setShowDiarioCoachingModal(true);
  };

  const handleSaveDiarioCoaching = async () => {
    if (!canManageCoachingSection) {
      setError('Salvataggio diario coaching non consentito per il ruolo corrente.');
      return;
    }
    if (!diarioCoachingForm.content.trim()) {
      alert('Inserisci il contenuto della nota');
      return;
    }

    setSavingDiarioCoaching(true);
    try {
      if (diarioCoachingForm.id) {
        await clientiService.updateDiaryEntry(id, 'coaching', diarioCoachingForm.id, diarioCoachingForm.content, diarioCoachingForm.entry_date);
      } else {
        await clientiService.createDiaryEntry(id, 'coaching', diarioCoachingForm.content, diarioCoachingForm.entry_date);
      }
      setShowDiarioCoachingModal(false);
      setDiarioCoachingForm({ id: null, entry_date: '', content: '' });
      fetchDiarioCoaching();
    } catch (err) {
      console.error('Error saving coaching diary entry:', err);
      alert('Errore durante il salvataggio della nota');
    } finally {
      setSavingDiarioCoaching(false);
    }
  };

  const handleDeleteDiarioCoaching = async (entryId) => {
    if (!canManageCoachingSection) {
      setError('Eliminazione diario coaching non consentita per il ruolo corrente.');
      return;
    }
    if (!confirm('Sei sicuro di voler eliminare questa nota?')) return;

    try {
      await clientiService.deleteDiaryEntry(id, 'coaching', entryId);
      fetchDiarioCoaching();
    } catch (err) {
      console.error('Error deleting coaching diary entry:', err);
      alert('Errore durante l\'eliminazione della nota');
    }
  };

  const fetchProfessionistiHistory = async () => {
    setLoadingHistory(true);
    try {
      const response = await clientiService.getProfessionistiHistory(id);
      setProfessionistiHistory(response.history || []);
    } catch (err) {
      console.error('Error fetching professional history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const fetchAvailableProfessionals = async () => {
    try {
      const [nutri, coach, psico, medico, hm] = await Promise.all([
        teamService.getAvailableProfessionals('nutrizione'),
        teamService.getAvailableProfessionals('coach'),
        teamService.getAvailableProfessionals('psicologia'),
        teamService.getAvailableProfessionals('medico'),
        teamService.getAvailableProfessionals('health_manager'),
      ]);
      setAvailableProfessionals({
        nutrizionista: nutri.professionals || [],
        coach: coach.professionals || [],
        psicologa: psico.professionals || [],
        medico: medico.professionals || [],
        health_manager: hm.professionals || [],
      });
    } catch (err) {
      console.error('Error fetching available professionals:', err);
    }
  };

  // Handle assign professional
  const handleOpenAssignModal = (tipo) => {
    if (!canManageAssignmentType(tipo)) {
      setError('Assegnazione non consentita per il ruolo/specialità corrente.');
      return;
    }
    setAssigningType(tipo);
    setAssignForm({ user_id: '', data_dal: new Date().toISOString().split('T')[0], motivazione_aggiunta: '' });
    setShowAssignModal(true);
  };

  const handleAssignProfessional = async () => {
    if (!assignForm.user_id || !assignForm.data_dal || !assignForm.motivazione_aggiunta) {
      setError('Compila tutti i campi obbligatori');
      return;
    }
    setAssignLoading(true);
    try {
      await clientiService.assignProfessionista(id, {
        tipo_professionista: assigningType,
        user_id: parseInt(assignForm.user_id),
        data_dal: assignForm.data_dal,
        motivazione_aggiunta: assignForm.motivazione_aggiunta,
      });
      setShowAssignModal(false);
      // Refresh data
      const data = await clientiService.getCliente(id);
      setCliente(data.data || data);
      await fetchProfessionistiHistory();
    } catch (err) {
      console.error('Error assigning professional:', err);
      setError('Errore nell\'assegnazione del professionista');
    } finally {
      setAssignLoading(false);
    }
  };

  // Handle interrupt assignment
  const handleOpenInterruptModal = (assignment) => {
    if (!canManageTeamAssignments) {
      setError('Interruzione assegnazioni non consentita per il ruolo Professionista.');
      return;
    }
    if (!canManageAssignmentType(assignment?.tipo_professionista)) {
      setError('Interruzione assegnazione non consentita per il ruolo/specialità corrente.');
      return;
    }
    setInterruptingAssignment(assignment);
    setInterruptForm({ motivazione_interruzione: '' });
    setShowInterruptModal(true);
  };

  const handleInterruptAssignment = async () => {
    if (!interruptForm.motivazione_interruzione) {
      setError('Inserisci la motivazione');
      return;
    }
    setAssignLoading(true);
    try {
      if (interruptingAssignment.has_history && interruptingAssignment.id) {
        await clientiService.interruptProfessionista(id, interruptingAssignment.id, {
          motivazione_interruzione: interruptForm.motivazione_interruzione,
        });
      } else {
        await clientiService.interruptLegacyProfessionista(id, {
          user_id: interruptingAssignment.professionista_id,
          tipo_professionista: interruptingAssignment.tipo_professionista,
          motivazione_interruzione: interruptForm.motivazione_interruzione,
        });
      }
      setShowInterruptModal(false);
      // Refresh data
      const data = await clientiService.getCliente(id);
      setCliente(data.data || data);
      await fetchProfessionistiHistory();
    } catch (err) {
      console.error('Error interrupting assignment:', err);
      setError('Errore nell\'interruzione dell\'assegnazione');
    } finally {
      setAssignLoading(false);
    }
  };

  // Get active professionals by type from history
  const getActiveProfessionals = (tipo) => {
    return professionistiHistory.filter(h => h.tipo_professionista === tipo && h.is_active);
  };

  const getWeeklySnapshotProfessional = (response, role) => {
    const roleMap = {
      nutritionist: {
        idKey: 'nutritionist_user_id',
        nameKey: 'nutritionist_name',
        historyType: 'nutrizionista',
        fallbackLabel: 'Nutrizionista',
      },
      psychologist: {
        idKey: 'psychologist_user_id',
        nameKey: 'psychologist_name',
        historyType: 'psicologa',
        fallbackLabel: 'Psicologo/a',
      },
      coach: {
        idKey: 'coach_user_id',
        nameKey: 'coach_name',
        historyType: 'coach',
        fallbackLabel: 'Coach',
      },
    };

    const config = roleMap[role];
    if (!config) return null;

    const professionalId = response?.[config.idKey];
    const professionalName = response?.[config.nameKey];

    const fromHistory = professionalId
      ? professionistiHistory.find(
        (h) =>
          h.tipo_professionista === config.historyType &&
            Number(h.professionista_id) === Number(professionalId),
      )
      : null;

    const activeFallback = getActiveProfessionals(config.historyType)[0];

    return {
      assignment: fromHistory || activeFallback || null,
      name: professionalName || fromHistory?.professionista_nome || activeFallback?.professionista_nome || config.fallbackLabel,
    };
  };

  // Get history for timeline (sorted by date desc)
  const getTimelineHistory = () => {
    return [...professionistiHistory].sort((a, b) => {
      const dateA = new Date(a.data_dal?.split('/').reverse().join('-') || 0);
      const dateB = new Date(b.data_dal?.split('/').reverse().join('-') || 0);
      return dateB - dateA;
    });
  };

  const populateForm = (c) => {
    setFormData({
      nome_cognome: c.nome_cognome || c.nomeCognome || '',
      data_di_nascita: c.data_di_nascita || c.dataDiNascita || '',
      genere: c.genere || '',
      indirizzo: c.indirizzo || '',
      paese: c.paese || '',
      professione: c.professione || '',
      professione_note: c.professione_note || c.professioneNote || '',
      origine: c.origine || '',
      mail: c.mail || c.email || '',
      numero_telefono: c.numero_telefono || c.numeroTelefono || '',
      storia_cliente: c.storia_cliente || c.storiaCliente || '',
      problema: c.problema || '',
      paure: c.paure || '',
      conseguenze: c.conseguenze || '',
      stato_cliente: c.stato_cliente || c.statoCliente || '',
      stato_cliente_data: c.stato_cliente_data || c.statoClienteData || '',
      programma_attuale: c.programma_attuale || c.programmaAttuale || '',
      tipologia_cliente: c.tipologia_cliente || c.tipologiaCliente || '',
      data_inizio_abbonamento: c.data_inizio_abbonamento || c.dataInizioAbbonamento || '',
      durata_programma_giorni: c.durata_programma_giorni ?? c.durataProgrammaGiorni ?? '',
      data_rinnovo: c.data_rinnovo || c.dataRinnovo || '',
      data_inizio_nutrizione: c.data_inizio_nutrizione || c.dataInizioNutrizione || '',
      durata_nutrizione_giorni: c.durata_nutrizione_giorni ?? c.durataNutrizioneGiorni ?? '',
      data_scadenza_nutrizione: c.data_scadenza_nutrizione || c.dataScadenzaNutrizione || '',
      data_inizio_coach: c.data_inizio_coach || c.dataInizioCoach || '',
      durata_coach_giorni: c.durata_coach_giorni ?? c.durataCoachGiorni ?? '',
      data_scadenza_coach: c.data_scadenza_coach || c.dataScadenzaCoach || '',
      data_inizio_psicologia: c.data_inizio_psicologia || c.dataInizioPsicologia || '',
      durata_psicologia_giorni: c.durata_psicologia_giorni ?? c.durataPsicologiaGiorni ?? '',
      data_scadenza_psicologia: c.data_scadenza_psicologia || c.dataScadenzaPsicologia || '',
      modalita_pagamento: c.modalita_pagamento || c.modalitaPagamento || '',
      rate_cliente_sales: c.rate_cliente_sales || c.rateClienteSales || '',
      note_rinnovo: c.note_rinnovo || c.noteRinnovo || '',
      stato_nutrizione: c.stato_nutrizione || c.statoNutrizione || '',
      stato_nutrizione_data: c.stato_nutrizione_data || c.statoNutrizioneData || '',
      stato_coach: c.stato_coach || c.statoCoach || '',
      stato_coach_data: c.stato_coach_data || c.statoCoachData || '',
      stato_psicologia: c.stato_psicologia || c.statoPsicologia || '',
      stato_psicologia_data: c.stato_psicologia_data || c.statoPsicologiaData || '',
      check_day: c.check_day || c.checkDay || '',
      di_team: c.di_team || c.diTeam || '',
      figura_di_riferimento: c.figura_di_riferimento || c.figuraDiRiferimento || '',
      alert: c.alert || false,
      call_iniziale_nutrizionista: c.call_iniziale_nutrizionista || c.callInizialeNutrizionista || false,
      data_call_iniziale_nutrizionista: c.data_call_iniziale_nutrizionista || c.dataCallInizialeNutrizionista || '',
      reach_out_nutrizione: c.reach_out_nutrizione || c.reachOutNutrizione || '',
      stato_cliente_chat_nutrizione: c.stato_cliente_chat_nutrizione || c.statoClienteChatNutrizione || '',
      // Patologie - Lista completa
      nessuna_patologia: c.nessuna_patologia || c.nessunaPatologia || false,
      patologia_ibs: c.patologia_ibs || c.patologiaIbs || false,
      patologia_reflusso: c.patologia_reflusso || c.patologiaReflusso || false,
      patologia_gastrite: c.patologia_gastrite || c.patologiaGastrite || false,
      patologia_dca: c.patologia_dca || c.patologiaDca || false,
      patologia_insulino_resistenza: c.patologia_insulino_resistenza || c.patologiaInsulinoResistenza || false,
      patologia_diabete: c.patologia_diabete || c.patologiaDiabete || false,
      patologia_dislipidemie: c.patologia_dislipidemie || c.patologiaDislipidemie || false,
      patologia_steatosi_epatica: c.patologia_steatosi_epatica || c.patologiaSteatosiEpatica || false,
      patologia_ipertensione: c.patologia_ipertensione || c.patologiaIpertensione || false,
      patologia_pcos: c.patologia_pcos || c.patologiaPcos || false,
      patologia_endometriosi: c.patologia_endometriosi || c.patologiaEndometriosi || false,
      patologia_obesita_sindrome: c.patologia_obesita_sindrome || c.patologiaObesitaSindrome || false,
      patologia_osteoporosi: c.patologia_osteoporosi || c.patologiaOsteoporosi || false,
      patologia_diverticolite: c.patologia_diverticolite || c.patologiaDiverticolite || false,
      patologia_crohn: c.patologia_crohn || c.patologiaCrohn || false,
      patologia_stitichezza: c.patologia_stitichezza || c.patologiaStitichezza || false,
      patologia_tiroidee: c.patologia_tiroidee || c.patologiaTiroidee || false,
      patologia_altro_check: c.patologia_altro_check || c.patologiaAltroCheck || (!!c.patologia_altro) || false,
      patologia_altro: c.patologia_altro || c.patologiaAltro || '',
      storia_nutrizione: c.storia_nutrizione || c.storiaNutrizione || '',
      note_extra_nutrizione: c.note_extra_nutrizione || c.noteExtraNutrizione || '',
      alert_nutrizione: c.alert_nutrizione || c.alertNutrizione || '',
      call_iniziale_coach: c.call_iniziale_coach || c.callInizialeCoach || false,
      data_call_iniziale_coach: c.data_call_iniziale_coach || c.dataCallInizialeCoach || '',
      reach_out_coaching: c.reach_out_coaching || c.reachOutCoaching || '',
      stato_cliente_chat_coaching: c.stato_cliente_chat_coaching || c.statoClienteChatCoaching || '',
      luogo_di_allenamento: c.luogo_di_allenamento || c.luogoDiAllenamento || '',
      storia_coach: c.storia_coach || c.storiaCoach || '',
      note_extra_coach: c.note_extra_coach || c.noteExtraCoach || '',
      alert_coaching: c.alert_coaching || c.alertCoaching || '',
      call_iniziale_psicologa: c.call_iniziale_psicologa || c.callInizialePsicologa || false,
      data_call_iniziale_psicologia: c.data_call_iniziale_psicologia || c.dataCallInizialePsicologa || '',
      reach_out_psicologia: c.reach_out_psicologia || c.reachOutPsicologia || '',
      stato_cliente_chat_psicologia: c.stato_cliente_chat_psicologia || c.statoClienteChatPsicologia || '',
      storia_psicologica: c.storia_psicologica || c.storiaPsicologica || '',
      note_extra_psicologa: c.note_extra_psicologa || c.noteExtraPsicologa || '',
      alert_psicologia: c.alert_psicologia || c.alertPsicologia || '',
      nessuna_patologia_psico: c.nessuna_patologia_psico || false,
      patologia_psico_dca: c.patologia_psico_dca || false,
      patologia_psico_obesita_psicoemotiva: c.patologia_psico_obesita_psicoemotiva || false,
      patologia_psico_ansia_umore_cibo: c.patologia_psico_ansia_umore_cibo || false,
      patologia_psico_comportamenti_disfunzionali: c.patologia_psico_comportamenti_disfunzionali || false,
      patologia_psico_immagine_corporea: c.patologia_psico_immagine_corporea || false,
      patologia_psico_psicosomatiche: c.patologia_psico_psicosomatiche || false,
      patologia_psico_relazionali_altro: c.patologia_psico_relazionali_altro || false,
      patologia_psico_altro_check: c.patologia_psico_altro_check || c.patologiaPsicoAltroCheck || (!!c.patologia_psico_altro) || false,
      patologia_psico_altro: c.patologia_psico_altro || c.patologiaPsicoAltro || '',
      sedute_psicologia_comprate: c.sedute_psicologia_comprate ?? 0,
      sedute_psicologia_svolte: c.sedute_psicologia_svolte ?? 0,
    });

    // Check custom professione — se il valore nel DB non corrisponde
    // a nessuna opzione predefinita, seleziona "Altro" e mostra il campo testo
    const allProfessioni = PROFESSIONI_OPTIONS.flatMap(g => g.options);
    if (c.professione && !allProfessioni.includes(c.professione)) {
      setShowProfessioneAltro(true);
      setProfessioneAltro(c.professione);
      setFormData(prev => ({ ...prev, professione: '__ALTRO__' }));
    }
  };

  // Calculate age
  const calculateAge = useCallback((dateStr) => {
    if (!dateStr) return null;
    const birthDate = new Date(dateStr);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    return age >= 0 ? age : null;
  }, []);

  // Handle form change
  const handleInputChange = (field, value) => {
    setFormData(prev => {
      const updated = { ...prev, [field]: value };
      // Auto-calculate data_rinnovo
      if (field === 'data_inizio_abbonamento' || field === 'durata_programma_giorni') {
        const dataInizio = field === 'data_inizio_abbonamento' ? value : prev.data_inizio_abbonamento;
        const durata = field === 'durata_programma_giorni' ? value : prev.durata_programma_giorni;
        if (dataInizio && durata) {
          const startDate = new Date(dataInizio);
          const durataNum = parseInt(durata);
          if (!isNaN(durataNum) && durataNum > 0) {
            startDate.setDate(startDate.getDate() + durataNum);
            updated.data_rinnovo = startDate.toISOString().split('T')[0];
          }
        }
      }
      return updated;
    });
    setSaveSuccess(false);

    if (field === 'professione') {
      if (value === '__ALTRO__') {
        setShowProfessioneAltro(true);
      } else {
        setShowProfessioneAltro(false);
        setProfessioneAltro('');
      }
    }
  };

  // Save form
  const handleSave = async () => {
    setSaving(true);
    setSaveSuccess(false);
    try {
      // Clean data before sending
      const dataToSend = {};

      // Fields that are read-only on the backend (dump_only in schema)
      const readonlyFields = [
        'stato_cliente_data',
        'stato_nutrizione_data',
        'stato_coach_data',
        'stato_psicologia_data',
        'cliente_id',
        'created_at',
        'updated_at',
        'createdAt',
        'updatedAt',
      ];

      // Only send fields that have values, convert empty strings to null for optional fields
      Object.entries(formData).forEach(([key, value]) => {
        // Skip readonly fields
        if (readonlyFields.includes(key)) {
          return;
        }
        if (value === '' || value === null || value === undefined) {
          // Don't send empty values, backend will keep existing
        } else {
          dataToSend[key] = value;
        }
      });

      // Handle custom professione
      if (formData.professione === '__ALTRO__' && professioneAltro) {
        dataToSend.professione = professioneAltro;
      }

      console.log('Saving data:', JSON.stringify(dataToSend, null, 2));
      await clientiService.updateCliente(id, dataToSend);
      setSaveSuccess(true);
      const refreshed = await clientiService.getCliente(id);
      setCliente(refreshed.data || refreshed);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Error saving:', err);
      console.error('Error response:', err.response);
      console.error('Error response data:', JSON.stringify(err.response?.data, null, 2));
      const errorMsg = err.response?.data?.message || err.response?.data?.error || JSON.stringify(err.response?.data) || err.message;
      setError('Errore nel salvataggio: ' + errorMsg);
    } finally {
      setSaving(false);
    }
  };

  // Reset form
  const handleReset = () => {
    if (cliente) {
      populateForm(cliente);
    }
  };

  // Delete
  const handleDelete = async () => {
    if (!canDeleteClientRecord) {
      setError('Eliminazione paziente non consentita.');
      return;
    }
    setDeleting(true);
    try {
      await clientiService.deleteCliente(id);
      navigate('/clienti-lista');
    } catch (err) {
      console.error('Error deleting:', err);
      setError('Errore nella cancellazione');
    } finally {
      setDeleting(false);
      setShowDeleteModal(false);
    }
  };

  // Tabs configuration (must stay before early returns to keep hook order stable)
  const mainTabs = [
    { id: 'anagrafica', label: 'Anagrafica', icon: 'ri-user-line' },
    { id: 'programma', label: 'Programma', icon: 'ri-file-list-3-line' },
    { id: 'team', label: 'Team', icon: 'ri-team-line' },
    { id: 'nutrizione', label: 'Nutrizione', icon: 'ri-heart-pulse-line' },
    { id: 'coaching', label: 'Coaching', icon: 'ri-run-line' },
    { id: 'psicologia', label: 'Psicologia', icon: 'ri-mental-health-line' },
    { id: 'medico', label: 'Medico', icon: 'ri-stethoscope-line' },
    { id: 'check_periodici', label: 'Check Periodici', icon: 'ri-calendar-check-line' },
    { id: 'check_iniziali', label: 'Check Iniziali', icon: 'ri-file-list-2-line' },
    { id: 'tickets', label: 'Ticket', icon: 'ri-ticket-2-line' },
    { id: 'call_bonus', label: 'Call Bonus', icon: 'ri-phone-line' },
  ].filter((tab) => getAllowedMainTabsForUser().has(tab.id));

  useEffect(() => {
    if (!mainTabs.some((tab) => tab.id === activeTab)) {
      setActiveTab(mainTabs[0]?.id || 'anagrafica');
    }
  }, [mainTabs, activeTab]);

  // Loading state
  if (loading) {
    return (
      <div className="cd-loading">
        <div className="cd-spinner"></div>
        <p className="cd-loading-text">Caricamento...</p>
      </div>
    );
  }

  // Error state
  if (error && !cliente) {
    return (
      <div className="cd-alert cd-alert-danger">
        <i className="ri-error-warning-line"></i>
        <span>{error}</span>
        <Link to="/clienti-lista" className="cd-btn-back">
          Torna alla Lista
        </Link>
      </div>
    );
  }

  if (!cliente) return null;

  // Normalize data
  const c = {
    id: cliente.cliente_id || cliente.clienteId,
    nome: cliente.nome_cognome || cliente.nomeCognome,
    statoCliente: cliente.stato_cliente || cliente.statoCliente || 'ghost',
    alert: cliente.alert,
    programma: cliente.programma_attuale || cliente.programmaAttuale,
    tipologia: cliente.tipologia_cliente || cliente.tipologiaCliente,
    dataInizio: cliente.data_inizio_abbonamento || cliente.dataInizioAbbonamento,
    dataRinnovo: cliente.data_rinnovo || cliente.dataRinnovo,
    giorniRimanenti: cliente.giorni_rimanenti_calcolati || cliente.giorniRimanentiCalcolati,
    nutrizionistiMultipli: cliente.nutrizionisti_multipli || cliente.nutrizionistiMultipli || [],
    coachesMultipli: cliente.coaches_multipli || cliente.coachesMultipli || [],
    psicologiMultipli: cliente.psicologi_multipli || cliente.psicologiMultipli || [],
    nutrizionista: cliente.nutrizionista,
    coach: cliente.coach,
    psicologa: cliente.psicologa,
    // Team Esterno
    healthManagerUser: cliente.health_manager_user || cliente.healthManagerUser,
    personalConsultant: cliente.personal_consultant || cliente.personalConsultant,
  };

  const age = calculateAge(formData.data_di_nascita);
  const statusGradient = STATUS_GRADIENTS[c.statoCliente] || STATUS_GRADIENTS.ghost;
  const statusColor = STATUS_COLORS[c.statoCliente] || 'secondary';

  // Get initials
  const getInitials = (name) => {
    if (!name) return '??';
    const parts = name.split(' ');
    return parts.length >= 2
      ? `${parts[0][0]}${parts[parts.length-1][0]}`.toUpperCase()
      : name.substring(0, 2).toUpperCase();
  };

  return (
    <>
      <SupportWidget
        pageTitle="Dettaglio Paziente"
        pageDescription="In questa scheda puoi gestire l'intero percorso del paziente, visionare i piani e monitorare i progressi."
        pageIcon={FaUserCircle}
        docsSection="la-scheda-completa-del-paziente"
        onStartTour={handleTourStart}
        brandName="Suite Clinica"
        logoSrc="/suitemind.png"
        accentColor="#85FF00"
      />
      {/* Page Header */}
      <div className="cd-page-header" data-tour="header-dettaglio">
        <div>
          <h4>Dettaglio Paziente</h4>
          <nav aria-label="breadcrumb">
            <ul className="cd-breadcrumb">
              <li>
                <Link to="/clienti-lista">Pazienti</Link>
              </li>
              <li className="cd-breadcrumb-sep">{c.nome}</li>
            </ul>
          </nav>
        </div>
        <div className="cd-header-actions">
          <Link to="/clienti-lista" className="cd-btn-back">
            <i className="ri-arrow-left-line"></i>
            Torna alla Lista
          </Link>
          {canSaveGlobalClientCard && (
            <button className="cd-btn-save" onClick={handleSave} disabled={saving} data-tour="salva-modifiche">
              {saving ? (
                <><span className="spinner-border spinner-border-sm"></span>Salvataggio...</>
              ) : saveSuccess ? (
                <><i className="ri-check-line"></i>Salvato!</>
              ) : (
                <><i className="ri-save-line"></i>Salva Modifiche</>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Success/Error alerts */}
      {saveSuccess && (
        <div className="cd-alert cd-alert-success">
          <i className="ri-check-double-line"></i>
          Modifiche salvate con successo!
        </div>
      )}
      {error && (
        <div className="cd-alert cd-alert-danger">
          <i className="ri-error-warning-line"></i>
          {error}
          <button type="button" className="btn-close" onClick={() => setError(null)}></button>
        </div>
      )}

      <div className="cd-layout">
        {/* Profile Card - Left Column */}
        <div data-tour="profilo-paziente">
          <div className="cd-profile-card">
            {/* Gradient Header */}
            <div
              className="cd-profile-banner"
              style={{ background: statusGradient }}
            >
              {/* Status badges */}
              <div className="cd-profile-badges">
                <span className={`cd-profile-badge ${c.statoCliente}`}>
                  <i className={`ri-${c.statoCliente === 'attivo' ? 'checkbox-circle' : 'close-circle'}-line`}></i>
                  {STATO_LABELS[c.statoCliente] || c.statoCliente}
                </span>
                {c.alert && (
                  <span className="cd-profile-badge danger">
                    <i className="ri-alarm-warning-line"></i>Alert
                  </span>
                )}
              </div>

              {/* Avatar */}
              <div className="cd-profile-avatar-wrap">
                <div className="cd-profile-avatar">
                  {cliente?.latest_photo_front ? (
                    <img
                      src={cliente.latest_photo_front}
                      alt={c.nome}
                      className="cd-profile-avatar-img"
                      onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                    />
                  ) : null}
                  <span className="cd-profile-avatar-text" style={cliente?.latest_photo_front ? { display: 'none' } : {}}>
                    {getInitials(c.nome)}
                  </span>
                </div>
              </div>
            </div>

            {/* Card Body */}
            <div className="cd-profile-body">
              <h4 className="cd-profile-name">{c.nome}</h4>
              <p className="cd-profile-email">
                {formData.mail || 'Nessuna email'}
              </p>

              {/* Badges */}
              <div className="cd-profile-tags">
                {c.tipologia && (
                  <span className="cd-tag cd-tag-info">
                    {TIPOLOGIA_LABELS[c.tipologia] || c.tipologia}
                  </span>
                )}
                {c.programma && (
                  <span className="cd-tag cd-tag-primary">
                    {c.programma}
                  </span>
                )}
              </div>

              {/* Quick Stats */}
              <div className="cd-stats-grid">
                <div className="cd-stat-box">
                  <div className="cd-stat-box-label">ID Paziente</div>
                  <div className="cd-stat-box-value">#{c.id}</div>
                </div>
                <div className="cd-stat-box">
                  <div className="cd-stat-box-label">Età</div>
                  <div className="cd-stat-box-value">{age ? `${age} anni` : '-'}</div>
                </div>
                <div className="cd-stat-box">
                  <div className="cd-stat-box-label">Giorni Rimanenti</div>
                  <div className="cd-stat-box-value">{c.giorniRimanenti || '-'}</div>
                </div>
                <div className="cd-stat-box">
                  <div className="cd-stat-box-label">Rinnovo</div>
                  <div className="cd-stat-box-value">
                    {c.dataRinnovo ? new Date(c.dataRinnovo).toLocaleDateString('it-IT') : '-'}
                  </div>
                </div>
              </div>

              {/* Team Quick View */}
              <div className="cd-team-section-title">Team Assegnato</div>
              <div>
                {/* Health Manager */}
                {(() => {
                  const hmAssignment = getActiveProfessionals('health_manager')[0];
                  const hmUser = c.healthManagerUser || formData.healthManagerUser || (hmAssignment && {
                    id: hmAssignment.professionista_id,
                    full_name: hmAssignment.professionista_nome,
                    email: hmAssignment.professionista_email,
                    avatar_path: hmAssignment.avatar_path,
                  });
                  if (!hmUser) return null;

                  return (
                    <div className="cd-team-group">
                      <div className="cd-team-group-header">
                        <div className="cd-team-icon health-manager">
                          <i className="ri-user-star-line"></i>
                        </div>
                        <span className="cd-team-group-label">Health Manager</span>
                      </div>
                      <div className="cd-team-member">
                        {hmUser.avatar_path ? (
                          <img
                            src={hmUser.avatar_path}
                            alt=""
                            className="cd-team-member-avatar"
                          />
                        ) : (
                          <div
                            className="cd-team-member-initials"
                            style={{ background: '#9333ea' }}
                          >
                            {(hmUser.full_name || hmUser.email || '??')
                              .split(' ')
                              .map(n => n[0])
                              .join('')
                              .substring(0, 2)
                              .toUpperCase()}
                          </div>
                        )}
                        <span className="cd-team-member-name">
                          {hmUser.full_name || hmUser.email}
                        </span>
                      </div>
                    </div>
                  );
                })()}

                {/* Nutrizionisti */}
                {c.nutrizionistiMultipli?.length > 0 && (
                  <div className="cd-team-group">
                    <div className="cd-team-group-header">
                      <div className="cd-team-icon nutrizione">
                        <i className="ri-heart-pulse-line"></i>
                      </div>
                      <span className="cd-team-group-label">Nutrizione</span>
                    </div>
                    {c.nutrizionistiMultipli.map((prof, idx) => (
                      <div key={idx} className="cd-team-member">
                        {prof.avatar_path ? (
                          <img
                            src={prof.avatar_path}
                            alt=""
                            className="cd-team-member-avatar"
                          />
                        ) : (
                          <div
                            className="cd-team-member-initials"
                            style={{ background: '#22c55e' }}
                          >
                            {(prof.full_name || prof.email || '??').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                          </div>
                        )}
                        <span className="cd-team-member-name">{prof.full_name || prof.email}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Coach */}
                {c.coachesMultipli?.length > 0 && (
                  <div className="cd-team-group">
                    <div className="cd-team-group-header">
                      <div className="cd-team-icon coach">
                        <i className="ri-run-line"></i>
                      </div>
                      <span className="cd-team-group-label">Coach</span>
                    </div>
                    {c.coachesMultipli.map((prof, idx) => (
                      <div key={idx} className="cd-team-member">
                        {prof.avatar_path ? (
                          <img
                            src={prof.avatar_path}
                            alt=""
                            className="cd-team-member-avatar"
                          />
                        ) : (
                          <div
                            className="cd-team-member-initials"
                            style={{ background: '#f59e0b' }}
                          >
                            {(prof.full_name || prof.email || '??').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                          </div>
                        )}
                        <span className="cd-team-member-name">{prof.full_name || prof.email}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Psicologi */}
                {c.psicologiMultipli?.length > 0 && (
                  <div className="cd-team-group">
                    <div className="cd-team-group-header">
                      <div className="cd-team-icon psicologia">
                        <i className="ri-mental-health-line"></i>
                      </div>
                      <span className="cd-team-group-label">Psicologia</span>
                    </div>
                    {c.psicologiMultipli.map((prof, idx) => (
                      <div key={idx} className="cd-team-member">
                        {prof.avatar_path ? (
                          <img
                            src={prof.avatar_path}
                            alt=""
                            className="cd-team-member-avatar"
                          />
                        ) : (
                          <div
                            className="cd-team-member-initials"
                            style={{ background: '#06b6d4' }}
                          >
                            {(prof.full_name || prof.email || '??').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                          </div>
                        )}
                        <span className="cd-team-member-name">{prof.full_name || prof.email}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Nessun professionista */}
                {!c.healthManagerUser && !c.nutrizionistiMultipli?.length && !c.coachesMultipli?.length && !c.psicologiMultipli?.length && (
                  <div className="cd-team-empty">Nessun professionista assegnato</div>
                )}
              </div>

              {/* Action Buttons */}
              {canDeleteClientRecord && (
                <button
                  className="cd-btn-delete"
                  onClick={() => setShowDeleteModal(true)}
                >
                  <i className="ri-delete-bin-line"></i>
                  Elimina Paziente
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Details Section - Right Column */}
        <div style={{ minWidth: 0 }}>
          <div className="cd-content-card">
            {/* Tabs Navigation */}
            <div className="cd-tabs-wrapper">
              {tabScroll.canLeft && (
                <button className="cd-tabs-arrow cd-tabs-arrow-left" onClick={() => scrollTabs(-1)} aria-label="Scorri tab a sinistra">
                  <i className="ri-arrow-left-s-line"></i>
                </button>
              )}
              <div className="cd-tabs" data-tour="nav-tabs-dettaglio" ref={tabsRef}>
                {mainTabs.map(tab => (
                  <button
                    key={tab.id}
                    className={`cd-tab ${activeTab === tab.id ? 'active' : ''}`}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    <i className={tab.icon}></i>
                    {tab.label}
                  </button>
                ))}
              </div>
              {tabScroll.canRight && (
                <button className="cd-tabs-arrow cd-tabs-arrow-right" onClick={() => scrollTabs(1)} aria-label="Scorri tab a destra">
                  <i className="ri-arrow-right-s-line"></i>
                </button>
              )}
            </div>

            {/* Tab Content */}
            <div className="cd-tab-content">
              {/* ========== ANAGRAFICA TAB ========== */}
              {activeTab === 'anagrafica' && (
                <div className="cd-form-grid cols-2">
                  {/* Dati Personali */}
                  <div data-tour="anagrafica-dati">
                    <div className="cd-section-title">
                      Dati Personali
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Nome Completo</label>
                      <input
                        type="text"
                        className="cd-input"
                        value={formData.nome_cognome}
                        onChange={(e) => handleInputChange('nome_cognome', e.target.value)}
                      />
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Data di Nascita</label>
                      <DatePicker
                        className="cd-input"
                        value={formData.data_di_nascita}
                        onChange={(e) => handleInputChange('data_di_nascita', e.target.value)}
                      />
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Genere</label>
                      <select
                        className="cd-select"
                        value={formData.genere}
                        onChange={(e) => handleInputChange('genere', e.target.value)}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(GENERE_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Professione</label>
                      <select
                        className="cd-select"
                        value={formData.professione}
                        onChange={(e) => handleInputChange('professione', e.target.value)}
                      >
                        <option value="">Seleziona professione...</option>
                        {PROFESSIONI_OPTIONS.map((group) => (
                          <optgroup key={group.group} label={group.group}>
                            {group.options.map((opt) => (
                              <option key={opt} value={opt}>
                                {opt === '__ALTRO__' ? 'Altro (specifica)' : opt}
                              </option>
                            ))}
                          </optgroup>
                        ))}
                      </select>
                    </div>
                    {showProfessioneAltro && (
                      <div className="cd-field">
                        <input
                          type="text"
                          className="cd-input"
                          placeholder="Specifica professione..."
                          value={professioneAltro}
                          onChange={(e) => setProfessioneAltro(e.target.value)}
                        />
                      </div>
                    )}
                    <div className="cd-field">
                      <label className="cd-field-label">Origine</label>
                      <input
                        type="text"
                        className="cd-input"
                        value={formData.origine}
                        onChange={(e) => handleInputChange('origine', e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Contatti */}
                  <div data-tour="anagrafica-contatti">
                    <div className="cd-section-title">
                      Contatti
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Email</label>
                      <input
                        type="email"
                        className="cd-input"
                        value={formData.mail}
                        onChange={(e) => handleInputChange('mail', e.target.value)}
                      />
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Telefono</label>
                      <input
                        type="tel"
                        className="cd-input"
                        value={formData.numero_telefono}
                        onChange={(e) => handleInputChange('numero_telefono', e.target.value)}
                      />
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Indirizzo</label>
                      <input
                        type="text"
                        className="cd-input"
                        value={formData.indirizzo}
                        onChange={(e) => handleInputChange('indirizzo', e.target.value)}
                      />
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Paese</label>
                      <input
                        type="text"
                        className="cd-input"
                        value={formData.paese}
                        onChange={(e) => handleInputChange('paese', e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Storia */}
                  <div style={{ gridColumn: '1 / -1' }} data-tour="anagrafica-storia">
                    <div className="cd-section-title">
                      Storia e Obiettivi
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Storia del Cliente</label>
                      <textarea
                        className="cd-textarea"
                        rows="3"
                        value={formData.storia_cliente}
                        onChange={(e) => handleInputChange('storia_cliente', e.target.value)}
                      ></textarea>
                    </div>
                    <div className="cd-form-grid cols-3">
                      <div>
                        <label className="cd-field-label">Problema</label>
                        <textarea
                          className="cd-textarea"
                          rows="2"
                          value={formData.problema}
                          onChange={(e) => handleInputChange('problema', e.target.value)}
                        ></textarea>
                      </div>
                      <div>
                        <label className="cd-field-label">Paure</label>
                        <textarea
                          className="cd-textarea"
                          rows="2"
                          value={formData.paure}
                          onChange={(e) => handleInputChange('paure', e.target.value)}
                        ></textarea>
                      </div>
                      <div>
                        <label className="cd-field-label">Conseguenze</label>
                        <textarea
                          className="cd-textarea"
                          rows="2"
                          value={formData.conseguenze}
                          onChange={(e) => handleInputChange('conseguenze', e.target.value)}
                        ></textarea>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ========== PROGRAMMA TAB ========== */}
              {activeTab === 'programma' && (
                <div className="cd-form-grid cols-2">
                  {/* Stato */}
                  <div data-tour="programma-stato">
                    <div className="cd-section-title">
                      Stato Cliente
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Stato</label>
                      <select
                        className="cd-select"
                        value={formData.stato_cliente}
                        onChange={(e) => handleInputChange('stato_cliente', e.target.value)}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(STATO_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Tipologia</label>
                      <select
                        className="cd-select"
                        value={formData.tipologia_cliente}
                        onChange={(e) => handleInputChange('tipologia_cliente', e.target.value)}
                      >
                        <option value="">Seleziona...</option>
                        <option value="a">A</option>
                        <option value="b">B</option>
                        <option value="c">C</option>
                      </select>
                    </div>
                  </div>

                  {/* Programma */}
                  <div>
                    <div className="cd-section-title">
                      Programma
                    </div>
                    <div className="cd-field">
                      <label className="cd-field-label">Programma Attuale</label>
                      <input
                        type="text"
                        className="cd-input"
                        value={formData.programma_attuale}
                        onChange={(e) => handleInputChange('programma_attuale', e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Date abbonamento generali */}
                  <div style={{ gridColumn: '1 / -1' }} data-tour="programma-date">
                    <div className="cd-section-title">
                      Date Abbonamento (generale)
                    </div>
                    <div className="cd-date-plan-card">
                      <div className="cd-date-plan-grid">
                        <div>
                          <label className="cd-field-label">Data Inizio</label>
                          <DatePicker
                            className="cd-input"
                            value={formData.data_inizio_abbonamento}
                            onChange={(e) => handleInputChange('data_inizio_abbonamento', e.target.value)}
                          />
                        </div>
                        <div>
                          <label className="cd-field-label">Durata (giorni)</label>
                          <input
                            type="number"
                            className="cd-input"
                            value={formData.durata_programma_giorni || ''}
                            onChange={(e) => handleInputChange('durata_programma_giorni', e.target.value)}
                            min="0"
                          />
                        </div>
                        <div>
                          <label className="cd-field-label">Data Scadenza</label>
                          <DatePicker
                            className="cd-input disabled"
                            value={formData.data_inizio_abbonamento && formData.durata_programma_giorni
                              ? new Date(new Date(formData.data_inizio_abbonamento).getTime() + Number(formData.durata_programma_giorni) * 86400000).toISOString().split('T')[0]
                              : formData.data_rinnovo || ''}
                            disabled
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Date per piano (Nutrizione, Coach, Psicologia) */}
                  <div style={{ gridColumn: '1 / -1' }} data-tour="programma-date-per-piano">
                    <div className="cd-section-title">
                      Date per piano
                    </div>
                    {/* Nutrizione */}
                    <div className="cd-date-plan-card">
                      <div className="cd-date-plan-label">
                        <i className="ri-heart-pulse-line"></i> Nutrizione
                      </div>
                      <div className="cd-date-plan-grid">
                        <div>
                          <label className="cd-field-label">Data Inizio</label>
                          <DatePicker
                            className="cd-input sm"
                            value={formData.data_inizio_nutrizione || ''}
                            onChange={(e) => handleInputChange('data_inizio_nutrizione', e.target.value)}
                          />
                        </div>
                        <div>
                          <label className="cd-field-label">Durata (giorni)</label>
                          <input
                            type="number"
                            className="cd-input sm"
                            value={formData.durata_nutrizione_giorni || ''}
                            onChange={(e) => handleInputChange('durata_nutrizione_giorni', e.target.value)}
                            min="0"
                          />
                        </div>
                        <div>
                          <label className="cd-field-label">Data Scadenza</label>
                          <DatePicker
                            className="cd-input sm disabled"
                            value={formData.data_inizio_nutrizione && formData.durata_nutrizione_giorni
                              ? new Date(new Date(formData.data_inizio_nutrizione).getTime() + Number(formData.durata_nutrizione_giorni) * 86400000).toISOString().split('T')[0]
                              : formData.data_scadenza_nutrizione || ''}
                            disabled
                          />
                        </div>
                      </div>
                    </div>
                    {/* Coach */}
                    <div className="cd-date-plan-card">
                      <div className="cd-date-plan-label">
                        <i className="ri-run-line"></i> Coach
                      </div>
                      <div className="cd-date-plan-grid">
                        <div>
                          <label className="cd-field-label">Data Inizio</label>
                          <DatePicker
                            className="cd-input sm"
                            value={formData.data_inizio_coach || ''}
                            onChange={(e) => handleInputChange('data_inizio_coach', e.target.value)}
                          />
                        </div>
                        <div>
                          <label className="cd-field-label">Durata (giorni)</label>
                          <input
                            type="number"
                            className="cd-input sm"
                            value={formData.durata_coach_giorni || ''}
                            onChange={(e) => handleInputChange('durata_coach_giorni', e.target.value)}
                            min="0"
                          />
                        </div>
                        <div>
                          <label className="cd-field-label">Data Scadenza</label>
                          <DatePicker
                            className="cd-input sm disabled"
                            value={formData.data_inizio_coach && formData.durata_coach_giorni
                              ? new Date(new Date(formData.data_inizio_coach).getTime() + Number(formData.durata_coach_giorni) * 86400000).toISOString().split('T')[0]
                              : formData.data_scadenza_coach || ''}
                            disabled
                          />
                        </div>
                      </div>
                    </div>
                    {/* Psicologia */}
                    <div className="cd-date-plan-card">
                      <div className="cd-date-plan-label">
                        <i className="ri-mental-health-line"></i> Psicologia
                      </div>
                      <div className="cd-date-plan-grid">
                        <div>
                          <label className="cd-field-label">Data Inizio</label>
                          <DatePicker
                            className="cd-input sm"
                            value={formData.data_inizio_psicologia || ''}
                            onChange={(e) => handleInputChange('data_inizio_psicologia', e.target.value)}
                          />
                        </div>
                        <div>
                          <label className="cd-field-label">Durata (giorni)</label>
                          <input
                            type="number"
                            className="cd-input sm"
                            value={formData.durata_psicologia_giorni || ''}
                            onChange={(e) => handleInputChange('durata_psicologia_giorni', e.target.value)}
                            min="0"
                          />
                        </div>
                        <div>
                          <label className="cd-field-label">Data Scadenza</label>
                          <DatePicker
                            className="cd-input sm disabled"
                            value={formData.data_inizio_psicologia && formData.durata_psicologia_giorni
                              ? new Date(new Date(formData.data_inizio_psicologia).getTime() + Number(formData.durata_psicologia_giorni) * 86400000).toISOString().split('T')[0]
                              : formData.data_scadenza_psicologia || ''}
                            disabled
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ========== TEAM TAB ========== */}
              {activeTab === 'team' && (
                <div className="row g-4">
                  {/* Sub-tabs for Team Clinico / Team Esterno */}
                  <div className="col-12" data-tour="team-subtabs">
                    <ScrollableSubtabs style={{ marginBottom: '20px' }}>
                      <button
                        className={`cd-subtab ${teamSubTab === 'clinico' ? 'active green' : ''}`}
                        onClick={() => setTeamSubTab('clinico')}
                      >
                        <i className="ri-heart-pulse-line"></i>
                        Team Clinico
                      </button>
                      {canViewExternalTeamTab && (
                        <button
                          className={`cd-subtab ${teamSubTab === 'esterno' ? 'active blue' : ''}`}
                          onClick={() => setTeamSubTab('esterno')}
                        >
                          <i className="ri-team-line"></i>
                          Team Esterno
                        </button>
                      )}
                    </ScrollableSubtabs>
                  </div>

                  {/* ===== TEAM CLINICO ===== */}
                  {teamSubTab === 'clinico' && (
                    <div data-tour="team-clinico-wrapper">
                      <div>
                      {/* Professionisti Clinici */}
                      <div>
                        <div className="cd-section-title">
                          Professionisti Assegnati
                        </div>
                        {loadingHistory ? (
                          <div className="cd-loading">
                            <div className="cd-spinner"></div>
                            <p className="cd-loading-text">Caricamento...</p>
                          </div>
                        ) : (
                          <div className="cd-assignment-grid">
                            {/* Nutrizionisti */}
                            <div>
                              <div className="cd-inner-card">
                                <div className="cd-inner-card-body">
                                  <div className="cd-inner-card-header-row">
                                    <div className="cd-inner-card-header-left">
                                      <div className="cd-icon-circle success">
                                        <i className="ri-heart-pulse-line"></i>
                                      </div>
                                      <span className="cd-inner-card-title">Nutrizionista</span>
                                    </div>
                                    {canManageAssignmentType('nutrizionista') && (
                                      <button
                                        className="cd-btn-icon-sm"
                                        onClick={() => handleOpenAssignModal('nutrizionista')}
                                        title="Aggiungi Nutrizionista"
                                        style={{ background: 'rgba(34, 197, 94, 0.1)', color: '#22c55e' }}
                                      >
                                        <i className="ri-add-line"></i>
                                      </button>
                                    )}
                                  </div>
                                  {getActiveProfessionals('nutrizionista').length > 0 ? (
                                    getActiveProfessionals('nutrizionista').map((assignment, idx) => (
                                      <div key={idx} className="cd-assignment-row">
                                        <div className="cd-assignment-info">
                                          {assignment.avatar_path ? (
                                            <img
                                              src={assignment.avatar_path}
                                              alt=""
                                              className="cd-prof-avatar"
                                            />
                                          ) : (
                                            <div className="cd-prof-initials" style={{ background: '#22c55e' }}>
                                              {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                          <div>
                                            <span className="cd-prof-name">{assignment.professionista_nome}</span>
                                            <span className="cd-prof-date">dal {assignment.data_dal}</span>
                                          </div>
                                        </div>
                                        {canManageAssignmentType('nutrizionista') && (
                                          <button
                                            className="cd-btn-remove"
                                            onClick={() => handleOpenInterruptModal(assignment)}
                                            title="Rimuovi"
                                          >
                                            <i className="ri-close-line"></i>
                                          </button>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <span className="cd-empty-text">Nessuno assegnato</span>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Coach */}
                            <div>
                              <div className="cd-inner-card">
                                <div className="cd-inner-card-body">
                                  <div className="cd-inner-card-header-row">
                                    <div className="cd-inner-card-header-left">
                                      <div className="cd-icon-circle warning">
                                        <i className="ri-run-line"></i>
                                      </div>
                                      <span className="cd-inner-card-title">Coach</span>
                                    </div>
                                    {canManageAssignmentType('coach') && (
                                      <button
                                        className="cd-btn-icon-sm"
                                        onClick={() => handleOpenAssignModal('coach')}
                                        title="Aggiungi Coach"
                                        style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b' }}
                                      >
                                        <i className="ri-add-line"></i>
                                      </button>
                                    )}
                                  </div>
                                  {getActiveProfessionals('coach').length > 0 ? (
                                    getActiveProfessionals('coach').map((assignment, idx) => (
                                      <div key={idx} className="cd-assignment-row">
                                        <div className="cd-assignment-info">
                                          {assignment.avatar_path ? (
                                            <img
                                              src={assignment.avatar_path}
                                              alt=""
                                              className="cd-prof-avatar"
                                            />
                                          ) : (
                                            <div className="cd-prof-initials" style={{ background: '#f59e0b' }}>
                                              {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                          <div>
                                            <span className="cd-prof-name">{assignment.professionista_nome}</span>
                                            <span className="cd-prof-date">dal {assignment.data_dal}</span>
                                          </div>
                                        </div>
                                        {canManageAssignmentType('coach') && (
                                          <button
                                            className="cd-btn-remove"
                                            onClick={() => handleOpenInterruptModal(assignment)}
                                            title="Rimuovi"
                                          >
                                            <i className="ri-close-line"></i>
                                          </button>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <span className="cd-empty-text">Nessuno assegnato</span>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Psicologi */}
                            <div>
                              <div className="cd-inner-card">
                                <div className="cd-inner-card-body">
                                  <div className="cd-inner-card-header-row">
                                    <div className="cd-inner-card-header-left">
                                      <div className="cd-icon-circle info">
                                        <i className="ri-mental-health-line"></i>
                                      </div>
                                      <span className="cd-inner-card-title">Psicologo</span>
                                    </div>
                                    {canManageAssignmentType('psicologa') && (
                                      <button
                                        className="cd-btn-icon-sm"
                                        onClick={() => handleOpenAssignModal('psicologa')}
                                        title="Aggiungi Psicologo"
                                        style={{ background: 'rgba(6, 182, 212, 0.1)', color: '#06b6d4' }}
                                      >
                                        <i className="ri-add-line"></i>
                                      </button>
                                    )}
                                  </div>
                                  {getActiveProfessionals('psicologa').length > 0 ? (
                                    getActiveProfessionals('psicologa').map((assignment, idx) => (
                                      <div key={idx} className="cd-assignment-row">
                                        <div className="cd-assignment-info">
                                          {assignment.avatar_path ? (
                                            <img
                                              src={assignment.avatar_path}
                                              alt=""
                                              className="cd-prof-avatar"
                                            />
                                          ) : (
                                            <div className="cd-prof-initials" style={{ background: '#06b6d4' }}>
                                              {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                          <div>
                                            <span className="cd-prof-name">{assignment.professionista_nome}</span>
                                            <span className="cd-prof-date">dal {assignment.data_dal}</span>
                                          </div>
                                        </div>
                                        {canManageAssignmentType('psicologa') && (
                                          <button
                                            className="cd-btn-remove"
                                            onClick={() => handleOpenInterruptModal(assignment)}
                                            title="Rimuovi"
                                          >
                                            <i className="ri-close-line"></i>
                                          </button>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <span className="cd-empty-text">Nessuno assegnato</span>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Medici */}
                            <div>
                              <div className="cd-inner-card">
                                <div className="cd-inner-card-body">
                                  <div className="cd-inner-card-header-row">
                                    <div className="cd-inner-card-header-left">
                                      <div className="cd-icon-circle danger">
                                        <i className="ri-stethoscope-line"></i>
                                      </div>
                                      <span className="cd-inner-card-title">Medico</span>
                                    </div>
                                    {canManageAssignmentType('medico') && (
                                      <button
                                        className="cd-btn-icon-sm"
                                        onClick={() => handleOpenAssignModal('medico')}
                                        title="Aggiungi Medico"
                                        style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}
                                      >
                                        <i className="ri-add-line"></i>
                                      </button>
                                    )}
                                  </div>
                                  {getActiveProfessionals('medico').length > 0 ? (
                                    getActiveProfessionals('medico').map((assignment, idx) => (
                                      <div key={idx} className="cd-assignment-row">
                                        <div className="cd-assignment-info">
                                          {assignment.avatar_path ? (
                                            <img
                                              src={assignment.avatar_path}
                                              alt=""
                                              className="cd-prof-avatar"
                                            />
                                          ) : (
                                            <div className="cd-prof-initials" style={{ background: '#ef4444' }}>
                                              {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                          <div>
                                            <span className="cd-prof-name">{assignment.professionista_nome}</span>
                                            <span className="cd-prof-date">dal {assignment.data_dal}</span>
                                          </div>
                                        </div>
                                        {canManageAssignmentType('medico') && (
                                          <button
                                            className="cd-btn-remove"
                                            onClick={() => handleOpenInterruptModal(assignment)}
                                            title="Rimuovi"
                                          >
                                            <i className="ri-close-line"></i>
                                          </button>
                                        )}
                                      </div>
                                    ))
                                  ) : (
                                    <span className="cd-empty-text">Nessuno assegnato</span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Timeline Storico Assegnazioni - Orizzontale */}
                      <div data-tour="team-timeline" style={{ marginTop: '20px' }}>
                        <div className="cd-section-title">
                          <i className="ri-history-line"></i>
                          Storico Assegnazioni
                        </div>
                        {loadingHistory ? (
                          <div className="cd-loading">
                            <div className="cd-spinner"></div>
                          </div>
                        ) : getTimelineHistory().length > 0 ? (
                          <div className="cd-timeline">
                            {/* Horizontal line */}
                            <div className="cd-timeline-line" style={{ background: 'linear-gradient(to right, #10b981, #3b82f6, #8b5cf6)' }}></div>

                            <div className="cd-timeline-items">
                              {getTimelineHistory().map((item, idx) => {
                                const colorConfig = TIPO_PROFESSIONISTA_COLORS[item.tipo_professionista] || { bg: 'secondary', icon: 'text-secondary' };
                                const icon = TIPO_PROFESSIONISTA_ICONS[item.tipo_professionista] || 'ri-user-line';

                                return (
                                  <div key={idx} className="cd-timeline-item">
                                    {/* Dot on line */}
                                    <div className="cd-timeline-dot-wrap">
                                      <div
                                        className="cd-timeline-dot"
                                        style={{ background: { success: '#22c55e', warning: '#f59e0b', info: '#06b6d4', danger: '#ef4444', primary: '#3b82f6' }[colorConfig.bg] || '#6b7280' }}
                                      >
                                        <i className={icon} style={{ color: 'white' }}></i>
                                      </div>
                                    </div>

                                    {/* Date label */}
                                    <div className="cd-timeline-date">
                                      {item.data_dal || '—'}
                                      {item.data_al && <span style={{ display: 'block' }}>→ {item.data_al}</span>}
                                    </div>

                                    {/* Card */}
                                    <div className={`cd-timeline-card ${!item.is_active ? 'inactive' : ''}`}>
                                      <div>
                                        {/* Status badge */}
                                        <div className="mb-2">
                                          {item.is_active ? (
                                            <span className="cd-timeline-badge" style={{ background: 'rgba(34, 197, 94, 0.1)', color: '#22c55e' }}>Attivo</span>
                                          ) : (
                                            <span className="cd-timeline-badge" style={{ background: 'rgba(107, 114, 128, 0.1)', color: '#6b7280' }}>Concluso</span>
                                          )}
                                        </div>

                                        {/* Avatar */}
                                        <div className="d-flex justify-content-center mb-2">
                                          {item.avatar_path ? (
                                            <img
                                              src={item.avatar_path}
                                              alt=""
                                              className="cd-timeline-card-avatar"
                                            />
                                          ) : (
                                            <div
                                              className="cd-timeline-card-initials"
                                              style={{ background: { success: '#22c55e', warning: '#f59e0b', info: '#06b6d4', danger: '#ef4444', primary: '#3b82f6' }[colorConfig.bg] || '#6b7280' }}
                                            >
                                              {item.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                        </div>

                                        {/* Name */}
                                        <div className="cd-timeline-card-name">
                                          {item.professionista_nome}
                                        </div>

                                        {/* Type badge */}
                                        <span className="cd-badge xs" style={{ background: { success: 'rgba(34, 197, 94, 0.1)', warning: 'rgba(245, 158, 11, 0.1)', info: 'rgba(6, 182, 212, 0.1)', danger: 'rgba(239, 68, 68, 0.1)', primary: 'rgba(59, 130, 246, 0.1)' }[colorConfig.bg] || 'rgba(107, 114, 128, 0.1)', color: { success: '#22c55e', warning: '#f59e0b', info: '#06b6d4', danger: '#ef4444', primary: '#3b82f6' }[colorConfig.bg] || '#6b7280' }}>
                                          {TIPO_PROFESSIONISTA_LABELS[item.tipo_professionista] || item.tipo_professionista}
                                        </span>

                                        {/* Motivazione (tooltip style) */}
                                        {item.motivazione_aggiunta && (
                                          <div className="cd-timeline-motivation">
                                            <span className="text-success">
                                              <i className="ri-add-line me-1"></i>
                                              {item.motivazione_aggiunta.length > 30
                                                ? item.motivazione_aggiunta.substring(0, 30) + '...'
                                                : item.motivazione_aggiunta}
                                            </span>
                                          </div>
                                        )}
                                        {item.motivazione_interruzione && (
                                          <div className="cd-timeline-motivation">
                                            <span className="text-danger">
                                              <i className="ri-close-line me-1"></i>
                                              {item.motivazione_interruzione.length > 30
                                                ? item.motivazione_interruzione.substring(0, 30) + '...'
                                                : item.motivazione_interruzione}
                                            </span>
                                          </div>
                                        )}

                                        {/* Legacy indicator */}
                                        {!item.has_history && (
                                          <div className="mt-1">
                                            <span className="cd-badge xs" style={{ background: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b' }}>
                                              Legacy
                                            </span>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ) : (
                          <div className="cd-empty">
                            <div className="cd-empty-icon"><i className="ri-history-line"></i></div>
                            <p className="cd-empty-text">Nessuna assegnazione registrata</p>
                          </div>
                        )}
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== TEAM ESTERNO ===== */}
                  {canViewExternalTeamTab && teamSubTab === 'esterno' && (
                    <div data-tour="team-esterno">
                      <div className="cd-inner-card">
                        <div className="cd-inner-card-body">
                          <div className="cd-inner-card-header-row">
                            <div className="cd-inner-card-header-left">
                              <div className="cd-icon-circle primary">
                                <i className="ri-user-star-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Health Manager</span>
                            </div>
                            {canManageAssignmentType('health_manager') && (
                              <button
                                className="cd-btn-icon-sm"
                                onClick={() => handleOpenAssignModal('health_manager')}
                                title="Assegna Health Manager"
                                style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6' }}
                              >
                                <i className="ri-add-line"></i>
                              </button>
                            )}
                          </div>
                          {(formData.healthManagerUser || getActiveProfessionals('health_manager')[0]) ? (
                            (() => {
                              const hmAssignment = getActiveProfessionals('health_manager')[0];
                              const hmUser = formData.healthManagerUser || (hmAssignment && {
                                id: hmAssignment.professionista_id,
                                full_name: hmAssignment.professionista_nome,
                                avatar_path: hmAssignment.avatar_path,
                              });
                              if (!hmUser) return null;
                              return (
                                <div className="cd-assignment-row">
                                  <div className="cd-assignment-info">
                                    {hmUser.avatar_path ? (
                                      <img
                                        src={hmUser.avatar_path}
                                        alt=""
                                        className="cd-prof-avatar"
                                      />
                                    ) : (
                                      <div className="cd-prof-initials" style={{ background: '#3b82f6' }}>
                                        {(hmUser.full_name || '')
                                          .split(' ')
                                          .map((n) => n[0])
                                          .join('')
                                          .substring(0, 2)
                                          .toUpperCase() || '??'}
                                      </div>
                                    )}
                                    <div>
                                      <span className="cd-prof-name">{hmUser.full_name || 'Health Manager'}</span>
                                      {hmAssignment?.data_dal && (
                                        <span className="cd-prof-date">dal {hmAssignment.data_dal}</span>
                                      )}
                                    </div>
                                  </div>
                                  {canManageAssignmentType('health_manager') && (
                                    <button
                                      className="cd-btn-remove"
                                      onClick={() => handleOpenInterruptModal(hmAssignment || {
                                        tipo_professionista: 'health_manager',
                                        professionista_id: hmUser.id,
                                        professionista_nome: hmUser.full_name,
                                        avatar_path: hmUser.avatar_path,
                                        data_dal: hmAssignment?.data_dal || null,
                                        is_active: true,
                                        has_history: !!hmAssignment?.id,
                                        id: hmAssignment?.id,
                                      })}
                                      title="Rimuovi"
                                    >
                                      <i className="ri-close-line"></i>
                                    </button>
                                  )}
                                </div>
                              );
                            })()
                          ) : (
                            <span className="cd-empty-text">Nessun Health Manager assegnato</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ========== NUTRIZIONE TAB ========== */}
              {activeTab === 'nutrizione' && (
                <div>
                  {/* Alert Criticità - Sempre in evidenza se presente */}
                  {formData.alert_nutrizione && (
                    <div>
                      <div className="cd-alert cd-alert-danger">
                        <i className="ri-alarm-warning-line"></i>
                        <div>
                          <strong>Alert Nutrizione</strong>
                          <p>{formData.alert_nutrizione}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Sub-tab Navigation - Same style as Team tab */}
                  <div data-tour="nutrizione-subtabs">
                    <ScrollableSubtabs>
                      {[
                        { key: 'panoramica', label: 'Panoramica', icon: 'ri-dashboard-line', color: 'green' },
                        { key: 'setup', label: 'Setup', icon: 'ri-settings-3-line', color: 'blue' },
                        { key: 'piano', label: 'Piano Alimentare', icon: 'ri-restaurant-line', color: 'green' },
                        { key: 'patologie', label: 'Anamnesi', icon: 'ri-heart-pulse-line', color: 'red' },
                        { key: 'diario', label: 'Diario', icon: 'ri-book-2-line', color: 'pink' },
                        { key: 'alert', label: 'Alert', icon: 'ri-alarm-warning-line', color: 'red' },
                        { key: 'vecchie_note', label: 'Vecchie Note', icon: 'ri-archive-line', color: 'secondary' },
                      ].map(({ key, label, icon, color }) => (
                            <button
                              key={key}
                              className={`cd-subtab ${nutrizioneSubTab === key ? `active ${color}` : ''}`}
                              onClick={() => setNutrizioneSubTab(key)}
                            >
                              <i className={icon}></i>
                              {label}
                            </button>
                      ))}
                    </ScrollableSubtabs>
                  </div>

                  {/* ===== PANORAMICA SUB-TAB ===== */}
                  {nutrizioneSubTab === 'panoramica' && (
                    <div data-tour="nutrizione-panoramica">
                      <div className="cd-sections">
                      {/* Nutrizionisti Assegnati - Same style as Team tab */}
                      <div>
                        <div className="cd-section-title">
                          Nutrizionisti Assegnati
                        </div>
                        {loadingHistory ? (
                          <div className="cd-loading">
                            <div className="cd-spinner" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento...</small>
                          </div>
                        ) : (
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-row">
                                <div className="cd-inner-card-header-left">
                                  <div className="cd-icon-circle success lg">
                                    <i className="ri-heart-pulse-line"></i>
                                  </div>
                                  <span className="cd-inner-card-title">Team Nutrizione</span>
                                </div>
                                <span className="cd-badge" style={{ background: 'rgba(34, 197, 94, 0.1)', color: '#22c55e' }}>{getActiveProfessionals('nutrizionista').length} attivi</span>
                              </div>

                              {getActiveProfessionals('nutrizionista').length > 0 ? (
                                <div className="d-flex flex-wrap gap-2">
                                  {getActiveProfessionals('nutrizionista').map((assignment, idx) => (
                                    <div key={idx} className="cd-assignment-row">
                                      {assignment.avatar_path ? (
                                        <img src={assignment.avatar_path} alt="" className="cd-prof-avatar" />
                                      ) : (
                                        <div className="cd-prof-initials lg" style={{ background: '#22c55e' }}>
                                          {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                        </div>
                                      )}
                                      <div>
                                        <span className="cd-prof-name">{assignment.professionista_nome}</span>
                                        <span className="cd-prof-date">dal {assignment.data_dal}</span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="cd-empty-text">Nessun nutrizionista assegnato. Vai alla tab "Team" per assegnare.</p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>


                      {/* Storico Assegnazioni Timeline - Orizzontale come Team tab */}
                      {professionistiHistory.filter(h => h.tipo_professionista === 'nutrizionista').length > 0 && (
                        <div>
                          <div className="cd-section-title">
                            <i className="ri-history-line"></i>
                            Storico Assegnazioni
                          </div>
                          <div className="cd-timeline">
                            {/* Horizontal line */}
                            <div className="cd-timeline-line" style={{ background: 'linear-gradient(to right, #22c55e, #16a34a)' }}></div>

                            <div className="cd-timeline-items">
                              {professionistiHistory
                                .filter(h => h.tipo_professionista === 'nutrizionista')
                                .sort((a, b) => {
                                  const dateA = new Date(a.data_dal?.split('/').reverse().join('-') || 0);
                                  const dateB = new Date(b.data_dal?.split('/').reverse().join('-') || 0);
                                  return dateB - dateA;
                                })
                                .map((item, idx) => (
                                  <div key={idx} className="cd-timeline-item">
                                    {/* Dot on line */}
                                    <div className="cd-timeline-dot-wrap">
                                      <div className="cd-timeline-dot" style={{ background: '#22c55e' }}>
                                        <i className="ri-heart-pulse-line"></i>
                                      </div>
                                    </div>

                                    {/* Date label */}
                                    <div className="cd-timeline-date">
                                      {item.data_dal || '—'}
                                      {item.data_al && <span className="d-block">→ {item.data_al}</span>}
                                    </div>

                                    {/* Card */}
                                    <div className={`cd-timeline-card ${!item.is_active ? 'inactive' : ''}`}>
                                        {/* Status badge */}
                                        <div className="mb-2">
                                          {item.is_active ? (
                                            <span className="cd-timeline-badge" style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>Attivo</span>
                                          ) : (
                                            <span className="cd-timeline-badge" style={{ background: 'rgba(107,114,128,0.1)', color: '#6b7280' }}>Concluso</span>
                                          )}
                                        </div>

                                        {/* Avatar */}
                                        <div className="d-flex justify-content-center mb-2">
                                          {item.avatar_path ? (
                                            <img
                                              src={item.avatar_path}
                                              alt=""
                                              className="cd-timeline-card-avatar"
                                            />
                                          ) : (
                                            <div
                                              className="cd-timeline-card-initials"
                                              style={{ background: '#22c55e' }}
                                            >
                                              {item.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                        </div>

                                        {/* Name */}
                                        <div className="cd-timeline-card-name">
                                          {item.professionista_nome}
                                        </div>
                                    </div>
                                  </div>
                                ))}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Stati Servizio e Chat in row */}
                      <div>
                        <div className="cd-section-title">
                          Stato Servizio
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle success">
                                <i className="ri-heart-pulse-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Stato Nutrizione</span>
                            </div>
                            <select
                              className="cd-select sm mb-2"
                              value={formData.stato_nutrizione || ''}
                              onChange={(e) => handleInputChange('stato_nutrizione', e.target.value)}
                            >
                              <option value="">Seleziona stato...</option>
                              <option value="attivo">Attivo</option>
                              <option value="pausa">Pausa</option>
                              <option value="ghost">Ghost</option>
                              <option value="stop">Ex-Cliente</option>
                            </select>
                            {c.stato_nutrizione_data && (
                              <span className="cd-prof-date">
                                <i className="ri-calendar-line me-1"></i>
                                Ultimo cambio: {new Date(c.stato_nutrizione_data).toLocaleDateString('it-IT')}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div>
                        <div className="cd-section-title">
                          Stato Chat
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle warning">
                                <i className="ri-chat-3-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Stato Chat Nutrizione</span>
                            </div>
                            <select
                              className="cd-select sm mb-2"
                              value={formData.stato_cliente_chat_nutrizione || ''}
                              onChange={(e) => handleInputChange('stato_cliente_chat_nutrizione', e.target.value)}
                            >
                              <option value="">Seleziona stato...</option>
                              <option value="attivo">Attivo</option>
                              <option value="pausa">Pausa</option>
                              <option value="ghost">Ghost</option>
                            </select>
                          </div>
                        </div>
                      </div>

                      {/* Timeline Storico Stati Unificata */}
                      <div data-tour="nutrizione-storico">
                        <div className="cd-section-title">
                          <i className="ri-history-line"></i>
                          Storico Stati (Servizio + Chat)
                        </div>
                        {loadingStoricoNutrizione ? (
                          <div className="cd-loading">
                            <div className="cd-spinner" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento storico...</small>
                          </div>
                        ) : (storicoStatoNutrizione.length > 0 || storicoChatNutrizione.length > 0) ? (
                            <div className="cd-timeline">
                              {/* Horizontal line */}
                              <div className="cd-timeline-line" style={{ background: 'linear-gradient(to right, #22c55e, #f59e0b)' }}></div>

                              <div className="cd-timeline-items">
                                {/* Combine and sort both histories */}
                                {[
                                  ...storicoStatoNutrizione.map(item => ({ ...item, tipo: 'servizio' })),
                                  ...storicoChatNutrizione.map(item => ({ ...item, tipo: 'chat' }))
                                ]
                                  .sort((a, b) => {
                                    const dateA = new Date(a.data_inizio?.split('/').reverse().join('-') || 0);
                                    const dateB = new Date(b.data_inizio?.split('/').reverse().join('-') || 0);
                                    return dateB - dateA;
                                  })
                                  .map((item, idx) => {
                                    const isServizio = item.tipo === 'servizio';
                                    const dotColor = isServizio ? '#22c55e' : '#f59e0b';
                                    const icon = isServizio ? 'ri-heart-pulse-line' : 'ri-chat-3-line';

                                    return (
                                      <div key={idx} className="cd-timeline-item">
                                        {/* Dot on line */}
                                        <div className="cd-timeline-dot-wrap">
                                          <div className="cd-timeline-dot" style={{ background: dotColor }}>
                                            <i className={icon}></i>
                                          </div>
                                        </div>

                                        {/* Date label */}
                                        <div className="cd-timeline-date">
                                          {item.data_inizio || '—'}
                                          {item.data_fine && <span className="d-block">→ {item.data_fine}</span>}
                                        </div>

                                        {/* Card */}
                                        <div className={`cd-timeline-card ${!item.is_attivo ? 'inactive' : ''}`}>
                                            {/* Type badge */}
                                            <div className="mb-1">
                                              <span className="cd-timeline-badge" style={{ background: isServizio ? 'rgba(34,197,94,0.1)' : 'rgba(245,158,11,0.1)', color: isServizio ? '#22c55e' : '#f59e0b' }}>
                                                {isServizio ? 'Servizio' : 'Chat'}
                                              </span>
                                            </div>

                                            {/* Status badge */}
                                            <div className="mb-1">
                                              <span className="cd-timeline-badge" style={{ background: 'rgba(107,114,128,0.1)', color: '#6b7280' }}>
                                                {STATO_LABELS[item.stato] || item.stato}
                                              </span>
                                            </div>

                                            {/* Active indicator */}
                                            {item.is_attivo && (
                                              <div style={{ fontSize: '0.65rem', color: '#22c55e' }}>
                                                <i className="ri-checkbox-circle-fill me-1"></i>In corso
                                              </div>
                                            )}

                                            {/* Duration */}
                                            {item.durata_giorni > 0 && !item.is_attivo && (
                                              <div className="cd-prof-date">
                                                {item.durata_giorni} giorni
                                              </div>
                                            )}
                                        </div>
                                      </div>
                                    );
                                  })}
                              </div>
                            </div>
                        ) : (
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body cd-empty">
                              <i className="ri-history-line cd-empty-icon"></i>
                              <p className="cd-empty-text">Nessuno storico stati disponibile</p>
                              <small>I cambi di stato verranno tracciati automaticamente</small>
                            </div>
                          </div>
                        )}
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== SETUP SUB-TAB ===== */}
                  {nutrizioneSubTab === 'setup' && (
                    <div data-tour="nutrizione-setup">
                      <div className="cd-sections">
                      {/* Call Iniziale */}
                      <div>
                        <div className="cd-section-title">
                          Call Iniziale
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle primary">
                                <i className="ri-phone-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Call Iniziale Nutrizionista</span>
                            </div>
                            <div className="form-check form-switch mb-2">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                id="callNutrizionista"
                                checked={formData.call_iniziale_nutrizionista || false}
                                onChange={(e) => handleInputChange('call_iniziale_nutrizionista', e.target.checked)}
                              />
                              <label className="form-check-label small" htmlFor="callNutrizionista">
                                {formData.call_iniziale_nutrizionista ? 'Effettuata' : 'Non effettuata'}
                              </label>
                              {formData.call_iniziale_nutrizionista && (
                                <span className="cd-badge ms-2" style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>Completata</span>
                              )}
                            </div>
                            {formData.call_iniziale_nutrizionista && (
                              <div className="mt-3">
                                <label className="cd-field-label">Data Call</label>
                                <DatePicker
                                  className="cd-input sm"
                                  value={formData.data_call_iniziale_nutrizionista || ''}
                                  onChange={(e) => handleInputChange('data_call_iniziale_nutrizionista', e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Reach Out */}
                      <div>
                        <div className="cd-section-title">
                          Reach Out Settimanale
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle info">
                                <i className="ri-calendar-check-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Giorno Reach Out</span>
                            </div>
                            <select
                              className="cd-select sm"
                              value={formData.reach_out_nutrizione || ''}
                              onChange={(e) => handleInputChange('reach_out_nutrizione', e.target.value)}
                            >
                              <option value="">Seleziona giorno...</option>
                              <option value="lunedi">Lunedì</option>
                              <option value="martedi">Martedì</option>
                              <option value="mercoledi">Mercoledì</option>
                              <option value="giovedi">Giovedì</option>
                              <option value="venerdi">Venerdì</option>
                              <option value="sabato">Sabato</option>
                              <option value="domenica">Domenica</option>
                            </select>
                            {formData.reach_out_nutrizione && (
                              <span className="cd-prof-date d-block mt-2">
                                <i className="ri-calendar-event-line me-1"></i>
                                Reach out ogni {
                                  { lunedi: 'Lunedì', martedi: 'Martedì', mercoledi: 'Mercoledì', giovedi: 'Giovedì', venerdi: 'Venerdì', sabato: 'Sabato', domenica: 'Domenica' }[formData.reach_out_nutrizione]
                                }
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Date call di visita */}
                      <div>
                        <div className="cd-section-title">
                          Date call di visita
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle success">
                                <i className="ri-calendar-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Date in cui sono state fatte le call di visita</span>
                            </div>
                            <ul className="list-unstyled mb-0 small">
                              {formData.call_iniziale_nutrizionista && formData.data_call_iniziale_nutrizionista ? (
                                <li className="d-flex align-items-center mb-2">
                                  <i className="ri-check-line text-success me-2"></i>
                                  Call iniziale nutrizionista: <strong className="ms-1">{formData.data_call_iniziale_nutrizionista}</strong>
                                </li>
                              ) : (
                                <li className="cd-empty-text">Nessuna data call di visita registrata. Compila &quot;Call Iniziale Nutrizionista&quot; sopra per registrare la data.</li>
                              )}
                            </ul>
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== PATOLOGIE SUB-TAB ===== */}
                  {nutrizioneSubTab === 'patologie' && (
                    <div data-tour="nutrizione-patologie">
                      <div className="cd-sections">
                      <div>
                        <div className="cd-section-title">
                          Patologie del Cliente
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle warning">
                                <i className="ri-stethoscope-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Patologie Nutrizionali</span>
                            </div>

                            {/* Nessuna Patologia - in evidenza */}
                            <div
                              className={`cd-no-pathology-banner ${formData.nessuna_patologia ? 'active' : ''}`}
                            >
                              <div className="form-check mb-0">
                                <input
                                  className="form-check-input"
                                  type="checkbox"
                                  id="nessuna_patologia"
                                  checked={formData.nessuna_patologia || false}
                                  onChange={(e) => handleInputChange('nessuna_patologia', e.target.checked)}
                                />
                                <label className={`form-check-label small ${formData.nessuna_patologia ? 'fw-semibold text-success' : ''}`} htmlFor="nessuna_patologia">
                                  Nessuna Patologia
                                </label>
                              </div>
                            </div>

                            {/* Lista patologie */}
                            <div className="cd-pathology-grid">
                              {[
                                { key: 'patologia_ibs', label: 'IBS' },
                                { key: 'patologia_reflusso', label: 'Reflusso' },
                                { key: 'patologia_gastrite', label: 'Gastrite' },
                                { key: 'patologia_dca', label: 'DCA' },
                                { key: 'patologia_insulino_resistenza', label: 'Insulino Resistenza' },
                                { key: 'patologia_diabete', label: 'Diabete' },
                                { key: 'patologia_dislipidemie', label: 'Dislipidemie' },
                                { key: 'patologia_steatosi_epatica', label: 'Steatosi Epatica' },
                                { key: 'patologia_ipertensione', label: 'Ipertensione' },
                                { key: 'patologia_pcos', label: 'PCOS' },
                                { key: 'patologia_endometriosi', label: 'Endometriosi' },
                                { key: 'patologia_obesita_sindrome', label: 'Obesità' },
                                { key: 'patologia_osteoporosi', label: 'Osteoporosi' },
                                { key: 'patologia_diverticolite', label: 'Diverticolite' },
                                { key: 'patologia_crohn', label: 'Crohn' },
                                { key: 'patologia_stitichezza', label: 'Stitichezza' },
                                { key: 'patologia_tiroidee', label: 'Tiroidee' },
                              ].map(({ key, label }) => (
                                <div key={key}>
                                  <div className="form-check">
                                    <input
                                      className="form-check-input"
                                      type="checkbox"
                                      id={key}
                                      checked={formData[key] || false}
                                      onChange={(e) => handleInputChange(key, e.target.checked)}
                                    />
                                    <label className={`form-check-label small ${formData[key] ? 'fw-medium' : ''}`} htmlFor={key}>
                                      {label}
                                    </label>
                                  </div>
                                </div>
                              ))}
                              {/* Altro Checkbox */}
                              <div>
                                <div className="form-check">
                                  <input
                                    className="form-check-input"
                                    type="checkbox"
                                    id="patologia_altro_check"
                                    checked={formData.patologia_altro_check || false}
                                    onChange={(e) => handleInputChange('patologia_altro_check', e.target.checked)}
                                  />
                                  <label className={`form-check-label small ${formData.patologia_altro_check ? 'fw-medium' : ''}`} htmlFor="patologia_altro_check">
                                    Altro...
                                  </label>
                                </div>
                              </div>
                            </div>
                            
                            {/* Altro Input */}
                            {formData.patologia_altro_check && (
                              <div className="mt-2">
                                <input
                                  type="text"
                                  className="cd-input sm"
                                  placeholder="Specifica altra patologia..."
                                  value={formData.patologia_altro || ''}
                                  onChange={(e) => handleInputChange('patologia_altro', e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* ===== ANAMNESI (campo unico) ===== */}
                      <div>
                        <div className="cd-section-title">
                          Anamnesi Nutrizionale
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-row">
                              <div className="cd-inner-card-header-left">
                                <div className="cd-icon-circle purple">
                                  <i className="ri-file-list-3-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Anamnesi Nutrizione</span>
                              </div>
                              <button
                                className="cd-btn-save"
                                onClick={handleSaveAnamnesi}
                                disabled={savingAnamnesi || loadingAnamnesi}
                              >
                                {savingAnamnesi ? (
                                  <><span className="cd-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }}></span>Salvataggio...</>
                                ) : (
                                  <><i className="ri-save-line"></i>Salva</>
                                )}
                              </button>
                            </div>

                            {loadingAnamnesi ? (
                              <div className="cd-loading">
                                <div className="cd-spinner" role="status"></div>
                                <small className="ms-2 text-muted">Caricamento anamnesi...</small>
                              </div>
                            ) : (
                              <>
                                <div className="cd-field">
                                  <textarea
                                    className="cd-textarea"
                                    rows="8"
                                    placeholder="Scrivi qui l'anamnesi nutrizionale del cliente...&#10;&#10;• Anamnesi patologica remota e prossima&#10;• Anamnesi familiare&#10;• Stile di vita e abitudini&#10;• Terapie e allergie"
                                    value={anamnesiContent}
                                    onChange={(e) => setAnamnesiContent(e.target.value)}
                                  ></textarea>
                                </div>
                                {anamnesiNutrizione && (
                                  <div className="cd-prof-date border-top pt-2">
                                    <i className="ri-information-line me-1"></i>
                                    Creato: {anamnesiNutrizione.created_at} da {anamnesiNutrizione.created_by || 'N/D'}
                                    {anamnesiNutrizione.last_modified_by && (
                                      <span className="ms-3">
                                        | Ultima modifica: {anamnesiNutrizione.updated_at} da {anamnesiNutrizione.last_modified_by}
                                      </span>
                                    )}
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== PIANO ALIMENTARE SUB-TAB ===== */}
                  {nutrizioneSubTab === 'piano' && (
                    <div data-tour="nutrizione-piani-wrapper">
                      <div className="cd-sections">
                      {/* Piano Attivo */}
                      <div data-tour="nutrizione-piani">
                        <div className="cd-section-title">
                          Piano Alimentare Attivo
                        </div>
                        {loadingMealPlans ? (
                          <div className="cd-loading">
                            <div className="cd-spinner" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento piani...</small>
                          </div>
                        ) : (
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-row">
                                <div className="cd-inner-card-header-left">
                                  <div className="cd-icon-circle success">
                                    <i className="ri-restaurant-line"></i>
                                  </div>
                                  <span className="cd-inner-card-title">Piano Corrente</span>
                                </div>
                                {canManageNutritionSection && (
                                  <button
                                    className="cd-btn-save"
                                    onClick={() => setShowAddMealPlanModal(true)}
                                  >
                                    <i className="ri-add-line"></i>
                                    Nuovo Piano
                                  </button>
                                )}
                              </div>

                              {(() => {
                                const activePlan = mealPlans.find(p => p.is_active);
                                if (activePlan) {
                                  return (
                                    <div className="cd-date-plan-card" style={{ background: 'rgba(34,197,94,0.08)' }}>
                                      <div className="d-flex justify-content-between align-items-start mb-2">
                                        <div>
                                          <h6 className="mb-1 fw-semibold">{activePlan.name || 'Piano Alimentare'}</h6>
                                          <span className="cd-prof-date">
                                            <i className="ri-calendar-line me-1"></i>
                                            {activePlan.start_date ? new Date(activePlan.start_date).toLocaleDateString('it-IT') : '-'}
                                            {' → '}
                                            {activePlan.end_date ? new Date(activePlan.end_date).toLocaleDateString('it-IT') : '-'}
                                            {activePlan.duration_days && (
                                              <span className="ms-2">({activePlan.duration_days} giorni)</span>
                                            )}
                                          </span>
                                        </div>
                                        <span className="cd-badge" style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>Attivo</span>
                                      </div>

                                      {activePlan.notes && (
                                        <p className="cd-prof-date mb-2 mt-2">
                                          <i className="ri-sticky-note-line me-1"></i>
                                          {activePlan.notes}
                                        </p>
                                      )}

                                      <div className="d-flex gap-2 mt-3 flex-wrap">
                                        {activePlan.has_file && activePlan.piano_alimentare_file_path && (
                                          <button
                                            className="cd-btn-save"
                                            onClick={() => handlePreviewPlan(activePlan)}
                                          >
                                            <i className="ri-eye-line"></i>
                                            Visualizza
                                          </button>
                                        )}
                                        {canManageNutritionSection && (
                                          <button
                                            className="cd-btn-back"
                                            onClick={() => handleOpenEditPlan(activePlan)}
                                          >
                                            <i className="ri-edit-line"></i>
                                            Modifica
                                          </button>
                                        )}
                                        <button
                                          className="cd-btn-back"
                                          onClick={() => handleViewVersions(activePlan)}
                                        >
                                          <i className="ri-history-line"></i>
                                          Storico
                                        </button>
                                        {activePlan.extra_files && activePlan.extra_files.length > 0 && (
                                          <span className="cd-badge" style={{ background: 'rgba(107,114,128,0.1)', color: '#6b7280' }}>
                                            +{activePlan.extra_files.length} file extra
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  );
                                } else {
                                  return (
                                    <p className="cd-empty-text">
                                      <i className="ri-information-line me-1"></i>
                                      Nessun piano alimentare attivo
                                    </p>
                                  );
                                }
                              })()}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Storico Piani */}
                      {mealPlans.filter(p => !p.is_active).length > 0 && (
                        <div>
                          <div className="cd-section-title">
                            <i className="ri-history-line"></i>
                            Storico Piani Alimentari
                          </div>
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                                <div className="cd-icon-circle secondary">
                                  <i className="ri-archive-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Piani Precedenti</span>
                                <span className="cd-badge ms-auto" style={{ background: 'rgba(107,114,128,0.1)', color: '#6b7280' }}>{mealPlans.filter(p => !p.is_active).length}</span>
                              </div>

                              <div className="cd-table-wrap">
                                <table className="cd-table">
                                  <thead>
                                    <tr>
                                      <th>Nome</th>
                                      <th>Periodo</th>
                                      <th>Durata</th>
                                      <th className="text-end">Azioni</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {mealPlans
                                      .filter(p => !p.is_active)
                                      .sort((a, b) => new Date(b.start_date) - new Date(a.start_date))
                                      .map((plan) => (
                                        <tr key={plan.id || plan.start_date}>
                                          <td>
                                            <span className="fw-medium">{plan.name || 'Piano Alimentare'}</span>
                                            {plan.is_legacy && (
                                              <span className="cd-badge ms-2" style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b' }}>Legacy</span>
                                            )}
                                          </td>
                                          <td>
                                            {plan.start_date ? new Date(plan.start_date).toLocaleDateString('it-IT') : '-'}
                                            {' → '}
                                            {plan.end_date ? new Date(plan.end_date).toLocaleDateString('it-IT') : '-'}
                                          </td>
                                          <td>
                                            {plan.duration_days ? `${plan.duration_days}gg` : '-'}
                                          </td>
                                          <td className="text-end">
                                            <div className="d-flex gap-1 justify-content-end">
                                              {plan.has_file && plan.piano_alimentare_file_path && (
                                                <>
                                                  <button
                                                    className="cd-btn-action-sm"
                                                    onClick={() => handlePreviewPlan(plan)}
                                                    title="Visualizza"
                                                  >
                                                    <i className="ri-eye-line"></i>
                                                  </button>
                                                  <a
                                                    href={`/uploads/${plan.piano_alimentare_file_path}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="cd-btn-action-sm"
                                                    title="Scarica"
                                                  >
                                                    <i className="ri-download-line"></i>
                                                  </a>
                                                </>
                                              )}
                                              {!plan.is_legacy && (
                                                <>
                                                  {canManageNutritionSection && (
                                                    <button
                                                      className="cd-btn-action-sm"
                                                      onClick={() => handleOpenEditPlan(plan)}
                                                      title="Modifica"
                                                    >
                                                      <i className="ri-edit-line"></i>
                                                    </button>
                                                  )}
                                                  <button
                                                    className="cd-btn-action-sm"
                                                    onClick={() => handleViewVersions(plan)}
                                                    title="Storico"
                                                  >
                                                    <i className="ri-history-line"></i>
                                                  </button>
                                                </>
                                              )}
                                            </div>
                                          </td>
                                        </tr>
                                      ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Date Dieta Legacy dal modello Cliente */}
                      {(c.dieta_dal || c.nuova_dieta_dal) && (
                        <div>
                          <div className="cd-section-title">
                            Date Riferimento
                          </div>
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                                <div className="cd-icon-circle info">
                                  <i className="ri-calendar-2-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Date Dieta Cliente</span>
                              </div>
                              <div className="cd-form-grid cols-2">
                                <div>
                                  <label className="cd-field-label">Dieta Dal</label>
                                  <DatePicker
                                    className="cd-input sm"
                                    value={formData.dieta_dal || ''}
                                    onChange={(e) => handleInputChange('dieta_dal', e.target.value)}
                                  />
                                </div>
                                <div>
                                  <label className="cd-field-label">Nuova Dieta Dal</label>
                                  <DatePicker
                                    className="cd-input sm"
                                    value={formData.nuova_dieta_dal || ''}
                                    onChange={(e) => handleInputChange('nuova_dieta_dal', e.target.value)}
                                  />
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                      </div>
                    </div>
                  )}
                  {/* ===== DIARIO SUB-TAB ===== */}
                  {nutrizioneSubTab === 'diario' && (
                    <div data-tour="nutrizione-diario">
                      <div className="cd-sections">
                      <div>
                        <div className="cd-section-title">
                          Diario Nutrizionale
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-row">
                              <div className="cd-inner-card-header-left">
                                <div className="cd-icon-circle pink">
                                  <i className="ri-book-2-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Note del Percorso</span>
                                <span className="cd-badge ms-2" style={{ background: 'rgba(107,114,128,0.1)', color: '#6b7280' }}>{diarioEntries.length}</span>
                              </div>
                              {canManageNutritionSection && (
                                <button
                                  className="cd-btn-save"
                                  onClick={() => handleOpenDiarioModal()}
                                >
                                  <i className="ri-add-line"></i>
                                  Nuova Nota
                                </button>
                              )}
                            </div>

                            {loadingDiario ? (
                              <div className="cd-loading">
                                <div className="cd-spinner" role="status"></div>
                                <small className="ms-2 text-muted">Caricamento diario...</small>
                              </div>
                            ) : diarioEntries.length === 0 ? (
                              <div className="cd-empty">
                                <p className="cd-empty-text">
                                  <i className="ri-information-line me-1"></i>
                                  Nessuna nota nel diario. Clicca "Nuova Nota" per aggiungerne una.
                                </p>
                              </div>
                            ) : (
                              <div className="d-flex flex-column gap-3">
                                {diarioEntries.map((entry) => (
                                  <div key={entry.id} className="cd-diary-entry">
                                    <div className="cd-diary-header">
                                      <div className="cd-diary-meta">
                                        <span className="cd-badge" style={{ background: 'rgba(59,130,246,0.1)', color: '#3b82f6' }}>
                                          <i className="ri-calendar-line me-1"></i>
                                          {entry.entry_date_display}
                                          {entry.created_at && (
                                            <span className="ms-1 opacity-75">
                                              ({entry.created_at.split(' ')[1]})
                                            </span>
                                          )}
                                        </span>
                                        <span className="cd-prof-date">
                                          <i className="ri-user-line me-1"></i>
                                          {entry.author}
                                        </span>
                                      </div>
                                      <div className="cd-diary-actions">
                                        {canManageNutritionSection && (
                                          <button
                                            className="cd-btn-action-sm"
                                            onClick={() => handleOpenDiarioModal(entry)}
                                            title="Modifica"
                                          >
                                            <i className="ri-edit-line"></i>
                                          </button>
                                        )}
                                        {(user?.is_admin || user?.role === 'admin') && (
                                          <button
                                            className="cd-btn-action-sm danger"
                                            onClick={() => handleDeleteDiarioEntry(entry.id)}
                                            title="Elimina"
                                          >
                                            <i className="ri-delete-bin-line"></i>
                                          </button>
                                        )}
                                        <button
                                          className="cd-btn-action-sm"
                                          onClick={() => handleOpenHistoryModal(entry, 'nutrizione')}
                                          title="Storico Modifiche"
                                        >
                                          <i className="ri-history-line"></i>
                                        </button>
                                      </div>
                                    </div>
                                    <p className="cd-diary-content">{entry.content}</p>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== ALERT SUB-TAB ===== */}
                  {nutrizioneSubTab === 'alert' && (
                    <div data-tour="nutrizione-alert">
                      <div className="cd-sections">
                      <div>
                        <div className="cd-section-title">
                          Alert e Criticità
                        </div>
                        <div className="cd-inner-card danger-border">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle danger">
                                <i className="ri-alarm-warning-line"></i>
                              </div>
                              <span className="cd-inner-card-title danger">Alert Nutrizione</span>
                            </div>
                            <p className="cd-prof-date mb-2">
                              Informazioni critiche: allergie, intolleranze, controindicazioni alimentari.
                              Queste note saranno sempre visibili in evidenza.
                            </p>
                            <textarea
                              className="cd-textarea"
                              style={{ borderColor: '#fecaca' }}
                              rows="4"
                              placeholder="Es: Allergia alle arachidi, Intolleranza al lattosio, Celiachia..."
                              value={formData.alert_nutrizione || ''}
                              onChange={(e) => handleInputChange('alert_nutrizione', e.target.value)}
                            ></textarea>
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {nutrizioneSubTab === 'vecchie_note' && (
                    <div>
                      <div className="cd-sections">
                        <div>
                          <div className="cd-section-title">
                            <i className="ri-archive-line"></i>
                            Vecchie Note Nutrizione (legacy)
                          </div>
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                                <div className="cd-icon-circle secondary">
                                  <i className="ri-history-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Storia Nutrizione</span>
                              </div>
                              <textarea
                                className="cd-textarea"
                                rows="8"
                                placeholder="Nessuna storia nutrizione..."
                                value={formData.storia_nutrizione || ''}
                                onChange={(e) => handleInputChange('storia_nutrizione', e.target.value)}
                              ></textarea>
                            </div>
                          </div>
                          <div className="cd-inner-card" style={{ marginTop: '16px' }}>
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                                <div className="cd-icon-circle secondary">
                                  <i className="ri-file-text-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Note Extra Nutrizione</span>
                              </div>
                              <textarea
                                className="cd-textarea"
                                rows="8"
                                placeholder="Nessuna nota extra..."
                                value={formData.note_extra_nutrizione || ''}
                                onChange={(e) => handleInputChange('note_extra_nutrizione', e.target.value)}
                              ></textarea>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ========== COACHING TAB ========== */}
              {activeTab === 'coaching' && (
                <div>
                  {/* Sub-tab Navigation */}
                  <div className="col-12" data-tour="coaching-subtabs">
                    <ScrollableSubtabs>
                        {[
                          { key: 'panoramica', label: 'Panoramica', icon: 'ri-dashboard-line', color: 'orange' },
                          { key: 'setup', label: 'Setup', icon: 'ri-settings-3-line', color: 'blue' },
                          { key: 'piano', label: 'Piano Allenamento', icon: 'ri-run-line', color: 'orange' },
                          { key: 'luoghi', label: 'Luoghi', icon: 'ri-map-pin-line', color: 'green' },
                          { key: 'anamnesi', label: 'Anamnesi', icon: 'ri-file-list-3-line', color: 'red' },
                          { key: 'diario', label: 'Diario', icon: 'ri-book-2-line', color: 'pink' },
                          { key: 'alert', label: 'Alert', icon: 'ri-alarm-warning-line', color: 'red' },
                          { key: 'vecchie_note', label: 'Vecchie Note', icon: 'ri-archive-line', color: 'secondary' },
                        ].map(({ key, label, icon, color }) => (
                            <button
                              key={key}
                              className={`cd-subtab ${coachingSubTab === key ? `active ${color}` : ''}`}
                              onClick={() => setCoachingSubTab(key)}
                            >
                              <i className={icon}></i>
                              {label}
                            </button>
                        ))}
                    </ScrollableSubtabs>
                  </div>

                  {/* ===== PANORAMICA SUB-TAB ===== */}
                  {coachingSubTab === 'panoramica' && (
                    <div data-tour="coaching-panoramica">
                      <div className="cd-sections">
                      {/* Coach Assegnati - Same style as Nutrizione */}
                      <div>
                        <div className="cd-section-title">
                          Coach Assegnati
                        </div>
                        {loadingHistory ? (
                          <div className="cd-loading">
                            <div className="spinner-border spinner-border-sm text-warning" role="status"></div>
                            <small className="ms-2 cd-loading-text">Caricamento...</small>
                          </div>
                        ) : (
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-row">
                                <div className="cd-inner-card-header-left">
                                  <div className="cd-icon-circle warning lg">
                                    <i className="ri-run-line"></i>
                                  </div>
                                  <span className="cd-inner-card-title">Team Coaching</span>
                                </div>
                                <span className="cd-badge" style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b' }}>{getActiveProfessionals('coach').length} attivi</span>
                              </div>

                              {getActiveProfessionals('coach').length > 0 ? (
                                <div className="d-flex flex-wrap gap-2">
                                  {getActiveProfessionals('coach').map((assignment, idx) => (
                                    <div key={idx} className="cd-assignment-row">
                                      <div className="cd-assignment-info">
                                      {assignment.avatar_path ? (
                                        <img src={assignment.avatar_path} alt="" className="cd-prof-avatar" />
                                      ) : (
                                        <div className="cd-prof-initials lg" style={{ background: '#f59e0b' }}>
                                          {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                        </div>
                                      )}
                                      <div>
                                        <span className="cd-prof-name">{assignment.professionista_nome}</span>
                                        <span className="cd-prof-date">dal {assignment.data_dal}</span>
                                      </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-muted small mb-0">Nessun coach assegnato. Vai alla tab "Team" per assegnare.</p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Storico Assegnazioni Timeline - Orizzontale come Nutrizione */}
                      {professionistiHistory.filter(h => h.tipo_professionista === 'coach').length > 0 && (
                        <div>
                          <div className="cd-section-title">
                            <i className="ri-history-line"></i>
                            Storico Assegnazioni
                          </div>
                          <div className="cd-timeline">
                            {/* Horizontal line */}
                            <div className="cd-timeline-line" style={{ background: 'linear-gradient(to right, #f59e0b, #d97706)' }}></div>

                            <div className="cd-timeline-items">
                              {professionistiHistory
                                .filter(h => h.tipo_professionista === 'coach')
                                .sort((a, b) => {
                                  const dateA = new Date(a.data_dal?.split('/').reverse().join('-') || 0);
                                  const dateB = new Date(b.data_dal?.split('/').reverse().join('-') || 0);
                                  return dateB - dateA;
                                })
                                .map((item, idx) => (
                                  <div key={idx} className="cd-timeline-item">
                                    {/* Dot on line */}
                                    <div className="cd-timeline-dot-wrap">
                                      <div
                                        className="cd-timeline-dot"
                                        style={{ background: '#f59e0b' }}
                                      >
                                        <i className="ri-run-line"></i>
                                      </div>
                                    </div>

                                    {/* Date label */}
                                    <div className="cd-timeline-date">
                                      {item.data_dal || '—'}
                                      {item.data_al && <span className="d-block">→ {item.data_al}</span>}
                                    </div>

                                    {/* Card */}
                                    <div className={`cd-timeline-card ${!item.is_active ? 'inactive' : ''}`}>
                                      <div>
                                        {/* Status badge */}
                                        <div className="mb-2">
                                          {item.is_active ? (
                                            <span className="cd-timeline-badge" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>Attivo</span>
                                          ) : (
                                            <span className="cd-timeline-badge" style={{ background: 'rgba(107,114,128,0.15)', color: '#6b7280' }}>Concluso</span>
                                          )}
                                        </div>

                                        {/* Avatar */}
                                        <div className="d-flex justify-content-center mb-2">
                                          {item.avatar_path ? (
                                            <img
                                              src={item.avatar_path}
                                              alt=""
                                              className="cd-timeline-card-avatar"
                                            />
                                          ) : (
                                            <div
                                              className="cd-timeline-card-initials"
                                              style={{ background: '#f59e0b' }}
                                            >
                                              {item.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                        </div>

                                        {/* Name */}
                                        <div className="cd-timeline-card-name">
                                          {item.professionista_nome}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Stati Servizio e Chat in row */}
                      <div>
                        <div className="cd-section-title">
                          Stato Servizio
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle warning">
                                <i className="ri-run-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Stato Coaching</span>
                            </div>
                            <div className="cd-field">
                            <select
                              className="cd-select sm"
                              value={formData.stato_coach || ''}
                              onChange={(e) => handleInputChange('stato_coach', e.target.value)}
                            >
                              <option value="">Seleziona stato...</option>
                              <option value="attivo">Attivo</option>
                              <option value="pausa">Pausa</option>
                              <option value="ghost">Ghost</option>
                              <option value="stop">Ex-Cliente</option>
                            </select>
                            </div>
                            {c.stato_coach_data && (
                              <span className="cd-prof-date">
                                <i className="ri-calendar-line me-1"></i>
                                Ultimo cambio: {new Date(c.stato_coach_data).toLocaleDateString('it-IT')}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div>
                        <div className="cd-section-title">
                          Stato Chat
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle secondary">
                                <i className="ri-chat-3-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Stato Chat Coaching</span>
                            </div>
                            <div className="cd-field">
                            <select
                              className="cd-select sm"
                              value={formData.stato_cliente_chat_coaching || ''}
                              onChange={(e) => handleInputChange('stato_cliente_chat_coaching', e.target.value)}
                            >
                              <option value="">Seleziona stato...</option>
                              <option value="attivo">Attivo</option>
                              <option value="pausa">Pausa</option>
                              <option value="ghost">Ghost</option>
                            </select>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Timeline Storico Stati Unificata */}
                      <div>
                        <div className="cd-section-title">
                          <i className="ri-history-line"></i>
                          Storico Stati (Servizio + Chat)
                        </div>
                        {loadingStoricoCoaching ? (
                          <div className="cd-loading">
                            <div className="spinner-border spinner-border-sm text-warning" role="status"></div>
                            <small className="ms-2 cd-loading-text">Caricamento storico...</small>
                          </div>
                        ) : (storicoStatoCoaching.length > 0 || storicoChatCoaching.length > 0) ? (
                            <div className="cd-timeline">
                              {/* Horizontal line */}
                              <div className="cd-timeline-line" style={{ background: 'linear-gradient(to right, #f59e0b, #6b7280)' }}></div>

                              <div className="cd-timeline-items">
                                {/* Combine and sort both histories */}
                                {[
                                  ...storicoStatoCoaching.map(item => ({ ...item, tipo: 'servizio' })),
                                  ...storicoChatCoaching.map(item => ({ ...item, tipo: 'chat' }))
                                ]
                                  .sort((a, b) => {
                                    const dateA = new Date(a.data_inizio?.split('/').reverse().join('-') || 0);
                                    const dateB = new Date(b.data_inizio?.split('/').reverse().join('-') || 0);
                                    return dateB - dateA;
                                  })
                                  .map((item, idx) => {
                                    const isServizio = item.tipo === 'servizio';
                                    const bgColor = isServizio ? 'warning' : 'secondary';
                                    const icon = isServizio ? 'ri-run-line' : 'ri-chat-3-line';
                                    const dotBg = isServizio ? '#f59e0b' : '#6b7280';

                                    return (
                                      <div key={idx} className="cd-timeline-item">
                                        {/* Dot on line */}
                                        <div className="cd-timeline-dot-wrap">
                                          <div
                                            className="cd-timeline-dot"
                                            style={{ background: dotBg }}
                                          >
                                            <i className={icon}></i>
                                          </div>
                                        </div>

                                        {/* Date label */}
                                        <div className="cd-timeline-date">
                                          {item.data_inizio || '—'}
                                          {item.data_fine && <span className="d-block">→ {item.data_fine}</span>}
                                        </div>

                                        {/* Card */}
                                        <div className={`cd-timeline-card ${!item.is_attivo ? 'inactive' : ''}`}>
                                          <div>
                                            {/* Type badge */}
                                            <div className="mb-1">
                                              <span className="cd-timeline-badge" style={{ background: isServizio ? 'rgba(245,158,11,0.15)' : 'rgba(107,114,128,0.15)', color: dotBg }}>
                                                {isServizio ? 'Servizio' : 'Chat'}
                                              </span>
                                            </div>

                                            {/* Status badge */}
                                            <div className="mb-1">
                                              <span className={`badge bg-${STATUS_COLORS[item.stato] || 'secondary'}`} style={{ fontSize: '0.7rem' }}>
                                                {STATO_LABELS[item.stato] || item.stato}
                                              </span>
                                            </div>

                                            {/* Active indicator */}
                                            {item.is_attivo && (
                                              <div style={{ fontSize: '0.65rem', color: '#f59e0b' }}>
                                                <i className="ri-checkbox-circle-fill me-1"></i>In corso
                                              </div>
                                            )}

                                            {/* Duration */}
                                            {item.durata_giorni > 0 && !item.is_attivo && (
                                              <div className="text-muted" style={{ fontSize: '0.6rem' }}>
                                                {item.durata_giorni} giorni
                                              </div>
                                            )}
                                          </div>
                                        </div>
                                      </div>
                                    );
                                  })}
                              </div>
                            </div>
                        ) : (
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body cd-empty">
                              <i className="ri-history-line cd-empty-icon"></i>
                              <p className="mb-0 cd-empty-text">Nessuno storico stati disponibile</p>
                              <small className="cd-empty-text">I cambi di stato verranno tracciati automaticamente</small>
                            </div>
                          </div>
                        )}
                      </div>

                      </div>
                    </div>
                  )}

                  {/* ===== SETUP SUB-TAB ===== */}
                  {coachingSubTab === 'setup' && (
                    <div data-tour="coaching-setup">
                      <div className="cd-sections">
                      {/* Call Iniziale */}
                      <div>
                        <div className="cd-section-title">
                          Call Iniziale
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle primary">
                                <i className="ri-phone-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Call Iniziale Coach</span>
                            </div>
                            <div className="form-check form-switch mb-2">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                id="callCoach"
                                checked={formData.call_iniziale_coach || false}
                                onChange={(e) => handleInputChange('call_iniziale_coach', e.target.checked)}
                              />
                              <label className="form-check-label small" htmlFor="callCoach">
                                {formData.call_iniziale_coach ? 'Effettuata' : 'Non effettuata'}
                              </label>
                              {formData.call_iniziale_coach && (
                                <span className="cd-badge ms-2" style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>Completata</span>
                              )}
                            </div>
                            {formData.call_iniziale_coach && (
                              <div className="cd-field mt-3">
                                <label className="cd-field-label">Data Call</label>
                                <DatePicker
                                  className="cd-input sm"
                                  value={formData.data_call_iniziale_coach || ''}
                                  onChange={(e) => handleInputChange('data_call_iniziale_coach', e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Reach Out */}
                      <div>
                        <div className="cd-section-title">
                          Reach Out Settimanale
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle info">
                                <i className="ri-calendar-check-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Giorno Reach Out</span>
                            </div>
                            <div className="cd-field">
                            <select
                              className="cd-select sm"
                              value={formData.reach_out_coaching || ''}
                              onChange={(e) => handleInputChange('reach_out_coaching', e.target.value)}
                            >
                              <option value="">Seleziona giorno...</option>
                              <option value="lunedi">Lunedì</option>
                              <option value="martedi">Martedì</option>
                              <option value="mercoledi">Mercoledì</option>
                              <option value="giovedi">Giovedì</option>
                              <option value="venerdi">Venerdì</option>
                              <option value="sabato">Sabato</option>
                              <option value="domenica">Domenica</option>
                            </select>
                            </div>
                            {formData.reach_out_coaching && (
                              <span className="cd-prof-date d-block mt-2">
                                <i className="ri-calendar-event-line me-1"></i>
                                Reach out ogni {
                                  { lunedi: 'Lunedì', martedi: 'Martedì', mercoledi: 'Mercoledì', giovedi: 'Giovedì', venerdi: 'Venerdì', sabato: 'Sabato', domenica: 'Domenica' }[formData.reach_out_coaching]
                                }
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== PIANO ALLENAMENTO SUB-TAB ===== */}
                  {coachingSubTab === 'piano' && (
                    <div data-tour="coaching-piani-wrapper">
                      <div className="cd-sections">
                      <div data-tour="coaching-schede">
                        <div className="cd-section-title">
                          Piano Allenamento Attivo
                        </div>
                        {loadingTrainingPlans ? (
                          <div className="cd-loading">
                            <div className="spinner-border spinner-border-sm text-warning" role="status"></div>
                            <small className="ms-2 cd-loading-text">Caricamento piani...</small>
                          </div>
                        ) : (
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-row">
                                <div className="cd-inner-card-header-left">
                                  <div className="cd-icon-circle warning">
                                    <i className="ri-run-line"></i>
                                  </div>
                                  <span className="cd-inner-card-title">Piano Corrente</span>
                                </div>
                                {canManageCoachingSection && (
                                  <button
                                    className="cd-btn-save"
                                    onClick={() => setShowAddTrainingPlanModal(true)}
                                  >
                                    <i className="ri-add-line"></i>
                                    Nuovo Piano
                                  </button>
                                )}
                              </div>
                              {(() => {
                                const activePlan = trainingPlans.find(p => p.is_active);
                                if (activePlan) {
                                  return (
                                    <div className="p-3 rounded-3" style={{ background: 'rgba(245,158,11,0.08)' }}>
                                      <div className="d-flex justify-content-between align-items-start mb-2">
                                        <div>
                                          <h6 className="mb-1 fw-semibold">{activePlan.name || 'Piano Allenamento'}</h6>
                                          <small className="text-muted">
                                            <i className="ri-calendar-line me-1"></i>
                                            {activePlan.start_date ? new Date(activePlan.start_date).toLocaleDateString('it-IT') : '-'}
                                            {' → '}
                                            {activePlan.end_date ? new Date(activePlan.end_date).toLocaleDateString('it-IT') : '-'}
                                          </small>
                                        </div>
                                        <span className="cd-badge" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>Attivo</span>
                                      </div>
                                      {activePlan.notes && (
                                        <p className="small text-muted mb-2 mt-2">
                                          <i className="ri-sticky-note-line me-1"></i>
                                          {activePlan.notes}
                                        </p>
                                      )}
                                      <div className="d-flex gap-2 mt-3 flex-wrap">
                                        {activePlan.has_file && activePlan.piano_allenamento_file_path && (
                                          <button
                                            className="cd-btn-save"
                                            onClick={() => handlePreviewTrainingPlan(activePlan)}
                                          >
                                            <i className="ri-eye-line"></i>
                                            Visualizza
                                          </button>
                                        )}
                                        {canManageCoachingSection && (
                                          <button
                                            className="cd-btn-back"
                                            onClick={() => handleOpenEditTrainingPlan(activePlan)}
                                          >
                                            <i className="ri-edit-line"></i>
                                            Modifica
                                          </button>
                                        )}
                                        <button
                                          className="cd-btn-back"
                                          onClick={() => handleViewTrainingVersions(activePlan)}
                                        >
                                          <i className="ri-history-line"></i>
                                          Storico
                                        </button>
                                      </div>
                                    </div>
                                  );
                                } else {
                                  return (
                                    <p className="text-muted small mb-0">
                                      <i className="ri-information-line me-1"></i>
                                      Nessun piano allenamento attivo
                                    </p>
                                  );
                                }
                              })()}
                            </div>
                          </div>
                        )}
                      </div>
                      {/* Storico Piani */}
                      {trainingPlans.filter(p => !p.is_active).length > 0 && (
                        <div>
                          <div className="cd-section-title">
                            <i className="ri-history-line"></i>
                            Storico Piani Allenamento
                          </div>
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-table-wrap">
                                <table className="cd-table">
                                  <thead>
                                    <tr>
                                      <th>Nome</th>
                                      <th>Periodo</th>
                                      <th>Durata</th>
                                      <th className="text-end">Azioni</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {trainingPlans
                                      .filter(p => !p.is_active)
                                      .sort((a, b) => new Date(b.start_date) - new Date(a.start_date))
                                      .map((plan) => (
                                        <tr key={plan.id}>
                                          <td><span className="fw-medium">{plan.name || 'Piano Allenamento'}</span></td>
                                          <td>
                                            {plan.start_date ? new Date(plan.start_date).toLocaleDateString('it-IT') : '-'}
                                            {' → '}
                                            {plan.end_date ? new Date(plan.end_date).toLocaleDateString('it-IT') : '-'}
                                          </td>
                                          <td>{plan.duration_days ? `${plan.duration_days}gg` : '-'}</td>
                                          <td className="text-end">
                                            <div className="d-flex gap-1 justify-content-end">
                                              {plan.has_file && plan.piano_allenamento_file_path && (
                                                <button
                                                  className="cd-btn-action-sm"
                                                  onClick={() => handlePreviewTrainingPlan(plan)}
                                                  title="Visualizza"
                                                >
                                                  <i className="ri-eye-line"></i>
                                                </button>
                                              )}
                                              {canManageCoachingSection && (
                                                <button
                                                  className="cd-btn-action-sm"
                                                  onClick={() => handleOpenEditTrainingPlan(plan)}
                                                  title="Modifica"
                                                >
                                                  <i className="ri-edit-line"></i>
                                                </button>
                                              )}
                                              <button
                                                className="cd-btn-action-sm"
                                                onClick={() => handleViewTrainingVersions(plan)}
                                                title="Storico"
                                              >
                                                <i className="ri-history-line"></i>
                                              </button>
                                            </div>
                                          </td>
                                        </tr>
                                      ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                      </div>
                    </div>
                  )}

                  {/* ===== LUOGHI ALLENAMENTO SUB-TAB ===== */}
                  {coachingSubTab === 'luoghi' && (
                    <div data-tour="coaching-luoghi">
                      <div className="cd-sections">
                      {/* Header con bottone Nuovo Luogo */}
                      <div>
                        <div className="cd-inner-card-header-row mb-3">
                          <div className="cd-section-title mb-0">
                            <i className="ri-map-pin-line"></i>
                            Storico Luoghi di Allenamento
                          </div>
                          {canManageCoachingSection && (
                            <button
                              className="cd-btn-save"
                              onClick={() => handleOpenLocationModal()}
                            >
                              <i className="ri-add-line"></i>
                              Nuovo Luogo
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Timeline Orizzontale Luoghi */}
                      <div>
                        {loadingLocations ? (
                          <div className="cd-loading">
                            <div className="spinner-border spinner-border-sm text-success" role="status"></div>
                            <small className="ms-2 cd-loading-text">Caricamento luoghi...</small>
                          </div>
                        ) : trainingLocations.length === 0 ? (
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body cd-empty">
                              <i className="ri-map-pin-line cd-empty-icon"></i>
                              <p className="mb-0 cd-empty-text">Nessun luogo configurato</p>
                              <small className="cd-empty-text">Clicca "Nuovo Luogo" per aggiungerne uno</small>
                            </div>
                          </div>
                        ) : (
                          <div className="cd-timeline">
                            {/* Horizontal line */}
                            <div className="cd-timeline-line" style={{ background: 'linear-gradient(to right, #10b981, #3b82f6, #f59e0b)' }}></div>

                            <div className="cd-timeline-items">
                              {trainingLocations
                                .sort((a, b) => {
                                  const dateA = new Date(a.start_date || 0);
                                  const dateB = new Date(b.start_date || 0);
                                  return dateB - dateA;
                                })
                                .map((loc, idx) => {
                                  const locationLabels = { casa: 'Casa', palestra: 'Palestra', ibrido: 'Ibrido' };
                                  const locationColors = { casa: '#3b82f6', palestra: '#f59e0b', ibrido: '#10b981' };
                                  const locationIcons = { casa: 'ri-home-line', palestra: 'ri-building-line', ibrido: 'ri-shuffle-line' };
                                  const bgColor = locationColors[loc.location] || '#6b7280';

                                  return (
                                    <div key={loc.id || idx} className="cd-timeline-item">
                                      {/* Dot on line */}
                                      <div className="cd-timeline-dot-wrap">
                                        <div
                                          className="cd-timeline-dot"
                                          style={{ background: bgColor }}
                                        >
                                          <i className={locationIcons[loc.location]}></i>
                                        </div>
                                      </div>

                                      {/* Date label */}
                                      <div className="cd-timeline-date">
                                        {loc.start_date ? new Date(loc.start_date).toLocaleDateString('it-IT') : '—'}
                                        {loc.end_date ? (
                                          <span className="d-block">→ {new Date(loc.end_date).toLocaleDateString('it-IT')}</span>
                                        ) : (
                                          <span className="d-block text-success">→ In corso</span>
                                        )}
                                      </div>

                                      {/* Card */}
                                      <div
                                        className={`cd-timeline-card ${!loc.is_active ? 'inactive' : ''}`}
                                        style={{ cursor: canManageCoachingSection ? 'pointer' : 'default' }}
                                        onClick={canManageCoachingSection ? () => handleOpenLocationModal(loc) : undefined}
                                      >
                                        <div>
                                          {/* Status badge */}
                                          <div className="mb-1">
                                            {loc.is_active ? (
                                              <span className="cd-timeline-badge" style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e' }}>Attivo</span>
                                            ) : (
                                              <span className="cd-timeline-badge" style={{ background: 'rgba(107,114,128,0.15)', color: '#6b7280' }}>Concluso</span>
                                            )}
                                          </div>

                                          {/* Location icon */}
                                          <div className="d-flex justify-content-center mb-1">
                                            <div
                                              className="rounded-circle d-flex align-items-center justify-content-center"
                                              style={{ width: '36px', height: '36px', background: `${bgColor}20` }}
                                            >
                                              <i className={locationIcons[loc.location]} style={{ color: bgColor, fontSize: '1rem' }}></i>
                                            </div>
                                          </div>

                                          {/* Location name */}
                                          <div className="cd-timeline-card-name">
                                            {locationLabels[loc.location] || loc.location}
                                          </div>

                                          {/* Duration */}
                                          {loc.duration_days > 0 && !loc.is_active && (
                                            <div className="text-muted" style={{ fontSize: '0.6rem' }}>
                                              {loc.duration_days} giorni
                                            </div>
                                          )}

                                          {/* Edit hint */}
                                          <div className="text-primary mt-1" style={{ fontSize: '0.6rem' }}>
                                            <i className="ri-edit-line me-1"></i>Modifica
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })}
                            </div>
                          </div>
                        )}
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== ANAMNESI SUB-TAB (Coaching) ===== */}
                  {coachingSubTab === 'anamnesi' && (
                    <div>
                      <div className="cd-sections">
                      <div>
                        <div className="cd-section-title">
                          Anamnesi Coaching
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-row">
                              <div className="cd-inner-card-header-left">
                                <div className="cd-icon-circle orange">
                                  <i className="ri-file-list-3-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Anamnesi Coach</span>
                              </div>
                              <button
                                className="cd-btn-save"
                                onClick={handleSaveAnamnesiCoaching}
                                disabled={savingAnamnesiCoaching || loadingAnamnesiCoaching}
                              >
                                {savingAnamnesiCoaching ? (
                                  <><span className="cd-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }}></span>Salvataggio...</>
                                ) : (
                                  <><i className="ri-save-line"></i>Salva</>
                                )}
                              </button>
                            </div>

                            {loadingAnamnesiCoaching ? (
                              <div className="cd-loading">
                                <div className="cd-spinner" role="status"></div>
                                <small className="ms-2 text-muted">Caricamento anamnesi...</small>
                              </div>
                            ) : (
                              <>
                                <div className="cd-field">
                                  <textarea
                                    className="cd-textarea"
                                    rows="8"
                                    placeholder="Scrivi qui l'anamnesi sportiva del cliente...&#10;&#10;• Storia sportiva&#10;• Infortuni pregressi&#10;• Obiettivi&#10;• Note iniziali"
                                    value={anamnesiCoachingContent}
                                    onChange={(e) => setAnamnesiCoachingContent(e.target.value)}
                                  ></textarea>
                                </div>
                                {anamnesiCoaching && (
                                  <div className="cd-prof-date border-top pt-2">
                                    <i className="ri-information-line me-1"></i>
                                    Creato: {anamnesiCoaching.created_at} da {anamnesiCoaching.created_by || 'N/D'}
                                    {anamnesiCoaching.last_modified_by && (
                                      <span className="ms-3">
                                        | Ultima modifica: {anamnesiCoaching.updated_at} da {anamnesiCoaching.last_modified_by}
                                      </span>
                                    )}
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== DIARIO SUB-TAB ===== */}
                  {coachingSubTab === 'diario' && (
                    <div data-tour="coaching-diario">
                      <div className="cd-sections">
                      <div>
                        <div className="cd-section-title">
                          Diario Coaching
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-row">
                              <div className="cd-inner-card-header-left">
                                <div className="cd-icon-circle pink">
                                  <i className="ri-book-2-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Note del Percorso</span>
                                <span className="cd-badge ms-2" style={{ background: 'rgba(107,114,128,0.1)', color: '#6b7280' }}>{diarioCoachingEntries.length}</span>
                              </div>
                              {canManageCoachingSection && (
                                <button
                                  className="cd-btn-save"
                                  onClick={() => handleOpenDiarioCoachingModal()}
                                >
                                  <i className="ri-add-line"></i>
                                  Nuova Nota
                                </button>
                              )}
                            </div>
                            {loadingDiarioCoaching ? (
                              <div className="cd-loading">
                                <div className="spinner-border spinner-border-sm text-primary" role="status"></div>
                                <small className="ms-2 cd-loading-text">Caricamento diario...</small>
                              </div>
                            ) : diarioCoachingEntries.length === 0 ? (
                              <p className="cd-empty-text mb-0 text-center py-3">
                                <i className="ri-information-line me-1"></i>
                                Nessuna nota nel diario. Clicca "Nuova Nota" per aggiungerne una.
                              </p>
                            ) : (
                              <div className="d-flex flex-column gap-3">
                                {diarioCoachingEntries.map((entry) => (
                                  <div key={entry.id} className="cd-diary-entry">
                                    <div className="cd-diary-header">
                                      <div className="cd-diary-meta">
                                        <span className="cd-badge" style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b' }}>
                                          <i className="ri-calendar-line me-1"></i>
                                          {entry.entry_date_display}
                                          {entry.created_at && (
                                            <span className="ms-1 opacity-75 small">
                                              ({entry.created_at.split(' ')[1]})
                                            </span>
                                          )}
                                        </span>
                                        <small className="text-muted">
                                          <i className="ri-user-line me-1"></i>
                                          {entry.author}
                                        </small>
                                      </div>
                                      <div className="cd-diary-actions">
                                        {canManageCoachingSection && (
                                          <button
                                            className="cd-btn-action-sm"
                                            onClick={() => handleOpenDiarioCoachingModal(entry)}
                                            title="Modifica"
                                          >
                                            <i className="ri-edit-line"></i>
                                          </button>
                                        )}
                                        {(user?.is_admin || user?.role === 'admin') && (
                                          <button
                                            className="cd-btn-action-sm danger"
                                            onClick={() => handleDeleteDiarioCoaching(entry.id)}
                                            title="Elimina"
                                          >
                                            <i className="ri-delete-bin-line"></i>
                                          </button>
                                        )}
                                        <button
                                          className="cd-btn-action-sm"
                                          onClick={() => handleOpenHistoryModal(entry, 'coaching')}
                                          title="Storico Modifiche"
                                        >
                                          <i className="ri-history-line"></i>
                                        </button>
                                      </div>
                                    </div>
                                    <p className="mb-0 cd-diary-content">{entry.content}</p>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== ALERT SUB-TAB ===== */}
                  {coachingSubTab === 'alert' && (
                    <div data-tour="coaching-alert">
                      <div className="cd-sections">
                      <div>
                        <div className="cd-section-title">
                          Alert e Criticità
                        </div>
                        <div className="cd-inner-card danger-border">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle danger">
                                <i className="ri-alarm-warning-line"></i>
                              </div>
                              <span className="cd-inner-card-title danger">Alert Coaching</span>
                            </div>
                            <p className="text-muted small mb-2">
                              Informazioni critiche: infortuni, limitazioni fisiche, controindicazioni.
                              Queste note saranno sempre visibili in evidenza.
                            </p>
                            <div className="cd-field">
                            <textarea
                              className="cd-textarea"
                              rows="4"
                              placeholder="Es: Ernia lombare, Non può fare squat profondi, Problemi alle ginocchia..."
                              value={formData.alert_coaching || ''}
                              onChange={(e) => handleInputChange('alert_coaching', e.target.value)}
                            ></textarea>
                            </div>
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {coachingSubTab === 'vecchie_note' && (
                    <div>
                      <div className="cd-sections">
                        <div>
                          <div className="cd-section-title">
                            <i className="ri-archive-line"></i>
                            Vecchie Note Coach (legacy)
                          </div>
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                                <div className="cd-icon-circle secondary">
                                  <i className="ri-history-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Storia Coach</span>
                              </div>
                              <textarea
                                className="cd-textarea"
                                rows="8"
                                placeholder="Nessuna storia coach..."
                                value={formData.storia_coach || ''}
                                onChange={(e) => handleInputChange('storia_coach', e.target.value)}
                              ></textarea>
                            </div>
                          </div>
                          <div className="cd-inner-card" style={{ marginTop: '16px' }}>
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                                <div className="cd-icon-circle secondary">
                                  <i className="ri-file-text-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Note Extra Coach</span>
                              </div>
                              <textarea
                                className="cd-textarea"
                                rows="8"
                                placeholder="Nessuna nota extra..."
                                value={formData.note_extra_coach || ''}
                                onChange={(e) => handleInputChange('note_extra_coach', e.target.value)}
                              ></textarea>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ========== PSICOLOGIA TAB ========== */}
              {activeTab === 'psicologia' && (
                <div>
                  {/* Alert Psicologia - show at top if present */}
                  {formData.alert_psicologia && (
                    <div>
                      <div className="cd-alert cd-alert-danger">
                        <i className="ri-alarm-warning-line fs-4"></i>
                        <div>
                          <strong className="small">Alert Psicologia</strong>
                          <p className="mb-0 small">{formData.alert_psicologia}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Sub-tab Navigation - Same style as Nutrizione/Coaching */}
                  <div className="col-12" data-tour="psicologia-subtabs">
                    <ScrollableSubtabs>
                        {[
                          { key: 'panoramica', label: 'Panoramica', icon: 'ri-dashboard-line', color: 'purple' },
                          { key: 'setup', label: 'Setup', icon: 'ri-settings-3-line', color: 'blue' },
                          { key: 'patologie', label: 'Anamnesi', icon: 'ri-mental-health-line', color: 'red' },
                          { key: 'diario', label: 'Diario', icon: 'ri-book-2-line', color: 'pink' },
                          { key: 'alert', label: 'Alert', icon: 'ri-alarm-warning-line', color: 'red' },
                          { key: 'vecchie_note', label: 'Vecchie Note', icon: 'ri-archive-line', color: 'secondary' },
                        ].map(({ key, label, icon, color }) => (
                            <button
                              key={key}
                              className={`cd-subtab ${psicologiaSubTab === key ? `active ${color}` : ''}`}
                              onClick={() => setPsicologiaSubTab(key)}
                            >
                              <i className={icon}></i>
                              {label}
                            </button>
                        ))}
                    </ScrollableSubtabs>
                  </div>

                  {/* ===== PANORAMICA SUB-TAB ===== */}
                  {psicologiaSubTab === 'panoramica' && (
                    <div data-tour="psicologia-panoramica">
                      <div className="cd-sections">
                      {/* Psicologi Assegnati */}
                      <div>
                        <div className="cd-section-title">
                          Psicologi Assegnati
                        </div>
                        {loadingHistory ? (
                          <div className="cd-loading">
                            <div className="spinner-border spinner-border-sm" role="status"></div>
                            <small className="ms-2 cd-loading-text">Caricamento...</small>
                          </div>
                        ) : (
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-row">
                                <div className="cd-inner-card-header-left">
                                  <div className="cd-icon-circle purple lg">
                                    <i className="ri-mental-health-line"></i>
                                  </div>
                                  <span className="cd-inner-card-title">Team Psicologia</span>
                                </div>
                                <span className="cd-badge" style={{ background: 'rgba(168,85,247,0.1)', color: '#a855f7' }}>{getActiveProfessionals('psicologa').length} attivi</span>
                              </div>

                              {getActiveProfessionals('psicologa').length > 0 ? (
                                <div className="d-flex flex-wrap gap-2">
                                  {getActiveProfessionals('psicologa').map((assignment, idx) => (
                                    <div key={idx} className="cd-assignment-row">
                                      <div className="cd-assignment-info">
                                      {assignment.avatar_path ? (
                                        <img src={assignment.avatar_path} alt="" className="cd-prof-avatar" />
                                      ) : (
                                        <div className="cd-prof-initials lg" style={{ background: '#a855f7' }}>
                                          {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                        </div>
                                      )}
                                      <div>
                                        <span className="cd-prof-name">{assignment.professionista_nome}</span>
                                        <span className="cd-prof-date">dal {assignment.data_dal}</span>
                                      </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-muted small mb-0">Nessun psicologo assegnato. Vai alla tab "Team" per assegnare.</p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Storico Assegnazioni Timeline */}
                      {professionistiHistory.filter(h => h.tipo_professionista === 'psicologa').length > 0 && (
                        <div>
                          <div className="cd-section-title">
                            <i className="ri-history-line"></i>
                            Storico Assegnazioni
                          </div>
                          <div className="cd-timeline">
                            <div className="cd-timeline-line" style={{ background: 'linear-gradient(to right, #a855f7, #7c3aed)' }}></div>
                            <div className="cd-timeline-items">
                              {professionistiHistory
                                .filter(h => h.tipo_professionista === 'psicologa')
                                .sort((a, b) => {
                                  const dateA = new Date(a.data_dal?.split('/').reverse().join('-') || 0);
                                  const dateB = new Date(b.data_dal?.split('/').reverse().join('-') || 0);
                                  return dateB - dateA;
                                })
                                .map((item, idx) => (
                                  <div key={idx} className="cd-timeline-item">
                                    <div className="cd-timeline-dot-wrap">
                                      <div className="cd-timeline-dot" style={{ background: '#a855f7' }}>
                                        <i className="ri-mental-health-line"></i>
                                      </div>
                                    </div>
                                    <div className="cd-timeline-date">
                                      {item.data_dal || '—'}
                                      {item.data_al && <span className="d-block">→ {item.data_al}</span>}
                                    </div>
                                    <div className={`cd-timeline-card ${!item.is_active ? 'inactive' : ''}`}>
                                      <div>
                                        <div className="mb-2">
                                          {item.is_active ? (
                                            <span className="cd-timeline-badge" style={{ background: 'rgba(168,85,247,0.15)', color: '#a855f7' }}>Attivo</span>
                                          ) : (
                                            <span className="cd-timeline-badge" style={{ background: 'rgba(107,114,128,0.15)', color: '#6b7280' }}>Concluso</span>
                                          )}
                                        </div>
                                        <div className="d-flex justify-content-center mb-2">
                                          {item.avatar_path ? (
                                            <img src={item.avatar_path} alt="" className="cd-timeline-card-avatar" />
                                          ) : (
                                            <div className="cd-timeline-card-initials" style={{ background: '#a855f7' }}>
                                              {item.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                        </div>
                                        <div className="cd-timeline-card-name">
                                          {item.professionista_nome}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Stati Servizio e Chat */}
                      <div>
                        <div className="cd-section-title">Stato Servizio</div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle purple">
                                <i className="ri-mental-health-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Stato Psicologia</span>
                            </div>
                            <div className="cd-field">
                            <select
                              className="cd-select sm"
                              value={formData.stato_psicologia || ''}
                              onChange={(e) => handleInputChange('stato_psicologia', e.target.value)}
                            >
                              <option value="">Seleziona stato...</option>
                              <option value="attivo">Attivo</option>
                              <option value="pausa">Pausa</option>
                              <option value="ghost">Ghost</option>
                              <option value="stop">Ex-Cliente</option>
                            </select>
                            </div>
                            {c.stato_psicologia_data && (
                              <span className="cd-prof-date">
                                <i className="ri-calendar-line me-1"></i>
                                Ultimo cambio: {new Date(c.stato_psicologia_data).toLocaleDateString('it-IT')}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div>
                        <div className="cd-section-title">Stato Chat</div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle secondary">
                                <i className="ri-chat-3-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Stato Chat Psicologia</span>
                            </div>
                            <div className="cd-field">
                            <select
                              className="cd-select sm"
                              value={formData.stato_cliente_chat_psicologia || ''}
                              onChange={(e) => handleInputChange('stato_cliente_chat_psicologia', e.target.value)}
                            >
                              <option value="">Seleziona stato...</option>
                              <option value="attivo">Attivo</option>
                              <option value="pausa">Pausa</option>
                              <option value="ghost">Ghost</option>
                            </select>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Timeline Storico Stati Unificata */}
                      <div>
                        <div className="cd-section-title">
                          <i className="ri-history-line"></i>
                          Storico Stati (Servizio + Chat)
                        </div>
                        {loadingStoricoPsicologia ? (
                          <div className="cd-loading">
                            <div className="spinner-border spinner-border-sm" style={{ color: '#a855f7' }} role="status"></div>
                            <small className="ms-2 cd-loading-text">Caricamento storico...</small>
                          </div>
                        ) : (storicoStatoPsicologia.length > 0 || storicoChatPsicologia.length > 0) ? (
                          <div className="cd-timeline">
                            <div className="cd-timeline-line" style={{ background: 'linear-gradient(to right, #a855f7, #6b7280)' }}></div>
                            <div className="cd-timeline-items">
                              {[
                                ...storicoStatoPsicologia.map(item => ({ ...item, tipo: 'servizio' })),
                                ...storicoChatPsicologia.map(item => ({ ...item, tipo: 'chat' }))
                              ]
                                .sort((a, b) => {
                                  const dateA = new Date(a.data_inizio?.split('/').reverse().join('-') || 0);
                                  const dateB = new Date(b.data_inizio?.split('/').reverse().join('-') || 0);
                                  return dateB - dateA;
                                })
                                .map((item, idx) => {
                                  const isServizio = item.tipo === 'servizio';
                                  const bgColor = isServizio ? '#a855f7' : '#6b7280';
                                  const icon = isServizio ? 'ri-mental-health-line' : 'ri-chat-3-line';
                                  return (
                                    <div key={idx} className="cd-timeline-item">
                                      <div className="cd-timeline-dot-wrap">
                                        <div className="cd-timeline-dot" style={{ background: bgColor }}>
                                          <i className={icon}></i>
                                        </div>
                                      </div>
                                      <div className="cd-timeline-date">
                                        {item.data_inizio || '—'}
                                        {item.data_fine && <span className="d-block">→ {item.data_fine}</span>}
                                      </div>
                                      <div className={`cd-timeline-card ${!item.is_attivo ? 'inactive' : ''}`}>
                                        <div>
                                          <div className="mb-1">
                                            <span className="cd-timeline-badge" style={{ background: isServizio ? 'rgba(168,85,247,0.15)' : 'rgba(107,114,128,0.15)', color: bgColor }}>
                                              {isServizio ? 'Servizio' : 'Chat'}
                                            </span>
                                          </div>
                                          <div className="mb-1">
                                            <span className={`badge bg-${STATUS_COLORS[item.stato] || 'secondary'}`} style={{ fontSize: '0.7rem' }}>
                                              {STATO_LABELS[item.stato] || item.stato}
                                            </span>
                                          </div>
                                          {item.is_attivo && (
                                            <div style={{ fontSize: '0.65rem', color: '#a855f7' }}>
                                              <i className="ri-checkbox-circle-fill me-1"></i>In corso
                                            </div>
                                          )}
                                          {item.durata_giorni > 0 && !item.is_attivo && (
                                            <div className="text-muted" style={{ fontSize: '0.6rem' }}>{item.durata_giorni} giorni</div>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  );
                                })}
                            </div>
                          </div>
                        ) : (
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body cd-empty">
                              <i className="ri-history-line cd-empty-icon"></i>
                              <p className="mb-0 cd-empty-text">Nessuno storico stati disponibile</p>
                              <small className="cd-empty-text">I cambi di stato verranno tracciati automaticamente</small>
                            </div>
                          </div>
                        )}
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== SETUP SUB-TAB ===== */}
                  {psicologiaSubTab === 'setup' && (
                    <div data-tour="psicologia-setup">
                      <div className="cd-sections">
                      {/* Call Iniziale */}
                      <div>
                        <div className="cd-section-title">Call Iniziale</div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle primary">
                                <i className="ri-phone-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Call Iniziale Psicologa</span>
                            </div>
                            <div className="form-check form-switch mb-2">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                id="callPsicologa"
                                checked={formData.call_iniziale_psicologa || false}
                                onChange={(e) => handleInputChange('call_iniziale_psicologa', e.target.checked)}
                              />
                              <label className="form-check-label small" htmlFor="callPsicologa">
                                {formData.call_iniziale_psicologa ? 'Effettuata' : 'Non effettuata'}
                              </label>
                              {formData.call_iniziale_psicologa && (
                                <span className="cd-badge ms-2" style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>Completata</span>
                              )}
                            </div>
                            {formData.call_iniziale_psicologa && (
                              <div className="cd-field mt-3">
                                <label className="cd-field-label">Data Call</label>
                                <DatePicker
                                  className="cd-input sm"
                                  value={formData.data_call_iniziale_psicologia || ''}
                                  onChange={(e) => handleInputChange('data_call_iniziale_psicologia', e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Reach Out */}
                      <div>
                        <div className="cd-section-title">Reach Out Settimanale</div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle info">
                                <i className="ri-calendar-check-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Giorno Reach Out</span>
                            </div>
                            <div className="cd-field">
                            <select
                              className="cd-select sm"
                              value={formData.reach_out_psicologia || ''}
                              onChange={(e) => handleInputChange('reach_out_psicologia', e.target.value)}
                            >
                              <option value="">Seleziona giorno...</option>
                              <option value="lunedi">Lunedì</option>
                              <option value="martedi">Martedì</option>
                              <option value="mercoledi">Mercoledì</option>
                              <option value="giovedi">Giovedì</option>
                              <option value="venerdi">Venerdì</option>
                              <option value="sabato">Sabato</option>
                              <option value="domenica">Domenica</option>
                            </select>
                            </div>
                            {formData.reach_out_psicologia && (
                              <span className="cd-prof-date d-block mt-2">
                                <i className="ri-calendar-event-line me-1"></i>
                                Reach out ogni {{ lunedi: 'Lunedì', martedi: 'Martedì', mercoledi: 'Mercoledì', giovedi: 'Giovedì', venerdi: 'Venerdì', sabato: 'Sabato', domenica: 'Domenica' }[formData.reach_out_psicologia]}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Sedute Counter */}
                      <div>
                        <div className="cd-section-title">Sedute Acquistate</div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="d-flex align-items-center justify-content-between">
                              <div className="cd-inner-card-header-left">
                                <div className="cd-icon-circle cart xl">
                                  <i className="ri-shopping-cart-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Sedute Comprate</span>
                              </div>
                              <input
                                type="number"
                                className="cd-input sm cd-number-input-sm"
                                min="0"
                                value={formData.sedute_psicologia_comprate || 0}
                                onChange={(e) => handleInputChange('sedute_psicologia_comprate', parseInt(e.target.value) || 0)}
                              />
                            </div>
                          </div>
                        </div>
                      </div>

                      <div>
                        <div className="cd-section-title">Sedute Svolte</div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="d-flex align-items-center justify-content-between">
                              <div className="cd-inner-card-header-left">
                                <div className="cd-icon-circle check-done xl">
                                  <i className="ri-check-double-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Sedute Svolte</span>
                              </div>
                              <input
                                type="number"
                                className="cd-input sm cd-number-input-sm"
                                min="0"
                                value={formData.sedute_psicologia_svolte || 0}
                                onChange={(e) => handleInputChange('sedute_psicologia_svolte', parseInt(e.target.value) || 0)}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== PATOLOGIE SUB-TAB ===== */}
                  {psicologiaSubTab === 'patologie' && (
                    <div data-tour="psicologia-patologie">
                      <div className="cd-sections">
                      <div>
                        <div className="cd-section-title">Patologie Psicologiche</div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle warning">
                                <i className="ri-stethoscope-line"></i>
                              </div>
                              <span className="cd-inner-card-title">Patologie Psicologiche</span>
                            </div>

                            {/* Nessuna Patologia */}
                            <div className={`cd-no-pathology-banner ${formData.nessuna_patologia_psico ? 'active' : ''} mb-3`}>
                              <div className="form-check mb-0">
                                <input
                                  className="form-check-input"
                                  type="checkbox"
                                  id="nessuna_patologia_psico"
                                  checked={formData.nessuna_patologia_psico || false}
                                  onChange={(e) => handleInputChange('nessuna_patologia_psico', e.target.checked)}
                                />
                                <label className={`form-check-label small ${formData.nessuna_patologia_psico ? 'fw-semibold text-success' : ''}`} htmlFor="nessuna_patologia_psico">
                                  Nessuna Patologia Psicologica
                                </label>
                              </div>
                            </div>

                            {/* Lista patologie */}
                            <div className="cd-pathology-grid">
                              {PATOLOGIE_PSICO.map(({ key, label }) => (
                                <div key={key}>
                                  <div className="form-check">
                                    <input
                                      className="form-check-input"
                                      type="checkbox"
                                      id={key}
                                      checked={formData[key] || false}
                                      onChange={(e) => handleInputChange(key, e.target.checked)}
                                    />
                                    <label className={`form-check-label small ${formData[key] ? 'fw-medium' : ''}`} htmlFor={key}>
                                      {label}
                                    </label>
                                  </div>
                                </div>
                              ))}
                              {/* Altro Checkbox Psicologia */}
                              <div>
                                <div className="form-check">
                                  <input
                                    className="form-check-input"
                                    type="checkbox"
                                    id="patologia_psico_altro_check"
                                    checked={formData.patologia_psico_altro_check || false}
                                    onChange={(e) => handleInputChange('patologia_psico_altro_check', e.target.checked)}
                                  />
                                  <label className={`form-check-label small ${formData.patologia_psico_altro_check ? 'fw-medium' : ''}`} htmlFor="patologia_psico_altro_check">
                                    Altro...
                                  </label>
                                </div>
                              </div>
                            </div>

                            {/* Altro Input Psicologia */}
                            {formData.patologia_psico_altro_check && (
                              <div className="cd-field mt-2">
                                <input
                                  type="text"
                                  className="cd-input sm"
                                  placeholder="Specifica altra patologia psicologica..."
                                  value={formData.patologia_psico_altro || ''}
                                  onChange={(e) => handleInputChange('patologia_psico_altro', e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* ===== ANAMNESI PSICOLOGIA ===== */}
                      <div>
                        <div className="cd-section-title">Anamnesi Psicologica</div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-row">
                              <div className="cd-inner-card-header-left">
                                <div className="cd-icon-circle purple">
                                  <i className="ri-file-list-3-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Anamnesi Psicologia</span>
                              </div>
                              <button
                                className="cd-btn-save"
                                onClick={handleSaveAnamnesiPsicologia}
                                disabled={savingAnamnesiPsicologia || loadingAnamnesiPsicologia}
                              >
                                {savingAnamnesiPsicologia ? (
                                  <><span className="cd-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }}></span>Salvataggio...</>
                                ) : (
                                  <><i className="ri-save-line"></i>Salva</>
                                )}
                              </button>
                            </div>

                            {loadingAnamnesiPsicologia ? (
                              <div className="cd-loading">
                                <div className="cd-spinner" role="status"></div>
                                <small className="ms-2 text-muted">Caricamento anamnesi...</small>
                              </div>
                            ) : (
                              <>
                                <div className="cd-field">
                                  <textarea
                                    className="cd-textarea"
                                    rows="8"
                                    placeholder="Scrivi qui l'anamnesi psicologica del cliente...&#10;&#10;• Storia clinica&#10;• Motivazioni&#10;• Obiettivi terapeutici&#10;• Note iniziali"
                                    value={anamnesiPsicologiaContent}
                                    onChange={(e) => setAnamnesiPsicologiaContent(e.target.value)}
                                  ></textarea>
                                </div>
                                {anamnesiPsicologia && (
                                  <div className="cd-prof-date border-top pt-2">
                                    <i className="ri-information-line me-1"></i>
                                    Creato: {anamnesiPsicologia.created_at} da {anamnesiPsicologia.created_by || 'N/D'}
                                    {anamnesiPsicologia.last_modified_by && (
                                      <span className="ms-3">
                                        | Ultima modifica: {anamnesiPsicologia.updated_at} da {anamnesiPsicologia.last_modified_by}
                                      </span>
                                    )}
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}



                  {/* ===== DIARIO SUB-TAB ===== */}
                  {psicologiaSubTab === 'diario' && (
                    <div data-tour="psicologia-diario">
                      <div className="cd-sections">
                      <div>
                        <div className="cd-section-title">
                          Diario Psicologia
                        </div>
                        <div className="cd-inner-card">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-row">
                              <div className="cd-inner-card-header-left">
                                <div className="cd-icon-circle purple">
                                  <i className="ri-book-2-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Note del Percorso</span>
                                <span className="cd-badge ms-2" style={{ background: 'rgba(168,85,247,0.1)', color: '#a855f7' }}>{diarioPsicologiaEntries.length}</span>
                              </div>
                              {canManagePsychologySection && (
                                <button
                                  className="cd-btn-save"
                                  style={{ background: '#a855f7' }}
                                  onClick={() => handleOpenDiarioPsicologiaModal()}
                                >
                                  <i className="ri-add-line"></i>
                                  Nuova Nota
                                </button>
                              )}
                            </div>

                            {loadingDiarioPsicologia ? (
                              <div className="cd-loading">
                                <div className="spinner-border spinner-border-sm" style={{ color: '#a855f7' }} role="status"></div>
                                <small className="ms-2 cd-loading-text">Caricamento diario...</small>
                              </div>
                            ) : diarioPsicologiaEntries.length === 0 ? (
                              <p className="cd-empty-text mb-0 text-center py-3">
                                <i className="ri-information-line me-1"></i>
                                Nessuna nota nel diario. Clicca "Nuova Nota" per aggiungerne una.
                              </p>
                            ) : (
                              <div className="d-flex flex-column gap-3">
                                {diarioPsicologiaEntries.map((entry) => (
                                  <div key={entry.id} className="cd-diary-entry">
                                    <div className="cd-diary-header">
                                      <div className="cd-diary-meta">
                                        <span className="cd-badge me-2" style={{ background: '#f3e8ff', color: '#a855f7' }}>
                                          <i className="ri-calendar-line me-1"></i>
                                          {entry.entry_date_display || entry.entry_date}
                                          {entry.created_at && (
                                            <span className="ms-1 opacity-75 small">
                                              ({entry.created_at.split(' ')[1]})
                                            </span>
                                          )}
                                        </span>
                                        <small className="text-muted">
                                          <i className="ri-user-line me-1"></i>
                                          {entry.author || 'Staff'}
                                        </small>
                                      </div>
                                      <div className="cd-diary-actions">
                                        {canManagePsychologySection && (
                                          <button
                                            className="cd-btn-action-sm"
                                            onClick={() => handleOpenDiarioPsicologiaModal(entry)}
                                            title="Modifica"
                                          >
                                            <i className="ri-edit-line"></i>
                                          </button>
                                        )}
                                        {(user?.is_admin || user?.role === 'admin') && (
                                          <button
                                            className="cd-btn-action-sm danger"
                                            onClick={() => handleDeleteDiarioPsicologia(entry.id)}
                                            title="Elimina"
                                          >
                                            <i className="ri-delete-bin-line"></i>
                                          </button>
                                        )}
                                        <button
                                          className="cd-btn-action-sm"
                                          onClick={() => handleOpenHistoryModal(entry, 'psicologia')}
                                          title="Storico Modifiche"
                                        >
                                          <i className="ri-history-line"></i>
                                        </button>
                                      </div>
                                    </div>
                                    <p className="mb-0 cd-diary-content">{entry.content}</p>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== ALERT SUB-TAB ===== */}
                  {psicologiaSubTab === 'alert' && (
                    <div data-tour="psicologia-alert">
                      <div className="cd-sections">
                      <div>
                        <div className="cd-section-title">Alert / Criticità</div>
                        <div className="cd-inner-card danger-border">
                          <div className="cd-inner-card-body">
                            <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                              <div className="cd-icon-circle danger">
                                <i className="ri-alarm-warning-line"></i>
                              </div>
                              <span className="cd-inner-card-title danger">Note Critiche Psicologia</span>
                            </div>
                            <div className="cd-field">
                            <textarea
                              className="cd-textarea"
                              rows="6"
                              placeholder="Inserisci qui eventuali alert o criticità importanti per la gestione del cliente...&#10;&#10;⚠️ Queste note sono visibili a tutto il team"
                              value={formData.alert_psicologia || ''}
                              onChange={(e) => handleInputChange('alert_psicologia', e.target.value)}
                            ></textarea>
                            </div>
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {psicologiaSubTab === 'vecchie_note' && (
                    <div>
                      <div className="cd-sections">
                        <div>
                          <div className="cd-section-title">
                            <i className="ri-archive-line"></i>
                            Vecchie Note Psicologa (legacy)
                          </div>
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                                <div className="cd-icon-circle secondary">
                                  <i className="ri-history-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Storia Psicologica</span>
                              </div>
                              <textarea
                                className="cd-textarea"
                                rows="8"
                                placeholder="Nessuna storia psicologica..."
                                value={formData.storia_psicologica || ''}
                                onChange={(e) => handleInputChange('storia_psicologica', e.target.value)}
                              ></textarea>
                            </div>
                          </div>
                          <div className="cd-inner-card" style={{ marginTop: '16px' }}>
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                                <div className="cd-icon-circle secondary">
                                  <i className="ri-file-text-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Note Extra Psicologa</span>
                              </div>
                              <textarea
                                className="cd-textarea"
                                rows="8"
                                placeholder="Nessuna nota extra..."
                                value={formData.note_extra_psicologa || ''}
                                onChange={(e) => handleInputChange('note_extra_psicologa', e.target.value)}
                              ></textarea>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ========== CHECK TAB ========== */}
              {/* ========== MEDICO TAB ========== */}
              {activeTab === 'medico' && (
                <div className="cal-coming-soon">
                  <div className="cal-hero">
                    <div className="cal-hero-icon">
                      <i className="ri-stethoscope-line"></i>
                    </div>
                    <h3 className="cal-hero-title">Medico</h3>
                    <p className="cal-hero-desc">
                      Qui potrai gestire le assegnazioni mediche, i controlli semestrali
                      e lo storico clinico del paziente.
                      <br />
                      <strong>Disponibile con la versione 1.1 della Suite Clinica.</strong>
                    </p>
                    <div className="cal-soon-badge">
                      <i className="ri-rocket-2-line"></i>
                      In arrivo — v1.1
                    </div>
                  </div>
                </div>
              )}

              {/* ========== CHECK PERIODICI TAB ========== */}
              {activeTab === 'check_periodici' && (
                <div>
                  {/* Pills Navigation */}
                  <div data-tour="check-periodici-tabs">
                    <ScrollableSubtabs style={{ marginBottom: '20px' }}>
                      <button
                        className={`cd-subtab${activePeriodiciTab === 'setup' ? ' active blue' : ''}`}
                        onClick={() => setActivePeriodiciTab('setup')}
                      >
                        Setup
                      </button>
                      <button
                        className={`cd-subtab${activePeriodiciTab === 'weekly' ? ' active green' : ''}`}
                        onClick={() => setActivePeriodiciTab('weekly')}
                      >
                        Settimanale
                      </button>
                      <button
                        className={`cd-subtab${activePeriodiciTab === 'dca' ? ' active purple' : ''}`}
                        onClick={() => setActivePeriodiciTab('dca')}
                      >
                        DCA
                      </button>
                      <button
                        className={`cd-subtab${activePeriodiciTab === 'minor' ? ' active orange' : ''}`}
                        onClick={() => setActivePeriodiciTab('minor')}
                      >
                        Minori
                      </button>
                    </ScrollableSubtabs>
                  </div>

                  {/* Setup Sub-tab */}
                  {activePeriodiciTab === 'setup' && (
                    <div>
                      <div className="cd-sections">
                        <div>
                          <div className="cd-section-title">
                            <i className="ri-settings-3-line"></i>
                            Configurazione Check
                          </div>
                          <div className="cd-inner-card">
                            <div className="cd-inner-card-body">
                              <div className="cd-inner-card-header-left" style={{ marginBottom: '12px' }}>
                                <div className="cd-icon-circle blue">
                                  <i className="ri-calendar-check-line"></i>
                                </div>
                                <span className="cd-inner-card-title">Giorno del Check</span>
                              </div>
                              <select
                                className="cd-select"
                                value={
                                  // Normalizza formato lungo → corto per match
                                  { lunedi: 'lun', martedi: 'mar', mercoledi: 'mer', giovedi: 'gio', venerdi: 'ven', sabato: 'sab', domenica: 'dom' }[formData.check_day] || formData.check_day || ''
                                }
                                onChange={(e) => handleInputChange('check_day', e.target.value)}
                              >
                                <option value="">-- Seleziona giorno --</option>
                                <option value="lun">Lunedì</option>
                                <option value="mar">Martedì</option>
                                <option value="mer">Mercoledì</option>
                                <option value="gio">Giovedì</option>
                                <option value="ven">Venerdì</option>
                                <option value="sab">Sabato</option>
                                <option value="dom">Domenica</option>
                              </select>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Link Generation Section (Filtered) */}
                  {activePeriodiciTab !== 'setup' && (
                  <div data-tour="check-periodici-link" style={{ marginBottom: '24px' }}>
                    {canGenerateCheckLinks ? (
                      <>
                        <div className="cd-section-title">
                          <i className="ri-link"></i>
                          Genera Link Check
                        </div>
                        <div className="cd-form-grid cols-3">
                      {Object.values(CHECK_TYPES)
                        .filter(t => t.key === activePeriodiciTab)
                        .map((checkType) => {
                        const existingCheck = checkData.checks[checkType.key];
                        return (
                          <div key={checkType.key}>
                            <div className="cd-inner-card">
                              <div className="cd-inner-card-body">
                                <div className="cd-check-type-header">
                                  <div className="cd-icon-circle lg" style={{ background: checkType.bgColor }}>
                                    <i className={checkType.icon} style={{ color: checkType.color, fontSize: '14px' }}></i>
                                  </div>
                                  <div>
                                    <span className="cd-inner-card-title">{checkType.label}</span>
                                    {existingCheck && (
                                      <span className="cd-empty-text" style={{ display: 'block', fontSize: '0.7rem' }}>
                                        {existingCheck.response_count} compilazioni
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="cd-check-actions">
                                  <button
                                    className="cd-btn-save"
                                    style={{ background: checkType.color, flex: 1, fontSize: '0.75rem' }}
                                    onClick={() => handleGenerateCheckLink(checkType.key)}
                                    disabled={generatingLink === checkType.key}
                                  >
                                    {generatingLink === checkType.key ? (
                                      <span className="spinner-border spinner-border-sm"></span>
                                    ) : (
                                      <i className={existingCheck ? 'ri-file-copy-line' : 'ri-add-line'}></i>
                                    )}
                                    {existingCheck ? 'Copia Link' : 'Genera Link'}
                                  </button>
                                  {existingCheck && (
                                    <button
                                      className="cd-btn-back"
                                      onClick={() => handleOpenCheckForm(existingCheck.url)}
                                      title="Apri form"
                                    >
                                      <i className="ri-external-link-line"></i>
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                        </div>
                      </>
                    ) : (
                      <div className="cd-alert cd-alert-info">
                        <span className="cd-empty-text">
                          La generazione dei link check non è disponibile per questo utente.
                        </span>
                      </div>
                    )}
                  </div>
                  )}

                  {/* Responses History Section (Filtered) */}
                  {activePeriodiciTab !== 'setup' && (
                  <div data-tour="check-periodici-risposte">
                    <div className="cd-section-title">
                      <i className="ri-history-line"></i>
                      Storico Compilazioni
                    </div>
                    <div className="cd-inner-card">
                      <div className="cd-inner-card-body">
                        {loadingChecks ? (
                          <div className="cd-loading">
                            <div className="spinner-border spinner-border-sm text-primary" role="status"></div>
                            <span className="cd-empty-text" style={{ marginLeft: '8px' }}>Caricamento check...</span>
                          </div>
                        ) : checkData.responses.filter(r => r.type === activePeriodiciTab).length === 0 ? (
                          <div className="cd-empty">
                            <i className="ri-inbox-line cd-empty-icon"></i>
                            <p className="cd-empty-text">Nessuna compilazione ricevuta</p>
                          </div>
                        ) : (
                          <div className="cd-table-wrap">
                            <table className="cd-table">
                              <thead>
                                <tr>
                                  <th>Data</th>
                                  <th>Tipo</th>
                                  <th style={{ textAlign: 'center' }}>Valutazioni</th>
                                  <th style={{ textAlign: 'center' }}>Azioni</th>
                                </tr>
                              </thead>
                              <tbody>
                                {checkData.responses
                                  .filter(r => r.type === activePeriodiciTab)
                                  .map((response) => (
                                  <tr key={`${response.source || response.type}-${response.id}`}>
                                    <td>
                                      <span style={{ fontWeight: 500 }}>{response.submit_date}</span>
                                    </td>
                                    <td>
                                      <span className="cd-badge" style={{
                                        background: response.source === 'typeform' ? '#f0f4ff' : (CHECK_TYPES[response.type]?.bgColor || '#f1f5f9'),
                                        color: response.source === 'typeform' ? '#6366f1' : (CHECK_TYPES[response.type]?.color || '#64748b'),
                                      }}>
                                        <i className={response.source === 'typeform' ? 'ri-survey-line' : CHECK_TYPES[response.type]?.icon}></i>
                                        {response.source === 'typeform' ? 'TypeForm' : (CHECK_TYPES[response.type]?.label || response.type)}
                                      </span>
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                      {response.type === 'weekly' && (
                                        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px' }}>
                                          {response.nutritionist_rating && (
                                            <span className="cd-badge" style={checkService.getRatingBadgeStyle(response.nutritionist_rating)} title="Nutrizionista">
                                              🥗 {response.nutritionist_rating}
                                            </span>
                                          )}
                                          {response.psychologist_rating && (
                                            <span className="cd-badge" style={checkService.getRatingBadgeStyle(response.psychologist_rating)} title="Psicologo">
                                              🧠 {response.psychologist_rating}
                                            </span>
                                          )}
                                          {response.coach_rating && (
                                            <span className="cd-badge" style={checkService.getRatingBadgeStyle(response.coach_rating)} title="Coach">
                                              🏋️ {response.coach_rating}
                                            </span>
                                          )}
                                          {response.progress_rating && (
                                            <span className="cd-badge" style={checkService.getRatingBadgeStyle(response.progress_rating)} title="Progresso">
                                              📈 {response.progress_rating}
                                            </span>
                                          )}
                                        </div>
                                      )}
                                      {response.type === 'minor' && response.score_global && (
                                        <span className="cd-badge" style={checkService.getRatingBadgeStyle(10 - response.score_global)}>
                                          EDE-Q6: {response.score_global.toFixed(1)}
                                        </span>
                                      )}
                                      {response.type === 'dca' && (
                                        <span className="cd-empty-text">-</span>
                                      )}
                                    </td>
                                    <td style={{ textAlign: 'center' }}>
                                      <button
                                        className="cd-btn-back"
                                        onClick={() => handleViewCheckResponse(response)}
                                        title="Visualizza dettagli"
                                      >
                                        <i className="ri-eye-line"></i>
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  )}
                </div>
              )}

              {/* ========== CHECK INIZIALI TAB ========== */}
              {activeTab === 'check_iniziali' && (
                <div>
                  {/* Pills Navigation */}
                  <div data-tour="check-iniziali-tabs">
                    <ScrollableSubtabs style={{ marginBottom: '20px' }}>
                      {[
                        { key: 'check_1', label: 'Nutrizione & Sport', icon: 'ri-heart-pulse-line' },
                        { key: 'check_2', label: 'Stile di Vita', icon: 'ri-user-heart-line' },
                        { key: 'check_3', label: 'Psicologico', icon: 'ri-mental-health-line' },
                      ].map(tab => (
                        <button
                          key={tab.key}
                          className={`cd-subtab${activeInizialiTab === tab.key ? ' active green' : ''}`}
                          onClick={() => setActiveInizialiTab(tab.key)}
                        >
                          <i className={tab.icon} style={{ marginRight: 4 }}></i> {tab.label}
                        </button>
                      ))}
                    </ScrollableSubtabs>
                  </div>

                  {/* Content */}
                  <div data-tour="check-iniziali-contenuto">
                    <div className="cd-inner-card">
                      <div className="cd-inner-card-body">
                        {loadingInitialChecks ? (
                          <div className="cd-loading">
                            <div className="spinner-border text-primary" role="status"></div>
                            <p className="cd-loading-text" style={{ marginTop: '8px' }}>Caricamento risposte...</p>
                          </div>
                        ) : !initialChecksData || !initialChecksData[activeInizialiTab] ? (
                          <div className="cd-empty">
                            <i className="ri-file-search-line cd-empty-icon"></i>
                            <h5>Nessun dato disponibile</h5>
                            <p className="cd-empty-text">Questo check non e' disponibile per questo cliente.</p>
                          </div>
                        ) : (() => {
                          const checkData = initialChecksData[activeInizialiTab];
                          const hasResponses = checkData.responses && Object.keys(checkData.responses).length > 0;
                          const hasUrl = checkData.url;

                          // Filter out redundant fields (email, phone, name) and empty values
                          const SKIP_KEYS = new Set([
                            'email', 'phone', 'last_name', 'first_name',
                            'privacy_accepted[]', 'privacy_accepted',
                          ]);
                          const formatLabel = (key) => {
                            return key
                              .replace(/_/g, ' ')
                              .replace(/\b\w/g, c => c.toUpperCase())
                              .replace(/\[\]/g, '')
                              .replace('[]', '');
                          };
                          const filteredResponses = hasResponses
                            ? Object.entries(checkData.responses).filter(([k, v]) => {
                                const keyLower = k.toLowerCase().replace(/\s+/g, '_');
                                if (SKIP_KEYS.has(keyLower)) return false;
                                if (v === null || v === undefined || v === '') return false;
                                return true;
                              })
                            : [];

                          // Check if this is a scale/frequency check (Check 3 style)
                          const SCALE_VALUES = new Set(['mai', 'raramente', 'a volte', 'spesso', 'sempre', 'il più delle volte', 'vero', 'falso']);
                          const isScaleCheck = activeInizialiTab === 'check_3' || (
                            filteredResponses.length > 10 &&
                            filteredResponses.filter(([, v]) => SCALE_VALUES.has(String(v).toLowerCase())).length > filteredResponses.length * 0.5
                          );

                          if (!hasResponses && hasUrl) {
                            return (
                              <div>
                                <div className="cd-alert cd-alert-info">
                                  <i className="ri-link" style={{ fontSize: '1.25rem', flexShrink: 0 }}></i>
                                  <div style={{ flex: 1 }}>
                                    <strong>Link da inviare al cliente</strong>
                                    <p className="cd-empty-text" style={{ marginBottom: '8px', marginTop: '4px' }}>Il cliente non ha ancora compilato. Copia il link qui sotto e invialo al cliente per permettergli di compilare il questionario.</p>
                                    <div style={{ display: 'flex', gap: '8px' }}>
                                      <input type="text" className="cd-input sm" value={checkData.url} readOnly style={{ flex: 1 }} />
                                      <button className="cd-btn-save" type="button" onClick={() => { navigator.clipboard.writeText(checkData.url); alert('Link copiato negli appunti'); }}>
                                        <i className="ri-file-copy-line"></i>Copia
                                      </button>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            );
                          }
                          if (!hasResponses && !hasUrl) {
                            return (
                              <div className="cd-empty">
                                <i className="ri-file-search-line cd-empty-icon"></i>
                                <h5>Nessun dato disponibile</h5>
                                <p className="cd-empty-text">Questo check non e' stato ancora compilato.</p>
                              </div>
                            );
                          }
                          return (
                            <div>
                              {/* Header with metadata */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>
                                    {filteredResponses.length} risposte
                                  </span>
                                  {checkData.completed_at && (
                                    <span className="cd-badge" style={{ background: '#f1f5f9', color: '#475569' }}>
                                      <i className="ri-calendar-event-line"></i>
                                      Compilato il: {new Date(checkData.completed_at).toLocaleDateString('it-IT')}
                                    </span>
                                  )}
                                  {checkData.score != null && (
                                    <span className="cd-badge" style={{ background: '#fef3c7', color: '#92400e' }}>
                                      <i className="ri-bar-chart-line"></i>
                                      Punteggio: {checkData.score}
                                    </span>
                                  )}
                                  {checkData.type != null && (
                                    <span className="cd-badge" style={{ background: '#ede9fe', color: '#5b21b6' }}>
                                      Tipo: {checkData.type}
                                    </span>
                                  )}
                                </div>
                                {hasUrl && (
                                  <button className="cd-btn-back" onClick={() => { navigator.clipboard.writeText(checkData.url); alert('Link copiato'); }}>
                                    <i className="ri-file-copy-line"></i>Copia link
                                  </button>
                                )}
                              </div>

                              {/* Attachments: photos and files */}
                              {checkData.attachments && checkData.attachments.length > 0 && (() => {
                                const photos = checkData.attachments.filter(a =>
                                  ['foto_frontale', 'foto_laterale', 'foto_posteriore', 'foto_attrezzatura'].includes(a.field_name)
                                );
                                const files = checkData.attachments.filter(a =>
                                  !['foto_frontale', 'foto_laterale', 'foto_posteriore', 'foto_attrezzatura'].includes(a.field_name)
                                );
                                const PHOTO_LABELS = {
                                  foto_frontale: 'Frontale',
                                  foto_laterale: 'Laterale',
                                  foto_posteriore: 'Posteriore',
                                  foto_attrezzatura: 'Attrezzatura',
                                };
                                const FILE_LABELS = {
                                  analisi_sangue: 'Analisi del Sangue',
                                  allegato_regime_alimentare: 'Regime Alimentare Pregresso',
                                };
                                return (
                                  <div style={{ marginBottom: '20px' }}>
                                    {photos.length > 0 && (
                                      <div style={{ marginBottom: '16px' }}>
                                        <h6 style={{ color: '#334155', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                          <i className="ri-camera-line"></i> Foto
                                        </h6>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
                                          {photos.map((att, i) => (
                                            <CheckPhoto key={i} url={att.download_url} label={PHOTO_LABELS[att.field_name] || formatLabel(att.field_name)} onClickFullscreen={(u) => setLightboxUrl(u)} />
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                    {files.length > 0 && (
                                      <div>
                                        <h6 style={{ color: '#334155', fontWeight: 600, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                          <i className="ri-attachment-line"></i> Allegati
                                        </h6>
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                          {files.map((att, i) => {
                                            const handleDownload = async () => {
                                              try {
                                                const resp = await api.get(att.download_url, { responseType: 'blob' });
                                                const url = URL.createObjectURL(resp.data);
                                                const link = document.createElement('a');
                                                link.href = url; link.download = att.filename || 'download'; link.click();
                                                URL.revokeObjectURL(url);
                                              } catch (e) { console.error('Download failed:', e); }
                                            };
                                            return (
                                              <div key={i} className="cd-response-item" onClick={handleDownload}
                                                style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 14px', cursor: 'pointer' }}>
                                                <i className="ri-file-download-line" style={{ fontSize: '1.2rem', color: '#25B36A' }}></i>
                                                <div>
                                                  <div style={{ fontWeight: 600, color: '#334155', fontSize: '0.85rem' }}>
                                                    {FILE_LABELS[att.field_name] || formatLabel(att.field_name)}
                                                  </div>
                                                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                                                    {att.filename}{att.size && ` - ${(att.size / 1024 / 1024).toFixed(1)} MB`}
                                                  </div>
                                                </div>
                                              </div>
                                            );
                                          })}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                );
                              })()}

                              {/* Scale/frequency check → compact table layout */}
                              {isScaleCheck ? (
                                <div className="cd-table-wrap">
                                  <table className="cd-table" style={{ fontSize: '0.85rem' }}>
                                    <thead>
                                      <tr>
                                        <th style={{ width: '60%' }}>Domanda</th>
                                        <th>Risposta</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {filteredResponses.map(([question, answer], idx) => {
                                        const ansStr = Array.isArray(answer) ? answer.join(', ') : String(answer);
                                        const isNegative = ['spesso', 'sempre', 'il più delle volte', 'vero'].includes(ansStr.toLowerCase());
                                        const isPositive = ['mai', 'falso'].includes(ansStr.toLowerCase());
                                        return (
                                          <tr key={idx}>
                                            <td style={{ fontWeight: 500, color: '#334155' }}>{formatLabel(question)}</td>
                                            <td>
                                              <span style={{
                                                display: 'inline-block',
                                                padding: '2px 10px',
                                                borderRadius: '12px',
                                                fontSize: '0.8rem',
                                                fontWeight: 600,
                                                background: isNegative ? '#fef2f2' : isPositive ? '#f0fdf4' : '#f8fafc',
                                                color: isNegative ? '#dc2626' : isPositive ? '#16a34a' : '#475569',
                                              }}>
                                                {ansStr}
                                              </span>
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              ) : (
                                /* Standard check → card grid layout */
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '10px' }}>
                                  {filteredResponses.map(([question, answer], idx) => {
                                    const ansStr = Array.isArray(answer) ? answer.join(', ') : String(answer);
                                    const isLongAnswer = ansStr.length > 80;
                                    return (
                                      <div key={idx} className="cd-response-item" style={isLongAnswer ? { gridColumn: '1 / -1' } : {}}>
                                        <div className="cd-response-question">{formatLabel(question)}</div>
                                        <div className="cd-response-answer">{ansStr}</div>
                                      </div>
                                    );
                                  })}
                                </div>
                              )}
                            </div>
                          );
                        })()}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ========== TICKETS TAB ========== */}
              {activeTab === 'tickets' && (
                <div>
                  {loadingTickets ? (
                    <div className="cd-loading">
                      <div className="spinner-border text-primary" role="status"></div>
                      <p className="cd-loading-text" style={{ marginTop: '8px' }}>Caricamento ticket...</p>
                    </div>
                  ) : patientTickets.length === 0 ? (
                    <div className="cd-empty">
                      <i className="ri-ticket-2-line cd-empty-icon"></i>
                      <p className="cd-empty-text">Nessun ticket associato a questo paziente</p>
                    </div>
                  ) : (
                    <div className="cd-table-wrap">
                      <table className="cd-table">
                        <thead>
                          <tr>
                            <th>Numero</th>
                            <th>Titolo</th>
                            <th>Stato</th>
                            <th>Priorita'</th>
                            <th>Assegnatari</th>
                            <th>Fonte</th>
                            <th>Data</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {patientTickets.map((t) => {
                            const statusCfg = {
                              aperto: { label: 'Aperto', bg: '#fef3c7', color: '#92400e' },
                              in_lavorazione: { label: 'In Lavorazione', bg: '#dbeafe', color: '#1e40af' },
                              risolto: { label: 'Risolto', bg: '#d1fae5', color: '#065f46' },
                              chiuso: { label: 'Chiuso', bg: '#f3f4f6', color: '#374151' },
                            }[t.status] || { label: t.status, bg: '#f3f4f6', color: '#374151' };
                            const prioCfg = {
                              alta: { label: 'Alta', bg: '#fee2e2', color: '#991b1b' },
                              media: { label: 'Media', bg: '#fef9c3', color: '#854d0e' },
                              bassa: { label: 'Bassa', bg: '#dcfce7', color: '#166534' },
                            }[t.priority] || { label: t.priority, bg: '#f3f4f6', color: '#374151' };
                            return (
                              <tr key={t.id} className="cd-cursor-pointer" onClick={() => openTicketDetail(t.id)}>
                                <td><span style={{ fontWeight: 600, color: '#3b82f6' }}>{t.ticket_number}</span></td>
                                <td>{t.title || <span className="cd-empty-text" style={{ fontStyle: 'italic' }}>{(t.description || '').slice(0, 50)}</span>}</td>
                                <td>
                                  <span className="cd-badge" style={{ background: statusCfg.bg, color: statusCfg.color }}>
                                    {statusCfg.label}
                                  </span>
                                </td>
                                <td>
                                  <span className="cd-badge" style={{ background: prioCfg.bg, color: prioCfg.color }}>
                                    {prioCfg.label}
                                  </span>
                                </td>
                                <td>
                                  <span className="cd-empty-text">
                                    {(t.assigned_users || []).map(u => u.name).join(', ') || '—'}
                                  </span>
                                </td>
                                <td>
                                  <i className={`ri-${t.source === 'teams' ? 'microsoft-line text-primary' : 'computer-line text-secondary'}`}></i>
                                </td>
                                <td><span className="cd-empty-text">{t.created_at ? new Date(t.created_at).toLocaleDateString('it-IT') : '—'}</span></td>
                                <td>
                                  <span className="cd-empty-text">
                                    {t.messages_count > 0 && <span style={{ marginRight: '8px' }}><i className="ri-chat-3-line"></i> {t.messages_count}</span>}
                                    {t.attachments_count > 0 && <span><i className="ri-attachment-2"></i> {t.attachments_count}</span>}
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* ==================== CALL BONUS TAB ==================== */}
              {activeTab === 'call_bonus' && (
                <div className="cal-coming-soon">
                  <div className="cal-hero">
                    <div className="cal-hero-icon">
                      <i className="ri-phone-line"></i>
                    </div>
                    <h3 className="cal-hero-title">Call Bonus</h3>
                    <p className="cal-hero-desc">
                      Qui potrai richiedere call bonus per i tuoi pazienti,
                      gestire le proposte AI e monitorare lo storico delle sessioni.
                      <br />
                      <strong>Disponibile con la versione 1.1 della Suite Clinica.</strong>
                    </p>
                    <div className="cal-soon-badge">
                      <i className="ri-rocket-2-line"></i>
                      In arrivo — v1.1
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ========== TICKET DETAIL MODAL ========== */}
      {(ticketDetailModal || loadingTicketDetail) && (
        <div className="cd-modal-backdrop" onClick={() => { setTicketDetailModal(null); setTicketMessages([]); }}>
          <div className="cd-modal lg full-height" onClick={(e) => e.stopPropagation()}>
            {loadingTicketDetail && !ticketDetailModal ? (
              <div className="cd-modal-body">
                <div className="cd-loading">
                  <div className="cd-spinner"></div>
                  <p className="cd-loading-text">Caricamento...</p>
                </div>
              </div>
            ) : ticketDetailModal && (
              <>
                <div className="cd-modal-header purple-bg">
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <h5>
                        <i className="ri-ticket-2-line text-primary"></i>
                        {ticketDetailModal.ticket_number}
                      </h5>
                      <span className="cd-badge" style={{
                        background: ({ aperto: '#fef3c7', in_lavorazione: '#dbeafe', risolto: '#d1fae5', chiuso: '#f3f4f6' })[ticketDetailModal.status] || '#f3f4f6',
                        color: ({ aperto: '#92400e', in_lavorazione: '#1e40af', risolto: '#065f46', chiuso: '#374151' })[ticketDetailModal.status] || '#374151',
                      }}>
                        {({ aperto: 'Aperto', in_lavorazione: 'In Lavorazione', risolto: 'Risolto', chiuso: 'Chiuso' })[ticketDetailModal.status] || ticketDetailModal.status}
                      </span>
                      <span className="cd-badge" style={{
                        background: ({ alta: '#fee2e2', media: '#fef9c3', bassa: '#dcfce7' })[ticketDetailModal.priority] || '#f3f4f6',
                        color: ({ alta: '#991b1b', media: '#854d0e', bassa: '#166534' })[ticketDetailModal.priority] || '#374151',
                      }}>
                        {({ alta: 'Alta', media: 'Media', bassa: 'Bassa' })[ticketDetailModal.priority] || ticketDetailModal.priority}
                      </span>
                      <i className={`ri-${ticketDetailModal.source === 'teams' ? 'microsoft-line text-primary' : 'computer-line text-secondary'}`}></i>
                    </div>
                    <span className="text-muted small">{ticketDetailModal.title || '(Senza titolo)'}</span>
                  </div>
                  <button className="cd-modal-close" onClick={() => { setTicketDetailModal(null); setTicketMessages([]); }}><i className="ri-close-line"></i></button>
                </div>
                <div className="cd-modal-body scrollable">
                  {/* Info */}
                  <div className="cd-form-grid cols-2" style={{ marginBottom: 24 }}>
                    <div>
                      <div className="cd-section-title">Assegnatari</div>
                      <div>{(ticketDetailModal.assigned_users || []).map(u => u.name).join(', ') || 'Nessuno'}</div>
                    </div>
                    <div>
                      <div className="cd-section-title">Creato da</div>
                      <div>{ticketDetailModal.created_by_name || 'Teams'} — {ticketDetailModal.created_at ? new Date(ticketDetailModal.created_at).toLocaleString('it-IT') : '—'}</div>
                    </div>
                    {ticketDetailModal.resolved_at && (
                      <div>
                        <div className="cd-section-title">Risolto il</div>
                        <div>{new Date(ticketDetailModal.resolved_at).toLocaleString('it-IT')}</div>
                      </div>
                    )}
                    {ticketDetailModal.closed_at && (
                      <div>
                        <div className="cd-section-title">Chiuso il</div>
                        <div>{new Date(ticketDetailModal.closed_at).toLocaleString('it-IT')}</div>
                      </div>
                    )}
                  </div>

                  {/* Descrizione */}
                  {ticketDetailModal.description && (
                    <div style={{ marginBottom: 24 }}>
                      <div className="cd-section-title">Descrizione</div>
                      <div className="cd-response-item cd-pre-wrap">{ticketDetailModal.description}</div>
                    </div>
                  )}

                  {/* Allegati */}
                  {ticketDetailModal.attachments && ticketDetailModal.attachments.length > 0 && (
                    <div style={{ marginBottom: 24 }}>
                      <div className="cd-section-title">
                        <i className="ri-attachment-2"></i>Allegati ({ticketDetailModal.attachments.length})
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {ticketDetailModal.attachments.map((att) => {
                          const sizeKb = att.file_size ? (att.file_size / 1024).toFixed(0) : '?';
                          return (
                            <a
                              key={att.id}
                              href={teamTicketsService.getAttachmentUrl(att.id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="cd-btn-back"
                            >
                              <i className={att.is_image ? 'ri-image-line' : 'ri-file-line'}></i>
                              {att.filename}
                              <span className="text-muted">({sizeKb} KB)</span>
                            </a>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Messaggi */}
                  {ticketMessages.length > 0 && (
                    <div>
                      <div className="cd-section-title">
                        <i className="ri-chat-3-line"></i>Messaggi ({ticketMessages.length})
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {ticketMessages.map((msg) => (
                          <div
                            key={msg.id}
                            className={`cd-ticket-msg ${msg.source === 'teams' ? 'teams' : 'internal'}`}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                              <span className="fw-semibold small">
                                <i className={`ri-${msg.source === 'teams' ? 'microsoft-line text-primary' : 'computer-line text-success'}`}></i>
                                {' '}{msg.sender_name || 'Anonimo'}
                              </span>
                              <small className="text-muted">{msg.created_at ? new Date(msg.created_at).toLocaleString('it-IT') : ''}</small>
                            </div>
                            <div className="small cd-pre-wrap">{msg.content}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                <div className="cd-modal-footer">
                  <button className="cd-btn-back" onClick={() => { setTicketDetailModal(null); setTicketMessages([]); }}>Chiudi</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* ========== CALL BONUS MODAL (3 steps) ========== */}
      {showCallBonusModal && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal lg">
            <div className="cd-modal-header purple-bg">
              <h5>
                <i className="ri-phone-line text-primary"></i>
                Richiedi Call Bonus
                <span className="cd-badge" style={{ background: 'rgba(59,130,246,0.15)', color: '#3b82f6', marginLeft: 8 }}>Step {callBonusStep}/3</span>
              </h5>
              <button className="cd-modal-close" onClick={() => setShowCallBonusModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">

                {/* ── STEP 1: Tipo + Note ── */}
                {callBonusStep === 1 && (
                  <div>
                    <p className="text-muted small" style={{ marginBottom: 12 }}>Seleziona il tipo di professionista e descrivi l'obiettivo della call bonus.</p>

                    <div className="cd-field">
                      <label className="cd-field-label">Tipo Professionista *</label>
                      <div style={{ display: 'flex', gap: 8 }}>
                        {[
                          { value: 'coach', label: 'Coaching', icon: 'ri-run-line', color: '#6366f1', bg: 'rgba(99,102,241,0.1)' },
                          { value: 'nutrizionista', label: 'Nutrizione', icon: 'ri-heart-pulse-line', color: '#10b981', bg: 'rgba(16,185,129,0.1)' },
                          { value: 'psicologa', label: 'Psicologia', icon: 'ri-mental-health-line', color: '#ec4899', bg: 'rgba(236,72,153,0.1)' },
                        ].map((t) => (
                          <button
                            key={t.value}
                            className={`cd-cb-type-btn${callBonusForm.tipo_professionista === t.value ? ' selected' : ''}`}
                            style={{
                              background: callBonusForm.tipo_professionista === t.value ? t.bg : '#f9fafb',
                              borderColor: callBonusForm.tipo_professionista === t.value ? t.color : '#e5e7eb',
                              color: t.color,
                            }}
                            onClick={() => setCallBonusForm({ ...callBonusForm, tipo_professionista: t.value })}
                          >
                            <i className={t.icon}></i>
                            <span className="small fw-semibold">{t.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="cd-field">
                      <label className="cd-field-label">Motivazione / Obiettivo</label>
                      <textarea
                        className="cd-textarea"
                        rows="4"
                        placeholder="Descrivi il motivo della richiesta e gli obiettivi della call bonus..."
                        value={callBonusForm.note_richiesta}
                        onChange={(e) => setCallBonusForm({ ...callBonusForm, note_richiesta: e.target.value })}
                      ></textarea>
                    </div>
                  </div>
                )}

                {/* ── STEP 2: AI Analysis + Matching ── */}
                {callBonusStep === 2 && (
                  <div>
                    {/* AI Analysis summary */}
                    {callBonusAnalysis && (
                      <div className="cd-ai-card">
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                          <i className="ri-robot-2-line text-primary"></i>
                          <span className="fw-semibold small">Analisi SuiteMind AI</span>
                        </div>
                        {callBonusAnalysis.summary && (
                          <p className="small text-muted" style={{ marginBottom: 8 }}>{callBonusAnalysis.summary}</p>
                        )}
                        {callBonusAnalysis.suggested_focus && callBonusAnalysis.suggested_focus.length > 0 && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                            {callBonusAnalysis.suggested_focus.map((f, i) => (
                              <span key={i} className="cd-badge xs" style={{ background: 'rgba(99,102,241,0.1)', color: '#6366f1' }}>
                                {f}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Professional matches */}
                    <p className="text-muted small" style={{ marginBottom: 12 }}>Seleziona il professionista per la call bonus:</p>
                    {callBonusMatches.length === 0 ? (
                      <div className="cd-empty">
                        <div className="cd-empty-icon"><i className="ri-user-search-line"></i></div>
                        <p className="cd-empty-text">Nessun professionista trovato per i criteri selezionati.</p>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        {callBonusMatches.map((prof) => (
                          <div
                            key={prof.id}
                            className="cd-cb-match-card"
                            onClick={() => handleSelectCallBonusProfessional(prof)}
                          >
                            {/* Avatar */}
                            <div className="cd-cb-avatar">
                              {prof.name ? prof.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : '??'}
                            </div>
                            {/* Info */}
                            <div style={{ flex: 1 }}>
                              <div className="fw-semibold small">{prof.name}</div>
                              {prof.match_reasons && prof.match_reasons.length > 0 && (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                                  {prof.match_reasons.slice(0, 4).map((r, i) => (
                                    <span key={i} className="cd-badge xs" style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981' }}>
                                      {r}
                                    </span>
                                  ))}
                                  {prof.match_reasons.length > 4 && (
                                    <span className="cd-badge xs" style={{ background: '#f3f4f6', color: '#6b7280' }}>
                                      +{prof.match_reasons.length - 4}
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                            {/* Score */}
                            <div style={{ textAlign: 'right', minWidth: 70 }}>
                              <div className="fw-bold" style={{ color: prof.score >= 70 ? '#10b981' : prof.score >= 40 ? '#f59e0b' : '#ef4444', fontSize: '1.1rem' }}>
                                {prof.score}%
                              </div>
                              <div className="progress" style={{ height: 4, width: 60 }}>
                                <div className="progress-bar" style={{ width: `${prof.score}%`, background: prof.score >= 70 ? '#10b981' : prof.score >= 40 ? '#f59e0b' : '#ef4444' }}></div>
                              </div>
                            </div>
                            <i className="ri-arrow-right-s-line text-muted"></i>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* ── STEP 3: Calendar Link + Confirm ── */}
                {callBonusStep === 3 && selectedCallBonusProfessional && (
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ marginBottom: 24 }}>
                      <div className="cd-cb-avatar lg" style={{ display: 'inline-flex', marginBottom: 12 }}>
                        {selectedCallBonusProfessional.name ? selectedCallBonusProfessional.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : '??'}
                      </div>
                      <h6 style={{ marginBottom: 4 }}>{selectedCallBonusProfessional.name}</h6>
                      <span className="cd-badge" style={{ background: 'rgba(99,102,241,0.1)', color: '#6366f1' }}>
                        Selezionato
                      </span>
                    </div>

                    <div style={{ marginBottom: 24 }}>
                      <p className="small fw-semibold" style={{ marginBottom: 8 }}>
                        <i className="ri-calendar-line text-primary"></i>
                        {' '}LINK CALL BONUS PROFESSIONISTA
                      </p>
                      {callBonusCalendarLink ? (
                        <a
                          href={callBonusCalendarLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="cd-btn-back"
                          style={{ padding: '12px 24px', fontSize: 14 }}
                        >
                          <i className="ri-calendar-line"></i>
                          Apri Calendario Call Bonus
                          <i className="ri-external-link-line"></i>
                        </a>
                      ) : (
                        <div className="cd-alert cd-alert-warning" style={{ display: 'inline-flex' }} role="alert">
                          <i className="ri-error-warning-line"></i>
                          <span className="small">Il professionista non ha configurato un link calendario per le call bonus.</span>
                        </div>
                      )}
                      <p className="text-muted small" style={{ marginTop: 8 }}>Prenota la call bonus nel calendario del professionista selezionato, poi conferma.</p>
                    </div>
                  </div>
                )}

            </div>
            <div className="cd-modal-footer">
              {callBonusStep === 1 && (
                <>
                  <button className="cd-btn-back" onClick={() => setShowCallBonusModal(false)}>Annulla</button>
                  <button
                    className="cd-btn-save"
                    onClick={handleCallBonusAnalyze}
                    disabled={!callBonusForm.tipo_professionista || callBonusAiLoading}
                  >
                    {callBonusAiLoading ? (
                      <><span className="spinner-border spinner-border-sm me-2"></span>Analisi in corso...</>
                    ) : (
                      <><i className="ri-robot-2-line"></i>Analizza con SuiteMind AI</>
                    )}
                  </button>
                </>
              )}
              {callBonusStep === 2 && (
                <button className="cd-btn-back" onClick={() => setCallBonusStep(1)}>
                  <i className="ri-arrow-left-line"></i>Indietro
                </button>
              )}
              {callBonusStep === 3 && (
                <>
                  <button className="cd-btn-back" onClick={() => setCallBonusStep(2)}>
                    <i className="ri-arrow-left-line"></i>Indietro
                  </button>
                  <button
                    className="cd-btn-save"
                    style={{ background: '#22c55e' }}
                    onClick={handleConfirmCallBonusBooking}
                    disabled={confirmingBooking}
                  >
                    {confirmingBooking ? (
                      <><span className="spinner-border spinner-border-sm me-2"></span>Conferma...</>
                    ) : (
                      <><i className="ri-check-line"></i>Ho prenotato la call</>
                    )}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Call Bonus Response Modal (professionista assegnato) */}
      {callBonusResponseModal && (
        <div className="cd-modal-backdrop" onClick={() => { setCallBonusResponseModal(null); setCallBonusInterestStep('ask'); }}>
          <div className="cd-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cd-modal-header purple-bg">
              <h5>
                <i className="ri-phone-line text-primary"></i>
                Risposta Call Bonus
              </h5>
              <button className="cd-modal-close" onClick={() => { setCallBonusResponseModal(null); setCallBonusInterestStep('ask'); }}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body" style={{ textAlign: 'center' }}>
              {/* Info richiesta */}
              <div className="cd-response-item" style={{ marginBottom: 24 }}>
                <p className="small text-muted" style={{ marginBottom: 4 }}>Richiesta da <strong>{callBonusResponseModal.created_by_nome}</strong></p>
                {callBonusResponseModal.note_richiesta && (
                  <p className="small fst-italic" style={{ marginBottom: 0 }}>"{callBonusResponseModal.note_richiesta}"</p>
                )}
              </div>

              {/* Step ASK: Il paziente è interessato? */}
              {callBonusInterestStep === 'ask' && (
                <div>
                  <p className="fw-semibold" style={{ marginBottom: 12 }}>Il paziente è interessato alla call bonus?</p>
                  <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
                    <button
                      className="cd-btn-save"
                      style={{ background: '#22c55e', padding: '12px 20px' }}
                      onClick={() => setCallBonusInterestStep('book_hm')}
                    >
                      <i className="ri-thumb-up-line"></i>Sì, interessato
                    </button>
                    <button
                      className="cd-btn-save"
                      style={{ background: '#ef4444', padding: '12px 20px' }}
                      onClick={handleDeclineCallBonus}
                      disabled={decliningCallBonus}
                    >
                      {decliningCallBonus ? (
                        <><span className="spinner-border spinner-border-sm me-2"></span>Invio...</>
                      ) : (
                        <><i className="ri-thumb-down-line"></i>No, non interessato</>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* Step BOOK_HM: Link HM + conferma prenotazione */}
              {callBonusInterestStep === 'book_hm' && (
                <div>
                  <div style={{ marginBottom: 24 }}>
                    <p className="small fw-semibold" style={{ marginBottom: 8 }}>
                      <i className="ri-calendar-line text-primary"></i>
                      {' '}LINK HM ASSOCIATO{callBonusResponseModal.hm_name ? ` — ${callBonusResponseModal.hm_name}` : ''}
                    </p>
                    {callBonusResponseModal.hm_calendar_link ? (
                      <a
                        href={callBonusResponseModal.hm_calendar_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="cd-btn-back"
                      >
                        <i className="ri-calendar-line"></i>
                        Apri Calendario HM
                        <i className="ri-external-link-line"></i>
                      </a>
                    ) : (
                      <div className="cd-alert cd-alert-warning" style={{ display: 'inline-flex' }} role="alert">
                        <i className="ri-error-warning-line"></i>
                        <span className="small">Link calendario HM non disponibile.</span>
                      </div>
                    )}
                    <p className="text-muted small" style={{ marginTop: 8 }}>Prenota la call bonus nel calendario dell'Health Manager, poi conferma.</p>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
                    <button
                      className="cd-btn-back"
                      onClick={() => setCallBonusInterestStep('ask')}
                    >
                      <i className="ri-arrow-left-line"></i>Indietro
                    </button>
                    <button
                      className="cd-btn-save"
                      style={{ background: '#22c55e' }}
                      onClick={handleConfirmCallBonusInterest}
                      disabled={confirmingBooking}
                    >
                      {confirmingBooking ? (
                        <><span className="spinner-border spinner-border-sm me-2"></span>Conferma...</>
                      ) : (
                        <><i className="ri-check-line"></i>Confermo prenotazione HM</>
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {showDeleteModal && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal">
            <div className="cd-modal-header">
              <h5>Conferma Eliminazione</h5>
              <button className="cd-modal-close" onClick={() => setShowDeleteModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <p>Sei sicuro di voler eliminare <strong>{c.nome}</strong>?</p>
              <p className="text-danger small">Questa azione non può essere annullata.</p>
            </div>
            <div className="cd-modal-footer">
              <button className="cd-btn-back" onClick={() => setShowDeleteModal(false)}>Annulla</button>
              <button className="cd-btn-save" style={{ background: '#ef4444' }} onClick={handleDelete} disabled={deleting}>
                {deleting ? <><span className="spinner-border spinner-border-sm me-2"></span>Eliminazione...</> : <><i className="ri-delete-bin-line"></i>Elimina</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assign Professional Modal */}
      {showAssignModal && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal">
            <div className="cd-modal-header">
              <h5>
                <i className={`${TIPO_PROFESSIONISTA_ICONS[assigningType]}`}></i>
                Assegna {TIPO_PROFESSIONISTA_LABELS[assigningType]}
              </h5>
              <button className="cd-modal-close" onClick={() => setShowAssignModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-field">
                <label className="cd-field-label">Professionista *</label>
                <select
                  className="cd-select"
                  value={assignForm.user_id}
                  onChange={(e) => setAssignForm({ ...assignForm, user_id: e.target.value })}
                >
                  <option value="">Seleziona professionista...</option>
                  {(availableProfessionals[assigningType] || []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.full_name || p.email}
                    </option>
                  ))}
                </select>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Data Inizio Assegnazione *</label>
                <DatePicker
                  className="cd-input"
                  value={assignForm.data_dal}
                  onChange={(e) => setAssignForm({ ...assignForm, data_dal: e.target.value })}
                />
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Motivazione Assegnazione *</label>
                <textarea
                  className="cd-textarea"
                  rows="3"
                  placeholder="Es: Inizio percorso, Cambio professionista per compatibilità, Nuova fase del programma..."
                  value={assignForm.motivazione_aggiunta}
                  onChange={(e) => setAssignForm({ ...assignForm, motivazione_aggiunta: e.target.value })}
                ></textarea>
              </div>
            </div>
            <div className="cd-modal-footer">
              <button className="cd-btn-back" onClick={() => setShowAssignModal(false)} disabled={assignLoading}>
                Annulla
              </button>
              <button className="cd-btn-save" onClick={handleAssignProfessional} disabled={assignLoading}>
                {assignLoading ? (
                  <><span className="spinner-border spinner-border-sm me-2"></span>Assegnazione...</>
                ) : (
                  <><i className="ri-check-line"></i>Assegna</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Interrupt Assignment Modal */}
      {showInterruptModal && interruptingAssignment && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal">
            <div className="cd-modal-header">
              <h5>
                <i className="ri-user-unfollow-line text-danger"></i>
                Rimuovi Assegnazione
              </h5>
              <button className="cd-modal-close" onClick={() => setShowInterruptModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-alert cd-alert-warning" style={{ marginBottom: 12 }}>
                <i className={`${TIPO_PROFESSIONISTA_ICONS[interruptingAssignment.tipo_professionista]} fs-4`}></i>
                <div>
                  <strong>{interruptingAssignment.professionista_nome}</strong>
                  <div className="small text-muted">
                    {TIPO_PROFESSIONISTA_LABELS[interruptingAssignment.tipo_professionista]} • dal {interruptingAssignment.data_dal}
                  </div>
                </div>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Motivazione Interruzione *</label>
                <textarea
                  className="cd-textarea"
                  rows="3"
                  placeholder="Es: Fine percorso, Cambio professionista, Incompatibilità, Richiesta cliente..."
                  value={interruptForm.motivazione_interruzione}
                  onChange={(e) => setInterruptForm({ ...interruptForm, motivazione_interruzione: e.target.value })}
                ></textarea>
              </div>
            </div>
            <div className="cd-modal-footer">
              <button className="cd-btn-back" onClick={() => setShowInterruptModal(false)} disabled={assignLoading}>
                Annulla
              </button>
              <button className="cd-btn-save" style={{ background: '#ef4444' }} onClick={handleInterruptAssignment} disabled={assignLoading}>
                {assignLoading ? (
                  <><span className="spinner-border spinner-border-sm me-2"></span>Rimozione...</>
                ) : (
                  <><i className="ri-close-line"></i>Rimuovi Assegnazione</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Meal Plan Modal */}
      {showAddMealPlanModal && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal">
            <div className="cd-modal-header success-bg">
              <h5>
                <i className="ri-restaurant-line text-success"></i>
                Nuovo Piano Alimentare
              </h5>
              <button className="cd-modal-close" onClick={() => setShowAddMealPlanModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-field">
                <label className="cd-field-label">Nome Piano (opzionale)</label>
                <input
                  type="text"
                  className="cd-input"
                  placeholder="Es: Piano Alimentare Gennaio 2026"
                  value={mealPlanForm.name}
                  onChange={(e) => setMealPlanForm({ ...mealPlanForm, name: e.target.value })}
                />
                <small className="text-muted">Se vuoto, verrà generato automaticamente</small>
              </div>
              <div className="cd-form-grid cols-2">
                <div>
                  <label className="cd-field-label">Data Inizio *</label>
                  <DatePicker
                    className="cd-input"
                    value={mealPlanForm.start_date}
                    onChange={(e) => setMealPlanForm({ ...mealPlanForm, start_date: e.target.value })}
                  />
                </div>
                <div>
                  <label className="cd-field-label">Data Fine *</label>
                  <DatePicker
                    className="cd-input"
                    value={mealPlanForm.end_date}
                    onChange={(e) => setMealPlanForm({ ...mealPlanForm, end_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Piano Alimentare (PDF) *</label>
                <input
                  type="file"
                  className="cd-input"
                  accept=".pdf"
                  onChange={(e) => setMealPlanFile(e.target.files[0])}
                />
                <small className="text-muted">Carica il piano alimentare in formato PDF (max 50MB)</small>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Note (opzionale)</label>
                <textarea
                  className="cd-textarea"
                  rows="2"
                  placeholder="Note aggiuntive..."
                  value={mealPlanForm.notes}
                  onChange={(e) => setMealPlanForm({ ...mealPlanForm, notes: e.target.value })}
                ></textarea>
              </div>
            </div>
            <div className="cd-modal-footer">
              <button
                className="cd-btn-back"
                onClick={() => {
                  setShowAddMealPlanModal(false);
                  setMealPlanForm({ name: '', start_date: '', end_date: '', notes: '' });
                  setMealPlanFile(null);
                }}
                disabled={savingMealPlan}
              >
                Annulla
              </button>
              <button className="cd-btn-save" style={{ background: '#22c55e' }} onClick={handleAddMealPlan} disabled={savingMealPlan}>
                {savingMealPlan ? (
                  <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                ) : (
                  <><i className="ri-save-line"></i>Salva Piano</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Meal Plan PDF Modal */}
      {showPreviewPlanModal && selectedPlan && (
        <div className="cd-modal-backdrop" onClick={() => setShowPreviewPlanModal(false)}>
          <div className="cd-modal xl full-height" onClick={(e) => e.stopPropagation()}>
            <div className="cd-modal-header success-bg">
              <h5>
                <i className="ri-file-pdf-line text-success"></i>
                {selectedPlan.name || 'Piano Alimentare'}
              </h5>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <a
                  href={`/uploads/${selectedPlan.piano_alimentare_file_path}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="cd-btn-action-sm"
                >
                  <i className="ri-download-line"></i>
                  Scarica
                </a>
                <button className="cd-modal-close" onClick={() => setShowPreviewPlanModal(false)}><i className="ri-close-line"></i></button>
              </div>
            </div>
            <div className="cd-modal-body fill">
              <iframe
                src={`/uploads/${selectedPlan.piano_alimentare_file_path}`}
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="Piano Alimentare PDF"
              />
            </div>
          </div>
        </div>
      )}

      {/* Edit Meal Plan Modal */}
      {showEditPlanModal && selectedPlan && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal">
            <div className="cd-modal-header blue-bg">
              <h5>
                <i className="ri-edit-line text-primary"></i>
                Modifica Piano Alimentare
              </h5>
              <button className="cd-modal-close" onClick={() => setShowEditPlanModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-alert cd-alert-info" style={{ marginBottom: 12 }}>
                <i className="ri-information-line"></i>
                Stai modificando: <strong>{selectedPlan.name || 'Piano Alimentare'}</strong>
              </div>
              <div className="cd-form-grid cols-2">
                <div>
                  <label className="cd-field-label">Data Inizio *</label>
                  <DatePicker
                    className="cd-input"
                    value={editPlanForm.start_date}
                    onChange={(e) => setEditPlanForm({ ...editPlanForm, start_date: e.target.value })}
                  />
                </div>
                <div>
                  <label className="cd-field-label">Data Fine *</label>
                  <DatePicker
                    className="cd-input"
                    value={editPlanForm.end_date}
                    onChange={(e) => setEditPlanForm({ ...editPlanForm, end_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Nuovo PDF (opzionale)</label>
                <input
                  type="file"
                  className="cd-input"
                  accept=".pdf"
                  onChange={(e) => setEditPlanFile(e.target.files[0])}
                />
                <small className="text-muted">Lascia vuoto per mantenere il PDF esistente</small>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Note (opzionale)</label>
                <textarea
                  className="cd-textarea"
                  rows="2"
                  placeholder="Note aggiuntive..."
                  value={editPlanForm.notes}
                  onChange={(e) => setEditPlanForm({ ...editPlanForm, notes: e.target.value })}
                ></textarea>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Motivo della modifica</label>
                <input
                  type="text"
                  className="cd-input"
                  placeholder="Es: Aggiornamento calorie settimanali"
                  value={editPlanForm.change_reason}
                  onChange={(e) => setEditPlanForm({ ...editPlanForm, change_reason: e.target.value })}
                />
                <small className="text-muted">Opzionale, verrà salvato nello storico delle modifiche</small>
              </div>
            </div>
            <div className="cd-modal-footer">
              <button
                className="cd-btn-back"
                onClick={() => {
                  setShowEditPlanModal(false);
                  setSelectedPlan(null);
                  setEditPlanForm({ start_date: '', end_date: '', notes: '', change_reason: '' });
                  setEditPlanFile(null);
                }}
                disabled={savingMealPlan}
              >
                Annulla
              </button>
              <button className="cd-btn-save" onClick={handleUpdateMealPlan} disabled={savingMealPlan}>
                {savingMealPlan ? (
                  <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                ) : (
                  <><i className="ri-save-line"></i>Salva Modifiche</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {showVersionsModal && selectedPlan && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal lg">
            <div className="cd-modal-header gray-bg">
              <h5>
                <i className="ri-history-line text-secondary"></i>
                Storico Modifiche
              </h5>
              <button className="cd-modal-close" onClick={() => { setShowVersionsModal(false); setPlanVersions([]); }}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-alert cd-alert-info" style={{ marginBottom: 12 }}>
                <i className="ri-information-line"></i>
                Piano: <strong>{selectedPlan.name || 'Piano Alimentare'}</strong>
              </div>
                {loadingVersions ? (
                  <div className="cd-loading">
                    <div className="cd-spinner"></div>
                    <p className="cd-loading-text">Caricamento storico...</p>
                  </div>
                ) : planVersions.length === 0 ? (
                  <div className="cd-empty">
                    <p className="cd-empty-text">
                      <i className="ri-information-line"></i>
                      {' '}Nessuna modifica registrata per questo piano
                    </p>
                  </div>
                ) : (
                  <div className="cd-table-wrap">
                    <table className="cd-table">
                      <thead>
                        <tr>
                          <th>Versione</th>
                          <th>Data Modifica</th>
                          <th>Modificato da</th>
                          <th>Periodo</th>
                          <th>Motivo</th>
                          <th>PDF</th>
                        </tr>
                      </thead>
                      <tbody>
                        {planVersions.map((version, idx) => (
                          <tr key={version.transaction_id || idx} className={version.is_current ? 'highlight-success' : ''}>
                            <td>
                              <span className="cd-badge" style={{ background: '#f3f4f6', color: '#6b7280' }}>v{version.version_number}</span>
                              {version.is_current && (
                                <span className="cd-badge" style={{ background: 'rgba(34,197,94,0.1)', color: '#16a34a', marginLeft: 4 }}>Attuale</span>
                              )}
                            </td>
                            <td>
                              {version.changed_at ? new Date(version.changed_at).toLocaleString('it-IT', {
                                day: '2-digit', month: '2-digit', year: 'numeric',
                                hour: '2-digit', minute: '2-digit'
                              }) : '-'}
                            </td>
                            <td>{version.changed_by || '-'}</td>
                            <td>
                              {version.start_date ? new Date(version.start_date).toLocaleDateString('it-IT') : '-'}
                              {' → '}
                              {version.end_date ? new Date(version.end_date).toLocaleDateString('it-IT') : '-'}
                            </td>
                            <td style={{ maxWidth: '200px' }}>
                              <span className="cd-text-truncate" style={{ maxWidth: '200px', display: 'inline-block' }} title={version.change_reason}>
                                {version.change_reason || '-'}
                              </span>
                            </td>
                            <td>
                              {version.has_file && version.piano_alimentare_file_path ? (
                                <a
                                  href={`/uploads/${version.piano_alimentare_file_path}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="cd-btn-action-sm"
                                  title="Scarica PDF"
                                >
                                  <i className="ri-download-line"></i>
                                </a>
                              ) : (
                                <span className="text-muted">-</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
            </div>
            <div className="cd-modal-footer">
              <button
                className="cd-btn-back"
                onClick={() => { setShowVersionsModal(false); setPlanVersions([]); }}
              >
                Chiudi
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Diario Entry Modal */}
      {showDiarioModal && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal">
            <div className="cd-modal-header pink-bg">
              <h5>
                <i className="ri-book-2-line" style={{ color: '#ec4899' }}></i>
                {diarioForm.id ? 'Modifica Nota' : 'Nuova Nota'}
              </h5>
              <button className="cd-modal-close" onClick={() => setShowDiarioModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-field">
                <label className="cd-field-label">Data *</label>
                <DatePicker
                  className="cd-input"
                  value={diarioForm.entry_date}
                  onChange={(e) => setDiarioForm({ ...diarioForm, entry_date: e.target.value })}
                />
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Contenuto *</label>
                <textarea
                  className="cd-textarea"
                  rows="6"
                  placeholder="Scrivi qui la nota del diario...&#10;&#10;• Progressi osservati&#10;• Difficoltà riscontrate&#10;• Aggiustamenti al piano&#10;• Feedback del cliente"
                  value={diarioForm.content}
                  onChange={(e) => setDiarioForm({ ...diarioForm, content: e.target.value })}
                ></textarea>
              </div>
            </div>
            <div className="cd-modal-footer">
              <button
                className="cd-btn-back"
                onClick={() => {
                  setShowDiarioModal(false);
                  setDiarioForm({ id: null, entry_date: '', content: '' });
                }}
                disabled={savingDiario}
              >
                Annulla
              </button>
              <button className="cd-btn-save" onClick={handleSaveDiarioEntry} disabled={savingDiario}>
                {savingDiario ? (
                  <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                ) : (
                  <><i className="ri-save-line"></i>Salva</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==================== COACHING MODALS ==================== */}

      {/* Add Training Plan Modal */}
      {showAddTrainingPlanModal && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cd-modal-header orange-bg">
              <h5>
                <i className="ri-run-line"></i>
                Nuovo Piano Allenamento
              </h5>
              <button className="cd-modal-close" onClick={() => setShowAddTrainingPlanModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-field">
                <label className="cd-field-label">Nome Piano (opzionale)</label>
                <input
                  type="text"
                  className="cd-input"
                  placeholder="Es: Programma Forza Fase 1"
                  value={trainingPlanForm.name}
                  onChange={(e) => setTrainingPlanForm({ ...trainingPlanForm, name: e.target.value })}
                />
              </div>
              <div className="cd-form-grid cols-2">
                <div className="cd-field">
                  <label className="cd-field-label">Data Inizio *</label>
                  <DatePicker
                    className="cd-input"
                    value={trainingPlanForm.start_date}
                    onChange={(e) => setTrainingPlanForm({ ...trainingPlanForm, start_date: e.target.value })}
                  />
                </div>
                <div className="cd-field">
                  <label className="cd-field-label">Data Fine *</label>
                  <DatePicker
                    className="cd-input"
                    value={trainingPlanForm.end_date}
                    onChange={(e) => setTrainingPlanForm({ ...trainingPlanForm, end_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Piano Allenamento (PDF) *</label>
                <input
                  type="file"
                  className="cd-input"
                  accept=".pdf"
                  onChange={(e) => setTrainingPlanFile(e.target.files[0])}
                />
                <small className="text-muted">Carica il piano di allenamento in formato PDF (max 50MB)</small>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Note (opzionale)</label>
                <textarea
                  className="cd-textarea"
                  rows="2"
                  placeholder="Note aggiuntive..."
                  value={trainingPlanForm.notes}
                  onChange={(e) => setTrainingPlanForm({ ...trainingPlanForm, notes: e.target.value })}
                ></textarea>
              </div>
            </div>
            <div className="cd-modal-footer">
              <button
                className="cd-btn-back"
                onClick={() => {
                  setShowAddTrainingPlanModal(false);
                  setTrainingPlanForm({ name: '', start_date: '', end_date: '', notes: '' });
                  setTrainingPlanFile(null);
                }}
                disabled={savingTrainingPlan}
              >
                Annulla
              </button>
              <button className="cd-btn-save" style={{ background: '#f59e0b' }} onClick={handleAddTrainingPlan} disabled={savingTrainingPlan}>
                {savingTrainingPlan ? (
                  <><span className="cd-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px', margin: '0 6px 0 0' }}></span>Salvataggio...</>
                ) : (
                  <><i className="ri-save-line"></i>Salva Piano</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Training Plan PDF Modal */}
      {showPreviewTrainingModal && selectedTrainingPlan && (
        <div className="cd-modal-backdrop" onClick={() => setShowPreviewTrainingModal(false)}>
          <div className="cd-modal xl full-height" onClick={(e) => e.stopPropagation()}>
            <div className="cd-modal-header orange-bg">
              <h5>
                <i className="ri-file-pdf-line"></i>
                {selectedTrainingPlan.name || 'Piano Allenamento'}
              </h5>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <a
                  href={`/uploads/${selectedTrainingPlan.piano_allenamento_file_path}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="cd-btn-action-sm"
                >
                  <i className="ri-download-line"></i>
                  Scarica
                </a>
                <button className="cd-modal-close" onClick={() => setShowPreviewTrainingModal(false)}><i className="ri-close-line"></i></button>
              </div>
            </div>
            <div className="cd-modal-body fill">
              <iframe
                src={`/uploads/${selectedTrainingPlan.piano_allenamento_file_path}`}
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="Piano Allenamento PDF"
              />
            </div>
          </div>
        </div>
      )}

      {/* Edit Training Plan Modal */}
      {showEditTrainingModal && selectedTrainingPlan && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cd-modal-header blue-bg">
              <h5>
                <i className="ri-edit-line"></i>
                Modifica Piano Allenamento
              </h5>
              <button className="cd-modal-close" onClick={() => setShowEditTrainingModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-alert cd-alert-info">
                <i className="ri-information-line"></i>
                Stai modificando: <strong>{selectedTrainingPlan.name || 'Piano Allenamento'}</strong>
              </div>
              <div className="cd-form-grid cols-2">
                <div className="cd-field">
                  <label className="cd-field-label">Data Inizio *</label>
                  <DatePicker
                    className="cd-input"
                    value={editTrainingForm.start_date}
                    onChange={(e) => setEditTrainingForm({ ...editTrainingForm, start_date: e.target.value })}
                  />
                </div>
                <div className="cd-field">
                  <label className="cd-field-label">Data Fine *</label>
                  <DatePicker
                    className="cd-input"
                    value={editTrainingForm.end_date}
                    onChange={(e) => setEditTrainingForm({ ...editTrainingForm, end_date: e.target.value })}
                  />
                </div>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Nuovo PDF (opzionale)</label>
                <input
                  type="file"
                  className="cd-input"
                  accept=".pdf"
                  onChange={(e) => setEditTrainingFile(e.target.files[0])}
                />
                <small className="text-muted">Lascia vuoto per mantenere il PDF esistente</small>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Note (opzionale)</label>
                <textarea
                  className="cd-textarea"
                  rows="2"
                  placeholder="Note aggiuntive..."
                  value={editTrainingForm.notes}
                  onChange={(e) => setEditTrainingForm({ ...editTrainingForm, notes: e.target.value })}
                ></textarea>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Motivo della modifica</label>
                <input
                  type="text"
                  className="cd-input"
                  placeholder="Es: Aggiornamento esercizi fase intermedia"
                  value={editTrainingForm.change_reason}
                  onChange={(e) => setEditTrainingForm({ ...editTrainingForm, change_reason: e.target.value })}
                />
                <small className="text-muted">Opzionale, verrà salvato nello storico delle modifiche</small>
              </div>
            </div>
            <div className="cd-modal-footer">
              <button
                className="cd-btn-back"
                onClick={() => {
                  setShowEditTrainingModal(false);
                  setSelectedTrainingPlan(null);
                  setEditTrainingForm({ start_date: '', end_date: '', notes: '', change_reason: '' });
                  setEditTrainingFile(null);
                }}
                disabled={savingTrainingPlan}
              >
                Annulla
              </button>
              <button className="cd-btn-save" onClick={handleUpdateTrainingPlan} disabled={savingTrainingPlan}>
                {savingTrainingPlan ? (
                  <><span className="cd-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px', margin: '0 6px 0 0' }}></span>Salvataggio...</>
                ) : (
                  <><i className="ri-save-line"></i>Salva Modifiche</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Training Plan Version History Modal */}
      {showTrainingVersionsModal && selectedTrainingPlan && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal lg" onClick={(e) => e.stopPropagation()}>
            <div className="cd-modal-header gray-bg">
              <h5>
                <i className="ri-history-line"></i>
                Storico Modifiche
              </h5>
              <button className="cd-modal-close" onClick={() => { setShowTrainingVersionsModal(false); setTrainingVersions([]); }}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-alert cd-alert-info">
                <i className="ri-information-line"></i>
                Piano: <strong>{selectedTrainingPlan.name || 'Piano Allenamento'}</strong>
              </div>
              {loadingTrainingVersions ? (
                <div className="cd-loading">
                  <div className="cd-spinner"></div>
                  <p className="cd-loading-text">Caricamento storico...</p>
                </div>
              ) : trainingVersions.length === 0 ? (
                <p className="cd-empty">
                  <i className="ri-information-line"></i>
                  Nessuna modifica registrata per questo piano
                </p>
              ) : (
                <div className="cd-table-wrap">
                  <table className="cd-table">
                    <thead>
                      <tr>
                        <th>Versione</th>
                        <th>Data Modifica</th>
                        <th>Modificato da</th>
                        <th>Periodo</th>
                        <th>Motivo</th>
                        <th>PDF</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trainingVersions.map((version, idx) => (
                        <tr key={version.transaction_id || idx} className={version.is_current ? 'highlight-warning' : ''}>
                          <td>
                            <span className="cd-badge" style={{ background: 'rgba(107,114,128,0.1)', color: '#6b7280' }}>v{version.version_number}</span>
                            {version.is_current && (
                              <span className="cd-badge" style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b', marginLeft: '4px' }}>Attuale</span>
                            )}
                          </td>
                          <td>
                            {version.changed_at ? new Date(version.changed_at).toLocaleString('it-IT', {
                              day: '2-digit', month: '2-digit', year: 'numeric',
                              hour: '2-digit', minute: '2-digit'
                            }) : '-'}
                          </td>
                          <td>{version.changed_by || '-'}</td>
                          <td>
                            {version.start_date ? new Date(version.start_date).toLocaleDateString('it-IT') : '-'}
                            {' → '}
                            {version.end_date ? new Date(version.end_date).toLocaleDateString('it-IT') : '-'}
                          </td>
                          <td style={{ maxWidth: '200px' }}>
                            <span className="cd-text-truncate" style={{ maxWidth: '200px', display: 'inline-block' }} title={version.change_reason}>
                              {version.change_reason || '-'}
                            </span>
                          </td>
                          <td>
                            {version.has_file && version.piano_allenamento_file_path ? (
                              <a
                                href={`/uploads/${version.piano_allenamento_file_path}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="cd-btn-action-sm"
                                title="Scarica PDF"
                              >
                                <i className="ri-download-line"></i>
                              </a>
                            ) : (
                              <span style={{ color: '#94a3b8' }}>-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div className="cd-modal-footer">
              <button
                className="cd-btn-back"
                onClick={() => { setShowTrainingVersionsModal(false); setTrainingVersions([]); }}
              >
                Chiudi
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Training Location Modal */}
      {showLocationModal && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cd-modal-header green-location-bg">
              <h5>
                <i className="ri-map-pin-line"></i>
                {locationForm.id ? 'Modifica Luogo' : 'Nuovo Luogo di Allenamento'}
              </h5>
              <button className="cd-modal-close" onClick={() => setShowLocationModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-field">
                <label className="cd-field-label">Luogo di Allenamento *</label>
                <select
                  className="cd-select"
                  value={locationForm.location}
                  onChange={(e) => setLocationForm({ ...locationForm, location: e.target.value })}
                >
                  <option value="">Seleziona...</option>
                  <option value="casa">Casa</option>
                  <option value="palestra">Palestra</option>
                  <option value="ibrido">Ibrido</option>
                </select>
              </div>
              <div className="cd-form-grid cols-2">
                <div className="cd-field">
                  <label className="cd-field-label">Data Inizio *</label>
                  <DatePicker
                    className="cd-input"
                    value={locationForm.start_date}
                    onChange={(e) => setLocationForm({ ...locationForm, start_date: e.target.value })}
                  />
                </div>
                <div className="cd-field">
                  <label className="cd-field-label">Data Fine (opzionale)</label>
                  <DatePicker
                    className="cd-input"
                    value={locationForm.end_date}
                    onChange={(e) => setLocationForm({ ...locationForm, end_date: e.target.value })}
                  />
                  <small className="text-muted">Lascia vuoto se ancora in corso</small>
                </div>
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Note (opzionale)</label>
                <textarea
                  className="cd-textarea"
                  rows="2"
                  placeholder="Note aggiuntive sul luogo..."
                  value={locationForm.notes}
                  onChange={(e) => setLocationForm({ ...locationForm, notes: e.target.value })}
                ></textarea>
              </div>
              {locationForm.id && (
                <div className="cd-field">
                  <label className="cd-field-label">Motivo della modifica</label>
                  <input
                    type="text"
                    className="cd-input"
                    placeholder="Es: Cambio palestra, Inizio fase home training..."
                    value={locationForm.change_reason}
                    onChange={(e) => setLocationForm({ ...locationForm, change_reason: e.target.value })}
                  />
                </div>
              )}
            </div>
            <div className="cd-modal-footer">
              <button
                className="cd-btn-back"
                onClick={() => {
                  setShowLocationModal(false);
                  setLocationForm({ id: null, location: '', start_date: '', end_date: '', notes: '', change_reason: '' });
                }}
                disabled={savingLocation}
              >
                Annulla
              </button>
              <button className="cd-btn-save" style={{ background: '#22c55e' }} onClick={handleSaveLocation} disabled={savingLocation}>
                {savingLocation ? (
                  <><span className="cd-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px', margin: '0 6px 0 0' }}></span>Salvataggio...</>
                ) : (
                  <><i className="ri-save-line"></i>Salva</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Coaching Diario Entry Modal */}
      {showDiarioCoachingModal && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cd-modal-header orange-bg">
              <h5>
                <i className="ri-book-2-line"></i>
                {diarioCoachingForm.id ? 'Modifica Nota Coaching' : 'Nuova Nota Coaching'}
              </h5>
              <button className="cd-modal-close" onClick={() => setShowDiarioCoachingModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-field">
                <label className="cd-field-label">Data *</label>
                <DatePicker
                  className="cd-input"
                  value={diarioCoachingForm.entry_date}
                  onChange={(e) => setDiarioCoachingForm({ ...diarioCoachingForm, entry_date: e.target.value })}
                />
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Contenuto *</label>
                <textarea
                  className="cd-textarea"
                  rows="6"
                  placeholder="Scrivi qui la nota del diario coaching...&#10;&#10;• Progressi allenamento&#10;• Performance osservata&#10;• Aggiustamenti al piano&#10;• Feedback del cliente"
                  value={diarioCoachingForm.content}
                  onChange={(e) => setDiarioCoachingForm({ ...diarioCoachingForm, content: e.target.value })}
                ></textarea>
              </div>
            </div>
            <div className="cd-modal-footer">
              <button
                className="cd-btn-back"
                onClick={() => {
                  setShowDiarioCoachingModal(false);
                  setDiarioCoachingForm({ id: null, entry_date: '', content: '' });
                }}
                disabled={savingDiarioCoaching}
              >
                Annulla
              </button>
              <button className="cd-btn-save" style={{ background: '#f59e0b' }} onClick={handleSaveDiarioCoaching} disabled={savingDiarioCoaching}>
                {savingDiarioCoaching ? (
                  <><span className="cd-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px', margin: '0 6px 0 0' }}></span>Salvataggio...</>
                ) : (
                  <><i className="ri-save-line"></i>Salva</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Psicologia Diario Entry Modal */}
      {showDiarioPsicologiaModal && (
        <div className="cd-modal-backdrop">
          <div className="cd-modal" onClick={(e) => e.stopPropagation()}>
            <div className="cd-modal-header purple-bg">
              <h5>
                <i className="ri-book-2-line" style={{ color: '#a855f7' }}></i>
                {diarioPsicologiaForm.id ? 'Modifica Nota Psicologia' : 'Nuova Nota Psicologia'}
              </h5>
              <button className="cd-modal-close" onClick={() => setShowDiarioPsicologiaModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              <div className="cd-field">
                <label className="cd-field-label">Data *</label>
                <DatePicker
                  className="cd-input"
                  value={diarioPsicologiaForm.entry_date}
                  onChange={(e) => setDiarioPsicologiaForm({ ...diarioPsicologiaForm, entry_date: e.target.value })}
                />
              </div>
              <div className="cd-field">
                <label className="cd-field-label">Contenuto *</label>
                <textarea
                  className="cd-textarea"
                  rows="6"
                  placeholder="Scrivi qui la nota del diario psicologia...&#10;&#10;• Progressi terapeutici&#10;• Osservazioni cliniche&#10;• Punti trattati nella seduta&#10;• Note per il prossimo incontro"
                  value={diarioPsicologiaForm.content}
                  onChange={(e) => setDiarioPsicologiaForm({ ...diarioPsicologiaForm, content: e.target.value })}
                ></textarea>
              </div>
            </div>
            <div className="cd-modal-footer">
              <button
                className="cd-btn-back"
                onClick={() => {
                  setShowDiarioPsicologiaModal(false);
                  setDiarioPsicologiaForm({ id: null, entry_date: '', content: '' });
                }}
                disabled={savingDiarioPsicologia}
              >
                Annulla
              </button>
              <button className="cd-btn-save" style={{ background: '#a855f7', color: 'white' }} onClick={handleSaveDiarioPsicologia} disabled={savingDiarioPsicologia}>
                {savingDiarioPsicologia ? (
                  <><span className="cd-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px', margin: '0 6px 0 0' }}></span>Salvataggio...</>
                ) : (
                  <><i className="ri-save-line"></i>Salva</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Check Response Detail Modal — same style as CheckAzienda */}
      {showCheckResponseModal && selectedCheckResponse && createPortal(
        <div className="chk-modal-backdrop" onClick={() => setShowCheckResponseModal(false)}>
          <div className="chk-modal" onClick={(e) => e.stopPropagation()}>
            {/* HEADER */}
            <div className="chk-modal-header">
              <div className="chk-modal-header-left">
                <div className={`chk-modal-type-dot ${selectedCheckResponse.type || 'weekly'}`}></div>
                <h5 className="chk-modal-title">
                  {selectedCheckResponse.type === 'weekly' ? 'Check Settimanale' : selectedCheckResponse.type === 'dca' ? 'Check DCA' : 'Check Minori'}
                </h5>
              </div>
              <button className="chk-modal-close" onClick={() => setShowCheckResponseModal(false)}>
                <i className="ri-close-line"></i>
              </button>
            </div>

            {/* BODY */}
            <div className="chk-modal-body">
              {loadingCheckDetail ? (
                <div className="chk-loading">
                  <div className="spinner-border"></div>
                  <p>Caricamento dettagli...</p>
                </div>
              ) : (
                <>
                  {/* Info grid */}
                  <div className="chk-modal-section">
                    <div className="chk-modal-grid">
                      <div className="chk-modal-field">
                        <span className="chk-modal-label">Data compilazione</span>
                        <span className="chk-modal-value">{selectedCheckResponse.submit_date || '-'}</span>
                      </div>
                      {selectedCheckResponse.type === 'weekly' && (
                        <div className="chk-modal-field">
                          <span className="chk-modal-label">Peso</span>
                          <span className="chk-modal-value">{selectedCheckResponse.weight ? `${selectedCheckResponse.weight} kg` : '-'}</span>
                        </div>
                      )}
                      <div className="chk-modal-field">
                        <span className="chk-modal-label">Tipo</span>
                        <span className={`chk-modal-type-badge ${selectedCheckResponse.type || 'weekly'}`}>
                          <i className={selectedCheckResponse.type === 'weekly' ? 'ri-calendar-check-line' : selectedCheckResponse.type === 'dca' ? 'ri-heart-pulse-line' : 'ri-user-heart-line'}></i>
                          {selectedCheckResponse.type === 'weekly' ? 'Settimanale' : selectedCheckResponse.type === 'dca' ? 'DCA' : 'Minori'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Photos — Weekly */}
                  {selectedCheckResponse.type === 'weekly' && (
                    <div className="chk-modal-section">
                      <span className="chk-modal-label">Foto Progressi</span>
                      <div className="chk-photo-grid">
                        {[
                          { key: 'photo_front', label: 'Frontale' },
                          { key: 'photo_side', label: 'Laterale' },
                          { key: 'photo_back', label: 'Posteriore' },
                        ].map((photo) => (
                          <div key={photo.key} className="chk-photo-slot">
                            <label>{photo.label}</label>
                            {selectedCheckResponse[photo.key] ? (
                              <img
                                src={selectedCheckResponse[photo.key]}
                                alt={photo.label}
                                onClick={() => setLightboxUrl(selectedCheckResponse[photo.key])}
                                onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling && (e.target.nextSibling.style.display = 'flex'); }}
                              />
                            ) : null}
                            <div className="chk-photo-empty" style={selectedCheckResponse[photo.key] ? { display: 'none' } : {}}><i className="ri-image-line"></i> Non caricata</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Ratings */}
                  {(selectedCheckResponse.nutritionist_rating || selectedCheckResponse.psychologist_rating ||
                    selectedCheckResponse.coach_rating || selectedCheckResponse.progress_rating) && (
                    <div className="chk-modal-section">
                      <span className="chk-modal-label">Valutazioni Professionisti</span>
                      <div className="chk-modal-ratings">
                        {selectedCheckResponse.nutritionist_rating && (() => {
                          const nutriInfo = getWeeklySnapshotProfessional(selectedCheckResponse, 'nutritionist');
                          const nutri = nutriInfo?.assignment;
                          const initials = nutri?.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??';
                          return (
                            <div className="chk-modal-rating-card green">
                              {nutri?.avatar_path
                                ? <img src={nutri.avatar_path} alt="" className="avatar" />
                                : <div className="initials green">{initials}</div>}
                              <div className="value">{selectedCheckResponse.nutritionist_rating}</div>
                              <div className="name">{nutriInfo?.name || 'Nutrizionista'}</div>
                            </div>
                          );
                        })()}
                        {selectedCheckResponse.psychologist_rating && (() => {
                          const psicoInfo = getWeeklySnapshotProfessional(selectedCheckResponse, 'psychologist');
                          const psico = psicoInfo?.assignment;
                          const initials = psico?.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??';
                          return (
                            <div className="chk-modal-rating-card amber">
                              {psico?.avatar_path
                                ? <img src={psico.avatar_path} alt="" className="avatar" />
                                : <div className="initials amber">{initials}</div>}
                              <div className="value">{selectedCheckResponse.psychologist_rating}</div>
                              <div className="name">{psicoInfo?.name || 'Psicologo/a'}</div>
                            </div>
                          );
                        })()}
                        {selectedCheckResponse.coach_rating && (() => {
                          const coachInfo = getWeeklySnapshotProfessional(selectedCheckResponse, 'coach');
                          const coach = coachInfo?.assignment;
                          const initials = coach?.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??';
                          return (
                            <div className="chk-modal-rating-card blue">
                              {coach?.avatar_path
                                ? <img src={coach.avatar_path} alt="" className="avatar" />
                                : <div className="initials blue">{initials}</div>}
                              <div className="value">{selectedCheckResponse.coach_rating}</div>
                              <div className="name">{coachInfo?.name || 'Coach'}</div>
                            </div>
                          );
                        })()}
                        {selectedCheckResponse.progress_rating && (
                          <div className="chk-modal-rating-card purple">
                            <div className="initials purple"><i className="ri-line-chart-line"></i></div>
                            <div className="value">{selectedCheckResponse.progress_rating}</div>
                            <div className="name">Progresso</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Wellness — Weekly */}
                  {selectedCheckResponse.type === 'weekly' && (
                    <div className="chk-modal-section">
                      <span className="chk-modal-label">Benessere</span>
                      <div className="chk-wellness-grid">
                        {[
                          { key: 'digestion_rating', label: 'Digestione', icon: 'ri-restaurant-line' },
                          { key: 'energy_rating', label: 'Energia', icon: 'ri-flashlight-line' },
                          { key: 'strength_rating', label: 'Forza', icon: 'ri-boxing-line' },
                          { key: 'hunger_rating', label: 'Fame', icon: 'ri-restaurant-2-line' },
                          { key: 'sleep_rating', label: 'Sonno', icon: 'ri-moon-line' },
                          { key: 'mood_rating', label: 'Umore', icon: 'ri-emotion-happy-line' },
                          { key: 'motivation_rating', label: 'Motivazione', icon: 'ri-fire-line' },
                        ].map(item => (
                          <div key={item.key} className="chk-wellness-item">
                            <i className={`${item.icon} chk-wellness-icon`}></i>
                            <span className="label">{item.label}</span>
                            <span className="value">
                              {selectedCheckResponse[item.key] != null ? `${selectedCheckResponse[item.key]}/10` : '-'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* DCA Detail Sections */}
                  {selectedCheckResponse.type === 'dca' && (
                    <>
                      <div className="chk-modal-section">
                        <span className="chk-modal-label">Benessere Emotivo</span>
                        <div className="chk-wellness-grid">
                          {[
                            { key: 'mood_balance_rating', label: 'Equilibrio umore', icon: 'ri-emotion-happy-line' },
                            { key: 'food_plan_serenity', label: 'Serenita\u0300 piano alimentare', icon: 'ri-leaf-line' },
                            { key: 'food_weight_worry', label: 'Preoccupazione peso/cibo', icon: 'ri-scales-3-line' },
                            { key: 'emotional_eating', label: 'Alimentazione emotiva', icon: 'ri-emotion-sad-line' },
                            { key: 'body_comfort', label: 'Comfort corporeo', icon: 'ri-body-scan-line' },
                            { key: 'body_respect', label: 'Rispetto del corpo', icon: 'ri-heart-line' },
                          ].map(item => (
                            <div key={item.key} className="chk-wellness-item">
                              <i className={`${item.icon} chk-wellness-icon`}></i>
                              <span className="label">{item.label}</span>
                              <span className="value">{selectedCheckResponse[item.key] != null ? `${selectedCheckResponse[item.key]}/5` : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="chk-modal-section">
                        <span className="chk-modal-label">Allenamento</span>
                        <div className="chk-wellness-grid">
                          {[
                            { key: 'exercise_wellness', label: 'Esercizio come benessere', icon: 'ri-run-line' },
                            { key: 'exercise_guilt', label: 'Senso di colpa esercizio', icon: 'ri-error-warning-line' },
                          ].map(item => (
                            <div key={item.key} className="chk-wellness-item">
                              <i className={`${item.icon} chk-wellness-icon`}></i>
                              <span className="label">{item.label}</span>
                              <span className="value">{selectedCheckResponse[item.key] != null ? `${selectedCheckResponse[item.key]}/5` : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="chk-modal-section">
                        <span className="chk-modal-label">Riposo e Relazioni</span>
                        <div className="chk-wellness-grid">
                          {[
                            { key: 'sleep_satisfaction', label: 'Soddisfazione sonno', icon: 'ri-moon-line' },
                            { key: 'relationship_time', label: 'Tempo relazioni', icon: 'ri-group-line' },
                            { key: 'personal_time', label: 'Tempo personale', icon: 'ri-user-smile-line' },
                          ].map(item => (
                            <div key={item.key} className="chk-wellness-item">
                              <i className={`${item.icon} chk-wellness-icon`}></i>
                              <span className="label">{item.label}</span>
                              <span className="value">{selectedCheckResponse[item.key] != null ? `${selectedCheckResponse[item.key]}/5` : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="chk-modal-section">
                        <span className="chk-modal-label">Emozioni e Gestione</span>
                        <div className="chk-wellness-grid">
                          {[
                            { key: 'life_interference', label: 'Interferenza sulla vita', icon: 'ri-forbid-line' },
                            { key: 'unexpected_management', label: 'Gestione imprevisti', icon: 'ri-shield-check-line' },
                            { key: 'self_compassion', label: 'Auto-compassione', icon: 'ri-heart-pulse-line' },
                            { key: 'inner_dialogue', label: 'Dialogo interiore', icon: 'ri-chat-heart-line' },
                          ].map(item => (
                            <div key={item.key} className="chk-wellness-item">
                              <i className={`${item.icon} chk-wellness-icon`}></i>
                              <span className="label">{item.label}</span>
                              <span className="value">{selectedCheckResponse[item.key] != null ? `${selectedCheckResponse[item.key]}/5` : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="chk-modal-section">
                        <span className="chk-modal-label">Sostenibilita\u0300 e Motivazione</span>
                        <div className="chk-wellness-grid">
                          {[
                            { key: 'long_term_sustainability', label: 'Sostenibilita\u0300 lungo termine', icon: 'ri-timer-line' },
                            { key: 'values_alignment', label: 'Allineamento valori', icon: 'ri-compass-3-line' },
                            { key: 'motivation_level', label: 'Livello motivazione', icon: 'ri-fire-line' },
                          ].map(item => (
                            <div key={item.key} className="chk-wellness-item">
                              <i className={`${item.icon} chk-wellness-icon`}></i>
                              <span className="label">{item.label}</span>
                              <span className="value">{selectedCheckResponse[item.key] != null ? `${selectedCheckResponse[item.key]}/5` : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="chk-modal-section">
                        <span className="chk-modal-label">Organizzazione Pasti</span>
                        <div className="chk-wellness-grid">
                          {[
                            { key: 'meal_organization', label: 'Organizzazione pasti', icon: 'ri-restaurant-line' },
                            { key: 'meal_stress', label: 'Stress pasti', icon: 'ri-alarm-warning-line' },
                            { key: 'shopping_awareness', label: 'Consapevolezza spesa', icon: 'ri-shopping-cart-line' },
                            { key: 'shopping_impact', label: 'Impatto spesa', icon: 'ri-shopping-bag-line' },
                            { key: 'meal_clarity', label: 'Chiarezza pasti', icon: 'ri-lightbulb-line' },
                          ].map(item => (
                            <div key={item.key} className="chk-wellness-item">
                              <i className={`${item.icon} chk-wellness-icon`}></i>
                              <span className="label">{item.label}</span>
                              <span className="value">{selectedCheckResponse[item.key] != null ? `${selectedCheckResponse[item.key]}/5` : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="chk-modal-section">
                        <span className="chk-modal-label">Parametri Fisici</span>
                        <div className="chk-wellness-grid">
                          {[
                            { key: 'digestion_rating', label: 'Digestione', icon: 'ri-restaurant-line' },
                            { key: 'energy_rating', label: 'Energia', icon: 'ri-flashlight-line' },
                            { key: 'strength_rating', label: 'Forza', icon: 'ri-boxing-line' },
                            { key: 'hunger_rating', label: 'Fame', icon: 'ri-restaurant-2-line' },
                            { key: 'sleep_rating', label: 'Sonno', icon: 'ri-moon-line' },
                            { key: 'mood_rating', label: 'Umore', icon: 'ri-emotion-happy-line' },
                            { key: 'motivation_rating', label: 'Motivazione', icon: 'ri-fire-line' },
                          ].map(item => (
                            <div key={item.key} className="chk-wellness-item">
                              <i className={`${item.icon} chk-wellness-icon`}></i>
                              <span className="label">{item.label}</span>
                              <span className="value">{selectedCheckResponse[item.key] != null ? `${selectedCheckResponse[item.key]}/10` : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="chk-modal-section">
                        <span className="chk-modal-label">Referral</span>
                        <div className="chk-feedback-block neutral"><p>{selectedCheckResponse.referral || <span className="chk-empty-text">Nessun referral indicato</span>}</p></div>
                      </div>
                    </>
                  )}

                  {/* Minor Detail Sections */}
                  {selectedCheckResponse.type === 'minor' && (
                    <>
                      <div className="chk-modal-section">
                        <span className="chk-modal-label">Dati Antropometrici</span>
                        <div className="chk-stats-row">
                          <div className="chk-stat-box"><label>Peso attuale</label><span>{selectedCheckResponse.peso_attuale ? `${selectedCheckResponse.peso_attuale} kg` : '-'}</span></div>
                          <div className="chk-stat-box"><label>Altezza</label><span>{selectedCheckResponse.altezza ? `${selectedCheckResponse.altezza} cm` : '-'}</span></div>
                        </div>
                      </div>
                      <div className="chk-modal-section">
                        <span className="chk-modal-label">EDE-Q6 Scores</span>
                        <div className="chk-modal-ratings">
                          {[
                            { key: 'score_global', label: 'Global Score', color: 'purple' },
                            { key: 'score_restraint', label: 'Restrizione', color: 'green' },
                            { key: 'score_eating_concern', label: 'Preoccup. Alimentare', color: 'amber' },
                            { key: 'score_shape_concern', label: 'Preoccup. Forma', color: 'blue' },
                            { key: 'score_weight_concern', label: 'Preoccup. Peso', color: 'green' },
                          ].map(item => (
                            <div key={item.key} className={`chk-modal-rating-card ${item.color}`}>
                              <div className={`initials ${item.color}`}>
                                <i className={item.key === 'score_global' ? 'ri-bar-chart-box-line' : 'ri-pie-chart-line'}></i>
                              </div>
                              <div className="value">{selectedCheckResponse[item.key] != null ? selectedCheckResponse[item.key].toFixed(2) : '-'}</div>
                              <div className="name">{item.label}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                      {selectedCheckResponse.score_global != null && (
                        <div className="chk-modal-section">
                          <span className="chk-modal-label">Indicazione Clinica</span>
                          <div className={`chk-feedback-block ${selectedCheckResponse.score_global >= 4 ? 'red' : selectedCheckResponse.score_global >= 2.5 ? 'amber' : 'green'}`}>
                            <label>
                              {selectedCheckResponse.score_global >= 4
                                ? 'Punteggio elevato \u2014 possibile significativita\u0300 clinica'
                                : selectedCheckResponse.score_global >= 2.5
                                ? 'Punteggio moderato \u2014 monitorare'
                                : 'Punteggio nella norma'}
                            </label>
                            <p>Global Score: {selectedCheckResponse.score_global.toFixed(2)} / 6.00</p>
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  {/* Professional Feedback — Weekly */}
                  {selectedCheckResponse.type === 'weekly' && (
                    <div className="chk-modal-section">
                      <span className="chk-modal-label">Feedback Professionisti</span>
                      <div className="chk-feedback-block green">
                        <label>Feedback Nutrizionista</label>
                        <p>{selectedCheckResponse.nutritionist_feedback || <span className="chk-empty-text">Non compilato</span>}</p>
                      </div>
                      <div className="chk-feedback-block amber">
                        <label>Feedback Psicologo</label>
                        <p>{selectedCheckResponse.psychologist_feedback || <span className="chk-empty-text">Non compilato</span>}</p>
                      </div>
                      <div className="chk-feedback-block blue">
                        <label>Feedback Coach</label>
                        <p>{selectedCheckResponse.coach_feedback || <span className="chk-empty-text">Non compilato</span>}</p>
                      </div>
                    </div>
                  )}

                  {/* Programs — Weekly */}
                  {selectedCheckResponse.type === 'weekly' && (
                    <div className="chk-modal-section">
                      <span className="chk-modal-label">Programmi</span>
                      <div className="chk-feedback-block neutral"><label>Aderenza programma alimentare</label><p>{selectedCheckResponse.nutrition_program_adherence || <span className="chk-empty-text">Non compilato</span>}</p></div>
                      <div className="chk-feedback-block neutral"><label>Aderenza programma sportivo</label><p>{selectedCheckResponse.training_program_adherence || <span className="chk-empty-text">Non compilato</span>}</p></div>
                      <div className="chk-feedback-block neutral"><label>Esercizi modificati/aggiunti</label><p>{selectedCheckResponse.exercise_modifications || <span className="chk-empty-text">Non compilato</span>}</p></div>
                      <div className="chk-stats-row">
                        <div className="chk-stat-box"><label>Passi giornalieri</label><span>{selectedCheckResponse.daily_steps || '-'}</span></div>
                        <div className="chk-stat-box"><label>Settimane completate</label><span>{selectedCheckResponse.completed_training_weeks || '-'}</span></div>
                        <div className="chk-stat-box"><label>Giorni allenamento</label><span>{selectedCheckResponse.planned_training_days || '-'}</span></div>
                      </div>
                      <div className="chk-feedback-block neutral" style={{ marginTop: '8px' }}><label>Tematiche live settimanali</label><p>{selectedCheckResponse.live_session_topics || <span className="chk-empty-text">Non compilato</span>}</p></div>
                    </div>
                  )}

                  {/* Reflections — Weekly */}
                  {selectedCheckResponse.type === 'weekly' && (
                    <div className="chk-modal-section">
                      <span className="chk-modal-label">Riflessioni</span>
                      <div className="chk-reflection success"><label><i className="ri-check-line"></i> Cosa ha funzionato</label><p>{selectedCheckResponse.what_worked || <span className="chk-empty-text">Non compilato</span>}</p></div>
                      <div className="chk-reflection danger"><label><i className="ri-close-line"></i> Cosa non ha funzionato</label><p>{selectedCheckResponse.what_didnt_work || <span className="chk-empty-text">Non compilato</span>}</p></div>
                      <div className="chk-reflection warning"><label><i className="ri-lightbulb-line"></i> Cosa ho imparato</label><p>{selectedCheckResponse.what_learned || <span className="chk-empty-text">Non compilato</span>}</p></div>
                      <div className="chk-reflection info"><label><i className="ri-focus-line"></i> Focus prossima settimana</label><p>{selectedCheckResponse.what_focus_next || <span className="chk-empty-text">Non compilato</span>}</p></div>
                      <div className="chk-feedback-block red" style={{ marginTop: '8px' }}><label><i className="ri-first-aid-kit-line"></i> Infortuni / Note importanti</label><p>{selectedCheckResponse.injuries_notes || <span className="chk-empty-text">Nessun infortunio segnalato</span>}</p></div>
                    </div>
                  )}

                  {/* Referral — Weekly */}
                  {selectedCheckResponse.type === 'weekly' && (
                    <div className="chk-modal-section">
                      <span className="chk-modal-label">Referral</span>
                      <div className="chk-feedback-block neutral"><p>{selectedCheckResponse.referral || <span className="chk-empty-text">Nessun referral indicato</span>}</p></div>
                    </div>
                  )}

                  {/* Extra Comments — Weekly & DCA */}
                  {(selectedCheckResponse.type === 'weekly' || selectedCheckResponse.type === 'dca') && (
                    <div className="chk-modal-section">
                      <span className="chk-modal-label">Commenti extra</span>
                      <div className="chk-feedback-block neutral"><p>{selectedCheckResponse.extra_comments || <span className="chk-empty-text">Nessun commento aggiuntivo</span>}</p></div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* FOOTER */}
            <div className="chk-modal-footer">
              <button className="chk-modal-close-btn" onClick={() => setShowCheckResponseModal(false)}>Chiudi</button>
            </div>
          </div>
        </div>,
        document.body
      )}
      {/* Modal Storico Diario */}
      {showDiaryHistoryModal && (
        <div className="cd-modal-backdrop" tabIndex="-1">
          <div className="cd-modal lg" onClick={(e) => e.stopPropagation()}>
            <div className="cd-modal-header">
              <h5>Storico Modifiche</h5>
              <button type="button" className="cd-modal-close" onClick={() => setShowDiaryHistoryModal(false)}><i className="ri-close-line"></i></button>
            </div>
            <div className="cd-modal-body">
              {loadingDiaryHistory ? (
                <div className="cd-loading">
                  <div className="cd-spinner"></div>
                </div>
              ) : diaryHistory.length === 0 ? (
                <p className="cd-empty">Nessuna modifica precedente trovata.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {diaryHistory.map((version, idx) => (
                    <div key={idx} className="cd-diary-entry">
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <small style={{ color: '#64748b' }}>
                          <i className="ri-time-line" style={{ marginRight: '4px' }}></i>
                          {version.modified_at}
                          <span style={{ margin: '0 8px' }}>•</span>
                          <i className="ri-user-line" style={{ marginRight: '4px' }}></i>
                          {version.author}
                        </small>
                      </div>
                      <p className="cd-diary-content" style={{ marginTop: '8px', marginBottom: '4px' }}>{version.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="cd-modal-footer">
              <button type="button" className="cd-btn-back" onClick={() => setShowDiaryHistoryModal(false)}>Chiudi</button>
            </div>
          </div>
        </div>
      )}

      {/* Support and Tour Components */}

      <GuidedTour
        key={tourKey}
        steps={activeTourSteps}
        isOpen={mostraTour}
        onClose={() => setMostraTour(false)}
        onComplete={() => {
          setMostraTour(false);
          console.log('Tour Dettaglio Paziente completato');
        }}
        onStepChange={(index, step) => {
          if (step.tabId) {
            setActiveTab(step.tabId);
          }
          if (step.onEnter) {
            step.onEnter();
          }
        }}
      />

      {/* Lightbox fullscreen photo */}
      {lightboxUrl && (
        <div className="cd-lightbox-backdrop" onClick={() => setLightboxUrl(null)}>
          <button className="cd-lightbox-close" onClick={() => setLightboxUrl(null)}>
            <i className="ri-close-line"></i>
          </button>
          <img src={lightboxUrl} alt="Foto" className="cd-lightbox-img" onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </>
  );
}

export default ClientiDetail;
